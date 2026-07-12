from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_authenticated_user
from app.services.credit_meter import charge_usage, ensure_minimum_credit
from app.services.metered_brain import generate_metered_response


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    operation: str | None = Field(default=None, max_length=180)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=40)


@router.post("/respond")
def respond(payload: ChatRequest, session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para continuar.")

    # Impede nova chamada paga quando o usuário não possui nem o crédito mínimo.
    ensure_minimum_credit(user_id)

    try:
        result = generate_metered_response(
            message=message,
            operation=payload.operation.strip() if payload.operation else None,
            history=[item.model_dump() for item in payload.history],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    usage = charge_usage(user_id, result)

    return {
        "reply": result.text,
        "provider": result.provider,
        "model": result.model,
        "operation": payload.operation,
        "usage": {
            "inputTokens": usage["input_tokens"],
            "cachedInputTokens": usage["cached_input_tokens"],
            "outputTokens": usage["output_tokens"],
            "costUsd": round(usage["cost_usd"], 8),
            "measuredCredits": usage["credits"],
            "chargedCredits": usage["charged_credits"],
            "adminExempt": usage["admin_exempt"],
            "remainingCredits": usage.get("remaining_credits"),
        },
    }
