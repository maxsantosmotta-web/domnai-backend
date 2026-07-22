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

# Canonicaliza o bloco de falha inteiro antes do patch final. A substituição é
# feita por função para que "\\n" permaneça literal no Python gerado; uma string
# de reposição comum do re.sub converteria isso em quebra de linha dentro do
# f-string e causaria SyntaxError.
failure_pattern = re.compile(
    r'            except Exception(?: as \w+)?:\n'
    r'(?:                .*\n)+?'
    r'(?=        elif decision\.get\("action"\) == "offer":)',
    flags=re.M,
)


def canonical_failure(_match: re.Match) -> str:
    return (
        '            except Exception:\n'
        '                print(f"artifact_delivery failure task_id={task_id}\\n{traceback.format_exc()}", flush=True)\n'
        '                raise\n'
    )


source, failure_count = failure_pattern.subn(canonical_failure, source, count=1)
if failure_count != 1 and 'artifact_delivery failure task_id=' not in source:
    raise RuntimeError('Bloco completo de falha da entrega de artefato não localizado.')

# Também corrige qualquer versão já malformada deixada por uma execução anterior.
malformed_log = re.compile(
    r'(?P<indent>[ \t]*)print\(f"artifact_delivery failure task_id=\{task_id\}\s*\n'
    r'\{traceback\.format_exc\(\)\}", flush=True\)'
)
source = malformed_log.sub(
    lambda match: (
        f'{match.group("indent")}print('
        'f"artifact_delivery failure task_id={task_id}\\n{traceback.format_exc()}", '
        'flush=True)'
    ),
    source,
)

compile(source, str(worker_path), 'exec')
worker_path.write_text(source, encoding='utf-8')

# A entrega final deve permanecer em uma única mensagem. Este estágio não cria
# mensagens provisórias, cartões extras nem aviso separado; a persistência
# canônica é aplicada por finalize_new_core_only.py ao final da cadeia.
print('Entrega progressiva preservada sem mensagens extras; log de falha compilável e finalização única mantida.')
