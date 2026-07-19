from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI

from app.api.domnai_core_parallel import ParallelApiDependencies, build_parallel_router
from app.domnai_core.api_observability import InMemoryApiEventSink
from app.domnai_core.api_security import StaticBearerAuthenticator, TokenAuthenticator
from app.domnai_core.clerk_authenticator import ClerkTokenAuthenticator
from app.domnai_core.composition import DomnAICoreRuntime, build_domnai_core_runtime
from app.domnai_core.parallel_api_config import ParallelApiSettings


@lru_cache(maxsize=1)
def get_parallel_runtime() -> DomnAICoreRuntime:
    return build_domnai_core_runtime()


@lru_cache(maxsize=1)
def get_parallel_events() -> InMemoryApiEventSink:
    return InMemoryApiEventSink()


def build_parallel_authenticator(settings: ParallelApiSettings) -> TokenAuthenticator:
    if settings.auth_mode == "static":
        return StaticBearerAuthenticator(
            token=settings.static_token,
            subject=settings.static_subject,
            scopes=settings.scopes,
        )
    return ClerkTokenAuthenticator(scopes=settings.scopes)


def mount_parallel_api(
    app: FastAPI,
    *,
    settings: ParallelApiSettings | None = None,
    runtime_provider=get_parallel_runtime,
    events=None,
) -> bool:
    resolved = settings or ParallelApiSettings.from_env()
    if not resolved.enabled:
        return False
    app.include_router(
        build_parallel_router(
            ParallelApiDependencies(
                runtime_provider=runtime_provider,
                authenticator=build_parallel_authenticator(resolved),
                events=events or get_parallel_events(),
            )
        )
    )
    return True
