# Gurobi-based Smart Home Energy Optimization

##  **Important: Gurobi License Required**

**This code requires Gurobi Optimizer with a valid license to run.**

- **Academic License**: Free for academic research (requires university email verification)
- **Commercial License**: Required for commercial use
- **Get License**: Visit [Gurobi License Center](https://www.gurobi.com/downloads/licenses/)
- **Installation Guide**: [Gurobi Installation Instructions](https://www.gurobi.com/documentation/quickstart.html)

Without a valid Gurobi license, the optimization code will not execute.

---

This repository contains the implementation of a Mixed Integer Linear Programming (MILP) optimization system using Gurobi for smart home energy management. The system optimizes the scheduling of household appliances to minimize electricity costs under different tariff structures.

##  Overview

The optimization system processes household energy consumption data and reschedules appliance usage to minimize costs while respecting operational constraints. It supports two UK electricity tariff structures:
- **Economy 7**: 7-hour off-peak period
- **Economy 10**: 10-hour off-peak period

##  System Architecture

```
Input: Household appliance events → Gurobi MILP Optimizer → Optimized schedules → Cost Analysis
```

## File Structure

```
gurobi/
├── gurobi_optimizer.py          # Core MILP optimization engine
├── cost_calculator.py           # Cost calculation for original vs optimized schedules  
├── run_optimization.py          # Main execution script for batch processing
├── show_results.py              # Display optimization results in table format
├── generate_summary.py          # Generate statistical summaries and analysis
├── tariff_config.json           # Electricity tariff configuration
├── results/                     # Optimization results
│   ├── Economy_7/              # Results for Economy 7 tariff (19 households)
│   ├── Economy_10/             # Results for Economy 10 tariff (19 households)
│   └── *.csv                   # Summary tables and statistics
└── README.md                   # This file
```



##  Results

The system has been tested on 19 UK households with the following key findings:

| Metric | Economy 7 | Economy 10 | Improvement |
|--------|-----------|------------|-------------|
| **Average Savings Rate** | 8.33% | 11.79% | +3.46% |
| **Overall Savings Rate** | 8.97% | 13.10% | +4.13% |
| **Best Performance** | 7 households | 12 households | 63.2% prefer E10 |


##  Technical Details

### Optimization Model
- **Objective**: Minimize total electricity cost
- **Variables**: Binary scheduling decisions for each appliance event
- **Constraints**: 
  - Appliance operational windows
  - Power consumption limits
  - Temporal dependencies
  - User comfort requirements

### Key Features
- **Flexible time windows**: Respects appliance-specific scheduling constraints
- **Multi-tariff support**: Handles different electricity pricing structures
- **Scalable processing**: Batch optimization for multiple households
- **Comprehensive analysis**: Detailed cost breakdown and savings calculation

##  Performance Metrics

The system evaluates performance using:
- **Absolute cost savings** (£)
- **Percentage savings rate** (%)
- **Optimization success rate**
- **Computational efficiency**

