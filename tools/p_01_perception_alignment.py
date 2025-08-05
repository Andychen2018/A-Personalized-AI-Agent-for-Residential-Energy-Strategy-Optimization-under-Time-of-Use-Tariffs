
# import os
# import pandas as pd
# import numpy as np

# # （1）读取数据路径接口
# def load_power_data(file_path: str) -> pd.DataFrame:
#     df = pd.read_csv(file_path, parse_dates=["Time"])
#     return df

# # （2）异常记录处理函数（已增强）
# def remove_issue_records(df: pd.DataFrame) -> pd.DataFrame:
#     if "Issues" in df.columns:
#         issues_count = (df["Issues"] == 1).sum()
#         print(f"⚠️ 标记为异常 (Issues == 1) 的记录数: {issues_count}")
#         df_clean = df[df["Issues"] != 1].copy()
#         print(f"✅ 清洗后有效记录数: {len(df_clean)}")
#         return df_clean
#     print("⚠️ 未检测到 Issues 列，默认全部有效")
#     return df.copy()

# # （3）感知时间粒度
# def detect_temporal_granularity(df: pd.DataFrame, time_col: str = "Time") -> str:
#     diffs = df[time_col].sort_values().diff().dropna()
#     if diffs.empty:
#         return "Unknown"
#     common_diff = diffs.mode()[0]
#     freq = pd.tseries.frequencies.to_offset(common_diff).freqstr.lower()
#     return f"1{freq}" if freq in {"s", "min", "h", "d"} else freq

# # （4）处理高频（<1min）时间序列数据（聚合为分钟级）
# def downsample_to_minute(df: pd.DataFrame) -> pd.DataFrame:
#     df["Time_min"] = df["Time"].dt.floor("min")
#     power_cols = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
#     df_min = df.groupby("Time_min")[power_cols].mean().reset_index()
#     df_min.rename(columns={"Time_min": "Time"}, inplace=True)
#     return df_min

# # （5）处理低频（>1min）时间序列数据（插值）
# def interpolate_to_minute(df: pd.DataFrame, target_freq: str = "1min") -> pd.DataFrame:
#     df = df.set_index("Time").resample(target_freq).interpolate(method="time").reset_index()
#     return df

# # （6）保存结果函数（新增打印行数）
# def save_aligned_result(df: pd.DataFrame, save_dir: str, filename: str) -> str:
#     os.makedirs(save_dir, exist_ok=True)
#     save_path = os.path.join(save_dir, filename)
#     df.to_csv(save_path, index=False)
#     print(f"📏 对齐后总行数：{len(df)}")
#     return save_path

# # ✅ Agent 主流程封装
# def preprocess_power_series(input_path: str="/home/deep/TimeSeries/dataset/cleand_data/CLEAN_House1.csv", 
#                             output_dir: str = "./output/01_preprocessed/",
#                             ) -> str:
#     print("我们正在执行时间序列细粒度感知任务，请稍等：\n")
#     print("🤖 [Agent 感知模块] 启动：解析原始功率数据，执行时间一致性检查与分辨率对齐...\n")

#     df_raw = load_power_data(input_path)
#     print(f"📊 原始记录数：{len(df_raw)}")

#     df_clean = remove_issue_records(df_raw)

#     granularity = detect_temporal_granularity(df_clean)
#     print(f"🔍 感知时间粒度：{granularity}")

#     if pd.Timedelta(granularity) < pd.Timedelta("1min"):
#         print("📉 高频采样数据 → 执行滑动平均聚合")
#         df_result = downsample_to_minute(df_clean)
#     elif pd.Timedelta(granularity) > pd.Timedelta("1min"):
#         print("📈 低频采样数据 → 执行插值插补")
#         df_result = interpolate_to_minute(df_clean)
#     else:
#         print("⏱️ 已为 1min 粒度，无需调整")
#         df_result = df_clean.copy()

#     result_path = save_aligned_result(df_result, output_dir, "01_perception_alignment_result.csv")
#     print(f"\n✅ 各个电器的序列感知对齐完成！文件将保存在路径：{result_path}")
#     print("📌 我给您看一下感知结果的前5行数据，它们是以1min为细粒度的数据：")
#     print(df_result.head())

#     return result_path
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

# ✅ Main agent preprocessing routine (single file)
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


# ✅ Enhanced batch processing function for multiple houses
def preprocess_power_series_single(input_path: str, house_id: str, base_output_dir: str = "./output/01_preprocessed/") -> str:
    """
    Process a single house data file with house-specific output directory.

    Args:
        input_path: Path to the input CSV file
        house_id: House identifier (e.g., "house1", "house2")
        base_output_dir: Base output directory

    Returns:
        Path to the saved result file
    """
    # Create house-specific output directory
    house_output_dir = os.path.join(base_output_dir, house_id)

    print(f"\n🏠 Processing {house_id.upper()}...")
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

    # Save with house-specific filename
    filename = f"01_perception_alignment_result_{house_id}.csv"
    result_path = save_aligned_result(df_result, house_output_dir, filename)
    print(f"\n✅ {house_id.upper()} appliance-level series alignment completed! File saved at: {result_path}")
    print("📌 Here are the first 5 rows of the aligned 1-minute resolution data:")
    print(df_result.head())

    return result_path


def batch_preprocess_power_series(input_dir: str = "/home/deep/TimeSeries/dataset/cleand_data/",
                                  base_output_dir: str = "./output/01_preprocessed/",
                                  file_pattern: str = "CLEAN_House*.csv") -> dict:
    """
    Batch process multiple house data files.

    Args:
        input_dir: Directory containing input CSV files
        base_output_dir: Base output directory
        file_pattern: File pattern to match (e.g., "CLEAN_House*.csv")

    Returns:
        Dictionary mapping house_id to result file path
    """
    import glob

    # Find all matching files
    search_pattern = os.path.join(input_dir, file_pattern)
    input_files = glob.glob(search_pattern)
    input_files.sort()  # Sort for consistent processing order

    if not input_files:
        print(f"⚠️ No files found matching pattern: {search_pattern}")
        return {}

    print(f"🔍 Found {len(input_files)} files to process:")
    for file_path in input_files:
        print(f"  - {os.path.basename(file_path)}")

    results = {}
    failed_files = []

    print(f"\n🚀 Starting batch processing of {len(input_files)} house data files...\n")
    print("=" * 80)

    for i, input_path in enumerate(input_files, 1):
        filename = os.path.basename(input_path)

        # Extract house number from filename (e.g., "CLEAN_House1.csv" -> "house1")
        try:
            if "House" in filename:
                house_num = filename.split("House")[1].split(".")[0]
                house_id = f"house{house_num}"
            else:
                # Fallback: use filename without extension
                house_id = os.path.splitext(filename)[0].lower()

            print(f"\n[{i}/{len(input_files)}] Processing: {filename} → {house_id}")

            result_path = preprocess_power_series_single(input_path, house_id, base_output_dir)
            results[house_id] = result_path

            print(f"✅ {house_id} completed successfully!")

        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            failed_files.append(filename)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch processing completed!")
    print(f"✅ Successfully processed: {len(results)} files")
    if failed_files:
        print(f"❌ Failed to process: {len(failed_files)} files")
        for failed_file in failed_files:
            print(f"  - {failed_file}")

    print(f"\n📁 Results saved in: {base_output_dir}")
    print("📋 Processed houses:")
    for house_id, result_path in results.items():
        print(f"  - {house_id}: {result_path}")

    return results


def batch_preprocess_specific_houses(house_numbers: list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21],
                                     input_dir: str = "/home/deep/TimeSeries/dataset/cleand_data/",
                                     base_output_dir: str = "./output/01_preprocessed/") -> dict:
    """
    Batch process specific house data files by house numbers.

    Args:
        house_numbers: List of house numbers to process
        input_dir: Directory containing input CSV files
        base_output_dir: Base output directory

    Returns:
        Dictionary mapping house_id to result file path
    """
    results = {}
    failed_files = []

    print(f"🔍 Target houses: {house_numbers}")
    print(f"📁 Input directory: {input_dir}")
    print(f"📁 Output directory: {base_output_dir}")

    # Check which files exist
    existing_files = []
    missing_files = []

    for house_num in house_numbers:
        filename = f"CLEAN_House{house_num}.csv"
        file_path = os.path.join(input_dir, filename)

        if os.path.exists(file_path):
            existing_files.append((house_num, file_path))
        else:
            missing_files.append(filename)

    if missing_files:
        print(f"⚠️ Missing files: {missing_files}")

    print(f"✅ Found {len(existing_files)} files to process:")
    for house_num, file_path in existing_files:
        print(f"  - House{house_num}: {os.path.basename(file_path)}")

    if not existing_files:
        print("❌ No files found to process!")
        return {}

    print(f"\n🚀 Starting batch processing of {len(existing_files)} house data files...\n")
    print("=" * 80)

    for i, (house_num, input_path) in enumerate(existing_files, 1):
        filename = os.path.basename(input_path)
        house_id = f"house{house_num}"

        try:
            print(f"\n[{i}/{len(existing_files)}] Processing: {filename} → {house_id}")

            result_path = preprocess_power_series_single(input_path, house_id, base_output_dir)
            results[house_id] = result_path

            print(f"✅ {house_id} completed successfully!")

        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            failed_files.append(filename)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch processing completed!")
    print(f"✅ Successfully processed: {len(results)} files")
    if failed_files:
        print(f"❌ Failed to process: {len(failed_files)} files")
        for failed_file in failed_files:
            print(f"  - {failed_file}")

    print(f"\n📁 Results saved in: {base_output_dir}")
    print("📋 Processed houses:")
    for house_id, result_path in results.items():
        print(f"  - {house_id}: {result_path}")

    return results


def batch_preprocess_specific_houses(house_numbers: list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21],
                                     input_dir: str = "/home/deep/TimeSeries/dataset/cleand_data/",
                                     base_output_dir: str = "./output/01_preprocessed/") -> dict:
    """
    Batch process specific house data files by house numbers.

    Args:
        house_numbers: List of house numbers to process
        input_dir: Directory containing input CSV files
        base_output_dir: Base output directory

    Returns:
        Dictionary mapping house_id to result file path
    """
    results = {}
    failed_files = []

    print(f"🔍 Target houses: {house_numbers}")
    print(f"📁 Input directory: {input_dir}")
    print(f"📁 Output directory: {base_output_dir}")

    # Check which files exist
    existing_files = []
    missing_files = []

    for house_num in house_numbers:
        filename = f"CLEAN_House{house_num}.csv"
        file_path = os.path.join(input_dir, filename)

        if os.path.exists(file_path):
            existing_files.append((house_num, file_path))
        else:
            missing_files.append(filename)

    if missing_files:
        print(f"⚠️ Missing files: {missing_files}")

    print(f"✅ Found {len(existing_files)} files to process:")
    for house_num, file_path in existing_files:
        print(f"  - House{house_num}: {os.path.basename(file_path)}")

    if not existing_files:
        print("❌ No files found to process!")
        return {}

    print(f"\n🚀 Starting batch processing of {len(existing_files)} house data files...\n")
    print("=" * 80)

    for i, (house_num, input_path) in enumerate(existing_files, 1):
        filename = os.path.basename(input_path)
        house_id = f"house{house_num}"

        try:
            print(f"\n[{i}/{len(existing_files)}] Processing: {filename} → {house_id}")

            result_path = preprocess_power_series_single(input_path, house_id, base_output_dir)
            results[house_id] = result_path

            print(f"✅ {house_id} completed successfully!")

        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            failed_files.append(filename)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch processing completed!")
    print(f"✅ Successfully processed: {len(results)} files")
    if failed_files:
        print(f"❌ Failed to process: {len(failed_files)} files")
        for failed_file in failed_files:
            print(f"  - {failed_file}")

    print(f"\n📁 Results saved in: {base_output_dir}")
    print("📋 Processed houses:")
    for house_id, result_path in results.items():
        print(f"  - {house_id}: {result_path}")

    return results
