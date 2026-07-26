from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.operation_charge_decision import (
    ASK_CONFIRMATION,
    CHARGE,
    DO_NOT_CHARGE,
    decide_operation_charge,
)


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
    continuity_observation: dict | None = None,
    last_delivery: str = "",
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

    observation = continuity_observation if isinstance(continuity_observation, dict) else {}
    charge_decision = decide_operation_charge(
        objective_event=event,
        continuity=observation,
    )

    return {
        "version": 4,
        "cycleId": cycle_id,
        "operation": normalized_operation,
        "firstMessage": first_message,
        "lastUserMessage": _clean(message, 500),
        "lastDeliverySummary": _clean(last_delivery, 700),
        "status": "active",
        "opensNewCycle": bool(event["opensNewCycle"]),
        "cycleReason": str(event["reason"]),
        "continuityObservation": {
            "label": _clean(observation.get("label"), 40),
            "confidence": float(observation.get("confidence") or 0.0),
            "reason": _clean(observation.get("reason"), 120),
            "requiresConfirmation": bool(observation.get("requiresConfirmation")),
            "mode": "observation",
        },
        "chargeDecision": {
            "decision": _clean(charge_decision.get("decision"), 40),
            "reason": _clean(charge_decision.get("reason"), 120),
            "confidence": float(charge_decision.get("confidence") or 0.0),
            "source": _clean(charge_decision.get("source"), 60),
            "mode": "decision_only",
            "debitExecuted": False,
        },
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _validate_charge_decision_contract() -> None:
    objective = decide_operation_charge(
        objective_event={"opensNewCycle": True, "reason": "operation_changed"},
        continuity={"label": "NOVO_ASSUNTO", "confidence": 1.0},
    )
    continuation = decide_operation_charge(
        objective_event={"opensNewCycle": False, "reason": "continuation"},
        continuity={"label": "CONTINUACAO", "confidence": 0.92},
    )
    correction = decide_operation_charge(
        objective_event={"opensNewCycle": False, "reason": "continuation"},
        continuity={"label": "CORRECAO", "confidence": 0.99},
    )
    high_confidence_new_subject = decide_operation_charge(
        objective_event={"opensNewCycle": False, "reason": "continuation"},
        continuity={
            "label": "NOVO_ASSUNTO",
            "confidence": 0.96,
            "requiresConfirmation": False,
        },
    )
    low_confidence_new_subject = decide_operation_charge(
        objective_event={"opensNewCycle": False, "reason": "continuation"},
        continuity={
            "label": "NOVO_ASSUNTO",
            "confidence": 0.70,
            "requiresConfirmation": False,
        },
    )
    ambiguous = decide_operation_charge(
        objective_event={"opensNewCycle": False, "reason": "continuation"},
        continuity={"label": "AMBIGUO", "confidence": 0.50, "requiresConfirmation": True},
    )

    assert objective["decision"] == CHARGE
    assert continuation["decision"] == DO_NOT_CHARGE
    assert correction["decision"] == DO_NOT_CHARGE
    assert high_confidence_new_subject["decision"] == CHARGE
    assert low_confidence_new_subject["decision"] == ASK_CONFIRMATION
    assert ambiguous["decision"] == ASK_CONFIRMATION


_validate_charge_decision_contract()
