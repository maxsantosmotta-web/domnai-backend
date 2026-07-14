from sqlalchemy import select

from app.models import AuditEvent

ALLOWED_CATEGORIES = {"plan", "payment", "credits", "pdf"}
ALLOWED_RESULTS = {"success", "failed", "canceled"}


def record_audit_event(
    db,
    *,
    user_id: str,
    category: str,
    module: str,
    action: str,
    description: str,
    result: str = "success",
    source: str = "system",
    source_key: str | None = None,
) -> AuditEvent | None:
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        return None

    normalized_category = category if category in ALLOWED_CATEGORIES else "payment"
    normalized_result = result if result in ALLOWED_RESULTS else "success"
    normalized_source_key = str(source_key or "").strip()[:255] or None

    if normalized_source_key:
        existing = db.scalar(
            select(AuditEvent.id).where(AuditEvent.source_key == normalized_source_key)
        )
        if existing:
            return None

    event = AuditEvent(
        user_id=normalized_user_id,
        category=normalized_category,
        module=str(module or "Plataforma").strip()[:80],
        action=str(action or "event").strip()[:80],
        description=str(description or "Evento registrado.").strip()[:500],
        result=normalized_result,
        source=str(source or "system").strip()[:40],
        source_key=normalized_source_key,
    )
    db.add(event)
    db.flush()
    return event
