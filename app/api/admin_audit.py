from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select

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


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


@router.get("")
def admin_audit_overview(
    category: str = Query(default="all"),
    limit: int = Query(default=10, ge=1, le=100),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    normalized_category = category if category in CATEGORY_LABELS else "all"

    with session_scope() as db:
        summary_row = db.execute(
            select(
                func.count(AuditEvent.id).label("total"),
                func.sum(case((AuditEvent.category == "plan", 1), else_=0)).label("plans"),
                func.sum(case((AuditEvent.category == "payment", 1), else_=0)).label("payments"),
                func.sum(case((AuditEvent.category == "credits", 1), else_=0)).label("credits"),
                func.sum(case((AuditEvent.category == "pdf", 1), else_=0)).label("pdfs"),
            )
        ).one()

        query = (
            select(AuditEvent, UserProfile.full_name)
            .outerjoin(UserProfile, UserProfile.user_id == AuditEvent.user_id)
            .order_by(AuditEvent.created_at.desc())
        )
        if normalized_category != "all":
            query = query.where(AuditEvent.category == normalized_category)

        rows = db.execute(query.limit(limit)).all()
        filtered_total = db.scalar(
            select(func.count(AuditEvent.id)).where(
                True if normalized_category == "all" else AuditEvent.category == normalized_category
            )
        )

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
            "total": int(summary_row.total or 0),
            "plans": int(summary_row.plans or 0),
            "payments": int(summary_row.payments or 0),
            "credits": int(summary_row.credits or 0),
            "pdfs": int(summary_row.pdfs or 0),
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
