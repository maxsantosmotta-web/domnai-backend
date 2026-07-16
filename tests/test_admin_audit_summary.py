from app.api.chat_state import _has_completed_response


def test_completed_response_is_countable():
    assert _has_completed_response([
        {
            "role": "assistant",
            "text": "Resposta concluída e entregue ao usuário.",
            "processing": False,
            "isError": False,
        }
    ]) is True


def test_empty_or_processing_room_is_not_countable():
    assert _has_completed_response([]) is False
    assert _has_completed_response([
        {
            "role": "assistant",
            "text": "DomnAI está analisando...",
            "processing": True,
            "isError": False,
        }
    ]) is False


def test_error_only_room_is_not_countable():
    assert _has_completed_response([
        {
            "role": "assistant",
            "text": "Não foi possível concluir.",
            "processing": False,
            "isError": True,
        }
    ]) is False
