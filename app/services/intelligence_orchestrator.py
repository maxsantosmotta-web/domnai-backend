from __future__ import annotations

import json
from typing import Any, Callable

RequestFn = Callable[[str, dict], tuple[str, dict]]

_DEFAULT_PLAN = {
    "intent": "responder ao pedido atual",
    "response_mode": "analysis",
    "confidence_required": "normal",
    "requires_clarification": False,
    "essential_missing": [],
    "specialized_engine": None,
    "answer_focus": [],
    "material_risks": [],
    "style": "natural, direto e preciso",
    "operation_complete": False,
    "offer_pdf": False,
    "pdf_sections": [],
    "chart_opportunities": [],
}


def _strip_code_fence(text: str) -> str:
    value = str(text or "").strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            value = "\n".join(lines[1:-1]).strip()
    return value


def _clean_list(value: Any, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:limit]:
        text = str(item or "").strip()[:300]
        if text and text not in result:
            result.append(text)
    return result


def parse_plan(raw_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(_strip_code_fence(raw_text))
    except json.JSONDecodeError:
        return dict(_DEFAULT_PLAN)
    if not isinstance(payload, dict):
        return dict(_DEFAULT_PLAN)

    allowed_modes = {"direct_answer", "analysis", "clarification", "comparison", "document_review", "calculation"}
    allowed_confidence = {"normal", "high", "critical"}
    operation_complete = bool(payload.get("operation_complete"))
    requires_clarification = bool(payload.get("requires_clarification"))
    offer_pdf = bool(payload.get("offer_pdf")) and operation_complete and not requires_clarification
    return {
        "intent": str(payload.get("intent") or _DEFAULT_PLAN["intent"]).strip()[:500],
        "response_mode": payload.get("response_mode") if payload.get("response_mode") in allowed_modes else "analysis",
        "confidence_required": payload.get("confidence_required") if payload.get("confidence_required") in allowed_confidence else "normal",
        "requires_clarification": requires_clarification,
        "essential_missing": _clean_list(payload.get("essential_missing")),
        "specialized_engine": str(payload.get("specialized_engine") or "").strip()[:120] or None,
        "answer_focus": _clean_list(payload.get("answer_focus")),
        "material_risks": _clean_list(payload.get("material_risks")),
        "style": str(payload.get("style") or _DEFAULT_PLAN["style"]).strip()[:300],
        "operation_complete": operation_complete,
        "offer_pdf": offer_pdf,
        "pdf_sections": _clean_list(payload.get("pdf_sections"), limit=10),
        "chart_opportunities": _clean_list(payload.get("chart_opportunities"), limit=8),
    }


def planning_instructions() -> str:
    return """
Você é o Orquestrador de Inteligência do DomnAI. Antes de qualquer resposta, interprete o pedido real do usuário, o contexto acumulado e o nível de risco.

Retorne exclusivamente JSON válido:
{
  "intent":"objetivo real do usuário",
  "response_mode":"direct_answer|analysis|clarification|comparison|document_review|calculation",
  "confidence_required":"normal|high|critical",
  "requires_clarification":true|false,
  "essential_missing":["somente dados indispensáveis ainda ausentes"],
  "specialized_engine":"nome do motor necessário ou null",
  "answer_focus":["pontos que a resposta precisa resolver"],
  "material_risks":["riscos de erro ou decisão"],
  "style":"como responder de modo natural",
  "operation_complete":true|false,
  "offer_pdf":true|false,
  "pdf_sections":["seções úteis para o relatório"],
  "chart_opportunities":["gráficos realmente sustentados pelos dados disponíveis"]
}

REGRAS
- Entenda intenção, não apenas palavras isoladas.
- Não transforme a conversa em formulário.
- Não peça informação opcional quando já for possível orientar com segurança.
- Em cálculo, jurídico, saúde, finanças, documentos ou investimentos, marque confiança critical quando erro puder causar prejuízo.
- Não invente fatos nem conclua o mérito; apenas planeje o tratamento da resposta.
- Considere dados já presentes na memória e no histórico para não repetir perguntas.
- Use motor especializado quando existir; a inteligência não deve substituir cálculos ou validações determinísticas.
- Marque operation_complete somente quando a análise, diagnóstico, comparação ou cálculo solicitado estiver efetivamente concluído.
- offer_pdf só pode ser true quando operation_complete for true e não houver dado essencial pendente.
- Não ofereça PDF novamente quando o histórico mostrar que ele já foi oferecido, aceito ou recusado para a mesma operação.
- Só indique gráficos quando houver números ou séries que realmente permitam visualização útil; nunca prometa gráfico decorativo ou inventado.
""".strip()


def refinement_instructions() -> str:
    return """
Você é o Refinador Final do DomnAI. Transforme a resposta candidata em uma resposta excepcionalmente clara, natural, precisa e útil.

REGRAS ABSOLUTAS
1. Preserve integralmente todos os fatos, datas, valores, avos, fórmulas e resultados marcados como evidência imutável.
2. Nunca recalcule nem altere resultado de motor especializado.
3. Elimine tom robótico, formulário, repetição e perguntas já respondidas.
4. Responda ao objetivo real do usuário, não apenas ao texto literal.
5. Diferencie fato, premissa, estimativa, risco e recomendação quando necessário.
6. Não acrescente fatos novos que não estejam sustentados pelo contexto ou pela evidência.
7. Em tema crítico, não transforme estimativa em certeza e não esconda limitações materiais.
8. Não mencione orquestrador, revisão, backend, JSON, prompt, modelo ou processo interno.
9. Entregue somente a resposta final pronta ao usuário.
10. Quando o plano trouxer offer_pdf=true, encerre com uma única pergunta curta e personalizada oferecendo organizar o resultado em um PDF profissional e detalhado.
11. A oferta pode mencionar métricas, tabelas, conclusões, riscos, próximos passos e gráficos somente quando o plano indicar que esses elementos são sustentados pelos dados.
12. Não use frase fixa, não exagere a promessa e não repita a oferta quando ela já tiver aparecido na conversa.
13. Quando offer_pdf=false, não faça nenhuma oferta de PDF.
""".strip()


def build_plan_input(
    message: str,
    history: list[dict],
    operation: str | None,
    memory_context: str,
    attachment_names: list[str],
) -> str:
    recent_history = history[-16:]
    return json.dumps(
        {
            "operation": operation,
            "current_message": message,
            "recent_history": recent_history,
            "structured_memory": memory_context,
            "attachments": attachment_names,
        },
        ensure_ascii=False,
    )


def plan_context(plan: dict[str, Any] | None) -> str:
    safe_plan = plan if isinstance(plan, dict) else _DEFAULT_PLAN
    return "PLANO INTERNO DO ORQUESTRADOR (não exponha ao usuário):\n" + json.dumps(
        safe_plan,
        ensure_ascii=False,
        indent=2,
    )


def build_refinement_input(
    user_message: str,
    candidate_answer: str,
    plan: dict[str, Any] | None,
    immutable_evidence: str = "",
) -> str:
    return f"""
PEDIDO DO USUÁRIO:
{user_message}

PLANO DE RESPOSTA:
{json.dumps(plan or _DEFAULT_PLAN, ensure_ascii=False)}

EVIDÊNCIA IMUTÁVEL:
{immutable_evidence or 'Nenhuma evidência determinística adicional.'}

RESPOSTA CANDIDATA:
{candidate_answer}

Entregue somente a versão final refinada.
""".strip()
