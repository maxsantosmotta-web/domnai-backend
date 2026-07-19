from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class HistoryMessage:
    role: Role
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("HistoryMessage.content não pode ser vazio.")


@dataclass(frozen=True, slots=True)
class Attachment:
    name: str
    mime_type: str
    content: bytes

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Attachment.name não pode ser vazio.")
        if not self.mime_type.strip():
            raise ValueError("Attachment.mime_type não pode ser vazio.")


@dataclass(frozen=True, slots=True)
class ConversationRequest:
    message: str
    history: tuple[HistoryMessage, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    operation: str | None = None
    memory: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("ConversationRequest.message não pode ser vazio.")


@dataclass(frozen=True, slots=True)
class ConversationResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    memory_update: dict | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("ConversationResponse.text não pode ser vazio.")
        for field_name in ("input_tokens", "output_tokens", "cached_input_tokens"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} não pode ser negativo.")
