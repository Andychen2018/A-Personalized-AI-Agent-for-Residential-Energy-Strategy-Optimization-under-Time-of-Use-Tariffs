#!/usr/bin/env python3
"""
Monthly Electricity Cost Comparison Plot Generator

This script generates monthly cost comparison plots for 19 households showing:
1. Standard cost (from 06_monthly_total_summary.csv)
2. Economy_7 original cost (from 06_monthly_total_summary.csv)
3. Economy_7 optimized cost (calculated from migrated + non-migrated costs)
4. Economy_10 original cost (from 06_monthly_total_summary.csv)
5. Economy_10 optimized cost (calculated from migrated + non-migrated costs)

Features:
- Academic-style plots with Times New Roman font
- Monthly vertical grid lines for better readability
- Saves results in /home/deep/TimeSeries/Agent_V2/output/Monthly_cost_trends/house*/

Author: Smart Home Energy Management System
Date: 2025-01-21
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os
import argparse
import glob
import matplotlib.dates as mdates
from matplotlib import rcParams

# Set font configuration for academic style
# Configure matplotlib to use serif fonts (Times-like)
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'Times', 'Liberation Serif', 'DejaVu Serif', 'serif']
rcParams['font.size'] = 12
rcParams['axes.labelsize'] = 14
rcParams['axes.titlesize'] = 16
rcParams['xtick.labelsize'] = 12
rcParams['ytick.labelsize'] = 12
rcParams['legend.fontsize'] = 12

# Set additional academic style parameters
rcParams['axes.linewidth'] = 1.2
rcParams['grid.linewidth'] = 0.5
rcParams['lines.linewidth'] = 2.0
rcParams['patch.linewidth'] = 0.5
rcParams['xtick.major.width'] = 1.2
rcParams['ytick.major.width'] = 1.2
rcParams['xtick.minor.width'] = 0.8
rcParams['ytick.minor.width'] = 0.8

# Clear matplotlib font cache to ensure font changes take effect
import matplotlib.font_manager as fm
try:
    fm._rebuild()
except AttributeError:
    # For newer matplotlib versions
    try:
        fm.fontManager.__init__()
    except:
        pass  # If font manager initialization fails, continue anyway

def load_baseline_costs(baseline_file):
    """
    Load baseline costs from 06_monthly_total_summary.csv
    
    Args:
        baseline_file: Path to the baseline cost summary file
        
    Returns:
        DataFrame: Monthly baseline costs
    """
    df = pd.read_csv(baseline_file)
    df['month'] = pd.to_datetime(df['month'])
    return df

def load_optimized_costs(migrated_file, non_migrated_file):
    """
    Load and calculate optimized costs from migrated and non-migrated files
    
    Args:
        migrated_file: Path to migrated costs CSV
        non_migrated_file: Path to non-migrated costs CSV
        
    Returns:
        DataFrame: Monthly optimized costs
    """
    # Load migrated events (optimized)
    migrated_df = pd.read_csv(migrated_file)
    migrated_df['orig_start_time'] = pd.to_datetime(migrated_df['orig_start_time'])
    migrated_df['sched_start_time'] = pd.to_datetime(migrated_df['sched_start_time'])
    migrated_df['month'] = migrated_df['orig_start_time'].dt.to_period('M')
    
    # Load non-migrated events (unchanged)
    non_migrated_df = pd.read_csv(non_migrated_file)
    non_migrated_df['start_time'] = pd.to_datetime(non_migrated_df['start_time'])
    non_migrated_df['month'] = non_migrated_df['start_time'].dt.to_period('M')
    
    # Calculate monthly costs
    monthly_costs = []
    
    # Get all unique months
    all_months = set(migrated_df['month'].unique()) | set(non_migrated_df['month'].unique())
    
    for month in sorted(all_months):
        # Optimized cost = scheduled cost of migrated events + original cost of non-migrated events
        migrated_month = migrated_df[migrated_df['month'] == month]
        non_migrated_month = non_migrated_df[non_migrated_df['month'] == month]
        
        optimized_cost = (migrated_month['sched_total_cost'].sum() + 
                         non_migrated_month['total_cost'].sum())
        
        # Original cost = original cost of migrated events + original cost of non-migrated events
        original_cost = (migrated_month['orig_total_cost'].sum() + 
                        non_migrated_month['total_cost'].sum())
        
        monthly_costs.append({
            'month': month.to_timestamp(),
            'optimized_cost': optimized_cost,
            'original_cost': original_cost
        })
    
    return pd.DataFrame(monthly_costs)

def create_cost_comparison_plot(baseline_df, economy_7_optimized_df, economy_10_optimized_df, output_file=None, house_id=None):
    """
    Create the monthly cost comparison plot with academic styling

    Args:
        baseline_df: DataFrame with baseline costs
        economy_7_optimized_df: DataFrame with Economy_7 optimized costs
        economy_10_optimized_df: DataFrame with Economy_10 optimized costs
        output_file: Optional output file path
        house_id: House identifier for the plot title
    """
    # Merge dataframes on month
    merged_df = baseline_df.copy()

    # Merge Economy_7 optimized costs
    economy_7_optimized_df = economy_7_optimized_df.rename(columns={
        'optimized_cost': 'economy_7_optimized_cost'
    })
    merged_df = pd.merge(merged_df, economy_7_optimized_df[['month', 'economy_7_optimized_cost']],
                        on='month', how='outer')

    # Merge Economy_10 optimized costs
    economy_10_optimized_df = economy_10_optimized_df.rename(columns={
        'optimized_cost': 'economy_10_optimized_cost'
    })
    merged_df = pd.merge(merged_df, economy_10_optimized_df[['month', 'economy_10_optimized_cost']],
                        on='month', how='outer')

    merged_df = merged_df.sort_values('month')

    # Create the plot with academic styling
    fig, ax = plt.subplots(figsize=(16, 10))

    # Define colors matching the provided figure
    colors = {
        'standard': '#FFD700',           # Yellow/Gold (Standard_cost)
        'economy_7_orig': '#87CEEB',     # Light blue (Economy_7_Original_cost)
        'economy_7_opt': '#4682B4',      # Steel blue (Economy_7_Optimized_cost)
        'economy_10_orig': '#DDA0DD',    # Plum (Economy_10_Original_cost)
        'economy_10_opt': '#9370DB'      # Medium slate blue (Economy_10_Optimized_cost)
    }

    # Plot the 5 curves matching the provided figure style
    ax.plot(merged_df['month'], merged_df['cost_Standard'],
            marker='o', linewidth=2.0, markersize=6, color=colors['standard'],
            label='Standard_cost', alpha=0.9)

    ax.plot(merged_df['month'], merged_df['cost_Economy_7'],
            marker='s', linewidth=2.0, markersize=6, color=colors['economy_7_orig'],
            label='Economy_7_Original_cost', alpha=0.9)

    ax.plot(merged_df['month'], merged_df['economy_7_optimized_cost'],
            marker='^', linewidth=2.0, markersize=6, color=colors['economy_7_opt'],
            label='Economy_7_Optimized_cost', alpha=0.9)

    ax.plot(merged_df['month'], merged_df['cost_Economy_10'],
            marker='v', linewidth=2.0, markersize=6, color=colors['economy_10_orig'],
            label='Economy_10_Original_cost', alpha=0.9)

    ax.plot(merged_df['month'], merged_df['economy_10_optimized_cost'],
            marker='d', linewidth=2.0, markersize=6, color=colors['economy_10_opt'],
            label='Economy_10_Optimized_cost', alpha=0.9)

    # Set academic-style labels and title
    ax.set_xlabel('Month', fontsize=14, fontweight='bold')
    ax.set_ylabel('Monthly Electricity Cost (£)', fontsize=14, fontweight='bold')

    if house_id:
        ax.set_title(f'Monthly Electricity Cost Comparison - {house_id.upper()}',
                    fontsize=16, fontweight='bold', pad=20)

    # Configure monthly grid lines
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())

    # Add comprehensive grid
    ax.grid(True, which='major', axis='x', alpha=0.7, linestyle='-', linewidth=1.0, color='gray')
    ax.grid(True, which='minor', axis='x', alpha=0.4, linestyle='--', linewidth=0.5, color='gray')
    ax.grid(True, which='major', axis='y', alpha=0.3, linestyle='-', linewidth=0.5, color='gray')

    # Customize legend with academic style
    legend = ax.legend(loc='upper right', fontsize=12, framealpha=0.95,
                      fancybox=True, shadow=True, ncol=1)
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_edgecolor('black')
    legend.get_frame().set_linewidth(1)

    # Format x-axis with better rotation and alignment
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    plt.setp(ax.yaxis.get_majorticklabels())

    # Set y-axis to start from 0 with some padding
    ax.set_ylim(bottom=0)

    # Add subtle border
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
        spine.set_color('black')

    # Adjust layout for academic presentation
    plt.tight_layout()

    # Save with high quality for academic use
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        print(f"✅ Academic-style plot saved to: {output_file}")
        plt.close()  # Close to free memory when processing multiple houses
    else:
        plt.show()

    return merged_df

def get_available_houses():
    """Get list of available houses from the cost analysis directory"""
    cost_analysis_dir = "/home/deep/TimeSeries/Agent_V2/output/03_cost_analysis/UK"
    if not os.path.exists(cost_analysis_dir):
        return []

    houses = []
    for item in os.listdir(cost_analysis_dir):
        if item.startswith('house') and os.path.isdir(os.path.join(cost_analysis_dir, item)):
            houses.append(item)

    # Sort houses numerically (house1, house2, ..., house21)
    def extract_house_number(house_name):
        try:
            return int(house_name.replace('house', ''))
        except ValueError:
            return 999  # Put invalid names at the end

    return sorted(houses, key=extract_house_number)

def process_single_house(house_id):
    """Process a single house and generate its cost comparison plot"""
    print(f"\n🏠 Processing {house_id}")
    print("-" * 40)

    # File paths for this house
    baseline_file = f"/home/deep/TimeSeries/Agent_V2/output/03_cost_analysis/UK/{house_id}/06_monthly_total_summary.csv"

    # Economy_7 files
    economy_7_migrated_file = f"/home/deep/TimeSeries/Agent_V2/output/06_cost_cal/UK/Economy_7/{house_id}/migrated_costs.csv"
    economy_7_non_migrated_file = f"/home/deep/TimeSeries/Agent_V2/output/06_cost_cal/UK/Economy_7/{house_id}/non_migrated_costs.csv"

    # Economy_10 files
    economy_10_migrated_file = f"/home/deep/TimeSeries/Agent_V2/output/06_cost_cal/UK/Economy_10/{house_id}/migrated_costs.csv"
    economy_10_non_migrated_file = f"/home/deep/TimeSeries/Agent_V2/output/06_cost_cal/UK/Economy_10/{house_id}/non_migrated_costs.csv"

    # Create output directory for this house
    output_dir = f"/home/deep/TimeSeries/Agent_V2/output/Monthly_cost_trends/{house_id}"
    os.makedirs(output_dir, exist_ok=True)

    # Output file for this house
    output_file = os.path.join(output_dir, "monthly_cost_comparison.png")

    # Check if files exist
    all_files = [baseline_file, economy_7_migrated_file, economy_7_non_migrated_file,
                 economy_10_migrated_file, economy_10_non_migrated_file]

    missing_files = []
    for file_path in all_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"⚠️  Warning: Missing files for {house_id}:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False

    try:
        print("📂 Loading baseline costs...")
        baseline_df = load_baseline_costs(baseline_file)
        print(f"   ✅ Loaded {len(baseline_df)} months of baseline data")

        print("📂 Loading Economy_7 optimized costs...")
        economy_7_optimized_df = load_optimized_costs(economy_7_migrated_file, economy_7_non_migrated_file)
        print(f"   ✅ Loaded {len(economy_7_optimized_df)} months of Economy_7 optimized data")

        print("📂 Loading Economy_10 optimized costs...")
        economy_10_optimized_df = load_optimized_costs(economy_10_migrated_file, economy_10_non_migrated_file)
        print(f"   ✅ Loaded {len(economy_10_optimized_df)} months of Economy_10 optimized data")

        print("📊 Creating cost comparison plot...")
        merged_df = create_cost_comparison_plot(baseline_df, economy_7_optimized_df, economy_10_optimized_df, output_file, house_id)

        # Print summary statistics for this house
        print_house_summary(merged_df, house_id)

        return True

    except Exception as e:
        print(f"❌ Error processing {house_id}: {str(e)}")
        return False

def main():
    """Main function to generate cost comparison plots for all 19 households"""
    parser = argparse.ArgumentParser(description='Generate monthly electricity cost comparison plots for 19 households')
    parser.add_argument('--house', type=str, help='Specific house to process (e.g., house1)', default=None)
    parser.add_argument('--single', action='store_true', help='Process only one house (house1 by default)')

    args = parser.parse_args()

    print("🚀 Academic-Style Monthly Electricity Cost Comparison Plot Generator")
    print("📊 Processing 19 Households with Times New Roman Font")
    print("=" * 80)

    # Get available houses
    available_houses = get_available_houses()

    if not available_houses:
        print("❌ No houses found in the cost analysis directory")
        return

    print(f"📋 Available houses ({len(available_houses)}): {', '.join(available_houses)}")

    # Determine which houses to process
    houses_to_process = []

    if args.house:
        if args.house in available_houses:
            houses_to_process = [args.house]
        else:
            print(f"❌ House '{args.house}' not found. Available houses: {', '.join(available_houses)}")
            return
    elif args.single:
        # Process only house1 if available, otherwise first available house
        if 'house1' in available_houses:
            houses_to_process = ['house1']
        else:
            houses_to_process = [available_houses[0]]
        print(f"💡 Single house mode. Processing: {houses_to_process[0]}")
    else:
        # Default: process ALL available houses (19 households)
        houses_to_process = available_houses
        print(f"🏠 Processing ALL {len(houses_to_process)} households for comprehensive analysis")

    # Process houses with progress tracking
    successful_houses = []
    failed_houses = []
    total_houses = len(houses_to_process)

    print(f"\n🔄 Starting batch processing of {total_houses} house(s)...")
    print("-" * 80)

    for i, house_id in enumerate(houses_to_process, 1):
        print(f"\n[{i}/{total_houses}] Processing {house_id}...")
        success = process_single_house(house_id)
        if success:
            successful_houses.append(house_id)
            print(f"✅ {house_id} completed successfully")
        else:
            failed_houses.append(house_id)
            print(f"❌ {house_id} failed")

    # Print comprehensive final summary
    print("\n" + "=" * 80)
    print("🎯 COMPREHENSIVE PROCESSING SUMMARY")
    print("=" * 80)

    if successful_houses:
        print(f"✅ Successfully processed {len(successful_houses)}/{total_houses} house(s):")
        for house_id in successful_houses:
            output_dir = f"/home/deep/TimeSeries/Agent_V2/output/Monthly_cost_trends/{house_id}"
            print(f"   📁 {house_id}: {output_dir}/monthly_cost_comparison.png")

    if failed_houses:
        print(f"\n❌ Failed to process {len(failed_houses)} house(s): {', '.join(failed_houses)}")

    # Calculate success rate
    success_rate = (len(successful_houses) / total_houses) * 100 if total_houses > 0 else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}% ({len(successful_houses)}/{total_houses})")
    print(f"🎉 Academic-style plots generated with Times New Roman font!")
    print(f"📂 All plots saved in: /home/deep/TimeSeries/Agent_V2/output/Monthly_cost_trends/")

    if len(successful_houses) >= 19:
        print(f"🏆 COMPLETE: All 19 households processed successfully!")
    elif len(successful_houses) > 0:
        print(f"⚠️  PARTIAL: {len(successful_houses)} out of 19 households processed.")

def print_house_summary(merged_df, house_id):
    """Print summary statistics for a house"""
    print(f"\n📈 Cost Comparison Summary for {house_id or 'House'}:")
    print("-" * 50)

    if 'cost_Standard' in merged_df.columns:
        # Remove NaN values for calculation
        valid_data = merged_df.dropna(subset=['cost_Standard'])

        if not valid_data.empty:
            avg_standard = valid_data['cost_Standard'].mean()
            print(f"Average Standard Cost: £{avg_standard:.2f}")

            # Economy_7 comparison
            if 'economy_7_optimized_cost' in merged_df.columns:
                valid_e7 = merged_df.dropna(subset=['cost_Standard', 'economy_7_optimized_cost'])
                if not valid_e7.empty:
                    avg_e7_optimized = valid_e7['economy_7_optimized_cost'].mean()
                    savings_e7_pct = (avg_standard - avg_e7_optimized) / avg_standard * 100
                    print(f"Average Economy_7 Optimized Cost: £{avg_e7_optimized:.2f}")
                    print(f"Economy_7 Savings: {savings_e7_pct:.1f}%")

            # Economy_10 comparison
            if 'economy_10_optimized_cost' in merged_df.columns:
                valid_e10 = merged_df.dropna(subset=['cost_Standard', 'economy_10_optimized_cost'])
                if not valid_e10.empty:
                    avg_e10_optimized = valid_e10['economy_10_optimized_cost'].mean()
                    savings_e10_pct = (avg_standard - avg_e10_optimized) / avg_standard * 100
                    print(f"Average Economy_10 Optimized Cost: £{avg_e10_optimized:.2f}")
                    print(f"Economy_10 Savings: {savings_e10_pct:.1f}%")

if __name__ == "__main__":
    main()
