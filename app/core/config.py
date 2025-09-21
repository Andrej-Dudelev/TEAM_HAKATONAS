from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

if not settings.OPENAI_API_KEY:
    print("OPENAI_API_KEY not found. The application might not work as expected.")
else:
    print("OpenAI API Key loaded successfully.")