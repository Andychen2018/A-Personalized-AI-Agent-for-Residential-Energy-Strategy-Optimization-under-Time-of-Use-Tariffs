# 文件：tools/p_052_conflict_resolver.py

import pandas as pd
import os
from datetime import datetime, timedelta


def time_to_minutes(tstr):
    h, m = map(int, tstr.split(":"))
    return int(h) * 60 + int(m)

def minutes_to_time(m):
    return f"{m//60:02d}:{m%60:02d}"

def recover_date(event_id):
    # 兼容电器名称中带下划线，如 "Tumble_Dryer_2013-10-24_01"
    # 提取中间的日期字段
    for token in event_id.split("_"):
        try:
            datetime.strptime(token, "%Y-%m-%d")
            return token
        except:
            continue
    raise ValueError(f"Cannot find a valid date in event_id: {event_id}")
    # raise ValueError(f"event_id 中找不到有效日期: {event_id}")


def resolve_conflicts(df: pd.DataFrame, output_path=None):
    df = df.copy()
    df = df[df['shifted_start_time'] != "FAILED"]

    grouped = df.groupby(["appliance_name", df["event_id"].apply(recover_date)])
    updated_rows = []

    for (appliance, date), group in grouped:
        used_slots = []  # list of [start_min, end_min]
        group_sorted = group.sort_values("event_id")

        for _, row in group_sorted.iterrows():
            start = time_to_minutes(row['shifted_start_time'])
            end = time_to_minutes(row['shifted_end_time'])
            dur = row['duration(min)']

            # 检查是否冲突
            conflict = False
            for s, e in used_slots:
                if not (end <= s or start >= e):
                    conflict = True
                    break

            if not conflict:
                base_date = datetime.strptime(date, "%Y-%m-%d")
                new_row = row.copy()
                new_row['shifted_start_datetime'] = base_date + timedelta(minutes=start)
                new_row['shifted_end_datetime'] = base_date + timedelta(minutes=end)
                used_slots.append([start, end])
                updated_rows.append(new_row)
                # used_slots.append([start, end])
                # updated_rows.append(row)
            else:
                # 查找新的可用时间段，必须晚于当前 used_slots 的最晚结束时间
                used_slots.sort()
                latest_end = max(e for _, e in used_slots)
                found = False

                for cand_start in range(latest_end, 38 * 60 - dur):
                    cand_end = cand_start + dur
                    overlap = any(not (cand_end <= s or cand_start >= e) for s, e in used_slots)
                    if not overlap:
                        new_row = row.copy()
                        new_row['shifted_start_time'] = minutes_to_time(cand_start)
                        new_row['shifted_end_time'] = minutes_to_time(cand_end)
                        base_date = datetime.strptime(date, "%Y-%m-%d")
                        new_row['shifted_start_datetime'] = base_date + timedelta(minutes=cand_start)
                        new_row['shifted_end_datetime'] = base_date + timedelta(minutes=cand_end)
                        used_slots.append([cand_start, cand_end])
                        updated_rows.append(new_row)
                        found = True
                        break

                if not found:
                    new_row = row.copy()
                    new_row['shifted_start_time'] = "FAILED"
                    new_row['shifted_end_time'] = "FAILED"
                    new_row['shifted_start_datetime'] = None
                    new_row['shifted_end_datetime'] = None
                    updated_rows.append(new_row)

 
    df['_original_order'] = range(len(df))

    
    df_out = pd.DataFrame(updated_rows)

    # 与原 df 的顺序对齐
    df_out = df_out.merge(df[["event_id", "_original_order"]], on="event_id", how="left")
    df_out = df_out.sort_values("_original_order").drop(columns=["_original_order"])

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_out.to_csv(output_path, index=False)
        print(f"✅ Result after conflict handling saved to: {output_path}")

    # 📊 Add summary statistics
    total_events = len(df_out)
    failed_events = df_out['shifted_start_time'].eq("FAILED").sum()
    success_events = total_events - failed_events

    print("\n📊 Scheduling statistics after conflict handling:")
    print(f"📁 Total number of events: {total_events}")
    print(f"✅ Successfully scheduled events: {success_events}")
    print(f"❌ Events still failed after conflict handling: {failed_events}")

    summary = df_out[df_out["shifted_start_time"] != "FAILED"] \
        .groupby(["appliance_name"]).size().to_frame("Success")
    print(f"\n📊 Number of successful schedules per appliance:")
    print(summary)

    return df_out

   

def resolve_conflicts_for_all():
    base_path = "./output/05_scheduling/"
    for name in ["Economy_7", "Economy_10"]:
        input_path = os.path.join(base_path, f"heuristic_{name}.csv")
        output_path = os.path.join(base_path, f"heuristic_{name}_resolved.csv")
        if os.path.exists(input_path):
            print(f"\n🔍 Processing scheduling conflict file: {input_path}")
            # print(f"\n🔍 正在处理调度冲突文件：{input_path}")
            df = pd.read_csv(input_path)
            resolve_conflicts(df, output_path)
        else:
            print(f"⚠️ File not found: {input_path}")
            # print(f"⚠️ 未找到文件：{input_path}")

# ✅ 默认处理两个结果文件（Economy_7 和 Economy_10）
if __name__ == "__main__":
    resolve_conflicts_for_all()
