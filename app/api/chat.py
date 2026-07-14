from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.audit import record_audit_event
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import LibraryAsset
from app.services.artifact_decision import decide_artifact
from app.services.credit_meter import charge_usage, ensure_minimum_credit
from app.services.diagnosis_memory import load_diagnosis_state, save_diagnosis_state
from app.services.orchestrated_brain import generate_orchestrated_response
from app.services.pdf_report import generate_pdf_report
from app.services.spreadsheet_artifact import generate_csv, generate_xlsx


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatAttachmentItem(BaseModel):
    library_id: str = Field(min_length=1, max_length=180)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    operation: str | None = Field(default=None, max_length=180)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=40)
    attachments: list[ChatAttachmentItem] = Field(default_factory=list, max_length=10)


def _load_attachments(user_id: str, attachment_ids: list[str]) -> list[dict]:
    if not attachment_ids:
        return []

    unique_ids = list(dict.fromkeys(attachment_ids))
    with session_scope() as db:
        assets = db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.user_id == user_id,
                LibraryAsset.id.in_(unique_ids),
            )
        ).all()

        assets_by_id = {
            asset.id: {
                "id": asset.id,
                "name": asset.name,
                "mime_type": asset.mime_type,
                "content": bytes(asset.content or b""),
            }
            for asset in assets
        }

    missing_ids = [asset_id for asset_id in unique_ids if asset_id not in assets_by_id]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Um dos arquivos anexados não foi encontrado na Biblioteca.")

    return [assets_by_id[asset_id] for asset_id in unique_ids]


def _artifact_offer(artifact_type: str | None) -> str:
    if artifact_type == "pdf":
        return "Posso organizar esse resultado em um PDF profissional e salvar na sua Biblioteca."
    if artifact_type == "csv":
        return "Posso transformar esses dados em um arquivo CSV editável e salvar na sua Biblioteca."
    if artifact_type == "xlsx":
        return "Posso transformar esse resultado em uma planilha editável e salvar na sua Biblioteca."
    return ""


def _create_artifact(
    *,
    user_id: str,
    operation: str | None,
    answer: str,
    decision: dict,
) -> dict:
    artifact_type = decision.get("artifact_type")
    title = str(decision.get("title") or "Documento DomnAI").strip()[:180]

    if artifact_type == "pdf":
        generated = generate_pdf_report(
            {
                "title": title,
                "operation": operation or "Análise geral",
                "summary": answer,
                "sections": [{"title": "Resultado", "content": answer}],
                "metrics": [],
                "tables": [],
                "charts": [],
            }
        )
        mime_type = "application/pdf"
        action = "pdf_delivered"
    elif artifact_type == "csv":
        generated = generate_csv(
            title,
            decision.get("headers") or [],
            decision.get("rows") or [],
        )
        mime_type = generated.mime_type
        action = "spreadsheet_delivered"
    elif artifact_type == "xlsx":
        generated = generate_xlsx(
            title,
            str(decision.get("sheet_name") or "Dados"),
            decision.get("headers") or [],
            decision.get("rows") or [],
        )
        mime_type = generated.mime_type
        action = "spreadsheet_delivered"
    else:
        raise ValueError("Tipo de artefato inválido.")

    asset = LibraryAsset(
        user_id=user_id,
        name=generated.filename,
        mime_type=mime_type,
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
            action=action,
            description=f"Arquivo concluído e disponibilizado pelo chat: {asset.name}.",
            source="chat",
            source_key=f"artifact:{asset.id}",
        )
        return {
            "id": asset.id,
            "libraryId": asset.id,
            "name": asset.name,
            "type": "pdf" if artifact_type == "pdf" else "spreadsheet",
            "artifactType": artifact_type,
            "mimeType": asset.mime_type,
            "size": asset.size_bytes,
            "sizeBytes": asset.size_bytes,
            "contentUrl": f"/api/library/{asset.id}/content",
            "savedToLibrary": True,
            "capabilityEvidence": {
                "local_artifact_created": True,
                "external_link_generated": False,
                "email_sent": False,
            },
        }


@router.post("/respond")
def respond(payload: ChatRequest, session: dict = Depends(require_authenticated_user)):
    user_id = str(session.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para continuar.")

    operation = payload.operation.strip() if payload.operation else None
    attachments = _load_attachments(
        user_id,
        [item.library_id for item in payload.attachments],
    )
    diagnosis_state = load_diagnosis_state(user_id, operation)
    history = [item.model_dump() for item in payload.history]

    ensure_minimum_credit(user_id)

    try:
        result = generate_orchestrated_response(
            message=message,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    usage = charge_usage(user_id, result)

    if result.diagnosis_state is not None:
        try:
            save_diagnosis_state(user_id, operation, result.diagnosis_state)
        except Exception:
            pass

    reply = result.text
    artifact = None
    decision = decide_artifact(
        message=message,
        operation=operation,
        history=history,
        answer=reply,
    )

    if decision.get("action") == "offer":
        offer = _artifact_offer(decision.get("artifact_type"))
        if offer and offer.casefold() not in reply.casefold():
            reply = f"{reply.rstrip()}\n\n{offer}"
    elif decision.get("action") == "create":
        try:
            artifact = _create_artifact(
                user_id=user_id,
                operation=operation,
                answer=reply,
                decision=decision,
            )
            reply = f"{reply.rstrip()}\n\nArquivo criado e salvo na sua Biblioteca."
        except Exception:
            reply = f"{reply.rstrip()}\n\nNão foi possível gerar o arquivo nesta tentativa."

    return {
        "reply": reply,
        "artifact": artifact,
        "provider": result.provider,
        "model": result.model,
        "operation": payload.operation,
        "usage": {
            "inputTokens": usage["input_tokens"],
            "cachedInputTokens": usage["cached_input_tokens"],
            "outputTokens": usage["output_tokens"],
            "costUsd": round(usage["cost_usd"], 8),
            "measuredCredits": usage["credits"],
            "chargedCredits": usage["charged_credits"],
            "adminExempt": usage["admin_exempt"],
            "remainingCredits": usage.get("remaining_credits"),
        },
    }
