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

