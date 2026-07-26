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


def objective_cycle_event(
    *,
    operation: str | None,
    previous: dict | None,
    force_new: bool = False,
) -> dict:
    normalized_operation = _clean(operation, 180) or None
    previous_operation = _clean((previous or {}).get("operation"), 180) or None

    if previous is None:
        return {"opensNewCycle": True, "reason": "first_conversation"}
    if force_new:
        return {"opensNewCycle": True, "reason": "explicit_restart"}
    if previous_operation != normalized_operation:
        return {"opensNewCycle": True, "reason": "operation_changed"}
    return {"opensNewCycle": False, "reason": "continuation"}


def build_cycle_state(
    *,
    operation: str | None,
    message: str,
    previous: dict | None,
    force_new: bool = False,
) -> dict:
    normalized_operation = _clean(operation, 180) or None
    event = objective_cycle_event(
        operation=normalized_operation,
        previous=previous,
        force_new=force_new,
    )
    same_cycle = previous is not None and not event["opensNewCycle"]

    cycle_id = _clean((previous or {}).get("cycleId"), 80) if same_cycle else ""
    if not cycle_id:
        cycle_id = str(uuid4())

    first_message = _clean((previous or {}).get("firstMessage"), 500) if same_cycle else ""
    if not first_message:
        first_message = _clean(message, 500)

    return {
        "version": 2,
        "cycleId": cycle_id,
        "operation": normalized_operation,
        "firstMessage": first_message,
        "lastUserMessage": _clean(message, 500),
        "status": "active",
        "opensNewCycle": bool(event["opensNewCycle"]),
        "cycleReason": str(event["reason"]),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
