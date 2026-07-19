from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
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


def main() -> None:
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
    print('chat_task_worker: operation inicializada antes de todos os desvios de fluxo.')


if __name__ == '__main__':
    main()
