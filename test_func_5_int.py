
import os
import json
import pandas as pd

from tools.p_042_user_constraints import revise_constraints_by_llm, generate_default_constraints
from tools.p_043_filter_shiftable_events import process_and_mask_events 

# 路径常量
EVENT_PATH = "./output/02_event_segments/02_appliance_event_segments_id.csv"
CONSTRAINT_PATH = "./output/04_user_constraints/appliance_constraints_revise_by_llm.json"
INTERMEDIATE_PATH = "./output/04_user_constraints/shiftable_event_filtered_by_duration.csv"
DEFAULT_CONSTRAINT_GEN_PATH = "./config/appliance_constraints.json" 

def print_event_statistics(df, title="统计结果"):
    total = len(df)
    true_count = df["is_reschedulable"].sum()
    false_count = total - true_count
    summary = {
        "total": total,
        "reschedulable_true": int(true_count),
        "reschedulable_false": int(false_count),
        "by_appliance": df.groupby("appliance_name")["is_reschedulable"]
                                .value_counts().unstack(fill_value=0).to_dict()
    }
    print(f"\n📊 {title}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary

def time_to_minutes(t):
    # 假设时间格式始终是 HH:MM
    h, m = map(int, t.split(":"))
    return h * 60 + m

def minutes_to_time(m):
    h = m // 60
    m = m % 60
    return f"{h:02}:{m:02}"

def merge_intervals(intervals):
    if not intervals:
        return []
    
    # 将时间转换为分钟，便于排序和合并
    converted_intervals = []
    for start_str, end_str in intervals:
        start_min = time_to_minutes(start_str)
        end_min = time_to_minutes(end_str)
        
        # 考虑到可能已经有 24:00 的表示，统一处理到 0-1440 范围内
        if end_str == "24:00":
            end_min = 24 * 60
        
        if end_min < start_min: # 这是一个跨天的区间，将其调整到连续的时间轴上
            end_min += 24 * 60 # 加上一天的分钟数
        converted_intervals.append([start_min, end_min])

    sorted_intervals = sorted(converted_intervals)
    
    merged = []
    for start, end in sorted_intervals:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end) # 合并重叠区间

    # 将合并后的分钟时间转换回 HH:MM 格式
    result = []
    for s_min, e_min in merged:
        # 如果是 24:00，则保持 24:00
        converted_start = minutes_to_time(s_min % (24*60))
        converted_end = "24:00" if e_min == 24 * 60 else minutes_to_time(e_min % (24*60))
        result.append([converted_start, converted_end])
    return result

def step1_generate_default_constraints_wrapper():
    # 确保默认约束文件存在，如果不存在则生成
    if not os.path.exists(DEFAULT_CONSTRAINT_GEN_PATH):
        generate_default_constraints()
    else:
        print("✅ Default constraint file already exists or has been manually maintained.")
        # print("✅ 默认约束文件已存在或手动维护。")

def step2_revise_constraints_by_instruction(user_instruction: str):
    print("🧠 Invoking LLM to parse constraints...")
    # print("🧠 调用 LLM 解析约束...")
    success = revise_constraints_by_llm(user_instruction)

    if success:
        with open(CONSTRAINT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 再次处理合并重叠区间，以防 LLM 输出或 normalize_constraint_time_fields 后仍有重叠
        for appliance, cons in data.items():
            if "forbidden_time" in cons:
                # 再次执行 merge_intervals，以确保 24:00 的正确性
                cons["forbidden_time"] = merge_intervals(cons["forbidden_time"])

        with open(CONSTRAINT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Revised constraints have been saved to: {CONSTRAINT_PATH}")
        # print(f"✅ 已将修订后的约束保存至: {CONSTRAINT_PATH}")
    else:
        print("❌ Failed to revise constraints via LLM.")
        # print("❌ LLM 修订约束失败。")

def step3_filter_by_min_duration():
    full_df = pd.read_csv(EVENT_PATH, parse_dates=["start_time", "end_time"])
    shiftable_df = full_df[full_df["Shiftability"] == "Shiftable"].copy()
    shiftable_df["is_reschedulable"] = shiftable_df["is_reschedulable"].astype(bool)

    with open(CONSTRAINT_PATH, "r", encoding="utf-8") as f:
        constraint_dict = json.load(f)

    for idx, row in shiftable_df.iterrows():
        aid = row["appliance_name"]
        # 使用 .get() 确保键不存在时返回默认值 0
        min_dur = constraint_dict.get(aid, {}).get("min_duration", 0) 
        if row["duration(min)"] <= min_dur:
            shiftable_df.at[idx, "is_reschedulable"] = False

    shiftable_df.to_csv(INTERMEDIATE_PATH, index=False)
    print_event_statistics(shiftable_df, "After Step 3: Filtered by min_duration")
    # print_event_statistics(shiftable_df, "Step 3 后：min_duration 筛选后")

def step4_apply_tariff_masks():
    for tariff in ["Economy_7", "Economy_10"]:
        # process_and_mask_events 负责读取 intermediate_path，应用约束并输出到最终路径
        final_path = process_and_mask_events(
            event_csv_path=INTERMEDIATE_PATH,
            constraint_json_path=CONSTRAINT_PATH,
            tariff_name=tariff
        )
        df_tariff = pd.read_csv(final_path)
        print_event_statistics(df_tariff, f"After Step 4: Filtered under {tariff} tariff")
        # print_event_statistics(df_tariff, f"Step 4 后：{tariff} 电价下筛选后")

def filter_events_by_constraints_and_tariff(user_instruction: str = None):
    """
    对外主函数：执行完整约束分析与事件筛选流程
    """
    if user_instruction is None:
        user_instruction = (
            "For Washing Machine, Tumble Dryer, and Dishwasher:\n"
            "- Replace the default forbidden operating time with 23:30 to 06:00 (next day);\n"
            "- Set latest_finish to 14:00 of the next day (i.e., 38:00);\n"
            "- Ignore all events shorter than 5 minutes.\n"
            "Keep all other appliances with default scheduling rules."
        )

    step1_generate_default_constraints_wrapper() 
    step2_revise_constraints_by_instruction(user_instruction)
    step3_filter_by_min_duration()
    step4_apply_tariff_masks()

if __name__ == "__main__":
    filter_events_by_constraints_and_tariff()