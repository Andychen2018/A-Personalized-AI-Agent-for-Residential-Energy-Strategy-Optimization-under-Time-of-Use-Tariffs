# Timing Uncertainties Robustness Experiment

## Overview

This experiment evaluates the robustness of the smart home energy management system against **timing uncertainties**. In real-world scenarios, appliance events may not occur exactly at their predicted times due to various factors such as user behavior variations, sensor delays, or system latencies. This experiment introduces random timing perturbations (±5 minutes) to appliance events and measures how well the optimization algorithm maintains its cost-saving performance.

## Experiment Objectives

1. **Assess Timing Robustness**: Evaluate how timing uncertainties affect the system's ability to optimize energy costs
2. **Measure Performance Retention**: Calculate the percentage of cost savings retained when events are time-shifted
3. **Statistical Analysis**: Perform statistical tests to determine the significance of performance changes
4. **Benchmark Comparison**: Compare results against expected performance thresholds (95% retention rate)

## Methodology

### Timing Perturbation Strategy
- **Perturbation Range**: ±5 minutes random offset
- **Perturbation Rate**: ~84% of events are perturbed
- **Distribution**: Uniform random distribution within the range
- **Scope**: Applied to schedulable appliance events only

### Test Configuration
- **Tariff Types**: Economy_7, Economy_10
- **Test Houses**: house1, house2, house3, house20, house21
- **Baseline**: Original optimization results without timing uncertainties
- **Comparison**: Perturbed optimization results vs. baseline performance

## Code Organization



## Key Results

### Overall Performance
- **Average Savings Retention Rate**: **97.5%**
- **Expected Threshold**: 95.0%
- **Performance vs. Expectation**: **+2.5%** ✅

### Tariff-Specific Results
| Tariff Type | Avg. Baseline Savings | Avg. Perturbed Savings | Retention Rate | Statistical Significance |
|-------------|----------------------|----------------------|----------------|-------------------------|
| Economy_7   | £136.98             | £133.33              | **97.9%**      | Not significant (p=0.293) |
| Economy_10  | £188.40             | £181.07              | **97.1%**      | Not significant (p=0.272) |

### House-Specific Performance
| House ID | Economy_7 Retention | Economy_10 Retention | Average Retention | Performance Level |
|----------|-------------------|---------------------|------------------|------------------|
| house1   | 99.7%            | 99.9%               | **99.8%**        | Excellent        |
| house2   | 100.3%           | 100.1%              | **100.2%**       | Excellent        |
| house3   | 92.0%            | 90.4%               | **91.2%**        | Good             |
| house20  | 97.4%            | 96.1%               | **96.8%**        | Excellent        |
| house21  | 100.1%           | 99.1%               | **99.6%**        | Excellent        |



### Automated Execution
```bash
cd experiments/Robustness/02Timing_Uncertainties
python run_timing_uncertainty_experiment.py
```

### Manual Step-by-Step Execution
```bash
# Generate timing perturbations
python 00generate_timing_uncertainties.py

# Run optimization pipeline
python 01event_scheduler.py
python 02_collision_resolver.py
python 03_event_splitter.py
python 04_cost_cal.py

# Analyze results
python 05_robustness_analysis.py
```

