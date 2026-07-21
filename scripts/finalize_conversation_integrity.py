from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path("/app/app/services/chat_task_worker.py")
ORCHESTRATOR_PATH = Path("/app/app/services/orchestrated_brain.py")


def replace_function(source: str, name: str, replacement: str) -> str:
    start = source.index(f"def {name}(")
    end = source.index("\n\ndef ", start + 1)
    return source[:start] + replacement.rstrip() + source[end:]


def patch_worker() -> None:
    source = WORKER_PATH.read_text(encoding="utf-8")

    if "from sqlalchemy.orm import aliased\n" not in source:
        source = source.replace(
            "from sqlalchemy import select, update\n",
            "from sqlalchemy import select, update\nfrom sqlalchemy.orm import aliased\n",
            1,
        )

    if "_claim_lock = threading.Lock()\n" not in source:
        source = source.replace(
            "_worker_lock = threading.Lock()\n",
            "_worker_lock = threading.Lock()\n_claim_lock = threading.Lock()\n",
            1,
        )

    claim_function = '''def _claim_next_task() -> str | None:
    # A seleção e a marcação são serializadas dentro do processo. Além disso,
    # uma tarefa do mesmo usuário só é elegível quando não existe outra em
    # processamento, preservando a ordem da conversa sem reduzir o paralelismo
    # entre usuários diferentes.
    with _claim_lock:
        with session_scope() as db:
            processing = aliased(ChatTask)
            processing_for_same_user = (
                select(processing.id)
                .where(
                    processing.user_id == ChatTask.user_id,
                    processing.status == "processing",
                )
                .correlate(ChatTask)
                .exists()
            )
            task = db.scalar(
                select(ChatTask)
                .where(
                    ChatTask.status == "queued",
                    ~processing_for_same_user,
                )
                .order_by(ChatTask.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if task is None:
                return None
            task.status = "processing"
            task.updated_at = _now()
            return task.id
'''
    source = replace_function(source, "_claim_next_task", claim_function)

    block_start = source.index("        sources: list[dict] = []\n", source.index("def _process_task("))
    block_end = source.index("        intelligence_started_at = time.perf_counter()\n", block_start)
    context_block = '''        sources: list[dict] = []
        context_blocks: list[str] = []

        user_name = str(payload.get("user_name") or "").strip()[:80]
        if user_name and operation and not history:
            context_blocks.append(
                "PERSONALIZAÇÃO INTERNA (não é fala do usuário): "
                f"o primeiro nome do usuário autenticado é {user_name}. "
                "Use-o somente se soar natural na abertura; não invente saudação nem exponha este contexto."
            )

        if not payload.get("local_artifact_followup") and should_research_web(original_message):
            research_started_at = time.perf_counter()
            research = research_web(original_message)
            timings["research_ms"] = _elapsed_ms(research_started_at)
            sources = research.sources
            context_blocks.append(
                "EVIDÊNCIA EXTERNA VERIFICADA (não é fala do usuário):\\n"
                + research.text
                + "\\nUse somente fatos sustentados por esta evidência e nunca invente fontes ou URLs."
            )

        external_context = "\\n\\n".join(context_blocks)
'''
    source = source[:block_start] + context_block + source[block_end:]

    old_call = '''        result = generate_orchestrated_response(
            message=message_for_brain,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
'''
    new_call = '''        result = generate_orchestrated_response(
            message=original_message,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
            external_context=external_context,
        )
'''
    if old_call in source:
        source = source.replace(old_call, new_call, 1)
    elif new_call not in source:
        raise RuntimeError("chamada do orquestrador em formato desconhecido")

    required = (
        "processing_for_same_user",
        "should_research_web(original_message)",
        "external_context=external_context",
        "message=original_message",
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"integridade do worker ausente: {marker}")

    forbidden = (
        "should_research_web(original_message, operation)",
        "message=message_for_brain",
        "PESQUISA WEB VERIFICADA:\\n{research.text}",
    )
    for marker in forbidden:
        if marker in source:
            raise RuntimeError(f"mistura antiga permaneceu no worker: {marker}")

    WORKER_PATH.write_text(source, encoding="utf-8")


def patch_orchestrator() -> None:
    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    old_signature = '''def generate_orchestrated_response(
    message: str,
    history: list[dict],
    operation: str | None,
    attachments: list[dict] | None = None,
    diagnosis_state: dict | None = None,
) -> MeteredBrainResult:
'''
    new_signature = '''def generate_orchestrated_response(
    message: str,
    history: list[dict],
    operation: str | None,
    attachments: list[dict] | None = None,
    diagnosis_state: dict | None = None,
    external_context: str = "",
) -> MeteredBrainResult:
'''
    if old_signature in source:
        source = source.replace(old_signature, new_signature, 1)
    elif new_signature not in source:
        raise RuntimeError("assinatura do orquestrador em formato desconhecido")

    anchor = "    safe_attachments = attachments or []\n"
    context_setup = '''    safe_attachments = attachments or []
    contextual_history = list(history)
    safe_external_context = str(external_context or "").strip()
    if safe_external_context:
        contextual_history.append({
            "role": "assistant",
            "content": (
                "CONTEXTO INTERNO SEPARADO DA MENSAGEM DO USUÁRIO:\\n"
                + safe_external_context
            ),
        })
'''
    if context_setup not in source:
        if anchor not in source:
            raise RuntimeError("âncora de anexos do orquestrador ausente")
        source = source.replace(anchor, context_setup, 1)

    source = source.replace(
        "history=_normalized_history(history),",
        "history=_normalized_history(contextual_history),",
        1,
    )

    source = source.replace(
        '''            history=history,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
            orchestration_plan=plan or None,
''',
        '''            history=contextual_history,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
            orchestration_plan=plan or None,
''',
        1,
    )

    last_general_old = '''    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=None,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )
'''
    last_general_new = '''    base_result = generate_metered_response(
        message=message,
        history=contextual_history,
        operation=None,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )
'''
    if last_general_old in source:
        source = source.replace(last_general_old, last_general_new, 1)
    elif last_general_new not in source:
        raise RuntimeError("rota geral final em formato desconhecido")

    for marker in (
        'external_context: str = ""',
        "contextual_history = list(history)",
        "history=_normalized_history(contextual_history)",
        "history=contextual_history",
    ):
        if marker not in source:
            raise RuntimeError(f"separação de contexto ausente: {marker}")

    ORCHESTRATOR_PATH.write_text(source, encoding="utf-8")


patch_worker()
patch_orchestrator()
print("Integridade conversacional aplicada: ordem por usuário e evidência separada da mensagem original.")
