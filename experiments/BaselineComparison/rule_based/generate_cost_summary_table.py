#!/usr/bin/env python3
"""
生成费用汇总表格：
1. 从已迁移事件和未迁移事件的结果中提取费用数据
2. 计算总的迁移前费用和迁移后费用
3. 生成类似用户提供的表格格式
"""

import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CostSummaryTableGenerator:
    def __init__(self):
        self.results_path = "/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results"
        
        # 房屋和电价类型映射
        self.house_tariff_mapping = self._detect_house_tariff_mapping()
    
    def _detect_house_tariff_mapping(self):
        """自动检测房屋和电价类型的映射关系"""
        mapping = {}

        # 检测每个房屋在哪些电价类型下有数据
        for tariff_type in ['Economy_7', 'Economy_10']:
            tariff_dir = f"{self.results_path}/{tariff_type}"
            if os.path.exists(tariff_dir):
                house_dirs = [d for d in os.listdir(tariff_dir) if d.startswith('house')]
                for house_dir in house_dirs:
                    house_id = house_dir.replace('house', '')
                    if house_id not in mapping:
                        mapping[house_id] = []
                    mapping[house_id].append(tariff_type)

        logger.info(f"检测到房屋电价映射: {len(mapping)}个房屋")
        for house_id, tariff_types in mapping.items():
            logger.info(f"  house{house_id}: {tariff_types}")

        return mapping
    
    def load_shifted_events_summary(self, house_id, tariff_type):
        """加载已迁移事件的汇总数据"""
        summary_file = f"{self.results_path}/{tariff_type}/house{house_id}/cost_calculation_summary_house{house_id}_{tariff_type}.json"
        
        if not os.path.exists(summary_file):
            logger.warning(f"已迁移事件汇总文件不存在: {summary_file}")
            return None
        
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"加载已迁移事件汇总失败: {e}")
            return None
    
    def load_unshifted_events_summary(self, house_id, tariff_type):
        """加载未迁移事件的汇总数据"""
        summary_file = f"{self.results_path}/{tariff_type}/house{house_id}/unshifted_events_cost_summary_house{house_id}_{tariff_type}.json"
        
        if not os.path.exists(summary_file):
            logger.warning(f"未迁移事件汇总文件不存在: {summary_file}")
            return None
        
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"加载未迁移事件汇总失败: {e}")
            return None
    
    def calculate_house_costs(self, house_id):
        """计算单个房屋在所有电价类型下的总费用"""
        tariff_types = self.house_tariff_mapping.get(house_id)
        if not tariff_types:
            logger.warning(f"未找到house{house_id}的电价类型")
            return []

        results = []

        for tariff_type in tariff_types:
            # 加载已迁移事件数据
            shifted_summary = self.load_shifted_events_summary(house_id, tariff_type)

            # 加载未迁移事件数据
            unshifted_summary = self.load_unshifted_events_summary(house_id, tariff_type)

            if not shifted_summary and not unshifted_summary:
                logger.warning(f"house{house_id} {tariff_type}没有找到任何费用数据")
                continue

            # 计算总费用
            result = {
                'house_id': house_id,
                'tariff_type': tariff_type,
                'shifted_original_cost': 0.0,
                'shifted_optimized_cost': 0.0,
                'unshifted_cost': 0.0,
                'total_original_cost': 0.0,
                'total_optimized_cost': 0.0,
                'total_savings': 0.0,
                'savings_rate': 0.0
            }

            # 已迁移事件费用
            if shifted_summary:
                result['shifted_original_cost'] = shifted_summary.get('total_original_cost_calculated', 0.0)
                result['shifted_optimized_cost'] = shifted_summary.get('total_optimized_cost_calculated', 0.0)

            # 未迁移事件费用
            if unshifted_summary:
                result['unshifted_cost'] = unshifted_summary.get('total_unshifted_cost', 0.0)

            # 计算总费用
            result['total_original_cost'] = result['shifted_original_cost'] + result['unshifted_cost']
            result['total_optimized_cost'] = result['shifted_optimized_cost'] + result['unshifted_cost']
            result['total_savings'] = result['total_original_cost'] - result['total_optimized_cost']

            if result['total_original_cost'] > 0:
                result['savings_rate'] = (result['total_savings'] / result['total_original_cost']) * 100

            results.append(result)

        return results
    
    def generate_summary_table(self):
        """生成费用汇总表格"""
        logger.info("开始生成费用汇总表格")
        
        all_results = []
        
        # 获取所有房屋ID并排序
        house_ids = list(self.house_tariff_mapping.keys())
        house_ids.sort(key=lambda x: int(x))
        
        for house_id in house_ids:
            house_results = self.calculate_house_costs(house_id)
            if house_results:
                for result in house_results:
                    all_results.append(result)
                    logger.info(f"house{house_id} {result['tariff_type']}: 原始£{result['total_original_cost']:.2f}, 优化后£{result['total_optimized_cost']:.2f}, 节约{result['savings_rate']:.2f}%")
        
        if not all_results:
            logger.error("没有找到任何费用数据")
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame(all_results)
        
        # 按电价类型分组
        economy_7_data = df[df['tariff_type'] == 'Economy_7']
        economy_10_data = df[df['tariff_type'] == 'Economy_10']
        
        # 创建表格数据
        table_data = []
        
        # 确保两种电价类型的房屋数量相同，如果不同则用空值填充
        max_houses = max(len(economy_7_data), len(economy_10_data))
        
        for i in range(max_houses):
            row = {}
            
            # Economy_7数据
            if i < len(economy_7_data):
                e7_row = economy_7_data.iloc[i]
                row['house_id'] = f"house{e7_row['house_id']}"
                row['original_economy_7'] = e7_row['total_original_cost']
                row['optimized_economy_7'] = e7_row['total_optimized_cost']
            else:
                row['house_id'] = f"house{i+1}"
                row['original_economy_7'] = None
                row['optimized_economy_7'] = None
            
            # Economy_10数据
            if i < len(economy_10_data):
                e10_row = economy_10_data.iloc[i]
                row['original_economy_10'] = e10_row['total_original_cost']
                row['optimized_economy_10'] = e10_row['total_optimized_cost']
            else:
                row['original_economy_10'] = None
                row['optimized_economy_10'] = None
            
            # 计算节约
            if row['original_economy_7'] and row['original_economy_10']:
                total_original = row['original_economy_7'] + row['original_economy_10']
                total_optimized = row['optimized_economy_7'] + row['optimized_economy_10']
                row['saving'] = total_original - total_optimized
                row['saving_rate'] = (row['saving'] / total_original) * 100 if total_original > 0 else 0
            else:
                # 只有一种电价类型的情况
                if row['original_economy_7']:
                    row['saving'] = row['original_economy_7'] - row['optimized_economy_7']
                    row['saving_rate'] = (row['saving'] / row['original_economy_7']) * 100 if row['original_economy_7'] > 0 else 0
                elif row['original_economy_10']:
                    row['saving'] = row['original_economy_10'] - row['optimized_economy_10']
                    row['saving_rate'] = (row['saving'] / row['original_economy_10']) * 100 if row['original_economy_10'] > 0 else 0
                else:
                    row['saving'] = None
                    row['saving_rate'] = None
            
            table_data.append(row)
        
        # 创建最终表格DataFrame
        table_df = pd.DataFrame(table_data)
        
        return table_df, all_results
    
    def format_table_output(self, table_df):
        """格式化表格输出"""
        print("\n" + "="*120)
        print("基于规则的事件调度费用汇总表格")
        print("="*120)
        print()

        # 表头
        print(f"{'':15} | {'Original':35} | {'Optimized':35} | {'Saving':10} | {'Saving Rate'}")
        print(f"{'':15} | {'Economy 7':17} | {'Economy 10':17} | {'Economy 7':17} | {'Economy 10':17} | {'(most)':10} | {'(%)'}")
        print("-" * 120)

        # 数据行
        for _, row in table_df.iterrows():
            house_id = row['house_id']

            # 格式化数值，None显示为"-"
            orig_e7 = f"{row['original_economy_7']:.2f}" if row['original_economy_7'] is not None else "—"
            orig_e10 = f"{row['original_economy_10']:.2f}" if row['original_economy_10'] is not None else "—"
            opt_e7 = f"{row['optimized_economy_7']:.2f}" if row['optimized_economy_7'] is not None else "—"
            opt_e10 = f"{row['optimized_economy_10']:.2f}" if row['optimized_economy_10'] is not None else "—"
            saving = f"{row['saving']:.2f}" if row['saving'] is not None else "—"
            saving_rate = f"{row['saving_rate']:.2f}" if row['saving_rate'] is not None else "—"

            print(f"{house_id:15} | {orig_e7:17} | {orig_e10:17} | {opt_e7:17} | {opt_e10:17} | {saving:10} | {saving_rate}")

        print("-" * 120)
        print()

        # 添加数据状态说明
        e7_count = sum(1 for _, row in table_df.iterrows() if row['original_economy_7'] is not None)
        e10_count = sum(1 for _, row in table_df.iterrows() if row['original_economy_10'] is not None)

        print(f"数据状态:")
        print(f"  Economy_7: {e7_count}个房屋有数据")
        print(f"  Economy_10: {e10_count}个房屋有数据")
        print(f"  注: '—' 表示该电价类型下暂无数据或正在计算中")
    
    def save_results(self, table_df, all_results):
        """保存结果到文件"""
        # 保存详细表格
        table_file = f"{self.results_path}/cost_summary_table.csv"
        table_df.to_csv(table_file, index=False)
        logger.info(f"费用汇总表格已保存到: {table_file}")
        
        # 保存详细数据
        detailed_df = pd.DataFrame(all_results)
        detailed_file = f"{self.results_path}/detailed_cost_summary.csv"
        detailed_df.to_csv(detailed_file, index=False)
        logger.info(f"详细费用数据已保存到: {detailed_file}")
        
        # 保存统计汇总
        summary_stats = {
            'total_houses': len(all_results),
            'economy_7_houses': len([r for r in all_results if r['tariff_type'] == 'Economy_7']),
            'economy_10_houses': len([r for r in all_results if r['tariff_type'] == 'Economy_10']),
            'total_original_cost': sum(r['total_original_cost'] for r in all_results),
            'total_optimized_cost': sum(r['total_optimized_cost'] for r in all_results),
            'total_savings': sum(r['total_savings'] for r in all_results),
            'average_savings_rate': np.mean([r['savings_rate'] for r in all_results if r['savings_rate'] is not None])
        }
        
        stats_file = f"{self.results_path}/overall_cost_summary_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(summary_stats, f, indent=2)
        logger.info(f"统计汇总已保存到: {stats_file}")
        
        # 打印统计信息
        print(f"\n总体统计:")
        print(f"  总房屋数: {summary_stats['total_houses']}")
        print(f"  Economy_7房屋数: {summary_stats['economy_7_houses']}")
        print(f"  Economy_10房屋数: {summary_stats['economy_10_houses']}")
        print(f"  总原始费用: £{summary_stats['total_original_cost']:.2f}")
        print(f"  总优化后费用: £{summary_stats['total_optimized_cost']:.2f}")
        print(f"  总节约: £{summary_stats['total_savings']:.2f}")
        print(f"  平均节约率: {summary_stats['average_savings_rate']:.2f}%")


def main():
    """主函数"""
    generator = CostSummaryTableGenerator()
    
    # 生成汇总表格
    table_df, all_results = generator.generate_summary_table()
    
    if table_df is not None:
        # 格式化输出表格
        generator.format_table_output(table_df)
        
        # 保存结果
        generator.save_results(table_df, all_results)
    else:
        logger.error("生成表格失败")


if __name__ == "__main__":
    main()
