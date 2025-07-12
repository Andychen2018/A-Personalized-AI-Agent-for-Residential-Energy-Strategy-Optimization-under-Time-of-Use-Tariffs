import json
import os

import requests
from config import settings

def chat_with_api(messages, model=settings.llm_model4mini):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.open_api_key}"}
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
    messages = [{"role": "user", "content": "你好，你是谁？"}]
    res = chat_with_api(messages)
    print(res)
