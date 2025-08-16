#!/usr/bin/env python3
"""
直接显示19个家庭的完整结果表格
类似论文中的格式
"""

import pandas as pd
import json
import os
from typing import Dict

def load_all_results() -> Dict:
    """加载所有处理结果"""
    results = {
        "Economy_7": {},
        "Economy_10": {}
    }
    
    for tariff_type in ["Economy_7", "Economy_10"]:
        results_dir = f"results/{tariff_type}"
        if not os.path.exists(results_dir):
            continue
        
        house_dirs = [d for d in os.listdir(results_dir) if d.startswith('house')]
        for house_dir in house_dirs:
            json_file = os.path.join(results_dir, house_dir, f"cost_summary_{house_dir}_{tariff_type}.json")
            
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                results[tariff_type][house_dir] = data
    
    return results

def display_complete_table():
    """显示完整的结果表格"""
    print("📊 Gurobi优化结果完整表格 (19个家庭)")
    print("=" * 140)
    
    # 加载结果
    results = load_all_results()
    
    # 获取所有house并排序
    all_houses = set()
    for tariff_type in results:
        all_houses.update(results[tariff_type].keys())
    all_houses = sorted(all_houses, key=lambda x: int(x.replace('house', '')))
    
    # 表头
    print(f"{'':12} {'Original':24} {'Optimized':24} {'Saving':20} {'Saving Rate'}")
    print(f"{'House':<12} {'Economy 7':<12} {'Economy 10':<12} {'Economy 7':<12} {'Economy 10':<12} {'(most)':<12} {'(%)':<8}")
    print("-" * 140)
    
    # 统计变量
    total_e7_original = 0
    total_e7_optimized = 0
    total_e10_original = 0
    total_e10_optimized = 0
    e7_better_count = 0
    e10_better_count = 0
    
    # 显示每个house的数据
    for house in all_houses:
        house_num = house.replace('house', '')
        
        # Economy_7数据
        if house in results["Economy_7"]:
            e7_data = results["Economy_7"][house]
            e7_original = e7_data["total_original_cost"]
            e7_optimized = e7_data["total_optimized_cost"]
            e7_savings = e7_data["total_savings"]
            e7_rate = e7_data["overall_savings_percentage"]
            
            total_e7_original += e7_original
            total_e7_optimized += e7_optimized
        else:
            e7_original = e7_optimized = e7_savings = e7_rate = None
        
        # Economy_10数据
        if house in results["Economy_10"]:
            e10_data = results["Economy_10"][house]
            e10_original = e10_data["total_original_cost"]
            e10_optimized = e10_data["total_optimized_cost"]
            e10_savings = e10_data["total_savings"]
            e10_rate = e10_data["overall_savings_percentage"]
            
            total_e10_original += e10_original
            total_e10_optimized += e10_optimized
        else:
            e10_original = e10_optimized = e10_savings = e10_rate = None
        
        # 确定最佳节约
        if e7_savings is not None and e10_savings is not None:
            if e7_savings >= e10_savings:
                max_savings = e7_savings
                max_rate = e7_rate
                e7_better_count += 1
            else:
                max_savings = e10_savings
                max_rate = e10_rate
                e10_better_count += 1
        elif e7_savings is not None:
            max_savings = e7_savings
            max_rate = e7_rate
            e7_better_count += 1
        elif e10_savings is not None:
            max_savings = e10_savings
            max_rate = e10_rate
            e10_better_count += 1
        else:
            max_savings = max_rate = None
        
        # 格式化输出
        e7_orig_str = f"{e7_original:.2f}" if e7_original is not None else "—"
        e10_orig_str = f"{e10_original:.2f}" if e10_original is not None else "—"
        e7_opt_str = f"{e7_optimized:.2f}" if e7_optimized is not None else "—"
        e10_opt_str = f"{e10_optimized:.2f}" if e10_optimized is not None else "—"
        max_sav_str = f"{max_savings:.2f}" if max_savings is not None else "—"
        max_rate_str = f"{max_rate:.2f}" if max_rate is not None else "—"
        
        print(f"{house_num:<12} {e7_orig_str:<12} {e10_orig_str:<12} {e7_opt_str:<12} {e10_opt_str:<12} {max_sav_str:<12} {max_rate_str:<8}")
    
    # 显示汇总统计
    print("-" * 140)
    print(f"{'TOTAL':<12} {total_e7_original:<12.2f} {total_e10_original:<12.2f} {total_e7_optimized:<12.2f} {total_e10_optimized:<12.2f}")
    
    # 计算总体节约率
    e7_total_savings = total_e7_original - total_e7_optimized
    e10_total_savings = total_e10_original - total_e10_optimized
    e7_total_rate = (e7_total_savings / total_e7_original * 100) if total_e7_original > 0 else 0
    e10_total_rate = (e10_total_savings / total_e10_original * 100) if total_e10_original > 0 else 0
    
    print(f"{'SAVINGS':<12} {e7_total_savings:<12.2f} {e10_total_savings:<12.2f}")
    print(f"{'RATE (%)':<12} {e7_total_rate:<12.2f} {e10_total_rate:<12.2f}")
    
    print("\n" + "=" * 140)
    print("📈 汇总统计")
    print(f"Economy_7  - 总原始成本: ${total_e7_original:.2f}, 总优化成本: ${total_e7_optimized:.2f}")
    print(f"           - 总节约: ${e7_total_savings:.2f}, 整体节约率: {e7_total_rate:.2f}%")
    print(f"Economy_10 - 总原始成本: ${total_e10_original:.2f}, 总优化成本: ${total_e10_optimized:.2f}")
    print(f"           - 总节约: ${e10_total_savings:.2f}, 整体节约率: {e10_total_rate:.2f}%")
    print(f"\n🏆 最佳电价分布:")
    print(f"Economy_7更好: {e7_better_count} houses ({e7_better_count/19*100:.1f}%)")
    print(f"Economy_10更好: {e10_better_count} houses ({e10_better_count/19*100:.1f}%)")

def display_paper_style_table():
    """显示论文风格的表格"""
    print("\n\n📋 论文风格表格")
    print("=" * 100)
    
    results = load_all_results()
    all_houses = sorted([h for h in results["Economy_7"].keys()], key=lambda x: int(x.replace('house', '')))
    
    # 表头
    print(f"{'':8} {'Original':20} {'Optimized':20} {'Saving':12} {'Saving Rate'}")
    print(f"{'':8} {'Economy 7':<10} {'Economy 10':<10} {'Economy 7':<10} {'Economy 10':<10} {'(most)':<8} {'(%)':<8}")
    print("-" * 100)
    
    for house in all_houses:
        house_num = house.replace('house', '')
        
        # 获取数据
        e7_data = results["Economy_7"][house]
        e10_data = results["Economy_10"][house]
        
        e7_orig = e7_data["total_original_cost"]
        e7_opt = e7_data["total_optimized_cost"]
        e7_sav = e7_data["total_savings"]
        e7_rate = e7_data["overall_savings_percentage"]
        
        e10_orig = e10_data["total_original_cost"]
        e10_opt = e10_data["total_optimized_cost"]
        e10_sav = e10_data["total_savings"]
        e10_rate = e10_data["overall_savings_percentage"]
        
        # 最大节约
        if e7_sav >= e10_sav:
            max_sav = e7_sav
            max_rate = e7_rate
        else:
            max_sav = e10_sav
            max_rate = e10_rate
        
        print(f"{house_num:<8} {e7_orig:<10.2f} {e10_orig:<10.2f} {e7_opt:<10.2f} {e10_opt:<10.2f} {max_sav:<8.2f} {max_rate:<8.2f}")

def main():
    """主函数"""
    # 显示完整表格
    display_complete_table()
    
    # 显示论文风格表格
    display_paper_style_table()

if __name__ == "__main__":
    main()
