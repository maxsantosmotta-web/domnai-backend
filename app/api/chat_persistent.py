from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.chat import ChatRequest
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import ChatTask
from app.services.credit_meter import ensure_minimum_credit

router = APIRouter(prefix="/api/chat", tags=["chat-persistent"])


@router.post("/respond")
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

    deadline = time.monotonic() + 115
    while time.monotonic() < deadline:
        with session_scope() as db:
            current = db.get(ChatTask, task_id)
            if current is None:
                raise HTTPException(status_code=500, detail="A tarefa do chat desapareceu durante o processamento.")
            if current.status == "completed":
                result = json.loads(current.result_json or "{}")
                usage = result.get("usage") or {}
                artifacts = result.get("artifacts") or []
                return {
                    "reply": result.get("reply") or "O DomnAI não retornou uma resposta em texto.",
                    "artifact": artifacts[0] if artifacts else None,
                    "artifacts": artifacts,
                    "sources": result.get("sources") or [],
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "operation": payload.operation,
                    "taskId": task_id,
                    "usage": {
                        "inputTokens": usage.get("input_tokens", 0),
                        "cachedInputTokens": usage.get("cached_input_tokens", 0),
                        "outputTokens": usage.get("output_tokens", 0),
                        "costUsd": round(float(usage.get("cost_usd", 0)), 8),
                        "measuredCredits": usage.get("credits", 0),
                        "chargedCredits": usage.get("charged_credits", 0),
                        "adminExempt": usage.get("admin_exempt", False),
                        "remainingCredits": usage.get("remaining_credits"),
                    },
                }
            if current.status == "failed":
                raise HTTPException(status_code=503, detail=current.error_message or "Não foi possível concluir a resposta.")
        time.sleep(0.6)

    return {
        "reply": "A resposta continua sendo processada e será restaurada nesta conversa quando você voltar.",
        "artifact": None,
        "artifacts": [],
        "sources": [],
        "provider": "persistent-worker",
        "model": None,
        "operation": payload.operation,
        "taskId": task_id,
        "processing": True,
        "usage": {},
    }
