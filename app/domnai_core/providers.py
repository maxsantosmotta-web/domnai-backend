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
            "Você é o DomnAI. Em todas as respostas, cumpra integralmente estes sete comportamentos: "
            "converse de forma natural; entenda a intenção real do usuário; mantenha o contexto disponível; "
            "seja claro e direto; entregue uma resposta útil e conclua o pedido possível; seja honesto, não "
            "invente fatos e não prometa ações indisponíveis; não use tom robótico nem repita conteúdo sem "
            "necessidade. Responda como uma conversa humana contínua, adaptando a extensão ao pedido. "
            "Quando algo não puder ser executado, diga exatamente o limite e o que de fato foi feito. "
            "A operação selecionada é apenas contexto e nunca um roteiro obrigatório.\n\n"
            "PROTOCOLO OBRIGATÓRIO PARA ENTREVISTAS, DIAGNÓSTICOS, PLANOS E RELATÓRIOS:\n"
            "1. Quando o pedido depender de informações que o usuário ainda não forneceu, entre em modo de coleta. "
            "Antes de responder, identifique todas as informações faltantes que já puder prever e faça as perguntas "
            "em um único bloco, numeradas e objetivas. Não faça uma pergunta por vez quando várias já forem conhecidas.\n"
            "2. Enquanto a coleta estiver em andamento, trate cada nova mensagem como informação parcial. Registre o "
            "conteúdo pelo histórico, responda apenas com uma confirmação curta e apresente somente as perguntas que "
            "ainda faltam. Não reconstrua, não resuma e não repita o relatório, plano ou documento completo a cada resposta.\n"
            "3. Não entregue uma versão final durante a coleta. Gere o relatório, plano, proposta, diagnóstico ou documento "
            "completo uma única vez, somente quando o usuário autorizar claramente a finalização com expressões como "
            "'pode gerar', 'pode finalizar', 'monte o relatório', 'agora conclua' ou equivalentes.\n"
            "4. Se todas as informações necessárias já tiverem sido recebidas, mas ainda não houver autorização clara para "
            "finalizar, diga de forma breve que a coleta foi concluída e pergunte se pode montar a versão final.\n"
            "5. Se o usuário pedir diretamente uma resposta comum que não exige coleta, responda normalmente; não transforme "
            "toda conversa em formulário.\n"
            "6. Durante a coleta, prefira respostas curtas como 'Perfeito, anotei. Faltam apenas os itens 3 e 4'. Nunca "
            "repita informações já confirmadas, salvo se o usuário pedir uma revisão do que foi coletado."
        )
        if request.operation:
            instructions += f"\nContexto opcional selecionado pelo usuário: {request.operation}."
        if request.memory:
            instructions += "\nMemória disponível:\n" + json.dumps(
                request.memory, ensure_ascii=False, separators=(",", ":")
            )

        previous_response_id = str(
            request.metadata.get("previous_response_id") or ""
        ).strip()
        last_tool_results = request.metadata.get("last_tool_results") or ()

        prepared_attachments = ()
        if previous_response_id and last_tool_results:
            input_items = [
                {
                    "type": "function_call_output",
                    "call_id": str(item.get("call_id") or ""),
                    "output": json.dumps(
                        item.get("output") or {},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                }
                for item in last_tool_results
                if item.get("call_id")
            ]
            if not input_items:
                raise ProviderRequestError(
                    "Resultado de ferramenta sem call_id para continuidade da Responses API."
                )
        else:
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
        tool_definitions = request.metadata.get("tool_definitions") or ()
        if tool_definitions:
            payload["tools"] = list(tool_definitions)
            payload["tool_choice"] = "auto"
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        data = self._request(payload)
        tool_calls = self._extract_function_calls(data)
        text = self._extract_text(data)
        if not text and tool_calls:
            text = "Executando ferramenta solicitada."
        if not text:
            raise ProviderRequestError("A OpenAI não retornou texto nem chamada de ferramenta.")

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
                "tool_calls": tool_calls,
            },
        )

    def _request(self, payload: dict) -> dict:
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
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderRequestError(f"OpenAI respondeu HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderRequestError(f"Falha ao consultar a OpenAI: {exc}") from exc

    @staticmethod
    def _extract_text(data: dict) -> str:
        text = str(data.get("output_text") or "").strip()
        if text:
            return text
        parts: list[str] = []
        for output in data.get("output") or []:
            for content in output.get("content") or []:
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(str(content["text"]).strip())
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def _extract_function_calls(data: dict) -> tuple[dict, ...]:
        calls: list[dict] = []
        for output in data.get("output") or []:
            if output.get("type") != "function_call":
                continue
            name = str(output.get("name") or "").strip()
            call_id = str(output.get("call_id") or output.get("id") or "").strip()
            raw_arguments = output.get("arguments") or "{}"
            try:
                arguments = (
                    json.loads(raw_arguments)
                    if isinstance(raw_arguments, str)
                    else dict(raw_arguments)
                )
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ProviderRequestError(
                    f"Argumentos inválidos na chamada da ferramenta {name or '<sem nome>'}."
                ) from exc
            if not name or not call_id or not isinstance(arguments, dict):
                raise ProviderRequestError("Chamada de ferramenta incompleta na Responses API.")
            calls.append({"name": name, "arguments": arguments, "call_id": call_id})
        return tuple(calls)
