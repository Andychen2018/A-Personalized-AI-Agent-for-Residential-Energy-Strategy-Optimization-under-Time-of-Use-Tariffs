#!/usr/bin/env python3
"""
生成部分费用汇总表格 - 显示当前已完成的数据
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

def check_data_availability():
    """检查当前数据可用性"""
    results_path = "/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results"
    
    data_status = {
        'Economy_7': {},
        'Economy_10': {}
    }
    
    for tariff_type in ['Economy_7', 'Economy_10']:
        tariff_dir = f"{results_path}/{tariff_type}"
        if os.path.exists(tariff_dir):
            house_dirs = [d for d in os.listdir(tariff_dir) if d.startswith('house')]
            for house_dir in house_dirs:
                house_id = house_dir.replace('house', '')
                
                # 检查已迁移事件数据
                shifted_file = f"{tariff_dir}/{house_dir}/cost_calculation_summary_{house_dir}_{tariff_type}.json"
                shifted_available = os.path.exists(shifted_file)
                
                # 检查未迁移事件数据
                unshifted_file = f"{tariff_dir}/{house_dir}/unshifted_events_cost_summary_{house_dir}_{tariff_type}.json"
                unshifted_available = os.path.exists(unshifted_file)
                
                data_status[tariff_type][house_id] = {
                    'shifted': shifted_available,
                    'unshifted': unshifted_available,
                    'complete': shifted_available and unshifted_available
                }
    
    return data_status

def load_house_data(house_id, tariff_type, results_path):
    """加载单个房屋的数据"""
    house_dir = f"house{house_id}"
    
    # 加载已迁移事件数据
    shifted_file = f"{results_path}/{tariff_type}/{house_dir}/cost_calculation_summary_{house_dir}_{tariff_type}.json"
    shifted_data = None
    if os.path.exists(shifted_file):
        try:
            with open(shifted_file, 'r') as f:
                shifted_data = json.load(f)
        except Exception as e:
            logger.warning(f"加载已迁移事件数据失败 {house_id}-{tariff_type}: {e}")
    
    # 加载未迁移事件数据
    unshifted_file = f"{results_path}/{tariff_type}/{house_dir}/unshifted_events_cost_summary_{house_dir}_{tariff_type}.json"
    unshifted_data = None
    if os.path.exists(unshifted_file):
        try:
            with open(unshifted_file, 'r') as f:
                unshifted_data = json.load(f)
        except Exception as e:
            logger.warning(f"加载未迁移事件数据失败 {house_id}-{tariff_type}: {e}")
    
    if shifted_data and unshifted_data:
        # 计算总费用
        original_cost = shifted_data.get('total_original_cost_calculated', 0) + unshifted_data.get('total_unshifted_cost', 0)
        optimized_cost = shifted_data.get('total_optimized_cost_calculated', 0) + unshifted_data.get('total_unshifted_cost', 0)
        savings = original_cost - optimized_cost
        savings_rate = (savings / original_cost * 100) if original_cost > 0 else 0
        
        return {
            'original_cost': original_cost,
            'optimized_cost': optimized_cost,
            'savings': savings,
            'savings_rate': savings_rate
        }
    
    return None

def generate_partial_summary():
    """生成部分汇总表格"""
    results_path = "/home/deep/TimeSeries/Agent_V2/experiments/BaselineComparison/rule_based/results"
    
    # 检查数据可用性
    data_status = check_data_availability()
    
    print("\n" + "="*120)
    print("基于规则的事件调度费用汇总表格 (部分数据)")
    print("="*120)
    print()
    
    # 获取所有房屋ID
    all_house_ids = set()
    for tariff_type in ['Economy_7', 'Economy_10']:
        all_house_ids.update(data_status[tariff_type].keys())
    
    house_ids = sorted(list(all_house_ids), key=lambda x: int(x))
    
    # 表头
    print(f"{'':15} | {'Original':35} | {'Optimized':35} | {'Saving':10} | {'Saving Rate'} | {'Status'}")
    print(f"{'':15} | {'Economy 7':17} | {'Economy 10':17} | {'Economy 7':17} | {'Economy 10':17} | {'(most)':10} | {'(%)'} | {'E7/E10'}")
    print("-" * 140)
    
    # 数据行
    for house_id in house_ids:
        # Economy_7数据
        e7_data = load_house_data(house_id, 'Economy_7', results_path)
        e7_status = data_status['Economy_7'].get(house_id, {})
        
        # Economy_10数据
        e10_data = load_house_data(house_id, 'Economy_10', results_path)
        e10_status = data_status['Economy_10'].get(house_id, {})
        
        # 格式化数值
        orig_e7 = f"{e7_data['original_cost']:.2f}" if e7_data else "—"
        orig_e10 = f"{e10_data['original_cost']:.2f}" if e10_data else "—"
        opt_e7 = f"{e7_data['optimized_cost']:.2f}" if e7_data else "—"
        opt_e10 = f"{e10_data['optimized_cost']:.2f}" if e10_data else "—"
        
        # 计算总节约
        if e7_data and e10_data:
            total_savings = e7_data['savings'] + e10_data['savings']
            total_original = e7_data['original_cost'] + e10_data['original_cost']
            total_savings_rate = (total_savings / total_original * 100) if total_original > 0 else 0
            saving = f"{total_savings:.2f}"
            saving_rate = f"{total_savings_rate:.2f}"
        elif e7_data:
            saving = f"{e7_data['savings']:.2f}"
            saving_rate = f"{e7_data['savings_rate']:.2f}"
        elif e10_data:
            saving = f"{e10_data['savings']:.2f}"
            saving_rate = f"{e10_data['savings_rate']:.2f}"
        else:
            saving = "—"
            saving_rate = "—"
        
        # 状态
        e7_complete = e7_status.get('complete', False)
        e10_complete = e10_status.get('complete', False)
        status = f"{'✓' if e7_complete else '○'}/{'✓' if e10_complete else '○'}"
        
        print(f"house{house_id:10} | {orig_e7:17} | {orig_e10:17} | {opt_e7:17} | {opt_e10:17} | {saving:10} | {saving_rate:8} | {status}")
    
    print("-" * 140)
    print()
    
    # 统计信息
    e7_complete_count = sum(1 for house_id in house_ids if data_status['Economy_7'].get(house_id, {}).get('complete', False))
    e10_complete_count = sum(1 for house_id in house_ids if data_status['Economy_10'].get(house_id, {}).get('complete', False))
    
    print(f"数据完成状态:")
    print(f"  Economy_7: {e7_complete_count}/{len(house_ids)} 个房屋完成")
    print(f"  Economy_10: {e10_complete_count}/{len(house_ids)} 个房屋完成")
    print(f"  总进度: {(e7_complete_count + e10_complete_count)}/{len(house_ids) * 2} ({(e7_complete_count + e10_complete_count)/(len(house_ids) * 2)*100:.1f}%)")
    print()
    print(f"图例: ✓=完成, ○=未完成或计算中")

if __name__ == "__main__":
    generate_partial_summary()
