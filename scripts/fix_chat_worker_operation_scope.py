from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
ARTIFACT_DECISION_PATH = Path('/app/app/services/artifact_decision.py')
ANCHOR = '''        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
        existing_result = json.loads(task.result_json) if task.result_json else None
'''
REPLACEMENT = '''        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
        operation = payload.get("operation")
        existing_result = json.loads(task.result_json) if task.result_json else None
'''
DUPLICATE = '''        original_message = str(payload.get("message") or "").strip()
        operation = payload.get("operation")
        history = payload.get("history") or []
'''
DEDUPLICATED = '''        original_message = str(payload.get("message") or "").strip()
        history = payload.get("history") or []
'''


def _fix_worker_scope() -> None:
    if not WORKER_PATH.exists():
        raise RuntimeError('chat_task_worker.py não encontrado no runtime.')

    source = WORKER_PATH.read_text(encoding='utf-8')

    if REPLACEMENT not in source:
        if ANCHOR not in source:
            raise RuntimeError('Ponto seguro para inicializar operation não encontrado.')
        source = source.replace(ANCHOR, REPLACEMENT, 1)

    if DUPLICATE in source:
        source = source.replace(DUPLICATE, DEDUPLICATED, 1)

    operation_index = source.index('        operation = payload.get("operation")')
    conditional_index = source.index('    if existing_result is None:')
    if operation_index > conditional_index:
        raise RuntimeError('operation continuou inicializada depois do ramo condicional.')

    WORKER_PATH.write_text(source, encoding='utf-8')


def _fix_artifact_decision_scope() -> None:
    if not ARTIFACT_DECISION_PATH.exists():
        raise RuntimeError('artifact_decision.py não encontrado no runtime.')

    source = ARTIFACT_DECISION_PATH.read_text(encoding='utf-8')
    unsafe = '    del operation, answer\n'
    safe = '    del answer\n'

    if unsafe in source:
        source = source.replace(unsafe, safe, 1)

    function_start = source.index('def _requires_artifact_decision(')
    function_end = source.index('\n\ndef decide_artifact(', function_start)
    function_source = source[function_start:function_end]

    if 'del operation' in function_source:
        raise RuntimeError('artifact_decision ainda remove operation antes de terminar a função.')

    ARTIFACT_DECISION_PATH.write_text(source, encoding='utf-8')


def main() -> None:
    _fix_worker_scope()
    _fix_artifact_decision_scope()
    print('Escopos finais corrigidos: worker e decisão de artefatos preservam operation.')


if __name__ == '__main__':
    main()
