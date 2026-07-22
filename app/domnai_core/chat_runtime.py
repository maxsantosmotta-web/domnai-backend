from __future__ import annotations

from functools import lru_cache

from app.domnai_core.composition import build_domnai_core_runtime
from app.domnai_core.contracts import Attachment, ConversationRequest, HistoryMessage
from app.services.metered_brain import MeteredBrainResult


@lru_cache(maxsize=1)
def _runtime():
    return build_domnai_core_runtime()


def _normalize(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _is_pdf_followup(message: str) -> bool:
    normalized = _normalize(message)
    if "pdf" not in normalized:
        return False
    followup_markers = (
        "mande isso", "me mande", "manda isso", "envie isso", "me envie",
        "coloque isso", "organize isso", "transforme isso", "isso no pdf",
        "somente no pdf", "só no pdf", "fechar no pdf", "finalizar no pdf",
    )
    return any(marker in normalized for marker in followup_markers)


def _last_completed_assistant_answer(history: list[dict]) -> str:
    for item in reversed(history):
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        normalized = _normalize(content)
        if "openai respondeu http" in normalized or "não foi possível" in normalized:
            continue
        return content
    return ""


def generate_new_core_response(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    attachments: list[dict],
    user_id: str,
    task_id: str,
) -> MeteredBrainResult:
    # Pedido de PDF ao final da conversa é uma etapa de empacotamento, não uma
    # nova análise. Reutiliza a última resposta concluída para impedir recálculo,
    # mudança silenciosa de valores ou recusa indevida de geração do arquivo.
    if _is_pdf_followup(message):
        source_answer = _last_completed_assistant_answer(history)
        if source_answer:
            return MeteredBrainResult(
                text=source_answer,
                provider="local-artifact",
                model="deterministic-followup",
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                diagnosis_state=None,
                timings={"artifact_followup_reuse": 1},
            )

    request = ConversationRequest(
        message=message,
        operation=operation,
        history=tuple(
            HistoryMessage(
                role=str(item.get('role') or 'user'),
                content=str(item.get('content') or '').strip(),
            )
            for item in history[-100:]
            if str(item.get('role') or '') in {'system', 'user', 'assistant', 'tool'}
            and str(item.get('content') or '').strip()
        ),
        attachments=tuple(
            Attachment(
                name=str(item.get('name') or 'arquivo'),
                mime_type=str(item.get('mime_type') or 'application/octet-stream'),
                content=bytes(item.get('content') or b''),
            )
            for item in attachments
        ),
        memory={},
        metadata={
            'request_id': task_id,
            'user_id': user_id,
            'conversation_id': user_id,
            'runtime': 'new-core-only',
        },
    )
    response = _runtime().engine.respond(request)
    return MeteredBrainResult(
        text=response.text,
        provider=response.provider,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cached_input_tokens=response.cached_input_tokens,
        diagnosis_state=None,
        timings={'new_core_only': 1},
    )
