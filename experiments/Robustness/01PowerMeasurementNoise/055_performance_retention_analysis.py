#!/usr/bin/env python3
"""
功率测量噪声鲁棒性实验 - 性能保持率分析

计算在±10%功率测量噪声扰动下的系统性能保持率：
Performance Retention = (Original_Optimized_Cost - Noisy_Cost) / (Original_Optimized_Cost - Standard_Cost) × 100%

其中：
- Original_Optimized_Cost: 原始系统优化后的费用（表格中的Optimized列）
- Noisy_Cost: 噪声扰动下的费用（我们054_cost_cal.py的结果）
- Standard_Cost: 标准费用（无优化的基准）

性能保持率越高，说明系统在噪声扰动下的鲁棒性越好。
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import json

# 路径配置
BASE_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
COST_OUTPUT_DIR = os.path.join(BASE_DIR, "output", "06_cost_cal")

def load_original_optimized_results() -> Dict[str, Dict[str, float]]:
    """
    加载原始优化结果（表格9中的Optimized列数据）
    
    Returns:
        {house_id: {'Economy_7': cost, 'Economy_10': cost, 'Standard': cost}}
    """
    # 表格9中的原始优化结果数据
    original_data = {
        'house1': {'Standard': 624.11, 'Economy_7': 438.74, 'Economy_10': 424.87},
        'house2': {'Standard': 479.93, 'Economy_7': 379.43, 'Economy_10': 330.22},
        'house3': {'Standard': 998.95, 'Economy_7': 804.08, 'Economy_10': 685.07},
        'house20': {'Standard': 524.15, 'Economy_7': 423.84, 'Economy_10': 387.54},
        'house21': {'Standard': 495.20, 'Economy_7': 391.36, 'Economy_10': 352.66},
    }
    
    return original_data

def load_noisy_results() -> Dict[str, Dict[str, float]]:
    """
    从054_cost_cal.py的输出中提取噪声扰动下的结果（After列）

    Returns:
        {house_id: {'Economy_7': cost, 'Economy_10': cost}}
    """
    # 从054_cost_cal.py的运行结果中提取的"After"数据（噪声扰动后）
    noisy_data = {
        'house1': {'Economy_7': 440.66, 'Economy_10': 426.46},
        'house2': {'Economy_7': 450.15, 'Economy_10': 400.73},
        'house3': {'Economy_7': 831.78, 'Economy_10': 720.48},
        'house20': {'Economy_7': 451.40, 'Economy_10': 418.18},
        'house21': {'Economy_7': 424.86, 'Economy_10': 386.18},
    }

    return noisy_data

def calculate_performance_retention(original_optimized: float,
                                  noisy_cost: float) -> float:
    """
    计算性能保持率

    Performance Retention = (1 - (Noisy_Cost - Original_Optimized_Cost) / Original_Optimized_Cost) × 100%

    这个公式直接比较噪声扰动后的费用与原始优化费用的差异。
    - 如果噪声扰动后费用等于原始优化费用，保持率为100%
    - 如果噪声扰动后费用增加，保持率会下降

    Args:
        original_optimized: 原始优化后的费用（表格9中的Optimized列）
        noisy_cost: 噪声扰动下的费用（054输出的After列）

    Returns:
        性能保持率 (%)
    """
    if original_optimized <= 0:
        return 0.0

    # 计算费用增加比例
    cost_increase_ratio = (noisy_cost - original_optimized) / original_optimized

    # 性能保持率 = 100% - 费用增加比例
    retention_rate = (1 - cost_increase_ratio) * 100.0

    # 确保保持率不为负数
    retention_rate = max(0.0, retention_rate)

    return retention_rate

def calculate_cost_increase_rate(original_optimized: float, noisy_cost: float) -> float:
    """
    计算费用增加率
    
    Cost Increase Rate = (Noisy_Cost - Original_Optimized_Cost) / Original_Optimized_Cost × 100%
    
    Args:
        original_optimized: 原始优化后的费用
        noisy_cost: 噪声扰动下的费用
    
    Returns:
        费用增加率 (%)
    """
    if original_optimized <= 0:
        return 0.0
    
    increase_rate = ((noisy_cost - original_optimized) / original_optimized) * 100.0
    return increase_rate

def analyze_performance_retention():
    """
    分析功率测量噪声对系统性能的影响
    """
    print("🚀 功率测量噪声鲁棒性实验 - 性能保持率分析")
    print("=" * 80)
    
    # 加载数据
    original_data = load_original_optimized_results()
    noisy_data = load_noisy_results()
    
    # 分析结果
    results = []
    
    print(f"\n📊 性能保持率分析结果:")
    print("=" * 100)
    header = f"{'House':>6} {'Tariff':>10} {'Original':>10} {'Noisy':>10} {'Cost Inc':>10} {'Perf Ret':>10} {'Status':>10}"
    print(header)
    print("-" * 100)

    for house_id in sorted(original_data.keys()):
        for tariff in ['Economy_7', 'Economy_10']:
            if house_id in noisy_data and tariff in noisy_data[house_id]:
                original_cost = original_data[house_id][tariff]
                noisy_cost = noisy_data[house_id][tariff]

                # 计算性能保持率（直接比较原始优化费用与噪声扰动后费用）
                retention_rate = calculate_performance_retention(original_cost, noisy_cost)

                # 计算费用增加率
                cost_increase_rate = calculate_cost_increase_rate(original_cost, noisy_cost)

                # 判断性能状态
                if retention_rate >= 95:
                    status = "优秀"
                elif retention_rate >= 90:
                    status = "良好"
                elif retention_rate >= 80:
                    status = "一般"
                else:
                    status = "较差"

                print(f"{house_id:>6} {tariff:>10} {original_cost:>10.2f} {noisy_cost:>10.2f} {cost_increase_rate:>9.1f}% {retention_rate:>9.1f}% {status:>10}")

                results.append({
                    'house_id': house_id,
                    'tariff': tariff,
                    'original_optimized_cost': original_cost,
                    'noisy_cost': noisy_cost,
                    'cost_increase_rate': cost_increase_rate,
                    'performance_retention_rate': retention_rate,
                    'status': status
                })
    
    print("-" * 120)
    
    # 计算总体统计
    df_results = pd.DataFrame(results)
    
    print(f"\n📈 总体统计:")
    print("=" * 60)
    
    # 按电价方案分组统计
    for tariff in ['Economy_7', 'Economy_10']:
        tariff_data = df_results[df_results['tariff'] == tariff]
        
        avg_retention = tariff_data['performance_retention_rate'].mean()
        min_retention = tariff_data['performance_retention_rate'].min()
        max_retention = tariff_data['performance_retention_rate'].max()
        std_retention = tariff_data['performance_retention_rate'].std()
        
        avg_cost_increase = tariff_data['cost_increase_rate'].mean()
        
        print(f"\n🔋 {tariff}:")
        print(f"   平均性能保持率: {avg_retention:.1f}%")
        print(f"   性能保持率范围: {min_retention:.1f}% - {max_retention:.1f}%")
        print(f"   性能保持率标准差: {std_retention:.1f}%")
        print(f"   平均费用增加率: {avg_cost_increase:.1f}%")
        
        # 统计各性能等级的房屋数量
        status_counts = tariff_data['status'].value_counts()
        print(f"   性能等级分布: {dict(status_counts)}")
    
    # 整体统计
    overall_avg_retention = df_results['performance_retention_rate'].mean()
    overall_avg_cost_increase = df_results['cost_increase_rate'].mean()
    
    print(f"\n🎯 整体性能:")
    print(f"   平均性能保持率: {overall_avg_retention:.1f}%")
    print(f"   平均费用增加率: {overall_avg_cost_increase:.1f}%")
    
    # 鲁棒性评估
    if overall_avg_retention >= 95:
        robustness_level = "高鲁棒性"
    elif overall_avg_retention >= 90:
        robustness_level = "中等鲁棒性"
    elif overall_avg_retention >= 80:
        robustness_level = "低鲁棒性"
    else:
        robustness_level = "鲁棒性较差"
    
    print(f"   系统鲁棒性评估: {robustness_level}")
    
    # 保存结果
    output_file = os.path.join(BASE_DIR, "output", "performance_retention_analysis.csv")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_results.to_csv(output_file, index=False)
    print(f"\n💾 详细结果已保存到: {output_file}")
    
    return df_results

def main():
    """主函数"""
    analyze_performance_retention()

if __name__ == "__main__":
    main()
