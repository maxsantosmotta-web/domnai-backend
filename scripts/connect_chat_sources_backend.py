from pathlib import Path

worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')

worker = worker.replace(
    'def _append_completed_response(user_id: str, payload: dict, reply: str, artifacts: list[dict]) -> None:',
    'def _append_completed_response(user_id: str, payload: dict, reply: str, artifacts: list[dict], sources: list[dict]) -> None:',
    1,
)

worker = worker.replace(
    '                "attachments": artifacts,\n                "isError": False,',
    '                "attachments": artifacts,\n                "sources": sources,\n                "isError": False,',
    1,
)

worker = worker.replace(
    '                    "attachments": [],\n                    "isError": False,',
    '                    "attachments": [],\n                    "sources": [],\n                    "isError": False,',
    1,
)

worker = worker.replace(
    '                "attachments": artifacts,\n                "isError": False,',
    '                "attachments": artifacts,\n                "sources": sources,\n                "isError": False,',
    1,
)

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
if old_call not in worker:
    raise RuntimeError('Não foi possível localizar a persistência final da resposta.')
worker = worker.replace(old_call, new_call, 1)
worker_path.write_text(worker, encoding='utf-8')

state_path = Path('/app/app/api/chat_state.py')
state = state_path.read_text(encoding='utf-8')

state = state.replace(
    '                "attachments": [],\n                "isError": False,',
    '                "attachments": [],\n                "sources": [],\n                "isError": False,',
    1,
)

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
    raise RuntimeError('Não foi possível localizar o bloco seguro das mensagens.')
state = state.replace(attachment_end, source_block, 1)
state = state.replace(
    '            "attachments": attachments,\n            "isError": bool(item.get("isError")),',
    '            "attachments": attachments,\n            "sources": sources if role == "assistant" else [],\n            "isError": bool(item.get("isError")),',
    1,
)
state_path.write_text(state, encoding='utf-8')
