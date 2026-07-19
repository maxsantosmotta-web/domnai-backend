from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domnai_core.api_observability import InMemoryApiEventSink
from app.domnai_core.clerk_authenticator import ClerkTokenAuthenticator
from app.domnai_core.contracts import ConversationResponse
from app.domnai_core.parallel_api_bootstrap import mount_parallel_api
from app.domnai_core.parallel_api_config import ParallelApiSettings


class StubEngine:
    def respond(self, request):
        return ConversationResponse(
            text="ok",
            provider="stub",
            model="stub",
            metadata={"request_id": request.metadata.get("request_id")},
        )


def _runtime():
    return SimpleNamespace(
        settings=SimpleNamespace(model="stub"),
        engine=StubEngine(),
        persistence_backend="memory",
        registered_tools=(),
    )


def test_parallel_api_is_not_mounted_when_disabled():
    app = FastAPI()
    mounted = mount_parallel_api(
        app,
        settings=ParallelApiSettings(enabled=False),
        runtime_provider=_runtime,
    )
    assert mounted is False
    assert TestClient(app).get("/api/parallel/domnai-core/status").status_code == 404


def test_parallel_api_mounts_with_static_auth_and_can_be_disabled_immediately():
    settings = ParallelApiSettings(
        enabled=True,
        auth_mode="static",
        static_token="segredo",
        static_subject="tester",
    )
    app = FastAPI()
    events = InMemoryApiEventSink()
    assert mount_parallel_api(app, settings=settings, runtime_provider=_runtime, events=events) is True
    client = TestClient(app)
    assert client.get("/api/parallel/domnai-core/status").status_code == 401
    response = client.get(
        "/api/parallel/domnai-core/status",
        headers={"Authorization": "Bearer segredo"},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert events.items()[-1].subject == "tester"


def test_clerk_authenticator_uses_existing_identity_and_rejects_missing_subject():
    authenticator = ClerkTokenAuthenticator(
        scopes=("domnai:status",),
        verifier=lambda token: {"sub": "clerk-user", "sid": "session"},
    )
    principal = authenticator.authenticate("jwt")
    assert principal.subject == "clerk-user"
    principal.require("domnai:status")

    invalid = ClerkTokenAuthenticator(
        scopes=("domnai:status",),
        verifier=lambda token: {},
    )
    try:
        invalid.authenticate("jwt")
    except PermissionError as exc:
        assert "usuário" in str(exc)
    else:
        raise AssertionError("Era esperado bloqueio de sessão sem usuário.")


def test_typed_settings_default_to_disabled(monkeypatch):
    for name in (
        "DOMNAI_PARALLEL_API_ENABLED",
        "DOMNAI_PARALLEL_API_AUTH_MODE",
        "DOMNAI_PARALLEL_API_STATIC_TOKEN",
        "DOMNAI_PARALLEL_API_SCOPES",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = ParallelApiSettings.from_env()
    assert settings.enabled is False
    assert settings.auth_mode == "clerk"


def test_enabled_static_mode_requires_token(monkeypatch):
    monkeypatch.setenv("DOMNAI_PARALLEL_API_ENABLED", "true")
    monkeypatch.setenv("DOMNAI_PARALLEL_API_AUTH_MODE", "static")
    monkeypatch.delenv("DOMNAI_PARALLEL_API_STATIC_TOKEN", raising=False)
    try:
        ParallelApiSettings.from_env()
    except ValueError as exc:
        assert "STATIC_TOKEN" in str(exc)
    else:
        raise AssertionError("Era esperado bloqueio de modo static sem token.")
