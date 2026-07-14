import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_authenticated_user
from app.config import settings
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_CREDITS = 100000
OWNER_EMAIL = "maxsantosmotta@gmail.com"


def _safe_clerk_error_code(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        errors = payload.get("errors") or []
        raw_code = str((errors[0] if errors else {}).get("code") or "unknown")
    except (ValueError, UnicodeDecodeError, AttributeError, IndexError):
        raw_code = "unknown"

    safe_code = "".join(
        character for character in raw_code
        if character.isalnum() or character in {"_", "-", "."}
    )
    return safe_code[:80] or "unknown"


def _clerk_user_email(user_id: str) -> str:
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Falha na validação do Clerk. Etapa: configuração. Código: secret_key_missing.",
        )

    request = Request(
        f"https://api.clerk.com/v1/users/{user_id}",
        headers={
            "Authorization": f"Bearer {settings.clerk_secret_key}",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_code = _safe_clerk_error_code(exc)
        public_status = 503 if exc.code >= 500 else 403
        raise HTTPException(
            status_code=public_status,
            detail=(
                "Falha na validação do Clerk. "
                f"Etapa: consulta do usuário. HTTP: {exc.code}. Código: {error_code}."
            ),
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=503,
            detail="Falha na validação do Clerk. Etapa: conexão. Código: network_error.",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=503,
            detail="Falha na validação do Clerk. Etapa: conexão. Código: timeout.",
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Falha na validação do Clerk. Etapa: leitura da resposta. Código: invalid_response.",
        ) from exc

    primary_id = payload.get("primary_email_address_id")
    addresses = payload.get("email_addresses") or []
    primary = next((item for item in addresses if item.get("id") == primary_id), None)
    if primary is None and addresses:
        primary = addresses[0]

    return str((primary or {}).get("email_address") or "").strip().lower()


def owner_access_status(session: dict) -> dict:
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    is_admin = _clerk_user_email(user_id) == OWNER_EMAIL
    return {
        "role": "admin" if is_admin else "user",
        "isAdmin": is_admin,
    }


def _grant_admin_access(user_id: str) -> dict:
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

    if _clerk_user_email(user_id) != OWNER_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")

    return _grant_admin_access(user_id)
