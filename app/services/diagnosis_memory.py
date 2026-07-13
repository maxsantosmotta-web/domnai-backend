from __future__ import annotations

import json
from typing import Any

from app.database import session_scope
from app.models import DiagnosisState

MAX_LIST_ITEMS = 30
MAX_ITEM_LENGTH = 500


def empty_diagnosis_state(operation: str | None = None) -> dict[str, Any]:
    return {
        "operation": operation,
        "confirmed_facts": [],
        "missing_data": [],
        "assumptions": [],
        "documents": [],
        "validated_calculations": [],
        "risks": [],
        "provisional_conclusion": "",
        "next_steps": [],
    }


def _clean_text(value: Any, limit: int = MAX_ITEM_LENGTH) -> str:
    return str(value or "").strip()[:limit]


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= MAX_LIST_ITEMS:
            break
    return result


def sanitize_diagnosis_state(value: Any, operation: str | None = None) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    return {
        "operation": _clean_text(source.get("operation") or operation, 180) or None,
        "confirmed_facts": _clean_list(source.get("confirmed_facts")),
        "missing_data": _clean_list(source.get("missing_data")),
        "assumptions": _clean_list(source.get("assumptions")),
        "documents": _clean_list(source.get("documents")),
        "validated_calculations": _clean_list(source.get("validated_calculations")),
        "risks": _clean_list(source.get("risks")),
        "provisional_conclusion": _clean_text(source.get("provisional_conclusion"), 1600),
        "next_steps": _clean_list(source.get("next_steps")),
    }


def load_diagnosis_state(user_id: str, operation: str | None) -> dict[str, Any]:
    with session_scope() as db:
        record = db.get(DiagnosisState, user_id)
        if record is None:
            return empty_diagnosis_state(operation)
        try:
            payload = json.loads(record.state_json or "{}")
        except json.JSONDecodeError:
            payload = {}

    state = sanitize_diagnosis_state(payload, operation)
    stored_operation = state.get("operation")
    if operation and stored_operation and stored_operation != operation:
        return empty_diagnosis_state(operation)
    if operation:
        state["operation"] = operation
    return state


def save_diagnosis_state(user_id: str, operation: str | None, state: dict[str, Any]) -> None:
    safe_state = sanitize_diagnosis_state(state, operation)
    with session_scope() as db:
        record = db.get(DiagnosisState, user_id)
        if record is None:
            record = DiagnosisState(user_id=user_id)
            db.add(record)
        record.operation = operation
        record.state_json = json.dumps(safe_state, ensure_ascii=False)
        db.flush()


def clear_diagnosis_state(user_id: str) -> None:
    with session_scope() as db:
        record = db.get(DiagnosisState, user_id)
        if record is not None:
            db.delete(record)


def diagnosis_context(state: dict[str, Any] | None) -> str:
    safe = sanitize_diagnosis_state(state or {})
    if not any(
        safe.get(key)
        for key in (
            "confirmed_facts",
            "missing_data",
            "assumptions",
            "documents",
            "validated_calculations",
            "risks",
            "provisional_conclusion",
            "next_steps",
        )
    ):
        return ""
    return "MEMÓRIA ESTRUTURADA DO DIAGNÓSTICO (use como contexto, sem expor este bloco ao usuário):\n" + json.dumps(
        safe,
        ensure_ascii=False,
        indent=2,
    )


def diagnosis_extractor_instructions(operation: str | None) -> str:
    operation_label = operation or "operação não selecionada"
    return f"""
Você atualiza a memória estruturada de um diagnóstico do DomnAI.
Operação ativa: {operation_label}.

Retorne exclusivamente JSON válido com estas chaves:
{{
  "operation": "nome da operação ou null",
  "confirmed_facts": ["fatos confirmados pelo usuário ou documento"],
  "missing_data": ["dados essenciais ainda faltantes"],
  "assumptions": ["premissas e estimativas claramente identificadas"],
  "documents": ["documentos ou arquivos efetivamente considerados"],
  "validated_calculations": ["cálculos conferidos e seus resultados"],
  "risks": ["riscos materiais identificados"],
  "provisional_conclusion": "conclusão atual, vazia se ainda não houver",
  "next_steps": ["próximas ações objetivas"]
}}

REGRAS
- Atualize o estado anterior; não apague informação válida sem motivo explícito.
- Não transforme hipótese em fato confirmado.
- Remova de missing_data aquilo que já foi respondido.
- Registre somente informações relevantes para a decisão atual.
- Não invente documentos, cálculos, leis, riscos ou conclusões.
- Não inclua dados sensíveis desnecessários.
- Não use markdown, comentários ou texto fora do JSON.
""".strip()


def build_diagnosis_update_input(
    prior_state: dict[str, Any] | None,
    user_message: str,
    final_answer: str,
    attachment_names: list[str] | None = None,
) -> str:
    return f"""
ESTADO ANTERIOR:
{json.dumps(sanitize_diagnosis_state(prior_state or {}), ensure_ascii=False)}

NOVA MENSAGEM DO USUÁRIO:
{user_message}

RESPOSTA FINAL DO DOMNAI:
{final_answer}

ARQUIVOS ANEXADOS NESTA ETAPA:
{json.dumps(attachment_names or [], ensure_ascii=False)}

Atualize e retorne somente o JSON completo do estado.
""".strip()


def parse_diagnosis_state(raw_text: str, operation: str | None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return sanitize_diagnosis_state(fallback or {}, operation)
    return sanitize_diagnosis_state(payload, operation)
