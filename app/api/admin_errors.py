import re
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

SEVERITY_PRIORITY = {"critical": 0, "error": 1, "warning": 2}


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


def _canonical_message(title: str, message: str) -> str:
    """Remove valores variáveis sem alterar os registros originais do banco."""
    value = " ".join(str(message or "").split()).casefold()
    title_value = " ".join(str(title or "").split()).casefold()

    if "uniqueviolation" in value or "duplicate key value" in value:
        constraint = re.search(r'unique constraint ["\']([^"\']+)["\']', value)
        key_name = re.search(r"key\s*\(([^)]+)\)\s*=", value)
        return "|".join((
            "unique-violation",
            constraint.group(1) if constraint else "",
            key_name.group(1) if key_name else "",
        ))

    value = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        "<uuid>",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\b0x[0-9a-f]+\b", "<hex>", value, flags=re.IGNORECASE)
    value = re.sub(r"\breq[_-][a-z0-9_-]+\b", "<request>", value, flags=re.IGNORECASE)
    value = re.sub(r"key\s*\(([^)]+)\)\s*=\s*\([^)]+\)", r"key(\1)=(<value>)", value)
    value = re.sub(r"\b\d{6,}\b", "<number>", value)
    return f"{title_value}|{value}"


def _group_key(event: dict) -> tuple[str, str, str, str, str, str]:
    return (
        str(event.get("module") or "").strip().casefold(),
        str(event.get("title") or "").strip().casefold(),
        str(event.get("source") or "").strip().casefold(),
        str(event.get("path") or "").strip().casefold(),
        str(event.get("method") or "").strip().upper(),
        _canonical_message(event.get("title") or "", event.get("message") or ""),
    )


def _merge_events(events: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str, str, str, str], dict] = {}

    for event in events:
        key = _group_key(event)
        current = grouped.get(key)
        if current is None:
            grouped[key] = dict(event)
            continue

        current["occurrences"] += event["occurrences"]

        first_seen = [
            value for value in (current.get("first_seen_at"), event.get("first_seen_at"))
            if value is not None
        ]
        last_seen = [
            value for value in (current.get("last_seen_at"), event.get("last_seen_at"))
            if value is not None
        ]
        current["first_seen_at"] = min(first_seen) if first_seen else None
        current["last_seen_at"] = max(last_seen) if last_seen else None

        # Um grupo só é resolvido quando todas as ocorrências equivalentes foram resolvidas.
        if current.get("resolved_at") is None or event.get("resolved_at") is None:
            current["resolved_at"] = None
        else:
            current["resolved_at"] = max(current["resolved_at"], event["resolved_at"])

        current_severity = current.get("severity") if current.get("severity") in SEVERITY_PRIORITY else "error"
        event_severity = event.get("severity") if event.get("severity") in SEVERITY_PRIORITY else "error"
        if SEVERITY_PRIORITY[event_severity] < SEVERITY_PRIORITY[current_severity]:
            current["severity"] = event_severity

        if (event.get("last_seen_at") or datetime.min.replace(tzinfo=timezone.utc)) >= (
            current.get("last_seen_at") or datetime.min.replace(tzinfo=timezone.utc)
        ):
            current["message"] = event["message"]
            current["id"] = event["id"]

    return list(grouped.values())


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

    merged_events = _merge_events(events)
    items = []
    affected_module_names = set()
    total_occurrences = 0
    status_counts = {"active": 0, "stable": 0, "resolved": 0}
    active_severity_counts = {"critical": 0, "error": 0, "warning": 0}

    for event in merged_events:
        status = _status(event, now)
        severity = event["severity"] if event["severity"] in active_severity_counts else "error"
        if status in {"active", "stable"} and event.get("module"):
            affected_module_names.add(event["module"])
        total_occurrences += event["occurrences"]
        status_counts[status] += 1
        if status == "active":
            active_severity_counts[severity] += 1
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

    status_priority = {"active": 0, "stable": 1, "resolved": 2}
    items.sort(
        key=lambda item: (
            status_priority.get(item["status"], 9),
            SEVERITY_PRIORITY.get(item["severity"], 9),
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
            "criticalGroups": active_severity_counts["critical"],
            "warningGroups": active_severity_counts["warning"],
            "affectedModules": len(affected_module_names),
            "totalOccurrences": total_occurrences,
            "totalGroups": len(items),
        },
        "generatedAt": now.isoformat(),
        "source": "operational_events",
    }
