#!/usr/bin/env python3
"""
约束解析错误生成器
随机选取5%的约束条目并引入错误，用于鲁棒性分析实验
"""

import json
import os
import random
import copy
from pathlib import Path
import numpy as np

class ConstraintErrorGenerator:
    def __init__(self, error_rate=0.05, seed=42):
        """
        初始化约束错误生成器
        
        Args:
            error_rate: 错误率，默认5%
            seed: 随机种子，确保结果可重现
        """
        self.error_rate = error_rate
        random.seed(seed)
        np.random.seed(seed)
        
    def load_original_constraints(self, file_path):
        """加载原始约束文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_corrupted_constraints(self, constraints, output_path):
        """保存损坏的约束文件"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(constraints, f, indent=2, ensure_ascii=False)
    
    def get_modifiable_constraints(self, constraints_data):
        """
        获取所有可修改的约束条目
        返回: [(appliance_name, constraint_type, constraint_path), ...]
        """
        modifiable_items = []
        
        for appliance_name, appliance_data in constraints_data.items():
            if 'constraints' in appliance_data:
                constraint_obj = appliance_data['constraints']
                
                # 1. forbidden_time 时间段
                if 'forbidden_time' in constraint_obj:
                    for i, time_range in enumerate(constraint_obj['forbidden_time']):
                        modifiable_items.append((
                            appliance_name, 
                            'forbidden_time', 
                            f'constraints.forbidden_time[{i}]'
                        ))
                
                # 2. latest_finish 时间
                if 'latest_finish' in constraint_obj:
                    modifiable_items.append((
                        appliance_name,
                        'latest_finish',
                        'constraints.latest_finish'
                    ))
                
                # 3. shift_rule 规则
                if 'shift_rule' in constraint_obj:
                    modifiable_items.append((
                        appliance_name,
                        'shift_rule', 
                        'constraints.shift_rule'
                    ))
                
                # 4. min_duration 最小持续时间
                if 'min_duration' in constraint_obj:
                    modifiable_items.append((
                        appliance_name,
                        'min_duration',
                        'constraints.min_duration'
                    ))
        
        return modifiable_items
    
    def corrupt_time_range(self, time_range):
        """损坏时间范围"""
        start_time, end_time = time_range
        
        corruption_type = random.choice([
            'swap_times',      # 交换开始和结束时间
            'extend_range',    # 扩展时间范围
            'shrink_range',    # 缩小时间范围
            'shift_range'      # 整体偏移时间范围
        ])
        
        if corruption_type == 'swap_times':
            return [end_time, start_time]
        
        elif corruption_type == 'extend_range':
            # 随机扩展1-3小时
            extend_hours = random.randint(1, 3)
            new_start = self.adjust_time(start_time, -extend_hours * 60)
            new_end = self.adjust_time(end_time, extend_hours * 60)
            return [new_start, new_end]
        
        elif corruption_type == 'shrink_range':
            # 随机缩小30分钟-2小时
            shrink_minutes = random.randint(30, 120)
            new_start = self.adjust_time(start_time, shrink_minutes)
            new_end = self.adjust_time(end_time, -shrink_minutes)
            return [new_start, new_end]
        
        elif corruption_type == 'shift_range':
            # 整体偏移1-4小时
            shift_hours = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
            shift_minutes = shift_hours * 60
            new_start = self.adjust_time(start_time, shift_minutes)
            new_end = self.adjust_time(end_time, shift_minutes)
            return [new_start, new_end]
        
        return time_range
    
    def adjust_time(self, time_str, minutes_delta):
        """调整时间字符串"""
        # 解析时间 (格式: "HH:MM")
        hours, minutes = map(int, time_str.split(':'))
        total_minutes = hours * 60 + minutes + minutes_delta
        
        # 处理跨天情况
        total_minutes = total_minutes % (24 * 60)
        if total_minutes < 0:
            total_minutes += 24 * 60
        
        new_hours = total_minutes // 60
        new_minutes = total_minutes % 60
        
        return f"{new_hours:02d}:{new_minutes:02d}"
    
    def corrupt_latest_finish(self, latest_finish):
        """损坏最晚完成时间"""
        corruption_type = random.choice([
            'earlier_finish',   # 提前完成时间
            'later_finish',     # 延后完成时间
            'invalid_time'      # 设置无效时间
        ])
        
        if corruption_type == 'earlier_finish':
            # 提前2-6小时
            hours_earlier = random.randint(2, 6)
            return self.adjust_time(latest_finish, -hours_earlier * 60)
        
        elif corruption_type == 'later_finish':
            # 延后2-8小时
            hours_later = random.randint(2, 8)
            return self.adjust_time(latest_finish, hours_later * 60)
        
        elif corruption_type == 'invalid_time':
            # 设置明显无效的时间
            return random.choice(["25:00", "48:00", "99:99", "00:00"])
        
        return latest_finish
    
    def corrupt_shift_rule(self, shift_rule):
        """损坏调度规则"""
        rules = ["only_delay", "only_advance", "both", "none"]
        available_rules = [r for r in rules if r != shift_rule]
        return random.choice(available_rules)
    
    def corrupt_min_duration(self, min_duration):
        """损坏最小持续时间"""
        corruption_type = random.choice([
            'increase_duration',  # 增加持续时间
            'decrease_duration',  # 减少持续时间
            'invalid_duration'    # 设置无效持续时间
        ])
        
        if corruption_type == 'increase_duration':
            # 增加5-30分钟
            return min_duration + random.randint(5, 30)
        
        elif corruption_type == 'decrease_duration':
            # 减少1-5分钟，但不小于1
            decrease = random.randint(1, min(5, min_duration - 1))
            return max(1, min_duration - decrease)
        
        elif corruption_type == 'invalid_duration':
            # 设置无效持续时间
            return random.choice([0, -1, 999, 1440])  # 0, 负数, 过大值
        
        return min_duration
    
    def apply_constraint_corruption(self, constraints_data, appliance_name, constraint_type, constraint_path):
        """应用约束损坏"""
        corrupted_data = copy.deepcopy(constraints_data)
        
        if constraint_type == 'forbidden_time':
            # 解析路径获取索引
            path_parts = constraint_path.split('[')
            index = int(path_parts[1].split(']')[0])
            original_range = corrupted_data[appliance_name]['constraints']['forbidden_time'][index]
            corrupted_range = self.corrupt_time_range(original_range)
            corrupted_data[appliance_name]['constraints']['forbidden_time'][index] = corrupted_range
        
        elif constraint_type == 'latest_finish':
            original_time = corrupted_data[appliance_name]['constraints']['latest_finish']
            corrupted_time = self.corrupt_latest_finish(original_time)
            corrupted_data[appliance_name]['constraints']['latest_finish'] = corrupted_time
        
        elif constraint_type == 'shift_rule':
            original_rule = corrupted_data[appliance_name]['constraints']['shift_rule']
            corrupted_rule = self.corrupt_shift_rule(original_rule)
            corrupted_data[appliance_name]['constraints']['shift_rule'] = corrupted_rule
        
        elif constraint_type == 'min_duration':
            original_duration = corrupted_data[appliance_name]['constraints']['min_duration']
            corrupted_duration = self.corrupt_min_duration(original_duration)
            corrupted_data[appliance_name]['constraints']['min_duration'] = corrupted_duration
        
        return corrupted_data
    
    def generate_corrupted_constraints(self, original_file_path, output_file_path):
        """
        生成损坏的约束文件
        
        Args:
            original_file_path: 原始约束文件路径
            output_file_path: 输出损坏约束文件路径
        
        Returns:
            dict: 包含损坏信息的统计数据
        """
        # 加载原始约束
        constraints_data = self.load_original_constraints(original_file_path)
        
        # 获取所有可修改的约束条目
        modifiable_items = self.get_modifiable_constraints(constraints_data)
        
        # 计算需要损坏的条目数量
        num_to_corrupt = max(1, int(len(modifiable_items) * self.error_rate))
        
        # 随机选择要损坏的条目
        items_to_corrupt = random.sample(modifiable_items, num_to_corrupt)
        
        # 应用损坏
        corrupted_data = copy.deepcopy(constraints_data)
        corruption_log = []
        
        for appliance_name, constraint_type, constraint_path in items_to_corrupt:
            original_value = self.get_constraint_value(constraints_data, appliance_name, constraint_type, constraint_path)
            corrupted_data = self.apply_constraint_corruption(corrupted_data, appliance_name, constraint_type, constraint_path)
            new_value = self.get_constraint_value(corrupted_data, appliance_name, constraint_type, constraint_path)
            
            corruption_log.append({
                'appliance': appliance_name,
                'constraint_type': constraint_type,
                'constraint_path': constraint_path,
                'original_value': original_value,
                'corrupted_value': new_value
            })
        
        # 保存损坏的约束文件
        self.save_corrupted_constraints(corrupted_data, output_file_path)
        
        # 返回统计信息
        return {
            'total_constraints': len(modifiable_items),
            'corrupted_constraints': num_to_corrupt,
            'error_rate': num_to_corrupt / len(modifiable_items),
            'corruption_log': corruption_log,
            'output_file': output_file_path
        }
    
    def get_constraint_value(self, constraints_data, appliance_name, constraint_type, constraint_path):
        """获取约束值用于日志记录"""
        if constraint_type == 'forbidden_time':
            path_parts = constraint_path.split('[')
            index = int(path_parts[1].split(']')[0])
            return constraints_data[appliance_name]['constraints']['forbidden_time'][index]
        elif constraint_type == 'latest_finish':
            return constraints_data[appliance_name]['constraints']['latest_finish']
        elif constraint_type == 'shift_rule':
            return constraints_data[appliance_name]['constraints']['shift_rule']
        elif constraint_type == 'min_duration':
            return constraints_data[appliance_name]['constraints']['min_duration']
        return None


def main():
    """主函数：为指定的家庭生成约束错误"""
    
    # 配置参数
    target_houses = [1, 2, 3, 20, 21]  # 目标家庭
    tariff_types = ['Economy_7', 'Economy_10']  # 电价类型
    error_rate = 0.05  # 5%错误率
    
    # 路径配置
    base_original_path = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/03Constraint_Parsing_Errors/Original_data/UK"
    base_error_path = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/03Constraint_Parsing_Errors/Error_data/UK"
    
    # 初始化错误生成器
    generator = ConstraintErrorGenerator(error_rate=error_rate)
    
    # 处理每个家庭和电价类型的组合
    all_results = {}
    
    for tariff_type in tariff_types:
        all_results[tariff_type] = {}
        
        for house_id in target_houses:
            print(f"处理 {tariff_type}/house{house_id}...")
            
            # 构建文件路径
            original_file = os.path.join(
                base_original_path, 
                tariff_type, 
                f"house{house_id}", 
                "appliance_reschedulable_spaces.json"
            )
            
            error_file = os.path.join(
                base_error_path,
                tariff_type,
                f"house{house_id}",
                "appliance_reschedulable_spaces.json"
            )
            
            # 检查原始文件是否存在
            if not os.path.exists(original_file):
                print(f"警告: 原始文件不存在 - {original_file}")
                continue
            
            try:
                # 生成损坏的约束
                result = generator.generate_corrupted_constraints(original_file, error_file)
                all_results[tariff_type][f"house{house_id}"] = result
                
                print(f"  ✓ 成功生成错误约束")
                print(f"    总约束数: {result['total_constraints']}")
                print(f"    损坏约束数: {result['corrupted_constraints']}")
                print(f"    实际错误率: {result['error_rate']:.1%}")
                print(f"    输出文件: {error_file}")
                
            except Exception as e:
                print(f"  ✗ 处理失败: {str(e)}")
                continue
    
    # 保存处理结果日志
    log_file = os.path.join(base_error_path, "constraint_corruption_log.json")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n所有处理完成！")
    print(f"详细日志保存在: {log_file}")
    
    # 打印总体统计
    total_files = sum(len(houses) for houses in all_results.values())
    print(f"成功处理文件数: {total_files}")


if __name__ == "__main__":
    main()
