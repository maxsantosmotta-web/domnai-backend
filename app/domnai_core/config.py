from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE_VALUES = {"1", "true", "yes", "on"}
_ALLOWED_RISKS = {"low", "medium", "high"}


@dataclass(frozen=True, slots=True)
class DomnAICoreSettings:
    enabled: bool
    use_postgres: bool
    ensure_schema: bool
    enable_builtin_tools: bool
    model: str
    timeout_seconds: float
    max_tool_iterations: int
    max_tool_calls_per_turn: int = 8
    allowed_tool_risks: tuple[str, ...] = ("low",)

    @classmethod
    def from_env(cls) -> "DomnAICoreSettings":
        timeout_seconds = _read_positive_float("DOMNAI_CORE_TIMEOUT_SECONDS", 45.0)
        max_tool_iterations = _read_non_negative_int("DOMNAI_CORE_MAX_TOOL_ITERATIONS", 3)
        max_tool_calls_per_turn = _read_positive_int("DOMNAI_CORE_MAX_TOOL_CALLS_PER_TURN", 8)
        model = os.getenv("DOMNAI_CORE_MODEL", "gpt-4.1-mini").strip()
        if not model:
            raise ValueError("DOMNAI_CORE_MODEL não pode ser vazio.")
        return cls(
            enabled=_read_bool("DOMNAI_CORE_PREVIEW_ENABLED", False),
            use_postgres=_read_bool("DOMNAI_CORE_USE_POSTGRES", False),
            ensure_schema=_read_bool("DOMNAI_CORE_ENSURE_SCHEMA", False),
            enable_builtin_tools=_read_bool("DOMNAI_CORE_ENABLE_BUILTIN_TOOLS", True),
            model=model,
            timeout_seconds=timeout_seconds,
            max_tool_iterations=max_tool_iterations,
            max_tool_calls_per_turn=max_tool_calls_per_turn,
            allowed_tool_risks=_read_risk_levels("DOMNAI_CORE_ALLOWED_TOOL_RISKS", ("low",)),
        )


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _read_positive_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{name} deve ser maior que zero.")
    return value


def _read_non_negative_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} não pode ser negativo.")
    return value


def _read_positive_int(name: str, default: int) -> int:
    value = _read_non_negative_int(name, default)
    if value < 1:
        raise ValueError(f"{name} deve ser maior que zero.")
    return value


def _read_risk_levels(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    values = tuple(dict.fromkeys(part.strip().lower() for part in raw.split(",") if part.strip()))
    if not values:
        raise ValueError(f"{name} deve conter ao menos um nível de risco.")
    invalid = [value for value in values if value not in _ALLOWED_RISKS]
    if invalid:
        raise ValueError(f"{name} contém níveis inválidos: {', '.join(invalid)}.")
    return values
