from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.chat import ChatRequest
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ActiveChatState, ChatTask
from app.services.credit_meter import ensure_minimum_credit


router = APIRouter(prefix="/api/chat", tags=["chat-persistent"])


def _load_messages(state: ActiveChatState | None) -> list[dict]:
    if state is None:
        return []
    try:
        messages = json.loads(state.messages_json or "[]")
    except json.JSONDecodeError:
        return []
    return messages if isinstance(messages, list) else []


def _persist_queued_exchange(
    db,
    *,
    user_id: str,
    task_id: str,
    message: str,
    operation: str | None,
    attachments: list,
    now: datetime,
) -> None:
    state = db.get(ActiveChatState, user_id)
    if state is None:
        state = ActiveChatState(user_id=user_id, messages_json="[]")
        db.add(state)

    messages = _load_messages(state)
    messages.extend([
        {
            "id": f"user-{task_id}",
            "role": "user",
            "text": message,
            "attachments": [
                {
                    "id": f"attachment-{item.library_id}",
                    "libraryId": item.library_id,
                    "name": "",
                    "type": "file",
                    "mimeType": "",
                    "size": 0,
                }
                for item in attachments
            ],
            "sources": [],
            "isError": False,
            "taskId": task_id,
            "processing": False,
        },
        {
            "id": f"assistant-{task_id}",
            "role": "assistant",
            "text": "DomnAI está analisando...",
            "attachments": [],
            "sources": [],
            "isError": False,
            "taskId": task_id,
            "processing": True,
        },
    ])
    state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
    state.active_operation = operation
    state.updated_at = now


@router.post("/respond", status_code=status.HTTP_202_ACCEPTED)
def persistent_respond(payload: ChatRequest, session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para continuar.")

    ensure_minimum_credit(user_id)
    now = datetime.now(timezone.utc)
    task_id = str(uuid4())
    operation = payload.operation.strip() if payload.operation else None
    task = ChatTask(
        id=task_id,
        user_id=user_id,
        status="queued",
        request_json=json.dumps(
            {
                "message": message,
                "operation": operation,
                "history": [item.model_dump() for item in payload.history],
                "attachment_ids": [item.library_id for item in payload.attachments],
            },
            ensure_ascii=False,
        ),
        created_at=now,
        updated_at=now,
    )
    with session_scope() as db:
        db.add(task)
        _persist_queued_exchange(
            db,
            user_id=user_id,
            task_id=task_id,
            message=message,
            operation=operation,
            attachments=payload.attachments,
            now=now,
        )
        db.flush()

    return {
        "taskId": task_id,
        "status": "queued",
        "processing": True,
        "reply": "DomnAI está analisando...",
        "artifact": None,
        "artifacts": [],
        "sources": [],
        "operation": payload.operation,
    }
