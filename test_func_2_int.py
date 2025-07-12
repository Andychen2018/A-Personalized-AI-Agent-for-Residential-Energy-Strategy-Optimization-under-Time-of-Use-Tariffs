import os
import sys

# 导入工具函数
from tools.p_01_perception_alignment import preprocess_power_series
from tools.p_02_shiftable_identifier import identify_appliance_shiftability
from tools.p_02_segment_events import run_event_segmentation
from tools.p_02_event_id import add_event_id

from tools.llm_proxy import GPTProxyClient
from tools.p_03_tariff_modeling import simulate_tariff_cost_detailed
from tools.p_03_energy_summary import summarize_tariff_results_and_visualize

def preprocess(user_input):
    preprocess_power_series()
    df_shift = identify_appliance_shiftability(user_input)
    df_result = run_event_segmentation()
    df_event_log = add_event_id()
    return df_event_log


if __name__ == "__main__":
    user_input = """
        Hi, I have several appliances at home:
        Aggregate, Fridge, Chest Freezer, Upright Freezer, Tumble Dryer, Washing Machine, Dishwasher, Computer Site, Television Site, Electric Heater.

        Note: Entry 0 is the aggregated total power of the household and not an actual appliance.
        These devices correspond to Appliance1 through Appliance9 in the dataset and will be used for energy analysis.

        Important:
        1. All appliance names that differ only by a numeric suffix or parenthesis 
        (e.g., "Electric Heater (2)", "Electric Heater(3)") should be treated as the same appliance type 
        as the base name (e.g., "Electric Heater") when determining shiftability.
        2. If an appliance name contains a brand or location descriptor (e.g., "MJY Computer", "Freezer (Utility Room)"),
        use only the core appliance type (e.g., "Computer", "Freezer") to determine shiftability.
        """
    df_event_log = preprocess(user_input)
    