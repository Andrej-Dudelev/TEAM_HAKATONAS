# app/core/config.py
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"  # default modelis, jei .env nerasta

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# singleton
settings = Settings()

# Patikrinimui – gali pasileist debug print
if not settings.OPENAI_API_KEY:
    print("⚠️  OPENAI_API_KEY nerastas arba blogas (bus None).")
else:
    print("✅ API Key rastas.")
