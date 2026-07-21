from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
ARTIFACT_DECISION_PATH = Path('/app/app/services/artifact_decision.py')
BRAIN_PATH = Path('/app/app/services/domnai_brain.py')
ORCHESTRATOR_PATH = Path('/app/app/services/orchestrated_brain.py')
ANCHOR = '''        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
        existing_result = json.loads(task.result_json) if task.result_json else None
'''
REPLACEMENT = '''        payload = json.loads(task.request_json)
        payload["task_id"] = task_id
        operation = payload.get("operation")
        existing_result = json.loads(task.result_json) if task.result_json else None
'''
DUPLICATE = '''        original_message = str(payload.get("message") or "").strip()
        operation = payload.get("operation")
        history = payload.get("history") or []
'''
DEDUPLICATED = '''        original_message = str(payload.get("message") or "").strip()
        history = payload.get("history") or []
'''


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
                exc.read()
                if exc.code in transient_codes and attempt < max_attempts - 1:
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


LIGHT_CONVERSATION_HELPERS = '''def _normalized_casual_message(message: str) -> str:
    return " ".join(
        "".join(
            char if char.isalnum() or char.isspace() else " "
            for char in _normalized_text(message)
        ).split()
    )


def _is_light_conversation(message: str, attachments: list[dict]) -> bool:
    if attachments:
        return False
    normalized = _normalized_casual_message(message)
    if not normalized or len(normalized) > 100:
        return False
    casual_messages = {
        "oi", "ola", "bom dia", "boa tarde", "boa noite", "boa noite chat",
        "e ai", "chat tudo bem", "tudo bem", "como voce esta", "como vai",
        "obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu",
        "tchau", "ate mais", "falamos depois", "ate logo",
    }
    return normalized in casual_messages


def _light_conversation_response(
    message: str,
    history: list[dict],
    diagnosis_state: dict | None,
) -> MeteredBrainResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return generate_metered_response(
            message=message,
            history=history,
            operation=None,
            attachments=[],
            diagnosis_state=diagnosis_state,
        )

    model = os.getenv("DOMNAI_LIGHT_MODEL", os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini")).strip()
    input_messages = _normalized_history(history, limit=6)
    input_messages.append({"role": "user", "content": message})
    text, usage = _openai_request(
        api_key,
        {
            "model": model,
            "instructions": (
                "Você é o DomnAI. Converse como uma pessoa atenciosa, natural e direta em português do Brasil. "
                "Responda ao que o usuário acabou de dizer considerando o histórico recente. "
                "Não use frases padronizadas, não pareça atendimento automático, não cite a operação selecionada "
                "e não transforme uma saudação em entrevista. Seja breve, mas humano."
            ),
            "input": input_messages,
            "temperature": 0.8,
            "max_output_tokens": 180,
        },
    )
    return MeteredBrainResult(
        text=text,
        provider="openai-light-conversation",
        model=model,
        input_tokens=_usage_value(usage, "input_tokens"),
        output_tokens=_usage_value(usage, "output_tokens"),
        cached_input_tokens=_cached_value(usage),
        diagnosis_state=diagnosis_state,
        timings={"orchestrator_ms": 0, "generation_ms": 0},
    )
'''


LIGHT_CONVERSATION_BLOCK = '''    if _is_light_conversation(message, safe_attachments):
        return _light_conversation_response(message, history, diagnosis_state)
'''


SERIAL_CLAIM_FUNCTION = '''def _claim_next_task() -> str | None:
    with session_scope() as db:
        earlier = aliased(ChatTask)
        earlier_for_same_user = select(earlier.id).where(
            earlier.user_id == ChatTask.user_id,
            earlier.status.in_(("queued", "processing")),
            (
                (earlier.created_at < ChatTask.created_at)
                | (
                    (earlier.created_at == ChatTask.created_at)
                    & (earlier.id < ChatTask.id)
                )
            ),
        )
        task = db.scalar(
            select(ChatTask)
            .where(
                ChatTask.status == "queued",
                ~earlier_for_same_user.exists(),
            )
            .order_by(ChatTask.created_at.asc(), ChatTask.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if task is None:
            return None
        task.status = "processing"
        task.updated_at = _now()
        return task.id
'''


BRAIN_PREPARATION = '''        sources: list[dict] = []
        brain_history = list(history)
        if user_name and operation and not history:
            brain_history.append({
                "role": "assistant",
                "content": (
                    "CONTEXTO INTERNO DE PERSONALIZAÇÃO — não atribua isto ao usuário: "
                    f"o primeiro nome autenticado é {user_name}. Use-o naturalmente apenas se fizer sentido; "
                    "não explique este contexto."
                ),
            })
        message_for_brain = original_message
        if not payload.get("local_artifact_followup") and should_research_web(original_message, operation):
            research_started_at = time.perf_counter()
            research = research_web(original_message)
            timings["research_ms"] = _elapsed_ms(research_started_at)
            sources = research.sources
            brain_history.append({
                "role": "assistant",
                "content": (
                    "EVIDÊNCIA EXTERNA VERIFICADA — não atribua este texto ao usuário e não o grave como fato pessoal:\n"
                    f"{research.text}\n\n"
                    "Use somente afirmações sustentadas por esta evidência. Não invente fontes, URLs, números ou datas."
                ),
            })
'''


def _fix_worker_scope() -> None:
    if not WORKER_PATH.exists():
        raise RuntimeError('chat_task_worker.py não encontrado no runtime.')
    source = WORKER_PATH.read_text(encoding='utf-8')
    if REPLACEMENT not in source:
        if ANCHOR not in source:
            raise RuntimeError('Ponto seguro para inicializar operation não encontrado.')
        source = source.replace(ANCHOR, REPLACEMENT, 1)
    if DUPLICATE in source:
        source = source.replace(DUPLICATE, DEDUPLICATED, 1)
    operation_index = source.index('        operation = payload.get("operation")')
    conditional_index = source.index('    if existing_result is None:')
    if operation_index > conditional_index:
        raise RuntimeError('operation continuou inicializada depois do ramo condicional.')
    WORKER_PATH.write_text(source, encoding='utf-8')


def _serialize_user_conversations() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')
    if 'from sqlalchemy.orm import aliased\n' not in source:
        source = source.replace('from sqlalchemy import select, update\n', 'from sqlalchemy import select, update\nfrom sqlalchemy.orm import aliased\n', 1)
    start = source.index('def _claim_next_task() -> str | None:')
    end = source.index('\n\ndef _load_attachments(', start)
    source = source[:start] + SERIAL_CLAIM_FUNCTION.rstrip() + source[end:]
    if '~earlier_for_same_user.exists()' not in source:
        raise RuntimeError('serialização por usuário não foi instalada no worker.')
    WORKER_PATH.write_text(source, encoding='utf-8')


def _separate_message_and_evidence() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')
    start = source.index('        sources: list[dict] = []')
    end = source.index('        intelligence_started_at = time.perf_counter()', start)
    source = source[:start] + BRAIN_PREPARATION.rstrip() + '\n' + source[end:]
    call_start = source.index('        result = generate_orchestrated_response(', end)
    call_end = source.index('        )\n', call_start) + len('        )\n')
    call = source[call_start:call_end]
    call = call.replace('            history=history,\n', '            history=brain_history,\n', 1)
    source = source[:call_start] + call + source[call_end:]
    for required in (
        'message_for_brain = original_message',
        'history=brain_history,',
        'EVIDÊNCIA EXTERNA VERIFICADA',
        'não o grave como fato pessoal',
    ):
        if required not in source:
            raise RuntimeError(f'separação de evidência ausente no worker: {required}')
    WORKER_PATH.write_text(source, encoding='utf-8')


def _fix_artifact_decision_scope() -> None:
    if not ARTIFACT_DECISION_PATH.exists():
        raise RuntimeError('artifact_decision.py não encontrado no runtime.')
    source = ARTIFACT_DECISION_PATH.read_text(encoding='utf-8')
    for unsafe in ('    del operation, answer\n', '    del answer, operation\n', '    del operation\n', '    del answer\n'):
        source = source.replace(unsafe, '')
    function_start = source.index('def _requires_artifact_decision(')
    function_end = source.index('\n\ndef decide_artifact(', function_start)
    function_source = source[function_start:function_end]
    if 'del operation' in function_source or 'del answer' in function_source:
        raise RuntimeError('artifact_decision ainda apaga parâmetros usados pela decisão final.')
    if 'answer' not in function_source or 'operation' not in function_source:
        raise RuntimeError('artifact_decision perdeu os parâmetros exigidos pela decisão final.')
    ARTIFACT_DECISION_PATH.write_text(source, encoding='utf-8')


def _fix_openai_retry() -> None:
    if not BRAIN_PATH.exists():
        raise RuntimeError('domnai_brain.py não encontrado no runtime.')
    source = BRAIN_PATH.read_text(encoding='utf-8')
    if 'import threading\n' not in source:
        source = source.replace('import os\n', 'import os\nimport threading\nimport time\nfrom datetime import datetime, timezone\nfrom email.utils import parsedate_to_datetime\n', 1)
    start = source.index('def _post_json(')
    end = source.index('\n\ndef _integration_api_key', start)
    source = source[:start] + POST_JSON_REPLACEMENT.rstrip() + source[end:]
    if 'transient_codes = {429, 500, 502, 503, 504}' not in source:
        raise RuntimeError('429 não foi incluído como transitório no runtime final.')
    BRAIN_PATH.write_text(source, encoding='utf-8')


def _fix_simple_conversation() -> None:
    if not ORCHESTRATOR_PATH.exists():
        raise RuntimeError('orchestrated_brain.py não encontrado no runtime.')
    source = ORCHESTRATOR_PATH.read_text(encoding='utf-8')

    function_start = source.index('def _simple_conversation_response(')
    function_end = source.index('\n\ndef _specialized_engine(', function_start)
    source = source[:function_start] + LIGHT_CONVERSATION_HELPERS.rstrip() + source[function_end:]

    old_block_start = source.index('    simple_reply = _simple_conversation_response(')
    old_block_end = source.index('\n    if _specialized_engine({}, operation, message) is None:', old_block_start)
    source = source[:old_block_start] + LIGHT_CONVERSATION_BLOCK.rstrip() + source[old_block_end:]

    forbidden = (
        'Tudo ótimo! E com você? Como posso ajudar hoje?',
        'Por nada!',
        'Até mais!',
        'provider="domnai-local-conversation"',
    )
    if any(item in source for item in forbidden):
        raise RuntimeError('Respostas automáticas fixas permaneceram no runtime final.')
    if 'provider="openai-light-conversation"' not in source:
        raise RuntimeError('Conversa leve real não foi instalada no runtime final.')
    ORCHESTRATOR_PATH.write_text(source, encoding='utf-8')


def main() -> None:
    _fix_worker_scope()
    _serialize_user_conversations()
    _separate_message_and_evidence()
    _fix_artifact_decision_scope()
    _fix_openai_retry()
    _fix_simple_conversation()
    print('Runtime final corrigido: tarefas em ordem, evidência separada, conversa livre e operação sem captura.')


if __name__ == '__main__':
    main()
