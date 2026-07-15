from io import BytesIO
from unittest.mock import patch
from urllib import error

import pytest

from app.services.artifact_decision import _requires_artifact_decision
from app.services.domnai_brain import _post_json
from app.services.metered_brain import MeteredBrainResult
from app.services.orchestrated_brain import (
    _specialized_engine,
    generate_orchestrated_response,
)


class _ProviderResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def _provider_http_error(code: int, body: bytes = b'{"error":{"message":"internal request req_secret"}}'):
    return error.HTTPError(
        url="https://provider.test",
        code=code,
        msg="provider error",
        hdrs=None,
        fp=BytesIO(body),
    )


def base_result(text="Resposta-base"):
    return MeteredBrainResult(
        text=text,
        provider="test-provider",
        model="test-model",
        input_tokens=10,
        output_tokens=5,
        cached_input_tokens=0,
        diagnosis_state={"status": "kept"},
        timings={"generation_ms": 12},
    )


def test_operation_name_routes_to_labor_engine():
    assert _specialized_engine(
        plan={},
        operation="Cálculo de Rescisão Trabalhista",
        message="Preciso de ajuda.",
    ) == "labor_termination"


def test_natural_language_routes_to_labor_engine_without_frontend_operation():
    assert _specialized_engine(
        plan={},
        operation=None,
        message="Quero calcular minha rescisão.",
    ) == "labor_termination"


def test_orchestrator_plan_can_select_labor_engine():
    assert _specialized_engine(
        plan={"specialized_engine": "labor_termination"},
        operation=None,
        message="Analise este caso.",
    ) == "labor_termination"


def test_unrelated_operation_does_not_route_to_labor_engine():
    assert _specialized_engine(
        plan={"specialized_engine": None},
        operation="Análise Contratual",
        message="Revise as cláusulas deste contrato.",
    ) is None


def test_general_operation_skips_orchestrator_and_preserves_base_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = []

    def fake_openai_request(_api_key, payload):
        calls.append(payload)
        raise AssertionError("Operação geral não deve chamar o orquestrador")

    monkeypatch.setattr("app.services.orchestrated_brain._openai_request", fake_openai_request)
    monkeypatch.setattr(
        "app.services.orchestrated_brain.generate_metered_response",
        lambda **_kwargs: base_result(),
    )

    result = generate_orchestrated_response(
        message="Analise este contrato.",
        history=[],
        operation="Análise Contratual",
        attachments=[],
        diagnosis_state=None,
    )

    assert calls == []
    assert result.text == "Resposta-base"
    assert result.provider == "direct:test-provider"
    assert result.diagnosis_state == {"status": "kept"}
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.timings["generation_ms"] == 12
    assert result.timings["orchestrator_ms"] == 0


def test_general_response_does_not_depend_on_orchestrator_availability(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.orchestrated_brain._openai_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("orchestrator unavailable")),
    )
    monkeypatch.setattr(
        "app.services.orchestrated_brain.generate_metered_response",
        lambda **_kwargs: base_result("Resposta preservada"),
    )

    result = generate_orchestrated_response(
        message="Compare duas opções.",
        history=[],
        operation="Comparação",
        attachments=[],
        diagnosis_state={"status": "kept"},
    )

    assert result.text == "Resposta preservada"
    assert result.provider == "direct:test-provider"
    assert result.diagnosis_state == {"status": "kept"}
    assert result.timings["orchestrator_ms"] == 0


def test_without_openai_key_uses_existing_base_flow(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.orchestrated_brain.generate_metered_response",
        lambda **_kwargs: base_result("Fluxo-base sem chave"),
    )

    result = generate_orchestrated_response(
        message="Compare duas alternativas para mim.",
        history=[],
        operation=None,
        attachments=[],
        diagnosis_state=None,
    )

    assert result.text == "Fluxo-base sem chave"
    assert result.provider == "direct:test-provider"
    assert result.timings["orchestrator_ms"] == 0


def test_provider_retries_once_after_transient_500_and_returns_success():
    effects = [_provider_http_error(500), _ProviderResponse(b'{"ok": true}')]
    with patch("app.services.domnai_brain.request.urlopen", side_effect=effects) as urlopen:
        result = _post_json("https://provider.test", {}, {"input": "hello"})

    assert result == {"ok": True}
    assert urlopen.call_count == 2


def test_repeated_provider_500_returns_clean_user_message():
    effects = [_provider_http_error(500), _provider_http_error(500)]
    with patch("app.services.domnai_brain.request.urlopen", side_effect=effects) as urlopen:
        with pytest.raises(RuntimeError) as raised:
            _post_json("https://provider.test", {}, {"input": "hello"})

    message = str(raised.value)
    assert urlopen.call_count == 2
    assert message == (
        "O serviço de inteligência está temporariamente indisponível. "
        "Tente novamente em alguns segundos."
    )
    assert "req_secret" not in message
    assert "server_error" not in message


def test_provider_400_is_not_retried_or_exposed():
    with patch(
        "app.services.domnai_brain.request.urlopen",
        side_effect=_provider_http_error(400, b'{"error":{"message":"sensitive detail"}}'),
    ) as urlopen:
        with pytest.raises(RuntimeError) as raised:
            _post_json("https://provider.test", {}, {"input": "hello"})

    assert urlopen.call_count == 1
    assert str(raised.value) == "Não foi possível processar esta solicitação no momento. Tente novamente."
    assert "sensitive detail" not in str(raised.value)


def test_completed_operation_can_offer_artifact_once():
    assert _requires_artifact_decision(
        "Conclua meu plano",
        "Plano de Ação Empresarial",
        [],
        "x" * 1200,
    ) is True


def test_previous_pdf_offer_is_not_repeated_when_user_changes_subject():
    history = [{
        "role": "assistant",
        "content": "Posso transformar este conteúdo em PDF e enviar aqui no chat.",
    }]
    assert _requires_artifact_decision(
        "Agora quero falar de outro assunto",
        "Plano de Ação Empresarial",
        history,
        "x" * 1200,
    ) is False


def test_accepting_previous_offer_allows_pdf_creation():
    history = [{
        "role": "assistant",
        "content": "Posso transformar este conteúdo em PDF e enviar aqui no chat.",
    }]
    assert _requires_artifact_decision(
        "Sim, pode gerar",
        "Plano de Ação Empresarial",
        history,
        "Conteúdo concluído",
    ) is True


def test_existing_artifact_link_request_does_not_start_new_generation():
    history = [{
        "role": "assistant",
        "content": "Arquivo criado e enviado no chat.",
    }]
    assert _requires_artifact_decision(
        "Manda o link do arquivo",
        "Plano de Ação Empresarial",
        history,
        "Arquivo já existente",
    ) is False
