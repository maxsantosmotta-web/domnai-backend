import json
import os
from urllib import error, request

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction

router = APIRouter(prefix="/api/admin", tags=["admin"])

OWNER_EMAIL = "maxsantosmotta@gmail.com"
ADMIN_CREDITS = 100000


def _clerk_user_email(user_id: str) -> str:
    secret = os.getenv("CLERK_SECRET_KEY", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Clerk não configurado para validar o administrador.")

    req = request.Request(
        f"https://api.clerk.com/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {secret}", "Accept": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Não foi possível validar a conta no Clerk.") from exc

    primary_id = payload.get("primary_email_address_id")
    addresses = payload.get("email_addresses") or []
    primary = next((item for item in addresses if item.get("id") == primary_id), None)
    selected = primary or (addresses[0] if addresses else {})
    return str(selected.get("email_address", "")).strip().lower()


@router.post("/bootstrap")
def bootstrap_owner_admin(session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    email = _clerk_user_email(user_id)
    if email != OWNER_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")

    with session_scope() as db:
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
                description="Créditos administrativos de teste do proprietário",
            ))

        return {
            "status": "ok",
            "role": "admin",
            "email": email,
            "plan": "premium",
            "totalCredits": account.plan_credits + account.extra_credits,
        }
