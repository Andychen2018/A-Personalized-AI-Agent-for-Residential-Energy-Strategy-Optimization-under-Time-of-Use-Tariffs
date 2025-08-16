#!/usr/bin/env python3
"""
功率测量噪声鲁棒性实验 - 事件过滤流程运行器

执行步骤:
1. 041_get_appliance_list - 提取电器列表
2. 043_min_duration_filter - 最小持续时间过滤
3. 044_tou_optimization_filter - TOU优化过滤

基于噪声事件分割结果进行可调度事件过滤
"""

import os
import sys
from datetime import datetime

# 🎯 功率测量噪声实验路径配置
EXPERIMENT_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
sys.path.insert(0, '/home/deep/TimeSeries/Agent_V2')
sys.path.insert(0, EXPERIMENT_DIR)

# 导入修改后的模块
import importlib.util

# 导入041_get_appliance_list
spec_041 = importlib.util.spec_from_file_location("appliance_list", os.path.join(EXPERIMENT_DIR, "041_get_appliance_list.py"))
appliance_list_module = importlib.util.module_from_spec(spec_041)
spec_041.loader.exec_module(appliance_list_module)

# 导入043_min_duration_filter
spec_043 = importlib.util.spec_from_file_location("min_duration", os.path.join(EXPERIMENT_DIR, "043_min_duration_filter.py"))
min_duration_module = importlib.util.module_from_spec(spec_043)
spec_043.loader.exec_module(min_duration_module)

# 导入044_tou_optimization_filter
spec_044 = importlib.util.spec_from_file_location("tou_filter", os.path.join(EXPERIMENT_DIR, "044_tou_optimization_filter.py"))
tou_filter_module = importlib.util.module_from_spec(spec_044)
spec_044.loader.exec_module(tou_filter_module)

# 目标房屋
TARGET_HOUSES = [1, 2, 3, 20, 21]


def check_prerequisites():
    """检查前提条件"""
    print("🔍 检查前提条件...")
    
    # 检查事件分割结果是否存在
    event_segments_dir = os.path.join(EXPERIMENT_DIR, "output/02_event_segments")
    if not os.path.exists(event_segments_dir):
        print(f"❌ 事件分割结果目录不存在: {event_segments_dir}")
        print("请先运行事件分割流程")
        return False
    
    # 检查每个房屋的事件分割文件
    missing_houses = []
    for house_num in TARGET_HOUSES:
        house_id = f"house{house_num}"
        event_file = os.path.join(event_segments_dir, house_id, f"02_appliance_event_segments_id_{house_id}.csv")
        if not os.path.exists(event_file):
            missing_houses.append(house_id)
    
    if missing_houses:
        print(f"❌ 缺少事件分割文件: {missing_houses}")
        return False
    
    print(f"✅ 所有 {len(TARGET_HOUSES)} 个房屋的事件分割结果已准备就绪")
    return True


def run_appliance_list_extraction():
    """步骤1: 提取电器列表"""
    print("\n" + "=" * 80)
    print("步骤1: 提取电器列表")
    print("=" * 80)
    
    # 准备房屋数据字典
    house_data_dict = {f"house{house_num}": {} for house_num in TARGET_HOUSES}
    
    # 运行批量电器列表提取
    results = appliance_list_module.batch_get_appliance_lists(
        house_data_dict=house_data_dict,
        tariff_type="UK"
    )
    
    # 统计结果
    success_count = len([r for r in results.values() if r is not None])
    print(f"\n📊 电器列表提取结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
    
    return results, success_count > 0


def run_min_duration_filter():
    """步骤2: 最小持续时间过滤"""
    print("\n" + "=" * 80)
    print("步骤2: 最小持续时间过滤")
    print("=" * 80)
    
    # 创建过滤器实例
    filter_processor = min_duration_module.MinDurationEventFilter()
    
    # 准备房屋列表
    house_list = [f"house{house_num}" for house_num in TARGET_HOUSES]
    
    # 运行批量最小持续时间过滤
    results = filter_processor.process_batch_households(house_list)
    
    # 统计结果
    success_count = len([r for r in results.values() if r is not None])
    print(f"\n📊 最小持续时间过滤结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
    
    return results, success_count > 0


def run_tou_optimization_filter():
    """步骤3: TOU优化过滤"""
    print("\n" + "=" * 80)
    print("步骤3: TOU优化过滤")
    print("=" * 80)
    
    # 准备房屋列表
    house_list = [f"house{house_num}" for house_num in TARGET_HOUSES]
    
    # 运行批量TOU优化过滤
    results = tou_filter_module.process_batch_households_complete_pipeline(
        house_list=house_list,
        tariff_type="UK"
    )
    
    # 统计结果
    success_count = len([r for r in results.values() if r is not None])
    print(f"\n📊 TOU优化过滤结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
    
    return results, success_count > 0


def run_filtering_pipeline():
    """运行完整的事件过滤流程"""
    print("🚀 功率测量噪声鲁棒性实验 - 事件过滤流程")
    print("=" * 80)
    print(f"🎯 目标房屋: {TARGET_HOUSES}")
    print(f"📁 实验目录: {EXPERIMENT_DIR}")
    print()
    
    # 检查前提条件
    if not check_prerequisites():
        return False
    
    # 步骤1: 提取电器列表
    appliance_results, step1_success = run_appliance_list_extraction()
    if not step1_success:
        print("❌ 步骤1失败，终止流程")
        return False
    
    # 步骤2: 最小持续时间过滤
    min_duration_results, step2_success = run_min_duration_filter()
    if not step2_success:
        print("❌ 步骤2失败，终止流程")
        return False
    
    # 步骤3: TOU优化过滤
    tou_results, step3_success = run_tou_optimization_filter()
    if not step3_success:
        print("❌ 步骤3失败，终止流程")
        return False
    
    # 流程完成
    print("\n" + "=" * 80)
    print("🎉 功率测量噪声事件过滤流程完成！")
    print("=" * 80)
    print(f"📁 结果保存位置:")
    print(f"  • 电器列表: {os.path.join(EXPERIMENT_DIR, 'output/04_appliance_summary/')}")
    print(f"  • 最小持续时间过滤: {os.path.join(EXPERIMENT_DIR, 'output/04_min_duration_filter/')}")
    print(f"  • TOU优化过滤: {os.path.join(EXPERIMENT_DIR, 'output/04_tou_optimization_filter/')}")
    print()
    
    return True


def main():
    """主函数"""
    try:
        success = run_filtering_pipeline()
        return success
    except Exception as e:
        print(f"❌ 流程执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
