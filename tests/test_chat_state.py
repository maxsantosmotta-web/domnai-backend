from app.api.chat_state import _safe_messages


def test_safe_messages_preserves_long_assistant_response_without_truncation():
    original = "Início do diagnóstico\n" + ("detalhe completo " * 1800) + "\nFIM_CONFIRMADO"

    saved = _safe_messages([
        {
            "id": "assistant-long",
            "role": "assistant",
            "text": original,
            "attachments": [],
            "sources": [],
            "isError": False,
            "processing": False,
        }
    ])

    assert len(original) > 20000
    assert saved[0]["text"] == original
    assert saved[0]["text"].endswith("FIM_CONFIRMADO")
