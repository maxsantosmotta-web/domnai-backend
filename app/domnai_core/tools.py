from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

_ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


class ToolPolicyError(RuntimeError):
    pass


class ToolTimeoutError(TimeoutError):
    pass


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
    duration_ms: float = 0.0
    risk_level: str = "low"


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    risk_level: str = "low"
    timeout_seconds: float = 3.0
    max_calls_per_turn: int = 4

    def __post_init__(self) -> None:
        normalized = self.risk_level.strip().lower()
        if normalized not in _ALLOWED_RISK_LEVELS:
            raise ValueError("risk_level deve ser low, medium ou high.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds deve ser maior que zero.")
        if self.max_calls_per_turn < 1:
            raise ValueError("max_calls_per_turn deve ser maior que zero.")
        object.__setattr__(self, "risk_level", normalized)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    strict: bool = True
    policy: ToolPolicy = ToolPolicy()

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
    """Registro explícito com política, timeout e execução controlada."""

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
        risk_level: str = "low",
        timeout_seconds: float = 3.0,
        max_calls_per_turn: int = 4,
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

        policy = ToolPolicy(
            risk_level=risk_level,
            timeout_seconds=float(timeout_seconds),
            max_calls_per_turn=int(max_calls_per_turn),
        )
        self._handlers[normalized] = handler
        self._definitions[normalized] = ToolDefinition(
            name=normalized,
            description=(description or f"Executa a ferramenta {normalized}.").strip(),
            parameters=dict(schema),
            strict=bool(strict),
            policy=policy,
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def definitions(self) -> tuple[dict, ...]:
        return tuple(
            self._definitions[name].as_openai_tool()
            for name in sorted(self._definitions)
        )

    def policy(self, name: str) -> ToolPolicy:
        definition = self._definitions.get(name)
        if definition is None:
            raise KeyError(f"Ferramenta não registrada: {name}")
        return definition.policy

    def policies(self) -> dict[str, ToolPolicy]:
        return {name: self._definitions[name].policy for name in sorted(self._definitions)}

    def execute(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.name)
        if handler is None:
            raise KeyError(f"Ferramenta não registrada: {call.name}")
        policy = self.policy(call.name)
        started = perf_counter()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"domnai-tool-{call.name}")
        future = executor.submit(handler, dict(call.arguments))
        try:
            output = future.result(timeout=policy.timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise ToolTimeoutError(
                f"Ferramenta {call.name} excedeu o timeout de {policy.timeout_seconds:g}s."
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        if not isinstance(output, dict):
            raise TypeError("A ferramenta deve retornar um dicionário.")
        duration_ms = max(0.0, (perf_counter() - started) * 1000)
        return ToolResult(
            name=call.name,
            output=output,
            call_id=call.call_id,
            duration_ms=duration_ms,
            risk_level=policy.risk_level,
        )
