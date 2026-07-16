from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ChatTask

router = APIRouter(prefix="/api/chat/tasks", tags=["chat-tasks"])


def _user_id(session: dict) -> str:
    value = str(session.get("sub") or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return value


@router.post("/{task_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_task(task_id: str, session: dict = Depends(require_authenticated_user)):
    """Reabre a mesma tarefa para preservar a chave idempotente de cobrança."""
    user_id = _user_id(session)
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None or task.user_id != user_id:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

        if task.status == "failed":
            task.status = "queued"
            task.error_message = None
            task.completed_at = None
            task.updated_at = datetime.now(timezone.utc)

        return {
            "taskId": task.id,
            "status": task.status,
            "reused": True,
        }


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
