from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.domnai_core.attachments import AttachmentPreparer
from app.domnai_core.contracts import ConversationRequest, ConversationResponse


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    pass


class OpenAIResponsesProvider:
    """Adaptador independente para a Responses API, sem importar o backend legado."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 45.0,
        attachment_preparer: AttachmentPreparer | None = None,
    ) -> None:
        self._api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self._model = (model or os.getenv("DOMNAI_CORE_MODEL", "gpt-4.1-mini")).strip()
        self._timeout_seconds = timeout_seconds
        self._attachment_preparer = attachment_preparer or AttachmentPreparer()

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        if not self._api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY não configurada para o novo núcleo.")

        instructions = (
            "Você é o DomnAI. Converse de forma natural, direta e contextual. "
            "A operação selecionada é apenas contexto e nunca um roteiro obrigatório. "
            "Não prometa executar ações que não foram realmente disponibilizadas."
        )
        if request.operation:
            instructions += f"\nContexto opcional selecionado pelo usuário: {request.operation}."
        if request.memory:
            instructions += "\nMemória disponível:\n" + json.dumps(
                request.memory, ensure_ascii=False, separators=(",", ":")
            )

        input_items = [
            {"role": item.role, "content": item.content}
            for item in request.history
            if item.role in {"user", "assistant", "system"}
        ]

        user_content: list[dict] = [{"type": "input_text", "text": request.message}]
        prepared_attachments = self._attachment_preparer.prepare(request.attachments)
        user_content.extend(item.content_item for item in prepared_attachments)
        input_items.append({"role": "user", "content": user_content})

        payload = {
            "model": self._model,
            "instructions": instructions,
            "input": input_items,
            "temperature": 0.2,
            "max_output_tokens": 2200,
        }
        http_request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderRequestError(f"OpenAI respondeu HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderRequestError(f"Falha ao consultar a OpenAI: {exc}") from exc

        text = str(data.get("output_text") or "").strip()
        if not text:
            parts: list[str] = []
            for output in data.get("output") or []:
                for content in output.get("content") or []:
                    if content.get("type") == "output_text" and content.get("text"):
                        parts.append(str(content["text"]).strip())
            text = "\n".join(part for part in parts if part).strip()
        if not text:
            raise ProviderRequestError("A OpenAI não retornou texto.")

        usage = data.get("usage") or {}
        details = usage.get("input_tokens_details") or {}
        return ConversationResponse(
            text=text,
            provider="openai-responses",
            model=self._model,
            input_tokens=max(0, int(usage.get("input_tokens") or 0)),
            output_tokens=max(0, int(usage.get("output_tokens") or 0)),
            cached_input_tokens=max(0, int(details.get("cached_tokens") or 0)),
            metadata={
                "response_id": data.get("id"),
                "attachment_count": len(prepared_attachments),
            },
        )
