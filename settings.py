"""
项目配置文件
统一管理所有配置参数，包括LLM配置、API密钥等
"""

class Settings:
    """
    项目设置类
    包含所有全局配置参数
    """
    
    # LLM相关配置
    llm_model4mini = "gpt-4.1"                                              # LLM模型名称
    llm_max_tokens = 1024                                                   # LLM最大token数
    llm_url = "https://az.gptplus5.com/v1/chat/completions"                # LLM API地址
    http_timeout = 60                                                       # HTTP请求超时时间(秒)

    # API密钥配置
    ai_easy_api_key = "sk-"  # AI API密钥，请替换为你自己的密钥
    
    # 用户输入配置
    max_input_retries = 3                                                   # 参数验证失败时的最大重试次数

# 创建全局设置实例
settings = Settings()