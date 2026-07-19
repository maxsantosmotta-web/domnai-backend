import json

import pytest

from app.domnai_core.artifacts import (
    ArtifactService,
    ArtifactValidationError,
    InMemoryArtifactStore,
)


def test_uploaded_and_generated_artifacts_are_separated():
    store = InMemoryArtifactStore()
    service = ArtifactService(store)

    uploaded = service.register_uploaded(
        name="entrada.txt",
        mime_type="text/plain",
        content=b"conteudo enviado",
        owner_id="u1",
    )
    generated = service.generate_text(
        name="saida.md",
        text="# Resultado",
        mime_type="text/markdown",
        owner_id="u1",
    )

    assert uploaded.origin == "uploaded"
    assert generated.origin == "generated"
    assert service.list_summaries(owner_id="u1", origin="uploaded")[0]["artifact_id"] == uploaded.artifact_id
    assert service.list_summaries(owner_id="u1", origin="generated")[0]["artifact_id"] == generated.artifact_id


def test_text_json_and_csv_generation_are_deterministic_and_readable():
    service = ArtifactService(InMemoryArtifactStore())

    text = service.generate_text(name="nota.txt", text="Olá", owner_id="u1")
    payload = service.generate_json(name="dados.json", data={"b": 2, "a": 1}, owner_id="u1")
    csv_file = service.generate_csv(
        name="dados.csv",
        rows=[{"nome": "Ana", "idade": 30}, {"nome": "João", "idade": 40}],
        owner_id="u1",
    )

    assert service.read_text(text.artifact_id, owner_id="u1") == "Olá"
    assert json.loads(service.read_text(payload.artifact_id, owner_id="u1")) == {"a": 1, "b": 2}
    csv_text = service.read_text(csv_file.artifact_id, owner_id="u1")
    assert "nome,idade" in csv_text
    assert "Ana,30" in csv_text


def test_owner_isolation_blocks_cross_user_access():
    service = ArtifactService(InMemoryArtifactStore())
    artifact = service.generate_text(name="privado.txt", text="segredo", owner_id="u1")

    with pytest.raises(PermissionError):
        service.get(artifact.artifact_id, owner_id="u2")

    assert service.list_summaries(owner_id="u2") == ()


def test_size_and_supported_format_limits_are_enforced():
    service = ArtifactService(InMemoryArtifactStore(), max_artifact_bytes=5, max_text_characters=5)

    with pytest.raises(ArtifactValidationError, match="limite"):
        service.generate_text(name="grande.txt", text="abcdef")

    with pytest.raises(ArtifactValidationError, match="não suportada"):
        service.generate_text(name="arquivo.pdf", text="x", mime_type="application/pdf")


def test_binary_artifact_cannot_be_read_as_text():
    service = ArtifactService(InMemoryArtifactStore())
    artifact = service.register_uploaded(
        name="imagem.png",
        mime_type="image/png",
        content=b"\x89PNG",
        owner_id="u1",
    )

    with pytest.raises(ArtifactValidationError, match="Leitura textual não suportada"):
        service.read_text(artifact.artifact_id, owner_id="u1")


def test_summary_exposes_hash_but_not_raw_content():
    service = ArtifactService(InMemoryArtifactStore())
    artifact = service.generate_text(name="nota.txt", text="conteudo", owner_id="u1")

    summary = artifact.summary()

    assert summary["sha256"] == artifact.sha256
    assert summary["size_bytes"] == len(b"conteudo")
    assert "content" not in summary
