import json

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ActiveChatState, ChatTask
from app.services.diagnosis_memory import clear_diagnosis_state


router = APIRouter(prefix="/api/chat-state", tags=["chat-state"])


class ChatStatePayload(BaseModel):
    messages: list[dict] = Field(default_factory=list, max_length=300)
    active_operation: str | None = Field(default=None, max_length=120)


def _user_id(session: dict) -> str:
    value = str(session.get("sub") or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return value


def _safe_messages(items: list[dict]) -> list[dict]:
    safe = []
    for item in items[-300:]:
        role = str(item.get("role") or "").strip().lower()
        text = str(item.get("text") or "")
        if role not in {"user", "assistant", "operation"}:
            continue

        task_id = str(item.get("taskId") or "")[:180] or None
        processing = bool(item.get("processing"))

        if role == "operation":
            safe.append({
                "id": item.get("id"),
                "role": "operation",
                "text": text[:180],
                "operationId": str(item.get("operationId") or "")[:120] or None,
                "attachments": [],
                "sources": [],
                "isError": False,
                "taskId": task_id,
                "processing": False,
            })
            continue

        attachments = []
        for attachment in (item.get("attachments") or [])[:20]:
            attachments.append({
                "id": str(attachment.get("id") or "")[:180],
                "libraryId": str(attachment.get("libraryId") or "")[:180] or None,
                "name": str(attachment.get("name") or "")[:255],
                "type": str(attachment.get("type") or "file")[:40],
                "mimeType": str(attachment.get("mimeType") or "")[:120],
                "size": int(attachment.get("size") or 0),
            })

        sources = []
        seen_urls = set()
        for source_item in (item.get("sources") or [])[:12]:
            url = str(source_item.get("url") or "").strip()
            if not url.startswith(("https://", "http://")) or url in seen_urls:
                continue
            seen_urls.add(url)
            title = str(source_item.get("title") or url).strip()[:240]
            sources.append({"title": title, "url": url[:1500]})

        safe.append({
            "id": item.get("id"),
            "role": role,
            "text": text,
            "attachments": attachments,
            "sources": sources if role == "assistant" else [],
            "isError": bool(item.get("isError")),
            "taskId": task_id,
            "processing": processing if role == "assistant" else False,
        })
    return safe


def _load_messages(state: ActiveChatState | None) -> list[dict]:
    if state is None:
        return []
    try:
        messages = json.loads(state.messages_json or "[]")
    except json.JSONDecodeError:
        return []
    return messages if isinstance(messages, list) else []


def _task_key(item: dict) -> tuple[str, str] | None:
    task_id = str(item.get("taskId") or "").strip()
    role = str(item.get("role") or "").strip()
    if not task_id or role not in {"user", "assistant"}:
        return None
    return task_id, role


def _completed_assistant(task: ChatTask, fallback: dict | None) -> dict | None:
    if task.status != "completed" or not task.result_json:
        return fallback
    try:
        result = json.loads(task.result_json)
    except json.JSONDecodeError:
        return fallback
    return {
        "id": (fallback or {}).get("id") or f"assistant-{task.id}",
        "role": "assistant",
        "text": str(result.get("reply") or ""),
        "attachments": result.get("artifacts") or [],
        "sources": result.get("sources") or [],
        "isError": False,
        "taskId": task.id,
        "processing": False,
    }


def _merge_server_task_messages(db, user_id: str, incoming: list[dict], existing: list[dict]) -> list[dict]:
    incoming_by_key = {key: item for item in incoming if (key := _task_key(item))}
    existing_by_key = {key: item for item in existing if (key := _task_key(item))}
    task_ids = {task_id for task_id, _role in set(incoming_by_key) | set(existing_by_key)}
    if not task_ids:
        return incoming

    tasks = db.scalars(
        select(ChatTask).where(ChatTask.user_id == user_id, ChatTask.id.in_(task_ids))
    ).all()
    tasks_by_id = {task.id: task for task in tasks}

    merged = list(incoming)
    positions = {key: index for index, item in enumerate(merged) if (key := _task_key(item))}

    for key in set(incoming_by_key) | set(existing_by_key):
        task_id, role = key
        task = tasks_by_id.get(task_id)
        existing_item = existing_by_key.get(key)
        incoming_item = incoming_by_key.get(key)
        authoritative = incoming_item

        if role == "assistant" and task is not None:
            if task.status == "completed":
                authoritative = _completed_assistant(task, existing_item or incoming_item)
            elif existing_item and not existing_item.get("processing") and not existing_item.get("isError"):
                authoritative = existing_item
            elif task.status in {"queued", "processing", "generated"} and existing_item:
                authoritative = existing_item
        elif incoming_item is None and existing_item is not None and task is not None:
            authoritative = existing_item

        if authoritative is None:
            continue
        if key in positions:
            merged[positions[key]] = authoritative
        else:
            positions[key] = len(merged)
            merged.append(authoritative)

    return merged[-300:]


@router.get("")
def get_chat_state(session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            return {"messages": [], "activeOperation": None}
        messages = _load_messages(state)
        return {
            "messages": messages,
            "activeOperation": state.active_operation,
            "updatedAt": state.updated_at.isoformat(),
        }


@router.put("")
def save_chat_state(payload: ChatStatePayload, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    incoming = _safe_messages(payload.messages)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        existing = _load_messages(state)
        messages = _merge_server_task_messages(db, user_id, incoming, existing)
        if state is None:
            state = ActiveChatState(user_id=user_id)
            db.add(state)
        state.messages_json = json.dumps(messages, ensure_ascii=False)
        state.active_operation = payload.active_operation
        db.flush()
        return {"saved": True, "messageCount": len(messages)}


@router.delete("")
def clear_chat_state(session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is not None:
            db.delete(state)
    try:
        clear_diagnosis_state(user_id)
    except Exception:
        pass
    return Response(status_code=204)
