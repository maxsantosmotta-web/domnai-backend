from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    output: dict


ToolHandler = Callable[[dict], dict]


class ToolRegistry:
    """Registro explícito: nenhuma ferramenta é executada sem estar cadastrada."""

    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("O nome da ferramenta não pode ser vazio.")
        if normalized in self._handlers:
            raise ValueError(f"Ferramenta já registrada: {normalized}")
        self._handlers[normalized] = handler

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def execute(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.name)
        if handler is None:
            raise KeyError(f"Ferramenta não registrada: {call.name}")
        output = handler(dict(call.arguments))
        if not isinstance(output, dict):
            raise TypeError("A ferramenta deve retornar um dicionário.")
        return ToolResult(name=call.name, output=output)
