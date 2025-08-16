# Gurobi-based Smart Home Energy Optimization

## ⚠️ **Important: Gurobi License Required**

**This code requires Gurobi Optimizer with a valid license to run.**

- **Academic License**: Free for academic research (requires university email verification)
- **Commercial License**: Required for commercial use
- **Get License**: Visit [Gurobi License Center](https://www.gurobi.com/downloads/licenses/)
- **Installation Guide**: [Gurobi Installation Instructions](https://www.gurobi.com/documentation/quickstart.html)

Without a valid Gurobi license, the optimization code will not execute.

---

This repository contains the implementation of a Mixed Integer Linear Programming (MILP) optimization system using Gurobi for smart home energy management. The system optimizes the scheduling of household appliances to minimize electricity costs under different tariff structures.

## 📋 Overview

The optimization system processes household energy consumption data and reschedules appliance usage to minimize costs while respecting operational constraints. It supports two UK electricity tariff structures:
- **Economy 7**: 7-hour off-peak period
- **Economy 10**: 10-hour off-peak period

## 🏗️ System Architecture

```
Input: Household appliance events → Gurobi MILP Optimizer → Optimized schedules → Cost Analysis
```

## 📁 File Structure

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

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- **Gurobi Optimizer with valid license** (see warning above)
- **Required packages**: `pandas`, `numpy`, `gurobipy`

### Installation

#### Step 1: Install Gurobi and Get License
```bash
# Install Gurobi Python package
pip install gurobipy

# For academic users: Get free academic license
# 1. Register at https://www.gurobi.com/academia/academic-program-and-licenses/
# 2. Download and install license file
# 3. Set environment variable: export GRB_LICENSE_FILE=/path/to/gurobi.lic
```

#### Step 2: Install Dependencies
```bash
# Install required Python packages
pip install pandas numpy
```

#### Step 3: Verify Installation
```bash
# Test Gurobi installation
python -c "import gurobipy; print('Gurobi installed successfully')"
```

### Usage

1. **Run complete optimization for all households:**
   ```bash
   python run_optimization.py
   ```

2. **Display results table:**
   ```bash
   python show_results.py
   ```

3. **Generate summary statistics:**
   ```bash
   python generate_summary.py
   ```

## 📊 Results

The system has been tested on 19 UK households with the following key findings:

| Metric | Economy 7 | Economy 10 | Improvement |
|--------|-----------|------------|-------------|
| **Average Savings Rate** | 8.33% | 11.79% | +3.46% |
| **Overall Savings Rate** | 8.97% | 13.10% | +4.13% |
| **Best Performance** | 7 households | 12 households | 63.2% prefer E10 |

### Highlights
- **Maximum savings**: 31.12% (House 7, Economy 10)
- **All households achieved cost reduction**: Range 2.10% - 31.12%
- **Economy 10 outperforms Economy 7** in 63.2% of cases

## 🔧 Technical Details

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

## 📈 Performance Metrics

The system evaluates performance using:
- **Absolute cost savings** (£)
- **Percentage savings rate** (%)
- **Optimization success rate**
- **Computational efficiency**

## 🔍 Code Components

### Core Modules

1. **`gurobi_optimizer.py`**
   - MILP model formulation
   - Constraint generation
   - Gurobi solver interface

2. **`cost_calculator.py`**
   - Original cost calculation
   - Optimized cost calculation  
   - Savings analysis

3. **`run_optimization.py`**
   - Data loading and preprocessing
   - Batch processing coordination
   - Result aggregation

### Analysis Tools

4. **`show_results.py`**
   - Tabular result presentation
   - Comparative analysis display

5. **`generate_summary.py`**
   - Statistical analysis
   - Performance metrics calculation
   - Export functionality

## 📋 Configuration

### Tariff Settings (Used in Code)
```python
# Actual tariff rates used in cost_calculator.py
{
  "Economy_7": {
    "type": "time_based",
    "periods": [
      {
        "start": "00:30",
        "end": "07:30",
        "rate": 0.15
      },
      {
        "start": "07:30",
        "end": "00:30",
        "rate": 0.3
      }
    ]
  },
  "Economy_10": {
    "type": "time_based",
    "periods": [
      {
        "start": "01:00",
        "end": "06:00",
        "rate": 0.15
      },
      {
        "start": "06:00",
        "end": "13:00",
        "rate": 0.3
      },
      {
        "start": "13:00",
        "end": "16:00",
        "rate": 0.15
      },
      {
        "start": "16:00",
        "end": "20:00",
        "rate": 0.3
      },
      {
        "start": "20:00",
        "end": "22:00",
        "rate": 0.15
      },
      {
        "start": "22:00",
        "end": "01:00",
        "rate": 0.3
      }
    ]
  },
  "Standard": {
    "type": "flat",
    "rate": 0.3
  }
}
```

**Time Periods:**
- **Economy_7**: Off-peak 00:30-07:30 (7 hours)
- **Economy_10**: Off-peak 00:30-07:30, 13:00-15:00, 20:30-22:30 (10 hours total)

## 🎯 Research Applications

This implementation supports research in:
- Smart home energy management
- Demand response optimization
- Electricity tariff analysis
- MILP applications in energy systems
- Household energy behavior modeling

## 📄 Citation

If you use this code in your research, please cite:
```
[Your paper citation here]
```

## 🔧 Troubleshooting

### Common Issues

**"No Gurobi license found"**
- Ensure you have a valid Gurobi license
- Check license file path and environment variables
- For academic users: Verify university email registration

**"gurobipy module not found"**
```bash
pip install gurobipy
```

**"License expired"**
- Academic licenses expire annually and need renewal
- Check license status: `grbgetkey --help`

**Performance Issues**
- Gurobi academic license is limited to 2000 variables
- Commercial license required for larger problems

## 📞 Contact

For questions or issues, please contact [your contact information].

## 📜 License

[Your license information here]
