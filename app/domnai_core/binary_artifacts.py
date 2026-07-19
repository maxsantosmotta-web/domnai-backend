from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.domnai_core.artifacts import Artifact, ArtifactService, ArtifactValidationError


@dataclass(frozen=True, slots=True)
class ArtifactGenerationAuthorization:
    """Prova explícita de que o usuário pediu ou aceitou gerar um arquivo."""

    explicitly_requested: bool = False
    contextually_accepted: bool = False
    source: str = ""

    @property
    def authorized(self) -> bool:
        return self.explicitly_requested or self.contextually_accepted

    def require(self) -> None:
        if not self.authorized:
            raise PermissionError(
                "A geração de arquivo exige pedido explícito ou aceite contextual confirmado."
            )


class BinaryArtifactService:
    """Gera binários locais somente após autorização explícita e os persiste no ArtifactService."""

    def __init__(self, artifacts: ArtifactService) -> None:
        self._artifacts = artifacts

    def generate_pdf(
        self,
        *,
        name: str,
        text: str,
        authorization: ArtifactGenerationAuthorization,
        owner_id: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        authorization.require()
        if not text.strip():
            raise ArtifactValidationError("O conteúdo do PDF não pode ser vazio.")

        output = io.BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        story = []
        for block in text.splitlines():
            normalized = block.strip()
            if normalized:
                story.append(Paragraph(_escape_reportlab(normalized), styles["BodyText"]))
            else:
                story.append(Spacer(1, 4 * mm))
        document.build(story or [Paragraph(" ", styles["BodyText"])])

        return self._artifacts.register_generated_binary(
            name=name,
            mime_type="application/pdf",
            content=output.getvalue(),
            owner_id=owner_id,
            metadata=_authorized_metadata(metadata, authorization),
        )

    def generate_xlsx(
        self,
        *,
        name: str,
        rows: Iterable[dict],
        authorization: ArtifactGenerationAuthorization,
        owner_id: str = "",
        metadata: dict | None = None,
        sheet_name: str = "Dados",
    ) -> Artifact:
        authorization.require()
        normalized_rows = list(rows)
        if not normalized_rows:
            raise ArtifactValidationError("Os dados do XLSX não podem ser vazios.")
        if any(not isinstance(row, dict) for row in normalized_rows):
            raise TypeError("Cada linha do XLSX deve ser um dicionário.")

        headers: list[str] = []
        for row in normalized_rows:
            for key in row:
                value = str(key)
                if value not in headers:
                    headers.append(value)
        if not headers:
            raise ArtifactValidationError("O XLSX precisa ter ao menos uma coluna.")

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = (sheet_name.strip() or "Dados")[:31]
        worksheet.append(headers)
        for row in normalized_rows:
            worksheet.append([_safe_cell_value(row.get(header)) for header in headers])

        output = io.BytesIO()
        workbook.save(output)
        workbook.close()

        return self._artifacts.register_generated_binary(
            name=name,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=output.getvalue(),
            owner_id=owner_id,
            metadata=_authorized_metadata(metadata, authorization),
        )


def _authorized_metadata(
    metadata: dict | None,
    authorization: ArtifactGenerationAuthorization,
) -> dict:
    result = dict(metadata or {})
    result["generation_authorized"] = True
    result["authorization_mode"] = (
        "explicit_request" if authorization.explicitly_requested else "contextual_acceptance"
    )
    if authorization.source.strip():
        result["authorization_source"] = authorization.source.strip()
    return result


def _escape_reportlab(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _safe_cell_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
