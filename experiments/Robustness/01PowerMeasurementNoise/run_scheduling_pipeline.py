#!/usr/bin/env python3
"""
功率测量噪声鲁棒性实验 - 调度和成本计算流程运行器

执行步骤:
1. 051_event_scheduler - 事件调度优化
2. 052_collision_resolver - 冲突解决
3. 053_event_splitter - 事件分割
4. 054_cost_cal - 成本计算

基于噪声TOU过滤结果进行事件调度和成本分析
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

# 导入051_event_scheduler
spec_051 = importlib.util.spec_from_file_location("event_scheduler", os.path.join(EXPERIMENT_DIR, "051event_scheduler.py"))
scheduler_module = importlib.util.module_from_spec(spec_051)
spec_051.loader.exec_module(scheduler_module)

# 导入052_collision_resolver
spec_052 = importlib.util.spec_from_file_location("collision_resolver", os.path.join(EXPERIMENT_DIR, "052_collision_resolver.py"))
resolver_module = importlib.util.module_from_spec(spec_052)
spec_052.loader.exec_module(resolver_module)

# 导入053_event_splitter
spec_053 = importlib.util.spec_from_file_location("event_splitter", os.path.join(EXPERIMENT_DIR, "053event_splitter.py"))
splitter_module = importlib.util.module_from_spec(spec_053)
spec_053.loader.exec_module(splitter_module)

# 导入054_cost_cal
spec_054 = importlib.util.spec_from_file_location("cost_cal", os.path.join(EXPERIMENT_DIR, "054_cost_cal.py"))
cost_module = importlib.util.module_from_spec(spec_054)
spec_054.loader.exec_module(cost_module)

# 目标房屋和电价方案
TARGET_HOUSES = [1, 2, 3, 20, 21]
TARGET_TARIFFS = ["Economy_7", "Economy_10"]


def check_prerequisites():
    """检查前提条件"""
    print("🔍 检查前提条件...")
    
    # 检查TOU过滤结果是否存在
    tou_filter_dir = os.path.join(EXPERIMENT_DIR, "output/04_tou_optimization_filter")
    if not os.path.exists(tou_filter_dir):
        print(f"❌ TOU过滤结果目录不存在: {tou_filter_dir}")
        print("请先运行TOU过滤流程")
        return False
    
    # 检查每个房屋和电价方案的TOU过滤文件
    missing_files = []
    for house_num in TARGET_HOUSES:
        house_id = f"house{house_num}"
        for tariff in TARGET_TARIFFS:
            tou_file = os.path.join(tou_filter_dir, "UK", tariff, house_id, f"tou_filtered_{house_id}_{tariff}.csv")
            if not os.path.exists(tou_file):
                missing_files.append(f"{house_id}/{tariff}")
    
    if missing_files:
        print(f"❌ 缺少TOU过滤文件: {missing_files}")
        return False
    
    print(f"✅ 所有 {len(TARGET_HOUSES)} 个房屋 x {len(TARGET_TARIFFS)} 个电价方案的TOU过滤结果已准备就绪")
    return True


def run_event_scheduling():
    """步骤1: 事件调度优化"""
    print("\n" + "=" * 80)
    print("步骤1: 事件调度优化")
    print("=" * 80)
    
    results = {}
    
    for tariff in TARGET_TARIFFS:
        print(f"\n🔋 处理电价方案: {tariff}")
        
        # 准备房屋列表
        house_list = [f"house{house_num}" for house_num in TARGET_HOUSES]
        
        # 运行批量事件调度
        try:
            tariff_results = scheduler_module.process_batch_houses(tariff, house_list)
            results[tariff] = tariff_results
            
            success_count = len([r for r in tariff_results.get('results', {}).values() if r.get('success', False)])
            print(f"📊 {tariff} 调度结果: {success_count}/{len(TARGET_HOUSES)} 个房屋成功处理")
            
        except Exception as e:
            print(f"❌ {tariff} 调度失败: {e}")
            results[tariff] = {"error": str(e)}
    
    return results, len(results) > 0


def run_collision_resolution():
    """步骤2: 冲突解决"""
    print("\n" + "=" * 80)
    print("步骤2: 冲突解决")
    print("=" * 80)
    
    try:
        # 创建冲突解决器实例
        resolver = resolver_module.P052CollisionResolver()
        
        results = {}
        
        for tariff in TARGET_TARIFFS:
            print(f"\n🔧 处理电价方案: {tariff}")
            
            # 运行冲突解决
            tariff_results = resolver.process_tariff_batch(tariff)
            results[tariff] = tariff_results
            
            if tariff_results.get('success', False):
                processed_count = len(tariff_results.get('house_results', {}))
                print(f"📊 {tariff} 冲突解决结果: {processed_count} 个房屋处理完成")
            else:
                print(f"❌ {tariff} 冲突解决失败")
        
        return results, len(results) > 0
        
    except Exception as e:
        print(f"❌ 冲突解决失败: {e}")
        import traceback
        traceback.print_exc()
        return {}, False


def run_event_splitting():
    """步骤3: 事件分割"""
    print("\n" + "=" * 80)
    print("步骤3: 事件分割")
    print("=" * 80)
    
    try:
        results = {}
        
        for tariff in TARGET_TARIFFS:
            print(f"\n📊 处理电价方案: {tariff}")
            
            # 运行事件分割
            tariff_results = splitter_module.process_tariff(tariff)
            results[tariff] = tariff_results
            
            if tariff_results:
                print(f"📊 {tariff} 事件分割完成")
            else:
                print(f"❌ {tariff} 事件分割失败")
        
        return results, len(results) > 0
        
    except Exception as e:
        print(f"❌ 事件分割失败: {e}")
        import traceback
        traceback.print_exc()
        return {}, False


def run_cost_calculation():
    """步骤4: 成本计算"""
    print("\n" + "=" * 80)
    print("步骤4: 成本计算")
    print("=" * 80)
    
    try:
        results = {}
        
        for tariff in TARGET_TARIFFS:
            print(f"\n💰 处理电价方案: {tariff}")
            
            # 运行成本计算
            tariff_results = cost_module.process_tariff(tariff)
            results[tariff] = tariff_results
            
            if tariff_results:
                print(f"📊 {tariff} 成本计算完成")
            else:
                print(f"❌ {tariff} 成本计算失败")
        
        return results, len(results) > 0
        
    except Exception as e:
        print(f"❌ 成本计算失败: {e}")
        import traceback
        traceback.print_exc()
        return {}, False


def run_scheduling_pipeline():
    """运行完整的调度和成本计算流程"""
    print("🚀 功率测量噪声鲁棒性实验 - 调度和成本计算流程")
    print("=" * 80)
    print(f"🎯 目标房屋: {TARGET_HOUSES}")
    print(f"🔋 目标电价方案: {TARGET_TARIFFS}")
    print(f"📁 实验目录: {EXPERIMENT_DIR}")
    print()
    
    # 检查前提条件
    if not check_prerequisites():
        return False
    
    # 步骤1: 事件调度优化
    scheduling_results, step1_success = run_event_scheduling()
    if not step1_success:
        print("❌ 步骤1失败，终止流程")
        return False
    
    # 步骤2: 冲突解决
    collision_results, step2_success = run_collision_resolution()
    if not step2_success:
        print("❌ 步骤2失败，终止流程")
        return False
    
    # 步骤3: 事件分割
    splitting_results, step3_success = run_event_splitting()
    if not step3_success:
        print("❌ 步骤3失败，终止流程")
        return False
    
    # 步骤4: 成本计算
    cost_results, step4_success = run_cost_calculation()
    if not step4_success:
        print("❌ 步骤4失败，终止流程")
        return False
    
    # 流程完成
    print("\n" + "=" * 80)
    print("🎉 功率测量噪声调度和成本计算流程完成！")
    print("=" * 80)
    print(f"📁 结果保存位置:")
    print(f"  • 事件调度: {os.path.join(EXPERIMENT_DIR, 'output/05_Initial_scheduling_optimization/')}")
    print(f"  • 冲突解决: {os.path.join(EXPERIMENT_DIR, 'output/05_Collision_Resolved_Scheduling/')}")
    print(f"  • 事件分割: {os.path.join(EXPERIMENT_DIR, 'output/05_event_split/')}")
    print(f"  • 成本计算: {os.path.join(EXPERIMENT_DIR, 'output/06_cost_cal/')}")
    print()
    
    return True


def main():
    """主函数"""
    try:
        success = run_scheduling_pipeline()
        return success
    except Exception as e:
        print(f"❌ 流程执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
