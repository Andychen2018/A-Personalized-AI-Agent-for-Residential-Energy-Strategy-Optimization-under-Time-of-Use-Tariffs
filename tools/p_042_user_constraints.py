
import os
import sys
import json
import pandas as pd

# ✅ 添加当前目录到 sys.path，确保同目录模块都能导入
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from llm_proxy import GPTProxyClient # 假设此模块存在并可用

# ✅ 路径常量
APPLIANCE_LABEL_PATH = "./output/02_behavior_modeling/02_1_appliance_shiftable_label.csv"
DEFAULT_PATH = "./config/appliance_constraints.json"
OUTPUT_PATH = "./output/04_user_constraints/appliance_constraints_revise_by_llm.json"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# 默认规则值
default_values = {
    "forbidden_time": [["00:00", "06:30"], ["23:00", "24:00"]], # 初始默认值已使用 24:00
    "latest_finish": "24:00",
    "shift_rule": "only_delay",
    "min_duration": 5
}

def generate_default_constraints():
    df = pd.read_csv(APPLIANCE_LABEL_PATH)
    constraints = {}
    for _, row in df.iterrows():
        name = row["ApplianceName"].strip()
        constraints[name] = default_values.copy()

    os.makedirs(os.path.dirname(DEFAULT_PATH), exist_ok=True)
    with open(DEFAULT_PATH, "w", encoding="utf-8") as f:
        json.dump(constraints, f, indent=2, ensure_ascii=False)
    print(f"✅ Default appliance scheduling constraints have been saved to: {DEFAULT_PATH}")
    # print(f"✅ 默认电器调度约束已保存至: {DEFAULT_PATH}")
    return constraints

def normalize_time_string(t):
    if isinstance(t, str):
        t = t.strip().lower()
        if "of the next day" in t:
            try:
                hh_mm = t.replace("of the next day", "").strip()
                hour, minute = map(int, hh_mm.split(":"))
                return f"{hour + 24}:{minute:02d}"
            except:
                return t
    return t

def expand_cross_day_time_range(start, end):
    # 这里我们修正逻辑，确保 00:00 作为结束时，如果实际是“第二天开始”，能转成 24:00
    # 首先，处理 00:00 的特殊情况，如果它代表的是当天的结束而非第二天的开始，那么就是 24:00
    if end == "00:00" and start != "00:00": # 避免 00:00-00:00 的情况
        # 进一步判断，如果 start > end (代表跨天)，且 end 是 00:00，则将其视为 24:00
        # 转换为分钟来判断
        def to_minutes(tstr):
            h, m = map(int, tstr.split(":"))
            return h * 60 + m
        
        start_min = to_minutes(start)
        end_min_raw = to_minutes(end)

        if start_min >= end_min_raw: # 这是一个跨天的区间
            # 如果结束时间是 00:00，并且是跨天的，通常意味着 24:00
            # 比如 23:00 到 00:00, 这里的 00:00 实际上是 24:00
            return [[start, "24:00"]]
        else:
            # 例如 01:00 到 02:00，非跨天
            return [[start, end]]
    else:
        # 如果不是 00:00 结束的跨天情况，沿用原有逻辑
        def to_minutes(tstr):
            h, m = map(int, tstr.split(":"))
            return h * 60 + m

        s_min = to_minutes(start)
        e_min = to_minutes(end)
        
        if s_min >= e_min: # 如果结束时间小于或等于开始时间，则认为是跨天
            # 分割成两个区间：从开始到24:00，以及从00:00到（24+结束时间）
            # 注意：这里的 end_hour, end_min 是原始的，用于计算第二天的时间点
            end_hour, end_min = map(int, end.split(":"))
            return [[start, "24:00"], ["00:00", f"{24 + end_hour}:{end_min:02d}"]]
        else:
            return [[start, end]]

def normalize_constraint_time_fields(constraint_dict):
    for aid, rule in constraint_dict.items():
        if "latest_finish" in rule:
            rule["latest_finish"] = normalize_time_string(rule["latest_finish"])
        if "forbidden_time" in rule:
            new_ranges = []
            # 在这里，我们先对每个区间应用 expand_cross_day_time_range
            # 然后再进行一个后处理，将 '00:00' 且是区间结束的，变为 '24:00'
            for start, end in rule["forbidden_time"]:
                expanded = expand_cross_day_time_range(start, end)
                new_ranges.extend(expanded)
            
            # 后处理：将形如 ['X:XX', '00:00'] 的区间转换为 ['X:XX', '24:00']
            processed_ranges = []
            for start, end in new_ranges:
                if end == "00:00" and start != "00:00": # 确保不是 00:00-00:00 的空区间
                    processed_ranges.append([start, "24:00"])
                else:
                    processed_ranges.append([start, end])
            
            rule["forbidden_time"] = processed_ranges

        for field in ["allowed", "migratable"]:
            if field in rule and isinstance(rule[field], list):
                rule[field] = [
                    [normalize_time_string(s), normalize_time_string(e)]
                    for s, e in rule[field]
                ]

def revise_constraints_by_llm(user_instruction: str):
    client = GPTProxyClient()

    with open(DEFAULT_PATH, "r", encoding="utf-8") as f:
        default_dict = json.load(f)

    example_output = {
        "Washing Machine": {
            "forbidden_time": [["0:00", "6:00"],["23:30", "24:00"]], # 明确展示分割后的跨天表示
            "latest_finish": "38:00",
            "shift_rule": "only_delay",
            "min_duration": 8
        },
        "Tumble Dryer": {
            "forbidden_time": [["0:00", "6:00"],["23:30", "24:00"]],
            "latest_finish": "38:00",
            "shift_rule": "only_delay",
            "min_duration": 8
        },
        "Dishwasher": {
            "forbidden_time": [["0:00", "6:00"],["23:00", "24:00"]],
            "latest_finish": "38:00",
            "shift_rule": "only_delay",
            "min_duration": 8
        }
    }
    
    prompt = f"""
You are a smart assistant helping to revise electricity scheduling constraints.
You will receive:
- `user_instruction`: Natural language describing desired changes.
- `original_constraints`: A JSON dictionary of appliance scheduling rules.

Your job:
1. ONLY modify the appliances mentioned in the user's instruction;
2. If the user does NOT mention a field (e.g., forbidden_time), KEEP its default;
3. **If user explicitly mentions forbidden_time (e.g., "do not run between 23:30 and 06:00 the next day"), you should RETURN A NEW 'forbidden' FIELD with these ranges. This 'forbidden' field will REPLACE any existing 'forbidden_time' for that appliance. Convert time ranges to standard 24-hour format with 0:00-based ranges, splitting cross-day intervals where 00:00 represents the start of a new day, but 24:00 represents the end of the current day (e.g., "23:30 to 06:00 next day" becomes [['23:30','24:00'], ['00:00','06:00']]). If a forbidden time ends at midnight of the current day, use '24:00' (e.g., '23:00 to 00:00' becomes ['23:00', '24:00']);**
4. If the user's instruction implies a latest_finish constraint (e.g., "finish by 2pm the next day"), convert it to 24+ format (e.g., 38:00);
5. If the user's instruction refers to a minimum runtime (e.g., "events shorter than 8 minutes should be ignored"), use that value to update min_duration per appliance;
6. shift_rule should remain "only_delay" by default.

Output MUST be a valid JSON covering all appliances. Do not include any other text or markdown.

Example expected_output (partial):
{json.dumps(example_output, indent=2, ensure_ascii=False)}

original_constraints:
{json.dumps(default_dict, indent=2, ensure_ascii=False)}

user_instruction:
{user_instruction}
"""

    print("🧠 Calling LLM to revise constraints...")

    try:
        response = client.chat([{"role": "user", "content": prompt}])
        if not response["success"]:
            raise ValueError(response["error"])

        content = response["content"].strip().strip("```json").strip("```")
        revised_constraints = json.loads(content)

        # 补全未提及设备或字段
        for aid in default_dict:
            if aid not in revised_constraints:
                revised_constraints[aid] = default_dict[aid]
            else:
                for k in default_values:
                    # 如果LLM返回了某个字段，则使用LLM的值；否则保留默认值
                    if k not in revised_constraints[aid]:
                        revised_constraints[aid][k] = default_dict[aid][k]
                    # 特别处理 'forbidden' 字段，如果LLM返回了它，则用它替换 'forbidden_time'
                    if k == "forbidden_time" and "forbidden" in revised_constraints[aid]:
                         # LLM返回了'forbidden'，意味着用户有覆盖意图，替换默认的'forbidden_time'
                        revised_constraints[aid]["forbidden_time"] = revised_constraints[aid]["forbidden"]
                        del revised_constraints[aid]["forbidden"] # 删除临时字段

        normalize_constraint_time_fields(revised_constraints) # 再次确保所有时间字段格式正确

        

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(revised_constraints, f, indent=2, ensure_ascii=False)


        print(f"✅ Constraints revised based on user input and saved to: {OUTPUT_PATH}")
        # print(f"✅ 已根据用户输入修改约束，保存至: {OUTPUT_PATH}")
        # 找出实际被修改的设备，进行更精确的报告
        modified_appliances = []
        for aid, new_rule in revised_constraints.items():
            old_rule = default_dict.get(aid, {})
            # 简单比较，如果字典内容不同则认为被修改
            if json.dumps(new_rule, sort_keys=True) != json.dumps(old_rule, sort_keys=True):
                modified_appliances.append(aid)
        print(f"🔍 Appliances modified in this revision: {modified_appliances if modified_appliances else 'None'}")
        # print(f"🔍 本次修改设备: {modified_appliances if modified_appliances else '无修改'}")
        return True

    except Exception as e:
        print(f"❌ Failed to revise constraints via LLM: {e}")
        # print(f"❌ LLM约束修改失败: {e}")
        return False