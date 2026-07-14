from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import OperationalEvent

router = APIRouter(prefix="/api/admin/errors", tags=["admin-errors"])

SEVERITY_LABELS = {
    "critical": "Crítico",
    "error": "Erro",
    "warning": "Alerta",
}

STATUS_LABELS = {
    "active": "Ativo",
    "stable": "Estabilizado",
    "resolved": "Resolvido",
}


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    normalized = _normalize_datetime(value)
    return normalized.isoformat() if normalized else None


def _status(event: dict, now: datetime) -> str:
    resolved_at = _normalize_datetime(event.get("resolved_at"))
    last_seen_at = _normalize_datetime(event.get("last_seen_at"))
    if resolved_at is not None:
        return "resolved"
    if last_seen_at is None:
        return "resolved"
    if last_seen_at >= now - timedelta(minutes=30):
        return "active"
    if last_seen_at >= now - timedelta(days=7):
        return "stable"
    return "resolved"


@router.get("")
def admin_errors_overview(
    limit: int = Query(default=500, ge=1, le=2000),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    now = datetime.now(timezone.utc)

    with session_scope() as db:
        rows = db.scalars(
            select(OperationalEvent)
            .order_by(OperationalEvent.last_seen_at.desc())
            .limit(limit)
        ).all()
        events = [{
            "id": item.id,
            "module": item.module,
            "severity": item.severity,
            "title": item.title,
            "message": item.message,
            "source": item.source,
            "path": item.path,
            "method": item.method,
            "occurrences": int(item.occurrences or 0),
            "first_seen_at": _normalize_datetime(item.first_seen_at),
            "last_seen_at": _normalize_datetime(item.last_seen_at),
            "resolved_at": _normalize_datetime(item.resolved_at),
        } for item in rows]

    items = []
    module_names = set()
    total_occurrences = 0
    status_counts = {"active": 0, "stable": 0, "resolved": 0}
    severity_counts = {"critical": 0, "error": 0, "warning": 0}

    for event in events:
        status = _status(event, now)
        severity = event["severity"] if event["severity"] in severity_counts else "error"
        module_names.add(event["module"])
        total_occurrences += event["occurrences"]
        status_counts[status] += 1
        severity_counts[severity] += 1
        items.append({
            "id": event["id"],
            "module": event["module"],
            "severity": severity,
            "severityLabel": SEVERITY_LABELS[severity],
            "status": status,
            "statusLabel": STATUS_LABELS[status],
            "title": event["title"],
            "message": event["message"],
            "source": event["source"],
            "path": event["path"],
            "method": event["method"],
            "occurrences": event["occurrences"],
            "firstSeenAt": _iso(event["first_seen_at"]),
            "lastSeenAt": _iso(event["last_seen_at"]),
        })

    severity_priority = {"critical": 0, "error": 1, "warning": 2}
    status_priority = {"active": 0, "stable": 1, "resolved": 2}
    items.sort(
        key=lambda item: (
            status_priority.get(item["status"], 9),
            severity_priority.get(item["severity"], 9),
            item.get("lastSeenAt") or "",
        ),
        reverse=False,
    )

    return {
        "items": items,
        "summary": {
            "activeGroups": status_counts["active"],
            "stableGroups": status_counts["stable"],
            "resolvedGroups": status_counts["resolved"],
            "criticalGroups": severity_counts["critical"],
            "warningGroups": severity_counts["warning"],
            "affectedModules": len(module_names),
            "totalOccurrences": total_occurrences,
            "totalGroups": len(items),
        },
        "generatedAt": now.isoformat(),
        "source": "operational_events",
    }
