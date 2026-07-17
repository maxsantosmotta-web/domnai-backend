from pathlib import Path


FRONTEND = Path('/frontend/src')
BACKEND = Path('/app/app')


def replace_if_old(source: str, old: str, new: str, desired_marker: str, label: str) -> str:
    """Aplica a transformação somente quando o estado final ainda não existe."""
    if desired_marker in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: estado final ausente e trecho antigo encontrado {count} vez(es).')
    return source.replace(old, new, 1)


def fix_frontend() -> None:
    # Auditoria: o arquivo atual já pode vir completo de uma etapa anterior.
    audit_path = FRONTEND / 'AdminAuditView.jsx'
    audit = audit_path.read_text(encoding='utf-8')

    audit_has_complete_counters = (
        'spreadsheetsDelivered' in audit
        and 'conversationsCompleted' in audit
        and ('const AUDIT_COUNTERS' in audit or "label: 'Planilhas concluídas'" in audit)
    )
    if not audit_has_complete_counters:
        audit = replace_if_old(
            audit,
            """            { label: 'PDFs concluídos', value: summary.pdfsDelivered },
          ]}""",
            """            { label: 'PDFs concluídos', value: summary.pdfsDelivered },
            { label: 'Planilhas concluídas', value: summary.spreadsheetsDelivered },
            { label: 'Conversas/Operações concluídas', value: summary.conversationsCompleted },
          ]}""",
            'summary.spreadsheetsDelivered',
            'Categorias completas do gráfico de Auditoria',
        )

    audit_has_complete_balance = (
        'completedActions' in audit
        and 'summary.spreadsheetsDelivered' in audit
        and 'summary.conversationsCompleted' in audit
    ) or (
        'summary.pdfsDelivered + summary.spreadsheetsDelivered + summary.conversationsCompleted' in audit
    )
    if not audit_has_complete_balance:
        audit = replace_if_old(
            audit,
            """            { label: 'Concluídas', value: summary.planChanges + summary.paymentsApproved + summary.creditsAdded + summary.creditsConsumed + summary.pdfsDelivered, color: '#64e6a6' },""",
            """            { label: 'Concluídas', value: summary.planChanges + summary.paymentsApproved + summary.creditsAdded + summary.creditsConsumed + summary.pdfsDelivered + summary.spreadsheetsDelivered + summary.conversationsCompleted, color: '#64e6a6' },""",
            'summary.pdfsDelivered + summary.spreadsheetsDelivered + summary.conversationsCompleted',
            'Balanço completo da Auditoria',
        )

    audit_path.write_text(audit, encoding='utf-8')

    overview_path = FRONTEND / 'AdminOverviewView.jsx'
    overview = overview_path.read_text(encoding='utf-8')
    overview = replace_if_old(
        overview,
        """    { label: 'PDFs', value: auditSummary.pdfsDelivered || 0 },
  ];""",
        """    { label: 'PDFs', value: auditSummary.pdfsDelivered || 0 },
    { label: 'Planilhas', value: auditSummary.spreadsheetsDelivered || 0 },
    { label: 'Conversas/Operações', value: auditSummary.conversationsCompleted || 0 },
  ];""",
        "label: 'Planilhas', value: auditSummary.spreadsheetsDelivered",
        'Gráfico completo da Auditoria na Visão geral',
    )
    overview_path.write_text(overview, encoding='utf-8')


def fix_backend() -> None:
    # Feedbacks: se o filtro já existe, não reaplicar.
    feedback_path = BACKEND / 'api' / 'feedback.py'
    feedback = feedback_path.read_text(encoding='utf-8')
    feedback = replace_if_old(
        feedback,
        """        summary_row = db.execute(select(
            func.count(UserFeedback.id).label("total"),
            func.sum(case((UserFeedback.category == "suggestion", 1), else_=0)).label("suggestions"),
            func.sum(case((UserFeedback.category == "problem", 1), else_=0)).label("problems"),
            func.sum(case((UserFeedback.category == "praise", 1), else_=0)).label("praises"),
            func.avg(UserFeedback.rating).label("average"),
        )).one()""",
        """        summary_row = db.execute(
            select(
                func.count(UserFeedback.id).label("total"),
                func.sum(case((UserFeedback.category == "suggestion", 1), else_=0)).label("suggestions"),
                func.sum(case((UserFeedback.category == "problem", 1), else_=0)).label("problems"),
                func.sum(case((UserFeedback.category == "praise", 1), else_=0)).label("praises"),
                func.avg(UserFeedback.rating).label("average"),
            ).where(UserFeedback.admin_hidden_at.is_(None))
        ).one()""",
        'where(UserFeedback.admin_hidden_at.is_(None))',
        'Resumo de Feedbacks visíveis',
    )
    feedback_path.write_text(feedback, encoding='utf-8')

    # Saúde: se o smoke test real já existe, não reaplicar.
    health_path = BACKEND / 'api' / 'health.py'
    health = health_path.read_text(encoding='utf-8')

    health = replace_if_old(
        health,
        """import os
from datetime import datetime, timezone
from time import perf_counter
""",
        """import os
from datetime import datetime, timezone
from functools import lru_cache
from time import perf_counter
""",
        'from functools import lru_cache',
        'Cache do smoke test de PDF',
    )
    health = replace_if_old(
        health,
        """from app.database import get_engine, is_database_configured
""",
        """from app.database import get_engine, is_database_configured
from app.services.pdf_report import generate_pdf_report
""",
        'from app.services.pdf_report import generate_pdf_report',
        'Importação do gerador real de PDF',
    )
    health = replace_if_old(
        health,
        """@router.get("/health")
def health():
""",
        """@lru_cache(maxsize=1)
def _pdf_generator_check() -> bool:
    try:
        generated = generate_pdf_report({
            "title": "DomnAI Health Check",
            "operation": "Saúde operacional",
            "summary": "Verificação interna do gerador de PDF.",
            "sections": [{"title": "Status", "content": "Gerador disponível."}],
            "metrics": [],
            "tables": [],
            "charts": [],
        })
        content = bytes(getattr(generated, "content", b"") or b"")
        return content.startswith(b"%PDF") and len(content) > 100
    except Exception:
        return False


@router.get("/health")
def health():
""",
        'def _pdf_generator_check() -> bool:',
        'Smoke test real do gerador de PDF',
    )
    health = replace_if_old(
        health,
        """        "pdfGeneratorAvailable": True,
""",
        """        "pdfGeneratorAvailable": _pdf_generator_check(),
""",
        '"pdfGeneratorAvailable": _pdf_generator_check()',
        'Estado real do gerador de PDF',
    )
    health_path.write_text(health, encoding='utf-8')


applied = []
if FRONTEND.exists():
    fix_frontend()
    applied.append('frontend')
if BACKEND.exists():
    fix_backend()
    applied.append('backend')
if not applied:
    raise RuntimeError('Nenhuma etapa compatível do Docker foi encontrada para o Bloco 3.')

print(f'Bloco 3 validado/corrigido com segurança em: {", ".join(applied)}.')
