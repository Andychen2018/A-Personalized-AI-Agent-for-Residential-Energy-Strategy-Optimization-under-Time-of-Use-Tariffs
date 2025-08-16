#!/usr/bin/env python3
"""
Test Function 6 Integration Tool
集成执行 P051~P054 工具的完整流程

功能：
1. P051: 电器工作空间生成器 (Appliance Space Generator)
2. P052: 事件调度器 (Event Scheduler)  
3. P053: 冲突解决器 (Collision Resolver)
4. P054: 事件分割器 (Event Splitter)

作者：Agent V2
日期：2025-01-08
"""

import os
import sys
import argparse
from typing import List, Dict, Optional

# 添加 tools 目录到 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

# 导入各个工具模块
try:
    from tools.p_051_appliance_space_generator import run_generate_appliance_spaces, process_batch_houses as p051_batch
    from tools.p_052_event_scheduler import run_event_scheduler, process_batch_houses as p052_batch
    from tools.p_053_collision_resolver import run_collision_resolution, run_single_house_collision_resolution
    from tools.p_054_event_splitter import run_splitter_interactive, split_events_for_house, list_houses_from_segments, summarize_results
except ImportError as e:
    print(f"Warning: Some modules could not be imported: {e}")
    print("Please ensure the tools directory is accessible.")


class IntegratedWorkflow:
    """集成工作流程类"""
    
    def __init__(self):
        self.config = {
            'tariff_group': None,      # 'UK', 'TOU_D', 'Germany_Variable'
            'processing_mode': None,   # 'single', 'batch'
            'house_id': None,          # 单个处理时的house ID
            'house_list': None,        # 批处理时的house列表
            'test_mode': False         # P051的测试模式标志
        }
        
    def setup_configuration_from_args(self, tariff_group="UK", processing_mode="single", house_id="house1"):
        """从参数设置配置"""
        print("🎯 Test Function 6 Integration Tool")
        print("=" * 60)
        print("集成执行 P051~P054 工具的完整流程")
        print()
        
        # 设置电价方案组
        self.config['tariff_group'] = tariff_group
        self.config['test_mode'] = (tariff_group in ['TOU_D', 'Germany_Variable'])
        print(f"✅ 已选择电价方案组: {self.config['tariff_group']}")
        
        # 设置处理模式
        self.config['processing_mode'] = processing_mode
        
        if processing_mode == "single":
            # 确保house ID格式正确
            if house_id.isdigit():
                house_id = f"house{house_id}"
            elif not house_id.startswith("house"):
                house_id = f"house{house_id}"
            self.config['house_id'] = house_id
            print(f"✅ 已选择处理模式: 单个家庭处理 ({house_id})")
        else:
            # 批量处理
            available_houses = [f"house{i}" for i in range(1, 22) if i not in [12, 14]]
            self.config['house_list'] = available_houses
            print(f"✅ 已选择处理模式: 批量处理 ({len(available_houses)} 个家庭)")
        
        print()
        return True
        
    def setup_configuration(self):
        """设置全局配置参数"""
        print("🎯 Test Function 6 Integration Tool")
        print("=" * 60)
        print("集成执行 P051~P054 工具的完整流程")
        print()
        
        # 第一步：选择电价方案组
        print("📋 第一步：选择电价方案组")
        print("1. UK (Economy_7 + Economy_10) [默认]")
        print("2. TOU_D (California, 季节性)")
        print("3. Germany_Variable (德国可变电价)")
        
        try:
            tariff_choice = input("选择电价方案 (1-3) [默认: 1]: ").strip()
            if not tariff_choice:
                tariff_choice = "1"
        except (EOFError, KeyboardInterrupt):
            tariff_choice = "1"
            
        tariff_map = {
            "1": "UK",
            "2": "TOU_D", 
            "3": "Germany_Variable"
        }
        
        self.config['tariff_group'] = tariff_map.get(tariff_choice, "UK")
        self.config['test_mode'] = (self.config['tariff_group'] in ['TOU_D', 'Germany_Variable'])
        
        print(f"✅ 已选择电价方案组: {self.config['tariff_group']}")
        
        # 第二步：选择处理模式
        print("\n📋 第二步：选择处理模式")
        print("1. 单个家庭处理 [默认]")
        print("2. 批量处理 (house1~house21, 排除house12,house14)")
        
        try:
            mode_choice = input("选择处理模式 (1-2) [默认: 1]: ").strip()
            if not mode_choice:
                mode_choice = "1"
        except (EOFError, KeyboardInterrupt):
            mode_choice = "1"
            
        if mode_choice == "1":
            self.config['processing_mode'] = 'single'
            # 获取house ID
            try:
                house_id = input("输入House ID (e.g., house1) [默认: house1]: ").strip()
                if not house_id:
                    house_id = "house1"
                # 确保house ID格式正确
                if house_id.isdigit():
                    house_id = f"house{house_id}"
                elif not house_id.startswith("house"):
                    house_id = f"house{house_id}"
            except (EOFError, KeyboardInterrupt):
                house_id = "house1"
            self.config['house_id'] = house_id
            print(f"✅ 已选择单个处理: {house_id}")
        else:
            self.config['processing_mode'] = 'batch'
            # 生成批处理house列表（排除house12, house14）
            self.config['house_list'] = [f"house{i}" for i in range(1, 22) if i not in (12, 14)]
            print(f"✅ 已选择批量处理: {len(self.config['house_list'])} 个家庭")
            
        print(f"\n🔧 配置完成:")
        print(f"   电价方案组: {self.config['tariff_group']}")
        print(f"   处理模式: {self.config['processing_mode']}")
        if self.config['processing_mode'] == 'single':
            print(f"   目标家庭: {self.config['house_id']}")
        else:
            print(f"   目标家庭: {len(self.config['house_list'])} 个")
        print(f"   测试模式: {self.config['test_mode']}")
        
    def run_p051_appliance_space_generator(self):
        """执行 P051: 电器工作空间生成器"""
        print(f"\n{'='*60}")
        print("🚀 步骤 1/4: 执行 P051 - 电器工作空间生成器")
        print(f"{'='*60}")
        
        try:
            # P051 只需要 test_mode 参数
            result = run_generate_appliance_spaces(test_mode=self.config['test_mode'])
            print("✅ P051 执行完成")
            return True
        except Exception as e:
            print(f"❌ P051 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def run_p052_event_scheduler(self):
        """执行 P052: 事件调度器"""
        print(f"\n{'='*60}")
        print("🚀 步骤 2/4: 执行 P052 - 事件调度器")
        print(f"{'='*60}")
        
        try:
            if self.config['tariff_group'] == 'UK':
                # UK 需要处理 Economy_7 和 Economy_10
                tariff_list = ['Economy_7', 'Economy_10']
            elif self.config['tariff_group'] == 'TOU_D':
                tariff_list = ['TOU_D']
            elif self.config['tariff_group'] == 'Germany_Variable':
                tariff_list = ['Germany_Variable']
            else:
                tariff_list = ['Economy_7']  # 默认
                
            for tariff_name in tariff_list:
                print(f"\n📊 处理电价方案: {tariff_name}")
                
                if self.config['processing_mode'] == 'single':
                    # 单个处理：直接调用主函数，传入参数避免交互
                    run_event_scheduler(mode='single', tariff_name=tariff_name, house_id=self.config['house_id'])
                else:
                    # 批量处理
                    result = p052_batch(tariff_name=tariff_name, house_list=self.config['house_list'])
                    print(f"✅ {tariff_name} 批量处理完成")
                    
            print("✅ P052 执行完成")
            return True
        except Exception as e:
            print(f"❌ P052 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def run_p053_collision_resolver(self):
        """执行 P053: 冲突解决器"""
        print(f"\n{'='*60}")
        print("🚀 步骤 3/4: 执行 P053 - 冲突解决器")
        print(f"{'='*60}")
        
        try:
            if self.config['processing_mode'] == 'single':
                # 单个处理
                if self.config['tariff_group'] == 'UK':
                    tariff_list = ['Economy_7', 'Economy_10']
                elif self.config['tariff_group'] == 'TOU_D':
                    tariff_list = ['TOU_D']
                elif self.config['tariff_group'] == 'Germany_Variable':
                    tariff_list = ['Germany_Variable']
                else:
                    tariff_list = ['Economy_7']
                    
                for tariff_name in tariff_list:
                    print(f"\n📊 处理电价方案: {tariff_name}")
                    result = run_single_house_collision_resolution(
                        tariff_name=tariff_name, 
                        house_id=self.config['house_id']
                    )
                    print(f"✅ {tariff_name} - {self.config['house_id']} 处理完成")
            else:
                # 批量处理：使用默认模式，会处理所有电价方案
                result = run_collision_resolution(mode="default")
                print("✅ 批量冲突解决完成")
                
            print("✅ P053 执行完成")
            return True
        except Exception as e:
            print(f"❌ P053 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def run_p054_event_splitter(self):
        """执行 P054: 事件分割器"""
        print(f"\n{'='*60}")
        print("🚀 步骤 4/4: 执行 P054 - 事件分割器")
        print(f"{'='*60}")

        try:
            # 确定要处理的电价方案列表
            if self.config['tariff_group'] == 'UK':
                tariff_list = ['Economy_7', 'Economy_10']
            elif self.config['tariff_group'] == 'TOU_D':
                tariff_list = ['TOU_D']
            elif self.config['tariff_group'] == 'Germany_Variable':
                tariff_list = ['Germany_Variable']
            else:
                tariff_list = ['Economy_7']  # 默认

            # 确定要处理的house列表
            if self.config['processing_mode'] == 'single':
                target_houses = [self.config['house_id']]
            else:
                # 批处理：获取所有可用的house
                try:
                    available_houses = list_houses_from_segments()
                    # 过滤出我们配置的house列表中存在的house
                    target_houses = [h for h in self.config['house_list'] if h in available_houses]
                    print(f"📊 找到 {len(target_houses)} 个可处理的家庭")
                except:
                    target_houses = self.config['house_list']

            # 执行事件分割
            total_tasks = len(tariff_list) * len(target_houses)
            current_task = 0
            all_results = {}  # 使用 P054 原本的数据结构

            print(f"📊 开始处理 {len(target_houses)} 个家庭，{len(tariff_list)} 个电价方案，共 {total_tasks} 个任务")

            for tariff_name in tariff_list:
                for house_id in target_houses:
                    current_task += 1
                    print(f"\n📊 [{current_task}/{total_tasks}] 处理 {house_id} - {tariff_name}...")

                    try:
                        result = split_events_for_house(tariff_name, house_id)
                        if result:
                            # 显示文件路径信息（模仿原版输出）
                            for scope_key, scope_data in result.items():
                                migrated_path = scope_data.get('migrated', '')
                                non_migrated_path = scope_data.get('non_migrated', '')
                                print(f"✅ {house_id} [{tariff_name}/{scope_key}] -> {migrated_path}, {non_migrated_path}")

                            # 收集结果用于汇总（使用 P054 原本的数据结构）
                            if house_id not in all_results:
                                all_results[house_id] = {}
                            all_results[house_id].update(result)
                        else:
                            print(f"⚠️  {house_id} - {tariff_name} 无数据或处理失败")
                    except Exception as e:
                        print(f"❌ 错误 {house_id} - {tariff_name}: {e}")

            # 使用 P054 原本的汇总函数显示统计表格
            if all_results:
                summarize_results(all_results)

            print("✅ P054 执行完成")
            return True
        except Exception as e:
            print(f"❌ P054 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _display_p054_summary(self, all_results: List[Dict]):
        """显示 P054 事件分割统计表格"""
        if not all_results:
            return

        print(f"\n📊 P054 事件分割统计表")
        print("=" * 80)
        header = f"{'House':8} {'Tariff':12} {'Scope':12} {'Total':8} {'Migrated':10} {'Non-Migrated':12} {'Migration%':10}"
        print(header)
        print("-" * 80)

        # 按数字顺序排序 house ID
        def house_sort_key(result):
            try:
                return int(result['house_id'].replace('house', ''))
            except:
                return 999

        sorted_results = sorted(all_results, key=house_sort_key)

        total_events = 0
        total_migrated = 0
        total_non_migrated = 0

        for result in sorted_results:
            house_id = result['house_id']
            tariff_name = result['tariff_name']
            scope = result['scope']
            total = result['total_events']
            migrated = result['migrated']
            non_migrated = result['non_migrated']
            migration_rate = (migrated / total * 100) if total > 0 else 0

            print(f"{house_id:8} {tariff_name:12} {scope:12} {total:8d} {migrated:10d} {non_migrated:12d} {migration_rate:9.1f}%")

            total_events += total
            total_migrated += migrated
            total_non_migrated += non_migrated

        print("-" * 80)
        overall_migration_rate = (total_migrated / total_events * 100) if total_events > 0 else 0
        print(f"{'TOTAL':8} {'':12} {'':12} {total_events:8d} {total_migrated:10d} {total_non_migrated:12d} {overall_migration_rate:9.1f}%")
        print("-" * 80)

    def run_complete_workflow(self, interactive=True, tariff_group="UK", processing_mode="single", house_id="house1"):
        """执行完整工作流程"""
        if interactive:
            success = self.setup_configuration()
        else:
            success = self.setup_configuration_from_args(tariff_group, processing_mode, house_id)
            
        if not success:
            return False
        
        # 确认执行 (仅在交互模式下询问)
        if interactive:
            print(f"\n⚠️  即将开始执行完整流程，这可能需要较长时间...")
            try:
                confirm = input("是否继续？(y/N) [默认: N]: ").strip().lower()
                if confirm not in ['y', 'yes', '1']:
                    print("❌ 用户取消执行")
                    return False
            except (EOFError, KeyboardInterrupt):
                print("❌ 用户取消执行")
                return False
        else:
            print(f"\n🚀 开始执行完整流程...")
            
        # 执行各个步骤
        steps = [
            ("P051", self.run_p051_appliance_space_generator),
            ("P052", self.run_p052_event_scheduler),
            ("P053", self.run_p053_collision_resolver),
            ("P054", self.run_p054_event_splitter)
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            if step_func():
                success_count += 1
            else:
                print(f"\n❌ {step_name} 执行失败")
                if interactive:
                    print("是否继续执行后续步骤？")
                    try:
                        continue_choice = input("继续执行？(y/N) [默认: N]: ").strip().lower()
                        if continue_choice not in ['y', 'yes']:
                            break
                    except (EOFError, KeyboardInterrupt):
                        break
                else:
                    print("自动继续执行后续步骤...")
                    
        # 总结
        print(f"\n{'='*60}")
        print("🎯 工作流程执行总结")
        print(f"{'='*60}")
        print(f"✅ 成功执行步骤: {success_count}/4")
        print(f"📊 配置信息:")
        print(f"   电价方案组: {self.config['tariff_group']}")
        print(f"   处理模式: {self.config['processing_mode']}")
        if self.config['processing_mode'] == 'single':
            print(f"   目标家庭: {self.config['house_id']}")
        else:
            print(f"   目标家庭: {len(self.config['house_list'])} 个")
            
        if success_count == 4:
            print("🎉 完整工作流程执行成功！")
            return True
        else:
            print("⚠️  工作流程部分完成，请检查失败的步骤")
            return False


def main(tariff_group, mode, house_id, interactive):
    """
    主函数
    
    Args:
        tariff_group: 电价方案组 ("UK", "TOU_D", "Germany_Variable")
        mode: 处理模式 (1=single, 2=batch)
        house_id: 单个家庭处理时的house ID
        interactive: 是否使用交互模式
    """
    # 转换数字模式为字符串模式
    if mode == 1:
        processing_mode = "single"
    elif mode == 2:
        processing_mode = "batch"
    else:
        print("❌ Invalid mode. Using single mode as default.")
        processing_mode = "single"
    
    workflow = IntegratedWorkflow()
    workflow.run_complete_workflow(interactive, tariff_group, processing_mode, house_id)


def parse_args():
    parser = argparse.ArgumentParser(description="Test Function 6 Integration Tool - 集成执行 P051~P054 工具的完整流程")
    parser.add_argument(
        "--tariff-group", 
        type=str, 
        default="UK",
        choices=["UK", "TOU_D", "Germany_Variable"],
        help="电价方案组 (default: UK)"
    )
    parser.add_argument(
        "--mode", 
        type=int, 
        default=2,
        choices=[1, 2],
        help="处理模式: 1=Single household (default), 2=Batch processing"
    )
    parser.add_argument(
        "--house-id", 
        type=str, 
        default="house1",
        help="单个家庭处理时的house ID (default: house1)"
    )
    parser.add_argument(
        "--interactive", 
        action="store_true",
        help="使用交互模式 (默认使用命令行参数)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print("args:", args)
    main(args.tariff_group, args.mode, args.house_id, args.interactive)
