from app.services.artifact_decision import _requires_artifact_decision


def test_operation_remains_available_for_contextual_artifact_gate():
    history = [
        {"role": "user", "content": "Contexto detalhado da conversa com dados suficientes para consolidar."},
        {"role": "assistant", "content": "Análise detalhada construída ao longo da conversa com o usuário."},
    ] * 5

    result = _requires_artifact_decision(
        "vamos parar por aqui",
        "Diagnóstico do Negócio",
        history,
        "Resposta consolidada",
    )

    assert isinstance(result, bool)
