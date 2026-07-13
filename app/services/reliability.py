from __future__ import annotations

HIGH_RISK_OPERATIONS = {
    "Análise Contratual",
    "Cálculo de Rescisão Trabalhista",
    "Gestão Financeira Empresarial",
    "Precificação Estratégica",
    "Análise de Dívidas e Renegociação",
    "Análise de Investimentos",
    "Análise Imobiliária",
    "Organização Financeira Pessoal",
    "Planejamento de Treinos para Academia",
    "Planejamento de Exercícios em Casa",
    "Análise de Alimentação e Rotina Fitness",
    "Pilates para Fazer em Casa",
    "Yoga para Fazer em Casa",
    "Cuidados com a Pele em Casa",
    "Plano de Treino Esportivo",
    "Preparação para Corrida",
    "Plano de Alongamento e Mobilidade",
    "Preparação Física para Esportes",
}

CALCULATION_MARKERS = (
    "calcule",
    "cálculo",
    "quanto",
    "total",
    "percentual",
    "porcentagem",
    "juros",
    "margem",
    "rescisão",
    "férias",
    "décimo terceiro",
    "13º",
    "fgts",
    "preço",
    "precificação",
    "parcela",
    "financiamento",
    "retorno",
    "rentabilidade",
)


def needs_independent_review(operation: str | None, message: str, attachments: list[dict] | None = None) -> bool:
    if operation in HIGH_RISK_OPERATIONS:
        return True
    if attachments:
        return True
    normalized = (message or "").casefold()
    return any(marker in normalized for marker in CALCULATION_MARKERS)


def reviewer_instructions(operation: str | None) -> str:
    operation_label = operation or "operação não selecionada"
    return f"""
Você é o Revisor de Confiabilidade do DomnAI. Sua única função é auditar e, quando necessário, corrigir a resposta preliminar antes que ela seja mostrada ao usuário.

Contexto da operação: {operation_label}.

AUDITORIA OBRIGATÓRIA
1. Verifique se a resposta realmente atende ao pedido e utiliza corretamente os dados fornecidos.
2. Procure contradições, omissões, datas incompatíveis, unidades erradas, percentuais incorretos e conclusões não sustentadas.
3. Refaça silenciosamente toda soma, subtração, multiplicação, divisão, proporcionalidade, contagem de períodos e arredondamento.
4. Em cálculo financeiro, trabalhista ou comercial, confira cada parcela e o total por um caminho independente.
5. Não aceite total fechado quando faltar dado indispensável. Nesse caso, substitua o total por cenários ou faça perguntas objetivas.
6. Diferencie fato confirmado, declaração do usuário, hipótese, estimativa e recomendação.
7. Em jurídico, saúde, finanças e investimentos, elimine certeza indevida, promessas e orientação perigosa.
8. Em documentos, não afirme que uma cláusula existe sem apoio no conteúdo analisado. Informe página ou seção quando essa informação estiver disponível.
9. Preserve a linguagem natural e direta. Não mencione revisão, auditoria, modelo, prompt ou processo interno.
10. Entregue somente a versão final corrigida, pronta para o usuário. Não explique o que você alterou.

Se a resposta preliminar estiver correta, apenas a refine para máxima clareza e precisão, sem acrescentar fatos novos.
""".strip()


def build_review_input(user_message: str, draft_answer: str) -> str:
    return f"""
PEDIDO DO USUÁRIO:
{user_message}

RESPOSTA PRELIMINAR A SER AUDITADA:
{draft_answer}

Produza agora somente a resposta final corrigida e segura.
""".strip()
