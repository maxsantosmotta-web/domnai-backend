from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.chat import ChatRequest
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ChatTask
from app.services.credit_meter import ensure_minimum_credit

router = APIRouter(prefix="/api/chat", tags=["chat-persistent"])


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
    task = ChatTask(
        id=task_id,
        user_id=user_id,
        status="queued",
        request_json=json.dumps(
            {
                "message": message,
                "operation": payload.operation.strip() if payload.operation else None,
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
    }
