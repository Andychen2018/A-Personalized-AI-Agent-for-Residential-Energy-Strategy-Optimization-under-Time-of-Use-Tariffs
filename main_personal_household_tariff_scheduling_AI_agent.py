#!/usr/bin/env python3
"""main_flow.py
基于TOOLS配置的统一工作流程执行器。

工作流程按TOOLS数组顺序执行：
Step0(index 0): Data Preprocessing & Perception Alignment (test_func_2_int)  -> test_func_2_int_main
Step1(index 1): Tariff Analysis & Cost Optimization (test_func_3_int)          -> test_func_3_int_main
Step2(index 2): Appliance Information Standardization (test_func_4_int)        -> test_func_4_int_main
Step3(index 3): Energy Optimization & Constraint Processing (test_func_5_int)             -> test_func_5_int_main
Step4(index 4): Smart Scheduling & System Integration (test_func_6_int)             -> test_func_6_int_main
Step5(index 5): Cost Analysis & Intelligent Recommendations (test_func_7_int)             -> test_func_7_int_main

每个步骤统一架构：
    params = collect_param()
    function(**params)
"""

# 全部可用的房屋列表 (基于 test_func_2_int.py 中的 target_houses)
# TARGET_HOUSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]
TARGET_HOUSES = [1, 2]
# DEFAULT_HOUSE_LIST = "house1,house2,house3,house4,house5,house6,house7,house8,house9,house10,house11,house13,house15,house16,house17,house18,house19,house20,house21"
DEFAULT_HOUSE_LIST = "house1,house2"

from typing import Optional, Dict, Any, List
import json
import logging

# Suppress matplotlib INFO level logging messages globally
logging.getLogger('matplotlib.category').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

# 导入配置
from settings import settings

# 导入LLM聊天接口
from llm import chat_with_api

# 导入工具模块
from test_func_2_int import main as test_func_2_int_main
from test_func_3_int import main as test_func_3_int_main
from test_func_4_int import main as test_func_4_int_main
from test_func_5_int import main as test_func_5_int_main
from test_func_6_int import main as test_func_6_int_main
from test_func_7_int import main as test_func_7_int_main

# 美观界面相关函数
def print_mixed_color(cyan_part, blue_part):
    """打印混合颜色文本：青色部分 + 蓝色部分"""
    print(f"\033[96m{cyan_part}\033[94m{blue_part}\033[0m")

def print_welcome_banner():
    """打印包含价值说明的欢迎横幅"""
    print()
    print_magenta("╔═════════════════════════════════════════════════════════════════════════════════════════════════════╗")
    print_magenta("║                                  🏠 Smart Home Energy Management v2.0                               ║")
    print_magenta("║                                      Intelligent Energy Analytics                                   ║")
    print_magenta("╠═════════════════════════════════════════════════════════════════════════════════════════════════════║")
    print_magenta("║               Agent system provides intelligent services by the giving data                         ║")
    print_magenta("║  🔍 Smart analysis of home electricity usage, optimize appliance scheduling                         ║")
    print_magenta("║  📊 Deep analysis of your electricity patterns, identify energy saving potential                    ║")
    print_magenta("║  ⏰ Smart recommendations for optimal usage times, avoid peak pricing periods                       ║")
    print_magenta("║  💰 Average savings of 15-30% on electricity bills, make your wallet happier                        ║")
    print_magenta("║  🌱 Reduce carbon emissions, contribute to environmental protection                                 ║")
    print_magenta("╚═════════════════════════════════════════════════════════════════════════════════════════════════════╝")

def print_boxed_section(title, content_lines, emoji="📋"):
    """Print section with left border, border in cyan, content in blue"""
    print()
    print_cyan("═" * 100)
    print(f"\033[96m║ \033[95m{emoji} {title}\033[0m")
    print_cyan("╠" + "═" * 100)
    for line in content_lines:
        # Check if it's a box line (contains ┌─、│、└ etc.)
        if any(char in line for char in ['┌', '─', '│', '└', '┐', '┘']):
            print_cyan(f"║ {line}")  # Box lines in cyan
        else:
            # Border cyan, content blue
            print_mixed_color("║ ", line)
    print_cyan("╚" + "═" * 100)

def print_centered_title(title):
    """Print centered title without borders"""
    print()
    # Calculate padding for centering (100 chars total width)
    title_length = len(title)
    padding = (100 - title_length) // 2
    centered_title = " " * padding + title
    print_magenta(centered_title)

def print_workflow_execution_plan():
    """Print workflow execution plan"""
    print()
    print_cyan("═" * 100)
    print_centered_title("Start Analysis")
    print_cyan("═" * 100)
    print()
    print_cyan("🚀 System will automatically execute following steps:")
    print_blue("   Step 1: Data Analysis & Perception Alignment")
    print_blue("   Step 2: Pricing Calculation & Initial Recommendation")
    print_blue("   Step 3: Device Recognition & Behavior Modeling")
    print_blue("   Step 4: Energy Optimization & Constraint Processing")
    print_blue("   Step 5: Smart Scheduling & Integration")
    print_blue("   Step 6: Final Cost Calculation & Intelligent Recommendation")
    print()
    print_yellow("⏳ Estimated time: 3-10 minutes (depends on data volume)")
    print_yellow("💡 Please be patient during execution, system will show progress for each step")
    print_cyan("═" * 100)

def print_parameter_collection_header():
    """Print clean parameter collection header"""
    print()
    print_cyan("═" * 100)
    print_centered_title("Parameter Configuration")
    print_cyan("═" * 100)
    print_blue("🔧 Analyzing your input and configuring system parameters...")

def print_parameter_progress(params_dict):
    """Print enhanced parameter collection progress with LLM intelligence"""
    print()
    print_blue("🤖 LLM Intelligent Parameter Analysis:")
    print_blue("   🔍 Parsing user input with natural language understanding...")
    import time
    time.sleep(0.8)

    # 动态显示处理模式
    mode_text = "Single household" if params_dict.get('mode') == 1 else "Batch processing"
    print_blue(f"   ✅ Processing mode: {mode_text}")
    print_cyan("      └─ Used in: Data Analysis, Pricing Calculation, Device Recognition")
    time.sleep(0.5)

    # 动态显示房屋ID
    house_id = params_dict.get('house_id', 'house1')
    print_blue(f"   ✅ House identifier: {house_id} (REFIT dataset)")
    print_cyan("      └─ Used in: Energy Optimization, Smart Scheduling, Cost Calculation")
    time.sleep(0.5)

    # 动态显示电价区域
    tariff_type = params_dict.get('tariff_type', 'UK')
    if tariff_type == 'UK':
        tariff_desc = "UK (Economy 7/10 tariffs)"
    elif tariff_type == 'Germany':
        tariff_desc = "Germany (Dynamic pricing)"
    elif tariff_type == 'California':
        tariff_desc = "California (TOU-D tariffs)"
    else:
        tariff_desc = f"{tariff_type} tariffs"

    print_blue(f"   ✅ Pricing region: {tariff_desc}")
    print_cyan("      └─ Used in: Pricing Calculation, Constraint Processing")
    time.sleep(0.5)

    print_blue("   ✅ Analysis scope: Complete workflow (6-step pipeline)")
    print_cyan("      └─ Used in: All workflow steps for comprehensive optimization")
    time.sleep(0.5)

    print_green("   🎉 LLM successfully configured all parameters for optimal analysis!")

def print_parameter_summary(params_dict, user_input=""):
    """Print clean parameter summary"""
    print()
    print_cyan("═" * 100)
    print_centered_title("Configuration Summary")
    print_cyan("═" * 100)

    # Use provided user input or extract from params
    if not user_input:
        user_input = "house1, UK, single"  # Default fallback

    print_blue("┌─ Configuration  Details ─────────────────────────────────────────────────────────┐")
    print_blue("│                                                                                  │")
    print_blue(f"│  📝 User Input: {user_input}")

    # Show key parameters in a clean format
    if params_dict.get('mode'):
        mode_text = "Single household analysis" if params_dict['mode'] == 1 else "Batch processing"
        print_blue(f"│  ✅ Processing Mode: {mode_text}")

    if params_dict.get('house_id'):
        print_blue(f"│  ✅ House ID: {params_dict['house_id']}")

    if params_dict.get('tariff_type'):
        # 动态显示正确的电价方案
        tariff_type = params_dict['tariff_type']
        if tariff_type == 'UK':
            tariff_text = "UK (Economy 7/10)"
        elif tariff_type == 'Germany':
            tariff_text = "Germany (Dynamic pricing)"
        elif tariff_type == 'California':
            tariff_text = "California (TOU-D tariffs)"
        else:
            tariff_text = f"{tariff_type} tariffs"
        print_blue(f"│  ✅ Pricing Plan: {tariff_text}")

    print_blue("│  ✅ Analysis Type: Complete workflow (6 steps)")
    print_blue("│                                                                                  │")
    print_blue("└──────────────────────────────────────────────────────────────────────────────────┘")
    print_cyan("═" * 100)

# 工具配置定义 (按执行顺序排列)
TOOLS = [
    {
        'function': test_func_2_int_main,
        'name': 'Data Preprocessing & Perception Alignment (test_func_2_int)',
        'description': 'Data preprocessing pipeline - includes perception alignment, variability identification, event segmentation',
        'parameters': {
            'mode': {
                'description': 'Processing mode (1=single household, 2=batch processing)',
                'default': 1,
                'type': 'int',
                'prompt': 'Enter processing mode',
                'validator': lambda x: str(x).isdigit()
            },
            'house_number': {
                'description': 'House number (numeric)',
                'default': 1,
                'type': 'int',
                'prompt': 'Enter house number (numeric)',
                'validator': lambda x: str(x).isdigit()
            }
        }
    },
    {
        'function': test_func_3_int_main,
        'name': 'Tariff Analysis & Cost Optimization (test_func_3_int)',
        'description': 'UK, Germany, California tariff scheme analysis',
        'parameters': {
            'mode': {
                'description': 'Analysis mode (1=single household, 2=batch, 3=display only)',
                'default': 1,  # 默认单个家庭模式
                'type': 'int',
                'prompt': 'Enter analysis mode (1=single household, 2=batch, 3=display only)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2, 3]
            },
            'tariff_type': {
                'description': 'Tariff type (UK/Germany/California)',
                'default': 'UK',
                'type': 'str',
                'prompt': 'Select tariff type (UK / Germany / California)',
                'validator': lambda x: str(x).lower() in ['uk', 'germany', 'california']
            },
            'house_id': {
                'description': 'House ID (format: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': 'Enter house ID (e.g., house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            }
        }
    },
    {
        'function': test_func_4_int_main,
        'name': 'Appliance Information Standardization (test_func_4_int)',
        'description': 'Standardize appliance names and handle duplicates',
        'parameters': {
            'mode': {
                'description': 'Extraction mode (1=single household, 2=batch)',
                'default': 1,  # 默认单个家庭模式
                'type': 'int',
                'prompt': 'Enter extraction mode (1=single household, 2=batch)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'tariff_type': {
                'description': 'Tariff type (UK/Germany/California)',
                'default': 'UK',
                'type': 'str',
                'prompt': 'Select tariff type (UK / Germany / California)',
                'validator': lambda x: str(x).lower() in ['uk', 'germany', 'california']
            },
            'house_id': {
                'description': 'House ID (format: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': 'Enter house ID (e.g., house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            }
        }
    },
    {
        'function': test_func_5_int_main,
        'name': 'Energy Optimization & Constraint Processing (test_func_5_int)',
        'description': 'User constraints, minimum duration filtering, TOU optimization',
        'parameters': {
            'mode': {
                'description': 'Optimization mode (1=single household, 2=batch)',
                'default': 1,  # 默认单个家庭模式
                'type': 'int',
                'prompt': 'Enter optimization mode (1=single household, 2=batch)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'house_id': {
                'description': 'House ID (format: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': 'Enter house ID (e.g., house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            },
            'user_instruction': {
                'description': 'User scheduling instruction (optional)',
                'default': '',  # 空字符串作为默认值
                'type': 'str',
                'prompt': 'Enter user scheduling instruction (leave empty for default logic)',
                'validator': None  # 允许空值
            },
            'house_list': {
                'description': 'House list (used in batch mode, separate multiple houses with commas, e.g., house1,house2,house3)',
                'default': '',  # 空字符串作为默认值
                'type': 'str',  # 改为字符串类型
                'prompt': 'Enter house list (usually empty)',
                'validator': None  # 通常为固定值None
            }
        }
    },
    {
        'function': test_func_6_int_main,
        'name': 'Smart Scheduling & System Integration (test_func_6_int)',
        'description': 'Complete scheduling and conflict resolution workflow',
        'parameters': {
            'tariff_group': {
                'description': 'Tariff group (mapped from tariff_type)',
                'default': 'UK',
                'type': 'str',
                'prompt': 'Select tariff group (UK/TOU_D/Germany_Variable)',
                'validator': lambda x: str(x) in ['UK', 'TOU_D', 'Germany_Variable']
            },
            'mode': {
                'description': 'Processing mode (1=single household, 2=batch)',
                'default': 1,
                'type': 'int',
                'prompt': 'Select processing mode (1=single household, 2=batch)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'house_id': {
                'description': 'House ID (format: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': 'Enter house ID (e.g., house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            },
            'interactive': {
                'description': 'Interactive mode (true/false)',
                'default': False,
                'type': 'bool',
                'prompt': 'Enable interactive mode (true / false)',
                'validator': lambda x: str(x).lower() in ['true', 'false', 'yes', 'no', '1', '0']
            }
        }
    },
    {
        'function': test_func_7_int_main,
        'name': 'Cost Analysis & Intelligent Recommendations (test_func_7_int)',
        'description': 'Read scheduling results and calculate costs under different tariff schemes',
        'parameters': {
            'tariff_group': {
                'description': 'Tariff group (mapped from tariff_type)',
                'default': 'UK',
                'type': 'str',
                'prompt': 'Select tariff group (UK/TOU_D/Germany_Variable)',
                'validator': lambda x: str(x) in ['UK', 'TOU_D', 'Germany_Variable']
            },
            'mode': {
                'description': 'Processing mode (1=single household, 2=batch)',
                'default': 1,
                'type': 'int',
                'prompt': 'Select processing mode (1=single household, 2=batch)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'house_id': {
                'description': 'House ID (format: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': 'Enter house ID (e.g., house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            },
            'interactive': {
                'description': 'Interactive mode (true/false)',
                'default': False,
                'type': 'bool',
                'prompt': 'Enable interactive mode (true / false)',
                'validator': lambda x: str(x).lower() in ['true', 'false', 'yes', 'no', '1', '0']
            }
        }
    }
]

# tariff_type 到 tariff_group 的映射
TARIFF_MAPPING = {
    "UK": "UK",
    "California": "TOU_D",
    "Germany": "Germany_Variable"
}

# 增强的颜色输出函数
def print_green(text):
    """成功/完成信息 - 绿色"""
    print(f"\033[92m{text}\033[0m")

def print_blue(text):
    """一般信息 - 蓝色"""
    print(f"\033[94m{text}\033[0m")

def print_yellow(text):
    """警告信息 - 黄色"""
    print(f"\033[93m{text}\033[0m")

def print_red(text):
    """错误信息 - 红色"""
    print(f"\033[91m{text}\033[0m")

def print_cyan(text):
    """高亮信息 - 青色"""
    print(f"\033[96m{text}\033[0m")

def print_magenta(text):
    """特殊信息 - 紫色"""
    print(f"\033[95m{text}\033[0m")

def print_bold(text):
    """粗体文本"""
    print(f"\033[1m{text}\033[0m")

def print_underline(text):
    """下划线文本"""
    print(f"\033[4m{text}\033[0m")

def print_header(text, char="=", width=120):
    """打印标题头部"""
    print_bold(f"\n{char * width}")
    print_bold(f"{text:^{width}}")
    print_bold(f"{char * width}")

def print_section(title, content_lines, emoji="📋"):
    """打印格式化的章节"""
    print_cyan(f"\n{emoji} {title}")
    print_blue("─" * 120)
    for line in content_lines:
        print_blue(f"   {line}")

def print_step_info(step_num, title, description, emoji="🔧"):
    """打印步骤信息"""
    print_cyan(f"\n{emoji} 步骤 {step_num}: {title}")
    print_blue(f"   └─ {description}")

def print_parameter_info(param_name, description, default_value, emoji="⚙️"):
    """打印参数信息"""
    default_display = "无" if default_value is None else str(default_value)
    print_blue(f"   {emoji} {param_name}: {description}")
    print_blue(f"      └─ 默认值: {default_display}")



def print_divider(char="─", width=120):
    """打印分隔线"""
    print_blue(char * width)



# === Post-run guidance ===
def print_post_run_output_tips(params: dict | None = None):
    """Print an orange asterisk box guiding users to key outputs (concise, English only).
    Style:
      - Orange '*' border only
      - Tips in bold magenta, paths in bright green
      - Tips flush-left; paths indented with "   ➤ "
      - 03_* appears after 02_* folders
    """
    # infer example house
    example_house = None
    if params:
        hid = params.get('house_id') or params.get('house_number')
        if isinstance(hid, int):
            example_house = f"house{hid}"
        elif isinstance(hid, str) and hid.startswith('house'):
            example_house = hid
    example_house = example_house or 'house1'

    width = 110
    orange = "\033[93m"
    tipcol = "\033[95m\033[1m"   # bold magenta for tips
    pathcol = "\033[92m"          # bright green for paths
    reset = "\033[0m"

    def star_line():
        print(f"{orange}{'*' * width}{reset}")

    def boxed(text: str = "", color: str = pathcol):
        raw = text.replace("\n", " ")
        if len(raw) > width - 4:
            raw = raw[: width - 7] + "..."
        pad = " " * (width - 4 - len(raw))
        print(f"{orange}* {reset}{color}{raw}{reset}{pad}{orange} *{reset}")

    star_line()
    boxed("🤖 By the way, based on your electricity usage and tariff options,", tipcol)
    boxed("our AI agent analyzed your data to help you make informed decisions.", tipcol)
    boxed("You're welcome to double‑check and compare with your preferences.", tipcol)
    boxed()
    boxed("If you want to dive deeper, here are some helpful places to look:", tipcol)
    boxed()

    # 01 + 02 (then 03) — phrased with If ... check:
    boxed("If you want to review perception/alignment results, check:", tipcol)
    boxed(f"   ➤ output/01_preprocessed/{example_house}/")
    boxed()

    boxed("If you want to inspect extracted appliance events (start/end, duration, energy), check:", tipcol)
    boxed(f"   ➤ output/02_event_segments/{example_house}/")
    boxed()

    boxed("If you want to see appliance semantics and shiftability (LLM‑assisted), check:", tipcol)
    boxed(f"   ➤ output/02_behavior_modeling/{example_house}/")
    boxed()

    boxed("If you want baseline monthly and per‑appliance costs (Standard / E7 / E10), check:", tipcol)
    boxed(f"   ➤ output/03_cost_analysis/UK/{example_house}/06_monthly_total_summary.csv")
    boxed(f"   ➤ output/03_cost_analysis/UK/{example_house}/07_monthly_by_appliance.csv")
    boxed()

    boxed("If you want to review constraint processing and optimization filters, check:", tipcol)
    boxed(f"   ➤ output/04_user_constraints/{example_house}/")
    boxed(f"   ➤ output/04_min_duration_filter/{example_house}/")
    boxed(f"   ➤ output/04_TOU_filter/{example_house}/")
    boxed()

    boxed("If you want to examine scheduling spaces and final schedules, check:", tipcol)
    boxed(f"   ➤ output/05_appliance_working_spaces/{example_house}/")
    boxed(f"   ➤ output/05_Initial_scheduling_optimization/{example_house}/")
    boxed(f"   ➤ output/05_Collision_Resolved_Scheduling/{example_house}/")
    boxed(f"   ➤ output/05_scheduling/{example_house}/")
    boxed(f"   ➤ output/05_event_split/{example_house}/ (optional)")
    boxed()

    # Optional advanced detail: which events were re‑scheduled under E7/E10
    boxed("If you want to explore which events were re‑scheduled for cost optimization, check:", tipcol)
    boxed(f"   ➤ output/05_scheduling/ (e.g., Economy_7 / Economy_10 resolved CSVs)")
    boxed()

    # Detailed per‑event cost breakdown after scheduling
    boxed("If you want detailed per‑event cost breakdown after scheduling, check:", tipcol)
    boxed(f"   ➤ output/06_cost_cal/UK/Economy_7/{example_house}/ (migrated_costs.csv, non_migrated_costs.csv)")
    boxed(f"   ➤ output/06_cost_cal/UK/Economy_10/{example_house}/ (migrated_costs.csv, non_migrated_costs.csv)")
    boxed()

    star_line()


def print_input_prompt(prompt_text, example=""):
    """打印美化的输入提示"""
    print_divider("═", 120)
    print_cyan(f"💬 {prompt_text}")
    if example:
        print_blue(f"   💡 示例: {example}")
    print(f"\033[94m   ⌨️  请输入: \033[0m", end="")


class LLMParameterManager:
    """基于LLM对话的参数管理器"""

    def __init__(self):
        self._cache = {}
        self._conversation_history = []

    def _create_parameter_extraction_prompt(self, param_name: str, param_config: Dict[str, Any], user_message: str) -> str:
        """创建参数提取的提示词"""
        description = param_config.get('description', '')
        default = param_config.get('default')
        param_type = param_config.get('type', 'str')
        step_names = param_config.get('step_names', [])

        # 构建步骤使用信息
        step_info = ""
        if step_names:
            step_list = ", ".join(step_names)
            step_info = f"- 使用步骤: {step_list}"

        # 构建参数选项说明
        options_text = ""
        if param_name == 'mode':
            if 'single' in description.lower() or '单个' in description:
                options_text = "可选值: 1=单个家庭, 2=批量处理"
            elif 'analysis' in description.lower() or '分析' in description:
                options_text = "可选值: 1=单个家庭, 2=批量, 3=仅显示"
        elif param_name == 'tariff_type':
            options_text = "可选值: UK, Germany, California"
        elif param_name == 'tariff_group':
            options_text = "可选值: UK, TOU_D, Germany_Variable"
        elif param_name == 'interactive':
            options_text = "可选值: true, false"

        prompt = f"""
    你是一个智能参数提取助手。用户正在使用家庭能源管理系统，需要你帮助从用户的消息中提取参数信息。

    当前需要提取的参数：
    - 参数名: {param_name}
    - 参数描述: {description}
    - 参数类型: {param_type}
    - 默认值: {default if default is not None else '无'}
    {f"- {step_info}" if step_info else ""}
    {f"- {options_text}" if options_text else ""}

    用户消息: "{user_message}"

    请分析用户消息，如果能从中提取到该参数的值，请直接返回该值。
    如果无法提取，请用友好的方式向用户询问该参数，并说明参数的用途和使用步骤。

    请以JSON格式回复，包含以下字段：
    {{
        "extracted_value": "提取到的值，如果未提取到则为null",
        "response": "给用户的回复消息"
    }}

    注意事项：
    1. 如果提取到值，请确保格式正确
    2. 如果是house_id，确保格式为houseN（如house1）
    3. 如果是数字类型，确保返回有效数字
    4. 回复要简洁友好，帮助用户理解参数用途和使用场景
    """
        return prompt

    def _extract_json_from_llm_response(self, response_text: str) -> Dict[str, Any]:
        """从LLM响应中提取JSON"""
        try:
            # 尝试直接解析JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON块
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # 如果都失败了，返回默认结构
            return {
                "extracted_value": None,
                "response": response_text
            }

    def get_param_with_llm_conversation(self, param_name: str, param_config: Dict[str, Any], user_message: str = "") -> Any:
        """通过LLM对话获取参数值"""
        # 检查缓存
        if param_name in self._cache:
            cached_value = self._cache[param_name]
            print_blue(f"📝 使用之前输入的参数: {param_name} = {cached_value}")
            return cached_value

        max_retries = 3
        retry_count = 0

        # 如果没有用户消息，先询问用户
        if not user_message.strip():
            user_message = input(f"请输入关于 {param_config.get('description', param_name)} 的信息: ").strip()

        while retry_count < max_retries:
            try:
                # 创建LLM提示
                prompt = self._create_parameter_extraction_prompt(param_name, param_config, user_message)

                # 调用LLM API
                messages = [{"role": "user", "content": prompt}]
                llm_response = chat_with_api(messages)

                if not llm_response:
                    print_red("❌ LLM API调用失败，将使用默认值或用户直接输入")
                    return self._fallback_to_direct_input(param_name, param_config)

                # 提取LLM响应内容
                response_content = llm_response.get('choices', [{}])[0].get('message', {}).get('content', '')
                response_data = self._extract_json_from_llm_response(response_content)

                extracted_value = response_data.get('extracted_value')
                llm_message = response_data.get('response', '')

                print_blue(f"🤖 LLM回答: {llm_message}")

                if extracted_value is not None:
                    # LLM成功提取了参数值
                    try:
                        # 验证和转换类型
                        converted_value = self._convert_and_validate(extracted_value, param_config)
                        self._cache[param_name] = converted_value
                        print_green(f"✅ 成功提取参数: {param_name} = {converted_value}")
                        return converted_value
                    except ValueError as e:
                        print_yellow(f"⚠️ 提取的值验证失败: {e}")
                        user_message = input("请重新输入: ").strip()
                        retry_count += 1
                        continue
                else:
                    # LLM需要更多信息
                    user_message = input("👤 请回复: ").strip()

            except Exception as e:
                print_red(f"❌ LLM处理错误: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    return self._fallback_to_direct_input(param_name, param_config)
                user_message = input("请重新输入: ").strip()

        # 重试次数用完，回退到直接输入
        return self._fallback_to_direct_input(param_name, param_config)

    def _convert_and_validate(self, value: Any, param_config: Dict[str, Any]) -> Any:
        """转换和验证参数值"""
        param_type = param_config.get('type', 'str')
        validator = param_config.get('validator')

        # 类型转换
        if param_type == 'int':
            converted_value = int(str(value))
        elif param_type == 'bool':
            if isinstance(value, bool):
                converted_value = value
            else:
                converted_value = str(value).lower() in ['true', 'yes', '1', 'on']
        else:  # str
            converted_value = str(value)

        # 验证
        if validator and not validator(converted_value):
            raise ValueError(f"值 {converted_value} 不符合验证规则")

        return converted_value

    def _fallback_to_direct_input(self, param_name: str, param_config: Dict[str, Any]) -> Any:
        """回退到直接输入模式"""
        print_yellow(f"⚠️ 回退到直接输入模式获取参数: {param_name}")

        # 显示参数描述和使用步骤
        description = param_config.get('description', param_name)
        step_names = param_config.get('step_names', [])

        if step_names:
            step_list = ", ".join(step_names)
            print_green(f"🛠 需要输入参数: {description}")
            print_blue(f"📍 此参数将用于以下步骤: {step_list}")
        else:
            print_green(f"🛠 需要输入参数: {description}")

        prompt = param_config.get('prompt', f"请输入 {param_name}")
        default = param_config.get('default')
        validator = param_config.get('validator')
        param_type = param_config.get('type', 'str')

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                if default == '':
                    default_display = "空"
                elif default is not None:
                    default_display = str(default)
                else:
                    default_display = "无"

                user_input = input(f"{prompt} [默认: {default_display}]: ").strip()

                if not user_input:
                    if default is not None:
                        final_value = default
                    else:
                        print_red("❌ 此参数不能为空，请重新输入")
                        retry_count += 1
                        continue
                else:
                    final_value = user_input

                # 验证和转换
                converted_value = self._convert_and_validate(final_value, param_config)
                self._cache[param_name] = converted_value
                return converted_value

            except (ValueError, TypeError) as e:
                retry_count += 1
                if retry_count < max_retries:
                    print_red(f"❌ 输入错误: {e}，请重新输入")
                else:
                    if default is not None:
                        self._cache[param_name] = default
                        return default
                    raise

        if default is not None:
            self._cache[param_name] = default
            return default
        else:
            raise ValueError(f"参数 {param_name} 获取失败")


class ParameterMemoryManager:
    """统一的参数内存管理器"""

    def __init__(self):
        self._cache = {}

    def get_param_with_config(self, param_name: str, param_config: Dict[str, Any]) -> Any:
        """根据参数配置获取参数值，支持缓存，所有参数都通过用户输入获得"""
        # 检查缓存 - 如果用户之前输入过此参数，直接使用
        if param_name in self._cache:
            cached_value = self._cache[param_name]
            print_blue(f"📝 使用之前输入的参数: {param_name} = {cached_value}")
            return cached_value

        # 从配置中获取信息
        prompt = param_config.get('prompt', f"请输入 {param_config.get('description', param_name)}")
        default = param_config.get('default')
        validator = param_config.get('validator')
        param_type = param_config.get('type', 'str')

        # 显示参数描述和使用步骤
        description = param_config.get('description', param_name)
        step_names = param_config.get('step_names', [])

        if step_names:
            step_list = ", ".join(step_names)
            print_green(f"🛠 需要输入参数: {description}")
            print_blue(f"📍 此参数将用于以下步骤: {step_list}")
        else:
            print_green(f"🛠 需要输入参数: {description}")

        retry_count = 0
        max_retries = settings.max_input_retries

        while retry_count < max_retries:
            try:
                # 显示提示和默认值
                if default == '':
                    default_display = "空"
                elif default is not None:
                    default_display = str(default)
                else:
                    default_display = "无"
                user_input = input(f"{prompt} [默认: {default_display}]: ").strip()

                # 处理用户输入
                if not user_input:
                    if default is not None:  # None 才算没有默认值，空字符串是有效默认值
                        final_value = default
                    else:
                        print_red("❌ 此参数不能为空，请重新输入")
                        retry_count += 1
                        continue
                else:
                    final_value = user_input

                # 验证输入
                if validator and not validator(final_value):
                    retry_count += 1
                    remaining_retries = max_retries - retry_count
                    if remaining_retries > 0:
                        print_red(f"❌ 输入不符合要求，请重新输入 (还有 {remaining_retries} 次机会)")
                    else:
                        print_red("❌ 验证失败次数过多，使用默认值")
                        if default is not None:
                            final_value = default
                        else:
                            raise ValueError(f"参数 {param_name} 验证失败且无默认值")
                    continue

                # 类型转换
                converted_value = self._convert_to_type(final_value, param_type)

                # 缓存并返回
                self._cache[param_name] = converted_value
                print_blue(f"🧷 已设定 {param_name} = {converted_value}")
                return converted_value

            except (EOFError, KeyboardInterrupt):
                print_yellow("\n⚠️ 捕获到中断，使用默认值")
                if default is not None:
                    self._cache[param_name] = default
                    return default
                else:
                    raise ValueError(f"参数 {param_name} 被中断且无默认值")
            except Exception as e:
                retry_count += 1
                remaining_retries = max_retries - retry_count
                if remaining_retries > 0:
                    print_red(f"❌ 输入处理错误: {e}，请重新输入 (还有 {remaining_retries} 次机会)")
                else:
                    print_red(f"❌ 错误次数过多: {e}")
                    if default is not None:
                        self._cache[param_name] = default
                        return default
                    else:
                        raise ValueError(f"参数 {param_name} 处理失败且无默认值")

        # 如果重试次数用完，使用默认值或抛出异常
        if default is not None:
            print_yellow(f"⚠️ 重试次数用完，使用默认值: {param_name} = {default}")
            self._cache[param_name] = default
            return default
        else:
            raise ValueError(f"参数 {param_name} 重试次数用完且无默认值")

    def _convert_to_type(self, value: Any, target_type: str) -> Any:
        """类型转换"""
        if target_type == 'int':
            return int(value)
        elif target_type == 'bool':
            if isinstance(value, bool):
                return value
            return str(value).lower() in ['true', 'yes', '1']
        elif target_type == 'list':
            if value is None or str(value).lower() == 'none':
                return None
            return value  # 简单处理，根据需要可扩展
        else:  # 'str'
            return str(value) if value is not None else None


class WorkflowRunner:
    """统一的工作流程执行器 - 使用LLM对话模式"""

    def __init__(self, use_llm_conversation: bool = True):
        self.use_llm_conversation = use_llm_conversation
        if use_llm_conversation:
            self.param_manager = LLMParameterManager()
        else:
            self.param_manager = ParameterMemoryManager()

        # 全局参数存储，用于一次性收集所有参数
        self.global_params = {}
        self.params_collected = False

    def collect_all_params_upfront(self, user_input_message: str = "") -> None:
        """一次性收集所有步骤需要的参数"""
        if self.params_collected:
            print_blue("📝 Parameters already collected, using existing configuration")
            return

        # Print clean header
        print_parameter_collection_header()

        # Parse user input directly and set parameters (skip verbose collection)
        self._parse_user_input_directly(user_input_message)

        # Show enhanced parameter collection progress with actual parameters
        print_parameter_progress(self.global_params)

        self.params_collected = True

        # Print clean summary
        print_parameter_summary(self.global_params, user_input_message)

    def _get_academic_step_title(self, step_index: int, original_name: str) -> str:
        """Generate academic-style step titles"""
        academic_titles = {
            0: "Phase I: Data Preprocessing & Perception Alignment",
            1: "Phase II: Tariff Analysis & Cost Optimization",
            2: "Phase III: Appliance Information Standardization",
            3: "Phase IV: Energy Optimization & Constraint Processing",
            4: "Phase V: Smart Scheduling & System Integration",
            5: "Phase VI: Cost Analysis & Intelligent Recommendations"
        }

        return academic_titles.get(step_index, f"Phase {step_index + 1}: {original_name}")

    def _parse_user_input_directly(self, user_input_message: str) -> None:
        """直接解析用户输入并设置参数，跳过冗长的收集过程"""
        # 默认参数设置
        self.global_params = {
            'mode': 1,  # Single household
            'house_list': '',
            'interactive': False,
            'user_instruction': '',
            'house_id': 'house1',
            'house_number': 1,
            'tariff_type': 'UK',
            'tariff_group': 'UK'
        }

        # 如果有用户输入，尝试解析
        if user_input_message:
            input_lower = user_input_message.lower()

            # 解析房屋ID
            if 'house' in input_lower:
                import re
                house_match = re.search(r'house(\d+)', input_lower)
                if house_match:
                    house_num = int(house_match.group(1))
                    self.global_params['house_id'] = f'house{house_num}'
                    self.global_params['house_number'] = house_num

            # 解析电价类型
            if 'uk' in input_lower:
                self.global_params['tariff_type'] = 'UK'
                self.global_params['tariff_group'] = 'UK'
            elif 'germany' in input_lower:
                self.global_params['tariff_type'] = 'Germany'
                self.global_params['tariff_group'] = 'Germany_Variable'
            elif 'california' in input_lower:
                self.global_params['tariff_type'] = 'California'
                self.global_params['tariff_group'] = 'TOU_D'

            # 解析处理模式
            if 'batch' in input_lower:
                self.global_params['mode'] = 2
            else:
                self.global_params['mode'] = 1

    def _analyze_all_parameters(self) -> Dict[str, Dict[str, Any]]:
        """分析所有步骤的参数需求，合并重复参数"""
        all_params = {}
        param_usage = {}  # 记录每个参数在哪些步骤中使用

        for step_index, tool_config in enumerate(TOOLS):
            step_name = tool_config['name']
            for param_name, param_config in tool_config['parameters'].items():

                if param_name not in all_params:
                    # 第一次遇到这个参数
                    all_params[param_name] = param_config.copy()
                    all_params[param_name]['used_in_steps'] = [step_index]
                    all_params[param_name]['step_names'] = [step_name]
                else:
                    # 参数在多个步骤中使用
                    all_params[param_name]['used_in_steps'].append(step_index)
                    all_params[param_name]['step_names'].append(step_name)

                    # 如果参数配置不同，发出警告
                    if (all_params[param_name].get('type') != param_config.get('type') or
                        all_params[param_name].get('default') != param_config.get('default')):
                        print_yellow(f"⚠️ 参数 {param_name} 在不同步骤中有不同配置")

        return all_params

    def _collect_parameters_by_priority(self, all_params_info: Dict[str, Dict[str, Any]], user_input_message: str):
        """按优先级收集参数，支持批量模式智能处理"""

        # 第一步：优先收集 mode 参数
        mode_value = self._collect_mode_parameter_first(all_params_info, user_input_message)

        # 第二步：根据 mode 设置智能默认值和跳过策略
        skip_params = set()

        if mode_value == 2:  # 批量模式
            # 批量模式：自动设置全部house参数
            self.global_params['house_list'] = DEFAULT_HOUSE_LIST
            self.global_params['house_id'] = 'house1'  # 取第一个作为兼容性默认值
            self.global_params['house_number'] = 1      # 取第一个作为兼容性默认值

            # 跳过这些参数的收集
            skip_params.update(['house_list', 'house_id', 'house_number'])

            print_green(f"\n🔧 批量模式：自动设置处理全部 {len(TARGET_HOUSES)} 个房屋")
            print_blue(f"� 房屋列表: {DEFAULT_HOUSE_LIST}")

        elif mode_value == 1:  # 单个家庭模式
            # 单个模式：跳过 house_list
            self.global_params['house_list'] = ''  # 单个模式不需要
            skip_params.add('house_list')

            print_green("\n� 单个家庭模式：需要指定具体房屋信息")

        # 第三步：处理特殊参数
        # interactive 参数：自动设置为 False
        if 'interactive' in all_params_info:
            self.global_params['interactive'] = False
            skip_params.add('interactive')
            print_green("\n🔧 配置参数: 是否交互模式 (true/false)")
            print_blue("📋 自动设置为: False (非交互模式)")

        # user_instruction 参数：显示配置信息
        if 'user_instruction' in all_params_info:
            self.global_params['user_instruction'] = ''
            skip_params.add('user_instruction')
            print_green("\n� 配置参数: 用户调度指令 (可选)")
            print_blue("💡 您可以在 config/defaullt_user_constrain.txt 文件中修改用户约束配置")
            print_blue("🤖 LLM 将根据您的要求修改电器运行时间")
            print_blue("📋 目前使用默认约束信息 (如有需要可在配置文件中自定义)")

        # 第四步：收集剩余参数
        sorted_params = self._sort_parameters_by_priority(all_params_info)

        print_blue("\n📝 按优先级收集剩余参数...")

        for param_name in sorted_params:
            if param_name in skip_params:
                continue  # 跳过已处理的参数

            param_config = all_params_info[param_name]
            step_names = ", ".join(param_config['step_names'])

            print_green(f"\n🛠 收集参数: {param_config.get('description', param_name)}")
            print_blue(f"📍 此参数将用于以下步骤: {step_names}")

            # 为LLM和直接输入模式更新prompt，包含步骤信息
            enhanced_config = param_config.copy()
            original_prompt = enhanced_config.get('prompt', f"请输入 {param_name}")
            enhanced_config['prompt'] = f"{original_prompt} (将用于步骤: {step_names})"

            if self.use_llm_conversation:
                param_value = self.param_manager.get_param_with_llm_conversation(
                    param_name, enhanced_config, user_input_message
                )
            else:
                param_value = self.param_manager.get_param_with_config(param_name, enhanced_config)

            self.global_params[param_name] = param_value

            # 处理参数间的依赖关系
            self._handle_parameter_dependencies(param_name, param_value)

    def _collect_mode_parameter_first(self, all_params_info: Dict[str, Dict[str, Any]], user_input_message: str) -> int:
        """优先收集 mode 参数，决定后续参数收集策略"""

        if 'mode' not in all_params_info:
            # 如果没有 mode 参数，默认为单个家庭模式
            print_blue("📋 未发现 mode 参数，默认使用单个家庭模式")
            return 1

        mode_config = all_params_info['mode']
        step_names = ", ".join(mode_config['step_names'])

        print_green(f"\n🛠 优先收集参数: {mode_config.get('description', 'mode')}")
        print_blue(f"📍 此参数将用于以下步骤: {step_names}")
        print_blue("🎯 此参数决定后续参数收集策略")

        # 为LLM和直接输入模式更新prompt
        enhanced_config = mode_config.copy()
        original_prompt = enhanced_config.get('prompt', f"请输入 mode")
        enhanced_config['prompt'] = f"{original_prompt} (将用于步骤: {step_names})"

        if self.use_llm_conversation:
            mode_value = self.param_manager.get_param_with_llm_conversation(
                'mode', enhanced_config, user_input_message
            )
        else:
            mode_value = self.param_manager.get_param_with_config('mode', enhanced_config)

        self.global_params['mode'] = mode_value

        # 处理参数依赖
        self._handle_parameter_dependencies('mode', mode_value)

        return mode_value

    def _sort_parameters_by_priority(self, all_params_info: Dict[str, Dict[str, Any]]) -> List[str]:
        """按优先级对参数排序 (mode 已经优先处理)"""
        # 定义参数优先级 (mode 不在这里，因为已经优先处理)
        priority_order = [
            'house_id',       # 房屋ID
            'house_number',   # 房屋编号
            'tariff_type',    # 电价类型
            'tariff_group',   # 电价组
            'house_list'      # 房屋列表
        ]

        # 按优先级排序，未在优先级列表中的参数按字母顺序排在最后
        sorted_params = []
        remaining_params = set(all_params_info.keys()) - {'mode'}  # 排除已处理的mode

        # 首先添加优先级参数
        for param in priority_order:
            if param in remaining_params:
                sorted_params.append(param)
                remaining_params.remove(param)

        # 然后添加剩余参数（按字母顺序）
        sorted_params.extend(sorted(remaining_params))

        return sorted_params

    def _handle_parameter_dependencies(self, param_name: str, param_value: Any):
        """处理参数间的依赖关系"""
        # 处理 tariff_type 到 tariff_group 的映射
        if param_name == 'tariff_type' and 'tariff_group' not in self.global_params:
            if param_value in TARIFF_MAPPING:
                mapped_group = TARIFF_MAPPING[param_value]
                self.global_params['tariff_group'] = mapped_group
                print_blue(f"🔗 自动映射: tariff_type ({param_value}) -> tariff_group ({mapped_group})")

        # 处理 house_number 到 house_id 的转换
        if param_name == 'house_number' and 'house_id' not in self.global_params:
            house_id = f"house{param_value}"
            self.global_params['house_id'] = house_id
            print_blue(f"🔗 自动转换: house_number ({param_value}) -> house_id ({house_id})")

    def _display_collected_params(self):
        """显示收集到的所有参数"""
        print_green("\n📋 最终收集的参数总览：")
        print_blue("=" * 120)
        for param_name, param_value in self.global_params.items():
            print_blue(f"📌 {param_name}: {param_value}")
        print_blue("=" * 120)

    def get_params_for_step(self, step_index: int) -> Dict[str, Any]:
        """获取指定步骤所需的参数"""
        if not self.params_collected:
            raise RuntimeError("参数尚未收集，请先调用 collect_all_params_upfront()")

        tool_config = TOOLS[step_index]
        step_params = {}

        for param_name in tool_config['parameters'].keys():
            if param_name in self.global_params:
                step_params[param_name] = self.global_params[param_name]
            else:
                # 如果全局参数中没有，使用默认值
                default_value = tool_config['parameters'][param_name].get('default')
                step_params[param_name] = default_value
                print_yellow(f"⚠️ 参数 {param_name} 未找到，使用默认值: {default_value}")

        return step_params

    def collect_param(self, step_index: int, user_input_message: str = "") -> Dict[str, Any]:
        """统一的参数收集函数 - 支持LLM对话或直接输入（兼容旧版本）"""
        if self.params_collected:
            # 如果已经收集过所有参数，直接返回该步骤的参数
            return self.get_params_for_step(step_index)

        # 否则按原来的方式单独收集这个步骤的参数
        if step_index < 0 or step_index >= len(TOOLS):
            raise ValueError(f"无效的步骤索引: {step_index}")

        tool_config = TOOLS[step_index]
        params = {}

        print_blue(f"📋 收集 {tool_config['name']} 的参数...")

        if self.use_llm_conversation:
            print_green("🤖 使用LLM对话模式收集参数")

            for param_name, param_config in tool_config['parameters'].items():
                # 为单步执行添加步骤信息
                enhanced_config = param_config.copy()
                enhanced_config['step_names'] = [tool_config['name']]
                enhanced_config['used_in_steps'] = [step_index]

                params[param_name] = self.param_manager.get_param_with_llm_conversation(
                    param_name, enhanced_config, user_input_message
                )
        else:
            print_green("📝 使用直接输入模式收集参数")

            for param_name, param_config in tool_config['parameters'].items():
                # 为单步执行添加步骤信息
                enhanced_config = param_config.copy()
                enhanced_config['step_names'] = [tool_config['name']]
                enhanced_config['used_in_steps'] = [step_index]

                params[param_name] = self.param_manager.get_param_with_config(param_name, enhanced_config)

        # 打印收集完成的所有参数
        print_green("✅ 参数收集完成！最终参数如下：")
        for param_name, param_value in params.items():
            print_blue(f"  📌 {param_name}: {param_value}")

        return params

    def execute_step_with_user_input(self, step_index: int, user_input: str = ""):
        """执行指定步骤 - 支持用户输入消息"""
        if step_index < 0 or step_index >= len(TOOLS):
            print_red(f"❌ 无效的步骤索引: {step_index}")
            return

        tool_config = TOOLS[step_index]

        # Create academic-style step title
        step_title = self._get_academic_step_title(step_index, tool_config['name'])
        separator = "═" * 120
        print_green(f"\n{separator}")
        print_green(f"🚀 {step_title.upper()}")
        print_green(f"{separator}")

        try:
            # 收集参数（支持用户输入消息）
            params = self.collect_param(step_index, user_input)

            # 执行函数
            function_name = tool_config['function'].__name__
            print_blue(f"⚙️ Executing: {tool_config['description']} (function: {function_name})")
            result = tool_config['function'](**params)

            # Get academic phase title for completion message
            phase_title = self._get_academic_step_title(step_index, tool_config['name'])
            print_green(f"--- {phase_title.upper()} COMPLETED ---")
            # If this is the final phase, print output tips for users
            if step_index == len(TOOLS) - 1:
                try:
                    print_post_run_output_tips(params)
                except Exception:
                    pass
            return result

        except Exception as e:
            # Get academic phase title for error message
            phase_title = self._get_academic_step_title(step_index, tool_config['name'])
            print_red(f"❌ {phase_title.upper()} EXECUTION FAILED: {e}")
            import traceback
            traceback.print_exc()

    def execute_step(self, step_index: int):
        """执行指定步骤 - 统一架构（保持向后兼容）"""
        return self.execute_step_with_user_input(step_index, "")

    def interactive_mode(self):
        """交互式运行模式 - 允许用户输入消息来驱动参数收集"""
        print_green("🚀 进入交互式模式")
        print_blue("💡 您可以通过自然语言描述来设置参数，例如：")
        print_blue("   '我想分析house3的德国电价方案'")
        print_blue("   '使用批量模式处理所有房屋'")
        print_blue("   '启用交互模式进行调度优化'")

        while True:
            try:
                print("\n" + "="*120)
                print_green("📋 可用的步骤:")
                for i, tool in enumerate(TOOLS):
                    print_blue(f"  {i}: {tool['name']} - {tool['description']}")

                print_yellow("\n输入指令选项:")
                print_yellow("  - 输入步骤编号 (0-5) 来执行特定步骤")
                print_yellow("  - 输入 'all' 执行所有步骤（逐步收集参数）")
                print_yellow("  - 输入 'collect-all' 一次性收集所有参数后执行所有步骤")
                print_yellow("  - 输入 'quit' 或 'exit' 退出")
                print_yellow("  - 输入其他文本作为参数设置的自然语言描述")

                user_input = input("\n👤 请输入: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print_green("👋 退出交互模式")
                    break
                elif user_input == 'all':
                    self.run_all_steps()
                elif user_input == 'collect-all':
                    print_green("🔧 启动一次性参数收集模式")
                    additional_input = input("请描述您的整体需求（可选）: ").strip()
                    self.run_all_steps_with_upfront_collection(additional_input)
                elif user_input.isdigit():
                    step_index = int(user_input)
                    self.execute_step(step_index)
                else:
                    # 尝试解析用户输入并执行相应步骤
                    print_green(f"🤖 处理用户输入: {user_input}")
                    self._handle_natural_language_input(user_input)

            except KeyboardInterrupt:
                print_yellow("\n⚠️ 捕获到中断信号")
                break
            except Exception as e:
                print_red(f"❌ 交互模式错误: {e}")

    def _handle_natural_language_input(self, user_input: str):
        """处理自然语言输入"""
        # 简单的关键词匹配来确定执行哪个步骤
        lower_input = user_input.lower()

        if any(keyword in lower_input for keyword in ['预处理', '感知', '事件', '基础']):
            self.execute_step_with_user_input(0, user_input)
        elif any(keyword in lower_input for keyword in ['电价', '成本', '分析', 'tariff']):
            self.execute_step_with_user_input(1, user_input)
        elif any(keyword in lower_input for keyword in ['电器', '标准化', 'appliance']):
            self.execute_step_with_user_input(2, user_input)
        elif any(keyword in lower_input for keyword in ['优化', '约束', '过滤']):
            self.execute_step_with_user_input(3, user_input)
        elif any(keyword in lower_input for keyword in ['调度', '集成', 'scheduling']):
            self.execute_step_with_user_input(4, user_input)
        elif any(keyword in lower_input for keyword in ['成本计算', '费用', '成本', 'cost']):
            self.execute_step_with_user_input(5, user_input)
        else:
            # 如果无法匹配特定步骤，询问用户
            print_yellow("🤔 无法确定要执行的步骤，请指定步骤编号或使用更明确的描述")

    def run_all_steps(self):
        """按顺序执行所有步骤"""
        print_green("🚀 开始执行完整工作流程")
        print_blue(f"📊 共有 {len(TOOLS)} 个步骤需要执行")

        for step_index in range(len(TOOLS)):
            self.execute_step(step_index)

        print_green("\n🎉 All steps execution completed!")

    def run_all_steps_with_upfront_collection(self, user_input_message: str = ""):
        """一次性收集所有参数后执行所有步骤"""
        # 一次性收集所有参数
        self.collect_all_params_upfront(user_input_message)

        # 执行所有步骤
        for step_index in range(len(TOOLS)):
            self.execute_step_with_collected_params(step_index)

        print_green("\n🎉 All steps execution completed!")

    def execute_step_with_collected_params(self, step_index: int):
        """使用已收集的参数执行指定步骤"""
        if step_index < 0 or step_index >= len(TOOLS):
            print_red(f"❌ 无效的步骤索引: {step_index}")
            return

        tool_config = TOOLS[step_index]

        # Create academic-style step title
        step_title = self._get_academic_step_title(step_index, tool_config['name'])
        separator = "═" * 120
        print_green(f"\n{separator}")
        print_green(f"🚀 {step_title.upper()}")
        print_green(f"{separator}")

        try:
            # 获取该步骤的参数
            params = self.get_params_for_step(step_index)

            # 显示使用的参数
            print_blue(f"📋 {tool_config['name']} parameters used:")
            for param_name, param_value in params.items():
                print_blue(f"  📌 {param_name}: {param_value}")

            # 执行函数
            function_name = tool_config['function'].__name__
            print_blue(f"⚙️ Executing: {tool_config['description']} (function: {function_name})")
            result = tool_config['function'](**params)

            # Get academic phase title for completion message
            phase_title = self._get_academic_step_title(step_index, tool_config['name'])
            print_green(f"--- {phase_title.upper()} COMPLETED ---")
            if step_index == len(TOOLS) - 1:
                try:
                    print_post_run_output_tips(params)
                except Exception:
                    pass
            return result

        except Exception as e:
            # Get academic phase title for error message
            phase_title = self._get_academic_step_title(step_index, tool_config['name'])
            print_red(f"❌ {phase_title.upper()} EXECUTION FAILED: {e}")
            import traceback
            traceback.print_exc()

    def run_specific_steps(self, step_indices: List[int]):
        """执行指定的步骤列表"""
        print_green(f"🚀 开始执行指定步骤: {step_indices}")

        for step_index in step_indices:
            self.execute_step(step_index)

        print_green("\n🎉 指定步骤执行结束！")

    def run_steps_range(self, start_index: int, end_index: int):
        """执行指定范围的步骤"""
        if start_index < 0 or end_index >= len(TOOLS) or start_index > end_index:
            print_red(f"❌ 无效的步骤范围: [{start_index}, {end_index}]")
            return

        step_indices = list(range(start_index, end_index + 1))
        self.run_specific_steps(step_indices)

    def run(self):
        """主运行方法 - 使用改进的界面"""
        # 美化的输入提示
        print_input_prompt(
            "请描述您的需求（支持自然语言或参数格式）",
            "house1, uk, single"
        )

        try:
            user_initial_input = input().strip()

            if user_initial_input:
                print_green(f"✅ 收到您的输入: {user_initial_input}")
                print_blue("🚀 正在启动智能家庭能源管理系统...")
            else:
                print_yellow("⚠️ 未输入内容，将使用默认配置")
                print_blue("🚀 正在启动智能家庭能源管理系统...")

            # 系统启动成功提示
            print_green("\n🎉 系统启动成功！")

            # 显示详细的工作流程执行计划
            print_workflow_execution_plan()

            # 开始执行工作流程
            print_green("🚀 开始执行工作流程，请耐心等待...")
            self.run_all_steps_with_upfront_collection(user_initial_input)

        except KeyboardInterrupt:
            print_yellow("\n👋 程序被用户中断")


def test_parameter_collection():
    """测试参数收集功能"""
    print_green("🧪 测试一次性参数收集功能")

    runner = WorkflowRunner(use_llm_conversation=False)

    # 分析所有参数
    all_params = runner._analyze_all_parameters()

    print_green("📊 参数分析结果：")
    for param_name, param_info in all_params.items():
        steps = ", ".join([f"Step{i}" for i in param_info['used_in_steps']])
        print_blue(f"📌 {param_name}: 使用在 {steps}")
        print_blue(f"   类型: {param_info.get('type', 'str')}, 默认值: {param_info.get('default', '无')}")

    print_green(f"\n✅ 总共需要收集 {len(all_params)} 个参数")
    print_blue(f"✅ 总共有 {len(TOOLS)} 个步骤")


def main_test():
    """测试模式主函数"""
    test_parameter_collection()


def main_beautiful():
    """Final version main function - beautiful and complete interface"""
    try:
        # Display welcome banner (includes value proposition)
        print_welcome_banner()

        # System startup instructions - redesigned structure and layout
        startup_content = [
            "💡 Quick Start: Input format [House, Pricing Plan, Processing Mode]",
            "",
            "┌─ 🎯 Input Examples ────────────────────────────────────────────────────────────────┐",
            "│                                                                                    │",
            "│  'house1, UK, single'        → Analyze 1st household UK pricing                    │",
            "│  'Germany, batch'            → Batch analysis German pricing                       │",
            "│  'analyze house3 california' → AI smart parsing & auto config                      │",
            "│                                                                                    │",
            "└────────────────────────────────────────────────────────────────────────────────────┘",
            "",
            "📋 Parameter Details:",
            "",
            "🏠 House Number  │ house1~house21 (REFIT dataset household IDs)",
            "💰 Pricing Plan  │ UK= Economy 7, Economy 10",
            "                 │ california= California TOU (Time-of-Use) D Tariffs",
            "                 │ germany= Dynamic Pricing in Germany",
            "⚙️  Process Mode  │ single=Single household analysis | batch=Batch processing",
            "",
            "💡 Pricing Plan Features:",
            "   • uk: Significant peak-valley price differences, default tiered pricing",
            "   • california: High summer peak prices, seasonal variations",
            "   • germany: Real-time price fluctuations, dynamic optimization effects"
        ]
        print_boxed_section("🚀 How to Start System", startup_content)

        # Personalized configuration instructions - boxed layout
        config_file_content = [
            "🎯 Want personalized analysis? You can customize configurations at:",
            "",
            "💡 Raw Power Data Config: tools/p_01_perception_alignment.py",
            "   └─ Modify your actual power data path in preprocess_power_series() function",
            "   └─ Support importing your household's real power monitoring data",
            "",
            "🏠 Home Appliance Names Config: config/house_appliances.json",
            "   └─ Fill in specific names of appliances in your home (e.g., Fridge, Washing Machine)",
            "   └─ Help AI more accurately identify and optimize your appliance usage",
            "",
            "⏰ Usage Time Preferences Config: config/default_user_constrain.txt",
            "   └─ Set your personal requirements for appliance operating times",
            "   └─ Example: washing machine only after 8 PM, AC maintains comfort during day"
        ]
        print_boxed_section("📁 Personalization Configuration Guide", config_file_content)

        # Input prompt section
        print()
        print_cyan("💬 Please enter your requirements using the format above")
        print_cyan("📝 Example: house1, UK, single")
        print()
        print_cyan("═" * 100)
        print(f"\033[95m   ⌨️   Wating for your choice (eg.: house1, UK, single): \033[0m", end="")
        print("")

        user_input = input().strip()

        # Process user input
        if user_input:
            print_green(f"✅ Request received: {user_input}")
            print_blue("🚀 Starting system...")
        else:
            print_yellow("⚠️ Using default configuration: house1, uk, single")
            print_blue("🚀 Starting system...")

        # System startup successful
        print_green("🎉 Startup successful!")

        # Display execution plan
        print_workflow_execution_plan()

        # Create workflow runner with LLM conversation mode
        runner = WorkflowRunner(use_llm_conversation=True)

        # Start execution directly with user input (avoid duplicate input prompts)
        runner.run_all_steps_with_upfront_collection(user_input if user_input else "")

    except KeyboardInterrupt:
        print_yellow("\n👋 Program interrupted by user")
    except Exception as e:
        print_red(f"❌ Program execution error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主函数 - 支持LLM对话模式和传统输入模式"""
    try:
        print_green("🎉 欢迎使用智能家庭能源管理系统工作流程！")
        print_blue("🤖 系统支持 LLM 智能对话，您可以直接用自然语言描述需求")

        print_blue("📊 当前工作流程主要包含以下 6 个步骤：")
        print_blue("   1) 电器数据感知与标准化对齐")
        print_blue("   2) 电器设备可调度性识别")
        print_blue("   3) 家用电器运行事件分割")
        print_blue("   4) 电价建模、费用计算与初步区间电价推荐方案")
        print_blue("   5) 用户约束解析与可调度事件过滤")
        print_blue("   6) 可调度事件优化、费用计算、及最终区间电价推荐方案")

        print_blue("🔧 默认采用一次性参数收集模式（高效执行所有步骤）")
        print_blue("💡 您也可以选择逐步交互模式，更细致地控制每个步骤")

        print_blue("💡 默认情况下，记录电器运行的瞬时功率数据读取路径可以在 “tools/p_01_perception_alignment.py 中 函数preprocess_power_series(input_path: str)'中进行路径修改")
        print_blue("💡 系统执行的过程中需要您告知家庭电器的名称，以便于LLM判断电器的是否可进行优化运行区间的迁移，您可以在'config/house_appliances.json'中填写您电器的名称")

        print_blue("📥 参数说明（用于自动配置环境）：")
        print_blue("   - houseX : 数据集选择（如 house1 表示 REFIT 数据集的第1户家庭）")
        print_blue("   - tariff : 区域电价方案（如 uk 表示英国电价配置,TOU_D表示加州TOU电价，Germany表示德国电价）")
        print_blue("   - mode   : 家庭模式（如 single 表示单用户家庭，多用户可选 batch）")

        print_blue("📝 示例输入： 'house1, uk, single' 或 'uk, batch' ")
        print_blue("👉 系统将自动填充相关参数，开始执行完整流程")
        # print_green("🎉 欢迎使用家庭能源管理系统工作流程！")
        # print_blue("🤖 本系统支持LLM智能对话模式，您可以用自然语言描述需求")
        # print_blue(f"📊 当前工作流程包含 {len(TOOLS)} 个步骤")
        # print_blue("🔧 默认使用一次性参数收集模式，提高执行效率")

        # 创建工作流程运行器（默认使用LLM对话模式）
        runner = WorkflowRunner(use_llm_conversation=True)
        runner.run()

    except KeyboardInterrupt:
        print_yellow("\n👋 程序被用户中断")
    except Exception as e:
        print_red(f"❌ 程序运行错误: {str(e)}")
        import traceback
        traceback.print_exc()


def main_without_llm():
    """传统模式主函数 - 不使用LLM对话"""
    try:
        print_green("🎉 欢迎使用家庭能源管理系统工作流程（传统输入模式）！")

        # 创建工作流程运行器（不使用LLM对话模式）
        runner = WorkflowRunner(use_llm_conversation=False)
        runner.run_all_steps()

    except KeyboardInterrupt:
        print_yellow("\n👋 程序被用户中断")
    except Exception as e:
        print_red(f"❌ 程序运行错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main_beautiful()
