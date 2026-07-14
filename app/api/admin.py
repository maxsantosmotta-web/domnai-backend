from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_CREDITS = 100000
ADMIN_TRANSACTION_KIND = "admin_credit"
ADMIN_TRANSACTION_DESCRIPTION = "Créditos administrativos do proprietário"


def _has_persisted_admin_access(user_id: str) -> bool:
    with session_scope() as db:
        account = db.get(BillingAccount, user_id)
        if account is None:
            return False

        admin_marker = db.scalar(
            select(CreditTransaction.id)
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.kind == ADMIN_TRANSACTION_KIND,
                CreditTransaction.description == ADMIN_TRANSACTION_DESCRIPTION,
            )
            .limit(1)
        )

        return bool(
            admin_marker
            and account.plan == "premium"
            and account.subscription_status == "active"
            and account.plan_credits >= ADMIN_CREDITS
        )


def owner_access_status(session: dict) -> dict:
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    is_admin = _has_persisted_admin_access(user_id)
    return {
        "role": "admin" if is_admin else "user",
        "isAdmin": is_admin,
    }


def _grant_admin_access(user_id: str) -> dict:
    with session_scope() as db:
        account = db.get(BillingAccount, user_id)
        if account is None:
            raise HTTPException(status_code=403, detail="Vínculo administrativo não encontrado.")

        marker = db.scalar(
            select(CreditTransaction.id)
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.kind == ADMIN_TRANSACTION_KIND,
                CreditTransaction.description == ADMIN_TRANSACTION_DESCRIPTION,
            )
            .limit(1)
        )
        if not marker:
            raise HTTPException(status_code=403, detail="Vínculo administrativo não encontrado.")

        account.plan = "premium"
        account.subscription_status = "active"
        account.plan_credits = max(account.plan_credits, ADMIN_CREDITS)
        account.current_period_end = None

        return {
            "status": "ok",
            "role": "admin",
            "plan": "premium",
            "premiumActive": True,
            "subscriptionStatus": "active",
            "planCredits": account.plan_credits,
            "extraCredits": account.extra_credits,
            "totalCredits": account.plan_credits + account.extra_credits,
        }


@router.post("/bootstrap")
def bootstrap_owner_admin(session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    if not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")

    return _grant_admin_access(user_id)
