# Constraint Parsing Errors Robustness Experiment

## 🎯 Experiment Objective

This experiment evaluates the **robustness** of the home energy management system when faced with **constraint parsing errors**. The primary goal is to measure how well the system maintains its cost-saving performance when user-defined scheduling constraints are corrupted or misinterpreted.

### Research Questions
1. **How robust is the system to constraint parsing errors?**
2. **What is the performance retention rate under 4.4% constraint corruption?**
3. **Can the system maintain acceptable cost savings despite constraint errors?**

##  Experimental Design

### Target Households
- **house1, house2, house3, house20, house21** (5 representative households)
- Selected to cover diverse energy consumption patterns and appliance configurations

### Tariff Scenarios
- **Economy_7**: Single low-price period (00:30-07:30)
- **Economy_10**: Multiple low-price periods (01:00-06:00, 13:00-16:00, 20:00-22:00)

### Error Injection Strategy
The experiment introduces **4.4% constraint corruption rate** with the following error types:
- **forbidden_time** (45%): Time range errors (swap start/end times, invalid ranges)
- **min_duration** (30%): Duration constraint errors (unrealistic values)
- **latest_finish** (15%): Finish time constraint errors (invalid time formats)
- **shift_rule** (10%): Scheduling rule errors (strategy changes)



### Achieved Results
| Metric | Economy_7 | Economy_10 | Overall |
|--------|-----------|------------|---------|
| **Average Savings Retention** | 92.0% | 95.1% | **93.6%** |
| **Expected Performance** | 91.7% | 91.7% | 91.7% |
| **Performance vs. Expected** | +0.3% | +3.4% | **+1.9%** |

### Statistical Significance
- **Constraint Error Rate**: 4.4% (20 out of 450 constraints corrupted)
- **t-test Results**: p > 0.05 (not statistically significant)
- **Interpretation**: The system is highly robust to constraint parsing errors

### Cost Comparison Table
```
House    Standard            Economy_7           Economy_10            Retention Rate
ID           Cost   Original  Optimized   Original  Optimized         E7        E10        Avg
------------------------------------------------------------------------------------------------------------------------
house1 £  624.11 £  408.46 £  409.31 £  402.08 £  402.56     99.6%     99.8%     99.7%
house2 £  479.93 £  207.52 £  207.52 £  205.43 £  205.43    100.0%    100.0%    100.0%
house3 £  998.95 £  523.24 £  622.03 £  500.51 £  566.62     79.2%     86.7%     83.0%
house20 £  524.15 £  354.78 £  369.82 £  332.97 £  344.02     91.1%     94.2%     92.7%
house21 £  495.20 £  291.37 £  311.83 £  282.65 £  293.36     90.0%     95.0%     92.5%
```



### Invalid Time Formats
```json
// Original
"latest_finish": "24:00"

// Corrupted
"latest_finish": "99:99"
```


##  Performance Metrics 

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Savings Retention** | 93.6%  |
