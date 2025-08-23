# Power Measurement Noise Robustness Experiment

## Experiment Objective

This experiment aims to evaluate the robustness of smart home energy management systems under power measurement noise disturbances. By adding ±10% random noise to the original power data, we test the system's performance retention capability under imperfect measurement conditions.

## Experimental Design

- **Noise Type**: ±10% power measurement noise (uniform distribution)
- **Test Houses**: house1, house2, house3, house20, house21
- **Tariff Schemes**: Economy_7, Economy_10
- **Evaluation Metric**: Performance Retention Rate = (1 - Cost Increase Rate) × 100%

## Execution Order

### Phase 1: Data Preparation
```bash
python 00generate_power_measurement_noise.py
```
- Generate noisy power measurement data
- Output: Noise data files in `Noise_data/` directory

### Phase 2: Event Detection and Segmentation
```bash
python run_power_noise_experiment.py
```
Execution steps:
1. `021_shiftable_identifier.py` - Shiftability identification
2. `022_segment_events.py` - Event segmentation
3. `023_event_id.py` - Event ID assignment

### Phase 3: Event Filtering
```bash
python run_filtering_pipeline.py
```
Execution steps:
1. `041_get_appliance_list.py` - Extract appliance lists
2. `043_min_duration_filter.py` - Minimum duration filtering
3. `044_tou_optimization_filter.py` - TOU optimization filtering

### Phase 4: Scheduling Optimization and Cost Calculation
```bash
python run_scheduling_pipeline.py
```
Execution steps:
1. `051event_scheduler.py` - Event scheduling optimization
2. `052_collision_resolver.py` - Collision resolution
3. `053event_splitter.py` - Event splitting
4. `054_cost_cal.py` - Cost calculation

### Phase 5: Performance Evaluation
```bash
python 055_performance_retention_analysis.py
```
- Calculate performance retention rates
- Generate robustness evaluation report

## Experimental Results

### Overall Performance
- **Average Performance Retention Rate**: 91.8%
- **Average Cost Increase Rate**: 8.2%


### Tariff Scheme Comparison
| Tariff Scheme | Avg Retention Rate | Avg Cost Increase Rate | Performance Level Distribution |
|---------------|-------------------|----------------------|-------------------------------|
| Economy_7 | 92.5% | 7.5% | Excellent:2, Good:2, Fair:1 |
| Economy_10 | 91.1% | 8.9% | Excellent:1, Good:3, Poor:1 |

### House Robustness Ranking
| Rank | House | Avg Retention Rate | Avg Increase Rate | Robustness Level |
|------|-------|-------------------|------------------|------------------|
| 1 | H1 | 99.6% | 0.4% | Excellent |
| 2 | H3 | 95.7% | 4.3% | Excellent |
| 3 | H20 | 92.8% | 7.2% | Good |
| 4 | H21 | 91.0% | 9.1% | Good |
| 5 | H2 | 80.0% | 20.0% | Fair |

