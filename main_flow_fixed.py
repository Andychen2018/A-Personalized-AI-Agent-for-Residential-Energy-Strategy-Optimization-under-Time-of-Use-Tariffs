#!/usr/bin/env python3
"""
完善版main_flow.py - 基于参数记忆的智能家居能源管理助手
主要功能：
1. 管理用户确认的参数，避免重复询问
2. 智能工作流程管理和进度跟踪
3. LLM集成的自然语言交互
4. 完整的工具调用和历史记录
"""

import importlib
import json
import os
import time
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

# 工具注册表 - 完善的工具定义
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
    """完善的记忆管理系统"""
    
    def __init__(self):
        self.user_memory = {
            'confirmed_params': {},  # 用户已确认的参数
            'tool_history': [],      # 工具调用历史
            'workflow_state': None   # 当前工作流程状态
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
            'timestamp': time.time(),
            'workflow_state': self.user_memory['workflow_state']
        })
        print_blue(f"📝 工具历史已记录: {tool_name}")
    
    def get_tool_history(self) -> List[Dict]:
        """获取工具调用历史"""
        return self.user_memory['tool_history']
    
    def set_workflow_state(self, state: str):
        """设置当前工作流程状态"""
        self.user_memory['workflow_state'] = state
        print_blue(f"🔄 工作流程状态: {state}")
    
    def get_workflow_state(self) -> Optional[str]:
        """获取当前工作流程状态"""
        return self.user_memory['workflow_state']
    
    def get_workflow_progress(self) -> Dict[str, bool]:
        """获取工作流程进度"""
        workflow_steps = {
            'data_preprocessing': ['data_preprocessing_pipeline'],
            'tariff_analysis': ['tariff_cost_analysis'],
            'appliance_extraction': ['appliance_information_extraction'],
            'energy_optimization': ['energy_optimization_integration'],
            'scheduling': ['scheduling_workflow_integration']
        }
        
        progress = {}
        for step_name, required_tools in workflow_steps.items():
            completed = any(
                h['tool_name'] in required_tools 
                for h in self.user_memory['tool_history']
            )
            progress[step_name] = completed
            
        return progress
    
    def get_next_recommended_action(self) -> Optional[str]:
        """基于当前状态推荐下一步操作"""
        progress = self.get_workflow_progress()
        
        # 推荐工作流程顺序
        workflow_order = [
            ('data_preprocessing', 'data_preprocessing_pipeline', '建议先进行数据预处理'),
            ('tariff_analysis', 'tariff_cost_analysis', '建议分析电价方案'),
            ('appliance_extraction', 'appliance_information_extraction', '建议提取电器信息'),
            ('energy_optimization', 'energy_optimization_integration', '建议进行能源优化'),
            ('scheduling', 'scheduling_workflow_integration', '建议执行调度工作流程')
        ]
        
        for step_name, tool_name, description in workflow_order:
            if not progress[step_name]:
                return f"🔄 {description} (工具: {tool_name})"
        
        return "🎉 所有主要工作流程步骤已完成！"
    
    def clear_memory(self):
        """清除所有记忆"""
        self.user_memory = {
            'confirmed_params': {},
            'tool_history': [],
            'workflow_state': None
        }
        print_yellow("🧹 记忆已清除")
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        summary = "📝 当前记忆状态:\n"
        summary += f"- 已确认参数: {len(self.user_memory['confirmed_params'])} 个\n"
        summary += f"- 工具调用历史: {len(self.user_memory['tool_history'])} 次\n"
        summary += f"- 当前工作流程: {self.user_memory['workflow_state']}\n"
        
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
                            possible_values: List[Any] = None,
                            auto_confirm: bool = True) -> Any:
        """
        获取参数值，优先使用记忆中的值，否则智能推断或使用默认值
        
        Args:
            param_name: 参数名
            param_description: 参数描述
            default_value: 默认值
            possible_values: 可能的值列表
            auto_confirm: 是否自动确认推断的参数
            
        Returns:
            参数值
        """
        # 首先检查记忆中是否有这个参数
        if self.memory.has_confirmed_param(param_name):
            value = self.memory.get_confirmed_param(param_name)
            print_green(f"🧠 使用记忆中的参数: {param_name} = {value}")
            return value
        
        # 尝试从工具历史中推断参数
        inferred_value = self._infer_param_from_history(param_name)
        if inferred_value is not None:
            print_blue(f"🔍 从历史推断参数: {param_name} = {inferred_value}")
            if auto_confirm:
                self.memory.store_confirmed_param(param_name, inferred_value)
            return inferred_value
        
        # 如果没有记忆和推断，使用默认值
        value = default_value
        if value is not None:
            print_blue(f"🔧 使用默认参数: {param_name} = {value}")
            # 存储到记忆中
            if auto_confirm:
                self.memory.store_confirmed_param(param_name, value)
        
        return value
    
    def _infer_param_from_history(self, param_name: str) -> Optional[Any]:
        """从工具历史中推断参数值"""
        tool_history = self.memory.get_tool_history()
        
        # 从最近的工具调用中查找相同参数
        for history_item in reversed(tool_history):
            if param_name in history_item['tool_args']:
                return history_item['tool_args'][param_name]
        
        # 特殊推断逻辑
        if param_name == "house_id":
            # 查找任何包含 house 信息的参数
            for history_item in reversed(tool_history):
                for key, value in history_item['tool_args'].items():
                    if "house" in key.lower() and isinstance(value, (str, int)):
                        if isinstance(value, int):
                            return f"house{value}"
                        elif isinstance(value, str) and value.startswith("house"):
                            return value
        
        elif param_name == "house_number":
            # 从 house_id 推断 house_number
            for history_item in reversed(tool_history):
                if "house_id" in history_item['tool_args']:
                    house_id = history_item['tool_args']['house_id']
                    if isinstance(house_id, str) and house_id.startswith("house"):
                        try:
                            return int(house_id.replace("house", ""))
                        except ValueError:
                            pass
        
        elif param_name in ["mode", "processing_mode"]:
            # 推断处理模式
            for history_item in reversed(tool_history):
                for key, value in history_item['tool_args'].items():
                    if "mode" in key.lower():
                        return value
        
        return None


class Assistant:
    """完善的智能助手 - 集成记忆管理和工具调用"""
    
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
            "You have advanced memory capabilities and can remember user preferences, track workflow progress, and make intelligent recommendations.\n\n"
            
            "Your comprehensive tool suite includes:\n"
            "1. data_preprocessing_pipeline - Complete data preprocessing, perception alignment, and event identification\n"
            "2. tariff_cost_analysis - Electricity cost analysis under different tariff schemes (UK/Germany/California)\n"
            "3. appliance_information_extraction - Extract and standardize appliance information with duplicate handling\n"
            "4. energy_optimization_integration - User constraints processing, duration filtering, and TOU optimization\n"
            "5. scheduling_workflow_integration - Complete intelligent scheduling workflow (P051~P054)\n\n"
            
            "Advanced memory system features:\n"
            "- Remembers all user-confirmed parameters across sessions\n"
            "- Tracks complete tool usage history with timestamps\n"
            "- Monitors workflow progress and completion status\n"
            "- Provides intelligent parameter inference from context\n"
            "- Offers smart recommendations for next steps\n"
            "- Avoids redundant parameter requests\n\n"
            
            "Workflow intelligence:\n"
            "- Automatically tracks which steps have been completed\n"
            "- Suggests logical next steps based on current progress\n"
            "- Infers parameters from previous tool calls\n"
            "- Maintains consistency across related parameters\n"
            "- Provides progress updates and status summaries\n\n"
            
            "Your primary goal is to understand user intent and execute appropriate tools. "
            "Always return responses in this JSON format:\n"
            "{\"intent\": \"clear description of what you're doing\", \"tool\": {\"name\": \"tool_name\", \"args\": {\"param\": \"value\"}}}\n\n"
            
            "Available tools:\n" +
            self._get_tools_prompt() +
            "\n\n"
            "Key principles:\n"
            "- Use memory to avoid asking for the same information twice\n"
            "- Infer parameters intelligently from context and history\n"
            "- Provide helpful workflow guidance and next-step recommendations\n"
            "- Maintain parameter consistency across tool calls\n"
            "- Only ask for clarification when truly necessary"
        )
    
    def chat(self, user_input):
        """处理用户输入并返回助手响应"""
        self.messages.append({"role": "user", "content": user_input})
        
        # 将完整的记忆信息和工作流程状态添加到上下文中
        memory_context = f"\n\nMemory Context:\n{self.memory_manager.get_memory_summary()}"
        
        # 添加下一步推荐
        next_action = self.memory_manager.get_next_recommended_action()
        if next_action:
            memory_context += f"\nRecommended next action: {next_action}"
        
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
            # 如果不是JSON格式，可能是普通对话回复
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
            
            # 生成响应并添加智能建议
            response = f"✅ {intent}\n\n📊 结果:\n{result_str}"
            
            # 添加工作流程进度和下一步建议
            progress = self.memory_manager.get_workflow_progress()
            completed_count = sum(1 for v in progress.values() if v)
            response += f"\n\n📈 工作流程进度: {completed_count}/5 步骤已完成"
            
            next_action = self.memory_manager.get_next_recommended_action()
            if next_action and "所有主要工作流程步骤已完成" not in next_action:
                response += f"\n💡 {next_action}"
            
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
    
    def get_workflow_status(self):
        """获取工作流程状态"""
        progress = self.memory_manager.get_workflow_progress()
        status = "🔄 工作流程状态:\n"
        for step, completed in progress.items():
            icon = "✅" if completed else "⏳"
            status += f"{icon} {step}: {'已完成' if completed else '待执行'}\n"
        
        next_action = self.memory_manager.get_next_recommended_action()
        if next_action:
            status += f"\n💡 {next_action}"
        
        return status
    
    def force_confirm_param(self, param_name: str, param_value: Any):
        """强制确认参数（用于外部设置）"""
        self.memory_manager.store_confirmed_param(param_name, param_value)
        print_blue(f"🔧 外部设置参数: {param_name} = {param_value}")
    
    def clear_param(self, param_name: str):
        """清除特定参数"""
        if param_name in self.memory_manager.user_memory['confirmed_params']:
            del self.memory_manager.user_memory['confirmed_params'][param_name]
            print_yellow(f"🗑️ 已清除参数: {param_name}")
    
    def execute_tool_directly(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """直接执行工具（跳过LLM解析）"""
        intent = f"Direct execution of {tool_name}"
        print_green(f"🔧 直接执行工具: {tool_name}")
        return self._execute_tool_with_memory(tool_name, tool_args, intent)


# 主程序入口
if __name__ == "__main__":
    assistant = Assistant()

    print("=== 🏠 智能家电调度助手 V2 (Enhanced Memory Edition) ===")
    print("🎯 基于高级记忆管理的能源优化系统")
    print("📊 智能工作流程：数据预处理 → 成本分析 → 信息提取 → 能源优化 → 调度集成")
    print("🧠 记忆功能：参数记忆、历史追踪、智能推荐、进度管理")
    print("=" * 90)

    # 演示完整的记忆管理功能
    print("\n🔧 演示1: 数据预处理管道（建立基础参数记忆）")
    print("-" * 60)
    query1 = """
Hi, I have several appliances at home:
Fridge, Chest Freezer, Upright Freezer, Tumble Dryer, Washing Machine, Dishwasher, Computer Site, Television Site, Electric Heater.
Please process the raw power data for house1 in single mode and identify appliance events.
"""
    print_green("User: " + query1)
    response1 = assistant.chat(query1)
    print_yellow("AI response: " + response1)
    print()

    # 显示记忆状态
    print("📝 当前记忆状态:")
    print(assistant.get_memory_status())
    print()

    # 演示参数推断
    print("\n💰 演示2: 电价成本分析（智能参数推断）")
    print("-" * 60)
    query2 = "Now analyze the electricity costs under different tariff schemes - use the same house and mode as before."
    print_green("User: " + query2)
    response2 = assistant.chat(query2)
    print_yellow("AI response: " + response2)
    print()

    # 显示工作流程进度
    print("📈 当前工作流程进度:")
    print(assistant.get_workflow_status())
    print()

    # 演示参数记忆复用
    print("\n🔧 演示3: 电器信息提取（参数记忆复用）")
    print("-" * 60)
    query3 = "Extract and standardize the appliance information from the processed data."
    print_green("User: " + query3)
    response3 = assistant.chat(query3)
    print_yellow("AI response: " + response3)
    print()

    # 演示用户约束设置
    print("\n⚡ 演示4: 能源优化集成（带用户约束）")
    print("-" * 60)
    query4 = """Apply energy optimization with the following constraints:
- Set forbidden time for Washing Machine and Dishwasher: 23:30 to 06:00
- Latest finish time: 14:00 next day
- Ignore events shorter than 5 minutes
"""
    print_green("User: " + query4)
    response4 = assistant.chat(query4)
    print_yellow("AI response: " + response4)
    print()

    # 最终演示：完整调度
    print("\n📅 演示5: 调度工作流程集成（参数自动推断）")
    print("-" * 60)
    query5 = "Execute the complete scheduling workflow for appliance optimization using UK tariffs."
    print_green("User: " + query5)
    response5 = assistant.chat(query5)
    print_yellow("AI response: " + response5)
    print()

    # 显示最终的完整状态
    print("\n" + "=" * 90)
    print("🎉 智能家电调度分析完成！")
    print("=" * 90)
    
    print("\n📊 最终系统状态总览:")
    print(assistant.get_workflow_status())
    print()
    
    print("🧠 完整记忆内容:")
    print(assistant.get_memory_status())
    print()
    
    print("💡 记忆管理功能特点:")
    print("✅ 自动记忆用户确认的参数")
    print("✅ 智能推断相关参数值")
    print("✅ 追踪完整的工具调用历史")
    print("✅ 监控工作流程进度")
    print("✅ 提供智能的下一步建议")
    print("✅ 避免重复询问已确认的参数")
    
    print("\n🔄 高级功能演示:")
    print("- 参数推断：从 house_number=1 自动推断 house_id='house1'")
    print("- 模式记忆：一次设置 mode='single'，后续工具自动复用")
    print("- 电价类型：UK tariff 设置后，相关工具自动使用")
    print("- 工作流程：智能推荐下一步应该执行的工具")
    
    print("=" * 90)
