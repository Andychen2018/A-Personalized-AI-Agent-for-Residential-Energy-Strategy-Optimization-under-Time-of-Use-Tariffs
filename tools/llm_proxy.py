"""
LLM代理客户端模块
提供GPT代理服务的客户端实现，用于与LLM API进行交互
"""

import requests
import json
import sys
import os

# 添加项目根目录到Python路径，以便导入根目录的settings模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import settings


class GPTProxyClient:
    """
    GPT代理客户端类
    封装与LLM API的交互逻辑，提供统一的聊天接口
    """
    
    def __init__(self, model=None, api_key=None, base_url=None):
        """
        初始化GPT代理客户端
        
        Args:
            model (str, optional): LLM模型名称，默认使用settings中的配置
            api_key (str, optional): API密钥，默认使用settings中的配置
            base_url (str, optional): API基础URL，默认使用settings中的配置
        """
        self.model = model or settings.llm_model4mini
        self.api_key = api_key or settings.ai_easy_api_key
        self.url = base_url or settings.llm_url

    def chat(self, messages):
        """
        发送聊天消息到LLM API
        
        Args:
            messages (list): 消息列表，每个消息包含role和content字段
            
        Returns:
            dict: 包含成功状态、内容和原始响应的字典
                - success (bool): 请求是否成功
                - content (str): LLM响应内容（仅成功时）
                - error (str): 错误信息（仅失败时）
                - raw: 原始API响应数据
        """
        # 构建HTTP请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求负载
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.llm_max_tokens,
            "temperature": 0.7
        }

        try:
            # 发送HTTP POST请求到LLM API
            response = requests.post(self.url, json=payload, headers=headers, timeout=settings.http_timeout)

            # 处理非200状态码
            if response.status_code != 200:
                print("Request failed, status code:", response.status_code)
                print("Response content:", response.text)
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "raw": response.text
                }

            # 解析JSON响应
            result = response.json()
            if "choices" not in result or not result["choices"]:
                return {
                    "success": False,
                    "error": "Missing choices in response",
                    "raw": result
                }

            # 提取响应内容
            content = result["choices"][0]["message"]["content"]
            return {
                "success": True,
                "content": content,
                "raw": result
            }

        except Exception as e:
            # 处理异常情况
            return {
                "success": False,
                "error": str(e),
                "raw": None
            }   