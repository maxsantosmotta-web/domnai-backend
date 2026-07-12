import json

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ActiveChatState, ChatConversation


router = APIRouter(prefix="/api/chat-state", tags=["chat-state"])


class ChatStatePayload(BaseModel):
    messages: list[dict] = Field(default_factory=list, max_length=200)
    active_operation: str | None = Field(default=None, max_length=120)


class NewOperationPayload(BaseModel):
    messages: list[dict] = Field(default_factory=list, max_length=200)
    current_operation: str | None = Field(default=None, max_length=120)
    current_operation_name: str | None = Field(default=None, max_length=180)
    next_operation: str = Field(min_length=1, max_length=120)
    next_operation_name: str = Field(min_length=1, max_length=180)


def _user_id(session: dict) -> str:
    value = str(session.get("sub") or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return value


def _safe_messages(items: list[dict]) -> list[dict]:
    safe = []
    for item in items[-200:]:
        role = str(item.get("role") or "").strip().lower()
        text = str(item.get("text") or "")[:20000]
        if role not in {"user", "assistant"}:
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
        })
    return safe


def _conversation_title(messages: list[dict], operation_name: str | None) -> str:
    for item in messages:
        if item.get("role") == "user" and str(item.get("text") or "").strip():
            return str(item["text"]).strip()[:180]
    return (operation_name or "Conversa DomnAI")[:180]


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


@router.post("/new-operation")
def start_new_operation(payload: NewOperationPayload, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    messages = _safe_messages(payload.messages)

    with session_scope() as db:
        archived_id = None
        if messages:
            archived = ChatConversation(
                user_id=user_id,
                title=_conversation_title(messages, payload.current_operation_name),
                operation_id=payload.current_operation,
                messages_json=json.dumps(messages, ensure_ascii=False),
            )
            db.add(archived)
            db.flush()
            archived_id = archived.id

        state = db.get(ActiveChatState, user_id)
        if state is None:
            state = ActiveChatState(user_id=user_id)
            db.add(state)
        state.messages_json = "[]"
        state.active_operation = payload.next_operation
        db.flush()

        return {
            "started": True,
            "archivedConversationId": archived_id,
            "activeOperation": payload.next_operation,
            "activeOperationName": payload.next_operation_name,
            "messages": [],
        }


@router.delete("")
def clear_chat_state(session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is not None:
            db.delete(state)
    return Response(status_code=204)
