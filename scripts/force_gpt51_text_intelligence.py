from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: esperado 1 trecho, encontrado {count}")
    return text.replace(old, new, 1)


# Todas as chamadas textuais do DomnAI passam por _openai_request. A troca aqui
# evita configurações divergentes entre chat, memória, revisão, extração,
# pré-validação, planejamento e decisão de artefatos.
metered_path = Path('/app/app/services/metered_brain.py')
metered = metered_path.read_text(encoding='utf-8')

metered = replace_once(
    metered,
    '''from app.services.reliability import (
    build_review_input,
''',
    '''from app.services.reliability import (
    build_review_input,
''',
    'âncora de importações',
)

constant_anchor = '''

@dataclass(frozen=True)
class MeteredBrainResult:
'''
constant_block = '''

DOMNAI_TEXT_MODEL = "gpt-5.1"
DOMNAI_REASONING_EFFORT = "medium"
DOMNAI_MIN_OUTPUT_TOKENS = 5000


@dataclass(frozen=True)
class MeteredBrainResult:
'''
metered = replace_once(
    metered,
    constant_anchor,
    constant_block,
    'constantes centrais GPT-5.1',
)

metered = replace_once(
    metered,
    '''    model = os.getenv("DOMNAI_GATEWAY_MODEL", "gpt-4o-mini").strip()
''',
    '''    model = DOMNAI_TEXT_MODEL
''',
    'modelo do gateway',
)

metered = replace_once(
    metered,
    '''        {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 2200},
''',
    '''        {
            "model": model,
            "messages": messages,
            "reasoning_effort": DOMNAI_REASONING_EFFORT,
            "max_tokens": 5000,
        },
''',
    'payload do gateway GPT-5.1',
)

metered = replace_once(
    metered,
    '''def _openai_request(api_key: str, payload: dict) -> tuple[str, dict]:
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload,
    )
    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("O provedor não retornou uma resposta em texto.")
    return text, data.get("usage") or {}
''',
    '''def _openai_request(api_key: str, payload: dict) -> tuple[str, dict]:
    request_payload = dict(payload or {})
    request_payload["model"] = DOMNAI_TEXT_MODEL
    request_payload["reasoning"] = {"effort": DOMNAI_REASONING_EFFORT}
    request_payload["max_output_tokens"] = max(
        DOMNAI_MIN_OUTPUT_TOKENS,
        _as_int(request_payload.get("max_output_tokens")),
    )
    # Parâmetros de amostragem não devem controlar uma chamada com raciocínio.
    request_payload.pop("temperature", None)
    request_payload.pop("top_p", None)
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        request_payload,
    )
    text = _extract_response_text(data)
    if text:
        return text, data.get("usage") or {}

    incomplete = data.get("incomplete_details") or {}
    if data.get("status") == "incomplete" and incomplete.get("reason") in {"max_output_tokens", "max_tokens"}:
        retry_payload = dict(request_payload)
        retry_payload["reasoning"] = {"effort": DOMNAI_REASONING_EFFORT}
        retry_payload["max_output_tokens"] = max(7000, request_payload["max_output_tokens"])
        retry_data = _post_json(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            retry_payload,
        )
        retry_text = _extract_response_text(retry_data)
        if retry_text:
            first_usage = data.get("usage") or {}
            retry_usage = retry_data.get("usage") or {}
            combined_usage = {
                "input_tokens": _as_int(first_usage.get("input_tokens")) + _as_int(retry_usage.get("input_tokens")),
                "output_tokens": _as_int(first_usage.get("output_tokens")) + _as_int(retry_usage.get("output_tokens")),
                "input_tokens_details": {
                    "cached_tokens": _as_int((first_usage.get("input_tokens_details") or {}).get("cached_tokens"))
                    + _as_int((retry_usage.get("input_tokens_details") or {}).get("cached_tokens")),
                },
            }
            return retry_text, combined_usage

    raise RuntimeError("O provedor não retornou uma resposta em texto.")
''',
    'forçamento central robusto do GPT-5.1',
)

metered = replace_once(
    metered,
    '''    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
''',
    '''    model = DOMNAI_TEXT_MODEL
''',
    'modelo principal reportado',
)

metered_path.write_text(metered, encoding='utf-8')


# O pipeline trabalhista mantém seu próprio campo de modelo no resultado. Ele é
# alinhado ao mesmo valor para que telemetria e cobrança não indiquem um modelo
# diferente daquele realmente utilizado.
labor_path = Path('/app/app/services/labor_pipeline.py')
labor = labor_path.read_text(encoding='utf-8')
labor = replace_once(
    labor,
    '''    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
''',
    '''    model = "gpt-5.1"
''',
    'modelo do pipeline trabalhista',
)
labor_path.write_text(labor, encoding='utf-8')

print('GPT-5.1 mantido com raciocínio médio, orçamento ampliado e repetição técnica no mesmo nível.')