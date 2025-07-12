
# 文件：tools/p_051_base_scheduler.py

import pandas as pd
import json
import os
from datetime import datetime, timedelta

# 时间辅助函数
def time_to_minutes(time_str):
    hour, minute = map(int, time_str.split(":"))
    return int(hour) * 60 + int(minute)

def minutes_to_time(minutes):
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"

def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for current in intervals[1:]:
        prev = merged[-1]
        if current[0] <= prev[1]:
            merged[-1][1] = max(prev[1], current[1])
        else:
            merged.append(current)
    return merged

def subtract_intervals(base, subtract):
    subtract = merge_intervals(subtract)
    result = []
    for s, e in base:
        temp = [[s, e]]
        for rs, re in subtract:
            temp2 = []
            for ts, te in temp:
                if re <= ts or rs >= te:
                    temp2.append([ts, te])
                else:
                    if rs > ts:
                        temp2.append([ts, rs])
                    if re < te:
                        temp2.append([re, te])
            temp = temp2
        result.extend(temp)
    return merge_intervals(result)

def intersect_intervals(a, b):
    a = merge_intervals(a)
    b = merge_intervals(b)
    result = []
    i = j = 0
    while i < len(a) and j < len(b):
        s1, e1 = a[i]
        s2, e2 = b[j]
        start = max(s1, s2)
        end = min(e1, e2)
        if start < end:
            result.append([start, end])
        if e1 < e2:
            i += 1
        else:
            j += 1
    return result

def recover_real_datetime(event_id, shifted_time):
    try:
        date_str = event_id.split("_")[1]  
        date_base = datetime.strptime(date_str, "%Y-%m-%d")
        return date_base + timedelta(minutes=shifted_time)
    except Exception:
        return None

# 主调度函数
def schedule_shiftable_events(economy7_path, economy10_path, constraints_path, tariff_path, output_path):
    df_list = []
    economy7_appliances = []

    if economy7_path:
        df7 = pd.read_csv(economy7_path, parse_dates=['start_time', 'end_time'], dayfirst=True)
        df7['tariff'] = 'Economy_7'
        df_list.append(df7)
        economy7_appliances = df7['appliance_name'].unique()
    if economy10_path:
        df10 = pd.read_csv(economy10_path, parse_dates=['start_time', 'end_time'], dayfirst=True)
        df10['tariff'] = 'Economy_10'
        df_list.append(df10)

    if not df_list:
        raise ValueError("At least one of economy7_path or economy10_path must be provided.")
        # raise ValueError("必须提供至少一个 economy7_path 或 economy10_path")

    df = pd.concat(df_list, ignore_index=True)
    df = df[df['is_reschedulable'] == True].copy()

    with open(constraints_path, 'r') as f:
        constraints = json.load(f)
    with open(tariff_path, 'r') as f:
        tariffs = json.load(f)

    results = []


    for appliance_name, setting in constraints.items():
        min_dur = setting.get("min_duration", 0)
        latest_finish_min = time_to_minutes(setting['latest_finish'])

        df_app = df[(df['appliance_name'] == appliance_name) & (df['duration(min)'] >= min_dur)].copy()
        if df_app.empty:
            continue

        total_range = [[0, latest_finish_min]]
        forbid_all = []
        days = (latest_finish_min + 1439) // 1440
        for s, e in setting.get("forbidden_time", []):
            s_min = time_to_minutes(s)
            e_min = time_to_minutes(e)
            for i in range(days + 1):
                start = s_min + i * 1440
                end = e_min + i * 1440
                if start < latest_finish_min:
                    forbid_all.append([start, min(end, latest_finish_min)])
        runnable = subtract_intervals(total_range, forbid_all)

        tariff_type = "Economy_7" if appliance_name in economy7_appliances else "Economy_10"
        tconf = tariffs.get(tariff_type)

        low_all = []
        if tconf['type'] == 'time_based':
            for s, e in tconf['low_periods']:
                s_min = time_to_minutes(s)
                e_min = time_to_minutes(e)
                for i in range(days + 1):
                    st = s_min + i * 1440
                    et = e_min + i * 1440
                    if st < latest_finish_min:
                        low_all.append([st, min(et, latest_finish_min)])
            low_all = merge_intervals(low_all)
            high_all = subtract_intervals([[0, latest_finish_min]], low_all)
        else:
            low_all = []
            high_all = [[0, latest_finish_min]]

        best_zones = intersect_intervals(runnable, low_all)
        other_zones = subtract_intervals(runnable, best_zones)
        shift_rule = setting.get("shift_rule", "only_delay")

        for _, row in df_app.iterrows():
            dur = int(row['duration(min)'])
            if isinstance(row['start_time'], str):
                row['start_time'] = pd.to_datetime(row['start_time'])

            orig_start = row['start_time'].hour * 60 + row['start_time'].minute
            shifted_start, shifted_end = -1, -1
            zones = best_zones + other_zones

            for s, e in zones:
                cand = max(s, orig_start) if shift_rule == "only_delay" else s
                if cand + dur <= e:
                    shifted_start = cand
                    shifted_end = cand + dur
                    break

            if shifted_start != -1:
                rate = tconf.get("high_rate", tconf.get("rate"))
                for ls, le in low_all:
                    if ls <= shifted_start < le:
                        rate = tconf.get("low_rate", rate)
                        break
                energy_kwh = row['energy(W)'] / 1000
                cost = energy_kwh * rate * dur / 60

                results.append({
                    "event_id": row['event_id'],
                    "appliance_name": row['appliance_name'],
                    "original_start_time": row['start_time'],
                    "original_end_time": row['end_time'],
                    "shifted_start_time": minutes_to_time(shifted_start),
                    "shifted_end_time": minutes_to_time(shifted_end),
                    "shifted_start_datetime": recover_real_datetime(row['event_id'], shifted_start),
                    "shifted_end_datetime": recover_real_datetime(row['event_id'], shifted_end),
                    "duration(min)": dur,
                    "energy(W)": row['energy(W)'],
                    "tariff": tariff_type,
                    "rate_type": rate,
                    "estimated_cost": round(cost, 4)
                })
            else:
                results.append({
                    "event_id": row['event_id'],
                    "appliance_name": row['appliance_name'],
                    "original_start_time": row['start_time'],
                    "original_end_time": row['end_time'],
                    "shifted_start_time": "FAILED",
                    "shifted_end_time": "FAILED",
                    "shifted_start_datetime": None,
                    "shifted_end_datetime": None,
                    "duration(min)": dur,
                    "energy(W)": row['energy(W)'],
                    "tariff": tariff_type,
                    "rate_type": "N/A",
                    "estimated_cost": None
                })

    df_out = pd.DataFrame(results)
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_out.to_csv(output_path, index=False)

    return df_out


def run_scheduler_tool():
    for tariff_name in ["Economy_7", "Economy_10"]:
        print("\n" + "="*40)
        print(f"📊 Current Tariff Scheme: {tariff_name}")

        # Set file paths
        base_dir = "./output/04_user_constraints"
        input_path = os.path.join(base_dir, f"shiftable_event_masked_{tariff_name}.csv")
        constraint_path = os.path.join(base_dir, "appliance_constraints_revise_by_llm.json")
        tariff_path = "./config/tariff_config.json"
        output_path = f"./output/05_scheduling/heuristic_{tariff_name}.csv"

        # Load original data for statistics
        df_all = pd.read_csv(input_path, parse_dates=["start_time", "end_time"])
        total_count = len(df_all)
        schedulable_count = df_all["is_reschedulable"].sum()
        unschedulable_count = total_count - schedulable_count
        print("🔍 Gathering statistics from original event records...")
        print(f"📁 Total number of events: {total_count}")
        print(f"✅ Reschedulable events: {schedulable_count}")
        print(f"❌ Non-reschedulable events: {unschedulable_count}")

        # Run scheduling
        df_result = schedule_shiftable_events(
            economy7_path=input_path if tariff_name == "Economy_7" else None,
            economy10_path=input_path if tariff_name == "Economy_10" else None,
            constraints_path=constraint_path,
            tariff_path=tariff_path,
            output_path=output_path
        )

        # Group and summarize scheduling results
        df_result["status"] = df_result["shifted_start_time"].apply(lambda x: "Success" if x != "FAILED" else "Fail")
        summary = df_result.groupby(["appliance_name", "status"]).size().unstack(fill_value=0)
        print(f"\n📊 Scheduling results per appliance:")
        print(summary)

        # ✅ Output file path
        print(f"\n📁 Scheduling results saved to: {output_path}")

if __name__ == "__main__":
    run_scheduler_tool()
