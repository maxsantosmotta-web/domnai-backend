from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_patch_module():
    path = Path("scripts/fix_chat_worker_operation_scope.py")
    spec = importlib.util.spec_from_file_location("fix_chat_worker_operation_scope", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _original_orchestrator_source() -> str:
    return '''from __future__ import annotations

import os
import time
import unicodedata


def _normalized_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold().strip()


def _simple_conversation_response(message: str, attachments: list[dict], history: list[dict]) -> str | None:
    if attachments:
        return None
    normalized = " ".join(_normalized_text(message).replace("?", "").replace("!", "").split())
    if normalized == "oi" and not history:
        return "Tudo ótimo! E com você? Como posso ajudar hoje?"
    if normalized == "obrigado":
        return "Por nada!"
    if normalized == "tchau":
        return "Até mais!"
    return None


def _specialized_engine(plan, operation, message):
    if operation == "Cálculo de Rescisão Trabalhista":
        return "labor_termination"
    return None


def generate_orchestrated_response(message, history, operation, attachments=None, diagnosis_state=None):
    safe_attachments = attachments or []
    simple_reply = _simple_conversation_response(message, safe_attachments, history)
    if simple_reply is not None:
        return MeteredBrainResult(
            text=simple_reply,
            provider="domnai-local-conversation",
            model="local",
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            diagnosis_state=diagnosis_state,
        )

    if _specialized_engine({}, operation, message) is None:
        return generate_metered_response(message=message, history=history, operation=operation, attachments=safe_attachments, diagnosis_state=diagnosis_state)
    return "labor"
'''


def test_runtime_removes_canned_chatbot_responses(tmp_path, monkeypatch):
    module = _load_patch_module()
    target = tmp_path / "orchestrated_brain.py"
    target.write_text(_original_orchestrator_source(), encoding="utf-8")
    monkeypatch.setattr(module, "ORCHESTRATOR_PATH", target)

    module._fix_simple_conversation()

    final_source = target.read_text(encoding="utf-8")
    assert "Tudo ótimo! E com você? Como posso ajudar hoje?" not in final_source
    assert "Por nada!" not in final_source
    assert "Até mais!" not in final_source
    assert "domnai-local-conversation" not in final_source
    assert "openai-light-conversation" in final_source
    compile(final_source, str(target), "exec")


def test_light_conversation_uses_one_real_model_call_and_ignores_active_operation(tmp_path, monkeypatch):
    module = _load_patch_module()
    target = tmp_path / "orchestrated_brain.py"
    target.write_text(_original_orchestrator_source(), encoding="utf-8")
    monkeypatch.setattr(module, "ORCHESTRATOR_PATH", target)

    module._fix_simple_conversation()
    final_source = target.read_text(encoding="utf-8")

    helper_start = final_source.index("def _light_conversation_response(")
    helper_end = final_source.index("\n\ndef _specialized_engine(", helper_start)
    helper = final_source[helper_start:helper_end]
    assert helper.count("_openai_request(") == 1
    assert 'operation=None' in helper

    call_start = final_source.index("def generate_orchestrated_response(")
    call_source = final_source[call_start:]
    light_index = call_source.index("if _is_light_conversation(message, safe_attachments):")
    labor_index = call_source.index("if _specialized_engine({}, operation, message) is None:")
    assert light_index < labor_index


def test_real_labor_request_is_not_classified_as_light_conversation(tmp_path, monkeypatch):
    module = _load_patch_module()
    target = tmp_path / "orchestrated_brain.py"
    target.write_text(_original_orchestrator_source(), encoding="utf-8")
    monkeypatch.setattr(module, "ORCHESTRATOR_PATH", target)

    module._fix_simple_conversation()
    final_source = target.read_text(encoding="utf-8")

    namespace = {
        "MeteredBrainResult": object,
        "_normalized_history": lambda history, limit=6: history[-limit:],
        "_openai_request": lambda api_key, payload: ("resposta", {}),
        "generate_metered_response": lambda **kwargs: kwargs,
        "_usage_value": lambda usage, key: 0,
        "_cached_value": lambda usage: 0,
    }
    exec(final_source, namespace)
    classifier = namespace["_is_light_conversation"]

    assert classifier("Oi", []) is True
    assert classifier("Boa noite, chat!", []) is True
    assert classifier("Você pode me ajudar com um cálculo trabalhista?", []) is False
    assert classifier("Quero calcular minha rescisão", []) is False
