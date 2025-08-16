import os
import pandas as pd
from typing import Tuple

# 🎯 功率测量噪声鲁棒性实验路径配置
EXPERIMENT_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
NOISE_DATA_DIR = os.path.join(EXPERIMENT_DIR, "Noise_data")
OUTPUT_BASE_DIR = os.path.join(EXPERIMENT_DIR, "output")

# ========== Parameter Settings ==========
# 🎯 调整参数以减少过多的短时间事件
DEFAULT_PMIN = 10.0  # 提高最小功率阈值到10W，过滤掉待机功率
DEFAULT_TMIN = 5     # 提高最小持续时间到5分钟，过滤掉瞬时波动
BASELOAD_PMIN = 5.0  # 基础负载最小功率阈值
BASELOAD_TMIN = 10   # 基础负载最小持续时间

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

# ========== Enhanced API for single household ==========
def run_event_segmentation_single(
    house_id: str,
    power_csv: str,
    label_csv: str,
    output_dir: str = "./output/02_event_segments/"
) -> pd.DataFrame:
    """
    Run event segmentation for a single household

    Args:
        house_id: House identifier (e.g., "house1")
        power_csv: Path to power data CSV
        label_csv: Path to appliance label CSV
        output_dir: Output directory

    Returns:
        DataFrame with segmented events
    """
    # Create house-specific output directory
    house_output_dir = os.path.join(output_dir, house_id)
    os.makedirs(house_output_dir, exist_ok=True)

    output_csv = os.path.join(house_output_dir, f"02_appliance_event_segments_{house_id}.csv")

    print(f"🔍 Processing {house_id.upper()} event segmentation...")

    return process_all_appliances(power_csv, label_csv, output_csv)


# ========== Batch processing API ==========
def batch_run_event_segmentation(
    house_data_dict: dict,
    input_dir: str = None,  # 将使用噪声数据目录
    label_dir: str = None,  # 将使用实验输出目录
    output_dir: str = None  # 将使用实验输出目录
) -> dict:
    """
    功率测量噪声鲁棒性实验 - 批量事件分割

    Args:
        house_data_dict: Dictionary mapping house_id to house info
        input_dir: Directory containing noisy power data (will use NOISE_DATA_DIR if None)
        label_dir: Directory containing appliance labels (will use experiment output if None)
        output_dir: Directory to save event segments (will use experiment output if None)

    Returns:
        Dictionary mapping house_id to result DataFrame
    """

    # 🎯 使用功率测量噪声实验的路径配置
    if input_dir is None:
        input_dir = NOISE_DATA_DIR
    if label_dir is None:
        label_dir = os.path.join(OUTPUT_BASE_DIR, "02_behavior_modeling")
    if output_dir is None:
        output_dir = os.path.join(OUTPUT_BASE_DIR, "02_event_segments")

    results = {}
    failed_houses = []

    print(f"🚀 功率测量噪声实验 - 批量事件分割，处理 {len(house_data_dict)} 个房屋...")
    print(f"📁 噪声数据目录: {input_dir}")
    print(f"📁 标签目录: {label_dir}")
    print(f"📁 输出目录: {output_dir}")
    print("=" * 80)

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Processing {house_id}...")

            # 🎯 定义文件路径 - 使用噪声数据
            power_csv = os.path.join(input_dir, house_id, f"01_perception_alignment_result_{house_id}_noisy.csv")
            label_csv = os.path.join(label_dir, house_id, f"02_1_appliance_shiftable_label_{house_id}.csv")  # 每个房屋有自己的标签文件

            # Check if required files exist
            if not os.path.exists(power_csv):
                print(f"❌ Power data file not found: {power_csv}")
                failed_houses.append(house_id)
                continue

            if not os.path.exists(label_csv):
                print(f"❌ Label file not found: {label_csv}")
                failed_houses.append(house_id)
                continue

            # Run event segmentation
            df_result = run_event_segmentation_single(
                house_id=house_id,
                power_csv=power_csv,
                label_csv=label_csv,
                output_dir=output_dir
            )

            results[house_id] = df_result
            print(f"✅ {house_id} completed successfully! Generated {len(df_result)} events")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch event segmentation completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for failed_house in failed_houses:
            print(f"  - {failed_house}")

    # Display summary statistics
    total_events = sum(len(df) for df in results.values())
    print(f"📊 Total events generated: {total_events}")

    return results


# ========== Legacy API for backward compatibility ==========
def run_event_segmentation(
    power_csv=None,  # 将使用噪声数据
    label_csv=None,  # 将使用实验输出
    output_csv=None  # 将使用实验输出
):
    """功率测量噪声实验版本 - Legacy function for backward compatibility"""

    # 🎯 使用功率测量噪声实验的默认路径
    if power_csv is None:
        power_csv = os.path.join(NOISE_DATA_DIR, "house1/01_perception_alignment_result_house1_noisy.csv")
    if label_csv is None:
        label_csv = os.path.join(OUTPUT_BASE_DIR, "02_behavior_modeling/02_1_appliance_shiftable_label.csv")
    if output_csv is None:
        output_csv = os.path.join(OUTPUT_BASE_DIR, "02_event_segments/02_appliance_event_segments.csv")

    return process_all_appliances(power_csv, label_csv, output_csv)




















# import os
# import pandas as pd
# from typing import Tuple

# # ========== 参数设置 ==========
# DEFAULT_PMIN = 2.0
# DEFAULT_TMIN = 1  # minutes
# BASELOAD_PMIN = 1.0
# BASELOAD_TMIN = 5

# # ========== 工具函数：读取数据 ==========
# def load_power_data(power_csv: str) -> pd.DataFrame:
#     if not os.path.isfile(power_csv):
#         raise ValueError(f"❌ 输入路径 {power_csv} 不是一个文件，请检查路径是否正确。")
#     df = pd.read_csv(power_csv, parse_dates=["Time"])
#     df.set_index("Time", inplace=True)
#     return df

# def load_appliance_thresholds(label_csv: str) -> dict:
#     df = pd.read_csv(label_csv)
#     thresholds = {}
#     for _, row in df.iterrows():
#         aid = row["ApplianceID"]
#         name = row["ApplianceName"]
#         shift = row["Shiftability"]
#         pmin = row.get("Pmin", DEFAULT_PMIN)
#         tmin = row.get("Tmin", DEFAULT_TMIN)
#         thresholds[aid] = {
#             "ApplianceName": name,
#             "Shiftability": shift,
#             "Pmin": float(pmin) if not pd.isna(pmin) else DEFAULT_PMIN,
#             "Tmin": int(tmin) if not pd.isna(tmin) else DEFAULT_TMIN
#         }
#     return thresholds

# # ========== 不同电器策略的分段函数 ==========
# def segment_events_general(series: pd.Series, pmin: float, tmin: int) -> list:
#     segments = []
#     active = series > pmin
#     current_start = None

#     for i in range(len(series)):
#         time = series.index[i]
#         if active.iloc[i]:
#             if current_start is None:
#                 current_start = time
#         else:
#             if current_start is not None:
#                 duration = (time - current_start).total_seconds() / 60
#                 if duration >= tmin:
#                     segment = series[current_start:time]
#                     energy = segment.sum()
#                     segments.append((current_start, time, duration, energy))
#                 current_start = None

#     if current_start is not None:
#         duration = (series.index[-1] - current_start).total_seconds() / 60
#         if duration >= tmin:
#             segment = series[current_start:]
#             energy = segment.sum()
#             segments.append((current_start, series.index[-1], duration, energy))

#     return segments

# def segment_events_for_baseload(series: pd.Series, pmin: float, tmin: int) -> list:
#     return segment_events_general(series, pmin=BASELOAD_PMIN, tmin=BASELOAD_TMIN)

# def segment_events_for_shiftable(series: pd.Series, pmin: float, tmin: int) -> list:
#     return segment_events_general(series, pmin, tmin)

# def segment_events_for_non_shiftable(series: pd.Series, pmin: float, tmin: int) -> list:
#     return segment_events_general(series, pmin, tmin)

# # ========== 主流程 ==========
# def process_all_appliances(power_csv: str, label_csv: str, output_csv: str) -> pd.DataFrame:
#     print("接下来我们将对所有电器的时序数据进行事件识别处理，所有连续的运行数据被处理成离散的工作事件...")
#     df_power = load_power_data(power_csv)
#     thresholds = load_appliance_thresholds(label_csv)

#     all_segments = []

#     for aid, params in thresholds.items():
#         if aid not in df_power.columns:
#             print(f"⚠️ 数据中缺失电器列：{aid}，已跳过。")
#             continue

#         series = df_power[aid]
#         shift = params["Shiftability"]
#         name = params["ApplianceName"]
#         pmin = params["Pmin"]
#         tmin = params["Tmin"]

#         if shift == "Base":
#             segs = segment_events_for_baseload(series, pmin, tmin)
#         elif shift == "Shiftable":
#             segs = segment_events_for_shiftable(series, pmin, tmin)
#         else:
#             segs = segment_events_for_non_shiftable(series, pmin, tmin)

#         for (start, end, dur, energy) in segs:
#             all_segments.append({
#                 "appliance_ID": aid,
#                 "appliance_name": name,
#                 "Shiftability": shift,
#                 "start_time": start,
#                 "end_time": end,
#                 "duration(min)": round(dur, 2),
#                 "energy(W)": round(energy, 2)
#             })

#     result_df = pd.DataFrame(all_segments)
#     os.makedirs(os.path.dirname(output_csv), exist_ok=True)
#     result_df.to_csv(output_csv, index=False)
#     print(f"✅ 各个电器的运行事件结果已经处理完成，结果保存在：{output_csv}")
#     print(f"✅ 处理结果包含 {len(result_df)} 条事件记录。")
#     print("✅ 处理结果的前10条记录如下：")
#     print(result_df.head(10))
#     return result_df

# # ========== 对外调用入口 ==========
# def run_event_segmentation(
#     power_csv="./output/01_preprocessed/01_perception_alignment_result.csv",
#     label_csv="./output/02_behavior_modeling/02_1_appliance_shiftable_label.csv",
#     output_csv="./output/02_event_segments/02_appliance_event_segments.csv"
# ):    
#     return process_all_appliances(power_csv, label_csv, output_csv)


