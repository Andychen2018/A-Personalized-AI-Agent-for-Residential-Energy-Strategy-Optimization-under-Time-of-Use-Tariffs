# Monthly Electricity Cost Comparison - Summary Report

## Overview
This report summarizes the monthly electricity cost comparison analysis for 19 households, comparing Standard tariff with Economy 7 and Economy 10 tariffs (both original and optimized versions).

## Processing Results
- **Total Households Processed**: 19/19 (100% success rate)
- **Analysis Period**: Various periods (13-23 months per household)
- **Generated Plots**: 19 academic-style comparison charts

## Key Findings by Household

| House ID | Avg Standard Cost (£) | Economy 7 Savings | Economy 10 Savings | Best Option |
|----------|----------------------|-------------------|--------------------|-----------| 
| house1   | 29.71               | 29.7%             | 31.9%              | Economy 10 |
| house2   | 25.26               | 20.9%             | 31.2%              | Economy 10 |
| house3   | 47.49               | 19.5%             | 31.4%              | Economy 10 |
| house4   | 32.69               | 14.1%             | 20.9%              | Economy 10 |
| house5   | 48.40               | 13.0%             | 22.6%              | Economy 10 |
| house6   | 21.84               | -33.2%            | -21.0%             | Standard   |
| house7   | 39.75               | 22.6%             | 37.4%              | Economy 10 |
| house8   | 27.29               | 20.9%             | 25.6%              | Economy 10 |
| house9   | 38.65               | 15.4%             | 28.3%              | Economy 10 |
| house10  | 60.42               | 17.2%             | 25.4%              | Economy 10 |
| house11  | 13.21               | 16.0%             | 22.0%              | Economy 10 |
| house13  | 41.72               | 14.7%             | 25.3%              | Economy 10 |
| house15  | 14.96               | 17.4%             | 28.4%              | Economy 10 |
| house16  | 34.89               | 20.2%             | 27.5%              | Economy 10 |
| house17  | 31.87               | 14.8%             | 22.0%              | Economy 10 |
| house18  | 45.18               | 17.3%             | 24.0%              | Economy 10 |
| house19  | 16.83               | 15.0%             | 20.3%              | Economy 10 |
| house20  | 32.60               | 19.0%             | 25.9%              | Economy 10 |
| house21  | 30.95               | 21.0%             | 28.8%              | Economy 10 |

## Summary Statistics

### Overall Performance
- **Economy 7 Optimized**: 18/19 households benefit (94.7% success rate)
- **Economy 10 Optimized**: 18/19 households benefit (94.7% success rate)
- **Average Economy 7 Savings**: 16.8% (excluding house6)
- **Average Economy 10 Savings**: 26.1% (excluding house6)

### Cost Distribution
- **Lowest Average Cost**: house11 (£13.21)
- **Highest Average Cost**: house10 (£60.42)
- **Median Average Cost**: £32.60

### Special Cases
- **house6**: Only household where time-of-use tariffs increase costs
  - Economy 7: +33.2% cost increase
  - Economy 10: +21.0% cost increase
  - Likely due to high daytime electricity usage pattern

## Recommendations

### For Most Households (18/19)
- **Primary Recommendation**: Switch to Economy 10 Optimized tariff
- **Average Savings**: 26.1% reduction in electricity costs
- **Secondary Option**: Economy 7 Optimized (16.8% average savings)

### For house6
- **Recommendation**: Remain on Standard tariff
- **Reason**: Usage pattern not suitable for time-of-use tariffs
- **Suggestion**: Consider energy efficiency measures or usage pattern analysis

## Technical Details

### Plot Features
- **Colors**: Matching academic publication standards
  - Standard: Gold (#FFD700)
  - Economy 7 Original: Light Blue (#87CEEB)
  - Economy 7 Optimized: Steel Blue (#4682B4)
  - Economy 10 Original: Plum (#DDA0DD)
  - Economy 10 Optimized: Medium Slate Blue (#9370DB)

### Font Configuration
- **Target Font**: Times New Roman (serif family)
- **Fallback Fonts**: Liberation Serif, DejaVu Serif
- **Academic Styling**: Professional grid, legend, and axis formatting

## File Locations
All generated plots are saved in: `/home/deep/TimeSeries/Agent_V2/output/Monthly_cost_trends/`

Each household has its own subdirectory with the format:
`/output/Monthly_cost_trends/house{X}/monthly_cost_comparison.png`

---
*Report generated automatically by the Monthly Cost Comparison Analysis Tool*
*Date: 2025-08-21*
