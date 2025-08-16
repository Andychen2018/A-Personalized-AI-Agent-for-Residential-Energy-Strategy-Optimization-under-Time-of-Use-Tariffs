import json
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from constraint_parsing_test import ConstraintParsingExperiment

def generate_user_constraint_samples():
    """生成500个用户电器约束样本"""
    print("📊 生成用户电器约束样本数据集...")
    print("🎯 目标: 500个多样化的自然语言约束表达")
    
    experiment = ConstraintParsingExperiment()
    constraint_samples = experiment.generate_500_diverse_constraints()
    
    # 统计分布
    complexity_counts = {"simple": 0, "moderate": 0, "complex": 0}
    for sample in constraint_samples:
        complexity_counts[sample["ground_truth"]["complexity"]] += 1
    
    dataset = {
        "dataset_name": "User Appliance Constraint Samples",
        "description": "500 diverse natural language constraint expressions for household appliance scheduling",
        "total_samples": len(constraint_samples),
        "complexity_distribution": complexity_counts,
        "constraint_samples": constraint_samples
    }
    
    # 保存数据集 - 使用更描述性的文件名
    output_file = "experiments/user_appliance_constraint_samples.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已生成 {len(constraint_samples)} 个用户约束样本")
    print(f"📁 保存至: {output_file}")
    print(f"📊 复杂度分布:")
    print(f"   - 简单约束 (Simple): {complexity_counts['simple']} 个")
    print(f"   - 中等约束 (Moderate): {complexity_counts['moderate']} 个") 
    print(f"   - 复杂约束 (Complex): {complexity_counts['complex']} 个")
    
    return dataset

if __name__ == "__main__":
    generate_user_constraint_samples()