#!/usr/bin/env python3
"""
Plot appliance-level electricity cost comparison (grouped bar chart) for a household,
aggregating across all months.

This complements tools/plot_monthly_cost_comparison.py (which plots lines by month).
Here we produce a single figure per house showing, for each appliance:
- Standard_cost
- Economy_7_Original_cost
- Economy_7_Optimized_cost
- Economy_10_Original_cost
- Economy_10_Optimized_cost

Data sources (existing outputs; no changes to other code required):
- Original monthly per-appliance costs:
  output/03_cost_analysis/UK/<house>/07_monthly_by_appliance.csv
- Optimized per-event costs after scheduling (aggregate to per-appliance total):
  output/06_cost_cal/UK/Economy_7/<house>/{migrated_costs.csv, non_migrated_costs.csv}
  output/06_cost_cal/UK/Economy_10/<house>/{migrated_costs.csv, non_migrated_costs.csv}

Output:
  output/Monthly_cost_trends/<house>/appliance_cost_comparison.png

Usage examples:
  python tools/plot_monthly_appliance_cost_bars.py --house house1
  python tools/plot_monthly_appliance_cost_bars.py --all
"""

from __future__ import annotations

import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from typing import Dict, List, Optional, Tuple

# ---------------------- Matplotlib style (academic) ----------------------
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'Times', 'Liberation Serif', 'DejaVu Serif', 'serif']
rcParams['font.size'] = 12
rcParams['axes.labelsize'] = 13
rcParams['axes.titlesize'] = 16
rcParams['legend.fontsize'] = 11
rcParams['axes.linewidth'] = 1.2
rcParams['grid.linewidth'] = 0.6
rcParams['lines.linewidth'] = 1.8

# ---------------------- Paths ----------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_BASE = os.path.join(BASE_DIR, 'output')
COST_ANALYSIS_BASE = os.path.join(OUTPUT_BASE, '03_cost_analysis', 'UK')
COST_CAL_BASE = os.path.join(OUTPUT_BASE, '06_cost_cal', 'UK')
# Save under the same folder as other monthly trend plots
OUT_DIR_BASE = os.path.join(OUTPUT_BASE, 'Monthly_cost_trends')

# ---------------------- Helpers ----------------------

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def list_houses() -> List[str]:
    houses = []
    if os.path.exists(COST_ANALYSIS_BASE):
        for d in os.listdir(COST_ANALYSIS_BASE):
            if d.startswith('house') and os.path.isdir(os.path.join(COST_ANALYSIS_BASE, d)):
                houses.append(d)
    def hnum(h):
        try:
            return int(h.replace('house', ''))
        except Exception:
            return 1 << 30
    return sorted(houses, key=hnum)


def _month_str_from_ts(ts: pd.Timestamp) -> str:
    return pd.to_datetime(ts).to_period('M').strftime('%Y-%m')


# ---------------------- Loaders ----------------------

def load_monthly_by_appliance(house: str) -> pd.DataFrame:
    """Load original monthly per-appliance cost table.
    Returns columns: appliance_id, appliance_name, month (str YYYY-MM),
    cost_Standard, cost_Economy_7, cost_Economy_10 (if present).
    """
    p = os.path.join(COST_ANALYSIS_BASE, house, '07_monthly_by_appliance.csv')
    if not os.path.exists(p):
        raise FileNotFoundError(f"Not found: {p}. Please run tariff modeling first.")
    df = pd.read_csv(p)
    # Normalize month to YYYY-MM string
    if 'month' in df.columns:
        try:
            df['month'] = pd.to_datetime(df['month']).dt.to_period('M').astype(str)
        except Exception:
            df['month'] = df['month'].astype(str)
    else:
        raise ValueError('07_monthly_by_appliance.csv missing month column')
    # Ensure appliance name
    if 'appliance_name' not in df.columns:
        # fallback to appliance_id as name
        df['appliance_name'] = df.get('appliance_id', 'appliance')
    return df


def _load_cost_cal_csvs(house: str, tariff: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load migrated and non-migrated cost tables for a tariff. Return (mig, non)."""
    base = os.path.join(COST_CAL_BASE, tariff, house)
    mig = os.path.join(base, 'migrated_costs.csv')
    non = os.path.join(base, 'non_migrated_costs.csv')
    df_mig = pd.read_csv(mig) if os.path.exists(mig) else None
    df_non = pd.read_csv(non) if os.path.exists(non) else None
    return df_mig, df_non


def compute_optimized_by_appliance_total(house: str, tariff: str) -> pd.DataFrame:
    """Aggregate optimized and original costs per APPLIANCE across ALL months.
    Returns DataFrame with columns: appliance_name, optimized_cost, original_cost.
    """
    df_mig, df_non = _load_cost_cal_csvs(house, tariff)
    if df_mig is None and df_non is None:
        return pd.DataFrame(columns=['appliance_name', 'optimized_cost', 'original_cost'])

    frames = []
    # Non-migrated: total_cost counts for both original and optimized (unchanged)
    if df_non is not None and not df_non.empty:
        df_non['appliance_name'] = df_non.get('appliance_name', 'Unknown')
        g = df_non.groupby(['appliance_name'], as_index=False)['total_cost'].sum()
        g.rename(columns={'total_cost': 'optimized_cost'}, inplace=True)
        g['original_cost'] = g['optimized_cost']
        frames.append(g)

    # Migrated: optimized uses sched_total_cost; original uses orig_total_cost
    if df_mig is not None and not df_mig.empty:
        df_mig['appliance_name'] = df_mig.get('appliance_name', 'Unknown')
        part = df_mig.groupby(['appliance_name'], as_index=False)[['sched_total_cost', 'orig_total_cost']].sum()
        part.rename(columns={'sched_total_cost': 'optimized_cost', 'orig_total_cost': 'original_cost'}, inplace=True)
        frames.append(part)

    if not frames:
        return pd.DataFrame(columns=['appliance_name', 'optimized_cost', 'original_cost'])

    df = pd.concat(frames, ignore_index=True)
    df = df.groupby(['appliance_name'], as_index=False).sum()
    return df


# ---------------------- Merge and plotting ----------------------

def build_appliance_total_table(house: str) -> pd.DataFrame:
    """Build a per‑appliance TOTAL table across all months with columns:
       appliance_name, Standard_cost, Economy_7_Original_cost, Economy_7_Optimized_cost,
       Economy_10_Original_cost, Economy_10_Optimized_cost.
    """
    orig = load_monthly_by_appliance(house)
    # Sum across months for original costs
    base = (orig.groupby('appliance_name', as_index=False)[['cost_Standard','cost_Economy_7','cost_Economy_10']]
                .sum()
                .rename(columns={'cost_Standard':'Standard_cost',
                                 'cost_Economy_7':'Economy_7_Original_cost',
                                 'cost_Economy_10':'Economy_10_Original_cost'}))

    # Optimized totals from 06_cost_cal
    e7_tot = compute_optimized_by_appliance_total(house, 'Economy_7')
    e10_tot = compute_optimized_by_appliance_total(house, 'Economy_10')

    if not e7_tot.empty:
        base = base.merge(e7_tot[['appliance_name','optimized_cost']]
                          .rename(columns={'optimized_cost':'Economy_7_Optimized_cost'}),
                          on='appliance_name', how='left')
    else:
        base['Economy_7_Optimized_cost'] = 0.0

    if not e10_tot.empty:
        base = base.merge(e10_tot[['appliance_name','optimized_cost']]
                          .rename(columns={'optimized_cost':'Economy_10_Optimized_cost'}),
                          on='appliance_name', how='left')
    else:
        base['Economy_10_Optimized_cost'] = 0.0

    base = base.fillna(0.0)

    # Normalize appliance order and labels strictly by numeric ID in the name
    def extract_num(name: str, fallback: int) -> int:
        import re
        m = re.search(r"(appliance|device|app)\s*(\d+)", str(name), flags=re.I)
        return int(m.group(2)) if m else (fallback + 1)

    base['__num__'] = [extract_num(n, i) for i, n in enumerate(base['appliance_name'])]
    base = base.sort_values('__num__', ascending=True).reset_index(drop=True)
    base['__label__'] = [f"Appliance{num}" for num in base['__num__']]
    base = base.drop(columns=['__num__'])
    return base


def plot_appliance_total_bars(df: pd.DataFrame, house: str, out_path: str):
    labels = df['__label__'].astype(str).tolist()
    n = len(labels)

    # Colors to match reference figure
    colors = {
        'Standard_cost': '#E6D470',            # pale yellow similar to figure
        'Economy_7_Original_cost': '#9CC3E4',  # light blue
        'Economy_7_Optimized_cost': '#6E8EBF', # steel/medium blue
        'Economy_10_Original_cost': '#C8A0D8', # light plum
        'Economy_10_Optimized_cost': '#9C86D7' # medium slate purple
    }

    series = [
        'Standard_cost',
        'Economy_7_Original_cost',
        'Economy_7_Optimized_cost',
        'Economy_10_Original_cost',
        'Economy_10_Optimized_cost',
    ]

    x = np.arange(n)
    width = max(0.8 / len(series), 0.12)

    fig_w = max(14, min(30, 0.6 * n + 8))
    fig_h = 6
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    for i, col in enumerate(series):
        if col not in df.columns:
            continue
        ax.bar(x + (i - (len(series)-1)/2)*width, df[col].values, width=width,
               label=col, color=colors.get(col, '#888888'), edgecolor='black', linewidth=0.6, alpha=0.95)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha='center')
    ax.set_ylabel('Cost (£)')
    ax.set_title('Appliance-level Electricity Cost Comparison under Different Scheduling Strategies')
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.set_ylim(bottom=0)

    # Legend styling
    leg = ax.legend(loc='upper left', ncol=1, framealpha=0.95, fancybox=True, shadow=False)
    leg.get_frame().set_facecolor('white')
    leg.get_frame().set_edgecolor('black')

    plt.tight_layout()
    ensure_dir(os.path.dirname(out_path))
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved: {out_path}")


# ---------------------- CLI ----------------------

def main():
    parser = argparse.ArgumentParser(description='Plot appliance-level cost bars per household (across all months).')
    parser.add_argument('--house', type=str, help='House ID like house1')
    parser.add_argument('--all', action='store_true', help='Process all houses')
    args = parser.parse_args()

    houses = [args.house] if args.house else (list_houses() if args.all else [])
    if not houses:
        print('Please specify --house houseX or --all')
        return

    for house in houses:
        try:
            _ = load_monthly_by_appliance(house)  # validate data exists
            table = build_appliance_total_table(house)
            out_dir = os.path.join(OUT_DIR_BASE, house)
            out_path = os.path.join(out_dir, 'appliance_cost_comparison.png')
            plot_appliance_total_bars(table, house, out_path)
        except Exception as e:
            print(f"❌ Failed to plot {house}: {e}")


if __name__ == '__main__':
    main()

