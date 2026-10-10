from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def normalize_db_url(url: str) -> str:
    """Force the psycopg 3 driver, so plain Supabase URLs work as-is."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str) -> Engine:
    # prepare_threshold=None: Supabase's transaction pooler can't hold server-side prepared statements.
    return create_engine(normalize_db_url(url), pool_pre_ping=True, connect_args={"prepare_threshold": None})


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
