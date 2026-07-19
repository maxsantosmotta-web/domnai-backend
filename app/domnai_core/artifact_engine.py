from __future__ import annotations

from dataclasses import replace

from app.domnai_core.artifact_flow import ArtifactCoordinator, ArtifactIntent
from app.domnai_core.contracts import ConversationRequest, ConversationResponse
from app.domnai_core.engine import ConversationEngine


class ArtifactAwareConversationEngine(ConversationEngine):
    """Extensão opcional do motor que só gera artefatos por contrato explícito.

    A classe não interpreta linguagem natural para decidir geração. O chamador deve
    fornecer `artifact_intent` estruturado nos metadados da requisição. Sem esse
    contrato, o comportamento é exatamente o do `ConversationEngine` base.
    """

    def __init__(self, *args, artifact_coordinator: ArtifactCoordinator, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._artifact_coordinator = artifact_coordinator

    def respond(self, request: ConversationRequest) -> ConversationResponse:
        response = super().respond(request)
        intent = ArtifactIntent.from_metadata(request.metadata.get("artifact_intent"))
        if intent is None:
            return response

        owner_id = str(request.metadata.get("user_id") or "").strip()
        conversation_id = str(request.metadata.get("conversation_id") or "").strip()
        artifact = self._artifact_coordinator.execute(
            intent,
            owner_id=owner_id,
            conversation_id=conversation_id,
        )
        return replace(
            response,
            metadata={
                **dict(response.metadata),
                "artifact_generated": True,
                "artifact": artifact.summary(),
            },
        )
