from __future__ import annotations

import base64
from dataclasses import dataclass

from app.domnai_core.contracts import Attachment


class AttachmentValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedAttachment:
    name: str
    mime_type: str
    content_item: dict


class AttachmentPreparer:
    """Converte anexos do contrato interno para itens aceitos pelo provedor.

    Limites são aplicados antes de qualquer envio externo para proteger memória,
    custo e latência. O preparador não realiza rede nem persiste o conteúdo.
    """

    DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024
    DEFAULT_MAX_TOTAL_BYTES = 20 * 1024 * 1024
    DEFAULT_MAX_FILES = 5

    def __init__(
        self,
        *,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
        max_files: int = DEFAULT_MAX_FILES,
    ) -> None:
        self._max_file_bytes = max_file_bytes
        self._max_total_bytes = max_total_bytes
        self._max_files = max_files

    def prepare(self, attachments: tuple[Attachment, ...]) -> tuple[PreparedAttachment, ...]:
        if len(attachments) > self._max_files:
            raise AttachmentValidationError(
                f"Máximo de {self._max_files} anexos por solicitação."
            )

        total_bytes = sum(len(item.content) for item in attachments)
        if total_bytes > self._max_total_bytes:
            raise AttachmentValidationError("O tamanho total dos anexos excede o limite permitido.")

        prepared: list[PreparedAttachment] = []
        for attachment in attachments:
            size = len(attachment.content)
            if size == 0:
                raise AttachmentValidationError(f"O anexo {attachment.name} está vazio.")
            if size > self._max_file_bytes:
                raise AttachmentValidationError(
                    f"O anexo {attachment.name} excede o limite individual permitido."
                )

            encoded = base64.b64encode(attachment.content).decode("ascii")
            if attachment.mime_type.startswith("image/"):
                content_item = {
                    "type": "input_image",
                    "image_url": f"data:{attachment.mime_type};base64,{encoded}",
                }
            else:
                content_item = {
                    "type": "input_file",
                    "filename": attachment.name,
                    "file_data": encoded,
                }

            prepared.append(
                PreparedAttachment(
                    name=attachment.name,
                    mime_type=attachment.mime_type,
                    content_item=content_item,
                )
            )

        return tuple(prepared)
