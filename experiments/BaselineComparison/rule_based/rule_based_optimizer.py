#!/usr/bin/env python3
"""
基于规则的事件调度优化器
规则：只对每天每个电器的第一个事件进行优化调度，其他事件保持原时间
"""

import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class RuleBasedOptimizer:
    def __init__(self, events_file: str, global_spaces_file: str, tariff_name: str = "Economy_7"):
        """
        初始化基于规则的优化器
        
        Args:
            events_file: 事件CSV文件路径
            global_spaces_file: 全局调度空间JSON文件路径
            tariff_name: 电价方案名称
        """
        # 加载事件数据
        self.events_df = pd.read_csv(events_file)
        if 'is_reschedulable' in self.events_df.columns:
            self.reschedulable_events = self.events_df[
                self.events_df['is_reschedulable'] == True
            ].copy()
        else:
            self.reschedulable_events = self.events_df.copy()
        
        # 加载全局调度空间
        try:
            with open(global_spaces_file, 'r') as f:
                self.global_spaces = json.load(f)
            print(f"调度空间文件加载成功: {global_spaces_file}")
        except Exception as e:
            print(f"加载调度空间文件失败: {e}")
            self.global_spaces = {}

        self.tariff_name = tariff_name

        # 电价费率
        if tariff_name == "Economy_7":
            self.low_rate = 0.15
            self.high_rate = 0.30
        elif tariff_name == "Economy_10":
            self.low_rate = 0.13
            self.high_rate = 0.33
        else:
            self.low_rate = 0.15
            self.high_rate = 0.30

        print(f"加载了 {len(self.reschedulable_events)} 个可重新调度的事件")
        print(f"使用电价方案: {tariff_name}")
        print(f"可用电器调度空间: {list(self.global_spaces.keys())}")

        # 调试信息：显示调度空间内容
        if self.global_spaces:
            for appliance, space in list(self.global_spaces.items())[:2]:  # 只显示前2个
                print(f"  {appliance}: {len(space.get('optimal_windows', []))} 优质窗口, {len(space.get('suboptimal_windows', []))} 次优窗口")
        else:
            print("  警告: 调度空间为空，请检查调度空间文件是否正确生成")
    
    def _extract_event_info(self, event_id: str) -> Tuple[str, str, str]:
        """从event_id中提取电器名称、日期和序号"""
        pattern = r'(.+)_(\d{4}-\d{2}-\d{2})_(\d+)'
        match = re.match(pattern, event_id)
        
        if match:
            appliance_name = match.group(1)
            date = match.group(2)
            sequence_number = match.group(3)
            return appliance_name, date, sequence_number
        else:
            parts = event_id.split('_')
            if len(parts) >= 3:
                appliance_name = '_'.join(parts[:-2])
                date = parts[-2]
                sequence_number = parts[-1]
                return appliance_name, date, sequence_number
            else:
                return event_id, "unknown", "01"
    
    def _identify_first_events_per_day(self) -> List[int]:
        """识别每天每个电器的第一个事件"""
        first_events = []
        
        # 按电器和日期分组
        groups = {}
        
        for idx, row in self.reschedulable_events.iterrows():
            appliance_name, date, sequence_number = self._extract_event_info(row['event_id'])
            group_key = f"{appliance_name}_{date}"
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append((idx, sequence_number))
        
        # 对每个组按序号排序，取第一个
        for group_key, events in groups.items():
            # 按序号排序
            events.sort(key=lambda x: x[1])
            first_event_idx = events[0][0]  # 取第一个事件的索引
            first_events.append(first_event_idx)
        
        print(f"识别出 {len(first_events)} 个第一事件需要优化")
        print(f"总共 {len(groups)} 个电器-日期组合")
        
        return first_events
    
    def _time_48h_to_minutes(self, time_48h: str) -> int:
        """将48小时格式时间转换为分钟"""
        hours, minutes = map(int, time_48h.split(':'))
        return hours * 60 + minutes
    
    def _minutes_to_time_48h(self, minutes: int) -> str:
        """将分钟转换为48小时格式时间"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    def _datetime_to_minutes_48h(self, dt: datetime, base_date: datetime.date) -> int:
        """将datetime转换为48小时格式的分钟数"""
        event_date = dt.date()
        day_offset = (event_date - base_date).days
        
        if day_offset < 0:
            day_offset = 0
        elif day_offset > 1:
            day_offset = 1
        
        total_minutes = day_offset * 24 * 60 + dt.hour * 60 + dt.minute
        return total_minutes
    
    def _minutes_48h_to_datetime(self, minutes: int, base_date: datetime.date) -> datetime:
        """将48小时格式分钟数转换为datetime"""
        base_datetime = datetime.combine(base_date, datetime.min.time())
        return base_datetime + timedelta(minutes=minutes)
    
    def _find_best_scheduling_option(self, event_idx: int) -> Optional[Dict]:
        """为事件寻找最佳调度选项"""
        event = self.reschedulable_events.loc[event_idx]
        appliance_name = event['appliance_name']
        
        # 获取时间信息
        if 'start_time' in event:
            original_start = pd.to_datetime(event['start_time'])
            original_end = pd.to_datetime(event['end_time'])
        else:
            original_start = pd.to_datetime(event['original_start_time'])
            original_end = pd.to_datetime(event['original_end_time'])
        
        duration_minutes = int(event['duration(min)'])
        base_date = original_start.date()
        
        # 计算最早开始时间（原始开始时间+5分钟）
        original_start_48h = self._datetime_to_minutes_48h(original_start, base_date)
        earliest_start_48h = original_start_48h + 5
        
        # 检查电器调度空间
        if appliance_name not in self.global_spaces:
            return None
        
        appliance_space = self.global_spaces[appliance_name]
        
        # 首先尝试优质窗口
        for window in appliance_space.get('optimal_windows', []):
            window_start = self._time_48h_to_minutes(window['start_time_48h'])
            window_end = self._time_48h_to_minutes(window['end_time_48h'])
            
            # 应用最早开始时间约束
            effective_start = max(window_start, earliest_start_48h)
            
            # 检查是否有足够空间
            if effective_start + duration_minutes <= window_end:
                return {
                    'start_minutes': effective_start,
                    'end_minutes': effective_start + duration_minutes,
                    'window_type': 'optimal',
                    'price_rate': window['avg_price_rate'],
                    'base_date': base_date
                }
        
        # 如果优质窗口不可行，尝试次优窗口
        for window in appliance_space.get('suboptimal_windows', []):
            window_start = self._time_48h_to_minutes(window['start_time_48h'])
            window_end = self._time_48h_to_minutes(window['end_time_48h'])
            
            effective_start = max(window_start, earliest_start_48h)
            
            if effective_start + duration_minutes <= window_end:
                return {
                    'start_minutes': effective_start,
                    'end_minutes': effective_start + duration_minutes,
                    'window_type': 'suboptimal',
                    'price_rate': window['avg_price_rate'],
                    'base_date': base_date
                }
        
        return None
    
    def optimize_with_rules(self) -> pd.DataFrame:
        """使用基于规则的策略进行优化"""
        print("开始基于规则的事件优化...")
        
        # 识别需要优化的第一事件
        first_events = self._identify_first_events_per_day()
        
        # 创建结果DataFrame
        result_df = self.reschedulable_events.copy()
        result_df['shifted_start_time'] = ''
        result_df['shifted_end_time'] = ''
        result_df['shifted_start_datetime'] = ''
        result_df['shifted_end_datetime'] = ''
        result_df['tariff'] = self.tariff_name
        result_df['rate_type'] = 0.0
        result_df['estimated_cost'] = 0.0
        result_df['is_optimized'] = False  # 标记是否被优化
        
        successful_count = 0
        optimal_count = 0
        
        # 只优化第一事件
        for event_idx in first_events:
            event = self.reschedulable_events.loc[event_idx]
            
            # 寻找最佳调度选项
            best_option = self._find_best_scheduling_option(event_idx)
            
            if best_option:
                # 转换时间格式
                start_time_48h = self._minutes_to_time_48h(best_option['start_minutes'])
                end_time_48h = self._minutes_to_time_48h(best_option['end_minutes'])
                
                start_datetime = self._minutes_48h_to_datetime(
                    best_option['start_minutes'], 
                    best_option['base_date']
                )
                end_datetime = self._minutes_48h_to_datetime(
                    best_option['end_minutes'], 
                    best_option['base_date']
                )
                
                # 更新DataFrame
                result_df.at[event_idx, 'shifted_start_time'] = start_time_48h
                result_df.at[event_idx, 'shifted_end_time'] = end_time_48h
                result_df.at[event_idx, 'shifted_start_datetime'] = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                result_df.at[event_idx, 'shifted_end_datetime'] = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
                result_df.at[event_idx, 'is_optimized'] = True
                
                # 设置费率
                if best_option['window_type'] == 'optimal':
                    result_df.at[event_idx, 'rate_type'] = self.low_rate
                    optimal_count += 1
                else:
                    result_df.at[event_idx, 'rate_type'] = self.high_rate
                
                # 计算预估成本
                duration_minutes = int(result_df.at[event_idx, 'duration(min)'])
                energy_watts = result_df.at[event_idx, 'energy(W)']
                rate = result_df.at[event_idx, 'rate_type']
                estimated_cost = energy_watts * duration_minutes / 60 / 1000 * rate
                result_df.at[event_idx, 'estimated_cost'] = round(estimated_cost, 4)
                
                successful_count += 1
                
                print(f"优化成功: {event['event_id']} -> {start_time_48h}-{end_time_48h} ({best_option['window_type']})")
            else:
                event_id = self.reschedulable_events.loc[event_idx, 'event_id']
                print(f"优化失败: {event_id} - 无法找到合适的调度时间")
        
        # 打印结果统计
        total_first_events = len(first_events)
        print(f"\n基于规则的优化结果统计:")
        print(f"需要优化的第一事件: {total_first_events} 个")
        print(f"成功优化事件: {successful_count}/{total_first_events} ({successful_count/total_first_events:.1%})")
        print(f"优质窗口使用: {optimal_count}/{successful_count} ({optimal_count/successful_count:.1%})" if successful_count > 0 else "优质窗口使用: 0/0")
        
        return result_df

    def save_results(self, result_df: pd.DataFrame, output_file: str):
        """保存优化结果"""
        # 只保存被优化的事件（序号01的事件）
        optimized_events = result_df[result_df['is_optimized'] == True].copy()

        if len(optimized_events) == 0:
            print("没有成功优化的事件需要保存")
            return

        # 选择需要的列
        columns_to_save = [
            'event_id', 'appliance_name', 'original_start_time', 'original_end_time',
            'shifted_start_time', 'shifted_end_time', 'shifted_start_datetime', 'shifted_end_datetime',
            'duration(min)', 'energy(W)', 'tariff', 'rate_type', 'estimated_cost'
        ]

        # 处理列名差异
        if 'original_start_time' not in optimized_events.columns:
            if 'start_time' in optimized_events.columns:
                optimized_events['original_start_time'] = optimized_events['start_time']
                optimized_events['original_end_time'] = optimized_events['end_time']

        # 确保所有需要的列都存在
        available_columns = [col for col in columns_to_save if col in optimized_events.columns]
        output_df = optimized_events[available_columns].copy()

        # 保存到CSV
        output_df.to_csv(output_file, index=False)

        print(f"结果已保存到: {output_file}")
        print(f"成功优化的事件数: {len(output_df)}")

        # 统计信息
        total_cost = output_df['estimated_cost'].sum()
        optimal_events = len(output_df[output_df['rate_type'] == self.low_rate])

        print(f"优质窗口调度: {optimal_events} ({optimal_events/len(output_df):.1%})")
        print(f"总预估成本: ${total_cost:.2f}")


def main():
    """主函数"""
    # 检测当前工作目录并设置正确的路径
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")

    # 判断是否在rule_based目录中运行
    if current_dir.endswith('rule_based'):
        # 从rule_based目录运行
        base_path = '..'
        output_dir = 'output'
        spaces_dir = 'output'
    else:
        # 从项目根目录运行
        base_path = '.'
        output_dir = 'rule_based/output'
        spaces_dir = 'rule_based/output'

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    tariff_schemes = ["Economy_7", "Economy_10"]

    for tariff in tariff_schemes:
        try:
            print(f"\n{'='*80}")
            print(f"正在为 {tariff} 进行基于规则的事件优化调度")
            print(f"规则：只优化事件ID序号为01的事件")
            print(f"{'='*80}")

            # 文件路径
            events_file = os.path.join(base_path, 'output', '04_user_constraints', f'shiftable_event_masked_{tariff}.csv')

            # 先尝试使用gurobi的调度空间文件
            gurobi_spaces_file = os.path.join(base_path, 'gurobi', 'output', f'global_scheduling_spaces_shiftable_{tariff}.json')
            rule_spaces_file = os.path.join(spaces_dir, f'global_scheduling_spaces_shiftable_{tariff}.json')

            if os.path.exists(gurobi_spaces_file):
                spaces_file = gurobi_spaces_file
                print(f"使用gurobi调度空间文件: {spaces_file}")
            else:
                spaces_file = rule_spaces_file
                print(f"使用rule_based调度空间文件: {spaces_file}")

            output_file = os.path.join(output_dir, f'rule_based_{tariff}_optimized.csv')

            print(f"事件文件: {events_file}")
            print(f"调度空间文件: {spaces_file}")
            print(f"输出文件: {output_file}")

            # 检查文件是否存在
            if not os.path.exists(events_file):
                print(f"错误: 找不到事件文件: {events_file}")
                continue

            if not os.path.exists(spaces_file):
                print(f"错误: 找不到全局调度空间文件: {spaces_file}")
                print(f"请先运行: python rule_based/global_scheduling_space_builder.py")
                continue

            # 创建优化器
            optimizer = RuleBasedOptimizer(events_file, spaces_file, tariff)

            # 运行基于规则的优化
            result_df = optimizer.optimize_with_rules()

            # 保存结果
            optimizer.save_results(result_df, output_file)

        except Exception as e:
            print(f"处理 {tariff} 时出错: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n基于规则的优化完成!")
    print(f"结果已保存到 {output_dir} 目录")


if __name__ == "__main__":
    main()
