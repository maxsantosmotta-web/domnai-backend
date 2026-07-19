from app.domnai_core.artifact_engine import ArtifactAwareConversationEngine
from app.domnai_core.artifact_flow import ArtifactCoordinator, ArtifactIntent
from app.domnai_core.artifacts import ArtifactService, InMemoryArtifactStore
from app.domnai_core.contracts import ConversationRequest, ConversationResponse


class StubProvider:
    def generate(self, request):
        return ConversationResponse(text="Concluído.", provider="stub", model="stub")


def _coordinator(now=1000.0):
    store = InMemoryArtifactStore()
    service = ArtifactService(store, now_provider=lambda: now)
    return store, service, ArtifactCoordinator(service, now_provider=lambda: now)


def test_no_intent_keeps_engine_behavior_without_artifact():
    _, _, coordinator = _coordinator()
    engine = ArtifactAwareConversationEngine(StubProvider(), artifact_coordinator=coordinator)

    response = engine.respond(ConversationRequest(message="Converse normalmente."))

    assert response.text == "Concluído."
    assert "artifact_generated" not in response.metadata


def test_engine_generates_only_with_structured_authorized_intent():
    _, service, coordinator = _coordinator()
    engine = ArtifactAwareConversationEngine(StubProvider(), artifact_coordinator=coordinator)

    response = engine.respond(
        ConversationRequest(
            message="Gere o arquivo.",
            metadata={
                "user_id": "u1",
                "conversation_id": "c1",
                "artifact_intent": {
                    "format": "pdf",
                    "name": "relatorio.pdf",
                    "payload": "Relatório validado.",
                    "explicitly_requested": True,
                    "authorization_source": "mensagem_atual",
                },
            },
        )
    )

    assert response.metadata["artifact_generated"] is True
    summary = response.metadata["artifact"]
    assert summary["mime_type"] == "application/pdf"
    stored = service.get(summary["artifact_id"], owner_id="u1")
    assert stored.content.startswith(b"%PDF")
    assert stored.metadata["conversation_id"] == "c1"


def test_unauthorized_intent_is_blocked_after_conversation_response():
    _, _, coordinator = _coordinator()
    engine = ArtifactAwareConversationEngine(StubProvider(), artifact_coordinator=coordinator)

    try:
        engine.respond(
            ConversationRequest(
                message="Talvez um arquivo fosse útil.",
                metadata={
                    "artifact_intent": {
                        "format": "txt",
                        "name": "rascunho.txt",
                        "payload": "Conteúdo",
                    }
                },
            )
        )
    except PermissionError as exc:
        assert "pedido explícito" in str(exc)
    else:
        raise AssertionError("Era esperado bloqueio sem autorização.")


def test_retention_and_library_visibility_are_applied():
    _, service, coordinator = _coordinator(now=1000.0)
    intent = ArtifactIntent(
        format="txt",
        name="temporario.txt",
        payload="temporário",
        explicitly_requested=True,
        retention_seconds=120,
        library_visible=False,
    )

    artifact = coordinator.execute(intent, owner_id="u1", conversation_id="c1")

    assert artifact.metadata["expires_at"] == 1120.0
    assert coordinator.library_entries(owner_id="u1") == ()
    assert service.get(artifact.artifact_id, owner_id="u1").name == "temporario.txt"


def test_library_entries_return_safe_summaries_only():
    _, _, coordinator = _coordinator()
    artifact = coordinator.execute(
        ArtifactIntent(
            format="csv",
            name="dados.csv",
            payload=[{"nome": "Ana", "valor": 10}],
            explicitly_requested=True,
        ),
        owner_id="u1",
        conversation_id="c9",
    )

    entries = coordinator.library_entries(owner_id="u1")

    assert entries[0]["artifact_id"] == artifact.artifact_id
    assert entries[0]["conversation_id"] == "c9"
    assert entries[0]["library_status"] == "available"
    assert "content" not in entries[0]
