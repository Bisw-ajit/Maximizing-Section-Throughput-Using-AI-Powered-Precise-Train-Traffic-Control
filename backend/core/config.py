from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "RAILOPTIX"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./railoptix.db"
    RAILRADAR_API_KEY: str = ""
    MAPTILER_API_KEY: str = ""
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
