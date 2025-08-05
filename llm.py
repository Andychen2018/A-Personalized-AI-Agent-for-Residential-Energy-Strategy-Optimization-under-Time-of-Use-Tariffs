import json
import os

import requests


# Simulated settings module
class Settings:
    # LLM Configurations
    llm_model4mini = "gpt-4.1"
    llm_max_tokens = 1024
    llm_url = "https://az.gptplus5.com/v1/chat/completions"
    http_timeout = 60

    # API Key
    ai_easy_api_key = "sk-Gr04295hSF03dqn0Bf0cD03699D84450857266D5692aBa2d"


# Instantiate settings
settings = Settings()


def chat_with_api(messages, model=settings.llm_model4mini):
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
    messages = [{"role": "user", "content": "你好，你是谁？"}]
    res = chat_with_api(messages)
    print(res)
