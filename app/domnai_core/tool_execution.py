from __future__ import annotations

from dataclasses import dataclass

from app.domnai_core.tools import ToolCall, ToolRegistry, ToolResult


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ToolExecutionReport:
    results: tuple[ToolResult, ...]
    executed: int


class ToolExecutor:
    """Executa chamadas previamente decididas com limite rígido e registro explícito."""

    def __init__(self, registry: ToolRegistry, *, max_calls: int = 4) -> None:
        if max_calls < 1:
            raise ValueError("max_calls deve ser maior que zero.")
        self._registry = registry
        self._max_calls = max_calls

    def execute(self, calls: tuple[ToolCall, ...]) -> ToolExecutionReport:
        if len(calls) > self._max_calls:
            raise ToolExecutionError(
                f"Limite de {self._max_calls} chamadas de ferramenta por turno excedido."
            )

        results: list[ToolResult] = []
        for call in calls:
            try:
                result = self._registry.execute(call)
            except (KeyError, TypeError, ValueError) as exc:
                raise ToolExecutionError(str(exc)) from exc
            results.append(result)

        return ToolExecutionReport(results=tuple(results), executed=len(results))
