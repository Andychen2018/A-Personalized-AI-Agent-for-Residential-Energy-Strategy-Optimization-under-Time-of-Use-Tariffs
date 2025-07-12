import os
import json
import pandas as pd
from tools.p_051_base_scheduler import run_scheduler_tool as process_051
from tools.p_052_conflict_resolver import resolve_conflicts_for_all as process_052
from tools.p_053_tariff_input_builder import process_event_data as process_053
from tools.p_054_tariff_cost_analyzer import process as process_054

def peak_valley_tariff_appliance_scheduling_analyzer_tool():
    process_051()
    process_052()
    process_053()
    process_054()

if __name__ == "__main__":
    peak_valley_tariff_appliance_scheduling_analyzer_tool()
