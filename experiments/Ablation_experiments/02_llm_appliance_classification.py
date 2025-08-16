import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from llm import chat_with_api

class ApplianceClassificationExperiment:
    def __init__(self):
        """初始化电器分类实验"""
        self.load_base_appliance_dict()
        self.load_extended_test_dataset()
        print(f"🏠 从扩充测试集加载了 {len(self.test_appliances)} 个电器进行分类测试")
        print(f"📚 基础词典包含 {len(self.base_appliance_dict)} 个标准电器")
        self.print_dataset_summary()
    
    def load_base_appliance_dict(self):
        """加载280个基础电器词典作为查询库"""
        dict_path = os.path.join(project_root, "config", "appliance_shiftability_dict.json")
        
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                self.base_appliance_dict = json.load(f)
            print(f"📚 成功加载基础电器词典: {len(self.base_appliance_dict)} 个电器")
        except FileNotFoundError:
            print(f"❌ 未找到基础词典文件: {dict_path}")
            self.base_appliance_dict = {}
    
    def load_extended_test_dataset(self):
        """从extended_appliance_test_dataset.json加载测试数据"""
        dataset_path = os.path.join(current_dir, "extended_appliance_test_dataset.json")
        
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            print(f"📁 成功加载扩充测试集: {dataset_path}")
            
            # 提取测试用例
            self.test_appliances = []
            for test_case in dataset.get("test_cases", []):
                self.test_appliances.append({
                    "name": test_case["appliance_name"],
                    "expected": test_case["ground_truth_shiftability"],
                    "base_english": test_case.get("base_english_name", ""),
                    "variant_type": test_case.get("variant_type", "generated")
                })
                    
        except FileNotFoundError:
            print(f"❌ 未找到扩充测试集文件: {dataset_path}")
            print("💡 请先运行 generate_extended_appliance_dataset.py 生成测试数据")
            self.test_appliances = []
        except json.JSONDecodeError as e:
            print(f"❌ JSON文件格式错误: {e}")
            self.test_appliances = []
    
    def exact_match_in_dict(self, appliance_name: str) -> Optional[Tuple[str, str]]:
        """在280个词典中进行精确匹配"""
        name_lower = appliance_name.lower().strip()
        
        # 1. 直接匹配英文名称（主键）
        for english_name, info in self.base_appliance_dict.items():
            if english_name.lower() == name_lower:
                return english_name, info.get("shiftability", "").lower()
        
        # 2. 匹配中文名称
        for english_name, info in self.base_appliance_dict.items():
            chinese_name = info.get("chinese_name", "").lower()
            if chinese_name and chinese_name == name_lower:
                return english_name, info.get("shiftability", "").lower()
        
        # 3. 匹配别名（如果有的话）
        for english_name, info in self.base_appliance_dict.items():
            aliases = info.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                if alias.lower() == name_lower:
                    return english_name, info.get("shiftability", "").lower()
        
        return None
    
    def llm_similarity_match(self, appliance_name: str) -> Optional[Tuple[str, str, str]]:
        """使用LLM在280个词典中找相似的电器"""
        # 构建词典列表供LLM参考
        appliance_list = []
        for english_name, info in self.base_appliance_dict.items():
            chinese_name = info.get("chinese_name", "")
            shiftability = info.get("shiftability", "")
            appliance_list.append(f"{english_name} ({chinese_name}) - {shiftability}")
        
        # 只取前50个避免prompt过长
        sample_appliances = appliance_list[:50]
        appliance_examples = "\n".join(sample_appliances)
        
        prompt = f"""
        I have an appliance name: "{appliance_name}"
        
        Please find the most similar appliance from this standard dictionary (280 appliances):
        {appliance_examples}
        ... (and 230 more appliances)
        
        Your task:
        1. Find the appliance in the dictionary that is most similar to "{appliance_name}"
        2. Consider language variations (English/Chinese), brands, models, synonyms
        3. Return the exact English name from the dictionary and its shiftability
        
        Return format (JSON only):
        {{"matched_appliance": "exact_english_name_from_dict", "shiftability": "shiftable/base/non-shiftable", "confidence": "high/medium/low"}}
        
        If no reasonable match found, return:
        {{"matched_appliance": "none", "shiftability": "none", "confidence": "none"}}
        """
        
        messages = [
            {"role": "system", "content": "You are an expert at matching appliance names to a standard dictionary. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = chat_with_api(messages)
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content'].strip()
                
                # 提取JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    matched_appliance = result.get("matched_appliance", "none")
                    shiftability = result.get("shiftability", "none").lower()
                    confidence = result.get("confidence", "none")
                    
                    if matched_appliance != "none" and shiftability != "none":
                        return matched_appliance, shiftability, confidence
                
        except Exception as e:
            print(f"   ⚠️ LLM相似匹配失败: {e}")
        
        return None
    
    def classify_appliance_with_hybrid_approach(self, appliance_name: str) -> Tuple[str, str]:
        """混合方法：先精确匹配，再LLM相似匹配"""
        
        # 步骤1: 精确匹配
        exact_match = self.exact_match_in_dict(appliance_name)
        if exact_match:
            matched_name, shiftability = exact_match
            print(f"   ✅ 精确匹配: {appliance_name} → {matched_name} ({shiftability})")
            return shiftability, "exact_match"
        
        # 步骤2: LLM相似匹配
        print(f"   🔍 未找到精确匹配，使用LLM相似匹配...")
        similarity_match = self.llm_similarity_match(appliance_name)
        if similarity_match:
            matched_name, shiftability, confidence = similarity_match
            print(f"   🤖 LLM匹配: {appliance_name} → {matched_name} ({shiftability}, {confidence})")
            return shiftability, f"llm_match_{confidence}"
        
        # 步骤3: 默认保守分类
        print(f"   ❌ 无法匹配，使用默认分类")
        return "non-shiftable", "default"
    
    def print_dataset_summary(self):
        """打印数据集摘要信息"""
        if not self.test_appliances:
            return
            
        # 统计分布
        shiftable_count = sum(1 for a in self.test_appliances if a["expected"] == "shiftable")
        base_count = sum(1 for a in self.test_appliances if a["expected"] == "base")
        non_shiftable_count = sum(1 for a in self.test_appliances if a["expected"] == "non-shiftable")
        
        generated_count = sum(1 for a in self.test_appliances if a["variant_type"] == "generated")
        distractor_count = sum(1 for a in self.test_appliances if a["variant_type"] == "distractor")
        
        print(f"📊 扩充测试集分布:")
        print(f"   - Shiftable: {shiftable_count} 个")
        print(f"   - Base: {base_count} 个") 
        print(f"   - Non-shiftable: {non_shiftable_count} 个")
        print(f"   - 生成变体: {generated_count} 个")
        print(f"   - 干扰项: {distractor_count} 个")

def test_hybrid_appliance_classification():
    """测试混合方法电器分类性能"""
    print("🤖 测试混合方法电器分类性能...")
    
    experiment = ApplianceClassificationExperiment()
    if not experiment.test_appliances:
        print("❌ 没有可测试的电器数据")
        return None
    
    # 测试前250个样本
    test_subset = experiment.test_appliances[:250]
    print(f"📝 测试前 {len(test_subset)} 个电器样本")
    
    results = {
        "experiment_info": {
            "description": "Hybrid appliance classification: exact match + LLM dictionary matching + LLM subjective judgment",
            "ground_truth_source": "extended_appliance_test_dataset.json",
            "base_dictionary": "appliance_shiftability_dict.json (280 appliances)",
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "classification_results": [], 
        "performance_summary": {}
    }
    
    correct_count = 0
    method_stats = {
        "exact_match": 0, 
        "llm_dict_match_high": 0, 
        "llm_dict_match_medium": 0, 
        "llm_dict_match_low": 0, 
        "llm_subjective": 0
    }
    
    for i, appliance in enumerate(test_subset):
        print(f"\n🔄 分类进度: {i+1}/{len(test_subset)} - {appliance['name']}")
        
        # 混合方法预测
        predicted, method = experiment.classify_appliance_with_hybrid_approach(appliance['name'])
        # Ground Truth
        expected = appliance['expected']
        is_correct = (predicted == expected)
        
        if is_correct:
            correct_count += 1
        
        # 统计方法使用情况
        method_stats[method] = method_stats.get(method, 0) + 1
        
        result = {
            "appliance_name": appliance['name'],
            "predicted_shiftability": predicted,
            "ground_truth": expected,
            "correct": is_correct,
            "classification_method": method,
            "base_english": appliance['base_english'],
            "variant_type": appliance['variant_type']
        }
        
        # 显示实时结果
        status = "✅" if is_correct else "❌"
        print(f"   {status} 预测: {predicted} | 真实: {expected} | 方法: {method}")
        
        results["classification_results"].append(result)
        
        # 添加延迟避免API限制
        if method.startswith("llm"):
            time.sleep(1.0)
    
    # 计算性能指标
    accuracy = (correct_count / len(test_subset)) * 100
    
    # 按方法分析准确率
    method_accuracy = {}
    for method in method_stats.keys():
        method_results = [r for r in results["classification_results"] if r["classification_method"] == method]
        if method_results:
            method_correct = sum(1 for r in method_results if r["correct"])
            method_accuracy[method] = round((method_correct / len(method_results)) * 100, 1)
        else:
            method_accuracy[method] = 0.0
    
    results["performance_summary"] = {
        "total_tested": len(test_subset),
        "correct_classifications": correct_count,
        "overall_accuracy": round(accuracy, 1),
        "method_statistics": method_stats,
        "method_accuracy": method_accuracy
    }
    
    # 保存结果
    output_file = "experiments/hybrid_classification_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 混合方法电器分类测试完成")
    print(f"📊 总体准确率: {accuracy:.1f}% ({correct_count}/{len(test_subset)})")
    print(f"📊 方法使用统计:")
    for method, count in method_stats.items():
        acc = method_accuracy.get(method, 0)
        print(f"   - {method}: {count} 次 (准确率: {acc}%)")
    print(f"📁 详细结果: {output_file}")
    
    return results

if __name__ == "__main__":
    test_hybrid_appliance_classification()
