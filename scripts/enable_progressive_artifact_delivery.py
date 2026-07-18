from pathlib import Path


WORKER = Path('/app/app/services/chat_task_worker.py')
source = WORKER.read_text(encoding='utf-8')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: esperado 1 trecho, encontrado {count}')
    return text.replace(old, new, 1)


helper_anchor = '''def _append_completed_response(
    user_id: str,
    payload: dict,
    reply: str,
    artifacts: list[dict],
    sources: list[dict],
) -> None:
'''
helper_block = '''def _publish_artifact_preparation(user_id: str, payload: dict) -> None:
    task_id = str(payload.get("task_id") or "")
    if not task_id:
        return
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            return
        try:
            messages = json.loads(state.messages_json or "[]")
            if not isinstance(messages, list):
                return
        except json.JSONDecodeError:
            return
        for index, item in enumerate(messages):
            if not isinstance(item, dict):
                continue
            if str(item.get("taskId") or "") != task_id or item.get("role") != "assistant":
                continue
            messages[index] = {
                **item,
                "text": (
                    "Perfeito. Vou organizar as informações desta conversa e preparar o arquivo para você. "
                    "Assim que estiver pronto, ele aparecerá aqui."
                ),
                "attachments": [],
                "sources": [],
                "isError": False,
                "processing": True,
            }
            state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
            state.updated_at = _now()
            return


def _append_completed_response(
    user_id: str,
    payload: dict,
    reply: str,
    artifacts: list[dict],
    sources: list[dict],
) -> None:
'''
source = replace_once(source, helper_anchor, helper_block, 'publicação do aviso de preparação')

artifact_branch_anchor = '''        replaced = False
        for index, item in enumerate(messages):
'''
artifact_branch = '''        if artifacts:
            preparation_found = False
            for index, item in enumerate(messages):
                if not isinstance(item, dict):
                    continue
                if str(item.get("taskId") or "") != task_id or item.get("role") != "assistant":
                    continue
                messages[index] = {
                    **item,
                    "processing": False,
                    "isError": False,
                }
                preparation_found = True
                break

            if not preparation_found:
                messages.append({
                    "id": f"assistant-{task_id}-preparation",
                    "role": "assistant",
                    "text": (
                        "Perfeito. Vou organizar as informações desta conversa e preparar o arquivo para você. "
                        "Assim que estiver pronto, ele aparecerá aqui."
                    ),
                    "attachments": [],
                    "sources": [],
                    "isError": False,
                    "taskId": task_id,
                    "processing": False,
                })

            messages.append({
                "id": f"assistant-{task_id}-delivery",
                "role": "assistant",
                "text": reply,
                "attachments": artifacts,
                "sources": sources,
                "isError": False,
                "taskId": task_id,
                "processing": False,
            })
            messages.append({
                "id": f"assistant-{task_id}-disclaimer",
                "role": "assistant",
                "text": (
                    "Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações "
                    "fornecidas durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação "
                    "por um profissional habilitado."
                ),
                "attachments": [],
                "sources": [],
                "isError": False,
                "taskId": task_id,
                "processing": False,
            })
            state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
            state.active_operation = payload.get("operation")
            state.updated_at = _now()
            return

        replaced = False
        for index, item in enumerate(messages):
'''
source = replace_once(source, artifact_branch_anchor, artifact_branch, 'persistência da entrega progressiva')

create_anchor = '''        if decision.get("action") == "create":
            try:
'''
create_block = '''        if decision.get("action") == "create":
            _publish_artifact_preparation(user_id, payload)
            try:
'''
source = replace_once(source, create_anchor, create_block, 'aviso antes da geração')

old_delivery = '''                artifacts.append(artifact)
                clean_reply = _clean_artifact_contradictions(reply)
                completion = _artifact_completion_message(decision.get("artifact_type"))
                reply = f"{clean_reply}\n\n{completion}" if clean_reply and result.provider != "local-artifact" else completion
                payload["artifact_delivery_state"] = "completed"
'''
new_delivery = '''                artifacts.append(artifact)
                reply = (
                    "Pronto! Seu arquivo foi gerado com base nas informações desta conversa e está disponível logo abaixo. "
                    "O conteúdo foi organizado para facilitar a leitura e a consulta. "
                    "Ele também foi salvo automaticamente na Biblioteca."
                )
                payload["artifact_delivery_state"] = "completed"
'''
source = replace_once(source, old_delivery, new_delivery, 'mensagem final de arquivo pronto')

WORKER.write_text(source, encoding='utf-8')
print('Entrega progressiva ativada: aviso, geração real, arquivo e orientação final.')
