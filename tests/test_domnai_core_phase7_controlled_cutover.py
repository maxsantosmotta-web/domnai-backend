from types import SimpleNamespace

import pytest

from app.domnai_core.cutover import (
    ControlledCutoverRouter,
    ControlledCutoverSettings,
    evaluate_cutover_eligibility,
)
from app.services.metered_brain import MeteredBrainResult


def _legacy(text="legado"):
    return MeteredBrainResult(
        text=text,
        provider="legacy",
        model="legacy-model",
        input_tokens=10,
        output_tokens=5,
    )


def test_cutover_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DOMNAI_CUTOVER_ENABLED", raising=False)
    monkeypatch.delenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", raising=False)
    settings = ControlledCutoverSettings.from_env()
    assert settings.enabled is False
    assert settings.traffic_percent == 0


def test_enabled_cutover_requires_positive_traffic(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "true")
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "0")
    with pytest.raises(ValueError):
        ControlledCutoverSettings.from_env()


def test_partial_cutover_requires_fallback(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "true")
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "10")
    monkeypatch.setenv("DOMNAI_CUTOVER_FALLBACK_ENABLED", "false")
    with pytest.raises(ValueError):
        ControlledCutoverSettings.from_env()


def test_eligibility_blocks_without_shadow_approval():
    settings = ControlledCutoverSettings(enabled=True, traffic_percent=100, require_shadow_approval=True)
    decision = evaluate_cutover_eligibility(
        settings=settings,
        user_id="u1",
        request_id="r1",
        attachments=[],
        local_artifact_followup=False,
        shadow_approved=False,
    )
    assert decision.selected is False
    assert decision.reason == "shadow_not_approved"


def test_eligibility_blocks_attachments_and_local_artifacts():
    settings = ControlledCutoverSettings(enabled=True, traffic_percent=100, require_shadow_approval=False)
    attachment = evaluate_cutover_eligibility(
        settings=settings,
        user_id="u1",
        request_id="r1",
        attachments=[{"id": "a1"}],
        local_artifact_followup=False,
        shadow_approved=True,
    )
    artifact = evaluate_cutover_eligibility(
        settings=settings,
        user_id="u1",
        request_id="r1",
        attachments=[],
        local_artifact_followup=True,
        shadow_approved=True,
    )
    assert attachment.reason == "attachments_not_supported"
    assert artifact.reason == "local_artifact_followup"


def test_router_uses_new_core_for_selected_request():
    settings = ControlledCutoverSettings(enabled=True, traffic_percent=100, require_shadow_approval=False)
    captured = {}

    def candidate(request):
        captured["request"] = request
        return SimpleNamespace(
            text="novo núcleo",
            provider="new-core",
            model="new-model",
            input_tokens=12,
            output_tokens=7,
            cached_input_tokens=2,
        )

    router = ControlledCutoverRouter(settings, candidate=candidate)
    routed = router.route(
        request_id="r1",
        user_id="u1",
        conversation_id="c1",
        message="Olá",
        operation=None,
        history=[{"role": "user", "content": "Antes"}],
        memory={"preference": "natural"},
        attachments=[],
        local_artifact_followup=False,
        shadow_approved=True,
        legacy=lambda: _legacy(),
    )
    assert routed.route == "new-core"
    assert routed.result.text == "novo núcleo"
    assert routed.fallback_used is False
    assert captured["request"].metadata["cutover"] is True
    assert captured["request"].metadata["user_id"] == "u1"


def test_router_falls_back_when_candidate_fails():
    settings = ControlledCutoverSettings(enabled=True, traffic_percent=100, require_shadow_approval=False)

    def candidate(_request):
        raise TimeoutError("falhou")

    router = ControlledCutoverRouter(settings, candidate=candidate)
    routed = router.route(
        request_id="r1",
        user_id="u1",
        conversation_id="c1",
        message="Olá",
        operation=None,
        history=[],
        memory=None,
        attachments=[],
        local_artifact_followup=False,
        shadow_approved=True,
        legacy=lambda: _legacy("fallback legado"),
    )
    assert routed.route == "legacy"
    assert routed.result.text == "fallback legado"
    assert routed.fallback_used is True
    assert routed.fallback_reason == "TimeoutError"


def test_router_falls_back_on_empty_candidate_response():
    settings = ControlledCutoverSettings(enabled=True, traffic_percent=100, require_shadow_approval=False)
    router = ControlledCutoverRouter(
        settings,
        candidate=lambda _request: SimpleNamespace(text="", provider="new", model="m"),
    )
    routed = router.route(
        request_id="r1",
        user_id="u1",
        conversation_id="c1",
        message="Olá",
        operation=None,
        history=[],
        memory=None,
        attachments=[],
        local_artifact_followup=False,
        shadow_approved=True,
        legacy=lambda: _legacy(),
    )
    assert routed.fallback_used is True
    assert routed.fallback_reason == "RuntimeError"


def test_disabled_router_never_calls_candidate():
    called = {"candidate": 0}

    def candidate(_request):
        called["candidate"] += 1
        return SimpleNamespace(text="novo", provider="new", model="m")

    router = ControlledCutoverRouter(ControlledCutoverSettings(), candidate=candidate)
    routed = router.route(
        request_id="r1",
        user_id="u1",
        conversation_id="c1",
        message="Olá",
        operation=None,
        history=[],
        memory=None,
        attachments=[],
        local_artifact_followup=False,
        shadow_approved=True,
        legacy=lambda: _legacy(),
    )
    assert routed.route == "legacy"
    assert routed.fallback_reason == "disabled"
    assert called["candidate"] == 0
