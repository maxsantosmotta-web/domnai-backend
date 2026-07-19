"""Núcleo source-first do DomnAI.

Este pacote não depende do fluxo legado nem altera a rota de produção.
"""

from app.domnai_core.contracts import (
    Attachment,
    ConversationRequest,
    ConversationResponse,
    HistoryMessage,
)
from app.domnai_core.engine import ConversationEngine, ModelProvider

__all__ = [
    "Attachment",
    "ConversationEngine",
    "ConversationRequest",
    "ConversationResponse",
    "HistoryMessage",
    "ModelProvider",
]
