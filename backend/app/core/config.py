from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str = ""
    GEMINI_API_KEY: str = ""

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # fallback dev
       "http://172.16.20.97:5173",  # Network IP

    ]

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
