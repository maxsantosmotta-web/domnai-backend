import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.orm.session import sessionmaker as SessionMaker

Base = declarative_base()


def get_database_url() -> str | None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return None

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)

    return database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine | None:
    database_url = get_database_url()

    if not database_url:
        return None

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> SessionMaker | None:
    engine = get_engine()

    if engine is None:
        return None

    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def is_database_configured() -> bool:
    return get_database_url() is not None and get_engine() is not None and get_session_factory() is not None


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session_factory = get_session_factory()

    if session_factory is None:
        raise RuntimeError("DATABASE_URL não configurada no ambiente.")

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
