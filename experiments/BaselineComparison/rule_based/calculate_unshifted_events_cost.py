#!/usr/bin/env python3
"""
未迁移事件费用计算脚本：
1. 从完整事件中过滤出未迁移的事件
2. 计算这些未迁移事件的费用
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UnshiftedEventsCostCalculator:
    def __init__(self, tariff_type=None):
        self.tariff_type = tariff_type  # 指定的电价类型，如果为None则自动检测所有类型

        # 电价配置 (£/kWh) - 与Gurobi保持一致
        self.tariff_config = {
            'Economy_7': {
                'low_price': 0.15,
                'high_price': 0.3,
                'low_price_hours': [(0.5, 7.5)]  # 00:30-07:30 (与Gurobi一致)
            },
            'Economy_10': {
                'low_price': 0.15,
                'high_price': 0.3,
                'low_price_hours': [(1, 6), (13, 16), (20, 22)]  # 01:00-06:00, 13:00-16:00, 20:00-22:00 (与Gurobi一致)
            },
            'Standard': {
                'low_price': 0.3,
                'high_price': 0.3,
                'low_price_hours': []  # 无低价时段
            }
        }

        # 数据路径
        self.power_data_path = "/home/deep/TimeSeries/Agent_V2/output/01_preprocessed"
        self.event_segments_path = "/home/deep/TimeSeries/Agent_V2/output/02_event_segments"
        self.results_path = "/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results"

        # 房屋和电价类型映射 - 根据结果目录自动检测
        self.house_tariff_mapping = self._detect_house_tariff_mapping()

    def _detect_house_tariff_mapping(self):
        """自动检测房屋和电价类型的映射关系"""
        mapping = {}

        # 如果指定了特定的电价类型，只处理该类型
        if self.tariff_type:
            tariff_dir = f"{self.results_path}/{self.tariff_type}"
            if os.path.exists(tariff_dir):
                house_dirs = [d for d in os.listdir(tariff_dir) if d.startswith('house')]
                for house_dir in house_dirs:
                    house_id = house_dir.replace('house', '')
                    # 检查是否有已迁移事件的汇总文件
                    summary_file = f"{tariff_dir}/{house_dir}/cost_calculation_summary_{house_dir}_{self.tariff_type}.json"
                    if os.path.exists(summary_file):
                        mapping[house_id] = self.tariff_type
        else:
            # 自动检测所有电价类型
            for tariff_type in ['Economy_7', 'Economy_10']:
                tariff_dir = f"{self.results_path}/{tariff_type}"
                if os.path.exists(tariff_dir):
                    house_dirs = [d for d in os.listdir(tariff_dir) if d.startswith('house')]
                    for house_dir in house_dirs:
                        house_id = house_dir.replace('house', '')
                        # 检查是否有已迁移事件的汇总文件
                        summary_file = f"{tariff_dir}/{house_dir}/cost_calculation_summary_{house_dir}_{tariff_type}.json"
                        if os.path.exists(summary_file):
                            mapping[house_id] = tariff_type

        logger.info(f"检测到房屋电价映射: {len(mapping)}个房屋")
        for tariff in ['Economy_7', 'Economy_10']:
            count = sum(1 for t in mapping.values() if t == tariff)
            if count > 0:
                logger.info(f"  {tariff}: {count}个房屋")

        return mapping

    def load_complete_events(self, house_id):
        """加载房屋的完整事件数据"""
        events_file = f"{self.event_segments_path}/house{house_id}/02_appliance_event_segments_id_house{house_id}.csv"
        
        if not os.path.exists(events_file):
            logger.error(f"完整事件文件不存在: {events_file}")
            return None
        
        try:
            df = pd.read_csv(events_file)
            logger.info(f"成功加载house{house_id}的完整事件数据: {len(df)}个事件")
            return df
        except Exception as e:
            logger.error(f"加载完整事件数据失败 {events_file}: {e}")
            return None
    
    def load_shifted_events(self, house_id, tariff_type):
        """加载已迁移的事件数据"""
        shifted_file = f"{self.results_path}/{tariff_type}/house{house_id}/first_event_optimization_results_house{house_id}_{tariff_type}.csv"
        
        if not os.path.exists(shifted_file):
            logger.warning(f"已迁移事件文件不存在: {shifted_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(shifted_file)
            logger.info(f"成功加载house{house_id}的已迁移事件数据: {len(df)}个事件")
            return df
        except Exception as e:
            logger.error(f"加载已迁移事件数据失败 {shifted_file}: {e}")
            return pd.DataFrame()
    
    def find_unshifted_events(self, complete_events, shifted_events):
        """找出未迁移的事件"""
        if shifted_events.empty:
            logger.info("没有已迁移事件，所有事件都是未迁移的")
            return complete_events
        
        # 获取已迁移事件的event_id列表
        shifted_event_ids = set(shifted_events['event_id'].tolist())
        
        # 过滤出未迁移的事件
        unshifted_events = complete_events[~complete_events['event_id'].isin(shifted_event_ids)]
        
        logger.info(f"找到未迁移事件: {len(unshifted_events)}个 (总事件: {len(complete_events)}, 已迁移: {len(shifted_events)})")
        
        return unshifted_events
    
    def load_power_data(self, house_id):
        """加载房屋的功率数据"""
        power_file = f"{self.power_data_path}/house{house_id}/01_perception_alignment_result_house{house_id}.csv"
        
        if not os.path.exists(power_file):
            logger.error(f"功率数据文件不存在: {power_file}")
            return None
        
        try:
            df = pd.read_csv(power_file)
            df['Time'] = pd.to_datetime(df['Time'])
            df.set_index('Time', inplace=True)
            logger.info(f"成功加载house{house_id}的功率数据: {len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"加载功率数据失败 {power_file}: {e}")
            return None
    
    def get_rate_for_time(self, timestamp, tariff_type):
        """获取指定时间的电价"""
        hour = timestamp.hour + timestamp.minute / 60.0
        config = self.tariff_config[tariff_type]

        for start_hour, end_hour in config['low_price_hours']:
            if start_hour <= hour < end_hour:
                return config['low_price']
        return config['high_price']

    def calculate_event_cost_optimized(self, power_df, appliance_id, start_time, end_time, tariff_type):
        """优化的事件费用计算方法 - 参考gurobi实现"""
        try:
            start_dt = pd.to_datetime(start_time)
            end_dt = pd.to_datetime(end_time)

            # 检查设备是否存在
            if appliance_id not in power_df.columns:
                return {
                    'total_cost': 0.0,
                    'low_price_power': 0.0,
                    'high_price_power': 0.0,
                    'total_minutes': 0,
                    'missing_minutes': 0,
                    'status': 'no_appliance'
                }

            # 获取时间段内的功率数据
            mask = (power_df.index >= start_dt) & (power_df.index <= end_dt)
            power_series = power_df.loc[mask, appliance_id]

            if power_series.empty:
                return {
                    'total_cost': 0.0,
                    'low_price_power': 0.0,
                    'high_price_power': 0.0,
                    'total_minutes': 0,
                    'missing_minutes': 0,
                    'status': 'no_data'
                }

            total_cost = 0.0
            low_price_power = 0.0
            high_price_power = 0.0
            missing_minutes = 0
            current_rate_lookup_time = start_dt

            for power_at_minute in power_series:
                try:
                    power_at_minute = float(power_at_minute) if not pd.isna(power_at_minute) else 0.0
                except (ValueError, TypeError):
                    power_at_minute = 0.0
                    missing_minutes += 1

                if power_at_minute > 0:
                    power_kw = power_at_minute / 1000.0
                    rate = self.get_rate_for_time(current_rate_lookup_time, tariff_type)
                    minute_cost = rate * power_kw * (1/60)
                    total_cost += minute_cost

                    # 统计低价和高价功率
                    if rate == self.tariff_config[tariff_type]['low_price']:
                        low_price_power += power_kw
                    else:
                        high_price_power += power_kw

                current_rate_lookup_time += pd.Timedelta(minutes=1)

            return {
                'total_cost': total_cost,
                'low_price_power': low_price_power,
                'high_price_power': high_price_power,
                'total_minutes': len(power_series),
                'missing_minutes': missing_minutes,
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"计算事件费用失败: {e}")
            return {
                'total_cost': 0.0,
                'low_price_power': 0.0,
                'high_price_power': 0.0,
                'total_minutes': 0,
                'missing_minutes': 0,
                'status': 'error'
            }

    def calculate_unshifted_events_costs(self, house_id):
        """计算单个房屋未迁移事件的费用"""
        logger.info(f"开始处理 house{house_id} 的未迁移事件")

        # 获取电价类型
        tariff_type = self.house_tariff_mapping.get(house_id, 'Economy_7')
        logger.info(f"house{house_id} 使用电价类型: {tariff_type}")

        # 加载完整事件数据
        complete_events = self.load_complete_events(house_id)
        if complete_events is None:
            return None

        # 加载已迁移事件数据
        shifted_events = self.load_shifted_events(house_id, tariff_type)

        # 找出未迁移的事件
        unshifted_events = self.find_unshifted_events(complete_events, shifted_events)

        if unshifted_events.empty:
            logger.info(f"house{house_id} 没有未迁移的事件")
            return None

        # 加载功率数据
        power_df = self.load_power_data(house_id)
        if power_df is None:
            return None

        # 计算每个未迁移事件的费用
        results = []
        total_cost = 0.0
        data_quality_stats = {
            'total_events': 0,
            'successful': 0,
            'data_missing': 0,
            'errors': 0
        }

        for idx, event in unshifted_events.iterrows():
            try:
                data_quality_stats['total_events'] += 1

                # 计算事件费用
                cost_result = self.calculate_event_cost_optimized(
                    power_df,
                    event['appliance_ID'],
                    event['start_time'],
                    event['end_time'],
                    tariff_type
                )

                # 更新统计
                if cost_result['status'] == 'success':
                    data_quality_stats['successful'] += 1
                else:
                    data_quality_stats['errors'] += 1

                if cost_result['missing_minutes'] > 0:
                    data_quality_stats['data_missing'] += 1

                # 记录结果
                result = {
                    'event_id': event['event_id'],
                    'appliance_name': event['appliance_name'],
                    'appliance_id': event['appliance_ID'],
                    'shiftability': event['Shiftability'],
                    'is_reschedulable': event['is_reschedulable'],
                    'start_time': event['start_time'],
                    'end_time': event['end_time'],
                    'duration_minutes': event['duration(min)'],
                    'energy_w': event['energy(W)'],
                    'cost_calculated': cost_result['total_cost'],
                    'low_price_power': cost_result['low_price_power'],
                    'high_price_power': cost_result['high_price_power'],
                    'total_minutes': cost_result['total_minutes'],
                    'missing_minutes': cost_result['missing_minutes'],
                    'tariff_type': tariff_type
                }

                results.append(result)
                total_cost += cost_result['total_cost']

                if idx % 100 == 0:
                    logger.info(f"已处理 {data_quality_stats['total_events']}/{len(unshifted_events)} 个未迁移事件")

            except Exception as e:
                logger.error(f"处理事件 {idx} 失败: {e}")
                data_quality_stats['errors'] += 1
                continue

        # 计算汇总统计
        summary = {
            'house_id': house_id,
            'tariff_type': tariff_type,
            'total_unshifted_events': len(results),
            'total_complete_events': len(complete_events),
            'total_shifted_events': len(shifted_events),
            'total_unshifted_cost': total_cost,
            'data_quality': data_quality_stats
        }

        logger.info(f"house{house_id} 未迁移事件费用计算完成:")
        logger.info(f"  未迁移事件数: {len(results)}")
        logger.info(f"  未迁移事件总费用: £{total_cost:.6f}")
        logger.info(f"  数据质量: 成功{data_quality_stats['successful']}/{data_quality_stats['total_events']} ({data_quality_stats['successful']/data_quality_stats['total_events']*100:.1f}%)")

        return results, summary

    def save_results(self, results, summary, house_id):
        """保存未迁移事件的计算结果"""
        tariff_type = summary['tariff_type']
        output_dir = f"{self.results_path}/{tariff_type}/house{house_id}"

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 保存详细结果
        results_df = pd.DataFrame(results)
        results_file = f"{output_dir}/unshifted_events_cost_results_house{house_id}_{tariff_type}.csv"
        results_df.to_csv(results_file, index=False)
        logger.info(f"未迁移事件详细结果已保存到: {results_file}")

        # 保存汇总结果
        summary_file = f"{output_dir}/unshifted_events_cost_summary_house{house_id}_{tariff_type}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"未迁移事件汇总结果已保存到: {summary_file}")

    def process_all_houses(self):
        """处理所有房屋的未迁移事件费用计算"""
        logger.info("开始批量处理所有房屋的未迁移事件费用计算")

        all_summaries = []

        # 获取所有房屋ID
        house_ids = list(self.house_tariff_mapping.keys())
        house_ids.sort(key=lambda x: int(x))

        logger.info(f"找到 {len(house_ids)} 个房屋需要处理")

        for house_id in house_ids:
            try:
                # 计算未迁移事件费用
                result = self.calculate_unshifted_events_costs(house_id)

                if result is not None:
                    results, summary = result
                    # 保存结果
                    self.save_results(results, summary, house_id)
                    all_summaries.append(summary)

            except Exception as e:
                logger.error(f"处理 house{house_id} 失败: {e}")
                continue

        # 保存总体汇总
        self.save_overall_summary(all_summaries)

        logger.info("批量处理完成")

    def save_overall_summary(self, all_summaries):
        """保存总体汇总结果"""
        if not all_summaries:
            logger.warning("没有汇总数据可保存")
            return

        # 按tariff类型分组统计
        tariff_stats = {}

        for summary in all_summaries:
            tariff = summary['tariff_type']
            if tariff not in tariff_stats:
                tariff_stats[tariff] = {
                    'house_count': 0,
                    'total_unshifted_events': 0,
                    'total_complete_events': 0,
                    'total_shifted_events': 0,
                    'total_unshifted_cost': 0.0
                }

            stats = tariff_stats[tariff]
            stats['house_count'] += 1
            stats['total_unshifted_events'] += summary['total_unshifted_events']
            stats['total_complete_events'] += summary['total_complete_events']
            stats['total_shifted_events'] += summary['total_shifted_events']
            stats['total_unshifted_cost'] += summary['total_unshifted_cost']

        # 计算总体统计
        overall_stats = {
            'calculation_timestamp': datetime.now().isoformat(),
            'tariff_statistics': {},
            'grand_total': {
                'total_houses': len(all_summaries),
                'total_unshifted_events': sum(s['total_unshifted_events'] for s in all_summaries),
                'total_complete_events': sum(s['total_complete_events'] for s in all_summaries),
                'total_shifted_events': sum(s['total_shifted_events'] for s in all_summaries),
                'total_unshifted_cost': sum(s['total_unshifted_cost'] for s in all_summaries)
            }
        }

        # 添加每个tariff的统计
        for tariff, stats in tariff_stats.items():
            overall_stats['tariff_statistics'][tariff] = {
                'house_count': stats['house_count'],
                'total_unshifted_events': stats['total_unshifted_events'],
                'total_complete_events': stats['total_complete_events'],
                'total_shifted_events': stats['total_shifted_events'],
                'total_unshifted_cost': stats['total_unshifted_cost'],
                'average_unshifted_cost_per_house': stats['total_unshifted_cost'] / stats['house_count'] if stats['house_count'] > 0 else 0,
                'shift_rate': (stats['total_shifted_events'] / stats['total_complete_events'] * 100) if stats['total_complete_events'] > 0 else 0
            }

        # 保存总体汇总
        overall_file = f"{self.results_path}/overall_unshifted_events_cost_summary.json"
        with open(overall_file, 'w') as f:
            json.dump(overall_stats, f, indent=2)

        logger.info(f"未迁移事件总体汇总已保存到: {overall_file}")

        # 打印汇总信息
        grand_total = overall_stats['grand_total']
        logger.info("=== 未迁移事件费用计算总体汇总 ===")
        logger.info(f"总房屋数: {grand_total['total_houses']}")
        logger.info(f"总完整事件数: {grand_total['total_complete_events']}")
        logger.info(f"总已迁移事件数: {grand_total['total_shifted_events']}")
        logger.info(f"总未迁移事件数: {grand_total['total_unshifted_events']}")
        logger.info(f"总未迁移事件费用: £{grand_total['total_unshifted_cost']:.6f}")

        for tariff, stats in overall_stats['tariff_statistics'].items():
            logger.info(f"\n{tariff}:")
            logger.info(f"  房屋数: {stats['house_count']}")
            logger.info(f"  未迁移事件数: {stats['total_unshifted_events']}")
            logger.info(f"  未迁移事件费用: £{stats['total_unshifted_cost']:.6f}")
            logger.info(f"  迁移率: {stats['shift_rate']:.2f}%")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='计算未迁移事件的费用')
    parser.add_argument('--tariff_type', type=str, choices=['Economy_7', 'Economy_10'],
                       help='指定电价类型，如果不指定则处理所有类型')

    args = parser.parse_args()

    calculator = UnshiftedEventsCostCalculator(tariff_type=args.tariff_type)
    calculator.process_all_houses()


if __name__ == "__main__":
    main()
