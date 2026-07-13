from __future__ import annotations

import json
import os

from app.services.diagnosis_memory import diagnosis_context
from app.services.domnai_brain import _normalized_history
from app.services.intelligence_orchestrator import (
    build_plan_input,
    build_refinement_input,
    parse_plan,
    planning_instructions,
    refinement_instructions,
)
from app.services.labor_termination import (
    OPERATION,
    calculate,
    extraction_instructions,
    missing_data_prompt_instructions,
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


def _orchestration_plan(
    api_key: str,
    model: str,
    message: str,
    history: list[dict],
    attachments: list[dict],
    diagnosis_state: dict | None,
) -> tuple[dict, dict]:
    raw_plan, usage = _openai_request(
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
                        operation=OPERATION,
                        memory_context=diagnosis_context(diagnosis_state),
                        attachment_names=[str(item.get("name") or "arquivo") for item in attachments],
                    ),
                }],
            }],
            "temperature": 0.0,
            "max_output_tokens": 700,
        },
    )
    return parse_plan(raw_plan), usage


def _refine(
    api_key: str,
    model: str,
    message: str,
    candidate: str,
    plan: dict,
    immutable_evidence: str = "",
) -> tuple[str, dict]:
    return _openai_request(
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
                        candidate_answer=candidate,
                        plan=plan,
                        immutable_evidence=immutable_evidence,
                    ),
                }],
            }],
            "temperature": 0.0,
            "max_output_tokens": 2400,
        },
    )


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

    plan, plan_usage = _orchestration_plan(
        api_key,
        model,
        message,
        history,
        attachments,
        diagnosis_state,
    )

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
        context_payload = {
            "orchestrator_plan": plan,
            "missing_fields": calculation.missing_fields,
            "known_data": extracted,
            "current_message": message,
        }
        candidate_questions, question_usage = _openai_request(
            api_key,
            {
                "model": os.getenv("DOMNAI_LABOR_QUESTION_MODEL", model).strip() or model,
                "instructions": missing_data_prompt_instructions(),
                "input": [{
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": json.dumps(context_payload, ensure_ascii=False),
                    }],
                }],
                "temperature": 0.1,
                "max_output_tokens": 500,
            },
        )
        questions, refinement_usage = _refine(
            api_key,
            model,
            message,
            candidate_questions,
            plan,
            immutable_evidence="Campos indispensáveis ainda ausentes: " + ", ".join(calculation.missing_fields),
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
        input_tokens, output_tokens, cached_tokens = _usage_totals(
            plan_usage,
            extraction_usage,
            question_usage,
            refinement_usage,
            memory_usage,
        )
        return MeteredBrainResult(
            text=questions,
            provider="openai-orchestrated-labor-adaptive-preflight-deterministic",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
            diagnosis_state=updated_state,
        )

    report_json = json.dumps(calculation.report, ensure_ascii=False, indent=2)
    candidate_text, render_usage = _openai_request(
        api_key,
        {
            "model": os.getenv("DOMNAI_LABOR_RENDER_MODEL", model).strip() or model,
            "instructions": render_instructions(),
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": f"PLANO DO ORQUESTRADOR:\n{json.dumps(plan, ensure_ascii=False)}\n\nPEDIDO ATUAL:\n{message}\n\nRELATÓRIO DETERMINÍSTICO OBRIGATÓRIO:\n{report_json}",
                }],
            }],
            "temperature": 0.0,
            "max_output_tokens": 2400,
        },
    )

    final_text, refinement_usage = _refine(
        api_key,
        model,
        message,
        candidate_text,
        plan,
        immutable_evidence=report_json,
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
        plan_usage,
        extraction_usage,
        render_usage,
        refinement_usage,
        memory_usage,
    )
    return MeteredBrainResult(
        text=final_text,
        provider="openai-orchestrated-labor-deterministic-refined-memory",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_tokens,
        diagnosis_state=updated_state,
    )
