from pathlib import Path
import re


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

# Canonicaliza o bloco de falha inteiro antes do patch final. Alguns patches
# anteriores deixavam uma resposta automática multilinha; o patch final antigo
# removia apenas a primeira linha e podia deixar chaves soltas no Python gerado.
failure_pattern = re.compile(
    r'            except Exception(?: as \w+)?:\n'
    r'(?:                .*\n)+?'
    r'(?=        elif decision\.get\("action"\) == "offer":)',
    flags=re.M,
)
canonical_failure = (
    '            except Exception:\n'
    '                print(f"artifact_delivery failure task_id={task_id}\\n{traceback.format_exc()}", flush=True)\n'
    '                raise\n'
)
source, failure_count = failure_pattern.subn(canonical_failure, source, count=1)
if failure_count != 1 and 'artifact_delivery failure task_id=' not in source:
    raise RuntimeError('Bloco completo de falha da entrega de artefato não localizado.')

compile(source, str(worker_path), 'exec')
worker_path.write_text(source, encoding='utf-8')

# A entrega final deve permanecer em uma única mensagem. Este estágio não cria
# mensagens provisórias, cartões extras nem aviso separado; a persistência
# canônica é aplicada por finalize_new_core_only.py ao final da cadeia.
print('Entrega progressiva preservada sem mensagens extras; falha de artefato canonicalizada sem sintaxe residual.')
