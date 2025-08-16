

import os
import json
import pandas as pd
from datetime import datetime

def time_to_minutes(time_str):
    """将时间字符串转换为分钟数"""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m

def get_price_levels(tariff_config, tariff_name):
    """获取电价等级信息，返回按价格排序的等级"""
    config_key = list(tariff_config.keys())[0] if len(tariff_config) == 1 else tariff_name
    tariff_plan = tariff_config[config_key]

    if tariff_plan.get("type") == "flat":
        return {"levels": [], "time_blocks": []}

    # 获取时间块
    time_blocks = []
    if "time_blocks" in tariff_plan:
        time_blocks = tariff_plan["time_blocks"]
    elif "seasonal_rates" in tariff_plan:
        time_blocks = tariff_plan["seasonal_rates"]["summer"]["time_blocks"]
    elif "periods" in tariff_plan:
        time_blocks = [{"start": p["start"], "end": p["end"], "rate": p["rate"]}
                      for p in tariff_plan["periods"]]

    # 按价格排序，获取价格等级
    unique_rates = sorted(set(block["rate"] for block in time_blocks))
    rate_to_level = {rate: idx for idx, rate in enumerate(unique_rates)}

    # 为每个时间块添加等级信息
    for block in time_blocks:
        block["price_level"] = rate_to_level[block["rate"]]

    return {
        "levels": unique_rates,  # [0.15, 0.25, 0.35, 0.45]
        "time_blocks": time_blocks,
        "min_level": 0,  # 最低价格等级
        "max_level": len(unique_rates) - 1  # 最高价格等级
    }

def get_seasonal_price_levels(tariff_config, tariff_name, month):
    """获取特定月份的季节性电价等级信息"""
    config_key = list(tariff_config.keys())[0] if len(tariff_config) == 1 else tariff_name
    tariff_plan = tariff_config[config_key]

    if "seasonal_rates" not in tariff_plan:
        return get_price_levels(tariff_config, tariff_name)

    # 确定月份属于哪个季节
    time_blocks = []
    for season_name, season_data in tariff_plan["seasonal_rates"].items():
        if month in season_data["months"]:
            time_blocks = season_data["time_blocks"]
            break

    if not time_blocks:
        # 如果没有找到对应季节，使用夏季作为默认
        time_blocks = tariff_plan["seasonal_rates"]["summer"]["time_blocks"]

    # 按价格排序，获取价格等级
    unique_rates = sorted(set(block["rate"] for block in time_blocks))
    rate_to_level = {rate: idx for idx, rate in enumerate(unique_rates)}

    # 为每个时间块添加等级信息
    for block in time_blocks:
        block["price_level"] = rate_to_level[block["rate"]]

    return {
        "levels": unique_rates,
        "time_blocks": time_blocks,
        "min_level": 0,
        "max_level": len(unique_rates) - 1
    }

def get_event_price_profile(start_time, end_time, price_info):
    """分析事件在各价格等级的时间分布"""
    if not price_info["time_blocks"]:
        return {}
        
    event_start_min = start_time.hour * 60 + start_time.minute
    event_end_min = end_time.hour * 60 + end_time.minute
    
    # 确保事件在同一天内（不处理跨天事件）
    if event_end_min < event_start_min:
        event_end_min += 1440  # 加一天的分钟数
    
    level_minutes = {}
    
    for block in price_info["time_blocks"]:
        block_start = time_to_minutes(block["start"])
        block_end = time_to_minutes(block["end"])
        level = block["price_level"]
        
        # 处理跨天的时间块（如Economy_7: 00:30-07:30实际是前一天23:30-07:30）
        if block_end <= block_start:
            # 跨天时间块，分成两段处理
            # 第一段：block_start 到 1440 (24:00)
            overlap_start_1 = max(event_start_min, block_start)
            overlap_end_1 = min(event_end_min, 1440)
            if overlap_start_1 < overlap_end_1:
                overlap_minutes_1 = overlap_end_1 - overlap_start_1
                level_minutes[level] = level_minutes.get(level, 0) + overlap_minutes_1
            
            # 第二段：0 (00:00) 到 block_end
            overlap_start_2 = max(event_start_min, 0)
            overlap_end_2 = min(event_end_min, block_end)
            if overlap_start_2 < overlap_end_2:
                overlap_minutes_2 = overlap_end_2 - overlap_start_2
                level_minutes[level] = level_minutes.get(level, 0) + overlap_minutes_2
        else:
            # 正常时间块
            overlap_start = max(event_start_min, block_start)
            overlap_end = min(event_end_min, block_end)
            
            if overlap_start < overlap_end:
                overlap_minutes = overlap_end - overlap_start
                level_minutes[level] = level_minutes.get(level, 0) + overlap_minutes
    
    # 如果没有找到重叠，使用fallback机制
    if not level_minutes:
        # 尝试使用事件开始时间的价格等级
        fallback_level = get_time_price_level(start_time, price_info)
        if fallback_level >= 0:
            event_duration = event_end_min - event_start_min
            if event_duration > 1440:  # 防止跨天计算错误
                event_duration = int((end_time - start_time).total_seconds() / 60)
            level_minutes[fallback_level] = event_duration
        else:
            # 最后的fallback：使用最低价格等级
            event_duration = int((end_time - start_time).total_seconds() / 60)
            level_minutes[price_info["min_level"]] = event_duration
    
    # Ensure all price levels are represented in the result, even if 0 minutes
    complete_level_minutes = {}
    for level in range(price_info["min_level"], price_info["max_level"] + 1):
        complete_level_minutes[level] = level_minutes.get(level, 0)

    return complete_level_minutes

def get_time_price_level(timestamp, price_info):
    """获取指定时间点的价格等级"""
    if not price_info["time_blocks"]:
        return price_info.get("min_level", 0)
        
    time_minutes = timestamp.hour * 60 + timestamp.minute
    
    for block in price_info["time_blocks"]:
        block_start = time_to_minutes(block["start"])
        block_end = time_to_minutes(block["end"])
        
        # 处理跨天的时间块
        if block_end <= block_start:
            # 跨天情况：检查是否在后半段(00:00-block_end)或前半段(block_start-1440)
            if time_minutes < block_end or time_minutes >= block_start:
                return block["price_level"]
        else:
            # 正常情况
            if block_start <= time_minutes < block_end:
                return block["price_level"]
    
    # 如果没有找到匹配的时间块，返回最低价格等级
    return price_info.get("min_level", 0)

def should_keep_for_rescheduling(level_minutes, price_info, threshold_minutes=5):
    """判断事件是否值得调度优化 - 修正后的逻辑"""
    if not level_minutes:
        return False

    # 修正后的TOU过滤逻辑：
    # 1. 计算事件在各个非最低价格等级的总持续时间
    high_price_total_minutes = sum(minutes for level, minutes in level_minutes.items()
                                  if level > price_info["min_level"])

    # 2. 如果事件在高价格区间的持续时间 >= 阈值，值得调度
    if high_price_total_minutes >= threshold_minutes:
        return True

    # 3. 如果事件完全在最低价格等级，不值得调度（已经最优）
    if len(level_minutes) == 1 and price_info["min_level"] in level_minutes:
        return False

    # 4. 如果事件在高价格区间的时间 < 阈值，不值得调度
    # （即使有高价格区间，但时间太短，调度成本大于收益）
    return False

def should_keep_for_tou_rescheduling(level_minutes, price_info, threshold_minutes=5):
    """
    TOU filtering logic: Determine if events are worth rescheduling
    Keep events that have >= 5 minutes in non-lowest price periods

    🎯 改进版本：考虑绝对价格差异，而不仅仅是相对等级
    """
    if not level_minutes:
        return False

    # TOU filtering logic: determine if worth rescheduling
    # 1. Calculate event duration in lowest price level (Level 0)
    low_price_minutes = level_minutes.get(price_info["min_level"], 0)
    total_minutes = sum(level_minutes.values())

    # 2. If event runs entirely in lowest price period, not worth rescheduling
    if low_price_minutes == total_minutes:
        return False

    # 🎯 改进：计算加权价格差异，而不仅仅看等级
    lowest_price = price_info["levels"][price_info["min_level"]]

    # 计算事件在高价格时段的加权时间和价格差异
    high_price_weighted_minutes = 0
    for level, minutes in level_minutes.items():
        if level > price_info["min_level"]:
            current_price = price_info["levels"][level]
            price_diff = current_price - lowest_price
            # 价格差异越大，权重越高
            high_price_weighted_minutes += minutes * (price_diff / lowest_price)

    # 3. 如果加权高价格时间 >= 阈值，值得调度
    # 这样可以更好地处理季节性价格差异
    if high_price_weighted_minutes >= threshold_minutes * 0.1:  # 降低阈值，因为使用了加权
        return True

    # 4. 备用逻辑：如果在非最低价格等级的时间 >= 阈值，也值得调度
    non_low_price_minutes = sum(minutes for level, minutes in level_minutes.items()
                               if level > price_info["min_level"])

    if non_low_price_minutes >= threshold_minutes:
        return True

    # 5. Otherwise, rescheduling benefit too small, not worth it
    return False

def process_and_mask_events(
    event_csv_path,
    constraint_json_path,
    tariff_name="Economy_7",
    tariff_config_path=None,
    output_dir="./output/04_TOU_filter/",
    house_id="house1"
):
    # Auto-detect tariff config path if not provided
    if tariff_config_path is None:
        # For California TOU_D, use specific config file
        if tariff_name == "TOU_D":
            possible_paths = [
                "./config/TOU_D.json",
                "../config/TOU_D.json",
                "../Agent_V2/config/TOU_D.json",
                "./Agent_V2/config/TOU_D.json",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "TOU_D.json")
            ]
        elif tariff_name in ["Germany_Variable", "Germany_Variable_Base"]:
            # For Germany tariffs, use specific config file
            possible_paths = [
                "./config/Germany_Variable.json",
                "../config/Germany_Variable.json",
                "../Agent_V2/config/Germany_Variable.json",
                "./Agent_V2/config/Germany_Variable.json",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "Germany_Variable.json")
            ]
        else:
            # For UK tariffs, use general config file
            possible_paths = [
                "./config/tariff_config.json",
                "../config/tariff_config.json",
                "../Agent_V2/config/tariff_config.json",
                "./Agent_V2/config/tariff_config.json",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tariff_config.json")
            ]

        for path in possible_paths:
            if os.path.exists(path):
                tariff_config_path = path
                break
        if tariff_config_path is None:
            if tariff_name == "TOU_D":
                tariff_config_path = "./config/TOU_D.json"
            elif tariff_name in ["Germany_Variable", "Germany_Variable_Base"]:
                tariff_config_path = "./config/Germany_Variable.json"
            else:
                tariff_config_path = "./config/tariff_config.json"

    # 加载事件数据 - 从最小持续时间过滤器的输出
    df = pd.read_csv(event_csv_path, parse_dates=["start_time", "end_time"])
    df["is_reschedulable"] = df["is_reschedulable"].astype(bool)

    # TOU过滤器只处理is_reschedulable=True的事件
    # 提取这些可调度事件进行TOU分析
    reschedulable_events = df[df["is_reschedulable"] == True].copy()

    # 统计输入数据
    input_reschedulable = len(reschedulable_events)

    print(f"📊 TOU Filter Processing:")
    print(f"  • Extracted is_reschedulable=True events from P043 output: {input_reschedulable:,}")
    print(f"  • Will perform TOU price analysis on these events")

    # Load constraint dictionary
    with open(constraint_json_path, "r", encoding="utf-8") as f:
        constraint_dict = json.load(f)

    # Load tariff configuration
    with open(tariff_config_path, "r", encoding="utf-8") as f:
        tariff_config = json.load(f)

    if tariff_name not in tariff_config:
        raise ValueError(f"❌ Tariff configuration not found for: {tariff_name}")

    # TOU filter core logic: analyze price characteristics of reschedulable events
    # Determine if these events are worth time-shifting optimization

    print(f"🔄 Analyzing price characteristics of {input_reschedulable:,} reschedulable events...")
    print(f"📋 Filtering criteria:")
    print(f"  • Events running entirely in lowest price period (Level 0) → not worth rescheduling")
    print(f"  • Events with <5 minutes in non-lowest price periods → rescheduling benefit too small")

    # Create output DataFrame containing only reschedulable events
    output_df = reschedulable_events.copy()

    # Step 1: Price level analysis based on scheduling value
    # For seasonal tariffs like TOU_D, process events by month

    # Initialize all price-related columns
    output_df["price_level_profile"] = ""
    output_df["primary_price_level"] = -1
    output_df["start_price_level"] = -1
    output_df["end_price_level"] = -1
    output_df["optimization_potential"] = 0.0

    # Check if this is a seasonal tariff
    temp_price_info = get_price_levels(tariff_config, tariff_name)

    # Check if tariff has seasonal rates
    config_key = list(tariff_config.keys())[0] if len(tariff_config) == 1 else tariff_name
    is_seasonal = "seasonal_rates" in tariff_config[config_key]

    if temp_price_info["levels"]:  # Only filter when there are multiple price levels
        if is_seasonal:
            # For seasonal tariffs, process events by month
            print(f"🌍 Processing seasonal tariff {tariff_name} by month...")

            # Group events by month
            output_df["month"] = output_df["start_time"].dt.month
            months_in_data = output_df["month"].unique()

            for month in months_in_data:
                month_events = output_df[output_df["month"] == month]
                if len(month_events) == 0:
                    continue

                print(f"📅 Processing month {month}: {len(month_events)} events")

                # Get price info for this specific month
                price_info = get_seasonal_price_levels(tariff_config, tariff_name, month)

                for idx, row in month_events.iterrows():
                    try:
                        # Mark price levels for start and end times
                        start_level = get_time_price_level(row["start_time"], price_info)
                        end_level = get_time_price_level(row["end_time"], price_info)
                        output_df.at[idx, "start_price_level"] = start_level
                        output_df.at[idx, "end_price_level"] = end_level

                        # Analyze event's price level distribution
                        level_minutes = get_event_price_profile(
                            row["start_time"], row["end_time"], price_info
                        )

                        # Update DataFrame - ensure all records have values
                        output_df.at[idx, "price_level_profile"] = json.dumps(level_minutes) if level_minutes else "{}"

                        if level_minutes:
                            primary_level = max(level_minutes.keys(), key=lambda x: level_minutes[x])
                            output_df.at[idx, "primary_price_level"] = primary_level
                            output_df.at[idx, "optimization_potential"] = primary_level / price_info["max_level"]

                            # TOU filtering logic: determine if event is worth rescheduling
                            should_reschedule = should_keep_for_tou_rescheduling(level_minutes, price_info, threshold_minutes=5)
                            if not should_reschedule:
                                output_df.at[idx, "is_reschedulable"] = False
                        else:
                            # Use default values if no price distribution found
                            output_df.at[idx, "primary_price_level"] = price_info["min_level"]
                            output_df.at[idx, "optimization_potential"] = 0.0
                            output_df.at[idx, "price_level_profile"] = "{}"

                    except Exception as e:
                        print(f"⚠️ Error processing event {row.get('event_id', idx)}: {e}")
                        # Use safe default values on error
                        output_df.at[idx, "price_level_profile"] = "{}"
                        output_df.at[idx, "primary_price_level"] = price_info["min_level"]
        else:
            # For non-seasonal tariffs, process all events with same price structure
            price_info = temp_price_info
            for idx, row in output_df.iterrows():
                try:
                    # Mark price levels for start and end times
                    start_level = get_time_price_level(row["start_time"], price_info)
                    end_level = get_time_price_level(row["end_time"], price_info)
                    output_df.at[idx, "start_price_level"] = start_level
                    output_df.at[idx, "end_price_level"] = end_level

                    # Analyze event's price level distribution
                    level_minutes = get_event_price_profile(
                        row["start_time"], row["end_time"], price_info
                    )

                    # Update DataFrame - ensure all records have values
                    output_df.at[idx, "price_level_profile"] = json.dumps(level_minutes) if level_minutes else "{}"

                    if level_minutes:
                        primary_level = max(level_minutes.keys(), key=lambda x: level_minutes[x])
                        output_df.at[idx, "primary_price_level"] = primary_level
                        output_df.at[idx, "optimization_potential"] = primary_level / price_info["max_level"]

                        # TOU filtering logic: determine if event is worth rescheduling
                        should_reschedule = should_keep_for_tou_rescheduling(level_minutes, price_info, threshold_minutes=5)
                        if not should_reschedule:
                            output_df.at[idx, "is_reschedulable"] = False
                    else:
                        # Use default values if no price distribution found
                        output_df.at[idx, "primary_price_level"] = price_info["min_level"]
                        output_df.at[idx, "optimization_potential"] = 0.0
                        output_df.at[idx, "price_level_profile"] = "{}"

                except Exception as e:
                    print(f"⚠️ Error processing event {row.get('event_id', idx)}: {e}")
                    # Use safe default values on error
                    output_df.at[idx, "price_level_profile"] = "{}"
                    output_df.at[idx, "primary_price_level"] = price_info["min_level"]
                    output_df.at[idx, "start_price_level"] = price_info["min_level"]
                    output_df.at[idx, "end_price_level"] = price_info["min_level"]
                    output_df.at[idx, "optimization_potential"] = 0.0
    else:
        # 平价电价情况
        output_df["price_level_profile"] = "{}"
        output_df["primary_price_level"] = 0
        output_df["start_price_level"] = 0
        output_df["end_price_level"] = 0
        output_df["optimization_potential"] = 0.0

    # Add price level description when saving results
    if temp_price_info["levels"]:
        level_mapping = {i: f"Level_{i}({rate})" for i, rate in enumerate(temp_price_info["levels"])}
        print(f"📊 Price level mapping for {tariff_name}:")
        for level, desc in level_mapping.items():
            print(f"   {desc}")

    # Save results - using new path structure
    # output_dir/{tariff_type}/{tariff_plan}/house1/tou_filtered_house1_{tariff_plan}.csv
    # Infer tariff_type from tariff_config
    tariff_type_mapping = {
        "Economy_7": "UK",
        "Economy_10": "UK",
        "Germany_Variable": "Germany",
        "TOU_D": "California"
    }
    inferred_tariff_type = tariff_type_mapping.get(tariff_name, "UK")

    # Calculate final statistics
    final_reschedulable = len(output_df[output_df["is_reschedulable"] == True])
    events_filtered_out = input_reschedulable - final_reschedulable
    filter_efficiency = (events_filtered_out / input_reschedulable * 100) if input_reschedulable > 0 else 0

    # Output statistics
    print(f"📊 TOU filtering statistics for {tariff_name}:")
    print(f"  • Processed reschedulable events: {input_reschedulable:,}")
    print(f"  • Final reschedulable events: {final_reschedulable:,}")
    print(f"  • Events filtered out by TOU: {events_filtered_out:,}")
    print(f"  • TOU filtering efficiency: {filter_efficiency:.1f}%")
    print(f"  • Note: Filtered out events not worth rescheduling (entirely in Level 0 or <5min in non-Level 0 periods)")

    house_output_dir = os.path.join(output_dir, inferred_tariff_type, tariff_name, house_id)
    os.makedirs(house_output_dir, exist_ok=True)
    output_path = os.path.join(house_output_dir, f"tou_filtered_{house_id}_{tariff_name}.csv")
    output_df.to_csv(output_path, index=False)
    print(f"✅ Filtered results have been saved to: {output_path}")
    return output_path


def process_single_household_complete_pipeline(
    house_id: str,
    tariff_type: str = "UK",
    tariff_plans: list = None,
    min_duration_input_dir: str = None,
    constraints_dir: str = None,
    output_dir: str = None
):
    """Process complete TOU filtering pipeline for a single household"""

    # Auto-detect paths if not provided
    if min_duration_input_dir is None:
        possible_paths = [
            "./output/04_min_duration_filter",
            "../Agent_V2/output/04_min_duration_filter",
            "./Agent_V2/output/04_min_duration_filter",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "04_min_duration_filter")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                min_duration_input_dir = path
                break
        if min_duration_input_dir is None:
            min_duration_input_dir = "./output/04_min_duration_filter"

    if constraints_dir is None:
        possible_paths = [
            "./output/04_user_constraints",
            "../Agent_V2/output/04_user_constraints",
            "./Agent_V2/output/04_user_constraints",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "04_user_constraints")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                constraints_dir = path
                break
        if constraints_dir is None:
            constraints_dir = "./output/04_user_constraints"

    if output_dir is None:
        # Create output directory relative to script location
        script_dir = os.path.dirname(os.path.dirname(__file__))
        output_dir = os.path.join(script_dir, "output", "04_TOU_filter")

    if tariff_plans is None:
        # Default tariff plans for each region
        default_plans = {
            "UK": ["Economy_7", "Economy_10"],
            "Germany": ["Germany_Variable"],
            "California": ["TOU_D"]
        }
        tariff_plans = default_plans.get(tariff_type, ["Economy_7"])

    print(f"🏠 Processing TOU filtering for {house_id.upper()}")
    print(f"📊 Tariff type: {tariff_type}")
    print(f"📋 Tariff plans: {tariff_plans}")

    results = {}

    # 输入文件路径
    event_csv_path = os.path.join(min_duration_input_dir, house_id, f"min_duration_filtered_{house_id}.csv")
    constraint_json_path = os.path.join(constraints_dir, house_id, "appliance_constraints_revise_by_llm.json")

    # 检查输入文件
    if not os.path.exists(event_csv_path):
        print(f"❌ Event file not found: {event_csv_path}")
        return None

    if not os.path.exists(constraint_json_path):
        print(f"❌ Constraint file not found: {constraint_json_path}")
        return None

    # 处理每个电价方案
    for tariff_name in tariff_plans:
        print(f"\n🔄 Processing {tariff_name}...")

        try:
            output_path = process_and_mask_events(
                event_csv_path=event_csv_path,
                constraint_json_path=constraint_json_path,
                tariff_name=tariff_name,
                tariff_config_path=None,  # Let function auto-detect
                output_dir=output_dir,
                house_id=house_id
            )

            results[tariff_name] = {
                "output_file": output_path,
                "status": "success"
            }

            print(f"✅ {tariff_name} completed successfully!")

        except Exception as e:
            print(f"❌ Error processing {tariff_name}: {str(e)}")
            results[tariff_name] = {
                "output_file": None,
                "status": "failed",
                "error": str(e)
            }

    return {
        "house_id": house_id,
        "tariff_type": tariff_type,
        "results": results
    }


def process_batch_households_complete_pipeline(
    house_list: list,
    tariff_type: str = "UK",
    tariff_plans: list = None,
    min_duration_input_dir: str = None,
    constraints_dir: str = None,
    output_dir: str = None
):
    """Process complete TOU filtering pipeline for multiple households"""

    # Auto-detect paths if not provided
    if min_duration_input_dir is None:
        possible_paths = [
            "./output/04_min_duration_filter",
            "../Agent_V2/output/04_min_duration_filter",
            "./Agent_V2/output/04_min_duration_filter",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "04_min_duration_filter")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                min_duration_input_dir = path
                break
        if min_duration_input_dir is None:
            min_duration_input_dir = "./output/04_min_duration_filter"

    if constraints_dir is None:
        possible_paths = [
            "./output/04_user_constraints",
            "../Agent_V2/output/04_user_constraints",
            "./Agent_V2/output/04_user_constraints",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "04_user_constraints")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                constraints_dir = path
                break
        if constraints_dir is None:
            constraints_dir = "./output/04_user_constraints"

    if output_dir is None:
        # Create output directory relative to script location
        script_dir = os.path.dirname(os.path.dirname(__file__))
        output_dir = os.path.join(script_dir, "output", "04_TOU_filter")

    if tariff_plans is None:
        # Default tariff plans for each region
        default_plans = {
            "UK": ["Economy_7", "Economy_10"],
            "Germany": ["Germany_Variable"],
            "California": ["TOU_D"]
        }
        tariff_plans = default_plans.get(tariff_type, ["Economy_7"])

    print(f"🚀 Starting batch TOU filtering...")
    print(f"🏠 Target households: {len(house_list)}")
    print(f"📊 Tariff type: {tariff_type}")
    print(f"📋 Tariff plans: {tariff_plans}")
    print("=" * 80)

    results = {}
    failed_houses = []

    for i, house_id in enumerate(house_list, 1):
        try:
            print(f"\n[{i}/{len(house_list)}] Processing {house_id}...")

            result = process_single_household_complete_pipeline(
                house_id=house_id,
                tariff_type=tariff_type,
                tariff_plans=tariff_plans,
                min_duration_input_dir=min_duration_input_dir,
                constraints_dir=constraints_dir,
                output_dir=output_dir
            )

            if result:
                results[house_id] = result
                print(f"✅ {house_id} completed successfully!")
            else:
                failed_houses.append(house_id)
                print(f"❌ Failed to process {house_id}")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Generate batch summary
    print(f"\n🎉 Batch TOU filtering completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for house in failed_houses:
            print(f"  - {house}")

    # Generate detailed results table
    if results:
        generate_batch_results_table(results, tariff_type)

    return results


def generate_batch_results_table(results: dict, tariff_type: str):
    """Generate summary tables for batch processing results"""
    import pandas as pd

    print(f"\n📊 Batch TOU Filtering Results Summary - {tariff_type}")
    print("=" * 100)

    # Collect data for each tariff plan
    tariff_plans = set()
    for result in results.values():
        if result and 'results' in result:
            tariff_plans.update(result['results'].keys())

    tariff_plans = sorted(list(tariff_plans))

    # Generate table for each tariff plan
    for plan_name in tariff_plans:
        print(f"\n📋 {plan_name} Results:")
        print("-" * 80)

        table_data = []

        for house_id, result in results.items():
            if result and 'results' in result and plan_name in result['results']:
                plan_result = result['results'][plan_name]

                if plan_result['status'] == 'success':
                    # Read the output file to get statistics
                    try:
                        output_file = plan_result['output_file']
                        df = pd.read_csv(output_file)

                        total_events = len(df)
                        final_reschedulable = len(df[df['is_reschedulable'] == True])

                        # 获取通过最小持续时间过滤的可调度事件数量
                        min_duration_file = f"./output/04_min_duration_filter/{house_id}/min_duration_filtered_{house_id}.csv"
                        if os.path.exists(min_duration_file):
                            min_df = pd.read_csv(min_duration_file)
                            # TOU过滤器处理的是通过最小持续时间过滤的可调度事件
                            input_reschedulable = len(min_df[min_df['is_reschedulable'] == True])
                        else:
                            input_reschedulable = 0

                        events_filtered_out = input_reschedulable - final_reschedulable
                        filter_efficiency = (events_filtered_out / input_reschedulable * 100) if input_reschedulable > 0 else 0

                        table_data.append({
                            'House_ID': house_id,
                            'Total_Events': total_events,
                            'Input_Reschedulable': input_reschedulable,
                            'Final_Reschedulable': final_reschedulable,
                            'Events_Filtered_Out': events_filtered_out,
                            'Filter_Efficiency_%': round(filter_efficiency, 1)
                        })

                    except Exception as e:
                        print(f"⚠️ Error reading results for {house_id}: {e}")
                        table_data.append({
                            'House_ID': house_id,
                            'Total_Events': 'Error',
                            'Input_Reschedulable': 'Error',
                            'Final_Reschedulable': 'Error',
                            'Events_Filtered_Out': 'Error',
                            'Filter_Efficiency_%': 'Error'
                        })
                else:
                    table_data.append({
                        'House_ID': house_id,
                        'Total_Events': 'Failed',
                        'Input_Reschedulable': 'Failed',
                        'Final_Reschedulable': 'Failed',
                        'Events_Filtered_Out': 'Failed',
                        'Filter_Efficiency_%': 'Failed'
                    })

        if table_data:
            # Sort table data by House_ID numerically (house1, house2, ..., house21)
            def sort_key(item):
                house_id = item['House_ID']
                if house_id.startswith('house'):
                    try:
                        return int(house_id[5:])  # Extract number after 'house'
                    except ValueError:
                        return 999  # Put invalid house IDs at the end
                return 999

            table_data.sort(key=sort_key)

            # Create and display table
            df_table = pd.DataFrame(table_data)
            print(df_table.to_string(index=False, formatters={
                'Total_Events': lambda x: f'{x:,}' if isinstance(x, int) else str(x),
                'Input_Reschedulable': lambda x: f'{x:,}' if isinstance(x, int) else str(x),
                'Final_Reschedulable': lambda x: f'{x:,}' if isinstance(x, int) else str(x),
                'Events_Filtered_Out': lambda x: f'{x:,}' if isinstance(x, int) else str(x)
            }))

            # Calculate summary statistics for successful entries
            successful_data = [row for row in table_data if isinstance(row['Total_Events'], int)]
            if successful_data:
                total_houses = len(successful_data)
                total_events = sum(row['Total_Events'] for row in successful_data)
                total_input = sum(row['Input_Reschedulable'] for row in successful_data)
                total_final = sum(row['Final_Reschedulable'] for row in successful_data)
                total_filtered = sum(row['Events_Filtered_Out'] for row in successful_data)
                avg_efficiency = sum(row['Filter_Efficiency_%'] for row in successful_data) / total_houses

                print(f"\n📊 {plan_name} Summary:")
                print(f"  • Successfully processed: {total_houses} households")
                print(f"  • Total events: {total_events:,}")
                print(f"  • Input reschedulable events: {total_input:,}")
                print(f"  • Final reschedulable events: {total_final:,}")
                print(f"  • Events filtered out by TOU: {total_filtered:,}")
                print(f"  • Average TOU filtering efficiency: {avg_efficiency:.1f}%")
        else:
            print("No data available for this tariff plan.")

    print("=" * 100)


def get_available_houses(min_duration_dir: str = None) -> list:
    """Get available houses from min duration filter output directory"""
    available_houses = []

    # Auto-detect the correct path
    if min_duration_dir is None:
        # Try different possible paths
        possible_paths = [
            "./output/04_min_duration_filter",  # Current directory
            "../Agent_V2/output/04_min_duration_filter",  # If running from TimeSeries
            "./Agent_V2/output/04_min_duration_filter",  # If running from TimeSeries
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "04_min_duration_filter")  # Relative to script
        ]

        min_duration_dir = None
        for path in possible_paths:
            if os.path.exists(path):
                min_duration_dir = path
                break

        if min_duration_dir is None:
            print(f"❌ Could not find min_duration_filter directory in any of these locations:")
            for path in possible_paths:
                print(f"  - {os.path.abspath(path)}")
            # Fallback to a default list
            return [f"house{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]]

    try:
        if os.path.exists(min_duration_dir):
            print(f"📁 Scanning for houses in: {os.path.abspath(min_duration_dir)}")
            # Get all subdirectories that start with 'house'
            for item in os.listdir(min_duration_dir):
                item_path = os.path.join(min_duration_dir, item)
                if os.path.isdir(item_path) and item.startswith('house'):
                    # Check if the required min duration filtered file exists
                    expected_file = os.path.join(item_path, f"min_duration_filtered_{item}.csv")
                    if os.path.exists(expected_file):
                        available_houses.append(item)

            available_houses.sort()  # Sort for consistent ordering
            print(f"✅ Found {len(available_houses)} houses with min duration filtered files")

        if not available_houses:
            print(f"⚠️ No houses found in {min_duration_dir}")
            # Fallback to a default list if no houses found
            available_houses = [f"house{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]]

    except Exception as e:
        print(f"❌ Error scanning for available houses: {str(e)}")
        # Fallback to a default list
        available_houses = [f"house{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]]

    return available_houses


def main():
    """Main function for direct execution of TOU filtering"""
    print("🚀 Agent V2 - TOU Optimization Event Filter")
    print("=" * 70)

    print("Please select processing mode:")
    print("1. Single household processing (Default)")
    print("2. Batch processing")

    try:
        choice = input("Enter your choice (1-2) [Default: 1]: ").strip()
        if not choice:
            choice = "1"

        # Select tariff type
        print("\nSelect tariff type:")
        print("1. UK (Default)")
        print("2. Germany")
        print("3. California")

        tariff_choice = input("Enter your choice (1-3) [Default: 1]: ").strip()
        if not tariff_choice:
            tariff_choice = "1"

        tariff_map = {"1": "UK", "2": "Germany", "3": "California"}
        tariff_type = tariff_map.get(tariff_choice, "UK")

        # Get available houses from min duration filter output
        available_houses = get_available_houses()

        if choice == "1":
            # Single household mode
            print(f"\n📋 Available households: {available_houses}")
            house_input = input("Enter house ID (e.g., house1) [Default: house1]: ").strip()
            if not house_input:
                house_input = "house1"

            if house_input not in available_houses:
                print(f"❌ House {house_input} not found in configuration")
                return

            # Process single household
            result = process_single_household_complete_pipeline(house_input, tariff_type)

            if result:
                print(f"\n✅ Processing completed successfully!")
                print(f"📊 Results for {result['tariff_type']} tariffs:")

                for plan_name, plan_result in result['results'].items():
                    if plan_result['status'] == 'success':
                        print(f"  ✅ {plan_name}: {plan_result['output_file']}")
                    else:
                        print(f"  ❌ {plan_name}: {plan_result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Processing failed")

        elif choice == "2":
            # Batch processing mode
            print(f"\n📋 Available households: {len(available_houses)} houses")
            print("Select batch processing mode:")
            print("1. Process first 3 households")
            print("2. Process all households")
            print("3. Custom selection")

            batch_choice = input("Enter your choice (1-3) [Default: 1]: ").strip()
            if not batch_choice:
                batch_choice = "1"

            if batch_choice == "1":
                selected_houses = available_houses[:3]
            elif batch_choice == "2":
                selected_houses = available_houses
            elif batch_choice == "3":
                print(f"Available houses: {available_houses}")
                house_input = input("Enter house IDs separated by commas: ").strip()
                selected_houses = [h.strip() for h in house_input.split(',') if h.strip() in available_houses]
                if not selected_houses:
                    print("❌ No valid houses selected")
                    return
            else:
                print("❌ Invalid choice")
                return

            print(f"🎯 Selected houses: {selected_houses}")

            # Process batch
            results = process_batch_households_complete_pipeline(selected_houses, tariff_type)

            if results:
                print(f"\n✅ Batch processing completed!")
                print(f"📊 Summary:")
                print(f"  • Total processed: {len(results)} households")
                print(f"  • Tariff type: {tariff_type}")
            else:
                print(f"❌ Batch processing failed")

        else:
            print("❌ Invalid choice")
            return

    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
