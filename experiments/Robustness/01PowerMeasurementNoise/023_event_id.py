import pandas as pd
import os

# 🎯 功率测量噪声鲁棒性实验路径配置
EXPERIMENT_DIR = "/home/deep/TimeSeries/Agent_V2/experiments/Robustness/01PowerMeasurementNoise"
OUTPUT_BASE_DIR = os.path.join(EXPERIMENT_DIR, "output")

# ========== Single household processing ==========
def add_event_id_single(
    house_id: str,
    input_csv: str,
    output_dir: str = None  # 将使用实验输出目录
) -> pd.DataFrame:
    """
    功率测量噪声实验 - 为单个房屋添加事件ID

    Args:
        house_id: House identifier (e.g., "house1")
        input_csv: Path to input event segments CSV
        output_dir: Output directory (will use experiment output if None)

    Returns:
        DataFrame with event IDs added
    """

    # 🎯 使用功率测量噪声实验的输出目录
    if output_dir is None:
        output_dir = os.path.join(OUTPUT_BASE_DIR, "02_event_segments")

    print(f"🔍 功率测量噪声实验 - 处理 {house_id.upper()} 事件ID分配...")
    print("为每个检测到的电器操作事件分配唯一标识符 'event_id'...")

    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"❌ 输入文件不存在: {input_csv}")

    # Create house-specific output directory
    house_output_dir = os.path.join(output_dir, house_id)
    os.makedirs(house_output_dir, exist_ok=True)

    output_csv = os.path.join(house_output_dir, f"02_appliance_event_segments_id_{house_id}.csv")

    df = pd.read_csv(input_csv, parse_dates=["start_time", "end_time"])

    # Add date column
    df["date"] = df["start_time"].dt.date.astype(str)

    # Generate cumulative index per (appliance_name, date) group
    df["event_index"] = df.groupby(["appliance_name", "date"]).cumcount() + 1

    # Generate event_id, e.g., Washer_2024-06-01_01
    df["event_id"] = (
        df["appliance_name"].str.replace(" ", "_") + "_" +
        df["date"] + "_" +
        df["event_index"].astype(str).str.zfill(2)
    )

    # Add reschedulable flag
    df["is_reschedulable"] = df["Shiftability"].apply(
        lambda x: True if x.strip().lower() == "shiftable" else False
    )

    # Reorder columns
    df = df[[
        "event_id", "appliance_name", "appliance_ID", "Shiftability",
        "start_time", "end_time", "duration(min)", "energy(W)", "is_reschedulable"
    ]]

    # Save result
    df.to_csv(output_csv, index=False)
    print(f"✅ The event log with event_id for {house_id.upper()} has been saved to: {output_csv}")

    print(f"Note: Each event_id is a unique identifier that includes appliance name, date, and event index.")
    print(f"Here are the first 10 rows of the result for {house_id.upper()}:")
    print(df.head(10))

    return df


# ========== Batch processing ==========
def batch_add_event_id(
    house_data_dict: dict,
    input_dir: str = None,  # 将使用实验输出目录
    output_dir: str = None  # 将使用实验输出目录
) -> dict:
    """
    功率测量噪声实验 - 批量添加事件ID

    Args:
        house_data_dict: Dictionary mapping house_id to house info
        input_dir: Directory containing event segments (will use experiment output if None)
        output_dir: Output directory (will use experiment output if None)

    Returns:
        Dictionary mapping house_id to result DataFrame
    """

    # 🎯 使用功率测量噪声实验的输出目录
    if input_dir is None:
        input_dir = os.path.join(OUTPUT_BASE_DIR, "02_event_segments")
    if output_dir is None:
        output_dir = os.path.join(OUTPUT_BASE_DIR, "02_event_segments")

    results = {}
    failed_houses = []

    print(f"🚀 功率测量噪声实验 - 批量事件ID分配，处理 {len(house_data_dict)} 个房屋...")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print("=" * 80)

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Processing {house_id}...")

            # Define input file path
            input_csv = os.path.join(input_dir, house_id, f"02_appliance_event_segments_{house_id}.csv")

            # Check if required file exists
            if not os.path.exists(input_csv):
                print(f"❌ Event segments file not found: {input_csv}")
                failed_houses.append(house_id)
                continue

            # Add event IDs
            df_result = add_event_id_single(
                house_id=house_id,
                input_csv=input_csv,
                output_dir=output_dir
            )

            results[house_id] = df_result
            print(f"✅ {house_id} completed successfully! Processed {len(df_result)} events")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch event ID assignment completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for failed_house in failed_houses:
            print(f"  - {failed_house}")

    # Display summary statistics
    total_events = sum(len(df) for df in results.values())
    print(f"📊 Total events with IDs: {total_events}")

    return results


# ========== Legacy function for backward compatibility ==========
def add_event_id(
    input_csv: str = "./output/02_event_segments/02_appliance_event_segments.csv",
    output_csv: str = "./output/02_event_segments/02_appliance_event_segments_id.csv"
) -> pd.DataFrame:
    """Legacy function for backward compatibility"""
    print("Next, we will assign a unique identifier 'event_id' to each detected appliance operation event...")

    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"❌ Input file not found: {input_csv}")

    df = pd.read_csv(input_csv, parse_dates=["start_time", "end_time"])

    # Add date column
    df["date"] = df["start_time"].dt.date.astype(str)

    # Generate cumulative index per (appliance_name, date) group
    df["event_index"] = df.groupby(["appliance_name", "date"]).cumcount() + 1

    # Generate event_id, e.g., Washer_2024-06-01_01
    df["event_id"] = (
        df["appliance_name"].str.replace(" ", "_") + "_" +
        df["date"] + "_" +
        df["event_index"].astype(str).str.zfill(2)
    )

    # Add reschedulable flag
    df["is_reschedulable"] = df["Shiftability"].apply(
        lambda x: True if x.strip().lower() == "shiftable" else False
    )

    # Reorder columns
    df = df[[
        "event_id", "appliance_name", "appliance_ID", "Shiftability",
        "start_time", "end_time", "duration(min)", "energy(W)", "is_reschedulable"
    ]]

    # Save result
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"✅ The event log with event_id has been saved to: {output_csv}")

    print("Note: Each event_id is a unique identifier that includes appliance name, date, and event index.")
    print("Here are the first 10 rows of the result:")
    print(df.head(10))

    return df










# # import pandas as pd
# # import os

# # def add_event_id(input_csv: str, output_csv: str) -> pd.DataFrame:
# #     if not os.path.isfile(input_csv):
# #         raise FileNotFoundError(f"❌ 输入文件不存在：{input_csv}")

# #     df = pd.read_csv(input_csv, parse_dates=["start_time", "end_time"])

# #     # 添加日期字段
# #     df["date"] = df["start_time"].dt.date.astype(str)

# #     # 为每个 appliance_name + date 的组合生成累加索引
# #     df["event_index"] = df.groupby(["appliance_name", "date"]).cumcount() + 1

# #     # 生成 event_id，例如：Washer_2024-06-01_01
# #     df["event_id"] = (
# #         df["appliance_name"].str.replace(" ", "_") + "_" +
# #         df["date"] + "_" +
# #         df["event_index"].astype(str).str.zfill(2)
# #     )

# #     # 添加是否可调度标志
# #     df["is_reschedulable"] = df["Shiftability"].apply(
# #         lambda x: True if x.strip().lower() == "shiftable" else False
# #     )

# #     # 重新排列列顺序
# #     df = df[[
# #         "event_id", "appliance_name", "appliance_ID", "Shiftability",
# #         "start_time", "end_time", "duration(min)", "energy(W)", "is_reschedulable"
# #     ]]

# #     # 保存结果
# #     os.makedirs(os.path.dirname(output_csv), exist_ok=True)
# #     df.to_csv(output_csv, index=False)
# #     print(f"✅ 含 event_id 的日志表已保存至：{output_csv}")
# #     return df


# import pandas as pd
# import os

# def add_event_id(
#     input_csv: str = "./output/02_event_segments/02_appliance_event_segments.csv",
#     output_csv: str = "./output/02_event_segments/02_appliance_event_segments_id.csv"
# ) -> pd.DataFrame:
#     print(" 接下来我们将对所有识别出的事件添加独特的标识 event_id...")
#     if not os.path.isfile(input_csv):
#         raise FileNotFoundError(f"❌ 输入文件不存在：{input_csv}")
    

#     df = pd.read_csv(input_csv, parse_dates=["start_time", "end_time"])

#     # 添加日期字段
#     df["date"] = df["start_time"].dt.date.astype(str)

#     # 为每个 appliance_name + date 的组合生成累加索引
#     df["event_index"] = df.groupby(["appliance_name", "date"]).cumcount() + 1

#     # 生成 event_id，例如：Washer_2024-06-01_01
#     df["event_id"] = (
#         df["appliance_name"].str.replace(" ", "_") + "_" +
#         df["date"] + "_" +
#         df["event_index"].astype(str).str.zfill(2)
#     )

#     # 添加是否可调度标志
#     df["is_reschedulable"] = df["Shiftability"].apply(
#         lambda x: True if x.strip().lower() == "shiftable" else False
#     )

#     # 重新排列列顺序
#     df = df[[ 
#         "event_id", "appliance_name", "appliance_ID", "Shiftability",
#         "start_time", "end_time", "duration(min)", "energy(W)", "is_reschedulable"
#     ]]

#     # 保存结果
#     os.makedirs(os.path.dirname(output_csv), exist_ok=True)
#     df.to_csv(output_csv, index=False)
#     print(f"✅ 含 event_id 的日志表已保存至：{output_csv}")
    
#     print("请注意：event_id 是唯一的标识符，包含了电器名称、日期和事件索引。")
#     print("我将为你展示前10条数据结果。")
#     print(df.head(10))  # 显示前5行数据以验证结果

#     return df










