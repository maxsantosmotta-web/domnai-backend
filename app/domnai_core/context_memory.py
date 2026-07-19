from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable

from app.domnai_core.memory import MemoryStore

_ALLOWED_CATEGORIES = ("preferences", "decisions", "corrections", "restrictions", "facts")
_MAX_ITEMS_PER_CATEGORY = 50
_MAX_VALUE_LENGTH = 1000
_MAX_SUMMARY_LENGTH = 4000


@dataclass(frozen=True, slots=True)
class MemoryScope:
    user_id: str = ""
    conversation_id: str = ""

    @property
    def user_key(self) -> str:
        return f"user:{self.user_id.strip()}" if self.user_id.strip() else ""

    @property
    def conversation_key(self) -> str:
        return f"conversation:{self.conversation_id.strip()}" if self.conversation_id.strip() else ""


class ContextMemoryManager:
    """Combina memória durável do usuário com memória específica da conversa.

    Apenas categorias explícitas são promovidas para memória estruturada. Fatos só
    são aceitos quando marcados como informados pelo usuário, evitando transformar
    inferências do modelo em verdades persistentes.
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def load(self, scope: MemoryScope) -> dict:
        user_memory = self._store.load(scope.user_key) if scope.user_key else {}
        conversation_memory = self._store.load(scope.conversation_key) if scope.conversation_key else {}
        return self.compose(user_memory, conversation_memory)

    def apply_update(self, scope: MemoryScope, update: dict | None) -> dict:
        if not update:
            return self.load(scope)
        normalized = self.normalize_update(update)
        if scope.user_key:
            current_user = self._store.load(scope.user_key)
            next_user = self._merge_profile(current_user, normalized.get("user", {}))
            self._store.save(scope.user_key, next_user)
        if scope.conversation_key:
            current_conversation = self._store.load(scope.conversation_key)
            next_conversation = self._merge_profile(
                current_conversation, normalized.get("conversation", {})
            )
            self._store.save(scope.conversation_key, next_conversation)
        return self.load(scope)

    @staticmethod
    def compose(user_memory: dict, conversation_memory: dict) -> dict:
        return {
            "user": deepcopy(user_memory),
            "conversation": deepcopy(conversation_memory),
            "context_summary": str(conversation_memory.get("summary") or ""),
        }

    @classmethod
    def normalize_update(cls, update: dict) -> dict:
        if not isinstance(update, dict):
            raise TypeError("memory_update deve ser um dicionário.")
        result = {"user": {}, "conversation": {}}
        for scope_name in ("user", "conversation"):
            raw_scope = update.get(scope_name) or {}
            if not isinstance(raw_scope, dict):
                raise TypeError(f"memory_update.{scope_name} deve ser um dicionário.")
            normalized_scope: dict = {}
            for category in _ALLOWED_CATEGORIES:
                raw_items = raw_scope.get(category) or []
                if not isinstance(raw_items, (list, tuple)):
                    raise TypeError(f"{scope_name}.{category} deve ser uma lista.")
                items = cls._normalize_items(raw_items, category=category)
                if items:
                    normalized_scope[category] = items
            if scope_name == "conversation" and "summary" in raw_scope:
                summary = str(raw_scope.get("summary") or "").strip()
                normalized_scope["summary"] = summary[:_MAX_SUMMARY_LENGTH]
            result[scope_name] = normalized_scope
        return result

    @classmethod
    def summarize_history(cls, messages: Iterable[object], *, max_characters: int = 2500) -> str:
        if max_characters < 100:
            raise ValueError("max_characters deve ser pelo menos 100.")
        lines: list[str] = []
        for item in messages:
            role = str(getattr(item, "role", "") or "").strip()
            content = " ".join(str(getattr(item, "content", "") or "").split())
            if role and content:
                lines.append(f"{role}: {content}")
        if not lines:
            return ""
        selected: list[str] = []
        used = 0
        for line in reversed(lines):
            cost = len(line) + 1
            if selected and used + cost > max_characters:
                break
            selected.append(line[:max_characters])
            used += min(cost, max_characters)
        selected.reverse()
        return "\n".join(selected)[:max_characters]

    @classmethod
    def _normalize_items(cls, values: Iterable[object], *, category: str) -> list[dict]:
        normalized: list[dict] = []
        seen: set[str] = set()
        for raw in values:
            if isinstance(raw, str):
                item = {"value": raw.strip(), "source": "user"}
            elif isinstance(raw, dict):
                item = {
                    "value": str(raw.get("value") or "").strip(),
                    "source": str(raw.get("source") or "").strip().lower(),
                }
            else:
                raise TypeError(f"Item de memória em {category} deve ser texto ou objeto.")
            value = item["value"][:_MAX_VALUE_LENGTH]
            source = item["source"] or "unknown"
            if not value:
                continue
            if category == "facts" and source != "user":
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append({"value": value, "source": source})
            if len(normalized) >= _MAX_ITEMS_PER_CATEGORY:
                break
        return normalized

    @classmethod
    def _merge_profile(cls, current: dict, update: dict) -> dict:
        result = deepcopy(current) if isinstance(current, dict) else {}
        for category in _ALLOWED_CATEGORIES:
            incoming = update.get(category) or []
            if not incoming:
                continue
            existing = result.get(category) or []
            combined = cls._normalize_items([*existing, *incoming], category=category)
            result[category] = combined[-_MAX_ITEMS_PER_CATEGORY:]
        if "summary" in update:
            result["summary"] = str(update.get("summary") or "")[:_MAX_SUMMARY_LENGTH]
        return result
