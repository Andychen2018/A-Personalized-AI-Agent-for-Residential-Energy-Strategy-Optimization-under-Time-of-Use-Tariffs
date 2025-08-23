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
