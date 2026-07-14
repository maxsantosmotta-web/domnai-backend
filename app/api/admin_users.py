from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.admin import (
    ADMIN_TRANSACTION_DESCRIPTION,
    ADMIN_TRANSACTION_KIND,
    _grant_admin_access,
    _has_persisted_admin_access,
)
from app.auth import require_authenticated_user
from app.config import settings
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction, UserProfile

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])
logger = logging.getLogger(__name__)

CLERK_USERS_URL = "https://api.clerk.com/v1/users"
CLERK_PAGE_SIZE = 100
MAX_CLERK_USERS = 5000


def _require_admin(session: dict) -> tuple[str, dict]:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id, _grant_admin_access(user_id)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clerk_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, str) and not value.strip().isdigit():
        try:
            return _normalize_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    try:
        numeric = int(value)
        if numeric > 10_000_000_000:
            numeric /= 1000
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _iso(value: datetime | None) -> str | None:
    normalized = _normalize_datetime(value)
    return normalized.isoformat() if normalized else None


def _primary_email(user: dict) -> str:
    addresses = user.get("email_addresses") or []
    primary_id = user.get("primary_email_address_id")
    for item in addresses:
        if item.get("id") == primary_id:
            return str(item.get("email_address") or "").strip().lower()
    if addresses:
        return str(addresses[0].get("email_address") or "").strip().lower()
    return ""


def _clerk_users() -> list[dict]:
    secret = str(settings.clerk_secret_key or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="CLERK_SECRET_KEY não configurada.")

    users: list[dict] = []
    offset = 0
    try:
        while offset < MAX_CLERK_USERS:
            query = urlencode({
                "limit": CLERK_PAGE_SIZE,
                "offset": offset,
                "order_by": "-created_at",
            })
            request = Request(
                f"{CLERK_USERS_URL}?{query}",
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "DomnAI-Admin/1.0",
                },
            )
            with urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))

            batch = payload if isinstance(payload, list) else payload.get("data", [])
            if not isinstance(batch, list):
                raise ValueError("Resposta inválida do Clerk.")
            users.extend(batch)
            if len(batch) < CLERK_PAGE_SIZE:
                break
            offset += len(batch)
    except HTTPError as exc:
        detail = "Não foi possível consultar os usuários no Clerk."
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            errors = payload.get("errors") if isinstance(payload, dict) else None
            if isinstance(errors, list) and errors:
                detail = errors[0].get("long_message") or errors[0].get("message") or detail
            elif isinstance(payload, dict):
                detail = payload.get("message") or detail
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail) from exc
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Não foi possível consultar os usuários no Clerk.") from exc

    return users[:MAX_CLERK_USERS]


def _resolved_plan(account: dict | None) -> str:
    raw_plan = str((account or {}).get("plan") or "").strip().lower()
    if raw_plan == "premium":
        return "premium"
    if raw_plan == "free":
        return "free"
    return "unselected"


def _plan_label(value: str) -> str:
    return {
        "premium": "Plano Premium",
        "free": "Plano Free",
        "unselected": "Sem plano",
    }.get(value, "Sem plano")


def _latest(*values: datetime | None) -> datetime | None:
    normalized = [_normalize_datetime(value) for value in values if value is not None]
    normalized = [value for value in normalized if value is not None]
    return max(normalized) if normalized else None


def _brain_insights(summary: dict) -> list[dict]:
    total = summary["totalUsers"]
    if total == 0:
        return [{
            "level": "info",
            "title": "Base ainda sem usuários",
            "message": "O IAttom Brain começará a analisar a base assim que houver cadastros ativos.",
        }]

    insights: list[dict] = []
    incomplete = total - summary["profileCompleted"]
    inactive = total - summary["activeLast7Days"]
    if incomplete:
        insights.append({
            "level": "attention",
            "title": "Cadastros incompletos",
            "message": f"{incomplete} usuário(s) ainda não concluíram o perfil obrigatório.",
        })
    if summary["unselectedUsers"]:
        insights.append({
            "level": "attention",
            "title": "Plano ainda não escolhido",
            "message": f"{summary['unselectedUsers']} usuário(s) estão sem Plano Free ou Plano Premium definido.",
        })
    if inactive:
        insights.append({
            "level": "info",
            "title": "Atividade recente",
            "message": f"{summary['activeLast7Days']} de {total} usuário(s) tiveram atividade nos últimos 7 dias.",
        })
    premium_rate = round((summary["premiumUsers"] / total) * 100, 1)
    insights.append({
        "level": "positive" if premium_rate >= 20 else "info",
        "title": "Conversão para Plano Premium",
        "message": f"{premium_rate:.1f}% da base está no Plano Premium.",
    })
    return insights[:4]


@router.get("")
def list_admin_users(
    limit: int = Query(default=500, ge=1, le=1000),
    session: dict = Depends(require_authenticated_user),
):
    admin_user_id, admin_state = _require_admin(session)
    warnings: list[str] = []

    clerk_available = True
    try:
        clerk_users = _clerk_users()
    except HTTPException as exc:
        clerk_available = False
        clerk_users = []
        warnings.append(f"Clerk: {exc.detail}")
        logger.warning("Módulo Usuários operando com fallback do banco: %s", exc.detail)

    clerk_by_id = {
        str(item.get("id") or "").strip(): item
        for item in clerk_users
        if str(item.get("id") or "").strip()
    }

    accounts: dict[str, dict] = {}
    profiles: dict[str, dict] = {}
    admin_ids: set[str] = {admin_user_id}
    credit_activity: dict[str, datetime] = {}

    try:
        with session_scope() as db:
            account_rows = db.scalars(select(BillingAccount)).all()
            profile_rows = db.scalars(select(UserProfile)).all()
            accounts = {
                item.user_id: {
                    "plan": str(item.plan or "unselected"),
                    "subscription_status": str(item.subscription_status or "inactive"),
                    "plan_credits": int(item.plan_credits or 0),
                    "extra_credits": int(item.extra_credits or 0),
                    "updated_at": _normalize_datetime(item.updated_at),
                }
                for item in account_rows
            }
            profiles = {
                item.user_id: {
                    "full_name": str(item.full_name or ""),
                    "completed": bool(item.completed),
                    "updated_at": _normalize_datetime(item.updated_at),
                }
                for item in profile_rows
            }
            admin_ids.update(
                str(value)
                for value in db.scalars(
                    select(CreditTransaction.user_id)
                    .where(
                        CreditTransaction.kind == ADMIN_TRANSACTION_KIND,
                        CreditTransaction.description == ADMIN_TRANSACTION_DESCRIPTION,
                    )
                    .distinct()
                ).all()
                if value
            )
            credit_activity = {
                str(user_id): _normalize_datetime(value)
                for user_id, value in db.execute(
                    select(CreditTransaction.user_id, func.max(CreditTransaction.created_at))
                    .group_by(CreditTransaction.user_id)
                ).all()
                if user_id and value is not None
            }
    except Exception as exc:
        logger.exception("Falha parcial no banco do módulo Usuários")
        warnings.append(f"Banco: {type(exc).__name__}")

    accounts.setdefault(admin_user_id, {
        "plan": str(admin_state.get("plan") or "premium"),
        "subscription_status": str(admin_state.get("subscriptionStatus") or "active"),
        "plan_credits": int(admin_state.get("planCredits") or 0),
        "extra_credits": int(admin_state.get("extraCredits") or 0),
        "updated_at": datetime.now(timezone.utc),
    })

    database_user_ids = set(accounts) | set(profiles) | set(credit_activity)
    if clerk_available:
        # Clerk é a fonte oficial de existência do usuário. Registros apagados
        # permanecem no banco apenas como histórico e não entram na tela.
        user_ids = set(clerk_by_id)
        user_ids.add(admin_user_id)
    else:
        # Somente quando o Clerk está indisponível o banco vira fallback.
        user_ids = database_user_ids | {admin_user_id}

    historical_excluded = database_user_ids - set(clerk_by_id) if clerk_available else set()
    now = datetime.now(timezone.utc)
    start_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    active_cutoff = now - timedelta(days=7)

    items: list[dict] = []
    growth_counts: defaultdict[str, int] = defaultdict(int)
    plan_counts = {"premium": 0, "free": 0, "unselected": 0}
    new_this_week = 0
    new_this_month = 0
    active_last_7_days = 0
    profile_completed = 0
    total_credits = 0

    for user_id in user_ids:
        clerk_user = clerk_by_id.get(user_id, {})
        profile = profiles.get(user_id, {})
        account = accounts.get(user_id, {})
        created_at = _clerk_datetime(clerk_user.get("created_at"))
        last_activity = _latest(
            _clerk_datetime(clerk_user.get("last_sign_in_at")),
            account.get("updated_at"),
            profile.get("updated_at"),
            credit_activity.get(user_id),
        )

        plan = _resolved_plan(account)
        if user_id == admin_user_id and plan == "unselected":
            bootstrap_plan = str(admin_state.get("plan") or "premium").strip().lower()
            plan = bootstrap_plan if bootstrap_plan in {"premium", "free"} else "premium"
        plan_counts[plan] += 1

        credits = int(account.get("plan_credits") or 0) + int(account.get("extra_credits") or 0)
        total_credits += credits
        completed = bool(profile.get("completed"))
        profile_completed += int(completed)
        if created_at and created_at >= start_week:
            new_this_week += 1
        if created_at and created_at >= start_month:
            new_this_month += 1
        if last_activity and last_activity >= active_cutoff:
            active_last_7_days += 1
        if created_at and created_at >= now - timedelta(days=29):
            growth_counts[created_at.date().isoformat()] += 1

        first_name = str(clerk_user.get("first_name") or "").strip()
        last_name = str(clerk_user.get("last_name") or "").strip()
        clerk_name = " ".join(part for part in (first_name, last_name) if part).strip()
        name = clerk_name or str(profile.get("full_name") or "") or "Usuário DomnAI"
        blocked = bool(clerk_user.get("banned") or clerk_user.get("locked"))
        has_clerk_record = bool(clerk_user)
        is_admin = user_id in admin_ids

        items.append({
            "id": user_id,
            "name": name,
            "email": _primary_email(clerk_user),
            "role": "admin" if is_admin else "user",
            "roleLabel": "Admin" if is_admin else "Usuário",
            "plan": plan,
            "planLabel": _plan_label(plan),
            "subscriptionStatus": str(account.get("subscription_status") or "inactive"),
            "planCredits": int(account.get("plan_credits") or 0),
            "extraCredits": int(account.get("extra_credits") or 0),
            "totalCredits": credits,
            "profileCompleted": completed,
            "accountStatus": "blocked" if blocked else ("active" if has_clerk_record else "fallback"),
            "accountStatusLabel": "Bloqueado" if blocked else ("Ativo" if has_clerk_record else "Fallback interno"),
            "createdAt": _iso(created_at),
            "lastActivityAt": _iso(last_activity),
        })

    items.sort(
        key=lambda item: (item.get("createdAt") or "", item.get("lastActivityAt") or ""),
        reverse=True,
    )
    items = items[:limit]

    growth = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date()
        key = day.isoformat()
        growth.append({"date": key, "label": day.strftime("%d/%m"), "count": growth_counts.get(key, 0)})

    summary = {
        "totalUsers": len(user_ids),
        "newThisWeek": new_this_week,
        "newThisMonth": new_this_month,
        "profileCompleted": profile_completed,
        "premiumUsers": plan_counts["premium"],
        "freeUsers": plan_counts["free"],
        "unselectedUsers": plan_counts["unselected"],
        "adminUsers": len(admin_ids.intersection(user_ids)),
        "activeLast7Days": active_last_7_days,
        "totalCredits": total_credits,
    }

    admin_account = accounts.get(admin_user_id, {})
    return {
        "items": items,
        "summary": summary,
        "growth": growth,
        "planDistribution": [
            {"key": "premium", "label": "Plano Premium", "count": plan_counts["premium"]},
            {"key": "free", "label": "Plano Free", "count": plan_counts["free"]},
            {"key": "unselected", "label": "Sem plano", "count": plan_counts["unselected"]},
        ],
        "brainInsights": _brain_insights(summary),
        "generatedAt": now.isoformat(),
        "source": "clerk+database" if clerk_available else "database-fallback",
        "sourceCounts": {
            "clerk": len(clerk_by_id),
            "database": len(database_user_ids),
            "combined": len(user_ids),
            "historicalExcluded": len(historical_excluded),
        },
        "currentAdminDiagnostic": {
            "accountFound": bool(admin_account),
            "rawPlan": str(admin_account.get("plan") or "unselected"),
            "resolvedPlan": _resolved_plan(admin_account),
            "subscriptionStatus": str(admin_account.get("subscription_status") or "inactive"),
            "isCountedAsPremium": any(item["id"] == admin_user_id and item["plan"] == "premium" for item in items),
        },
        "dataWarning": " | ".join(warnings),
    }
