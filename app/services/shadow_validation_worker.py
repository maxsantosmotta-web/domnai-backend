from __future__ import annotations

import json
import logging
import threading
import time
from functools import lru_cache

from sqlalchemy import text

from app.database import session_scope
from app.domnai_core.shadow_results import PersistingShadowComparisonSink, PostgresShadowResultStore
from app.domnai_core.shadow_validation import ShadowValidationSettings, ShadowValidator

logger = logging.getLogger("domnai.shadow_worker")
_started = False
_lock = threading.Lock()


@lru_cache(maxsize=1)
def _store() -> PostgresShadowResultStore:
    store = PostgresShadowResultStore()
    store.ensure_schema()
    return store


def _claim_completed_task() -> dict | None:
    store = _store()
    with session_scope() as db:
        row = db.execute(text(f"""
            SELECT t.id, t.user_id, t.request_json, t.result_json
            FROM chat_tasks t
            WHERE t.status = 'completed'
              AND t.result_json IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM {store.TABLE} s
                  WHERE s.request_id = t.id
              )
            ORDER BY t.completed_at ASC NULLS LAST
            LIMIT 1
        """)).mappings().first()
    return dict(row) if row else None


def process_one_shadow_task(
    *,
    settings: ShadowValidationSettings | None = None,
    candidate=None,
    store: PostgresShadowResultStore | None = None,
) -> bool:
    resolved = settings or ShadowValidationSettings.from_env()
    if not resolved.enabled:
        return False
    task = _claim_completed_task()
    if task is None:
        return False
    request_id = str(task["id"])
    user_id = str(task["user_id"])
    if not resolved.selects(f"{user_id}:{request_id}"):
        return False
    request_payload = json.loads(task["request_json"] or "{}")
    legacy_result = json.loads(task["result_json"] or "{}")
    resolved_store = store or _store()
    validator = ShadowValidator(
        resolved,
        sink=PersistingShadowComparisonSink(resolved_store),
        candidate=candidate,
    )
    validator.run(
        request_id=request_id,
        user_id=user_id,
        conversation_id=user_id,
        message=str(request_payload.get("message") or ""),
        operation=request_payload.get("operation"),
        history=request_payload.get("history") or [],
        legacy_text=str(legacy_result.get("reply") or ""),
        legacy_provider=str(legacy_result.get("provider") or "legacy"),
    )
    return True


def _loop() -> None:
    while True:
        try:
            settings = ShadowValidationSettings.from_env()
            if not settings.enabled:
                time.sleep(5)
                continue
            processed = process_one_shadow_task(settings=settings)
            if not processed:
                time.sleep(1)
        except Exception:
            logger.exception("Falha isolada no worker de validação shadow.")
            time.sleep(2)


def start_shadow_validation_worker() -> bool:
    global _started
    try:
        settings = ShadowValidationSettings.from_env()
    except Exception:
        logger.exception("Configuração inválida do worker shadow.")
        return False
    if not settings.enabled:
        return False
    with _lock:
        if _started:
            return True
        _started = True
        threading.Thread(target=_loop, name="domnai-shadow-worker", daemon=True).start()
    return True
