from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.admin import ADMIN_TRANSACTION_KIND, _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.config import settings
from app.database import session_scope
from app.models import (
    ActiveChatState,
    BillingAccount,
    CreditTransaction,
    DiagnosisState,
    LibraryAsset,
    UserFeedback,
    UserProfile,
)

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])

CLERK_USERS_URL = "https://api.clerk.com/v1/users"
CLERK_PAGE_SIZE = 100
MAX_CLERK_USERS = 5000


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


def _clerk_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        numeric = int(value)
        if numeric > 10_000_000_000:
            numeric = numeric / 1000
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


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
        raise HTTPException(status_code=503, detail="CLERK_SECRET_KEY não configurada para o módulo Usuários.")

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
            detail = payload.get("errors", [{}])[0].get("long_message") or payload.get("message") or detail
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail) from exc
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Não foi possível consultar os usuários no Clerk.") from exc

    return users[:MAX_CLERK_USERS]


def _activity_map(db, model, column, user_ids: set[str]) -> dict[str, datetime]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(model.user_id, func.max(column))
        .where(model.user_id.in_(user_ids))
        .group_by(model.user_id)
    ).all()
    return {str(user_id): value for user_id, value in rows if value is not None}


def _latest(*values: datetime | None) -> datetime | None:
    normalized = []
    for value in values:
        if value is None:
            continue
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        normalized.append(value)
    return max(normalized) if normalized else None


def _plan_label(value: str) -> str:
    return {
        "premium": "Premium",
        "free": "Free",
        "unselected": "Sem plano",
        "free_demo": "Sem plano",
    }.get(value, value.replace("_", " ").title() if value else "Sem plano")


def _build_brain_insights(summary: dict) -> list[dict]:
    total = summary["totalUsers"]
    if total == 0:
        return [{
            "level": "info",
            "title": "Base ainda sem usuários",
            "message": "O IAttom Brain começará a comparar adesão, atividade e conversão assim que houver cadastros.",
        }]

    incomplete = total - summary["profileCompleted"]
    unselected = summary["unselectedUsers"]
    inactive = total - summary["activeLast7Days"]
    premium_rate = round((summary["premiumUsers"] / total) * 100, 1)

    insights = []
    if incomplete:
        insights.append({
            "level": "attention",
            "title": "Cadastros incompletos",
            "message": f"{incomplete} usuário(s) ainda não concluíram o perfil obrigatório.",
        })
    if unselected:
        insights.append({
            "level": "attention",
            "title": "Plano ainda não escolhido",
            "message": f"{unselected} usuário(s) estão sem FREE ou PREMIUM definido.",
        })
    if inactive:
        insights.append({
            "level": "info",
            "title": "Atividade recente",
            "message": f"{summary['activeLast7Days']} de {total} usuário(s) tiveram atividade nos últimos 7 dias.",
        })
    insights.append({
        "level": "positive" if premium_rate >= 20 else "info",
        "title": "Conversão para Premium",
        "message": f"{premium_rate:.1f}% da base está atualmente no plano Premium.",
    })
    return insights[:4]


@router.get("")
def list_admin_users(
    limit: int = Query(default=500, ge=1, le=1000),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    clerk_users = _clerk_users()
    user_ids = {str(item.get("id") or "").strip() for item in clerk_users}
    user_ids.discard("")

    with session_scope() as db:
        accounts = {
            item.user_id: item
            for item in db.scalars(
                select(BillingAccount).where(BillingAccount.user_id.in_(user_ids))
            ).all()
        } if user_ids else {}
        profiles = {
            item.user_id: item
            for item in db.scalars(
                select(UserProfile).where(UserProfile.user_id.in_(user_ids))
            ).all()
        } if user_ids else {}
        admin_ids = set(
            db.scalars(
                select(CreditTransaction.user_id)
                .where(
                    CreditTransaction.user_id.in_(user_ids),
                    CreditTransaction.kind == ADMIN_TRANSACTION_KIND,
                )
                .distinct()
            ).all()
        ) if user_ids else set()

        billing_activity = _activity_map(db, BillingAccount, BillingAccount.updated_at, user_ids)
        profile_activity = _activity_map(db, UserProfile, UserProfile.updated_at, user_ids)
        credit_activity = _activity_map(db, CreditTransaction, CreditTransaction.created_at, user_ids)
        chat_activity = _activity_map(db, ActiveChatState, ActiveChatState.updated_at, user_ids)
        diagnosis_activity = _activity_map(db, DiagnosisState, DiagnosisState.updated_at, user_ids)
        feedback_activity = _activity_map(db, UserFeedback, UserFeedback.created_at, user_ids)
        library_activity = _activity_map(db, LibraryAsset, LibraryAsset.created_at, user_ids)

    now = datetime.now(timezone.utc)
    start_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    active_cutoff = now - timedelta(days=7)

    items = []
    growth_counts: defaultdict[str, int] = defaultdict(int)
    plan_counts = {"premium": 0, "free": 0, "unselected": 0}
    new_this_week = 0
    new_this_month = 0
    active_last_7_days = 0
    profile_completed = 0
    total_credits = 0

    for clerk_user in clerk_users:
        user_id = str(clerk_user.get("id") or "").strip()
        if not user_id:
            continue

        profile = profiles.get(user_id)
        account = accounts.get(user_id)
        created_at = _clerk_datetime(clerk_user.get("created_at"))
        clerk_last_sign_in = _clerk_datetime(clerk_user.get("last_sign_in_at"))
        last_activity = _latest(
            clerk_last_sign_in,
            billing_activity.get(user_id),
            profile_activity.get(user_id),
            credit_activity.get(user_id),
            chat_activity.get(user_id),
            diagnosis_activity.get(user_id),
            feedback_activity.get(user_id),
            library_activity.get(user_id),
        )

        raw_plan = str(account.plan if account else "unselected").lower()
        if raw_plan == "free_demo":
            raw_plan = "unselected"
        normalized_plan = raw_plan if raw_plan in plan_counts else "unselected"
        plan_counts[normalized_plan] += 1

        credits = int((account.plan_credits + account.extra_credits) if account else 0)
        total_credits += credits
        completed = bool(profile and profile.completed)
        if completed:
            profile_completed += 1
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
        name = clerk_name or (profile.full_name if profile else "") or "Usuário DomnAI"
        blocked = bool(clerk_user.get("banned") or clerk_user.get("locked"))

        items.append({
            "id": user_id,
            "name": name,
            "email": _primary_email(clerk_user),
            "role": "admin" if user_id in admin_ids else "user",
            "roleLabel": "Admin" if user_id in admin_ids else "Usuário",
            "plan": normalized_plan,
            "planLabel": _plan_label(normalized_plan),
            "subscriptionStatus": str(account.subscription_status if account else "inactive"),
            "planCredits": int(account.plan_credits if account else 0),
            "extraCredits": int(account.extra_credits if account else 0),
            "totalCredits": credits,
            "profileCompleted": completed,
            "accountStatus": "blocked" if blocked else "active",
            "accountStatusLabel": "Bloqueado" if blocked else "Ativo",
            "createdAt": _iso(created_at),
            "lastActivityAt": _iso(last_activity),
        })

    items.sort(key=lambda item: item.get("createdAt") or "", reverse=True)
    items = items[:limit]

    growth = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date()
        key = day.isoformat()
        growth.append({
            "date": key,
            "label": day.strftime("%d/%m"),
            "count": growth_counts.get(key, 0),
        })

    summary = {
        "totalUsers": len(clerk_users),
        "newThisWeek": new_this_week,
        "newThisMonth": new_this_month,
        "profileCompleted": profile_completed,
        "premiumUsers": plan_counts["premium"],
        "freeUsers": plan_counts["free"],
        "unselectedUsers": plan_counts["unselected"],
        "activeLast7Days": active_last_7_days,
        "totalCredits": total_credits,
    }

    return {
        "items": items,
        "summary": summary,
        "growth": growth,
        "planDistribution": [
            {"key": "premium", "label": "Premium", "count": plan_counts["premium"]},
            {"key": "free", "label": "Free", "count": plan_counts["free"]},
            {"key": "unselected", "label": "Sem plano", "count": plan_counts["unselected"]},
        ],
        "brainInsights": _build_brain_insights(summary),
        "generatedAt": now.isoformat(),
        "source": "clerk+database",
    }
