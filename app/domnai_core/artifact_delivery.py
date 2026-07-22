from __future__ import annotations

from app.audit import record_audit_event
from app.database import session_scope
from app.models import LibraryAsset
from app.services.credit_meter import charge_artifact, ensure_artifact_credit
from app.services.pdf_report import generate_pdf_report
from app.services.spreadsheet_artifact import generate_csv, generate_xlsx


def artifact_offer(artifact_type: str | None) -> str:
    if artifact_type == 'pdf':
        return 'Posso gerar este conteúdo em PDF e enviar o arquivo aqui no chat.'
    if artifact_type == 'csv':
        return 'Posso transformar estes dados em CSV e enviar o arquivo aqui no chat.'
    if artifact_type == 'xlsx':
        return 'Posso transformar este resultado em uma planilha e enviar o arquivo aqui no chat.'
    return ''


def create_artifact(
    *,
    user_id: str,
    operation: str | None,
    answer: str,
    decision: dict,
    billing_key: str | None = None,
) -> dict:
    artifact_type = str(decision.get('artifact_type') or '').strip().lower()
    ensure_artifact_credit(user_id, artifact_type)
    title = str(decision.get('title') or 'Documento DomnAI').strip()[:180]

    if artifact_type == 'pdf':
        generated = generate_pdf_report({
            'title': title,
            'operation': operation or 'Análise geral',
            'summary': answer,
            'sections': [{'title': 'Resultado', 'content': answer}],
            'metrics': [],
            'tables': [],
            'charts': [],
        })
        action = 'pdf_delivered'
    elif artifact_type == 'csv':
        generated = generate_csv(title, decision.get('headers') or [], decision.get('rows') or [])
        action = 'spreadsheet_delivered'
    elif artifact_type == 'xlsx':
        generated = generate_xlsx(
            title,
            str(decision.get('sheet_name') or 'Dados'),
            decision.get('headers') or [],
            decision.get('rows') or [],
        )
        action = 'spreadsheet_delivered'
    else:
        raise ValueError('Tipo de artefato inválido.')

    artifact_usage = charge_artifact(user_id, artifact_type, idempotency_key=billing_key)
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
            category='artifact',
            module='Chat',
            action=action,
            description=(
                f'Arquivo concluído e disponibilizado pelo novo núcleo: {asset.name}. '
                f"{artifact_usage.get('charged_credits', 0)} crédito(s) consumido(s)."
            ),
            source='domnai-core',
            source_key=f'artifact:{asset.id}',
        )
        return {
            'id': asset.id,
            'libraryId': asset.id,
            'name': asset.name,
            'type': 'pdf' if artifact_type == 'pdf' else 'spreadsheet',
            'artifactType': artifact_type,
            'mimeType': asset.mime_type,
            'size': asset.size_bytes,
            'sizeBytes': asset.size_bytes,
            'contentUrl': f'/api/library/{asset.id}/content',
            'savedToLibrary': True,
            'chargedCredits': artifact_usage.get('charged_credits', 0),
            'remainingCredits': artifact_usage.get('remaining_credits'),
            'capabilityEvidence': {
                'local_artifact_created': True,
                'external_link_generated': False,
                'email_sent': False,
            },
        }
