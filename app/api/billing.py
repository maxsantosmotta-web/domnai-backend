import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction, ProcessedStripeEvent

router = APIRouter(prefix="/api/billing", tags=["billing"])

PLAN_CREDITS = 500
EXTRA_CREDIT_PACK = 250


class CheckoutRequest(BaseModel):
    product: str


class ConsumeCreditsRequest(BaseModel):
    amount: int
    description: str


def _stripe_secret() -> str:
    value = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not value:
        raise HTTPException(status_code=503, detail="Stripe não configurada.")
    stripe.api_key = value
    return value


def _price_id(product: str) -> tuple[str, str]:
    mapping = {
        "premium_monthly": ("STRIPE_PRICE_PREMIUM_MONTHLY", "subscription"),
        "premium_yearly": ("STRIPE_PRICE_PREMIUM_YEARLY", "subscription"),
        "credits_250": ("STRIPE_PRICE_CREDITS_250", "payment"),
    }
    if product not in mapping:
        raise HTTPException(status_code=400, detail="Produto financeiro inválido.")
    env_name, mode = mapping[product]
    price_id = os.getenv(env_name, "").strip()
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Preço Stripe não configurado: {env_name}.")
    return price_id, mode


def _frontend_url() -> str:
    return os.getenv("APP_URL", "https://domnai.iattomassist.com.br").rstrip("/")


def _get_or_create_account(db, user_id: str) -> BillingAccount:
    account = db.get(BillingAccount, user_id)
    if account is None:
        account = BillingAccount(user_id=user_id, plan="unselected", subscription_status="inactive")
        db.add(account)
        db.flush()
    return account


def _is_premium(account: BillingAccount) -> bool:
    if account.plan != "premium":
        return False
    if account.subscription_status not in {"active", "trialing", "past_due"}:
        return False
    if account.current_period_end is None:
        return account.subscription_status in {"active", "trialing"}
    now = datetime.now(timezone.utc)
    period_end = account.current_period_end
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    return now <= period_end


def _serialize_account(account: BillingAccount) -> dict:
    premium_active = _is_premium(account)
    plan = "premium" if premium_active else account.plan
    if plan == "free_demo":
        plan = "unselected"
    return {
        "plan": plan,
        "subscriptionStatus": account.subscription_status,
        "planCredits": account.plan_credits,
        "extraCredits": account.extra_credits,
        "totalCredits": account.plan_credits + account.extra_credits,
        "premiumActive": premium_active,
        "currentPeriodEnd": account.current_period_end.isoformat() if account.current_period_end else None,
    }


def _record_transaction(db, account: BillingAccount, kind: str, amount: int, description: str, event_id: str | None = None):
    db.add(CreditTransaction(
        user_id=account.user_id,
        kind=kind,
        amount=amount,
        plan_balance=account.plan_credits,
        extra_balance=account.extra_credits,
        description=description[:255],
        stripe_event_id=event_id,
    ))


def _datetime_from_unix(value) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _subscription_period_end(subscription) -> datetime | None:
    return _datetime_from_unix(subscription.get("current_period_end"))


@router.get("/status")
def billing_status(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        account = _get_or_create_account(db, user_id)
        if account.plan == "free_demo":
            account.plan = "unselected"
            db.flush()
        return _serialize_account(account)


@router.post("/select-free")
def select_free_plan(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        account = _get_or_create_account(db, user_id)
        if _is_premium(account):
            raise HTTPException(status_code=409, detail="Gerencie ou cancele sua assinatura PREMIUM antes de mudar para o FREE.")
        account.plan = "free"
        account.subscription_status = "inactive"
        account.plan_credits = 0
        account.current_period_end = None
        db.flush()
        return _serialize_account(account)


@router.get("/transactions")
def billing_transactions(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        items = db.scalars(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(100)
        ).all()
        return {"items": [{
            "id": item.id,
            "kind": item.kind,
            "amount": item.amount,
            "planBalance": item.plan_balance,
            "extraBalance": item.extra_balance,
            "description": item.description,
            "createdAt": item.created_at.isoformat(),
        } for item in items]}


@router.post("/checkout")
def create_checkout(payload: CheckoutRequest, session: dict = Depends(require_authenticated_user)):
    _stripe_secret()
    user_id = session.get("sub")
    price_id, mode = _price_id(payload.product)
    success_url = f"{_frontend_url()}/#/dashboard?checkout=success"
    cancel_url = f"{_frontend_url()}/#/dashboard?checkout=cancelled"

    with session_scope() as db:
        account = _get_or_create_account(db, user_id)
        customer_id = account.stripe_customer_id

    params = {
        "mode": mode,
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": user_id,
        "metadata": {"user_id": user_id, "product": payload.product},
        "allow_promotion_codes": True,
    }
    if customer_id:
        params["customer"] = customer_id
    elif mode == "payment":
        params["customer_creation"] = "always"

    if mode == "subscription":
        params["subscription_data"] = {"metadata": {"user_id": user_id, "product": payload.product}}

    checkout = stripe.checkout.Session.create(**params)
    return {"url": checkout.url}


@router.post("/portal")
def create_customer_portal(session: dict = Depends(require_authenticated_user)):
    _stripe_secret()
    user_id = session.get("sub")
    with session_scope() as db:
        account = _get_or_create_account(db, user_id)
        if not account.stripe_customer_id:
            raise HTTPException(status_code=400, detail="Cliente ainda não possui cadastro financeiro.")
        portal = stripe.billing_portal.Session.create(
            customer=account.stripe_customer_id,
            return_url=f"{_frontend_url()}/#/dashboard",
        )
        return {"url": portal.url}


@router.post("/consume")
def consume_credits(payload: ConsumeCreditsRequest, session: dict = Depends(require_authenticated_user)):
    if payload.amount <= 0 or payload.amount > 100:
        raise HTTPException(status_code=400, detail="Quantidade de créditos inválida.")
    user_id = session.get("sub")
    with session_scope() as db:
        account = _get_or_create_account(db, user_id)
        available = account.plan_credits + account.extra_credits
        if available < payload.amount:
            raise HTTPException(status_code=402, detail="Créditos insuficientes.")

        remaining = payload.amount
        from_plan = min(account.plan_credits, remaining)
        account.plan_credits -= from_plan
        remaining -= from_plan
        if remaining:
            account.extra_credits -= remaining

        _record_transaction(db, account, "consumption", -payload.amount, payload.description or "Consumo de créditos")
        return _serialize_account(account)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook Stripe não configurado.")
    _stripe_secret()

    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Assinatura de webhook inválida.")

    event_id = event["id"]
    event_type = event["type"]
    obj = event["data"]["object"]

    with session_scope() as db:
        if db.get(ProcessedStripeEvent, event_id):
            return {"received": True, "duplicate": True}

        if event_type == "checkout.session.completed":
            user_id = (obj.get("metadata") or {}).get("user_id") or obj.get("client_reference_id")
            product = (obj.get("metadata") or {}).get("product")
            if user_id:
                account = _get_or_create_account(db, user_id)
                account.stripe_customer_id = obj.get("customer") or account.stripe_customer_id

                if obj.get("mode") == "subscription":
                    account.stripe_subscription_id = obj.get("subscription")
                    account.plan = "premium"
                    account.subscription_status = "active"
                    account.plan_credits = PLAN_CREDITS
                    if account.stripe_subscription_id:
                        subscription = stripe.Subscription.retrieve(account.stripe_subscription_id)
                        account.current_period_end = _subscription_period_end(subscription)
                    _record_transaction(db, account, "plan_credit", PLAN_CREDITS, "Créditos do plano PREMIUM", event_id)

                elif obj.get("mode") == "payment" and product == "credits_250":
                    account.extra_credits += EXTRA_CREDIT_PACK
                    _record_transaction(db, account, "extra_credit", EXTRA_CREDIT_PACK, "Pacote avulso de 250 créditos", event_id)

        elif event_type == "invoice.paid":
            billing_reason = obj.get("billing_reason")
            subscription_id = obj.get("subscription")
            if subscription_id and billing_reason != "subscription_create":
                account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_subscription_id == subscription_id))
                if account:
                    account.plan = "premium"
                    account.subscription_status = "active"
                    account.plan_credits = PLAN_CREDITS
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    account.current_period_end = _subscription_period_end(subscription)
                    _record_transaction(db, account, "plan_credit", PLAN_CREDITS, "Renovação do plano PREMIUM", event_id)

        elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
            subscription_id = obj.get("id")
            account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_subscription_id == subscription_id))
            if account:
                account.subscription_status = obj.get("status", "inactive")
                account.current_period_end = _subscription_period_end(obj)
                if event_type == "customer.subscription.deleted" or obj.get("status") in {"canceled", "unpaid", "incomplete_expired"}:
                    account.plan = "free"
                    account.plan_credits = 0

        elif event_type == "invoice.payment_failed":
            subscription_id = obj.get("subscription")
            if subscription_id:
                account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_subscription_id == subscription_id))
                if account:
                    account.subscription_status = "past_due"

        db.add(ProcessedStripeEvent(event_id=event_id, event_type=event_type))

    return {"received": True}
