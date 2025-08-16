#!/usr/bin/env python3
"""
功率测量噪声鲁棒性实验 - 完整流程运行器

执行步骤:
1. 021_shiftable_identifier - 可调度性识别
2. 022_segment_events - 事件分割
3. 023_event_id - 事件ID分配

基于噪声功率数据进行完整的事件检测和分割流程
"""

import os
import sys
import json
from datetime import datetime

# 🎯 功率测量噪声实验路径配置
EXPERIMENT_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
sys.path.insert(0, '/home/deep/TimeSeries/Agent_V2')
sys.path.insert(0, EXPERIMENT_DIR)

# 导入修改后的功率测量噪声实验模块
import importlib.util

# 导入021_shiftable_identifier
spec_021 = importlib.util.spec_from_file_location("si", os.path.join(EXPERIMENT_DIR, "021_shiftable_identifier.py"))
si_module = importlib.util.module_from_spec(spec_021)
spec_021.loader.exec_module(si_module)

# 导入022_segment_events
spec_022 = importlib.util.spec_from_file_location("seg", os.path.join(EXPERIMENT_DIR, "022_segment_events.py"))
seg_module = importlib.util.module_from_spec(spec_022)
spec_022.loader.exec_module(seg_module)

# 导入023_event_id
spec_023 = importlib.util.spec_from_file_location("eid", os.path.join(EXPERIMENT_DIR, "023_event_id.py"))
eid_module = importlib.util.module_from_spec(spec_023)
spec_023.loader.exec_module(eid_module)

# 创建别名
batch_identify_appliance_shiftability = si_module.batch_identify_appliance_shiftability
batch_run_event_segmentation = seg_module.batch_run_event_segmentation
batch_add_event_id = eid_module.batch_add_event_id

# 目标房屋
TARGET_HOUSES = [1, 2, 3, 20, 21]


def load_house_appliances_config():
    """加载房屋电器配置"""
    config_path = os.path.join(EXPERIMENT_DIR, "config/house_appliances.json")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            house_appliances = json.load(f)
        
        # 转换格式以匹配原始期望的格式
        formatted_appliances = {}
        for house_id, config in house_appliances.items():
            if 'appliances' in config:
                # 将电器列表转换为字符串描述
                appliances_str = ', '.join(config['appliances'])
                formatted_appliances[house_id] = appliances_str
        
        return formatted_appliances

    except Exception as e:
        print(f"❌ 加载房屋电器配置失败: {str(e)}")
        return {}


def check_prerequisites():
    """检查前提条件"""
    print("🔍 检查前提条件...")
    
    # 检查噪声数据是否存在
    noise_data_dir = os.path.join(EXPERIMENT_DIR, "Noise_data")
    if not os.path.exists(noise_data_dir):
        print(f"❌ 噪声数据目录不存在: {noise_data_dir}")
        print("请先运行 00generate_power_measurement_noise.py 生成噪声数据")
        return False
    
    # 检查每个房屋的噪声数据文件
    missing_houses = []
    for house_num in TARGET_HOUSES:
        house_id = f"house{house_num}"
        noise_file = os.path.join(noise_data_dir, house_id, f"01_perception_alignment_result_{house_id}_noisy.csv")
        if not os.path.exists(noise_file):
            missing_houses.append(house_id)
    
    if missing_houses:
        print(f"❌ 缺少噪声数据文件: {missing_houses}")
        return False
    
    print(f"✅ 所有 {len(TARGET_HOUSES)} 个房屋的噪声数据已准备就绪")
    return True


def run_shiftability_identification(target_house_appliances):
    """步骤1: 可调度性识别"""
    print("\n" + "=" * 80)
    print("步骤1: 可调度性识别")
    print("=" * 80)
    
    # 输出目录
    experiment_behavior_dir = os.path.join(EXPERIMENT_DIR, "output/02_behavior_modeling/")
    
    # 运行可调度性识别
    shiftability_results = batch_identify_appliance_shiftability(
        house_appliances_dict=target_house_appliances,
        output_dir=experiment_behavior_dir
    )
    
    # 统计结果
    success_count = len([r for r in shiftability_results.values() if r is not None])
    print(f"\n📊 可调度性识别结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
    
    return shiftability_results, success_count > 0


def run_event_segmentation(target_house_appliances):
    """步骤2: 事件分割"""
    print("\n" + "=" * 80)
    print("步骤2: 事件分割")
    print("=" * 80)
    
    # 路径配置
    noise_data_dir = os.path.join(EXPERIMENT_DIR, "Noise_data")
    experiment_behavior_dir = os.path.join(EXPERIMENT_DIR, "output/02_behavior_modeling/")
    experiment_segments_dir = os.path.join(EXPERIMENT_DIR, "output/02_event_segments/")
    
    # 运行事件分割
    segmentation_results = batch_run_event_segmentation(
        house_data_dict=target_house_appliances,
        input_dir=noise_data_dir,
        label_dir=experiment_behavior_dir,
        output_dir=experiment_segments_dir
    )
    
    # 统计结果
    success_count = len([r for r in segmentation_results.values() if r is not None])
    total_events = sum(len(df) for df in segmentation_results.values() if df is not None)
    
    print(f"\n📊 事件分割结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
    print(f"📊 总事件数: {total_events}")
    
    return segmentation_results, success_count > 0


def run_event_id_assignment(target_house_appliances):
    """步骤3: 事件ID分配"""
    print("\n" + "=" * 80)
    print("步骤3: 事件ID分配")
    print("=" * 80)
    
    # 路径配置
    experiment_segments_dir = os.path.join(EXPERIMENT_DIR, "output/02_event_segments/")
    
    # 运行事件ID分配
    event_id_results = batch_add_event_id(
        house_data_dict=target_house_appliances,
        input_dir=experiment_segments_dir,
        output_dir=experiment_segments_dir
    )
    
    # 统计结果
    success_count = len([r for r in event_id_results.values() if r is not None])
    total_events_with_id = sum(len(df) for df in event_id_results.values() if df is not None)
    
    print(f"\n📊 事件ID分配结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
    print(f"📊 带ID的事件总数: {total_events_with_id}")
    
    return event_id_results, success_count > 0


def run_power_noise_experiment():
    """运行完整的功率测量噪声实验"""
    print("🚀 功率测量噪声鲁棒性实验 - 完整流程")
    print("=" * 80)
    print(f"🎯 目标房屋: {TARGET_HOUSES}")
    print(f"📁 实验目录: {EXPERIMENT_DIR}")
    print()
    
    # 检查前提条件
    if not check_prerequisites():
        return False
    
    # 加载房屋电器配置
    house_appliances = load_house_appliances_config()
    target_house_appliances = {}
    for house_num in TARGET_HOUSES:
        house_id = f"house{house_num}"
        if house_id in house_appliances:
            target_house_appliances[house_id] = house_appliances[house_id]
        else:
            print(f"⚠️ 没有找到 {house_id} 的电器配置")
    
    print(f"📋 找到 {len(target_house_appliances)} 个房屋的电器配置")
    
    # 步骤1: 可调度性识别
    shiftability_results, step1_success = run_shiftability_identification(target_house_appliances)
    if not step1_success:
        print("❌ 步骤1失败，终止实验")
        return False
    
    # 步骤2: 事件分割
    segmentation_results, step2_success = run_event_segmentation(target_house_appliances)
    if not step2_success:
        print("❌ 步骤2失败，终止实验")
        return False
    
    # 步骤3: 事件ID分配
    event_id_results, step3_success = run_event_id_assignment(target_house_appliances)
    if not step3_success:
        print("❌ 步骤3失败，终止实验")
        return False
    
    # 实验完成
    print("\n" + "=" * 80)
    print("🎉 功率测量噪声实验完成！")
    print("=" * 80)
    print(f"📁 结果保存位置:")
    print(f"  • 可调度性识别: {os.path.join(EXPERIMENT_DIR, 'output/02_behavior_modeling/')}")
    print(f"  • 事件分割: {os.path.join(EXPERIMENT_DIR, 'output/02_event_segments/')}")
    print()
    
    return True


def main():
    """主函数"""
    try:
        success = run_power_noise_experiment()
        return success
    except Exception as e:
        print(f"❌ 实验执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
