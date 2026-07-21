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


def test_final_runtime_patch_preserves_answer_and_operation(tmp_path, monkeypatch):
    module = _load_patch_module()
    target = tmp_path / "artifact_decision.py"
    target.write_text(
        '''def _requires_artifact_decision(message, operation, history, answer):
    del operation, answer
    explicit_request = False
    accepted_previous_offer = False
    if explicit_request or accepted_previous_offer:
        return True
    return bool(operation and len(str(answer or "").strip()) >= 1000)


def decide_artifact():
    return None
''',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ARTIFACT_DECISION_PATH", target)

    module._fix_artifact_decision_scope()

    final_source = target.read_text(encoding="utf-8")
    assert "del operation" not in final_source
    assert "del answer" not in final_source

    namespace = {}
    exec(final_source, namespace)
    decide = namespace["_requires_artifact_decision"]
    assert decide("teste", "Cálculo de Rescisão Trabalhista", [], "resposta curta") is False
    assert decide("teste", "Cálculo de Rescisão Trabalhista", [], "x" * 1000) is True


def test_runtime_patch_guards_both_parameters():
    source = Path("scripts/fix_chat_worker_operation_scope.py").read_text(encoding="utf-8")
    assert "'    del operation, answer\\n'" in source
    assert "'    del answer\\n'" in source
    assert "'    del operation\\n'" in source
    assert "preservam operation e answer" in source
