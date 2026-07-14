from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ChatTask, LibraryAsset
from app.services.credit_meter import ensure_minimum_credit

router = APIRouter(prefix="/api/chat/tasks", tags=["chat-tasks"])


class ChatTaskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    operation: str | None = Field(default=None, max_length=180)
    history: list[dict] = Field(default_factory=list, max_length=40)
    attachment_ids: list[str] = Field(default_factory=list, max_length=10)


def _user_id(session: dict) -> str:
    value = str(session.get("sub") or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return value


def _load_attachments(user_id: str, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    with session_scope() as db:
        assets = db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.user_id == user_id,
                LibraryAsset.id.in_(list(dict.fromkeys(ids))),
            )
        ).all()
        return [{
            "id": item.id,
            "name": item.name,
            "mime_type": item.mime_type,
            "content": bytes(item.content or b""),
        } for item in assets]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_task(payload: ChatTaskRequest, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    ensure_minimum_credit(user_id)
    now = datetime.now(timezone.utc)
    task = ChatTask(
        id=str(uuid4()),
        user_id=user_id,
        status="queued",
        request_json=json.dumps({
            "message": payload.message.strip(),
            "operation": payload.operation,
            "history": payload.history,
            "attachments": _load_attachments(user_id, payload.attachment_ids),
        }, ensure_ascii=False, default=lambda value: ""),
        created_at=now,
        updated_at=now,
    )
    with session_scope() as db:
        db.add(task)
        db.flush()
        return {"taskId": task.id, "status": task.status}


@router.get("/{task_id}")
def get_task(task_id: str, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None or task.user_id != user_id:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        result = json.loads(task.result_json) if task.result_json else None
        return {
            "taskId": task.id,
            "status": task.status,
            "result": result,
            "error": task.error_message,
            "createdAt": task.created_at.isoformat(),
            "updatedAt": task.updated_at.isoformat(),
            "completedAt": task.completed_at.isoformat() if task.completed_at else None,
        }
