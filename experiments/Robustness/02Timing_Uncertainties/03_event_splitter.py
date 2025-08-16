#!/usr/bin/env python3
"""
时间不确定性鲁棒性实验 - Event Splitter (简化版本)

根据成功迁移与未迁移，将事件分为两类并输出为CSV：
- migrated_events.csv（成功迁移的事件）
- non_migrated_events.csv（未迁移的事件 = 全量事件 - 成功迁移事件）

专门适配时间不确定性扰动实验，只支持Economy_7和Economy_10
"""

import os
import pandas as pd
from typing import Dict, List

# 🎯 时间不确定性实验路径配置
BASE_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties"
OUTPUT_BASE = os.path.join(BASE_DIR, 'output')

# 输入路径：使用时间不确定性实验的调度结果
SCHEDULED_BASE = os.path.join(OUTPUT_BASE, '05_Collision_Resolved_Scheduling')

# 输出路径：时间不确定性实验的事件分割结果
COST_CAL_BASE = os.path.join(OUTPUT_BASE, '05_event_split')

# 原始事件数据路径（用于获取全量事件）
ORIGINAL_DATA_BASE = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties/Error_data/UK"

# 支持的电价类型和目标房屋
SUPPORTED_TARIFFS = ['Economy_7', 'Economy_10']
TARGET_HOUSES = ['house1', 'house2', 'house3', 'house20', 'house21']


def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def load_full_events(house_id: str) -> pd.DataFrame:
    """加载全量事件数据 - 使用原始事件数据（无扰动）"""
    # 🎯 使用原始事件数据，不是扰动后的数据
    path = os.path.join("/home/deep/TimeSeries/Agent_V2/output/02_event_segments",
                       house_id, f"02_appliance_event_segments_id_{house_id}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"原始事件文件不存在: {path}")

    df = pd.read_csv(path)
    if 'start_time' in df.columns:
        df['start_time'] = pd.to_datetime(df['start_time'])
    if 'end_time' in df.columns:
        df['end_time'] = pd.to_datetime(df['end_time'])
    return df


def load_scheduled_events(tariff_name: str, house_id: str) -> pd.DataFrame:
    """加载调度事件文件 - 时间不确定性实验版本"""
    if tariff_name not in SUPPORTED_TARIFFS:
        raise ValueError(f"时间不确定性实验不支持的电价类型: {tariff_name}")
    
    path = os.path.join(SCHEDULED_BASE, tariff_name, house_id, 'scheduled_events.csv')
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"调度事件文件不存在: {path}")

    df = pd.read_csv(path)
    # 标准化字段
    if 'scheduled_start_time' in df.columns:
        df['scheduled_start_time'] = pd.to_datetime(df['scheduled_start_time'])
    if 'scheduled_end_time' in df.columns:
        df['scheduled_end_time'] = pd.to_datetime(df['scheduled_end_time'])
    if 'original_start_time' in df.columns:
        df['original_start_time'] = pd.to_datetime(df['original_start_time'])
    if 'original_end_time' in df.columns:
        df['original_end_time'] = pd.to_datetime(df['original_end_time'])
    return df


def split_events_for_house(tariff_name: str, house_id: str) -> Dict[str, Dict[str, str]]:
    """为某个house输出迁移/未迁移事件CSV - 时间不确定性实验版本"""
    if tariff_name not in SUPPORTED_TARIFFS:
        raise ValueError(f"时间不确定性实验不支持的电价类型: {tariff_name}")
    
    print(f"  🏠 处理 {house_id} - {tariff_name}")

    # 🎯 加载原始全量事件数据（无扰动）
    df_full = load_full_events(house_id)

    # 基础列检查
    required_cols = ['event_id', 'appliance_name', 'start_time', 'end_time', 'duration(min)', 'energy(W)']
    for col in required_cols:
        if col not in df_full.columns:
            raise ValueError(f"全量事件数据缺少列: {col}")

    # 加载调度结果
    df_sched = load_scheduled_events(tariff_name, house_id)
    df_success = df_sched[df_sched['schedule_status'] == 'SUCCESS'].copy()
    
    # 创建输出目录
    out_dir = os.path.join(COST_CAL_BASE, tariff_name, house_id)
    ensure_dir(out_dir)
    
    # 获取迁移成功的事件ID
    migrated_ids = set(df_success['event_id'].tolist())
    
    # 迁移事件：调度成功的事件
    df_migrated = df_success[['event_id', 'appliance_name', 'original_start_time', 'original_end_time',
                              'scheduled_start_time', 'scheduled_end_time', 'schedule_status']].copy()
    df_migrated = df_migrated.merge(
        df_full[['event_id', 'duration(min)', 'energy(W)']], on='event_id', how='left'
    )
    
    # 未迁移事件：全量事件 - 迁移事件
    df_non_migrated = df_full[~df_full['event_id'].isin(migrated_ids)].copy()
    if 'start_time' in df_non_migrated.columns:
        df_non_migrated.rename(columns={'start_time': 'original_start_time', 'end_time': 'original_end_time'}, inplace=True)
    
    # 保存文件
    migrated_path = os.path.join(out_dir, 'migrated_events.csv')
    non_migrated_path = os.path.join(out_dir, 'non_migrated_events.csv')
    df_migrated.to_csv(migrated_path, index=False)
    df_non_migrated.to_csv(non_migrated_path, index=False)
    
    print(f"    ✅ 迁移事件: {len(df_migrated)}, 未迁移事件: {len(df_non_migrated)}")
    
    # 返回结果
    results = {
        tariff_name: {
            'migrated': migrated_path,
            'non_migrated': non_migrated_path,
            'stats': {
                'house_id': house_id,
                'scope': tariff_name,
                'total_events': len(df_full),
                'migrated': len(df_migrated),
                'non_migrated': len(df_non_migrated)
            }
        }
    }
    
    return results


def run_timing_uncertainty_split():
    """运行时间不确定性实验的事件分割"""
    print("🚀 时间不确定性实验 - Event Splitter")
    print("=" * 60)
    
    all_results = {}
    
    for tariff_name in SUPPORTED_TARIFFS:
        print(f"\n💰 处理 {tariff_name}:")
        print("-" * 40)
        
        for house_id in TARGET_HOUSES:
            try:
                result = split_events_for_house(tariff_name, house_id)
                if house_id not in all_results:
                    all_results[house_id] = {}
                all_results[house_id].update(result)
            except Exception as e:
                print(f"    ❌ {house_id} 处理失败: {e}")
    
    # 打印汇总统计
    print(f"\n📊 事件分割汇总:")
    print("=" * 80)
    print(f"{'House':8} {'Tariff':12} {'Total':>8} {'Migrated':>10} {'Non-Mig':>10} {'Success%':>10}")
    print("-" * 80)
    
    total_events = 0
    total_migrated = 0
    total_non_migrated = 0
    
    for house_id in TARGET_HOUSES:
        if house_id in all_results:
            for tariff_name in SUPPORTED_TARIFFS:
                if tariff_name in all_results[house_id]:
                    stats = all_results[house_id][tariff_name]['stats']
                    success_rate = stats['migrated'] / stats['total_events'] * 100 if stats['total_events'] > 0 else 0
                    
                    print(f"{house_id:8} {tariff_name:12} {stats['total_events']:>8} "
                          f"{stats['migrated']:>10} {stats['non_migrated']:>10} {success_rate:>9.1f}%")
                    
                    total_events += stats['total_events']
                    total_migrated += stats['migrated']
                    total_non_migrated += stats['non_migrated']
    
    overall_success_rate = total_migrated / total_events * 100 if total_events > 0 else 0
    print("-" * 80)
    print(f"{'总计':8} {'':12} {total_events:>8} {total_migrated:>10} {total_non_migrated:>10} {overall_success_rate:>9.1f}%")
    
    print(f"\n✅ 事件分割完成！")
    print(f"📁 输出目录: {COST_CAL_BASE}")
    
    return all_results


def main():
    """主函数"""
    try:
        results = run_timing_uncertainty_split()
        return True
    except Exception as e:
        print(f"❌ 事件分割失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
