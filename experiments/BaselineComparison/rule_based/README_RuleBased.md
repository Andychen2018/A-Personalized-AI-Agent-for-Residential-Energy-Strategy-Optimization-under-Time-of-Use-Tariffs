# Rule-Based Optimization Experiment

## Overview

This directory contains the rule-based home energy management optimization experiment code. The experiment uses heuristic rules to shift appliance usage to low-price periods to reduce electricity costs.

## Experiment Objectives

- Implement rule-based load scheduling optimization algorithms
- Calculate electricity costs before and after optimization
- Compare results with Gurobi optimization
- Evaluate cost savings under different tariff structures

## File Structure

### Core Scripts
- **`run_rule_based_optimization.py`** - Main entry script, executes the complete optimization workflow
- **`rule_based_optimizer.py`** - Core logic of the rule-based optimizer
- **`first_event_optimizer.py`** - First event optimizer, handles specific optimization strategies

### Cost Calculation Scripts
- **`calculate_cost_savings.py`** - Calculate cost savings for shifted events
- **`calculate_unshifted_events_cost.py`** - Calculate costs for unshifted events
- **`generate_cost_summary_table.py`** - Generate final cost summary tables

### Monitoring and Utility Tools
- **`generate_partial_summary.py`** - Generate partial progress summaries (for monitoring long-running calculations)
- **`monitor_and_generate_final_table.py`** - Automatically monitor calculation progress and generate final tables

### Results Directory
- **`results/`** - Store all experiment results
  - `Economy_7/` - Results under Economy 7 tariff structure
  - `Economy_10/` - Results under Economy 10 tariff structure
  - `*.csv` - Summary table files
  - `*.json` - Detailed statistical data

## Tariff Configuration

### Economy 7
- **Low-price period**: 00:30-07:30 (£0.15/kWh)
- **High-price period**: 07:30-00:30 (£0.30/kWh)

### Economy 10
- **Low-price periods**:
  - 01:00-06:00 (£0.15/kWh)
  - 13:00-16:00 (£0.15/kWh)
  - 20:00-22:00 (£0.15/kWh)
- **High-price periods**: Other times (£0.30/kWh)

## Usage

### 1. Complete Experiment Workflow

```bash
# Run the complete rule-based optimization experiment
python run_rule_based_optimization.py
```

This will execute the following steps:
1. Load household energy consumption data
2. Apply rule-based optimization algorithms
3. Generate optimization result files

### 2. Cost Calculation

```bash
# Calculate cost savings for shifted events
python calculate_cost_savings.py

# Calculate costs for unshifted events
python calculate_unshifted_events_cost.py --tariff_type Economy_7
python calculate_unshifted_events_cost.py --tariff_type Economy_10
```

### 3. Generate Final Summary

```bash
# Generate complete cost summary tables
python generate_cost_summary_table.py
```

### 4. Monitor Long-Running Calculations

```bash
# Monitor calculation progress and automatically generate final tables
python monitor_and_generate_final_table.py
```

## Output Results

### Main Output Files

1. **`cost_summary_table.csv`** - Main cost summary table
   - Contains original costs, optimized costs, savings amount, and savings rate for each house

2. **`detailed_cost_summary.csv`** - Detailed cost breakdown
   - Contains detailed breakdown of shifted event costs and unshifted event costs

3. **`overall_cost_summary_stats.json`** - Overall statistical data
   - Average savings rate, total savings amount, and other statistical information

### House-Level Results

Each house under each tariff structure has the following files:
- `cost_calculation_summary_houseX_TariffType.json` - Shifted event cost summary
- `unshifted_events_cost_summary_houseX_TariffType.json` - Unshifted event cost summary
- Detailed CSV result files

## Algorithm Description

### Rule-Based Optimization Strategy

1. **Load Identification**: Identify schedulable appliance loads
2. **Time Window Analysis**: Analyze schedulable time windows for each load
3. **Cost Calculation**: Calculate electricity costs for different time periods
4. **Optimization Decision**: Shift loads to the lowest-cost available time slots
5. **Constraint Checking**: Ensure shifted schedules satisfy all constraints

### Comparison with Gurobi

- **Gurobi**: Mathematical optimization, globally optimal solution
- **Rule-based**: Heuristic rules, fast approximate solution
- **Comparison Metrics**: Cost savings, computation time, practicality

## Data Requirements

### Input Data
- Household power consumption data (located in `/output/01_preprocessed/`)
- Appliance event data (located in `/output/02_events/`)
- Optimization result data (from previous optimization steps)

### Data Format
- Power data: Time series CSV files containing timestamps and power values
- Event data: JSON format containing event start time, duration, power, and other information

## Important Notes

1. **Tariff Configuration Consistency**: Ensure the same tariff configuration as Gurobi experiments
2. **Data Integrity**: Ensure all required input data files exist
3. **Computation Time**: Cost calculations for large datasets may take considerable time
4. **Memory Usage**: Pay attention to memory usage when processing large amounts of event data

## Troubleshooting

### Common Issues

1. **File Not Found Error**: Check if data path configuration is correct
2. **Out of Memory**: Reduce batch size or increase system memory
3. **Long Computation Time**: Use monitoring scripts to track progress
4. **Inconsistent Results**: Verify tariff configuration matches reference experiments

### Debugging Suggestions

1. Use `generate_partial_summary.py` to check intermediate results
2. Check log output to understand calculation progress
3. Verify input data integrity and format
4. Compare results on small datasets to validate algorithm correctness

## Extensions and Modifications

### Adding New Tariff Structures
1. Modify the `tariff_config` dictionary in relevant scripts
2. Add new tariff period definitions
3. Update cost calculation logic

### Modifying Optimization Strategies
1. Edit optimization logic in `rule_based_optimizer.py`
2. Adjust load scheduling rules
3. Add new constraint conditions

### Performance Optimization
1. Use parallel processing to accelerate calculations
2. Optimize data loading and processing workflows
3. Implement incremental calculations to avoid redundant work

## About Current Files

### Core Files Confirmation ✅

All 9 Python scripts in the current directory are required:

1. **Main Workflow** (3 files)
   - `run_rule_based_optimization.py` - Main entry point
   - `rule_based_optimizer.py` - Core optimization logic
   - `first_event_optimizer.py` - Specific optimization strategies

2. **Cost Calculation** (3 files)
   - `calculate_cost_savings.py` - Shifted event costs
   - `calculate_unshifted_events_cost.py` - Unshifted event costs
   - `generate_cost_summary_table.py` - Final summary

3. **Monitoring Tools** (2 files)
   - `generate_partial_summary.py` - Progress monitoring
   - `monitor_and_generate_final_table.py` - Automated monitoring

### Optional Cleanup

- `__pycache__/` directory can be deleted (Python will automatically regenerate)
- If re-running experiments, the `results/` directory can be cleared

## Quick Start

```bash


# 2. Run complete experiment
python run_rule_based_optimization.py

# 3. Calculate costs (if needed)
python calculate_cost_savings.py
python calculate_unshifted_events_cost.py --tariff_type Economy_7
python calculate_unshifted_events_cost.py --tariff_type Economy_10

# 4. Generate final summary
python generate_cost_summary_table.py
```

## Version History

- **v1.0**: Initial version with basic rule-based optimization functionality
- **v1.1**: Fixed tariff configuration to match Gurobi consistency
- **v1.2**: Added monitoring and automation tools, improved user experience
- **v1.3**: Code cleanup, removed redundant files, improved documentation
