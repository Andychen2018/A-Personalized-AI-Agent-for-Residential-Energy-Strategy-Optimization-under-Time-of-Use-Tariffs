from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Configurations
    llm_model4mini: str = "gpt-4.1"
    llm_max_tokens: int = 1024
    llm_url: str = "https://az.gptplus5.com/v1/chat/completions"
    http_timeout: int = 60

    # API Key
    open_api_key: str = "sk-" # 请替换为你自己的 key

settings = Settings()
