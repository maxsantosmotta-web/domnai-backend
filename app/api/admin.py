from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_CREDITS = 100000


def _grant_admin_access(user_id: str) -> dict:
    with session_scope() as db:
        existing_admin = db.scalar(
            select(BillingAccount).where(BillingAccount.plan_credits >= ADMIN_CREDITS)
        )

        if existing_admin is not None and existing_admin.user_id != user_id:
            raise HTTPException(status_code=403, detail="A conta administrativa já foi definida.")

        account = db.get(BillingAccount, user_id)
        if account is None:
            account = BillingAccount(user_id=user_id)
            db.add(account)
            db.flush()

        previous_total = account.plan_credits + account.extra_credits
        account.plan = "premium"
        account.subscription_status = "active"
        account.plan_credits = max(account.plan_credits, ADMIN_CREDITS)
        account.current_period_end = None

        if previous_total < ADMIN_CREDITS:
            db.add(CreditTransaction(
                user_id=user_id,
                kind="admin_credit",
                amount=ADMIN_CREDITS - previous_total,
                plan_balance=account.plan_credits,
                extra_balance=account.extra_credits,
                description="Créditos administrativos do proprietário",
            ))

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
    return _grant_admin_access(user_id)
