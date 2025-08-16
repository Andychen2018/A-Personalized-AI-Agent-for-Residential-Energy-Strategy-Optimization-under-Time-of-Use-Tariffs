# Gurobi家庭电器优化系统

基于Gurobi的智能家庭电器事件优化系统，在分时电价下优化可调度电器的运行时间，实现电费节约。

## 🚀 快速开始

### 1. 环境准备
```bash
# 激活gurobi环境
conda activate gurobi

# 进入项目目录
cd experiments/BaselineComparison/gurobi
```

### 2. 一键运行完整优化
```bash
python run_optimization.py
```
**这是主要执行文件，会自动完成所有19个家庭在两种电价下的优化和费用计算**

### 3. 查看结果
```bash
# 显示所有家庭的费用对比表格
python show_results.py

# 生成详细统计报告
python generate_summary.py
```

## 📁 代码结构与执行顺序

### 🎯 主执行文件
- **`run_optimization.py`** - **主程序，直接运行此文件即可**
  - 批量处理所有19个家庭
  - 自动调用优化器和费用计算器
  - 生成完整的时间统计
  - 保存所有结果到 `./results/` 目录

### 🔧 核心模块 (被 run_optimization.py 调用)
1. **`gurobi_optimizer.py`** - Gurobi优化引擎
   - MILP模型构建
   - 约束条件生成
   - 求解器接口
   - **包含详细的时间统计功能**

2. **`cost_calculator.py`** - 费用计算引擎
   - 计算所有事件的原始费用
   - 整合优化结果计算优化后费用
   - 生成完整的费用分析报告

### 📊 结果分析工具 (优化完成后运行)
3. **`show_results.py`** - 结果展示工具
   - 显示19个家庭的完整对比表格
   - Economy_7 vs Economy_10 费用对比
   - 论文风格的格式化输出

4. **`generate_summary.py`** - 统计分析工具
   - 生成详细统计报告
   - 导出CSV和JSON格式
   - 性能指标计算

### ⚙️ 配置文件
- **`tariff_config.json`** - 电价配置
  - Economy_7: 00:30-07:30 低价时段
  - Economy_10: 01:00-06:00, 13:00-16:00, 20:00-22:00 低价时段

## 📈 执行流程

```
1. python run_optimization.py (主程序)
   ├── 调用 gurobi_optimizer.py (优化调度)
   └── 调用 cost_calculator.py (费用计算)
   
2. python show_results.py (查看结果表格)

3. python generate_summary.py (生成统计报告)
```

## 📊 输出结果

### 目录结构
```
results/
├── Economy_7/                    # Economy_7电价结果
│   ├── house1/
│   │   ├── optimization_results_house1_Economy_7.csv      # Gurobi优化结果
│   │   ├── optimization_summary_house1_Economy_7.json     # 优化汇总
│   │   ├── complete_cost_analysis_house1_Economy_7.csv    # 完整费用分析
│   │   └── cost_summary_house1_Economy_7.json            # 费用汇总
│   └── ... (house2-house19)
├── Economy_10/                   # Economy_10电价结果
│   └── ... (house1-house19)
├── overall_statistics.json       # 总体统计 (包含时间统计)
├── overall_summary.csv          # 总体汇总CSV
└── overall_optimization_summary.json  # 优化汇总
```

### 关键输出文件
1. **`complete_cost_analysis_*.csv`** - 每个事件的详细费用分析
2. **`cost_summary_*.json`** - 家庭级别费用汇总
3. **`overall_statistics.json`** - 所有家庭的综合统计
4. **`overall_summary.csv`** - 适合Excel分析的汇总表

## ⏱️ 时间统计功能

系统会详细记录每个阶段的处理时间：
- **数据加载时间**: CSV和功率数据加载
- **功率计算时间**: 事件功率曲线计算
- **优化阶段时间**: Gurobi求解时间
- **费用计算时间**: 完整费用分析时间
- **保存时间**: 结果文件保存时间

## 🎯 主要功能

- ✅ **智能优化**: 使用Gurobi MILP求解器优化可调度电器运行时间
- ✅ **完整费用计算**: 包含所有事件(可调度+不可调度)的费用分析
- ✅ **双电价对比**: Economy_7 vs Economy_10 全面对比
- ✅ **批量处理**: 19个家庭 × 2种电价 = 38个优化任务
- ✅ **详细统计**: 节约金额、节约率、时间统计等
- ✅ **多格式输出**: JSON、CSV、格式化表格

## 🔒 约束条件

- 🚫 洗衣机、烘干机、洗碗机禁止在23:30-06:00运行
- ⏰ 所有事件必须在38小时内完成
- 🔄 同一电器的事件不能时间重叠
- ⏱️ 最小持续时间5分钟
- 🎯 每15分钟检查一次可行的迁移时间

## 💡 使用建议

1. **首次运行**: 直接执行 `python run_optimization.py`
2. **查看结果**: 运行 `python show_results.py` 查看对比表格
3. **详细分析**: 运行 `python generate_summary.py` 生成报告
4. **结果文件**: 查看 `./results/` 目录下的详细数据

**预计处理时间**: 约30-60分钟完成所有38个优化任务

## 📋 代码调用关系

### 独立执行的文件
- `run_optimization.py` - 主程序
- `show_results.py` - 结果展示
- `generate_summary.py` - 统计分析

### 被调用的模块
- `gurobi_optimizer.py` - 被 run_optimization.py 调用
- `cost_calculator.py` - 被 run_optimization.py 调用
- `tariff_config.json` - 被所有模块读取

**建议执行顺序**: run_optimization.py → show_results.py → generate_summary.py
