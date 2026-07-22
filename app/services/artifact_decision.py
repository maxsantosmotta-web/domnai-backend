from __future__ import annotations

import json
import os
from typing import Any

from app.services.metered_brain import _openai_request


_NONE = {
    "action": "none",
    "artifact_type": None,
    "title": "",
    "sheet_name": "Dados",
    "headers": [],
    "rows": [],
}

_OFFER_MARKERS = (
    "posso gerar este conteúdo em pdf",
    "posso gerar esse conteúdo em pdf",
    "posso transformar este conteúdo em pdf",
    "posso organizar esse resultado em um pdf",
    "posso organizar este resultado em um pdf",
    "posso compilar esse resultado em um pdf",
    "posso compilar este resultado em um pdf",
    "pdf profissional",
    "planilha editável",
    "arquivo csv editável",
)

_ACCEPTANCE_EXACT = {"sim", "pode", "quero", "ok", "claro", "perfeito"}
_ACCEPTANCE_PHRASES = (
    "sim, pode", "sim pode", "pode gerar", "pode criar",
    "quero o pdf", "quero a planilha", "gere o pdf", "gera o pdf",
    "crie o pdf", "cria o pdf", "faça o pdf", "transforme em pdf",
    "transforma em pdf", "gere a planilha", "crie a planilha",
)

_SPREADSHEET_REQUEST_MARKERS = (
    "planilha", "excel", "xlsx", "csv", "tabela editável", "tabela editavel",
    "folha de cálculo", "folha de calculo", "linhas e colunas", "formato tabular",
    "quadro editável", "quadro editavel",
)

_EXPLICIT_ARTIFACT_MARKERS = (
    "pdf", *_SPREADSHEET_REQUEST_MARKERS, "gere um relatório", "crie um relatório",
    "crie o arquivo", "gere o arquivo", "transforme em arquivo", "transforma em arquivo",
)

_REUSE_MARKERS = (
    "abrir arquivo", "abre o arquivo", "baixar", "download", "manda o link",
    "envia o link", "me passa o link", "salvar na galeria",
)

_CREATED_MARKERS = (
    "arquivo criado", "pdf criado", "planilha criada", "enviado no chat",
)

_DIRECT_PDF_MARKERS = (
    "pdf", "em formato pdf", "manda isso no pdf", "mande isso no pdf",
    "me manda no pdf", "me mande no pdf", "gera o pdf", "gere o pdf",
    "cria o pdf", "crie o pdf", "faça o pdf", "transforma em pdf",
    "transforme em pdf", "fechar no pdf", "finalizar no pdf",
)


def _normalize(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _history_text(history: list[dict], limit: int = 12) -> str:
    return " ".join(_normalize(item.get("content") or "") for item in history[-limit:])


def _contains_any(value: str, markers: tuple[str, ...]) -> bool:
    return any(marker in value for marker in markers)


def _explicit_spreadsheet_request(value: str) -> bool:
    return _contains_any(_normalize(value), _SPREADSHEET_REQUEST_MARKERS)


def _accepted_offer(value: str) -> bool:
    normalized = _normalize(value).strip(" .,!?:;")
    if normalized in _ACCEPTANCE_EXACT:
        return True
    return any(normalized == phrase or normalized.startswith(f"{phrase} ") for phrase in _ACCEPTANCE_PHRASES)


def _artifact_type_from_offer(text: str) -> str:
    normalized = _normalize(text)
    if "planilha" in normalized or "xlsx" in normalized or "excel" in normalized:
        return "xlsx"
    if "csv" in normalized:
        return "csv"
    return "pdf"


def _remove_offer_from_answer(text: str) -> str:
    paragraphs = [part.strip() for part in str(text or "").split("\n\n") if part.strip()]
    kept = [part for part in paragraphs if not _contains_any(_normalize(part), _OFFER_MARKERS)]
    return "\n\n".join(kept).strip()


def _last_completed_assistant_answer(history: list[dict]) -> str:
    for item in reversed(history):
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        normalized = _normalize(content)
        if "openai respondeu http" in normalized or "não foi possível" in normalized:
            continue
        return _remove_offer_from_answer(content)
    return ""


def _direct_pdf_decision(message: str, operation: str | None, history: list[dict]) -> dict | None:
    normalized = _normalize(message)
    if not _contains_any(normalized, _DIRECT_PDF_MARKERS):
        return None
    if _explicit_spreadsheet_request(message):
        return None
    source_answer = _last_completed_assistant_answer(history)
    if not source_answer:
        return None
    return {
        "action": "create",
        "artifact_type": "pdf",
        "title": str(operation or "Relatório consolidado").strip()[:180],
        "sheet_name": "Dados",
        "headers": [],
        "rows": [],
        "source_answer": source_answer,
        "local_artifact_followup": True,
    }


def resolve_pending_artifact_acceptance(message: str, history: list[dict]) -> dict | None:
    direct = _direct_pdf_decision(message, None, history)
    if direct:
        return direct
    if _explicit_spreadsheet_request(message) or not _accepted_offer(message):
        return None

    for index in range(len(history) - 1, -1, -1):
        item = history[index]
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        content = str(item.get("content") or "").strip()
        if not _contains_any(_normalize(content), _OFFER_MARKERS):
            continue
        source_answer = _remove_offer_from_answer(content)
        if len(source_answer) < 120:
            for previous_index in range(index - 1, -1, -1):
                previous = history[previous_index]
                if str(previous.get("role") or "").strip().lower() != "assistant":
                    continue
                candidate = _remove_offer_from_answer(str(previous.get("content") or ""))
                if len(candidate) >= 120:
                    source_answer = candidate
                    break
        if len(source_answer) < 120:
            return None
        artifact_type = _artifact_type_from_offer(content)
        return {
            "action": "create",
            "artifact_type": artifact_type,
            "title": "Documento DomnAI",
            "sheet_name": "Dados",
            "headers": [],
            "rows": [],
            "source_answer": source_answer,
            "local_artifact_followup": True,
        }
    return None


def _strip_code_fence(text: str) -> str:
    value = str(text or "").strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            value = "\n".join(lines[1:-1]).strip()
    return value


def _clean_rows(value: Any, width: int) -> list[list[Any]]:
    if not isinstance(value, list) or width <= 0:
        return []
    rows: list[list[Any]] = []
    for raw_row in value[:5000]:
        if not isinstance(raw_row, list):
            continue
        row = list(raw_row[:width])
        if len(row) < width:
            row.extend([""] * (width - len(row)))
        rows.append(row)
    return rows


def _parse_decision(raw_text: str) -> dict:
    try:
        payload = json.loads(_strip_code_fence(raw_text))
    except (json.JSONDecodeError, TypeError):
        return dict(_NONE)
    if not isinstance(payload, dict):
        return dict(_NONE)

    action = str(payload.get("action") or "none").strip().lower()
    artifact_type = str(payload.get("artifact_type") or "").strip().lower() or None
    if action not in {"none", "offer", "create"}:
        action = "none"
    if artifact_type not in {"pdf", "xlsx", "csv"}:
        artifact_type = None
    if action != "none" and not artifact_type:
        action = "none"

    headers = [str(item or "").strip()[:180] for item in (payload.get("headers") or [])[:50]]
    headers = [item for item in headers if item]
    rows = _clean_rows(payload.get("rows"), len(headers))
    if action == "create" and artifact_type in {"xlsx", "csv"} and not headers:
        action = "offer"

    return {
        "action": action,
        "artifact_type": artifact_type,
        "title": str(payload.get("title") or "Documento DomnAI").strip()[:180],
        "sheet_name": str(payload.get("sheet_name") or "Dados").strip()[:31],
        "headers": headers,
        "rows": rows,
    }


def _requires_artifact_decision(message: str, operation: str | None, history: list[dict], answer: str) -> bool:
    del operation, answer
    normalized = _normalize(message)
    recent_text = _history_text(history)
    offer_already_made = _contains_any(recent_text, _OFFER_MARKERS)
    artifact_already_created = _contains_any(recent_text, _CREATED_MARKERS)
    if artifact_already_created and _contains_any(normalized, _REUSE_MARKERS):
        return False
    explicit_request = _contains_any(normalized, _EXPLICIT_ARTIFACT_MARKERS)
    accepted_previous_offer = offer_already_made and _accepted_offer(normalized)
    return explicit_request or accepted_previous_offer


def decide_artifact(*, message: str, operation: str | None, history: list[dict], answer: str) -> dict:
    direct = _direct_pdf_decision(message, operation, history)
    if direct:
        return direct

    accepted = resolve_pending_artifact_acceptance(message, history)
    if accepted:
        if operation and str(accepted.get("title") or "").casefold() == "documento domnai":
            accepted["title"] = str(operation).strip()[:180]
        return accepted

    if not _requires_artifact_decision(message, operation, history, answer):
        return dict(_NONE)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return dict(_NONE)

    request_payload = {
        "operation": operation,
        "current_message": message,
        "recent_history": history[-10:],
        "completed_answer": answer,
    }
    instructions = """
Você decide como criar um arquivo que foi pedido explicitamente pelo usuário.
Retorne somente JSON válido com:
{
  "action":"none|offer|create",
  "artifact_type":"pdf|xlsx|csv|null",
  "title":"nome claro do arquivo",
  "sheet_name":"nome curto da aba",
  "headers":["colunas da planilha"],
  "rows":[["valores"]]
}
Regras:
- Não ofereça arquivo por iniciativa própria.
- Só use create quando a mensagem atual pediu explicitamente um arquivo ou aceitou uma oferta anterior real.
- O formato explicitamente pedido na mensagem atual sempre tem prioridade.
- Para XLSX/CSV com action=create, produza headers e rows completos usando apenas dados sustentados pela conversa e pela resposta.
- Não invente números.
- O arquivo é entregue diretamente no chat e salvo automaticamente na Biblioteca.
""".strip()

    try:
        raw_text, _usage = _openai_request(
            api_key,
            {
                "model": os.getenv("DOMNAI_ARTIFACT_MODEL", os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini")).strip(),
                "instructions": instructions,
                "input": [{
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(request_payload, ensure_ascii=False)}],
                }],
                "temperature": 0.0,
                "max_output_tokens": 1800,
            },
        )
        return _parse_decision(raw_text)
    except Exception:
        return dict(_NONE)
