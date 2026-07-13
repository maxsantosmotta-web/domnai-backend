from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import LibraryAsset
from app.services.credit_meter import charge_usage, ensure_minimum_credit
from app.services.diagnosis_memory import load_diagnosis_state, save_diagnosis_state
from app.services.labor_pipeline import generate_labor_response
from app.services.labor_termination import OPERATION as LABOR_TERMINATION_OPERATION
from app.services.orchestrated_brain import generate_orchestrated_response


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatAttachmentItem(BaseModel):
    library_id: str = Field(min_length=1, max_length=180)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    operation: str | None = Field(default=None, max_length=180)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=40)
    attachments: list[ChatAttachmentItem] = Field(default_factory=list, max_length=10)


def _load_attachments(user_id: str, attachment_ids: list[str]) -> list[dict]:
    if not attachment_ids:
        return []

    unique_ids = list(dict.fromkeys(attachment_ids))
    with session_scope() as db:
        assets = db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.user_id == user_id,
                LibraryAsset.id.in_(unique_ids),
            )
        ).all()

        assets_by_id = {
            asset.id: {
                "id": asset.id,
                "name": asset.name,
                "mime_type": asset.mime_type,
                "content": bytes(asset.content or b""),
            }
            for asset in assets
        }

    missing_ids = [asset_id for asset_id in unique_ids if asset_id not in assets_by_id]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Um dos arquivos anexados não foi encontrado na Biblioteca.")

    return [assets_by_id[asset_id] for asset_id in unique_ids]


@router.post("/respond")
def respond(payload: ChatRequest, session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para continuar.")

    operation = payload.operation.strip() if payload.operation else None
    attachments = _load_attachments(
        user_id,
        [item.library_id for item in payload.attachments],
    )
    diagnosis_state = load_diagnosis_state(user_id, operation)
    history = [item.model_dump() for item in payload.history]

    ensure_minimum_credit(user_id)

    try:
        if operation == LABOR_TERMINATION_OPERATION:
            result = generate_labor_response(
                message=message,
                history=history,
                attachments=attachments,
                diagnosis_state=diagnosis_state,
            )
        else:
            result = generate_orchestrated_response(
                message=message,
                operation=operation,
                history=history,
                attachments=attachments,
                diagnosis_state=diagnosis_state,
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    usage = charge_usage(user_id, result)

    if result.diagnosis_state is not None:
        try:
            save_diagnosis_state(user_id, operation, result.diagnosis_state)
        except Exception:
            # A memória é auxiliar e nunca pode impedir a entrega da resposta.
            pass

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
