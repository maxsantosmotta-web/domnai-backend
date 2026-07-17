from __future__ import annotations

import os
import time
import unicodedata

from app.services.artifact_source import resolve_local_artifact_request
from app.services.diagnosis_memory import diagnosis_context
from app.services.domnai_brain import _normalized_history
from app.services.intelligence_orchestrator import (
    build_plan_input,
    parse_plan,
    planning_instructions,
)
from app.services.labor_termination import OPERATION as LABOR_TERMINATION_OPERATION
from app.services.metered_brain import (
    MeteredBrainResult,
    _openai_request,
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


def _simple_conversation_response(message: str, attachments: list[dict], history: list[dict]) -> str | None:
    if attachments:
        return None

    normalized = " ".join(_normalized_text(message).replace("?", "").replace("!", "").split())
    if not normalized or len(normalized) > 80:
        return None

    greeting_messages = {
        "oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai",
        "chat tudo bem", "chat, tudo bem", "tudo bem", "como voce esta", "como vai",
    }
    thanks_messages = {
        "obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu", "agradecido", "agradecida",
    }
    farewell_messages = {
        "tchau", "ate mais", "boa noite chat", "falamos depois", "ate logo",
    }

    # Confirmações como “certo”, “pode continuar” e “perfeito” dependem da
    # pergunta anterior e devem sempre ser interpretadas pelo modelo.
    if normalized in greeting_messages and not history:
        return "Tudo ótimo! E com você? Como posso ajudar hoje?"
    if normalized in thanks_messages:
        return "Por nada!"
    if normalized in farewell_messages:
        return "Até mais!"
    return None


def _specialized_engine(plan: dict, operation: str | None, message: str) -> str | None:
    operation_text = _normalized_text(operation)
    engine_text = _normalized_text(plan.get("specialized_engine"))
    message_text = _normalized_text(message)

    labor_operation = _normalized_text(LABOR_TERMINATION_OPERATION)
    if operation_text == labor_operation:
        return "labor_termination"

    if any(marker in engine_text for marker in ("labor_termination", "rescisao", "trabalhista", "labor")):
        return "labor_termination"

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
    safe_attachments = attachments or []

    local_artifact = resolve_local_artifact_request(message, history)
    if local_artifact:
        return MeteredBrainResult(
            text=local_artifact["source_answer"],
            provider="local-artifact",
            model="local",
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            diagnosis_state=diagnosis_state,
            timings={"orchestrator_ms": 0, "generation_ms": 0},
        )

    simple_reply = _simple_conversation_response(message, safe_attachments, history)
    if simple_reply is not None:
        return MeteredBrainResult(
            text=simple_reply,
            provider="domnai-local-conversation",
            model="local",
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            diagnosis_state=diagnosis_state,
        )

    if _specialized_engine({}, operation, message) is None:
        base_result = generate_metered_response(
            message=message,
            history=history,
            operation=operation,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
        )
        return MeteredBrainResult(
            text=base_result.text,
            provider=f"direct:{base_result.provider}",
            model=base_result.model,
            input_tokens=base_result.input_tokens,
            output_tokens=base_result.output_tokens,
            cached_input_tokens=base_result.cached_input_tokens,
            diagnosis_state=base_result.diagnosis_state,
            timings={"orchestrator_ms": 0, **(base_result.timings or {})},
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return generate_metered_response(
            message=message,
            history=history,
            operation=operation,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
        )

    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
    plan: dict = {}
    plan_usage: dict = {}

    orchestrator_started_at = time.perf_counter()
    try:
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
    except Exception:
        plan = {}
        plan_usage = {}

    orchestrator_ms = max(0, round((time.perf_counter() - orchestrator_started_at) * 1000))
    engine = _specialized_engine(plan, operation, message)
    if engine == "labor_termination":
        from app.services.labor_pipeline import generate_labor_response

        return generate_labor_response(
            message=message,
            history=history,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
            orchestration_plan=plan or None,
            orchestration_usage=plan_usage,
        )

    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=operation,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )

    return MeteredBrainResult(
        text=base_result.text,
        provider=f"orchestrated:{base_result.provider}",
        model=base_result.model,
        input_tokens=base_result.input_tokens + _usage_value(plan_usage, "input_tokens"),
        output_tokens=base_result.output_tokens + _usage_value(plan_usage, "output_tokens"),
        cached_input_tokens=base_result.cached_input_tokens + _cached_value(plan_usage),
        diagnosis_state=base_result.diagnosis_state,
        timings={"orchestrator_ms": orchestrator_ms, **(base_result.timings or {})},
    )
