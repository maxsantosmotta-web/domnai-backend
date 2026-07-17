from pathlib import Path


FRONTEND = Path('/frontend/src')
BACKEND = Path('/app/app')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: esperado 1 trecho, encontrado {count}.')
    return source.replace(old, new, 1)


# 1) Auditoria: manter os nove contadores também nos gráficos finais.
audit_path = FRONTEND / 'AdminAuditView.jsx'
audit = audit_path.read_text(encoding='utf-8')
audit = replace_once(
    audit,
    """            { label: 'PDFs concluídos', value: summary.pdfsDelivered },
          ]}""",
    """            { label: 'PDFs concluídos', value: summary.pdfsDelivered },
            { label: 'Planilhas concluídas', value: summary.spreadsheetsDelivered },
            { label: 'Conversas/Operações concluídas', value: summary.conversationsCompleted },
          ]}""",
    'Categorias completas do gráfico de Auditoria',
)
audit = replace_once(
    audit,
    """            { label: 'Concluídas', value: summary.planChanges + summary.paymentsApproved + summary.creditsAdded + summary.creditsConsumed + summary.pdfsDelivered, color: '#64e6a6' },""",
    """            { label: 'Concluídas', value: summary.planChanges + summary.paymentsApproved + summary.creditsAdded + summary.creditsConsumed + summary.pdfsDelivered + summary.spreadsheetsDelivered + summary.conversationsCompleted, color: '#64e6a6' },""",
    'Balanço completo da Auditoria',
)
audit_path.write_text(audit, encoding='utf-8')


overview_path = FRONTEND / 'AdminOverviewView.jsx'
overview = overview_path.read_text(encoding='utf-8')
overview = replace_once(
    overview,
    """    { label: 'PDFs', value: auditSummary.pdfsDelivered || 0 },
  ];""",
    """    { label: 'PDFs', value: auditSummary.pdfsDelivered || 0 },
    { label: 'Planilhas', value: auditSummary.spreadsheetsDelivered || 0 },
    { label: 'Conversas/Operações', value: auditSummary.conversationsCompleted || 0 },
  ];""",
    'Gráfico completo da Auditoria na Visão geral',
)
overview_path.write_text(overview, encoding='utf-8')


# 2) Feedbacks: cards e gráficos devem usar somente registros visíveis no Admin.
feedback_path = BACKEND / 'api' / 'feedback.py'
feedback = feedback_path.read_text(encoding='utf-8')
feedback = replace_once(
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
    'Resumo de Feedbacks visíveis',
)
feedback_path.write_text(feedback, encoding='utf-8')


# 3) Saúde: substituir o verde fixo do PDF por smoke test real, executado uma vez por processo.
health_path = BACKEND / 'api' / 'health.py'
health = health_path.read_text(encoding='utf-8')
health = replace_once(
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
    'Cache do smoke test de PDF',
)
health = replace_once(
    health,
    """from app.database import get_engine, is_database_configured
""",
    """from app.database import get_engine, is_database_configured
from app.services.pdf_report import generate_pdf_report
""",
    'Importação do gerador real de PDF',
)
health = replace_once(
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
    'Smoke test real do gerador de PDF',
)
health = replace_once(
    health,
    """        "pdfGeneratorAvailable": True,
""",
    """        "pdfGeneratorAvailable": _pdf_generator_check(),
""",
    'Estado real do gerador de PDF',
)
health_path.write_text(health, encoding='utf-8')


print('Bloco 3 corrigido: Auditoria completa, Feedbacks visíveis e verificação real do gerador de PDF.')
