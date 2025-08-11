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
    """管理用户确认参数的简化记忆系统"""
    
    def __init__(self):
        self.confirmed_params = {}  # 用户已确认的参数
    
    def store_confirmed_param(self, param_name: str, param_value: Any):
        """存储用户确认的参数"""
        self.confirmed_params[param_name] = param_value
        print_blue(f"📝 记忆已保存: {param_name} = {param_value}")
    
    def get_confirmed_param(self, param_name: str) -> Optional[Any]:
        """获取用户之前确认的参数"""
        return self.confirmed_params.get(param_name)
    
    def has_confirmed_param(self, param_name: str) -> bool:
        """检查是否有用户确认的参数"""
        return param_name in self.confirmed_params
    
    def clear_memory(self):
        """清除所有记忆"""
        self.confirmed_params = {}
        print_yellow("🧹 记忆已清除")
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        if not self.confirmed_params:
            return "📝 当前记忆状态: 无已确认参数"
        
        summary = "📝 当前记忆状态:\n"
        summary += f"- 已确认参数: {len(self.confirmed_params)} 个\n"
        
        for key, value in self.confirmed_params.items():
            summary += f"  - {key}: {value}\n"
        
        return summary


class Assistant:
    """AI助手主类 - 简化版本，专注于参数记忆"""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.available_tools = {
            'data_preprocessing_pipeline': {
                'description': '数据预处理管道 - 包含感知对齐、可变性识别、事件分割',
                'parameters': ['batch_or_single', 'house_id', 'appliance_config_path'],
                'function': self._call_data_preprocessing_pipeline
            },
            'tariff_cost_analysis': {
                'description': '电价成本分析 - 英国、德国、加州电价方案分析',
                'parameters': ['house_or_batch', 'specific_house_id', 'tariff_type'],
                'function': self._call_tariff_cost_analysis
            },
            'appliance_information_extraction': {
                'description': '电器信息提取 - 标准化电器名称和处理重复',
                'parameters': ['house_or_batch', 'specific_house_id'],
                'function': self._call_appliance_information_extraction
            },
            'energy_optimization_integration': {
                'description': '能源优化集成 - 用户约束、最小持续时间过滤、TOU优化',
                'parameters': ['batch_or_single', 'house_id'],
                'function': self._call_energy_optimization_integration
            },
            'scheduling_workflow_integration': {
                'description': '调度工作流程集成 - 完整的调度和冲突解决',
                'parameters': ['house_id', 'appliance_config_path', 'run_complete'],
                'function': self._call_scheduling_workflow_integration
            }
        }
    
    def run(self):
        """运行AI助手"""
        print_green("🚀 AI助手启动成功！")
        print_blue("💡 本助手支持家庭电器调度的完整工作流程，包含记忆功能")
        print_yellow("📝 系统会记住您确认的参数，避免重复询问")
        
        while True:
            try:
                self._display_help()
                user_input = input("\n请选择操作 (输入编号或描述): ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print_green("👋 感谢使用AI助手！")
                    break
                elif user_input == '6':
                    self.memory_manager.clear_memory()
                elif user_input == '7':
                    print(self.memory_manager.get_memory_summary())
                elif user_input in ['1', '2', '3', '4', '5']:
                    tool_names = list(self.available_tools.keys())
                    selected_tool = tool_names[int(user_input) - 1]
                    self._execute_tool(selected_tool)
                else:
                    selected_tool = self._select_tool_by_description(user_input)
                    if selected_tool:
                        self._execute_tool(selected_tool)
                    else:
                        print_red("❌ 无法理解您的请求，请重新选择")
                        
            except KeyboardInterrupt:
                print_yellow("\n👋 用户中断，退出程序")
                break
            except Exception as e:
                print_red(f"❌ 发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
    
    def _display_help(self):
        """显示帮助信息"""
        print("\n" + "="*60)
        print_blue("🛠️  可用工具:")
        for i, (tool_name, tool_info) in enumerate(self.available_tools.items(), 1):
            print(f"{i}. {tool_info['description']}")
        
        print_blue("\n� 系统功能:")
        print("6. 清除记忆")
        print("7. 查看记忆状态")
        print("q. 退出程序")
        print("="*60)
    
    def _get_parameter_with_memory(self, param_name: str, param_description: str = None) -> str:
        """获取参数，优先使用记忆中的值"""
        if self.memory_manager.has_confirmed_param(param_name):
            cached_value = self.memory_manager.get_confirmed_param(param_name)
            print_blue(f"📝 使用记忆中的参数: {param_name} = {cached_value}")
            use_cached = input(f"是否使用记忆中的值 '{cached_value}'? (y/n, 默认y): ").strip().lower()
            if use_cached in ['', 'y', 'yes', '是']:
                return cached_value
        
        prompt = param_description or f"请输入 {param_name}"
        new_value = input(f"{prompt}: ").strip()
        if new_value:
            self.memory_manager.store_confirmed_param(param_name, new_value)
        return new_value
    
    def _execute_tool(self, tool_name: str):
        """执行选定的工具"""
        if tool_name not in self.available_tools:
            print_red(f"❌ 工具 {tool_name} 不存在")
            return
        
        tool_info = self.available_tools[tool_name]
        print_green(f"🔧 执行工具: {tool_info['description']}")
        
        try:
            # 收集所需参数
            tool_args = {}
            for param in tool_info['parameters']:
                param_value = self._get_parameter_with_memory(param, f"{param} 参数")
                if not param_value:
                    print_red(f"❌ 参数 {param} 不能为空")
                    return
                tool_args[param] = param_value
            
            # 执行工具
            print_blue(f"⚙️ 正在执行工具...")
            result = tool_info['function'](**tool_args)
            
            print_green(f"✅ 工具执行完成")
            if result:
                print_blue(f"📋 执行结果: {result}")
                
        except Exception as e:
            print_red(f"❌ 工具执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _select_tool_by_description(self, user_input: str) -> Optional[str]:
        """通过用户描述选择工具"""
        # 简单的关键词匹配
        keywords_map = {
            'data_preprocessing_pipeline': ['数据', '预处理', '感知', '对齐', '事件', '分割'],
            'tariff_cost_analysis': ['电价', '成本', '分析', '德国', '英国', '加州'],
            'appliance_information_extraction': ['电器', '信息', '提取', '标准化'],
            'energy_optimization_integration': ['能源', '优化', '约束', 'TOU'],
            'scheduling_workflow_integration': ['调度', '工作流程', '冲突', '解决']
        }
        
        user_input_lower = user_input.lower()
        for tool_name, keywords in keywords_map.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return tool_name
        
        return None


# 工具函数定义
def _call_data_preprocessing_pipeline(batch_or_single: str, house_id: str = None, appliance_config_path: str = None) -> str:
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
    
    print("\n� 最终系统状态总览:")
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
