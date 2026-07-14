from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import session_scope
from app.models import ChatTask
from app.services.credit_meter import charge_usage, ensure_minimum_credit
from app.services.diagnosis_memory import load_diagnosis_state, save_diagnosis_state
from app.services.orchestrated_brain import generate_orchestrated_response
from app.services.web_research import research_web, should_research_web

_worker_started = False
_worker_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc)


def recover_interrupted_tasks() -> None:
    with session_scope() as db:
        db.execute(
            update(ChatTask)
            .where(ChatTask.status == "processing")
            .values(status="queued", updated_at=_now())
        )


def _claim_next_task() -> str | None:
    with session_scope() as db:
        task = db.scalar(
            select(ChatTask)
            .where(ChatTask.status.in_(["queued", "generated"]))
            .order_by(ChatTask.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if task is None:
            return None
        if task.status == "queued":
            task.status = "processing"
            task.updated_at = _now()
        return task.id


def _process_task(task_id: str) -> None:
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None:
            return
        payload = json.loads(task.request_json)
        existing_result = json.loads(task.result_json) if task.result_json else None
        user_id = task.user_id

    if existing_result is None:
        ensure_minimum_credit(user_id)
        message = str(payload.get("message") or "").strip()
        operation = payload.get("operation")
        history = payload.get("history") or []
        attachments = payload.get("attachments") or []
        diagnosis_state = load_diagnosis_state(user_id, operation)
        sources = []
        research_text = ""
        if should_research_web(message, operation):
            research = research_web(message)
            research_text = research.text
            sources = research.sources
            message = (
                f"{message}\n\nPESQUISA WEB VERIFICADA PARA USO NA RESPOSTA:\n{research_text}\n\n"
                "Use apenas fatos sustentados pela pesquisa e cite as fontes reais fornecidas."
            )
        result = generate_orchestrated_response(
            message=message,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
        existing_result = {
            "reply": result.text,
            "provider": result.provider,
            "model": result.model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cached_input_tokens": result.cached_input_tokens,
            "diagnosis_state": result.diagnosis_state,
            "sources": sources,
        }
        with session_scope() as db:
            task = db.get(ChatTask, task_id)
            if task is None:
                return
            task.result_json = json.dumps(existing_result, ensure_ascii=False)
            task.status = "generated"
            task.updated_at = _now()

    from app.services.metered_brain import MeteredBrainResult
    meter_result = MeteredBrainResult(
        text=existing_result["reply"],
        provider=existing_result["provider"],
        model=existing_result["model"],
        input_tokens=int(existing_result.get("input_tokens") or 0),
        output_tokens=int(existing_result.get("output_tokens") or 0),
        cached_input_tokens=int(existing_result.get("cached_input_tokens") or 0),
        diagnosis_state=existing_result.get("diagnosis_state"),
    )
    usage = charge_usage(user_id, meter_result, idempotency_key=f"chat-task:{task_id}")
    if meter_result.diagnosis_state is not None:
        try:
            save_diagnosis_state(user_id, payload.get("operation"), meter_result.diagnosis_state)
        except Exception:
            pass
    existing_result["usage"] = usage
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None:
            return
        task.result_json = json.dumps(existing_result, ensure_ascii=False)
        task.status = "completed"
        task.completed_at = _now()
        task.updated_at = _now()
        task.credit_transaction_key = f"chat-task:{task_id}"


def _loop() -> None:
    recover_interrupted_tasks()
    while True:
        task_id = _claim_next_task()
        if not task_id:
            time.sleep(1.5)
            continue
        try:
            _process_task(task_id)
        except Exception as exc:
            with session_scope() as db:
                task = db.get(ChatTask, task_id)
                if task is not None:
                    task.status = "failed"
                    task.error_message = str(exc)[:4000]
                    task.updated_at = _now()


def start_chat_task_worker() -> None:
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
        threading.Thread(target=_loop, name="domnai-chat-worker", daemon=True).start()
