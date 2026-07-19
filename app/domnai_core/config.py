from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class DomnAICoreSettings:
    enabled: bool
    use_postgres: bool
    ensure_schema: bool
    model: str
    timeout_seconds: float
    max_tool_iterations: int

    @classmethod
    def from_env(cls) -> "DomnAICoreSettings":
        timeout_seconds = _read_positive_float("DOMNAI_CORE_TIMEOUT_SECONDS", 45.0)
        max_tool_iterations = _read_non_negative_int("DOMNAI_CORE_MAX_TOOL_ITERATIONS", 3)
        model = os.getenv("DOMNAI_CORE_MODEL", "gpt-4.1-mini").strip()
        if not model:
            raise ValueError("DOMNAI_CORE_MODEL não pode ser vazio.")
        return cls(
            enabled=_read_bool("DOMNAI_CORE_PREVIEW_ENABLED", False),
            use_postgres=_read_bool("DOMNAI_CORE_USE_POSTGRES", False),
            ensure_schema=_read_bool("DOMNAI_CORE_ENSURE_SCHEMA", False),
            model=model,
            timeout_seconds=timeout_seconds,
            max_tool_iterations=max_tool_iterations,
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
