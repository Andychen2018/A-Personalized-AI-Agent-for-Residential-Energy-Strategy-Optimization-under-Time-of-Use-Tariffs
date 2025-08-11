import os
import sys

# 导入工具函数
from tools.p_01_perception_alignment import batch_preprocess_specific_houses
from tools.p_02_shiftable_identifier import (
    batch_identify_appliance_shiftability,
    identify_appliance_shiftability_single
)
from tools.p_02_segment_events import (
    batch_run_event_segmentation,
    run_event_segmentation_single
)
from tools.p_02_event_id import (
    batch_add_event_id,
    add_event_id_single
)
# 其他工具暂时注释掉，等需要时再启用
# from tools.llm_proxy import GPTProxyClient
# from tools.p_03_tariff_modeling import simulate_tariff_cost_detailed
# from tools.p_03_energy_summary import summarize_tariff_results_and_visualize


def load_house_appliances_config(config_path: str = "./config/house_appliances.json") -> dict:
    """
    Load house appliances configuration from JSON file

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary mapping house_id to appliance description
    """
    house_appliances = {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # Parse the content line by line
        lines = content.split('\n')
        current_house = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a house header
            if line.startswith('House '):
                house_num = line.split()[1]
                current_house = f"house{house_num}"
            elif current_house and not line.startswith('House '):
                # This is appliance description
                house_appliances[current_house] = line
                current_house = None

        return house_appliances

    except Exception as e:
        print(f"❌ Error loading house appliances config: {str(e)}")
        return {}


def batch_preprocess_target_houses():
    """
    Batch process specified household data - perception alignment step only
    """
    print("🏠 Starting batch processing of specified households' raw data perception...")
    print("=" * 80)

    # Specify target household numbers
    target_houses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]

    # Collect statistics before processing
    import pandas as pd
    processing_stats = []

    print("📊 Collecting original data statistics...")
    for house_num in target_houses:
        input_path = f"/home/deep/TimeSeries/dataset/cleand_data/CLEAN_House{house_num}.csv"
        if os.path.exists(input_path):
            try:
                df = pd.read_csv(input_path)
                original_records = len(df)
                issues_count = (df["Issues"] == 1).sum() if "Issues" in df.columns else 0
                clean_records = original_records - issues_count
                processing_stats.append({
                    'house_num': house_num,
                    'original_records': original_records,
                    'issues_count': issues_count,
                    'clean_records': clean_records,
                    'processed_records': 0,  # Will be updated after processing
                    'status': 'Pending'
                })
            except Exception as e:
                processing_stats.append({
                    'house_num': house_num,
                    'original_records': 0,
                    'issues_count': 0,
                    'clean_records': 0,
                    'processed_records': 0,
                    'status': f'Error: {str(e)}'
                })
        else:
            processing_stats.append({
                'house_num': house_num,
                'original_records': 0,
                'issues_count': 0,
                'clean_records': 0,
                'processed_records': 0,
                'status': 'File not found'
            })

    # Execute batch preprocessing
    results = batch_preprocess_specific_houses(
        house_numbers=target_houses,
        input_dir="/home/deep/TimeSeries/dataset/cleand_data/",
        base_output_dir="./output/01_preprocessed/"
    )

    # Update processing statistics with results
    for stat in processing_stats:
        house_id = f"house{stat['house_num']}"
        if house_id in results:
            # Read processed file to get record count
            try:
                processed_df = pd.read_csv(results[house_id])
                stat['processed_records'] = len(processed_df)
                stat['status'] = 'Success'
            except Exception as e:
                stat['status'] = f'Processing error: {str(e)}'
        elif stat['status'] == 'Pending':
            stat['status'] = 'Failed'

    # Display comprehensive results table
    print("\n" + "=" * 100)
    print("🎉 Batch perception processing completed!")
    print(f"✅ Successfully processed {len(results)} household data")
    print("📋 Processing results summary:")
    print("=" * 100)

    # Create formatted table
    print(f"{'House':<8} {'Original':<12} {'Issues':<10} {'Clean':<12} {'Processed':<12} {'Status':<15}")
    print(f"{'ID':<8} {'Records':<12} {'Count':<10} {'Records':<12} {'Records':<12} {'Status':<15}")
    print("-" * 100)

    total_original = 0
    total_issues = 0
    total_clean = 0
    total_processed = 0
    success_count = 0

    for stat in processing_stats:
        house_display = f"House{stat['house_num']}"
        original = f"{stat['original_records']:,}" if stat['original_records'] > 0 else "N/A"
        issues = f"{stat['issues_count']:,}" if stat['issues_count'] > 0 else "0"
        clean = f"{stat['clean_records']:,}" if stat['clean_records'] > 0 else "N/A"
        processed = f"{stat['processed_records']:,}" if stat['processed_records'] > 0 else "N/A"
        status = stat['status']

        print(f"{house_display:<8} {original:<12} {issues:<10} {clean:<12} {processed:<12} {status:<15}")

        if stat['status'] == 'Success':
            total_original += stat['original_records']
            total_issues += stat['issues_count']
            total_clean += stat['clean_records']
            total_processed += stat['processed_records']
            success_count += 1

    print("-" * 100)
    # Format totals with proper alignment
    total_orig_str = f"{total_original:,}"
    total_issues_str = f"{total_issues:,}"
    total_clean_str = f"{total_clean:,}"
    total_processed_str = f"{total_processed:,}"
    success_str = f"{success_count} Success"

    print(f"{'TOTAL':<8} {total_orig_str:<12} {total_issues_str:<10} {total_clean_str:<12} {total_processed_str:<12} {success_str:<15}")
    print("=" * 100)

    # Additional summary
    print(f"\n📈 Data Processing Summary:")
    print(f"  • Total households targeted: {len(target_houses)}")
    print(f"  • Successfully processed: {success_count}")
    print(f"  • Failed/Missing: {len(target_houses) - success_count}")
    print(f"  • Total original records: {total_original:,}")
    print(f"  • Total issue records removed: {total_issues:,}")
    print(f"  • Total clean records: {total_clean:,}")
    print(f"  • Total processed records (1-min aligned): {total_processed:,}")
    if total_clean > 0:
        compression_ratio = (total_clean - total_processed) / total_clean * 100
        print(f"  • Data compression ratio: {compression_ratio:.1f}% (due to downsampling from 7s to 1min)")

    return results


def batch_process_complete_pipeline():
    """
    Complete pipeline: perception + shiftability + event segmentation + event ID
    """
    print("🚀 Starting complete processing pipeline for all specified households...")
    print("This includes: 1) Perception alignment, 2) Shiftability identification, 3) Event segmentation, 4) Event ID assignment")
    print("=" * 100)

    # Target households
    target_houses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]

    # Load house appliances configuration
    house_appliances = load_house_appliances_config()

    # Filter to only include target houses
    target_house_appliances = {}
    for house_num in target_houses:
        house_id = f"house{house_num}"
        if house_id in house_appliances:
            target_house_appliances[house_id] = house_appliances[house_id]
        else:
            print(f"⚠️ No appliance configuration found for {house_id}")

    print(f"📋 Found appliance configurations for {len(target_house_appliances)} households")

    # Step 1: Perception alignment (if not already done)
    print("\n" + "=" * 100)
    print("STEP 1: Perception Alignment")
    print("=" * 100)

    perception_results = batch_preprocess_target_houses()

    # Step 2: Shiftability identification
    print("\n" + "=" * 100)
    print("STEP 2: Shiftability Identification")
    print("=" * 100)

    shiftability_results = batch_identify_appliance_shiftability(
        house_appliances_dict=target_house_appliances,
        output_dir="./output/02_behavior_modeling/"
    )

    # Display Step 2 summary table
    print("\n" + "=" * 100)
    print("📊 STEP 2 SUMMARY: Shiftability Identification Results")
    print("=" * 100)

    header_format = '{:<8} {:<12} {:<12} {:<12} {:<15}'
    print(header_format.format('House', 'Total', 'Shiftable', 'Non-Shiftable', 'Status'))
    print(header_format.format('ID', 'Appliances', 'Appliances', 'Appliances', ''))
    print("-" * 100)

    step2_total_appliances = 0
    step2_total_shiftable = 0
    step2_success_count = 0

    for house_num in target_houses:
        house_id = f"house{house_num}"

        if house_id in shiftability_results:
            try:
                df_shift = shiftability_results[house_id]
                total_appliances = len(df_shift)
                shiftable_count = len(df_shift[df_shift['Shiftability'] == 'Shiftable'])
                non_shiftable_count = total_appliances - shiftable_count
                status = 'Success'

                step2_total_appliances += total_appliances
                step2_total_shiftable += shiftable_count
                step2_success_count += 1

            except Exception as e:
                total_appliances = 0
                shiftable_count = 0
                non_shiftable_count = 0
                status = f'Error: {str(e)[:10]}...'
        else:
            total_appliances = 0
            shiftable_count = 0
            non_shiftable_count = 0
            status = 'Failed'

        house_display = f"House{house_num}"
        print(header_format.format(
            house_display,
            str(total_appliances) if total_appliances > 0 else 'N/A',
            str(shiftable_count) if shiftable_count > 0 else 'N/A',
            str(non_shiftable_count) if non_shiftable_count > 0 else 'N/A',
            status
        ))

    print("-" * 100)
    step2_total_non_shiftable = step2_total_appliances - step2_total_shiftable
    success_str = f"{step2_success_count} Success"

    print(header_format.format(
        'TOTAL',
        str(step2_total_appliances),
        str(step2_total_shiftable),
        str(step2_total_non_shiftable),
        success_str
    ))
    print("=" * 100)

    # Step 3: Event segmentation
    print("\n" + "=" * 100)
    print("STEP 3: Event Segmentation")
    print("=" * 100)

    segmentation_results = batch_run_event_segmentation(
        house_data_dict=target_house_appliances,
        input_dir="./output/01_preprocessed/",
        label_dir="./output/02_behavior_modeling/",
        output_dir="./output/02_event_segments/"
    )

    # Display Step 3 summary table
    print("\n" + "=" * 100)
    print("📊 STEP 3 SUMMARY: Event Segmentation Results")
    print("=" * 100)

    header_format = '{:<8} {:<15} {:<15} {:<15}'
    print(header_format.format('House', 'Events', 'Shiftable', 'Status'))
    print(header_format.format('ID', 'Generated', 'Events', ''))
    print("-" * 100)

    step3_total_events = 0
    step3_total_shiftable_events = 0
    step3_success_count = 0

    for house_num in target_houses:
        house_id = f"house{house_num}"

        if house_id in segmentation_results:
            try:
                df_events = segmentation_results[house_id]
                total_events = len(df_events)
                shiftable_events = len(df_events[df_events['Shiftability'] == 'Shiftable'])
                status = 'Success'

                step3_total_events += total_events
                step3_total_shiftable_events += shiftable_events
                step3_success_count += 1

            except Exception as e:
                total_events = 0
                shiftable_events = 0
                status = f'Error: {str(e)[:10]}...'
        else:
            total_events = 0
            shiftable_events = 0
            status = 'Failed'

        house_display = f"House{house_num}"
        events_str = f"{total_events:,}" if total_events > 0 else 'N/A'
        shiftable_str = f"{shiftable_events:,}" if shiftable_events > 0 else 'N/A'

        print(header_format.format(house_display, events_str, shiftable_str, status))

    print("-" * 100)
    success_str = f"{step3_success_count} Success"
    total_events_str = f"{step3_total_events:,}"
    total_shiftable_str = f"{step3_total_shiftable_events:,}"

    print(header_format.format('TOTAL', total_events_str, total_shiftable_str, success_str))
    print("=" * 100)

    # Step 4: Event ID assignment
    print("\n" + "=" * 100)
    print("STEP 4: Event ID Assignment")
    print("=" * 100)

    event_id_results = batch_add_event_id(
        house_data_dict=target_house_appliances,
        input_dir="./output/02_event_segments/",
        output_dir="./output/02_event_segments/"
    )

    # Display Step 4 summary table
    print("\n" + "=" * 100)
    print("📊 STEP 4 SUMMARY: Event ID Assignment Results")
    print("=" * 100)

    header_format = '{:<8} {:<15} {:<15} {:<15}'
    print(header_format.format('House', 'Events with', 'Reschedulable', 'Status'))
    print(header_format.format('ID', 'Event IDs', 'Events', ''))
    print("-" * 100)

    step4_total_events = 0
    step4_total_reschedulable = 0
    step4_success_count = 0

    for house_num in target_houses:
        house_id = f"house{house_num}"

        if house_id in event_id_results:
            try:
                df_events = event_id_results[house_id]
                total_events = len(df_events)
                reschedulable_events = len(df_events[df_events['is_reschedulable'] == True])
                status = 'Success'

                step4_total_events += total_events
                step4_total_reschedulable += reschedulable_events
                step4_success_count += 1

            except Exception as e:
                total_events = 0
                reschedulable_events = 0
                status = f'Error: {str(e)[:10]}...'
        else:
            total_events = 0
            reschedulable_events = 0
            status = 'Failed'

        house_display = f"House{house_num}"
        events_str = f"{total_events:,}" if total_events > 0 else 'N/A'
        reschedulable_str = f"{reschedulable_events:,}" if reschedulable_events > 0 else 'N/A'

        print(header_format.format(house_display, events_str, reschedulable_str, status))

    print("-" * 100)
    success_str = f"{step4_success_count} Success"
    total_events_str = f"{step4_total_events:,}"
    total_reschedulable_str = f"{step4_total_reschedulable:,}"

    print(header_format.format('TOTAL', total_events_str, total_reschedulable_str, success_str))
    print("=" * 100)

    # Final comprehensive summary
    print("\n" + "=" * 120)
    print("🎉 COMPLETE PIPELINE FINISHED!")
    print("📊 Final Comprehensive Results Summary")
    print("=" * 120)

    print(f"📈 Overall Pipeline Summary:")
    print(f"  • Total households targeted: {len(target_houses)}")
    print(f"  • Step 1 - Perception alignment: {len(perception_results)} households successfully processed")
    print(f"  • Step 2 - Shiftability identification: {step2_success_count} households successfully processed")
    print(f"  • Step 3 - Event segmentation: {step3_success_count} households successfully processed")
    print(f"  • Step 4 - Event ID assignment: {step4_success_count} households successfully processed")

    print(f"\n📊 Key Statistics:")
    # Calculate total aligned records
    import pandas as pd
    total_aligned_records = 0
    for house_id in perception_results:
        if os.path.exists(perception_results[house_id]):
            try:
                df = pd.read_csv(perception_results[house_id])
                total_aligned_records += len(df)
            except:
                pass
    print(f"  • Total aligned records (1-min): {total_aligned_records:,}")
    print(f"  • Total appliances identified: {step2_total_appliances}")
    print(f"  • Total shiftable appliances: {step2_total_shiftable}")
    print(f"  • Total events generated: {step3_total_events:,}")
    print(f"  • Total reschedulable events: {step4_total_reschedulable:,}")

    if step2_total_appliances > 0:
        shiftable_ratio = (step2_total_shiftable / step2_total_appliances) * 100
        print(f"  • Shiftable appliances ratio: {shiftable_ratio:.1f}%")

    if step3_total_events > 0:
        reschedulable_ratio = (step4_total_reschedulable / step3_total_events) * 100
        print(f"  • Reschedulable events ratio: {reschedulable_ratio:.1f}%")

    print(f"\n📁 Results saved in:")
    print(f"  • Perception: ./output/01_preprocessed/")
    print(f"  • Shiftability: ./output/02_behavior_modeling/")
    print(f"  • Event segments: ./output/02_event_segments/")

    print("=" * 120)

    return {
        'perception': perception_results,
        'shiftability': shiftability_results,
        'segmentation': segmentation_results,
        'event_id': event_id_results
    }


def process_single_house_complete(house_number: int):
    """
    Complete pipeline for a single household
    """
    house_id = f"house{house_number}"

    print(f"🚀 Starting complete processing pipeline for {house_id.upper()}...")
    print("This includes: 1) Perception alignment, 2) Shiftability identification, 3) Event segmentation, 4) Event ID assignment")
    print("=" * 80)

    # Load house appliances configuration
    house_appliances = load_house_appliances_config()

    if house_id not in house_appliances:
        print(f"❌ No appliance configuration found for {house_id}")
        return None

    appliance_text = house_appliances[house_id]
    print(f"📋 Appliances for {house_id.upper()}: {appliance_text}")

    try:
        # Step 1: Perception alignment
        print(f"\n--- STEP 1: Perception Alignment for {house_id.upper()} ---")
        from tools.p_01_perception_alignment import preprocess_power_series_single

        input_path = f"/home/deep/TimeSeries/dataset/cleand_data/CLEAN_House{house_number}.csv"
        perception_result = preprocess_power_series_single(
            input_path=input_path,
            house_id=house_id,
            base_output_dir="./output/01_preprocessed/"
        )

        # Step 2: Shiftability identification
        print(f"\n--- STEP 2: Shiftability Identification for {house_id.upper()} ---")
        shiftability_result = identify_appliance_shiftability_single(
            user_text=appliance_text,
            house_id=house_id,
            output_dir="./output/02_behavior_modeling/"
        )

        # Step 3: Event segmentation
        print(f"\n--- STEP 3: Event Segmentation for {house_id.upper()} ---")
        power_csv = perception_result
        label_csv = os.path.join("./output/02_behavior_modeling/", house_id, f"02_1_appliance_shiftable_label_{house_id}.csv")

        segmentation_result = run_event_segmentation_single(
            house_id=house_id,
            power_csv=power_csv,
            label_csv=label_csv,
            output_dir="./output/02_event_segments/"
        )

        # Step 4: Event ID assignment
        print(f"\n--- STEP 4: Event ID Assignment for {house_id.upper()} ---")
        input_csv = os.path.join("./output/02_event_segments/", house_id, f"02_appliance_event_segments_{house_id}.csv")

        event_id_result = add_event_id_single(
            house_id=house_id,
            input_csv=input_csv,
            output_dir="./output/02_event_segments/"
        )

        print(f"\n🎉 Complete pipeline for {house_id.upper()} finished!")
        print(f"📊 Generated {len(event_id_result)} events")

        return {
            'perception': perception_result,
            'shiftability': shiftability_result,
            'segmentation': segmentation_result,
            'event_id': event_id_result
        }

    except Exception as e:
        print(f"❌ Error processing {house_id}: {str(e)}")
        return None


def preprocess_single_house(house_number: int):
    """
    Process single household data - perception alignment step only

    Args:
        house_number: Household number (1-21)
    """
    print(f"🏠 Starting to process House{house_number} data...")

    # Execute perception alignment
    from tools.p_01_perception_alignment import preprocess_power_series_single

    input_path = f"/home/deep/TimeSeries/dataset/cleand_data/CLEAN_House{house_number}.csv"
    house_id = f"house{house_number}"

    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        return None

    try:
        result_path = preprocess_power_series_single(
            input_path=input_path,
            house_id=house_id,
            base_output_dir="./output/01_preprocessed/"
        )

        print(f"✅ House{house_number} perception processing completed!")
        print(f"📁 Result saved at: {result_path}")

        # Other steps temporarily skipped
        print("⏭️ Other processing steps temporarily skipped (shiftability identification, event segmentation, event ID, etc.)")

        return result_path

    except Exception as e:
        print(f"❌ House{house_number} processing failed: {str(e)}")
        return None


import argparse


def main(mode, house_number):
    """
    Main function for perception module processing
    
    Args:
        mode: Processing mode (1-5)
        house_number: House number for single household processing
    """
    print("🚀 Starting Agent V2 Test - Perception Module")
    print("=" * 80)

    # User input description (temporarily retained, may be used in subsequent steps)
    user_input = """Hi, I have several appliances at home: Aggregate, Fridge, Chest Freezer, Upright Freezer, Tumble Dryer, Washing Machine, Dishwasher, Computer Site, Television Site, Electric Heater.
    Note: Entry 0 is the Aggregate total power of the household and not an actual appliance."""

    target_houses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]

    if mode == 1:
        # Single household mode
        print(f"Available households: {target_houses}")
        if house_number in target_houses:
            result = process_single_house_complete(house_number)
        else:
            print(f"❌ Household number {house_number} is not in the target list")
            print(f"Available households: {target_houses}")

    elif mode == 2:
        # Batch mode - process all households
        results = batch_process_complete_pipeline()

    elif mode == 3:
        # Perception only - single household            
        print(f"Available households: {target_houses}")
        if house_number in target_houses:
            result = preprocess_single_house(house_number)
        else:
            print(f"❌ Household number {house_number} is not in the target list")
            print(f"Available households: {target_houses}")

    elif mode == 4:
        # Perception only - batch process all households
        results = batch_preprocess_target_houses()

    elif mode == 5:
        # Test mode - process first 3 households only (perception only)
        print("🧪 Test mode: Processing first 3 households [1, 2, 3] - Perception only")
        test_results = batch_preprocess_specific_houses(
            house_numbers=[1, 2, 3],
            input_dir="/home/deep/TimeSeries/dataset/cleand_data/",
            base_output_dir="./output/01_preprocessed/"
        )
        print(f"🎉 Test completed! Processed {len(test_results)} households")

    else:
        print("❌ Invalid choice, exiting program")

    print("\n🏁 Program execution completed!")


def parse_args():
    parser = argparse.ArgumentParser(description="Agent V2 Test - Perception Module")
    parser.add_argument(
        "--mode", 
        type=int, 
        default=2,
        choices=[1, 2, 3, 4, 5],
        help="Processing mode: 1=Single household (default), 2=Batch processing, 3=Perception only single, 4=Perception only batch, 5=Test mode"
    )
    parser.add_argument(
        "--house-number", 
        type=int, 
        default=1,
        help="House number for single household processing (1-21, default: 1)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print("args:", args)
    main(args.mode, args.house_number)