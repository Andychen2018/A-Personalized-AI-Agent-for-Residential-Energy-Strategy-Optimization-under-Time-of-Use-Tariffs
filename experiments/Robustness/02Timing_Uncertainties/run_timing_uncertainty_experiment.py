#!/usr/bin/env python3
"""
时间不确定性鲁棒性实验运行器
完整运行时间不确定性扰动实验的所有步骤
"""

import os
import sys
import subprocess
import time
from datetime import datetime

class TimingUncertaintyExperiment:
    def __init__(self):
        self.base_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/02Timing_Uncertainties"
        self.target_houses = ["house1", "house2", "house3", "house20", "house21"]
        self.tariff_types = ["Economy_7", "Economy_10"]
        
        # 实验步骤
        self.steps = [
            {
                "name": "时间不确定性数据生成",
                "script": "00generate_timing_uncertainties.py",
                "description": "对事件时间加入±5分钟随机扰动"
            },
            {
                "name": "事件调度优化",
                "script": "01event_scheduler.py",
                "description": "使用扰动后的事件数据进行调度优化"
            },
            {
                "name": "冲突解决",
                "script": "02_collision_resolver.py",
                "description": "解决调度冲突"
            },
            {
                "name": "事件分割",
                "script": "03_event_splitter.py",
                "description": "分离迁移和未迁移事件"
            },
            {
                "name": "费用计算",
                "script": "04_cost_cal.py",
                "description": "计算电费成本"
            },
            {
                "name": "鲁棒性分析",
                "script": "05_robustness_analysis.py",
                "description": "分析性能保持率"
            }
        ]
    
    def run_step(self, step_info):
        """运行单个实验步骤"""
        print(f"\n🚀 步骤: {step_info['name']}")
        print(f"📝 描述: {step_info['description']}")
        print(f"🔧 脚本: {step_info['script']}")
        print("-" * 60)
        
        script_path = os.path.join(self.base_dir, step_info['script'])
        
        if not os.path.exists(script_path):
            print(f"❌ 脚本文件不存在: {script_path}")
            return False
        
        try:
            start_time = time.time()
            
            # 运行脚本
            result = subprocess.run(
                [sys.executable, step_info['script']],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ {step_info['name']} 完成 (耗时: {duration:.1f}秒)")
                if result.stdout:
                    print("📊 输出:")
                    print(result.stdout)
                return True
            else:
                print(f"❌ {step_info['name']} 失败 (返回码: {result.returncode})")
                if result.stderr:
                    print("🚨 错误信息:")
                    print(result.stderr)
                if result.stdout:
                    print("📊 输出:")
                    print(result.stdout)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {step_info['name']} 超时 (30分钟)")
            return False
        except Exception as e:
            print(f"💥 {step_info['name']} 异常: {str(e)}")
            return False
    
    def check_prerequisites(self):
        """检查实验前提条件"""
        print("🔍 检查实验前提条件...")
        print("=" * 60)
        
        # 检查原始数据
        original_data_dir = os.path.join(self.base_dir, "Original_data/UK")
        if not os.path.exists(original_data_dir):
            print(f"❌ 原始数据目录不存在: {original_data_dir}")
            return False
        
        # 检查约束文件
        constraint_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/03Constraint_Parsing_Errors/Original_data/UK"
        if not os.path.exists(constraint_dir):
            print(f"❌ 约束文件目录不存在: {constraint_dir}")
            return False
        
        # 检查基线费用数据
        baseline_dir = "/home/deep/TimeSeries/Agent_V2/output/06_cost_cal/UK"
        if not os.path.exists(baseline_dir):
            print(f"❌ 基线费用数据目录不存在: {baseline_dir}")
            return False
        
        # 检查目标房屋和电价类型的数据完整性
        missing_files = []
        for tariff_type in self.tariff_types:
            for house_id in self.target_houses:
                # 检查原始事件数据
                event_file = os.path.join(original_data_dir, tariff_type, house_id, f"tou_filtered_{house_id}_{tariff_type}.csv")
                if not os.path.exists(event_file):
                    missing_files.append(f"原始事件: {event_file}")
                
                # 检查约束文件
                constraint_file = os.path.join(constraint_dir, tariff_type, house_id, "appliance_reschedulable_spaces.json")
                if not os.path.exists(constraint_file):
                    missing_files.append(f"约束文件: {constraint_file}")
                
                # 检查基线费用数据
                baseline_migrated = os.path.join(baseline_dir, tariff_type, house_id, "migrated_costs.csv")
                baseline_non_migrated = os.path.join(baseline_dir, tariff_type, house_id, "non_migrated_costs.csv")
                if not os.path.exists(baseline_migrated):
                    missing_files.append(f"基线迁移费用: {baseline_migrated}")
                if not os.path.exists(baseline_non_migrated):
                    missing_files.append(f"基线非迁移费用: {baseline_non_migrated}")
        
        if missing_files:
            print("❌ 缺少以下必要文件:")
            for file in missing_files[:10]:  # 只显示前10个
                print(f"   - {file}")
            if len(missing_files) > 10:
                print(f"   ... 还有 {len(missing_files) - 10} 个文件")
            return False
        
        print("✅ 所有前提条件检查通过")
        return True
    
    def run_experiment(self):
        """运行完整的时间不确定性实验"""
        print("🚀 时间不确定性鲁棒性实验")
        print("=" * 80)
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🏠 目标房屋: {', '.join(self.target_houses)}")
        print(f"💰 电价类型: {', '.join(self.tariff_types)}")
        print(f"⏱️ 扰动范围: ±5分钟")
        print()
        
        # 检查前提条件
        if not self.check_prerequisites():
            print("\n❌ 前提条件检查失败，实验终止")
            return False
        
        # 运行实验步骤
        successful_steps = 0
        total_steps = len(self.steps)
        
        for i, step in enumerate(self.steps, 1):
            print(f"\n📍 步骤 {i}/{total_steps}")
            
            if self.run_step(step):
                successful_steps += 1
            else:
                print(f"\n💥 步骤 {i} 失败，实验终止")
                break
        
        # 实验总结
        print(f"\n📊 实验总结:")
        print("=" * 60)
        print(f"✅ 成功步骤: {successful_steps}/{total_steps}")
        print(f"📅 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if successful_steps == total_steps:
            print("🎉 时间不确定性鲁棒性实验完成！")
            print(f"📁 结果文件: {self.base_dir}/timing_uncertainty_analysis.json")
            return True
        else:
            print("❌ 实验未完全成功")
            return False

def main():
    """主函数"""
    experiment = TimingUncertaintyExperiment()
    
    try:
        success = experiment.run_experiment()
        return success
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断实验")
        return False
    except Exception as e:
        print(f"\n💥 实验异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
