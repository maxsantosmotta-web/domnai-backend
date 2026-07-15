from __future__ import annotations

from app.services.artifact_decision import resolve_pending_artifact_acceptance


_BLOCKED_SOURCE_MARKERS = (
    "não consigo gerar",
    "nao consigo gerar",
    "não tenho como gerar",
    "nao tenho como gerar",
    "não posso gerar",
    "nao posso gerar",
    "arquivo criado",
    "pdf criado",
    "domnai está analisando",
    "domnai esta analisando",
)


def _normalize(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _is_direct_pdf_request(message: str) -> bool:
    normalized = _normalize(message)
    if any(term in normalized for term in ("link", "url", "abrir", "download", "baixar")):
        return False
    return "pdf" in normalized and any(
        term in normalized
        for term in (
            "gera",
            "gere",
            "gerar",
            "cria",
            "crie",
            "criar",
            "manda",
            "envia",
            "transforma",
            "transforme",
        )
    )


def _last_substantive_assistant_answer(history: list[dict]) -> str:
    for item in reversed(history):
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        candidate = str(item.get("content") or "").strip()
        normalized = _normalize(candidate)
        if len(candidate) < 120:
            continue
        if any(marker in normalized for marker in _BLOCKED_SOURCE_MARKERS):
            continue
        return candidate
    return ""


def resolve_local_artifact_request(message: str, history: list[dict]) -> dict | None:
    accepted = resolve_pending_artifact_acceptance(message, history)
    if accepted is not None:
        return accepted

    if not _is_direct_pdf_request(message):
        return None

    source_answer = _last_substantive_assistant_answer(history)
    if not source_answer:
        return None

    return {
        "action": "create",
        "artifact_type": "pdf",
        "title": "Documento DomnAI",
        "sheet_name": "Dados",
        "headers": [],
        "rows": [],
        "source_answer": source_answer,
        "local_artifact_followup": True,
    }
