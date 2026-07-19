from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from functools import lru_cache

from sqlalchemy import text

from app.database import session_scope
from app.domnai_core.cutover import ControlledCutoverRouter, ControlledCutoverSettings, RoutedBrainResult
from app.domnai_core.shadow_results import PostgresShadowResultStore, evaluate_shadow_results
from app.services.metered_brain import MeteredBrainResult

logger = logging.getLogger("domnai.cutover_runtime")


@dataclass(frozen=True, slots=True)
class CutoverMetric:
    request_id: str
    route: str
    selected_percent: int
    fallback_used: bool
    fallback_reason: str
    duration_ms: int

    def as_dict(self) -> dict:
        return asdict(self)


class PostgresCutoverMetricStore:
    TABLE = "domnai_cutover_metrics"

    def ensure_schema(self) -> None:
        with session_scope() as db:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id BIGSERIAL PRIMARY KEY,
                    request_id VARCHAR(128) NOT NULL,
                    route VARCHAR(40) NOT NULL,
                    selected_percent INTEGER NOT NULL,
                    fallback_used BOOLEAN NOT NULL,
                    fallback_reason VARCHAR(200) NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            db.execute(text(
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_created ON {self.TABLE} (created_at DESC)"
            ))

    def save(self, metric: CutoverMetric) -> None:
        self.ensure_schema()
        with session_scope() as db:
            db.execute(text(f"""
                INSERT INTO {self.TABLE} (
                    request_id, route, selected_percent, fallback_used,
                    fallback_reason, duration_ms
                ) VALUES (
                    :request_id, :route, :selected_percent, :fallback_used,
                    :fallback_reason, :duration_ms
                )
            """), metric.as_dict())

    def summary(self, *, limit: int = 1000) -> dict:
        self.ensure_schema()
        safe_limit = max(1, min(int(limit), 5000))
        with session_scope() as db:
            rows = db.execute(text(f"""
                SELECT route, fallback_used, fallback_reason, duration_ms, created_at
                FROM {self.TABLE}
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": safe_limit}).mappings().all()
        total = len(rows)
        new_core = sum(1 for row in rows if row["route"] == "new-core")
        legacy = sum(1 for row in rows if row["route"] == "legacy")
        fallbacks = sum(1 for row in rows if row["fallback_used"])
        average_duration = round(sum(int(row["duration_ms"] or 0) for row in rows) / total, 2) if total else 0.0
        reasons: dict[str, int] = {}
        for row in rows:
            reason = str(row["fallback_reason"] or "")
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
        return {
            "sampleCount": total,
            "newCoreResponses": new_core,
            "legacyResponses": legacy,
            "fallbackCount": fallbacks,
            "fallbackRate": round(fallbacks / total, 4) if total else 0.0,
            "averageDurationMs": average_duration,
            "fallbackReasons": reasons,
        }


@lru_cache(maxsize=1)
def get_cutover_metric_store() -> PostgresCutoverMetricStore:
    return PostgresCutoverMetricStore()


def shadow_is_approved() -> bool:
    try:
        store = PostgresShadowResultStore()
        store.ensure_schema()
        return evaluate_shadow_results(store.recent(limit=1000)).approved
    except Exception:
        logger.exception("Não foi possível consultar a aprovação shadow; corte bloqueado.")
        return False


def route_brain_request(
    *,
    request_id: str,
    user_id: str,
    conversation_id: str,
    message: str,
    operation: str | None,
    history: list[dict],
    memory: dict | None,
    attachments: list[dict],
    local_artifact_followup: bool,
    legacy,
) -> RoutedBrainResult:
    """Ponto único de corte. Configuração é relida por tarefa para rollback imediato."""
    try:
        settings = ControlledCutoverSettings.from_env()
    except Exception:
        logger.exception("Configuração inválida de cutover; usando legado.")
        return RoutedBrainResult(legacy(), route="legacy", fallback_used=True, fallback_reason="invalid_config")

    if not settings.enabled:
        return RoutedBrainResult(legacy(), route="legacy", fallback_reason="disabled")

    started = time.perf_counter()
    approved = shadow_is_approved() if settings.require_shadow_approval else True
    try:
        routed = ControlledCutoverRouter(settings).route(
            request_id=request_id,
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            operation=operation,
            history=history,
            memory=memory,
            attachments=attachments,
            local_artifact_followup=local_artifact_followup,
            shadow_approved=approved,
            legacy=legacy,
        )
    except Exception:
        logger.exception("Falha sem fallback no corte controlado.")
        raise

    try:
        get_cutover_metric_store().save(CutoverMetric(
            request_id=request_id,
            route=routed.route,
            selected_percent=settings.traffic_percent,
            fallback_used=routed.fallback_used,
            fallback_reason=routed.fallback_reason,
            duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
        ))
    except Exception:
        logger.exception("Falha isolada ao registrar métrica de cutover.")
    return routed
