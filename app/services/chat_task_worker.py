from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import session_scope
from app.models import ActiveChatState, ChatTask, LibraryAsset
from app.services.artifact_decision import decide_artifact
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


def _load_attachments(user_id: str, attachment_ids: list[str]) -> list[dict]:
    if not attachment_ids:
        return []
    unique_ids = list(dict.fromkeys(attachment_ids))
    with session_scope() as db:
        assets = db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.user_id == user_id,
                LibraryAsset.id.in_(unique_ids),
            )
        ).all()
        by_id = {item.id: item for item in assets}
        return [
            {
                "id": item.id,
                "name": item.name,
                "mime_type": item.mime_type,
                "content": bytes(item.content or b""),
            }
            for asset_id in unique_ids
            if (item := by_id.get(asset_id)) is not None
        ]


def _append_completed_response(user_id: str, payload: dict, reply: str, artifacts: list[dict]) -> None:
    task_id = str(payload.get("task_id") or "")
    if not task_id:
        return

    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            state = ActiveChatState(user_id=user_id, messages_json="[]")
            db.add(state)
        try:
            messages = json.loads(state.messages_json or "[]")
            if not isinstance(messages, list):
                messages = []
        except json.JSONDecodeError:
            messages = []

        replaced = False
        for index, item in enumerate(messages):
            if not isinstance(item, dict):
                continue
            if str(item.get("taskId") or "") != task_id:
                continue
            if item.get("role") != "assistant":
                continue
            messages[index] = {
                **item,
                "text": reply,
                "attachments": artifacts,
                "isError": False,
                "processing": False,
                "taskId": task_id,
            }
            replaced = True
            break

        if not replaced:
            has_user_message = any(
                isinstance(item, dict)
                and item.get("role") == "user"
                and str(item.get("taskId") or "") == task_id
                for item in messages
            )
            if not has_user_message:
                messages.append({
                    "id": f"user-{task_id}",
                    "role": "user",
                    "text": str(payload.get("message") or ""),
                    "attachments": [],
                    "isError": False,
                    "taskId": task_id,
                    "processing": False,
                })
            messages.append({
                "id": f"assistant-{task_id}",
                "role": "assistant",
                "text": reply,
                "attachments": artifacts,
                "isError": False,
                "taskId": task_id,
                "processing": False,
            })

        state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
        state.active_operation = payload.get("operation")
        state.updated_at = _now()


def _process_task(task_id: str) -> None:
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None:
            return
        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
        existing_result = json.loads(task.result_json) if task.result_json else None
        user_id = task.user_id

    if existing_result is None:
        ensure_minimum_credit(user_id)
        original_message = str(payload.get("message") or "").strip()
        operation = payload.get("operation")
        history = payload.get("history") or []
        attachments = _load_attachments(user_id, payload.get("attachment_ids") or [])
        diagnosis_state = load_diagnosis_state(user_id, operation)
        sources: list[dict] = []
        message_for_brain = original_message
        if should_research_web(original_message, operation):
            research = research_web(original_message)
            sources = research.sources
            message_for_brain = (
                f"{original_message}\n\nPESQUISA WEB VERIFICADA:\n{research.text}\n\n"
                "Use os fatos pesquisados e não invente fontes ou URLs."
            )
        result = generate_orchestrated_response(
            message=message_for_brain,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
        reply = result.text
        artifacts: list[dict] = []
        decision = decide_artifact(
            message=original_message,
            operation=operation,
            history=history,
            answer=reply,
        )
        if decision.get("action") == "create":
            try:
                from app.api.chat import _create_artifact
                artifact = _create_artifact(
                    user_id=user_id,
                    operation=operation,
                    answer=reply,
                    decision=decision,
                )
                artifacts.append(artifact)
                reply = f"{reply.rstrip()}\n\nArquivo criado e salvo na sua Biblioteca."
            except Exception:
                reply = f"{reply.rstrip()}\n\nNão foi possível gerar o arquivo nesta tentativa."
        elif decision.get("action") == "offer":
            from app.api.chat import _artifact_offer
            offer = _artifact_offer(decision.get("artifact_type"))
            if offer and offer.casefold() not in reply.casefold():
                reply = f"{reply.rstrip()}\n\n{offer}"

        existing_result = {
            "reply": reply,
            "artifacts": artifacts,
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
    _append_completed_response(
        user_id,
        payload,
        existing_result["reply"],
        existing_result.get("artifacts") or [],
    )
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
            time.sleep(1.0)
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
