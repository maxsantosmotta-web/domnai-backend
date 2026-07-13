from fastapi import APIRouter, Depends

from app.auth import require_authenticated_user
from app.config import settings
from app.database import Base, get_database_url, get_engine, is_database_configured
from app.services import count_saved_analyses

router = APIRouter(prefix="/api/database", tags=["database"])


def run_database_initialization():
    engine = get_engine()

    if not is_database_configured() or engine is None:
        return {
            "status": "error",
            "message": "DATABASE_URL não configurada no ambiente do backend.",
            "databaseUrlConfigured": bool(get_database_url()),
        }

    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    return {
        "status": "ok",
        "message": "Tabelas iniciais criadas ou já existentes.",
        "tables": sorted(Base.metadata.tables.keys()),
    }


@router.get("/env-check")
def database_env_check(_session: dict = Depends(require_authenticated_user)):
    return {
        "status": "ok",
        "appName": settings.app_name,
        "environment": settings.environment,
        "databaseUrlConfigured": bool(get_database_url()),
    }


@router.get("/status")
def database_status(_session: dict = Depends(require_authenticated_user)):
    configured = is_database_configured()

    return {
        "status": "ok" if configured else "not_configured",
        "databaseConfigured": configured,
        "databaseUrlConfigured": bool(get_database_url()),
        "savedAnalyses": count_saved_analyses() if configured else None,
    }


@router.post("/init")
def initialize_database(_session: dict = Depends(require_authenticated_user)):
    return run_database_initialization()
