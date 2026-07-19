from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.domnai_core_parallel import ParallelApiDependencies, build_parallel_router
from app.domnai_core.api_observability import InMemoryApiEventSink
from app.domnai_core.api_security import StaticBearerAuthenticator
from app.domnai_core.composition import DomnAICoreRuntime
from app.domnai_core.config import DomnAICoreSettings
from app.domnai_core.contracts import ConversationResponse
from app.domnai_core.memory import InMemoryMemoryStore
from app.domnai_core.observability import InMemoryCoreMetricsSink


class StubEngine:
    def __init__(self):
        self.request = None

    def respond(self, request):
        self.request = request
        return ConversationResponse(
            text="Resposta protegida.",
            provider="stub",
            model="stub-model",
            metadata={"request_id": request.metadata.get("request_id")},
        )


def _runtime(engine):
    settings = DomnAICoreSettings(
        enabled=True,
        use_postgres=False,
        ensure_schema=False,
        enable_builtin_tools=False,
        model="stub-model",
        timeout_seconds=10.0,
        max_tool_iterations=1,
    )
    return DomnAICoreRuntime(
        settings=settings,
        engine=engine,
        memory_store=InMemoryMemoryStore(),
        repository=None,
        metrics=InMemoryCoreMetricsSink(),
        persistence_backend="memory",
        registered_tools=(),
    )


def _client(scopes=("domnai:status", "domnai:respond")):
    engine = StubEngine()
    events = InMemoryApiEventSink()
    authenticator = StaticBearerAuthenticator(token="segredo", subject="user-123", scopes=scopes)
    app = FastAPI()
    app.include_router(build_parallel_router(ParallelApiDependencies(
        runtime_provider=lambda: _runtime(engine),
        authenticator=authenticator,
        events=events,
    )))
    return TestClient(app), engine, events


def test_parallel_api_rejects_missing_token():
    client, _, _ = _client()
    response = client.get("/api/parallel/domnai-core/status")
    assert response.status_code == 401


def test_parallel_api_rejects_invalid_token():
    client, _, _ = _client()
    response = client.get(
        "/api/parallel/domnai-core/status",
        headers={"Authorization": "Bearer errado"},
    )
    assert response.status_code == 401


def test_parallel_api_enforces_scope():
    client, _, events = _client(scopes=("domnai:status",))
    response = client.post(
        "/api/parallel/domnai-core/respond",
        headers={"Authorization": "Bearer segredo"},
        json={"message": "Olá", "conversation_id": "c1"},
    )
    assert response.status_code == 403
    assert events.items()[-1].status_code == 403


def test_parallel_api_propagates_subject_conversation_and_request_id():
    client, engine, events = _client()
    response = client.post(
        "/api/parallel/domnai-core/respond",
        headers={
            "Authorization": "Bearer segredo",
            "X-Request-ID": "req-externo-1",
        },
        json={"message": "Olá", "conversation_id": "conversation-7"},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-externo-1"
    assert response.json()["request_id"] == "req-externo-1"
    assert engine.request.metadata["user_id"] == "user-123"
    assert engine.request.metadata["conversation_id"] == "conversation-7"
    assert engine.request.metadata["scoped_memory"] is True
    event = events.items()[-1]
    assert event.subject == "user-123"
    assert event.conversation_id == "conversation-7"
    assert event.status_code == 200


def test_status_is_protected_and_does_not_expose_secrets():
    client, _, events = _client()
    response = client.get(
        "/api/parallel/domnai-core/status",
        headers={"Authorization": "Bearer segredo"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert "token" not in str(payload).lower()
    assert events.items()[-1].route == "/status"
