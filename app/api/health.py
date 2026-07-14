import os
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import get_engine, is_database_configured

router = APIRouter(tags=["health"])


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 1)


def _database_check() -> dict:
    started_at = perf_counter()
    if not is_database_configured():
        return {"configured": False, "reachable": False, "latencyMs": None}

    engine = get_engine()
    if engine is None:
        return {"configured": True, "reachable": False, "latencyMs": None}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "configured": True,
            "reachable": True,
            "latencyMs": _elapsed_ms(started_at),
        }
    except Exception:
        return {
            "configured": True,
            "reachable": False,
            "latencyMs": _elapsed_ms(started_at),
        }


@router.get("/health")
def health():
    started_at = perf_counter()
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
        "statusLabel": "Operacional" if essential_ready else "Atenção necessária",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "serverCheckMs": _elapsed_ms(started_at),
        "dependencies": dependencies,
    }
