import math
import os

from fastapi import HTTPException
from sqlalchemy import select

from app.database import session_scope
from app.models import BillingAccount, CreditTransaction
from app.services.metered_brain import MeteredBrainResult

ADMIN_CREDITS = 100000
DEFAULT_USD_PER_CREDIT = 0.001
ARTIFACT_MINIMUM_CREDITS = 7

MODEL_RATES_USD_PER_MILLION = {
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
}

BLOCKED_SUBSCRIPTION_STATUSES = {
    "past_due",
    "unpaid",
    "canceled",
    "incomplete",
    "incomplete_expired",
    "expired",
    "paused",
}
ALLOWED_SUBSCRIPTION_STATUSES = {"active", "trialing", "extra_active", "inactive"}


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def calculate_usage_cost(result: MeteredBrainResult) -> dict:
    if result.provider == "local-artifact":
        return {
            "cost_usd": 0.0,
            "credits": 0,
            "usd_per_credit": _float_env("DOMNAI_USD_PER_CREDIT", DEFAULT_USD_PER_CREDIT),
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
        }

    rates = MODEL_RATES_USD_PER_MILLION.get(
        result.model,
        {
            "input": _float_env("DOMNAI_INPUT_USD_PER_MILLION", 0.15),
            "cached_input": _float_env("DOMNAI_CACHED_INPUT_USD_PER_MILLION", 0.075),
            "output": _float_env("DOMNAI_OUTPUT_USD_PER_MILLION", 0.60),
        },
    )
    cached_tokens = min(result.cached_input_tokens, result.input_tokens)
    uncached_input_tokens = max(0, result.input_tokens - cached_tokens)
    cost_usd = (
        (uncached_input_tokens * rates["input"])
        + (cached_tokens * rates["cached_input"])
        + (result.output_tokens * rates["output"])
    ) / 1_000_000
    usd_per_credit = _float_env("DOMNAI_USD_PER_CREDIT", DEFAULT_USD_PER_CREDIT)
    credits = max(1, math.ceil(cost_usd / usd_per_credit))
    return {
        "cost_usd": cost_usd,
        "credits": credits,
        "usd_per_credit": usd_per_credit,
        "input_tokens": result.input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": result.output_tokens,
    }


def _is_admin(account: BillingAccount) -> bool:
    return account.plan_credits >= ADMIN_CREDITS


def _ensure_financial_access(account: BillingAccount) -> None:
    if _is_admin(account):
        return

    status = str(account.subscription_status or "inactive").strip().lower()
    if status in BLOCKED_SUBSCRIPTION_STATUSES:
        raise HTTPException(
            status_code=402,
            detail="Acesso bloqueado por pendência financeira. Regularize a assinatura ou compre um novo pacote de créditos.",
        )
    if status not in ALLOWED_SUBSCRIPTION_STATUSES:
        raise HTTPException(status_code=402, detail="Acesso financeiro indisponível.")


def _available_credits(account: BillingAccount) -> int:
    return account.plan_credits + account.extra_credits


def _debit_credits(account: BillingAccount, amount: int) -> None:
    remaining = amount
    from_plan = min(max(0, account.plan_credits), remaining)
    account.plan_credits -= from_plan
    remaining -= from_plan
    if remaining:
        account.extra_credits -= remaining


def ensure_minimum_credit(user_id: str) -> None:
    with session_scope() as db:
        account = db.get(BillingAccount, user_id)
        if account is None:
            raise HTTPException(status_code=402, detail="Você não possui créditos para continuar.")
        _ensure_financial_access(account)
        if _is_admin(account):
            return
        if _available_credits(account) < 1:
            raise HTTPException(status_code=402, detail="Créditos insuficientes para gerar uma resposta.")


def ensure_artifact_credit(user_id: str, artifact_type: str) -> None:
    normalized_type = str(artifact_type or "").strip().lower()
    label = "planilha" if normalized_type in {"xlsx", "csv", "spreadsheet", "planilha"} else "PDF"

    with session_scope() as db:
        account = db.get(BillingAccount, user_id)
        if account is None:
            raise HTTPException(status_code=402, detail=f"Saldo insuficiente para gerar {label}.")
        _ensure_financial_access(account)
        if _is_admin(account):
            return
        if _available_credits(account) < ARTIFACT_MINIMUM_CREDITS:
            raise HTTPException(status_code=402, detail=f"Saldo insuficiente para gerar {label}.")


def charge_artifact(user_id: str, artifact_type: str, idempotency_key: str | None = None) -> dict:
    normalized_type = str(artifact_type or "").strip().lower()
    label = "planilha" if normalized_type in {"xlsx", "csv", "spreadsheet", "planilha"} else "PDF"

    with session_scope() as db:
        account = db.scalar(
            select(BillingAccount)
            .where(BillingAccount.user_id == user_id)
            .with_for_update()
        )
        if account is None:
            raise HTTPException(status_code=402, detail=f"Saldo insuficiente para gerar {label}.")
        _ensure_financial_access(account)

        if idempotency_key:
            existing = db.scalar(
                select(CreditTransaction).where(CreditTransaction.stripe_event_id == idempotency_key)
            )
            if existing is not None:
                return {
                    "charged_credits": abs(int(existing.amount or 0)),
                    "remaining_credits": _available_credits(account),
                    "idempotentReplay": True,
                }

        if _is_admin(account):
            db.add(CreditTransaction(
                user_id=user_id,
                kind="admin_artifact",
                amount=0,
                plan_balance=account.plan_credits,
                extra_balance=account.extra_credits,
                stripe_event_id=idempotency_key,
                description=f"Geração administrativa de {label}"[:255],
            ))
            return {"charged_credits": 0, "remaining_credits": _available_credits(account), "admin_exempt": True}

        if _available_credits(account) < ARTIFACT_MINIMUM_CREDITS:
            raise HTTPException(status_code=402, detail=f"Saldo insuficiente para gerar {label}.")

        _debit_credits(account, ARTIFACT_MINIMUM_CREDITS)
        db.add(CreditTransaction(
            user_id=user_id,
            kind="artifact_usage",
            amount=-ARTIFACT_MINIMUM_CREDITS,
            plan_balance=account.plan_credits,
            extra_balance=account.extra_credits,
            stripe_event_id=idempotency_key,
            description=f"Geração de {label}"[:255],
        ))
        return {
            "charged_credits": ARTIFACT_MINIMUM_CREDITS,
            "remaining_credits": _available_credits(account),
            "admin_exempt": False,
        }


def charge_usage(user_id: str, result: MeteredBrainResult, idempotency_key: str | None = None) -> dict:
    usage = calculate_usage_cost(result)
    if result.provider == "local-artifact":
        with session_scope() as db:
            account = db.get(BillingAccount, user_id)
            if account is None:
                raise HTTPException(status_code=402, detail="Conta de créditos não encontrada.")
            _ensure_financial_access(account)
            remaining = _available_credits(account)
        return {
            **usage,
            "charged_credits": 0,
            "admin_exempt": False,
            "remaining_credits": remaining,
            "localArtifactDelivery": True,
        }

    with session_scope() as db:
        account = db.scalar(
            select(BillingAccount)
            .where(BillingAccount.user_id == user_id)
            .with_for_update()
        )
        if account is None:
            raise HTTPException(status_code=402, detail="Conta de créditos não encontrada.")
        _ensure_financial_access(account)

        if idempotency_key:
            existing = db.scalar(
                select(CreditTransaction).where(CreditTransaction.stripe_event_id == idempotency_key)
            )
            if existing is not None:
                return {
                    **usage,
                    "charged_credits": abs(int(existing.amount or 0)),
                    "admin_exempt": existing.kind == "admin_usage",
                    "remaining_credits": _available_credits(account),
                    "idempotentReplay": True,
                }

        if _is_admin(account):
            db.add(CreditTransaction(
                user_id=user_id,
                kind="admin_usage",
                amount=0,
                plan_balance=account.plan_credits,
                extra_balance=account.extra_credits,
                stripe_event_id=idempotency_key,
                description=(
                    f"Uso administrativo: {usage['credits']} crédito(s) medidos; "
                    f"{usage['input_tokens']} entrada, {usage['output_tokens']} saída; "
                    f"US$ {usage['cost_usd']:.8f}"
                )[:255],
            ))
            return {**usage, "charged_credits": 0, "admin_exempt": True}

        available = _available_credits(account)
        if available < usage["credits"]:
            raise HTTPException(
                status_code=402,
                detail=f"Créditos insuficientes. Esta resposta exige {usage['credits']} crédito(s) e o saldo disponível é {available}.",
            )

        _debit_credits(account, usage["credits"])
        db.add(CreditTransaction(
            user_id=user_id,
            kind="ai_usage",
            amount=-usage["credits"],
            plan_balance=account.plan_credits,
            extra_balance=account.extra_credits,
            stripe_event_id=idempotency_key,
            description=(
                f"DomnAI: {usage['input_tokens']} tokens entrada, "
                f"{usage['output_tokens']} saída; US$ {usage['cost_usd']:.8f}"
            )[:255],
        ))
        return {
            **usage,
            "charged_credits": usage["credits"],
            "admin_exempt": False,
            "remaining_credits": _available_credits(account),
            "fully_covered": True,
        }
