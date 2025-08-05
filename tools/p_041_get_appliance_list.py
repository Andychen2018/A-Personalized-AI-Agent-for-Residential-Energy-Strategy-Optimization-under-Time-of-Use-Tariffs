#!/usr/bin/env python3
"""
Agent V2 - Appliance Information Standardization Tool
====================================================

This module provides appliance information standardization functionality:
- Extract appliance lists from event segments
- Handle duplicate appliance names with automatic numbering
- Support multiple tariff types (UK, Germany, California)
- Single household or batch processing
- Generate structured appliance summaries for scheduling modules
"""

import os
import pandas as pd
import json
from typing import Dict, List, Tuple, Optional
from collections import Counter


def handle_duplicate_appliance_names(appliances_data: List[Dict]) -> List[Dict]:
    """
    Handle duplicate appliance names by adding automatic numbering

    Args:
        appliances_data: List of appliance dictionaries with 'appliance_id' and 'appliance_name'

    Returns:
        List of appliance dictionaries with deduplicated names
    """
    name_counts = Counter(item['appliance_name'] for item in appliances_data)
    name_counters = {}

    result = []
    for item in appliances_data:
        original_name = item['appliance_name']

        if name_counts[original_name] > 1:
            # Multiple appliances with same name, add numbering
            if original_name not in name_counters:
                name_counters[original_name] = 1
            else:
                name_counters[original_name] += 1

            # Add number suffix
            new_name = f"{original_name} ({name_counters[original_name]})"
        else:
            # Unique name, keep as is
            new_name = original_name

        # Create new item with updated name
        new_item = item.copy()
        new_item['appliance_name'] = new_name
        new_item['original_name'] = original_name
        result.append(new_item)

    return result


def get_appliance_list_from_csv(
    csv_path: str,
    house_id: str = "",
    tariff_type: str = "UK",
    output_dir: str = "./output/04_appliance_summary"
) -> Optional[Dict]:
    """
    Extract and standardize appliance information from event segments CSV

    Args:
        csv_path: Path to the event segments CSV file
        house_id: House identifier (e.g., "house1")
        tariff_type: Type of tariff ("UK", "Germany", "California")
        output_dir: Output directory for results

    Returns:
        Dictionary containing appliance summary information
    """
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        return None

    try:
        df = pd.read_csv(csv_path)
        print(f"📊 Loaded {len(df)} events from {csv_path}")
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return None

    # Check and standardize column names
    # Handle both 'appliance_id' and 'appliance_ID' formats
    if 'appliance_ID' in df.columns and 'appliance_id' not in df.columns:
        df = df.rename(columns={'appliance_ID': 'appliance_id'})
        print("📝 Standardized column name: appliance_ID → appliance_id")

    required_columns = {"appliance_name", "appliance_id", "is_reschedulable"}
    if not required_columns.issubset(df.columns):
        print(f"❌ Missing required columns: {required_columns - set(df.columns)}")
        print(f"📋 Available columns: {list(df.columns)}")
        return None

    # Extract unique appliances
    appliance_df = df.drop_duplicates(subset=["appliance_id"])[
        ["appliance_id", "appliance_name", "is_reschedulable"]
    ].copy()

    print(f"🔍 Found {len(appliance_df)} unique appliances")

    # Convert to list of dictionaries for duplicate handling
    appliances_data = appliance_df.to_dict('records')

    # Handle duplicate names with automatic numbering
    appliances_data = handle_duplicate_appliance_names(appliances_data)

    # Convert back to DataFrame
    processed_df = pd.DataFrame(appliances_data)

    # Generate statistics
    appliance_counts = df["appliance_name"].value_counts()
    appliance_ids = sorted(processed_df["appliance_id"].unique().tolist())

    # Create mappings
    id_to_name_dict = dict(zip(processed_df["appliance_id"], processed_df["appliance_name"]))
    id_to_original_dict = dict(zip(processed_df["appliance_id"], processed_df["original_name"]))

    # Separate by reschedulability
    reschedulable_df = processed_df[processed_df["is_reschedulable"] == True]
    non_reschedulable_df = processed_df[processed_df["is_reschedulable"] == False]

    reschedulable_ids = sorted(reschedulable_df["appliance_id"].tolist())
    non_reschedulable_ids = sorted(non_reschedulable_df["appliance_id"].tolist())
    reschedulable_names = reschedulable_df["appliance_name"].tolist()
    non_reschedulable_names = non_reschedulable_df["appliance_name"].tolist()

    reschedulable_map = dict(zip(reschedulable_ids, reschedulable_names))
    non_reschedulable_map = dict(zip(non_reschedulable_ids, non_reschedulable_names))

    # Create comprehensive summary
    summary_dict = {
        "house_id": house_id,
        "tariff_type": tariff_type,
        "total_appliances": len(appliance_ids),
        "total_events": len(df),
        "appliance_names": processed_df["appliance_name"].tolist(),
        "appliance_counts": appliance_counts.to_dict(),
        "appliance_ids": appliance_ids,
        "id_to_name": id_to_name_dict,
        "id_to_original_name": id_to_original_dict,
        "reschedulable_ids": reschedulable_ids,
        "reschedulable_names": reschedulable_names,
        "non_reschedulable_ids": non_reschedulable_ids,
        "non_reschedulable_names": non_reschedulable_names,
        "reschedulable_map": reschedulable_map,
        "non_reschedulable_map": non_reschedulable_map,
        "appliance_details": appliances_data
    }

    # Create output directory structure
    if house_id:
        save_dir = os.path.join(output_dir, tariff_type, house_id)
    else:
        save_dir = os.path.join(output_dir, tariff_type)

    os.makedirs(save_dir, exist_ok=True)

    # Save comprehensive summary
    summary_file = os.path.join(save_dir, "appliance_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_dict, f, indent=2, ensure_ascii=False)

    # Save mapping files
    mapping_file = os.path.join(save_dir, "appliance_mappings.json")
    mappings = {
        "id_to_name": id_to_name_dict,
        "id_to_original_name": id_to_original_dict,
        "reschedulable_map": reschedulable_map,
        "non_reschedulable_map": non_reschedulable_map
    }
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)

    # Save detailed appliance list
    appliance_list_file = os.path.join(save_dir, "appliance_list.csv")
    processed_df.to_csv(appliance_list_file, index=False)

    print(f"✅ Appliance summary saved to: {save_dir}")
    print(f"📊 Summary: {len(reschedulable_ids)} reschedulable, {len(non_reschedulable_ids)} non-reschedulable")

    return summary_dict


def batch_get_appliance_lists(
    house_data_dict: dict,
    tariff_type: str = "UK",
    input_dir: str = "./output/02_event_segments/",
    output_dir: str = "./output/04_appliance_summary"
) -> Dict[str, Dict]:
    """
    Batch process appliance lists for multiple households

    Args:
        house_data_dict: Dictionary mapping house_id to house info
        tariff_type: Type of tariff ("UK", "Germany", "California")
        input_dir: Directory containing event segments
        output_dir: Output directory for results

    Returns:
        Dictionary mapping house_id to appliance summary
    """
    results = {}
    failed_houses = []

    print(f"🚀 Starting batch appliance list extraction...")
    print(f"📊 Tariff type: {tariff_type}")
    print(f"🏠 Target households: {len(house_data_dict)}")
    print("=" * 80)

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Processing {house_id}...")

            # Define event segments file path
            event_file = os.path.join(input_dir, house_id, f"02_appliance_event_segments_id_{house_id}.csv")

            if not os.path.exists(event_file):
                print(f"❌ Event file not found: {event_file}")
                failed_houses.append(house_id)
                continue

            # Process appliance list
            summary = get_appliance_list_from_csv(
                csv_path=event_file,
                house_id=house_id,
                tariff_type=tariff_type,
                output_dir=output_dir
            )

            if summary:
                results[house_id] = summary
                print(f"✅ {house_id} completed successfully!")
            else:
                print(f"❌ Failed to process {house_id}")
                failed_houses.append(house_id)

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Generate batch summary
    print(f"\n🎉 Batch appliance list extraction completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for failed_house in failed_houses:
            print(f"  - {failed_house}")

    # Generate overall statistics
    if results:
        print(f"\n📊 Overall Statistics:")
        total_appliances = sum(summary['total_appliances'] for summary in results.values())
        total_events = sum(summary['total_events'] for summary in results.values())
        total_reschedulable = sum(len(summary['reschedulable_ids']) for summary in results.values())
        total_non_reschedulable = sum(len(summary['non_reschedulable_ids']) for summary in results.values())

        print(f"  • Total appliances: {total_appliances}")
        print(f"  • Total events: {total_events:,}")
        print(f"  • Reschedulable appliances: {total_reschedulable}")
        print(f"  • Non-reschedulable appliances: {total_non_reschedulable}")

        # Save batch summary
        batch_summary = {
            "tariff_type": tariff_type,
            "processed_houses": list(results.keys()),
            "failed_houses": failed_houses,
            "total_houses": len(house_data_dict),
            "success_count": len(results),
            "total_appliances": total_appliances,
            "total_events": total_events,
            "total_reschedulable": total_reschedulable,
            "total_non_reschedulable": total_non_reschedulable
        }

        batch_summary_file = os.path.join(output_dir, tariff_type, "batch_summary.json")
        os.makedirs(os.path.dirname(batch_summary_file), exist_ok=True)
        with open(batch_summary_file, "w", encoding="utf-8") as f:
            json.dump(batch_summary, f, indent=2, ensure_ascii=False)

        print(f"📁 Batch summary saved to: {batch_summary_file}")

    print("=" * 80)

    return results


def single_house_appliance_analysis(
    house_id: str,
    tariff_type: str = "UK",
    input_dir: str = "./output/02_event_segments/",
    output_dir: str = "./output/04_appliance_summary"
) -> Optional[Dict]:
    """
    Analyze appliance information for a single household

    Args:
        house_id: House identifier (e.g., "house1")
        tariff_type: Type of tariff ("UK", "Germany", "California")
        input_dir: Directory containing event segments
        output_dir: Output directory for results

    Returns:
        Dictionary containing appliance summary or None if failed
    """
    print(f"🏠 Starting appliance analysis for {house_id.upper()}...")
    print(f"📊 Tariff type: {tariff_type}")
    print("=" * 60)

    # Define event segments file path
    event_file = os.path.join(input_dir, house_id, f"02_appliance_event_segments_id_{house_id}.csv")

    if not os.path.exists(event_file):
        print(f"❌ Event file not found: {event_file}")
        return None

    # Process appliance list
    summary = get_appliance_list_from_csv(
        csv_path=event_file,
        house_id=house_id,
        tariff_type=tariff_type,
        output_dir=output_dir
    )

    if summary:
        print(f"\n🎉 Appliance analysis completed for {house_id.upper()}!")
        print(f"📊 Results:")
        print(f"  • Total appliances: {summary['total_appliances']}")
        print(f"  • Total events: {summary['total_events']:,}")
        print(f"  • Reschedulable: {len(summary['reschedulable_ids'])}")
        print(f"  • Non-reschedulable: {len(summary['non_reschedulable_ids'])}")

        # Display appliance list
        print(f"\n📋 Appliance List:")
        for detail in summary['appliance_details']:
            status = "✅ Reschedulable" if detail['is_reschedulable'] else "❌ Non-reschedulable"
            original_note = f" (originally: {detail['original_name']})" if detail['appliance_name'] != detail['original_name'] else ""
            print(f"  • {detail['appliance_id']}: {detail['appliance_name']}{original_note} - {status}")

        return summary
    else:
        print(f"❌ Failed to analyze appliances for {house_id}")
        return None


if __name__ == "__main__":
    print("🧪 Testing appliance information standardization...")

    # Test duplicate name handling
    print("\n🔧 Testing duplicate name handling:")
    test_data = [
        {'appliance_id': 'Appliance1', 'appliance_name': 'Fridge', 'is_reschedulable': False},
        {'appliance_id': 'Appliance2', 'appliance_name': 'Fridge', 'is_reschedulable': False},
        {'appliance_id': 'Appliance3', 'appliance_name': 'Washing Machine', 'is_reschedulable': True},
        {'appliance_id': 'Appliance4', 'appliance_name': 'Fridge', 'is_reschedulable': False},
        {'appliance_id': 'Appliance5', 'appliance_name': 'Television', 'is_reschedulable': False},
    ]

    result = handle_duplicate_appliance_names(test_data)

    print("Original data:")
    for item in test_data:
        print(f"  {item['appliance_id']}: {item['appliance_name']}")

    print("\nAfter duplicate handling:")
    for item in result:
        print(f"  {item['appliance_id']}: {item['appliance_name']} (original: {item['original_name']})")

    print("\n✅ Duplicate name handling test completed!")

    # Test with real data if available
    test_file = "./output/02_event_segments/house1/02_appliance_event_segments_id_house1.csv"
    if os.path.exists(test_file):
        print(f"\n🔧 Testing with real data: {test_file}")
        summary = get_appliance_list_from_csv(
            csv_path=test_file,
            house_id="house1",
            tariff_type="UK"
        )

        if summary:
            print(f"✅ Real data test completed!")
            print(f"📊 Found {summary['total_appliances']} appliances with {summary['total_events']} events")
        else:
            print("❌ Real data test failed")
    else:
        print(f"\n⚠️  Real data file not found: {test_file}")
        print("Run the event segmentation pipeline first to generate test data.")

    print(f"\n🎯 All tests completed!")
