from app.domnai_core.contracts import ConversationRequest, HistoryMessage
from app.domnai_core.providers import OpenAIResponsesProvider


def test_provider_enforces_collection_before_final_report(monkeypatch):
    captured = {}
    provider = OpenAIResponsesProvider(api_key="test-key", model="test-model")

    def fake_request(payload):
        captured.update(payload)
        return {
            "id": "resp-test",
            "output_text": "Perfeito, anotei. Faltam apenas os itens 3 e 4.",
            "usage": {},
        }

    monkeypatch.setattr(provider, "_request", fake_request)

    response = provider.generate(
        ConversationRequest(
            message="A empresa tem três funcionários.",
            history=(
                HistoryMessage(
                    role="user",
                    content="Quero montar um relatório completo sobre minha empresa.",
                ),
                HistoryMessage(
                    role="assistant",
                    content="Preciso coletar algumas informações antes.",
                ),
            ),
        )
    )

    instructions = captured["instructions"]
    assert "PROTOCOLO OBRIGATÓRIO PARA ENTREVISTAS" in instructions
    assert "faça as perguntas em um único bloco" in instructions
    assert "Não reconstrua, não resuma e não repita" in instructions
    assert "somente quando o usuário autorizar claramente a finalização" in instructions
    assert "pergunte se pode montar a versão final" in instructions
    assert response.text.startswith("Perfeito, anotei")


def test_provider_keeps_history_available_during_collection(monkeypatch):
    captured = {}
    provider = OpenAIResponsesProvider(api_key="test-key", model="test-model")

    def fake_request(payload):
        captured.update(payload)
        return {"output_text": "Anotado.", "usage": {}}

    monkeypatch.setattr(provider, "_request", fake_request)
    provider.generate(
        ConversationRequest(
            message="O faturamento é de dez mil reais.",
            history=(
                HistoryMessage(role="user", content="Monte um diagnóstico financeiro."),
                HistoryMessage(role="assistant", content="Qual é o faturamento mensal?"),
            ),
        )
    )

    assert captured["input"][0] == {
        "role": "user",
        "content": "Monte um diagnóstico financeiro.",
    }
    assert captured["input"][1] == {
        "role": "assistant",
        "content": "Qual é o faturamento mensal?",
    }
    assert captured["input"][2]["role"] == "user"
