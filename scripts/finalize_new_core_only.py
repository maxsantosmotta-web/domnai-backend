from pathlib import Path
import re


def patch_main() -> None:
    path = Path('/app/app/main.py')
    source = path.read_text(encoding='utf-8')
    removals = (
        'from app.api.admin_cutover import router as admin_cutover_router\n',
        'from app.api.admin_legacy_retirement import router as admin_legacy_retirement_router\n',
        'from app.api.admin_shadow_validation import router as admin_shadow_validation_router\n',
        'from app.domnai_core.parallel_api_bootstrap import mount_parallel_api\n',
        'from app.services.cutover_worker_bootstrap import start_cutover_aware_chat_worker\n',
        'from app.services.shadow_validation_worker import start_shadow_validation_worker\n',
    )
    for marker in removals:
        source = source.replace(marker, '')
    if 'from app.services.chat_task_worker import start_chat_task_worker\n' not in source:
        source = source.replace(
            'from app.frontend_static import FrontendStaticFiles\n',
            'from app.frontend_static import FrontendStaticFiles\nfrom app.services.chat_task_worker import start_chat_task_worker\n',
            1,
        )
    source = source.replace(
        '    start_cutover_aware_chat_worker()\n    start_shadow_validation_worker()\n',
        '    start_chat_task_worker()\n',
        1,
    )
    for marker in (
        'app.include_router(admin_shadow_validation_router)\n',
        'app.include_router(admin_cutover_router)\n',
        'app.include_router(admin_legacy_retirement_router)\n',
        '# Desligada por padrão. Reverter a flag remove imediatamente toda a superfície paralela.\nmount_parallel_api(app)\n',
    ):
        source = source.replace(marker, '')
    forbidden = ('cutover', 'shadow_validation', 'legacy_retirement', 'mount_parallel_api')
    for marker in forbidden:
        if marker in source:
            raise RuntimeError(f'Referência legada permaneceu no app principal: {marker}')
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
