from __future__ import annotations

import json
import threading

from app.database import session_scope
from app.domnai_core.cutover_runtime import route_brain_request
from app.models import ChatTask
from app.services import chat_task_worker as worker

_context = threading.local()
_patched = False
_patch_lock = threading.Lock()
_original_process_task = worker._process_task
_original_generate = worker.generate_orchestrated_response


def _contextual_process_task(task_id: str) -> None:
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None:
            return
        payload = json.loads(task.request_json or "{}")
        _context.task_id = task_id
        _context.user_id = str(task.user_id)
        _context.local_artifact_followup = bool(payload.get("local_artifact_followup"))
    try:
        _original_process_task(task_id)
    finally:
        for name in ("task_id", "user_id", "local_artifact_followup"):
            if hasattr(_context, name):
                delattr(_context, name)


def _routed_generate(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    attachments: list[dict],
    diagnosis_state: dict | None,
):
    task_id = str(getattr(_context, "task_id", "") or "")
    user_id = str(getattr(_context, "user_id", "") or "")
    if not task_id or not user_id:
        return _original_generate(
            message=message,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )

    routed = route_brain_request(
        request_id=task_id,
        user_id=user_id,
        conversation_id=user_id,
        message=message,
        operation=operation,
        history=history,
        memory=diagnosis_state,
        attachments=attachments,
        local_artifact_followup=bool(getattr(_context, "local_artifact_followup", False)),
        legacy=lambda: _original_generate(
            message=message,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        ),
    )
    result = routed.result
    merged_timings = dict(result.timings or {})
    merged_timings.update({
        "cutover_route_new_core": 1 if routed.route == "new-core" else 0,
        "cutover_fallback": 1 if routed.fallback_used else 0,
    })
    return type(result)(
        text=result.text,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cached_input_tokens=result.cached_input_tokens,
        diagnosis_state=result.diagnosis_state,
        timings=merged_timings,
    )


def install_cutover_router() -> None:
    global _patched
    with _patch_lock:
        if _patched:
            return
        worker._process_task = _contextual_process_task
        worker.generate_orchestrated_response = _routed_generate
        _patched = True


def start_cutover_aware_chat_worker() -> None:
    install_cutover_router()
    worker.start_chat_task_worker()
