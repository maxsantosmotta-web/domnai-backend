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


source = replace_once(
    source,
    '''def _append_completed_response(
    user_id: str,
    payload: dict,
    reply: str,
    artifacts: list[dict],
    sources: list[dict],
) -> None:
''',
    '''def _append_completed_response(
    user_id: str,
    payload: dict,
    reply: str,
    artifacts: list[dict],
    sources: list[dict],
    post_artifact_text: str = "",
) -> None:
''',
    'assinatura da persistência da resposta',
)

anchor = '''        state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
        state.active_operation = payload.get("operation")
'''
replacement = '''        if artifacts and post_artifact_text:
            post_message_id = f"assistant-{task_id}-post-artifact"
            already_present = any(
                isinstance(item, dict) and item.get("id") == post_message_id
                for item in messages
            )
            if not already_present:
                messages.append({
                    "id": post_message_id,
                    "role": "assistant",
                    "text": post_artifact_text,
                    "attachments": [],
                    "sources": [],
                    "isError": False,
                    "taskId": task_id,
                    "processing": False,
                })

        state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
        state.active_operation = payload.get("operation")
'''
source = replace_once(source, anchor, replacement, 'mensagem posterior ao arquivo')

source = replace_once(
    source,
    '''        reply = result.text
        artifacts: list[dict] = []
''',
    '''        reply = result.text
        post_artifact_text = ""
        artifacts: list[dict] = []
''',
    'estado do texto posterior',
)

old_delivery = '''                artifacts.append(artifact)
                if result.provider == "local-artifact":
                    reply = "PDF criado e enviado aqui no chat. O mesmo arquivo também foi salvo automaticamente na Biblioteca."
                else:
                    reply = f"{reply.rstrip()}\\n\\nArquivo criado e enviado aqui no chat."
'''
new_delivery = '''                artifacts.append(artifact)
                reply = (
                    "Pronto! Seu arquivo foi gerado com base nas informações desta conversa e está disponível logo abaixo. "
                    "O conteúdo foi organizado para facilitar a leitura e a consulta. "
                    "Ele também foi salvo automaticamente na Biblioteca."
                )
                post_artifact_text = (
                    "Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações "
                    "fornecidas durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação "
                    "por um profissional habilitado."
                )
'''
source = replace_once(source, old_delivery, new_delivery, 'texto antes e depois do arquivo')

source = replace_once(
    source,
    '''            "artifacts": artifacts,
            "provider": result.provider,
''',
    '''            "artifacts": artifacts,
            "post_artifact_text": post_artifact_text,
            "provider": result.provider,
''',
    'persistência do aviso posterior',
)

source = replace_once(
    source,
    '''        existing_result["reply"],
        existing_result.get("artifacts") or [],
        existing_result.get("sources") or [],
    )
''',
    '''        existing_result["reply"],
        existing_result.get("artifacts") or [],
        existing_result.get("sources") or [],
        existing_result.get("post_artifact_text") or "",
    )
''',
    'envio do aviso posterior à persistência',
)

WORKER.write_text(source, encoding='utf-8')
print('Entrega de artefatos organizada como texto, arquivo e texto.')
