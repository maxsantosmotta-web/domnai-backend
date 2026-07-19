from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.domnai_core.cutover import ControlledCutoverSettings
from app.domnai_core.cutover_runtime import get_cutover_metric_store, shadow_is_approved

router = APIRouter(prefix="/api/admin/cutover", tags=["admin-cutover"])


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


@router.get("")
def cutover_overview(
    limit: int = Query(default=1000, ge=1, le=5000),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    try:
        settings = ControlledCutoverSettings.from_env()
        config_error = None
    except Exception as exc:
        settings = ControlledCutoverSettings()
        config_error = type(exc).__name__
    summary = get_cutover_metric_store().summary(limit=limit)
    shadow_approved = shadow_is_approved()
    return {
        "enabled": settings.enabled,
        "trafficPercent": settings.traffic_percent,
        "fallbackEnabled": settings.fallback_enabled,
        "requireShadowApproval": settings.require_shadow_approval,
        "shadowApproved": shadow_approved,
        "configurationError": config_error,
        "rollback": "Defina DOMNAI_CUTOVER_ENABLED=false e reinicie o serviço.",
        "summary": summary,
        "readyForFullCutover": bool(
            shadow_approved
            and summary["sampleCount"] >= 100
            and summary["fallbackRate"] <= 0.02
        ),
        "source": "domnai_cutover_metrics",
    }
