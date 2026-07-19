from __future__ import annotations

from typing import Protocol

from app.domnai_core.contracts import ConversationRequest, ConversationResponse


class ModelProvider(Protocol):
    """Porta de saída do núcleo para qualquer provedor de inteligência."""

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        ...


class ConversationEngine:
    """Ponto único de entrada do novo núcleo conversacional.

    Nesta primeira etapa, o motor apenas aplica invariantes arquiteturais e
    delega a geração a um provedor injetado. Memória, ferramentas, roteamento e
    persistência entrarão por portas próprias nas próximas etapas, sem acoplar o
    núcleo ao backend legado.
    """

    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    def respond(self, request: ConversationRequest) -> ConversationResponse:
        response = self._provider.generate(request)
        if not isinstance(response, ConversationResponse):
            raise TypeError("O provedor deve retornar ConversationResponse.")
        return response
