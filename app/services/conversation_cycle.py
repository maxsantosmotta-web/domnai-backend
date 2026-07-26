from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _clean(value: Any, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def latest_cycle_state(messages: list[dict] | None) -> dict | None:
    for item in reversed(messages or []):
        if not isinstance(item, dict):
            continue
        state = item.get("contextState")
        if isinstance(state, dict) and _clean(state.get("cycleId"), 80):
            return dict(state)
    return None


def build_cycle_state(
    *,
    operation: str | None,
    message: str,
    previous: dict | None,
) -> dict:
    normalized_operation = _clean(operation, 180) or None
    previous_operation = _clean((previous or {}).get("operation"), 180) or None
    same_operation = previous is not None and previous_operation == normalized_operation

    cycle_id = _clean((previous or {}).get("cycleId"), 80) if same_operation else ""
    if not cycle_id:
        cycle_id = str(uuid4())

    first_message = _clean((previous or {}).get("firstMessage"), 500) if same_operation else ""
    if not first_message:
        first_message = _clean(message, 500)

    return {
        "version": 1,
        "cycleId": cycle_id,
        "operation": normalized_operation,
        "firstMessage": first_message,
        "lastUserMessage": _clean(message, 500),
        "status": "active",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
