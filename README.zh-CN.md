# A-Personalized-AI-Agent-for-Residential-Energy-Strategy-Optimization-under-Time-of-Use-Tariffs
LLM-powered agent for appliance scheduling and energy cost optimization in smart homes.

# 🏠  项目简介

在“双碳”目标下、能源系统加速向低碳与智能化转型的背景下，电力用户正从被动负荷逐步演变为具备自主调控能力的能量响应单元。特别是在居民侧，家庭建筑的用电行为具有高度个体差异性、时间弹性与行为驱动性，是需求响应（Demand Response）与节能调度的关键载体。然而，传统的家庭能耗管理方式往往缺乏对电器运行特性和用户行为偏好的理解，无法有效响应多时段电价机制，导致优化策略难以落地。构建真正可落地的主动节能智能系统，需要系统具备以下关键能力：

个性化感知能力：识别每个家庭的电器组合、功率特征与使用习惯；
语义理解能力：从自然语言中提取调度需求与限制规则；
电价感知能力：适应并利用 Economy 7/10 等动态时段电价模型；
调度优化能力：在多约束下生成高可行性、低成本的运行计划。

为此，本项目构建了一个集成 大语言模型（LLM） + 启发式调度优化 的家庭电器节能智能体，系统围绕“感知–理解–推理–优化”四个阶段形成闭环式调度流程，具体包括：

🧩 感知（Perception）
基于非侵入式用电数据（如 REFIT），实现总功率与多电器功率的对齐、异常剔除与粒度统一，提取电器运行事件段（起止时间、功率、能耗）；

🧠 理解（Understanding）
结合大语言模型（如 GPT），自动识别用户输入的电器名称、使用语境与偏好约束，生成结构化的调度规则与参数（如禁止运行时间、最晚完成时间、迁移方向等）；

🧮 推理（Reasoning）
融合用户规则与电价模型，判断每个事件的迁移合法性，构建多维运行区间与调度空间，预测迁移对成本的影响；

🔧 优化（Optimization）
采用启发式搜索算法，在候选运行区间中选择满足限制条件且电价最低的时间段，生成可调度事件计划，并对原始/优化调度进行费用对比与节能评估。

本项目实现了完整的 Agent 控制逻辑与模块化工具链，支持以下应用场景：

🎓 学术研究：电价响应调度、语义约束建模、NILM 识别与多智能体优化；

🏠 智能家居系统原型验证：集成家庭用电设备实现端侧调度；

💡 节能平台与行业应用嵌入：提供清晰模块接口，支持多户/多电价方案并行调度测试。

## 📊 使用数据集：REFIT 电器级能耗数据

我们使用英国 Loughborough University 提供的公开数据集 **REFIT** 作为基础实验数据。其特点包括：

- 记录 20 户家庭 2013–2015 年间的每分钟级电器功率数据；
- 覆盖主要家用电器如冰箱、洗衣机、烘干机、电视等；
- 每户包括总功率（Aggregate）与多个子电器；
- 适用于 NILM、电价响应、调度优化等研究任务。

🔗 数据集链接：[REFIT Dataset](https://pureportal.strath.ac.uk/en/projects/personalised-retrofit-decision-support-tools-for-uk-homes-using-s/datasets/)

本项目中对其进行了多分辨率对齐、异常剔除与行为建模处理，作为后续 Agent 输入。

---

## 🧠 系统架构与工作流程

```
原始功率数据
     ↓
对齐与建模（1min粒度） ← p_01_perception_alignment
     ↓
电器语义识别 + Shiftability分类 ← p_02_shiftable_identifier
     ↓
运行事件提取（StartTime-EndTime-Energy） ← p_02_segment_events
     ↓
多区间电价下的费用模拟（多电价）及初始推荐方案 ← p_03_tariff_modeling
     ↓
用户自然语言约束解析 ← p_042_user_constraints + llm_proxy
     ↓
候选调度事件筛选 →调度区间启发式调度 → 事件碰撞冲突解决 ← p_051~p_053
     ↓
费用与节能对比分析及最终推荐方案 → 可视化 ← p_054_tariff_cost_analyzer
```

所有过程由 Agent 控制流程统一调度，工具支持独立调用测试。

---

## 🚀 快速开始指南

### ✅ 安装环境
```bash
pip install requirement.txt 
conda activate your_env_name
```

### ✅ 启动 Agent
```bash
export open_api_key=your_api_key
```

```bash
python personal_household_tariff_scheduling_agent.py
```

你将体验完整对话式流程，包括电器识别、电价分析、调度与节能反馈。

---

## ⚙️ 用户配置项说明（基础设置）
如果您想在本项目基础上进行改进研究，您可以修改如下部分以满足您自己的工作

| 文件或位置 | 说明 |
|------------|------|
| `open_api_key` | 设置 LLM 调用凭证，可通过环境变量或 `config.py` 中配置 |
| `tools/p_01_perception_alignment.py` | 修改 `raw_csv_path` 指定原始功率数据（REFIT 单户） |
| `test_func_2_int.py` | 在 `if __name__ == "__main__"` 处的对话中提供测试电器的名称（推荐来源于 `house_appliances.json`），当然也可以使用自己的电器名称 |
| `personal_household_tariff_scheduling_agent.py` | 在if __name__ == "__main__":后的第一个query用自然语言提供电器的名称作为 Agent 解析的内容 |

---

## 🛠️ 用户约束设置说明（可选扩展）

| 文件或位置 | 说明 |
|------------|------|
| `appliance_constraints.json` | 默认规则定义（本文设置的自然语言规则，LLM解析后自动保存在./config/appliance_constraints.json中） |
| `personal_household_tariff_scheduling_agent.py` | 可自定义自然语言规则，例如：<br>“Washing Machine 不允许在 23:00–6:30 运行，必须在次日14:00前完成”；<br>“Dishwasher 只允许延后调度” |

系统将调用 GPT 自动结构化为规则表，并对运行事件进行筛选与迁移判断。

---

## 🧪 推荐实验方式

1. 打开 `config/house_appliances.json` 选择任意家庭（如 `House1`）；
2. 将其电器填入 Agent 启动脚本personal_household_tariff_scheduling_agent.py,具体在if __name__ == "__main__":的第一个query中；
3. 启动主程序并观察输出路径：

| `01_preprocessed/`      | 🌐 原始功率数据对齐与粒度统一（如1分钟），为行为建模做准备                    
| `02_behavior_modeling/` | 📌 电器语义识别与可调度性分类（Shiftable / Non-shiftable / Base） 
| `02_event_segments/`    | 📊 提取各电器的运行事件段（起止时间、持续时长、能耗）                       
| `03_cost_cal/`          | 💰 原始未调度条件下的多电价费用模拟，建立基准线                          
| `04_user_constraints/`  | 🔐 用户约束规则解析与事件合法性筛选（使用默认或 LLM 解析）                  
| `05_scheduling/`        | 📅 调度优化结果输出（启发式调度器生成新的运行时间）                        
| `06_tariff/`            | 🔍 调度前后事件在高/低电价区间的分布统计                             
| `07_cost_analysis/`     | 📈 调度前后节省费用的图表与统计结果                                


---

## 📊 示例可视化结果
| 不同区间电价下的总费用及推荐方案|
| ![](output/07_cost_analysis/comparison.png)

| 月度节能对比 | 各电器节省分布 |
|--------------|----------------|
| ![](output/07_cost_analysis/monthly_cost_comparison_plot.png) | ![](output/07_cost_analysis/appliance_cost_comparison_barplot.png) |

---

## 📁 模块与工具组成

### 🛠️ 工具模块说明（部分）
| 模块路径                                     | 功能说明                                       |
| ---------------------------------------- | ------------------------------------------ |
| `tools/p_01_perception_alignment.py`     | 原始功率数据的时间对齐与粒度统一处理                         |
| `tools/p_02_shiftable_identifier.py`     | LLM识别电器语义 → Shiftability 与 Pmin/Tmin 推理    |
| `tools/p_02_segment_events.py`           | 双阈值提取运行事件段（基于功率序列）                         |
| `tools/p_03_tariff_modeling.py`          | 根据事件与电价模型模拟运行费用                            |
| `tools/p_03_energy_summary.py`           | 按年、月、日统计各类电器的能耗与费用                         |
| `tools/p_041_get_appliance_list.py`      | 提取数据集中电器及其 ID 映射                           |
| `tools/p_042_user_constraints.py`        | 自然语言调度规则 → 标准 JSON 结构                      |
| `tools/p_043_filter_shiftable_events.py` | 综合约束与电价规则筛选合法迁移事件                          |
| `tools/p_051_base_scheduler.py`          | 启发式调度算法：基于 allowed 区间寻找最优时间段               |
| `tools/p_052_conflict_resolver.py`       | 检测调度冲突并进行平移或合并修复                           |
| `tools/p_053_tariff_input_builder.py`    | 构建调度输入结构（电价向量 + 合法运行区间）                    |
| `tools/p_054_tariff_cost_analyzer.py`    | 调度结果费用评估与图表生成                              |
| `tools/llm_proxy.py`                     | GPT 接口封装：调用 GPTProxyClient.chat() 与大语言模型交互 |


### 📦 Agent 主控逻辑

- `personal_household_tariff_scheduling_agent.py`：主流程控制；
- `test_func_*.py`：每个模块的单独入口与调试接口。其中test_func_1.py用于显示最终计算分析结果的工具，2～6是各个阶段的工具

---

## 📄 引用与许可

本项目以 MIT License 开源，欢迎研究引用或二次开发：

```bibtex
@project{TariffSchedulingAgent,
  title={A Personalized AI Agent for Residential Energy Strategy Optimization under Time-of-Use Tariffs},
  author={Zhiqiang Chen},
  year={2025},
  url={https://github.com/Andychen2018/A-Personalized-AI-Agent-for-Residential-Energy-Strategy-Optimization-under-Time-of-Use-Tariffs}
  }
```

---

## 🔮 未来计划

- [ ] 集成强化学习（DQN）调度器；
- [ ] 接入 Web 前端界面与用户友好交互；
- [ ] 扩展更多电价机制（如实时电价 RTP）；
- [ ] 多家庭联合优化与区域级调度协同支持；



## 文件结构整体说明

```plaintext
.
├── config/                         # 📄 配置文件（系统默认参数与设备字典）
│   ├── appliance_constraints.json           # Agent 默认生成的电器约束（禁止时间、完成时间、迁移规则等）
│   ├── appliance_shiftability_dict.json     # 家庭常见电器可调度性字典（中英文 + Shiftability 标签）
│   ├── device_threshold_dict.json           # 家庭常见电器各电器默认的 Pmin / Tmin 运行阈值
│   ├── house_appliances.json                # REFIT数据集中每户家庭包含的电器列表（用于测试切换）
│   └── tariff_config.json                   # 模拟英国基础电价，区间电价Economy_7 ，Economy_10 的电价机制配置

├── output/                         # 🧾 所有中间与最终结果（按阶段分类）
│   ├── 01_preprocessed/            → 原始功率数据对齐与异常剔除
│   ├── 02_behavior_modeling/       → 电器语义识别与调度能力建模
│   ├── 02_event_segments/          → 提取运行事件段（起止时间、能耗、持续时间）
│   ├── 03_cost_cal/                → 不同电价下的原始运行费用模拟
│   ├── 04_user_constraints/        → 用户调度规则解析与事件筛选
│   ├── 05_scheduling/              → 优化调度结果（StartTime/EndTime 更新）
│   ├── 06_tariff/                  → 不同电价下迁移前后事件对比
│   └── 07_cost_analysis/           → 调度成本分析与图像可视化输出

├── tools/                         # 🛠️ 功能工具模块（支持 Agent 调用）
│   ├── p_01_perception_alignment.py         # 原始功率数据的时间对齐与粒度统一处理
│   ├── p_02_shiftable_identifier.py         # LLM识别电器语义 → Shiftability 与 Pmin/Tmin 推理
│   ├── p_02_segment_events.py               # 双阈值提取运行事件段（基于功率序列）
│   ├── p_03_tariff_modeling.py              # 根据事件与电价模型模拟运行费用
│   ├── p_03_energy_summsary.py              # 分别按照年、月、日；各个电器，base，shiftable，non-shiftable的条件进行费用的统计
│   ├── p_041_get_appliance_list.py          # 提取数据集中出现的电器及其 ID 映射
│   ├── p_042_user_constraints.py            # 自然语言调度规则 → 标准 JSON 结构
│   ├── p_043_filter_shiftable_events.py     # 综合约束规则与电价模型筛选合法迁移事件
│   ├── p_051_base_scheduler.py              # 启发式调度算法：基于 allowed 区间找最优时间段
│   ├── p_052_conflict_resolver.py           # 检测调度冲突并进行平移或合并修复
│   ├── p_053_tariff_input_builder.py        # 构建调度输入结构：电价向量 + 合法运行区间
│   ├── p_054_tariff_cost_analyzer.py        # 调度结果费用评估与图表生成
│   └── llm_proxy.py                         # GPT 调用接口封装器：提供 GPTProxyClient.chat() 方法，与大语言模型交互，实现自然语言 → JSON结构转换

├── test_func_1_int.py             # 工具1：汇总模拟费用并推荐最优电价方案
├── test_func_2_int.py             # 工具2：识别电器名称与 Shiftability 类型
├── test_func_3_int.py             # 工具3：执行电价模拟与推荐输出
├── test_func_4_int.py             # 工具4：输出系统默认调度规则（如禁止时段）
├── test_func_5_int.py             # 工具5：结合用户规则筛选合法迁移事件
├── test_func_6_int.py             # 工具6：分析并可视化调度前后事件与电价关系

├── personal_household_tariff_scheduling_agent.py  # ✅ 主入口：Agent控制 + 工具联动
├── llm.py                         # LLM统一接口封装（如 chat_with_api 的底层实现）
├── plot_cost_summary.py           # 最终成本图像绘制（如月度对比图、按电器/类型分布图）
├── config.py                      # 调用LLM模型的配置，用户在这里填写自己的open_api_key
├── requirements.txt               # Python 环境依赖文件
```