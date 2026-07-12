from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import session_scope
from app.models import DecisionAnalysis
from app.schemas import DecisionAnalysisRequest


_DECISION_CATEGORIES = [
    {
        "id": "contracts",
        "name": "Análise de contratos",
        "example": "Identifique cláusulas de risco, obrigações e pontos de atenção.",
    },
    {
        "id": "products",
        "name": "Comparação de produtos",
        "example": "Compare opções, custo-benefício, riscos e adequação ao uso.",
    },
    {
        "id": "services",
        "name": "Cotação de serviços",
        "example": "Avalie propostas, escopo, preço e condições comerciais.",
    },
    {
        "id": "negotiation",
        "name": "Negociação",
        "example": "Organize argumentos e estratégias para negociar melhor.",
    },
    {
        "id": "business",
        "name": "Decisões de negócio",
        "example": "Analise alternativas, riscos, custos e próximos passos.",
    },
]


def get_decision_categories() -> list[dict[str, str]]:
    """Return the decision categories exposed by the public API."""
    return [category.copy() for category in _DECISION_CATEGORIES]


def generate_initial_analysis(payload: DecisionAnalysisRequest) -> dict[str, object]:
    """Build the initial structured analysis used by the decisions endpoint.

    This endpoint remains deterministic. The conversational AI endpoint is
    responsible for model-generated answers.
    """
    category = payload.category.strip()
    question = payload.question.strip()
    context = payload.context.strip()

    recommendation = (
        "Organize as alternativas, confirme os dados mais importantes e "
        "compare benefícios, riscos, custos e consequências antes de decidir."
    )

    analysis = {
        "category": category,
        "question": question,
        "contextPreview": context[:500],
        "recommendation": recommendation,
        "pointsToReview": [
            "Objetivo principal da decisão",
            "Custos imediatos e futuros",
            "Riscos e obrigações envolvidos",
            "Alternativas disponíveis",
            "Informações que ainda precisam ser confirmadas",
        ],
    }

    try:
        with session_scope() as session:
            saved = DecisionAnalysis(
                category=category,
                question=question,
                context_preview=context[:2000],
                recommendation=recommendation,
            )
            session.add(saved)
            session.flush()
            analysis["id"] = saved.id
    except SQLAlchemyError:
        # The analysis endpoint must remain usable before database initialization.
        analysis["id"] = None

    return analysis


def count_saved_analyses() -> int:
    """Return the number of saved decision analyses without breaking health checks.

    Before the initial database migration runs, the table may not exist yet. In
    that case the status endpoint must remain available and report zero.
    """
    try:
        with session_scope() as session:
            count = session.scalar(
                select(func.count()).select_from(DecisionAnalysis)
            )
            return int(count or 0)
    except SQLAlchemyError:
        return 0
