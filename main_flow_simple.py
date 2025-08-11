#!/usr/bin/env python3
"""
简化版main_flow.py - 专注于参数记忆功能的AI助手
主要功能：管理用户确认的参数，避免重复询问
"""

import os
import sys
import json
import time
from typing import Dict, List, Optional, Any

# 导入工具模块
from test_func_2_int import batch_process_complete_pipeline, process_single_house_complete
from test_func_3_int import single_house_tariff_analysis, batch_tariff_analysis
from test_func_4_int import single_house_appliance_analysis, batch_appliance_analysis
from test_func_5_int import EnergyOptimizationIntegrator
from test_func_6_int import IntegratedWorkflow

# 颜色输出函数
def print_green(text):
    print(f"\033[92m{text}\033[0m")

def print_blue(text):
    print(f"\033[94m{text}\033[0m")

def print_yellow(text):
    print(f"\033[93m{text}\033[0m")

def print_red(text):
    print(f"\033[91m{text}\033[0m")

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
                    # 尝试通过关键词匹配选择工具
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
        
        print_blue("\n📋 系统功能:")
        print("6. 清除记忆")
        print("7. 查看记忆状态")
        print("q. 退出程序")
        print("="*60)
    
    def _get_parameter_with_memory(self, param_name: str, param_description: str = None) -> str:
        """获取参数，优先使用记忆中的值"""
        # 检查记忆中是否有该参数
        if self.memory_manager.has_confirmed_param(param_name):
            cached_value = self.memory_manager.get_confirmed_param(param_name)
            print_blue(f"📝 使用记忆中的参数: {param_name} = {cached_value}")
            
            # 询问是否使用缓存值
            use_cached = input(f"是否使用记忆中的值 '{cached_value}'? (y/n, 默认y): ").strip().lower()
            if use_cached in ['', 'y', 'yes', '是']:
                return cached_value
        
        # 获取新参数值
        prompt = param_description or f"请输入 {param_name}"
        new_value = input(f"{prompt}: ").strip()
        
        # 存储到记忆中
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
    
    # 工具调用函数
    def _call_data_preprocessing_pipeline(self, batch_or_single: str, house_id: str = None, appliance_config_path: str = None) -> str:
        """调用数据预处理管道"""
        try:
            if batch_or_single.lower() == 'batch':
                result = batch_process_complete_pipeline(appliance_config_path)
                return f"批处理完成，处理结果: {result}"
            else:
                result = process_single_house_complete(house_id, appliance_config_path)
                return f"单个房屋 {house_id} 处理完成，结果: {result}"
        except Exception as e:
            return f"数据预处理失败: {str(e)}"
    
    def _call_tariff_cost_analysis(self, house_or_batch: str, specific_house_id: str = None, tariff_type: str = None) -> str:
        """调用电价成本分析"""
        try:
            if house_or_batch.lower() == 'batch':
                result = batch_tariff_analysis(tariff_type)
                return f"批量电价分析完成，结果: {result}"
            else:
                result = single_house_tariff_analysis(specific_house_id, tariff_type)
                return f"房屋 {specific_house_id} 电价分析完成，结果: {result}"
        except Exception as e:
            return f"电价分析失败: {str(e)}"
    
    def _call_appliance_information_extraction(self, house_or_batch: str, specific_house_id: str = None) -> str:
        """调用电器信息提取"""
        try:
            if house_or_batch.lower() == 'batch':
                result = batch_appliance_analysis()
                return f"批量电器信息提取完成，结果: {result}"
            else:
                result = single_house_appliance_analysis(specific_house_id)
                return f"房屋 {specific_house_id} 电器信息提取完成，结果: {result}"
        except Exception as e:
            return f"电器信息提取失败: {str(e)}"
    
    def _call_energy_optimization_integration(self, batch_or_single: str, house_id: str = None) -> str:
        """调用能源优化集成"""
        try:
            integrator = EnergyOptimizationIntegrator()
            if batch_or_single.lower() == 'batch':
                result = integrator.process_batch_users()
                return f"批量能源优化完成，结果: {result}"
            else:
                result = integrator.process_single_user(house_id)
                return f"房屋 {house_id} 能源优化完成，结果: {result}"
        except Exception as e:
            return f"能源优化失败: {str(e)}"
    
    def _call_scheduling_workflow_integration(self, house_id: str, appliance_config_path: str = None, run_complete: str = "true") -> str:
        """调用调度工作流程集成"""
        try:
            workflow = IntegratedWorkflow()
            if run_complete.lower() == "true":
                result = workflow.run_complete_workflow(house_id, appliance_config_path)
                return f"完整调度工作流程完成，结果: {result}"
            else:
                # 可以添加部分工作流程的调用
                return f"部分调度工作流程完成"
        except Exception as e:
            return f"调度工作流程失败: {str(e)}"

def main():
    """主函数"""
    try:
        assistant = Assistant()
        assistant.run()
    except KeyboardInterrupt:
        print_yellow("\n👋 程序被用户中断")
    except Exception as e:
        print_red(f"❌ 程序运行错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
