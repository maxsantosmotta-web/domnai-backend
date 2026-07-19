import pytest
from fastapi import HTTPException

from app.api import domnai_core_preview
from app.domnai_core.composition import DomnAICoreRuntime, build_domnai_core_runtime
from app.domnai_core.config import DomnAICoreSettings
from app.domnai_core.contracts import ConversationRequest, ConversationResponse
from app.domnai_core.engine import ConversationEngine
from app.domnai_core.observability import InMemoryCoreMetricsSink


class StubProvider:
    def generate(self, request: ConversationRequest) -> ConversationResponse:
        return ConversationResponse(
            text="ok",
            provider="stub",
            model="stub-model",
            input_tokens=4,
            output_tokens=2,
        )


class FailingProvider:
    def generate(self, request: ConversationRequest) -> ConversationResponse:
        raise RuntimeError("falha controlada")


def settings(**overrides):
    values = {
        "enabled": True,
        "use_postgres": False,
        "ensure_schema": False,
        "enable_builtin_tools": True,
        "model": "test-model",
        "timeout_seconds": 10.0,
        "max_tool_iterations": 2,
    }
    values.update(overrides)
    return DomnAICoreSettings(**values)


def test_settings_are_loaded_and_validated_from_environment(monkeypatch):
    monkeypatch.setenv("DOMNAI_CORE_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("DOMNAI_CORE_USE_POSTGRES", "false")
    monkeypatch.setenv("DOMNAI_CORE_ENABLE_BUILTIN_TOOLS", "true")
    monkeypatch.setenv("DOMNAI_CORE_MODEL", "model-x")
    monkeypatch.setenv("DOMNAI_CORE_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("DOMNAI_CORE_MAX_TOOL_ITERATIONS", "4")

    loaded = DomnAICoreSettings.from_env()

    assert loaded.enabled is True
    assert loaded.enable_builtin_tools is True
    assert loaded.model == "model-x"
    assert loaded.timeout_seconds == 12.5
    assert loaded.max_tool_iterations == 4


def test_invalid_timeout_is_rejected(monkeypatch):
    monkeypatch.setenv("DOMNAI_CORE_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValueError, match="maior que zero"):
        DomnAICoreSettings.from_env()


def test_runtime_uses_memory_backend_without_touching_database():
    runtime = build_domnai_core_runtime(settings())
    assert runtime.persistence_backend == "memory"
    assert runtime.settings.model == "test-model"
    assert runtime.registered_tools == (
        "analyze_text",
        "calculate_expression",
        "extract_keywords",
        "normalize_text",
    )


def test_runtime_can_disable_builtin_tools_explicitly():
    runtime = build_domnai_core_runtime(settings(enable_builtin_tools=False))
    assert runtime.registered_tools == ()


def test_postgres_mode_requires_configured_database(monkeypatch):
    monkeypatch.setattr("app.domnai_core.composition.is_database_configured", lambda: False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        build_domnai_core_runtime(settings(use_postgres=True))


def test_engine_records_success_and_error_metrics():
    success_metrics = InMemoryCoreMetricsSink()
    response = ConversationEngine(StubProvider(), metrics=success_metrics).respond(
        ConversationRequest(message="Olá")
    )
    assert response.text == "ok"
    assert success_metrics.items()[0].outcome == "success"
    assert success_metrics.items()[0].input_tokens == 4

    error_metrics = InMemoryCoreMetricsSink()
    with pytest.raises(RuntimeError, match="falha controlada"):
        ConversationEngine(FailingProvider(), metrics=error_metrics).respond(
            ConversationRequest(message="Olá")
        )
    assert error_metrics.items()[0].outcome == "error"


def test_preview_status_uses_composed_runtime(monkeypatch):
    metrics = InMemoryCoreMetricsSink()
    runtime = DomnAICoreRuntime(
        settings=settings(),
        engine=ConversationEngine(StubProvider(), metrics=metrics),
        metrics=metrics,
        persistence_backend="memory",
        registered_tools=("calculate_expression",),
    )
    monkeypatch.setattr(domnai_core_preview, "get_preview_runtime", lambda: runtime)

    result = domnai_core_preview.status()

    assert result["enabled"] is True
    assert result["persistence_backend"] == "memory"
    assert result["metrics_count"] == 0


def test_preview_disabled_returns_404(monkeypatch):
    def disabled():
        raise PermissionError("Rota não habilitada.")

    monkeypatch.setattr(domnai_core_preview, "get_preview_runtime", disabled)
    with pytest.raises(HTTPException) as exc_info:
        domnai_core_preview.status()
    assert exc_info.value.status_code == 404
