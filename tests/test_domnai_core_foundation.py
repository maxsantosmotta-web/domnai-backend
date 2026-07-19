import pytest

from app.domnai_core import (
    ConversationEngine,
    ConversationRequest,
    ConversationResponse,
    HistoryMessage,
)


class StubProvider:
    def __init__(self) -> None:
        self.received = None

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.received = request
        return ConversationResponse(
            text="Resposta natural do novo núcleo.",
            provider="stub",
            model="stub-model",
            input_tokens=12,
            output_tokens=7,
        )


def test_engine_preserves_free_conversation_request_without_legacy_dependencies():
    provider = StubProvider()
    engine = ConversationEngine(provider)
    request = ConversationRequest(
        message="Chat, me ajuda a organizar essa ideia?",
        history=(HistoryMessage(role="user", content="Tenho um novo projeto."),),
        operation="Plano de Ação Empresarial",
        memory={"project": "novo produto"},
    )

    response = engine.respond(request)

    assert provider.received is request
    assert response.text == "Resposta natural do novo núcleo."
    assert response.provider == "stub"
    assert response.input_tokens == 12
    assert response.output_tokens == 7


def test_operation_is_optional_context_not_a_required_route():
    provider = StubProvider()
    engine = ConversationEngine(provider)

    response = engine.respond(ConversationRequest(message="Tudo bem?"))

    assert response.provider == "stub"
    assert provider.received.operation is None


def test_empty_user_message_is_rejected_at_the_core_boundary():
    with pytest.raises(ValueError, match="message não pode ser vazio"):
        ConversationRequest(message="   ")


def test_provider_must_return_core_response_contract():
    class InvalidProvider:
        def generate(self, request):
            return "texto solto"

    with pytest.raises(TypeError, match="ConversationResponse"):
        ConversationEngine(InvalidProvider()).respond(ConversationRequest(message="Olá"))


def test_negative_usage_is_rejected():
    with pytest.raises(ValueError, match="input_tokens não pode ser negativo"):
        ConversationResponse(
            text="Resposta",
            provider="stub",
            model="stub",
            input_tokens=-1,
        )
