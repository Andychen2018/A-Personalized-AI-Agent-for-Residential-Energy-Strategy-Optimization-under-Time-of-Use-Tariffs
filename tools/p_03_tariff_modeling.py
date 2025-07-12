


import json
import pandas as pd
import os
from typing import Tuple

def simulate_tariff_cost_detailed(
    event_csv: str,
    power_csv: str,
    output_dir: str = "./output/03_cost_cal"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    os.makedirs(output_dir, exist_ok=True)

    # 读取数据
    power_df = pd.read_csv(power_csv, parse_dates=["Time"])
    power_df.set_index("Time", inplace=True)

    run_df = pd.read_csv(event_csv, parse_dates=["start_time", "end_time"])

    # 名称映射
    # ✅ 从 shiftable label 表中读取 appliance 映射关系
    label_df = pd.read_csv("./output/02_behavior_modeling/02_1_appliance_shiftable_label.csv")
    name_to_appliance_id = dict(zip(label_df["ChineseName"], label_df["ApplianceID"]))

    

    run_df["appliance_id"] = run_df["appliance_name"].map(name_to_appliance_id)
    run_df["label"] = run_df["appliance_id"] + " (" + run_df["appliance_name"] + ")"
    run_df["month"] = run_df["start_time"].dt.to_period("M").astype(str)

    # 定义电价模式

    def get_price_schedule(mode):
        with open("./config/tariff_config.json", "r") as f:
            tariff_config = json.load(f)

        config = tariff_config.get(mode)
        if not config:
            raise ValueError(f"Unknown tariff mode: {mode}")

        if config["type"] == "flat":
            return [(0, 24, config["rate"])]

        elif config["type"] == "time_based":
            low_periods = []
            for start, end in config["low_periods"]:
                s = int(start.split(":")[0]) + int(start.split(":")[1]) / 60
                e = int(end.split(":")[0]) + int(end.split(":")[1]) / 60
                low_periods.append((s, e, config["low_rate"]))

            # 构建完整的24小时 schedule
            schedule = []
            low_periods.sort()
            last_end = 0
            for s, e, r in low_periods:
                if s > last_end:
                    schedule.append((last_end, s, config["high_rate"]))
                schedule.append((s, e, r))
                last_end = max(last_end, e)
            if last_end < 24:
                schedule.append((last_end, 24, config["high_rate"]))
            return schedule

        else:
            raise ValueError(f"Unsupported tariff type: {config['type']}")

    
    # 单段成本与能耗
    def compute_cost_and_energy(row, schedule):
        col = row["appliance_id"]
        if pd.isna(col) or col not in power_df.columns:
            return 0.0, 0.0

        segment = power_df.loc[row["start_time"]:row["end_time"]]
        if segment.empty or col not in segment.columns:
            return 0.0, 0.0

        cost = 0.0
        energy = 0.0
        for t, p in segment[col].items():
            hour = t.hour + t.minute / 60.0
            price = next((r for s, e, r in schedule if s <= hour < e), 0.3)
            cost += (p / 1000) * (1 / 60) * price
            energy += (p / 1000) * (1 / 60)
        return round(cost, 4), round(energy, 4)

    # 计算三种电价下的值
    for mode in ["Standard", "Economy_7", "Economy_10"]:
        schedule = get_price_schedule(mode)
        run_df[[f"cost_{mode}", f"energy_{mode}"]] = run_df.apply(
            lambda row: pd.Series(compute_cost_and_energy(row, schedule)), axis=1
        )

    # ------------------------------------------
    # 汇总：每个电器总费用与能耗
    summary = run_df.groupby("label")[[
        "cost_Standard", "cost_Economy_7", "cost_Economy_10",
        "energy_Standard", "energy_Economy_7", "energy_Economy_10"
    ]].sum().round(2)
    summary.loc["Total"] = summary.sum()
    summary.to_csv(f"{output_dir}/05_appliance_run_costs_summary.csv")

    # 保存主表
    run_df.to_csv(f"{output_dir}/03_appliance_run_costs_real.csv", index=False)

    # ------------------------------------------
    # 每月总费用与能耗
    monthly_total = run_df.groupby("month")[[
        "cost_Standard", "cost_Economy_7", "cost_Economy_10",
        "energy_Standard", "energy_Economy_7", "energy_Economy_10"
    ]].sum().reset_index()
    monthly_total.to_csv(f"{output_dir}/06_monthly_total_summary.csv", index=False)

    # 每月每电器费用与能耗
    monthly_by_appliance = run_df.groupby(["appliance_id", "appliance_name", "month"])[[
        "cost_Standard", "cost_Economy_7", "cost_Economy_10",
        "energy_Standard", "energy_Economy_7", "energy_Economy_10"
    ]].sum().reset_index()
    monthly_by_appliance.to_csv(f"{output_dir}/07_monthly_by_appliance.csv", index=False)

    # Shiftability 类型聚合
    if "Shiftability" in run_df.columns:
        by_shiftability = run_df.groupby("Shiftability")[[
            "cost_Standard", "cost_Economy_7", "cost_Economy_10",
            "energy_Standard", "energy_Economy_7", "energy_Economy_10"
        ]].sum().reset_index()
        by_shiftability.to_csv(f"{output_dir}/08_cost_by_shiftability.csv", index=False)
    else:
        by_shiftability = pd.DataFrame()

    # 推荐电价策略
    total_costs = run_df[["cost_Standard", "cost_Economy_7", "cost_Economy_10"]].sum()
    recommended_tariff = total_costs.idxmin().replace("cost_", "")
    with open(f"{output_dir}/09_recommended_tariff.txt", "w") as f:
        f.write(f"Recommended Tariff: {recommended_tariff}\n")

    # 提示信息
    # Prompt information
    print("✅ Cost and energy consumption analysis completed. Results saved to:", output_dir)
    print("📊 Summary:", summary.tail(1).to_dict())
    print("🎯 Recommended tariff scheme:", recommended_tariff)

    # print("✅ 成本与用电量分析完成，结果保存至:", output_dir)
    # print("📊 汇总：", summary.tail(1).to_dict())
    # print("🎯 推荐电价方案:", recommended_tariff)

    return run_df, summary
