from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domnai_core import ConversationEngine, ConversationRequest, HistoryMessage
from app.domnai_core.memory import InMemoryMemoryStore
from app.domnai_core.persistence import InMemoryConversationRepository
from app.domnai_core.providers import OpenAIResponsesProvider

router = APIRouter(prefix="/api/internal/domnai-core", tags=["domnai-core-preview"])

_memory = InMemoryMemoryStore()
_repository = InMemoryConversationRepository()
_engine = ConversationEngine(
    OpenAIResponsesProvider(),
    memory_store=_memory,
    repository=_repository,
)


class PreviewHistoryItem(BaseModel):
    role: str
    content: str


class PreviewRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    operation: str | None = None
    history: list[PreviewHistoryItem] = Field(default_factory=list)
    memory: dict = Field(default_factory=dict)


@router.post("/respond")
def respond(payload: PreviewRequest):
    if os.getenv("DOMNAI_CORE_PREVIEW_ENABLED", "").strip().lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Rota não habilitada.")

    try:
        request = ConversationRequest(
            message=payload.message,
            history=tuple(
                HistoryMessage(role=item.role, content=item.content)
                for item in payload.history
                if item.role in {"system", "user", "assistant", "tool"}
            ),
            operation=payload.operation,
            memory=payload.memory,
            metadata={"conversation_id": payload.conversation_id or ""},
        )
        response = _engine.respond(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "text": response.text,
        "provider": response.provider,
        "model": response.model,
        "usage": {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cached_input_tokens": response.cached_input_tokens,
        },
        "metadata": response.metadata,
    }
