"""
LLM聊天接口模块
提供与LLM API的通信功能
"""

import json
import os
import requests

# 导入统一的配置模块
from settings import settings


def chat_with_api(messages, model=settings.llm_model4mini):
    """
    与LLM API进行聊天对话
    
    Args:
        messages (list): 消息列表，包含角色和内容
        model (str): 使用的模型名称，默认使用settings中配置的模型
        
    Returns:
        dict or None: API响应的JSON数据，失败时返回None
    """
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.ai_easy_api_key}"}
    data = {
        "model": model,
        "messages": messages,
        "max_tokens": settings.llm_max_tokens,
    }
    try:
        response = requests.post(settings.llm_url, headers=headers, json=data, timeout=settings.http_timeout)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get response: {response.status_code}")
            print("Error:", response.text)
            return None
    except Exception as e:
        print("Exception occurred:", e)
        return None


if __name__ == "__main__":
    # 测试代码
    messages = [{"role": "user", "content": "Hello, who are you?"}]
    res = chat_with_api(messages)
    print(res)
