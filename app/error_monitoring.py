from datetime import datetime, timezone
from hashlib import sha256
import logging

from sqlalchemy import select

from app.database import session_scope
from app.models import OperationalEvent

logger = logging.getLogger(__name__)

MODULE_PREFIXES = (
    ("/api/admin/users", "Usuários"),
    ("/api/admin/billing", "Faturamento"),
    ("/api/billing", "Faturamento"),
    ("/api/auth", "Autenticação"),
    ("/api/chat", "Chat"),
    ("/api/profile", "Perfil"),
    ("/api/library", "Biblioteca"),
    ("/api/reports", "Relatórios"),
    ("/api/feedback", "Feedbacks"),
    ("/api/database", "Banco de dados"),
    ("/health", "Saúde operacional"),
)


def module_from_path(path: str) -> str:
    normalized = str(path or "").strip()
    for prefix, module in MODULE_PREFIXES:
        if normalized.startswith(prefix):
            return module
    return "Plataforma"


def _fingerprint(module: str, severity: str, title: str, message: str, path: str) -> str:
    raw = "|".join((module, severity, title, message[:220], path))
    return sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def record_operational_event(
    *,
    module: str,
    severity: str,
    title: str,
    message: str,
    source: str = "backend",
    path: str = "",
    method: str = "",
) -> None:
    now = datetime.now(timezone.utc)
    normalized_message = str(message or "Falha sem detalhes.").strip()[:4000]
    normalized_title = str(title or "Falha operacional").strip()[:160]
    normalized_module = str(module or "Plataforma").strip()[:80]
    normalized_severity = severity if severity in {"critical", "error", "warning"} else "error"
    fingerprint = _fingerprint(
        normalized_module,
        normalized_severity,
        normalized_title,
        normalized_message,
        str(path or "")[:255],
    )

    try:
        with session_scope() as db:
            event = db.scalar(
                select(OperationalEvent).where(OperationalEvent.fingerprint == fingerprint)
            )
            if event is None:
                db.add(OperationalEvent(
                    fingerprint=fingerprint,
                    module=normalized_module,
                    severity=normalized_severity,
                    title=normalized_title,
                    message=normalized_message,
                    source=str(source or "backend")[:32],
                    path=str(path or "")[:255],
                    method=str(method or "")[:12],
                    occurrences=1,
                    first_seen_at=now,
                    last_seen_at=now,
                    resolved_at=None,
                ))
                return

            event.occurrences = int(event.occurrences or 0) + 1
            event.message = normalized_message
            event.last_seen_at = now
            event.resolved_at = None
            event.source = str(source or event.source or "backend")[:32]
            event.path = str(path or event.path or "")[:255]
            event.method = str(method or event.method or "")[:12]
    except Exception as exc:
        logger.warning("Falha ao registrar evento operacional: %s", type(exc).__name__)
