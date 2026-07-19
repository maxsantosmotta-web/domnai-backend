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
from app.domnai_core.memory import InMemoryMemoryStore, MemoryStore, NullMemoryStore
from app.domnai_core.persistence import (
    ConversationRecord,
    ConversationRepository,
    InMemoryConversationRepository,
    NullConversationRepository,
)
from app.domnai_core.providers import OpenAIResponsesProvider
from app.domnai_core.tools import ToolCall, ToolRegistry, ToolResult

__all__ = [
    "Attachment",
    "ConversationEngine",
    "ConversationRecord",
    "ConversationRepository",
    "ConversationRequest",
    "ConversationResponse",
    "HistoryMessage",
    "InMemoryConversationRepository",
    "InMemoryMemoryStore",
    "MemoryStore",
    "ModelProvider",
    "NullConversationRepository",
    "NullMemoryStore",
    "OpenAIResponsesProvider",
    "ToolCall",
    "ToolRegistry",
    "ToolResult",
]
