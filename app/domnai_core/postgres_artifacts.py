from __future__ import annotations

import json
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import session_scope
from app.domnai_core.artifacts import Artifact, ArtifactOrigin

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


class PostgresArtifactSchemaManager:
    """Cria somente a tabela isolada de artefatos do novo núcleo."""

    def __init__(self, session_factory: SessionScopeFactory = session_scope) -> None:
        self._session_factory = session_factory

    def ensure_schema(self) -> None:
        with self._session_factory() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS domnai_core_artifacts (
                    artifact_id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(500) NOT NULL,
                    mime_type VARCHAR(255) NOT NULL,
                    content BYTEA NOT NULL,
                    origin VARCHAR(20) NOT NULL,
                    owner_id VARCHAR(255) NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_domnai_core_artifacts_owner_origin
                ON domnai_core_artifacts (owner_id, origin, created_at)
            """))


class PostgresArtifactStore:
    def __init__(
        self,
        session_factory: SessionScopeFactory = session_scope,
        *,
        ensure_schema: bool = False,
    ) -> None:
        self._session_factory = session_factory
        if ensure_schema:
            PostgresArtifactSchemaManager(session_factory).ensure_schema()

    def save(self, artifact: Artifact) -> None:
        owner_id = str(artifact.metadata.get("owner_id") or "").strip()
        metadata_json = json.dumps(artifact.metadata, ensure_ascii=False, separators=(",", ":"))
        with self._session_factory() as session:
            exists = session.execute(
                text("SELECT artifact_id FROM domnai_core_artifacts WHERE artifact_id = :id"),
                {"id": artifact.artifact_id},
            ).first()
            values = {
                "id": artifact.artifact_id,
                "name": artifact.name,
                "mime": artifact.mime_type,
                "content": artifact.content,
                "origin": artifact.origin,
                "owner": owner_id,
                "metadata": metadata_json,
                "created_at": datetime.now(timezone.utc),
            }
            if exists is None:
                session.execute(text("""
                    INSERT INTO domnai_core_artifacts
                        (artifact_id, name, mime_type, content, origin, owner_id, metadata_json, created_at)
                    VALUES
                        (:id, :name, :mime, :content, :origin, :owner, :metadata, :created_at)
                """), values)
            else:
                session.execute(text("""
                    UPDATE domnai_core_artifacts
                    SET name = :name,
                        mime_type = :mime,
                        content = :content,
                        origin = :origin,
                        owner_id = :owner,
                        metadata_json = :metadata
                    WHERE artifact_id = :id
                """), values)

    def get(self, artifact_id: str) -> Artifact | None:
        normalized = artifact_id.strip()
        if not normalized:
            return None
        with self._session_factory() as session:
            row = session.execute(text("""
                SELECT artifact_id, name, mime_type, content, origin, metadata_json
                FROM domnai_core_artifacts
                WHERE artifact_id = :id
            """), {"id": normalized}).mappings().first()
        return _row_to_artifact(row) if row is not None else None

    def list(
        self,
        *,
        owner_id: str = "",
        origin: ArtifactOrigin | None = None,
    ) -> tuple[Artifact, ...]:
        clauses: list[str] = []
        params: dict = {}
        if owner_id.strip():
            clauses.append("owner_id = :owner")
            params["owner"] = owner_id.strip()
        if origin is not None:
            clauses.append("origin = :origin")
            params["origin"] = origin
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._session_factory() as session:
            rows = session.execute(text(f"""
                SELECT artifact_id, name, mime_type, content, origin, metadata_json
                FROM domnai_core_artifacts
                {where}
                ORDER BY created_at ASC, artifact_id ASC
            """), params).mappings().all()
        return tuple(_row_to_artifact(row) for row in rows)


def _row_to_artifact(row: dict) -> Artifact:
    metadata = json.loads(row["metadata_json"])
    if not isinstance(metadata, dict):
        raise ValueError("metadata_json do artefato deve representar um objeto JSON.")
    content = row["content"]
    if isinstance(content, memoryview):
        content = content.tobytes()
    return Artifact(
        artifact_id=str(row["artifact_id"]),
        name=str(row["name"]),
        mime_type=str(row["mime_type"]),
        content=bytes(content),
        origin=str(row["origin"]),
        metadata=metadata,
    )
