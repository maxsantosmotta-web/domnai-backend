from __future__ import annotations

from typing import Any


CHARGE = "COBRAR"
DO_NOT_CHARGE = "NAO_COBRAR"
ASK_CONFIRMATION = "PEDIR_CONFIRMACAO"

HIGH_CONFIDENCE_THRESHOLD = 0.90


def decide_operation_charge(
    *,
    objective_event: dict | None,
    continuity: dict | None,
) -> dict:
    event = objective_event if isinstance(objective_event, dict) else {}
    observation = continuity if isinstance(continuity, dict) else {}

    event_reason = str(event.get("reason") or "").strip()
    opens_new_cycle = bool(event.get("opensNewCycle"))
    label = str(observation.get("label") or "").strip().upper()
    confidence = float(observation.get("confidence") or 0.0)
    requires_confirmation = bool(observation.get("requiresConfirmation"))

    if opens_new_cycle and event_reason in {
        "first_conversation",
        "operation_changed",
        "explicit_restart",
        "confirmed_new_analysis",
    }:
        return {
            "decision": CHARGE,
            "reason": event_reason,
            "confidence": 1.0,
            "source": "objective_rule",
        }

    if label in {"CONTINUACAO", "CORRECAO"}:
        return {
            "decision": DO_NOT_CHARGE,
            "reason": str(observation.get("reason") or label.casefold()),
            "confidence": confidence,
            "source": "continuity_classifier",
        }

    if label == "NOVO_ASSUNTO":
        if not requires_confirmation and confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return {
                "decision": CHARGE,
                "reason": str(observation.get("reason") or "high_confidence_new_subject"),
                "confidence": confidence,
                "source": "continuity_classifier",
            }
        return {
            "decision": ASK_CONFIRMATION,
            "reason": "low_confidence_new_subject",
            "confidence": confidence,
            "source": "safety_gate",
        }

    return {
        "decision": ASK_CONFIRMATION,
        "reason": str(observation.get("reason") or "ambiguous_context"),
        "confidence": confidence,
        "source": "safety_gate",
    }
