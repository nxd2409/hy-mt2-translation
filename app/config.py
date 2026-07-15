import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str
    host: str
    port: int
    vllm_api_url: str
    model_name: str
    default_temperature: float
    default_top_p: float
    default_top_k: int
    default_repetition_penalty: float
    default_max_tokens: int

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
