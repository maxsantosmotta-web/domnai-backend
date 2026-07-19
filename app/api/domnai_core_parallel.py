from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.domnai_core.api_observability import ApiEventSink, ApiRequestEvent, ApiRequestTimer, NullApiEventSink
from app.domnai_core.api_security import (
    ApiPrincipal,
    AuthenticationError,
    AuthorizationError,
    TokenAuthenticator,
    extract_bearer_token,
)
from app.domnai_core.composition import DomnAICoreRuntime
from app.domnai_core.contracts import ConversationRequest, HistoryMessage


class ParallelHistoryItem(BaseModel):
    role: str
    content: str


class ParallelRespondRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    conversation_id: str = Field(min_length=1, max_length=255)
    history: list[ParallelHistoryItem] = Field(default_factory=list, max_length=200)
    memory: dict = Field(default_factory=dict)
    operation: str | None = Field(default=None, max_length=100)


@dataclass(frozen=True, slots=True)
class ParallelApiDependencies:
    runtime_provider: Callable[[], DomnAICoreRuntime]
    authenticator: TokenAuthenticator
    events: ApiEventSink = NullApiEventSink()


def build_parallel_router(dependencies: ParallelApiDependencies) -> APIRouter:
    router = APIRouter(prefix="/api/parallel/domnai-core", tags=["domnai-core-parallel"])

    def principal_from_header(authorization: str | None) -> ApiPrincipal:
        try:
            token = extract_bearer_token(authorization)
            return dependencies.authenticator.authenticate(token)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc

    @router.get("/status")
    def status(response: Response, authorization: str | None = Header(default=None)):
        request_id = uuid4().hex
        timer = ApiRequestTimer()
        principal = principal_from_header(authorization)
        try:
            principal.require("domnai:status")
            runtime = dependencies.runtime_provider()
            payload = {
                "enabled": True,
                "model": runtime.settings.model,
                "persistence_backend": runtime.persistence_backend,
                "registered_tools": runtime.registered_tools,
                "request_id": request_id,
            }
            response.headers["X-Request-ID"] = request_id
            dependencies.events.record(ApiRequestEvent(
                request_id=request_id,
                route="/status",
                method="GET",
                status_code=200,
                duration_ms=timer.elapsed_ms(),
                subject=principal.subject,
            ))
            return payload
        except AuthorizationError as exc:
            dependencies.events.record(ApiRequestEvent(
                request_id=request_id,
                route="/status",
                method="GET",
                status_code=403,
                duration_ms=timer.elapsed_ms(),
                subject=principal.subject,
                error_type=type(exc).__name__,
            ))
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @router.post("/respond")
    def respond(
        payload: ParallelRespondRequest,
        response: Response,
        authorization: str | None = Header(default=None),
        x_request_id: str | None = Header(default=None),
    ):
        request_id = (x_request_id or "").strip()[:128] or uuid4().hex
        timer = ApiRequestTimer()
        principal = principal_from_header(authorization)
        try:
            principal.require("domnai:respond")
            runtime = dependencies.runtime_provider()
            request = ConversationRequest(
                message=payload.message,
                history=tuple(
                    HistoryMessage(role=item.role, content=item.content)
                    for item in payload.history
                    if item.role in {"system", "user", "assistant", "tool"}
                ),
                operation=payload.operation,
                memory=payload.memory,
                metadata={
                    "request_id": request_id,
                    "conversation_id": payload.conversation_id,
                    "user_id": principal.subject,
                    "scoped_memory": True,
                    "api_surface": "parallel",
                },
            )
            result = runtime.engine.respond(request)
            response.headers["X-Request-ID"] = request_id
            dependencies.events.record(ApiRequestEvent(
                request_id=request_id,
                route="/respond",
                method="POST",
                status_code=200,
                duration_ms=timer.elapsed_ms(),
                subject=principal.subject,
                conversation_id=payload.conversation_id,
            ))
            return {
                "text": result.text,
                "provider": result.provider,
                "model": result.model,
                "request_id": request_id,
                "usage": {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cached_input_tokens": result.cached_input_tokens,
                },
                "metadata": result.metadata,
            }
        except AuthorizationError as exc:
            status_code = 403
            error = exc
        except ValueError as exc:
            status_code = 422
            error = exc
        except (RuntimeError, KeyError, TypeError) as exc:
            status_code = 503
            error = exc
        dependencies.events.record(ApiRequestEvent(
            request_id=request_id,
            route="/respond",
            method="POST",
            status_code=status_code,
            duration_ms=timer.elapsed_ms(),
            subject=principal.subject,
            conversation_id=payload.conversation_id,
            error_type=type(error).__name__,
        ))
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return router
