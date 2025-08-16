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

### Core Scripts

#### 1. Data Generation
- **`00generate_timing_uncertainties.py`**: Generates time-perturbed event data
  - Loads original appliance events
  - Applies random ±5-minute offsets
  - Outputs perturbed event files

#### 2. Optimization Pipeline
- **`01event_scheduler.py`**: Schedules perturbed events using optimization algorithm
- **`02_collision_resolver.py`**: Resolves scheduling conflicts between appliances
- **`03_event_splitter.py`**: Splits events into migrated (successfully scheduled) and non-migrated categories
- **`04_cost_cal.py`**: Calculates electricity costs for both event categories
- **`05_robustness_analysis.py`**: Performs statistical analysis and generates results

#### 3. Automation
- **`run_timing_uncertainty_experiment.py`**: Automated pipeline runner
  - Executes all steps in sequence
  - Provides progress reporting
  - Handles error conditions

### Directory Structure

```
02Timing_Uncertainties/
├── README.md                           # This file
├── 00generate_timing_uncertainties.py  # Data generation
├── 01event_scheduler.py               # Event scheduling
├── 02_collision_resolver.py           # Conflict resolution
├── 03_event_splitter.py              # Event categorization
├── 04_cost_cal.py                     # Cost calculation
├── 05_robustness_analysis.py          # Statistical analysis
├── run_timing_uncertainty_experiment.py # Automation script
├── Error_data/                        # Perturbed event data
│   └── UK/
│       ├── Economy_7/
│       └── Economy_10/
└── output/                            # Experiment results
    ├── 04_Initial_scheduling_optimization/
    ├── 05_Collision_Resolved_Scheduling/
    ├── 05_event_split/
    ├── 06_cost_cal/
    └── timing_uncertainty_analysis.json
```

## Processing Pipeline

### Step 1: Timing Perturbation Generation
```bash
python 00generate_timing_uncertainties.py
```
- Loads original appliance events from `output/04_TOU_filter/UK/`
- Applies random ±5-minute time offsets to ~84% of events
- Saves perturbed events to `Error_data/UK/`

### Step 2: Event Scheduling
```bash
python 01event_scheduler.py
```
- Uses perturbed event data as input
- Applies the same optimization algorithm as baseline
- Generates scheduling solutions for time-shifted events

### Step 3: Conflict Resolution
```bash
python 02_collision_resolver.py
```
- Resolves scheduling conflicts between appliances
- Ensures no overlapping usage of shared resources
- Outputs final scheduling decisions

### Step 4: Event Categorization
```bash
python 03_event_splitter.py
```
- **Migrated Events**: Successfully scheduled events (perturbed → optimized times)
- **Non-migrated Events**: Events that couldn't be rescheduled (original times)
- Critical: Non-migrated events use **original** (non-perturbed) times for fair comparison

### Step 5: Cost Calculation
```bash
python 04_cost_cal.py
```
- Calculates electricity costs for both event categories
- Uses time-of-use tariff rates (Economy_7, Economy_10)
- Computes total optimized costs under timing uncertainties

### Step 6: Robustness Analysis
```bash
python 05_robustness_analysis.py
```
- Compares perturbed results against baseline performance
- Calculates cost savings retention rates
- Performs statistical significance tests
- Generates comprehensive analysis report

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

## Key Findings

### 1. Strong Timing Robustness
The system demonstrates excellent robustness against timing uncertainties, with 97.5% average savings retention rate, exceeding the 95% expectation threshold.

### 2. Consistent Performance Across Tariffs
Both Economy_7 and Economy_10 tariffs show similar robustness levels (97.9% vs. 97.1%), indicating the algorithm's effectiveness across different pricing structures.

### 3. House-Specific Variations
- **4 out of 5 houses** achieve >96% retention rates
- **house3** shows relatively lower performance (91.2%) but still within acceptable range
- **house2** even shows slight improvement (100.2%), possibly due to beneficial timing redistributions

### 4. Statistical Stability
Non-significant p-values (>0.05) indicate that cost changes are not statistically significant, demonstrating system stability under timing uncertainties.

## Running the Complete Experiment

### Prerequisites
- Python environment with required dependencies
- Baseline optimization results in `output/` directory
- Original appliance event data

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

## Output Files

- **`timing_uncertainty_analysis.json`**: Detailed numerical results
- **`output/06_cost_cal/`**: Cost calculation results for each house/tariff
- **`output/05_event_split/`**: Event categorization results
- **Console output**: Summary tables and statistical analysis

## Conclusion

The timing uncertainties robustness experiment successfully demonstrates that the smart home energy management system maintains **97.5% of its cost-saving performance** even when appliance events are subject to ±5-minute timing uncertainties. This exceeds the expected 95% threshold, confirming the system's robustness for real-world deployment where perfect timing predictions are not feasible.
