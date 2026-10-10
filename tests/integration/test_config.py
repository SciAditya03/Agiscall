import pytest

from app.config import Settings
from app.db import normalize_db_url


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql://u:p@h:5432/d",
        "postgres://u:p@h:5432/d",
        "postgresql+psycopg://u:p@h:5432/d",
    ],
)
def test_normalize_db_url_always_uses_psycopg3(raw):
    # Supabase hands out postgresql:// URLs; SQLAlchemy would pick psycopg2 for those.
    assert normalize_db_url(raw) == "postgresql+psycopg://u:p@h:5432/d"


def test_settings_come_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://x:y@z/db")
    monkeypatch.setenv("TOKEN_SECRET", "s3cret")
    monkeypatch.setenv("VERIFICATION_TTL_SECONDS", "30")

    settings = Settings()

    assert settings.database_url == "postgres://x:y@z/db"
    assert settings.token_secret == "s3cret"
    assert settings.verification_ttl_seconds == 30


def test_settings_defaults(monkeypatch):
    for name in ("DATABASE_URL", "TOKEN_SECRET", "VERIFICATION_TTL_SECONDS"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.verification_ttl_seconds == 600
    assert settings.database_url.endswith("@localhost:5433/aegiscall")


def test_token_secret_defaults_to_a_random_value(monkeypatch):
    # A committed default secret would let anyone who reads the repo forge verification tokens.
    monkeypatch.delenv("TOKEN_SECRET", raising=False)
    first, second = Settings(_env_file=None), Settings(_env_file=None)
    assert len(first.token_secret) >= 32
    assert first.token_secret != second.token_secret


def test_blank_token_secret_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "  ")
    assert len(Settings(_env_file=None).token_secret) >= 32
