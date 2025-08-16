#!/usr/bin/env python3
"""
修正的Gurobi优化系统
正确计算功率和费用，正确处理设备关联性
"""

import pandas as pd
import json
import gurobipy as gp
from gurobipy import GRB
from datetime import datetime, timedelta, time
import os
import glob
from typing import Dict, List, Tuple
import numpy as np
import logging
import time as time_module

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CorrectedOptimizationSystem:
    def __init__(self, tariff_config_path: str):
        """
        初始化修正的优化系统
        
        Args:
            tariff_config_path: 电价配置文件路径
        """
        # 加载并解析电价配置
        with open(tariff_config_path, 'r') as f:
            self.tariff_config = json.load(f)

        # 解析tariff_config.json为内部使用格式
        self.tariff_rates = self._parse_tariff_config()

        logger.info("电价配置解析完成:")
        for tariff_name, config in self.tariff_rates.items():
            total_hours = sum(end - start for start, end in config["low_periods"]) / 60
            logger.info(f"  {tariff_name}: {total_hours:.1f}小时低价时段, £{config['low_rate']}/£{config['high_rate']}")
        
        # 用户约束配置
        self.forbidden_appliances = ["Washing Machine", "Tumble Dryer", "Dishwasher"]
        self.forbidden_start_minute = 23 * 60 + 30  # 23:30
        self.forbidden_end_minute = 6 * 60          # 06:00
        self.completion_deadline_hours = 38         # 次日14:00 (38:00)
        self.min_duration_minutes = 5              # 最小持续时间
        
        # 时间配置 - 分钟级精度
        self.time_horizon_hours = 48  # 48小时窗口
        
        logger.info("修正优化系统初始化完成")

    def _parse_tariff_config(self) -> dict:
        """解析tariff_config.json为内部使用的格式"""
        parsed_rates = {}

        for tariff_name, config in self.tariff_config.items():
            if config.get("type") == "time_based":
                # 分析所有时段的费率
                all_rates = [period["rate"] for period in config["periods"]]
                unique_rates = sorted(set(all_rates))

                # 假设最低费率是低价时段，最高费率是高价时段
                low_rate = min(unique_rates)
                high_rate = max(unique_rates)

                # 找出所有低价时段
                low_periods = []
                for period in config["periods"]:
                    if period["rate"] == low_rate:
                        start_minutes = self._time_to_minutes(period["start"])
                        end_minutes = self._time_to_minutes(period["end"])

                        # 处理跨天的时间段 (如 22:00 到 01:00)
                        if end_minutes <= start_minutes:
                            # 跨天情况：分成两段
                            low_periods.append((start_minutes, 1440))  # 到当天结束
                            low_periods.append((0, end_minutes))       # 从第二天开始
                        else:
                            low_periods.append((start_minutes, end_minutes))

                parsed_rates[tariff_name] = {
                    "low_periods": low_periods,
                    "low_rate": low_rate,
                    "high_rate": high_rate
                }

            elif config.get("type") == "flat":
                # 平价电价
                parsed_rates[tariff_name] = {
                    "low_periods": [],
                    "low_rate": config["rate"],
                    "high_rate": config["rate"]
                }

        return parsed_rates

    def _time_to_minutes(self, time_str: str) -> int:
        """将时间字符串转换为当天的分钟数"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

    def load_power_data(self, house_id: str) -> pd.DataFrame:
        """加载房屋的瞬时功率数据"""
        # 从当前工作目录向上找到项目根目录
        current_dir = os.getcwd()
        while not os.path.exists(os.path.join(current_dir, "output", "01_preprocessed")):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # 到达根目录
                break
            current_dir = parent_dir

        power_file = os.path.join(current_dir, "output", "01_preprocessed", house_id, f"01_perception_alignment_result_{house_id}.csv")
        
        if not os.path.exists(power_file):
            raise FileNotFoundError(f"功率数据文件不存在: {power_file}")
        
        power_df = pd.read_csv(power_file)
        power_df['Time'] = pd.to_datetime(power_df['Time'])

        # 保持宽格式，在查询时动态转换
        appliance_columns = [col for col in power_df.columns if col.startswith('Appliance')]

        logger.info(f"加载功率数据: {house_id}, {len(power_df)} 条时间记录, {len(appliance_columns)} 个设备")
        return power_df
    
    def get_event_power_profile(self, event: pd.Series, power_df: pd.DataFrame) -> List[Tuple[datetime, float]]:
        """获取事件的真实功率曲线"""
        start_time = event['start_time']
        end_time = event['end_time']
        appliance_id_str = event['appliance_id']

        # 将appliance_id从字符串转换为数字 (如 "Appliance4" -> 4)
        if isinstance(appliance_id_str, str) and appliance_id_str.startswith('Appliance'):
            appliance_id = int(appliance_id_str.replace('Appliance', ''))
        else:
            appliance_id = appliance_id_str

        # 筛选时间范围的功率数据
        mask = (power_df['Time'] >= start_time) & (power_df['Time'] < end_time)
        event_power = power_df[mask].copy()
        event_power = event_power.sort_values('Time')

        # 从宽格式中提取指定设备的功率数据
        appliance_col = f'Appliance{appliance_id}'
        if appliance_col not in power_df.columns:
            logger.warning(f"设备列 {appliance_col} 不存在")
            return []

        power_profile = []
        for _, row in event_power.iterrows():
            power_w = row[appliance_col]
            power_profile.append((row['Time'], power_w))
        
        return power_profile
    
    def calculate_event_cost(self, power_profile: List[Tuple[datetime, float]], tariff_type: str) -> float:
        """根据功率曲线计算事件成本"""
        total_cost = 0.0

        for timestamp, power_w in power_profile:
            # 获取该时刻的电价
            minute_of_day = timestamp.hour * 60 + timestamp.minute
            rate = self._get_rate_at_minute(minute_of_day, tariff_type)

            # 计算该分钟的成本：瞬时功率W * 1分钟 / 60分钟 / 1000 = kWh
            # 这里直接使用瞬时功率，不计算平均值
            energy_kwh = power_w / 60 / 1000  # 该分钟的实际能耗
            minute_cost = energy_kwh * rate
            total_cost += minute_cost

        return total_cost
    
    def calculate_shifted_event_cost(self, power_profile: List[Tuple[datetime, float]], 
                                   new_start_time: datetime, tariff_type: str) -> float:
        """计算迁移后事件的成本"""
        if not power_profile:
            return 0.0
        
        # 计算时间偏移
        original_start = power_profile[0][0]
        time_shift = new_start_time - original_start
        
        total_cost = 0.0
        
        for original_timestamp, power_w in power_profile:
            # 计算迁移后的时间
            new_timestamp = original_timestamp + time_shift
            
            # 获取新时间的电价
            minute_of_day = new_timestamp.hour * 60 + new_timestamp.minute
            rate = self._get_rate_at_minute(minute_of_day, tariff_type)
            
            # 计算该分钟的成本
            energy_kwh = power_w / 60 / 1000
            minute_cost = energy_kwh * rate
            total_cost += minute_cost
        
        return total_cost
    
    def _get_rate_at_minute(self, minute_of_day: int, tariff_type: str) -> float:
        """获取指定分钟的电价费率"""
        if tariff_type not in self.tariff_rates:
            return 0.30  # 默认费率
        
        config = self.tariff_rates[tariff_type]
        
        # 检查是否在低价时段
        for start_min, end_min in config["low_periods"]:
            if start_min <= minute_of_day < end_min:
                return config["low_rate"]
        
        return config["high_rate"]
    
    def _is_forbidden_minute(self, minute_of_day: int, appliance_name: str) -> bool:
        """检查指定分钟对指定电器是否为禁止时段"""
        if appliance_name not in self.forbidden_appliances:
            return False
        
        # 23:30-06:00 (次日) 为禁止时段
        if minute_of_day >= self.forbidden_start_minute or minute_of_day < self.forbidden_end_minute:
            return True
        
        return False
    
    def _is_valid_scheduling_time(self, new_start_time: datetime, duration_min: int, 
                                 appliance_name: str, original_start_time: datetime) -> bool:
        """检查调度时间是否满足所有约束"""
        new_end_time = new_start_time + timedelta(minutes=duration_min)
        
        # 约束1: 不能在原始事件之前开始
        if new_start_time < original_start_time:
            return False
        
        # 约束2: 必须在38小时内完成
        original_date = original_start_time.date()
        deadline = datetime.combine(original_date, time(0, 0)) + timedelta(hours=self.completion_deadline_hours)
        if new_end_time > deadline:
            return False
        
        # 约束3: 检查禁止时段（如果适用）
        if appliance_name in self.forbidden_appliances:
            current_time = new_start_time
            while current_time < new_end_time:
                minute_of_day = current_time.hour * 60 + current_time.minute
                if self._is_forbidden_minute(minute_of_day, appliance_name):
                    return False
                current_time += timedelta(minutes=1)
        
        return True
    
    def optimize_single_file(self, csv_file: str, house_id: str, tariff_type: str) -> Dict:
        """优化单个文件的所有可调度事件"""
        # 开始计时
        optimization_start_time = time_module.time()
        logger.info(f"🚀 开始优化: {house_id} ({tariff_type}) - 开始时间: {datetime.now().strftime('%H:%M:%S')}")

        try:
            # 数据加载阶段
            data_loading_start = time_module.time()

            # 加载事件数据
            events_df = pd.read_csv(csv_file)
            events_df['start_time'] = pd.to_datetime(events_df['start_time'])
            events_df['end_time'] = pd.to_datetime(events_df['end_time'])

            # 加载功率数据
            power_df = self.load_power_data(house_id)

            data_loading_time = time_module.time() - data_loading_start
            
            # 过滤可调度事件
            reschedulable_df = events_df[
                (events_df['is_reschedulable'] == True) &
                (events_df['duration(min)'] >= self.min_duration_minutes)
            ].copy().reset_index(drop=True)
            
            if len(reschedulable_df) == 0:
                logger.warning(f"文件 {csv_file} 没有可调度事件")
                return {"status": "no_events", "file": csv_file}
            
            logger.info(f"📊 数据加载完成: {len(reschedulable_df)} 个可调度事件 (耗时: {data_loading_time:.2f}s)")

            # 功率曲线计算阶段
            power_calculation_start = time_module.time()
            events_with_power = []
            total_original_cost = 0.0
            
            for idx, event in reschedulable_df.iterrows():
                try:
                    power_profile = self.get_event_power_profile(event, power_df)
                    if not power_profile:
                        logger.warning(f"事件 {event['event_id']} 没有找到功率数据")
                        continue
                    
                    original_cost = self.calculate_event_cost(power_profile, tariff_type)
                    total_original_cost += original_cost
                    
                    events_with_power.append({
                        'event_data': event,
                        'power_profile': power_profile,
                        'original_cost': original_cost
                    })
                    
                except Exception as e:
                    logger.warning(f"处理事件 {event['event_id']} 时出错: {e}")
                    continue
            
            if not events_with_power:
                return {"status": "no_valid_events", "file": csv_file}

            power_calculation_time = time_module.time() - power_calculation_start
            logger.info(f"⚡ 功率曲线计算完成: {len(events_with_power)} 个事件，原始总成本: ${total_original_cost:.6f} (耗时: {power_calculation_time:.2f}s)")

            # 优化阶段
            optimization_phase_start = time_module.time()
            optimization_results = self._optimize_by_groups(events_with_power, tariff_type)
            optimization_phase_time = time_module.time() - optimization_phase_start

            logger.info(f"🎯 事件优化完成: {len(optimization_results)} 个事件被优化 (耗时: {optimization_phase_time:.2f}s)")

            # 结果保存阶段
            save_start = time_module.time()
            self._save_optimization_results(optimization_results, house_id, tariff_type, total_original_cost)
            save_time = time_module.time() - save_start
            
            # 计算总优化成本
            total_optimized_cost = sum(result['optimized_cost'] for result in optimization_results)
            total_savings = total_original_cost - total_optimized_cost

            # 计算总时间
            total_optimization_time = time_module.time() - optimization_start_time

            # 时间统计
            timing_stats = {
                "data_loading_time_seconds": round(data_loading_time, 3),
                "power_calculation_time_seconds": round(power_calculation_time, 3),
                "optimization_phase_time_seconds": round(optimization_phase_time, 3),
                "save_time_seconds": round(save_time, 3),
                "total_optimization_time_seconds": round(total_optimization_time, 3),
                "data_loading_time_formatted": f"{data_loading_time:.2f}s",
                "power_calculation_time_formatted": f"{power_calculation_time:.2f}s",
                "optimization_phase_time_formatted": f"{optimization_phase_time:.2f}s",
                "save_time_formatted": f"{save_time:.2f}s",
                "total_optimization_time_formatted": f"{total_optimization_time:.2f}s"
            }

            result = {
                "status": "success",
                "file": csv_file,
                "house_id": house_id,
                "tariff_type": tariff_type,
                "total_events": len(events_with_power),
                "original_cost": total_original_cost,
                "optimized_cost": total_optimized_cost,
                "total_savings": total_savings,
                "savings_percentage": (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0,
                "timing_stats": timing_stats,
                "optimization_results": optimization_results
            }

            logger.info(f"✅ 优化完成 {house_id} ({tariff_type}): 节约 ${total_savings:.6f} ({result['savings_percentage']:.2f}%)")
            logger.info(f"⏱️ 总耗时: {total_optimization_time:.2f}s (数据加载: {data_loading_time:.2f}s, 功率计算: {power_calculation_time:.2f}s, 优化: {optimization_phase_time:.2f}s, 保存: {save_time:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"优化文件 {csv_file} 时出错: {e}")
            return {
                "status": "error",
                "file": csv_file,
                "error": str(e)
            }
    
    def _optimize_by_groups(self, events_with_power: List[Dict], tariff_type: str) -> List[Dict]:
        """按电器分组进行优化，确保同一电器的所有事件在一个组内处理"""
        optimization_results = []

        # 只按电器分组，不按日期分组，避免跨日期迁移导致的重叠问题
        appliance_groups = {}
        for event_info in events_with_power:
            event = event_info['event_data']
            appliance = event['appliance_name']

            if appliance not in appliance_groups:
                appliance_groups[appliance] = []
            appliance_groups[appliance].append(event_info)

        logger.info(f"分组优化: {len(appliance_groups)} 个电器组")

        # 对每个电器组进行优化
        for appliance, group_events in appliance_groups.items():
            logger.info(f"优化电器组: {appliance} ({len(group_events)} 个事件)")

            # 使用贪心算法优化，确保同一电器的所有事件不重叠
            group_results = self._greedy_optimize_appliance_group(group_events, tariff_type)
            optimization_results.extend(group_results)

        return optimization_results

    def _greedy_optimize_appliance_group(self, group_events: List[Dict], tariff_type: str) -> List[Dict]:
        """优化单个电器的所有事件，确保全局非重叠"""
        results = []
        scheduled_intervals = []  # 全局已调度时间区间

        # 按原始开始时间排序
        sorted_events = sorted(group_events, key=lambda x: x['event_data']['start_time'])

        for event_info in sorted_events:
            event = event_info['event_data']
            power_profile = event_info['power_profile']
            original_cost = event_info['original_cost']
            duration_min = int(event['duration(min)'])

            # 寻找最优的调度时间
            best_start_time = event['start_time']  # 默认保持原时间
            best_cost = original_cost

            # 搜索48小时内的所有可能时间点（每15分钟一个）
            search_start = event['start_time']
            search_end = search_start + timedelta(hours=self.time_horizon_hours)

            current_time = search_start
            while current_time <= search_end:
                if self._is_valid_scheduling_time(
                    current_time,
                    duration_min,
                    event['appliance_name'],
                    event['start_time']
                ):
                    # 检查是否与已调度的事件重叠（全局检查）
                    candidate_end = current_time + timedelta(minutes=duration_min)
                    if not self._has_overlap_with_scheduled(current_time, candidate_end, scheduled_intervals):
                        # 计算在这个时间的成本
                        shifted_cost = self.calculate_shifted_event_cost(power_profile, current_time, tariff_type)

                        if shifted_cost < best_cost:
                            best_cost = shifted_cost
                            best_start_time = current_time

                # 每15分钟检查一次
                current_time += timedelta(minutes=15)

            # 计算优化后的结束时间
            best_end_time = best_start_time + timedelta(minutes=duration_min)

            # 将选定的时间区间添加到全局已调度列表
            scheduled_intervals.append((best_start_time, best_end_time))

            results.append({
                'event_id': event['event_id'],
                'appliance_name': event['appliance_name'],
                'appliance_id': event['appliance_id'],
                'original_start': event['start_time'],
                'original_end': event['end_time'],
                'optimized_start': best_start_time,
                'optimized_end': best_end_time,
                'duration_minutes': duration_min,
                'original_cost': original_cost,
                'optimized_cost': best_cost,
                'cost_savings': original_cost - best_cost,
                'savings_percentage': ((original_cost - best_cost) / original_cost * 100) if original_cost > 0 else 0,
                'time_shift_hours': (best_start_time - event['start_time']).total_seconds() / 3600,
                'power_profile_length': len(power_profile)
            })

        return results

    def _greedy_optimize_group(self, group_events: List[Dict], tariff_type: str) -> List[Dict]:
        """使用贪心算法优化一组事件，确保同一电器的事件不重叠"""
        results = []
        scheduled_intervals = []  # 记录已调度的时间区间

        # 按原始开始时间排序，保持事件顺序
        sorted_events = sorted(group_events, key=lambda x: x['event_data']['start_time'])

        for event_info in sorted_events:
            event = event_info['event_data']
            power_profile = event_info['power_profile']
            original_cost = event_info['original_cost']
            duration_min = int(event['duration(min)'])

            # 寻找最优的调度时间
            best_start_time = event['start_time']  # 默认保持原时间
            best_cost = original_cost

            # 搜索48小时内的所有可能时间点（每15分钟一个）
            search_start = event['start_time']
            search_end = search_start + timedelta(hours=self.time_horizon_hours)

            current_time = search_start
            while current_time <= search_end:
                if self._is_valid_scheduling_time(
                    current_time,
                    duration_min,
                    event['appliance_name'],
                    event['start_time']
                ):
                    # 检查是否与已调度的事件重叠
                    candidate_end = current_time + timedelta(minutes=duration_min)
                    if not self._has_overlap_with_scheduled(current_time, candidate_end, scheduled_intervals):
                        # 计算在这个时间的成本
                        shifted_cost = self.calculate_shifted_event_cost(power_profile, current_time, tariff_type)

                        if shifted_cost < best_cost:
                            best_cost = shifted_cost
                            best_start_time = current_time

                # 每15分钟检查一次
                current_time += timedelta(minutes=15)
            
            # 计算优化后的结束时间
            best_end_time = best_start_time + timedelta(minutes=duration_min)

            # 将选定的时间区间添加到已调度列表
            scheduled_intervals.append((best_start_time, best_end_time))

            results.append({
                'event_id': event['event_id'],
                'appliance_name': event['appliance_name'],
                'appliance_id': event['appliance_id'],
                'original_start': event['start_time'],
                'original_end': event['end_time'],
                'optimized_start': best_start_time,
                'optimized_end': best_end_time,
                'duration_minutes': int(event['duration(min)']),
                'original_cost': original_cost,
                'optimized_cost': best_cost,
                'cost_savings': original_cost - best_cost,
                'savings_percentage': ((original_cost - best_cost) / original_cost * 100) if original_cost > 0 else 0,
                'time_shift_hours': (best_start_time - event['start_time']).total_seconds() / 3600,
                'power_profile_length': len(power_profile)
            })
        
        return results

    def _has_overlap_with_scheduled(self, start_time: datetime, end_time: datetime,
                                   scheduled_intervals: List[Tuple[datetime, datetime]]) -> bool:
        """检查时间区间是否与已调度的区间重叠"""
        for scheduled_start, scheduled_end in scheduled_intervals:
            # 检查重叠：新区间开始时间 < 已调度结束时间 AND 新区间结束时间 > 已调度开始时间
            if start_time < scheduled_end and end_time > scheduled_start:
                return True
        return False

    def _save_optimization_results(self, optimization_results: List[Dict], house_id: str, tariff_type: str, original_cost: float):
        """保存优化结果到CSV文件"""
        # 创建输出目录结构 - 使用相对路径
        output_base = "./results"
        output_dir = os.path.join(output_base, tariff_type, house_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # 准备CSV数据
        csv_data = []
        for result in optimization_results:
            csv_data.append({
                'event_id': result['event_id'],
                'appliance_name': result['appliance_name'],
                'appliance_id': result['appliance_id'],
                'original_start_time': result['original_start'].strftime('%Y-%m-%d %H:%M:%S'),
                'original_end_time': result['original_end'].strftime('%Y-%m-%d %H:%M:%S'),
                'optimized_start_time': result['optimized_start'].strftime('%Y-%m-%d %H:%M:%S'),
                'optimized_end_time': result['optimized_end'].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': result['duration_minutes'],
                'original_cost': result['original_cost'],
                'optimized_cost': result['optimized_cost'],
                'cost_savings': result['cost_savings'],
                'savings_percentage': result['savings_percentage'],
                'time_shift_hours': result['time_shift_hours'],
                'power_profile_points': result['power_profile_length']
            })
        
        # 保存CSV文件
        csv_file = os.path.join(output_dir, f"optimization_results_{house_id}_{tariff_type}.csv")
        csv_df = pd.DataFrame(csv_data)
        csv_df.to_csv(csv_file, index=False)
        
        # 保存汇总信息
        summary = {
            'house_id': house_id,
            'tariff_type': tariff_type,
            'total_events': len(optimization_results),
            'total_original_cost': original_cost,
            'total_optimized_cost': sum(r['optimized_cost'] for r in optimization_results),
            'total_savings': sum(r['cost_savings'] for r in optimization_results),
            'average_savings_percentage': np.mean([r['savings_percentage'] for r in optimization_results]),
            'optimization_timestamp': datetime.now().isoformat()
        }
        
        summary_file = os.path.join(output_dir, f"optimization_summary_{house_id}_{tariff_type}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"结果已保存: {csv_file}")
        logger.info(f"汇总已保存: {summary_file}")
    
    def get_all_csv_files(self, data_dir: str) -> List[Tuple[str, str, str]]:
        """获取所有CSV文件路径"""
        csv_files = []
        
        for tariff_type in ["Economy_7", "Economy_10"]:
            tariff_dir = os.path.join(data_dir, tariff_type)
            if not os.path.exists(tariff_dir):
                continue
            
            house_dirs = glob.glob(os.path.join(tariff_dir, "house*"))
            for house_dir in house_dirs:
                house_id = os.path.basename(house_dir)
                csv_pattern = os.path.join(house_dir, f"tou_filtered_{house_id}_{tariff_type}.csv")
                csv_files_found = glob.glob(csv_pattern)
                
                for csv_file in csv_files_found:
                    csv_files.append((csv_file, house_id, tariff_type))
        
        logger.info(f"找到 {len(csv_files)} 个CSV文件")
        return csv_files
    
    def process_all_files(self, data_dir: str):
        """处理所有文件"""
        logger.info("开始处理所有文件...")
        
        csv_files = self.get_all_csv_files(data_dir)
        if not csv_files:
            logger.error("没有找到CSV文件")
            return
        
        all_results = []
        for csv_file, house_id, tariff_type in csv_files:
            result = self.optimize_single_file(csv_file, house_id, tariff_type)
            all_results.append(result)
        
        # 保存总体汇总
        self._save_overall_summary(all_results)
        logger.info("所有文件处理完成")
    
    def _save_overall_summary(self, all_results: List[Dict]):
        """保存总体汇总结果"""
        successful_results = [r for r in all_results if r.get("status") == "success"]
        
        if successful_results:
            summary_stats = {
                "total_files_processed": len(all_results),
                "successful_optimizations": len(successful_results),
                "total_events_optimized": sum(r["total_events"] for r in successful_results),
                "total_original_cost": sum(r["original_cost"] for r in successful_results),
                "total_optimized_cost": sum(r["optimized_cost"] for r in successful_results),
                "total_savings": sum(r["total_savings"] for r in successful_results),
                "average_savings_percentage": np.mean([r["savings_percentage"] for r in successful_results])
            }
            
            output_dir = "./results"
            os.makedirs(output_dir, exist_ok=True)

            summary_file = os.path.join(output_dir, "overall_optimization_summary.json")
            with open(summary_file, 'w') as f:
                json.dump(summary_stats, f, indent=2)
            
            logger.info(f"总体汇总已保存: {summary_file}")
            logger.info(f"总计处理 {summary_stats['total_events_optimized']} 个事件")
            logger.info(f"总节约: ${summary_stats['total_savings']:.2f} ({summary_stats['average_savings_percentage']:.2f}%)")


def main():
    """主函数"""
    print("🚀 修正的Gurobi优化系统")
    print("=" * 80)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tariff_config = os.path.join(base_dir, "tariff_config.json")
    data_dir = os.path.join(os.path.dirname(base_dir), "flterted_data")
    
    optimizer = CorrectedOptimizationSystem(tariff_config)
    optimizer.process_all_files(data_dir)
    
    print("\n🎉 修正优化系统运行完成!")


if __name__ == "__main__":
    main()
