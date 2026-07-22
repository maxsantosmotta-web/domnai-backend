from pathlib import Path
import re


DISCLAIMER = (
    'Este documento organiza informações para apoio à decisão e não substitui '
    'a avaliação de um profissional habilitado.'
)


def patch_main() -> None:
    path = Path('/app/app/main.py')
    source = path.read_text(encoding='utf-8')

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


def _canonical_append_completed_response() -> str:
    return '''def _append_completed_response(
    user_id: str,
    payload: dict,
    reply: str,
    artifacts: list[dict],
    sources: list[dict],
) -> None:
    task_id = str(payload.get("task_id") or "")
    if not task_id:
        return

    unique_artifacts: list[dict] = []
    seen_artifacts: set[str] = set()
    for artifact in artifacts or []:
        if not isinstance(artifact, dict):
            continue
        key = str(
            artifact.get("libraryId")
            or artifact.get("id")
            or artifact.get("contentUrl")
            or artifact.get("name")
            or ""
        )
        if not key or key in seen_artifacts:
            continue
        seen_artifacts.add(key)
        unique_artifacts.append(artifact)
        break

    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            state = ActiveChatState(user_id=user_id, messages_json="[]")
            db.add(state)
        try:
            messages = json.loads(state.messages_json or "[]")
            if not isinstance(messages, list):
                messages = []
        except json.JSONDecodeError:
            messages = []

        assistant_index = None
        normalized_messages = []
        for item in messages:
            if not isinstance(item, dict):
                normalized_messages.append(item)
                continue
            same_task = str(item.get("taskId") or "") == task_id
            if same_task and item.get("role") == "assistant":
                if assistant_index is None:
                    assistant_index = len(normalized_messages)
                    normalized_messages.append(item)
                continue
            normalized_messages.append(item)
        messages = normalized_messages

        final_message = {
            "id": f"assistant-{task_id}",
            "role": "assistant",
            "text": str(reply or "").strip(),
            "attachments": unique_artifacts,
            "sources": sources or [],
            "isError": False,
            "taskId": task_id,
            "processing": False,
        }

        if assistant_index is not None:
            messages[assistant_index] = {**messages[assistant_index], **final_message}
        else:
            has_user_message = any(
                isinstance(item, dict)
                and item.get("role") == "user"
                and str(item.get("taskId") or "") == task_id
                for item in messages
            )
            if not has_user_message:
                messages.append({
                    "id": f"user-{task_id}",
                    "role": "user",
                    "text": str(payload.get("message") or ""),
                    "attachments": [],
                    "sources": [],
                    "isError": False,
                    "taskId": task_id,
                    "processing": False,
                })
            messages.append(final_message)

        state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
        state.active_operation = payload.get("operation")
        state.updated_at = _now()
'''


def patch_worker() -> None:
    path = Path('/app/app/services/chat_task_worker.py')
    source = path.read_text(encoding='utf-8')

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

    append_start = source.find('def _append_completed_response(')
    process_start = source.find('\ndef _process_task(', append_start)
    if append_start < 0 or process_start < 0:
        raise RuntimeError('Função final de persistência do chat não localizada.')
    source = source[:append_start] + _canonical_append_completed_response().rstrip() + '\n\n' + source[process_start + 1:]

    artifact_result_anchor = '            "artifacts": artifacts,\n'
    if 'artifacts = artifacts[:1]' not in source:
        position = source.find(artifact_result_anchor)
        if position < 0:
            raise RuntimeError('Resultado de artefatos não localizado no worker final.')
        source = source[:position] + '        artifacts = artifacts[:1]\n' + source[position:]

    for old_disclaimer in (
        'Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações fornecidas durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação por um profissional habilitado.',
        'Este documento foi gerado com base nas informações fornecidas durante esta conversa. Seu conteúdo tem finalidade informativa e não substitui a análise, avaliação ou orientação de um profissional habilitado quando ela for necessária.',
        'Este relatório organiza as informações fornecidas e não substitui avaliação profissional quando o tema exigir análise jurídica, contábil, médica, financeira ou técnica especializada.',
    ):
        source = source.replace(old_disclaimer, DISCLAIMER)

    for marker in (
        'generate_orchestrated_response',
        'load_diagnosis_state',
        'save_diagnosis_state',
        'from app.api.chat import _create_artifact',
        'from app.api.chat import _artifact_offer',
    ):
        if marker in source:
            raise RuntimeError(f'Dependência antiga permaneceu no worker: {marker}')
    if source.count('def _append_completed_response(') != 1:
        raise RuntimeError('Persistência final do chat deve existir exatamente uma vez.')
    if 'unique_artifacts.append(artifact)\n        break' not in source:
        raise RuntimeError('Limite de um arquivo por solicitação não foi aplicado.')

    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


def patch_artifact_delivery() -> None:
    path = Path('/app/app/domnai_core/artifact_delivery.py')
    source = path.read_text(encoding='utf-8')
    source = source.replace(
        "            'summary': answer,\n            'sections': [{'title': 'Resultado', 'content': answer}],\n",
        "            'summary': '',\n            'sections': [{'title': 'Conteúdo consolidado', 'content': answer}],\n",
        1,
    )
    if "'summary': answer" in source:
        raise RuntimeError('Conteúdo do PDF continuou duplicado entre resumo e seção.')
    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


def patch_document_disclaimer() -> None:
    pdf_path = Path('/app/app/services/pdf_report.py')
    source = pdf_path.read_text(encoding='utf-8')
    disclaimer_pattern = re.compile(
        r'("Este (?:relatório|documento)[^"]*(?:habilitado|especializada)\.?")',
        flags=re.I,
    )
    source, count = disclaimer_pattern.subn(repr(DISCLAIMER), source)
    if count < 1 and DISCLAIMER not in source:
        raise RuntimeError('Aviso profissional do PDF não localizado.')
    if source.count(DISCLAIMER) != 1:
        raise RuntimeError('PDF deve conter exatamente um aviso profissional oficial.')
    compile(source, str(pdf_path), 'exec')
    pdf_path.write_text(source, encoding='utf-8')


patch_main()
patch_worker()
patch_artifact_delivery()
patch_document_disclaimer()
print('Runtime finalizado no novo núcleo: entrega única de artefato, PDF sem duplicação e aviso oficial único.')
