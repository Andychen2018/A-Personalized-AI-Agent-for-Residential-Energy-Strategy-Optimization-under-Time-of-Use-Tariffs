#!/usr/bin/env python3
"""
Agent V2 Test - Tariff Cost Analysis Module
============================================

This module provides tariff cost analysis functionality with support for multiple pricing schemes:
- UK: Standard, Economy_7, Economy_10
- Germany: Variable TOU rates
- California: TOU_D with seasonal rates

Features:
- Single household or batch processing
- Multiple tariff type support
- Automatic tariff recommendation
- Cost comparison and visualization
"""

import os
import sys
import json
from typing import Dict, List, Tuple

# Add current directory to path for imports
sys.path.append('.')

from tools.p_03_tariff_modeling import (
    simulate_tariff_cost_detailed,
    batch_simulate_tariff_costs,
    load_tariff_config,
    get_tariff_schedules
)
from tools.p_03_energy_summary import (
    summarize_tariff_results_and_visualize,
    batch_summarize_tariff_results
)


def load_house_appliances_config(config_path: str = "./config/house_appliances.json") -> dict:
    """
    Load house appliances configuration from text file

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


def get_available_tariff_types() -> List[str]:
    """Get list of available tariff types"""
    return ["UK", "Germany", "California"]


def display_tariff_info(tariff_type: str):
    """Display information about a specific tariff type"""
    try:
        config = load_tariff_config(tariff_type)
        schedules = get_tariff_schedules(tariff_type)

        print(f"\n📊 {tariff_type} Tariff Information:")
        print("=" * 50)

        for tariff_name in schedules.keys():
            print(f"  • {tariff_name}")

        print(f"\nTotal available schemes: {len(schedules)}")

    except Exception as e:
        print(f"❌ Error loading {tariff_type} tariff info: {str(e)}")


def single_house_tariff_analysis(
    house_id: str,
    tariff_type: str = "UK",
    input_dir: str = "./output/02_event_segments/",
    perception_dir: str = "./output/01_preprocessed/",
    label_dir: str = "./output/02_behavior_modeling/",
    output_dir: str = "./output/03_cost_analysis"
) -> Tuple[bool, str]:
    """
    Run tariff cost analysis for a single household

    Returns:
        Tuple of (success, message)
    """
    try:
        print(f"🏠 Starting tariff cost analysis for {house_id.upper()}...")
        print(f"📊 Tariff type: {tariff_type}")
        print("=" * 60)

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
            error_msg = f"Missing required files for {house_id}:\n" + "\n".join(f"  - {f}" for f in missing_files)
            print(f"❌ {error_msg}")
            return False, error_msg

        # Run tariff cost simulation
        run_df, summary = simulate_tariff_cost_detailed(
            event_csv=event_csv,
            power_csv=power_csv,
            label_csv=label_csv,
            house_id=house_id,
            tariff_type=tariff_type,
            output_dir=output_dir
        )

        # Generate summary and visualization
        summary_result = summarize_tariff_results_and_visualize(
            house_id=house_id,
            tariff_type=tariff_type,
            output_dir=output_dir
        )

        success_msg = f"✅ Tariff analysis completed successfully for {house_id.upper()}!"
        print(f"\n{success_msg}")

        if isinstance(summary_result, dict) and 'recommended_tariff' in summary_result:
            print(f"🎯 Recommended tariff: {summary_result['recommended_tariff']}")
            print(f"📁 Results saved to: {summary_result['output_dir']}")

        return True, success_msg

    except Exception as e:
        error_msg = f"Error processing {house_id}: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg


def batch_tariff_analysis(
    house_data_dict: dict,
    tariff_type: str = "UK",
    input_dir: str = "./output/02_event_segments/",
    perception_dir: str = "./output/01_preprocessed/",
    label_dir: str = "./output/02_behavior_modeling/",
    output_dir: str = "./output/03_cost_analysis"
) -> Dict:
    """
    Run batch tariff cost analysis for multiple households

    Returns:
        Dictionary with processing results
    """
    print(f"🚀 Starting batch tariff cost analysis...")
    print(f"📊 Tariff type: {tariff_type}")
    print(f"🏠 Target households: {len(house_data_dict)}")
    print("=" * 80)

    # Run batch cost simulation
    cost_results = batch_simulate_tariff_costs(
        house_data_dict=house_data_dict,
        tariff_type=tariff_type,
        input_dir=input_dir,
        perception_dir=perception_dir,
        label_dir=label_dir,
        output_dir=output_dir
    )

    # Run batch summary and visualization (skip detailed output for large batches)
    print(f"\n🔄 Generating summary reports and visualizations...")
    summary_results = batch_summarize_tariff_results(
        house_data_dict=house_data_dict,
        tariff_type=tariff_type,
        output_dir=output_dir
    )

    # Generate final summary table for all tariff types at the very end (most visible)
    if cost_results:
        print(f"\n" + "=" * 100)
        print(f"🎉 FINAL {tariff_type.upper()} TARIFF COST SUMMARY TABLE")
        print("=" * 100)

        # Collect cost data for all processed houses
        summary_data = []
        cost_columns = []

        # Get the first house to determine available cost columns
        first_house_data = next(iter(cost_results.values()))
        if first_house_data:
            run_df = first_house_data[0]
            cost_columns = [col for col in run_df.columns if col.startswith('cost_')]

        for house_id, (run_df, _) in cost_results.items():
            house_costs = run_df[cost_columns].sum()
            recommended = house_costs.idxmin().replace("cost_", "")

            house_data = {
                'House': house_id.upper(),
                'Recommended': recommended,
                'Best_Cost': house_costs.min()
            }

            # Add individual tariff costs
            for col in cost_columns:
                tariff_name = col.replace("cost_", "")
                house_data[tariff_name] = house_costs[col]

            summary_data.append(house_data)

        # Sort by house number for better display
        summary_data.sort(key=lambda x: int(x['House'].replace('HOUSE', '')))

        # Create dynamic header based on available tariffs
        tariff_names = [col.replace("cost_", "") for col in cost_columns]

        if tariff_type == "UK":
            # UK: 3 tariffs
            header_format = '{:<8} {:<12} {:<12} {:<12} {:<12} {:<12}'
            headers = ['House', 'Standard', 'Economy_7', 'Economy_10', 'Recommended', 'Best_Cost']
            units = ['ID', '($)', '($)', '($)', 'Tariff', '($)']
        elif tariff_type == "Germany":
            # Germany: 2 tariffs (Base first, then Variable TOU)
            header_format = '{:<8} {:<18} {:<18} {:<12} {:<12}'
            headers = ['House', 'Germany_Variable_Base', 'Germany_Variable', 'Recommended', 'Best_Cost']
            units = ['ID', '($)', '($)', 'Tariff', '($)']
        elif tariff_type == "California":
            # California: 2 tariffs (Base first, then TOU_D)
            header_format = '{:<8} {:<12} {:<12} {:<12} {:<12}'
            headers = ['House', 'TOU_D_Base', 'TOU_D', 'Recommended', 'Best_Cost']
            units = ['ID', '($)', '($)', 'Tariff', '($)']
        else:
            # Generic format
            header_format = '{:<8} ' + ' '.join(['{:<12}'] * (len(tariff_names) + 2))
            headers = ['House'] + tariff_names + ['Recommended', 'Best_Cost']
            units = ['ID'] + ['($)'] * len(tariff_names) + ['Tariff', '($)']

        print(header_format.format(*headers))
        print(header_format.format(*units))
        print("-" * 100)

        # Display each house
        tariff_totals = {name: 0 for name in tariff_names}

        for data in summary_data:
            house_display = data['House']
            recommended = data['Recommended']
            best_cost = data['Best_Cost']

            # Prepare row data
            if tariff_type == "UK":
                row_data = [
                    house_display,
                    f"${data['Standard']:.2f}",
                    f"${data['Economy_7']:.2f}",
                    f"${data['Economy_10']:.2f}",
                    recommended,
                    f"${best_cost:.2f}"
                ]
                tariff_totals['Standard'] += data['Standard']
                tariff_totals['Economy_7'] += data['Economy_7']
                tariff_totals['Economy_10'] += data['Economy_10']
            elif tariff_type == "Germany":
                row_data = [
                    house_display,
                    f"${data['Germany_Variable_Base']:.2f}",
                    f"${data['Germany_Variable']:.2f}",
                    recommended,
                    f"${best_cost:.2f}"
                ]
                tariff_totals['Germany_Variable'] += data['Germany_Variable']
                tariff_totals['Germany_Variable_Base'] += data['Germany_Variable_Base']
            elif tariff_type == "California":
                row_data = [
                    house_display,
                    f"${data['TOU_D_Base']:.2f}",
                    f"${data['TOU_D']:.2f}",
                    recommended,
                    f"${best_cost:.2f}"
                ]
                tariff_totals['TOU_D'] += data['TOU_D']
                tariff_totals['TOU_D_Base'] += data['TOU_D_Base']

            print(header_format.format(*row_data))

        # Display totals
        print("-" * 100)
        if tariff_type == "UK":
            total_row = [
                'TOTAL',
                f"${tariff_totals['Standard']:.2f}",
                f"${tariff_totals['Economy_7']:.2f}",
                f"${tariff_totals['Economy_10']:.2f}",
                'N/A',
                'N/A'
            ]
        elif tariff_type == "Germany":
            total_row = [
                'TOTAL',
                f"${tariff_totals['Germany_Variable_Base']:.2f}",
                f"${tariff_totals['Germany_Variable']:.2f}",
                'N/A',
                'N/A'
            ]
        elif tariff_type == "California":
            total_row = [
                'TOTAL',
                f"${tariff_totals['TOU_D_Base']:.2f}",
                f"${tariff_totals['TOU_D']:.2f}",
                'N/A',
                'N/A'
            ]

        print(header_format.format(*total_row))

        # Display recommendations summary
        recommendations = {}
        for data in summary_data:
            rec = data['Recommended']
            recommendations[rec] = recommendations.get(rec, 0) + 1

        print(f"\n📈 FINAL RECOMMENDATIONS SUMMARY:")
        for tariff, count in recommendations.items():
            print(f"  🎯 {tariff}: {count} households")

        # Calculate total savings
        total_best = sum(data['Best_Cost'] for data in summary_data)
        total_worst = max(tariff_totals.values()) if tariff_totals else 0
        total_savings = total_worst - total_best
        savings_pct = (total_savings / total_worst) * 100 if total_worst > 0 else 0

        print(f"\n💰 TOTAL POTENTIAL SAVINGS:")
        print(f"  💡 Best total cost: ${total_best:.2f}")
        print(f"  💡 Worst total cost: ${total_worst:.2f}")
        print(f"  💡 Total savings: ${total_savings:.2f} ({savings_pct:.1f}%)")

        # Display tariff comparison
        if tariff_type == "Germany":
            variable_total = tariff_totals['Germany_Variable']
            base_total = tariff_totals['Germany_Variable_Base']
            print(f"\n📊 GERMANY TARIFF COMPARISON:")
            print(f"  🔄 Variable TOU Rate: ${variable_total:.2f}")
            print(f"  📊 Flat Base Rate: ${base_total:.2f}")
            if base_total > 0:
                savings = base_total - variable_total
                savings_pct = (savings / base_total) * 100
                print(f"  💡 TOU Savings: ${savings:.2f} ({savings_pct:.1f}%)")

        elif tariff_type == "California":
            tou_total = tariff_totals['TOU_D']
            base_total = tariff_totals['TOU_D_Base']
            print(f"\n📊 CALIFORNIA TARIFF COMPARISON:")
            print(f"  🌞❄️ Seasonal TOU Rate: ${tou_total:.2f}")
            print(f"  📊 Flat Base Rate: ${base_total:.2f}")
            if base_total > 0:
                savings = base_total - tou_total
                savings_pct = (savings / base_total) * 100
                print(f"  💡 TOU Savings: ${savings:.2f} ({savings_pct:.1f}%)")

        print("=" * 100)

    return {
        'cost_results': cost_results,
        'summary_results': summary_results,
        'tariff_type': tariff_type,
        'total_processed': len(cost_results),
        'total_summarized': len(summary_results)
    }


def main():
    """Main function for interactive tariff cost analysis"""
    print("🚀 Starting Agent V2 Test - Tariff Cost Analysis Module")
    print("=" * 80)

    # Display available tariff types
    available_types = get_available_tariff_types()
    print("📊 Available tariff types:")
    for i, tariff_type in enumerate(available_types, 1):
        print(f"  {i}. {tariff_type}")
        display_tariff_info(tariff_type)

    print("\n" + "=" * 80)
    print("Please select processing mode:")
    print("1. Single household analysis (Default)")
    print("2. Batch analysis - All households")
    print("3. Display tariff information only")

    try:
        choice = input("Please enter your choice (1/2/3) [Default: 1]: ").strip()
        if not choice:
            choice = "1"

        if choice == "3":
            # Just display tariff information
            print("\n📊 Tariff Information Display Mode")
            return

        # Select tariff type
        print("\nSelect tariff type:")
        for i, tariff_type in enumerate(available_types, 1):
            print(f"  {i}. {tariff_type}")

        tariff_choice = input(f"Please enter your choice (1-{len(available_types)}) [Default: 1]: ").strip()
        if not tariff_choice:
            tariff_choice = "1"

        try:
            tariff_index = int(tariff_choice) - 1
            if 0 <= tariff_index < len(available_types):
                selected_tariff = available_types[tariff_index]
            else:
                print("Invalid choice, using UK as default")
                selected_tariff = "UK"
        except ValueError:
            print("Invalid input, using UK as default")
            selected_tariff = "UK"

        print(f"\n✅ Selected tariff type: {selected_tariff}")

        # Load house configuration
        house_appliances = load_house_appliances_config()

        if choice == "1":
            # Single household mode
            print(f"\n📋 Available households: {list(house_appliances.keys())}")
            house_input = input("Enter house ID (e.g., house1) [Default: house1]: ").strip()
            if not house_input:
                house_input = "house1"

            if house_input not in house_appliances:
                print(f"❌ House {house_input} not found in configuration")
                return

            success, message = single_house_tariff_analysis(
                house_id=house_input,
                tariff_type=selected_tariff
            )

            if success:
                print(f"\n🎉 Single household analysis completed!")
            else:
                print(f"\n❌ Analysis failed: {message}")

        elif choice == "2":
            # Batch mode
            results = batch_tariff_analysis(
                house_data_dict=house_appliances,
                tariff_type=selected_tariff
            )

            print(f"\n🎉 Batch analysis completed!")
            print(f"📊 Results summary:")
            print(f"  • Tariff type: {results['tariff_type']}")
            print(f"  • Total processed: {results['total_processed']}")
            print(f"  • Total summarized: {results['total_summarized']}")

        else:
            print("❌ Invalid choice")
            return

    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()