from __future__ import annotations

import json
import os
import re
import unicodedata
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
    "posso gerar este conteudo em pdf",
    "posso gerar esse conteudo em pdf",
    "posso transformar este conteudo em pdf",
    "posso organizar esse resultado em um pdf",
    "posso organizar este resultado em um pdf",
    "posso compilar esse resultado em um pdf",
    "posso compilar este resultado em um pdf",
    "pdf profissional",
    "planilha editavel",
    "arquivo csv editavel",
)

_ACCEPTANCE_EXACT = {
    "sim",
    "pode",
    "quero",
    "ok",
    "claro",
    "perfeito",
    "isso",
    "pode sim",
    "sim por favor",
}

_ACCEPTANCE_PHRASES = (
    "sim pode",
    "pode gerar",
    "pode criar",
    "pode fazer",
    "pode montar",
    "quero o arquivo",
    "quero o documento",
    "quero a planilha",
    "quero o pdf",
    "manda pra mim",
    "mande pra mim",
    "envia pra mim",
    "envie pra mim",
)

# Reconhecimento combinatório: intenção/ação x conteúdo x formato x entrega.
# Não depende de uma frase exata. Novas combinações naturais são cobertas pelos
# grupos abaixo sem precisar cadastrar cada sentença completa.
_ACTION_TERMS = (
    "gerar", "gera", "gere", "gerando",
    "criar", "cria", "crie", "criando",
    "fazer", "faz", "faca", "fazendo",
    "montar", "monta", "monte",
    "transformar", "transforma", "transforme",
    "converter", "converte", "converta",
    "exportar", "exporta", "exporte",
    "preparar", "prepara", "prepare",
    "organizar", "organiza", "organize",
    "compilar", "compila", "compile",
    "formatar", "formata", "formate",
    "finalizar", "finaliza", "finalize",
    "fechar", "fecha", "feche",
    "entregar", "entrega", "entregue",
    "mandar", "manda", "mande",
    "enviar", "envia", "envie",
    "salvar", "salva", "salve",
    "baixar", "baixa", "baixe",
    "imprimir", "imprime", "imprima",
    "colocar", "coloca", "coloque",
    "passar", "passa", "passe",
)

_DESIRE_TERMS = (
    "quero",
    "preciso",
    "gostaria",
    "pode",
    "poderia",
    "consegue",
    "conseguiria",
    "tem como",
    "da para",
    "da pra",
    "seria possivel",
    "eu quero",
    "eu preciso",
)

_REFERENCE_TERMS = (
    "isso",
    "esse conteudo",
    "este conteudo",
    "esse resultado",
    "este resultado",
    "essa analise",
    "esta analise",
    "esse relatorio",
    "este relatorio",
    "essa conversa",
    "esta conversa",
    "tudo",
    "tudo isso",
    "o que conversamos",
    "o que foi feito",
    "o resultado final",
    "a resposta",
    "as informacoes",
    "os dados",
    "o material",
)

_DELIVERY_TERMS = (
    "para baixar",
    "pra baixar",
    "para download",
    "pra download",
    "para imprimir",
    "pra imprimir",
    "em arquivo",
    "como arquivo",
    "em documento",
    "como documento",
    "em formato",
    "versao final",
    "arquivo final",
    "me manda",
    "me mande",
    "me envia",
    "me envie",
)

_PDF_FORMAT_TERMS = (
    "pdf",
    "formato pdf",
    "arquivo pdf",
    "documento pdf",
    "arquivo para impressao",
    "documento para impressao",
    "versao para impressao",
    "versao para imprimir",
    "pronto para imprimir",
)

_XLSX_FORMAT_TERMS = (
    "xlsx",
    "excel",
    "planilha",
    "folha de calculo",
    "tabela editavel",
    "quadro editavel",
    "linhas e colunas",
    "formato tabular",
    "arquivo de excel",
)

_CSV_FORMAT_TERMS = (
    "csv",
    "arquivo csv",
    "formato csv",
    "valores separados por virgula",
    "arquivo para importacao",
    "formato de importacao",
)

_GENERIC_DOCUMENT_TERMS = (
    "documento",
    "relatorio",
    "arquivo",
    "material",
    "versao para impressao",
    "versao final",
)

_NEGATION_PATTERNS = (
    r"\bnao\s+(?:quero|preciso|gere|gera|gerar|crie|cria|criar|faca|fazer|mande|mandar|envie|enviar)\b",
    r"\bsem\s+(?:pdf|planilha|excel|xlsx|csv|arquivo|documento)\b",
    r"\bnao\s+(?:em|no|na)\s+(?:pdf|planilha|excel|xlsx|csv)\b",
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
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _history_text(history: list[dict], limit: int = 12) -> str:
    return " ".join(_normalize(item.get("content") or "") for item in history[-limit:])


def _contains_any(value: str, markers: tuple[str, ...]) -> bool:
    return any(marker in value for marker in markers)


def _has_negation(normalized: str) -> bool:
    return any(re.search(pattern, normalized) for pattern in _NEGATION_PATTERNS)


def _has_request_intent(normalized: str) -> bool:
    return (
        _contains_any(normalized, _ACTION_TERMS)
        or _contains_any(normalized, _DESIRE_TERMS)
        or _contains_any(normalized, _DELIVERY_TERMS)
    )


def _has_reference(normalized: str) -> bool:
    return _contains_any(normalized, _REFERENCE_TERMS)


def detect_artifact_request(message: str, history: list[dict] | None = None) -> str | None:
    """Detecta intenção natural de gerar PDF, XLSX ou CSV.

    A decisão cruza grupos de ação, desejo, referência, entrega e formato.
    Não exige sentença cadastrada nem palavra-chave isolada. O histórico é usado
    apenas para aceitar respostas curtas a uma oferta real já feita.
    """
    normalized = _normalize(message)
    if not normalized or _has_negation(normalized):
        return None

    has_request = _has_request_intent(normalized)
    has_reference = _has_reference(normalized)
    short_request = len(normalized.split()) <= 6

    if _contains_any(normalized, _CSV_FORMAT_TERMS):
        if has_request or has_reference or short_request:
            return "csv"

    if _contains_any(normalized, _XLSX_FORMAT_TERMS):
        if has_request or has_reference or short_request:
            return "xlsx"

    if _contains_any(normalized, _PDF_FORMAT_TERMS):
        if has_request or has_reference or short_request:
            return "pdf"

    # Pedidos de documento/relatório para entrega ou impressão são PDF por padrão.
    if _contains_any(normalized, _GENERIC_DOCUMENT_TERMS) and (
        has_request or _contains_any(normalized, _DELIVERY_TERMS)
    ):
        return "pdf"

    # Expressões como "organiza isso para eu baixar" ou "fecha tudo para imprimir".
    if has_reference and _contains_any(normalized, _DELIVERY_TERMS):
        if "import" in normalized or "sistema" in normalized:
            return "csv"
        return "pdf"

    recent_text = _history_text(history or [])
    offer_already_made = _contains_any(recent_text, _OFFER_MARKERS)
    accepted = normalized in _ACCEPTANCE_EXACT or any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in _ACCEPTANCE_PHRASES
    )
    if offer_already_made and accepted:
        if "csv" in recent_text:
            return "csv"
        if "planilha" in recent_text or "xlsx" in recent_text or "excel" in recent_text:
            return "xlsx"
        return "pdf"

    return None


def _accepted_offer(value: str) -> bool:
    normalized = _normalize(value)
    if normalized in _ACCEPTANCE_EXACT:
        return True
    return any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in _ACCEPTANCE_PHRASES
    )


def _artifact_type_from_offer(text: str) -> str:
    normalized = _normalize(text)
    if "csv" in normalized:
        return "csv"
    if "planilha" in normalized or "xlsx" in normalized or "excel" in normalized:
        return "xlsx"
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
        if "openai respondeu http" in normalized or "nao foi possivel" in normalized:
            continue
        return _remove_offer_from_answer(content)
    return ""


def _direct_document_decision(
    message: str,
    operation: str | None,
    history: list[dict],
) -> dict | None:
    artifact_type = detect_artifact_request(message, history)
    if artifact_type != "pdf":
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
    direct = _direct_document_decision(message, None, history)
    if direct:
        return direct

    detected_type = detect_artifact_request(message, history)
    if detected_type in {"xlsx", "csv"}:
        return None
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
    del operation, answer
    normalized = _normalize(message)
    recent_text = _history_text(history)
    artifact_already_created = _contains_any(recent_text, _CREATED_MARKERS)
    if artifact_already_created and _contains_any(normalized, _REUSE_MARKERS):
        return False
    return detect_artifact_request(message, history) is not None


def decide_artifact(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    answer: str,
) -> dict:
    direct = _direct_document_decision(message, operation, history)
    if direct:
        return direct

    accepted = resolve_pending_artifact_acceptance(message, history)
    if accepted:
        if operation and str(accepted.get("title") or "").casefold() == "documento domnai":
            accepted["title"] = str(operation).strip()[:180]
        return accepted

    artifact_type = detect_artifact_request(message, history)
    if not artifact_type or not _requires_artifact_decision(message, operation, history, answer):
        return dict(_NONE)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return dict(_NONE)

    request_payload = {
        "operation": operation,
        "current_message": message,
        "detected_artifact_type": artifact_type,
        "recent_history": history[-20:],
        "completed_answer": answer,
    }
    instructions = """
Você estrutura um arquivo que o usuário pediu em linguagem natural.
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
- Respeite detected_artifact_type; não troque o formato pedido.
- Use create quando houver dados suficientes no histórico ou na resposta consolidada.
- Para XLSX/CSV, produza headers e rows completos apenas com dados sustentados pela conversa.
- Não invente números, nomes ou fatos.
- Use offer apenas quando realmente faltarem dados indispensáveis para formar a tabela.
- O arquivo será entregue no chat e salvo na Biblioteca.
""".strip()

    try:
        raw_text, _usage = _openai_request(
            api_key,
            {
                "model": os.getenv(
                    "DOMNAI_ARTIFACT_MODEL",
                    os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini"),
                ).strip(),
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
        parsed = _parse_decision(raw_text)
        if parsed.get("action") != "none":
            parsed["artifact_type"] = artifact_type
        return parsed
    except Exception:
        return dict(_NONE)
