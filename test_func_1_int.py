import pandas as pd
import json
import os
from rich import print
from rich.console import Console
from rich.table import Table

def agent_tariff_cost_summary_and_recommendation():
    
    original_cost_summary_csv_path = './output/03_cost_cal/05_appliance_run_costs_summary.csv'
    json_path = './output/07_cost_analysis/cost_analysis_summary.json'

    if not os.path.exists(original_cost_summary_csv_path):
        print(f"[red]❌ File not found: {original_cost_summary_csv_path}[/red]")
        return
    elif not os.path.exists(json_path):
        print(f"[red]❌ File not found: {json_path}[/red]")
        return

    df = pd.read_csv(original_cost_summary_csv_path)
    df_total = df.tail(1)

    df_original = pd.DataFrame({
        "Tariff Scheme": ["Standard", "Economy 7", "Economy 10"],
        "Total Cost (£)": [
            df_total["cost_Standard"].values[0],
            df_total["cost_Economy_7"].values[0],
            df_total["cost_Economy_10"].values[0],
        ],
        "Total Energy (kWh)": [
            df_total["energy_Standard"].values[0],
            df_total["energy_Economy_7"].values[0],
            df_total["energy_Economy_10"].values[0],
        ],
        "Version": ["Original"] * 3
    })

    with open(json_path, 'r') as f:
        cost_data = json.load(f)

    opt_eco7_cost = cost_data["total_costs"]["Economy_7"]["overall_cost_after_migration"]
    opt_eco10_cost = cost_data["total_costs"]["Economy_10"]["overall_cost_after_migration"]

    df_optimized = pd.DataFrame({
        "Tariff Scheme": ["Economy 7", "Economy 10"],
        "Total Cost (£)": [opt_eco7_cost, opt_eco10_cost],
        "Total Energy (kWh)": [
            df_total["energy_Economy_7"].values[0],
            df_total["energy_Economy_10"].values[0],
        ],
        "Version": ["Optimized"] * 2
    })

    df_all = pd.concat([df_original, df_optimized], ignore_index=True)
    standard_cost = df_original[df_original["Tariff Scheme"] == "Standard"]["Total Cost (£)"].values[0]
    df_all["Savings Compared to Standard (£)"] = (standard_cost - df_all["Total Cost (£)"]).round(2)

    cols = df_all.columns.tolist()
    cols.insert(1, cols.pop(cols.index("Version")))
    df_all = df_all[cols]

    print("[red]Based on our AI agent's analysis of your household electricity usage patterns,[/red]")
    print("[red]we have calculated the total cost and energy consumption under different scenarios.[/red]")
    print("[red]The results for various tariff schemes are as follows:[/red]\n")

    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    for col in df_all.columns:
        table.add_column(col)
    for _, row in df_all.iterrows():
        table.add_row(*[str(val) for val in row.values])
    console.print(table)

    df_ori = df_all[df_all["Version"] == "Original"]
    df_opt = df_all[df_all["Version"] == "Optimized"]
    best_ori = df_ori.loc[df_ori["Savings Compared to Standard (£)"].idxmax()]
    best_opt = df_opt.loc[df_opt["Savings Compared to Standard (£)"].idxmax()]

    print("\n🤖 [red]So, our final optimizations are: [/red]\n")
    print("In the case where no appliance schedule optimization is applied, based on your electricity usage pattern,")
    print(f"     we recommend you choose the **{best_ori['Tariff Scheme']}** tariff scheme.")
    print(f"     It will save you approximately £{best_ori['Savings Compared to Standard (£)']:.2f} compared to the Standard scheme.\n")
    print("If you allow shifting of some appliances while respecting your runtime constraints,")
    print(f"     we recommend you choose the **{best_opt['Tariff Scheme']}** tariff scheme.")
    print(f"     It will save you approximately £{best_opt['Savings Compared to Standard (£)']:.2f} compared to the Standard scheme.\n")

    print("🤖 [red]By the way, based on your electricity usage habits and the tariff options available,[/red]")
    print("our AI agent has carefully analyzed your data to help you make informed decisions.")
    print("Of course, you're always encouraged to double-check the results and compare them with your actual preferences.")
    print("📂 If you're curious and want to dive deeper into the details, here are some files you might find helpful:\n")
    print("🔸 Want to see the cost of each appliance’s operation *without any schedule adjustments*?")
    print("   ➤ You can check that here: ./output/03_cost_cal/05_appliance_run_costs_summary.csv\n")
    print("🔸 Interested in how your total electricity bill changes *month by month*?")
    print("   ➤ Have a look at: ./output/03_cost_cal/06_monthly_total_summary.csv\n")
    print("🔸 Wondering how much of your usage is from shiftable vs. non-shiftable appliances?")
    print("   ➤ Check this file: ./output/03_cost_cal/08_cost_by_shiftability.csv\n")
    print("🔸 For a high-level summary that compares *optimized* vs *unoptimized* costs:")
    print("   ➤ This one is useful: ./output/07_cost_analysis/cost_analysis_summary.json\n")
    print("🔄 And if you're specifically looking for how much you could save by allowing your appliances to shift their schedules,")
    print("   ➤ That info is also included in: ./output/07_cost_analysis/cost_analysis_summary.json\n")
    print("[red]🤖 If you want to explore which appliance operations were rescheduled to new time slots for cost optimization,[/red]")
    print("you can check the detailed results in the following files:")
    print("  ➤ ./output/05_scheduling/heuristic_Economy_7_resolved.csv")
    print("  ➤ ./output/05_scheduling/heuristic_Economy_10_resolved.csv\n")
    print("In these files:")
    print("  • [bold blue]original_start_time[/bold blue] and [bold blue]original_end_time[/bold blue] indicate the original working time of each appliance event (before any shifting).")
    print("  • [bold blue]shifted_start_datetime[/bold blue] and [bold blue]shifted_end_datetime[/bold blue] represent the optimized time after cost-aware rescheduling.\n")
    print("Note: The rescheduling results may differ between Economy7 and Economy10 tariffs,")
    print("as the agent selects the most cost-effective time slots under each scheme.")
if __name__ == "__main__":
    agent_tariff_cost_summary_and_recommendation()