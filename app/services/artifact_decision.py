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


def decide_artifact(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    answer: str,
) -> dict:
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
- Use create quando o usuário pediu naturalmente um arquivo, pediu para baixar, aceitou uma oferta anterior ou deixou claro que quer a entrega agora.
- Use offer quando um arquivo agregaria valor relevante, mas o usuário ainda não pediu nem confirmou.
- Use none quando texto é a melhor entrega ou não há conteúdo suficiente para um arquivo útil.
- PDF é adequado para relatório, parecer, análise narrativa, plano ou documento de leitura.
- XLSX/CSV é adequado quando os dados precisam ser editados, calculados, filtrados, comparados ou reutilizados em linhas e colunas.
- Para XLSX/CSV com action=create, produza headers e rows completos usando apenas dados sustentados pela conversa e pela resposta. Não invente números.
- Prefira XLSX para uso humano e CSV quando o usuário pedir CSV ou quando o foco for importação de dados.
- Não escolha e-mail nem link externo. O sistema cria um arquivo interno e fornece o link autenticado somente depois da geração real.
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
