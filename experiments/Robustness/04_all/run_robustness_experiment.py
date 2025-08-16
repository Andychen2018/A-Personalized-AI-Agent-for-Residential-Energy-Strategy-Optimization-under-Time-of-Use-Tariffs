#!/usr/bin/env python3
"""
约束解析错误鲁棒性实验运行脚本
使用错误约束文件运行完整的调度和费用计算流程
"""

import os
import sys
import subprocess
import time
from pathlib import Path

class RobustnessExperimentRunner:
    def __init__(self):
        self.base_dir = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all"
        self.target_houses = [1, 2, 3, 20, 21]
        self.tariff_types = ['Economy_7', 'Economy_10']
        
    def run_command(self, command, description):
        """运行命令并处理输出"""
        print(f"\n🔄 {description}")
        print(f"命令: {command}")
        print("-" * 60)
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=self.base_dir,
                capture_output=True, 
                text=True, 
                timeout=1800  # 30分钟超时
            )
            
            if result.returncode == 0:
                print(f"✅ {description} - 成功完成")
                if result.stdout:
                    print("输出:")
                    print(result.stdout)
                return True
            else:
                print(f"❌ {description} - 执行失败")
                print("错误输出:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} - 执行超时")
            return False
        except Exception as e:
            print(f"💥 {description} - 执行异常: {str(e)}")
            return False
    
    def check_prerequisites(self):
        """检查前置条件"""
        print("🔍 检查前置条件...")
        
        # 检查错误约束文件是否存在
        error_data_dir = os.path.join(self.base_dir, "Error_data/UK")
        if not os.path.exists(error_data_dir):
            print(f"❌ 错误约束文件目录不存在: {error_data_dir}")
            return False
        
        # 检查每个目标家庭的错误约束文件
        missing_files = []
        for tariff_type in self.tariff_types:
            for house_id in self.target_houses:
                constraint_file = os.path.join(
                    error_data_dir, 
                    tariff_type, 
                    f"house{house_id}", 
                    "appliance_reschedulable_spaces.json"
                )
                if not os.path.exists(constraint_file):
                    missing_files.append(constraint_file)
        
        if missing_files:
            print(f"❌ 缺失错误约束文件:")
            for file in missing_files:
                print(f"   - {file}")
            return False
        
        # 检查Error_data文件
        error_data_paths = [
            f"{self.base_dir}/Error_data/UK/Economy_7",
            f"{self.base_dir}/Error_data/UK/Economy_10"
        ]
        
        for path in error_data_paths:
            if not os.path.exists(path):
                print(f"❌ Error_data路径不存在: {path}")
                return False
        
        print("✅ 前置条件检查通过")
        return True
    
    def run_event_scheduling(self):
        """运行事件调度"""
        print("\n" + "="*60)
        print("📅 第1步: 事件调度 (使用错误约束)")
        print("="*60)
        
        success_count = 0
        total_count = len(self.tariff_types)
        
        for tariff_type in self.tariff_types:
            print(f"\n🏷️ 处理电价类型: {tariff_type}")
            
            # 为每个电价类型运行调度
            command = f"python 01event_scheduler.py --tariff {tariff_type} --batch"
            success = self.run_command(
                command, 
                f"事件调度 - {tariff_type}"
            )
            
            if success:
                success_count += 1
            
            time.sleep(2)  # 短暂休息
        
        print(f"\n📊 事件调度完成: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    def run_collision_resolution(self):
        """运行冲突解决"""
        print("\n" + "="*60)
        print("🔧 第2步: 冲突解决")
        print("="*60)
        
        success_count = 0
        total_count = len(self.tariff_types)
        
        for tariff_type in self.tariff_types:
            print(f"\n🏷️ 处理电价类型: {tariff_type}")
            
            command = f"python 02_collision_resolver.py --tariff {tariff_type} --batch"
            success = self.run_command(
                command, 
                f"冲突解决 - {tariff_type}"
            )
            
            if success:
                success_count += 1
            
            time.sleep(2)
        
        print(f"\n📊 冲突解决完成: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    def run_event_splitting(self):
        """运行事件分割"""
        print("\n" + "="*60)
        print("✂️ 第3步: 事件分割")
        print("="*60)
        
        success_count = 0
        total_count = len(self.tariff_types)
        
        for tariff_type in self.tariff_types:
            print(f"\n🏷️ 处理电价类型: {tariff_type}")
            
            command = f"python 03event_splitter.py --tariff {tariff_type} --batch"
            success = self.run_command(
                command, 
                f"事件分割 - {tariff_type}"
            )
            
            if success:
                success_count += 1
            
            time.sleep(2)
        
        print(f"\n📊 事件分割完成: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    def run_cost_calculation(self):
        """运行费用计算"""
        print("\n" + "="*60)
        print("💰 第4步: 费用计算")
        print("="*60)
        
        success_count = 0
        total_count = len(self.tariff_types)
        
        for tariff_type in self.tariff_types:
            print(f"\n🏷️ 处理电价类型: {tariff_type}")
            
            command = f"python 04_cost_cal.py --tariff {tariff_type} --batch"
            success = self.run_command(
                command, 
                f"费用计算 - {tariff_type}"
            )
            
            if success:
                success_count += 1
            
            time.sleep(2)
        
        print(f"\n📊 费用计算完成: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    def generate_performance_report(self):
        """生成性能报告"""
        print("\n" + "="*60)
        print("📊 第5步: 生成性能报告")
        print("="*60)
        
        # 这里可以添加性能分析代码
        # 比较原始性能和错误约束下的性能
        
        output_dir = os.path.join(self.base_dir, "output")
        if os.path.exists(output_dir):
            print(f"✅ 实验结果已保存到: {output_dir}")
            
            # 列出生成的文件
            for root, dirs, files in os.walk(output_dir):
                level = root.replace(output_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}{file}")
        
        return True
    
    def run_full_experiment(self):
        """运行完整实验"""
        print("🚀 启动约束解析错误鲁棒性实验")
        print("="*60)
        print(f"目标家庭: {self.target_houses}")
        print(f"电价类型: {self.tariff_types}")
        print(f"实验目录: {self.base_dir}")
        
        start_time = time.time()
        
        # 检查前置条件
        if not self.check_prerequisites():
            print("❌ 前置条件检查失败，实验终止")
            return False
        
        # 执行实验步骤
        steps = [
            ("事件调度", self.run_event_scheduling),
            ("冲突解决", self.run_collision_resolution), 
            ("事件分割", self.run_event_splitting),
            ("费用计算", self.run_cost_calculation),
            ("性能报告", self.generate_performance_report)
        ]
        
        failed_steps = []
        
        for step_name, step_func in steps:
            try:
                success = step_func()
                if not success:
                    failed_steps.append(step_name)
                    print(f"⚠️ {step_name} 执行失败，但继续执行后续步骤")
            except Exception as e:
                failed_steps.append(step_name)
                print(f"💥 {step_name} 执行异常: {str(e)}")
        
        # 实验总结
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*60)
        print("🎯 实验完成总结")
        print("="*60)
        print(f"总耗时: {duration:.1f} 秒")
        print(f"成功步骤: {len(steps) - len(failed_steps)}/{len(steps)}")
        
        if failed_steps:
            print(f"失败步骤: {', '.join(failed_steps)}")
            return False
        else:
            print("✅ 所有步骤执行成功！")
            return True

def main():
    """主函数"""
    runner = RobustnessExperimentRunner()
    
    try:
        success = runner.run_full_experiment()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ 实验被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 实验执行异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
