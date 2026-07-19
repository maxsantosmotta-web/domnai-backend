from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Callable

from app.domnai_core.composition import build_domnai_core_runtime
from app.domnai_core.contracts import ConversationRequest, HistoryMessage
from app.services.metered_brain import MeteredBrainResult

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class ControlledCutoverSettings:
    enabled: bool = False
    traffic_percent: int = 0
    require_shadow_approval: bool = True
    fallback_enabled: bool = True
    max_history_items: int = 100

    @classmethod
    def from_env(cls) -> "ControlledCutoverSettings":
        enabled = os.getenv("DOMNAI_CUTOVER_ENABLED", "false").strip().lower() in _TRUE_VALUES
        traffic_percent = int(os.getenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "0").strip() or "0")
        require_shadow_approval = (
            os.getenv("DOMNAI_CUTOVER_REQUIRE_SHADOW_APPROVAL", "true").strip().lower() in _TRUE_VALUES
        )
        fallback_enabled = os.getenv("DOMNAI_CUTOVER_FALLBACK_ENABLED", "true").strip().lower() in _TRUE_VALUES
        max_history_items = int(os.getenv("DOMNAI_CUTOVER_MAX_HISTORY_ITEMS", "100").strip() or "100")
        if not 0 <= traffic_percent <= 100:
            raise ValueError("DOMNAI_CUTOVER_TRAFFIC_PERCENT deve ficar entre 0 e 100.")
        if enabled and traffic_percent == 0:
            raise ValueError("Corte habilitado exige tráfego percentual maior que zero.")
        if not fallback_enabled and traffic_percent < 100:
            raise ValueError("Fallback só pode ser desativado com 100% do tráfego no novo núcleo.")
        if max_history_items < 1 or max_history_items > 300:
            raise ValueError("DOMNAI_CUTOVER_MAX_HISTORY_ITEMS deve ficar entre 1 e 300.")
        return cls(
            enabled=enabled,
            traffic_percent=traffic_percent,
            require_shadow_approval=require_shadow_approval,
            fallback_enabled=fallback_enabled,
            max_history_items=max_history_items,
        )

    def selects(self, *, user_id: str, request_id: str) -> bool:
        if not self.enabled or self.traffic_percent <= 0:
            return False
        digest = hashlib.sha256(f"{user_id}:{request_id}".encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % 100
        return bucket < self.traffic_percent


@dataclass(frozen=True, slots=True)
class CutoverDecision:
    selected: bool
    eligible: bool
    reason: str


@dataclass(frozen=True, slots=True)
class RoutedBrainResult:
    result: MeteredBrainResult
    route: str
    fallback_used: bool = False
    fallback_reason: str = ""


def evaluate_cutover_eligibility(
    *,
    settings: ControlledCutoverSettings,
    user_id: str,
    request_id: str,
    attachments: list[dict],
    local_artifact_followup: bool,
    shadow_approved: bool,
) -> CutoverDecision:
    if not settings.enabled:
        return CutoverDecision(False, False, "disabled")
    if settings.require_shadow_approval and not shadow_approved:
        return CutoverDecision(False, False, "shadow_not_approved")
    if attachments:
        return CutoverDecision(False, False, "attachments_not_supported")
    if local_artifact_followup:
        return CutoverDecision(False, False, "local_artifact_followup")
    selected = settings.selects(user_id=user_id, request_id=request_id)
    return CutoverDecision(selected, True, "selected" if selected else "outside_sample")


class ControlledCutoverRouter:
    def __init__(
        self,
        settings: ControlledCutoverSettings,
        *,
        candidate: Callable[[ConversationRequest], object] | None = None,
    ) -> None:
        self._settings = settings
        self._candidate = candidate or build_domnai_core_runtime().engine.respond

    def route(
        self,
        *,
        request_id: str,
        user_id: str,
        conversation_id: str,
        message: str,
        operation: str | None,
        history: list[dict],
        memory: dict | None,
        attachments: list[dict],
        local_artifact_followup: bool,
        shadow_approved: bool,
        legacy: Callable[[], MeteredBrainResult],
    ) -> RoutedBrainResult:
        decision = evaluate_cutover_eligibility(
            settings=self._settings,
            user_id=user_id,
            request_id=request_id,
            attachments=attachments,
            local_artifact_followup=local_artifact_followup,
            shadow_approved=shadow_approved,
        )
        if not decision.selected:
            return RoutedBrainResult(legacy(), route="legacy", fallback_reason=decision.reason)

        request = ConversationRequest(
            message=message,
            operation=operation,
            history=tuple(
                HistoryMessage(role=str(item.get("role") or "user"), content=str(item.get("content") or ""))
                for item in history[-self._settings.max_history_items :]
                if str(item.get("role") or "") in {"system", "user", "assistant", "tool"}
            ),
            memory=memory or {},
            metadata={
                "request_id": request_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "scoped_memory": True,
                "cutover": True,
            },
        )
        try:
            response = self._candidate(request)
            text = str(getattr(response, "text", "") or "").strip()
            if not text:
                raise RuntimeError("O novo núcleo retornou resposta vazia.")
            result = MeteredBrainResult(
                text=text,
                provider=str(getattr(response, "provider", "") or "domnai-core"),
                model=str(getattr(response, "model", "") or "unknown"),
                input_tokens=max(0, int(getattr(response, "input_tokens", 0) or 0)),
                output_tokens=max(0, int(getattr(response, "output_tokens", 0) or 0)),
                cached_input_tokens=max(0, int(getattr(response, "cached_input_tokens", 0) or 0)),
                diagnosis_state=memory or None,
                timings={"cutover_candidate": 1},
            )
            return RoutedBrainResult(result, route="new-core")
        except Exception as exc:
            if not self._settings.fallback_enabled:
                raise
            return RoutedBrainResult(
                legacy(),
                route="legacy",
                fallback_used=True,
                fallback_reason=type(exc).__name__,
            )
