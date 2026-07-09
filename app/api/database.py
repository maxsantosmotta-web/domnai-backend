from fastapi import APIRouter

from app.database import Base, engine, is_database_configured
from app.services import count_saved_analyses

router = APIRouter(prefix="/api/database", tags=["database"])


@router.get("/status")
def database_status():
    configured = is_database_configured()

    return {
        "status": "ok" if configured else "not_configured",
        "databaseConfigured": configured,
        "savedAnalyses": count_saved_analyses() if configured else None,
    }


@router.post("/init")
def initialize_database():
    if not is_database_configured():
        return {
            "status": "error",
            "message": "DATABASE_URL não configurada no ambiente do backend.",
        }

    Base.metadata.create_all(bind=engine)

    return {
        "status": "ok",
        "message": "Tabelas iniciais criadas ou já existentes.",
    }
