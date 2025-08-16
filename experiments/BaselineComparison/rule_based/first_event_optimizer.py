#!/usr/bin/env python3
"""
基于规则的第一事件优化器
规则：只对每个电器每天的第一个可调度事件进行优化迁移，其他事件保持原时间
"""

import pandas as pd
import json
import os
import time as time_module
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FirstEventOptimizer:
    def __init__(self, tariff_config_path: str):
        """
        初始化第一事件优化器
        
        Args:
            tariff_config_path: 电价配置文件路径
        """
        # 加载电价配置
        with open(tariff_config_path, 'r') as f:
            self.tariff_config = json.load(f)
        
        # 解析电价配置
        self.tariff_rates = self._parse_tariff_config()
        
        # 约束配置 (与Gurobi相同)
        self.forbidden_appliances = ["Washing Machine", "Tumble Dryer", "Dishwasher"]
        self.forbidden_start_minute = 23 * 60 + 30  # 23:30
        self.forbidden_end_minute = 6 * 60          # 06:00
        self.completion_deadline_hours = 38         # 次日14:00 (38:00)
        self.min_duration_minutes = 5              # 最小持续时间
        
        logger.info("第一事件优化器初始化完成")
        for tariff_name, config in self.tariff_rates.items():
            total_hours = sum(end - start for start, end in config["low_periods"]) / 60
            logger.info(f"  {tariff_name}: {total_hours:.1f}小时低价时段, £{config['low_rate']}/£{config['high_rate']}")

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
        """将时间字符串转换为分钟数"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

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
        
        # 23:30-06:00 禁止时段
        if self.forbidden_start_minute <= minute_of_day < 1440:  # 23:30-24:00
            return True
        if 0 <= minute_of_day < self.forbidden_end_minute:       # 00:00-06:00
            return True
        
        return False

    def load_power_data(self, house_id: str) -> pd.DataFrame:
        """加载功率数据"""
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
        power_df['timestamp'] = pd.to_datetime(power_df['Time'])

        # 获取设备列（排除Time和timestamp列）
        appliance_columns = [col for col in power_df.columns if col not in ['Time', 'timestamp', 'Aggregate']]
        
        logger.info(f"加载功率数据: {house_id}, {len(power_df)} 条时间记录, {len(appliance_columns)} 个设备")
        return power_df

    def get_event_power_profile(self, event: pd.Series, power_df: pd.DataFrame) -> List[Tuple[datetime, float]]:
        """获取事件的功率曲线"""
        start_time = event['start_time']
        end_time = event['end_time']

        # 处理列名不一致问题：appliance_id vs appliance_ID
        appliance_id_str = event.get('appliance_id', event.get('appliance_ID', None))
        if appliance_id_str is None:
            logger.warning(f"事件 {event.get('event_id', 'Unknown')} 缺少 appliance_id 信息")
            return []
        
        # 将appliance_id从字符串转换为数字 (如 "Appliance4" -> 4)
        try:
            appliance_num = int(appliance_id_str.replace('Appliance', ''))
        except:
            logger.warning(f"无法解析appliance_ID: {appliance_id_str}")
            return []
        
        # 在功率数据中找到对应的列
        appliance_column = None
        for col in power_df.columns:
            if col != 'timestamp' and str(appliance_num) in col:
                appliance_column = col
                break
        
        if appliance_column is None:
            logger.warning(f"未找到设备 {appliance_id_str} 对应的功率列")
            return []
        
        # 获取时间范围内的功率数据
        mask = (power_df['timestamp'] >= start_time) & (power_df['timestamp'] <= end_time)
        event_power_data = power_df[mask]
        
        if event_power_data.empty:
            logger.warning(f"事件 {event['event_id']} 没有找到功率数据")
            return []
        
        # 构建功率曲线
        power_profile = []
        for _, row in event_power_data.iterrows():
            timestamp = row['timestamp']
            power_w = row[appliance_column]
            power_profile.append((timestamp, power_w))
        
        return power_profile

    def calculate_event_cost(self, power_profile: List[Tuple[datetime, float]], tariff_type: str) -> float:
        """根据功率曲线计算事件成本"""
        total_cost = 0.0

        for timestamp, power_w in power_profile:
            # 获取该时刻的电价
            minute_of_day = timestamp.hour * 60 + timestamp.minute
            rate = self._get_rate_at_minute(minute_of_day, tariff_type)

            # 计算该分钟的成本：瞬时功率W * 1分钟 / 60分钟 / 1000 = kWh
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
        for timestamp, power_w in power_profile:
            # 计算迁移后的时间
            new_timestamp = timestamp + time_shift

            # 获取新时间的电价
            minute_of_day = new_timestamp.hour * 60 + new_timestamp.minute
            rate = self._get_rate_at_minute(minute_of_day, tariff_type)

            # 计算该分钟的成本
            energy_kwh = power_w / 60 / 1000
            minute_cost = energy_kwh * rate
            total_cost += minute_cost

        return total_cost

    def identify_first_events_per_day(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """识别每天每个电器编号最小的可调度事件（第一个事件）"""
        # 确保时间列是datetime类型
        events_df['start_time'] = pd.to_datetime(events_df['start_time'])
        events_df['end_time'] = pd.to_datetime(events_df['end_time'])

        # 只处理可调度事件
        reschedulable_events = events_df[events_df['is_reschedulable'] == True].copy()

        if reschedulable_events.empty:
            logger.warning("没有找到可调度事件")
            return pd.DataFrame()

        # 添加日期列
        reschedulable_events['date'] = reschedulable_events['start_time'].dt.date

        # 从event_id中提取编号（最后的数字部分）
        def extract_event_number(event_id):
            try:
                # 提取最后的数字部分，如 "Tumble_Dryer_2013-10-24_01" -> 1
                parts = event_id.split('_')
                return int(parts[-1])
            except:
                return 999  # 如果无法解析，给一个大数字

        reschedulable_events['event_number'] = reschedulable_events['event_id'].apply(extract_event_number)

        # 按电器名称和日期分组，找到每天每个电器编号最小的事件
        first_events_list = []
        for (appliance_name, date), group in reschedulable_events.groupby(['appliance_name', 'date']):
            # 找到该天该电器编号最小的事件
            min_number = group['event_number'].min()
            first_event = group[group['event_number'] == min_number].iloc[0]
            first_events_list.append(first_event)

        first_events = pd.DataFrame(first_events_list)

        logger.info(f"识别出 {len(first_events)} 个第一事件（每天每个电器编号最小）（来自 {len(reschedulable_events)} 个可调度事件）")

        # 按电器和日期统计
        daily_counts = first_events.groupby(['appliance_name', 'date']).size().reset_index(name='count')
        appliance_totals = daily_counts.groupby('appliance_name')['count'].sum()

        for appliance, total in appliance_totals.items():
            logger.info(f"  {appliance}: {total} 个第一事件（跨多天）")

        return first_events

    def optimize_first_event(self, event: pd.Series, power_profile: List[Tuple[datetime, float]],
                           tariff_type: str) -> Dict:
        """优化单个第一事件"""
        if not power_profile:
            return None

        original_start = event['start_time']
        duration_min = int(event['duration(min)'])
        appliance_name = event['appliance_name']

        # 计算原始成本
        original_cost = self.calculate_event_cost(power_profile, tariff_type)

        # 计算搜索范围：从事件发生当天0点开始，38小时后结束
        event_date = original_start.date()
        day_start = datetime.combine(event_date, datetime.min.time())  # 当天00:00
        search_absolute_end = day_start + timedelta(hours=self.completion_deadline_hours)  # 38小时后

        # 搜索起点：不能早于原始事件时间
        search_start = original_start
        search_end = search_absolute_end

        logger.debug(f"事件 {event['event_id']}: 原始时间 {original_start}, 搜索范围 [{search_start} ~ {search_end}]")

        best_cost = original_cost
        best_start_time = original_start

        # 每15分钟检查一次可行的迁移时间
        current_time = search_start
        while current_time <= search_end - timedelta(minutes=duration_min):
            candidate_end = current_time + timedelta(minutes=duration_min)

            # 检查是否违反禁止时段约束
            if self._violates_forbidden_period(current_time, candidate_end, appliance_name):
                current_time += timedelta(minutes=15)
                continue

            # 计算在这个时间的成本
            shifted_cost = self.calculate_shifted_event_cost(power_profile, current_time, tariff_type)

            if shifted_cost < best_cost:
                best_cost = shifted_cost
                best_start_time = current_time
                logger.debug(f"找到更优时间: {current_time}, 成本: {shifted_cost:.6f}")

            current_time += timedelta(minutes=15)

        # 计算优化后的结束时间
        best_end_time = best_start_time + timedelta(minutes=duration_min)
        cost_savings = original_cost - best_cost
        savings_percentage = (cost_savings / original_cost * 100) if original_cost > 0 else 0

        # 判断最优时间是否在低价时段
        best_minute_of_day = best_start_time.hour * 60 + best_start_time.minute
        best_rate = self._get_rate_at_minute(best_minute_of_day, tariff_type)
        is_low_rate_period = (best_rate == self.tariff_rates[tariff_type]["low_rate"])

        logger.info(f"  事件 {event['event_id']}: {original_start.strftime('%H:%M')} -> {best_start_time.strftime('%H:%M')}, "
                   f"节约: ${cost_savings:.6f} ({savings_percentage:.1f}%), "
                   f"{'低价时段' if is_low_rate_period else '高价时段'}")

        return {
            'event_id': event['event_id'],
            'appliance_name': event['appliance_name'],
            'appliance_id': event['appliance_id'],
            'original_start_time': original_start,
            'original_end_time': event['end_time'],
            'optimized_start_time': best_start_time,
            'optimized_end_time': best_end_time,
            'duration_minutes': duration_min,
            'original_cost': original_cost,
            'optimized_cost': best_cost,
            'cost_savings': cost_savings,
            'savings_percentage': savings_percentage,
            'is_shifted': best_start_time != original_start,
            'is_low_rate_period': is_low_rate_period,
            'search_start': search_start,
            'search_end': search_end
        }

    def _violates_forbidden_period(self, start_time: datetime, end_time: datetime, appliance_name: str) -> bool:
        """检查事件是否违反禁止时段约束"""
        if appliance_name not in self.forbidden_appliances:
            return False

        # 检查事件的每一分钟是否在禁止时段内
        current_time = start_time
        while current_time < end_time:
            minute_of_day = current_time.hour * 60 + current_time.minute
            if self._is_forbidden_minute(minute_of_day, appliance_name):
                return True
            current_time += timedelta(minutes=1)

        return False

    def optimize_single_file(self, csv_file: str, house_id: str, tariff_type: str) -> Dict:
        """优化单个CSV文件中的第一事件"""
        # 开始计时
        optimization_start_time = time_module.time()
        logger.info(f"🚀 开始第一事件优化: {house_id} ({tariff_type}) - 开始时间: {datetime.now().strftime('%H:%M:%S')}")

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

            # 识别第一事件
            first_events_identification_start = time_module.time()
            first_events_df = self.identify_first_events_per_day(events_df)

            if first_events_df.empty:
                logger.warning(f"文件 {csv_file} 没有第一事件")
                return {"status": "no_first_events", "file": csv_file}

            first_events_identification_time = time_module.time() - first_events_identification_start
            logger.info(f"📊 识别第一事件完成: {len(first_events_df)} 个第一事件 (耗时: {first_events_identification_time:.2f}s)")

            # 功率曲线计算和优化阶段
            optimization_phase_start = time_module.time()
            optimization_results = []
            total_original_cost = 0.0

            for _, event in first_events_df.iterrows():
                try:
                    # 获取功率曲线
                    power_profile = self.get_event_power_profile(event, power_df)
                    if not power_profile:
                        logger.warning(f"事件 {event['event_id']} 没有功率数据")
                        continue

                    # 优化事件
                    optimization_result = self.optimize_first_event(event, power_profile, tariff_type)
                    if optimization_result:
                        optimization_results.append(optimization_result)
                        total_original_cost += optimization_result['original_cost']

                except Exception as e:
                    logger.warning(f"处理事件 {event['event_id']} 时出错: {e}")
                    continue

            optimization_phase_time = time_module.time() - optimization_phase_start

            if not optimization_results:
                return {"status": "no_valid_events", "file": csv_file}

            logger.info(f"🎯 第一事件优化完成: {len(optimization_results)} 个事件被处理 (耗时: {optimization_phase_time:.2f}s)")

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
                "first_events_identification_time_seconds": round(first_events_identification_time, 3),
                "optimization_phase_time_seconds": round(optimization_phase_time, 3),
                "save_time_seconds": round(save_time, 3),
                "total_optimization_time_seconds": round(total_optimization_time, 3),
                "data_loading_time_formatted": f"{data_loading_time:.2f}s",
                "first_events_identification_time_formatted": f"{first_events_identification_time:.2f}s",
                "optimization_phase_time_formatted": f"{optimization_phase_time:.2f}s",
                "save_time_formatted": f"{save_time:.2f}s",
                "total_optimization_time_formatted": f"{total_optimization_time:.2f}s"
            }

            result = {
                "status": "success",
                "file": csv_file,
                "house_id": house_id,
                "tariff_type": tariff_type,
                "total_first_events": len(optimization_results),
                "original_cost": total_original_cost,
                "optimized_cost": total_optimized_cost,
                "total_savings": total_savings,
                "savings_percentage": (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0,
                "timing_stats": timing_stats,
                "optimization_results": optimization_results
            }

            logger.info(f"✅ 第一事件优化完成 {house_id} ({tariff_type}): 节约 ${total_savings:.6f} ({result['savings_percentage']:.2f}%)")
            logger.info(f"⏱️ 总耗时: {total_optimization_time:.2f}s (数据加载: {data_loading_time:.2f}s, 识别第一事件: {first_events_identification_time:.2f}s, 优化: {optimization_phase_time:.2f}s, 保存: {save_time:.2f}s)")
            return result

        except Exception as e:
            logger.error(f"优化文件 {csv_file} 时出错: {e}")
            return {"status": "error", "file": csv_file, "error": str(e)}

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
                'original_start_time': result['original_start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'original_end_time': result['original_end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'optimized_start_time': result['optimized_start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'optimized_end_time': result['optimized_end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': result['duration_minutes'],
                'original_cost': result['original_cost'],
                'optimized_cost': result['optimized_cost'],
                'cost_savings': result['cost_savings'],
                'savings_percentage': result['savings_percentage'],
                'is_shifted': result['is_shifted']
            })

        # 保存CSV文件
        csv_file = os.path.join(output_dir, f"first_event_optimization_results_{house_id}_{tariff_type}.csv")
        csv_df = pd.DataFrame(csv_data)
        csv_df.to_csv(csv_file, index=False)

        # 保存汇总JSON
        summary = {
            'house_id': house_id,
            'tariff_type': tariff_type,
            'total_first_events': len(optimization_results),
            'total_original_cost': original_cost,
            'total_optimized_cost': sum(r['optimized_cost'] for r in optimization_results),
            'total_savings': sum(r['cost_savings'] for r in optimization_results),
            'average_savings_percentage': sum(r['savings_percentage'] for r in optimization_results) / len(optimization_results) if optimization_results else 0,
            'shifted_events': sum(1 for r in optimization_results if r['is_shifted']),
            'optimization_timestamp': datetime.now().isoformat()
        }

        summary_file = os.path.join(output_dir, f"first_event_optimization_summary_{house_id}_{tariff_type}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"    第一事件优化结果已保存: {output_dir}")

if __name__ == "__main__":
    """测试代码"""
    print("🧪 第一事件优化器测试")
    print("=" * 60)

    # 配置文件路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tariff_config = os.path.join(base_dir, "tariff_config.json")

    # 测试数据路径
    data_dir = os.path.join(os.path.dirname(base_dir), "flterted_data")
    test_file = os.path.join(data_dir, "Economy_7", "house1", "tou_filtered_house1_Economy_7.csv")

    if os.path.exists(test_file):
        optimizer = FirstEventOptimizer(tariff_config)
        result = optimizer.optimize_single_file(test_file, "house1", "Economy_7")
        print(f"\n测试结果: {result['status']}")
        if result['status'] == 'success':
            print(f"处理了 {result['total_first_events']} 个第一事件")
            print(f"节约: ${result['total_savings']:.6f} ({result['savings_percentage']:.2f}%)")
    else:
        print(f"测试文件不存在: {test_file}")

    print("\n✅ 测试完成!")

    def calculate_shifted_event_cost(self, power_profile: List[Tuple[datetime, float]], 
                                   new_start_time: datetime, tariff_type: str) -> float:
        """计算迁移后事件的成本"""
        if not power_profile:
            return 0.0
        
        # 计算时间偏移
        original_start = power_profile[0][0]
        time_shift = new_start_time - original_start
        
        total_cost = 0.0
        for timestamp, power_w in power_profile:
            # 计算迁移后的时间
            new_timestamp = timestamp + time_shift
            
            # 获取新时间的电价
            minute_of_day = new_timestamp.hour * 60 + new_timestamp.minute
            rate = self._get_rate_at_minute(minute_of_day, tariff_type)
            
            # 计算该分钟的成本
            energy_kwh = power_w / 60 / 1000
            minute_cost = energy_kwh * rate
            total_cost += minute_cost
        
        return total_cost
