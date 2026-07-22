from __future__ import annotations

from functools import lru_cache

from app.domnai_core.composition import build_domnai_core_runtime
from app.domnai_core.contracts import Attachment, ConversationRequest, HistoryMessage
from app.services.metered_brain import MeteredBrainResult


@lru_cache(maxsize=1)
def _runtime():
    return build_domnai_core_runtime()


def generate_new_core_response(
    *,
    message: str,
    operation: str | None,
    history: list[dict],
    attachments: list[dict],
    user_id: str,
    task_id: str,
) -> MeteredBrainResult:
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
