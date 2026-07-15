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

_ACCEPTANCE_EXACT = {
    "sim",
    "pode",
    "quero",
    "ok",
    "claro",
    "perfeito",
}

_ACCEPTANCE_PHRASES = (
    "sim, pode",
    "sim pode",
    "pode gerar",
    "pode criar",
    "quero o pdf",
    "quero a planilha",
    "gere o pdf",
    "gera o pdf",
    "crie o pdf",
    "cria o pdf",
    "faça o pdf",
    "transforme em pdf",
    "transforma em pdf",
    "gere a planilha",
    "crie a planilha",
)

_EXPLICIT_ARTIFACT_MARKERS = (
    "pdf",
    "planilha",
    "xlsx",
    "excel",
    "csv",
    "gere um relatório",
    "crie um relatório",
    "crie o arquivo",
    "gere o arquivo",
    "transforme em arquivo",
    "transforma em arquivo",
)

_REUSE_MARKERS = (
    "abrir arquivo",
    "abre o arquivo",
    "baixar",
    "download",
    "manda o link",
    "envia o link",
    "me passa o link",
    "salvar na galeria",
)

_CREATED_MARKERS = (
    "arquivo criado",
    "pdf criado",
    "planilha criada",
    "enviado no chat",
)


def _normalize(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _history_text(history: list[dict], limit: int = 12) -> str:
    return " ".join(_normalize(item.get("content") or "") for item in history[-limit:])


def _contains_any(value: str, markers: tuple[str, ...]) -> bool:
    return any(marker in value for marker in markers)


def _accepted_offer(value: str) -> bool:
    normalized = _normalize(value).strip(" .,!?:;")
    if normalized in _ACCEPTANCE_EXACT:
        return True
    return any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in _ACCEPTANCE_PHRASES
    )


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


def resolve_pending_artifact_acceptance(message: str, history: list[dict]) -> dict | None:
    """Resolve um aceite usando o conteúdo já concluído, sem nova chamada de IA."""
    if not _accepted_offer(message):
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


def _requires_artifact_decision(
    message: str,
    operation: str | None,
    history: list[dict],
    answer: str,
) -> bool:
    normalized = _normalize(message)
    recent_text = _history_text(history)
    offer_already_made = _contains_any(recent_text, _OFFER_MARKERS)
    artifact_already_created = _contains_any(recent_text, _CREATED_MARKERS)

    if artifact_already_created and _contains_any(normalized, _REUSE_MARKERS):
        return False

    explicit_request = _contains_any(normalized, _EXPLICIT_ARTIFACT_MARKERS)
    accepted_previous_offer = offer_already_made and _accepted_offer(normalized)

    if explicit_request or accepted_previous_offer:
        return True
    if offer_already_made:
        return False
    return bool(operation and len(str(answer or "").strip()) >= 1000)


def decide_artifact(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    answer: str,
) -> dict:
    accepted = resolve_pending_artifact_acceptance(message, history)
    if accepted:
        return accepted

    if not _requires_artifact_decision(message, operation, history, answer):
        return dict(_NONE)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return dict(_NONE)

    recent_history = history[-10:]
    request_payload = {
        "operation": operation,
        "current_message": message,
        "recent_history": recent_history,
        "completed_answer": answer,
    }

    instructions = """
Você decide a melhor forma de entrega de uma resposta concluída pelo DomnAI.
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
- Não escolha formato por uma lista fixa de operações. Analise o pedido, o histórico e o conteúdo concluído.
- Use create quando o usuário pediu naturalmente um arquivo.
- Use offer somente quando um arquivo agregaria valor relevante, a explicação estiver concluída e não existir oferta anterior no histórico.
- Uma oferta de arquivo pode acontecer no máximo uma vez por conversa.
- Use none quando texto é a melhor entrega, não há conteúdo suficiente ou uma oferta anterior não foi aceita.
- PDF é adequado para relatório, parecer, análise narrativa, plano ou documento de leitura.
- XLSX/CSV é adequado quando os dados precisam ser editados, calculados, filtrados, comparados ou reutilizados em linhas e colunas.
- Para XLSX/CSV com action=create, produza headers e rows completos usando apenas dados sustentados pela conversa e pela resposta. Não invente números.
- Prefira XLSX para uso humano e CSV quando o usuário pedir CSV ou quando o foco for importação de dados.
- Não escolha e-mail nem link externo. O arquivo é entregue diretamente no chat e salvo automaticamente na Biblioteca após a geração real.
""".strip()

    try:
        raw_text, _usage = _openai_request(
            api_key,
            {
                "model": os.getenv("DOMNAI_ARTIFACT_MODEL", os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini")).strip(),
                "instructions": instructions,
                "input": [{
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": json.dumps(request_payload, ensure_ascii=False),
                    }],
                }],
                "temperature": 0.0,
                "max_output_tokens": 1800,
            },
        )
        return _parse_decision(raw_text)
    except Exception:
        return dict(_NONE)
