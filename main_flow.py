#!/usr/bin/env python3
"""main_flow.py
基于TOOLS配置的统一工作流程执行器。

工作流程按TOOLS数组顺序执行：
Step0(index 0): 感知与事件基础流水线  -> test_func_2_int_main
Step1(index 1): 电价成本分析          -> test_func_3_int_main
Step2(index 2): 电器信息标准化        -> test_func_4_int_main
Step3(index 3): 能源优化             -> test_func_5_int_main
Step4(index 4): 调度集成             -> test_func_6_int_main

每个步骤统一架构：
    params = collect_param()
    function(**params)
"""

from typing import Optional, Dict, Any, List

# 导入配置
from settings import settings

# 导入工具模块
from test_func_2_int import main as test_func_2_int_main
from test_func_3_int import main as test_func_3_int_main
from test_func_4_int import main as test_func_4_int_main
from test_func_5_int import main as test_func_5_int_main
from test_func_6_int import main as test_func_6_int_main

# 工具配置定义 (按执行顺序排列)
TOOLS = [
    {
        'function': test_func_2_int_main,
        'name': '感知与事件基础流水线',
        'description': '数据预处理管道 - 包含感知对齐、可变性识别、事件分割',
        'parameters': {
            'mode': {
                'description': '处理模式 (1=单个家庭, 2=批量处理)',
                'default': 1,
                'type': 'int',
                'prompt': '输入处理模式',
                'validator': lambda x: str(x).isdigit()
            },
            'house_number': {
                'description': '房屋编号 (数字)',
                'default': 1,
                'type': 'int', 
                'prompt': '输入房屋编号 (数字)',
                'validator': lambda x: str(x).isdigit()
            }
        }
    },
    {
        'function': test_func_3_int_main,
        'name': '电价成本分析',
        'description': '英国、德国、加州电价方案分析',
        'parameters': {
            'mode': {
                'description': '分析模式 (1=单个家庭, 2=批量, 3=仅显示)',
                'default': 1,  # 默认单个家庭模式
                'type': 'int',
                'prompt': '输入分析模式 (1=单个家庭, 2=批量, 3=仅显示)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2, 3]
            },
            'tariff_type': {
                'description': '电价类型 (UK/Germany/California)',
                'default': 'UK',
                'type': 'str',
                'prompt': '选择电价类型 (UK / Germany / California)',
                'validator': lambda x: str(x).lower() in ['uk', 'germany', 'california']
            },
            'house_id': {
                'description': '房屋ID (格式: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': '输入房屋ID (如 house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            }
        }
    },
    {
        'function': test_func_4_int_main,
        'name': '电器信息标准化',
        'description': '标准化电器名称和处理重复',
        'parameters': {
            'mode': {
                'description': '提取模式 (1=单个家庭, 2=批量)',
                'default': 1,  # 默认单个家庭模式
                'type': 'int',
                'prompt': '输入提取模式 (1=单个家庭, 2=批量)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'tariff_type': {
                'description': '电价类型 (UK/Germany/California)',
                'default': 'UK',
                'type': 'str',
                'prompt': '选择电价类型 (UK / Germany / California)',
                'validator': lambda x: str(x).lower() in ['uk', 'germany', 'california']
            },
            'house_id': {
                'description': '房屋ID (格式: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': '输入房屋ID (如 house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            }
        }
    },
    {
        'function': test_func_5_int_main,
        'name': '能源优化 (约束+过滤)',
        'description': '用户约束、最小持续时间过滤、TOU优化',
        'parameters': {
            'mode': {
                'description': '优化模式 (1=单个家庭, 2=批量)',
                'default': 1,  # 默认单个家庭模式
                'type': 'int',
                'prompt': '输入优化模式 (1=单个家庭, 2=批量)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'house_id': {
                'description': '房屋ID (格式: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': '输入房屋ID (如 house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            },
            'user_instruction': {
                'description': '用户调度指令 (可选)',
                'default': '',  # 空字符串作为默认值
                'type': 'str',
                'prompt': '输入用户调度指令 (可留空使用默认逻辑)',
                'validator': None  # 允许空值
            },
            'house_list': {
                'description': '房屋列表 (批量模式时使用，多个房屋请用英文逗号分割，如 house1,house2,house3)',
                'default': '',  # 空字符串作为默认值
                'type': 'str',  # 改为字符串类型
                'prompt': '输入房屋列表 (通常为空)',
                'validator': None  # 通常为固定值None
            }
        }
    },
    {
        'function': test_func_6_int_main,
        'name': '调度集成 (P051~P054)',
        'description': '完整的调度和冲突解决工作流程',
        'parameters': {
            'tariff_group': {
                'description': '电价组 (基于tariff_type映射)',
                'default': 'UK',
                'type': 'str',
                'prompt': '选择电价组 (UK/TOU_D/Germany_Variable)',
                'validator': lambda x: str(x) in ['UK', 'TOU_D', 'Germany_Variable']
            },
            'mode': {
                'description': '处理模式 (1=单个家庭, 2=批量)',
                'default': 1,
                'type': 'int',
                'prompt': '选择处理模式 (1=单个家庭, 2=批量)',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'house_id': {
                'description': '房屋ID (格式: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': '输入房屋ID (如 house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            },
            'interactive': {
                'description': '是否交互模式 (true/false)',
                'default': False,
                'type': 'bool',
                'prompt': '是否启用交互模式 (true / false)',
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

# 颜色输出函数
def print_green(text):
    print(f"\033[92m{text}\033[0m")

def print_blue(text):
    print(f"\033[94m{text}\033[0m")

def print_yellow(text):
    print(f"\033[93m{text}\033[0m")

def print_red(text):
    print(f"\033[91m{text}\033[0m")


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
        prompt = param_config.get('prompt', f"请输入 {param_name}")
        default = param_config.get('default')
        validator = param_config.get('validator')
        param_type = param_config.get('type', 'str')
        
        print_green(f"🛠 需要输入参数: {param_name}")
        
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
    """统一的工作流程执行器"""
    
    def __init__(self):
        self.param_manager = ParameterMemoryManager()
    
    def collect_param(self, step_index: int) -> Dict[str, Any]:
        """统一的参数收集函数 - 所有参数都通过用户输入获得"""
        if step_index < 0 or step_index >= len(TOOLS):
            raise ValueError(f"无效的步骤索引: {step_index}")
        
        tool_config = TOOLS[step_index]
        params = {}
        
        print_blue(f"📋 收集 {tool_config['name']} 的参数...")
        
        for param_name, param_config in tool_config['parameters'].items():
            # 所有参数都通过用户输入获得，支持缓存避免重复询问
            params[param_name] = self.param_manager.get_param_with_config(param_name, param_config)
        
        # 打印收集完成的所有参数
        print_green("✅ 参数收集完成！最终参数如下：")
        for param_name, param_value in params.items():
            print_blue(f"  📌 {param_name}: {param_value}")
        
        return params
    
    def execute_step(self, step_index: int):
        """执行指定步骤 - 统一架构"""
        if step_index < 0 or step_index >= len(TOOLS):
            print_red(f"❌ 无效的步骤索引: {step_index}")
            return
        
        tool_config = TOOLS[step_index]
        print_green(f"\n===== Step{step_index}: {tool_config['name']} =====")
        
        try:
            # 统一架构：params = collect_param()
            params = self.collect_param(step_index)
            
            # 统一架构：function(**params)
            function_name = tool_config['function'].__name__
            print_blue(f"⚙️ 正在执行: {tool_config['description']} (函数: {function_name})")
            result = tool_config['function'](**params)
            
            print_green(f"✅ Step{step_index}: {tool_config['name']} 完成")
            return result
            
        except Exception as e:
            print_red(f"❌ Step{step_index}: {tool_config['name']} 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run_all_steps(self):
        """按顺序执行所有步骤"""
        print_green("🚀 开始执行完整工作流程")
        print_blue(f"📊 共有 {len(TOOLS)} 个步骤需要执行")
        
        for step_index in range(len(TOOLS)):
            self.execute_step(step_index)
            
        print_green("\n🎉 全部步骤执行结束！")
    
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
        """主运行方法"""
        self.run_all_steps()


def main():
    """主函数"""
    try:
        runner = WorkflowRunner()
        runner.run()
    except KeyboardInterrupt:
        print_yellow("\n👋 程序被用户中断")
    except Exception as e:
        print_red(f"❌ 程序运行错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
