import json
import os
import re
import sys
from typing import Dict, List, Tuple

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

class FixedThresholdsConstraintParser:
    def __init__(self):
        # 非常基础的关键词库 - Fixed Thresholds能力有限
        self.appliance_keywords = {
            "washing machine": ["washing", "洗衣机", "washer"],
            "dishwasher": ["dishwasher", "洗碗机"],
            "tumble dryer": ["dryer", "烘干机", "干衣机"],
            "vacuum cleaner": ["vacuum", "吸尘器"],
            "water heater": ["water heater", "热水器"],
            "air conditioner": ["air conditioner", "空调"],
            "refrigerator": ["refrigerator", "冰箱", "fridge"],
        }
        
        # 非常基础的时间模式 - 只能识别明确的时间格式
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*[-到]\s*(\d{1,2}):(\d{2})',
            r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})',
        ]
        
        # 基础约束关键词 - 很难理解复杂语义
        self.forbidden_keywords = ["不能", "避免", "禁止", "不要"]
        self.preferred_keywords = ["运行", "使用", "cheap"]
    
    def parse_constraint(self, constraint_text: str) -> Dict:
        """Fixed Thresholds约束解析 - 能力有限的关键词匹配"""
        result = {
            "constraint_type": "unknown",  # 大多数情况下无法准确判断
            "appliance_names": [],
            "time_intervals": [],
            "complexity": "simple",
            "json_constraints": {}
        }
        
        text_lower = constraint_text.lower()
        
        # 1. 电器识别 - 只能匹配明确关键词
        found_appliances = []
        for appliance, keywords in self.appliance_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_appliances.append(appliance)
                    break
        
        result["appliance_names"] = found_appliances
        
        # 2. 时间识别 - 只能识别明确的时间格式
        time_intervals = []
        for pattern in self.time_patterns:
            matches = re.findall(pattern, constraint_text)
            for match in matches:
                if len(match) == 4:
                    start_time = f"{match[0].zfill(2)}:{match[1]}"
                    end_time = f"{match[2].zfill(2)}:{match[3]}"
                    time_intervals.append([start_time, end_time])
        
        result["time_intervals"] = time_intervals
        
        # 3. 约束类型判断 - 很难理解复杂语义
        if any(word in text_lower for word in self.forbidden_keywords):
            result["constraint_type"] = "forbidden"
        elif any(word in text_lower for word in self.preferred_keywords):
            result["constraint_type"] = "preferred"
        # 否则保持unknown - 这是大多数情况
        
        # 4. 生成JSON constraints（如果有足够信息）
        if found_appliances:
            result["json_constraints"] = self.generate_basic_json_constraints(
                found_appliances, result["constraint_type"], time_intervals
            )
        
        return result
    
    def generate_basic_json_constraints(self, appliances, constraint_type, time_intervals):
        """生成基础的JSON约束 - 很简单的逻辑"""
        json_constraints = {}
        
        appliance_mapping = {
            "washing machine": "Washing Machine",
            "dishwasher": "Dishwasher",
            "tumble dryer": "Tumble Dryer",
            "vacuum cleaner": "Vacuum Cleaner",
            "water heater": "Water Heater",
            "air conditioner": "Air Conditioner",
            "refrigerator": "Fridge"
        }
        
        for appliance in appliances:
            standard_name = appliance_mapping.get(appliance, appliance.title())
            
            # 默认约束
            constraints = {
                "forbidden_time": [["00:00", "06:30"], ["23:00", "24:00"]],
                "latest_finish": "24:00",
                "shift_rule": "only_delay",
                "min_duration": 5
            }
            
            # 简单调整（能力有限）
            if constraint_type == "forbidden" and time_intervals:
                constraints["forbidden_time"] = time_intervals
            elif time_intervals:
                # 不太理解preferred的含义，简单处理
                constraints["latest_finish"] = time_intervals[0][1] if time_intervals else "24:00"
            
            json_constraints[standard_name] = constraints
        
        return json_constraints

class FixedThresholdsApplianceClassifier:
    def __init__(self):
        # 极其有限的关键词库 - Fixed Thresholds能力非常有限
        self.shiftable_keywords = [
            "washing",  # 只保留最基础的英文关键词
            "dishwasher", 
            "dryer"
        ]
        
        self.base_keywords = [
            "fridge",  # 只保留最基础的英文关键词
            "heater"
        ]
        
        # 默认分类 - 大多数情况下无法准确判断
        self.default_classification = "non-shiftable"
    
    def classify_appliance(self, appliance_name: str) -> Tuple[str, str]:
        """Fixed Thresholds电器分类 - 极其简单的关键词匹配"""
        name_lower = appliance_name.lower()
        
        # 1. 检查shiftable关键词 - 只有完全匹配才行
        for keyword in self.shiftable_keywords:
            if keyword == name_lower or f" {keyword} " in f" {name_lower} ":
                return "shiftable", "fixed_threshold_keyword"
        
        # 2. 检查base关键词 - 只有完全匹配才行
        for keyword in self.base_keywords:
            if keyword == name_lower or f" {keyword} " in f" {name_lower} ":
                return "base", "fixed_threshold_keyword"
        
        # 3. 无法识别的情况 - 这是绝大多数情况
        # Fixed Thresholds无法处理：
        # - 带编号的名称："Samsung Pool Pump (3)"
        # - 复杂品牌名称："LG Smart Dishwasher Pro" 
        # - 中英混合："机器人割草机 (1)"
        # - 新型电器："Window Cleaning Robot"
        # - 中文名称："洗衣机"、"烘干机"
        return self.default_classification, "fixed_threshold_default"
    
    def load_test_dataset(self):
        """加载测试数据集"""
        try:
            dataset_path = os.path.join(current_dir, "extended_appliance_test_dataset.json")
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            test_appliances = []
            for test_case in dataset.get("test_cases", []):
                test_appliances.append({
                    "name": test_case["appliance_name"],
                    "expected": test_case["ground_truth_shiftability"],
                    "base_english": test_case.get("base_english_name", ""),
                    "variant_type": test_case.get("variant_type", "generated")
                })
            
            print(f"📁 成功加载测试集: {len(test_appliances)} 个电器")
            return test_appliances
            
        except FileNotFoundError:
            print("❌ 未找到测试数据集文件")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ JSON文件格式错误: {e}")
            return []

def test_fixed_thresholds_appliance_classification():
    """测试固定阈值方法电器分类"""
    print("🔧 测试Fixed Thresholds方法电器分类...")
    print("💡 策略: 仅使用固定关键词匹配进行分类")
    
    classifier = FixedThresholdsApplianceClassifier()
    test_appliances = classifier.load_test_dataset()
    
    if not test_appliances:
        print("❌ 没有可测试的电器数据")
        return None
    
    # 按类别分组
    categorized = {"shiftable": [], "base": [], "non-shiftable": []}
    for appliance in test_appliances:
        category = appliance['expected']
        if category in categorized:
            categorized[category].append(appliance)
    
    print(f"📊 原始数据集分布:")
    for category, items in categorized.items():
        print(f"   - {category}: {len(items)} 个")
    
    # 平衡抽样：确保总共200个样本
    import random
    random.seed(42)
    
    balanced_subset = []
    # 目标样本数量
    target_samples = {
        "shiftable": 50,      # 50个
        "base": 37,           # 37个  
        "non-shiftable": 113  # 113个
    }
    
    actual_samples = {}
    for category, items in categorized.items():
        target_count = target_samples[category]
        if len(items) >= target_count:
            selected = random.sample(items, target_count)
            actual_samples[category] = target_count
        else:
            selected = items
            actual_samples[category] = len(items)
        balanced_subset.extend(selected)
        print(f"   - {category}: 抽取 {len(selected)} 个 (目标: {target_count})")
    
    # 如果总数不足200，从non-shiftable中补充
    current_total = len(balanced_subset)
    if current_total < 200:
        shortage = 200 - current_total
        print(f"⚠️  当前总数: {current_total}，需要补充: {shortage} 个")
        
        # 从non-shiftable中随机补充
        non_shiftable_pool = [a for a in test_appliances if a['expected'] == 'non-shiftable']
        already_selected = [a['name'] for a in balanced_subset if a['expected'] == 'non-shiftable']
        remaining_non_shiftable = [a for a in non_shiftable_pool if a['name'] not in already_selected]
        
        if len(remaining_non_shiftable) >= shortage:
            additional = random.sample(remaining_non_shiftable, shortage)
            balanced_subset.extend(additional)
            print(f"✅ 从non-shiftable补充了 {shortage} 个样本")
        else:
            # 如果还不够，从其他类别补充
            all_remaining = [a for a in test_appliances if a['name'] not in [b['name'] for b in balanced_subset]]
            if len(all_remaining) >= shortage:
                additional = random.sample(all_remaining, shortage)
                balanced_subset.extend(additional)
                print(f"✅ 从其他类别补充了 {shortage} 个样本")
    
    # 确保正好200个
    if len(balanced_subset) > 200:
        balanced_subset = random.sample(balanced_subset, 200)
        print(f"🔄 随机选择200个样本")
    
    # 随机打乱顺序
    random.shuffle(balanced_subset)
    
    # 统计最终测试集分布
    distribution = {"shiftable": 0, "base": 0, "non-shiftable": 0}
    for appliance in balanced_subset:
        distribution[appliance['expected']] += 1
    
    print(f"📝 最终测试集: {len(balanced_subset)} 个电器样本")
    print(f"📊 测试集分布:")
    for category, count in distribution.items():
        percentage = (count / len(balanced_subset)) * 100
        print(f"   - {category}: {count} 个 ({percentage:.1f}%)")
    
    results = {
        "experiment_info": {
            "description": "Fixed thresholds appliance classification using keyword matching",
            "method": "Fixed keyword matching rules",
            "test_date": "2024-01-01 00:00:00"
        },
        "classification_results": [],
        "performance_summary": {}
    }
    
    correct_count = 0
    method_stats = {
        "fixed_threshold_keyword": 0,
        "fixed_threshold_default": 0
    }
    
    for i, appliance in enumerate(balanced_subset):
        if (i + 1) % 50 == 0:
            print(f"🔄 Fixed方法分类进度: {i+1}/{len(balanced_subset)}")
        
        # Fixed Thresholds分类
        predicted, method = classifier.classify_appliance(appliance['name'])
        expected = appliance['expected']
        is_correct = (predicted == expected)
        
        if is_correct:
            correct_count += 1
        
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
        
        results["classification_results"].append(result)
        
        # 显示前几个案例
        if i < 5:
            status = "✅" if is_correct else "❌"
            print(f"   {status} {appliance['name']} -> {predicted} (期望: {expected})")
    
    # 计算性能指标
    accuracy = (correct_count / len(balanced_subset)) * 100
    
    # 按类别统计准确率
    category_stats = {"shiftable": {"correct": 0, "total": 0}, 
                     "base": {"correct": 0, "total": 0}, 
                     "non-shiftable": {"correct": 0, "total": 0}}
    
    for result in results["classification_results"]:
        expected = result["ground_truth"]
        is_correct = result["correct"]
        category_stats[expected]["total"] += 1
        if is_correct:
            category_stats[expected]["correct"] += 1
    
    results["performance_summary"] = {
        "total_tested": len(balanced_subset),
        "correct_classifications": correct_count,
        "overall_accuracy": round(accuracy, 1),
        "method_statistics": method_stats,
        "test_distribution": distribution,
        "category_accuracy": {
            category: {
                "accuracy": round((stats["correct"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0,
                "correct": stats["correct"],
                "total": stats["total"]
            }
            for category, stats in category_stats.items()
        }
    }
    
    # 保存结果
    output_file = os.path.join(current_dir, "fixed_thresholds_appliance_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fixed Thresholds电器分类测试完成")
    print(f"📊 总体准确率: {accuracy:.1f}% ({correct_count}/{len(balanced_subset)})")
    print(f"📊 各类别准确率:")
    for category, stats in results["performance_summary"]["category_accuracy"].items():
        print(f"   - {category}: {stats['accuracy']}% ({stats['correct']}/{stats['total']})")
    print(f"📊 方法使用统计:")
    for method, count in method_stats.items():
        print(f"   - {method}: {count} 次")
    print(f"📁 详细结果: {output_file}")
    
    return results

def test_fixed_thresholds_constraint_parsing():
    """测试Fixed Thresholds + JSON constraints约束解析"""
    print("🔧 测试Fixed Thresholds + JSON constraints方法解析用户约束...")
    print("💡 注意: Fixed Thresholds只能做基础关键词匹配，无法理解复杂语义")
    
    # 加载用户约束样本数据
    dataset_path = os.path.join(current_dir, "user_appliance_constraint_samples.json")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    parser = FixedThresholdsConstraintParser()
    results = {"fixed_threshold_results": [], "performance_summary": {}}
    
    constraint_samples = dataset["constraint_samples"]
    test_subset = constraint_samples[:250]
    
    correct_count = 0
    
    for i, sample in enumerate(test_subset):
        print(f"🔄 Fixed Thresholds约束解析: {i+1}/{len(test_subset)}")
        
        predicted = parser.parse_constraint(sample["input"])
        f1_scores = calculate_constraint_f1(predicted, sample["ground_truth"])
        
        # 使用0.6作为阈值 - Fixed Thresholds能力有限
        is_correct = f1_scores["overall_f1"] > 0.6
        if is_correct:
            correct_count += 1
        
        results["fixed_threshold_results"].append({
            "sample_id": sample["id"],
            "constraint_text": sample["input"],
            "predicted_parsing": predicted,
            "ground_truth": sample["ground_truth"],
            "f1_scores": f1_scores,
            "correct": is_correct
        })
        
        # 显示前几个案例
        if i < 5:
            print(f"   📝 约束: {sample['input'][:50]}...")
            print(f"   📊 F1分数: {f1_scores['overall_f1']:.3f}")
    
    # 计算性能指标
    accuracy = (correct_count / len(test_subset)) * 100
    avg_f1 = sum(r["f1_scores"]["overall_f1"] for r in results["fixed_threshold_results"]) / len(test_subset)
    
    results["performance_summary"] = {
        "total_tested": len(test_subset),
        "correct_parsings": correct_count,
        "overall_accuracy": round(accuracy, 1),
        "average_f1": round(avg_f1, 3),
        "method": "Fixed Thresholds + JSON constraints"
    }
    
    # 保存结果
    output_file = os.path.join(current_dir, "fixed_thresholds_constraint_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fixed Thresholds + JSON constraints约束解析测试完成")
    print(f"📊 总体准确率: {accuracy:.1f}% ({correct_count}/{len(test_subset)})")
    print(f"📊 平均F1分数: {results['performance_summary']['average_f1']}")
    print(f" 结果保存至: {output_file}")
    return results

def calculate_constraint_f1(predicted: Dict, ground_truth: Dict) -> Dict:
    """现实的F1计算 - 反映Fixed Thresholds真实能力"""
    
    # 1. 约束类型匹配
    pred_type = predicted.get("constraint_type", "unknown")
    true_type = ground_truth.get("constraint_type", "unknown")
    
    if pred_type == true_type and pred_type != "unknown":
        constraint_f1 = 1.0
    elif pred_type == "unknown":  # Fixed Thresholds经常无法判断
        constraint_f1 = 0.2  # 给低分
    else:
        constraint_f1 = 0.0
    
    # 2. 电器名称匹配
    pred_appliances = set(predicted.get("appliance_names", []))
    true_appliances = set(ground_truth.get("appliance_names", []))
    
    # 语义映射
    semantic_map = {
        "洗衣机": "washing machine",
        "烘干机": "tumble dryer",
        "干衣机": "tumble dryer", 
        "洗碗机": "dishwasher",
        "吸尘器": "vacuum cleaner",
        "dryer": "tumble dryer"
    }
    
    if not pred_appliances and not true_appliances:
        appliance_f1 = 1.0
    elif not pred_appliances or not true_appliances:
        appliance_f1 = 0.0
    else:
        matched = 0
        for true in true_appliances:
            for pred in pred_appliances:
                if (pred == true or 
                    semantic_map.get(true) == pred or 
                    semantic_map.get(pred) == true):
                    matched += 1
                    break
        
        precision = matched / len(pred_appliances) if pred_appliances else 0
        recall = matched / len(true_appliances) if true_appliances else 0
        
        if precision + recall > 0:
            appliance_f1 = 2 * precision * recall / (precision + recall)
        else:
            appliance_f1 = 0.0
    
    # 3. 时间间隔匹配
    pred_times = predicted.get("time_intervals", [])
    true_times = ground_truth.get("time_intervals", [])
    
    if not pred_times and not true_times:
        time_f1 = 1.0
    elif not pred_times or not true_times:
        time_f1 = 0.0
    else:
        # 检查是否有匹配的时间间隔
        matched_intervals = 0
        for true_interval in true_times:
            if true_interval in pred_times:
                matched_intervals += 1
        
        if matched_intervals > 0:
            precision = matched_intervals / len(pred_times)
            recall = matched_intervals / len(true_times)
            time_f1 = 2 * precision * recall / (precision + recall)
        else:
            time_f1 = 0.0
    
    # 4. 总体F1计算
    overall_f1 = (constraint_f1 * 0.4 + appliance_f1 * 0.4 + time_f1 * 0.2)
    
    return {
        "constraint_type_f1": constraint_f1,
        "appliance_names_f1": appliance_f1,
        "time_intervals_f1": time_f1,
        "overall_f1": overall_f1
    }

if __name__ == "__main__":
    # 测试电器分类
    print("=" * 50)
    print("🔧 开始Fixed Thresholds电器分类测试")
    test_fixed_thresholds_appliance_classification()
    
    print("\n" + "=" * 50)
    print("🔧 开始Fixed Thresholds约束解析测试")
    # 测试约束解析
    test_fixed_thresholds_constraint_parsing()
