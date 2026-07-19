from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.domnai_core.contracts import ConversationRequest, ConversationResponse
from app.domnai_core.memory import MemoryStore, NullMemoryStore
from app.domnai_core.persistence import (
    ConversationRecord,
    ConversationRepository,
    NullConversationRepository,
)
from app.domnai_core.tools import ToolRegistry


class ModelProvider(Protocol):
    """Porta de saída do núcleo para qualquer provedor de inteligência."""

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        ...


class ConversationEngine:
    """Ponto único de entrada do novo núcleo conversacional.

    O motor coordena apenas contratos e portas explícitas. Provedor, memória,
    persistência e ferramentas permanecem substituíveis e não importam serviços
    do backend legado.
    """

    def __init__(
        self,
        provider: ModelProvider,
        *,
        memory_store: MemoryStore | None = None,
        repository: ConversationRepository | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self._provider = provider
        self._memory_store = memory_store or NullMemoryStore()
        self._repository = repository or NullConversationRepository()
        self._tools = tools or ToolRegistry()

    def respond(self, request: ConversationRequest) -> ConversationResponse:
        conversation_id = str(request.metadata.get("conversation_id") or "").strip()
        effective_request = request

        if conversation_id:
            stored_memory = self._memory_store.load(conversation_id)
            effective_memory = {**stored_memory, **dict(request.memory)}
            effective_metadata = {
                **dict(request.metadata),
                "available_tools": self._tools.names(),
            }
            effective_request = replace(
                request,
                memory=effective_memory,
                metadata=effective_metadata,
            )

        response = self._provider.generate(effective_request)
        if not isinstance(response, ConversationResponse):
            raise TypeError("O provedor deve retornar ConversationResponse.")

        if conversation_id and response.memory_update is not None:
            next_memory = {**dict(effective_request.memory), **dict(response.memory_update)}
            self._memory_store.save(conversation_id, next_memory)

        self._repository.append(
            ConversationRecord(
                conversation_id=conversation_id,
                request=effective_request,
                response=response,
            )
        )
        return response
