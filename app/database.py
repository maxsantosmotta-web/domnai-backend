from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

engine = None
SessionLocal = None

if settings.database_url:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def is_database_configured() -> bool:
    return engine is not None and SessionLocal is not None


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if not is_database_configured():
        raise RuntimeError("DATABASE_URL não configurada no ambiente.")

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
