import importlib
import json
import os
from typing import Dict, Any, List, Optional
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

# 工具注册表 - 重构后的工具定义
TOOLS = [
    {
        "name": "data_preprocessing_pipeline",
        "description": "Execute complete data preprocessing pipeline: perception alignment, shiftability identification, event segmentation, and event ID assignment. Use this when user provides appliance list and requests data preprocessing.",
        "parameters": {
            "user_input": "A string describing the user's appliances and data processing request",
            "mode": "Processing mode: 'single' for single household, 'batch' for multiple households, 'test' for test mode",
            "house_number": "House number for single household processing (1-21, default: 1)"
        }
    },
    {
        "name": "tariff_cost_analysis",
        "description": "Analyze electricity costs under different tariff schemes and recommend the most cost-effective tariff based on current usage patterns.",
        "parameters": {
            "tariff_type": "Tariff type: 'UK', 'Germany', 'California'",
            "mode": "Processing mode: 'single' for single household, 'batch' for multiple households",
            "house_id": "House ID for single household mode (default: 'house1')"
        }
    },
    {
        "name": "appliance_information_extraction",
        "description": "Extract and standardize appliance information from event segments, handle duplicate appliance names with automatic numbering.",
        "parameters": {
            "tariff_type": "Tariff type: 'UK', 'Germany', 'California'",
            "mode": "Processing mode: 'single' for single household, 'batch' for multiple households",
            "house_id": "House ID for single household mode (default: 'house1')"
        }
    },
    {
        "name": "energy_optimization_integration",
        "description": "Integrate user constraints processing, minimum duration filtering, and TOU optimization. This tool combines p042, p043, and p044 functionalities.",
        "parameters": {
            "mode": "Processing mode: 'single' for single household, 'batch' for multiple households",
            "house_id": "House ID for single household mode (default: 'house1')",
            "user_instruction": "Optional constraint modification instruction. If empty, uses default rules",
            "tariff_config": "Tariff configuration: 'tariff_config', 'TOU_D', 'Germany_Variable'"
        }
    },
    {
        "name": "scheduling_workflow_integration",
        "description": "Execute complete scheduling workflow: appliance space generation, event scheduling, collision resolution, and event splitting (P051~P054).",
        "parameters": {
            "tariff_group": "Tariff group: 'UK', 'TOU_D', 'Germany_Variable'",
            "processing_mode": "Processing mode: 'single' for single household, 'batch' for multiple households",
            "house_id": "House ID for single household mode (default: 'house1')"
        }
    }
]

class MemoryManager:
    """管理用户选择和工具参数的记忆系统"""
    
    def __init__(self):
        self.user_memory = {
            'confirmed_params': {},  # 用户已确认的参数
            'tool_history': [],      # 工具调用历史
            'current_workflow': None,  # 当前工作流程状态
            'user_preferences': {}   # 用户偏好设置
        }
    
    def store_confirmed_param(self, param_name: str, param_value: Any):
        """存储用户确认的参数"""
        self.user_memory['confirmed_params'][param_name] = param_value
        print_blue(f"📝 记忆已保存: {param_name} = {param_value}")
    
    def get_confirmed_param(self, param_name: str) -> Optional[Any]:
        """获取用户之前确认的参数"""
        return self.user_memory['confirmed_params'].get(param_name)
    
    def has_confirmed_param(self, param_name: str) -> bool:
        """检查是否有用户确认的参数"""
        return param_name in self.user_memory['confirmed_params']
    
    def add_tool_history(self, tool_name: str, tool_args: Dict, result: str):
        """添加工具调用历史"""
        self.user_memory['tool_history'].append({
            'tool_name': tool_name,
            'tool_args': tool_args,
            'result': result,
            'timestamp': None  # 可以添加时间戳
        })
    
    def get_tool_history(self) -> List[Dict]:
        """获取工具调用历史"""
        return self.user_memory['tool_history']
    
    def set_workflow_state(self, state: str):
        """设置当前工作流程状态"""
        self.user_memory['current_workflow'] = state
        print_blue(f"🔄 工作流程状态: {state}")
    
    def get_workflow_state(self) -> Optional[str]:
        """获取当前工作流程状态"""
        return self.user_memory['current_workflow']
    
    def clear_memory(self):
        """清除所有记忆"""
        self.user_memory = {
            'confirmed_params': {},
            'tool_history': [],
            'current_workflow': None,
            'user_preferences': {}
        }
        print_yellow("🧹 记忆已清除")
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        summary = "📝 当前记忆状态:\n"
        summary += f"- 已确认参数: {len(self.user_memory['confirmed_params'])} 个\n"
        summary += f"- 工具调用历史: {len(self.user_memory['tool_history'])} 次\n"
        summary += f"- 当前工作流程: {self.user_memory['current_workflow']}\n"
        
        if self.user_memory['confirmed_params']:
            summary += "\n已确认的参数:\n"
            for key, value in self.user_memory['confirmed_params'].items():
                summary += f"  - {key}: {value}\n"
        
        return summary


class ToolParameterManager:
    """工具参数管理器 - 处理参数推断和用户确认"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
    
    def get_param_with_memory(self, param_name: str, param_description: str, 
                            default_value: Any = None, 
                            possible_values: List[Any] = None) -> Any:
        """
        获取参数值，优先使用记忆中的值，否则使用默认值
        
        Args:
            param_name: 参数名
            param_description: 参数描述
            default_value: 默认值
            possible_values: 可能的值列表
            
        Returns:
            参数值
        """
        # 首先检查记忆中是否有这个参数
        if self.memory.has_confirmed_param(param_name):
            value = self.memory.get_confirmed_param(param_name)
            print_green(f"🧠 使用记忆中的参数: {param_name} = {value}")
            return value
        
        # 如果没有记忆，使用默认值（在实际应用中可以询问用户）
        value = default_value
        if value is not None:
            print_blue(f"🔧 使用默认参数: {param_name} = {value}")
            # 存储到记忆中
            self.memory.store_confirmed_param(param_name, value)
        
        return value
    
    def infer_parameters_from_context(self, tool_name: str, required_params: Dict) -> Dict:
        """
        从上下文和记忆中推断参数
        
        Args:
            tool_name: 工具名称
            required_params: 需要的参数字典
            
        Returns:
            推断出的参数字典
        """
        inferred_params = {}
        
        # 根据工具历史推断一些通用参数
        tool_history = self.memory.get_tool_history()
        
        for param_name, param_info in required_params.items():
            # 从记忆中获取
            if self.memory.has_confirmed_param(param_name):
                inferred_params[param_name] = self.memory.get_confirmed_param(param_name)
                continue
            
            # 根据工具历史推断
            if param_name == "house_id" and tool_history:
                # 查找最近使用的 house_id
                for history_item in reversed(tool_history):
                    if "house_id" in history_item['tool_args']:
                        inferred_params[param_name] = history_item['tool_args']['house_id']
                        print_blue(f"🔍 从历史推断参数: {param_name} = {inferred_params[param_name]}")
                        break
            
            # 如果还没有推断出来，使用默认值
            if param_name not in inferred_params:
                if param_name == "mode":
                    inferred_params[param_name] = "single"  # 默认单个处理
                elif param_name == "house_id":
                    inferred_params[param_name] = "house1"  # 默认house1
                elif param_name == "tariff_type":
                    inferred_params[param_name] = "UK"  # 默认UK
                elif param_name == "house_number":
                    inferred_params[param_name] = 1  # 默认1
                elif param_name == "processing_mode":
                    inferred_params[param_name] = "single"  # 默认单个处理
                elif param_name == "tariff_group":
                    inferred_params[param_name] = "UK"  # 默认UK
                elif param_name == "tariff_config":
                    inferred_params[param_name] = "tariff_config"  # 默认配置
        
        return inferred_params


class Assistant:
    """重构后的智能助手 - 集成记忆管理和工具调用"""
    
    def __init__(self):
        self.messages = []
        self.memory_manager = MemoryManager()
        self.param_manager = ToolParameterManager(self.memory_manager)
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self):
        """初始化系统提示"""
        system_prompt = self._build_system_prompt()
        self.messages = [{"role": "system", "content": system_prompt}]
    
    def _get_tools_prompt(self):
        """获取工具提示信息"""
        return (
            "Available tools:\n" +
            "\n".join(
                f"- {tool['name']}: {tool['description']} (parameters: {', '.join(tool['parameters'].keys())})"
                for tool in TOOLS
            )
        )
    
    def _build_system_prompt(self):
        """构建系统提示"""
        return (
            "You are a smart home energy management assistant (智能家居能源管理助手). "
            "You help users manage their home appliances and optimize energy usage through intelligent scheduling. "
            "You have memory capabilities and can remember user preferences and previous choices.\n\n"
            
            "You have access to several powerful tools for energy analysis:\n"
            "1. data_preprocessing_pipeline - Complete data preprocessing and event identification\n"
            "2. tariff_cost_analysis - Electricity cost analysis under different tariff schemes\n"
            "3. appliance_information_extraction - Extract and standardize appliance information\n"
            "4. energy_optimization_integration - User constraints and TOU optimization\n"
            "5. scheduling_workflow_integration - Complete intelligent scheduling workflow\n\n"
            
            "Your memory system:\n"
            "- Remembers user's confirmed parameters (house_id, tariff_type, mode, etc.)\n"
            "- Tracks tool usage history\n"
            "- Only asks for new parameters that haven't been confirmed before\n"
            "- Can infer parameters from context and previous choices\n\n"
            
            "Your job is to understand the user's goal and return a tool call in JSON format:\n"
            "{\"intent\": ..., \"tool\": {\"name\": ..., \"args\": {...}}}\n\n"
            
            "Available tools:\n" +
            self._get_tools_prompt() +
            "\n\n"
            "Always prioritize using memory to avoid asking users for the same information twice. "
            "If you need clarification or don't have enough information, ask the user for details."
        )
    
    def chat(self, user_input):
        """处理用户输入并返回助手响应"""
        self.messages.append({"role": "user", "content": user_input})
        
        # 将记忆信息添加到上下文中
        memory_context = f"\n\nCurrent memory state: {self.memory_manager.get_memory_summary()}"
        enhanced_messages = self.messages.copy()
        enhanced_messages[-1]["content"] += memory_context
        
        llm_response = chat_with_api(enhanced_messages)
        
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
            
            print_green(f"🔧 正在处理: {intent}")
            print_green(f"📋 调用工具: {tool_name}")
            
            # 使用记忆管理器处理工具调用
            return self._execute_tool_with_memory(tool_name, tool_args, intent)
            
        except json.JSONDecodeError:
            return content
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg
    
    def _execute_tool_with_memory(self, tool_name: str, tool_args: Dict, intent: str) -> str:
        """使用记忆管理器执行工具"""
        try:
            # 导入所需的工具模块
            import test_func_2_int
            import test_func_3_int  
            import test_func_4_int
            import test_func_5_int
            import test_func_6_int
            
            result = None
            
            # 工具1: 数据预处理管道
            if tool_name == "data_preprocessing_pipeline":
                # 使用记忆管理器获取参数
                user_input = tool_args.get("user_input", "")
                mode = self.param_manager.get_param_with_memory(
                    "mode", "处理模式", "single", ["single", "batch", "test"]
                )
                house_number = self.param_manager.get_param_with_memory(
                    "house_number", "房屋编号", 1
                )
                
                print(f"🏠 执行数据预处理管道 - 模式: {mode}, 房屋: {house_number}")
                
                if mode == "single":
                    result = test_func_2_int.process_single_house_complete(house_number)
                elif mode == "batch":
                    result = test_func_2_int.batch_process_complete_pipeline()
                elif mode == "test":
                    result = test_func_2_int.main(5, house_number)  # 测试模式
                
                self.memory_manager.set_workflow_state("data_preprocessed")
            
            # 工具2: 电价成本分析
            elif tool_name == "tariff_cost_analysis":
                tariff_type = self.param_manager.get_param_with_memory(
                    "tariff_type", "电价类型", "UK", ["UK", "Germany", "California"]
                )
                mode = self.param_manager.get_param_with_memory(
                    "mode", "处理模式", "single", ["single", "batch"]
                )
                house_id = self.param_manager.get_param_with_memory(
                    "house_id", "房屋ID", "house1"
                )
                
                print(f"💰 执行电价成本分析 - 类型: {tariff_type}, 模式: {mode}")
                
                if mode == "single":
                    success, message = test_func_3_int.single_house_tariff_analysis(
                        house_id=house_id, tariff_type=tariff_type
                    )
                    result = {"success": success, "message": message}
                else:
                    # 加载房屋配置并执行批量分析
                    house_appliances = test_func_3_int.load_house_appliances_config()
                    result = test_func_3_int.batch_tariff_analysis(
                        house_data_dict=house_appliances, tariff_type=tariff_type
                    )
                
                self.memory_manager.set_workflow_state("tariff_analyzed")
            
            # 工具3: 电器信息提取
            elif tool_name == "appliance_information_extraction":
                tariff_type = self.param_manager.get_param_with_memory(
                    "tariff_type", "电价类型", "UK", ["UK", "Germany", "California"]
                )
                mode = self.param_manager.get_param_with_memory(
                    "mode", "处理模式", "single", ["single", "batch"]
                )
                house_id = self.param_manager.get_param_with_memory(
                    "house_id", "房屋ID", "house1"
                )
                
                print(f"🔧 执行电器信息提取 - 类型: {tariff_type}, 模式: {mode}")
                
                if mode == "single":
                    result = test_func_4_int.single_house_appliance_analysis(
                        house_id=house_id, tariff_type=tariff_type
                    )
                else:
                    house_appliances = test_func_4_int.load_house_appliances_config()
                    result = test_func_4_int.batch_get_appliance_lists(
                        house_data_dict=house_appliances, tariff_type=tariff_type
                    )
                
                self.memory_manager.set_workflow_state("appliances_extracted")
            
            # 工具4: 能源优化集成
            elif tool_name == "energy_optimization_integration":
                mode = self.param_manager.get_param_with_memory(
                    "mode", "处理模式", "single", ["single", "batch"]
                )
                house_id = self.param_manager.get_param_with_memory(
                    "house_id", "房屋ID", "house1"
                )
                user_instruction = tool_args.get("user_instruction", None)
                tariff_config = self.param_manager.get_param_with_memory(
                    "tariff_config", "电价配置", "tariff_config", 
                    ["tariff_config", "TOU_D", "Germany_Variable"]
                )
                
                print(f"⚡ 执行能源优化集成 - 模式: {mode}, 配置: {tariff_config}")
                
                integrator = test_func_5_int.EnergyOptimizationIntegrator()
                
                if mode == "single":
                    result = integrator.process_single_user(
                        house_id=house_id,
                        user_instruction=user_instruction,
                        tariff_config=tariff_config
                    )
                else:
                    house_list = integrator.get_all_available_houses()
                    result = integrator.process_batch_users(
                        house_list=house_list,
                        tariff_config=tariff_config,
                        interactive_mode=False
                    )
                
                self.memory_manager.set_workflow_state("energy_optimized")
            
            # 工具5: 调度工作流程集成
            elif tool_name == "scheduling_workflow_integration":
                tariff_group = self.param_manager.get_param_with_memory(
                    "tariff_group", "电价组", "UK", ["UK", "TOU_D", "Germany_Variable"]
                )
                processing_mode = self.param_manager.get_param_with_memory(
                    "processing_mode", "处理模式", "single", ["single", "batch"]
                )
                house_id = self.param_manager.get_param_with_memory(
                    "house_id", "房屋ID", "house1"
                )
                
                print(f"📅 执行调度工作流程集成 - 电价组: {tariff_group}, 模式: {processing_mode}")
                
                workflow = test_func_6_int.IntegratedWorkflow()
                success = workflow.run_complete_workflow(
                    interactive=False,
                    tariff_group=tariff_group,
                    processing_mode=processing_mode,
                    house_id=house_id
                )
                
                result = {
                    "success": success,
                    "tariff_group": tariff_group,
                    "processing_mode": processing_mode,
                    "house_id": house_id
                }
                
                self.memory_manager.set_workflow_state("scheduling_completed")
            
            else:
                return f"Unknown tool: {tool_name}"
            
            # 将工具调用添加到历史记录
            result_str = json.dumps(result, indent=2, ensure_ascii=False) if result else "Tool executed successfully"
            self.memory_manager.add_tool_history(tool_name, tool_args, result_str)
            
            # 生成响应
            response = f"✅ {intent}\n\n📊 结果:\n{result_str}"
            self.messages.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            error_msg = f"❌ 工具执行错误 ({tool_name}): {str(e)}"
            print_red(error_msg)
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg
    
    def reset_conversation(self):
        """重置对话"""
        self._initialize_system_prompt()
        self.memory_manager.clear_memory()
    
    def get_conversation_history(self):
        """获取对话历史"""
        return self.messages.copy()
    
    def get_memory_status(self):
        """获取记忆状态"""
        return self.memory_manager.get_memory_summary()


if __name__ == "__main__":
    assistant = Assistant()

    print("=== 🏠 智能家电调度助手 V2 ===")
    print("🎯 基于记忆管理的能源优化系统")
    print("📊 完整流程：数据预处理 → 成本分析 → 信息提取 → 能源优化 → 调度集成")
    print("=" * 80)

    # 演示流程 1: 数据预处理
    print("\n🔧 步骤 1: 数据预处理管道")
    print("-" * 50)
    query = """
Hi, I have several appliances at home:
Fridge, Chest Freezer, Upright Freezer, Tumble Dryer, Washing Machine, Dishwasher, Computer Site, Television Site, Electric Heater.
Please process the raw power data and identify appliance events.
"""
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 演示流程 2: 电价成本分析
    print("\n💰 步骤 2: 电价成本分析")
    print("-" * 50)
    query = "Please analyze the electricity costs under different tariff schemes and recommend the best option."
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 演示流程 3: 电器信息提取
    print("\n🔧 步骤 3: 电器信息提取")
    print("-" * 50)
    query = "Extract and standardize the appliance information from the processed data."
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 演示流程 4: 能源优化集成
    print("\n⚡ 步骤 4: 能源优化集成")
    print("-" * 50)
    query = "Apply energy optimization with user constraints and TOU filtering."
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 演示流程 5: 调度工作流程集成
    print("\n📅 步骤 5: 调度工作流程集成")
    print("-" * 50)
    query = "Execute the complete scheduling workflow for appliance optimization."
    print_green("User: " + query)
    print_yellow("AI response: " + assistant.chat(query))
    print()

    # 显示记忆状态
    print("\n📝 最终记忆状态:")
    print("-" * 50)
    print(assistant.get_memory_status())

    print("\n" + "=" * 80)
    print("🎉 智能家电调度分析完成！")
    print("🧠 系统已学习并记住了您的偏好设置")
    print("📊 所有工具执行历史已保存在记忆中")
    print("=" * 80)
