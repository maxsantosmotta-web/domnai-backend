from pathlib import Path
import re


def patch_main() -> None:
    path = Path('/app/app/main.py')
    source = path.read_text(encoding='utf-8')

    # Remove somente imports, inicializações e rotas executáveis do runtime antigo.
    source = re.sub(
        r'^from app\.(?:api\.admin_(?:cutover|legacy_retirement|shadow_validation)|domnai_core\.parallel_api_bootstrap|services\.(?:cutover_worker_bootstrap|shadow_validation_worker)) import .*\n',
        '',
        source,
        flags=re.M,
    )
    if 'from app.services.chat_task_worker import start_chat_task_worker\n' not in source:
        marker = 'from app.frontend_static import FrontendStaticFiles\n'
        if marker not in source:
            raise RuntimeError('Importação de arquivos estáticos não localizada no app principal.')
        source = source.replace(
            marker,
            marker + 'from app.services.chat_task_worker import start_chat_task_worker\n',
            1,
        )

    source = re.sub(
        r'(?m)^\s*start_cutover_aware_chat_worker\(\)\s*$\n?',
        '',
        source,
    )
    source = re.sub(
        r'(?m)^\s*start_shadow_validation_worker\(\)\s*$\n?',
        '',
        source,
    )
    startup_match = re.search(
        r'(@app\.on_event\("startup"\)\s*\ndef\s+start_persistent_chat_worker\(\):\s*\n)(?P<body>(?:[ \t]+.*\n?)*)',
        source,
    )
    if not startup_match:
        raise RuntimeError('Inicialização do worker de chat não localizada.')
    source = (
        source[:startup_match.start('body')]
        + '    start_chat_task_worker()\n'
        + source[startup_match.end('body'):]
    )

    source = re.sub(
        r'(?m)^app\.include_router\(admin_(?:shadow_validation|cutover|legacy_retirement)_router\)\s*$\n?',
        '',
        source,
    )
    source = re.sub(
        r'(?ms)^# Desligada por padrão\..*?^mount_parallel_api\(app\)\s*$\n?',
        '',
        source,
    )
    source = re.sub(r'(?m)^mount_parallel_api\(app\)\s*$\n?', '', source)

    executable_forbidden = (
        'start_cutover_aware_chat_worker(',
        'start_shadow_validation_worker(',
        'mount_parallel_api(',
        'admin_cutover_router',
        'admin_shadow_validation_router',
        'admin_legacy_retirement_router',
    )
    for marker in executable_forbidden:
        if marker in source:
            raise RuntimeError(f'Referência executável legada permaneceu no app principal: {marker}')
    if source.count('start_chat_task_worker()') != 1:
        raise RuntimeError('O worker novo deve iniciar exatamente uma vez.')
    path.write_text(source, encoding='utf-8')


def patch_worker() -> None:
    path = Path('/app/app/services/chat_task_worker.py')
    source = path.read_text(encoding='utf-8')
    source = source.replace(
        'from app.services.orchestrated_brain import generate_orchestrated_response\n',
        'from app.domnai_core.chat_runtime import generate_new_core_response\n',
    )
    source = source.replace(
        'from app.services.diagnosis_memory import load_diagnosis_state, save_diagnosis_state\n',
        '',
    )
    source = re.sub(
        r'\n\s*diagnosis_state = load_diagnosis_state\(user_id, operation\)',
        '',
        source,
        count=1,
    )
    old_call_pattern = re.compile(
        r'result = generate_orchestrated_response\(\n'
        r'\s*message=(?:message_for_brain|original_message),\n'
        r'\s*operation=operation,\n'
        r'\s*history=(?:history|contextual_history),\n'
        r'\s*attachments=attachments,\n'
        r'\s*diagnosis_state=diagnosis_state,\n'
        r'\s*\)',
        re.S,
    )
    replacement = '''result = generate_new_core_response(
            message=message_for_brain if 'message_for_brain' in locals() else original_message,
            operation=operation,
            history=history,
            attachments=attachments,
            user_id=user_id,
            task_id=task_id,
        )'''
    if 'generate_new_core_response(' not in source:
        source, count = old_call_pattern.subn(replacement, source, count=1)
        if count != 1:
            raise RuntimeError('Chamada antiga do cérebro não localizada no worker final.')

    source = source.replace(
        '                from app.api.chat import _create_artifact\n                artifact = _create_artifact(',
        '                from app.domnai_core.artifact_delivery import create_artifact\n                artifact = create_artifact(',
    )
    source = source.replace(
        '            from app.api.chat import _artifact_offer\n            offer = _artifact_offer(decision.get("artifact_type"))',
        '            from app.domnai_core.artifact_delivery import artifact_offer\n            offer = artifact_offer(decision.get("artifact_type"))',
    )
    source = re.sub(
        r'\n\s*if existing_result\.get\("diagnosis_state"\) is not None:.*?\n\s*persistence_started_at =',
        '\n\n    persistence_started_at =',
        source,
        count=1,
        flags=re.S,
    )
    for marker in (
        'generate_orchestrated_response',
        'load_diagnosis_state',
        'save_diagnosis_state',
        'from app.api.chat import _create_artifact',
        'from app.api.chat import _artifact_offer',
    ):
        if marker in source:
            raise RuntimeError(f'Dependência antiga permaneceu no worker: {marker}')
    path.write_text(source, encoding='utf-8')


patch_main()
patch_worker()
print('Runtime finalizado no novo núcleo: sem cutover, shadow, fallback ou memória legada; PDF e planilha entregues pelo domnai_core.')
