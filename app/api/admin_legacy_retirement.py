from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.domnai_core.cutover import ControlledCutoverSettings
from app.domnai_core.cutover_runtime import get_cutover_metric_store
from app.domnai_core.retirement_readiness import evaluate_legacy_retirement

router = APIRouter(prefix="/api/admin/legacy-retirement", tags=["admin-legacy-retirement"])


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


@router.get("")
def legacy_retirement_overview(
    limit: int = Query(default=5000, ge=1, le=5000),
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
    report = evaluate_legacy_retirement(
        summary=summary,
        cutover_enabled=settings.enabled,
        traffic_percent=settings.traffic_percent,
        fallback_enabled=settings.fallback_enabled,
    )
    return {
        "ready": report.ready,
        "report": report.as_dict(),
        "configurationError": config_error,
        "requiredSequence": [
            "Ativar o corte gradualmente no Railway.",
            "Chegar a 100% mantendo fallback ativo.",
            "Registrar DOMNAI_FULL_CUTOVER_STARTED_AT em ISO-8601.",
            "Manter estabilidade por pelo menos 24 horas e 500 amostras.",
            "Confirmar explicitamente com DOMNAI_LEGACY_RETIREMENT_CONFIRMED=true.",
            "Somente depois abrir o PR que remove o legado.",
        ],
        "rollback": "Defina DOMNAI_CUTOVER_ENABLED=false e reinicie o serviço.",
        "source": "domnai_cutover_metrics",
    }
