from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.chat import ChatRequest
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ChatTask
from app.services.credit_meter import ensure_minimum_credit

router = APIRouter(prefix="/api/chat", tags=["chat-persistent"])

_ACTIVE_STATUSES = {"queued", "processing", "generated"}


def _normalized_operation(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _find_matching_active_task(user_id: str, message: str, operation: str | None) -> ChatTask | None:
    with session_scope() as db:
        candidates = db.scalars(
            select(ChatTask)
            .where(
                ChatTask.user_id == user_id,
                ChatTask.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(ChatTask.created_at.desc())
            .limit(20)
        ).all()

        for task in candidates:
            try:
                payload = json.loads(task.request_json or "{}")
            except json.JSONDecodeError:
                continue
            if str(payload.get("message") or "").strip() != message:
                continue
            if _normalized_operation(payload.get("operation")) != operation:
                continue
            return task
    return None


@router.post("/respond", status_code=status.HTTP_202_ACCEPTED)
def persistent_respond(payload: ChatRequest, session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para continuar.")

    operation = _normalized_operation(payload.operation)
    existing = _find_matching_active_task(user_id, message, operation)
    if existing is not None:
        return {
            "taskId": existing.id,
            "status": existing.status,
            "processing": True,
            "reply": "DomnAI está analisando...",
            "artifact": None,
            "artifacts": [],
            "sources": [],
            "operation": payload.operation,
            "reused": True,
        }

    ensure_minimum_credit(user_id)
    now = datetime.now(timezone.utc)
    task_id = str(uuid4())
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
        "reused": False,
    }
