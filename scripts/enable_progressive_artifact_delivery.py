from pathlib import Path
import re


WORKER = Path('/app/app/services/chat_task_worker.py')
source = WORKER.read_text(encoding='utf-8')

preparation_text = (
    "Perfeito. Vou organizar as informações desta conversa e preparar o arquivo para você. "
    "Assim que estiver pronto, ele aparecerá aqui."
)
ready_text = (
    "Pronto! Seu arquivo foi gerado com base nas informações desta conversa e está disponível logo abaixo. "
    "O conteúdo foi organizado para facilitar a leitura e a consulta. "
    "Ele também foi salvo automaticamente na Biblioteca."
)
disclaimer_text = (
    "Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações "
    "fornecidas durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação "
    "por um profissional habilitado."
)

if 'def _publish_artifact_preparation(' not in source:
    marker = 'def _append_completed_response('
    position = source.find(marker)
    if position < 0:
        raise RuntimeError('Função de persistência da resposta não encontrada.')
    helper = f'''def _publish_artifact_preparation(user_id: str, payload: dict) -> None:
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
            messages[index] = {{
                **item,
                "text": {preparation_text!r},
                "attachments": [],
                "sources": [],
                "isError": False,
                "processing": True,
            }}
            state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
            state.updated_at = _now()
            return


'''
    source = source[:position] + helper + source[position:]

if 'assistant-{task_id}-delivery' not in source:
    marker = '        replaced = False\n        for index, item in enumerate(messages):\n'
    position = source.find(marker)
    if position < 0:
        raise RuntimeError('Bloco de substituição da resposta não encontrado.')
    branch = f'''        if artifacts:
            preparation_found = False
            for index, item in enumerate(messages):
                if not isinstance(item, dict):
                    continue
                if str(item.get("taskId") or "") != task_id or item.get("role") != "assistant":
                    continue
                messages[index] = {{**item, "processing": False, "isError": False}}
                preparation_found = True
                break
            if not preparation_found:
                messages.append({{
                    "id": f"assistant-{{task_id}}-preparation",
                    "role": "assistant",
                    "text": {preparation_text!r},
                    "attachments": [],
                    "sources": [],
                    "isError": False,
                    "taskId": task_id,
                    "processing": False,
                }})
            messages.append({{
                "id": f"assistant-{{task_id}}-delivery",
                "role": "assistant",
                "text": reply,
                "attachments": artifacts,
                "sources": sources,
                "isError": False,
                "taskId": task_id,
                "processing": False,
            }})
            messages.append({{
                "id": f"assistant-{{task_id}}-disclaimer",
                "role": "assistant",
                "text": {disclaimer_text!r},
                "attachments": [],
                "sources": [],
                "isError": False,
                "taskId": task_id,
                "processing": False,
            }})
            state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
            state.active_operation = payload.get("operation")
            state.updated_at = _now()
            return

'''
    source = source[:position] + branch + source[position:]

if '_publish_artifact_preparation(user_id, payload)' not in source:
    pattern = r'(        if decision\.get\("action"\) == "create":\n)(\s+try:\n)'
    source, count = re.subn(pattern, r'\1            _publish_artifact_preparation(user_id, payload)\n\2', source, count=1)
    if count != 1:
        raise RuntimeError('Bloco de criação do arquivo não encontrado.')

if ready_text not in source:
    pattern = (
        r'                artifacts\.append\(artifact\)\n'
        r'(?:                .*\n)*?'
        r'                payload\["artifact_delivery_state"\] = "completed"\n'
    )
    replacement = (
        '                artifacts.append(artifact)\n'
        f'                reply = {ready_text!r}\n'
        '                payload["artifact_delivery_state"] = "completed"\n'
    )
    source, count = re.subn(pattern, replacement, source, count=1)
    if count != 1:
        raise RuntimeError('Bloco final de sucesso da geração não encontrado.')

WORKER.write_text(source, encoding='utf-8')
print('Entrega progressiva ativada: aviso, espera real, arquivo e orientação final.')
