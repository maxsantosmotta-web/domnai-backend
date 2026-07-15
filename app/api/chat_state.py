import json

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ActiveChatState
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
        text = str(item.get("text") or "")[:20000]
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
        safe.append({
            "id": item.get("id"),
            "role": role,
            "text": text,
            "attachments": attachments,
            "isError": bool(item.get("isError")),
            "taskId": task_id,
            "processing": processing if role == "assistant" else False,
        })
    return safe


@router.get("")
def get_chat_state(session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            return {"messages": [], "activeOperation": None}
        try:
            messages = json.loads(state.messages_json or "[]")
        except json.JSONDecodeError:
            messages = []
        return {
            "messages": messages if isinstance(messages, list) else [],
            "activeOperation": state.active_operation,
            "updatedAt": state.updated_at.isoformat(),
        }


@router.put("")
def save_chat_state(payload: ChatStatePayload, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    messages = _safe_messages(payload.messages)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
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
