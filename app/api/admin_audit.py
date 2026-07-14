from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import AuditEvent, UserProfile

router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit"])

CATEGORY_LABELS = {
    "plan": "Planos",
    "payment": "Pagamentos",
    "credits": "Créditos",
    "pdf": "PDFs concluídos",
}

ACTION_LABELS = {
    "plan_selected": "Plano escolhido",
    "plan_changed": "Plano alterado",
    "payment_approved": "Pagamento aprovado",
    "payment_failed": "Pagamento recusado",
    "subscription_canceled": "Assinatura cancelada",
    "credits_added": "Créditos adicionados",
    "credits_consumed": "Créditos consumidos",
    "pdf_delivered": "PDF concluído pelo chat",
}

RESULT_LABELS = {
    "success": "Concluído",
    "failed": "Recusado",
    "canceled": "Cancelado",
}

FILTER_ACTIONS = {
    "plan_change": ("plan_selected", "plan_changed"),
    "payment_approved": ("payment_approved",),
    "payment_failed": ("payment_failed",),
    "subscription_canceled": ("subscription_canceled",),
    "credits_added": ("credits_added",),
    "credits_consumed": ("credits_consumed",),
    "pdf_delivered": ("pdf_delivered",),
}


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


def _action_condition(action_filter: str):
    actions = FILTER_ACTIONS.get(action_filter)
    if not actions:
        return None
    if len(actions) == 1:
        return AuditEvent.action == actions[0]
    return or_(*(AuditEvent.action == action for action in actions))


@router.get("")
def admin_audit_overview(
    action: str = Query(default="all"),
    limit: int = Query(default=10, ge=1, le=100),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    normalized_action = action if action in FILTER_ACTIONS else "all"
    action_condition = _action_condition(normalized_action)

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
            )
        ).one()

        query = (
            select(AuditEvent, UserProfile.full_name)
            .outerjoin(UserProfile, UserProfile.user_id == AuditEvent.user_id)
            .order_by(AuditEvent.created_at.desc())
        )
        count_query = select(func.count(AuditEvent.id))

        if action_condition is not None:
            query = query.where(action_condition)
            count_query = count_query.where(action_condition)

        rows = db.execute(query.limit(limit)).all()
        filtered_total = db.scalar(count_query)

        items = [{
            "id": event.id,
            "userId": event.user_id,
            "userName": (full_name or "Usuário DomnAI").strip(),
            "category": event.category,
            "categoryLabel": CATEGORY_LABELS.get(event.category, event.category),
            "module": event.module,
            "action": event.action,
            "actionLabel": ACTION_LABELS.get(event.action, event.action),
            "description": event.description,
            "result": event.result,
            "resultLabel": RESULT_LABELS.get(event.result, event.result),
            "source": event.source,
            "createdAt": event.created_at.isoformat(),
        } for event, full_name in rows]

    return {
        "items": items,
        "total": int(filtered_total or 0),
        "summary": {
            "planChanges": int(summary_row.plan_changes or 0),
            "paymentsApproved": int(summary_row.payments_approved or 0),
            "paymentsFailed": int(summary_row.payments_failed or 0),
            "subscriptionsCanceled": int(summary_row.subscriptions_canceled or 0),
            "creditsAdded": int(summary_row.credits_added or 0),
            "creditsConsumed": int(summary_row.credits_consumed or 0),
            "pdfsDelivered": int(summary_row.pdfs_delivered or 0),
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
