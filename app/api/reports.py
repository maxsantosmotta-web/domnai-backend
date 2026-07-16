from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.audit import record_audit_event
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import LibraryAsset
from app.services.credit_meter import ensure_artifact_credit
from app.services.pdf_report import generate_pdf_report


router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportSection(BaseModel):
    title: str = Field(default="", max_length=180)
    content: str = Field(default="", max_length=30000)


class ReportMetric(BaseModel):
    label: str = Field(max_length=120)
    value: str = Field(max_length=180)


class ReportTable(BaseModel):
    title: str = Field(default="", max_length=180)
    headers: list[str] = Field(default_factory=list, max_length=10)
    rows: list[list[Any]] = Field(default_factory=list, max_length=100)


class ReportChart(BaseModel):
    title: str = Field(default="", max_length=180)
    labels: list[str] = Field(default_factory=list, max_length=12)
    values: list[float] = Field(default_factory=list, max_length=12)


class PdfReportRequest(BaseModel):
    confirmed: bool
    title: str = Field(default="Relatório DomnAI", max_length=180)
    operation: str = Field(default="", max_length=180)
    summary: str = Field(default="", max_length=20000)
    sections: list[ReportSection] = Field(default_factory=list, max_length=30)
    metrics: list[ReportMetric] = Field(default_factory=list, max_length=24)
    tables: list[ReportTable] = Field(default_factory=list, max_length=12)
    charts: list[ReportChart] = Field(default_factory=list, max_length=6)


@router.post("/pdf", status_code=status.HTTP_201_CREATED)
def create_pdf_report(
    payload: PdfReportRequest,
    session: dict = Depends(require_authenticated_user),
):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    if not payload.confirmed:
        raise HTTPException(
            status_code=409,
            detail="A geração do PDF exige confirmação explícita do usuário.",
        )

    ensure_artifact_credit(user_id, "pdf")

    try:
        generated = generate_pdf_report(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Não foi possível gerar o PDF.") from exc

    asset = LibraryAsset(
        user_id=user_id,
        name=generated.filename,
        mime_type="application/pdf",
        size_bytes=len(generated.content),
        content=generated.content,
    )

    with session_scope() as db:
        db.add(asset)
        db.flush()
        record_audit_event(
            db,
            user_id=user_id,
            category="pdf",
            module="Chat",
            action="pdf_delivered",
            description=f"PDF concluído e disponibilizado pelo chat: {asset.name}.",
            source="chat",
            source_key=f"pdf:{asset.id}",
        )
        return {
            "id": asset.id,
            "name": asset.name,
            "mimeType": asset.mime_type,
            "sizeBytes": asset.size_bytes,
            "createdAt": asset.created_at.isoformat(),
            "contentUrl": f"/api/library/{asset.id}/content",
            "savedToLibrary": True,
            "artifactType": "pdf",
            "capabilityEvidence": {
                "local_artifact_created": True,
                "external_link_generated": False,
                "email_sent": False,
            },
        }
