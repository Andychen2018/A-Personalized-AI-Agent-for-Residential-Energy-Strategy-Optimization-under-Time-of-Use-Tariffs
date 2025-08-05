
# import pandas as pd
# import os
# from typing import Tuple

# def simulate_tariff_cost_detailed(
#     event_csv: str,
#     power_csv: str,
#     output_dir: str = "./output/03_cost_cal"
# ) -> Tuple[pd.DataFrame, pd.DataFrame]:
#     os.makedirs(output_dir, exist_ok=True)

#     # 读取数据
#     power_df = pd.read_csv(power_csv, parse_dates=["Time"])
#     power_df.set_index("Time", inplace=True)

#     run_df = pd.read_csv(event_csv, parse_dates=["start_time", "end_time"])

#     # 名称映射
#     name_to_appliance_id = {
#         "Fridge": "Appliance1", "Refrigerator": "Appliance1",
#         "Chest Freezer": "Appliance2", "Upright Freezer": "Appliance3",
#         "Tumble Dryer": "Appliance4", "Clothes Dryer": "Appliance4",
#         "Washing Machine": "Appliance5", "Dishwasher": "Appliance6",
#         "Computer": "Appliance7", "Computer Site": "Appliance7",
#         "Television": "Appliance8", "Television Site": "Appliance8",
#         "Space Heater": "Appliance9", "Electric Heater": "Appliance9"
#     }

#     run_df["appliance_id"] = run_df["appliance_name"].map(name_to_appliance_id)
#     run_df["label"] = run_df["appliance_id"] + " (" + run_df["appliance_name"] + ")"
#     run_df["month"] = run_df["start_time"].dt.to_period("M").astype(str)

#     # 定义电价模式
#     def get_price_schedule(mode):
#         if mode == "Standard":
#             return [(0, 24, 0.3)]
#         elif mode == "Economy_7":
#             return [(0, 7, 0.15), (7, 24, 0.3)]
#         elif mode == "Economy_10":
#             return [(0, 3, 0.15), (13, 16, 0.15), (20, 23, 0.15),
#                     (3, 13, 0.3), (16, 20, 0.3), (23, 24, 0.3)]
#         else:
#             raise ValueError("Unknown mode")

#     # 单段成本与能耗
#     def compute_cost_and_energy(row, schedule):
#         col = row["appliance_id"]
#         if pd.isna(col) or col not in power_df.columns:
#             return 0.0, 0.0

#         segment = power_df.loc[row["start_time"]:row["end_time"]]
#         if segment.empty or col not in segment.columns:
#             return 0.0, 0.0

#         cost = 0.0
#         energy = 0.0
#         for t, p in segment[col].items():
#             hour = t.hour + t.minute / 60.0
#             price = next((r for s, e, r in schedule if s <= hour < e), 0.3)
#             cost += (p / 1000) * (1 / 60) * price
#             energy += (p / 1000) * (1 / 60)
#         return round(cost, 4), round(energy, 4)

#     # 计算三种电价下的值
#     for mode in ["Standard", "Economy_7", "Economy_10"]:
#         schedule = get_price_schedule(mode)
#         run_df[[f"cost_{mode}", f"energy_{mode}"]] = run_df.apply(
#             lambda row: pd.Series(compute_cost_and_energy(row, schedule)), axis=1
#         )

#     # ------------------------------------------
#     # 汇总：每个电器总费用与能耗
#     summary = run_df.groupby("label")[[
#         "cost_Standard", "cost_Economy_7", "cost_Economy_10",
#         "energy_Standard", "energy_Economy_7", "energy_Economy_10"
#     ]].sum().round(2)
#     summary.loc["Total"] = summary.sum()
#     summary.to_csv(f"{output_dir}/05_appliance_run_costs_summary.csv")

#     # 保存主表
#     run_df.to_csv(f"{output_dir}/03_appliance_run_costs_real.csv", index=False)

#     # ------------------------------------------
#     # 每月总费用与能耗
#     monthly_total = run_df.groupby("month")[[
#         "cost_Standard", "cost_Economy_7", "cost_Economy_10",
#         "energy_Standard", "energy_Economy_7", "energy_Economy_10"
#     ]].sum().reset_index()
#     monthly_total.to_csv(f"{output_dir}/06_monthly_total_summary.csv", index=False)

#     # 每月每电器费用与能耗
#     monthly_by_appliance = run_df.groupby(["appliance_id", "appliance_name", "month"])[[
#         "cost_Standard", "cost_Economy_7", "cost_Economy_10",
#         "energy_Standard", "energy_Economy_7", "energy_Economy_10"
#     ]].sum().reset_index()
#     monthly_by_appliance.to_csv(f"{output_dir}/07_monthly_by_appliance.csv", index=False)

#     # Shiftability 类型聚合
#     if "Shiftability" in run_df.columns:
#         by_shiftability = run_df.groupby("Shiftability")[[
#             "cost_Standard", "cost_Economy_7", "cost_Economy_10",
#             "energy_Standard", "energy_Economy_7", "energy_Economy_10"
#         ]].sum().reset_index()
#         by_shiftability.to_csv(f"{output_dir}/08_cost_by_shiftability.csv", index=False)
#     else:
#         by_shiftability = pd.DataFrame()

#     # 推荐电价策略
#     total_costs = run_df[["cost_Standard", "cost_Economy_7", "cost_Economy_10"]].sum()
#     recommended_tariff = total_costs.idxmin().replace("cost_", "")
#     with open(f"{output_dir}/09_recommended_tariff.txt", "w") as f:
#         f.write(f"Recommended Tariff: {recommended_tariff}\n")

#     # 提示信息
#     print("✅ 成本与用电量分析完成，结果保存至:", output_dir)
#     print("📊 汇总：", summary.tail(1).to_dict())
#     print("🎯 推荐电价方案:", recommended_tariff)

#     return run_df, summary










import json
import pandas as pd
import os
from typing import Tuple, Dict, List
from datetime import datetime, time

def load_tariff_config(tariff_type: str = "UK") -> Dict:
    """
    Load tariff configuration based on tariff type

    Args:
        tariff_type: "UK", "Germany", or "California"

    Returns:
        Dictionary containing tariff configuration
    """
    config_files = {
        "UK": "config/tariff_config.json",
        "Germany": "config/Germany_Variable.json",
        "California": "config/TOU_D.json"
    }

    if tariff_type not in config_files:
        raise ValueError(f"Unsupported tariff type: {tariff_type}. Supported types: {list(config_files.keys())}")

    config_file = config_files[tariff_type]
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Tariff config file not found: {config_file}")

    with open(config_file, "r") as f:
        return json.load(f)


def get_tariff_schedules(tariff_type: str = "UK") -> Dict:
    """
    Get all available tariff schedules for a given tariff type

    Args:
        tariff_type: "UK", "Germany", or "California"

    Returns:
        Dictionary mapping tariff names to their schedules
    """
    config = load_tariff_config(tariff_type)
    schedules = {}

    if tariff_type == "UK":
        # Handle UK tariff config format
        for tariff_name, tariff_config in config.items():
            if tariff_config["type"] == "flat":
                schedules[tariff_name] = [(0, 24, tariff_config["rate"])]
            elif tariff_config["type"] == "time_based":
                schedule = []
                for period in tariff_config["periods"]:
                    start_hour = time.fromisoformat(period["start"]).hour + time.fromisoformat(period["start"]).minute / 60
                    end_hour = time.fromisoformat(period["end"]).hour + time.fromisoformat(period["end"]).minute / 60

                    # Handle overnight periods (e.g., 22:00 to 06:00)
                    if end_hour <= start_hour:
                        end_hour += 24

                    schedule.append((start_hour, end_hour, period["rate"]))
                schedules[tariff_name] = schedule

    elif tariff_type == "Germany":
        # Handle Germany tariff config format
        for tariff_name, tariff_config in config.items():
            if tariff_config["tariff_type"] == "flat":
                schedules[tariff_name] = [(0, 24, tariff_config["rate"])]
            elif tariff_config["tariff_type"] == "TOU":
                schedule = []
                for block in tariff_config["time_blocks"]:
                    # Handle 24:00 as special case
                    start_time = block["start"]
                    end_time = block["end"]

                    if end_time == "24:00":
                        end_hour = 24
                    else:
                        end_time_obj = time.fromisoformat(end_time)
                        end_hour = end_time_obj.hour + end_time_obj.minute / 60

                    start_time_obj = time.fromisoformat(start_time)
                    start_hour = start_time_obj.hour + start_time_obj.minute / 60

                    schedule.append((start_hour, end_hour, block["rate"]))
                schedules[tariff_name] = schedule

    elif tariff_type == "California":
        # Handle California TOU_D format with seasonal rates
        for tariff_name, tariff_config in config.items():
            if tariff_config["tariff_type"] == "flat":
                schedules[tariff_name] = [(0, 24, tariff_config["rate"])]
            elif tariff_config["tariff_type"] == "TOU":
                # For TOU_D, store the complete seasonal configuration
                # We'll handle season selection during cost calculation
                schedules[tariff_name] = {
                    "type": "seasonal",
                    "seasonal_rates": tariff_config["seasonal_rates"]
                }

    return schedules


def simulate_tariff_cost_detailed(
    event_csv: str,
    power_csv: str,
    label_csv: str,
    house_id: str,
    tariff_type: str = "UK",
    output_dir: str = "./output/03_cost_analysis"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simulate tariff costs for different pricing schemes

    Args:
        event_csv: Path to event segments CSV file
        power_csv: Path to power consumption CSV file
        label_csv: Path to appliance shiftability label CSV file
        house_id: House identifier (e.g., "house1")
        tariff_type: Type of tariff ("UK", "Germany", "California")
        output_dir: Output directory for results

    Returns:
        Tuple of (detailed results DataFrame, summary DataFrame)
    """
    # Create house-specific output directory
    house_output_dir = os.path.join(output_dir, tariff_type, house_id)
    os.makedirs(house_output_dir, exist_ok=True)

    print(f"🔍 Processing {house_id.upper()} tariff cost analysis ({tariff_type})...")

    # Load data
    power_df = pd.read_csv(power_csv, parse_dates=["Time"])
    power_df.set_index("Time", inplace=True)

    run_df = pd.read_csv(event_csv, parse_dates=["start_time", "end_time"])

    # Load appliance mapping from shiftability label file
    if not os.path.exists(label_csv):
        raise FileNotFoundError(f"Label file not found: {label_csv}")

    label_df = pd.read_csv(label_csv)
    name_to_appliance_id = dict(zip(label_df["ChineseName"], label_df["ApplianceID"]))

    # Map appliance names to IDs
    run_df["appliance_id"] = run_df["appliance_name"].map(name_to_appliance_id)
    run_df["label"] = run_df["appliance_id"] + " (" + run_df["appliance_name"] + ")"
    run_df["month"] = run_df["start_time"].dt.to_period("M").astype(str)

    # Get tariff schedules for the specified type
    tariff_schedules = get_tariff_schedules(tariff_type)

    print(f"📊 Available tariff schemes for {tariff_type}: {list(tariff_schedules.keys())}")

    # Cost and energy computation function
    def compute_cost_and_energy(row, schedule_info, tariff_name=""):
        """
        Compute cost and energy for a single event row

        Args:
            row: Event row from DataFrame
            schedule_info: Either list of (start_hour, end_hour, rate) tuples or seasonal config dict
            tariff_name: Name of the tariff for seasonal handling

        Returns:
            Tuple of (cost, energy)
        """
        col = row["appliance_id"]
        if pd.isna(col) or col not in power_df.columns:
            return 0.0, 0.0

        segment = power_df.loc[row["start_time"]:row["end_time"]]
        if segment.empty or col not in segment.columns:
            return 0.0, 0.0

        cost = 0.0
        energy = 0.0

        # Handle seasonal tariffs (California TOU_D)
        if isinstance(schedule_info, dict) and schedule_info.get("type") == "seasonal":
            month = row["start_time"].month
            seasonal_rates = schedule_info["seasonal_rates"]

            # Determine season based on month
            season = None
            for season_name, season_config in seasonal_rates.items():
                if month in season_config["months"]:
                    season = season_name
                    break

            if season is None:
                print(f"⚠️ Warning: No season found for month {month}, using winter as default")
                season = "winter"

            # Get the appropriate time blocks for this season
            time_blocks = seasonal_rates[season]["time_blocks"]
            schedule = []
            for block in time_blocks:
                # Handle 24:00 as special case
                start_time = block["start"]
                end_time = block["end"]

                if end_time == "24:00":
                    end_hour = 24
                else:
                    end_time_obj = time.fromisoformat(end_time)
                    end_hour = end_time_obj.hour + end_time_obj.minute / 60

                start_time_obj = time.fromisoformat(start_time)
                start_hour = start_time_obj.hour + start_time_obj.minute / 60

                schedule.append((start_hour, end_hour, block["rate"]))
        else:
            # Regular schedule (list of tuples)
            schedule = schedule_info

        for t, p in segment[col].items():
            hour = t.hour + t.minute / 60.0

            # Find applicable rate for this hour
            price = 0.3  # Default rate
            for s, e, r in schedule:
                if s <= hour < e or (s > e and (hour >= s or hour < e)):  # Handle overnight periods
                    price = r
                    break

            cost += (p / 1000) * (1 / 60) * price  # Convert W to kW, minute to hour
            energy += (p / 1000) * (1 / 60)  # Convert W to kWh

        return round(cost, 4), round(energy, 4)

    # Calculate costs for all available tariff schemes
    cost_columns = []
    energy_columns = []

    for tariff_name, schedule_info in tariff_schedules.items():
        print(f"🔄 Processing tariff: {tariff_name}")

        # Process each tariff scheme
        run_df[[f"cost_{tariff_name}", f"energy_{tariff_name}"]] = run_df.apply(
            lambda row: pd.Series(compute_cost_and_energy(row, schedule_info, tariff_name)), axis=1
        )
        cost_columns.append(f"cost_{tariff_name}")
        energy_columns.append(f"energy_{tariff_name}")

    # ------------------------------------------
    # Summary: Total cost and energy by appliance
    all_columns = cost_columns + energy_columns
    summary = run_df.groupby("label")[all_columns].sum().round(4)
    summary.loc["Total"] = summary.sum()
    summary.to_csv(f"{house_output_dir}/05_appliance_run_costs_summary.csv")

    # Save main results table
    run_df.to_csv(f"{house_output_dir}/03_appliance_run_costs_real.csv", index=False)

    # ------------------------------------------
    # Monthly total cost and energy
    monthly_total = run_df.groupby("month")[all_columns].sum().reset_index()
    monthly_total.to_csv(f"{house_output_dir}/06_monthly_total_summary.csv", index=False)

    # Monthly cost and energy by appliance
    monthly_by_appliance = run_df.groupby(["appliance_id", "appliance_name", "month"])[all_columns].sum().reset_index()
    monthly_by_appliance.to_csv(f"{house_output_dir}/07_monthly_by_appliance.csv", index=False)

    # Shiftability type aggregation
    if "Shiftability" in run_df.columns:
        by_shiftability = run_df.groupby("Shiftability")[all_columns].sum().reset_index()
        by_shiftability.to_csv(f"{house_output_dir}/08_cost_by_shiftability.csv", index=False)
    else:
        by_shiftability = pd.DataFrame()

    # Recommend tariff strategy
    total_costs = run_df[cost_columns].sum()
    recommended_tariff = total_costs.idxmin().replace("cost_", "")

    # Save recommendation
    with open(f"{house_output_dir}/09_recommended_tariff.txt", "w") as f:
        f.write(f"Tariff Type: {tariff_type}\n")
        f.write(f"House ID: {house_id}\n")
        f.write(f"Recommended Tariff: {recommended_tariff}\n")
        f.write(f"Available Tariffs: {list(tariff_schedules.keys())}\n")
        f.write(f"\nTotal Costs Comparison:\n")
        for col in cost_columns:
            tariff_name = col.replace("cost_", "")
            f.write(f"  {tariff_name}: ${total_costs[col]:.2f}\n")

    # Display results
    print(f"✅ Cost and energy analysis completed for {house_id.upper()} ({tariff_type})")
    print(f"� Results saved to: {house_output_dir}")

    # Display detailed cost comparison for all tariffs
    print(f"\n💰 Detailed Cost Comparison for {house_id.upper()}:")
    print("-" * 50)
    for col in cost_columns:
        tariff_name = col.replace("cost_", "")
        cost = total_costs[col]
        is_recommended = (tariff_name == recommended_tariff)
        marker = "🎯 " if is_recommended else "   "
        print(f"{marker}{tariff_name:12s}: ${cost:8.2f}" + (" (Recommended)" if is_recommended else ""))

    print(f"\n🎯 Recommended tariff scheme: {recommended_tariff}")
    print(f"💰 Total cost with recommended tariff: ${total_costs[f'cost_{recommended_tariff}']:.2f}")

    # Calculate savings
    if len(cost_columns) > 1:
        max_cost = max(total_costs[col] for col in cost_columns)
        min_cost = min(total_costs[col] for col in cost_columns)
        savings = max_cost - min_cost
        savings_pct = (savings / max_cost) * 100 if max_cost > 0 else 0
        print(f"💡 Potential savings: ${savings:.2f} ({savings_pct:.1f}%)")

    return run_df, summary


def batch_simulate_tariff_costs(
    house_data_dict: dict,
    tariff_type: str = "UK",
    input_dir: str = "./output/02_event_segments/",
    perception_dir: str = "./output/01_preprocessed/",
    label_dir: str = "./output/02_behavior_modeling/",
    output_dir: str = "./output/03_cost_analysis"
) -> dict:
    """
    Batch simulate tariff costs for multiple households

    Args:
        house_data_dict: Dictionary mapping house_id to house info
        tariff_type: Type of tariff ("UK", "Germany", "California")
        input_dir: Directory containing event segments
        perception_dir: Directory containing perception alignment results
        label_dir: Directory containing appliance labels
        output_dir: Output directory

    Returns:
        Dictionary mapping house_id to result tuple (run_df, summary)
    """
    results = {}
    failed_houses = []

    print(f"🚀 Starting batch tariff cost analysis for {len(house_data_dict)} households...")
    print(f"📊 Tariff type: {tariff_type}")
    print("=" * 80)

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Processing {house_id}...")

            # Define file paths
            event_csv = os.path.join(input_dir, house_id, f"02_appliance_event_segments_id_{house_id}.csv")
            power_csv = os.path.join(perception_dir, house_id, f"01_perception_alignment_result_{house_id}.csv")
            label_csv = os.path.join(label_dir, house_id, f"02_1_appliance_shiftable_label_{house_id}.csv")

            # Check if required files exist
            missing_files = []
            if not os.path.exists(event_csv):
                missing_files.append(f"Event file: {event_csv}")
            if not os.path.exists(power_csv):
                missing_files.append(f"Power file: {power_csv}")
            if not os.path.exists(label_csv):
                missing_files.append(f"Label file: {label_csv}")

            if missing_files:
                print(f"❌ Missing files for {house_id}:")
                for missing_file in missing_files:
                    print(f"  - {missing_file}")
                failed_houses.append(house_id)
                continue

            # Run tariff cost simulation
            run_df, summary = simulate_tariff_cost_detailed(
                event_csv=event_csv,
                power_csv=power_csv,
                label_csv=label_csv,
                house_id=house_id,
                tariff_type=tariff_type,
                output_dir=output_dir
            )

            results[house_id] = (run_df, summary)
            print(f"✅ {house_id} completed successfully!")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Summary
    print(f"\n🎉 Batch tariff cost analysis completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for failed_house in failed_houses:
            print(f"  - {failed_house}")

    # Note: Summary table will be displayed by batch_tariff_analysis function to avoid duplication

    print(f"📁 Results saved in: {output_dir}/{tariff_type}/")

    return results
