from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE_VALUES = {"1", "true", "yes", "on"}
_ALLOWED_AUTH_MODES = {"clerk", "static"}


@dataclass(frozen=True, slots=True)
class ParallelApiSettings:
    enabled: bool = False
    auth_mode: str = "clerk"
    static_token: str = ""
    static_subject: str = "internal"
    scopes: tuple[str, ...] = ("domnai:status", "domnai:respond")

    @classmethod
    def from_env(cls) -> "ParallelApiSettings":
        auth_mode = os.getenv("DOMNAI_PARALLEL_API_AUTH_MODE", "clerk").strip().lower()
        if auth_mode not in _ALLOWED_AUTH_MODES:
            raise ValueError("DOMNAI_PARALLEL_API_AUTH_MODE deve ser clerk ou static.")
        scopes = tuple(
            dict.fromkeys(
                part.strip().lower()
                for part in os.getenv(
                    "DOMNAI_PARALLEL_API_SCOPES",
                    "domnai:status,domnai:respond",
                ).split(",")
                if part.strip()
            )
        )
        if not scopes:
            raise ValueError("DOMNAI_PARALLEL_API_SCOPES deve conter ao menos um escopo.")
        static_token = os.getenv("DOMNAI_PARALLEL_API_STATIC_TOKEN", "").strip()
        enabled = os.getenv("DOMNAI_PARALLEL_API_ENABLED", "false").strip().lower() in _TRUE_VALUES
        if enabled and auth_mode == "static" and not static_token:
            raise ValueError(
                "DOMNAI_PARALLEL_API_STATIC_TOKEN é obrigatório quando a API paralela usa modo static."
            )
        return cls(
            enabled=enabled,
            auth_mode=auth_mode,
            static_token=static_token,
            static_subject=os.getenv("DOMNAI_PARALLEL_API_STATIC_SUBJECT", "internal").strip() or "internal",
            scopes=scopes,
        )
