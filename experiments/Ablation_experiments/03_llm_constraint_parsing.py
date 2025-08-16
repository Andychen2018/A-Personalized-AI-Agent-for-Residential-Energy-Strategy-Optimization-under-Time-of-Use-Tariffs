import json
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from constraint_parsing_test import ConstraintParsingExperiment

def test_llm_constraint_parsing_detailed():
    """详细测试LLM约束解析功能 - 按复杂度分析"""
    print("🤖 详细测试LLM约束解析功能...")
    print("📊 按复杂度分类分析性能")
    
    # 加载用户约束样本数据
    dataset_path = os.path.join(current_dir, "user_appliance_constraint_samples.json")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    experiment = ConstraintParsingExperiment()
    results = {"detailed_parsing_results": [], "complexity_analysis": {}}
    
    # 按复杂度分类测试
    complexity_results = {"simple": [], "moderate": [], "complex": []}
    
    constraint_samples = dataset["constraint_samples"]
    
    for i, sample in enumerate(constraint_samples):
        print(f"🔄 LLM详细解析进度: {i+1}/{len(constraint_samples)}")
        
        try:
            predicted = experiment.parse_constraint_with_llm(sample["input"])
            f1_scores = experiment.calculate_f1_score(predicted, sample["ground_truth"])
            
            result = {
                "sample_id": sample["id"],
                "constraint_text": sample["input"],
                "predicted_parsing": predicted,
                "ground_truth": sample["ground_truth"],
                "f1_scores": f1_scores,
                "complexity_level": sample["ground_truth"]["complexity"]
            }
            
            results["detailed_parsing_results"].append(result)
            complexity_results[result["complexity_level"]].append(f1_scores["overall_f1"])
            
        except Exception as e:
            print(f"❌ 解析失败 {sample['id']}: {e}")
            continue
    
    # 计算各复杂度平均性能
    for complexity, scores in complexity_results.items():
        if scores:
            avg_f1 = sum(scores) / len(scores)
            results["complexity_analysis"][complexity] = {
                "sample_count": len(scores),
                "avg_f1_score": round(avg_f1 * 100, 1),
                "score_distribution": scores[:10]  # 前10个样本分数
            }
    
    # 保存详细结果
    output_file = "experiments/llm_constraint_parsing_detailed_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("✅ LLM约束解析详细测试完成")
    print(f"📊 详细分析结果: {output_file}")
    
    # 打印性能摘要
    print("\n📈 性能摘要:")
    for complexity, analysis in results["complexity_analysis"].items():
        print(f"   {complexity.capitalize()}: {analysis['avg_f1_score']}% F1-Score ({analysis['sample_count']} samples)")
    
    return results

if __name__ == "__main__":
    test_llm_constraint_parsing_detailed()
