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
    "posso transformar este conteúdo em pdf",
    "posso organizar esse resultado em um pdf",
    "posso organizar este resultado em um pdf",
    "pdf profissional",
    "planilha editável",
    "arquivo csv editável",
)

_ACCEPTANCE_MARKERS = (
    "sim",
    "pode",
    "pode gerar",
    "pode criar",
    "quero",
    "gera",
    "gere",
    "cria",
    "crie",
    "faça",
    "transforma",
    "transforme",
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

    # Abrir, baixar ou pedir o link de um arquivo existente não deve iniciar
    # uma nova geração. Esse pedido será tratado pelo fluxo de reutilização.
    if artifact_already_created and _contains_any(normalized, _REUSE_MARKERS):
        return False

    explicit_request = _contains_any(normalized, _EXPLICIT_ARTIFACT_MARKERS)
    accepted_previous_offer = offer_already_made and _contains_any(normalized, _ACCEPTANCE_MARKERS)

    if explicit_request or accepted_previous_offer:
        return True

    # Depois de uma oferta, qualquer outra mensagem que não seja aceite ou
    # pedido explícito não pode disparar nova oferta naquela conversa.
    if offer_already_made:
        return False

    # A oferta espontânea só é avaliada no final de uma resposta substancial
    # de uma operação, e apenas enquanto ainda não houve oferta anterior.
    return bool(operation and len(str(answer or "").strip()) >= 1000)


def decide_artifact(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    answer: str,
) -> dict:
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
- Use create quando o usuário pediu naturalmente um arquivo ou aceitou claramente uma oferta anterior.
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
