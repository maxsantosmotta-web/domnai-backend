from __future__ import annotations

from pathlib import Path


BRAIN_PATH = Path('/app/app/services/domnai_brain.py')
ORCHESTRATED_PATH = Path('/app/app/services/orchestrated_brain.py')


def _patch_rate_limit_client() -> None:
    source = BRAIN_PATH.read_text(encoding='utf-8')

    if 'import threading\n' not in source:
        source = source.replace('import os\n', 'import os\nimport threading\nimport time\n', 1)

    function_start = source.index('def _post_json(')
    function_end = source.index('\n\ndef _integration_api_key', function_start)
    lock_marker = '_OPENAI_REQUEST_LOCK = threading.Lock()\n\n\n'
    segment_start = source.rfind(lock_marker, 0, function_start)
    if segment_start < 0:
        segment_start = function_start

    replacement = '''_OPENAI_REQUEST_LOCK = threading.Lock()\n\n\ndef _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int = 75) -> dict:\n    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")\n    transient_codes = {429, 500, 502, 503, 504}\n    max_attempts = 4\n\n    with _OPENAI_REQUEST_LOCK:\n        for attempt in range(max_attempts):\n            if attempt:\n                time.sleep(min(8.0, float(2 ** (attempt - 1))))\n\n            http_request = request.Request(url, data=body, headers=headers, method="POST")\n            try:\n                with request.urlopen(http_request, timeout=timeout) as response:\n                    return json.loads(response.read().decode("utf-8"))\n            except error.HTTPError as exc:\n                raw_body = exc.read().decode("utf-8", errors="replace")\n                provider_code = ""\n                try:\n                    provider_payload = json.loads(raw_body or "{}")\n                    provider_error = provider_payload.get("error") or {}\n                    provider_code = str(provider_error.get("code") or provider_error.get("type") or "").strip()\n                except (json.JSONDecodeError, TypeError, AttributeError):\n                    provider_code = ""\n\n                hard_limit = provider_code in {"insufficient_quota", "billing_hard_limit_reached"}\n                retryable = exc.code in transient_codes and not hard_limit\n                if retryable and attempt < max_attempts - 1:\n                    continue\n\n                if exc.code == 429 and hard_limit:\n                    raise RuntimeError(\n                        "A conta de inteligência atingiu o limite de uso configurado. Verifique o faturamento do provedor."\n                    ) from exc\n                if exc.code == 429:\n                    raise RuntimeError(\n                        "O serviço de inteligência atingiu um limite momentâneo. Aguarde alguns segundos e tente novamente."\n                    ) from exc\n                if exc.code in transient_codes:\n                    raise RuntimeError(\n                        "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."\n                    ) from exc\n                raise RuntimeError(\n                    "Não foi possível processar esta solicitação no momento. Tente novamente."\n                ) from exc\n            except error.URLError as exc:\n                if attempt < max_attempts - 1:\n                    continue\n                raise RuntimeError(\n                    "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."\n                ) from exc\n\n    raise RuntimeError(\n        "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."\n    )\n'''

    source = source[:segment_start] + replacement + source[function_end:]

    final_segment = source[segment_start:source.index('\n\ndef _integration_api_key', segment_start)]
    required = ('429', 'max_attempts = 4', '_OPENAI_REQUEST_LOCK', 'insufficient_quota')
    if not all(item in final_segment for item in required):
        raise RuntimeError('Cliente OpenAI final não contém todas as proteções contra 429.')

    BRAIN_PATH.write_text(source, encoding='utf-8')


def _patch_simple_conversation() -> None:
    source = ORCHESTRATED_PATH.read_text(encoding='utf-8')

    old_normalization = '    normalized = " ".join(_normalized_text(message).replace("?", "").replace("!", "").split())'
    new_normalization = '    normalized = " ".join(_normalized_text(message).translate(str.maketrans("", "", "?!,.;:")).split())'
    if old_normalization in source:
        source = source.replace(old_normalization, new_normalization, 1)
    elif new_normalization not in source:
        raise RuntimeError('Normalização de conversa simples não encontrada.')

    old_greetings = '        "chat tudo bem", "chat, tudo bem", "tudo bem", "como voce esta", "como vai",\n'
    new_greetings = '        "chat tudo bem", "tudo bem", "como voce esta", "como vai", "boa noite chat",\n'
    if old_greetings in source:
        source = source.replace(old_greetings, new_greetings, 1)
    elif new_greetings not in source:
        raise RuntimeError('Lista de saudações simples não encontrada.')

    old_condition = '    if normalized in greeting_messages and not history:\n'
    new_condition = '    if normalized in greeting_messages:\n'
    if old_condition in source:
        source = source.replace(old_condition, new_condition, 1)
    elif new_condition not in source:
        raise RuntimeError('Condição de saudação simples não encontrada.')

    if new_normalization not in source or new_condition not in source or '"boa noite chat"' not in source:
        raise RuntimeError('Roteamento local de saudações não ficou completo.')

    ORCHESTRATED_PATH.write_text(source, encoding='utf-8')


def main() -> None:
    _patch_rate_limit_client()
    _patch_simple_conversation()
    print('Proteções finais aplicadas: retry 429 serializado e saudações fora do pipeline especializado.')


if __name__ == '__main__':
    main()
