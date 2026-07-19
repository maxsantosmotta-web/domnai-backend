from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Literal

from app.domnai_core.artifacts import Artifact, ArtifactService, ArtifactValidationError
from app.domnai_core.binary_artifacts import ArtifactGenerationAuthorization, BinaryArtifactService

ArtifactFormat = Literal["txt", "md", "json", "csv", "pdf", "xlsx"]


@dataclass(frozen=True, slots=True)
class ArtifactIntent:
    """Contrato explícito de intenção para impedir geração automática indevida."""

    format: ArtifactFormat
    name: str
    payload: object
    explicitly_requested: bool = False
    contextually_accepted: bool = False
    authorization_source: str = ""
    retention_seconds: int | None = None
    library_visible: bool = True

    def __post_init__(self) -> None:
        if self.format not in {"txt", "md", "json", "csv", "pdf", "xlsx"}:
            raise ArtifactValidationError(f"Formato de artefato não suportado: {self.format}")
        if not self.name.strip():
            raise ArtifactValidationError("O nome do artefato não pode ser vazio.")
        if self.retention_seconds is not None and self.retention_seconds < 60:
            raise ArtifactValidationError("A retenção deve ser de pelo menos 60 segundos.")

    @property
    def authorization(self) -> ArtifactGenerationAuthorization:
        return ArtifactGenerationAuthorization(
            explicitly_requested=self.explicitly_requested,
            contextually_accepted=self.contextually_accepted,
            source=self.authorization_source,
        )

    @property
    def authorized(self) -> bool:
        return self.authorization.authorized

    @classmethod
    def from_metadata(cls, value: object) -> ArtifactIntent | None:
        if value in (None, {}, False):
            return None
        if not isinstance(value, dict):
            raise TypeError("artifact_intent deve ser um dicionário.")
        return cls(
            format=str(value.get("format") or "").strip().lower(),
            name=str(value.get("name") or "").strip(),
            payload=value.get("payload"),
            explicitly_requested=bool(value.get("explicitly_requested")),
            contextually_accepted=bool(value.get("contextually_accepted")),
            authorization_source=str(value.get("authorization_source") or "").strip(),
            retention_seconds=(
                int(value["retention_seconds"])
                if value.get("retention_seconds") is not None
                else None
            ),
            library_visible=bool(value.get("library_visible", True)),
        )


class ArtifactCoordinator:
    """Integra intenção, geração, retenção e visão de Biblioteca sem publicar arquivos."""

    def __init__(
        self,
        artifacts: ArtifactService,
        *,
        binary: BinaryArtifactService | None = None,
        now_provider=time,
    ) -> None:
        self._artifacts = artifacts
        self._binary = binary or BinaryArtifactService(artifacts)
        self._now_provider = now_provider

    def execute(self, intent: ArtifactIntent, *, owner_id: str = "", conversation_id: str = "") -> Artifact:
        intent.authorization.require()
        metadata = {
            "conversation_id": conversation_id.strip(),
            "library_visible": intent.library_visible,
            "artifact_flow": "conversation_engine",
        }
        if intent.retention_seconds is not None:
            metadata["expires_at"] = float(self._now_provider()) + intent.retention_seconds

        if intent.format == "pdf":
            if not isinstance(intent.payload, str):
                raise TypeError("O conteúdo do PDF deve ser texto.")
            return self._binary.generate_pdf(
                name=intent.name,
                text=intent.payload,
                authorization=intent.authorization,
                owner_id=owner_id,
                metadata=metadata,
            )
        if intent.format == "xlsx":
            if not isinstance(intent.payload, (list, tuple)):
                raise TypeError("Os dados do XLSX devem ser uma lista de objetos.")
            return self._binary.generate_xlsx(
                name=intent.name,
                rows=intent.payload,
                authorization=intent.authorization,
                owner_id=owner_id,
                metadata=metadata,
            )
        if intent.format == "json":
            return self._artifacts.generate_json(
                name=intent.name,
                data=intent.payload,
                owner_id=owner_id,
                metadata=_text_metadata(metadata, intent),
            )
        if intent.format == "csv":
            if not isinstance(intent.payload, list):
                raise TypeError("Os dados do CSV devem ser uma lista de objetos.")
            return self._artifacts.generate_csv(
                name=intent.name,
                rows=intent.payload,
                owner_id=owner_id,
                metadata=_text_metadata(metadata, intent),
            )
        if not isinstance(intent.payload, str):
            raise TypeError("O conteúdo textual deve ser texto.")
        mime_type = "text/markdown" if intent.format == "md" else "text/plain"
        return self._artifacts.generate_text(
            name=intent.name,
            text=intent.payload,
            mime_type=mime_type,
            owner_id=owner_id,
            metadata=_text_metadata(metadata, intent),
        )

    def library_entries(self, *, owner_id: str) -> tuple[dict, ...]:
        entries = []
        for summary in self._artifacts.list_summaries(owner_id=owner_id):
            metadata = dict(summary.get("metadata") or {})
            if not metadata.get("library_visible", True):
                continue
            entries.append(
                {
                    **summary,
                    "conversation_id": str(metadata.get("conversation_id") or ""),
                    "library_status": "available",
                }
            )
        return tuple(entries)


def _text_metadata(metadata: dict, intent: ArtifactIntent) -> dict:
    return {
        **metadata,
        "generation_authorized": True,
        "authorization_mode": (
            "explicit_request" if intent.explicitly_requested else "contextual_acceptance"
        ),
        "authorization_source": intent.authorization_source,
    }
