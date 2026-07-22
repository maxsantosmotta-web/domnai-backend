from pathlib import Path
import re


def patch_main() -> None:
    path = Path('/app/app/main.py')
    source = path.read_text(encoding='utf-8')

    # Remova imports legados independentemente de espaçamento ou ordem gerada
    # pelos patches anteriores.
    source = re.sub(
        r'^from app\.(?:api\.(?:admin_cutover|admin_legacy_retirement|admin_shadow_validation)|domnai_core\.parallel_api_bootstrap|services\.(?:cutover_worker_bootstrap|shadow_validation_worker)) import .*\n',
        '',
        source,
        flags=re.M,
    )

    if 'from app.services.chat_task_worker import start_chat_task_worker\n' not in source:
        anchor = 'from app.frontend_static import FrontendStaticFiles\n'
        if anchor not in source:
            raise RuntimeError('Importação de FrontendStaticFiles não localizada no app principal.')
        source = source.replace(
            anchor,
            anchor + 'from app.services.chat_task_worker import start_chat_task_worker\n',
            1,
        )

    # Substitui o corpo inteiro do hook de startup. Não depende do nome ou da
    # quantidade de chamadas que patches anteriores tenham deixado ali.
    startup_pattern = re.compile(
        r'(@app\.on_event\(["\']startup["\']\)\n'
        r'def start_persistent_chat_worker\(\):\n)'
        r'(?:[ \t]+.*\n)+',
        flags=re.M,
    )
    source, startup_count = startup_pattern.subn(
        r'\1    start_chat_task_worker()\n',
        source,
        count=1,
    )
    if startup_count != 1:
        raise RuntimeError('Hook de startup do chat não localizado no app principal.')

    # Remove inclusões de rotas e montagem paralela mesmo que comentários ou
    # linhas em branco tenham mudado.
    source = re.sub(
        r'^app\.include_router\((?:admin_cutover_router|admin_legacy_retirement_router|admin_shadow_validation_router)\)\n',
        '',
        source,
        flags=re.M,
    )
    source = re.sub(r'^mount_parallel_api\(app\)\n', '', source, flags=re.M)

    executable_markers = (
        'admin_cutover_router',
        'admin_legacy_retirement_router',
        'admin_shadow_validation_router',
        'mount_parallel_api(',
        'start_cutover_aware_chat_worker(',
        'start_shadow_validation_worker(',
    )
    for marker in executable_markers:
        if marker in source:
            raise RuntimeError(f'Referência legada executável permaneceu no app principal: {marker}')
    if source.count('start_chat_task_worker()') != 1:
        raise RuntimeError('Worker do novo núcleo deve iniciar exatamente uma vez.')

    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


def patch_worker() -> None:
    path = Path('/app/app/services/chat_task_worker.py')
    source = path.read_text(encoding='utf-8')

    # Um patch anterior gerava quebras de linha reais dentro de strings Python.
    source = source.replace('usuário):\n"', 'usuário):\\n"')
    source = source.replace('+ "\nUse somente fatos', '+ "\\nUse somente fatos')
    source = source.replace('USUÁRIO:\n" + "\n\n".join', 'USUÁRIO:\\n" + "\\n\\n".join')

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
            message=original_message,
            operation=operation,
            history=contextual_history if 'contextual_history' in locals() else history,
            attachments=attachments,
            user_id=user_id,
            task_id=task_id,
        )'''
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
    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


patch_main()
patch_worker()
print('Runtime finalizado no novo núcleo: startup e worker sem referências executáveis ao legado.')
