from app.domnai_core.contracts import ConversationResponse
from app.domnai_core.shadow_validation import (
    InMemoryShadowComparisonSink,
    ShadowValidationSettings,
    ShadowValidator,
    compare_responses,
)


def test_shadow_mode_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DOMNAI_SHADOW_VALIDATION_ENABLED", raising=False)
    monkeypatch.delenv("DOMNAI_SHADOW_SAMPLE_PERCENT", raising=False)
    settings = ShadowValidationSettings.from_env()
    assert settings.enabled is False
    assert settings.sample_percent == 0
    assert settings.selects("qualquer") is False


def test_enabled_shadow_requires_positive_sample(monkeypatch):
    monkeypatch.setenv("DOMNAI_SHADOW_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("DOMNAI_SHADOW_SAMPLE_PERCENT", "0")
    try:
        ShadowValidationSettings.from_env()
    except ValueError as exc:
        assert "amostragem" in str(exc)
    else:
        raise AssertionError("Era esperado ValueError para shadow sem amostragem.")


def test_sampling_is_deterministic():
    settings = ShadowValidationSettings(enabled=True, sample_percent=37)
    first = settings.selects("usuario:requisicao")
    assert settings.selects("usuario:requisicao") is first


def test_compare_responses_does_not_store_raw_text():
    comparison = compare_responses(
        request_id="req-1",
        legacy_text="Resposta secreta do legado",
        candidate_text="Resposta diferente do candidato",
        legacy_provider="legacy",
        candidate_provider="core",
    )
    safe = comparison.as_safe_dict()
    assert "Resposta secreta" not in str(safe)
    assert safe["legacy_length"] > 0
    assert 0 <= safe["similarity_ratio"] <= 1


def test_shadow_validator_records_candidate_without_changing_legacy_result():
    sink = InMemoryShadowComparisonSink()

    def candidate(request):
        assert request.metadata["shadow_validation"] is True
        return ConversationResponse(text="Resposta candidata", provider="core", model="stub")

    validator = ShadowValidator(
        ShadowValidationSettings(enabled=True, sample_percent=100),
        sink=sink,
        candidate=candidate,
    )
    comparison = validator.run(
        request_id="req-2",
        user_id="user-1",
        conversation_id="conversation-1",
        message="Olá",
        operation=None,
        history=[],
        legacy_text="Resposta legada",
        legacy_provider="legacy",
    )
    assert comparison is not None
    assert comparison.legacy_provider == "legacy"
    assert comparison.candidate_provider == "core"
    assert sink.items() == (comparison,)


def test_candidate_failure_is_isolated_and_recorded():
    sink = InMemoryShadowComparisonSink()

    def candidate(_request):
        raise RuntimeError("falha interna que não pode chegar ao usuário")

    validator = ShadowValidator(
        ShadowValidationSettings(enabled=True, sample_percent=100),
        sink=sink,
        candidate=candidate,
    )
    comparison = validator.run(
        request_id="req-3",
        user_id="user-1",
        conversation_id="conversation-1",
        message="Olá",
        operation=None,
        history=[],
        legacy_text="Resposta legada preservada",
        legacy_provider="legacy",
    )
    assert comparison is not None
    assert comparison.candidate_provider == "error"
    assert comparison.candidate_error == "RuntimeError"
    assert comparison.candidate_empty is True
