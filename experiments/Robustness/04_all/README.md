# Constraint Parsing Error Robustness Experiment (04_all)

## Experiment Purpose

This experiment evaluates the robustness of the demand response optimization system when facing constraint parsing errors. The goal is to assess how well the system maintains its optimization performance when some constraints are corrupted or misinterpreted during the parsing process.

### Research Questions
1. How does constraint parsing error affect the overall system performance?
2. What is the performance retention rate under different error scenarios?
3. Which households are most/least resilient to constraint parsing errors?
4. How do different tariff schemes (Economy_7 vs Economy_10) respond to constraint errors?

## Experimental Setup

### Target Households
- house1, house2, house3, house20, house21

### Tariff Schemes
- Economy_7: Off-peak hours 00:00-07:00
- Economy_10: Off-peak hours 00:00-10:00

### Error Injection
- **Error Rate**: 4.4% (20 out of 450 total constraints corrupted)
- **Error Type**: Constraint parsing errors that affect optimization constraints
- **Error Location**: `/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/Error_data/UK/`

## Data Paths

### Input Data
- **Original Power Data**: `/home/deep/TimeSeries/Agent_V2/output/01_preprocessed/house*/01_perception_alignment_result_house*.csv`
- **Noisy Power Data**: `/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/output/01_preprocessed/house*/01_perception_alignment_result_house*_noisy.csv`
- **Constraint Error Log**: `/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/Error_data/UK/constraint_corruption_log.json`

### Intermediate Results
- **Event Splitting**: `/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/output/05_event_split/`
- **Cost Calculation**: `/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/output/06_cost_cal/`

### Output Results
- **Robustness Analysis**: `/home/deep/TimeSeries/Agent_V2/experiments/Robustness/04_all/robustness_savings_analysis.json`

## Experimental Pipeline

### Step 1: Data Preprocessing (01_preprocess.py)
- Adds noise to original power consumption data
- Generates noisy datasets for robustness testing

### Step 2: Constraint Error Injection (02_constraint_error.py)
- Injects parsing errors into optimization constraints
- Creates corrupted constraint files with 4.4% error rate

### Step 3: Event Splitting (03_event_splitter.py)
- Processes events under corrupted constraints
- Categorizes events as migrated vs non-migrated

### Step 4: Cost Calculation (04_cost_cal.py)
- Calculates electricity costs for both migrated and non-migrated events
- Uses noisy power data for realistic cost estimation

### Step 5: Robustness Analysis (05_robustness_analysis.py)
- Compares performance under error conditions vs baseline
- Calculates performance retention rates

## Experimental Results

### Baseline Performance (No Errors)
| House | Economy_7 | Economy_10 |
|-------|-----------|------------|
| house1 | £438.74 | £424.87 |
| house2 | £379.43 | £330.22 |
| house3 | £804.08 | £685.07 |
| house20 | £423.84 | £387.54 |
| house21 | £391.36 | £352.66 |

### Performance Under Constraint Errors
| House | Economy_7 | Economy_10 |
|-------|-----------|------------|
| house1 | £440.56 | £427.15 |
| house2 | £450.15 | £400.77 |
| house3 | £833.11 | £735.43 |
| house20 | £451.33 | £418.99 |
| house21 | £424.88 | £387.16 |

### Performance Retention Rates
| House | Economy_7 | Economy_10 | Average |
|-------|-----------|------------|---------|
| house1 | 99.6% | 99.5% | 99.5% |
| house2 | 84.3% | 82.4% | 83.4% |
| house3 | 96.5% | 93.2% | 94.9% |
| house20 | 93.9% | 92.5% | 93.2% |
| house21 | 92.1% | 91.1% | 91.6% |

### Key Findings

1. **Overall Robustness**: The system demonstrates good robustness with an average performance retention rate of 92.5%

2. **Household Variability**: 
   - **Most Robust**: house1 (99.5% retention) - minimal impact from constraint errors
   - **Least Robust**: house2 (83.4% retention) - most affected by constraint parsing errors

3. **Tariff Scheme Impact**: Economy_7 shows slightly better robustness than Economy_10

4. **Error Impact**: Despite 4.4% constraint corruption rate, most households maintain >90% performance

5. **Cost Degradation**: Average cost increase ranges from 0.5% (house1) to 16.6% (house2)

## Conclusions

The demand response optimization system shows strong robustness against constraint parsing errors. Even with 4.4% of constraints corrupted, the system maintains over 90% of its optimization performance for most households. This indicates that the optimization algorithm has inherent resilience and can adapt to partial constraint corruption while still delivering significant energy cost savings.

The variability in robustness across households suggests that system performance depends on the specific characteristics of each household's energy consumption patterns and the nature of their shiftable appliances.
