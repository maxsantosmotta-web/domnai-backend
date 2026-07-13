from __future__ import annotations

import json
import os

from app.services.diagnosis_memory import diagnosis_context
from app.services.domnai_brain import _normalized_history
from app.services.labor_termination import (
    OPERATION,
    calculate,
    extraction_instructions,
    parse_extracted_data,
    render_instructions,
)
from app.services.metered_brain import (
    MeteredBrainResult,
    _openai_request,
    _update_diagnosis_memory,
    _usage_totals,
)


def _conversation_input(message: str, history: list[dict], diagnosis_state: dict | None) -> list[dict]:
    items = _normalized_history(history)
    memory = diagnosis_context(diagnosis_state)
    if memory:
        items.insert(0, {"role": "developer", "content": memory})
    items.append({"role": "user", "content": message})
    return items


def generate_labor_response(
    message: str,
    history: list[dict],
    attachments: list[dict],
    diagnosis_state: dict | None,
) -> MeteredBrainResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada.")

    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
    extractor_model = os.getenv("DOMNAI_LABOR_EXTRACTOR_MODEL", model).strip() or model

    extraction_text, extraction_usage = _openai_request(
        api_key,
        {
            "model": extractor_model,
            "instructions": extraction_instructions(),
            "input": _conversation_input(message, history, diagnosis_state),
            "temperature": 0.0,
            "max_output_tokens": 900,
        },
    )
    extracted = parse_extracted_data(extraction_text)
    calculation = calculate(extracted)

    if not calculation.ready:
        questions = "Para calcular sem presumir dados, preciso confirmar:\n\n" + "\n".join(
            f"{index}. {question}" for index, question in enumerate(calculation.questions, start=1)
        )
        updated_state, memory_usage = _update_diagnosis_memory(
            api_key,
            model,
            OPERATION,
            diagnosis_state,
            message,
            questions,
            attachments,
        )
        input_tokens, output_tokens, cached_tokens = _usage_totals(extraction_usage, memory_usage)
        return MeteredBrainResult(
            text=questions,
            provider="openai-labor-preflight-deterministic",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
            diagnosis_state=updated_state,
        )

    report_json = json.dumps(calculation.report, ensure_ascii=False, indent=2)
    final_text, render_usage = _openai_request(
        api_key,
        {
            "model": os.getenv("DOMNAI_LABOR_RENDER_MODEL", model).strip() or model,
            "instructions": render_instructions(),
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": f"PEDIDO ATUAL:\n{message}\n\nRELATÓRIO DETERMINÍSTICO OBRIGATÓRIO:\n{report_json}",
                }],
            }],
            "temperature": 0.0,
            "max_output_tokens": 2400,
        },
    )

    updated_state, memory_usage = _update_diagnosis_memory(
        api_key,
        model,
        OPERATION,
        diagnosis_state,
        message,
        final_text,
        attachments,
    )
    input_tokens, output_tokens, cached_tokens = _usage_totals(
        extraction_usage,
        render_usage,
        memory_usage,
    )
    return MeteredBrainResult(
        text=final_text,
        provider="openai-labor-deterministic-memory",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_tokens,
        diagnosis_state=updated_state,
    )
