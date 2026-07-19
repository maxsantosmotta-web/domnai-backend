from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domnai_core.composition import DomnAICoreRuntime, build_domnai_core_runtime
from app.domnai_core.config import DomnAICoreSettings
from app.domnai_core.contracts import ConversationRequest, HistoryMessage
from app.domnai_core.observability import InMemoryCoreMetricsSink

router = APIRouter(prefix="/api/internal/domnai-core", tags=["domnai-core-preview"])


class PreviewHistoryItem(BaseModel):
    role: str
    content: str


class PreviewRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    operation: str | None = None
    history: list[PreviewHistoryItem] = Field(default_factory=list)
    memory: dict = Field(default_factory=dict)


@lru_cache(maxsize=1)
def get_preview_runtime() -> DomnAICoreRuntime:
    settings = DomnAICoreSettings.from_env()
    if not settings.enabled:
        raise PermissionError("Rota não habilitada.")
    return build_domnai_core_runtime(
        settings,
        metrics=InMemoryCoreMetricsSink(),
    )


@router.get("/status")
def status():
    runtime = _runtime_or_http_error()
    metrics_count = 0
    if isinstance(runtime.metrics, InMemoryCoreMetricsSink):
        metrics_count = len(runtime.metrics.items())
    return {
        "enabled": True,
        "persistence_backend": runtime.persistence_backend,
        "model": runtime.settings.model,
        "max_tool_iterations": runtime.settings.max_tool_iterations,
        "metrics_count": metrics_count,
    }


@router.post("/respond")
def respond(payload: PreviewRequest):
    runtime = _runtime_or_http_error()
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
        response = runtime.engine.respond(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, KeyError, TypeError) as exc:
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


def _runtime_or_http_error() -> DomnAICoreRuntime:
    try:
        return get_preview_runtime()
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
