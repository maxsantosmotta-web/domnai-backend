"""Núcleo source-first do DomnAI.

Este pacote não depende do fluxo legado nem altera a rota de produção.
"""

from app.domnai_core.attachments import (
    AttachmentPreparer,
    AttachmentValidationError,
    PreparedAttachment,
)
from app.domnai_core.builtin_tools import build_builtin_tool_registry
from app.domnai_core.composition import DomnAICoreRuntime, build_domnai_core_runtime
from app.domnai_core.config import DomnAICoreSettings
from app.domnai_core.context_memory import ContextMemoryManager, MemoryScope
from app.domnai_core.contracts import (
    Attachment,
    ConversationRequest,
    ConversationResponse,
    HistoryMessage,
)
from app.domnai_core.engine import ConversationEngine, ModelProvider
from app.domnai_core.memory import InMemoryMemoryStore, MemoryStore, NullMemoryStore
from app.domnai_core.observability import (
    CoreMetricsSink,
    CoreRequestMetric,
    InMemoryCoreMetricsSink,
    NullCoreMetricsSink,
)
from app.domnai_core.persistence import (
    ConversationRecord,
    ConversationRepository,
    InMemoryConversationRepository,
    NullConversationRepository,
)
from app.domnai_core.postgres import (
    PostgresConversationRepository,
    PostgresMemoryStore,
    PostgresSchemaManager,
)
from app.domnai_core.providers import OpenAIResponsesProvider
from app.domnai_core.tool_execution import (
    ToolExecutionError,
    ToolExecutionReport,
    ToolExecutor,
)
from app.domnai_core.tools import (
    ToolCall,
    ToolPolicy,
    ToolPolicyError,
    ToolRegistry,
    ToolResult,
    ToolTimeoutError,
)

__all__ = [
    "Attachment",
    "AttachmentPreparer",
    "AttachmentValidationError",
    "ContextMemoryManager",
    "ConversationEngine",
    "ConversationRecord",
    "ConversationRepository",
    "ConversationRequest",
    "ConversationResponse",
    "CoreMetricsSink",
    "CoreRequestMetric",
    "DomnAICoreRuntime",
    "DomnAICoreSettings",
    "HistoryMessage",
    "InMemoryConversationRepository",
    "InMemoryCoreMetricsSink",
    "InMemoryMemoryStore",
    "MemoryScope",
    "MemoryStore",
    "ModelProvider",
    "NullConversationRepository",
    "NullCoreMetricsSink",
    "NullMemoryStore",
    "OpenAIResponsesProvider",
    "PostgresConversationRepository",
    "PostgresMemoryStore",
    "PostgresSchemaManager",
    "PreparedAttachment",
    "ToolCall",
    "ToolExecutionError",
    "ToolExecutionReport",
    "ToolExecutor",
    "ToolPolicy",
    "ToolPolicyError",
    "ToolRegistry",
    "ToolResult",
    "ToolTimeoutError",
    "build_builtin_tool_registry",
    "build_domnai_core_runtime",
]
