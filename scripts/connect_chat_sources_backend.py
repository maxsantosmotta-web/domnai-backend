from pathlib import Path

worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')

old_signature = 'def _append_completed_response(user_id: str, payload: dict, reply: str, artifacts: list[dict]) -> None:'
new_signature = 'def _append_completed_response(user_id: str, payload: dict, reply: str, artifacts: list[dict], sources: list[dict]) -> None:'
if old_signature in worker:
    worker = worker.replace(old_signature, new_signature, 1)
elif new_signature not in worker:
    raise RuntimeError('Assinatura da persistência final não encontrada.')

old_assistant_payload = '                "attachments": artifacts,\n                "isError": False,'
new_assistant_payload = '                "attachments": artifacts,\n                "sources": sources,\n                "isError": False,'
worker = worker.replace(old_assistant_payload, new_assistant_payload)

old_user_payload = '                    "attachments": [],\n                    "isError": False,'
new_user_payload = '                    "attachments": [],\n                    "sources": [],\n                    "isError": False,'
worker = worker.replace(old_user_payload, new_user_payload, 1)

old_call = '''    _append_completed_response(
        user_id,
        payload,
        existing_result["reply"],
        existing_result.get("artifacts") or [],
    )'''
new_call = '''    _append_completed_response(
        user_id,
        payload,
        existing_result["reply"],
        existing_result.get("artifacts") or [],
        existing_result.get("sources") or [],
    )'''
if old_call in worker:
    worker = worker.replace(old_call, new_call, 1)
elif new_call not in worker:
    raise RuntimeError('Persistência final da resposta não encontrada.')

required_worker_markers = (
    new_signature,
    '"sources": sources,',
    'existing_result.get("sources") or [],',
)
missing_worker = [marker for marker in required_worker_markers if marker not in worker]
if missing_worker:
    raise RuntimeError(f'Consolidação de fontes incompleta no worker: {missing_worker}')

worker_path.write_text(worker, encoding='utf-8')

state_path = Path('/app/app/api/chat_state.py')
state = state_path.read_text(encoding='utf-8')

old_operation_payload = '                "attachments": [],\n                "isError": False,'
new_operation_payload = '                "attachments": [],\n                "sources": [],\n                "isError": False,'
state = state.replace(old_operation_payload, new_operation_payload, 1)

source_marker = '        sources = []\n        seen_urls = set()\n'
if source_marker not in state:
    attachment_end = '''        safe.append({
            "id": item.get("id"),'''
    source_block = '''        sources = []
        seen_urls = set()
        for source_item in (item.get("sources") or [])[:12]:
            url = str(source_item.get("url") or "").strip()
            if not url.startswith(("https://", "http://")) or url in seen_urls:
                continue
            seen_urls.add(url)
            title = str(source_item.get("title") or url).strip()[:240]
            sources.append({"title": title, "url": url[:1500]})

        safe.append({
            "id": item.get("id"),'''
    if attachment_end not in state:
        raise RuntimeError('Bloco seguro das mensagens não encontrado.')
    state = state.replace(attachment_end, source_block, 1)

old_sources_payload = '            "attachments": attachments,\n            "isError": bool(item.get("isError")),'
new_sources_payload = '            "attachments": attachments,\n            "sources": sources if role == "assistant" else [],\n            "isError": bool(item.get("isError")),'
if old_sources_payload in state:
    state = state.replace(old_sources_payload, new_sources_payload, 1)
elif new_sources_payload not in state:
    raise RuntimeError('Persistência segura das fontes não encontrada.')

required_state_markers = (
    source_marker,
    '"sources": sources if role == "assistant" else [],',
)
missing_state = [marker for marker in required_state_markers if marker not in state]
if missing_state:
    raise RuntimeError(f'Consolidação de fontes incompleta no estado do chat: {missing_state}')

state_path.write_text(state, encoding='utf-8')
