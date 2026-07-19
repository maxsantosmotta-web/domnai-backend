from __future__ import annotations

import json
from dataclasses import replace
from typing import Protocol

from app.domnai_core.contracts import ConversationRequest, ConversationResponse
from app.domnai_core.memory import MemoryStore, NullMemoryStore
from app.domnai_core.observability import (
    CoreMetricsSink,
    CoreRequestMetric,
    NullCoreMetricsSink,
    RequestTimer,
)
from app.domnai_core.persistence import (
    ConversationRecord,
    ConversationRepository,
    NullConversationRepository,
)
from app.domnai_core.tools import ToolCall, ToolRegistry


class ModelProvider(Protocol):
    """Porta de saída do núcleo para qualquer provedor de inteligência."""

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        ...


class ConversationEngine:
    """Ponto único de entrada do novo núcleo conversacional."""

    def __init__(
        self,
        provider: ModelProvider,
        *,
        memory_store: MemoryStore | None = None,
        repository: ConversationRepository | None = None,
        tools: ToolRegistry | None = None,
        max_tool_iterations: int = 3,
        metrics: CoreMetricsSink | None = None,
    ) -> None:
        if max_tool_iterations < 0:
            raise ValueError("max_tool_iterations não pode ser negativo.")
        self._provider = provider
        self._memory_store = memory_store or NullMemoryStore()
        self._repository = repository or NullConversationRepository()
        self._tools = tools or ToolRegistry()
        self._max_tool_iterations = max_tool_iterations
        self._metrics = metrics or NullCoreMetricsSink()

    def respond(self, request: ConversationRequest) -> ConversationResponse:
        timer = RequestTimer()
        try:
            response = self._respond(request)
        except Exception:
            self._metrics.record(
                CoreRequestMetric(outcome="error", duration_ms=timer.elapsed_ms())
            )
            raise

        self._metrics.record(
            CoreRequestMetric(
                outcome="success",
                duration_ms=timer.elapsed_ms(),
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                tool_iterations=max(0, int(response.metadata.get("tool_iterations") or 0)),
            )
        )
        return response

    def _respond(self, request: ConversationRequest) -> ConversationResponse:
        conversation_id = str(request.metadata.get("conversation_id") or "").strip()
        stored_memory = self._memory_store.load(conversation_id) if conversation_id else {}
        effective_memory = {**stored_memory, **dict(request.memory)}
        available_tools = self._tools.names()

        if stored_memory or available_tools:
            effective_request = replace(
                request,
                memory=effective_memory,
                metadata={
                    **dict(request.metadata),
                    "available_tools": available_tools,
                    "tool_definitions": self._tools.definitions(),
                },
            )
        else:
            effective_request = request

        response = self._run_provider_tool_loop(effective_request)

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

    def _run_provider_tool_loop(
        self, request: ConversationRequest
    ) -> ConversationResponse:
        current_request = request
        seen_calls: set[str] = set()
        tool_results: list[dict] = []
        tool_failures = 0

        for iteration in range(self._max_tool_iterations + 1):
            response = self._provider.generate(current_request)
            if not isinstance(response, ConversationResponse):
                raise TypeError("O provedor deve retornar ConversationResponse.")

            calls = self._extract_tool_calls(response)
            if not calls:
                if tool_results:
                    return replace(
                        response,
                        metadata={
                            **dict(response.metadata),
                            "tool_iterations": iteration,
                            "tool_results": tuple(tool_results),
                            "tool_failures": tool_failures,
                        },
                    )
                return response

            if iteration >= self._max_tool_iterations:
                raise RuntimeError("Limite de iterações de ferramentas atingido.")

            iteration_results: list[dict] = []
            for call in calls:
                signature = self._tool_call_signature(call)
                if signature in seen_calls:
                    raise RuntimeError(
                        f"Chamada repetida de ferramenta bloqueada: {call.name}"
                    )
                seen_calls.add(signature)

                try:
                    result = self._tools.execute(call)
                    serialized = {
                        "name": result.name,
                        "output": dict(result.output),
                        "call_id": result.call_id,
                        "status": "success",
                    }
                except Exception as exc:
                    tool_failures += 1
                    serialized = {
                        "name": call.name,
                        "output": {
                            "error": {
                                "type": type(exc).__name__,
                                "message": str(exc) or "Falha ao executar ferramenta.",
                            }
                        },
                        "call_id": call.call_id,
                        "status": "error",
                    }

                tool_results.append(serialized)
                iteration_results.append(serialized)

            current_request = replace(
                current_request,
                metadata={
                    **dict(current_request.metadata),
                    "tool_results": tuple(tool_results),
                    "last_tool_results": tuple(iteration_results),
                    "tool_iteration": iteration + 1,
                    "tool_failures": tool_failures,
                    "previous_response_id": response.metadata.get("response_id"),
                },
            )

        raise RuntimeError("Ciclo de ferramentas terminou em estado inválido.")

    @staticmethod
    def _extract_tool_calls(response: ConversationResponse) -> tuple[ToolCall, ...]:
        raw_calls = response.metadata.get("tool_calls") or ()
        calls: list[ToolCall] = []
        for raw in raw_calls:
            if isinstance(raw, ToolCall):
                calls.append(raw)
                continue
            if not isinstance(raw, dict):
                raise TypeError("Cada chamada de ferramenta deve ser ToolCall ou dicionário.")
            name = str(raw.get("name") or "").strip()
            arguments = raw.get("arguments") or {}
            call_id = str(raw.get("call_id") or "").strip() or None
            if not name:
                raise ValueError("Chamada de ferramenta sem nome.")
            if not isinstance(arguments, dict):
                raise TypeError("Os argumentos da ferramenta devem ser um dicionário.")
            calls.append(ToolCall(name=name, arguments=dict(arguments), call_id=call_id))
        return tuple(calls)

    @staticmethod
    def _tool_call_signature(call: ToolCall) -> str:
        return f"{call.name}:{json.dumps(call.arguments, ensure_ascii=False, sort_keys=True)}"
