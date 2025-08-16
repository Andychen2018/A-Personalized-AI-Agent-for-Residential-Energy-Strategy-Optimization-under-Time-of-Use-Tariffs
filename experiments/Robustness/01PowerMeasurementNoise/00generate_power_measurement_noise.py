#!/usr/bin/env python3
"""
功率测量噪声鲁棒性实验 - 噪声数据生成器

在原始每分钟功率数据上引入 ±10% 的随机乘性噪声：
- 只对30%的数据点添加噪声（更符合实际测量噪声的特点）
- 噪声公式: P_noisy = P * (1 + rand(-0.1, 0.1))
- 确保噪声后的功率值不会为负值或接近零

输入: Original_data/house*/01_perception_alignment_result_house*.csv
输出: Noise_data/house*/01_perception_alignment_result_house*_noisy.csv

目标房屋: house1, house2, house3, house20, house21
"""

import os
import pandas as pd
import numpy as np
from typing import Dict
import json
from datetime import datetime

# 🎯 功率测量噪声实验配置
BASE_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
ORIGINAL_DATA_DIR = os.path.join(BASE_DIR, "Original_data")
NOISE_DATA_DIR = os.path.join(BASE_DIR, "Noise_data")

# 目标房屋列表
TARGET_HOUSES = ['house1', 'house2', 'house3', 'house20', 'house21']

# 噪声参数
NOISE_LEVEL = 0.1  # ±10% 噪声
NOISE_RATIO = 0.3  # 对30%的数据点添加噪声（而不是全部）
RANDOM_SEED = 42   # 可重复性


def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def generate_selective_noise_mask(data_length: int, noise_ratio: float = 0.3, seed: int = 42) -> np.ndarray:
    """
    生成选择性噪声掩码，只对部分数据点添加噪声

    Args:
        data_length: 数据长度
        noise_ratio: 添加噪声的数据点比例 (0.3 = 30%)
        seed: 随机种子

    Returns:
        布尔掩码数组，True表示该位置需要添加噪声
    """
    np.random.seed(seed)
    # 随机选择需要添加噪声的位置
    noise_indices = np.random.choice(data_length, size=int(data_length * noise_ratio), replace=False)
    mask = np.zeros(data_length, dtype=bool)
    mask[noise_indices] = True
    return mask


def generate_multiplicative_noise(data_shape: tuple, noise_level: float = 0.1, seed: int = 42) -> np.ndarray:
    """
    生成乘性噪声因子，确保结果不会为负值

    Args:
        data_shape: 数据形状
        noise_level: 噪声水平 (±10% = 0.1)
        seed: 随机种子

    Returns:
        噪声因子数组 (1 + rand(-noise_level, noise_level))，限制在合理范围内
    """
    np.random.seed(seed)
    # 生成 [-noise_level, noise_level] 范围内的随机数
    noise_factors = np.random.uniform(-noise_level, noise_level, data_shape)
    # 返回乘性因子 (1 + noise)，确保最小值不小于0.1（避免结果接近0）
    multiplicative_factors = 1.0 + noise_factors
    # 限制噪声因子的范围，避免产生过小的值
    multiplicative_factors = np.maximum(multiplicative_factors, 0.1)
    return multiplicative_factors


def add_power_measurement_noise(df: pd.DataFrame, noise_level: float = 0.1, noise_ratio: float = 0.3, seed: int = 42) -> pd.DataFrame:
    """
    为功率数据添加测量噪声（只对部分数据点添加噪声）

    Args:
        df: 原始功率数据DataFrame
        noise_level: 噪声水平 (±10% = 0.1)
        noise_ratio: 添加噪声的数据点比例 (0.3 = 30%)
        seed: 随机种子

    Returns:
        添加噪声后的DataFrame
    """
    df_noisy = df.copy()

    # 获取所有功率列（除了Time列）
    power_columns = [col for col in df.columns if col != 'Time']

    print(f"    添加噪声到 {len(power_columns)} 个功率列")
    print(f"    噪声比例: {noise_ratio*100:.0f}% 的数据点将被添加噪声")

    total_noise_points = 0  # 统计总的噪声点数

    # 为每个功率列添加独立的噪声
    for i, col in enumerate(power_columns):
        # 为每列使用不同的随机种子，确保噪声独立
        col_seed = seed + i * 1000

        original_values = df[col].values
        noisy_values = original_values.copy()

        # 只对非零值考虑添加噪声
        non_zero_mask = original_values > 0
        non_zero_indices = np.where(non_zero_mask)[0]

        if len(non_zero_indices) > 0:
            # 生成选择性噪声掩码（只在非零值中选择）
            noise_mask = generate_selective_noise_mask(
                len(non_zero_indices), noise_ratio, col_seed
            )

            # 获取需要添加噪声的实际索引
            noise_indices = non_zero_indices[noise_mask]
            noise_count = len(noise_indices)
            total_noise_points += noise_count

            if noise_count > 0:
                # 为选中的数据点生成噪声因子
                noise_factors = generate_multiplicative_noise(
                    (noise_count,), noise_level, col_seed + 100
                )

                # 应用乘性噪声: P_noisy = P * noise_factor
                noisy_values[noise_indices] = original_values[noise_indices] * noise_factors

                # 确保噪声后的值仍然为正值（由于我们限制了噪声因子最小为0.1，这里应该不会有负值）
                noisy_values[noise_indices] = np.maximum(noisy_values[noise_indices], 0.01)  # 最小值设为0.01W

        df_noisy[col] = noisy_values

        # 统计信息
        original_mean = np.mean(original_values[non_zero_mask]) if np.any(non_zero_mask) else 0
        noisy_mean = np.mean(noisy_values[non_zero_mask]) if np.any(non_zero_mask) else 0
        noise_impact = (noisy_mean - original_mean) / original_mean * 100 if original_mean > 0 else 0

        if i < 3:  # 只显示前3列的详细信息
            noise_count_col = len(noise_indices) if len(non_zero_indices) > 0 else 0
            print(f"      {col}: 原始均值={original_mean:.2f}W, 噪声后均值={noisy_mean:.2f}W, "
                  f"影响={noise_impact:+.1f}%, 噪声点数={noise_count_col}/{len(non_zero_indices)}")

    print(f"    总计添加噪声的数据点: {total_noise_points}")

    return df_noisy


def process_house_power_data(house_id: str) -> Dict:
    """
    处理单个房屋的功率数据，添加测量噪声
    
    Args:
        house_id: 房屋ID (如 'house1')
    
    Returns:
        处理结果统计信息
    """
    print(f"  🏠 处理 {house_id}")
    
    # 输入文件路径
    input_file = os.path.join(ORIGINAL_DATA_DIR, house_id, f"01_perception_alignment_result_{house_id}.csv")
    
    if not os.path.exists(input_file):
        print(f"    ❌ 原始数据文件不存在: {input_file}")
        return {'success': False, 'error': 'File not found'}
    
    try:
        # 读取原始数据
        print(f"    📖 读取原始数据...")
        df_original = pd.read_csv(input_file)
        
        # 验证数据格式
        if 'Time' not in df_original.columns:
            raise ValueError("缺少Time列")
        
        # 转换时间列
        df_original['Time'] = pd.to_datetime(df_original['Time'])
        
        print(f"    📊 原始数据: {len(df_original)} 行, {len(df_original.columns)} 列")
        print(f"    📅 时间范围: {df_original['Time'].min()} - {df_original['Time'].max()}")
        
        # 添加功率测量噪声
        print(f"    🔊 添加 ±{NOISE_LEVEL*100:.0f}% 功率测量噪声...")
        df_noisy = add_power_measurement_noise(df_original, NOISE_LEVEL, NOISE_RATIO, RANDOM_SEED)
        
        # 创建输出目录
        output_dir = os.path.join(NOISE_DATA_DIR, house_id)
        ensure_dir(output_dir)
        
        # 保存噪声数据
        output_file = os.path.join(output_dir, f"01_perception_alignment_result_{house_id}_noisy.csv")
        df_noisy.to_csv(output_file, index=False)
        
        print(f"    ✅ 噪声数据已保存: {output_file}")
        
        # 计算统计信息
        power_columns = [col for col in df_original.columns if col != 'Time']
        
        original_total_power = df_original[power_columns].sum().sum()
        noisy_total_power = df_noisy[power_columns].sum().sum()
        total_power_change = (noisy_total_power - original_total_power) / original_total_power * 100
        
        # 计算各列的平均噪声影响
        column_impacts = []
        for col in power_columns:
            orig_mean = df_original[col].mean()
            noisy_mean = df_noisy[col].mean()
            if orig_mean > 0:
                impact = (noisy_mean - orig_mean) / orig_mean * 100
                column_impacts.append(abs(impact))
        
        avg_noise_impact = np.mean(column_impacts) if column_impacts else 0
        
        stats = {
            'success': True,
            'house_id': house_id,
            'data_points': len(df_original),
            'power_columns': len(power_columns),
            'time_range': {
                'start': df_original['Time'].min().isoformat(),
                'end': df_original['Time'].max().isoformat()
            },
            'noise_level': NOISE_LEVEL,
            'total_power_change_percent': total_power_change,
            'avg_noise_impact_percent': avg_noise_impact,
            'output_file': output_file
        }
        
        print(f"    📈 总功率变化: {total_power_change:+.2f}%")
        print(f"    📊 平均噪声影响: {avg_noise_impact:.2f}%")
        
        return stats
        
    except Exception as e:
        print(f"    ❌ 处理失败: {str(e)}")
        return {'success': False, 'error': str(e), 'house_id': house_id}


def generate_power_measurement_noise():
    """
    为所有目标房屋生成功率测量噪声数据
    """
    print("🚀 功率测量噪声鲁棒性实验 - 噪声数据生成")
    print("=" * 60)
    print(f"🎯 噪声水平: ±{NOISE_LEVEL*100:.0f}%")
    print(f"📊 噪声比例: {NOISE_RATIO*100:.0f}% 的数据点")
    print(f"🏠 目标房屋: {', '.join(TARGET_HOUSES)}")
    print(f"🎲 随机种子: {RANDOM_SEED}")
    print()
    
    # 确保输出目录存在
    ensure_dir(NOISE_DATA_DIR)
    
    # 处理结果
    results = []
    successful_houses = []
    failed_houses = []
    
    # 处理每个房屋
    for house_id in TARGET_HOUSES:
        result = process_house_power_data(house_id)
        results.append(result)
        
        if result['success']:
            successful_houses.append(house_id)
        else:
            failed_houses.append(house_id)
        print()
    
    # 生成汇总报告
    print("📊 噪声生成汇总:")
    print("=" * 60)
    print(f"✅ 成功处理: {len(successful_houses)} 个房屋")
    print(f"❌ 处理失败: {len(failed_houses)} 个房屋")
    
    if successful_houses:
        print(f"\n成功处理的房屋:")
        for house_id in successful_houses:
            house_result = next(r for r in results if r.get('house_id') == house_id and r['success'])
            print(f"  {house_id}: {house_result['data_points']} 数据点, "
                  f"总功率变化 {house_result['total_power_change_percent']:+.2f}%, "
                  f"平均噪声影响 {house_result['avg_noise_impact_percent']:.2f}%")
    
    if failed_houses:
        print(f"\n处理失败的房屋:")
        for house_id in failed_houses:
            house_result = next(r for r in results if r.get('house_id') == house_id and not r['success'])
            print(f"  {house_id}: {house_result['error']}")
    
    # 保存详细结果
    results_file = os.path.join(BASE_DIR, "power_noise_generation_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'experiment_info': {
                'name': 'Power Measurement Noise Generation',
                'noise_level': NOISE_LEVEL,
                'noise_ratio': NOISE_RATIO,
                'target_houses': TARGET_HOUSES,
                'random_seed': RANDOM_SEED,
                'generation_time': datetime.now().isoformat()
            },
            'results': results,
            'summary': {
                'successful_houses': successful_houses,
                'failed_houses': failed_houses,
                'success_rate': len(successful_houses) / len(TARGET_HOUSES) * 100
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 详细结果已保存: {results_file}")
    print(f"📁 噪声数据目录: {NOISE_DATA_DIR}")
    
    return results


def main():
    """主函数"""
    try:
        results = generate_power_measurement_noise()
        
        # 检查是否有成功的结果
        successful_count = sum(1 for r in results if r['success'])
        if successful_count > 0:
            print(f"\n🎉 功率测量噪声生成完成！成功处理 {successful_count} 个房屋")
            return True
        else:
            print(f"\n❌ 所有房屋处理失败！")
            return False
            
    except Exception as e:
        print(f"❌ 噪声生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
