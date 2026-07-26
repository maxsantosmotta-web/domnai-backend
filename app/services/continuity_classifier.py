from __future__ import annotations

import re
import unicodedata
from typing import Any


CONTINUATION = "CONTINUACAO"
CORRECTION = "CORRECAO"
NEW_SUBJECT = "NOVO_ASSUNTO"
AMBIGUOUS = "AMBIGUO"

_CORRECTION_MARKERS = (
    "corrigindo",
    "correcao",
    "nao e",
    "nao era",
    "na verdade",
    "quis dizer",
    "em vez de",
    "o correto e",
    "tem 120",
)

_CONTINUATION_MARKERS = (
    "e se",
    "nesse caso",
    "sobre isso",
    "com isso",
    "entao",
    "continue",
    "explique melhor",
    "detalhe",
    "refaca",
    "ajuste",
)

_NEW_SUBJECT_MARKERS = (
    "mudando de assunto",
    "outro assunto",
    "agora quero",
    "agora monte",
    "agora preciso",
    "outra coisa",
    "novo tema",
    "nova analise",
)

_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "essa", "esse", "esta", "este", "eu", "isso", "mais", "me", "na",
    "nas", "no", "nos", "o", "os", "ou", "para", "por", "que", "se", "sem", "um",
    "uma", "voce",
}


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().strip().split())


def _terms(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", _normalize(value))
        if len(token) >= 3 and token not in _STOPWORDS
    }


def _overlap(left: Any, right: Any) -> float:
    left_terms = _terms(left)
    right_terms = _terms(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms)))


def classify_continuity(
    *,
    operation: str | None,
    previous_state: dict | None,
    new_message: str,
    last_delivery: str = "",
) -> dict:
    message = _normalize(new_message)
    previous = previous_state if isinstance(previous_state, dict) else None

    if previous is None:
        return {
            "label": CONTINUATION,
            "confidence": 1.0,
            "reason": "first_conversation",
            "requiresConfirmation": False,
        }

    previous_operation = _normalize(previous.get("operation"))
    current_operation = _normalize(operation)
    if previous_operation != current_operation:
        return {
            "label": NEW_SUBJECT,
            "confidence": 1.0,
            "reason": "operation_changed",
            "requiresConfirmation": False,
        }

    if any(marker in message for marker in _CORRECTION_MARKERS):
        return {
            "label": CORRECTION,
            "confidence": 0.99,
            "reason": "correction_marker",
            "requiresConfirmation": False,
        }

    context = " ".join(
        part
        for part in (
            str(previous.get("firstMessage") or ""),
            str(previous.get("lastUserMessage") or ""),
            str(previous.get("lastDeliverySummary") or ""),
            str(last_delivery or ""),
        )
        if part
    )
    semantic_overlap = _overlap(message, context)

    if any(marker in message for marker in _NEW_SUBJECT_MARKERS):
        if semantic_overlap <= 0.20:
            return {
                "label": NEW_SUBJECT,
                "confidence": 0.96,
                "reason": "explicit_new_subject",
                "requiresConfirmation": False,
            }
        return {
            "label": AMBIGUOUS,
            "confidence": 0.60,
            "reason": "new_subject_marker_with_context_overlap",
            "requiresConfirmation": True,
        }

    if any(marker in message for marker in _CONTINUATION_MARKERS) or semantic_overlap >= 0.34:
        return {
            "label": CONTINUATION,
            "confidence": 0.92 if semantic_overlap >= 0.34 else 0.86,
            "reason": "context_continuity",
            "requiresConfirmation": False,
        }

    return {
        "label": AMBIGUOUS,
        "confidence": 0.50,
        "reason": "insufficient_context_overlap",
        "requiresConfirmation": True,
    }
