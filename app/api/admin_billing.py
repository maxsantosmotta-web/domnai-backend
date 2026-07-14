from datetime import datetime, timedelta, timezone
import logging
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.admin import (
    ADMIN_TRANSACTION_DESCRIPTION,
    ADMIN_TRANSACTION_KIND,
    _grant_admin_access,
    _has_persisted_admin_access,
)
from app.api.admin_users import _clerk_users, _primary_email
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import (
    BillingAccount,
    CreditTransaction,
    ProcessedStripeEvent,
    UserProfile,
)

router = APIRouter(prefix="/api/admin/billing", tags=["admin-billing"])
logger = logging.getLogger(__name__)

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}
ATTENTION_SUBSCRIPTION_STATUSES = {"past_due", "unpaid", "incomplete"}


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


def _iso(value: datetime | None) -> str | None:
    normalized = _normalize_datetime(value)
    return normalized.isoformat() if normalized else None


def _timestamp_to_iso(value) -> str | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _obj_get(value, key: str, default=None):
    if value is None:
        return default
    try:
        result = value.get(key, default)
    except AttributeError:
        result = getattr(value, key, default)
    return default if result is None else result


def _plan(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "premium":
        return "premium"
    if normalized == "free":
        return "free"
    return "unselected"


def _plan_label(value: str) -> str:
    return {
        "premium": "Plano Premium",
        "free": "Plano Free",
        "unselected": "Sem plano",
    }.get(value, "Sem plano")


def _status_label(value: str) -> str:
    return {
        "active": "Ativa",
        "trialing": "Em teste",
        "past_due": "Em atraso",
        "unpaid": "Não paga",
        "incomplete": "Incompleta",
        "incomplete_expired": "Expirada",
        "canceled": "Cancelada",
        "inactive": "Inativa",
        "none": "Sem assinatura",
        "paid": "Paga",
        "open": "Pendente",
        "void": "Cancelada",
        "uncollectible": "Inadimplente",
        "draft": "Rascunho",
    }.get(value, str(value or "Indefinido").replace("_", " ").title())


def _monthly_amount_cents(subscription) -> int:
    items = _obj_get(_obj_get(subscription, "items", {}), "data", []) or []
    total = 0.0
    for item in items:
        price = _obj_get(item, "price", {})
        unit_amount = int(_obj_get(price, "unit_amount", 0) or 0)
        quantity = int(_obj_get(item, "quantity", 1) or 1)
        recurring = _obj_get(price, "recurring", {})
        interval = str(_obj_get(recurring, "interval", "month") or "month")
        interval_count = max(1, int(_obj_get(recurring, "interval_count", 1) or 1))
        amount = unit_amount * quantity
        if interval == "year":
            amount /= 12 * interval_count
        elif interval == "week":
            amount *= 52 / (12 * interval_count)
        elif interval == "day":
            amount *= 365 / (12 * interval_count)
        else:
            amount /= interval_count
        total += amount
    return int(round(total))


def _stripe_snapshot(accounts: dict[str, dict], customer_user_ids: set[str], now: datetime) -> dict:
    result = {
        "configured": False,
        "connected": False,
        "mrrCents": 0,
        "revenueMonthCents": 0,
        "paidInvoicesMonth": 0,
        "pendingInvoices": 0,
        "pendingAmountCents": 0,
        "recentInvoices": [],
        "liveSubscriptions": {},
        "warning": "",
    }

    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        result["warning"] = "Stripe não configurado no ambiente. Os dados exibidos vêm do banco e dos webhooks já processados."
        return result

    result["configured"] = True
    stripe.api_key = secret

    customer_to_user = {
        account["stripe_customer_id"]: user_id
        for user_id, account in accounts.items()
        if user_id in customer_user_ids and account.get("stripe_customer_id")
    }
    relevant_customers = set(customer_to_user)

    try:
        result["connected"] = True
        for user_id in customer_user_ids:
            account = accounts.get(user_id, {})
            subscription_id = account.get("stripe_subscription_id")
            if not subscription_id:
                continue
            subscription = stripe.Subscription.retrieve(subscription_id)
            live_status = str(_obj_get(subscription, "status", account.get("subscription_status") or "inactive"))
            result["liveSubscriptions"][user_id] = {
                "status": live_status,
                "statusLabel": _status_label(live_status),
                "currentPeriodEnd": _timestamp_to_iso(_obj_get(subscription, "current_period_end")),
                "monthlyAmountCents": _monthly_amount_cents(subscription),
            }
            if live_status in ACTIVE_SUBSCRIPTION_STATUSES:
                result["mrrCents"] += result["liveSubscriptions"][user_id]["monthlyAmountCents"]

        if relevant_customers:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            recent_start = now - timedelta(days=90)
            invoices = stripe.Invoice.list(created={"gte": int(recent_start.timestamp())}, limit=100)
            for invoice in invoices.auto_paging_iter():
                customer_id = str(_obj_get(invoice, "customer", "") or "")
                if customer_id not in relevant_customers:
                    continue
                currency = str(_obj_get(invoice, "currency", "brl") or "brl").lower()
                if currency != "brl":
                    continue
                status = str(_obj_get(invoice, "status", "draft") or "draft")
                created_at = _timestamp_to_iso(_obj_get(invoice, "created"))
                created_dt = datetime.fromisoformat(created_at) if created_at else None
                amount_paid = int(_obj_get(invoice, "amount_paid", 0) or 0)
                amount_remaining = int(_obj_get(invoice, "amount_remaining", 0) or 0)
                user_id = customer_to_user[customer_id]
                if status == "paid" and created_dt and created_dt >= month_start:
                    result["revenueMonthCents"] += amount_paid
                    result["paidInvoicesMonth"] += 1
                if status in {"open", "uncollectible"}:
                    result["pendingInvoices"] += 1
                    result["pendingAmountCents"] += amount_remaining
                result["recentInvoices"].append({
                    "id": str(_obj_get(invoice, "id", "")),
                    "userId": user_id,
                    "number": str(_obj_get(invoice, "number", "") or "Sem número"),
                    "status": status,
                    "statusLabel": _status_label(status),
                    "amountPaidCents": amount_paid,
                    "amountRemainingCents": amount_remaining,
                    "createdAt": created_at,
                    "hostedUrl": str(_obj_get(invoice, "hosted_invoice_url", "") or ""),
                })
            result["recentInvoices"].sort(key=lambda item: item.get("createdAt") or "", reverse=True)
            result["recentInvoices"] = result["recentInvoices"][:50]
    except Exception as exc:
        logger.exception("Falha parcial ao consultar Stripe no Faturamento Adm")
        result["connected"] = False
        result["warning"] = f"Stripe indisponível nesta atualização: {type(exc).__name__}."

    return result


def _brain_insights(summary: dict, stripe_state: dict) -> list[dict]:
    insights: list[dict] = []
    if not stripe_state["configured"]:
        insights.append({
            "level": "attention",
            "title": "Stripe não configurado",
            "message": "A receita e as faturas em tempo real serão liberadas quando as credenciais financeiras estiverem configuradas.",
        })
    elif not stripe_state["connected"]:
        insights.append({
            "level": "attention",
            "title": "Consulta financeira parcial",
            "message": "O banco e os webhooks estão disponíveis, mas o Stripe não respondeu nesta atualização.",
        })
    if summary["overdueAccounts"]:
        insights.append({
            "level": "attention",
            "title": "Assinaturas com pendência",
            "message": f"{summary['overdueAccounts']} conta(s) exigem acompanhamento de cobrança.",
        })
    if summary["pendingInvoices"]:
        insights.append({
            "level": "attention",
            "title": "Faturas pendentes",
            "message": f"Existem {summary['pendingInvoices']} fatura(s) aguardando pagamento.",
        })
    customer_total = summary["customerUsers"]
    if customer_total:
        conversion = round((summary["paidSubscriptions"] / customer_total) * 100, 1)
        insights.append({
            "level": "positive" if conversion >= 20 else "info",
            "title": "Conversão financeira",
            "message": f"{conversion:.1f}% dos usuários clientes possuem assinatura paga ativa.",
        })
    else:
        insights.append({
            "level": "info",
            "title": "Base financeira em preparação",
            "message": "Ainda não existem usuários clientes ativos para medir conversão de assinatura.",
        })
    if summary["revenueMonthCents"] > 0:
        insights.append({
            "level": "positive",
            "title": "Receita confirmada no mês",
            "message": "O valor considera somente faturas pagas e vinculadas aos clientes atuais do DomnAI.",
        })
    return insights[:4]


@router.get("")
def admin_billing_overview(
    limit: int = Query(default=200, ge=1, le=1000),
    session: dict = Depends(require_authenticated_user),
):
    admin_user_id, admin_state = _require_admin(session)
    now = datetime.now(timezone.utc)
    warnings: list[str] = []

    clerk_available = True
    try:
        clerk_users = _clerk_users()
    except HTTPException as exc:
        clerk_available = False
        clerk_users = []
        warnings.append(f"Clerk: {exc.detail}")

    directory = {}
    for user in clerk_users:
        user_id = str(user.get("id") or "").strip()
        if not user_id:
            continue
        first_name = str(user.get("first_name") or "").strip()
        last_name = str(user.get("last_name") or "").strip()
        name = " ".join(part for part in (first_name, last_name) if part).strip() or "Usuário DomnAI"
        directory[user_id] = {"name": name, "email": _primary_email(user)}

    accounts: dict[str, dict] = {}
    profiles: dict[str, dict] = {}
    admin_ids: set[str] = {admin_user_id}
    transactions: list[dict] = []
    processed_events: list[datetime] = []

    try:
        with session_scope() as db:
            for item in db.scalars(select(BillingAccount)).all():
                accounts[item.user_id] = {
                    "plan": str(item.plan or "unselected"),
                    "subscription_status": str(item.subscription_status or "inactive"),
                    "plan_credits": int(item.plan_credits or 0),
                    "extra_credits": int(item.extra_credits or 0),
                    "stripe_customer_id": str(item.stripe_customer_id or ""),
                    "stripe_subscription_id": str(item.stripe_subscription_id or ""),
                    "current_period_end": _normalize_datetime(item.current_period_end),
                    "updated_at": _normalize_datetime(item.updated_at),
                }
            for item in db.scalars(select(UserProfile)).all():
                profiles[item.user_id] = {
                    "full_name": str(item.full_name or ""),
                    "completed": bool(item.completed),
                }
            admin_ids.update(
                str(value)
                for value in db.scalars(
                    select(CreditTransaction.user_id).where(
                        CreditTransaction.kind == ADMIN_TRANSACTION_KIND,
                        CreditTransaction.description == ADMIN_TRANSACTION_DESCRIPTION,
                    ).distinct()
                ).all()
                if value
            )
            transaction_rows = db.scalars(
                select(CreditTransaction).order_by(CreditTransaction.created_at.desc()).limit(300)
            ).all()
            transactions = [{
                "id": item.id,
                "userId": item.user_id,
                "kind": item.kind,
                "amount": int(item.amount or 0),
                "description": item.description,
                "planBalance": int(item.plan_balance or 0),
                "extraBalance": int(item.extra_balance or 0),
                "createdAt": _iso(item.created_at),
            } for item in transaction_rows]
            processed_events = [
                _normalize_datetime(value)
                for value in db.scalars(select(ProcessedStripeEvent.processed_at)).all()
                if value is not None
            ]
    except Exception as exc:
        logger.exception("Falha parcial no banco do Faturamento Adm")
        warnings.append(f"Banco: {type(exc).__name__}")

    accounts.setdefault(admin_user_id, {
        "plan": str(admin_state.get("plan") or "premium"),
        "subscription_status": str(admin_state.get("subscriptionStatus") or "active"),
        "plan_credits": int(admin_state.get("planCredits") or 0),
        "extra_credits": int(admin_state.get("extraCredits") or 0),
        "stripe_customer_id": "",
        "stripe_subscription_id": "",
        "current_period_end": None,
        "updated_at": now,
    })

    database_ids = set(accounts) | set(profiles)
    if clerk_available:
        active_user_ids = set(directory) | {admin_user_id}
    else:
        active_user_ids = database_ids | {admin_user_id}
    customer_user_ids = active_user_ids - admin_ids

    stripe_state = _stripe_snapshot(accounts, customer_user_ids, now)
    if stripe_state["warning"]:
        warnings.append(stripe_state["warning"])

    items: list[dict] = []
    plan_counts = {"premium": 0, "free": 0, "unselected": 0}
    paid_subscriptions = 0
    overdue_accounts = 0

    for user_id in active_user_ids:
        account = accounts.get(user_id, {})
        profile = profiles.get(user_id, {})
        directory_user = directory.get(user_id, {})
        plan = _plan(account.get("plan"))
        if user_id == admin_user_id and plan == "unselected":
            plan = _plan(admin_state.get("plan") or "premium")
        plan_counts[plan] += 1

        live = stripe_state["liveSubscriptions"].get(user_id, {})
        status = str(live.get("status") or account.get("subscription_status") or "inactive")
        is_admin = user_id in admin_ids
        has_paid_subscription = bool(
            not is_admin
            and account.get("stripe_subscription_id")
            and status in ACTIVE_SUBSCRIPTION_STATUSES
        )
        paid_subscriptions += int(has_paid_subscription)
        overdue_accounts += int(not is_admin and status in ATTENTION_SUBSCRIPTION_STATUSES)

        name = str(directory_user.get("name") or profile.get("full_name") or "Usuário DomnAI")
        email = str(directory_user.get("email") or "")
        items.append({
            "id": user_id,
            "name": name,
            "email": email,
            "role": "admin" if is_admin else "user",
            "roleLabel": "Admin" if is_admin else "Usuário",
            "plan": plan,
            "planLabel": _plan_label(plan),
            "subscriptionStatus": status,
            "subscriptionStatusLabel": _status_label(status),
            "paidSubscription": has_paid_subscription,
            "stripeConnected": bool(account.get("stripe_customer_id")),
            "monthlyAmountCents": int(live.get("monthlyAmountCents") or 0),
            "planCredits": int(account.get("plan_credits") or 0),
            "extraCredits": int(account.get("extra_credits") or 0),
            "totalCredits": int(account.get("plan_credits") or 0) + int(account.get("extra_credits") or 0),
            "currentPeriodEnd": live.get("currentPeriodEnd") or _iso(account.get("current_period_end")),
            "updatedAt": _iso(account.get("updated_at")),
        })

    items.sort(key=lambda item: (item["paidSubscription"], item.get("updatedAt") or ""), reverse=True)
    items = items[:limit]
    active_ids = {item["id"] for item in items}

    invoice_items = []
    for invoice in stripe_state["recentInvoices"]:
        if invoice["userId"] not in active_ids:
            continue
        user = next((item for item in items if item["id"] == invoice["userId"]), None)
        invoice_items.append({
            **invoice,
            "name": user["name"] if user else "Usuário DomnAI",
            "email": user["email"] if user else "",
        })

    transaction_items = []
    for transaction in transactions:
        user_id = transaction["userId"]
        if user_id not in active_user_ids or transaction["kind"] == ADMIN_TRANSACTION_KIND:
            continue
        user = next((item for item in items if item["id"] == user_id), None)
        transaction_items.append({
            **transaction,
            "name": user["name"] if user else "Usuário DomnAI",
            "email": user["email"] if user else "",
        })
        if len(transaction_items) >= 100:
            break

    webhook_24h = sum(1 for value in processed_events if value and value >= now - timedelta(hours=24))
    summary = {
        "totalAccounts": len(active_user_ids),
        "customerUsers": len(customer_user_ids),
        "premiumPlans": plan_counts["premium"],
        "freePlans": plan_counts["free"],
        "unselectedPlans": plan_counts["unselected"],
        "paidSubscriptions": paid_subscriptions,
        "overdueAccounts": overdue_accounts,
        "mrrCents": stripe_state["mrrCents"],
        "revenueMonthCents": stripe_state["revenueMonthCents"],
        "paidInvoicesMonth": stripe_state["paidInvoicesMonth"],
        "pendingInvoices": stripe_state["pendingInvoices"],
        "pendingAmountCents": stripe_state["pendingAmountCents"],
        "webhookEvents24h": webhook_24h,
        "processedEvents": len(processed_events),
    }

    return {
        "items": items,
        "invoices": invoice_items,
        "transactions": transaction_items,
        "summary": summary,
        "brainInsights": _brain_insights(summary, stripe_state),
        "stripe": {
            "configured": stripe_state["configured"],
            "connected": stripe_state["connected"],
            "statusLabel": "Conectado" if stripe_state["connected"] else ("Configuração pendente" if not stripe_state["configured"] else "Indisponível"),
        },
        "generatedAt": now.isoformat(),
        "source": "clerk+database+stripe" if clerk_available and stripe_state["connected"] else "parcial",
        "sourceCounts": {
            "clerk": len(directory),
            "database": len(database_ids),
            "active": len(active_user_ids),
            "historicalExcluded": len(database_ids - set(directory)) if clerk_available else 0,
        },
        "dataWarning": " | ".join(dict.fromkeys(warnings)),
    }
