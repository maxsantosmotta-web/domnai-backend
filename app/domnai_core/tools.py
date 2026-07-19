from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    output: dict
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    strict: bool = True

    def as_openai_tool(self) -> dict:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "strict": self.strict,
        }


ToolHandler = Callable[[dict], dict]


class ToolRegistry:
    """Registro explícito: nenhuma ferramenta é executada sem estar cadastrada."""

    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}
        self._definitions: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: ToolHandler,
        *,
        description: str | None = None,
        parameters: dict | None = None,
        strict: bool = True,
    ) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("O nome da ferramenta não pode ser vazio.")
        if normalized in self._handlers:
            raise ValueError(f"Ferramenta já registrada: {normalized}")

        schema = parameters or {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }
        if not isinstance(schema, dict):
            raise TypeError("O schema de parâmetros da ferramenta deve ser um dicionário.")

        self._handlers[normalized] = handler
        self._definitions[normalized] = ToolDefinition(
            name=normalized,
            description=(description or f"Executa a ferramenta {normalized}.").strip(),
            parameters=dict(schema),
            strict=bool(strict),
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def definitions(self) -> tuple[dict, ...]:
        return tuple(
            self._definitions[name].as_openai_tool()
            for name in sorted(self._definitions)
        )

    def execute(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.name)
        if handler is None:
            raise KeyError(f"Ferramenta não registrada: {call.name}")
        output = handler(dict(call.arguments))
        if not isinstance(output, dict):
            raise TypeError("A ferramenta deve retornar um dicionário.")
        return ToolResult(name=call.name, output=output, call_id=call.call_id)
