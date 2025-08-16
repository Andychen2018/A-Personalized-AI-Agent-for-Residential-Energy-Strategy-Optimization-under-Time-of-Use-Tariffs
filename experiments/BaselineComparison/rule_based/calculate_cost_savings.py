#!/usr/bin/env python3
"""
费用计算脚本：计算基于规则的事件迁移前后的费用
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

class CostCalculator:
    def __init__(self):
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
        self.results_path = "/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results"
    
    def get_electricity_price(self, timestamp, tariff_type):
        """获取指定时间的电价"""
        hour = timestamp.hour + timestamp.minute / 60.0
        
        config = self.tariff_config[tariff_type]
        
        # 检查是否在低价时段
        for start_hour, end_hour in config['low_price_hours']:
            if start_hour <= hour < end_hour:
                return config['low_price']
        
        return config['high_price']
    
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
    
    def calculate_event_cost_corrected(self, power_df, appliance_id, original_start, original_end, pricing_start, pricing_end, tariff_type):
        """修正的事件费用计算方法

        Args:
            power_df: 功率数据DataFrame
            appliance_id: 设备ID
            original_start: 原始开始时间（用于提取功率数据）
            original_end: 原始结束时间（用于提取功率数据）
            pricing_start: 定价开始时间（用于计算电价）
            pricing_end: 定价结束时间（用于计算电价）
            tariff_type: 电价类型
        """
        try:
            # 确保时间格式正确
            if isinstance(original_start, str):
                original_start = pd.to_datetime(original_start)
            if isinstance(original_end, str):
                original_end = pd.to_datetime(original_end)
            if isinstance(pricing_start, str):
                pricing_start = pd.to_datetime(pricing_start)
            if isinstance(pricing_end, str):
                pricing_end = pd.to_datetime(pricing_end)

            # 生成原始时间段的时间序列（用于提取功率）
            original_time_range = pd.date_range(start=original_start, end=original_end, freq='1min')
            # 生成定价时间段的时间序列（用于计算电价）
            pricing_time_range = pd.date_range(start=pricing_start, end=pricing_end, freq='1min')

            # 确保两个时间段长度相同
            if len(original_time_range) != len(pricing_time_range):
                logger.warning(f"时间段长度不匹配: 原始{len(original_time_range)}分钟, 定价{len(pricing_time_range)}分钟")
                # 取较短的长度
                min_length = min(len(original_time_range), len(pricing_time_range))
                original_time_range = original_time_range[:min_length]
                pricing_time_range = pricing_time_range[:min_length]

            # 获取电价配置
            config = self.tariff_config[tariff_type]
            low_price = config['low_price']
            high_price = config['high_price']
            low_price_hours = config['low_price_hours']

            total_cost = 0.0
            low_price_power = 0.0
            high_price_power = 0.0
            missing_minutes = 0

            for i, (power_timestamp, price_timestamp) in enumerate(zip(original_time_range, pricing_time_range)):
                # 从原始时间段提取功率数据
                power_kw = 0.0  # 默认为0
                if power_timestamp in power_df.index and appliance_id in power_df.columns:
                    power_value = power_df.loc[power_timestamp, appliance_id]
                    if not pd.isna(power_value):
                        power_kw = power_value / 1000.0  # 转换为kW
                else:
                    missing_minutes += 1

                # 根据定价时间段判断电价
                hour = price_timestamp.hour + price_timestamp.minute / 60.0
                is_low_price = False
                for start_hour, end_hour in low_price_hours:
                    if start_hour <= hour < end_hour:
                        is_low_price = True
                        break

                # 累加功率和费用
                if is_low_price:
                    low_price_power += power_kw
                    total_cost += power_kw * (1/60) * low_price  # 1分钟 = 1/60小时
                else:
                    high_price_power += power_kw
                    total_cost += power_kw * (1/60) * high_price

            return {
                'total_cost': total_cost,
                'low_price_power': low_price_power,
                'high_price_power': high_price_power,
                'total_minutes': len(original_time_range),
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
    

    
    def calculate_event_costs(self, house_id, tariff_type):
        """计算单个房屋所有事件的费用"""
        logger.info(f"开始计算 house{house_id} ({tariff_type}) 的事件费用")
        
        # 加载功率数据
        power_df = self.load_power_data(house_id)
        if power_df is None:
            return None
        
        # 加载优化结果
        results_file = f"{self.results_path}/{tariff_type}/house{house_id}/first_event_optimization_results_house{house_id}_{tariff_type}.csv"
        
        if not os.path.exists(results_file):
            logger.error(f"优化结果文件不存在: {results_file}")
            return None
        
        try:
            events_df = pd.read_csv(results_file)
            logger.info(f"加载了 {len(events_df)} 个事件")
        except Exception as e:
            logger.error(f"加载优化结果失败: {e}")
            return None
        
        # 计算每个事件的费用
        results = []
        total_original_cost = 0.0
        total_optimized_cost = 0.0

        # 统计数据质量
        data_quality_stats = {
            'total_events': 0,
            'original_data_missing': 0,
            'optimized_data_missing': 0,
            'out_of_range': 0,
            'successful': 0
        }

        for idx, event in events_df.iterrows():
            try:
                # 获取设备ID
                appliance_id = event['appliance_id']
                data_quality_stats['total_events'] += 1

                # 计算原始时间段费用（功率数据和电价都来自原始时间段）
                original_result = self.calculate_event_cost_corrected(
                    power_df, appliance_id,
                    event['original_start_time'],
                    event['original_end_time'],
                    event['original_start_time'],
                    event['original_end_time'],
                    tariff_type
                )
                original_cost_calculated = original_result['total_cost']

                # 计算优化后费用（功率数据来自原始时间段，电价来自优化后时间段）
                optimized_result = self.calculate_event_cost_corrected(
                    power_df, appliance_id,
                    event['original_start_time'],  # 功率数据仍从原始时间段提取
                    event['original_end_time'],    # 功率数据仍从原始时间段提取
                    event['optimized_start_time'], # 电价从优化后时间段计算
                    event['optimized_end_time'],   # 电价从优化后时间段计算
                    tariff_type
                )
                optimized_cost_calculated = optimized_result['total_cost']

                # 更新数据质量统计
                if original_result['missing_minutes'] > 0:
                    data_quality_stats['original_data_missing'] += 1
                if optimized_result['missing_minutes'] > 0:
                    data_quality_stats['optimized_data_missing'] += 1
                if original_result['status'] == 'success' and optimized_result['status'] == 'success':
                    data_quality_stats['successful'] += 1
                
                # 计算节约
                cost_savings_calculated = original_cost_calculated - optimized_cost_calculated
                savings_percentage_calculated = (cost_savings_calculated / original_cost_calculated * 100) if original_cost_calculated > 0 else 0
                
                # 记录结果
                result = {
                    'event_id': event['event_id'],
                    'appliance_name': event['appliance_name'],
                    'appliance_id': appliance_id,
                    'original_start_time': event['original_start_time'],
                    'original_end_time': event['original_end_time'],
                    'optimized_start_time': event['optimized_start_time'],
                    'optimized_end_time': event['optimized_end_time'],
                    'duration_minutes': event['duration_minutes'],
                    'original_cost_reported': event['original_cost'],
                    'optimized_cost_reported': event['optimized_cost'],
                    'original_cost_calculated': original_cost_calculated,
                    'optimized_cost_calculated': optimized_cost_calculated,
                    'cost_savings_calculated': cost_savings_calculated,
                    'savings_percentage_calculated': savings_percentage_calculated,
                    'is_shifted': event['is_shifted'],
                    'original_low_price_power': original_result['low_price_power'],
                    'original_high_price_power': original_result['high_price_power'],
                    'original_missing_minutes': original_result['missing_minutes'],
                    'optimized_low_price_power': optimized_result['low_price_power'],
                    'optimized_high_price_power': optimized_result['high_price_power'],
                    'optimized_missing_minutes': optimized_result['missing_minutes']
                }
                
                results.append(result)
                total_original_cost += original_cost_calculated
                total_optimized_cost += optimized_cost_calculated
                
                if idx % 50 == 0:
                    logger.info(f"已处理 {idx+1}/{len(events_df)} 个事件")
                    
            except Exception as e:
                logger.error(f"处理事件 {idx} 失败: {e}")
                continue
        
        # 计算总体统计
        total_savings = total_original_cost - total_optimized_cost
        total_savings_percentage = (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0
        
        summary = {
            'house_id': house_id,
            'tariff_type': tariff_type,
            'total_events': len(results),
            'total_original_cost_calculated': total_original_cost,
            'total_optimized_cost_calculated': total_optimized_cost,
            'total_cost_savings_calculated': total_savings,
            'total_savings_percentage_calculated': total_savings_percentage,
            'data_quality': data_quality_stats
        }
        
        logger.info(f"house{house_id} ({tariff_type}) 费用计算完成:")
        logger.info(f"  总事件数: {len(results)}")
        logger.info(f"  原始总费用: £{total_original_cost:.6f}")
        logger.info(f"  优化后总费用: £{total_optimized_cost:.6f}")
        logger.info(f"  总节约: £{total_savings:.6f} ({total_savings_percentage:.2f}%)")
        logger.info(f"  数据质量: 成功{data_quality_stats['successful']}/{data_quality_stats['total_events']} ({data_quality_stats['successful']/data_quality_stats['total_events']*100:.1f}%)")
        if data_quality_stats['original_data_missing'] > 0 or data_quality_stats['optimized_data_missing'] > 0:
            logger.warning(f"  数据缺失: 原始{data_quality_stats['original_data_missing']}, 优化后{data_quality_stats['optimized_data_missing']}")
        
        return results, summary

    def save_results(self, results, summary, house_id, tariff_type):
        """保存计算结果"""
        output_dir = f"{self.results_path}/{tariff_type}/house{house_id}"

        # 保存详细结果
        results_df = pd.DataFrame(results)
        results_file = f"{output_dir}/cost_calculation_results_house{house_id}_{tariff_type}.csv"
        results_df.to_csv(results_file, index=False)
        logger.info(f"详细结果已保存到: {results_file}")

        # 保存汇总结果
        summary_file = f"{output_dir}/cost_calculation_summary_house{house_id}_{tariff_type}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"汇总结果已保存到: {summary_file}")

    def process_all_houses(self):
        """处理所有房屋的费用计算"""
        logger.info("开始批量处理所有房屋的费用计算")

        all_summaries = []

        # 遍历所有tariff类型和房屋
        for tariff_type in ['Economy_7', 'Economy_10']:
            tariff_dir = f"{self.results_path}/{tariff_type}"

            if not os.path.exists(tariff_dir):
                logger.warning(f"目录不存在: {tariff_dir}")
                continue

            # 获取所有房屋目录
            house_dirs = [d for d in os.listdir(tariff_dir) if d.startswith('house')]
            house_dirs.sort(key=lambda x: int(x.replace('house', '')))

            logger.info(f"处理 {tariff_type}: 找到 {len(house_dirs)} 个房屋")

            for house_dir in house_dirs:
                house_id = house_dir.replace('house', '')

                try:
                    # 计算费用
                    results, summary = self.calculate_event_costs(house_id, tariff_type)

                    if results is not None:
                        # 保存结果
                        self.save_results(results, summary, house_id, tariff_type)
                        all_summaries.append(summary)

                except Exception as e:
                    logger.error(f"处理 house{house_id} ({tariff_type}) 失败: {e}")
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
                    'total_events': 0,
                    'total_original_cost': 0.0,
                    'total_optimized_cost': 0.0,
                    'total_savings': 0.0
                }

            stats = tariff_stats[tariff]
            stats['house_count'] += 1
            stats['total_events'] += summary['total_events']
            stats['total_original_cost'] += summary['total_original_cost_calculated']
            stats['total_optimized_cost'] += summary['total_optimized_cost_calculated']
            stats['total_savings'] += summary['total_cost_savings_calculated']

        # 计算总体统计
        overall_stats = {
            'calculation_timestamp': datetime.now().isoformat(),
            'tariff_statistics': {},
            'grand_total': {
                'total_houses': len(all_summaries),
                'total_events': sum(s['total_events'] for s in all_summaries),
                'total_original_cost': sum(s['total_original_cost_calculated'] for s in all_summaries),
                'total_optimized_cost': sum(s['total_optimized_cost_calculated'] for s in all_summaries),
                'total_savings': sum(s['total_cost_savings_calculated'] for s in all_summaries)
            }
        }

        # 添加每个tariff的统计
        for tariff, stats in tariff_stats.items():
            savings_percentage = (stats['total_savings'] / stats['total_original_cost'] * 100) if stats['total_original_cost'] > 0 else 0

            overall_stats['tariff_statistics'][tariff] = {
                'house_count': stats['house_count'],
                'total_events': stats['total_events'],
                'total_original_cost': stats['total_original_cost'],
                'total_optimized_cost': stats['total_optimized_cost'],
                'total_savings': stats['total_savings'],
                'savings_percentage': savings_percentage,
                'average_savings_per_house': stats['total_savings'] / stats['house_count'] if stats['house_count'] > 0 else 0,
                'average_events_per_house': stats['total_events'] / stats['house_count'] if stats['house_count'] > 0 else 0
            }

        # 计算总体节约百分比
        grand_total = overall_stats['grand_total']
        grand_total['savings_percentage'] = (grand_total['total_savings'] / grand_total['total_original_cost'] * 100) if grand_total['total_original_cost'] > 0 else 0

        # 保存总体汇总
        overall_file = f"{self.results_path}/overall_cost_calculation_summary.json"
        with open(overall_file, 'w') as f:
            json.dump(overall_stats, f, indent=2)

        logger.info(f"总体汇总已保存到: {overall_file}")

        # 打印汇总信息
        logger.info("=== 费用计算总体汇总 ===")
        logger.info(f"总房屋数: {grand_total['total_houses']}")
        logger.info(f"总事件数: {grand_total['total_events']}")
        logger.info(f"总原始费用: £{grand_total['total_original_cost']:.6f}")
        logger.info(f"总优化后费用: £{grand_total['total_optimized_cost']:.6f}")
        logger.info(f"总节约: £{grand_total['total_savings']:.6f} ({grand_total['savings_percentage']:.2f}%)")

        for tariff, stats in overall_stats['tariff_statistics'].items():
            logger.info(f"\n{tariff}:")
            logger.info(f"  房屋数: {stats['house_count']}")
            logger.info(f"  事件数: {stats['total_events']}")
            logger.info(f"  总节约: £{stats['total_savings']:.6f} ({stats['savings_percentage']:.2f}%)")
            logger.info(f"  平均每房屋节约: £{stats['average_savings_per_house']:.6f}")


def main():
    """主函数"""
    calculator = CostCalculator()
    calculator.process_all_houses()


if __name__ == "__main__":
    main()
