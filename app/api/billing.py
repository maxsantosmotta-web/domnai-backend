import math
import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.audit import record_audit_event
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import BillingAccount, CreditTransaction, ProcessedStripeEvent, UserProfile

router = APIRouter(prefix="/api/billing", tags=["billing"])

PLAN_CREDITS = 500
EXTRA_CREDIT_PACK = 250
PAID_STATUSES = {"paid", "no_payment_required"}
BLOCKED_STATUSES = {"past_due", "unpaid", "canceled", "incomplete", "incomplete_expired", "expired", "paused"}


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


def _require_completed_profile(db, user_id: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None or not profile.completed:
        raise HTTPException(status_code=428, detail="Complete seu cadastro antes de escolher um plano.")
    return profile


def _period_end(obj) -> datetime | None:
    value = obj.get("current_period_end")
    return datetime.fromtimestamp(int(value), tz=timezone.utc) if value else None


def _is_premium(account: BillingAccount) -> bool:
    if account.plan != "premium" or account.subscription_status not in {"active", "trialing"}:
        return False
    if account.current_period_end is None:
        return True
    end = account.current_period_end
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) <= end


def _serialize(account: BillingAccount) -> dict:
    plan = account.plan
    if plan == "free_demo":
        plan = "unselected"
    return {
        "plan": plan,
        "subscriptionStatus": account.subscription_status,
        "planCredits": account.plan_credits,
        "extraCredits": account.extra_credits,
        "totalCredits": account.plan_credits + account.extra_credits,
        "premiumActive": _is_premium(account),
        "currentPeriodEnd": account.current_period_end.isoformat() if account.current_period_end else None,
    }


def _tx(db, account, kind, amount, description, event_id=None):
    item = CreditTransaction(
        user_id=account.user_id,
        kind=kind,
        amount=amount,
        plan_balance=account.plan_credits,
        extra_balance=account.extra_credits,
        description=description[:255],
        stripe_event_id=event_id,
    )
    db.add(item)
    db.flush()
    return item


def _audit(db, account, event_id, action, description, result="success"):
    record_audit_event(
        db,
        user_id=account.user_id,
        category="payment",
        module="Faturamento",
        action=action,
        description=description,
        result=result,
        source="stripe",
        source_key=f"stripe:{event_id}:payment",
    )


def _account_by_object(db, obj):
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or obj.get("client_reference_id")
    if user_id:
        return _get_or_create_account(db, str(user_id)), metadata
    payment_intent = obj.get("payment_intent")
    if payment_intent:
        try:
            pi = stripe.PaymentIntent.retrieve(payment_intent)
            metadata = dict(pi.get("metadata") or {})
            if metadata.get("user_id"):
                return _get_or_create_account(db, str(metadata["user_id"])), metadata
        except Exception:
            pass
    customer = obj.get("customer")
    if customer:
        account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_customer_id == customer))
        if account:
            return account, metadata
    return None, metadata


def _block(account, status):
    account.subscription_status = status
    account.plan_credits = 0


def _grant_pack(db, account, event_id):
    account.extra_credits += EXTRA_CREDIT_PACK
    if str(account.subscription_status or "").lower() in BLOCKED_STATUSES:
        account.subscription_status = "extra_active"
        account.plan_credits = 0
    _tx(db, account, "extra_credit", EXTRA_CREDIT_PACK, "Pacote avulso de 250 créditos", event_id)
    _audit(db, account, event_id, "payment_approved", "Pagamento do pacote de créditos aprovado.")


def _reverse(db, obj, event_id, reason, fraction=1.0):
    account, metadata = _account_by_object(db, obj)
    if not account:
        return
    if metadata.get("product") == "credits_250":
        amount = max(1, min(EXTRA_CREDIT_PACK, math.ceil(EXTRA_CREDIT_PACK * fraction)))
        account.extra_credits -= amount
        _tx(db, account, "credit_reversal", -amount, f"Reversão por {reason}", event_id)
        if account.subscription_status == "extra_active" and account.plan_credits + account.extra_credits <= 0:
            account.subscription_status = "inactive"
        description = f"{amount} crédito(s) removido(s) por {reason}."
    else:
        _block(account, "unpaid")
        description = f"Acesso PREMIUM bloqueado por {reason}."
    _audit(db, account, event_id, "payment_reversed", description, "reversed")


@router.get("/status")
def billing_status(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        account = db.get(BillingAccount, user_id)
        profile = db.get(UserProfile, user_id)
        if account is None:
            return {
                "plan": "unselected", "subscriptionStatus": "inactive", "planCredits": 0,
                "extraCredits": 0, "totalCredits": 0, "premiumActive": False,
                "currentPeriodEnd": None, "profileCompleted": bool(profile and profile.completed),
                "financialAccountExists": False,
            }
        payload = _serialize(account)
        payload["profileCompleted"] = bool(profile and profile.completed)
        payload["financialAccountExists"] = True
        return payload


@router.post("/select-free")
def select_free_plan(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        _require_completed_profile(db, user_id)
        account = _get_or_create_account(db, user_id)
        if _is_premium(account):
            raise HTTPException(status_code=409, detail="Gerencie ou cancele sua assinatura PREMIUM antes de mudar para o FREE.")
        account.plan = "free"
        account.subscription_status = "inactive"
        account.plan_credits = 0
        account.current_period_end = None
        return _serialize(account)


@router.get("/transactions")
def billing_transactions(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        items = db.scalars(
            select(CreditTransaction).where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc()).limit(100)
        ).all()
        return {"items": [{
            "id": item.id, "kind": item.kind, "amount": item.amount,
            "planBalance": item.plan_balance, "extraBalance": item.extra_balance,
            "description": item.description, "createdAt": item.created_at.isoformat(),
        } for item in items]}


@router.post("/checkout")
def create_checkout(payload: CheckoutRequest, session: dict = Depends(require_authenticated_user)):
    _stripe_secret()
    user_id = session.get("sub")
    price_id, mode = _price_id(payload.product)
    with session_scope() as db:
        if mode == "subscription":
            _require_completed_profile(db, user_id)
        account = _get_or_create_account(db, user_id)
        customer_id = account.stripe_customer_id
    metadata = {"user_id": user_id, "product": payload.product}
    params = {
        "mode": mode,
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{_frontend_url()}/#/dashboard?checkout=success",
        "cancel_url": f"{_frontend_url()}/#/dashboard?checkout=cancelled",
        "client_reference_id": user_id,
        "metadata": metadata,
        "allow_promotion_codes": True,
    }
    if customer_id:
        params["customer"] = customer_id
    elif mode == "payment":
        params["customer_creation"] = "always"
    if mode == "subscription":
        params["subscription_data"] = {"metadata": metadata}
    else:
        params["payment_intent_data"] = {"metadata": metadata}
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
        account = db.scalar(select(BillingAccount).where(BillingAccount.user_id == user_id).with_for_update())
        if account is None:
            raise HTTPException(status_code=402, detail="Conta de créditos não encontrada.")
        if str(account.subscription_status or "").lower() in BLOCKED_STATUSES:
            raise HTTPException(status_code=402, detail="Acesso bloqueado por pendência financeira.")
        available = account.plan_credits + account.extra_credits
        if available < payload.amount:
            raise HTTPException(status_code=402, detail="Créditos insuficientes.")
        remaining = payload.amount
        from_plan = min(max(0, account.plan_credits), remaining)
        account.plan_credits -= from_plan
        remaining -= from_plan
        if remaining:
            account.extra_credits -= remaining
        _tx(db, account, "consumption", -payload.amount, payload.description or "Consumo de créditos")
        return _serialize(account)


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

        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            account, metadata = _account_by_object(db, obj)
            if account and obj.get("payment_status") in PAID_STATUSES:
                account.stripe_customer_id = obj.get("customer") or account.stripe_customer_id
                if obj.get("mode") == "payment" and metadata.get("product") == "credits_250":
                    _grant_pack(db, account, event_id)
                elif obj.get("mode") == "subscription":
                    account.stripe_subscription_id = obj.get("subscription")
                    account.plan = "premium"
                    account.subscription_status = "active"
                    account.plan_credits = PLAN_CREDITS
                    if account.stripe_subscription_id:
                        subscription = stripe.Subscription.retrieve(account.stripe_subscription_id)
                        account.subscription_status = str(subscription.get("status") or "active")
                        account.current_period_end = _period_end(subscription)
                    _tx(db, account, "plan_credit", PLAN_CREDITS, "Créditos do plano PREMIUM", event_id)
                    _audit(db, account, event_id, "payment_approved", "Pagamento do plano PREMIUM aprovado.")

        elif event_type == "invoice.paid":
            subscription_id = obj.get("subscription")
            if subscription_id and obj.get("billing_reason") != "subscription_create":
                account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_subscription_id == subscription_id))
                if account:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    account.plan = "premium"
                    account.subscription_status = str(subscription.get("status") or "active")
                    account.current_period_end = _period_end(subscription)
                    account.plan_credits = PLAN_CREDITS
                    _tx(db, account, "plan_credit", PLAN_CREDITS, "Renovação do plano PREMIUM", event_id)
                    _audit(db, account, event_id, "payment_approved", "Renovação do plano PREMIUM aprovada.")

        elif event_type == "invoice.payment_failed":
            subscription_id = obj.get("subscription")
            account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_subscription_id == subscription_id)) if subscription_id else None
            if account:
                _block(account, "past_due")
                _audit(db, account, event_id, "payment_failed", "Renovação recusada. Acesso bloqueado imediatamente.", "failed")

        elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
            account = db.scalar(select(BillingAccount).where(BillingAccount.stripe_subscription_id == obj.get("id")))
            if account:
                status = "canceled" if event_type.endswith("deleted") else str(obj.get("status") or "inactive")
                account.subscription_status = status
                account.current_period_end = _period_end(obj)
                if status in BLOCKED_STATUSES:
                    account.plan_credits = 0
                if status in {"canceled", "incomplete_expired"}:
                    account.plan = "free"

        elif event_type == "charge.refunded":
            amount = int(obj.get("amount") or 0)
            refunded = int(obj.get("amount_refunded") or amount)
            _reverse(db, obj, event_id, "reembolso", refunded / amount if amount else 1.0)

        elif event_type in {"charge.dispute.created", "charge.dispute.funds_withdrawn"}:
            _reverse(db, obj, event_id, "contestação/chargeback")

        elif event_type in {"payment_intent.payment_failed", "checkout.session.async_payment_failed"}:
            account, _ = _account_by_object(db, obj)
            if account:
                _audit(db, account, event_id, "payment_failed", "Pagamento recusado pelo processador financeiro.", "failed")

        db.add(ProcessedStripeEvent(event_id=event_id, event_type=event_type))

    return {"received": True}
