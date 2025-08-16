import json
import os
import sys
import re
import time
import random
from typing import Dict, List, Tuple, Any
from collections import defaultdict

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 导入项目中的LLM函数
from llm import chat_with_api

class ConstraintParsingExperiment:
    def __init__(self):
        print("🧪 约束解析语义准确率实验初始化...")
        print("🤖 使用项目LLM: chat_with_api")
        print("📊 目标: 生成500个多样化自然语言约束表达")
        
    def generate_500_diverse_constraints(self) -> List[Dict]:
        """生成500个多样化的自然语言约束表达"""
        constraints = []
        
        # 1. 简单时间约束 (Simple Temporal) - 200个
        simple_constraints = self._generate_simple_temporal_constraints(200)
        constraints.extend(simple_constraints)
        
        # 2. 中等复杂度约束 (Moderate Complexity) - 200个  
        moderate_constraints = self._generate_moderate_complexity_constraints(200)
        constraints.extend(moderate_constraints)
        
        # 3. 复杂多电器协调约束 (Complex Multi-appliance) - 100个
        complex_constraints = self._generate_complex_coordination_constraints(100)
        constraints.extend(complex_constraints)
        
        # 打乱顺序
        random.shuffle(constraints)
        
        return constraints[:500]
    
    def _generate_simple_temporal_constraints(self, count: int) -> List[Dict]:
       
        constraints = []
        
        # 基础模板
        templates = [
            # 英文模板
            "Run {appliance} during {time_start}-{time_end}",
            "{appliance} should not operate between {time_start} and {time_end}",
            "{appliance} must finish by {time}",
            "Avoid using {appliance} from {time_start} to {time_end}",
            "{appliance} only during off-peak hours {time_start}-{time_end}",
            "Schedule {appliance} between {time_start} and {time_end}",
            "{appliance} forbidden during {time_start}-{time_end}",
            "Use {appliance} in cheap electricity period {time_start}-{time_end}",
            
            # 中文模板
            "{appliance}在{time_start}到{time_end}运行",
            "{appliance}不能在{time_start}-{time_end}工作",
            "{appliance}必须在{time}前完成",
            "避免在{time_start}到{time_end}使用{appliance}",
            "{appliance}只在便宜时段{time_start}-{time_end}运行",
            "{appliance}安排在{time_start}和{time_end}之间",
            "{appliance}在{time_start}-{time_end}禁止运行",
            "在经济电价时段{time_start}-{time_end}使用{appliance}",
        ]
        
        appliances = [
            "washing machine", "dishwasher", "tumble dryer", "dryer", 
            "洗衣机", "洗碗机", "烘干机", "干衣机"
        ]
        
        time_slots = [
            ("23:00", "06:00"), ("01:00", "07:00"), ("22:30", "07:30"),
            ("00:00", "08:00"), ("23:30", "06:30"), ("02:00", "08:00")
        ]
        
        deadlines = ["14:00", "16:00", "18:00", "20:00", "22:00"]
        
        for i in range(count):
            template = random.choice(templates)
            appliance = random.choice(appliances)
            
            if "{time}" in template and not "{time_start}" in template:
                # 截止时间约束
                deadline = random.choice(deadlines)
                constraint_text = template.format(appliance=appliance, time=deadline)
                
                ground_truth = {
                    "constraint_type": "deadline",
                    "appliance_names": [appliance],
                    "time_intervals": [deadline],
                    "complexity": "simple"
                }
            else:
                # 时间段约束
                start_time, end_time = random.choice(time_slots)
                constraint_text = template.format(
                    appliance=appliance, 
                    time_start=start_time, 
                    time_end=end_time
                )
                
                # 判断约束类型
                if any(word in template.lower() for word in ["not", "avoid", "forbidden", "不能", "避免", "禁止"]):
                    constraint_type = "forbidden"
                else:
                    constraint_type = "preferred"
                
                ground_truth = {
                    "constraint_type": constraint_type,
                    "appliance_names": [appliance],
                    "time_intervals": [[start_time, end_time]],
                    "complexity": "simple"
                }
            
            constraints.append({
                "id": f"simple_{i+1}",
                "input": constraint_text,
                "ground_truth": ground_truth
            })
        
        return constraints
    
    def _generate_moderate_complexity_constraints(self, count: int) -> List[Dict]:
        """生成中等复杂度约束 - 目标准确率94.2%"""
        constraints = []
        
        templates = [
            # 多时间段
            "{appliance} avoid peak hours {time1_start}-{time1_end} and {time2_start}-{time2_end}",
            "{appliance}避开高峰时段{time1_start}-{time1_end}和{time2_start}-{time2_end}",
            "Run {appliance} during {time1_start}-{time1_end} or {time2_start}-{time2_end}",
            "{appliance}在{time1_start}-{time1_end}或{time2_start}-{time2_end}运行",
            
            # 条件约束
            "{appliance} only on weekends during {time_start}-{time_end}",
            "{appliance}只在周末的{time_start}-{time_end}运行",
            "If electricity is cheap, run {appliance} between {time_start}-{time_end}",
            "如果电价便宜，{appliance}在{time_start}-{time_end}运行",
            
            # 原因约束
            "{appliance} not during {time_start}-{time_end} due to noise concerns",
            "{appliance}因为噪音问题不能在{time_start}-{time_end}运行",
            "Avoid {appliance} during dinner time {time_start}-{time_end}",
            "晚餐时间{time_start}-{time_end}避免使用{appliance}",
            
            # 季节性约束
            "In winter, {appliance} preferred during {time_start}-{time_end}",
            "冬天时{appliance}最好在{time_start}-{time_end}使用",
        ]
        
        appliances = [
            "washing machine", "dishwasher", "tumble dryer", "vacuum cleaner",
            "洗衣机", "洗碗机", "烘干机", "吸尘器"
        ]
        
        time_slots = [
            ("07:00", "09:00"), ("17:00", "20:00"), ("12:00", "14:00"),
            ("22:00", "08:00"), ("23:00", "06:00"), ("01:00", "07:00")
        ]
        
        for i in range(count):
            template = random.choice(templates)
            appliance = random.choice(appliances)
            
            if "time1_start" in template:
                # 多时间段约束
                time1 = random.choice(time_slots)
                time2 = random.choice(time_slots)
                constraint_text = template.format(
                    appliance=appliance,
                    time1_start=time1[0], time1_end=time1[1],
                    time2_start=time2[0], time2_end=time2[1]
                )
                
                if any(word in template.lower() for word in ["avoid", "避开"]):
                    constraint_type = "forbidden"
                else:
                    constraint_type = "preferred"
                
                ground_truth = {
                    "constraint_type": constraint_type,
                    "appliance_names": [appliance],
                    "time_intervals": [list(time1), list(time2)],
                    "complexity": "moderate",
                    "reasons": ["multiple_periods"]
                }
            else:
                # 单时间段但有条件/原因
                time_slot = random.choice(time_slots)
                constraint_text = template.format(
                    appliance=appliance,
                    time_start=time_slot[0],
                    time_end=time_slot[1]
                )
                
                if any(word in template.lower() for word in ["not", "avoid", "不能", "避免"]):
                    constraint_type = "forbidden"
                else:
                    constraint_type = "preferred"
                
                # 识别原因
                reasons = []
                if any(word in template.lower() for word in ["noise", "噪音"]):
                    reasons.append("noise")
                elif any(word in template.lower() for word in ["dinner", "晚餐"]):
                    reasons.append("meal_time")
                elif any(word in template.lower() for word in ["weekend", "周末"]):
                    reasons.append("schedule")
                elif any(word in template.lower() for word in ["winter", "冬天"]):
                    reasons.append("seasonal")
                
                ground_truth = {
                    "constraint_type": constraint_type,
                    "appliance_names": [appliance],
                    "time_intervals": [list(time_slot)],
                    "complexity": "moderate",
                    "reasons": reasons if reasons else ["conditional"]
                }
            
            constraints.append({
                "id": f"moderate_{i+1}",
                "input": constraint_text,
                "ground_truth": ground_truth
            })
        
        return constraints
    
    def _generate_complex_coordination_constraints(self, count: int) -> List[Dict]:
        """生成复杂多电器协调约束 - 目标准确率89.7%"""
        constraints = []
        
        templates = [
            # 依赖关系
            "{appliance1} must run before {appliance2}, both during {time_start}-{time_end}",
            "{appliance1}必须在{appliance2}之前运行，都在{time_start}-{time_end}",
            "{appliance2} can only start after {appliance1} finishes",
            "{appliance2}只能在{appliance1}完成后开始",
            
            # 多电器时间约束
            "{appliance1} and {appliance2} both avoid {time_start}-{time_end}, but {appliance3} can run anytime",
            "{appliance1}和{appliance2}都避开{time_start}-{time_end}，但{appliance3}可以随时运行",
            "Run {appliance1}, {appliance2}, and {appliance3} sequentially during cheap hours {time_start}-{time_end}",
            "在便宜时段{time_start}-{time_end}依次运行{appliance1}、{appliance2}和{appliance3}",
            
            # 冲突避免
            "{appliance1} and {appliance2} cannot run simultaneously, prefer {time_start}-{time_end}",
            "{appliance1}和{appliance2}不能同时运行，优先{time_start}-{time_end}",
            "If {appliance1} runs during {time_start}-{time_end}, then {appliance2} must wait until {deadline}",
            "如果{appliance1}在{time_start}-{time_end}运行，{appliance2}必须等到{deadline}",
            
            # 复杂条件
            "On weekdays, {appliance1} before 09:00, {appliance2} after 18:00, {appliance3} during lunch {time_start}-{time_end}",
            "工作日{appliance1}在09:00前，{appliance2}在18:00后，{appliance3}在午餐时间{time_start}-{time_end}",
        ]
        
        appliances = [
            ["washing machine", "tumble dryer", "dishwasher"],
            ["洗衣机", "烘干机", "洗碗机"],
            ["vacuum cleaner", "washing machine", "dryer"],
            ["吸尘器", "洗衣机", "干衣机"]
        ]
        
        time_slots = [
            ("23:00", "06:00"), ("01:00", "07:00"), ("12:00", "14:00"),
            ("18:00", "22:00"), ("07:00", "09:00"), ("22:00", "08:00")
        ]
        
        deadlines = ["09:00", "18:00", "14:00", "20:00"]
        
        for i in range(count):
            template = random.choice(templates)
            appliance_set = random.choice(appliances)
            
            if "{appliance3}" in template:
                # 三电器约束
                time_slot = random.choice(time_slots)
                constraint_text = template.format(
                    appliance1=appliance_set[0],
                    appliance2=appliance_set[1], 
                    appliance3=appliance_set[2],
                    time_start=time_slot[0],
                    time_end=time_slot[1]
                )
                appliance_names = appliance_set[:3]
                time_intervals = [list(time_slot)]
            elif "{appliance2}" in template:
                # 双电器约束
                time_slot = random.choice(time_slots)
                if "{deadline}" in template:
                    # 包含截止时间的模板
                    deadline = random.choice(deadlines)
                    constraint_text = template.format(
                        appliance1=appliance_set[0],
                        appliance2=appliance_set[1],
                        time_start=time_slot[0],
                        time_end=time_slot[1],
                        deadline=deadline
                    )
                    time_intervals = [list(time_slot), deadline]
                elif "before 09:00" in template or "在09:00前" in template:
                    # 固定时间的复杂模板
                    constraint_text = template.format(
                        appliance1=appliance_set[0],
                        appliance2=appliance_set[1],
                        appliance3=appliance_set[2] if len(appliance_set) > 2 else "microwave",
                        time_start=time_slot[0],
                        time_end=time_slot[1]
                    )
                    time_intervals = [["07:00", "09:00"], ["18:00", "22:00"], list(time_slot)]
                    appliance_names = appliance_set[:3] if len(appliance_set) > 2 else appliance_set[:2] + ["microwave"]
                else:
                    # 普通双电器约束
                    constraint_text = template.format(
                        appliance1=appliance_set[0],
                        appliance2=appliance_set[1],
                        time_start=time_slot[0],
                        time_end=time_slot[1]
                    )
                    time_intervals = [list(time_slot)]
                
                if "{appliance3}" not in template and "appliance_names" not in locals():
                    appliance_names = appliance_set[:2]
            else:
                # 单电器复杂约束
                time_slot = random.choice(time_slots)
                constraint_text = template.format(
                    appliance1=appliance_set[0],
                    time_start=time_slot[0],
                    time_end=time_slot[1]
                )
                appliance_names = [appliance_set[0]]
                time_intervals = [list(time_slot)]
            
            # 识别约束类型
            constraint_types = []
            if any(word in template.lower() for word in ["before", "after", "sequential", "之前", "之后", "依次"]):
                constraint_types.append("dependency")
            if any(word in template.lower() for word in ["avoid", "cannot", "不能", "避开"]):
                constraint_types.append("forbidden")
            if any(word in template.lower() for word in ["prefer", "during", "优先", "在"]):
                constraint_types.append("preferred")
            
            if not constraint_types:
                constraint_types = ["coordination"]
            
            ground_truth = {
                "constraint_type": constraint_types[0] if len(constraint_types) == 1 else "mixed",
                "appliance_names": appliance_names,
                "time_intervals": time_intervals,
                "complexity": "complex",
                "coordination_type": "multi_appliance",
                "dependency_relations": len(appliance_names) > 1
            }
            
            constraints.append({
                "id": f"complex_{i+1}",
                "input": constraint_text,
                "ground_truth": ground_truth
            })
        
        return constraints
    
    def parse_constraint_with_llm(self, constraint_text: str) -> Dict:
        """使用LLM解析单个约束"""
        prompt = f"""
    You are an expert at parsing household appliance scheduling constraints.
    Parse the following natural language constraint and extract structured information.

    IMPORTANT: Return ONLY valid JSON without any explanation or additional text.

    Extract the following information:
    1. constraint_type: "preferred", "forbidden", "deadline", "dependency", "mixed"
    2. appliance_names: list of appliance names mentioned
    3. time_intervals: list of time ranges [["start", "end"]] or deadlines ["time"]
    4. complexity: "simple", "moderate", "complex" 
    5. Additional fields if applicable:
    - reasons: list of reasons (e.g., ["noise", "cost", "schedule"])
    - coordination_type: "single", "multi_appliance" 
    - dependency_relations: true/false

    Time format: Use 24-hour format (HH:MM)
    Appliance names: Keep original language (English/Chinese)

    Constraint to parse: "{constraint_text}"

    Return JSON:
    """
        
        messages = [
            {"role": "system", "content": "You are a professional constraint parser. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = chat_with_api(messages)
            
            if response and "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"].strip()
                
                # 提取JSON
                json_content = self._extract_json_from_response(content)
                if json_content:
                    parsed_result = json.loads(json_content)
                    return self._normalize_parsed_result(parsed_result)
                else:
                    print(f"⚠️ 无法提取JSON: {content[:100]}...")
                    return {}
            else:
                print(f"⚠️ LLM响应异常")
                return {}
                
        except Exception as e:
            print(f"❌ LLM解析失败: {e}")
            return {}
    
    def _extract_json_from_response(self, content: str) -> str:
        """从LLM响应中提取JSON"""
        # 方法1: ```json```
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # 方法2: ```
        json_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # 方法3: JSON对象
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json_match.group(0).strip()
        
        # 方法4: 整个内容
        if content.strip().startswith('{') and content.strip().endswith('}'):
            return content.strip()
        
        return None
    
    def _normalize_parsed_result(self, parsed: Dict) -> Dict:
        """标准化解析结果"""
        normalized = {}
        
        # 标准化字段名
        field_mapping = {
            "constraint_type": "constraint_type",
            "appliance_names": "appliance_names", 
            "appliances": "appliance_names",
            "time_intervals": "time_intervals",
            "times": "time_intervals",
            "complexity": "complexity",
            "reasons": "reasons",
            "coordination_type": "coordination_type",
            "dependency_relations": "dependency_relations"
        }
        
        for key, value in parsed.items():
            mapped_key = field_mapping.get(key, key)
            normalized[mapped_key] = value
        
        # 确保必要字段存在
        if "constraint_type" not in normalized:
            normalized["constraint_type"] = "unknown"
        if "appliance_names" not in normalized:
            normalized["appliance_names"] = []
        if "time_intervals" not in normalized:
            normalized["time_intervals"] = []
        if "complexity" not in normalized:
            normalized["complexity"] = "simple"
            
        return normalized
    
    def calculate_f1_score(self, predicted: Dict, ground_truth: Dict) -> Dict:
        """计算F1分数"""
        scores = {}
        
        # 1. 约束类型F1
        constraint_type_score = 1.0 if predicted.get("constraint_type") == ground_truth.get("constraint_type") else 0.0
        scores["constraint_type_f1"] = constraint_type_score
        
        # 2. 电器名称F1
        pred_appliances = set(predicted.get("appliance_names", []))
        true_appliances = set(ground_truth.get("appliance_names", []))
        
        if true_appliances:
            appliance_precision = len(pred_appliances & true_appliances) / len(pred_appliances) if pred_appliances else 0
            appliance_recall = len(pred_appliances & true_appliances) / len(true_appliances)
            appliance_f1 = 2 * appliance_precision * appliance_recall / (appliance_precision + appliance_recall) if (appliance_precision + appliance_recall) > 0 else 0
        else:
            appliance_f1 = 1.0 if not pred_appliances else 0.0
        
        scores["appliance_names_f1"] = appliance_f1
        
        # 3. 时间间隔F1
        pred_times = predicted.get("time_intervals", [])
        true_times = ground_truth.get("time_intervals", [])
        
        if true_times:
            time_matches = 0
            for true_time in true_times:
                for pred_time in pred_times:
                    if self._time_intervals_match(pred_time, true_time):
                        time_matches += 1
                        break
            
            time_precision = time_matches / len(pred_times) if pred_times else 0
            time_recall = time_matches / len(true_times)
            time_f1 = 2 * time_precision * time_recall / (time_precision + time_recall) if (time_precision + time_recall) > 0 else 0
        else:
            time_f1 = 1.0 if not pred_times else 0.0
        
        scores["time_intervals_f1"] = time_f1
        
        # 4. 总体F1分数
        overall_f1 = (constraint_type_score + appliance_f1 + time_f1) / 3
        scores["overall_f1"] = overall_f1
        
        return scores
    
    def _time_intervals_match(self, pred_time, true_time) -> bool:
        """检查时间间隔是否匹配"""
        if isinstance(pred_time, list) and isinstance(true_time, list):
            if len(pred_time) == 2 and len(true_time) == 2:
                return pred_time[0] == true_time[0] and pred_time[1] == true_time[1]
        elif isinstance(pred_time, str) and isinstance(true_time, str):
            return pred_time == true_time
        return False
    
    def run_constraint_parsing_experiment(self) -> Dict:
        """运行500个约束解析实验"""
        print("🧪 开始500个多样化约束解析实验...")
        print("📊 按复杂度分类: 简单(200) + 中等(200) + 复杂(100)")
        
        # 生成500个测试用例
        test_cases = self.generate_500_diverse_constraints()
        print(f"✅ 生成了 {len(test_cases)} 个测试用例")
        
        # 按复杂度分组统计
        results_by_complexity = {
            "simple": {"scores": [], "total": 0},
            "moderate": {"scores": [], "total": 0}, 
            "complex": {"scores": [], "total": 0}
        }
        
        all_results = []
        
        for i, test_case in enumerate(test_cases):
            print(f"🔄 进度: {i+1}/500 - 测试: {test_case['input'][:60]}...")
            
            # 使用LLM解析约束
            predicted = self.parse_constraint_with_llm(test_case["input"])
            ground_truth = test_case["ground_truth"]
            
            # 计算F1分数
            f1_scores = self.calculate_f1_score(predicted, ground_truth)
            
            # 记录结果
            result = {
                "id": test_case["id"],
                "input": test_case["input"],
                "predicted": predicted,
                "ground_truth": ground_truth,
                "f1_scores": f1_scores,
                "complexity": ground_truth["complexity"]
            }
            all_results.append(result)
            
            # 按复杂度分组
            complexity = ground_truth["complexity"]
            results_by_complexity[complexity]["scores"].append(f1_scores["overall_f1"])
            results_by_complexity[complexity]["total"] += 1
            
            # 每50个测试显示进度
            if (i + 1) % 50 == 0:
                print(f"📈 已完成 {i+1}/500 测试")
            
            # 添加延迟避免API限制
            time.sleep(0.2)
        
        return {
            "all_results": all_results,
            "results_by_complexity": results_by_complexity,
            "total_cases": len(test_cases)
        }

if __name__ == "__main__":
    experiment = ConstraintParsingExperiment()
    results = experiment.run_constraint_parsing_experiment()
    
    print("\n" + "="*80)
    print("📊 约束解析语义准确率实验结果 (F1-Score)")
    print("="*80)
    
    # 按复杂度显示结果
    for complexity, data in results["results_by_complexity"].items():
        if data["scores"]:
            avg_f1 = sum(data["scores"]) / len(data["scores"]) * 100
            print(f"{complexity.capitalize()} Constraints ({data['total']} cases): {avg_f1:.1f}% F1-Score")
        else:
            print(f"{complexity.capitalize()} Constraints: No data")
    
    # 总体结果
    all_scores = []
    for complexity_data in results["results_by_complexity"].values():
        all_scores.extend(complexity_data["scores"])
    
    if all_scores:
        overall_f1 = sum(all_scores) / len(all_scores) * 100
        print(f"\nOverall Performance: {overall_f1:.1f}% F1-Score")
    
    # 保存详细结果
    output_file = "experiments/constraint_parsing_500_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    summary = {
        "experiment_info": {
            "total_cases": results["total_cases"],
            "complexity_distribution": {
                "simple": results["results_by_complexity"]["simple"]["total"],
                "moderate": results["results_by_complexity"]["moderate"]["total"], 
                "complex": results["results_by_complexity"]["complex"]["total"]
            }
        },
        "performance_by_complexity": {},
        "sample_results": results["all_results"][:20]  # 保存前20个样本
    }
    
    for complexity, data in results["results_by_complexity"].items():
        if data["scores"]:
            summary["performance_by_complexity"][complexity] = {
                "f1_score": round(sum(data["scores"]) / len(data["scores"]) * 100, 1),
                "total_cases": data["total"],
                "individual_scores": data["scores"][:10]  # 前10个分数样本
            }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 实验完成！详细结果保存在: {output_file}")
    print("🎯 目标对比:")
    print("   - 简单约束: 98.5% (目标)")
    print("   - 中等约束: 94.2% (目标)")  
    print("   - 复杂约束: 89.7% (目标)")
