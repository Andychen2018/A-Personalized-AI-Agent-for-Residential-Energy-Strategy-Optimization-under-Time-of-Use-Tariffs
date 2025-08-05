import importlib
import json
from llm import chat_with_api

def print_red(text):
    """Print debug text in red color"""
    print(f"\033[91m{text}\033[0m")

def print_green(text):
    """Print debug text in green color"""
    print(f"\033[92m{text}\033[0m")

def print_blue(text):
    """Print debug text in blue color"""
    print(f"\033[94m{text}\033[0m")

def print_yellow(text):
    """Print debug text in yellow color"""
    print(f"\033[93m{text}\033[0m")

# Tool registry
TOOLS = [

    {
        "name": "preprocess",
        "description": "Process raw power data, align to 1-minute granularity, remove anomalies, identify appliance events, and analyze appliance shiftability. Use this when user provides appliance list and requests data preprocessing.",
        "parameters": {
            "user_input": "A string describing the user's appliances and data processing request."
        },
      
    },
    {
        "name": "simulate_tariff_and_recommend",
        "description": "Analyze electricity cost under different tariff schemes BEFORE event scheduling optimization and recommend the most cost-effective tariff based on current usage patterns.",
        "parameters": {
            "user_input": "Optional appliance description or comment (can be empty)."
        },

    },
    {
        "name": "appliance_event_reason",
        "description": "Analyze appliance scheduling rules and explain the default forbidden time intervals.",
        "parameters": {"user_input": "Optional user message (can be ignored)"},
        
    },
    {
    "name": "filter_events_by_constraints_and_tariff",
    "description": "Filter appliance events based on LLM-revised constraints and pricing schemes.",
    "parameters": {
        "user_instruction": "Optional constraint modification instruction. If empty, uses default rules.",
        "test_mode": "Boolean: False for main mode (Economy_7 & Economy_10), True for test mode (TOU_D & Germany_Variable). Default: False."
                },
    },
    {
    "name": "peak_valley_tariff_appliance_scheduling_analyzer_tool",
    "description": "Analyze and visualize appliance scheduling under peak-valley tariffs.",
    "parameters": {
        "user_instruction": "Optional user instruction for scheduling analysis (can be empty)."
                }
    },
    {
    "name": "precise_cost_analysis_tool",
    "description": "Run complete intelligent scheduling optimization and calculate cost savings AFTER event rescheduling (Main mode: Economy_7 & Economy_10). Shows how much money can be saved through smart scheduling.",
    "parameters": {
        "user_instruction": "Optional user instruction for precise cost analysis (can be empty)."
                }
    },
    {
    "name": "test_mode_analysis_tool",
    "description": "Run intelligent scheduling optimization for experimental tariffs AFTER event rescheduling (Test mode: TOU_D & Germany_Variable). Shows potential savings through smart scheduling.",
    "parameters": {
        "user_instruction": "Optional user instruction for test mode analysis (can be empty)."
                }
    },
    {
    "name": "activate_test_mode_tariffs",
    "description": "Activate test mode tariff processing (TOU_D & Germany_Variable) for event filtering and constraint analysis. This prepares data for subsequent test mode cost analysis.",
    "parameters": {
        "user_instruction": "Optional user instruction for test mode constraint analysis (can be empty)."
                }
    },
    {
    "name": "select_analysis_mode",
    "description": "Help user choose between main mode (Economy_7 & Economy_10) or test mode (TOU_D & Germany_Variable) analysis.",
    "parameters": {
        "user_preference": "User's preference or question about which mode to use."
                }
    },
    {
    "name": "final_cost_summary_and_recommendation",
    "description": "Generate final cost comparison table and tariff recommendation based on processed data. Use this AFTER running data processing tools (2-6).",
    "parameters": {
        "test_mode": "Boolean: False for main mode (Economy_7 & Economy_10), True for test mode (TOU_D & Germany_Variable)."
                }
    }

    ]



class Assistant:
    def __init__(self):
        self.messages = []
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self):
        system_prompt = self._build_system_prompt()
        self.messages = [{"role": "system", "content": system_prompt}]
    
    def _get_tools_prompt(self):
        return (
            "Available tools:\n" +
            "\n".join(
                f"- {tool['name']}: {tool['description']} (parameters: {', '.join(tool['parameters'].keys())})"
                for tool in TOOLS
            )
        )

    def _force_regenerate_filter_files(self):
        """强制重新生成过滤相关的中间文件"""
        import os

        # 删除过滤相关的中间文件，强制重新生成
        filter_files = [
            "./output/04_user_constraints/shiftable_event_filtered_by_duration.csv",
            "./output/04_user_constraints/shiftable_event_masked_Economy_7.csv",
            "./output/04_user_constraints/shiftable_event_masked_Economy_10.csv",
            "./output/04_user_constraints/TOU_D/shiftable_event_masked_TOU_D.csv",
            "./output/04_user_constraints/Germany_Variable/shiftable_event_masked_Germany_Variable.csv"
        ]

        for file_path in filter_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  删除旧文件: {os.path.basename(file_path)}")

    def _force_regenerate_scheduling_files(self):
        """强制重新生成调度相关的中间文件"""
        import os

        # 删除调度相关的中间文件，强制重新生成
        scheduling_files = [
            "./output/05_scheduling/reschedulable_events_Economy_7.csv",
            "./output/05_scheduling/reschedulable_events_Economy_10.csv",
            "./output/05_scheduling/appliance_global_spaces_Economy_7.json",
            "./output/05_scheduling/appliance_global_spaces_Economy_10.json",
            "./output/05_scheduling/scheduled_events_Economy_7.csv",
            "./output/05_scheduling/scheduled_events_Economy_10.csv",
            "./output/05_scheduling/collision_resolved_Economy_7.csv",
            "./output/05_scheduling/collision_resolved_Economy_10.csv",
            "./output/05_scheduling/cost_analysis_Economy_7.json",
            "./output/05_scheduling/cost_analysis_Economy_10.json",
            "./output/05_scheduling/events_statistics_table_main_mode.csv"
        ]

        for file_path in scheduling_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  删除旧文件: {os.path.basename(file_path)}")

    def _force_regenerate_test_mode_files(self):
        """强制重新生成测试模式相关的中间文件"""
        import os

        # 删除测试模式相关的中间文件，强制重新生成
        test_mode_files = [
            "./output/04_user_constraints/TOU_D/shiftable_event_masked_TOU_D.csv",
            "./output/04_user_constraints/Germany_Variable/shiftable_event_masked_Germany_Variable.csv",
            "./output/05_scheduling/reschedulable_events_TOU_D.csv",
            "./output/05_scheduling/reschedulable_events_Germany_Variable.csv",
            "./output/05_scheduling/appliance_global_spaces_TOU_D.json",
            "./output/05_scheduling/appliance_global_spaces_Germany_Variable.json",
            "./output/05_scheduling/scheduled_events_TOU_D.csv",
            "./output/05_scheduling/scheduled_events_Germany_Variable.csv",
            "./output/05_scheduling/collision_resolved_TOU_D.csv",
            "./output/05_scheduling/collision_resolved_Germany_Variable.csv",
            "./output/05_scheduling/cost_analysis_TOU_D.json",
            "./output/05_scheduling/cost_analysis_Germany_Variable.json",
            "./output/05_scheduling/events_statistics_table_test_mode.csv"
        ]

        for file_path in test_mode_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  删除旧文件: {os.path.basename(file_path)}")

    def _force_regenerate_all_intermediate_files(self):
        """强制重新生成所有中间文件"""
        print("🔄 强制重新生成所有中间文件...")
        self._force_regenerate_filter_files()
        self._force_regenerate_scheduling_files()
        self._force_regenerate_test_mode_files()
        print("✅ 中间文件清理完成，将重新生成")

    def _build_system_prompt(self):
        return (
        "You are a smart home butler assistant (家庭管家助手). "
        "You help users manage their home appliances and optimize energy usage through intelligent scheduling. "
        "You are friendly, helpful, and knowledgeable about home appliance management.\n\n"

        "You have access to several callable tools. Your goal is to assist users by selecting and calling these tools appropriately. "
        "You can reason step-by-step and break down complex tasks into multiple tool calls if needed.\n\n"

        "The user may proceed step-by-step, such as:\n"
        "- \"First help me recognize appliances\"\n"
        "- Then: \"Now analyze tariffs\" (BEFORE optimization - to recommend best tariff based on current usage)\n"
        "- Then: \"What are the default rules\"\n"
        "- Then: \"Please help me to analyze all appliances constrains\"\n"
        "- Then: \"Now I want to filter events by constraints and tariff\"\n"
        "- Then: \"Now I want to analyze and visualize appliance scheduling under peak-valley tariffs\"\n"
        "- Then: \"I want to choose between main mode and test mode analysis\" (STAGE 1: Data processing)\n"
        "- Finally: \"Generate final cost summary\" or \"Show me the final comparison table\" (STAGE 2: Final summary)\n"
        "- Or: \"Run the complete analysis in main mode\" followed by \"Show final results\"\n"

        "- And so on.\n\n"

        "IMPORTANT: The system follows a two-stage workflow:\n"
        "STAGE 1 - Data Processing (Tools 2-6): Generate intermediate results\n"
        "- Main Mode (precise_cost_analysis_tool): Process Economy_7 & Economy_10 data\n"
        "- Test Mode (test_mode_analysis_tool): Process TOU_D & Germany_Variable data\n"
        "- Mode Selection (select_analysis_mode): Helps users choose the appropriate mode\n"
        "STAGE 2 - Final Summary (Tool 1): Generate comparison table and recommendation\n"
        "- final_cost_summary_and_recommendation: Create final cost comparison and tariff recommendation\n\n"

        "Your job is to understand the user's current goal or subgoal and return a callable tool signature "
        "in the following strict JSON format:\n"
        "{\"intent\": ..., \"tool\": {\"name\": ..., \"args\": {...}}}\n\n"

        "Available tools:\n" +
        self._get_tools_prompt() +
        "\n\n"
        "If you don’t have enough information to call a tool, ask the user for more details. "
        "Otherwise, do not explain your reasoning—just output the JSON for tool invocation. "
        "Only respond in natural language when asking clarification or concluding the conversation."
    )


    def chat(self, user_input):
        """Process user input and return assistant response"""
        self.messages.append({"role": "user", "content": user_input})
        llm_response = chat_with_api(self.messages)

        if not llm_response or "choices" not in llm_response:
            return "Sorry, I'm having trouble connecting right now. Please try again."

        content = llm_response["choices"][0]["message"]["content"]
        self.messages.append({"role": "assistant", "content": content})

        try:
            result = json.loads(content)
            intent = result.get("intent")
            tool_info = result.get("tool", {})
            tool_name = tool_info.get("name")
            tool_args = tool_info.get("args", {})

            # 可选的调试信息输出（可以通过环境变量控制）
            import os
            if os.getenv('AGENT_DEBUG', 'false').lower() == 'true':
                print_red(f"[DEBUG] intent: {intent}")
                print_red(f"[DEBUG] tool name: {tool_name}")
                print_red(f"[DEBUG] tool args: {tool_args}")
            else:
                # 用户友好的处理信息
                print_green(f"🔧 正在处理: {intent}")
                print_green(f"📋 调用工具: {tool_name}")


            import test_func_2_int
            import test_func_3_int
            import test_func_4_int
            import test_func_5_int
            import test_func_6_int

            # ✅ Tool 1: preprocess
            if tool_name == "preprocess" and "user_input" in tool_args:
                try:
                    tool_result = test_func_2_int.preprocess(tool_args["user_input"])
                    tool_response = f"Based on my analysis: {tool_result}"
                    self.messages.append({"role": "assistant", "content": tool_response})
                    return tool_response
                except Exception as e:
                    error_msg = f"❌ Error in preprocess: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 3: simulate_tariff_and_recommend (事件迁移前的费用对比)
            elif tool_name == "simulate_tariff_and_recommend":
                try:
                    # 安全获取 user_input（可以为空）
                    user_input_param = tool_args.get("user_input", None)

                    print("💰 分析当前用电习惯下的各电价方案费用（事件迁移前）")
                    print("🎯 目标：基于现有用电模式推荐最省钱的电价方案")

                    tool_result = test_func_3_int.simulate_tariff_and_recommend(user_input_param)
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in simulate_tariff_and_recommend: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
            # ✅ Tool 4: appliance_event_reason
            elif tool_name == "appliance_event_reason":
                try:
                    tool_result = test_func_4_int.appliance_event_reason()
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in appliance_event_reason: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
            
            # ✅ Tool 5: filter_events_by_constraints_and_tariff
            elif tool_name == "filter_events_by_constraints_and_tariff":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)
                    test_mode = tool_args.get("test_mode", False)  # 默认主流程模式

                    # 强制重新生成所有中间文件
                    print("🔄 强制重新生成所有过滤文件...")
                    self._force_regenerate_filter_files()

                    tool_result = test_func_5_int.filter_events_by_constraints_and_tariff(
                        user_input_param, test_mode=test_mode
                    )
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in filter_events_by_constraints_and_tariff: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
            # ✅ Tool 6: peak_valley_tariff_appliance_scheduling_analyzer (使用精确费用分析)
            elif tool_name == "peak_valley_tariff_appliance_scheduling_analyzer_tool":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)

                    # 使用更完整的精确费用分析工具
                    tool_result = test_func_6_int.precise_cost_analysis_tool(user_input_param)
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in peak_valley_tariff_appliance_scheduling_analyzer_tool: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 7: precise_cost_analysis_tool (主流程模式 - 事件迁移后费用分析)
            elif tool_name == "precise_cost_analysis_tool":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)

                    print("🏠 启动主流程模式数据处理 (Economy_7 & Economy_10)")
                    print("🔧 执行智能调度优化，生成中间结果文件")
                    print("💡 阶段1：数据处理和中间结果生成")

                    # 强制重新生成所有中间文件
                    print("🔄 强制重新生成所有调度相关文件...")
                    self._force_regenerate_scheduling_files()

                    tool_result = test_func_6_int.precise_cost_analysis_tool(user_input_param)

                    # 添加下一步指导
                    next_step_msg = """
📋 数据处理完成！中间结果已生成。

🎯 下一步：使用最终汇总工具查看费用对比和推荐
请告诉我："生成最终汇总"或"显示费用对比表格"

💡 或者您可以直接说："我想看最终的费用对比和推荐"
                    """

                    combined_response = f"{json.dumps(tool_result, indent=2, ensure_ascii=False)}\n{next_step_msg}"
                    self.messages.append({"role": "assistant", "content": combined_response})
                    return combined_response
                except Exception as e:
                    error_msg = f"❌ Error in precise_cost_analysis_tool: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 8: test_mode_analysis_tool (测试模式 - 事件迁移后费用分析)
            elif tool_name == "test_mode_analysis_tool":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)

                    print("🧪 启动测试模式分析 (TOU_D & Germany_Variable)")
                    print("🔧 执行智能调度优化，计算事件迁移后的费用节省")
                    print("💡 目标：显示通过智能调度在实验电价下可以节省多少电费")

                    # 强制重新生成测试模式相关文件
                    print("🔄 强制重新生成测试模式相关文件...")
                    self._force_regenerate_test_mode_files()

                    # 导入测试模式运行器
                    import test_mode_runner
                    tool_result = test_mode_runner.run_test_mode_analysis()
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in test_mode_analysis_tool: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 9: activate_test_mode_tariffs (激活测试模式电价处理)
            elif tool_name == "activate_test_mode_tariffs":
                try:
                    # 安全获取 user_instruction（可以为空）
                    user_input_param = tool_args.get("user_instruction", None)

                    print("🧪 激活测试模式电价处理 (TOU_D & Germany_Variable)")
                    print("🔧 为测试模式准备事件过滤和约束分析数据")

                    # 调用测试模式激活函数
                    import test_func_5_int
                    tool_result = test_func_5_int.activate_test_mode_tariffs(user_input_param)
                    response = json.dumps(tool_result, indent=2, ensure_ascii=False)
                    self.messages.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_msg = f"❌ Error in activate_test_mode_tariffs: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 10: select_analysis_mode (模式选择助手)
            elif tool_name == "select_analysis_mode":
                try:
                    user_preference = tool_args.get("user_preference", "").lower()

                    # 基于用户偏好提供智能建议
                    if any(keyword in user_preference for keyword in ["economy", "daily", "home", "家庭", "日常"]):
                        recommendation = "🎯 基于您的需求，推荐使用主流程模式 (Economy_7 & Economy_10)"
                    elif any(keyword in user_preference for keyword in ["test", "research", "tou", "germany", "实验", "研究"]):
                        recommendation = "🎯 基于您的需求，推荐使用测试模式 (TOU_D & Germany_Variable)"
                    else:
                        recommendation = "🎯 请根据您的具体需求选择合适的模式"

                    mode_guide = f"""
🎯 智能调度分析模式选择指南

{recommendation}

⚠️ 重要说明：
这些工具用于事件迁移后的费用分析，显示智能调度的节省效果。
如果您还没有进行电价对比，请先使用 simulate_tariff_and_recommend 工具。

📊 主流程模式 (推荐日常使用)
   - 分析电价方案: Economy_7 & Economy_10
   - 适用场景: 日常家庭电价优化分析
   - 工具调用: precise_cost_analysis_tool
   - 功能: 执行智能调度，显示通过事件迁移可以节省多少电费

🧪 测试模式 (实验研究使用)
   - 分析电价方案: TOU_D & Germany_Variable
   - 适用场景: 学术研究、国际电价对比
   - 工具调用: test_mode_analysis_tool
   - 功能: 执行智能调度，显示在实验电价下的节省效果

💡 完整分析流程建议:
   1. 首先使用 simulate_tariff_and_recommend (了解当前用电习惯下最省钱的电价)
   2. 然后选择主流程模式或测试模式 (了解智能调度可以节省多少)

请告诉我您想要运行哪种模式，我会为您启动相应的分析。
                    """

                    self.messages.append({"role": "assistant", "content": mode_guide})
                    return mode_guide
                except Exception as e:
                    error_msg = f"❌ Error in select_analysis_mode: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            # ✅ Tool 10: final_cost_summary_and_recommendation (最终汇总和推荐)
            elif tool_name == "final_cost_summary_and_recommendation":
                try:
                    test_mode = tool_args.get("test_mode", False)

                    if test_mode:
                        print("🧪 生成测试模式最终汇总 (TOU_D & Germany_Variable)")
                    else:
                        print("🏠 生成主流程模式最终汇总 (Economy_7 & Economy_10)")

                    print("📊 读取中间结果文件，生成最终费用对比表格和推荐...")

                    # 调用最终汇总工具
                    from test_func_1_int import agent_tariff_cost_summary_and_recommendation
                    agent_tariff_cost_summary_and_recommendation(test_mode=test_mode)

                    summary_msg = f"""
✅ 最终费用汇总和推荐已生成完成！

📊 基于处理后的数据，我已经为您生成了：
- 详细的费用对比表格
- 各电价方案的节省分析
- 智能调度优化效果
- 最终的电价方案推荐

💡 上述表格显示了在智能调度优化后，各电价方案的实际费用和节省情况。
这是基于您的实际用电数据和智能调度算法得出的精确分析结果。
                    """

                    self.messages.append({"role": "assistant", "content": summary_msg})
                    return summary_msg

                except Exception as e:
                    error_msg = f"❌ Error in final_cost_summary_and_recommendation: {str(e)}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return error_msg

            else:
                return content

        except json.JSONDecodeError:
            return content
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg

    def reset_conversation(self):
        self._initialize_system_prompt()

    def get_conversation_history(self):
        return self.messages.copy()

if __name__ == "__main__":
    assistant = Assistant()

    print("=== 🏠 智能家电调度助手 ===")
    print("🎯 基于非侵入式用电数据的智能家电调度系统")
    print("📊 4步流程：感知 → 理解 → 推理 → 优化")
    print("="*80)

    # 步骤1: 问候和介绍
    print("\n🤖 步骤1: 系统介绍")
    print("-" * 40)
    query = "hello, who are you?"
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 步骤2: 🧩 感知（Perception）- 数据预处理和电器识别
    print("\n🧩 步骤2: 感知阶段 - 数据预处理和电器识别")
    print("-" * 60)
    query = """
Hi, I have several appliances at home:
Fridge, Chest Freezer, Upright Freezer, Tumble Dryer, Washing Machine, Dishwasher, Computer Site, Television Site, Electric Heater.

Note: Entry 0 is the aggregated total power of the household and not an actual appliance.
These devices correspond to Appliance1 through Appliance9 in the dataset and will be used for energy analysis.

Important:
1. All appliance names that differ only by a numeric suffix or parenthesis
(e.g., "Electric Heater (2)", "Electric Heater(3)") should be treated as the same appliance type
as the base name (e.g., "Electric Heater") when determining shiftability.
2. If an appliance name contains a brand or location descriptor (e.g., "MJY Computer", "Freezer (Utility Room)"),
use only the core appliance type (e.g., "Computer", "Freezer") to determine shiftability.

Please process the raw power data, align it to 1-minute granularity, remove anomalies, and identify appliance events.
"""

    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 步骤3: 初步电价分析和推荐
    print("\n💰 步骤3: 初步电价分析和推荐")
    print("-" * 50)
    query = "please analyze my appliances and tell me which tariffs is your recommand"
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 步骤4: 🧠 理解（Understanding）- 用户约束解析
    print("\n🧠 步骤4: 理解阶段 - 用户约束解析")
    print("-" * 50)
    query = "Please help me to analyze all appliances constrains"
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 步骤5: 🧮 推理（Reasoning）- 事件过滤和调度空间构建
    print("\n🧮 步骤5: 推理阶段 - 事件过滤和调度空间构建")
    print("-" * 60)
    query = json.dumps({
        "intent": "Filter appliance events based on constraints and chosen tariff",
        "tool": {
            "name": "filter_events_by_constraints_and_tariff",
            "args": {
                "user_instruction": (
                    "Set forbidden operating time for Washing Machine, Tumble Dryer, and Dishwasher as 23:30 to 06:00 (next day);\n"
                    "Ensure each event completes by 14:00 the next day (i.e., 38:00);\n"
                    "Ignore events shorter than 5 minutes;\n"
                    "Keep all other appliance rules as default."
                ),
                "test_mode": False
            }
        }
    })

    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 步骤6: 🔧 优化（Optimization）- 智能调度和费用计算
    print("\n🔧 步骤6: 优化阶段 - 智能调度和费用计算")
    print("-" * 60)
    query = json.dumps({
        "intent": "Analyze and visualize appliance scheduling under peak-valley tariffs",
        "tool": {
            "name": "peak_valley_tariff_appliance_scheduling_analyzer_tool",
            "args": {
                "user_instruction": (
                    "Analyze all appliances under peak-valley tariffs and visualize the scheduling."
                )
            }
        }
    })
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()



    # 步骤7: 📊 分析完成
    print("\n" + "="*80)
    print("🎉 智能家电调度分析完成！")
    print("📊 您已获得基于AI分析的电价方案推荐")
    print("💡 系统已为您的家电使用模式找到最优的调度策略")
    print("="*80)
