01_generate_test_data.py和生成500个用户的自然语言约束。
    "experiments/user_appliance_constraint_samples.json"

02_llm_appliance_classification.py生成500个电器的属性，包括用户用别的名字，别的写法
    "experiments/user_appliance_constraint_samples.json"
    并且作为LLM集成方法对电器的名称进行发分类 ，🔍 先查词典精确匹配 🤖 再LLM语义匹配词典 💭 最后LLM内置知识兜底
    "experiments/llm_appliance_classification_results.json"
    总体准确率: 90.4% (226/250)
📊 方法使用统计:
   - exact_match: 48 次 (准确率: 100.0%)
   - llm_dict_match_high: 0 次 (准确率: 0.0%)
   - llm_dict_match_medium: 0 次 (准确率: 0.0%)
   - llm_dict_match_low: 0 次 (准确率: 0.0%)
   - llm_subjective: 0 次 (准确率: 0.0%)
   - llm_match_low: 17 次 (准确率: 88.2%)
   - llm_match_medium: 75 次 (准确率: 86.7%)
   - llm_match_high: 75 次 (准确率: 92.0%)
   - default: 35 次 (准确率: 82.9%)
  


03_llm_constraint_parsing.py解析500个用户的自然语言约束。
    🤖 LLM语义理解：解析自然语言约束的含义
    📊 复杂度分析：按simple/moderate/complex三个级别评估性能
    📝 结构化提取：从自然语言中提取时间段、电器名称、约束类型等结构化信息
     结果在experiments/llm_constraint_parsing_detailed_analysis.json
     结果为87.4% 简单的96.5 200个  中等的97.2 200个  49.6难的100个，按数据量给权重 0.2 0.2 01 平均后为87.4

04_fixed_thresholds_methods.py代码作为固定的阈值和关键词等方法实现电器分类和约束解析

    结果 experiments/fixed_thresholds_appliance_results.json
        experiments/fixed_thresholds_constraint_results.json
