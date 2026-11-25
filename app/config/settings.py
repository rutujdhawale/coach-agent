import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    PRIMARY_MODEL: str = "groq/openai/gpt-oss-120b"
    FALLBACK_MODELS: str = "groq/qwen/qwen3.8-27b,groq/openai/gpt-oss-20b,gemini/gemini-2.5-flash"
    MAX_OUTPUT_TOKENS: int = 700
    SESSION_DB_URL: str = "sqlite+aiosqlite:///./data/sessions.db"
    AUTH_REQUIRED: bool = False
    JWT_SECRET: str = "examblue-dev-secret-change-in-prod"
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "examblue"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings():
    return Settings()
