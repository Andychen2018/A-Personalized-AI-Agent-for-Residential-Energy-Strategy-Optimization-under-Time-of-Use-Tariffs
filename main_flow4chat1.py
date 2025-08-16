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
import json

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

# ============================================================================
# 默认用户调度指令配置 (可在程序启动前修改)
# ============================================================================
DEFAULT_USER_INSTRUCTION = (
    "Set forbidden operating time for Washing Machine, Tumble Dryer, and Dishwasher as 23:30 to 06:00 (next day);\n"
    "Ensure each event completes by 14:00 the next day (i.e., 38:00);\n"
    "Ignore events shorter than 5 minutes;\n"
    "Keep all other appliance rules as default."
)

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
            'house_id': {
                'description': '房屋ID (格式: houseN)',
                'default': 'house1',
                'type': 'str',
                'prompt': '输入房屋ID (如: house1)',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
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
                'default': DEFAULT_USER_INSTRUCTION,  # 使用预设的默认指令
                'type': 'str',
                'prompt': '输入用户调度指令 (直接回车使用默认指令)',
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
    {f"- {options_text}" if options_text else ""}

    用户消息: "{user_message}"

    请分析用户消息，如果能从中提取到该参数的值，请直接返回该值。
    如果无法提取，请用友好的方式向用户询问该参数，并说明参数的用途。

    请以JSON格式回复，包含以下字段：
    {{
        "extracted_value": "提取到的值，如果未提取到则为null",
        "response": "给用户的回复消息"
    }}

    注意事项：
    1. 如果提取到值，请确保格式正确
    2. 如果是house_id，确保格式为houseN（如house1）
    3. 如果是数字类型，确保返回有效数字
    4. 回复要简洁友好，帮助用户理解参数用途
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
        # 调试信息：显示当前缓存状态
        print_yellow(f"🔍 调试: 查找参数 {param_name}，当前缓存: {list(self._cache.keys())}")

        # 检查缓存
        if param_name in self._cache:
            cached_value = self._cache[param_name]
            print_blue(f"📝 使用之前输入的参数: {param_name} = {cached_value}")
            return cached_value

        # 检查是否可以从其他已缓存的参数推导出当前参数
        derived_value = self._try_derive_parameter(param_name, param_config)
        if derived_value is not None:
            self._cache[param_name] = derived_value
            print_blue(f"📝 从已有参数推导: {param_name} = {derived_value}")
            return derived_value
        
        max_retries = 3
        retry_count = 0
        
        # 如果没有用户消息，先询问用户
        if not user_message.strip():
            default_value = param_config.get('default')
            if param_name == 'user_instruction' and len(str(default_value)) > 50:
                default_display = "预设默认指令"
            else:
                default_display = str(default_value) if default_value is not None else "无"

            user_message = input(f"请输入关于 {param_config.get('description', param_name)} 的信息 [默认: {default_display}]: ").strip()

            # 如果用户直接回车（空输入），使用默认值
            if not user_message and default_value is not None:
                try:
                    converted_value = self._convert_and_validate(default_value, param_config)
                    self._cache[param_name] = converted_value
                    print_green(f"✅ 使用默认值: {param_name} = {converted_value}")
                    return converted_value
                except ValueError as e:
                    print_yellow(f"⚠️ 默认值验证失败: {e}")
                    # 继续执行 LLM 处理
        
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

                        # 如果用户输入空字符串，检查是否有默认值
                        if not user_message:
                            default_value = param_config.get('default')
                            if default_value is not None:
                                try:
                                    converted_value = self._convert_and_validate(default_value, param_config)
                                    self._cache[param_name] = converted_value
                                    print_green(f"✅ 使用默认值: {param_name} = {converted_value}")
                                    return converted_value
                                except ValueError:
                                    pass  # 默认值也无效，继续循环

                        retry_count += 1
                        continue
                else:
                    # LLM需要更多信息
                    user_message = input("👤 请回复: ").strip()

                    # 如果用户输入空字符串，检查是否有默认值
                    if not user_message:
                        default_value = param_config.get('default')
                        if default_value is not None:
                            try:
                                converted_value = self._convert_and_validate(default_value, param_config)
                                self._cache[param_name] = converted_value
                                print_green(f"✅ 使用默认值: {param_name} = {converted_value}")
                                return converted_value
                            except ValueError as e:
                                print_yellow(f"⚠️ 默认值验证失败: {e}")
                                # 继续循环，要求用户重新输入
                    
            except Exception as e:
                print_red(f"❌ LLM处理错误: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    return self._fallback_to_direct_input(param_name, param_config)
                user_message = input("请重新输入: ").strip()

                # 如果用户输入空字符串，检查是否有默认值
                if not user_message:
                    default_value = param_config.get('default')
                    if default_value is not None:
                        try:
                            converted_value = self._convert_and_validate(default_value, param_config)
                            self._cache[param_name] = converted_value
                            print_green(f"✅ 使用默认值: {param_name} = {converted_value}")
                            return converted_value
                        except ValueError:
                            pass  # 默认值也无效，继续循环
        
        # 重试次数用完，回退到直接输入
        return self._fallback_to_direct_input(param_name, param_config)

    def _try_derive_parameter(self, param_name: str, param_config: Dict[str, Any]) -> Any:
        """尝试从已有参数推导出当前参数"""
        try:
            # house_number 可以从 house_id 推导
            if param_name == 'house_number' and 'house_id' in self._cache:
                house_id = self._cache['house_id']
                if isinstance(house_id, str) and house_id.startswith('house'):
                    house_number = int(house_id.replace('house', ''))
                    return self._convert_and_validate(house_number, param_config)

            # house_id 可以从 house_number 推导（向后兼容）
            elif param_name == 'house_id' and 'house_number' in self._cache:
                house_number = self._cache['house_number']
                house_id = f"house{house_number}"
                return self._convert_and_validate(house_id, param_config)

            # mode 参数在不同步骤间通常保持一致
            elif param_name == 'mode' and any(k.endswith('_mode') or k.startswith('mode_') for k in self._cache):
                for cached_key, cached_value in self._cache.items():
                    if 'mode' in cached_key.lower():
                        return self._convert_and_validate(cached_value, param_config)

            # tariff_type 参数在不同步骤间通常保持一致
            elif param_name == 'tariff_type' and any('tariff' in k.lower() for k in self._cache):
                for cached_key, cached_value in self._cache.items():
                    if 'tariff' in cached_key.lower() and cached_key != param_name:
                        return self._convert_and_validate(cached_value, param_config)

        except (ValueError, TypeError):
            pass  # 推导失败，返回 None

        return None

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
                    # 对于用户调度指令，如果是长文本，显示简化版本
                    if param_name == 'user_instruction' and len(str(default)) > 50:
                        default_display = "预设默认指令"
                    else:
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
    """统一的工作流程执行器 - 使用LLM对话模式"""
    
    def __init__(self, use_llm_conversation: bool = True):
        self.use_llm_conversation = use_llm_conversation
        if use_llm_conversation:
            self.param_manager = LLMParameterManager()
        else:
            self.param_manager = ParameterMemoryManager()
    
    def collect_param(self, step_index: int, user_input_message: str = "") -> Dict[str, Any]:
        """统一的参数收集函数 - 支持LLM对话或直接输入"""
        if step_index < 0 or step_index >= len(TOOLS):
            raise ValueError(f"无效的步骤索引: {step_index}")
        
        tool_config = TOOLS[step_index]
        params = {}
        
        print_blue(f"📋 收集 {tool_config['name']} 的参数...")
        
        if self.use_llm_conversation:
            print_green("🤖 使用LLM对话模式收集参数")
            
            for param_name, param_config in tool_config['parameters'].items():
                params[param_name] = self.param_manager.get_param_with_llm_conversation(
                    param_name, param_config, user_input_message
                )
        else:
            print_green("📝 使用直接输入模式收集参数")
            
            for param_name, param_config in tool_config['parameters'].items():
                params[param_name] = self.param_manager.get_param_with_config(param_name, param_config)
        
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
        print_green(f"\n===== Step{step_index}: {tool_config['name']} =====")
        
        try:
            # 收集参数（支持用户输入消息）
            params = self.collect_param(step_index, user_input)
            
            # 执行函数
            function_name = tool_config['function'].__name__
            print_blue(f"⚙️ 正在执行: {tool_config['description']} (函数: {function_name})")
            result = tool_config['function'](**params)
            
            print_green(f"✅ Step{step_index}: {tool_config['name']} 完成")
            return result
            
        except Exception as e:
            print_red(f"❌ Step{step_index}: {tool_config['name']} 执行失败: {e}")
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
                print("\n" + "="*60)
                print_green("📋 可用的步骤:")
                for i, tool in enumerate(TOOLS):
                    print_blue(f"  {i}: {tool['name']} - {tool['description']}")
                
                print_yellow("\n输入指令选项:")
                print_yellow("  - 输入步骤编号 (0-4) 来执行特定步骤")
                print_yellow("  - 输入 'all' 执行所有步骤")
                print_yellow("  - 输入 'quit' 或 'exit' 退出")
                print_yellow("  - 输入其他文本作为参数设置的自然语言描述")
                
                user_input = input("\n👤 请输入: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print_green("👋 退出交互模式")
                    break
                elif user_input == 'all':
                    self.run_all_steps()
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
        else:
            # 如果无法匹配特定步骤，询问用户
            print_yellow("🤔 无法确定要执行的步骤，请指定步骤编号或使用更明确的描述")
    
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
        # 询问运行模式
        print_green("🎯 选择运行模式:")
        print_blue("  1: 交互式模式 (推荐) - 支持自然语言参数设置")
        print_blue("  2: 自动模式 - 按顺序执行所有步骤")
        
        try:
            mode_choice = input("请选择模式 (1 或 2): ").strip()
            if mode_choice == '1':
                self.interactive_mode()
            else:
                self.run_all_steps()
        except KeyboardInterrupt:
            print_yellow("\n👋 程序被用户中断")


def main():
    """主函数 - 支持LLM对话模式和传统输入模式"""
    try:
        print_green("🎉 欢迎使用家庭能源管理系统工作流程！")
        print_blue("🤖 本系统支持LLM智能对话模式，您可以用自然语言描述需求")
        
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
    main()
