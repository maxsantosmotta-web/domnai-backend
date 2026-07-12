from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_authenticated_user
from app.services.domnai_brain import generate_domnai_response


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
    del session  # A autenticação é obrigatória; o usuário será usado na etapa de memória e créditos.

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para continuar.")

    try:
        result = generate_domnai_response(
            message=message,
            operation=payload.operation.strip() if payload.operation else None,
            history=[item.model_dump() for item in payload.history],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "reply": result.text,
        "provider": result.provider,
        "model": result.model,
        "operation": payload.operation,
    }
