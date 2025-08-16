#!/usr/bin/env python3
"""
测试LLM对话式参数收集功能
"""

from main_flow4chat import LLMParameterManager, print_green, print_blue, print_yellow, print_red

def test_llm_parameter_extraction():
    """测试LLM参数提取功能"""
    
    print_green("🧪 测试LLM参数提取功能")
    
    # 创建参数管理器
    param_manager = LLMParameterManager()
    
    # 测试参数配置
    test_configs = [
        {
            'param_name': 'mode',
            'param_config': {
                'description': '处理模式 (1=单个家庭, 2=批量处理)',
                'default': 1,
                'type': 'int',
                'validator': lambda x: str(x).isdigit() and int(str(x)) in [1, 2]
            },
            'test_messages': [
                "我想处理单个家庭",
                "使用批量模式",
                "mode=2",
                "1"
            ]
        },
        {
            'param_name': 'house_id', 
            'param_config': {
                'description': '房屋ID (格式: houseN)',
                'default': 'house1',
                'type': 'str',
                'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
            },
            'test_messages': [
                "分析house3的数据",
                "我需要house10的信息",
                "房屋编号是5",
                "house7"
            ]
        },
        {
            'param_name': 'tariff_type',
            'param_config': {
                'description': '电价类型 (UK/Germany/California)',
                'default': 'UK',
                'type': 'str',
                'validator': lambda x: str(x).lower() in ['uk', 'germany', 'california']
            },
            'test_messages': [
                "使用德国电价方案",
                "我想分析加州的电价",
                "UK电价",
                "Germany"
            ]
        }
    ]
    
    # 执行测试
    for test_config in test_configs:
        param_name = test_config['param_name']
        param_config = test_config['param_config']
        
        print_blue(f"\n{'='*50}")
        print_blue(f"测试参数: {param_name}")
        print_blue(f"参数描述: {param_config['description']}")
        
        for i, test_message in enumerate(test_config['test_messages']):
            print_yellow(f"\n测试消息 {i+1}: '{test_message}'")
            
            try:
                # 重置缓存以便重新测试
                if param_name in param_manager._cache:
                    del param_manager._cache[param_name]
                
                # 测试参数提取
                result = param_manager.get_param_with_llm_conversation(
                    param_name, param_config, test_message
                )
                print_green(f"✅ 提取结果: {result}")
                
            except Exception as e:
                print_red(f"❌ 提取失败: {e}")

def test_interactive_mode():
    """测试交互模式"""
    from main_flow4chat import WorkflowRunner
    
    print_green("\n🧪 测试交互模式")
    print_blue("💡 您可以输入以下测试语句:")
    print_blue("   - '分析house3的德国电价'")
    print_blue("   - '使用批量模式'") 
    print_blue("   - 或直接输入 'quit' 退出测试")
    
    runner = WorkflowRunner(use_llm_conversation=True)
    
    # 模拟交互模式的简化版本
    while True:
        try:
            user_input = input("\n👤 请输入测试消息 (输入 'quit' 退出): ").strip()
            if user_input.lower() == 'quit':
                break
                
            print_green(f"🤖 处理输入: {user_input}")
            runner._handle_natural_language_input(user_input)
            
        except KeyboardInterrupt:
            print_yellow("\n⚠️ 测试被中断")
            break
        except Exception as e:
            print_red(f"❌ 测试错误: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        test_interactive_mode()
    else:
        print_green("🎯 LLM对话式参数收集测试")
        print_blue("使用 'python test_llm_chat.py interactive' 来测试交互模式")
        print_blue("直接运行来测试参数提取功能")
        test_llm_parameter_extraction()
