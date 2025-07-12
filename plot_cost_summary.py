import json
import pandas as pd
import matplotlib.pyplot as plt
import os


def ensure_output_dir():
    os.makedirs("./output/07_cost_analysis", exist_ok=True)


def generate_appliance_cost_barplot():
    with open("./output/07_cost_analysis/cost_analysis_summary.json", "r") as f:
        cost_data = json.load(f)

    apps = [f"Appliance{i}" for i in range(1, 10)]
    e7 = cost_data["appliance_costs"]["Economy_7"]
    e10 = cost_data["appliance_costs"]["Economy_10"]

    df_appliances = pd.DataFrame({"Appliance": apps})
    df_appliances["Economy_7_Original_cost"] = [
        e7["Non_shifted"].get(app, 0) + e7["Shifted_original"].get(app, 0) for app in apps
    ]
    df_appliances["Economy_7_Optimized_cost"] = [
        e7["Non_shifted"].get(app, 0) + e7["Shifted_after_migration"].get(app, 0) for app in apps
    ]
    df_appliances["Economy_10_Original_cost"] = [
        e10["Non_shifted"].get(app, 0) + e10["Shifted_original"].get(app, 0) for app in apps
    ]
    df_appliances["Economy_10_Optimized_cost"] = [
        e10["Non_shifted"].get(app, 0) + e10["Shifted_after_migration"].get(app, 0) for app in apps
    ]

    df_std = pd.read_csv("./output/03_cost_cal/05_appliance_run_costs_summary.csv")
    df_std["Appliance"] = df_std["label"].str.extract(r"(Appliance\d+)")
    df_std = df_std[df_std["Appliance"].isin(apps)][["Appliance", "cost_Standard"]]
    df_std.rename(columns={"cost_Standard": "Standard_cost"}, inplace=True)

    df_appliances = df_appliances.merge(df_std, on="Appliance")
    df_appliances = df_appliances[[
        "Appliance", "Standard_cost",
        "Economy_7_Original_cost", "Economy_7_Optimized_cost",
        "Economy_10_Original_cost", "Economy_10_Optimized_cost"
    ]]

    colors = ["#ebd49c", "#d6e4cc", "#96b4d3", "#dbc6e0", "#9b72aa"]

    plt.figure(figsize=(14, 6))
    bar_width = 0.15
    x = range(len(df_appliances))
    labels = df_appliances["Appliance"]

    for i, (col, color) in enumerate(zip(df_appliances.columns[1:], colors)):
        plt.bar([p + i * bar_width for p in x], df_appliances[col], width=bar_width, label=col, color=color)

    plt.xticks([p + 2 * bar_width for p in x], labels, rotation=0)
    plt.ylabel("Cost (£)")
    plt.title("Appliance-level Electricity Cost Comparison under Different Scheduling Strategies")
    plt.legend()
    plt.grid(True, axis="y", linestyle="--", alpha=0.6)
    plt.tight_layout()

    plt.savefig("./output/07_cost_analysis/appliance_cost_comparison_barplot.png", dpi=600)
    df_appliances.to_csv("./output/07_cost_analysis/appliance_cost_comparison.csv", index=False)
    print("✅ 成功保存图像和数据：appliance_cost_comparison_barplot.png / .csv")
    plt.close()


def generate_monthly_cost_lineplot():
    with open("./output/07_cost_analysis/cost_analysis_summary.json", "r") as f:
        cost_data = json.load(f)

    monthly_e7 = cost_data["monthly_costs"]["Economy_7"]
    monthly_e10 = cost_data["monthly_costs"]["Economy_10"]
    months = list(monthly_e7["Non_shifted"].keys())

    df_costs = pd.DataFrame({
        "month": months,
        "Economy_7_Original_cost": [monthly_e7["Non_shifted"][m] + monthly_e7["Shifted_original"].get(m, 0) for m in months],
        "Economy_7_Optimized_cost": [monthly_e7["Non_shifted"][m] + monthly_e7["Shifted_after_migration"].get(m, 0) for m in months],
        "Economy_10_Original_cost": [monthly_e10["Non_shifted"][m] + monthly_e10["Shifted_original"].get(m, 0) for m in months],
        "Economy_10_Optimized_cost": [monthly_e10["Non_shifted"][m] + monthly_e10["Shifted_after_migration"].get(m, 0) for m in months]
    })

    df_std = pd.read_csv("./output/03_cost_cal/06_monthly_total_summary.csv")
    df_costs = df_costs.merge(df_std[["month", "cost_Standard"]], on="month")
    df_costs.rename(columns={"cost_Standard": "Standard_cost"}, inplace=True)

    df_costs.to_csv("./output/07_cost_analysis/monthly_cost_comparison.csv", index=False)
    print("✅ 成功保存 CSV：monthly_cost_comparison.csv")

    line_colors = {
        "Standard_cost": "#ebd49c",
        "Economy_7_Original_cost": "#d6e4cc",
        "Economy_7_Optimized_cost": "#96b4d3",
        "Economy_10_Original_cost": "#dbc6e0",
        "Economy_10_Optimized_cost": "#9b72aa"
    }

    plt.figure(figsize=(12, 6))
    for col in line_colors:
        plt.plot(df_costs["month"], df_costs[col], marker="o", label=col, color=line_colors[col])

    plt.xlabel("Month")
    plt.ylabel("Monthly Cost (£)")
    plt.title("Monthly Electricity Cost Comparison under Different Tariff and Scheduling Strategies")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig("./output/07_cost_analysis/monthly_cost_comparison_plot.png", dpi=600)
    print("✅ 成功保存图像：monthly_cost_comparison_plot.png")
    plt.close()


if __name__ == "__main__":
    ensure_output_dir()
    generate_appliance_cost_barplot()
    generate_monthly_cost_lineplot()
    print("🎉 所有图表和数据生成完毕。")

