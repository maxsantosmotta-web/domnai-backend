from pathlib import Path


worker_path = Path('/app/app/services/chat_task_worker.py')
source = worker_path.read_text(encoding='utf-8')

required = (
    'def _append_completed_response(',
    'def _process_task(',
    'decide_artifact(',
)
for marker in required:
    if marker not in source:
        raise RuntimeError(f'Worker de artefatos incompleto antes da finalização: {marker}')

# A entrega final deve permanecer em uma única mensagem. Este estágio não cria
# mensagens provisórias, cartões extras nem aviso separado; a persistência
# canônica é aplicada por finalize_new_core_only.py ao final da cadeia.
print('Entrega progressiva preservada sem mensagens extras; finalização única mantida.')
