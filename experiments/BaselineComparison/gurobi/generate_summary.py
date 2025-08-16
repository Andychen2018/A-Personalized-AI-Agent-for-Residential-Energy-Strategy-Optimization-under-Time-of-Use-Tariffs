#!/usr/bin/env python3
"""
生成所有处理结果的汇总表格
类似论文中的表格格式
"""

import pandas as pd
import json
import os
from typing import Dict, List
import numpy as np

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

def generate_summary_table(results: Dict) -> pd.DataFrame:
    """生成汇总表格"""
    
    # 获取所有house的列表
    all_houses = set()
    for tariff_type in results:
        all_houses.update(results[tariff_type].keys())
    
    # 按house编号排序
    all_houses = sorted(all_houses, key=lambda x: int(x.replace('house', '')))
    
    table_data = []
    
    for house in all_houses:
        row = {"House": house}
        
        # Economy_7数据
        if house in results["Economy_7"]:
            e7_data = results["Economy_7"][house]
            row["Original_Economy_7"] = e7_data["total_original_cost"]
            row["Optimized_Economy_7"] = e7_data["total_optimized_cost"]
            row["Savings_Economy_7"] = e7_data["total_savings"]
            row["Savings_Rate_Economy_7"] = e7_data["overall_savings_percentage"]
        else:
            row["Original_Economy_7"] = None
            row["Optimized_Economy_7"] = None
            row["Savings_Economy_7"] = None
            row["Savings_Rate_Economy_7"] = None
        
        # Economy_10数据
        if house in results["Economy_10"]:
            e10_data = results["Economy_10"][house]
            row["Original_Economy_10"] = e10_data["total_original_cost"]
            row["Optimized_Economy_10"] = e10_data["total_optimized_cost"]
            row["Savings_Economy_10"] = e10_data["total_savings"]
            row["Savings_Rate_Economy_10"] = e10_data["overall_savings_percentage"]
        else:
            row["Original_Economy_10"] = None
            row["Optimized_Economy_10"] = None
            row["Savings_Economy_10"] = None
            row["Savings_Rate_Economy_10"] = None
        
        # 计算最大节约（如果两个电价都有数据）
        if row["Savings_Economy_7"] is not None and row["Savings_Economy_10"] is not None:
            row["Max_Savings"] = max(row["Savings_Economy_7"], row["Savings_Economy_10"])
            # 计算最大节约率（基于原始成本）
            if row["Savings_Economy_7"] >= row["Savings_Economy_10"]:
                row["Max_Savings_Rate"] = row["Savings_Rate_Economy_7"]
                row["Best_Tariff"] = "Economy_7"
            else:
                row["Max_Savings_Rate"] = row["Savings_Rate_Economy_10"]
                row["Best_Tariff"] = "Economy_10"
        elif row["Savings_Economy_7"] is not None:
            row["Max_Savings"] = row["Savings_Economy_7"]
            row["Max_Savings_Rate"] = row["Savings_Rate_Economy_7"]
            row["Best_Tariff"] = "Economy_7"
        elif row["Savings_Economy_10"] is not None:
            row["Max_Savings"] = row["Savings_Economy_10"]
            row["Max_Savings_Rate"] = row["Savings_Rate_Economy_10"]
            row["Best_Tariff"] = "Economy_10"
        else:
            row["Max_Savings"] = None
            row["Max_Savings_Rate"] = None
            row["Best_Tariff"] = None
        
        table_data.append(row)
    
    return pd.DataFrame(table_data)

def format_table_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """格式化表格用于显示"""
    display_df = pd.DataFrame()
    
    display_df["House"] = df["House"]
    
    # Original costs
    display_df["Original_E7"] = df["Original_Economy_7"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display_df["Original_E10"] = df["Original_Economy_10"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    
    # Optimized costs
    display_df["Optimized_E7"] = df["Optimized_Economy_7"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display_df["Optimized_E10"] = df["Optimized_Economy_10"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    
    # Savings
    display_df["Savings_E7"] = df["Savings_Economy_7"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display_df["Savings_E10"] = df["Savings_Economy_10"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    
    # Max savings
    display_df["Max_Savings"] = df["Max_Savings"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display_df["Max_Savings_Rate"] = df["Max_Savings_Rate"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    display_df["Best_Tariff"] = df["Best_Tariff"].fillna("—")
    
    return display_df

def calculate_statistics(df: pd.DataFrame) -> Dict:
    """计算统计信息"""
    stats = {}
    
    # 有效数据的house数量
    valid_e7 = df["Original_Economy_7"].notna().sum()
    valid_e10 = df["Original_Economy_10"].notna().sum()
    valid_both = (df["Original_Economy_7"].notna() & df["Original_Economy_10"].notna()).sum()
    
    stats["houses_with_e7"] = int(valid_e7)
    stats["houses_with_e10"] = int(valid_e10)
    stats["houses_with_both"] = int(valid_both)

    # Economy_7统计
    if valid_e7 > 0:
        e7_data = df[df["Original_Economy_7"].notna()]
        stats["e7_total_original"] = float(e7_data["Original_Economy_7"].sum())
        stats["e7_total_optimized"] = float(e7_data["Optimized_Economy_7"].sum())
        stats["e7_total_savings"] = float(e7_data["Savings_Economy_7"].sum())
        stats["e7_avg_savings_rate"] = float(e7_data["Savings_Rate_Economy_7"].mean())
        stats["e7_overall_savings_rate"] = float((stats["e7_total_savings"] / stats["e7_total_original"]) * 100)

    # Economy_10统计
    if valid_e10 > 0:
        e10_data = df[df["Original_Economy_10"].notna()]
        stats["e10_total_original"] = float(e10_data["Original_Economy_10"].sum())
        stats["e10_total_optimized"] = float(e10_data["Optimized_Economy_10"].sum())
        stats["e10_total_savings"] = float(e10_data["Savings_Economy_10"].sum())
        stats["e10_avg_savings_rate"] = float(e10_data["Savings_Rate_Economy_10"].mean())
        stats["e10_overall_savings_rate"] = float((stats["e10_total_savings"] / stats["e10_total_original"]) * 100)

    # 最佳电价统计
    if valid_both > 0:
        both_data = df[(df["Original_Economy_7"].notna()) & (df["Original_Economy_10"].notna())]
        stats["e7_better_count"] = int((both_data["Best_Tariff"] == "Economy_7").sum())
        stats["e10_better_count"] = int((both_data["Best_Tariff"] == "Economy_10").sum())
    
    return stats

def main():
    """主函数"""
    print("📊 生成Gurobi优化结果汇总表")
    print("=" * 80)
    
    # 加载所有结果
    print("🔍 加载处理结果...")
    results = load_all_results()
    
    print(f"找到的结果:")
    print(f"  Economy_7: {len(results['Economy_7'])} houses")
    print(f"  Economy_10: {len(results['Economy_10'])} houses")
    
    if not results["Economy_7"] and not results["Economy_10"]:
        print("❌ 没有找到任何处理结果!")
        return
    
    # 生成汇总表格
    print("\n📋 生成汇总表格...")
    df = generate_summary_table(results)
    
    # 计算统计信息
    stats = calculate_statistics(df)
    
    # 格式化显示表格
    display_df = format_table_for_display(df)
    
    # 保存详细数据
    df.to_csv("results/detailed_summary_table.csv", index=False)
    display_df.to_csv("results/formatted_summary_table.csv", index=False)
    
    # 显示表格
    print("\n📊 Gurobi优化结果汇总表")
    print("=" * 120)
    print(f"{'House':<8} {'Original':<20} {'Optimized':<20} {'Savings':<16} {'Max':<12} {'Best':<10}")
    print(f"{'':8} {'E7':<10} {'E10':<10} {'E7':<10} {'E10':<10} {'E7':<8} {'E10':<8} {'Savings':<8} {'Rate':<8} {'Tariff':<10}")
    print("-" * 120)
    
    for _, row in display_df.iterrows():
        print(f"{row['House']:<8} {row['Original_E7']:<10} {row['Original_E10']:<10} "
              f"{row['Optimized_E7']:<10} {row['Optimized_E10']:<10} "
              f"{row['Savings_E7']:<8} {row['Savings_E10']:<8} "
              f"{row['Max_Savings']:<8} {row['Max_Savings_Rate']:<8} {row['Best_Tariff']:<10}")
    
    # 显示统计信息
    print("\n📈 统计信息")
    print("=" * 60)
    print(f"处理的house数量:")
    print(f"  Economy_7: {stats['houses_with_e7']} houses")
    print(f"  Economy_10: {stats['houses_with_e10']} houses")
    print(f"  两种电价都有: {stats['houses_with_both']} houses")
    
    if "e7_total_original" in stats:
        print(f"\nEconomy_7 汇总:")
        print(f"  总原始成本: ${stats['e7_total_original']:.2f}")
        print(f"  总优化成本: ${stats['e7_total_optimized']:.2f}")
        print(f"  总节约: ${stats['e7_total_savings']:.2f}")
        print(f"  整体节约率: {stats['e7_overall_savings_rate']:.2f}%")
        print(f"  平均节约率: {stats['e7_avg_savings_rate']:.2f}%")
    
    if "e10_total_original" in stats:
        print(f"\nEconomy_10 汇总:")
        print(f"  总原始成本: ${stats['e10_total_original']:.2f}")
        print(f"  总优化成本: ${stats['e10_total_optimized']:.2f}")
        print(f"  总节约: ${stats['e10_total_savings']:.2f}")
        print(f"  整体节约率: {stats['e10_overall_savings_rate']:.2f}%")
        print(f"  平均节约率: {stats['e10_avg_savings_rate']:.2f}%")
    
    if "e7_better_count" in stats:
        print(f"\n🏆 最佳电价分布 (在{stats['houses_with_both']}个有两种电价的house中):")
        print(f"  Economy_7更好: {stats['e7_better_count']} houses ({stats['e7_better_count']/stats['houses_with_both']*100:.1f}%)")
        print(f"  Economy_10更好: {stats['e10_better_count']} houses ({stats['e10_better_count']/stats['houses_with_both']*100:.1f}%)")
    
    # 保存统计信息
    with open("results/summary_statistics.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n💾 结果已保存:")
    print(f"  详细数据: results/detailed_summary_table.csv")
    print(f"  格式化表格: results/formatted_summary_table.csv")
    print(f"  统计信息: results/summary_statistics.json")
    
    print(f"\n🎉 汇总表生成完成!")

if __name__ == "__main__":
    main()
