from __future__ import annotations

import json
from dataclasses import replace
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from app.domnai_core.contracts import ConversationRequest, ConversationResponse
from app.domnai_core.memory import MemoryStore, NullMemoryStore
from app.domnai_core.observability import CoreMetricsSink, CoreRequestMetric, NullCoreMetricsSink, RequestTimer
from app.domnai_core.persistence import ConversationRecord, ConversationRepository, NullConversationRepository
from app.domnai_core.tools import ToolCall, ToolPolicyError, ToolRegistry


class ModelProvider(Protocol):
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
        max_tool_calls_per_turn: int = 8,
        allowed_tool_risks: tuple[str, ...] = ("low",),
        metrics: CoreMetricsSink | None = None,
    ) -> None:
        if max_tool_iterations < 0:
            raise ValueError("max_tool_iterations não pode ser negativo.")
        if max_tool_calls_per_turn < 1:
            raise ValueError("max_tool_calls_per_turn deve ser maior que zero.")
        normalized_risks = tuple(dict.fromkeys(value.strip().lower() for value in allowed_tool_risks))
        if not normalized_risks:
            raise ValueError("allowed_tool_risks deve conter ao menos um nível.")
        if any(value not in {"low", "medium", "high"} for value in normalized_risks):
            raise ValueError("allowed_tool_risks contém nível inválido.")
        self._provider = provider
        self._memory_store = memory_store or NullMemoryStore()
        self._repository = repository or NullConversationRepository()
        self._tools = tools or ToolRegistry()
        self._max_tool_iterations = max_tool_iterations
        self._max_tool_calls_per_turn = max_tool_calls_per_turn
        self._allowed_tool_risks = normalized_risks
        self._metrics = metrics or NullCoreMetricsSink()

    def respond(self, request: ConversationRequest) -> ConversationResponse:
        timer = RequestTimer()
        try:
            response = self._respond(request)
        except Exception:
            self._metrics.record(CoreRequestMetric(outcome="error", duration_ms=timer.elapsed_ms()))
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
        request_id = str(request.metadata.get("request_id") or "").strip() or uuid4().hex
        conversation_id = str(request.metadata.get("conversation_id") or "").strip()
        stored_memory = self._memory_store.load(conversation_id) if conversation_id else {}
        effective_memory = {**stored_memory, **dict(request.memory)}
        available_tools = self._tools.names()
        enriched_metadata = {**dict(request.metadata), "request_id": request_id}
        if stored_memory or available_tools or enriched_metadata != dict(request.metadata):
            effective_request = replace(
                request,
                memory=effective_memory,
                metadata={
                    **enriched_metadata,
                    "available_tools": available_tools,
                    "tool_definitions": self._tools.definitions(),
                },
            )
        else:
            effective_request = request

        response = self._run_provider_tool_loop(effective_request)
        response = replace(response, metadata={**dict(response.metadata), "request_id": request_id})
        if conversation_id and response.memory_update is not None:
            next_memory = {**dict(effective_request.memory), **dict(response.memory_update)}
            self._memory_store.save(conversation_id, next_memory)
        self._repository.append(
            ConversationRecord(conversation_id=conversation_id, request=effective_request, response=response)
        )
        return response

    def _run_provider_tool_loop(self, request: ConversationRequest) -> ConversationResponse:
        current_request = request
        request_id = str(request.metadata.get("request_id") or "")
        seen_calls: set[str] = set()
        tool_results: list[dict] = []
        tool_trace: list[dict] = []
        tool_failures = 0
        call_counts: dict[str, int] = {}
        total_calls = 0

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
                            "request_id": request_id,
                            "tool_iterations": iteration,
                            "tool_results": tuple(tool_results),
                            "tool_trace": tuple(tool_trace),
                            "tool_failures": tool_failures,
                            "tool_calls_executed": total_calls,
                        },
                    )
                return replace(response, metadata={**dict(response.metadata), "request_id": request_id})
            if iteration >= self._max_tool_iterations:
                raise RuntimeError("Limite de iterações de ferramentas atingido.")
            if total_calls + len(calls) > self._max_tool_calls_per_turn:
                raise RuntimeError(
                    f"Limite de {self._max_tool_calls_per_turn} chamadas de ferramenta por turno atingido."
                )

            iteration_results: list[dict] = []
            for call in calls:
                signature = self._tool_call_signature(call)
                if signature in seen_calls:
                    raise RuntimeError(f"Chamada repetida de ferramenta bloqueada: {call.name}")
                seen_calls.add(signature)
                total_calls += 1
                call_counts[call.name] = call_counts.get(call.name, 0) + 1
                started = perf_counter()
                risk_level = "unknown"
                try:
                    policy = self._tools.policy(call.name)
                    risk_level = policy.risk_level
                    if risk_level not in self._allowed_tool_risks:
                        raise ToolPolicyError(
                            f"Ferramenta {call.name} possui risco {risk_level} não autorizado."
                        )
                    if call_counts[call.name] > policy.max_calls_per_turn:
                        raise ToolPolicyError(
                            f"Ferramenta {call.name} excedeu o limite de {policy.max_calls_per_turn} chamadas por turno."
                        )
                    result = self._tools.execute(call)
                    serialized = {"name": result.name, "output": dict(result.output), "call_id": result.call_id}
                    trace_item = {
                        "request_id": request_id,
                        "sequence": total_calls,
                        "iteration": iteration + 1,
                        "name": result.name,
                        "call_id": result.call_id,
                        "status": "success",
                        "risk_level": result.risk_level,
                        "duration_ms": round(result.duration_ms, 3),
                    }
                except Exception as exc:
                    tool_failures += 1
                    serialized = {
                        "name": call.name,
                        "output": {"error": {"type": type(exc).__name__, "message": str(exc) or "Falha ao executar ferramenta."}},
                        "call_id": call.call_id,
                        "status": "error",
                    }
                    trace_item = {
                        "request_id": request_id,
                        "sequence": total_calls,
                        "iteration": iteration + 1,
                        "name": call.name,
                        "call_id": call.call_id,
                        "status": "error",
                        "risk_level": risk_level,
                        "duration_ms": round(max(0.0, (perf_counter() - started) * 1000), 3),
                        "error_type": type(exc).__name__,
                    }
                tool_results.append(serialized)
                iteration_results.append(serialized)
                tool_trace.append(trace_item)

            current_request = replace(
                current_request,
                metadata={
                    **dict(current_request.metadata),
                    "request_id": request_id,
                    "tool_results": tuple(tool_results),
                    "last_tool_results": tuple(iteration_results),
                    "tool_trace": tuple(tool_trace),
                    "tool_iteration": iteration + 1,
                    "tool_failures": tool_failures,
                    "tool_calls_executed": total_calls,
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
