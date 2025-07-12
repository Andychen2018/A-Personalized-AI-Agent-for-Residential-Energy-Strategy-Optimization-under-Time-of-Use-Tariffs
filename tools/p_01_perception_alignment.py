
import os
import pandas as pd
import numpy as np

# (1) Load power data
def load_power_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, parse_dates=["Time"])
    return df

# (2) Remove issue-labeled records (enhanced)
def remove_issue_records(df: pd.DataFrame) -> pd.DataFrame:
    if "Issues" in df.columns:
        issues_count = (df["Issues"] == 1).sum()
        print(f"⚠️ Number of records flagged as issues (Issues == 1): {issues_count}")
        df_clean = df[df["Issues"] != 1].copy()
        print(f"✅ Number of valid records after cleaning: {len(df_clean)}")
        return df_clean
    print("⚠️ No 'Issues' column detected. Assuming all records are valid.")
    return df.copy()

# (3) Detect time granularity
def detect_temporal_granularity(df: pd.DataFrame, time_col: str = "Time") -> str:
    diffs = df[time_col].sort_values().diff().dropna()
    if diffs.empty:
        return "Unknown"
    common_diff = diffs.mode()[0]
    freq = pd.tseries.frequencies.to_offset(common_diff).freqstr.lower()
    return f"1{freq}" if freq in {"s", "min", "h", "d"} else freq

# (4) Downsample high-frequency (<1min) data to 1-minute resolution
def downsample_to_minute(df: pd.DataFrame) -> pd.DataFrame:
    df["Time_min"] = df["Time"].dt.floor("min")
    power_cols = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
    df_min = df.groupby("Time_min")[power_cols].mean().reset_index()
    df_min.rename(columns={"Time_min": "Time"}, inplace=True)
    return df_min

# (5) Interpolate low-frequency (>1min) data to 1-minute resolution
def interpolate_to_minute(df: pd.DataFrame, target_freq: str = "1min") -> pd.DataFrame:
    df = df.set_index("Time").resample(target_freq).interpolate(method="time").reset_index()
    return df

# (6) Save results
def save_aligned_result(df: pd.DataFrame, save_dir: str, filename: str) -> str:
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    df.to_csv(save_path, index=False)
    print(f"📏 Total rows after alignment: {len(df)}")
    return save_path

# ✅ Main agent preprocessing routine
def preprocess_power_series(input_path: str = "/home/deep/TimeSeries/dataset/cleand_data/CLEAN_House1.csv",
                            output_dir: str = "./output/01_preprocessed/") -> str:
    print("Starting time-series granularity recognition task...\n")
    print("🤖 [Agent Perception Module] Launching: parsing raw power data, checking time consistency and aligning resolution...\n")

    df_raw = load_power_data(input_path)
    print(f"📊 Raw records count: {len(df_raw)}")

    df_clean = remove_issue_records(df_raw)

    granularity = detect_temporal_granularity(df_clean)
    print(f"🔍 Detected temporal granularity: {granularity}")

    if pd.Timedelta(granularity) < pd.Timedelta("1min"):
        print("📉 High-frequency sampling detected → applying downsampling by averaging")
        df_result = downsample_to_minute(df_clean)
    elif pd.Timedelta(granularity) > pd.Timedelta("1min"):
        print("📈 Low-frequency sampling detected → applying interpolation")
        df_result = interpolate_to_minute(df_clean)
    else:
        print("⏱️ Already in 1-minute resolution, no adjustment needed.")
        df_result = df_clean.copy()

    result_path = save_aligned_result(df_result, output_dir, "01_perception_alignment_result.csv")
    print(f"\n✅ Appliance-level series alignment completed! File saved at: {result_path}")
    print("📌 Here are the first 5 rows of the aligned 1-minute resolution data:")
    print(df_result.head())

    return result_path
