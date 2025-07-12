import requests
import json
from config import settings

class GPTProxyClient:
    def __init__(self, model=None, api_key=None, base_url=None):
        self.model = model or settings.llm_model4mini
        self.api_key = api_key or settings.open_api_key
        self.url = base_url or settings.llm_url

 

    def chat(self, messages):
        headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json"
    }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.llm_max_tokens,
            "temperature": 0.7
        }

        try:

            response = requests.post(self.url, json=payload, headers=headers, timeout=settings.http_timeout)

            # 非200状态码处理
            if response.status_code != 200:
                print("❌ 请求失败，状态码：", response.status_code)
                print("❌ 响应内容：", response.text)
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "raw": response.text
                }

            result = response.json()
            if "choices" not in result or not result["choices"]:
                return {
                    "success": False,
                    "error": "返回结果中缺少 choices",
                    "raw": result
                }

            content = result["choices"][0]["message"]["content"]
            return {
                "success": True,
                "content": content,
                "raw": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw": None
            }   