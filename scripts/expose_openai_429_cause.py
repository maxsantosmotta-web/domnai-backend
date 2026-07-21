from __future__ import annotations

from pathlib import Path


BRAIN_PATH = Path('/app/app/services/domnai_brain.py')

POST_JSON_REPLACEMENT = '''_OPENAI_REQUEST_LIMIT = threading.BoundedSemaphore(value=2)


def _retry_after_seconds(exc: error.HTTPError, attempt: int) -> float:
    raw_value = str(exc.headers.get("Retry-After") or "").strip()
    if raw_value:
        try:
            return max(0.0, min(float(raw_value), 30.0))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(raw_value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, min((retry_at - datetime.now(timezone.utc)).total_seconds(), 30.0))
            except (TypeError, ValueError, OverflowError):
                pass
    return min(1.0 * (2 ** attempt), 8.0)


def _provider_error_details(exc: error.HTTPError, raw_body: bytes) -> tuple[str, str, str]:
    error_type = ""
    error_code = ""
    message = ""
    try:
        parsed = json.loads(raw_body.decode("utf-8", errors="replace"))
        details = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(details, dict):
            error_type = str(details.get("type") or "")[:120]
            error_code = str(details.get("code") or "")[:120]
            message = " ".join(str(details.get("message") or "").split())[:300]
    except (ValueError, TypeError):
        pass
    return error_type, error_code, message


def _is_permanent_429(error_type: str, error_code: str) -> bool:
    permanent_markers = {
        "insufficient_quota",
        "billing_hard_limit_reached",
        "billing_not_active",
        "account_deactivated",
        "organization_deactivated",
    }
    normalized = {error_type.casefold().strip(), error_code.casefold().strip()}
    return bool(normalized & permanent_markers)


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int = 75) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    transient_codes = {429, 500, 502, 503, 504}
    max_attempts = 4

    with _OPENAI_REQUEST_LIMIT:
        for attempt in range(max_attempts):
            http_request = request.Request(url, data=body, headers=headers, method="POST")
            try:
                with request.urlopen(http_request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except error.HTTPError as exc:
                raw_body = exc.read()
                error_type, error_code, provider_message = _provider_error_details(exc, raw_body)
                retry_after = str(exc.headers.get("Retry-After") or "").strip()
                request_id = str(exc.headers.get("x-request-id") or "").strip()[:120]
                remaining_requests = str(exc.headers.get("x-ratelimit-remaining-requests") or "").strip()
                remaining_tokens = str(exc.headers.get("x-ratelimit-remaining-tokens") or "").strip()
                print(
                    "openai_http_error "
                    f"status={exc.code} attempt={attempt + 1}/{max_attempts} "
                    f"type={error_type or '-'} code={error_code or '-'} "
                    f"retry_after={retry_after or '-'} request_id={request_id or '-'} "
                    f"remaining_requests={remaining_requests or '-'} remaining_tokens={remaining_tokens or '-'} "
                    f"message={provider_message or '-'}",
                    flush=True,
                )

                permanent_429 = exc.code == 429 and _is_permanent_429(error_type, error_code)
                if exc.code in transient_codes and not permanent_429 and attempt < max_attempts - 1:
                    time.sleep(_retry_after_seconds(exc, attempt))
                    continue
                if exc.code in transient_codes:
                    raise RuntimeError(
                        "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."
                    ) from exc
                raise RuntimeError(
                    "Não foi possível processar esta solicitação no momento. Tente novamente."
                ) from exc
            except error.URLError as exc:
                if attempt < max_attempts - 1:
                    time.sleep(min(1.0 * (2 ** attempt), 8.0))
                    continue
                raise RuntimeError(
                    "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."
                ) from exc

    raise RuntimeError(
        "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."
    )
'''


def main() -> None:
    if not BRAIN_PATH.exists():
        raise RuntimeError('domnai_brain.py não encontrado no runtime.')
    source = BRAIN_PATH.read_text(encoding='utf-8')
    start = source.index('_OPENAI_REQUEST_LIMIT =')
    end = source.index('\n\ndef _integration_api_key', start)
    source = source[:start] + POST_JSON_REPLACEMENT.rstrip() + source[end:]
    required = (
        'openai_http_error',
        '_provider_error_details',
        '_is_permanent_429',
        'insufficient_quota',
    )
    if not all(item in source for item in required):
        raise RuntimeError('Diagnóstico seguro do 429 não foi instalado integralmente.')
    BRAIN_PATH.write_text(source, encoding='utf-8')
    print('Diagnóstico seguro do HTTP 429 instalado no runtime final.')


if __name__ == '__main__':
    main()
