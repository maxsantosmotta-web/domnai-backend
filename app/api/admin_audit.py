from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import AuditEvent

router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit"])


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


@router.get("")
def admin_audit_overview(
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)

    with session_scope() as db:
        summary_row = db.execute(
            select(
                func.sum(
                    case((AuditEvent.action.in_(("plan_selected", "plan_changed")), 1), else_=0)
                ).label("plan_changes"),
                func.sum(case((AuditEvent.action == "payment_approved", 1), else_=0)).label("payments_approved"),
                func.sum(case((AuditEvent.action == "payment_failed", 1), else_=0)).label("payments_failed"),
                func.sum(
                    case((AuditEvent.action == "subscription_canceled", 1), else_=0)
                ).label("subscriptions_canceled"),
                func.sum(case((AuditEvent.action == "credits_added", 1), else_=0)).label("credits_added"),
                func.sum(
                    case((AuditEvent.action == "credits_consumed", 1), else_=0)
                ).label("credits_consumed"),
                func.sum(case((AuditEvent.action == "pdf_delivered", 1), else_=0)).label("pdfs_delivered"),
                func.sum(
                    case((AuditEvent.action == "spreadsheet_delivered", 1), else_=0)
                ).label("spreadsheets_delivered"),
                func.sum(
                    case((AuditEvent.action == "conversation_completed", 1), else_=0)
                ).label("conversations_completed"),
            )
        ).one()

    return {
        "summary": {
            "planChanges": int(summary_row.plan_changes or 0),
            "paymentsApproved": int(summary_row.payments_approved or 0),
            "paymentsFailed": int(summary_row.payments_failed or 0),
            "subscriptionsCanceled": int(summary_row.subscriptions_canceled or 0),
            "creditsAdded": int(summary_row.credits_added or 0),
            "creditsConsumed": int(summary_row.credits_consumed or 0),
            "pdfsDelivered": int(summary_row.pdfs_delivered or 0),
            "spreadsheetsDelivered": int(summary_row.spreadsheets_delivered or 0),
            "conversationsCompleted": int(summary_row.conversations_completed or 0),
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
