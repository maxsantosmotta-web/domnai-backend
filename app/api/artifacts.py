from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.audit import record_audit_event
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import LibraryAsset
from app.services.spreadsheet_artifact import generate_csv, generate_xlsx


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class SpreadsheetRequest(BaseModel):
    title: str = Field(default="Planilha DomnAI", max_length=180)
    sheet_name: str = Field(default="Dados", max_length=31)
    format: Literal["xlsx", "csv"] = "xlsx"
    headers: list[str] = Field(min_length=1, max_length=50)
    rows: list[list[Any]] = Field(default_factory=list, max_length=5000)


def _serialize_created_asset(asset: LibraryAsset, artifact_type: str) -> dict:
    return {
        "id": asset.id,
        "name": asset.name,
        "mimeType": asset.mime_type,
        "sizeBytes": asset.size_bytes,
        "createdAt": asset.created_at.isoformat(),
        "contentUrl": f"/api/library/{asset.id}/content",
        "savedToLibrary": True,
        "artifactType": artifact_type,
        "capabilityEvidence": {
            "local_artifact_created": True,
            "external_link_generated": False,
            "email_sent": False,
        },
    }


@router.post("/spreadsheet", status_code=status.HTTP_201_CREATED)
def create_spreadsheet(
    payload: SpreadsheetRequest,
    session: dict = Depends(require_authenticated_user),
):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    try:
        if payload.format == "csv":
            generated = generate_csv(payload.title, payload.headers, payload.rows)
        else:
            generated = generate_xlsx(
                payload.title,
                payload.sheet_name,
                payload.headers,
                payload.rows,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Não foi possível gerar a planilha.") from exc

    asset = LibraryAsset(
        user_id=user_id,
        name=generated.filename,
        mime_type=generated.mime_type,
        size_bytes=len(generated.content),
        content=generated.content,
    )

    with session_scope() as db:
        db.add(asset)
        db.flush()
        record_audit_event(
            db,
            user_id=user_id,
            category="artifact",
            module="Chat",
            action="spreadsheet_delivered",
            description=f"Planilha concluída e disponibilizada pelo chat: {asset.name}.",
            source="chat",
            source_key=f"spreadsheet:{asset.id}",
        )
        return _serialize_created_asset(asset, payload.format)
