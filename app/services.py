from app.database import is_database_configured, session_scope
from app.models import DecisionAnalysis
from app.schemas import DecisionAnalysisRequest


def get_decision_categories():
    return [
        {
            "id": "contrato",
            "name": "Analisar contrato",
            "example": "Este contrato tem cláusulas de risco?",
        },
        {
            "id": "produto",
            "name": "Comparar produto",
            "example": "Vale a pena comprar este produto?",
        },
        {
            "id": "orcamento",
            "name": "Avaliar orçamento",
            "example": "Qual orçamento é o melhor?",
        },
        {
            "id": "negociacao",
            "name": "Negociar preço",
            "example": "Como posso negociar um preço melhor?",
        },
        {
            "id": "empresa",
            "name": "Abrir empresa",
            "example": "Qual a melhor opção para abrir minha empresa?",
        },
        {
            "id": "decisao-geral",
            "name": "Outra decisão importante",
            "example": "Esta proposta está justa?",
        },
    ]


def generate_initial_analysis(payload: DecisionAnalysisRequest):
    categories = get_decision_categories()
    selected_category = next(
        (item for item in categories if item["id"] == payload.category),
        {"id": payload.category, "name": "Decisão personalizada", "example": payload.question},
    )

    context_preview = " ".join(payload.context.split())[:500]
    recommendation = "Avance apenas se os benefícios forem maiores que os riscos, os custos estiverem claros e você tiver comparado alternativas suficientes."

    analysis = {
        "category": selected_category,
        "question": payload.question,
        "summary": "Análise inicial gerada para validar o fluxo do DomnAI antes da integração com IA real.",
        "contextPreview": context_preview,
        "decisionFramework": {
            "risks": [
                "Verifique pontos que possam gerar custo escondido, obrigação futura ou perda de controle.",
                "Confirme se as condições principais estão claras, documentadas e comparáveis.",
                "Evite decidir apenas pela urgência ou pela pressão de terceiros.",
            ],
            "advantages": [
                "A decisão pode ser positiva se resolver o problema principal com custo e risco controlados.",
                "Comparar alternativas antes de agir aumenta a chance de uma escolha melhor.",
                "Registrar os critérios da decisão evita arrependimento e reduz improviso.",
            ],
            "attentionPoints": [
                "Não avalie somente o preço.",
                "Considere prazo, garantia, multa, obrigação futura, reputação e impacto financeiro.",
                "Se envolver contrato, empresa, tributo ou valor alto, revise os detalhes antes de aceitar.",
            ],
            "nextQuestions": [
                "Qual é o valor total envolvido?",
                "Existe multa, fidelidade, juros ou obrigação futura?",
                "Quais alternativas você já comparou?",
                "Qual é o pior cenário se essa decisão der errado?",
                "O que acontece se você decidir esperar mais alguns dias?",
            ],
        },
        "recommendation": recommendation,
        "disclaimer": "Esta análise é informativa e não substitui orientação profissional jurídica, contábil, financeira ou técnica quando necessária.",
        "persistence": {
            "enabled": False,
            "saved": False,
            "id": None,
        },
    }

    if is_database_configured():
        with session_scope() as session:
            record = DecisionAnalysis(
                category=selected_category["id"],
                question=payload.question,
                context_preview=context_preview,
                recommendation=recommendation,
            )
            session.add(record)
            session.flush()

            analysis["persistence"] = {
                "enabled": True,
                "saved": True,
                "id": record.id,
            }

    return analysis


def count_saved_analyses() -> int | None:
    if not is_database_configured():
        return None

    with session_scope() as session:
        return session.query(DecisionAnalysis).count()
