#!/usr/bin/env python3
"""
Test Function 7 Integration Tool
集成执行 P061 成本计算工具

功能：
1. P061: 成本计算器 (Cost Calculator)
   - 读取 P054 事件分割器的输出文件
   - 计算不同电价方案下的成本
   - 支持单个家庭和批量处理
   - 支持 UK、TOU_D、Germany_Variable 电价方案

作者：Agent V2
日期：2025-01-08
"""

import os
import sys
import argparse
from typing import List, Dict, Optional

# 颜色输出函数
def print_magenta(text):
    """打印紫红色文本"""
    print(f"\033[95m{text}\033[0m")

def print_cyan(text):
    """打印青色文本"""
    print(f"\033[96m{text}\033[0m")

# 添加 tools 目录到 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

# 导入 P061 工具模块
try:
    from tools.p_061_cost_cal import (
        process_house_tariff, 
        list_houses, 
        summarize,
        create_total_cost_summary,
        create_tou_d_combined_summary
    )
except ImportError as e:
    print(f"Warning: P061 module could not be imported: {e}")
    print("Please ensure the tools directory is accessible.")


class CostCalculationWorkflow:
    """成本计算工作流程类"""
    
    def __init__(self):
        self.config = {
            'tariff_group': None,      # 'UK', 'TOU_D', 'Germany_Variable'
            'processing_mode': None,   # 'single', 'batch'
            'house_id': None,          # 单个处理时的house ID
            'house_list': None,        # 批处理时的house列表
            'uk_tariffs': None,        # UK电价方案选择
            'tou_d_seasons': None      # TOU_D季节选择
        }
        
    def setup_configuration_from_args(self, tariff_group="UK", processing_mode="single", house_id="house1"):
        """从参数设置配置"""
        # Remove tool introduction output

        # 设置电价方案组
        self.config['tariff_group'] = tariff_group
        print(f"✅ Selected tariff group: {self.config['tariff_group']}")
        
        # Set specific tariff schemes based on tariff group
        if tariff_group == 'UK':
            self.config['uk_tariffs'] = ['Economy_7', 'Economy_10']  # Default: process both UK tariffs
        elif tariff_group == 'TOU_D':
            self.config['tou_d_seasons'] = ['winter', 'summer']      # Default: process both seasons

        # Set processing mode
        self.config['processing_mode'] = processing_mode
        
        if processing_mode == "single":
            # Ensure house ID format is correct
            if house_id.isdigit():
                house_id = f"house{house_id}"
            elif not house_id.startswith("house"):
                house_id = f"house{house_id}"
            self.config['house_id'] = house_id
            print(f"✅ Selected processing mode: Single household processing ({house_id})")
        else:
            # Batch processing: fixed house1~house21, excluding house12 and house14
            available_houses = [f"house{i}" for i in range(1, 22) if i not in [12, 14]]
            self.config['house_list'] = available_houses
            print(f"✅ Selected processing mode: Batch processing ({len(available_houses)} households)")
        
        print()
        return True
        
    def setup_configuration(self):
        """设置全局配置参数"""
        print("🎯 Test Function 7 Integration Tool")
        print("=" * 60)
        print("集成执行 P061 成本计算工具")
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
        print(f"✅ 已选择电价方案组: {self.config['tariff_group']}")
        
        # 根据电价方案进行具体配置
        if self.config['tariff_group'] == 'UK':
            print("\n📋 UK 电价方案选择:")
            print("1. Economy_7")
            print("2. Economy_10")
            print("3. 两种方案都处理 [默认]")
            
            try:
                uk_choice = input("选择UK电价方案 (1-3) [默认: 3]: ").strip()
                if not uk_choice:
                    uk_choice = "3"
            except (EOFError, KeyboardInterrupt):
                uk_choice = "3"
                
            if uk_choice == "1":
                self.config['uk_tariffs'] = ['Economy_7']
            elif uk_choice == "2":
                self.config['uk_tariffs'] = ['Economy_10']
            else:
                self.config['uk_tariffs'] = ['Economy_7', 'Economy_10']
                
        elif self.config['tariff_group'] == 'TOU_D':
            print("\n📋 TOU_D 季节选择:")
            print("1. Winter")
            print("2. Summer")
            print("3. 两个季节都处理 [默认]")
            
            try:
                season_choice = input("选择TOU_D季节 (1-3) [默认: 3]: ").strip()
                if not season_choice:
                    season_choice = "3"
            except (EOFError, KeyboardInterrupt):
                season_choice = "3"
                
            if season_choice == "1":
                self.config['tou_d_seasons'] = ['winter']
            elif season_choice == "2":
                self.config['tou_d_seasons'] = ['summer']
            else:
                self.config['tou_d_seasons'] = ['winter', 'summer']
        
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
        if self.config['tariff_group'] == 'UK':
            print(f"   UK tariff schemes: {self.config['uk_tariffs']}")
        elif self.config['tariff_group'] == 'TOU_D':
            print(f"   TOU_D seasons: {self.config['tou_d_seasons']}")

    def run_p061_cost_calculator(self):
        """Execute Cost Calculation & Analysis"""
        print(f"\n{'='*120}")
        print("🚀 STEP 1: Cost Calculation & Analysis")
        print(f"{'='*120}")
        
        try:
            # Determine target household list
            if self.config['processing_mode'] == 'single':
                target_houses = [self.config['house_id']]
            else:
                # Batch processing: filter from available households
                available_houses = list_houses()
                target_houses = [h for h in self.config['house_list'] if h in available_houses]
                print(f"📊 Found {len(target_houses)} processable households")
            
            # Generate task list (tariff, scope)
            tasks = []
            if self.config['tariff_group'] == 'UK':
                for tariff in self.config['uk_tariffs']:
                    tasks.append((tariff, tariff))  # UK: tariff and scope are the same
            elif self.config['tariff_group'] == 'TOU_D':
                for season in self.config['tou_d_seasons']:
                    tasks.append(('TOU_D', season))  # TOU_D: tariff='TOU_D', scope=season
            elif self.config['tariff_group'] == 'Germany_Variable':
                tasks.append(('Germany_Variable', 'All'))  # Germany: scope='All'
            
            # 执行成本计算
            total_tasks = len(target_houses) * len(tasks)
            current_task = 0
            all_stats = []
            
            print(f"📊 Starting processing for {len(target_houses)} household(s), {len(tasks)} tariff scheme(s), total {total_tasks} task(s)")

            for house_id in target_houses:
                for tariff, scope in tasks:
                    current_task += 1
                    print(f"\n📊 [{current_task}/{total_tasks}] Calculating costs for {house_id} under {tariff} tariff scheme...")

                    try:
                        stats = process_house_tariff(house_id, tariff, scope)
                        all_stats.append(stats)
                        print(f"✅ Cost calculation completed for {house_id} - {tariff}/{scope}")
                    except FileNotFoundError as e:
                        print(f"⚠️  Skipped {house_id} {tariff}/{scope}: Required data files not found")
                    except Exception as e:
                        print(f"❌ Cost calculation failed for {house_id} {tariff}/{scope}: {e}")
            
            # Generate summary report
            if all_stats:
                print(f"\n📊 Generating summary report...")
                
                if self.config['tariff_group'] == 'TOU_D':
                    # TOU_D 特殊处理：先显示分季节汇总，再显示合并汇总
                    summarize(all_stats)
                    create_tou_d_combined_summary(all_stats)
                else:
                    # UK 和 Germany_Variable 的常规处理
                    summarize(all_stats)
                    
                    # 添加总费用对比表格
                    if self.config['tariff_group'] in ['UK', 'Germany_Variable']:
                        create_total_cost_summary(all_stats, self.config['tariff_group'])

            print("--- STEP 1: Cost Calculation & Analysis COMPLETED ---")

            # 添加推荐功能
            if self.config['tariff_group'] == 'UK':
                print(f"\n{'='*120}")
                print("🚀 STEP 2: Intelligent Tariff Recommendation")
                print(f"{'='*120}")
                self._generate_uk_recommendations(all_stats)
                print("--- STEP 2: Intelligent Tariff Recommendation COMPLETED ---")

            return True

        except Exception as e:
            print(f"❌ STEP 1: Cost Calculation & Analysis FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_complete_workflow(self, interactive=True, tariff_group="UK", processing_mode="single", house_id="house1"):
        """执行完整工作流程"""
        if interactive:
            success = self.setup_configuration()
        else:
            success = self.setup_configuration_from_args(tariff_group, processing_mode, house_id)
            
        if not success:
            return False
        
        # Confirm execution (only ask in interactive mode)
        if interactive:
            print(f"\n⚠️  About to start cost calculation, this may take a long time...")
            try:
                confirm = input("Continue? (y/N) [default: N]: ").strip().lower()
                if confirm not in ['y', 'yes', '1']:
                    print("❌ User cancelled execution")
                    return False
            except (EOFError, KeyboardInterrupt):
                print("❌ User cancelled execution")
                return False
        else:
            print(f"\n🚀 Starting cost calculation...")
            
        # 执行成本计算
        success = self.run_p061_cost_calculator()
        
        # Summary
        print(f"\n{'='*120}")
        print("🎯 Cost Calculation Execution Summary")
        print(f"{'='*120}")
        print(f"📊 Configuration Information:")
        print(f"   Tariff group: {self.config['tariff_group']}")
        print(f"   Processing mode: {self.config['processing_mode']}")
        if self.config['processing_mode'] == 'single':
            print(f"   Target household: {self.config['house_id']}")
        else:
            print(f"   Target households: {len(self.config['house_list'])} households")
        if self.config['tariff_group'] == 'UK':
            print(f"   UK tariff schemes: {self.config['uk_tariffs']}")
        elif self.config['tariff_group'] == 'TOU_D':
            print(f"   TOU_D seasons: {self.config['tou_d_seasons']}")

        if success:
            print("🎉 Cost calculation executed successfully!")
            print(f"📁 Output directory: output/06_cost_cal/")
            return True
        else:
            print("❌ Cost calculation execution failed, please check error messages")
            return False

    def _generate_uk_recommendations(self, all_stats):
        """Generate UK tariff scheme recommendations"""
        print(f"\n🎯 UK Tariff Scheme Recommendations")
        print("-"*120)

        # 按家庭分组统计
        house_summary = {}
        for stat in all_stats:
            house_id = stat['house_id']
            scope = stat['scope']  # Economy_7 或 Economy_10

            if house_id not in house_summary:
                house_summary[house_id] = {}

            # 计算总费用 (非迁移 + 迁移后)
            total_cost = stat['non_cost'] + stat['mig_sched_cost']
            house_summary[house_id][scope] = total_cost

        # 生成推荐表格
        print(f"{'House ID':10} {'Economy_7':>12} {'Economy_10':>12} {'Savings':>12} {'Recommended':>15}")
        print(f"{'':10} {'Total Cost':>12} {'Total Cost':>12} {'(£)':>12} {'Tariff':>15}")
        print("-"*120)

        total_savings = 0.0
        economy_7_count = 0
        economy_10_count = 0

        # 按数字顺序排序 house ID
        def house_sort_key(house_id):
            try:
                return int(house_id.replace('house', ''))
            except:
                return 999

        for house_id in sorted(house_summary.keys(), key=house_sort_key):
            house_data = house_summary[house_id]

            # 确保两种电价方案都有数据
            if 'Economy_7' not in house_data or 'Economy_10' not in house_data:
                continue

            economy_7_cost = house_data['Economy_7']
            economy_10_cost = house_data['Economy_10']

            # 确定推荐方案（费用更低的）
            if economy_7_cost <= economy_10_cost:
                recommended = "Economy_7"
                savings = economy_10_cost - economy_7_cost
                economy_7_count += 1
            else:
                recommended = "Economy_10"
                savings = economy_7_cost - economy_10_cost
                economy_10_count += 1

            total_savings += savings

            print(f"{house_id:10} {economy_7_cost:12.2f} {economy_10_cost:12.2f} {savings:12.2f} {recommended:>15}")

        print("-"*120)

        # 美化推荐结果显示
        self._display_beautiful_recommendation_summary(economy_7_count, economy_10_count, total_savings)

        # 保存推荐结果到文件
        self._save_uk_recommendations(house_summary)

    def _display_beautiful_recommendation_summary(self, economy_7_count, economy_10_count, total_savings):
        """显示美化的推荐结果摘要"""
        print()
        print_magenta("╔" + "═" * 120 + "╗")
        print_magenta("║" + " " * 41 + "🎯 INTELLIGENT TARIFF RECOMMENDATION SYSTEM" + " " * 36 + "║")
        print_magenta("╠" + "═" * 120 + "╣")

        # 确定主要推荐方案
        if economy_7_count > economy_10_count:
            primary_recommendation = "Economy_7"
            primary_count = economy_7_count
            secondary_recommendation = "Economy_10"
            secondary_count = economy_10_count
        else:
            primary_recommendation = "Economy_10"
            primary_count = economy_10_count
            secondary_recommendation = "Economy_7"
            secondary_count = economy_7_count

        # 显示主要推荐
        if primary_count > 0:
            # 主要标题行 - 有右侧边框
            line1 = f"║  🏆 RECOMMENDED TARIFF: {primary_recommendation:<20} 💡 SMART CHOICE!"
            print_magenta(f"{line1:<119}║")
            print_magenta(f"║{' ' * 120}║")

            # 分析结果标题 - 有右侧边框
            line2 = f"║   📊 Analysis Results:"
            print_magenta(f"{line2:<120}║")

            # 子项目 - 无右侧边框
            line3 = f"║     • {primary_recommendation} recommended for: {primary_count:>2} household(s)"
            print_magenta(line3)

            if secondary_count > 0:
                line4 = f"║     • {secondary_recommendation} recommended for: {secondary_count:>2} household(s)"
                print_magenta(line4)

            print_magenta(f"║{' ' * 120}║")

            # 财务收益标题 - 有右侧边框
            line5 = f"║   💰 Financial Benefits:"
            print_magenta(f"{line5:<120}║")

            # 子项目 - 无右侧边框
            line6 = f"║     • Total potential savings: £{total_savings:>8.2f}"
            print_magenta(line6)

            total_households = economy_7_count + economy_10_count
            if total_households > 0:
                avg_savings = total_savings / total_households
                line7 = f"║     • Average savings per household: £{avg_savings:>8.2f}"
                print_magenta(line7)

            print_magenta(f"║{' ' * 120}║")

            # 推荐基础标题 - 有右侧边框
            line8 = f"║   🔍 Recommendation Basis:"
            print_magenta(f"{line8:<120}║")

            # 子项目 - 无右侧边框
            line9 = f"║     • Comprehensive cost analysis across all tariff options"
            print_magenta(line9)

            line10 = f"║     • Optimized scheduling with smart load shifting"
            print_magenta(line10)

            line11 = f"║     • Personalized recommendations based on usage patterns"
            print_magenta(line11)

            print_magenta(f"║{' ' * 120}║")

            # Why标题 - 有右侧边框
            line12 = f"║   💡 Why {primary_recommendation}?"
            print_magenta(f"{line12:<120}║")

            # 子项目 - 无右侧边框
            if primary_recommendation == "Economy_10":
                line13 = f"║     • 10-hour off-peak period (00:30-07:30 + 13:30-16:30)"
                print_magenta(line13)

                line14 = f"║     • More flexible scheduling opportunities"
                print_magenta(line14)

                line15 = f"║     • Better suited for households with diverse appliance usage"
                print_magenta(line15)
            else:
                line13 = f"║     • 7-hour continuous off-peak period (00:30-07:30)"
                print_magenta(line13)

                line14 = f"║     • Simpler time-of-use structure"
                print_magenta(line14)

                line15 = f"║     • Ideal for households with concentrated night-time usage"
                print_magenta(line15)
        else:
            line_no_data = f"║   ⚠️  No recommendations available - insufficient data"
            print_magenta(f"{line_no_data:<120}║")

        print_magenta(f"║{' ' * 120}║")
        print_magenta("╚" + "═" * 120 + "╝")
        print()

        # 添加文件保存提示
        print("💾 📋 Detailed recommendation report saved to:")
        print("   📁 output/06_cost_cal/UK/tariff_recommendations.csv")
        print()
        print("✅ 🎉 Intelligent recommendation analysis completed successfully!")

    def _save_uk_recommendations(self, house_summary):
        """保存UK推荐结果到文件"""
        import os
        import csv

        # 创建输出目录
        output_dir = "output/06_cost_cal/UK"
        os.makedirs(output_dir, exist_ok=True)

        # 保存推荐结果
        recommendations_file = os.path.join(output_dir, "tariff_recommendations.csv")

        with open(recommendations_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['House_ID', 'Economy_7_Cost', 'Economy_10_Cost', 'Recommended_Tariff', 'Savings'])

            # 按数字顺序排序
            def house_sort_key(house_id):
                try:
                    return int(house_id.replace('house', ''))
                except:
                    return 999

            for house_id in sorted(house_summary.keys(), key=house_sort_key):
                house_data = house_summary[house_id]

                if 'Economy_7' not in house_data or 'Economy_10' not in house_data:
                    continue

                economy_7_cost = house_data['Economy_7']
                economy_10_cost = house_data['Economy_10']

                if economy_7_cost <= economy_10_cost:
                    recommended = "Economy_7"
                    savings = economy_10_cost - economy_7_cost
                else:
                    recommended = "Economy_10"
                    savings = economy_7_cost - economy_10_cost

                writer.writerow([house_id, f"{economy_7_cost:.2f}", f"{economy_10_cost:.2f}", recommended, f"{savings:.2f}"])

        # 文件保存提示已在美化显示中包含


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
    
    workflow = CostCalculationWorkflow()
    workflow.run_complete_workflow(interactive, tariff_group, processing_mode, house_id)


def parse_args():
    parser = argparse.ArgumentParser(description="Test Function 7 Integration Tool - 集成执行 P061 成本计算工具")
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
        default=1,
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
