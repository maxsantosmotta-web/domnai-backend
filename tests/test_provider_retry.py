from io import BytesIO
from unittest.mock import patch
from urllib import error

import pytest

from app.services.domnai_brain import _post_json


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def _http_error(code: int, body: bytes = b'{"error":{"message":"internal request req_secret"}}'):
    return error.HTTPError(
        url="https://provider.test",
        code=code,
        msg="provider error",
        hdrs=None,
        fp=BytesIO(body),
    )


def test_retries_once_after_transient_500_and_returns_success():
    effects = [_http_error(500), _Response(b'{"ok": true}')]
    with patch("app.services.domnai_brain.request.urlopen", side_effect=effects) as urlopen:
        result = _post_json("https://provider.test", {}, {"input": "hello"})

    assert result == {"ok": True}
    assert urlopen.call_count == 2


def test_second_transient_failure_returns_clean_user_message():
    effects = [_http_error(500), _http_error(500)]
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


def test_permanent_400_is_not_retried_or_exposed():
    with patch(
        "app.services.domnai_brain.request.urlopen",
        side_effect=_http_error(400, b'{"error":{"message":"sensitive detail"}}'),
    ) as urlopen:
        with pytest.raises(RuntimeError) as raised:
            _post_json("https://provider.test", {}, {"input": "hello"})

    assert urlopen.call_count == 1
    assert str(raised.value) == "Não foi possível processar esta solicitação no momento. Tente novamente."
    assert "sensitive detail" not in str(raised.value)
