from __future__ import annotations

from dataclasses import dataclass

from app.database import is_database_configured
from app.domnai_core.builtin_tools import build_builtin_tool_registry
from app.domnai_core.config import DomnAICoreSettings
from app.domnai_core.engine import ConversationEngine
from app.domnai_core.memory import InMemoryMemoryStore
from app.domnai_core.observability import CoreMetricsSink, NullCoreMetricsSink
from app.domnai_core.persistence import InMemoryConversationRepository
from app.domnai_core.postgres import (
    PostgresConversationRepository,
    PostgresMemoryStore,
    PostgresSchemaManager,
)
from app.domnai_core.providers import OpenAIResponsesProvider
from app.domnai_core.tools import ToolRegistry


@dataclass(frozen=True, slots=True)
class DomnAICoreRuntime:
    settings: DomnAICoreSettings
    engine: ConversationEngine
    metrics: CoreMetricsSink
    persistence_backend: str
    registered_tools: tuple[str, ...]


def build_domnai_core_runtime(
    settings: DomnAICoreSettings | None = None,
    *,
    tools: ToolRegistry | None = None,
    metrics: CoreMetricsSink | None = None,
) -> DomnAICoreRuntime:
    resolved = settings or DomnAICoreSettings.from_env()
    metrics_sink = metrics or NullCoreMetricsSink()

    if resolved.use_postgres:
        if not is_database_configured():
            raise RuntimeError(
                "DOMNAI_CORE_USE_POSTGRES está ativo, mas DATABASE_URL não está configurada."
            )
        if resolved.ensure_schema:
            PostgresSchemaManager().ensure_schema()
        memory_store = PostgresMemoryStore()
        repository = PostgresConversationRepository()
        persistence_backend = "postgres"
    else:
        memory_store = InMemoryMemoryStore()
        repository = InMemoryConversationRepository()
        persistence_backend = "memory"

    if tools is not None:
        resolved_tools = tools
    elif resolved.enable_builtin_tools:
        resolved_tools = build_builtin_tool_registry()
    else:
        resolved_tools = ToolRegistry()

    provider = OpenAIResponsesProvider(
        model=resolved.model,
        timeout_seconds=resolved.timeout_seconds,
    )
    engine = ConversationEngine(
        provider,
        memory_store=memory_store,
        repository=repository,
        tools=resolved_tools,
        max_tool_iterations=resolved.max_tool_iterations,
        max_tool_calls_per_turn=resolved.max_tool_calls_per_turn,
        allowed_tool_risks=resolved.allowed_tool_risks,
        metrics=metrics_sink,
    )
    return DomnAICoreRuntime(
        settings=resolved,
        engine=engine,
        metrics=metrics_sink,
        persistence_backend=persistence_backend,
        registered_tools=resolved_tools.names(),
    )
