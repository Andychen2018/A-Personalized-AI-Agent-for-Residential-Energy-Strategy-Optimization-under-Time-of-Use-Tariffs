#!/usr/bin/env python3
"""
P052 - Event Scheduler
基于电器工作空间的事件调度优化器

功能：
1. 读取P051生成的电器工作空间文件
2. 提取可调度事件（is_reschedulable=True）
3. 基于价格等级和约束进行事件调度优化
4. 支持所有电价方案（UK、TOU_D、Germany_Variable）
5. 支持单用户和批量模式

输入：
- 电器工作空间：output/05_appliance_working_spaces/{tariff_name}/{house_id}/
- 可调度事件：output/04_TOU_filter/{tariff_name}/{house_id}/

输出：
- 调度结果：output/05_Initial_scheduling_optimization/{tariff_name}/{house_id}/
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
import glob

class EventScheduler:
    """基于电器工作空间的事件调度优化器"""

    def __init__(self, tariff_name: str, house_id: str = None):
        """
        初始化调度器

        Args:
            tariff_name: 电价方案名称
            house_id: 用户ID（可选，批量模式时为None）
        """
        self.tariff_name = tariff_name
        self.house_id = house_id
        self.appliance_spaces = {}
        self.season = None  # 用于TOU_D的季节性处理
        self.appliance_name_cache = {}  # 缓存电器名称映射结果
        self.mapping_messages = set()  # 避免重复显示映射信息
        self.appliance_id_mapping = {}  # 电器ID映射: appliance1 -> 真实电器名称
        self.reverse_id_mapping = {}   # 反向映射: 真实电器名称 -> appliance1

    def find_appliance_mapping(self, appliance_name: str, available_keys: List[str], cache_key: str = None) -> Optional[str]:
        """
        智能电器名称映射

        Args:
            appliance_name: 事件中的电器名称 (如 "Washing Machine")
            available_keys: 工作空间中可用的电器名称列表 (如 ["Washing Machine (1)", "Washing Machine (2)"])
            cache_key: 缓存键，用于避免重复计算

        Returns:
            映射后的电器名称，如果找不到则返回None
        """
        # 检查缓存
        if cache_key and cache_key in self.appliance_name_cache:
            return self.appliance_name_cache[cache_key]

        mapped_name = None

        # 1. 精确匹配
        if appliance_name in available_keys:
            mapped_name = appliance_name

        # 2. 带编号后缀匹配 (如 "Washing Machine" -> "Washing Machine (1)")
        if not mapped_name:
            for key in available_keys:
                if key.startswith(appliance_name + " (") or key.startswith(appliance_name + "("):
                    mapped_name = key
                    break

        # 3. 模糊匹配 (如 "Computer" -> "Computer Site", "Television" -> "Television Site")
        if not mapped_name:
            for key in available_keys:
                # 检查是否包含相同的主要词汇
                if appliance_name.lower() in key.lower():
                    mapped_name = key
                    break
                elif key.lower() in appliance_name.lower() and len(key) >= 4:
                    mapped_name = key
                    break

        # 4. 部分匹配 (如关键词匹配)
        if not mapped_name:
            appliance_words = appliance_name.lower().split()
            for key in available_keys:
                key_words = key.lower().split()
                # 检查是否有共同的关键词
                if any(word in key_words for word in appliance_words if len(word) >= 3):
                    mapped_name = key
                    break

        # 缓存结果
        if cache_key:
            self.appliance_name_cache[cache_key] = mapped_name

        return mapped_name

    def build_appliance_id_mapping(self, house_id: str) -> None:
        """
        建立电器ID映射表: appliance1 <-> 真实电器名称
        这样P052内部可以使用标准化ID，避免名称匹配问题
        """
        # 清空之前的映射
        self.appliance_id_mapping.clear()
        self.reverse_id_mapping.clear()

        # 获取所有可用的电器名称
        all_appliance_names = set()

        # 从工作空间获取电器名称
        if self.tariff_name == "TOU_D":
            # TOU_D有季节性工作空间
            for season in ["summer", "winter"]:
                if house_id in self.appliance_spaces and season in self.appliance_spaces[house_id]:
                    all_appliance_names.update(self.appliance_spaces[house_id][season].keys())
        else:
            # 其他电价方案
            if house_id in self.appliance_spaces:
                all_appliance_names.update(self.appliance_spaces[house_id].keys())

        # 建立映射: appliance1, appliance2, ... -> 真实电器名称
        sorted_names = sorted(all_appliance_names)  # 保证顺序一致

        for i, real_name in enumerate(sorted_names, 1):
            appliance_id = f"appliance{i}"
            self.appliance_id_mapping[appliance_id] = real_name
            self.reverse_id_mapping[real_name] = appliance_id

        print(f"   📋 Building appliance ID mapping table ({len(self.appliance_id_mapping)} appliances):")
        for appliance_id, real_name in self.appliance_id_mapping.items():
            print(f"     {appliance_id} ↔ {real_name}")

    def get_mapped_appliance_name(self, original_name: str, house_id: str) -> str:
        """
        获取映射后的电器名称，优先使用精确匹配，否则使用智能匹配

        Args:
            original_name: 事件中的原始电器名称 (如 "Washing Machine")
            house_id: 用户ID

        Returns:
            映射后的电器名称 (如 "Washing Machine (1)" 或 "appliance1")
        """
        # 1. 检查是否有精确的反向映射
        if original_name in self.reverse_id_mapping:
            mapped_id = self.reverse_id_mapping[original_name]
            return self.appliance_id_mapping[mapped_id]

        # 2. 智能匹配：寻找最佳匹配的电器
        best_match = None
        best_score = 0

        for real_name in self.reverse_id_mapping.keys():
            # 计算匹配分数
            score = self.calculate_name_match_score(original_name, real_name)
            if score > best_score:
                best_score = score
                best_match = real_name

        # 3. 如果找到了好的匹配，返回对应的真实名称
        if best_match and best_score > 0.7:  # 阈值可调
            return best_match

        # 4. 如果没有找到匹配，返回原始名称（保持向后兼容）
        return original_name

    def calculate_name_match_score(self, name1: str, name2: str) -> float:
        """计算两个电器名称的匹配分数"""
        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()

        # 精确匹配
        if name1_lower == name2_lower:
            return 1.0

        # 基础名称匹配 (如 "Washing Machine" vs "Washing Machine (1)")
        base1 = name1_lower.split("(")[0].strip()
        base2 = name2_lower.split("(")[0].strip()

        if base1 == base2:
            return 0.9

        # 包含关系匹配
        if base1 in base2 or base2 in base1:
            return 0.8

        # 关键词匹配
        words1 = set(base1.split())
        words2 = set(base2.split())

        if words1 and words2:
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union) * 0.7

        return 0.0

    def calculate_price_levels_for_intervals(self, available_intervals: List, house_id: str, event_date) -> Dict[str, List]:
        """
        为available_intervals动态计算价格等级

        Args:
            available_intervals: 可用时间区间列表 [[start_min, end_min], ...]
            house_id: 用户ID
            event_date: 事件日期

        Returns:
            按价格等级分组的区间字典 {"0": [[start, end], ...], "1": [...]}
        """
        price_level_intervals = {}

        # 加载该用户的价格等级数据
        price_levels = self.load_price_levels_for_date(house_id, event_date)

        if not price_levels:
            print(f"   ⚠️ 无法获取 {house_id} 在 {event_date} 的价格等级数据")
            return {}

        # 为每个时间区间计算价格等级
        for interval in available_intervals:
            if isinstance(interval, list) and len(interval) == 2:
                start_min, end_min = interval

                # 计算区间的主要价格等级（取区间中点的价格等级）
                mid_min = (start_min + end_min) // 2
                mid_hour = mid_min // 60
                mid_minute = mid_min % 60

                # 获取该时间点的价格等级
                price_level = self.get_price_level_at_time(price_levels, mid_hour, mid_minute)

                if price_level is not None:
                    level_str = str(price_level)
                    if level_str not in price_level_intervals:
                        price_level_intervals[level_str] = []
                    price_level_intervals[level_str].append([start_min, end_min])

        return price_level_intervals

    def load_price_levels_for_date(self, house_id: str, event_date) -> Optional[List]:
        """加载指定日期的价格等级数据"""
        try:
            # 🎯 根据电价方案返回标准的24小时价格等级数组
            if "/" in self.tariff_name:
                region, tariff = self.tariff_name.split("/", 1)
            else:
                tariff = self.tariff_name

            if tariff == "Economy_7":
                # Economy_7: 00:30-07:30为Level 0，其余为Level 1
                price_levels = [1] * 24  # 默认Level 1
                # 00:30-07:30设为Level 0
                # 注意：这里简化处理，将01:00-07:00设为Level 0
                # 实际应该是00:30-07:30，但按小时处理
                for hour in range(1, 8):  # 01:00-07:59
                    price_levels[hour] = 0
                return price_levels

            elif tariff == "Economy_10":
                # Economy_10: 00:00-05:00和13:00-16:00和20:00-22:00为Level 0
                price_levels = [1] * 24  # 默认Level 1
                # 00:00-04:59
                for hour in range(0, 5):
                    price_levels[hour] = 0
                # 13:00-15:59
                for hour in range(13, 16):
                    price_levels[hour] = 0
                # 20:00-21:59
                for hour in range(20, 22):
                    price_levels[hour] = 0
                return price_levels

            elif tariff == "Germany_Variable":
                # Germany_Variable: 动态价格，这里简化为固定模式
                # 假设夜间(22:00-06:00)为Level 0，其余为Level 1
                price_levels = [1] * 24
                for hour in range(22, 24):  # 22:00-23:59
                    price_levels[hour] = 0
                for hour in range(0, 6):   # 00:00-05:59
                    price_levels[hour] = 0
                return price_levels

            elif tariff == "TOU_D":
                # TOU_D: 复杂的季节性价格，这里简化
                # 假设夜间为Level 0，白天为Level 1，峰值为Level 2
                price_levels = [1] * 24
                # 夜间 00:00-05:59
                for hour in range(0, 6):
                    price_levels[hour] = 0
                # 峰值 16:00-20:59
                for hour in range(16, 21):
                    price_levels[hour] = 2
                return price_levels

            else:
                # 默认：夜间便宜
                price_levels = [1] * 24
                for hour in range(0, 6):
                    price_levels[hour] = 0
                return price_levels

        except Exception as e:
            print(f"   ⚠️ 加载价格等级数据失败: {e}")
            return None

    def get_price_level_at_time(self, price_levels: List[int], hour: int, minute: int) -> Optional[int]:
        """获取指定时间的价格等级"""
        if not price_levels or hour < 0 or hour >= 24:
            return None

        # 价格等级数组通常是24小时的，每小时一个等级
        if len(price_levels) == 24:
            return price_levels[hour]
        elif len(price_levels) == 1440:  # 每分钟一个等级
            time_index = hour * 60 + minute
            if 0 <= time_index < len(price_levels):
                return price_levels[time_index]

        return None

    def calculate_scheduling_benefit(self, original_start_min: int, new_start_min: int,
                                   duration_min: int, price_levels: List[int],
                                   original_level: int) -> float:
        """
        计算调度优化的收益分数

        Args:
            original_start_min: 原始开始时间（分钟）
            new_start_min: 新的开始时间（分钟）
            duration_min: 事件持续时间（分钟）
            price_levels: 24小时价格等级数组
            original_level: 原始价格等级

        Returns:
            float: 优化收益分数（越高越好）
        """
        if not price_levels:
            return 0.0

        # 计算原始时间段的价格等级分布
        original_distribution = {}
        for minute_offset in range(duration_min):
            current_min = (original_start_min + minute_offset) % 1440  # 处理跨天
            hour = current_min // 60
            if 0 <= hour < len(price_levels):
                level = price_levels[hour]
                original_distribution[level] = original_distribution.get(level, 0) + 1

        # 计算新时间段的价格等级分布
        new_distribution = {}
        for minute_offset in range(duration_min):
            current_min = (new_start_min + minute_offset) % 1440  # 处理跨天
            hour = current_min // 60
            if 0 <= hour < len(price_levels):
                level = price_levels[hour]
                new_distribution[level] = new_distribution.get(level, 0) + 1

        # 计算在最低价格等级的时间变化
        min_level = min(price_levels) if price_levels else 0
        original_low_minutes = original_distribution.get(min_level, 0)
        new_low_minutes = new_distribution.get(min_level, 0)
        low_minutes_gain = new_low_minutes - original_low_minutes

        # 计算加权成本变化（假设价格等级越低，价格越便宜）
        original_weighted_cost = sum(level * minutes for level, minutes in original_distribution.items())
        new_weighted_cost = sum(level * minutes for level, minutes in new_distribution.items())
        cost_improvement = original_weighted_cost - new_weighted_cost

        # 综合评分：优先考虑低价时间增加，其次考虑整体成本改善
        benefit_score = low_minutes_gain * 10 + cost_improvement

        return benefit_score

    def get_appliance_spaces_path(self, house_id: str, season: str = None) -> str:
        """获取电器工作空间文件路径"""
        # 解析tariff_name
        if "/" in self.tariff_name:
            region, tariff = self.tariff_name.split("/", 1)
            if tariff == "TOU_D" and season:
                return f"output/05_appliance_working_spaces/TOU_D/{season}/{house_id}/appliance_reschedulable_spaces.json"
            elif tariff in ["Economy_7", "Economy_10"]:
                return f"output/05_appliance_working_spaces/{region}/{tariff}/{house_id}/appliance_reschedulable_spaces.json"
            else:
                return f"output/05_appliance_working_spaces/{tariff}/{house_id}/appliance_reschedulable_spaces.json"
        else:
            if self.tariff_name == "TOU_D" and season:
                return f"output/05_appliance_working_spaces/TOU_D/{season}/{house_id}/appliance_reschedulable_spaces.json"
            elif self.tariff_name in ["Economy_7", "Economy_10"]:
                return f"output/05_appliance_working_spaces/UK/{self.tariff_name}/{house_id}/appliance_reschedulable_spaces.json"
            else:
                return f"output/05_appliance_working_spaces/{self.tariff_name}/{house_id}/appliance_reschedulable_spaces.json"

    def get_events_path(self, house_id: str) -> str:
        """获取可调度事件文件路径"""
        # 解析tariff_name，处理"UK/Economy_7"格式
        if "/" in self.tariff_name:
            region, tariff = self.tariff_name.split("/", 1)
        else:
            # 根据电价方案确定区域和路径
            if self.tariff_name == "TOU_D":
                region = "California"
                tariff = self.tariff_name
            elif self.tariff_name == "Germany_Variable":
                region = "Germany"
                tariff = self.tariff_name
            elif self.tariff_name in ["Economy_7", "Economy_10"]:
                region = "UK"
                tariff = self.tariff_name
            else:
                region = "UK"  # 默认
                tariff = self.tariff_name

        # 构建路径模式
        patterns = [
            f"output/04_TOU_filter/{region}/{tariff}/{house_id}/*.csv",
            f"output/04_user_constraints/{house_id}/shiftable_event_masked_{tariff}.csv"
        ]

        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                return files[0]

        return None

    def get_output_path(self, house_id: str, season: str = None) -> str:
        """获取输出文件路径"""
        # 解析tariff_name
        if "/" in self.tariff_name:
            region, tariff = self.tariff_name.split("/", 1)
            if tariff == "TOU_D" and season:
                return f"output/05_Initial_scheduling_optimization/TOU_D/{season}/{house_id}/scheduled_events.csv"
            elif tariff in ["Economy_7", "Economy_10"]:
                return f"output/05_Initial_scheduling_optimization/{region}/{tariff}/{house_id}/scheduled_events.csv"
            else:
                return f"output/05_Initial_scheduling_optimization/{tariff}/{house_id}/scheduled_events.csv"
        else:
            if self.tariff_name == "TOU_D" and season:
                return f"output/05_Initial_scheduling_optimization/TOU_D/{season}/{house_id}/scheduled_events.csv"
            elif self.tariff_name in ["Economy_7", "Economy_10"]:
                return f"output/05_Initial_scheduling_optimization/UK/{self.tariff_name}/{house_id}/scheduled_events.csv"
            else:
                return f"output/05_Initial_scheduling_optimization/{self.tariff_name}/{house_id}/scheduled_events.csv"

    def load_appliance_spaces(self, house_id: str, season: str = None) -> bool:
        """加载指定用户的电器工作空间"""
        try:
            if self.tariff_name == "TOU_D":
                # TOU_D需要加载两个季节的工作空间
                if house_id not in self.appliance_spaces:
                    self.appliance_spaces[house_id] = {}

                seasons = ["summer", "winter"]
                loaded_seasons = 0

                for s in seasons:
                    spaces_file = self.get_appliance_spaces_path(house_id, s)

                    if os.path.exists(spaces_file):
                        with open(spaces_file, 'r', encoding='utf-8') as f:
                            spaces_data = json.load(f)

                        self.appliance_spaces[house_id][s] = spaces_data
                        loaded_seasons += 1

                if loaded_seasons > 0:
                    print(f"✅ Loaded {house_id} appliance working spaces ({loaded_seasons} seasons)")
                    # Build appliance ID mapping table
                    self.build_appliance_id_mapping(house_id)
                    return True
                else:
                    print(f"❌ No seasonal working spaces found for {house_id}")
                    return False
            else:
                # 其他电价方案
                spaces_file = self.get_appliance_spaces_path(house_id, season)

                if not os.path.exists(spaces_file):
                    print(f"❌ 电器工作空间文件不存在: {spaces_file}")
                    return False

                with open(spaces_file, 'r', encoding='utf-8') as f:
                    self.appliance_spaces[house_id] = json.load(f)

                print(f"✅ Loaded {house_id} appliance working spaces ({len(self.appliance_spaces[house_id])} appliances)")
                # Build appliance ID mapping table
                self.build_appliance_id_mapping(house_id)
                return True

        except Exception as e:
            print(f"❌ Failed to load appliance working spaces: {e}")
            return False

    def load_and_extract_reschedulable_events(self, house_id: str) -> pd.DataFrame:
        """加载并提取可调度事件"""
        events_path = self.get_events_path(house_id)

        if not events_path or not os.path.exists(events_path):
            print(f"❌ 事件文件不存在: {events_path}")
            return pd.DataFrame()

        try:
            # 读取事件数据
            df = pd.read_csv(events_path, parse_dates=['start_time', 'end_time'])

            # 提取可调度事件
            df_reschedulable = df[df['is_reschedulable'] == True].copy()

            print(f"📊 {house_id} event statistics:")
            print(f"   Total events: {len(df)}")
            print(f"   Reschedulable events: {len(df_reschedulable)}")
            if len(df) > 0:
                print(f"   Reschedulable ratio: {len(df_reschedulable)/len(df)*100:.1f}%")

            return df_reschedulable

        except Exception as e:
            print(f"❌ Failed to read event file: {e}")
            return pd.DataFrame()

    def save_reschedulable_events(self, df: pd.DataFrame, house_id: str, season: str = None):
        """保存可调度事件到初始调度目录"""
        if df.empty:
            return

        output_path = self.get_output_path(house_id, season).replace('scheduled_events.csv', 'reschedulable_events.csv')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path, index=False)
        print(f"📁 Reschedulable events saved: {output_path}")
    
    def time_to_minutes(self, time_str: str) -> int:
        """时间字符串转分钟（支持48小时制）"""
        hour, minute = map(int, time_str.split(":"))
        return hour * 60 + minute
    
    def minutes_to_time_48h(self, minutes: int) -> str:
        """分钟转48小时制时间字符串"""
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"
    
    def minutes_to_datetime(self, minutes: int, base_date) -> pd.Timestamp:
        """将48小时制分钟转换为实际日期时间"""
        days = minutes // 1440  # 计算天数偏移
        remaining_minutes = minutes % 1440  # 当天的分钟数
        
        hours = remaining_minutes // 60
        mins = remaining_minutes % 60
        
        # 基于事件原始日期计算新日期
        new_date = base_date + pd.Timedelta(days=days)
        
        # 使用 datetime.time 创建时间对象，然后与日期组合
        from datetime import time
        time_obj = time(hour=hours, minute=mins)
        return pd.Timestamp.combine(new_date, time_obj)
    
    def find_optimal_schedule_for_event(self, event_row: pd.Series, house_id: str) -> Optional[Dict]:
        """为单个事件找到最优调度方案"""

        original_appliance_name = event_row['appliance_name']
        duration_min = int(event_row['duration(min)'])
        current_level = int(event_row['primary_price_level'])

        # 🎯 使用映射表转换电器名称，避免名称匹配问题
        appliance_name = self.get_mapped_appliance_name(original_appliance_name, house_id)

        # 获取原始开始时间
        if isinstance(event_row['start_time'], str):
            original_start_time = pd.to_datetime(event_row['start_time'])
        else:
            original_start_time = event_row['start_time']

        event_date = original_start_time.date()
        original_start_min = original_start_time.hour * 60 + original_start_time.minute

        # 对于TOU_D，根据事件的月份确定季节
        season = None
        if self.tariff_name == "TOU_D" and 'month' in event_row:
            month = int(event_row['month'])
            # 夏季：5-10月，冬季：11-4月
            season = "summer" if 5 <= month <= 10 else "winter"

        # 获取电器工作空间（考虑季节性）
        if house_id not in self.appliance_spaces:
            return {"status": "failed", "error": f"工作空间不存在: {house_id}"}

        # 对于TOU_D，使用季节性工作空间
        if season:
            seasonal_spaces = self.appliance_spaces[house_id].get(season, {})
            available_keys = list(seasonal_spaces.keys())

            # 使用智能映射查找电器
            cache_key = f"{house_id}_{season}_{appliance_name}"
            mapped_name = self.find_appliance_mapping(appliance_name, available_keys, cache_key)

            if mapped_name:
                appliance_space = seasonal_spaces[mapped_name]
                if mapped_name != appliance_name:
                    # 避免重复显示相同的映射信息
                    mapping_key = f"{appliance_name}→{mapped_name}({season})"
                    if mapping_key not in self.mapping_messages:
                        print(f"   🔄 季节性电器名称映射: {appliance_name} → {mapped_name} ({season})")
                        self.mapping_messages.add(mapping_key)
            else:
                return {"status": "failed", "error": f"季节性工作空间不存在: {appliance_name} ({season})"}
        else:
            available_keys = list(self.appliance_spaces[house_id].keys())

            # 使用智能映射查找电器
            cache_key = f"{house_id}_{appliance_name}"
            mapped_name = self.find_appliance_mapping(appliance_name, available_keys, cache_key)

            if mapped_name:
                appliance_space = self.appliance_spaces[house_id][mapped_name]
                if mapped_name != appliance_name:
                    # 避免重复显示相同的映射信息
                    mapping_key = f"{appliance_name}→{mapped_name}"
                    if mapping_key not in self.mapping_messages:
                        print(f"   🔄 电器名称映射: {appliance_name} → {mapped_name}")
                        self.mapping_messages.add(mapping_key)
            else:
                return {"status": "failed", "error": f"工作空间不存在: {appliance_name}"}

        # 获取价格等级区间 - 兼容新旧格式
        price_level_intervals = appliance_space.get('price_level_intervals', {})
        available_intervals = appliance_space.get('available_intervals', [])
        forbidden_intervals = appliance_space.get('forbidden_intervals', [])

        # 如果没有price_level_intervals，从available_intervals动态计算
        if not price_level_intervals and available_intervals:
            price_level_intervals = self.calculate_price_levels_for_intervals(
                available_intervals, house_id, event_date
            )

        # 🎯 简化的优化逻辑：考虑所有可用区间，优先选择更低价格等级
        all_candidate_intervals = []
        for level_str, intervals in price_level_intervals.items():
            level = int(level_str)
            for start_min, end_min in intervals:
                all_candidate_intervals.append((level, start_min, end_min))

        if not all_candidate_intervals:
            return {"status": "failed", "error": "没有可用的调度区间"}

        # 应用调度约束：事件只能在原始时间5分钟后开始调度
        earliest_allowed = original_start_min + 5

        # 🎯 简化的调度逻辑：寻找所有可行的调度方案，优先选择更低价格等级
        valid_intervals = []

        for level, start_min, end_min in all_candidate_intervals:
            # 🎯 新逻辑：只要能在低价区间开始即可，不要求整个事件都在区间内

            # 计算候选开始时间（考虑5分钟延迟约束）
            candidate_start = max(start_min, earliest_allowed)

            # 检查开始时间是否在当前区间内
            if candidate_start >= end_min:
                continue

            candidate_end = candidate_start + duration_min

            # 🎯 关键修改：只检查事件结束时间是否与禁止区间冲突
            # 不再要求整个事件都在可用区间内
            is_forbidden = False
            for forbidden_start, forbidden_end in forbidden_intervals:
                # 检查事件结束时间是否在禁止区间内
                if forbidden_start <= candidate_end <= forbidden_end:
                    is_forbidden = True
                    break
                # 或者检查事件是否跨越禁止区间
                if candidate_start < forbidden_start and candidate_end > forbidden_end:
                    is_forbidden = True
                    break

            if is_forbidden:
                continue

            # 这个区间可行，添加到候选列表
            valid_intervals.append((level, candidate_start, candidate_end))

        if not valid_intervals:
            return {"status": "failed", "error": "所有候选区间都不满足约束条件 (时长/禁止区间/5分钟延迟)"}

        # 选择最优区间：优先选择更低价格等级，其次选择时间最早的
        valid_intervals.sort(key=lambda x: (x[0], x[1]))  # 按价格等级和开始时间排序
        best_level, new_start_min, new_end_min = valid_intervals[0]

        # 计算优化分数：如果调度到更低价格等级，则有正分数
        if best_level < current_level:
            optimization_score = current_level - best_level
        else:
            # 即使没有调度到更低等级，只要能调度就给予小的正分数
            optimization_score = 0.1

        # 转换为实际日期时间
        new_start_datetime = self.minutes_to_datetime(new_start_min, event_date)
        new_end_datetime = self.minutes_to_datetime(new_end_min, event_date)

        result = {
            'status': 'success',
            'original_start_time': original_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'original_end_time': event_row['end_time'],
            'original_price_level': current_level,
            'new_start_time': new_start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'new_end_time': new_end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'new_price_level': best_level,
            'start_time_48h': self.minutes_to_time_48h(new_start_min),
            'end_time_48h': self.minutes_to_time_48h(new_end_min),
            'optimization_score': optimization_score,
            'shift_type': 'DELAY',
            'shift_minutes': new_start_min - original_start_min,
            'season': season  # 添加季节信息
        }

        return result

    def schedule_events_for_house(self, house_id: str, season: str = None) -> pd.DataFrame:
        """为指定用户调度事件"""
        print(f"\n🏠 Processing {house_id} - {self.tariff_name}")
        if season:
            print(f"   Season: {season}")

        # 加载电器工作空间
        if not self.load_appliance_spaces(house_id, season):
            return pd.DataFrame()

        # 加载可调度事件
        df_events = self.load_and_extract_reschedulable_events(house_id)
        if df_events.empty:
            print(f"   ⚠️ No reschedulable events")
            return pd.DataFrame()

        # 保存可调度事件
        self.save_reschedulable_events(df_events, house_id, season)

        # 调度优化
        results = []
        successful_count = 0

        # 统计失败原因
        failure_reasons = {}

        for idx, event_row in df_events.iterrows():
            schedule_result = self.find_optimal_schedule_for_event(event_row, house_id)

            if schedule_result and schedule_result.get('status') == 'success':
                # 成功调度
                result_row = {
                    'event_id': event_row.get('event_id', idx),
                    'appliance_name': event_row['appliance_name'],
                    'original_start_time': schedule_result['original_start_time'],
                    'original_end_time': schedule_result['original_end_time'],
                    'scheduled_start_time': schedule_result['new_start_time'],
                    'scheduled_end_time': schedule_result['new_end_time'],
                    'original_price_level': schedule_result['original_price_level'],
                    'scheduled_price_level': schedule_result['new_price_level'],
                    'optimization_score': schedule_result['optimization_score'],
                    'shift_minutes': schedule_result['shift_minutes'],
                    'schedule_status': 'SUCCESS',
                    'failure_reason': '',
                    'season': schedule_result.get('season', '')
                }
                successful_count += 1
            else:
                # 调度失败
                failure_reason = schedule_result.get('error', '未知原因') if schedule_result else '调度方法返回None'
                failure_reasons[failure_reason] = failure_reasons.get(failure_reason, 0) + 1

                result_row = {
                    'event_id': event_row.get('event_id', idx),
                    'appliance_name': event_row['appliance_name'],
                    'original_start_time': event_row['start_time'],
                    'original_end_time': event_row['end_time'],
                    'scheduled_start_time': event_row['start_time'],
                    'scheduled_end_time': event_row['end_time'],
                    'original_price_level': event_row['primary_price_level'],
                    'scheduled_price_level': event_row['primary_price_level'],
                    'optimization_score': 0,
                    'shift_minutes': 0,
                    'schedule_status': 'FAILED',
                    'failure_reason': failure_reason,
                    'season': ''
                }

            results.append(result_row)

        # 创建结果DataFrame
        df_result = pd.DataFrame(results)

        # 保存调度结果
        output_path = self.get_output_path(house_id, season)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_result.to_csv(output_path, index=False)

        # 统计信息
        failed_count = len(df_events) - successful_count
        success_rate = successful_count / len(df_events) * 100 if len(df_events) > 0 else 0
        print(f"   📊 Scheduling results: {successful_count}/{len(df_events)} successful ({success_rate:.1f}%)")

        # 显示失败原因统计
        if failure_reasons:
            print(f"   ❌ Failure reason statistics:")
            for reason, count in failure_reasons.items():
                print(f"     {reason}: {count} events")

        print(f"   📁 Results saved: {output_path}")

        # 返回统计信息（用于批处理）
        self.last_result = {
            "status": "success",
            "house_id": house_id,
            "tariff_name": self.tariff_name,
            "season": season,
            "total_events": len(df_events),
            "successful_events": successful_count,
            "failed_events": failed_count,
            "success_rate": success_rate,
            "failure_reasons": failure_reasons
        }

        return df_result

def get_available_houses() -> List[str]:
    """获取所有可用的house ID，按数字顺序排序"""
    houses = set()

    # 从约束文件目录获取
    constraints_dir = "output/04_user_constraints"
    if os.path.exists(constraints_dir):
        for item in os.listdir(constraints_dir):
            if os.path.isdir(os.path.join(constraints_dir, item)) and item.startswith("house"):
                houses.add(item)

    # 按数字顺序排序
    def extract_house_number(house_id):
        try:
            return int(house_id.replace('house', ''))
        except:
            return 999

    return sorted(list(houses), key=extract_house_number)

def process_single_house(tariff_name: str, house_id: str, season: str = None) -> Dict:
    """处理单个用户的事件调度"""
    scheduler = EventScheduler(tariff_name, house_id)

    try:
        df_result = scheduler.schedule_events_for_house(house_id, season)

        if df_result.empty:
            return {
                "status": "failed",
                "error": "没有可调度事件或处理失败",
                "house_id": house_id,
                "tariff_name": tariff_name
            }

        # 从scheduler获取详细统计信息
        if hasattr(scheduler, 'last_result'):
            result = scheduler.last_result.copy()
            result["result_data"] = df_result
            return result
        else:
            # 备用统计计算
            successful_count = len(df_result[df_result['schedule_status'] == 'SUCCESS'])
            total_count = len(df_result)

            return {
                "status": "success",
                "house_id": house_id,
                "tariff_name": tariff_name,
                "season": season,
                "total_events": total_count,
                "successful_events": successful_count,
                "failed_events": total_count - successful_count,
                "success_rate": successful_count / total_count * 100 if total_count > 0 else 0,
                "failure_reasons": {},
                "result_data": df_result
            }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "house_id": house_id,
            "tariff_name": tariff_name
        }

def process_batch_houses(tariff_name: str, house_list: List[str] = None) -> Dict:
    """批量处理多个用户的事件调度"""
    if house_list is None:
        house_list = get_available_houses()

    print(f"\n🚀 批量处理 {tariff_name} - {len(house_list)} 个用户")
    print("=" * 60)

    all_results = {}
    successful_houses = 0

    for house_id in house_list:
        if tariff_name == "TOU_D":
            # TOU_D处理统一的事件文件，但需要加载两个季节的工作空间
            print(f"\n� 处理 {house_id} - {tariff_name} (季节性调度)")
            result = process_single_house(tariff_name, house_id)
            all_results[house_id] = result

            if result["status"] == "success":
                successful_houses += 1
        else:
            # 其他电价方案
            result = process_single_house(tariff_name, house_id)
            all_results[house_id] = result

            if result["status"] == "success":
                successful_houses += 1

    # 显示详细统计表格
    print(f"\n📊 {tariff_name} 批处理统计表:")
    print("=" * 80)
    print(f"{'家庭编号':<10} {'可调度事件数':<12} {'成功调度数':<12} {'失败数':<8} {'成功率':<8}")
    print("-" * 80)

    total_reschedulable = 0
    total_successful = 0
    total_failed = 0

    # 按数字顺序排序显示
    def extract_house_number(house_id):
        try:
            return int(house_id.replace('house', ''))
        except:
            return 999

    for house_id in sorted(house_list, key=extract_house_number):
        result = all_results[house_id]
        if result["status"] == "success":
            reschedulable = result["total_events"]
            successful = result["successful_events"]
            failed = result["failed_events"]
            success_rate = result["success_rate"]

            total_reschedulable += reschedulable
            total_successful += successful
            total_failed += failed

            print(f"{house_id:<10} {reschedulable:<12} {successful:<12} {failed:<8} {success_rate:<7.1f}%")
        else:
            print(f"{house_id:<10} {'失败':<12} {'失败':<12} {'失败':<8} {'0.0%':<8}")

    print("-" * 80)
    overall_success_rate = total_successful / total_reschedulable * 100 if total_reschedulable > 0 else 0
    print(f"{'总计':<10} {total_reschedulable:<12} {total_successful:<12} {total_failed:<8} {overall_success_rate:<7.1f}%")
    print("=" * 80)

    return {
        "status": "success",
        "tariff_name": tariff_name,
        "total_houses": len(house_list),
        "successful_houses": int(successful_houses),
        "total_reschedulable_events": total_reschedulable,
        "total_successful_events": total_successful,
        "total_failed_events": total_failed,
        "overall_success_rate": overall_success_rate,
        "results": all_results
    }

def run_event_scheduler(mode: str = None, tariff_name: str = None, house_id: str = None):
    """运行事件调度器主函数"""
    print("🚀 Event Scheduler")
    print("=" * 120)

    # 交互式选择参数
    if not mode:
        print("\n📋 处理模式:")
        print("1. 单用户处理")
        print("2. 批量处理")

        try:
            mode_choice = input("选择模式 (1-2) [默认: 1]: ").strip()
            if not mode_choice:
                mode_choice = "1"
        except (EOFError, KeyboardInterrupt):
            mode_choice = "1"

        mode = "single" if mode_choice == "1" else "batch"

    if not tariff_name:
        print("\n📋 电价方案:")
        print("1. UK (Economy_7 + Economy_10)")
        print("2. TOU_D (California, 季节性)")
        print("3. Germany_Variable (Germany)")

        try:
            tariff_choice = input("选择电价方案 (1-3) [默认: 1]: ").strip()
            if not tariff_choice:
                tariff_choice = "1"
        except (EOFError, KeyboardInterrupt):
            tariff_choice = "1"

        tariff_mapping = {
            "1": ["Economy_7", "Economy_10"],
            "2": ["TOU_D"],
            "3": ["Germany_Variable"]
        }

        tariff_list = tariff_mapping.get(tariff_choice, ["Economy_7"])
    else:
        tariff_list = [tariff_name]

    # 执行调度
    all_results = {}

    for tariff in tariff_list:
        print(f"\n🔄 Processing tariff scheme: {tariff}")

        if mode == "single":
            if not house_id:
                available_houses = get_available_houses()
                print(f"可用用户: {', '.join(available_houses)}")
                house_id = input(f"输入用户ID [默认: {available_houses[0] if available_houses else 'house1'}]: ").strip()
                if not house_id:
                    house_id = available_houses[0] if available_houses else "house1"

            result = process_single_house(tariff, house_id)
            all_results[tariff] = {house_id: result}

        else:  # batch mode
            result = process_batch_houses(tariff)
            all_results[tariff] = result

    # 显示总结
    print(f"\n📊 Processing Summary:")
    print("=" * 120)

    for tariff, tariff_results in all_results.items():
        if mode == "single":
            for house, result in tariff_results.items():
                if result["status"] == "success":
                    print(f"✅ {tariff} - {house}: {result['successful_events']}/{result['total_events']} successful")
                else:
                    print(f"❌ {tariff} - {house}: failed - {result.get('error', 'unknown error')}")
        else:
            if tariff_results["status"] == "success":
                print(f"✅ {tariff}: {tariff_results['successful_houses']}/{tariff_results['total_houses']} households successful")
            else:
                print(f"❌ {tariff}: batch processing failed")

    return all_results

if __name__ == "__main__":
    # 交互式运行
    run_event_scheduler()
