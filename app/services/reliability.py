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

PREFLIGHT_OPERATIONS = {
    "Cálculo de Rescisão Trabalhista",
    "Gestão Financeira Empresarial",
    "Precificação Estratégica",
    "Análise de Viabilidade",
    "Análise de Dívidas e Renegociação",
    "Análise de Investimentos",
    "Análise Imobiliária",
    "Organização Financeira Pessoal",
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


def needs_preflight(operation: str | None, attachments: list[dict] | None = None) -> bool:
    if attachments:
        return False
    return operation in PREFLIGHT_OPERATIONS


def preflight_instructions(operation: str | None) -> str:
    operation_label = operation or "operação não selecionada"
    return f"""
Você é o Validador Prévio do DomnAI. Verifique se já existem dados suficientes na conversa para responder com segurança à operação: {operation_label}.

REGRAS
1. Considere toda a conversa recebida, sem repetir perguntas já respondidas.
2. Só bloqueie a análise quando faltar informação realmente indispensável para evitar erro material.
3. Não exija detalhes opcionais antes de oferecer orientação inicial útil.
4. Quando faltarem dados essenciais, faça no máximo três perguntas curtas, reunindo campos relacionados na mesma pergunta.
5. Não calcule, não analise e não dê recomendação nesta etapa.
6. Responda exatamente em um dos formatos abaixo:

READY

ou

ASK:
<perguntas objetivas em português do Brasil>

DADOS ESSENCIAIS POR CONTEXTO
- Rescisão: datas de admissão e desligamento, salário/base remuneratória, motivo da saída, aviso prévio, férias/13º já pagos e adicionais relevantes.
- Precificação/viabilidade: custos fixos e variáveis, taxas/impostos, volume esperado, preço ou margem pretendida e período analisado.
- Dívidas: saldo, juros, parcelas/prazos, renda ou capacidade de pagamento e propostas disponíveis.
- Investimentos: objetivo, prazo, liquidez necessária, tolerância a risco, valor e custos.
- Imóveis: preço, entrada/financiamento, custos adicionais, renda/objetivo, localização e condição documental quando relevantes.
- Organização financeira: renda líquida, despesas, dívidas, reservas e objetivo.
""".strip()


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
