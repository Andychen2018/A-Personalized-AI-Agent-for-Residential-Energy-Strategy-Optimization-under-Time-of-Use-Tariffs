import os
import pandas as pd
from typing import Tuple

# ========== Parameter Settings ==========
DEFAULT_PMIN = 2.0
DEFAULT_TMIN = 1  # minutes
BASELOAD_PMIN = 1.0
BASELOAD_TMIN = 5

# ========== Utility Function: Load Data ==========
def load_power_data(power_csv: str) -> pd.DataFrame:
    if not os.path.isfile(power_csv):
        raise ValueError(f"❌ The input path {power_csv} is not a valid file. Please check the path.")
    df = pd.read_csv(power_csv, parse_dates=["Time"])
    df.set_index("Time", inplace=True)
    return df

def load_appliance_thresholds(label_csv: str) -> dict:
    df = pd.read_csv(label_csv)
    thresholds = {}
    for _, row in df.iterrows():
        aid = row["ApplianceID"]
        name = row["ApplianceName"]
        shift = row["Shiftability"]
        pmin = row.get("Pmin", DEFAULT_PMIN)
        tmin = row.get("Tmin", DEFAULT_TMIN)
        thresholds[aid] = {
            "ApplianceName": name,
            "Shiftability": shift,
            "Pmin": float(pmin) if not pd.isna(pmin) else DEFAULT_PMIN,
            "Tmin": int(tmin) if not pd.isna(tmin) else DEFAULT_TMIN
        }
    return thresholds

# ========== Event Segmentation Strategies ==========
def segment_events_general(series: pd.Series, pmin: float, tmin: int) -> list:
    segments = []
    active = series > pmin
    current_start = None

    for i in range(len(series)):
        time = series.index[i]
        if active.iloc[i]:
            if current_start is None:
                current_start = time
        else:
            if current_start is not None:
                duration = (time - current_start).total_seconds() / 60
                if duration >= tmin:
                    segment = series[current_start:time]
                    energy = segment.sum()
                    segments.append((current_start, time, duration, energy))
                current_start = None

    if current_start is not None:
        duration = (series.index[-1] - current_start).total_seconds() / 60
        if duration >= tmin:
            segment = series[current_start:]
            energy = segment.sum()
            segments.append((current_start, series.index[-1], duration, energy))

    return segments

def segment_events_for_baseload(series: pd.Series, pmin: float, tmin: int) -> list:
    return segment_events_general(series, pmin=BASELOAD_PMIN, tmin=BASELOAD_TMIN)

def segment_events_for_shiftable(series: pd.Series, pmin: float, tmin: int) -> list:
    return segment_events_general(series, pmin, tmin)

def segment_events_for_non_shiftable(series: pd.Series, pmin: float, tmin: int) -> list:
    return segment_events_general(series, pmin, tmin)

# ========== Main Process ==========
def process_all_appliances(power_csv: str, label_csv: str, output_csv: str) -> pd.DataFrame:
    print("Now we will detect operation events for all appliances. Continuous power usage data will be segmented into discrete operation events...")
    df_power = load_power_data(power_csv)
    thresholds = load_appliance_thresholds(label_csv)

    all_segments = []

    for aid, params in thresholds.items():
        if aid not in df_power.columns:
            print(f"⚠️ Appliance column missing in data: {aid}. Skipping.")
            continue

        series = df_power[aid]
        shift = params["Shiftability"]
        name = params["ApplianceName"]
        pmin = params["Pmin"]
        tmin = params["Tmin"]

        if shift == "Base":
            segs = segment_events_for_baseload(series, pmin, tmin)
        elif shift == "Shiftable":
            segs = segment_events_for_shiftable(series, pmin, tmin)
        else:
            segs = segment_events_for_non_shiftable(series, pmin, tmin)

        for (start, end, dur, energy) in segs:
            all_segments.append({
                "appliance_ID": aid,
                "appliance_name": name,
                "Shiftability": shift,
                "start_time": start,
                "end_time": end,
                "duration(min)": round(dur, 2),
                "energy(W)": round(energy, 2)
            })

    result_df = pd.DataFrame(all_segments)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    result_df.to_csv(output_csv, index=False)
    print(f"✅ Appliance operation event detection completed. Result saved to: {output_csv}")
    print(f"✅ Total number of detected events: {len(result_df)}")
    print("✅ Here are the first 10 records from the result:")
    print(result_df.head(10))
    return result_df

# ========== Public API ==========
def run_event_segmentation(
    power_csv="./output/01_preprocessed/01_perception_alignment_result.csv",
    label_csv="./output/02_behavior_modeling/02_1_appliance_shiftable_label.csv",
    output_csv="./output/02_event_segments/02_appliance_event_segments.csv"
):    
    return process_all_appliances(power_csv, label_csv, output_csv)















