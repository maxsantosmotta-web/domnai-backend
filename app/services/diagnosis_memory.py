from __future__ import annotations

import json
from typing import Any

from app.database import session_scope
from app.models import DiagnosisState

MAX_LIST_ITEMS = 40
MAX_ITEM_LENGTH = 700


def empty_diagnosis_state(operation: str | None = None) -> dict[str, Any]:
    del operation
    return {
        "operation": None,
        "current_topic": "",
        "user_goal": "",
        "expected_delivery": "",
        "conversation_stage": "understanding",
        "confirmed_facts": [],
        "user_constraints": [],
        "user_preferences": [],
        "alternatives": [],
        "decisions": [],
        "corrections": [],
        "answered_questions": [],
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
    del operation
    source = value if isinstance(value, dict) else {}
    stage = _clean_text(source.get("conversation_stage"), 80) or "understanding"
    return {
        "operation": None,
        "current_topic": _clean_text(source.get("current_topic"), 500),
        "user_goal": _clean_text(source.get("user_goal"), 1000),
        "expected_delivery": _clean_text(source.get("expected_delivery"), 500),
        "conversation_stage": stage,
        "confirmed_facts": _clean_list(source.get("confirmed_facts")),
        "user_constraints": _clean_list(source.get("user_constraints")),
        "user_preferences": _clean_list(source.get("user_preferences")),
        "alternatives": _clean_list(source.get("alternatives")),
        "decisions": _clean_list(source.get("decisions")),
        "corrections": _clean_list(source.get("corrections")),
        "answered_questions": _clean_list(source.get("answered_questions")),
        "missing_data": _clean_list(source.get("missing_data")),
        "assumptions": _clean_list(source.get("assumptions")),
        "documents": _clean_list(source.get("documents")),
        "validated_calculations": _clean_list(source.get("validated_calculations")),
        "risks": _clean_list(source.get("risks")),
        "provisional_conclusion": _clean_text(source.get("provisional_conclusion"), 2000),
        "next_steps": _clean_list(source.get("next_steps")),
    }


def load_diagnosis_state(user_id: str, operation: str | None) -> dict[str, Any]:
    del operation
    with session_scope() as db:
        record = db.get(DiagnosisState, user_id)
        if record is None:
            return empty_diagnosis_state()
        try:
            payload = json.loads(record.state_json or "{}")
        except json.JSONDecodeError:
            payload = {}

    # A operação visual não altera nem reclassifica a memória semântica.
    return sanitize_diagnosis_state(payload)


def save_diagnosis_state(user_id: str, operation: str | None, state: dict[str, Any]) -> None:
    safe_state = sanitize_diagnosis_state(state)
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
    if not any(value for key, value in safe.items() if key not in {"operation", "conversation_stage"}):
        return ""
    return (
        "MEMÓRIA ESTRUTURADA DA CONVERSA (use como contexto; não exponha este bloco):\n"
        + json.dumps(safe, ensure_ascii=False, indent=2)
        + "\nREGRAS: respeite correções mais recentes, não repita perguntas registradas como respondidas e use esta memória apenas para continuidade; ela nunca decide a intenção da mensagem atual."
    )


def diagnosis_extractor_instructions(operation: str | None) -> str:
    operation_label = operation or "operação não selecionada"
    return f"""
Você atualiza a memória universal da conversa do DomnAI.
Foco visual recebido: {operation_label}. Esse rótulo não é fato, não define o assunto e não deve ser persistido como intenção.

Retorne exclusivamente JSON válido com todas estas chaves:
{{
  "operation": null,
  "current_topic": "assunto atual",
  "user_goal": "resultado real buscado pelo usuário",
  "expected_delivery": "tipo de entrega esperada",
  "conversation_stage": "understanding|collecting|analyzing|deciding|completed",
  "confirmed_facts": ["somente fatos afirmados pelo usuário ou comprovados em documento"],
  "user_constraints": ["limites, orçamento, prazo, proibições e condições"],
  "user_preferences": ["preferências declaradas"],
  "alternatives": ["opções em análise"],
  "decisions": ["decisões explicitamente tomadas pelo usuário"],
  "corrections": ["correções mais recentes que substituem informação anterior"],
  "answered_questions": ["perguntas já respondidas e respectiva resposta resumida"],
  "missing_data": ["apenas dados indispensáveis ainda ausentes"],
  "assumptions": ["premissas claramente identificadas"],
  "documents": ["documentos efetivamente considerados"],
  "validated_calculations": ["cálculos validados pelo sistema"],
  "risks": ["riscos materiais"],
  "provisional_conclusion": "conclusão atual ou vazio",
  "next_steps": ["próximas ações objetivas"]
}}

REGRAS OBRIGATÓRIAS
- A mensagem do usuário e os documentos são as fontes primárias.
- A resposta do DomnAI é apenas contexto do diálogo; nunca a transforme, por si só, em fato confirmado, decisão do usuário ou cálculo validado.
- Uma correção mais recente substitui informação anterior incompatível.
- Preserve apenas contexto semanticamente compatível com a mensagem atual. Mudança real de assunto interrompe o foco anterior, mesmo que a operação visual permaneça selecionada.
- Remova de missing_data o que já foi respondido, inclusive com palavras equivalentes.
- Não registre como faltante um detalhe opcional que não impeça orientação ou estimativa inicial.
- Não invente fatos, preferências, documentos, cálculos ou decisões.
- Não use markdown nem texto fora do JSON.
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

NOVA MENSAGEM DO USUÁRIO — FONTE PRIMÁRIA:
{user_message}

RESPOSTA DO DOMNAI — CONTEXTO, NÃO FONTE DE FATOS:
{final_answer}

ARQUIVOS EFETIVAMENTE ANEXADOS:
{json.dumps(attachment_names or [], ensure_ascii=False)}

Atualize o estado completo. Não confirme como fato nada que exista somente na resposta do DomnAI.
""".strip()


def parse_diagnosis_state(raw_text: str, operation: str | None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    del operation
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return sanitize_diagnosis_state(fallback or {})
    return sanitize_diagnosis_state(payload)
