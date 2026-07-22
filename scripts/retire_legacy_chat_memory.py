from pathlib import Path

memory_path = Path('/app/app/services/diagnosis_memory.py')
source = memory_path.read_text(encoding='utf-8')

load_start = source.index('def load_diagnosis_state(')
save_start = source.index('\ndef save_diagnosis_state(', load_start)
clear_start = source.index('\ndef clear_diagnosis_state(', save_start)
context_start = source.index('\ndef diagnosis_context(', clear_start)
extractor_start = source.index('\ndef diagnosis_extractor_instructions(', context_start)

replacement = '''def load_diagnosis_state(user_id: str, operation: str | None) -> dict[str, Any]:
    # A memória persistente do chat legado foi aposentada. A continuidade válida
    # vem somente do histórico enviado pela conversa atual.
    del user_id, operation
    return empty_diagnosis_state()


def save_diagnosis_state(user_id: str, operation: str | None, state: dict[str, Any]) -> None:
    # Não volte a gravar estados semânticos globais por usuário.
    del user_id, operation, state


def clear_diagnosis_state(user_id: str) -> None:
    # Mantido por compatibilidade de chamada; os registros antigos são eliminados
    # no startup e não participam mais de nenhuma resposta.
    del user_id


def diagnosis_context(state: dict[str, Any] | None) -> str:
    del state
    return ''
'''

source = source[:load_start] + replacement + source[extractor_start + 1:]
memory_path.write_text(source, encoding='utf-8')

main_path = Path('/app/app/main.py')
main = main_path.read_text(encoding='utf-8')

if 'from sqlalchemy import delete\n' not in main:
    main = main.replace('from fastapi.middleware.cors import CORSMiddleware\n', 'from fastapi.middleware.cors import CORSMiddleware\nfrom sqlalchemy import delete\n', 1)
if 'from app.database import session_scope\n' not in main:
    main = main.replace('from app.config import settings\n', 'from app.config import settings\nfrom app.database import session_scope\n', 1)
if 'from app.models import DiagnosisState\n' not in main:
    main = main.replace('from app.frontend_static import FrontendStaticFiles\n', 'from app.frontend_static import FrontendStaticFiles\nfrom app.models import DiagnosisState\n', 1)

old_startup = '''@app.on_event("startup")
def start_persistent_chat_worker():
    start_cutover_aware_chat_worker()
    start_shadow_validation_worker()
'''
new_startup = '''@app.on_event("startup")
def start_persistent_chat_worker():
    # Limpa definitivamente os estados persistidos pelo chat legado antes de
    # iniciar o fluxo atual. O histórico da conversa continua intacto.
    with session_scope() as db:
        db.execute(delete(DiagnosisState))
    start_cutover_aware_chat_worker()
'''
if old_startup in main:
    main = main.replace(old_startup, new_startup, 1)
elif new_startup not in main:
    raise RuntimeError('Startup do chat não localizado para aposentadoria da memória antiga.')

main_path.write_text(main, encoding='utf-8')

for path, forbidden in (
    (memory_path, 'MEMÓRIA ESTRUTURADA DA CONVERSA'),
    (main_path, 'start_shadow_validation_worker()'),
):
    text = path.read_text(encoding='utf-8')
    if forbidden in text:
        raise RuntimeError(f'Componente legado ainda ativo em {path}: {forbidden}')

print('Memória persistente do chat legado aposentada e estados antigos removidos no startup.')
