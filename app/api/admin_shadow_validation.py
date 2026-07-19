from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.domnai_core.shadow_results import PostgresShadowResultStore, evaluate_shadow_results
from app.domnai_core.shadow_validation import ShadowValidationSettings

router = APIRouter(prefix="/api/admin/shadow-validation", tags=["admin-shadow-validation"])


def _require_admin(session: dict) -> str:
    from fastapi import HTTPException

    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


@router.get("")
def shadow_validation_overview(
    limit: int = Query(default=500, ge=1, le=1000),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    store = PostgresShadowResultStore()
    store.ensure_schema()
    comparisons = store.recent(limit=limit)
    report = evaluate_shadow_results(comparisons)
    try:
        settings = ShadowValidationSettings.from_env()
        configuration = {
            "enabled": settings.enabled,
            "samplePercent": settings.sample_percent,
            "timeoutSeconds": settings.timeout_seconds,
        }
    except Exception as exc:
        configuration = {
            "enabled": False,
            "samplePercent": 0,
            "timeoutSeconds": 0,
            "configurationError": type(exc).__name__,
        }
    return {
        "summary": report.as_dict(),
        "configuration": configuration,
        "criteria": {
            "minimumSamples": 100,
            "minimumSuccessRate": 0.98,
            "minimumNonEmptyRate": 0.99,
            "minimumAverageSimilarity": 0.35,
        },
        "items": [item.as_safe_dict() for item in comparisons],
        "privacy": {
            "rawPromptsStored": False,
            "rawResponsesStored": False,
        },
    }
