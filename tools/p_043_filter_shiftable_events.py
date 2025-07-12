

import os
import json
import pandas as pd
from datetime import datetime

def time_to_minutes(tstr):
    h, m = map(int, tstr.split(":"))
    return h * 60 + m

def get_high_price_ranges(low_periods):
    """从低价区间反推出高价区间"""
    full_day = [(0, 1440)]
    low_periods_min = [(time_to_minutes(start), time_to_minutes(end)) for start, end in low_periods]
    merged = sorted(low_periods_min)

    high_periods = []
    current = 0
    for low_start, low_end in merged:
        if current < low_start:
            high_periods.append((current, low_start))
        current = max(current, low_end)
    if current < 1440:
        high_periods.append((current, 1440))
    return high_periods

def get_overlap_minutes(start, end, high_periods):
    """计算事件在高价区间的重叠时间（分钟）"""
    event_start = start.hour * 60 + start.minute
    event_end = end.hour * 60 + end.minute

    total_overlap = 0
    for high_start, high_end in high_periods:
        overlap_start = max(event_start, high_start)
        overlap_end = min(event_end, high_end)
        if overlap_start < overlap_end:
            total_overlap += overlap_end - overlap_start
    return total_overlap

def process_and_mask_events(
    event_csv_path,
    constraint_json_path,
    tariff_name="Economy_7",
    tariff_config_path="./config/tariff_config.json",
    output_dir="./output/04_user_constraints/"
):
    # 加载事件数据（字段需与实际匹配）
    df = pd.read_csv(event_csv_path, parse_dates=["start_time", "end_time"])

    # 只保留 Shiftable 类型事件
    df = df[df["Shiftability"] == "Shiftable"].copy()
    df["is_reschedulable"] = df["is_reschedulable"].astype(bool)

    # 加载用户修订的约束字典
    with open(constraint_json_path, "r", encoding="utf-8") as f:
        constraint_dict = json.load(f)

    # 加载电价方案配置
    with open(tariff_config_path, "r", encoding="utf-8") as f:
        tariff_config = json.load(f)
    if tariff_name not in tariff_config:
        raise ValueError(f"❌ Tariff configuration not found for: {tariff_name}")
        # raise ValueError(f"❌ 电价配置中未找到: {tariff_name}")

    # Step 1：处理最小运行时间限制
    for idx, row in df.iterrows():
        aid = row["appliance_name"]  # 注意小写字段名
        min_duration = constraint_dict.get(aid, {}).get("min_duration", 0)
        if row["duration(min)"] <= min_duration:
            df.at[idx, "is_reschedulable"] = False

    # Step 2：处理高价区重叠限制
    low_periods = tariff_config[tariff_name]["low_periods"]
    high_periods = get_high_price_ranges(low_periods)

    df["expensive_minutes"] = 0
    for idx, row in df.iterrows():
        if not row["is_reschedulable"]:
            continue
        start = row["start_time"]
        end = row["end_time"]
        overlap = get_overlap_minutes(start, end, high_periods)
        df.at[idx, "expensive_minutes"] = overlap
        if overlap < 5:
            df.at[idx, "is_reschedulable"] = False

    # 保存处理后的文件
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"shiftable_event_masked_{tariff_name}.csv")
    df.to_csv(output_path, index=False)
    print(f"✅ Filtered results have been saved to: {output_path}")
    # print(f"✅ 已保存筛选结果至：{output_path}")
    return output_path
