#!/usr/bin/env python3
"""
约束解析错误鲁棒性分析模块
整合费用计算和性能保持率分析
"""

import os
import pandas as pd
import json
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple

class RobustnessAnalyzer:
    def __init__(self):
        self.base_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all"
        self.target_houses = ["house1", "house2", "house3", "house20", "house21"]
        self.tariff_types = ['Economy_7', 'Economy_10']
        
        # 路径配置
        self.error_cost_dir = os.path.join(self.base_dir, "output/06_cost_cal")
        self.baseline_cost_dir = "/home/deep/TimeSeries/Agent_V2/output/06_cost_cal/UK"
        
        # 标准费用（无优化）- 从表格9获取
        self.standard_costs = {
            "house1": 624.11,
            "house2": 479.93,
            "house3": 998.95,
            "house20": 524.15,  # 对应表格中的house20
            "house21": 495.20   # 对应表格中的house21
        }

        # 基准优化费用（正确约束下的优化结果）- 从表格9的Optimized列获取
        self.baseline_optimized_costs = {
            "Economy_7": {
                "house1": 438.74,
                "house2": 379.43,
                "house3": 804.08,
                "house20": 423.84,
                "house21": 391.36
            },
            "Economy_10": {
                "house1": 424.87,
                "house2": 330.22,
                "house3": 685.07,
                "house20": 387.54,
                "house21": 352.66
            }
        }

        # 扰动后费用（04_all实验的实际结果）- 用户提供的正确数据
        self.disturbed_costs = {
            "Economy_7": {
                "house1": 440.56,
                "house2": 450.15,
                "house3": 833.11,
                "house20": 451.33,
                "house21": 424.88
            },
            "Economy_10": {
                "house1": 427.15,
                "house2": 400.77,
                "house3": 735.43,
                "house20": 418.99,
                "house21": 387.16
            }
        }
    
    def load_cost_data(self, cost_dir: str, tariff_type: str, house_id: str) -> Dict:
        """加载费用数据"""
        migrated_file = os.path.join(cost_dir, tariff_type, house_id, "migrated_costs.csv")
        non_migrated_file = os.path.join(cost_dir, tariff_type, house_id, "non_migrated_costs.csv")
        
        migrated_cost = 0.0
        non_migrated_cost = 0.0
        
        try:
            if os.path.exists(migrated_file):
                df_mig = pd.read_csv(migrated_file)
                # 迁移事件使用调度后费用
                if 'sched_total_cost' in df_mig.columns:
                    migrated_cost = df_mig['sched_total_cost'].sum()

            if os.path.exists(non_migrated_file):
                df_non = pd.read_csv(non_migrated_file)
                # 未迁移事件使用原始费用
                if 'total_cost' in df_non.columns:
                    non_migrated_cost = df_non['total_cost'].sum()
                    
        except Exception as e:
            print(f"⚠️ 加载费用数据失败 {tariff_type}/{house_id}: {e}")
        
        total_cost = migrated_cost + non_migrated_cost
        return {
            'migrated_cost': migrated_cost,
            'non_migrated_cost': non_migrated_cost,
            'total_cost': total_cost
        }
    
    def calculate_savings_retention(self) -> Dict:
        """计算节省能力保持率"""
        print("📊 计算节省能力保持率...")
        print("="*80)
        
        results = {}
        
        for tariff_type in self.tariff_types:
            print(f"\n🏷️ 分析 {tariff_type}:")
            print("-"*60)
            
            house_results = {}
            baseline_savings = []
            error_savings = []
            retention_rates = []
            
            for house_id in self.target_houses:
                # 获取标准费用（无优化）
                standard_cost = self.standard_costs.get(house_id, 0)

                # 获取基线优化费用（正确约束的优化结果）
                baseline_optimized_cost = self.baseline_optimized_costs.get(tariff_type, {}).get(house_id, 0)

                # 获取扰动后费用（04_all实验的实际结果）
                error_optimized_cost = self.disturbed_costs.get(tariff_type, {}).get(house_id, 0)
                
                # 计算节省能力
                baseline_savings_amount = standard_cost - baseline_optimized_cost  # 正确约束的节省能力
                error_savings_amount = standard_cost - error_optimized_cost      # 错误约束的节省能力

                # 计算性能保持率（费用越低越好，所以基准费用/错误费用）
                if error_optimized_cost > 0:
                    performance_retention = (baseline_optimized_cost / error_optimized_cost) * 100
                else:
                    performance_retention = 0.0

                # 计算费用增加率
                cost_increase_rate = ((error_optimized_cost - baseline_optimized_cost) / baseline_optimized_cost) * 100 if baseline_optimized_cost > 0 else 0
                
                house_results[house_id] = {
                    'standard_cost': standard_cost,
                    'baseline_optimized_cost': baseline_optimized_cost,
                    'error_optimized_cost': error_optimized_cost,
                    'baseline_savings': baseline_savings_amount,
                    'error_savings': error_savings_amount,
                    'performance_retention': performance_retention,
                    'cost_increase_rate': cost_increase_rate,
                    'cost_degradation': error_optimized_cost - baseline_optimized_cost
                }

                baseline_savings.append(baseline_savings_amount)
                error_savings.append(error_savings_amount)
                retention_rates.append(performance_retention)
                
                print(f"   🏠 {house_id}:")
                print(f"      标准费用: £{standard_cost:.2f}")
                print(f"      基线优化费用: £{baseline_optimized_cost:.2f}")
                print(f"      错误约束优化费用: £{error_optimized_cost:.2f}")
                print(f"      基线节省: £{baseline_savings_amount:.2f}")
                print(f"      错误约束节省: £{error_savings_amount:.2f}")
                print(f"      性能保持率: {performance_retention:.1f}%")
                print(f"      费用增加率: {cost_increase_rate:+.1f}%")
                print(f"      费用恶化: £{error_optimized_cost - baseline_optimized_cost:+.2f}")
                print()
            
            # 计算统计指标
            if baseline_savings and error_savings:
                avg_baseline_savings = np.mean(baseline_savings)
                avg_error_savings = np.mean(error_savings)
                avg_retention_rate = np.mean(retention_rates)
                
                # 配对t检验（比较节省金额）
                try:
                    t_stat, p_value = stats.ttest_rel(baseline_savings, error_savings)
                    
                    results[tariff_type] = {
                        'house_results': house_results,
                        'avg_baseline_savings': avg_baseline_savings,
                        'avg_error_savings': avg_error_savings,
                        'avg_retention_rate': avg_retention_rate,
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'significant': p_value < 0.05
                    }
                    
                    print(f"   📈 {tariff_type} 汇总:")
                    print(f"      平均基线节省: £{avg_baseline_savings:.2f}")
                    print(f"      平均错误约束节省: £{avg_error_savings:.2f}")
                    print(f"      平均节省能力保持率: {avg_retention_rate:.1f}%")
                    print(f"      t统计量: {t_stat:.3f}")
                    print(f"      p值: {p_value:.3f}")
                    print(f"      统计显著性: {'是' if p_value < 0.05 else '否'}")
                    
                except Exception as e:
                    print(f"      ⚠️ 统计检验失败: {e}")
        
        return results
    
    def print_comparison_table(self, results: Dict):
        """打印对比表格"""
        print(f"\n📊 费用对比表格 (类似Table 9):")
        print("="*120)
        
        header = f"{'House':6} {'Standard':>10} {'Economy_7':>20} {'Economy_10':>20} {'Retention Rate':>25}"
        subheader = f"{'ID':6} {'Cost':>10} {'Original':>10} {'Optimized':>10} {'Original':>10} {'Optimized':>10} {'E7':>10} {'E10':>10} {'Avg':>10}"
        
        print(header)
        print(subheader)
        print("-"*120)
        
        for house_id in self.target_houses:
            standard = self.standard_costs.get(house_id, 0)

            # Economy_7数据
            e7_data = results.get('Economy_7', {}).get('house_results', {}).get(house_id, {})
            e7_baseline = self.baseline_optimized_costs.get('Economy_7', {}).get(house_id, 0)  # 使用硬编码基准
            e7_optimized = e7_data.get('error_optimized_cost', 0)
            e7_retention = e7_data.get('performance_retention', 0)

            # Economy_10数据
            e10_data = results.get('Economy_10', {}).get('house_results', {}).get(house_id, {})
            e10_baseline = self.baseline_optimized_costs.get('Economy_10', {}).get(house_id, 0)  # 使用硬编码基准
            e10_optimized = e10_data.get('error_optimized_cost', 0)
            e10_retention = e10_data.get('performance_retention', 0)

            avg_retention = (e7_retention + e10_retention) / 2

            print(f"{house_id:6} £{standard:>8.2f} £{e7_baseline:>8.2f} £{e7_optimized:>8.2f} "
                  f"£{e10_baseline:>8.2f} £{e10_optimized:>8.2f} {e7_retention:>8.1f}% "
                  f"{e10_retention:>8.1f}% {avg_retention:>8.1f}%")
        
        print("-"*120)
    
    def generate_final_report(self) -> Dict:
        """生成最终报告"""
        print("🚀 约束解析错误鲁棒性分析 - 节省能力保持率")
        print("="*80)
        
        # 1. 约束错误统计
        error_log_file = os.path.join(self.base_dir, "Error_data/UK/constraint_corruption_log.json")
        error_stats = None
        
        if os.path.exists(error_log_file):
            try:
                with open(error_log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                total_constraints = sum(
                    house_data['total_constraints'] 
                    for tariff_data in log_data.values() 
                    for house_data in tariff_data.values()
                )
                total_corrupted = sum(
                    house_data['corrupted_constraints']
                    for tariff_data in log_data.values() 
                    for house_data in tariff_data.values()
                )
                
                error_stats = {
                    'total_constraints': total_constraints,
                    'total_corrupted': total_corrupted,
                    'error_rate': total_corrupted / total_constraints * 100 if total_constraints > 0 else 0
                }
                
                print(f"📋 约束错误统计:")
                print(f"   总约束数: {total_constraints}")
                print(f"   损坏约束数: {total_corrupted}")
                print(f"   错误率: {error_stats['error_rate']:.1f}%")
                
            except Exception as e:
                print(f"⚠️ 加载约束错误统计失败: {e}")
        
        # 2. 计算节省能力保持率
        savings_results = self.calculate_savings_retention()
        
        # 3. 打印对比表格
        self.print_comparison_table(savings_results)
        
        # 4. 总体结论
        print(f"\n🎯 实验结论:")
        print("="*60)
        
        all_retention_rates = []
        for tariff_type, data in savings_results.items():
            avg_retention = data['avg_retention_rate']
            all_retention_rates.append(avg_retention)
            print(f"✅ {tariff_type}: 平均节省能力保持率 {avg_retention:.1f}%")
        
        if all_retention_rates:
            overall_retention = np.mean(all_retention_rates)
            print(f"\n🏆 总体平均节省能力保持率: {overall_retention:.1f}%")
            
            # 与预期结果比较
            expected_retention = 91.7  # 根据表格8的预期
            print(f"📊 预期节省能力保持率: {expected_retention:.1f}%")
            print(f"📈 实际vs预期: {overall_retention - expected_retention:+.1f}%")
            
            if abs(overall_retention - expected_retention) <= 5:
                print("✅ 实验结果符合预期范围！")
            elif overall_retention > expected_retention:
                print("🎉 实验结果优于预期！系统鲁棒性很强")
            else:
                print("⚠️ 实验结果低于预期，需要进一步分析")
        
        # 5. 保存结果
        final_results = {
            'constraint_errors': error_stats,
            'savings_analysis': savings_results,
            'overall_retention_rate': overall_retention if all_retention_rates else None,
            'expected_retention_rate': 91.7,
            'experiment_metadata': {
                'target_houses': self.target_houses,
                'tariff_types': self.tariff_types,
                'standard_costs': self.standard_costs
            }
        }
        
        results_file = os.path.join(self.base_dir, "robustness_savings_analysis.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📁 详细结果已保存: {results_file}")
        
        return final_results

def main():
    """主函数"""
    analyzer = RobustnessAnalyzer()
    
    try:
        results = analyzer.generate_final_report()
        return True
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
