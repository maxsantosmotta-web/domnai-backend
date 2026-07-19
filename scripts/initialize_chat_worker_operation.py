from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
ANCHOR = '''        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
'''
INITIALIZED = '''        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
        operation = payload.get("operation")
'''


def main() -> None:
    if not WORKER_PATH.exists():
        raise RuntimeError('chat_task_worker.py não encontrado no runtime.')

    source = WORKER_PATH.read_text(encoding='utf-8')
    if INITIALIZED in source:
        print('chat_task_worker: operation já inicializada antes dos desvios de fluxo.')
        return
    if ANCHOR not in source:
        raise RuntimeError('chat_task_worker: ponto seguro de inicialização de operation não encontrado.')

    source = source.replace(ANCHOR, INITIALIZED, 1)
    WORKER_PATH.write_text(source, encoding='utf-8')
    print('chat_task_worker: operation inicializada imediatamente após o payload.')


if __name__ == '__main__':
    main()
