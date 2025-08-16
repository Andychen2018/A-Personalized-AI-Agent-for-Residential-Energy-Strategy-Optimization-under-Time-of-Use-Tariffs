#!/usr/bin/env python3
"""
时间不确定性鲁棒性实验 - Collision Resolver
专用冲突修复模块，处理同一电器同一日多次迁移事件之间的时间重叠冲突问题

📌 功能说明:
- 批量处理多个房屋的调度结果
- 解决同一电器同一日多次事件的时间重叠冲突
- 保留_01事件，重新调度_02, _03等后续事件
- 优先选择价格较低的时间段

📁 输入路径: experiments/Robustness/02Timing_Uncertainties/output/05_Initial_scheduling_optimization/{tariff_name}/house*/
📁 输出路径: experiments/Robustness/02Timing_Uncertainties/output/05_Collision_Resolved_Scheduling/{tariff_name}/house*/

适配时间不确定性扰动实验
版本: 2.1 - 时间不确定性实验版本
"""

import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import glob

class P052CollisionResolver:
    """时间不确定性实验的冲突解决器 - 批量处理多个房屋"""

    def __init__(self, input_dir: str = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties/output/05_Initial_scheduling_optimization",
                 output_dir: str = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties/output/05_Collision_Resolved_Scheduling"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.tariff_configs = {}
        self.appliance_spaces = {}

        # 时间不确定性实验配置
        self.base_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties"
        self.constraint_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/03Constraint_Parsing_Errors/Original_data/UK"

        print(f"🔧 P052冲突解决器初始化 - 鲁棒性实验模式")
        print(f"   📂 输入目录: {input_dir}")
        print(f"   📂 输出目录: {output_dir}")

    def parse_event_id(self, event_id: str) -> Tuple[str, str, str]:
        """
        解析事件ID，提取电器名称、日期和序号

        Args:
            event_id: 如 "Tumble_Dryer_2013-10-24_02"

        Returns:
            (appliance_base, date_str, sequence_num)
            如 ("Tumble_Dryer", "2013-10-24", "02")
        """
        # 匹配模式: ApplianceName_YYYY-MM-DD_NN
        pattern = r'^(.+)_(\d{4}-\d{2}-\d{2})_(\d+)$'
        match = re.match(pattern, event_id)

        if match:
            appliance_base = match.group(1)
            date_str = match.group(2)
            sequence_num = match.group(3)
            return appliance_base, date_str, sequence_num
        else:
            # 如果不匹配，返回原始值
            return event_id, "", "01"

    def load_tariff_config(self, tariff_name: str) -> dict:
        """加载电价配置"""
        if tariff_name in self.tariff_configs:
            return self.tariff_configs[tariff_name]

        # 首先尝试从统一配置文件加载
        unified_config_paths = [
            "./config/tariff_config.json",
            "../config/tariff_config.json",
            "./Agent_V2/config/tariff_config.json"
        ]

        for path in unified_config_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    all_configs = json.load(f)
                    if tariff_name in all_configs:
                        config = {tariff_name: all_configs[tariff_name]}
                        self.tariff_configs[tariff_name] = config
                        return config

        # 如果统一配置文件中没有，尝试单独的配置文件
        individual_config_paths = [
            f"./config/{tariff_name}.json",
            f"../config/{tariff_name}.json",
            f"./Agent_V2/config/{tariff_name}.json"
        ]

        for path in individual_config_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.tariff_configs[tariff_name] = config
                    return config

        raise FileNotFoundError(f"Cannot find config file for {tariff_name}")

    def load_appliance_spaces(self, tariff_name: str):
        """加载电器约束空间 - 使用错误约束文件"""
        if tariff_name in self.appliance_spaces:
            return

        # 🎯 构建错误约束文件路径
        error_constraints_base = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/03Constraint_Parsing_Errors/Error_data/UK"

        if tariff_name in ["Economy_7", "Economy_10"]:
            spaces_dir = os.path.join(error_constraints_base, tariff_name)
        else:
            # 对于其他电价方案，使用原始路径（如果需要的话）
            spaces_dir = os.path.join("./output/05_appliance_working_spaces", tariff_name)

        self.appliance_spaces[tariff_name] = {}

        # 查找约束空间文件
        if os.path.exists(spaces_dir):
            # 对于TOU_D，需要查找summer/winter子目录
            if tariff_name == "TOU_D":
                for season_dir in ["summer", "winter"]:
                    season_path = os.path.join(spaces_dir, season_dir)
                    if os.path.exists(season_path):
                        for house_dir in os.listdir(season_path):
                            house_path = os.path.join(season_path, house_dir)
                            if os.path.isdir(house_path):
                                spaces_file = os.path.join(house_path, "appliance_reschedulable_spaces.json")
                                if os.path.exists(spaces_file):
                                    try:
                                        with open(spaces_file, 'r', encoding='utf-8') as f:
                                            spaces_data = json.load(f)
                                            # 使用第一个找到的数据作为通用约束
                                            if not self.appliance_spaces[tariff_name]:
                                                self.appliance_spaces[tariff_name] = spaces_data
                                            return
                                    except Exception as e:
                                        print(f"⚠️ 加载约束空间失败 {spaces_file}: {e}")
            else:
                # 对于其他电价方案，直接查找house目录
                for house_dir in os.listdir(spaces_dir):
                    house_path = os.path.join(spaces_dir, house_dir)
                    if os.path.isdir(house_path):
                        spaces_file = os.path.join(house_path, "appliance_reschedulable_spaces.json")
                        if os.path.exists(spaces_file):
                            try:
                                with open(spaces_file, 'r', encoding='utf-8') as f:
                                    spaces_data = json.load(f)
                                    # 使用第一个house的数据作为通用约束
                                    if not self.appliance_spaces[tariff_name]:
                                        self.appliance_spaces[tariff_name] = spaces_data
                                    return
                            except Exception as e:
                                print(f"⚠️ 加载约束空间失败 {spaces_file}: {e}")

    def get_time_price_level(self, timestamp: datetime, tariff_config: dict, tariff_name: str) -> int:
        """获取指定时间点的价格等级"""
        config_key = list(tariff_config.keys())[0] if len(tariff_config) == 1 else tariff_name
        tariff_plan = tariff_config[config_key]

        if tariff_plan.get("type") == "flat":
            return 0

        # 获取时间段
        periods = []
        if tariff_plan.get("type") == "time_based":
            periods = tariff_plan.get("periods", [])
        elif tariff_plan.get("type") == "seasonal_time_based":
            # 根据月份选择季节
            month = timestamp.month
            if "summer" in tariff_plan and month in tariff_plan["summer"]["months"]:
                periods = tariff_plan["summer"]["periods"]
            elif "winter" in tariff_plan and month in tariff_plan["winter"]["months"]:
                periods = tariff_plan["winter"]["periods"]

        if not periods:
            return 0

        # 按价格排序获取等级
        unique_rates = sorted(set(period["rate"] for period in periods))
        rate_to_level = {rate: idx for idx, rate in enumerate(unique_rates)}

        # 查找当前时间对应的价格等级
        time_minutes = timestamp.hour * 60 + timestamp.minute

        for period in periods:
            start_minutes = int(period["start"].split(":")[0]) * 60 + int(period["start"].split(":")[1])
            end_minutes = int(period["end"].split(":")[0]) * 60 + int(period["end"].split(":")[1])

            # 处理跨天的时间段
            if end_minutes <= start_minutes:
                if time_minutes < end_minutes or time_minutes >= start_minutes:
                    return rate_to_level[period["rate"]]
            else:
                if start_minutes <= time_minutes < end_minutes:
                    return rate_to_level[period["rate"]]

        return 0

    def detect_collisions_in_group(self, group_df: pd.DataFrame) -> List[Tuple[int, int]]:
        """检测同一电器同一日事件组内的冲突"""
        collisions = []

        if len(group_df) <= 1:
            return collisions

        # 按调度后的开始时间排序
        sorted_events = group_df.sort_values('NewStartTime').reset_index()

        # 检测时间重叠
        for i in range(len(sorted_events) - 1):
            current_event = sorted_events.iloc[i]
            next_event = sorted_events.iloc[i + 1]

            current_end = pd.to_datetime(current_event['NewEndTime'])
            next_start = pd.to_datetime(next_event['NewStartTime'])

            # 如果下一个事件在当前事件结束前开始，则存在碰撞
            if next_start < current_end:
                collisions.append((current_event['index'], next_event['index']))

        return collisions

    def create_event_specific_constraints(
        self,
        appliance_name: str,
        original_start_datetime: datetime,
        original_price_level: int,
        occupied_slots: List[Tuple[datetime, datetime]],
        tariff_name: str
    ) -> Dict:
        """
        为特定事件创建个性化的约束空间

        Args:
            appliance_name: 电器名称
            original_start_datetime: 原始开始时间
            original_price_level: 原始价格等级
            occupied_slots: 已占用的时间段列表
            tariff_name: 电价方案名称

        Returns:
            更新后的约束空间字典
        """
        # 加载电器基础约束空间
        if tariff_name not in self.appliance_spaces:
            self.load_appliance_spaces(tariff_name)

        appliance_space = self.appliance_spaces[tariff_name].get(appliance_name)
        if not appliance_space:
            return {}

        # 深拷贝基础约束空间
        import copy
        event_constraints = copy.deepcopy(appliance_space)

        # 计算原始开始时间的分钟数（从当天00:00开始）
        original_start_min = original_start_datetime.hour * 60 + original_start_datetime.minute
        earliest_allowed = original_start_min + 5  # 只能向后调度（原始时间+5分钟后）

        # 1. 添加自身时间约束：原始时间+5分钟之前不可用
        self_forbidden_interval = [0, earliest_allowed]

        # 2. 将占用时间段转换为分钟数并添加到禁止区间
        occupied_intervals_min = []
        for start_dt, end_dt in occupied_slots:
            start_min = self.datetime_to_minutes_from_base(start_dt, original_start_datetime.date())
            end_min = self.datetime_to_minutes_from_base(end_dt, original_start_datetime.date())
            occupied_intervals_min.append([start_min, end_min])

        # 3. 更新禁止区间
        updated_forbidden = event_constraints['forbidden_intervals'].copy()
        updated_forbidden.append(self_forbidden_interval)
        updated_forbidden.extend(occupied_intervals_min)

        # 4. 重新计算可用区间
        updated_available = self.calculate_available_intervals(
            updated_forbidden, event_constraints['latest_finish_minutes']
        )

        # 5. 重新计算价格等级区间（只保留比原始等级更优或相等的等级）
        updated_price_intervals = {}
        base_price_intervals = event_constraints['price_level_intervals']

        for level_str, intervals in base_price_intervals.items():
            level = int(level_str)
            if level <= original_price_level:  # 只考虑更优或相等的价格等级
                updated_intervals = []
                for start_min, end_min in intervals:
                    # 检查这个价格区间与可用区间的交集
                    intersections = self.find_interval_intersections(
                        [[start_min, end_min]], updated_available
                    )
                    updated_intervals.extend(intersections)

                if updated_intervals:
                    updated_price_intervals[level_str] = updated_intervals

        # 6. 更新约束空间
        event_constraints['forbidden_intervals'] = updated_forbidden
        event_constraints['available_intervals'] = updated_available
        event_constraints['price_level_intervals'] = updated_price_intervals

        return event_constraints

    def find_available_time_slot_with_constraints(
        self,
        appliance_name: str,
        event_duration_minutes: int,
        original_start_datetime: datetime,
        original_price_level: int,
        occupied_slots: List[Tuple[datetime, datetime]],
        tariff_name: str
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        使用事件特定的约束空间寻找可用时间段

        Args:
            appliance_name: 电器名称
            event_duration_minutes: 事件持续时间（分钟）
            original_start_datetime: 原始开始时间
            original_price_level: 原始价格等级
            occupied_slots: 已占用的时间段列表
            tariff_name: 电价方案名称

        Returns:
            (start_time, end_time) 或 None
        """
        # 创建事件特定的约束空间
        event_constraints = self.create_event_specific_constraints(
            appliance_name, original_start_datetime, original_price_level,
            occupied_slots, tariff_name
        )

        if not event_constraints or not event_constraints.get('price_level_intervals'):
            return None

        # 收集所有候选区间
        candidate_intervals = []
        for level_str, intervals in event_constraints['price_level_intervals'].items():
            level = int(level_str)
            for start_min, end_min in intervals:
                # 检查区间是否足够容纳事件
                if end_min - start_min >= event_duration_minutes:
                    candidate_intervals.append((level, start_min, end_min))

        if not candidate_intervals:
            return None

        # 选择最优区间（价格等级最低，时间最早）
        candidate_intervals.sort(key=lambda x: (x[0], x[1]))
        _, best_start_min, _ = candidate_intervals[0]

        # 转换回datetime
        new_start_datetime = self.minutes_to_datetime_from_base(best_start_min, original_start_datetime.date())
        new_end_datetime = new_start_datetime + timedelta(minutes=event_duration_minutes)

        return (new_start_datetime, new_end_datetime)

    def datetime_to_minutes_from_base(self, dt: datetime, base_date) -> int:
        """将datetime转换为相对于基准日期的分钟数"""
        days_diff = (dt.date() - base_date).days
        return days_diff * 1440 + dt.hour * 60 + dt.minute

    def minutes_to_datetime_from_base(self, minutes: int, base_date) -> datetime:
        """将相对于基准日期的分钟数转换为datetime"""
        days = minutes // 1440
        remaining_minutes = minutes % 1440
        hours = remaining_minutes // 60
        mins = remaining_minutes % 60

        new_date = base_date + timedelta(days=days)
        return datetime.combine(new_date, datetime.min.time()) + timedelta(hours=hours, minutes=mins)

    def find_available_segments(self, start_min: int, end_min: int, duration_min: int,
                              occupied_intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """在给定区间内找到未被占用的可用片段"""
        available_segments = []
        current_start = start_min

        # 按开始时间排序占用区间
        occupied_intervals = sorted(occupied_intervals)

        for occupied_start, occupied_end in occupied_intervals:
            # 如果占用区间在当前搜索区间之前，跳过
            if occupied_end <= current_start:
                continue
            # 如果占用区间在当前搜索区间之后，添加剩余区间并结束
            if occupied_start >= end_min:
                break

            # 如果当前位置到占用区间开始有足够空间
            if occupied_start > current_start and occupied_start - current_start >= duration_min:
                available_segments.append((current_start, occupied_start))

            # 更新当前位置到占用区间结束后
            current_start = max(current_start, occupied_end)

        # 检查最后一个片段
        if current_start < end_min and end_min - current_start >= duration_min:
            available_segments.append((current_start, end_min))

        return available_segments

    def calculate_available_intervals(self, forbidden_intervals: List[List[int]], max_minutes: int) -> List[List[int]]:
        """根据禁止区间计算可用区间"""
        if not forbidden_intervals:
            return [[0, max_minutes]]

        # 合并重叠的禁止区间
        merged_forbidden = self.merge_intervals(forbidden_intervals)

        # 计算可用区间
        available_intervals = []
        current_start = 0

        for forbidden_start, forbidden_end in merged_forbidden:
            # 如果当前位置在禁止区间之前，添加可用区间
            if current_start < forbidden_start:
                available_intervals.append([current_start, forbidden_start])

            # 更新当前位置到禁止区间结束后
            current_start = max(current_start, forbidden_end)

        # 添加最后一个可用区间
        if current_start < max_minutes:
            available_intervals.append([current_start, max_minutes])

        return available_intervals

    def merge_intervals(self, intervals: List[List[int]]) -> List[List[int]]:
        """合并重叠的区间"""
        if not intervals:
            return []

        # 按开始时间排序
        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_intervals[0]]

        for current in sorted_intervals[1:]:
            last = merged[-1]

            # 如果当前区间与上一个区间重叠或相邻，合并它们
            if current[0] <= last[1]:
                merged[-1] = [last[0], max(last[1], current[1])]
            else:
                merged.append(current)

        return merged

    def find_interval_intersections(self, intervals1: List[List[int]], intervals2: List[List[int]]) -> List[List[int]]:
        """找到两组区间的交集"""
        intersections = []

        for start1, end1 in intervals1:
            for start2, end2 in intervals2:
                # 计算交集
                intersection_start = max(start1, start2)
                intersection_end = min(end1, end2)

                # 如果有有效交集，添加到结果中
                if intersection_start < intersection_end:
                    intersections.append([intersection_start, intersection_end])

        # 合并重叠的交集区间
        return self.merge_intervals(intersections)

    def resolve_collisions_for_house(
        self,
        input_file: str,
        output_file: str,
        tariff_name: str
    ) -> Dict[str, int]:
        """
        解决单个房屋的调度冲突

        Returns:
            统计信息字典
        """
        print(f"  🔧 Processing: {os.path.basename(input_file)}")

        # 读取调度结果
        df_all = pd.read_csv(input_file)

        # 保持原始列名，只转换时间列
        df_all['original_start_time'] = pd.to_datetime(df_all['original_start_time'])
        df_all['original_end_time'] = pd.to_datetime(df_all['original_end_time'])
        df_all['scheduled_start_time'] = pd.to_datetime(df_all['scheduled_start_time'])
        df_all['scheduled_end_time'] = pd.to_datetime(df_all['scheduled_end_time'])

        # 分离SUCCESS和FAILED事件
        df_success = df_all[df_all['schedule_status'] == 'SUCCESS'].copy()
        df_failed = df_all[df_all['schedule_status'] == 'FAILED'].copy()

        # 添加解析字段到SUCCESS事件
        df_success[['ApplianceBase', 'EventDate', 'SequenceNum']] = df_success['event_id'].apply(
            lambda x: pd.Series(self.parse_event_id(x))
        )

        # 计算统计数据
        total_events = len(df_all)
        original_optimized_events = len(df_success)  # p052成功优化的事件数

        stats = {
            'total_events': total_events,
            'original_optimized_events': original_optimized_events,
            'conflicts_detected': 0,  # 将在处理过程中计算
            'conflicts_resolved': 0,
            'resolution_failed': 0,
            'final_optimized_events': 0  # 将在最后计算
        }

        # 按电器和日期分组处理SUCCESS事件
        groups = df_success.groupby(['ApplianceBase', 'EventDate'])

        processed_groups = 0
        for _, group in groups:
            if len(group) <= 1:
                continue  # 单个事件无冲突

            processed_groups += 1

            # 按序号排序
            group = group.sort_values('SequenceNum')
            group_indices = group.index.tolist()

            # 分离_01事件和非_01事件
            primary_events = []  # _01事件
            secondary_events = []  # _02, _03等事件

            for idx in group_indices:
                seq_num = df_success.loc[idx, 'SequenceNum']
                if seq_num == '01':
                    primary_events.append(idx)
                else:
                    secondary_events.append(idx)

            if not secondary_events:
                continue  # 没有需要处理的非_01事件

            # 统计冲突检测数量（非_01事件）
            stats['conflicts_detected'] += len(secondary_events)

            # 收集_01事件占用的时间段
            occupied_slots = []
            for idx in primary_events:
                start_time = df_success.loc[idx, 'scheduled_start_time']
                end_time = df_success.loc[idx, 'scheduled_end_time']
                occupied_slots.append((start_time, end_time))

            # 重新调度非_01事件
            for idx in secondary_events:
                original_start = df_success.loc[idx, 'original_start_time']
                original_end = df_success.loc[idx, 'original_end_time']
                event_duration = int((original_end - original_start).total_seconds() / 60)

                # 使用约束空间寻找可用时间段
                appliance_name = df_success.loc[idx, 'appliance_name']
                original_price_level = int(df_success.loc[idx, 'original_price_level'])
                new_slot = self.find_available_time_slot_with_constraints(
                    appliance_name,
                    event_duration,
                    original_start,
                    original_price_level,
                    occupied_slots,
                    tariff_name
                )

                if new_slot:
                    # 成功找到新时间段
                    new_start, new_end = new_slot
                    df_success.loc[idx, 'scheduled_start_time'] = new_start
                    df_success.loc[idx, 'scheduled_end_time'] = new_end

                    occupied_slots.append((new_start, new_end))
                    stats['conflicts_resolved'] += 1
                else:
                    # 无法找到合适时间段，标记为失败
                    df_success.loc[idx, 'schedule_status'] = 'FAILED'
                    df_success.loc[idx, 'failure_reason'] = 'No available time slot after collision resolution'
                    stats['resolution_failed'] += 1

        if processed_groups > 0:
            print(f"    🔧 Processed {processed_groups} groups with conflicts")

        # 重新合并所有事件，保持原始列结构
        final_success_events = df_success[df_success['schedule_status'] == 'SUCCESS'].copy()
        final_failed_events_from_success = df_success[df_success['schedule_status'] == 'FAILED'].copy()

        # 合并所有事件，只保留原始列
        df_final = pd.concat([final_success_events, final_failed_events_from_success, df_failed], ignore_index=True)

        # 只保留原始输入文件的列，移除临时添加的列
        original_columns = ['event_id', 'appliance_name', 'original_start_time', 'original_end_time',
                          'scheduled_start_time', 'scheduled_end_time', 'original_price_level',
                          'scheduled_price_level', 'optimization_score', 'shift_minutes',
                          'schedule_status', 'failure_reason', 'season']

        # 只保留存在的列
        columns_to_keep = [col for col in original_columns if col in df_final.columns]
        df_final = df_final[columns_to_keep]

        # 计算最终优化事件数量（原始优化事件数 - 冲突解决失败的事件数）
        stats['final_optimized_events'] = stats['original_optimized_events'] - stats['resolution_failed']

        # 保存结果
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df_final.to_csv(output_file, index=False)

        print(f"    📊 Events: {stats['total_events']} | Conflicts: {stats['conflicts_detected']} | Resolved: {stats['conflicts_resolved']} | Failed: {stats['resolution_failed']}")

        return stats

    def generate_house_summary_table(self, house_results: Dict[str, Dict]) -> str:
        """生成单个电价方案下各房屋的统计表格"""
        if not house_results:
            return "No data available"

        # 表格标题
        table = "\n📋 House-by-House Summary Table:\n"
        table += "=" * 120 + "\n"
        table += f"{'House':<8} {'Total':<7} {'Original':<9} {'Conflicts':<9} {'Resolved':<9} {'Failed':<7} {'Final':<7} {'Orig%':<6} {'Final%':<7} {'Status':<8}\n"
        table += f"{'ID':<8} {'Events':<7} {'Optimized':<9} {'Detected':<9} {'Success':<9} {'Count':<7} {'Optimized':<7} {'Rate':<6} {'Rate':<7} {'':<8}\n"
        table += "-" * 120 + "\n"

        # 统计数据
        total_stats = {
            'total_events': 0,
            'original_optimized_events': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'resolution_failed': 0,
            'final_optimized_events': 0
        }

        successful_houses = 0

        # 按房屋ID升序排序（数字排序，不是字符串排序）
        def extract_house_number(house_id):
            """从house_id中提取数字进行排序"""
            try:
                # 提取house后面的数字，如house1 -> 1, house10 -> 10
                return int(house_id.replace('house', ''))
            except:
                # 如果提取失败，使用字符串排序
                return float('inf')

        sorted_houses = sorted(house_results.items(), key=lambda x: extract_house_number(x[0]))

        for house_id, result in sorted_houses:
            if result.get('status') == 'success' and 'stats' in result:
                stats = result['stats']
                successful_houses += 1

                # 累计总统计
                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

                # 计算百分比
                orig_rate = (stats['original_optimized_events'] / stats['total_events'] * 100) if stats['total_events'] > 0 else 0
                final_rate = (stats['final_optimized_events'] / stats['total_events'] * 100) if stats['total_events'] > 0 else 0

                # 添加行
                table += f"{house_id:<8} {stats['total_events']:<7} {stats['original_optimized_events']:<9} "
                table += f"{stats['conflicts_detected']:<9} {stats['conflicts_resolved']:<9} {stats['resolution_failed']:<7} "
                table += f"{stats['final_optimized_events']:<7} {orig_rate:<6.1f} {final_rate:<7.1f} {'✅':<8}\n"
            else:
                # 失败的房屋
                table += f"{house_id:<8} {'N/A':<7} {'N/A':<9} {'N/A':<9} {'N/A':<9} {'N/A':<7} {'N/A':<7} {'N/A':<6} {'N/A':<7} {'❌':<8}\n"

        # 总计行
        table += "-" * 120 + "\n"
        if total_stats['total_events'] > 0:
            total_orig_rate = total_stats['original_optimized_events'] / total_stats['total_events'] * 100
            total_final_rate = total_stats['final_optimized_events'] / total_stats['total_events'] * 100
            conflict_resolution_rate = (total_stats['conflicts_resolved'] / total_stats['conflicts_detected'] * 100) if total_stats['conflicts_detected'] > 0 else 0

            table += f"{'TOTAL':<8} {total_stats['total_events']:<7} {total_stats['original_optimized_events']:<9} "
            table += f"{total_stats['conflicts_detected']:<9} {total_stats['conflicts_resolved']:<9} {total_stats['resolution_failed']:<7} "
            table += f"{total_stats['final_optimized_events']:<7} {total_orig_rate:<6.1f} {total_final_rate:<7.1f} {f'{successful_houses}/{len(house_results)}':<8}\n"

            table += "\n📊 Summary Statistics:\n"
            table += f"  • Houses processed: {len(house_results)} (✅{successful_houses} ❌{len(house_results)-successful_houses})\n"
            table += f"  • Conflict resolution rate: {conflict_resolution_rate:.1f}%\n"
            table += f"  • Optimization improvement: {total_final_rate-total_orig_rate:+.1f}%\n"

        return table

    def process_tariff_batch(self, tariff_name: str) -> Dict[str, Dict]:
        """批量处理指定电价方案下所有房屋的冲突解决"""
        print(f"\n🔄 Processing collision resolution for tariff: {tariff_name}")
        print("=" * 60)



        # 查找输入文件 - 支持所有电价方案的目录结构
        input_patterns = [
            os.path.join(self.input_dir, tariff_name, "house*", "scheduled_events.csv"),  # 直接路径 (TOU_D, Germany_Variable)
            os.path.join(self.input_dir, "UK", tariff_name, "house*", "scheduled_events.csv"),  # UK嵌套路径 (Economy_7, Economy_10)
            os.path.join(self.input_dir, "*", tariff_name, "house*", "scheduled_events.csv")  # 通用嵌套路径
        ]

        input_files = []
        for pattern in input_patterns:
            files = glob.glob(pattern)
            if files:
                input_files = files
                print(f"📁 Using pattern: {pattern}")
                break

        if not input_files:
            print(f"❌ No input files found for any of these patterns:")
            for pattern in input_patterns:
                print(f"   - {pattern}")
            return {}

        print(f"📁 Found {len(input_files)} house files to process")

        results = {}
        total_stats = {
            'total_events': 0,
            'original_optimized_events': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'resolution_failed': 0,
            'final_optimized_events': 0
        }

        # 处理每个房屋
        for i, input_file in enumerate(sorted(input_files), 1):
            house_id = os.path.basename(os.path.dirname(input_file))
            print(f"[{i}/{len(input_files)}] {house_id}...", end=" ")

            # 构建输出路径，保持与输入路径相同的结构
            input_relative_path = os.path.relpath(input_file, self.input_dir)
            output_file = os.path.join(self.output_dir, input_relative_path)

            try:
                house_stats = self.resolve_collisions_for_house(
                    input_file, output_file, tariff_name
                )

                results[house_id] = {
                    'status': 'success',
                    'stats': house_stats,
                    'input_file': input_file,
                    'output_file': output_file
                }

                # 累计统计
                for key in total_stats:
                    total_stats[key] += house_stats[key]

                print("✅")

            except Exception as e:
                print(f"❌ {str(e)[:30]}...")
                results[house_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'input_file': input_file,
                    'output_file': output_file
                }

        # 输出总体统计
        successful_houses = len([r for r in results.values() if r['status'] == 'success'])
        failed_houses = len([r for r in results.values() if r['status'] == 'failed'])

        print(f"\n📊 Batch collision resolution summary for {tariff_name}:")
        print(f"  🏠 Houses processed:")
        print(f"    • Successfully processed: {successful_houses} houses")
        print(f"    • Failed: {failed_houses} houses")
        print(f"  📈 Event statistics:")
        print(f"    • Total events: {total_stats['total_events']:,}")
        print(f"    • Original optimized events (p052): {total_stats['original_optimized_events']:,}")
        print(f"    • Conflicts detected: {total_stats['conflicts_detected']:,}")
        print(f"    • Conflicts resolved: {total_stats['conflicts_resolved']:,}")
        print(f"    • Resolution failed: {total_stats['resolution_failed']:,}")
        print(f"    • Final optimized events: {total_stats['final_optimized_events']:,}")

        # 计算成功率
        if total_stats['conflicts_detected'] > 0:
            resolution_rate = total_stats['conflicts_resolved'] / total_stats['conflicts_detected'] * 100
            print(f"  ✅ Conflict resolution success rate: {resolution_rate:.1f}%")

        if total_stats['total_events'] > 0:
            original_optimization_rate = total_stats['original_optimized_events'] / total_stats['total_events'] * 100
            final_optimization_rate = total_stats['final_optimized_events'] / total_stats['total_events'] * 100
            print(f"  🎯 Original optimization rate: {original_optimization_rate:.1f}%")
            print(f"  🎯 Final optimization rate: {final_optimization_rate:.1f}%")

        # 生成并显示详细表格
        summary_table = self.generate_house_summary_table(results)
        print(summary_table)

        return results

    def process_single_house(self, tariff_name: str, house_id: str) -> Dict[str, any]:
        """
        处理单个房屋的冲突解决

        Args:
            tariff_name: 电价方案名称
            house_id: 房屋ID

        Returns:
            处理结果字典
        """
        print(f"🏠 Processing single house: {house_id} with tariff {tariff_name}")
        print("=" * 60)



        # 查找输入文件
        input_patterns = [
            os.path.join(self.input_dir, tariff_name, house_id, "scheduled_events.csv"),
            os.path.join(self.input_dir, "UK", tariff_name, house_id, "scheduled_events.csv"),
            os.path.join(self.input_dir, "*", tariff_name, house_id, "scheduled_events.csv")
        ]

        input_file = None
        for pattern in input_patterns:
            files = glob.glob(pattern)
            if files:
                input_file = files[0]
                print(f"📁 Found input file: {input_file}")
                break

        if not input_file:
            error_msg = f"No input file found for {tariff_name}/{house_id}"
            print(f"❌ {error_msg}")
            return {'status': 'failed', 'error': error_msg}

        # 构建输出路径
        input_relative_path = os.path.relpath(input_file, self.input_dir)
        output_file = os.path.join(self.output_dir, input_relative_path)

        try:
            # 处理冲突
            house_stats = self.resolve_collisions_for_house(
                input_file, output_file, tariff_name
            )

            result = {
                'status': 'success',
                'stats': house_stats,
                'input_file': input_file,
                'output_file': output_file
            }

            # 生成单个房屋的表格
            house_results = {house_id: result}
            summary_table = self.generate_house_summary_table(house_results)
            print(summary_table)

            print(f"✅ {house_id} processing completed successfully")
            return result

        except Exception as e:
            error_msg = f"Error processing {house_id}: {str(e)}"
            print(f"❌ {error_msg}")
            return {'status': 'failed', 'error': error_msg}


def run_collision_resolution(mode: str = "default", single_tariff: str = None):
    """
    运行冲突解决器的主函数

    Args:
        mode: 运行模式
            - "default": 默认模式 (UK下的Economy_7, Economy_10)
            - "test": 测试模式 (TOU_D, Germany_Variable)
            - "all": 所有电价方案
            - "single": 单个电价方案 (需要指定single_tariff)
        single_tariff: 当mode="single"时指定的电价方案名称
    """
    print("🚀 Starting P053 Collision Resolution...")
    print("=" * 80)

    resolver = P052CollisionResolver()

    # 根据模式选择电价方案
    if mode == "test":
        tariff_schemes = ["TOU_D", "Germany_Variable"]
        print("🧪 Test mode: Processing TOU_D and Germany_Variable")
    elif mode == "all":
        tariff_schemes = ["Economy_7", "Economy_10", "TOU_D", "Germany_Variable"]
        print("🌍 All mode: Processing all tariff schemes")
    elif mode == "single" and single_tariff:
        tariff_schemes = [single_tariff]
        print(f"🎯 Single mode: Processing {single_tariff}")
    else:
        # 默认模式：UK下的Economy_7和Economy_10
        tariff_schemes = ["Economy_7", "Economy_10"]
        print("🏠 Default mode: Processing UK Economy_7 and Economy_10")

    all_results = {}

    for i, tariff_name in enumerate(tariff_schemes, 1):
        print(f"\n{'='*20} [{i}/{len(tariff_schemes)}] {tariff_name} {'='*20}")

        try:
            tariff_results = resolver.process_tariff_batch(tariff_name)
            all_results[tariff_name] = tariff_results
            print(f"✅ {tariff_name} processing completed")

        except Exception as e:
            print(f"❌ Error processing tariff {tariff_name}: {str(e)}")
            all_results[tariff_name] = {'error': str(e)}

    # 生成总体报告
    print(f"\n🎉 P053 Collision Resolution completed!")
    print("=" * 80)

    total_houses = 0
    total_success = 0
    total_failed = 0
    grand_total_stats = {
        'total_events': 0,
        'original_optimized_events': 0,
        'conflicts_detected': 0,
        'conflicts_resolved': 0,
        'resolution_failed': 0,
        'final_optimized_events': 0
    }

    for tariff_name, results in all_results.items():
        if 'error' not in results:
            houses = len(results)
            success = len([r for r in results.values() if r.get('status') == 'success'])
            failed = len([r for r in results.values() if r.get('status') == 'failed'])

            total_houses += houses
            total_success += success
            total_failed += failed

            # 累计各电价方案的统计数据
            for _, house_result in results.items():
                if house_result.get('status') == 'success' and 'stats' in house_result:
                    house_stats = house_result['stats']
                    for key in grand_total_stats:
                        grand_total_stats[key] += house_stats.get(key, 0)

            print(f"📊 {tariff_name}: {success}/{houses} houses successful")

    print(f"\n📈 Overall Summary:")
    print(f"  🏠 Houses:")
    print(f"    • Total houses processed: {total_houses}")
    print(f"    • Successfully processed: {total_success}")
    print(f"    • Failed: {total_failed}")

    if total_houses > 0:
        success_rate = total_success / total_houses * 100
        print(f"    • House success rate: {success_rate:.1f}%")

    print(f"  📈 Events across all tariffs:")
    print(f"    • Total events: {grand_total_stats['total_events']:,}")
    print(f"    • Original optimized events (p052): {grand_total_stats['original_optimized_events']:,}")
    print(f"    • Conflicts detected: {grand_total_stats['conflicts_detected']:,}")
    print(f"    • Conflicts resolved: {grand_total_stats['conflicts_resolved']:,}")
    print(f"    • Resolution failed: {grand_total_stats['resolution_failed']:,}")
    print(f"    • Final optimized events: {grand_total_stats['final_optimized_events']:,}")

    # 计算总体成功率
    if grand_total_stats['conflicts_detected'] > 0:
        resolution_rate = grand_total_stats['conflicts_resolved'] / grand_total_stats['conflicts_detected'] * 100
        print(f"  ✅ Overall conflict resolution rate: {resolution_rate:.1f}%")

    if grand_total_stats['total_events'] > 0:
        original_opt_rate = grand_total_stats['original_optimized_events'] / grand_total_stats['total_events'] * 100
        final_opt_rate = grand_total_stats['final_optimized_events'] / grand_total_stats['total_events'] * 100
        print(f"  🎯 Original optimization rate: {original_opt_rate:.1f}%")
        print(f"  🎯 Final optimization rate: {final_opt_rate:.1f}%")

    return all_results


def run_single_house_collision_resolution(tariff_name: str = "Economy_7", house_id: str = "house1"):
    """
    运行单个房屋的冲突解决

    Args:
        tariff_name: 电价方案名称，默认Economy_7
        house_id: 房屋ID，默认house1
    """
    resolver = P052CollisionResolver()
    result = resolver.process_single_house(tariff_name, house_id)
    return result


def interactive_mode_selection():
    """交互式模式选择 - 两层选择结构"""
    print("🎯 P053 Collision Resolver - Interactive Mode Selection")
    print("=" * 60)

    # 第一层：选择处理模式
    print("\n📋 Step 1: Select Processing Mode")
    print("1️⃣  Single House Processing")
    print("2️⃣  Batch Processing")

    while True:
        try:
            mode_choice = input("\n🔍 Please select processing mode (1-2): ").strip()

            if mode_choice == "1":
                # 单个房屋处理
                return handle_single_house_selection()

            elif mode_choice == "2":
                # 批处理
                return handle_batch_processing_selection()

            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
                continue

        except KeyboardInterrupt:
            print("\n\n� Goodbye!")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


def handle_single_house_selection():
    """处理单个房屋选择"""
    print("\n🏠 Single House Processing Selected")
    print("=" * 40)

    # 选择电价方案
    print("\n📋 Step 2: Select Tariff Scheme")
    print("1️⃣  UK (Economy_7)")
    print("2️⃣  UK (Economy_10)")
    print("3️⃣  TOU_D (California, Seasonal)")
    print("4️⃣  Germany_Variable (Germany)")

    tariff_map = {
        "1": "Economy_7",
        "2": "Economy_10",
        "3": "TOU_D",
        "4": "Germany_Variable"
    }

    while True:
        try:
            tariff_choice = input("\n🔍 Please select tariff scheme (1-4): ").strip()

            if tariff_choice in tariff_map:
                tariff = tariff_map[tariff_choice]

                # 选择房屋ID
                house_id = input(f"\nEnter house ID (default: house1): ").strip()
                if not house_id:
                    house_id = "house1"

                print(f"\n🚀 Starting single house processing: {tariff}/{house_id}")
                return run_single_house_collision_resolution(tariff, house_id)

            else:
                print("❌ Invalid choice. Please enter 1-4.")
                continue

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


def handle_batch_processing_selection():
    """处理批处理选择"""
    print("\n📦 Batch Processing Selected")
    print("=" * 40)

    # 选择电价方案组
    print("\n📋 Step 2: Select Tariff Group")
    print("1️⃣  UK (Economy_7 + Economy_10)")
    print("2️⃣  TOU_D (California, Seasonal)")
    print("3️⃣  Germany_Variable (Germany)")
    print("4️⃣  All Tariffs (UK + TOU_D + Germany_Variable)")

    while True:
        try:
            group_choice = input("\n🔍 Please select tariff group (1-4): ").strip()

            if group_choice == "1":
                # UK电价方案
                print("\n🏠 UK Tariffs Selected (Economy_7 + Economy_10)")
                return run_collision_resolution(mode="default")

            elif group_choice == "2":
                # TOU_D
                print("\n🌞 TOU_D Selected (California, Seasonal)")
                return run_collision_resolution(mode="single", single_tariff="TOU_D")

            elif group_choice == "3":
                # Germany_Variable
                print("\n🇩🇪 Germany_Variable Selected (Germany)")
                return run_collision_resolution(mode="single", single_tariff="Germany_Variable")

            elif group_choice == "4":
                # 所有电价方案
                print("\n🌍 All Tariffs Selected")
                return run_collision_resolution(mode="all")

            else:
                print("❌ Invalid choice. Please enter 1-4.")
                continue

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


def run_robustness_experiment():
    """运行约束解析错误鲁棒性实验 - 冲突解决"""
    print("🚀 约束解析错误鲁棒性实验 - Collision Resolver")
    print("=" * 60)

    # 固定参数：2个电价类型
    tariff_list = ["Economy_7", "Economy_10"]
    target_houses = ["house1", "house2", "house3", "house20", "house21"]

    print(f"🎯 目标家庭: {', '.join(target_houses)}")
    print(f"🎯 电价类型: {', '.join(tariff_list)}")
    print(f"🎯 处理调度结果中的冲突")

    # 初始化冲突解决器
    resolver = P052CollisionResolver()

    all_results = {}

    for tariff_name in tariff_list:
        print(f"\n🔄 处理电价方案: {tariff_name}")
        print("=" * 40)

        try:
            # 批量处理该电价类型下的所有目标家庭
            result = resolver.process_tariff_batch(tariff_name)
            all_results[tariff_name] = result

            if result["status"] == "success":
                successful_houses = sum(1 for house_result in result["results"].values()
                                      if house_result.get("status") == "success")
                total_houses = len(result["results"])

                print(f"✅ {tariff_name}: {successful_houses}/{total_houses} 家庭处理成功")

                # 显示详细统计
                for house_id, house_result in result["results"].items():
                    if house_result.get("status") == "success":
                        stats = house_result.get("stats", {})
                        resolved = stats.get("resolved_collisions", 0)
                        total_events = stats.get("total_events", 0)
                        print(f"   🏠 {house_id}: {total_events} 事件, {resolved} 冲突已解决")
                    else:
                        print(f"   ❌ {house_id}: 处理失败")
            else:
                print(f"❌ {tariff_name}: 批量处理失败")

        except Exception as e:
            print(f"❌ {tariff_name}: 处理异常 - {str(e)}")
            all_results[tariff_name] = {"status": "failed", "error": str(e)}

    # 显示最终总结
    print(f"\n📊 冲突解决总结:")
    print("=" * 60)

    total_successful = 0
    total_processed = 0

    for tariff_name, result in all_results.items():
        if result["status"] == "success":
            successful = sum(1 for house_result in result["results"].values()
                           if house_result.get("status") == "success")
            total = len(result["results"])
            total_successful += successful
            total_processed += total

            print(f"✅ {tariff_name}: {successful}/{total} 家庭成功")
        else:
            print(f"❌ {tariff_name}: 处理失败")

    if total_processed > 0:
        overall_success_rate = total_successful / total_processed * 100
        print(f"\n🎯 总体成功率: {total_successful}/{total_processed} ({overall_success_rate:.1f}%)")

    return all_results

if __name__ == "__main__":
    # 鲁棒性实验模式：直接运行无交互版本
    run_robustness_experiment()
