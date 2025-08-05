
import os
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List
import glob

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

def summarize_tariff_results_and_visualize(
    house_id: str,
    tariff_type: str = "UK",
    output_dir: str = "./output/03_cost_analysis"
):
    """
    Summarize and visualize tariff results for a specific house and tariff type

    Args:
        house_id: House identifier (e.g., "house1")
        tariff_type: Type of tariff ("UK", "Germany", "California")
        output_dir: Base output directory
    """
    print(f"=== Tariff Summary and Visualization for {house_id.upper()} ({tariff_type}) ===")

    # Construct house-specific path
    house_output_dir = os.path.join(output_dir, tariff_type, house_id)
    cost_file = os.path.join(house_output_dir, "03_appliance_run_costs_real.csv")

    if not os.path.exists(cost_file):
        raise FileNotFoundError(f"Cost file not found: {cost_file}")

    df = pd.read_csv(cost_file, parse_dates=["start_time", "end_time"])
    df["month"] = df["start_time"].dt.to_period("M").astype(str)

    # Get all cost and energy columns dynamically
    cost_columns = [col for col in df.columns if col.startswith("cost_")]
    energy_columns = [col for col in df.columns if col.startswith("energy_")]

    if not cost_columns:
        print("⚠️ No cost columns found in the data")
        return

    print(f"📊 Found tariff schemes: {[col.replace('cost_', '') for col in cost_columns]}")

    # Summary 4: recommended tariff
    total_costs = df[cost_columns].sum()
    recommended_tariff = total_costs.idxmin().replace("cost_", "")

    # Files are already saved by simulate_tariff_cost_detailed, just read them
    monthly_total_path = os.path.join(house_output_dir, "06_monthly_total_summary.csv")
    monthly_by_appliance_path = os.path.join(house_output_dir, "07_monthly_by_appliance.csv")
    shiftability_path = os.path.join(house_output_dir, "08_cost_by_shiftability.csv")
    recommendation_path = os.path.join(house_output_dir, "09_recommended_tariff.txt")

    # Visualization
    def save_plot(data, x_col, y_cols, title, fname):
        if data.empty or not y_cols:
            print(f"⚠️ No data to plot for {title}")
            return

        plt.figure(figsize=(12, 6))
        for col in y_cols:
            if col in data.columns:
                plt.plot(data[x_col], data[col], marker='o', label=col.replace("cost_", ""))
        plt.title(f"{title} - {house_id.upper()} ({tariff_type})")
        plt.xlabel(x_col.capitalize())
        plt.ylabel("Cost ($)")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        save_path = os.path.join(house_output_dir, fname)
        plt.savefig(save_path)
        plt.close()
        print(f"📊 Plot saved: {save_path}")

    # Read monthly data for plotting
    if os.path.exists(monthly_total_path):
        monthly_total = pd.read_csv(monthly_total_path)
        # Create cost comparison plot
        save_plot(monthly_total, "month", cost_columns,
                  "Monthly Total Cost Comparison", "monthly_cost_comparison.png")

    # Display summaries
    print(f"\n✅ Monthly Total Summary for {house_id.upper()}:")
    if os.path.exists(monthly_total_path):
        print(pd.read_csv(monthly_total_path).head().to_string())

    print(f"\n✅ Recommended Tariff for {house_id.upper()}: {recommended_tariff}")

    # Display cost comparison
    print(f"\n💰 Total Cost Comparison for {house_id.upper()}:")
    for col in cost_columns:
        tariff_name = col.replace("cost_", "")
        print(f"  {tariff_name}: ${total_costs[col]:.2f}")

    print(f"\n📁 All results saved to: {house_output_dir}")

    return {
        'house_id': house_id,
        'tariff_type': tariff_type,
        'recommended_tariff': recommended_tariff,
        'total_costs': total_costs.to_dict(),
        'output_dir': house_output_dir
    }


def batch_summarize_tariff_results(
    house_data_dict: dict,
    tariff_type: str = "UK",
    output_dir: str = "./output/03_cost_analysis"
) -> dict:
    """
    Batch summarize tariff results for multiple households

    Args:
        house_data_dict: Dictionary mapping house_id to house info
        tariff_type: Type of tariff ("UK", "Germany", "California")
        output_dir: Base output directory

    Returns:
        Dictionary mapping house_id to summary results
    """
    results = {}
    failed_houses = []

    print(f"🚀 Starting batch tariff summary for {len(house_data_dict)} households...")
    print(f"📊 Tariff type: {tariff_type}")
    print("=" * 80)

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Summarizing {house_id}...")

            result = summarize_tariff_results_and_visualize(
                house_id=house_id,
                tariff_type=tariff_type,
                output_dir=output_dir
            )

            results[house_id] = result
            print(f"✅ {house_id} summary completed!")

        except Exception as e:
            print(f"❌ Error summarizing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Overall summary
    print(f"\n🎉 Batch tariff summary completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for failed_house in failed_houses:
            print(f"  - {failed_house}")

    # Display recommendations summary
    print(f"\n📊 Tariff Recommendations Summary ({tariff_type}):")
    print("-" * 60)
    for house_id, result in results.items():
        if isinstance(result, dict) and 'recommended_tariff' in result:
            recommended = result['recommended_tariff']
            total_cost = min(result['total_costs'].values()) if result['total_costs'] else 0
            print(f"  {house_id}: {recommended} (${total_cost:.2f})")

    return results

