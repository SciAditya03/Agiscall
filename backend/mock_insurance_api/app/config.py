from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/aegiscall"
    token_secret: str = "dev-only-change-me"
    verification_ttl_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
