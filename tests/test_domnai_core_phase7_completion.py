from __future__ import annotations

from types import SimpleNamespace

from app.domnai_core.cutover import ControlledCutoverSettings
from app.domnai_core.cutover_runtime import route_brain_request
from app.services.metered_brain import MeteredBrainResult


def legacy_result(text: str = "legado") -> MeteredBrainResult:
    return MeteredBrainResult(
        text=text,
        provider="legacy",
        model="legacy-model",
        input_tokens=1,
        output_tokens=1,
    )


def test_runtime_uses_legacy_when_cutover_is_disabled(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "false")
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "0")
    routed = route_brain_request(
        request_id="req-disabled",
        user_id="user-1",
        conversation_id="conv-1",
        message="olá",
        operation=None,
        history=[],
        memory=None,
        attachments=[],
        local_artifact_followup=False,
        legacy=legacy_result,
    )
    assert routed.route == "legacy"
    assert routed.result.text == "legado"
    assert routed.fallback_reason == "disabled"


def test_runtime_rolls_back_on_invalid_configuration(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "true")
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "0")
    routed = route_brain_request(
        request_id="req-invalid",
        user_id="user-1",
        conversation_id="conv-1",
        message="olá",
        operation=None,
        history=[],
        memory=None,
        attachments=[],
        local_artifact_followup=False,
        legacy=legacy_result,
    )
    assert routed.route == "legacy"
    assert routed.fallback_used is True
    assert routed.fallback_reason == "invalid_config"


def test_cutover_settings_default_to_zero_traffic(monkeypatch):
    for name in (
        "DOMNAI_CUTOVER_ENABLED",
        "DOMNAI_CUTOVER_TRAFFIC_PERCENT",
        "DOMNAI_CUTOVER_REQUIRE_SHADOW_APPROVAL",
        "DOMNAI_CUTOVER_FALLBACK_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = ControlledCutoverSettings.from_env()
    assert settings.enabled is False
    assert settings.traffic_percent == 0
    assert settings.fallback_enabled is True


def test_worker_bootstrap_installs_single_patch(monkeypatch):
    import app.services.cutover_worker_bootstrap as bootstrap

    monkeypatch.setattr(bootstrap, "_patched", False)
    bootstrap.install_cutover_router()
    first_process = bootstrap.worker._process_task
    first_generate = bootstrap.worker.generate_orchestrated_response
    bootstrap.install_cutover_router()
    assert bootstrap.worker._process_task is first_process
    assert bootstrap.worker.generate_orchestrated_response is first_generate


def test_routed_generate_preserves_cutover_timings(monkeypatch):
    import app.services.cutover_worker_bootstrap as bootstrap

    bootstrap._context.task_id = "task-1"
    bootstrap._context.user_id = "user-1"
    bootstrap._context.local_artifact_followup = False
    monkeypatch.setattr(
        bootstrap,
        "route_brain_request",
        lambda **kwargs: SimpleNamespace(
            result=legacy_result("novo"),
            route="new-core",
            fallback_used=False,
        ),
    )
    result = bootstrap._routed_generate(
        message="teste",
        operation=None,
        history=[],
        attachments=[],
        diagnosis_state=None,
    )
    assert result.text == "novo"
    assert result.timings["cutover_route_new_core"] == 1
    assert result.timings["cutover_fallback"] == 0
