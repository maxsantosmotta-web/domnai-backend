import os

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import get_engine, is_database_configured

router = APIRouter(tags=["health"])


def _database_check() -> dict:
    if not is_database_configured():
        return {"configured": False, "reachable": False}

    engine = get_engine()
    if engine is None:
        return {"configured": True, "reachable": False}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"configured": True, "reachable": True}
    except Exception:
        return {"configured": True, "reachable": False}


@router.get("/health")
def health():
    database = _database_check()
    dependencies = {
        "database": database,
        "openaiConfigured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "clerkConfigured": bool(settings.clerk_publishable_key),
        "stripeConfigured": bool(os.getenv("STRIPE_SECRET_KEY", "").strip()),
        "pdfGeneratorAvailable": True,
    }

    essential_ready = (
        database["reachable"]
        and dependencies["openaiConfigured"]
        and dependencies["clerkConfigured"]
    )

    return {
        "status": "ok" if essential_ready else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "dependencies": dependencies,
    }
