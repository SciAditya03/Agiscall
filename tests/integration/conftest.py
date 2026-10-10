"""Shared fixtures for the mock insurance API tests.

Fixtures that touch the database (`db`, `seeded`, `client`) need Postgres:
    docker compose up -d db
"""
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session, normalize_db_url
from app.main import create_app
from seed.seed import seed

SERVICE_DIR = Path(__file__).resolve().parents[2] / "backend" / "mock_insurance_api"
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/aegiscall_test"
)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    config = Config(str(SERVICE_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(config, "base")  # start from scratch so edited migrations are picked up
    command.upgrade(config, "head")
    engine = create_engine(normalize_db_url(TEST_DATABASE_URL))
    yield engine
    engine.dispose()


@pytest.fixture
def clean_engine(engine: Engine) -> Engine:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE operations, refund_requests, policies, customers RESTART IDENTITY CASCADE"))
    return engine


@pytest.fixture
def db(clean_engine: Engine) -> Iterator[Session]:
    with sessionmaker(bind=clean_engine)() as session:
        yield session


@pytest.fixture
def seeded(db: Session) -> Session:
    seed(db)
    return db


@pytest.fixture
def client(clean_engine: Engine) -> Iterator[TestClient]:
    app = create_app()
    factory = sessionmaker(bind=clean_engine, expire_on_commit=False)

    def override_get_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
