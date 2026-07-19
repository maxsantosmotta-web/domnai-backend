from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import Callable, Protocol

from app.domnai_core.composition import build_domnai_core_runtime
from app.domnai_core.config import DomnAICoreSettings
from app.domnai_core.contracts import ConversationRequest, HistoryMessage

logger = logging.getLogger("domnai.shadow_validation")
_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class ShadowValidationSettings:
    enabled: bool = False
    sample_percent: int = 0
    timeout_seconds: float = 45.0

    @classmethod
    def from_env(cls) -> "ShadowValidationSettings":
        enabled = os.getenv("DOMNAI_SHADOW_VALIDATION_ENABLED", "false").strip().lower() in _TRUE_VALUES
        raw_sample = os.getenv("DOMNAI_SHADOW_SAMPLE_PERCENT", "0").strip() or "0"
        raw_timeout = os.getenv("DOMNAI_SHADOW_TIMEOUT_SECONDS", "45").strip() or "45"
        sample_percent = int(raw_sample)
        timeout_seconds = float(raw_timeout)
        if not 0 <= sample_percent <= 100:
            raise ValueError("DOMNAI_SHADOW_SAMPLE_PERCENT deve ficar entre 0 e 100.")
        if timeout_seconds <= 0:
            raise ValueError("DOMNAI_SHADOW_TIMEOUT_SECONDS deve ser maior que zero.")
        if enabled and sample_percent == 0:
            raise ValueError("Shadow mode habilitado exige amostragem maior que zero.")
        return cls(enabled=enabled, sample_percent=sample_percent, timeout_seconds=timeout_seconds)

    def selects(self, key: str) -> bool:
        if not self.enabled or self.sample_percent <= 0:
            return False
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % 100
        return bucket < self.sample_percent


@dataclass(frozen=True, slots=True)
class ShadowComparison:
    request_id: str
    legacy_provider: str
    candidate_provider: str
    legacy_length: int
    candidate_length: int
    similarity_ratio: float
    candidate_empty: bool
    candidate_error: str = ""

    def as_safe_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "legacy_provider": self.legacy_provider,
            "candidate_provider": self.candidate_provider,
            "legacy_length": self.legacy_length,
            "candidate_length": self.candidate_length,
            "similarity_ratio": self.similarity_ratio,
            "candidate_empty": self.candidate_empty,
            "candidate_error": self.candidate_error,
        }


class ShadowComparisonSink(Protocol):
    def record(self, comparison: ShadowComparison) -> None:
        ...


class LoggingShadowComparisonSink:
    def record(self, comparison: ShadowComparison) -> None:
        logger.info("domnai_shadow_comparison %s", json.dumps(comparison.as_safe_dict(), ensure_ascii=False, sort_keys=True))


class InMemoryShadowComparisonSink:
    def __init__(self) -> None:
        self._items: list[ShadowComparison] = []
        self._lock = threading.RLock()

    def record(self, comparison: ShadowComparison) -> None:
        with self._lock:
            self._items.append(comparison)

    def items(self) -> tuple[ShadowComparison, ...]:
        with self._lock:
            return tuple(self._items)


def compare_responses(
    *,
    request_id: str,
    legacy_text: str,
    candidate_text: str,
    legacy_provider: str,
    candidate_provider: str,
    candidate_error: str = "",
) -> ShadowComparison:
    normalized_legacy = " ".join(legacy_text.split())
    normalized_candidate = " ".join(candidate_text.split())
    similarity = SequenceMatcher(None, normalized_legacy, normalized_candidate).ratio()
    return ShadowComparison(
        request_id=request_id,
        legacy_provider=legacy_provider,
        candidate_provider=candidate_provider,
        legacy_length=len(legacy_text),
        candidate_length=len(candidate_text),
        similarity_ratio=round(similarity, 4),
        candidate_empty=not bool(normalized_candidate),
        candidate_error=candidate_error[:200],
    )


class ShadowValidator:
    def __init__(
        self,
        settings: ShadowValidationSettings,
        *,
        sink: ShadowComparisonSink | None = None,
        candidate: Callable[[ConversationRequest], object] | None = None,
    ) -> None:
        self._settings = settings
        self._sink = sink or LoggingShadowComparisonSink()
        self._candidate = candidate or self._build_candidate()

    def should_run(self, *, user_id: str, request_id: str) -> bool:
        return self._settings.selects(f"{user_id}:{request_id}")

    def run(
        self,
        *,
        request_id: str,
        user_id: str,
        conversation_id: str,
        message: str,
        operation: str | None,
        history: list[dict],
        legacy_text: str,
        legacy_provider: str,
    ) -> ShadowComparison | None:
        if not self.should_run(user_id=user_id, request_id=request_id):
            return None
        request = ConversationRequest(
            message=message,
            operation=operation,
            history=tuple(
                HistoryMessage(role=str(item.get("role") or "user"), content=str(item.get("content") or ""))
                for item in history
                if str(item.get("role") or "") in {"system", "user", "assistant", "tool"}
            ),
            metadata={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "scoped_memory": False,
                "shadow_validation": True,
            },
        )
        try:
            response = self._candidate(request)
            candidate_text = str(getattr(response, "text", "") or "")
            candidate_provider = str(getattr(response, "provider", "") or "unknown")
            comparison = compare_responses(
                request_id=request_id,
                legacy_text=legacy_text,
                candidate_text=candidate_text,
                legacy_provider=legacy_provider,
                candidate_provider=candidate_provider,
            )
        except Exception as exc:
            comparison = compare_responses(
                request_id=request_id,
                legacy_text=legacy_text,
                candidate_text="",
                legacy_provider=legacy_provider,
                candidate_provider="error",
                candidate_error=type(exc).__name__,
            )
        self._sink.record(comparison)
        return comparison

    def _build_candidate(self) -> Callable[[ConversationRequest], object]:
        core = DomnAICoreSettings.from_env()
        isolated = replace(
            core,
            enabled=True,
            use_postgres=False,
            ensure_schema=False,
            enable_builtin_tools=False,
            timeout_seconds=self._settings.timeout_seconds,
        )
        runtime = build_domnai_core_runtime(isolated)
        return runtime.engine.respond


def schedule_shadow_validation(
    *,
    request_id: str,
    user_id: str,
    conversation_id: str,
    message: str,
    operation: str | None,
    history: list[dict],
    legacy_text: str,
    legacy_provider: str,
) -> bool:
    """Agenda comparação sem bloquear nem alterar a resposta entregue ao usuário."""
    try:
        settings = ShadowValidationSettings.from_env()
    except Exception:
        logger.exception("Configuração inválida de shadow validation; execução ignorada.")
        return False
    if not settings.selects(f"{user_id}:{request_id}"):
        return False

    def target() -> None:
        try:
            ShadowValidator(settings).run(
                request_id=request_id,
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                operation=operation,
                history=history,
                legacy_text=legacy_text,
                legacy_provider=legacy_provider,
            )
        except Exception:
            logger.exception("Falha isolada na validação shadow.")

    threading.Thread(target=target, name=f"domnai-shadow-{request_id[:8]}", daemon=True).start()
    return True
