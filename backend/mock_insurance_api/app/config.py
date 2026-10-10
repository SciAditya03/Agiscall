import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _random_secret() -> str:
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/aegiscall"
    # No committed default: unset means a fresh random secret per process, so tokens
    # can't be forged by anyone who has read the repo. Set it to share tokens across workers.
    token_secret: str = Field(default_factory=_random_secret)
    verification_ttl_seconds: int = 600

    @field_validator("token_secret")
    @classmethod
    def _blank_means_random(cls, value: str) -> str:
        return value.strip() or _random_secret()


@lru_cache
def get_settings() -> Settings:
    return Settings()
