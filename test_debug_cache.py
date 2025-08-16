#!/usr/bin/env python3
"""
测试带调试信息的缓存机制
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

from main_flow4chat1 import WorkflowRunner

def test_debug_cache():
    """测试带调试信息的缓存机制"""
    print("🧪 测试带调试信息的缓存机制")
    print("=" * 50)
    
    # 创建工作流程运行器
    runner = WorkflowRunner(use_llm_conversation=True)
    
    # 手动设置一些缓存值来模拟第一步的输入
    print("📋 模拟第一步用户输入:")
    runner.param_manager._cache['house_id'] = 'house1'
    runner.param_manager._cache['mode'] = 1
    
    print("当前缓存内容:")
    for key, value in runner.param_manager._cache.items():
        print(f"  - {key}: {value}")
    
    # 测试第二步参数收集（模拟）
    print(f"\n📋 模拟第二步参数收集:")
    
    # 模拟第二步的参数配置
    step2_config = {
        'house_id': {
            'description': '房屋ID (格式: houseN)',
            'default': 'house1',
            'type': 'str',
            'validator': lambda x: str(x).startswith('house') and str(x)[5:].isdigit()
        },
        'tariff_type': {
            'description': '电价类型 (UK/Germany/California)',
            'default': 'UK',
            'type': 'str',
            'validator': lambda x: str(x).lower() in ['uk', 'germany', 'california']
        }
    }
    
    # 测试 house_id 参数查找
    print(f"\n🔍 测试 house_id 参数查找:")
    try:
        house_id_result = runner.param_manager.get_param_with_llm_conversation(
            'house_id', step2_config['house_id'], ""
        )
        print(f"结果: {house_id_result}")
    except Exception as e:
        print(f"错误: {e}")
    
    # 测试 tariff_type 参数查找（应该使用默认值）
    print(f"\n🔍 测试 tariff_type 参数查找:")
    try:
        tariff_result = runner.param_manager.get_param_with_llm_conversation(
            'tariff_type', step2_config['tariff_type'], ""
        )
        print(f"结果: {tariff_result}")
    except Exception as e:
        print(f"错误: {e}")
    
    print(f"\n📋 最终缓存状态:")
    for key, value in runner.param_manager._cache.items():
        print(f"  - {key}: {value}")

if __name__ == "__main__":
    test_debug_cache()
