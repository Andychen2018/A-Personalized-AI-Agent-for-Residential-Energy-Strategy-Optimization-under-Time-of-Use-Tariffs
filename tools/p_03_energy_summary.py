
import os
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Image

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

def summarize_tariff_results_and_visualize(output_dir="./output/03_cost_cal"):
    print("=== Tariff Summary and Visualization ===")

    cost_file = os.path.join(output_dir, "03_appliance_run_costs_real.csv")
    if not os.path.exists(cost_file):
        raise FileNotFoundError(f"{cost_file} not found.")

    df = pd.read_csv(cost_file, parse_dates=["start_time", "end_time"])
    df["month"] = df["start_time"].dt.to_period("M").astype(str)

    # Summary 1: total monthly cost and energy
    monthly_total = df.groupby("month")[[ 
        "cost_Standard", "cost_Economy_7", "cost_Economy_10",
        "energy_Standard", "energy_Economy_7", "energy_Economy_10"
    ]].sum().reset_index()

    # Summary 2: monthly per appliance
    monthly_by_appliance = df.groupby(["appliance_ID", "appliance_name", "month"])[[
        "cost_Standard", "cost_Economy_7", "cost_Economy_10",
        "energy_Standard", "energy_Economy_7", "energy_Economy_10"
    ]].sum().reset_index()

    # Summary 3: shiftability-wise aggregation
    by_shiftability = df.groupby("Shiftability")[[ 
        "cost_Standard", "cost_Economy_7", "cost_Economy_10",
        "energy_Standard", "energy_Economy_7", "energy_Economy_10"
    ]].sum().reset_index()

    # Summary 4: recommended tariff
    total_costs = df[["cost_Standard", "cost_Economy_7", "cost_Economy_10"]].sum()
    recommended_tariff = total_costs.idxmin().replace("cost_", "")

    # Save summaries
    os.makedirs(output_dir, exist_ok=True)
    monthly_total_path = os.path.join(output_dir, "06_monthly_total_summary.csv")
    monthly_by_appliance_path = os.path.join(output_dir, "07_monthly_by_appliance.csv")
    shiftability_path = os.path.join(output_dir, "08_cost_by_shiftability.csv")
    recommendation_path = os.path.join(output_dir, "09_recommended_tariff.txt")

    monthly_total.to_csv(monthly_total_path, index=False)
    monthly_by_appliance.to_csv(monthly_by_appliance_path, index=False)
    by_shiftability.to_csv(shiftability_path, index=False)
    with open(recommendation_path, "w") as f:
        f.write(f"Recommended Tariff: {recommended_tariff}\n")

    # Plot only one useful chart
    def save_plot(data, x, ys, title, fname):
        plt.figure(figsize=(12, 5))
        for y in ys:
            plt.plot(data[x], data[y], label=y.replace("cost_", "").replace("_", " "), marker='o')
        plt.title(title)
        plt.xlabel(x)
        plt.ylabel("Cost (GBP)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        save_path = os.path.join(output_dir, fname)
        plt.savefig(save_path)
        plt.close()
        display(Image(filename=save_path))

    save_plot(monthly_total, "month",
              ["cost_Standard", "cost_Economy_7", "cost_Economy_10"],
              "Monthly Electricity Cost Comparison",
              "plot_monthly_costs.png")

    # Display saved CSVs
    print("✅ Monthly Total Summary:")
    display(pd.read_csv(monthly_total_path).head())

    print("✅ Monthly by Appliance:")
    display(pd.read_csv(monthly_by_appliance_path).head())

    print("✅ Summary by Shiftability:")
    display(pd.read_csv(shiftability_path))

    print("✔️ All results saved to:", output_dir)
    print("✔️ Recommended Tariff:", recommended_tariff)
    return recommended_tariff

