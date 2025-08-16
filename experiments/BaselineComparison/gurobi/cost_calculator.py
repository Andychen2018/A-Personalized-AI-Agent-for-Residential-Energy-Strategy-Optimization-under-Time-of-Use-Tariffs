#!/usr/bin/env python3
"""
完整的费用计算系统
计算所有事件（可调度+不可调度）的迁移前后费用
"""

import pandas as pd
import json
import os
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteCostCalculator:
    def __init__(self, tariff_config_path: str):
        """
        初始化完整费用计算器

        Args:
            tariff_config_path: 电价配置文件路径
        """
        # 电价配置 - 根据tariff_config.json的实际内容设置
        self.tariff_rates = {
            "Economy_7": {
                "low_periods": [(30, 450)],      # 00:30-07:30 (7小时)
                "low_rate": 0.15,                # £0.15/kWh
                "high_rate": 0.30                # £0.30/kWh
            },
            "Economy_10": {
                "low_periods": [(60, 360), (780, 960), (1200, 1320)],  # 01:00-06:00, 13:00-16:00, 20:00-22:00 (10小时)
                "low_rate": 0.15,                # £0.15/kWh (与tariff_config.json一致)
                "high_rate": 0.30                # £0.30/kWh
            }
        }

        logger.info("完整费用计算器初始化完成")
        logger.info("使用电价配置:")
        for tariff_name, config in self.tariff_rates.items():
            total_low_hours = sum(end - start for start, end in config["low_periods"]) / 60
            logger.info(f"  {tariff_name}: {total_low_hours:.1f}小时低价时段, £{config['low_rate']}/£{config['high_rate']}")

    
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
    
    def load_all_events(self, house_id: str) -> pd.DataFrame:
        """加载房屋的所有事件数据"""
        # 从完整事件文件加载
        current_dir = os.getcwd()
        while not os.path.exists(os.path.join(current_dir, "output", "02_event_segments")):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
            current_dir = parent_dir
        
        events_file = os.path.join(current_dir, "output", "02_event_segments", house_id, f"02_appliance_event_segments_id_{house_id}.csv")
        
        if not os.path.exists(events_file):
            raise FileNotFoundError(f"事件数据文件不存在: {events_file}")
        
        events_df = pd.read_csv(events_file)
        events_df['start_time'] = pd.to_datetime(events_df['start_time'])
        events_df['end_time'] = pd.to_datetime(events_df['end_time'])
        
        logger.info(f"加载所有事件: {house_id}, {len(events_df)} 个事件")
        logger.info(f"  可调度事件: {len(events_df[events_df['is_reschedulable'] == True])} 个")
        logger.info(f"  不可调度事件: {len(events_df[events_df['is_reschedulable'] == False])} 个")
        
        return events_df
    
    def load_optimization_results(self, house_id: str, tariff_type: str) -> pd.DataFrame:
        """加载优化结果"""
        results_file = f"./results/{tariff_type}/{house_id}/optimization_results_{house_id}_{tariff_type}.csv"

        if not os.path.exists(results_file):
            logger.warning(f"优化结果文件不存在: {results_file}")
            return pd.DataFrame()
        
        results_df = pd.read_csv(results_file)
        results_df['original_start_time'] = pd.to_datetime(results_df['original_start_time'])
        results_df['original_end_time'] = pd.to_datetime(results_df['original_end_time'])
        results_df['optimized_start_time'] = pd.to_datetime(results_df['optimized_start_time'])
        results_df['optimized_end_time'] = pd.to_datetime(results_df['optimized_end_time'])
        
        logger.info(f"加载优化结果: {house_id} ({tariff_type}), {len(results_df)} 个优化事件")
        return results_df
    
    def get_event_power_profile(self, event: pd.Series, power_df: pd.DataFrame) -> List[Tuple[datetime, float]]:
        """获取事件的真实功率曲线"""
        start_time = event['start_time']
        end_time = event['end_time']
        appliance_id_str = event['appliance_ID']
        
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
    
    def calculate_complete_costs(self, house_id: str, tariff_type: str) -> Dict:
        """计算完整的费用（所有事件）"""
        logger.info(f"开始计算完整费用: {house_id} ({tariff_type})")
        
        try:
            # 加载数据
            power_df = self.load_power_data(house_id)
            all_events_df = self.load_all_events(house_id)
            optimization_results_df = self.load_optimization_results(house_id, tariff_type)
            
            # 创建优化结果映射
            optimization_map = {}
            if not optimization_results_df.empty:
                for _, opt_result in optimization_results_df.iterrows():
                    optimization_map[opt_result['event_id']] = opt_result
            
            # 计算所有事件的费用
            all_event_costs = []
            total_original_cost = 0.0
            total_optimized_cost = 0.0
            
            processed_events = 0
            failed_events = 0
            
            for idx, event in all_events_df.iterrows():
                try:
                    # 获取功率曲线
                    power_profile = self.get_event_power_profile(event, power_df)
                    
                    if not power_profile:
                        failed_events += 1
                        continue
                    
                    # 计算原始成本
                    original_cost = self.calculate_event_cost(power_profile, tariff_type)
                    total_original_cost += original_cost
                    
                    # 检查是否有优化结果
                    event_id = event['event_id']
                    if event_id in optimization_map:
                        # 可调度事件：使用优化后的成本
                        opt_result = optimization_map[event_id]
                        optimized_cost = opt_result['optimized_cost']
                        is_optimized = True
                        optimized_start = opt_result['optimized_start_time']
                        optimized_end = opt_result['optimized_end_time']
                        cost_savings = original_cost - optimized_cost
                        savings_percentage = (cost_savings / original_cost * 100) if original_cost > 0 else 0
                    else:
                        # 不可调度事件：成本不变
                        optimized_cost = original_cost
                        is_optimized = False
                        optimized_start = event['start_time']
                        optimized_end = event['end_time']
                        cost_savings = 0.0
                        savings_percentage = 0.0
                    
                    total_optimized_cost += optimized_cost
                    
                    all_event_costs.append({
                        'event_id': event['event_id'],
                        'appliance_name': event['appliance_name'],
                        'appliance_id': event['appliance_ID'],
                        'is_reschedulable': event['is_reschedulable'],
                        'is_optimized': is_optimized,
                        'original_start_time': event['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'original_end_time': event['end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'optimized_start_time': optimized_start.strftime('%Y-%m-%d %H:%M:%S'),
                        'optimized_end_time': optimized_end.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration_minutes': event['duration(min)'],
                        'original_cost': original_cost,
                        'optimized_cost': optimized_cost,
                        'cost_savings': cost_savings,
                        'savings_percentage': savings_percentage,
                        'power_profile_points': len(power_profile)
                    })
                    
                    processed_events += 1
                    
                    if processed_events % 5000 == 0:
                        logger.info(f"  已处理 {processed_events} 个事件...")
                
                except Exception as e:
                    logger.warning(f"处理事件 {event['event_id']} 时出错: {e}")
                    failed_events += 1
                    continue
            
            logger.info(f"费用计算完成: 成功 {processed_events} 个, 失败 {failed_events} 个")
            
            # 计算总体统计
            total_savings = total_original_cost - total_optimized_cost
            overall_savings_percentage = (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0
            
            # 分类统计
            reschedulable_events = [e for e in all_event_costs if e['is_reschedulable']]
            non_reschedulable_events = [e for e in all_event_costs if not e['is_reschedulable']]
            optimized_events = [e for e in all_event_costs if e['is_optimized']]
            
            result = {
                'house_id': house_id,
                'tariff_type': tariff_type,
                'total_events': len(all_event_costs),
                'reschedulable_events': len(reschedulable_events),
                'non_reschedulable_events': len(non_reschedulable_events),
                'optimized_events': len(optimized_events),
                'total_original_cost': total_original_cost,
                'total_optimized_cost': total_optimized_cost,
                'total_savings': total_savings,
                'overall_savings_percentage': overall_savings_percentage,
                'reschedulable_original_cost': sum(e['original_cost'] for e in reschedulable_events),
                'reschedulable_optimized_cost': sum(e['optimized_cost'] for e in reschedulable_events),
                'reschedulable_savings': sum(e['cost_savings'] for e in reschedulable_events),
                'non_reschedulable_cost': sum(e['original_cost'] for e in non_reschedulable_events),
                'all_event_costs': all_event_costs
            }
            
            logger.info(f"完整费用计算结果:")
            logger.info(f"  总事件数: {result['total_events']}")
            logger.info(f"  可调度事件: {result['reschedulable_events']}")
            logger.info(f"  不可调度事件: {result['non_reschedulable_events']}")
            logger.info(f"  总原始成本: ${result['total_original_cost']:.6f}")
            logger.info(f"  总优化成本: ${result['total_optimized_cost']:.6f}")
            logger.info(f"  总节约: ${result['total_savings']:.6f} ({result['overall_savings_percentage']:.2f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"计算完整费用时出错: {e}")
            return None
    
    def save_complete_results(self, result: Dict):
        """保存完整结果"""
        house_id = result['house_id']
        tariff_type = result['tariff_type']
        
        # 创建输出目录
        output_dir = f"./results/{tariff_type}/{house_id}"
        os.makedirs(output_dir, exist_ok=True)

        # 保存详细的所有事件费用CSV
        csv_data = result['all_event_costs']
        csv_df = pd.DataFrame(csv_data)
        csv_file = os.path.join(output_dir, f"complete_cost_analysis_{house_id}_{tariff_type}.csv")
        csv_df.to_csv(csv_file, index=False)

        # 保存汇总统计JSON
        summary = {k: v for k, v in result.items() if k != 'all_event_costs'}
        summary['calculation_timestamp'] = datetime.now().isoformat()

        json_file = os.path.join(output_dir, f"complete_cost_summary_{house_id}_{tariff_type}.json")
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"完整结果已保存:")
        logger.info(f"  CSV: {csv_file}")
        logger.info(f"  JSON: {json_file}")


def main():
    """主函数"""
    print("🚀 完整费用计算系统")
    print("=" * 80)
    
    # 配置路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tariff_config = os.path.join(base_dir, "tariff_config.json")
    
    # 创建计算器
    calculator = CompleteCostCalculator(tariff_config)
    
    # 测试单个house
    test_house = "house1"
    test_tariff = "Economy_7"
    
    print(f"📊 测试计算: {test_house} ({test_tariff})")
    
    result = calculator.calculate_complete_costs(test_house, test_tariff)
    
    if result:
        calculator.save_complete_results(result)
        print("\n🎉 完整费用计算完成!")
    else:
        print("\n❌ 完整费用计算失败")


if __name__ == "__main__":
    main()
