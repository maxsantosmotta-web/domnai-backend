import math
import os

from fastapi import HTTPException
from sqlalchemy import select

from app.database import session_scope
from app.models import BillingAccount, CreditTransaction
from app.services.metered_brain import MeteredBrainResult

ADMIN_CREDITS = 100000
DEFAULT_USD_PER_CREDIT = 0.001

MODEL_RATES_USD_PER_MILLION = {
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
}


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def calculate_usage_cost(result: MeteredBrainResult) -> dict:
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


def ensure_minimum_credit(user_id: str) -> None:
    with session_scope() as db:
        account = db.get(BillingAccount, user_id)
        if account is None:
            raise HTTPException(status_code=402, detail="Você não possui créditos para continuar.")
        if account.plan_credits >= ADMIN_CREDITS:
            return
        if account.plan_credits + account.extra_credits < 1:
            raise HTTPException(status_code=402, detail="Créditos insuficientes para gerar uma resposta.")


def charge_usage(user_id: str, result: MeteredBrainResult, idempotency_key: str | None = None) -> dict:
    usage = calculate_usage_cost(result)
    with session_scope() as db:
        if idempotency_key:
            existing = db.scalar(
                select(CreditTransaction).where(CreditTransaction.stripe_event_id == idempotency_key)
            )
            if existing is not None:
                account = db.get(BillingAccount, user_id)
                return {
                    **usage,
                    "charged_credits": abs(int(existing.amount or 0)),
                    "admin_exempt": existing.kind == "admin_usage",
                    "remaining_credits": (account.plan_credits + account.extra_credits) if account else 0,
                    "idempotentReplay": True,
                }

        account = db.get(BillingAccount, user_id)
        if account is None:
            raise HTTPException(status_code=402, detail="Conta de créditos não encontrada.")

        is_admin = account.plan_credits >= ADMIN_CREDITS
        if is_admin:
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

        available = account.plan_credits + account.extra_credits
        charged = min(available, usage["credits"])
        remaining = charged
        from_plan = min(account.plan_credits, remaining)
        account.plan_credits -= from_plan
        remaining -= from_plan
        if remaining:
            account.extra_credits -= remaining

        db.add(CreditTransaction(
            user_id=user_id,
            kind="ai_usage",
            amount=-charged,
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
            "charged_credits": charged,
            "admin_exempt": False,
            "remaining_credits": account.plan_credits + account.extra_credits,
            "fully_covered": charged == usage["credits"],
        }
