from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from urllib import error

import pytest


def _load_patch_module():
    path = Path("scripts/fix_chat_worker_operation_scope.py")
    spec = importlib.util.spec_from_file_location("fix_chat_worker_operation_scope", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _http_error(code: int, retry_after: str | None = None) -> error.HTTPError:
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return error.HTTPError("https://api.openai.com/v1/responses", code, "error", headers, io.BytesIO(b"{}"))


def _prepare_runtime(tmp_path, monkeypatch):
    module = _load_patch_module()
    brain = tmp_path / "domnai_brain.py"
    brain.write_text(
        """import json
import os
from urllib import error, request


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int = 75) -> dict:
    body = json.dumps(payload).encode()
    transient_codes = {500, 502, 503, 504}
    for attempt in range(2):
        req = request.Request(url, data=body, headers=headers, method='POST')
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())


def _integration_api_key():
    return ''
""",
        encoding="utf-8",
    )
    orchestrator = tmp_path / "orchestrated_brain.py"
    orchestrator.write_text(
        """def _normalized_text(value):
    return str(value or '').casefold().strip()


def _simple_conversation_response(message, attachments, history):
    if attachments:
        return None
    normalized = " ".join(_normalized_text(message).replace("?", "").replace("!", "").split())
    greeting_messages = {
        "oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai",
        "chat tudo bem", "chat, tudo bem", "tudo bem", "como voce esta", "como vai",
    }
    if normalized in greeting_messages and not history:
        return "Tudo ótimo! E com você? Como posso ajudar hoje?"
    return None
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "BRAIN_PATH", brain)
    monkeypatch.setattr(module, "ORCHESTRATOR_PATH", orchestrator)
    module._fix_openai_retry()
    module._fix_simple_conversation()
    return brain, orchestrator


def test_http_429_retry_after_then_success(tmp_path, monkeypatch):
    brain, _ = _prepare_runtime(tmp_path, monkeypatch)
    namespace = {}
    exec(brain.read_text(encoding="utf-8"), namespace)
    calls = []
    sleeps = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"ok": True}).encode()

    def fake_urlopen(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise _http_error(429, "2")
        return Response()

    monkeypatch.setattr(namespace["request"], "urlopen", fake_urlopen)
    monkeypatch.setattr(namespace["time"], "sleep", sleeps.append)
    assert namespace["_post_json"]("https://api.openai.com/v1/responses", {}, {}) == {"ok": True}
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_http_429_persistent_stops_after_safe_limit(tmp_path, monkeypatch):
    brain, _ = _prepare_runtime(tmp_path, monkeypatch)
    namespace = {}
    exec(brain.read_text(encoding="utf-8"), namespace)
    calls = []
    monkeypatch.setattr(namespace["request"], "urlopen", lambda *a, **k: (calls.append(1), (_ for _ in ()).throw(_http_error(429)))[1])
    monkeypatch.setattr(namespace["time"], "sleep", lambda *_: None)
    with pytest.raises(RuntimeError, match="temporariamente indisponível"):
        namespace["_post_json"]("https://api.openai.com/v1/responses", {}, {})
    assert len(calls) == 4


def test_good_evening_stays_local_with_labor_operation_active(tmp_path, monkeypatch):
    _, orchestrator = _prepare_runtime(tmp_path, monkeypatch)
    namespace = {}
    exec(orchestrator.read_text(encoding="utf-8"), namespace)
    assert namespace["_simple_conversation_response"]("Boa noite, chat!", [], []) == "Tudo ótimo! E com você? Como posso ajudar hoje?"


def test_real_labor_request_is_not_classified_as_simple(tmp_path, monkeypatch):
    _, orchestrator = _prepare_runtime(tmp_path, monkeypatch)
    namespace = {}
    exec(orchestrator.read_text(encoding="utf-8"), namespace)
    assert namespace["_simple_conversation_response"]("Você pode me ajudar com um cálculo trabalhista?", [], []) is None


def test_worker_billing_remains_idempotent_and_single_processing_path():
    source = Path("app/services/chat_task_worker.py").read_text(encoding="utf-8")
    assert 'idempotency_key=f"chat-task:{task_id}"' in source
    assert source.count("result = generate_orchestrated_response(") == 1
    assert source.count("charge_usage(user_id, result") == 1


def test_shadow_does_not_replace_primary_worker_processing():
    worker = Path("app/services/chat_task_worker.py").read_text(encoding="utf-8")
    assert "shadow" not in worker.casefold()
    assert worker.count("generate_orchestrated_response(") == 1
