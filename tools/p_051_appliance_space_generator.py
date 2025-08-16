2
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np

class LevelBasedScheduler:
    """基于价格等级的智能调度器"""
    
    def __init__(self, tariff_config_path: str, constraints_path: str):
        # 加载配置
        with open(tariff_config_path, 'r') as f:
            self.tariff_config = json.load(f)
        print(f"✅ 电价配置加载成功: {list(self.tariff_config.keys())}")
        
        with open(constraints_path, 'r') as f:
            constraints_data = json.load(f)

        # 处理约束文件结构：如果有appliance_constraints字段，则提取它
        if "appliance_constraints" in constraints_data:
            self.constraints = constraints_data["appliance_constraints"]
        else:
            self.constraints = constraints_data

        print(f"✅ 约束配置加载成功: {list(self.constraints.keys())}")
    
    def get_appliance_global_intervals(self, appliance_name: str, tariff_name: str, show_details: bool = False) -> Dict[int, List[Tuple[int, int]]]:
        """获取以电器为中心的全局可运行区间（按价格等级分组，考虑用户约束）"""
        
        # 获取设备约束
        appliance_constraints = self.constraints.get(appliance_name, {})
        forbidden_times = appliance_constraints.get("forbidden_time", [])
        latest_finish = appliance_constraints.get("latest_finish", "24:00")
        
        # 转换最晚完成时间为分钟（支持48小时制）
        latest_finish_min = self.time_to_minutes(latest_finish)
        
        if show_details:
            print(f"   设备约束: {appliance_name}")
            print(f"     forbidden_time: {forbidden_times}")
            print(f"     latest_finish: {latest_finish} ({latest_finish_min}分钟)")
        
        # 构建48小时内的禁用时间区间
        forbidden_intervals = []
        
        for start_time, end_time in forbidden_times:
            start_min = self.time_to_minutes(start_time)
            end_min = self.time_to_minutes(end_time)
            
            # 处理跨天的禁止时间（如23:30-06:00）
            if end_min <= start_min:  # 跨天情况
                # 第一天：从start_min到24:00(1440分钟)
                forbidden_intervals.append((start_min, 1440))
                # 第二天：从24:00(1440分钟)到end_min+1440
                if latest_finish_min > 1440:
                    forbidden_intervals.append((1440, min(1440 + end_min, latest_finish_min)))
            else:  # 同一天
                # 第一天
                forbidden_intervals.append((start_min, end_min))
                # 第二天（如果latest_finish超过24小时）
                if latest_finish_min > 1440:
                    forbidden_intervals.append((1440 + start_min, min(1440 + end_min, latest_finish_min)))
        
        if show_details:
            print(f"     禁用区间: {forbidden_intervals}")
        
        # 构建全时间范围的可运行区间
        total_range = [(0, latest_finish_min)]
        runnable_intervals = self.subtract_intervals(total_range, forbidden_intervals)
        
        if show_details:
            print(f"     可运行区间: {[(self.minutes_to_time_48h(s), self.minutes_to_time_48h(e)) for s, e in runnable_intervals]}")
        
        # 按价格等级分组可运行区间
        price_level_intervals = {}
        
        for start_min, end_min in runnable_intervals:
            # 在每个可运行区间内，按15分钟步长检查价格等级
            current_min = start_min
            while current_min < end_min:
                level = self.get_price_level_from_csv_data(current_min, tariff_name)
                
                if level not in price_level_intervals:
                    price_level_intervals[level] = []
                
                # 找到当前价格等级的连续区间
                level_start = current_min
                while current_min < end_min and self.get_price_level_from_csv_data(current_min, tariff_name) == level:
                    current_min += 15
                
                level_end = min(current_min, end_min)
                
                # 合并连续区间
                if (price_level_intervals[level] and 
                    price_level_intervals[level][-1][1] == level_start):
                    # 扩展最后一个区间
                    price_level_intervals[level][-1] = (price_level_intervals[level][-1][0], level_end)
                else:
                    # 创建新区间
                    price_level_intervals[level].append((level_start, level_end))
        
        return price_level_intervals
    
    def get_event_candidate_intervals(self, event_current_level: int, global_intervals: Dict[int, List[Tuple[int, int]]]) -> Dict[int, List[Tuple[int, int]]]:
        """获取事件的候选调度区间（只包含比当前等级更优的区间）"""
        
        candidate_intervals = {}
        
        # 只选择比当前价格等级更低（更优）的区间
        for level, intervals in global_intervals.items():
            if level < event_current_level:  # 更低的等级 = 更便宜的价格
                candidate_intervals[level] = intervals
        
        return candidate_intervals
    
    def find_optimal_schedule(self, event_row: pd.Series, appliance_name: str, tariff_name: str, show_details: bool = False) -> Optional[Dict]:
        """为单个事件找到最优调度方案（考虑用户约束）"""
        
        duration_min = int(event_row['duration(min)'])
        
        # 获取事件当前的价格等级
        current_level = int(event_row.get('primary_price_level', 2))
        
        # 获取设备约束
        appliance_constraints = self.constraints.get(appliance_name, {})
        shift_rule = appliance_constraints.get("shift_rule", "only_delay")
        min_duration = appliance_constraints.get("min_duration", 0)
        
        # 检查事件是否满足最小持续时间要求
        if duration_min < min_duration:
            print(f"   ❌ 事件持续时间 {duration_min}分钟 < 最小要求 {min_duration}分钟")
            return None
        
        # 获取原始开始时间
        if isinstance(event_row['start_time'], str):
            original_start_time = pd.to_datetime(event_row['start_time'])
        else:
            original_start_time = event_row['start_time']
        
        # 计算事件在48小时制中的分钟偏移
        event_date = original_start_time.date()
        original_start_min = original_start_time.hour * 60 + original_start_time.minute
        
        if show_details:
            print(f"   事件详情:")
            print(f"     原始时间: {original_start_time} ({self.minutes_to_time_48h(original_start_min)})")
            print(f"     持续时间: {duration_min}分钟")
            print(f"     当前价格等级: {current_level}")
            print(f"     调度规则: {shift_rule}")
        
        # 获取设备的全局可运行区间
        global_intervals = self.get_appliance_global_intervals(appliance_name, tariff_name, show_details)
        
        # 获取事件的候选区间（只包含更优的价格等级）
        candidate_intervals = self.get_event_candidate_intervals(current_level, global_intervals)
        
        if not candidate_intervals:
            if show_details:
                print(f"   ❌ 没有更优的价格等级区间")
            return None
        
        # 根据shift_rule过滤候选区间
        filtered_intervals = {}
        for level, intervals in candidate_intervals.items():
            filtered_intervals[level] = []
            
            for start_min, end_min in intervals:
                if shift_rule == "only_delay":
                    # 只能延后：事件开始时间+5分钟后才能调度
                    earliest_allowed = original_start_min + 5
                    if end_min > earliest_allowed:  # 区间与允许时间有重叠或在其后
                        adjusted_start = max(start_min, earliest_allowed)
                        if adjusted_start + duration_min <= end_min:
                            filtered_intervals[level].append((adjusted_start, end_min))
                
                elif shift_rule == "only_advance":
                    # 只能提前：区间结束时间必须 <= 原始开始时间
                    if start_min < original_start_min:
                        adjusted_end = min(end_min, original_start_min)
                        if start_min + duration_min <= adjusted_end:
                            filtered_intervals[level].append((start_min, adjusted_end))
                
                else:  # "both" 或其他
                    # 可以提前或延后
                    if start_min + duration_min <= end_min:
                        filtered_intervals[level].append((start_min, end_min))
        
        # 移除空的等级
        filtered_intervals = {k: v for k, v in filtered_intervals.items() if v}
        
        if not filtered_intervals:
            if show_details:
                print(f"   ❌ 应用调度规则后无可用区间")
            return None
        
        # 寻找最优调度窗口
        best_option = None
        best_score = float('inf')
        
        # 优先选择价格等级最低的区间
        for level in sorted(filtered_intervals.keys()):
            intervals = filtered_intervals[level]
            
            for start_min, end_min in intervals:
                # 在区间内找到最早的可用开始时间
                candidate_start = start_min
                candidate_end = candidate_start + duration_min
                
                if candidate_end <= end_min:
                    # 计算优化得分（价格等级越低越好）
                    score = level
                    
                    if score < best_score:
                        best_score = score
                        
                        # 计算新的实际日期时间
                        new_start_datetime = self.minutes_to_datetime(candidate_start, event_date)
                        new_end_datetime = self.minutes_to_datetime(candidate_end, event_date)
                        
                        best_option = {
                            'start_minute': candidate_start,
                            'end_minute': candidate_end,
                            'start_time': new_start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                            'end_time': new_end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                            'start_time_48h': self.minutes_to_time_48h(candidate_start),
                            'end_time_48h': self.minutes_to_time_48h(candidate_end),
                            'price_level': level,
                            'optimization_score': current_level - level,
                            'shift_type': self._get_shift_type(original_start_min, candidate_start)
                        }
                        break  # 找到当前等级的最优解，跳出内层循环
            
            if best_option and best_option['price_level'] == level:
                break  # 找到最低等级的解，跳出外层循环
        
        if best_option and show_details:
            print(f"   ✅ 找到最优方案:")
            print(f"     新时间: {best_option['start_time']} - {best_option['end_time']}")
            print(f"     48h格式: {best_option['start_time_48h']} - {best_option['end_time_48h']}")
            print(f"     价格等级: {best_option['price_level']} (改善: {best_option['optimization_score']})")
            print(f"     调度类型: {best_option['shift_type']}")
        
        return best_option
    
    def _get_shift_type(self, original_minute: int, new_minute: int) -> str:
        """确定调度类型"""
        if new_minute < original_minute:
            return "ADVANCE"
        elif new_minute > original_minute:
            return "DELAY"
        else:
            return "NO_CHANGE"
    
    def time_to_minutes(self, time_str: str) -> int:
        """时间字符串转分钟（支持48小时制）"""
        hour, minute = map(int, time_str.split(":"))
        return hour * 60 + minute
    
    def minutes_to_time(self, minutes: int) -> str:
        """分钟转时间字符串"""
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"
    
    def minutes_to_time_48h(self, minutes: int) -> str:
        """分钟转48小时制时间字符串"""
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"
    
    def get_price_level_from_csv_data(self, minutes: int, tariff_name: str, season: str = None) -> int:
        """从电价配置中获取价格等级"""
        hour = (minutes // 60) % 24
        minute = minutes % 60
        current_time_str = f"{hour:02d}:{minute:02d}"

        # 获取当前时间的电价（自动处理季节性）
        current_rate = self.get_rate_for_time(current_time_str, tariff_name, season)

        # 获取该电价方案的所有费率，用于等级划分（自动处理季节性）
        all_rates = self.get_all_rates_for_tariff(tariff_name, season)

        # 为Germany_Variable使用固定的价格等级映射，保持与原始数据一致
        if tariff_name == "Germany_Variable":
            # Germany_Variable的固定价格等级映射
            price_level_mapping = {
                0.22: 0,  # Level 0 (最低价)
                0.26: 1,  # Level 1
                0.28: 2,  # Level 2
                0.30: 3,  # Level 3
                0.32: 4,  # Level 4
                0.34: 5   # Level 5 (最高价)
            }

            # 查找精确匹配或最接近的价格
            if current_rate in price_level_mapping:
                return price_level_mapping[current_rate]
            else:
                # 找最接近的价格
                closest_rate = min(price_level_mapping.keys(), key=lambda x: abs(x - current_rate))
                return price_level_mapping[closest_rate]

        else:
            # 其他电价方案使用动态排序
            sorted_rates = sorted(set(all_rates))

            # 直接根据费率在排序列表中的位置分配等级
            try:
                level = sorted_rates.index(current_rate)
                return level
            except ValueError:
                # 如果找不到精确匹配，找最接近的
                for i, rate in enumerate(sorted_rates):
                    if current_rate <= rate:
                        return i
                return len(sorted_rates) - 1  # 返回最高等级

    def get_rate_for_time(self, time_str: str, tariff_name: str, season: str = None) -> float:
        """获取指定时间的电价费率"""
        # 处理 TOU_D 季节性配置
        if tariff_name == "TOU_D" and season:
            return self.get_tou_d_rate_from_config(time_str, season)

        # 处理 TOU_D 无季节参数（使用混合费率）
        elif tariff_name == "TOU_D":
            return self.get_tou_d_rate(time_str)

        elif tariff_name in self.tariff_config:
            tariff_data = self.tariff_config[tariff_name]

            if tariff_data.get("type") == "time_based":
                # Economy_7, Economy_10 类型
                for period in tariff_data["periods"]:
                    if self.time_in_period(time_str, period["start"], period["end"]):
                        return period["rate"]
                return tariff_data["periods"][0]["rate"]  # 默认返回第一个费率

            elif tariff_data.get("type") == "flat":
                # Standard 类型
                return tariff_data["rate"]

            elif tariff_data.get("tariff_type") == "TOU":
                # TOU类型（如Germany_Variable），使用time_blocks
                if "time_blocks" in tariff_data:
                    for block in tariff_data["time_blocks"]:
                        if self.time_in_period(time_str, block["start"], block["end"]):
                            return block["rate"]
                    return tariff_data.get("default_rate", 0.3)

        return 0.3  # 默认费率

    def get_all_rates_for_tariff(self, tariff_name: str, season: str = None) -> list:
        """获取电价方案的所有费率"""
        rates = []

        # TOU_D 有季节参数：返回指定季节的费率
        if tariff_name == "TOU_D" and season:
            if "TOU_D" in self.tariff_config and "seasonal_rates" in self.tariff_config["TOU_D"]:
                tou_d_config = self.tariff_config["TOU_D"]["seasonal_rates"]
                if season in tou_d_config:
                    time_blocks = tou_d_config[season].get("time_blocks", [])
                    rates = [block["rate"] for block in time_blocks]

        # TOU_D 无季节参数：返回硬编码的混合费率
        elif tariff_name == "TOU_D":
            rates = [0.40, 0.43, 0.46, 0.48, 0.51, 0.60]  # 混合费率

        elif tariff_name in self.tariff_config:
            tariff_data = self.tariff_config[tariff_name]

            if tariff_data.get("type") == "time_based":
                rates = [period["rate"] for period in tariff_data["periods"]]
            elif tariff_data.get("type") == "flat":
                rates = [tariff_data["rate"]]
            elif tariff_data.get("tariff_type") == "TOU":
                # TOU类型（如Germany_Variable），从time_blocks中提取费率
                if "time_blocks" in tariff_data:
                    rates = [block["rate"] for block in tariff_data["time_blocks"]]

        return rates if rates else [0.3]

    def get_tou_d_rate_from_config(self, time_str: str, season: str = None) -> float:
        """从配置文件获取TOU_D电价费率（支持季节性）"""
        if "TOU_D" not in self.tariff_config:
            return self.get_tou_d_rate(time_str)  # 回退到硬编码版本

        tou_d_config = self.tariff_config["TOU_D"]

        if "seasonal_rates" not in tou_d_config:
            return self.get_tou_d_rate(time_str)  # 回退到硬编码版本

        # 如果没有指定季节，使用混合费率（优先夏季）
        if season is None:
            season = "summer"  # 默认使用夏季费率

        if season not in tou_d_config["seasonal_rates"]:
            return self.get_tou_d_rate(time_str)  # 回退到硬编码版本

        seasonal_config = tou_d_config["seasonal_rates"][season]
        time_blocks = seasonal_config.get("time_blocks", [])

        # 查找匹配的时间段
        for block in time_blocks:
            if self.time_in_period(time_str, block["start"], block["end"]):
                return block["rate"]

        # 如果没有找到匹配的时间段，返回默认费率
        return 0.40

    def get_tou_d_rate(self, time_str: str, month: int = None) -> float:
        """获取TOU_D电价费率（正确处理季节性费率）"""
        hour = int(time_str.split(":")[0])

        # 如果没有提供月份，使用混合费率来生成约束空间
        if month is None:
            # 使用混合季节费率来提供更多调度机会
            if 0 <= hour < 14:
                return 0.40   # 等级0 - 最低价
            elif 14 <= hour < 17:
                return 0.48   # 等级1
            elif 17 <= hour < 20:
                return 0.60   # 等级4 - 最高价
            elif 20 <= hour < 22:
                return 0.46   # 等级2
            else:  # 22-24
                return 0.43   # 等级3

        # 根据月份确定季节
        is_summer = 6 <= month <= 9

        if is_summer:
            # 夏季费率 (6-9月)
            if 0 <= hour < 14:
                return 0.40
            elif 14 <= hour < 17:
                return 0.48
            elif 17 <= hour < 20:
                return 0.60
            else:  # 20-24
                return 0.48
        else:
            # 冬季费率 (1-5月, 10-12月)
            if 0 <= hour < 17:
                return 0.43
            elif 17 <= hour < 20:
                return 0.51
            elif 20 <= hour < 22:
                return 0.46
            else:  # 22-24
                return 0.43

    def get_germany_variable_rate(self, time_str: str) -> float:
        """获取Germany_Variable电价费率"""
        hour = int(time_str.split(":")[0])

        if 0 <= hour < 4:
            return 0.22
        elif 4 <= hour < 8:
            return 0.26
        elif 8 <= hour < 12:
            return 0.30
        elif 12 <= hour < 16:
            return 0.34
        elif 16 <= hour < 20:
            return 0.32
        else:  # 20-24
            return 0.28

    def time_in_period(self, time_str: str, start_str: str, end_str: str) -> bool:
        """判断时间是否在指定时段内"""
        def time_to_minutes(t_str):
            h, m = map(int, t_str.split(":"))
            return h * 60 + m

        time_min = time_to_minutes(time_str)
        start_min = time_to_minutes(start_str)
        end_min = time_to_minutes(end_str)

        if start_min <= end_min:
            # 同一天内
            return start_min <= time_min < end_min
        else:
            # 跨天
            return time_min >= start_min or time_min < end_min
    
    def subtract_intervals(self, base_intervals: List[Tuple[int, int]], 
                          subtract_intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """从基础区间中减去禁用区间"""
        if not subtract_intervals:
            return base_intervals
        
        # 合并并排序禁用区间
        subtract_intervals = sorted(subtract_intervals)
        merged_subtract = []
        for start, end in subtract_intervals:
            if merged_subtract and start <= merged_subtract[-1][1]:
                merged_subtract[-1] = (merged_subtract[-1][0], max(merged_subtract[-1][1], end))
            else:
                merged_subtract.append((start, end))
        
        result = []
        for base_start, base_end in base_intervals:
            current_intervals = [(base_start, base_end)]
            
            for sub_start, sub_end in merged_subtract:
                new_intervals = []
                for curr_start, curr_end in current_intervals:
                    if sub_end <= curr_start or sub_start >= curr_end:
                        # 无重叠
                        new_intervals.append((curr_start, curr_end))
                    else:
                        # 有重叠，分割区间
                        if sub_start > curr_start:
                            new_intervals.append((curr_start, sub_start))
                        if sub_end < curr_end:
                            new_intervals.append((sub_end, curr_end))
                current_intervals = new_intervals
            
            result.extend(current_intervals)
        
        return result

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

def schedule_events_by_level(events_path: str, constraints_path: str, 
                           tariff_path: str, tariff_name: str, 
                           output_path: str) -> pd.DataFrame:
    """基于价格等级的事件调度主函数"""
    
    # 初始化调度器
    scheduler = LevelBasedScheduler(tariff_path, constraints_path)
    
    # 加载事件数据
    df = pd.read_csv(events_path, parse_dates=['start_time', 'end_time'])
    df_reschedulable = df[df['is_reschedulable'] == True].copy()
    
    print(f"🔍 Processing {len(df_reschedulable)} reschedulable events for {tariff_name}")
    
    results = []
    successful_count = 0
    failed_count = 0
    
    # 处理每个可调度事件
    for i, (_, event) in enumerate(df_reschedulable.iterrows()):
        appliance_name = event['appliance_name']

        # 只显示前2个事件的详细信息作为示例
        show_details = i < 2

        # 寻找最优调度方案
        optimal_schedule = scheduler.find_optimal_schedule(event, appliance_name, tariff_name, show_details)
        
        if optimal_schedule:
            # 调度成功
            results.append({
                "event_id": event['event_id'],
                "appliance_name": appliance_name,
                "original_start_time": event['start_time'],
                "original_end_time": event['end_time'],
                "original_price_level": int(event.get('primary_price_level', 2)),
                "shifted_start_time": optimal_schedule['start_time'],  # 现在包含完整日期时间
                "shifted_end_time": optimal_schedule['end_time'],      # 现在包含完整日期时间
                "shifted_price_level": optimal_schedule['price_level'],
                "duration(min)": event['duration(min)'],
                "energy(W)": event['energy(W)'],
                "tariff": tariff_name,
                "optimization_score": optimal_schedule['optimization_score'],
                "shift_type": optimal_schedule['shift_type'],  # 添加调度类型
                "schedule_status": "SUCCESS"
            })
            successful_count += 1
        else:
            # 调度失败
            results.append({
                "event_id": event['event_id'],
                "appliance_name": appliance_name,
                "original_start_time": event['start_time'],
                "original_end_time": event['end_time'],
                "original_price_level": int(event.get('primary_price_level', 2)),
                "shifted_start_time": "FAILED",
                "shifted_end_time": "FAILED",
                "shifted_price_level": None,
                "duration(min)": event['duration(min)'],
                "energy(W)": event['energy(W)'],
                "tariff": tariff_name,
                "optimization_score": 0,
                "shift_type": "FAILED",
                "schedule_status": "FAILED"
            })
            failed_count += 1
    
    # 创建结果DataFrame
    df_result = pd.DataFrame(results)
    
    # 保存结果
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_result.to_csv(output_path, index=False)
    
    print(f"\n📊 Scheduling Summary for {tariff_name}:")
    print(f"   ✅ Successful: {successful_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📈 Success Rate: {successful_count/(successful_count+failed_count)*100:.1f}%")
    print(f"   📁 Results saved to: {output_path}")
    
    return df_result

def extract_reschedulable_events(tariff_name: str) -> str:
    """提取可调度事件并保存为单独的CSV文件"""

    # 确定输入文件路径
    if tariff_name in ["Economy_7", "Economy_10"]:
        events_path = f"./output/04_user_constraints/shiftable_event_masked_{tariff_name}.csv"
    else:
        events_path = f"./output/04_user_constraints/{tariff_name}/shiftable_event_masked_{tariff_name}.csv"

    # 输出文件路径
    output_path = f"./output/05_scheduling/reschedulable_events_{tariff_name}.csv"

    if not os.path.exists(events_path):
        print(f"❌ Events file not found: {events_path}")
        return None

    # 读取事件数据
    df = pd.read_csv(events_path, parse_dates=['start_time', 'end_time'])

    # 提取可调度事件
    df_reschedulable = df[df['is_reschedulable'] == True].copy()

    print(f"📊 {tariff_name} 事件统计:")
    print(f"   总事件数: {len(df)}")
    print(f"   可调度事件数: {len(df_reschedulable)}")
    print(f"   可调度比例: {len(df_reschedulable)/len(df)*100:.1f}%")

    # 保存可调度事件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_reschedulable.to_csv(output_path, index=False)
    print(f"   📁 可调度事件已保存: {output_path}")

    return output_path

def run_level_based_scheduler():
    """运行基于价格等级的调度器"""
    tariff_schemes = ["Economy_7", "Economy_10", "TOU_D", "Germany_Variable"]
    
    for tariff_name in tariff_schemes:
        print(f"\n{'='*60}")
        print(f"🚀 Running Level-Based Scheduler for {tariff_name}")
        print(f"{'='*60}")
        
        # 第一步：提取可调度事件
        reschedulable_events_path = extract_reschedulable_events(tariff_name)
        if not reschedulable_events_path:
            continue

        # 第二步：运行调度
        constraints_path = "./output/04_user_constraints/appliance_constraints_revise_by_llm.json"
        tariff_path = "./config/tariff_config.json"
        output_path = f"./output/05_scheduling/level_based_{tariff_name}.csv"
        
        try:
            # 运行调度
            df_result = schedule_events_by_level(
                reschedulable_events_path, constraints_path, tariff_path,
                tariff_name, output_path
            )
            
            # 显示详细统计
            if not df_result.empty:
                successful_events = df_result[df_result['schedule_status'] == 'SUCCESS']
                if len(successful_events) > 0:
                    avg_improvement = successful_events['optimization_score'].mean()
                    print(f"📈 Average Price Level Improvement: {avg_improvement:.2f}")
                    
                    # 按设备类型统计
                    summary = df_result.groupby('appliance_name').agg({
                        'event_id': 'count',
                        'schedule_status': lambda x: (x == 'SUCCESS').sum()
                    }).rename(columns={
                        'event_id': 'Total_Events',
                        'schedule_status': 'Successful_Events'
                    })
                    summary['Success_Rate'] = (summary['Successful_Events'] / summary['Total_Events'] * 100).round(1)
                    print(f"\n📊 Per-appliance statistics:")
                    print(summary)
        
        except Exception as e:
            print(f"❌ Error processing {tariff_name}: {e}")
            import traceback
            traceback.print_exc()

def debug_appliance_intervals(scheduler, appliance_name: str, tariff_name: str, output_dir: str):
    """生成设备可运行区间的调试文件"""
    
    # 获取设备的全局可运行区间
    global_intervals = scheduler.get_appliance_global_intervals(appliance_name, tariff_name)
    
    # 创建调试数据
    debug_data = []
    
    # 添加全局区间信息
    for level, intervals in global_intervals.items():
        for start_min, end_min in intervals:
            debug_data.append({
                'appliance_name': appliance_name,
                'tariff': tariff_name,
                'price_level': level,
                'start_minute': start_min,
                'end_minute': end_min,
                'start_time_48h': scheduler.minutes_to_time_48h(start_min),
                'end_time_48h': scheduler.minutes_to_time_48h(end_min),
                'duration_minutes': end_min - start_min,
                'interval_type': 'AVAILABLE'
            })
    
    # 添加禁用区间信息
    appliance_constraints = scheduler.constraints.get(appliance_name, {})
    forbidden_times = appliance_constraints.get("forbidden_time", [])
    latest_finish = appliance_constraints.get("latest_finish", "24:00")
    latest_finish_min = scheduler.time_to_minutes(latest_finish)
    
    # 构建禁用区间
    forbidden_intervals = []
    for forbidden_period in forbidden_times:
        start_time, end_time = forbidden_period
        start_min = scheduler.time_to_minutes(start_time)
        end_min = scheduler.time_to_minutes(end_time)
        
        if start_min > end_min:  # 跨天情况
            forbidden_intervals.extend([
                (start_min, 1440),  # 当天剩余时间
                (1440, 1440 + end_min)  # 次日开始时间
            ])
        else:
            forbidden_intervals.append((start_min, end_min))
            if latest_finish_min > 1440:  # 如果允许到次日
                forbidden_intervals.append((1440 + start_min, 1440 + end_min))
    
    # 添加禁用区间到调试数据
    for start_min, end_min in forbidden_intervals:
        if start_min < latest_finish_min:
            debug_data.append({
                'appliance_name': appliance_name,
                'tariff': tariff_name,
                'price_level': -1,  # 用-1表示禁用区间
                'start_minute': start_min,
                'end_minute': min(end_min, latest_finish_min),
                'start_time_48h': scheduler.minutes_to_time_48h(start_min),
                'end_time_48h': scheduler.minutes_to_time_48h(min(end_min, latest_finish_min)),
                'duration_minutes': min(end_min, latest_finish_min) - start_min,
                'interval_type': 'FORBIDDEN'
            })
    
    # 保存调试文件
    import pandas as pd
    import os
    
    df_debug = pd.DataFrame(debug_data)
    df_debug = df_debug.sort_values(['start_minute'])
    
    os.makedirs(output_dir, exist_ok=True)
    debug_file = os.path.join(output_dir, f"debug_intervals_{appliance_name}_{tariff_name}.csv")
    df_debug.to_csv(debug_file, index=False)
    
    print(f"📁 调试文件已保存: {debug_file}")
    return debug_file

def debug_price_levels(scheduler, tariff_name: str, output_dir: str):
    """生成价格等级的调试文件"""
    
    debug_data = []
    
    # 生成48小时内每15分钟的价格等级
    for minutes in range(0, 2880, 15):  # 48小时 = 2880分钟
        level = scheduler.get_price_level_from_csv_data(minutes, tariff_name)
        debug_data.append({
            'tariff': tariff_name,
            'minute': minutes,
            'time_48h': scheduler.minutes_to_time_48h(minutes),
            'hour': minutes // 60,
            'price_level': level
        })
    
    # 保存调试文件
    import pandas as pd
    import os
    
    df_debug = pd.DataFrame(debug_data)
    
    os.makedirs(output_dir, exist_ok=True)
    debug_file = os.path.join(output_dir, f"debug_price_levels_{tariff_name}.csv")
    df_debug.to_csv(debug_file, index=False)
    
    print(f"📁 价格等级调试文件已保存: {debug_file}")
    return debug_file

def run_debug_analysis():
    """运行调试分析，生成中间文件"""
    
    print("🔍 开始生成调试文件...")
    
    # 初始化调度器
    tariff_path = "./config/tariff_config.json"
    constraints_path = "./output/04_user_constraints/appliance_constraints_revise_by_llm.json"
    output_dir = "./output/05_scheduling/debug"
    
    for tariff_name in ["Economy_7", "Economy_10", "TOU_D", "Germany_Variable"]:
        print(f"\n{'='*50}")
        print(f"🚀 生成 {tariff_name} 调试文件")
        print(f"{'='*50}")
        
        scheduler = LevelBasedScheduler(tariff_path, constraints_path)
        
        # 生成价格等级调试文件
        debug_price_levels(scheduler, tariff_name, output_dir)
        
        # 为每个设备生成可运行区间调试文件
        appliances = list(scheduler.constraints.keys())
        for appliance_name in appliances:
            print(f"\n📊 处理设备: {appliance_name}")
            debug_appliance_intervals(scheduler, appliance_name, tariff_name, output_dir)

def generate_appliance_global_spaces(scheduler, tariff_name: str, output_dir: str):
    """为每种电器生成全局约束空间和可运行空间"""
    
    print(f"\n🏗️ 生成电器全局空间文件 - {tariff_name}")
    print(f"{'='*60}")
    
    appliance_spaces = {}
    
    for appliance_name in scheduler.constraints.keys():
        print(f"\n📱 处理电器: {appliance_name}")
        
        # 获取电器约束
        appliance_constraints = scheduler.constraints[appliance_name]
        forbidden_times = appliance_constraints.get("forbidden_time", [])
        latest_finish = appliance_constraints.get("latest_finish", "24:00")
        shift_rule = appliance_constraints.get("shift_rule", "only_delay")
        min_duration = appliance_constraints.get("min_duration", 5)
        
        print(f"   约束信息:")
        print(f"     forbidden_time: {forbidden_times}")
        print(f"     latest_finish: {latest_finish}")
        print(f"     shift_rule: {shift_rule}")
        print(f"     min_duration: {min_duration}")
        
        # 计算最迟完成时间（分钟）
        latest_finish_min = scheduler.time_to_minutes(latest_finish)
        
        # 构建禁用区间
        forbidden_intervals = []
        for forbidden_period in forbidden_times:
            start_time, end_time = forbidden_period
            start_min = scheduler.time_to_minutes(start_time)
            end_min = scheduler.time_to_minutes(end_time)
            
            if start_min > end_min:  # 跨天情况
                forbidden_intervals.extend([
                    (start_min, 1440),  # 当天剩余时间
                    (1440, 1440 + end_min)  # 次日开始时间
                ])
            else:
                forbidden_intervals.append((start_min, end_min))
                # 如果允许到次日，也添加次日的禁用时间
                if latest_finish_min > 1440:
                    forbidden_intervals.append((1440 + start_min, 1440 + end_min))
        
        # 构建全局可运行区间（排除禁用区间）
        available_intervals = []
        current_start = 0
        
        # 按禁用区间开始时间排序
        forbidden_intervals.sort()
        
        for forbidden_start, forbidden_end in forbidden_intervals:
            if forbidden_start < latest_finish_min:
                # 添加禁用区间前的可用时间
                if current_start < forbidden_start:
                    available_intervals.append((current_start, forbidden_start))
                current_start = max(current_start, min(forbidden_end, latest_finish_min))
        
        # 添加最后一段可用时间
        if current_start < latest_finish_min:
            available_intervals.append((current_start, latest_finish_min))
        
        # 按价格等级分类可运行区间
        price_level_intervals = {}  # 动态创建价格等级字典

        for start_min, end_min in available_intervals:
            # 将区间按价格等级细分
            current_pos = start_min
            while current_pos < end_min:
                # 找到当前位置的价格等级
                current_level = scheduler.get_price_level_from_csv_data(current_pos, tariff_name)

                # 如果该价格等级不存在，则创建
                if current_level not in price_level_intervals:
                    price_level_intervals[current_level] = []

                # 找到相同价格等级的连续区间
                segment_start = current_pos
                while current_pos < end_min:
                    level = scheduler.get_price_level_from_csv_data(current_pos, tariff_name)
                    if level != current_level:
                        break
                    current_pos += 1

                # 添加到对应价格等级
                if current_pos > segment_start:
                    price_level_intervals[current_level].append((segment_start, current_pos))
        
        # 保存电器空间信息
        appliance_spaces[appliance_name] = {
            'appliance_name': appliance_name,
            'constraints': appliance_constraints,
            'latest_finish_minutes': latest_finish_min,
            'forbidden_intervals': forbidden_intervals,
            'available_intervals': available_intervals,
            'price_level_intervals': price_level_intervals
        }
        
        print(f"   ✅ 生成空间:")
        print(f"     可运行区间数: {len(available_intervals)}")

        # 动态显示各价格等级的区间数
        for level in sorted(price_level_intervals.keys()):
            level_name = f"等级{level}"
            if level == 0:
                level_name += "(最低价)"
            elif level == max(price_level_intervals.keys()):
                level_name += "(最高价)"
            print(f"     {level_name}区间数: {len(price_level_intervals[level])}")
    
    # 保存到JSON文件
    import json
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    spaces_file = os.path.join(output_dir, f"appliance_global_spaces_{tariff_name}.json")
    
    # 转换为可序列化格式
    serializable_spaces = {}
    for appliance_name, space_data in appliance_spaces.items():
        serializable_spaces[appliance_name] = {
            'appliance_name': space_data['appliance_name'],
            'constraints': space_data['constraints'],
            'latest_finish_minutes': space_data['latest_finish_minutes'],
            'forbidden_intervals': space_data['forbidden_intervals'],
            'available_intervals': space_data['available_intervals'],
            'price_level_intervals': {
                str(k): v for k, v in space_data['price_level_intervals'].items()
            }
        }
    
    with open(spaces_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_spaces, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 电器全局空间文件已保存: {spaces_file}")
    return appliance_spaces

def generate_appliance_global_spaces_no_save(scheduler, tariff_name: str):
    """为每种电器生成全局约束空间和可运行空间（不保存文件）"""

    print(f"\n🏗️ 生成电器工作空间 - {tariff_name}")
    print("=" * 60)

    appliance_spaces = {}

    for appliance_name in scheduler.constraints.keys():
        print(f"\n📱 处理电器: {appliance_name}")

        # 获取电器约束
        appliance_constraints = scheduler.constraints[appliance_name]

        # 显示约束信息
        print(f"   约束信息:")
        print(f"     forbidden_time: {appliance_constraints.get('forbidden_time', [])}")
        print(f"     latest_finish: {appliance_constraints.get('latest_finish', '24:00')}")
        print(f"     shift_rule: {appliance_constraints.get('shift_rule', 'only_delay')}")
        print(f"     min_duration: {appliance_constraints.get('min_duration', 5)}")

        # 生成电器空间
        appliance_space = scheduler.generate_appliance_global_space(
            appliance_name, appliance_constraints, tariff_name
        )

        if appliance_space:
            appliance_spaces[appliance_name] = appliance_space

            # 显示生成结果
            price_level_intervals = appliance_space.get('price_level_intervals', {})
            available_intervals = appliance_space.get('available_intervals', [])

            print(f"   ✅ 生成空间:")
            print(f"     可运行区间数: {len(available_intervals)}")

            for level in sorted(price_level_intervals.keys()):
                level_name = f"等级{level}"
                if level == 0:
                    level_name += "(最低价)"
                elif level == max(price_level_intervals.keys()):
                    level_name += "(最高价)"
                print(f"     {level_name}区间数: {len(price_level_intervals[level])}")
        else:
            print(f"   ❌ 生成失败")

    return appliance_spaces

def generate_appliance_global_spaces_with_season(scheduler, tariff_name: str, output_dir: str, season: str = None):
    """为每种电器生成全局约束空间和可运行空间（支持季节性）"""

    print(f"\n🏗️ 生成电器全局空间文件 - {tariff_name}")
    if season:
        print(f"   季节: {season}")
    print(f"{'='*60}")

    appliance_spaces = {}

    for appliance_name in scheduler.constraints.keys():
        print(f"\n📱 处理电器: {appliance_name}")

        # 获取电器约束
        appliance_constraints = scheduler.constraints[appliance_name]

        # 显示约束信息
        print(f"   约束信息:")
        print(f"     forbidden_time: {appliance_constraints.get('forbidden_time', [])}")
        print(f"     latest_finish: {appliance_constraints.get('latest_finish', '24:00')}")
        print(f"     shift_rule: {appliance_constraints.get('shift_rule', 'only_delay')}")
        print(f"     min_duration: {appliance_constraints.get('min_duration', 5)}")

        # 生成电器空间（季节参数会自动传递到价格计算方法）
        appliance_space = generate_single_appliance_space_seasonal(
            scheduler, appliance_name, appliance_constraints, tariff_name, season
        )

        if appliance_space:
            appliance_spaces[appliance_name] = appliance_space

            # 显示生成结果
            price_level_intervals = appliance_space.get('price_level_intervals', {})
            available_intervals = appliance_space.get('available_intervals', [])

            print(f"   ✅ 生成空间:")
            print(f"     可运行区间数: {len(available_intervals)}")

            for level in sorted(price_level_intervals.keys()):
                level_name = f"等级{level}"
                if level == 0:
                    level_name += "(最低价)"
                elif level == max(price_level_intervals.keys()):
                    level_name += "(最高价)"
                print(f"     {level_name}区间数: {len(price_level_intervals[level])}")
        else:
            print(f"   ❌ 生成失败")

    # 保存文件
    import os

    os.makedirs(output_dir, exist_ok=True)
    spaces_file = os.path.join(output_dir, f"appliance_global_spaces_{tariff_name}.json")

    # 转换为可序列化格式
    serializable_spaces = {}
    for appliance_name, space_data in appliance_spaces.items():
        serializable_data = {}
        for key, value in space_data.items():
            if key == 'price_level_intervals':
                # 转换价格等级区间为可序列化格式
                serializable_intervals = {}
                for level, intervals in value.items():
                    serializable_intervals[str(level)] = intervals
                serializable_data[key] = serializable_intervals
            else:
                serializable_data[key] = value
        serializable_spaces[appliance_name] = serializable_data

    with open(spaces_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_spaces, f, indent=2, ensure_ascii=False)

    print(f"\n📁 电器全局空间文件已保存: {spaces_file}")
    return appliance_spaces

def generate_appliance_global_spaces_seasonal(scheduler, tariff_name: str, output_dir: str, season: str = None):
    """为每种电器生成全局约束空间和可运行空间（简化的季节性处理）"""

    print(f"\n🏗️ 生成电器全局空间文件 - {tariff_name}")
    if season:
        print(f"   季节: {season}")
    print(f"{'='*60}")

    appliance_spaces = {}

    for appliance_name in scheduler.constraints.keys():
        print(f"\n📱 处理电器: {appliance_name}")

        # 获取电器约束
        appliance_constraints = scheduler.constraints[appliance_name]

        # 显示约束信息
        print(f"   约束信息:")
        print(f"     forbidden_time: {appliance_constraints.get('forbidden_time', [])}")
        print(f"     latest_finish: {appliance_constraints.get('latest_finish', '24:00')}")
        print(f"     shift_rule: {appliance_constraints.get('shift_rule', 'only_delay')}")
        print(f"     min_duration: {appliance_constraints.get('min_duration', 5)}")

        # 生成电器空间（季节参数会自动传递到价格计算方法）
        appliance_space = generate_single_appliance_space_seasonal(
            scheduler, appliance_name, appliance_constraints, tariff_name, season
        )

        if appliance_space:
            appliance_spaces[appliance_name] = appliance_space

            # 显示生成结果
            price_level_intervals = appliance_space.get('price_level_intervals', {})
            available_intervals = appliance_space.get('available_intervals', [])

            print(f"   ✅ 生成空间:")
            print(f"     可运行区间数: {len(available_intervals)}")

            for level in sorted(price_level_intervals.keys()):
                level_name = f"等级{level}"
                if level == 0:
                    level_name += "(最低价)"
                elif level == max(price_level_intervals.keys()):
                    level_name += "(最高价)"
                print(f"     {level_name}区间数: {len(price_level_intervals[level])}")
        else:
            print(f"   ❌ 生成失败")

    # 保存文件
    import os

    os.makedirs(output_dir, exist_ok=True)
    spaces_file = os.path.join(output_dir, f"appliance_global_spaces_{tariff_name}.json")

    # 转换为可序列化格式
    serializable_spaces = {}
    for appliance_name, space_data in appliance_spaces.items():
        serializable_data = {}
        for key, value in space_data.items():
            if key == 'price_level_intervals':
                # 转换价格等级区间为可序列化格式
                serializable_intervals = {}
                for level, intervals in value.items():
                    serializable_intervals[str(level)] = intervals
                serializable_data[key] = serializable_intervals
            else:
                serializable_data[key] = value
        serializable_spaces[appliance_name] = serializable_data

    with open(spaces_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_spaces, f, indent=2, ensure_ascii=False)

    print(f"\n📁 电器全局空间文件已保存: {spaces_file}")
    return appliance_spaces

def generate_single_appliance_space_seasonal(scheduler, appliance_name: str, appliance_constraints: dict, tariff_name: str, season: str = None):
    """为单个电器生成工作空间（简化的季节性处理）"""

    # 获取电器的全局可运行区间
    global_intervals = scheduler.get_appliance_global_intervals(appliance_name, tariff_name)

    # 获取可运行区间列表
    available_intervals = []
    for level, intervals in global_intervals.items():
        available_intervals.extend(intervals)

    # 按价格等级分组区间（季节参数会自动传递）
    price_level_intervals = {}

    for start_min, end_min in available_intervals:
        # 在每个可运行区间内，按15分钟步长检查价格等级
        current_min = start_min
        while current_min < end_min:
            # 关键：这里传递季节参数，让价格计算方法自动处理
            level = scheduler.get_price_level_from_csv_data(current_min, tariff_name, season)

            if level not in price_level_intervals:
                price_level_intervals[level] = []

            # 找到当前价格等级的连续区间
            level_start = current_min
            while current_min < end_min and scheduler.get_price_level_from_csv_data(current_min, tariff_name, season) == level:
                current_min += 15

            level_end = min(current_min, end_min)

            # 合并连续区间
            if (price_level_intervals[level] and
                price_level_intervals[level][-1][1] == level_start):
                # 扩展最后一个区间
                price_level_intervals[level][-1] = (price_level_intervals[level][-1][0], level_end)
            else:
                # 创建新区间
                price_level_intervals[level].append((level_start, level_end))

    # 为Germany_Variable强制包含所有6个价格等级，保持与原始数据一致
    if tariff_name == "Germany_Variable":
        # 确保包含所有6个价格等级（0-5），即使某些等级没有可用时间
        for level in range(6):
            if level not in price_level_intervals:
                price_level_intervals[level] = []  # 空区间列表

    # 保持原始价格等级编号（不重新映射）
    # 注意：即使某些价格等级没有可用时间（如被forbidden_time覆盖），
    # 也要保持与原始事件数据的价格等级编号一致性

    # 生成禁用区间
    forbidden_intervals = []
    forbidden_times = appliance_constraints.get('forbidden_time', [])
    for forbidden_period in forbidden_times:
        if len(forbidden_period) == 2:
            start_time, end_time = forbidden_period
            start_minutes = scheduler.time_to_minutes(start_time)
            end_minutes = scheduler.time_to_minutes(end_time)

            # 处理跨天情况
            if end_minutes <= start_minutes:
                end_minutes += 1440  # 加24小时

            forbidden_intervals.append([start_minutes, end_minutes])

    # 构建电器空间数据
    appliance_space = {
        'appliance_name': appliance_name,
        'constraints': appliance_constraints,
        'latest_finish_minutes': scheduler.time_to_minutes(appliance_constraints.get('latest_finish', '24:00')),
        'forbidden_intervals': forbidden_intervals,
        'available_intervals': available_intervals,
        'price_level_intervals': price_level_intervals
    }

    return appliance_space

def generate_appliance_intervals_csv(appliance_spaces: dict, tariff_name: str, output_dir: str):
    """生成电器区间的CSV调试文件"""
    
    debug_data = []
    
    for appliance_name, space_data in appliance_spaces.items():
        # 添加禁用区间
        for start_min, end_min in space_data['forbidden_intervals']:
            debug_data.append({
                'appliance_name': appliance_name,
                'tariff': tariff_name,
                'price_level': -1,
                'start_minute': start_min,
                'end_minute': end_min,
                'start_time_48h': f"{start_min//60:02d}:{start_min%60:02d}",
                'end_time_48h': f"{end_min//60:02d}:{end_min%60:02d}",
                'duration_minutes': end_min - start_min,
                'interval_type': 'FORBIDDEN'
            })
        
        # 添加可运行区间（按价格等级）
        for price_level, intervals in space_data['price_level_intervals'].items():
            price_level = int(price_level)
            for start_min, end_min in intervals:
                debug_data.append({
                    'appliance_name': appliance_name,
                    'tariff': tariff_name,
                    'price_level': price_level,
                    'start_minute': start_min,
                    'end_minute': end_min,
                    'start_time_48h': f"{start_min//60:02d}:{start_min%60:02d}",
                    'end_time_48h': f"{end_min//60:02d}:{end_min%60:02d}",
                    'duration_minutes': end_min - start_min,
                    'interval_type': 'AVAILABLE'
                })
    
    # 保存CSV文件
    import pandas as pd
    import os
    
    df_debug = pd.DataFrame(debug_data)
    df_debug = df_debug.sort_values(['appliance_name', 'start_minute'])
    
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, f"appliance_intervals_{tariff_name}.csv")
    df_debug.to_csv(csv_file, index=False)
    
    print(f"📁 电器区间CSV文件已保存: {csv_file}")
    return csv_file

def run_generate_appliance_spaces(test_mode: bool = False):
    """生成所有电器的全局空间文件

    Args:
        test_mode: False=主流程(Economy_7, Economy_10), True=测试流程(TOU_D, Germany_Variable)
    """

    print("🏗️ 开始生成电器全局空间文件...")

    # 初始化调度器
    tariff_path = "./config/tariff_config.json"
    constraints_path = "./output/04_user_constraints/appliance_constraints_revise_by_llm.json"
    output_dir = "./output/05_scheduling/appliance_spaces"

    if test_mode:
        # 测试模式：只生成TOU_D和Germany_Variable
        tariff_schemes = ["TOU_D", "Germany_Variable"]
        print("🧪 测试模式：生成 TOU_D 和 Germany_Variable 电器空间")
    else:
        # 主流程模式：只生成Economy_7和Economy_10
        tariff_schemes = ["Economy_7", "Economy_10"]
        print("🏠 主流程模式：生成 Economy_7 和 Economy_10 电器空间")

    for tariff_name in tariff_schemes:
        print(f"\n{'='*60}")
        print(f"🚀 生成 {tariff_name} 电器空间")
        print(f"{'='*60}")

        scheduler = LevelBasedScheduler(tariff_path, constraints_path)

        # 生成电器全局空间
        appliance_spaces = generate_appliance_global_spaces(scheduler, tariff_name, output_dir)

        # 生成CSV调试文件
        generate_appliance_intervals_csv(appliance_spaces, tariff_name, output_dir)

def get_all_available_houses() -> List[str]:
    """获取所有可用的house列表"""
    house_dirs = []
    constraints_dir = "output/04_user_constraints"

    if os.path.exists(constraints_dir):
        for item in os.listdir(constraints_dir):
            if item.startswith("house") and os.path.isdir(os.path.join(constraints_dir, item)):
                house_dirs.append(item)

    # 自然排序
    def natural_sort_key(house_id):
        import re
        return int(re.search(r'\d+', house_id).group())

    house_dirs.sort(key=natural_sort_key)
    return house_dirs

def get_tariff_config_path(tariff_name: str) -> str:
    """获取电价配置文件路径"""
    if tariff_name in ["Economy_7", "Economy_10"]:
        return "config/tariff_config.json"
    elif tariff_name == "TOU_D":
        return "config/TOU_D.json"
    elif tariff_name == "Germany_Variable":
        return "config/Germany_Variable.json"
    else:
        return "config/tariff_config.json"  # 默认

def get_output_directory(tariff_name: str, house_id: str, season: str = None) -> str:
    """获取正确的输出目录路径"""
    if tariff_name in ["Economy_7", "Economy_10"]:
        base_dir = f"output/05_appliance_working_spaces/UK/{tariff_name}/{house_id}"
    elif tariff_name == "TOU_D":
        if season:
            base_dir = f"output/05_appliance_working_spaces/TOU_D/{season}/{house_id}"
        else:
            base_dir = f"output/05_appliance_working_spaces/TOU_D/{house_id}"
    elif tariff_name == "Germany_Variable":
        base_dir = f"output/05_appliance_working_spaces/Germany_Variable/{house_id}"
    else:
        base_dir = f"output/05_appliance_working_spaces/{tariff_name}/{house_id}"

    return base_dir

def filter_reschedulable_appliances(appliance_spaces: Dict) -> Dict:
    """过滤出可调度的电器（有多个价格等级区间的电器）"""
    reschedulable_spaces = {}

    for appliance_name, space_data in appliance_spaces.items():
        price_level_intervals = space_data.get('price_level_intervals', {})

        # 检查是否有多个价格等级或者有Level 0（最低价格）区间
        has_multiple_levels = len(price_level_intervals) > 1
        has_level_0 = '0' in price_level_intervals or 0 in price_level_intervals

        # 检查是否有足够的调度空间
        total_available_time = 0
        for level, intervals in price_level_intervals.items():
            for start, end in intervals:
                total_available_time += (end - start)

        # 如果有多个价格等级或有最低价格区间，且总可用时间 > 60分钟，则认为可调度
        if (has_multiple_levels or has_level_0) and total_available_time > 60:
            reschedulable_spaces[appliance_name] = space_data
            print(f"   ✅ {appliance_name}: 可调度 (等级数: {len(price_level_intervals)}, 可用时间: {total_available_time}分钟)")
        else:
            print(f"   ❌ {appliance_name}: 不可调度 (等级数: {len(price_level_intervals)}, 可用时间: {total_available_time}分钟)")

    return reschedulable_spaces

def process_house_season(house_id: str, tariff_name: str, season: str,
                        tariff_config_path: str, constraints_path: str) -> Dict:
    """处理单个house的单个季节"""

    print(f"\n🏠 处理 {house_id} - {tariff_name}")
    if season:
        print(f"   季节: {season}")

    try:
        # 创建调度器实例
        scheduler = LevelBasedScheduler(tariff_config_path, constraints_path)

        # 创建正确的输出目录
        output_dir = get_output_directory(tariff_name, house_id, season)
        os.makedirs(output_dir, exist_ok=True)

        # 生成电器全局空间（传递季节参数给调度器）
        appliance_spaces = generate_appliance_global_spaces_seasonal(scheduler, tariff_name, output_dir, season)

        # 删除重复的文件（如果存在）
        duplicate_file = os.path.join(output_dir, f"appliance_global_spaces_{tariff_name}.json")
        if os.path.exists(duplicate_file):
            os.remove(duplicate_file)
            print(f"🗑️ 删除重复文件: {duplicate_file}")

        # 保存全局空间文件
        global_spaces_file = os.path.join(output_dir, "appliance_global_spaces.json")
        with open(global_spaces_file, 'w', encoding='utf-8') as f:
            json.dump(appliance_spaces, f, indent=2, ensure_ascii=False)

        print(f"📁 全局空间文件已保存: {global_spaces_file}")

        # 过滤可调度电器
        reschedulable_spaces = filter_reschedulable_appliances(appliance_spaces)

        # 保存可调度空间文件
        reschedulable_spaces_file = os.path.join(output_dir, "appliance_reschedulable_spaces.json")
        with open(reschedulable_spaces_file, 'w', encoding='utf-8') as f:
            json.dump(reschedulable_spaces, f, indent=2, ensure_ascii=False)

        print(f"📁 可调度空间文件已保存: {reschedulable_spaces_file}")

        # 统计信息
        total_appliances = len(appliance_spaces)
        reschedulable_appliances = len(reschedulable_spaces)

        print(f"📊 统计信息:")
        print(f"   总电器数: {total_appliances}")
        print(f"   可调度电器数: {reschedulable_appliances}")
        print(f"   可调度比例: {reschedulable_appliances/total_appliances*100:.1f}%")

        return {
            "status": "success",
            "house_id": house_id,
            "tariff_name": tariff_name,
            "season": season,
            "output_dir": output_dir,
            "total_appliances": total_appliances,
            "reschedulable_appliances": reschedulable_appliances,
            "global_spaces_file": global_spaces_file,
            "reschedulable_spaces_file": reschedulable_spaces_file
        }

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

def process_single_house(house_id: str = "house1", tariff_name: str = "Economy_7") -> Dict:
    """处理单个house"""

    print(f"🏠 单用户模式: {house_id}")
    print(f"📋 电价方案: {tariff_name}")

    # 检查约束文件是否存在
    constraints_path = f"output/04_user_constraints/{house_id}/appliance_constraints_revise_by_llm.json"
    if not os.path.exists(constraints_path):
        print(f"❌ 约束文件不存在: {constraints_path}")
        return {"status": "failed", "error": f"约束文件不存在: {constraints_path}"}

    # 获取电价配置路径
    tariff_config_path = get_tariff_config_path(tariff_name)
    if not os.path.exists(tariff_config_path):
        print(f"❌ 电价配置文件不存在: {tariff_config_path}")
        return {"status": "failed", "error": f"电价配置文件不存在: {tariff_config_path}"}

    try:
        # 对于TOU_D，需要处理季节性
        if tariff_name == "TOU_D":
            results = {}

            # 生成夏季空间
            print(f"\n🌞 生成夏季工作空间...")
            summer_result = process_house_season(house_id, tariff_name, "summer", tariff_config_path, constraints_path)
            results["summer"] = summer_result

            # 生成冬季空间
            print(f"\n❄️ 生成冬季工作空间...")
            winter_result = process_house_season(house_id, tariff_name, "winter", tariff_config_path, constraints_path)
            results["winter"] = winter_result

            return {
                "status": "success",
                "mode": "single_house",
                "house_id": house_id,
                "tariff_name": tariff_name,
                "seasonal_results": results
            }
        else:
            # 其他电价方案
            result = process_house_season(house_id, tariff_name, None, tariff_config_path, constraints_path)
            return {
                "status": result["status"],
                "mode": "single_house",
                "house_id": house_id,
                "tariff_name": tariff_name,
                "result": result
            }

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

def process_batch_houses(house_list: List[str] = None, tariff_name: str = "Economy_7") -> Dict:
    """批处理多个houses"""

    if house_list is None:
        house_list = get_all_available_houses()

    print(f"🏠 批处理模式: {len(house_list)} 个houses")
    print(f"📋 电价方案: {tariff_name}")
    print(f"🏘️ Houses: {', '.join(house_list)}")

    results = {}
    successful_count = 0
    failed_count = 0

    for i, house_id in enumerate(house_list, 1):
        print(f"\n[{i}/{len(house_list)}] 处理 {house_id}...")

        try:
            # 检查约束文件是否存在
            constraints_path = f"output/04_user_constraints/{house_id}/appliance_constraints_revise_by_llm.json"
            if not os.path.exists(constraints_path):
                print(f"❌ 约束文件不存在: {constraints_path}")
                results[house_id] = {"status": "failed", "error": f"约束文件不存在: {constraints_path}"}
                failed_count += 1
                continue

            # 获取电价配置路径
            tariff_config_path = get_tariff_config_path(tariff_name)
            if not os.path.exists(tariff_config_path):
                print(f"❌ 电价配置文件不存在: {tariff_config_path}")
                results[house_id] = {"status": "failed", "error": f"电价配置文件不存在: {tariff_config_path}"}
                failed_count += 1
                continue

            if tariff_name == "TOU_D":
                # TOU_D需要处理季节性
                house_results = {}

                # 夏季
                summer_result = process_house_season(house_id, tariff_name, "summer", tariff_config_path, constraints_path)
                house_results["summer"] = summer_result

                # 冬季
                winter_result = process_house_season(house_id, tariff_name, "winter", tariff_config_path, constraints_path)
                house_results["winter"] = winter_result

                results[house_id] = {
                    "status": "success",
                    "seasonal_results": house_results
                }
                successful_count += 1
            else:
                # 其他电价方案
                result = process_house_season(house_id, tariff_name, None, tariff_config_path, constraints_path)
                results[house_id] = result

                if result["status"] == "success":
                    successful_count += 1
                else:
                    failed_count += 1

            print(f"✅ {house_id} 处理完成")

        except Exception as e:
            print(f"❌ {house_id} 处理失败: {e}")
            results[house_id] = {"status": "failed", "error": str(e)}
            failed_count += 1

    print(f"\n📊 批处理统计:")
    print(f"   ✅ 成功: {successful_count}")
    print(f"   ❌ 失败: {failed_count}")
    print(f"   📈 成功率: {successful_count/(successful_count+failed_count)*100:.1f}%")

    return {
        "status": "success",
        "mode": "batch_houses",
        "tariff_name": tariff_name,
        "total_houses": len(house_list),
        "successful_count": successful_count,
        "failed_count": failed_count,
        "results": results
    }

def main():
    """主函数：交互式执行"""
    print("🚀 P051 电器工作空间生成器")
    print("=" * 60)
    print("功能：为每种电器构建具有迁移价值等级的可运行区间文件")
    print()

    try:
        # 选择处理模式
        print("📋 处理模式:")
        print("1. 单用户处理")
        print("2. 批处理")
        print("3. 原始功能（生成Economy_7和Economy_10）")
        print()

        try:
            mode_choice = input("选择模式 (1-3) [默认: 1]: ").strip()
            if not mode_choice:
                mode_choice = "1"
        except (EOFError, KeyboardInterrupt):
            print("使用默认模式: 1")
            mode_choice = "1"

        if mode_choice == "3":
            # 原始功能
            print("\n🔄 运行原始功能...")
            run_generate_appliance_spaces()
            return

        # 选择电价方案
        print("\n📋 电价方案:")
        print("1. UK (Economy_7 + Economy_10)")
        print("2. TOU_D (California, 季节性)")
        print("3. Germany_Variable (Germany)")
        print()

        try:
            tariff_choice = input("选择电价方案 (1-3) [默认: 1]: ").strip()
            if not tariff_choice:
                tariff_choice = "1"
        except (EOFError, KeyboardInterrupt):
            print("使用默认电价方案: 1")
            tariff_choice = "1"

        tariff_mapping = {
            "1": ["Economy_7", "Economy_10"],  # UK包含两个方案
            "2": ["TOU_D"],
            "3": ["Germany_Variable"]
        }

        tariff_list = tariff_mapping.get(tariff_choice, ["Economy_7"])

        if mode_choice == "1":
            # 单用户处理
            print("\n🏠 单用户处理")
            print("-" * 40)

            house_id = input("输入house ID [默认: house1]: ").strip()
            if not house_id:
                house_id = "house1"
            else:
                # 确保house ID格式正确
                if house_id.isdigit():
                    house_id = f"house{house_id}"
                elif not house_id.startswith("house"):
                    house_id = f"house{house_id}"

            # 处理多个电价方案
            all_results = {}
            for tariff_name in tariff_list:
                print(f"\n🔄 处理 {house_id} - {tariff_name}...")
                result = process_single_house(house_id, tariff_name)
                all_results[tariff_name] = result

                if result["status"] == "success":
                    print(f"✅ {tariff_name} 处理完成!")
                    if "seasonal_results" in result:
                        print("📊 季节性结果:")
                        for season, season_result in result["seasonal_results"].items():
                            if season_result["status"] == "success":
                                print(f"   {season}: ✅ 成功")
                            else:
                                print(f"   {season}: ❌ 失败")
                    else:
                        print("📊 处理结果: ✅ 成功")
                else:
                    print(f"❌ {tariff_name} 处理失败: {result.get('error', '未知错误')}")

            # 总结
            successful_tariffs = [t for t, r in all_results.items() if r["status"] == "success"]
            print(f"\n📊 单用户处理总结:")
            print(f"   成功的电价方案: {len(successful_tariffs)}/{len(tariff_list)}")
            print(f"   成功方案: {', '.join(successful_tariffs)}")

        elif mode_choice == "2":
            # 批处理
            print("\n🏠 批处理")
            print("-" * 40)

            # 获取可用houses
            all_houses = get_all_available_houses()
            print(f"可用houses: {len(all_houses)} 个 ({', '.join(all_houses)})")

            house_input = input(f"输入house IDs (逗号分隔) [默认: 全部 {len(all_houses)} 个]: ").strip()
            if not house_input:
                house_list = all_houses
            else:
                # 处理用户输入，确保格式正确
                raw_list = [h.strip() for h in house_input.split(",")]
                house_list = []
                for h in raw_list:
                    # 如果输入的是纯数字，转换为 houseN 格式
                    if h.isdigit():
                        house_list.append(f"house{h}")
                    # 如果已经是 houseN 格式，直接使用
                    elif h.startswith("house"):
                        house_list.append(h)
                    # 其他格式，尝试添加 house 前缀
                    else:
                        house_list.append(f"house{h}")

            # 处理多个电价方案
            all_results = {}
            for tariff_name in tariff_list:
                print(f"\n🔄 批处理 {len(house_list)} 个houses - {tariff_name}...")
                result = process_batch_houses(house_list, tariff_name)
                all_results[tariff_name] = result

                if result["status"] == "success":
                    print(f"✅ {tariff_name} 批处理完成!")
                    print(f"📊 统计: {result['successful_count']}/{result['total_houses']} 成功")
                else:
                    print(f"❌ {tariff_name} 批处理失败")

            # 总结
            successful_tariffs = [t for t, r in all_results.items() if r["status"] == "success"]
            print(f"\n📊 批处理总结:")
            print(f"   成功的电价方案: {len(successful_tariffs)}/{len(tariff_list)}")
            print(f"   成功方案: {', '.join(successful_tariffs)}")

        else:
            print("❌ 无效的模式选择")

    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
