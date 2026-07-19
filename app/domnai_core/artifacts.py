from __future__ import annotations

import csv
import hashlib
import io
import json
from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from time import time
from typing import Callable, Literal, Protocol
from uuid import uuid4

ArtifactOrigin = Literal["uploaded", "generated"]


class ArtifactValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: str
    name: str
    mime_type: str
    content: bytes
    origin: ArtifactOrigin
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ArtifactValidationError("artifact_id não pode ser vazio.")
        if not self.name.strip():
            raise ArtifactValidationError("name não pode ser vazio.")
        if not self.mime_type.strip():
            raise ArtifactValidationError("mime_type não pode ser vazio.")
        if self.origin not in {"uploaded", "generated"}:
            raise ArtifactValidationError("origin deve ser uploaded ou generated.")
        if not self.content:
            raise ArtifactValidationError("content não pode ser vazio.")

    @property
    def size_bytes(self) -> int:
        return len(self.content)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    def summary(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "mime_type": self.mime_type,
            "origin": self.origin,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "metadata": deepcopy(self.metadata),
        }


class ArtifactStore(Protocol):
    def save(self, artifact: Artifact) -> None:
        ...

    def get(self, artifact_id: str) -> Artifact | None:
        ...

    def list(self, *, owner_id: str = "", origin: ArtifactOrigin | None = None) -> tuple[Artifact, ...]:
        ...


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, Artifact] = {}
        self._lock = RLock()

    def save(self, artifact: Artifact) -> None:
        with self._lock:
            self._items[artifact.artifact_id] = artifact

    def get(self, artifact_id: str) -> Artifact | None:
        with self._lock:
            return self._items.get(artifact_id)

    def list(self, *, owner_id: str = "", origin: ArtifactOrigin | None = None) -> tuple[Artifact, ...]:
        normalized_owner = owner_id.strip()
        with self._lock:
            values = tuple(self._items.values())
        return tuple(
            item
            for item in values
            if (not normalized_owner or str(item.metadata.get("owner_id") or "") == normalized_owner)
            and (origin is None or item.origin == origin)
        )


class ArtifactService:
    """Criação, leitura e armazenamento de artefatos locais sem efeitos externos."""

    DEFAULT_MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
    DEFAULT_MAX_TEXT_CHARACTERS = 200_000
    _GENERATED_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
    _BINARY_GENERATED_MIME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    _READABLE_MIME_TYPES = _GENERATED_MIME_TYPES | {
        "text/html",
        "application/xml",
        "text/xml",
    }

    def __init__(
        self,
        store: ArtifactStore,
        *,
        max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
        max_text_characters: int = DEFAULT_MAX_TEXT_CHARACTERS,
        now_provider: Callable[[], float] = time,
    ) -> None:
        if max_artifact_bytes < 1:
            raise ValueError("max_artifact_bytes deve ser maior que zero.")
        if max_text_characters < 1:
            raise ValueError("max_text_characters deve ser maior que zero.")
        self._store = store
        self._max_artifact_bytes = max_artifact_bytes
        self._max_text_characters = max_text_characters
        self._now_provider = now_provider

    def register_uploaded(
        self,
        *,
        name: str,
        mime_type: str,
        content: bytes,
        owner_id: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        artifact = self._build_artifact(
            name=name,
            mime_type=mime_type,
            content=content,
            origin="uploaded",
            owner_id=owner_id,
            metadata=metadata,
        )
        self._store.save(artifact)
        return artifact

    def register_generated_binary(
        self,
        *,
        name: str,
        mime_type: str,
        content: bytes,
        owner_id: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        normalized_mime = mime_type.strip().lower()
        safe_metadata = deepcopy(metadata) if isinstance(metadata, dict) else {}
        if normalized_mime not in self._BINARY_GENERATED_MIME_TYPES:
            raise ArtifactValidationError(f"Geração binária não suportada para {normalized_mime}.")
        if safe_metadata.get("generation_authorized") is not True:
            raise PermissionError("Artefato binário sem autorização explícita registrada.")
        artifact = self._build_artifact(
            name=name,
            mime_type=normalized_mime,
            content=content,
            origin="generated",
            owner_id=owner_id,
            metadata=safe_metadata,
        )
        self._store.save(artifact)
        return artifact

    def generate_text(
        self,
        *,
        name: str,
        text: str,
        mime_type: str = "text/plain",
        owner_id: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        normalized_mime = mime_type.strip().lower()
        if normalized_mime not in self._GENERATED_MIME_TYPES:
            raise ArtifactValidationError(f"Geração não suportada para {normalized_mime}.")
        if len(text) > self._max_text_characters:
            raise ArtifactValidationError("O texto excede o limite permitido.")
        content = text.encode("utf-8")
        artifact = self._build_artifact(
            name=name,
            mime_type=normalized_mime,
            content=content,
            origin="generated",
            owner_id=owner_id,
            metadata=metadata,
        )
        self._store.save(artifact)
        return artifact

    def generate_json(
        self,
        *,
        name: str,
        data: object,
        owner_id: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        return self.generate_text(
            name=name,
            text=text,
            mime_type="application/json",
            owner_id=owner_id,
            metadata=metadata,
        )

    def generate_csv(
        self,
        *,
        name: str,
        rows: list[dict],
        owner_id: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        if not rows:
            raise ArtifactValidationError("rows não pode ser vazio.")
        if any(not isinstance(row, dict) for row in rows):
            raise TypeError("Cada linha CSV deve ser um dicionário.")
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                normalized = str(key)
                if normalized not in fieldnames:
                    fieldnames.append(normalized)
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({str(key): value for key, value in row.items()})
        return self.generate_text(
            name=name,
            text=output.getvalue(),
            mime_type="text/csv",
            owner_id=owner_id,
            metadata=metadata,
        )

    def read_text(self, artifact_id: str, *, owner_id: str = "") -> str:
        artifact = self._require_access(artifact_id, owner_id=owner_id)
        if artifact.mime_type.lower() not in self._READABLE_MIME_TYPES:
            raise ArtifactValidationError(
                f"Leitura textual não suportada para {artifact.mime_type}."
            )
        try:
            text = artifact.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArtifactValidationError("O artefato não contém UTF-8 válido.") from exc
        if len(text) > self._max_text_characters:
            raise ArtifactValidationError("O conteúdo textual excede o limite permitido.")
        return text

    def get(self, artifact_id: str, *, owner_id: str = "") -> Artifact:
        return self._require_access(artifact_id, owner_id=owner_id)

    def list_summaries(
        self,
        *,
        owner_id: str = "",
        origin: ArtifactOrigin | None = None,
    ) -> tuple[dict, ...]:
        return tuple(
            item.summary()
            for item in self._store.list(owner_id=owner_id, origin=origin)
            if not self._is_expired(item)
        )

    def _require_access(self, artifact_id: str, *, owner_id: str) -> Artifact:
        normalized_id = artifact_id.strip()
        if not normalized_id:
            raise ArtifactValidationError("artifact_id não pode ser vazio.")
        artifact = self._store.get(normalized_id)
        if artifact is None or self._is_expired(artifact):
            raise KeyError(f"Artefato não encontrado: {normalized_id}")
        normalized_owner = owner_id.strip()
        stored_owner = str(artifact.metadata.get("owner_id") or "")
        if normalized_owner and stored_owner and stored_owner != normalized_owner:
            raise PermissionError("Artefato pertence a outro usuário.")
        return artifact

    def _is_expired(self, artifact: Artifact) -> bool:
        expires_at = artifact.metadata.get("expires_at")
        if expires_at is None:
            return False
        try:
            return float(expires_at) <= float(self._now_provider())
        except (TypeError, ValueError) as exc:
            raise ArtifactValidationError("expires_at do artefato deve ser numérico.") from exc

    def _build_artifact(
        self,
        *,
        name: str,
        mime_type: str,
        content: bytes,
        origin: ArtifactOrigin,
        owner_id: str,
        metadata: dict | None,
    ) -> Artifact:
        normalized_name = name.strip()
        normalized_mime = mime_type.strip().lower()
        if not normalized_name:
            raise ArtifactValidationError("name não pode ser vazio.")
        if not normalized_mime:
            raise ArtifactValidationError("mime_type não pode ser vazio.")
        if not content:
            raise ArtifactValidationError("content não pode ser vazio.")
        if len(content) > self._max_artifact_bytes:
            raise ArtifactValidationError("O artefato excede o limite permitido.")
        safe_metadata = deepcopy(metadata) if isinstance(metadata, dict) else {}
        normalized_owner = owner_id.strip()
        if normalized_owner:
            safe_metadata["owner_id"] = normalized_owner
        return Artifact(
            artifact_id=uuid4().hex,
            name=normalized_name,
            mime_type=normalized_mime,
            content=bytes(content),
            origin=origin,
            metadata=safe_metadata,
        )
