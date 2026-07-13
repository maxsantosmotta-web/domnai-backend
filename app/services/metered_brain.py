import base64
import os
from dataclasses import dataclass

from app.services.domnai_brain import (
    _integration_api_key,
    _integration_base_url,
    _normalized_history,
    _post_json,
    build_system_prompt,
)
from app.services.reliability import (
    build_review_input,
    needs_independent_review,
    reviewer_instructions,
)


@dataclass(frozen=True)
class MeteredBrainResult:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


def _as_int(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _extract_response_text(data: dict) -> str:
    text = str(data.get("output_text", "")).strip()
    if text:
        return text

    parts = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(str(content["text"]).strip())
    return "\n".join(part for part in parts if part).strip()


def _gateway_response(message: str, history: list[dict], operation: str | None, attachments: list[dict]) -> MeteredBrainResult:
    if attachments:
        raise RuntimeError("A leitura de arquivos exige o provedor OpenAI configurado no DomnAI.")

    api_key = _integration_api_key()
    base_url = _integration_base_url()
    if not api_key or not base_url:
        raise RuntimeError("Integração OpenAI do gateway não configurada.")

    model = os.getenv("DOMNAI_GATEWAY_MODEL", "gpt-4o-mini").strip()
    messages = [{"role": "system", "content": build_system_prompt(operation)}]
    messages.extend(_normalized_history(history))
    messages.append({"role": "user", "content": message})

    data = _post_json(
        f"{base_url}/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2200,
        },
    )

    choices = data.get("choices") or []
    text = ""
    if choices:
        text = str((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError("O gateway não retornou uma resposta em texto.")

    usage = data.get("usage") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    return MeteredBrainResult(
        text=text,
        provider="replit-openai-gateway",
        model=model,
        input_tokens=_as_int(usage.get("prompt_tokens")),
        output_tokens=_as_int(usage.get("completion_tokens")),
        cached_input_tokens=_as_int(prompt_details.get("cached_tokens")),
    )


def _attachment_content(attachment: dict) -> dict:
    mime_type = str(attachment.get("mime_type") or "application/octet-stream").lower()
    filename = str(attachment.get("name") or "arquivo")[:255]
    encoded = base64.b64encode(attachment.get("content") or b"").decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"

    if mime_type.startswith("image/"):
        return {
            "type": "input_image",
            "image_url": data_url,
            "detail": "auto",
        }

    return {
        "type": "input_file",
        "filename": filename,
        "file_data": data_url,
    }


def _openai_request(api_key: str, payload: dict) -> tuple[str, dict]:
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload,
    )
    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("O provedor não retornou uma resposta em texto.")
    return text, data.get("usage") or {}


def _openai_response(message: str, history: list[dict], operation: str | None, attachments: list[dict]) -> MeteredBrainResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada.")

    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
    input_messages = _normalized_history(history)

    user_content = [{"type": "input_text", "text": message}]
    user_content.extend(_attachment_content(attachment) for attachment in attachments)
    input_messages.append({"role": "user", "content": user_content})

    draft_text, draft_usage = _openai_request(
        api_key,
        {
            "model": model,
            "instructions": build_system_prompt(operation),
            "input": input_messages,
            "temperature": 0.1,
            "max_output_tokens": 2400,
        },
    )

    final_text = draft_text
    review_usage: dict = {}
    reviewed = needs_independent_review(operation, message, attachments)

    if reviewed:
        review_model = os.getenv("DOMNAI_REVIEW_MODEL", model).strip() or model
        final_text, review_usage = _openai_request(
            api_key,
            {
                "model": review_model,
                "instructions": reviewer_instructions(operation),
                "input": [{
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": build_review_input(message, draft_text),
                    }],
                }],
                "temperature": 0.0,
                "max_output_tokens": 2400,
            },
        )

    draft_input_details = draft_usage.get("input_tokens_details") or {}
    review_input_details = review_usage.get("input_tokens_details") or {}
    return MeteredBrainResult(
        text=final_text,
        provider="openai-reviewed" if reviewed else "openai",
        model=model,
        input_tokens=_as_int(draft_usage.get("input_tokens")) + _as_int(review_usage.get("input_tokens")),
        output_tokens=_as_int(draft_usage.get("output_tokens")) + _as_int(review_usage.get("output_tokens")),
        cached_input_tokens=_as_int(draft_input_details.get("cached_tokens")) + _as_int(review_input_details.get("cached_tokens")),
    )


def generate_metered_response(
    message: str,
    history: list[dict],
    operation: str | None,
    attachments: list[dict] | None = None,
) -> MeteredBrainResult:
    provider = os.getenv("DOMNAI_AI_PROVIDER", "auto").strip().lower()
    safe_attachments = attachments or []

    if provider == "gateway":
        return _gateway_response(message, history, operation, safe_attachments)
    if provider in {"openai", "", "auto"}:
        if os.getenv("OPENAI_API_KEY", "").strip():
            return _openai_response(message, history, operation, safe_attachments)
        raise RuntimeError("OPENAI_API_KEY do DomnAI não configurada.")
    if provider == "anthropic":
        raise RuntimeError("Medição automática de créditos para Anthropic ainda não foi habilitada.")
    raise RuntimeError("DOMNAI_AI_PROVIDER inválido. Use openai, gateway ou auto.")
