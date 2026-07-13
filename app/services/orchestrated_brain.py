from __future__ import annotations

import os
import unicodedata

from app.services.diagnosis_memory import diagnosis_context
from app.services.domnai_brain import _normalized_history
from app.services.intelligence_orchestrator import (
    build_plan_input,
    build_refinement_input,
    parse_plan,
    planning_instructions,
    refinement_instructions,
)
from app.services.labor_termination import OPERATION as LABOR_TERMINATION_OPERATION
from app.services.metered_brain import (
    MeteredBrainResult,
    _openai_request,
    _update_diagnosis_memory,
    generate_metered_response,
)


def _usage_value(usage: dict, key: str) -> int:
    try:
        return max(0, int((usage or {}).get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _cached_value(usage: dict) -> int:
    details = (usage or {}).get("input_tokens_details") or {}
    return _usage_value(details, "cached_tokens")


def _normalized_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold().strip()


def _specialized_engine(plan: dict, operation: str | None, message: str) -> str | None:
    operation_text = _normalized_text(operation)
    engine_text = _normalized_text(plan.get("specialized_engine"))
    message_text = _normalized_text(message)

    labor_operation = _normalized_text(LABOR_TERMINATION_OPERATION)
    if operation_text == labor_operation:
        return "labor_termination"

    if any(marker in engine_text for marker in ("labor_termination", "rescisao", "trabalhista", "labor")):
        return "labor_termination"

    # Proteção para pedidos naturais quando o frontend não envia a operação.
    labor_markers = (
        "calcular minha rescisao",
        "calculo de rescisao",
        "verbas rescisorias",
        "demissao sem justa causa",
        "pedido de demissao",
        "aviso previo proporcional",
    )
    if any(marker in message_text for marker in labor_markers):
        return "labor_termination"

    return None


def generate_orchestrated_response(
    message: str,
    history: list[dict],
    operation: str | None,
    attachments: list[dict] | None = None,
    diagnosis_state: dict | None = None,
) -> MeteredBrainResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return generate_metered_response(
            message=message,
            history=history,
            operation=operation,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )

    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
    safe_attachments = attachments or []

    raw_plan, plan_usage = _openai_request(
        api_key,
        {
            "model": os.getenv("DOMNAI_ORCHESTRATOR_MODEL", model).strip() or model,
            "instructions": planning_instructions(),
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": build_plan_input(
                        message=message,
                        history=_normalized_history(history),
                        operation=operation,
                        memory_context=diagnosis_context(diagnosis_state),
                        attachment_names=[str(item.get("name") or "arquivo") for item in safe_attachments],
                    ),
                }],
            }],
            "temperature": 0.0,
            "max_output_tokens": 700,
        },
    )
    plan = parse_plan(raw_plan)

    engine = _specialized_engine(plan, operation, message)
    if engine == "labor_termination":
        from app.services.labor_pipeline import generate_labor_response

        return generate_labor_response(
            message=message,
            history=history,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
            orchestration_plan=plan,
            orchestration_usage=plan_usage,
        )

    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=operation,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )

    final_text, refinement_usage = _openai_request(
        api_key,
        {
            "model": os.getenv("DOMNAI_REFINER_MODEL", model).strip() or model,
            "instructions": refinement_instructions(),
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": build_refinement_input(
                        user_message=message,
                        candidate_answer=base_result.text,
                        plan=plan,
                        immutable_evidence=(
                            "Preserve sem alteração todos os números, datas, percentuais, referências documentais "
                            "e resultados explícitos da resposta candidata. Não recalcule nem introduza valores novos."
                        ),
                    ),
                }],
            }],
            "temperature": 0.0,
            "max_output_tokens": 2400,
        },
    )

    updated_state, memory_usage = _update_diagnosis_memory(
        api_key,
        model,
        operation,
        base_result.diagnosis_state or diagnosis_state,
        message,
        final_text,
        safe_attachments,
    )

    extra_input = _usage_value(plan_usage, "input_tokens") + _usage_value(refinement_usage, "input_tokens") + _usage_value(memory_usage, "input_tokens")
    extra_output = _usage_value(plan_usage, "output_tokens") + _usage_value(refinement_usage, "output_tokens") + _usage_value(memory_usage, "output_tokens")
    extra_cached = _cached_value(plan_usage) + _cached_value(refinement_usage) + _cached_value(memory_usage)

    return MeteredBrainResult(
        text=final_text,
        provider=f"orchestrated-refined:{base_result.provider}",
        model=base_result.model,
        input_tokens=base_result.input_tokens + extra_input,
        output_tokens=base_result.output_tokens + extra_output,
        cached_input_tokens=base_result.cached_input_tokens + extra_cached,
        diagnosis_state=updated_state,
    )