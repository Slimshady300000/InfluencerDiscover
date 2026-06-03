from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Influencer Discovery"
    database_url: str = "sqlite:///./data/influencer_discovery.db"
    redis_url: str = "redis://localhost:6379/0"
    youtube_api_key: str = ""
    search_engine_api_key: str = ""
    search_engine_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
