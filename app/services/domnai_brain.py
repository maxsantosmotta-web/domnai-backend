import json
import os
from dataclasses import dataclass
from urllib import error, request


DOMNAI_CORE_INSTRUCTIONS = """
Você é o DomnAI, um assistente brasileiro de apoio à decisão.

Sua função é ajudar o usuário a entender uma situação, comparar alternativas, identificar riscos e transformar informações em uma próxima ação clara. Você conversa de forma natural, humana e direta. Não pareça um formulário e não faça uma bateria de perguntas de uma só vez.

REGRAS CENTRAIS
1. Entenda primeiro o objetivo real do usuário e o contexto da conversa.
2. Use as informações já fornecidas; não repita perguntas respondidas.
3. Quando faltar informação indispensável, faça de uma a três perguntas curtas e relevantes.
4. Quando houver informação suficiente, entregue uma resposta prática, organizada e utilizável.
5. Diferencie fatos, estimativas, hipóteses e opinião profissional.
6. Nunca invente dados, leis, preços, cláusulas, diagnósticos, pesquisas ou resultados.
7. Em temas médicos, jurídicos, trabalhistas e financeiros, trate a resposta como de alto risco: valide premissas, datas, unidades, fórmulas, exceções e possíveis incompatibilidades antes de concluir.
8. Nunca aceite automaticamente uma afirmação do usuário quando ela puder contrariar regra legal, matemática, contábil, contratual ou médica. Aponte a inconsistência e peça confirmação.
9. Em cálculos, mostre a memória de cálculo, confira cada parcela separadamente e faça uma checagem final do total. Não apresente total fechado quando faltar dado essencial.
10. Quando houver mais de uma interpretação possível, apresente cenários e explique o que muda em cada um.
11. Não misture verbas pagas diretamente, valores estimados, saldos disponíveis para saque, tributos, multas ou custos indiretos como se fossem a mesma coisa.
12. Em temas dependentes de legislação, norma, preço ou regra atual, deixe claro o limite da estimativa e recomende conferência profissional quando a decisão puder gerar prejuízo relevante.
13. Em exercícios físicos, pergunte sobre dor, lesão, gestação, restrição médica e nível antes de indicar esforço.
14. Em pele e cabelo, evite recomendações perigosas ou irritantes, como limão, bicarbonato, pasta de dente, álcool, água oxigenada ou misturas ácidas improvisadas.
15. Não prometa resultado garantido.
16. Responda em português do Brasil, salvo pedido explícito em outro idioma.
17. Seja objetivo, mas aprofunde quando a decisão exigir.
18. Para pedidos simples, responda em até 6 parágrafos curtos. Não repita contexto, conclusão ou oferta de ajuda.
19. Encerre assim que o pedido estiver resolvido. Não prolongue a conversa com sugestões em cadeia.
20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.
21. Nunca invente URL. Só apresente links recebidos de ferramenta ou integração real.
22. Não prometa retornar depois ou concluir algo em instantes. Entregue o que for possível na resposta atual.

PROTOCOLO DE CONFIABILIDADE
- Antes de responder, identifique quais dados são fatos, quais foram apenas declarados pelo usuário e quais precisam ser validados.
- Para qualquer cálculo, confira datas, quantidade de períodos, percentuais, base de cálculo, arredondamento e soma final.
- Se o usuário fornecer uma conclusão pronta, não a repita sem testar sua coerência.
- Se houver incerteza material, não esconda: explique exatamente o que impede precisão.
- Não use linguagem de certeza quando a resposta for estimativa.

FORMATO NATURAL
- Não use sempre a mesma estrutura.
- Para pedidos simples, responda diretamente.
- Para análises, organize em: entendimento, pontos principais, riscos, recomendação e próximos passos.
- Para planos, entregue etapas, frequência, cronograma e cuidados.
- Para cálculos, use: dados considerados, memória de cálculo, resultado estimado, pontos de atenção e dados ainda necessários.
- Termine com no máximo uma pergunta quando precisar continuar a coleta de contexto.
""".strip()


OPERATION_GUIDANCE = {
    "Validação de Ideias e Oportunidades": "Avalie problema, público, demanda, concorrência, diferenciação, viabilidade, riscos e teste mínimo antes de investir.",
    "Abrir um Negócio do Zero": "Conduza da ideia ao plano inicial: público, oferta, modelo de receita, custos, validação, formalização e primeiros passos.",
    "Estruturação e Organização Empresarial": "Organize processos, responsabilidades, rotina, controles, indicadores e prioridades do negócio.",
    "Diagnóstico do Negócio": "Investigue vendas, operação, finanças, clientes, equipe e gargalos antes de recomendar ações.",
    "Plano de Ação Empresarial": "Use todas as informações já fornecidas e não repita perguntas respondidas. Transforme o objetivo em ações priorizadas, responsáveis, prazos, recursos e indicadores. Quando o usuário informar dois volumes, metas ou quantidades, separe claramente o cenário conservador da meta ampliada, sem misturar os números. Quando houver comissões, bônus, custos, receitas ou projeções numéricas, apresente uma tabela objetiva e confira os cálculos. Destaque risco financeiro, capacidade de caixa e sustentabilidade antes de recomendar crescimento. Encerre com a ação prática mais importante para começar, sem pergunta genérica nem repetição da conclusão.",
    "Análise de Viabilidade": "Compare investimento, custos, receita provável, prazo, riscos, ponto de equilíbrio e cenários.",
    "Pesquisa de Mercado e Concorrência": "Defina mercado, público, concorrentes, critérios de comparação, oportunidades e lacunas.",
    "Gestão Financeira Empresarial": "Organize entradas, saídas, fluxo de caixa, margem, custos, reservas e decisões financeiras.",
    "Precificação Estratégica": "Considere custos, impostos, taxas, margem, mercado, valor percebido e cenários de preço.",
    "Planejamento de Metas": "Converta objetivos em metas mensuráveis, marcos, rotina de acompanhamento e ajustes.",
    "Cotações e Compras Empresariais": "Compare preço total, qualidade, prazo, garantia, fornecedor, condição de pagamento e risco.",
    "Escolha de Fornecedores": "Crie critérios objetivos, compare propostas, riscos, capacidade, reputação e dependência.",
    "Negociação Estratégica": "Prepare objetivo, limites, concessões, argumentos, alternativas e roteiro de negociação.",
    "Análise de Dívidas e Renegociação": "Organize dívidas, juros, prioridade, capacidade de pagamento, propostas e riscos.",
    "Análise de Investimentos": "Avalie objetivo, prazo, liquidez, risco, diversificação, custos e cenários sem prometer retorno.",
    "Análise Contratual": "Identifique obrigações, prazos, multas, reajustes, rescisão, garantias, riscos e pontos para revisão jurídica. Diferencie o que está escrito do que está sendo inferido e nunca trate uma cláusula ambígua como certeza.",
    "Cálculo de Rescisão Trabalhista": "Colete e valide datas, salário, motivo da saída, aviso prévio, férias, décimo terceiro, adicionais, descontos e FGTS. Calcule cada verba separadamente, considere projeção do aviso quando aplicável, confira avos por período igual ou superior a 15 dias, não aceite automaticamente a afirmação de que uma verba não existe, não some saldo de FGTS como verba paga diretamente e não apresente total fechado sem explicar premissas, memória de cálculo e limites legais.",
    "Pesquisa e Comparação de Veículos": "Compare preço, custo de uso, manutenção, consumo, seguro, histórico, finalidade e risco da compra.",
    "Análise Imobiliária": "Avalie preço, localização, documentação, custos, financiamento, estado do imóvel, liquidez e riscos.",
    "Análise de Compras Pessoais de Alto Valor": "Compare necessidade, orçamento, custo total, garantia, alternativas, depreciação e impacto financeiro.",
    "Planejamento de Viagens e Orçamento": "Organize destino, datas, perfil, transporte, hospedagem, alimentação, atividades, margem de segurança e orçamento.",
    "Análise de Tendências Profissionais e Carreiras": "Relacione perfil, habilidades, mercado, caminhos, lacunas e plano de desenvolvimento.",
    "Planejamento de Estudos e Qualificação Profissional": "Monte objetivo, trilha, materiais, cronograma, prática, revisão e acompanhamento.",
    "Organização Financeira Pessoal": "Mapeie renda, despesas, dívidas, reservas, metas, orçamento e rotina de acompanhamento.",
    "Planejamento de Treinos para Academia": "Considere objetivo, nível, frequência, equipamentos, limitações, recuperação e progressão segura.",
    "Planejamento de Exercícios em Casa": "Considere espaço, equipamentos, nível, objetivo, tempo, limitações e progressão segura.",
    "Análise de Alimentação e Rotina Fitness": "Analise hábitos, objetivo, rotina e dificuldades; não prescreva dieta clínica e encaminhe quando necessário.",
    "Análise Estatística Esportiva para Apostas": "Analise dados e incerteza sem prometer ganho; destaque variância, risco financeiro e jogo responsável.",
    "Pilates para Fazer em Casa": "Crie prática doméstica segura conforme nível, objetivo, tempo, acessórios e limitações; explique execução e cuidados.",
    "Yoga para Fazer em Casa": "Crie sequência de posturas, respiração e relaxamento conforme nível, objetivo, duração e limitações.",
    "Cronograma Capilar Personalizado": "Investigue tipo e estado do cabelo, química, lavagem e calor; organize hidratação, nutrição e reconstrução com frequência segura.",
    "Cuidados com a Pele em Casa": "Investigue tipo de pele, sensibilidade, objetivo e produtos; monte rotina simples de manhã, noite e proteção solar, evitando misturas arriscadas.",
    "Plano de Treino Esportivo": "Considere modalidade, objetivo, nível, calendário, equipamentos, recuperação e limitações.",
    "Preparação para Corrida": "Considere experiência, distância atual, meta, frequência, ritmo, lesões, descanso e progressão gradual.",
    "Plano de Alongamento e Mobilidade": "Considere regiões limitadas, rotina, objetivo, dor e modalidade; diferencie mobilidade, alongamento e recuperação.",
    "Preparação Física para Esportes": "Adapte força, potência, resistência, mobilidade e recuperação à modalidade, nível e calendário.",
}


@dataclass(frozen=True)
class BrainResult:
    text: str
    provider: str
    model: str


def _operation_instructions(operation: str | None) -> str:
    if not operation:
        return "O usuário não selecionou uma operação. Identifique a intenção naturalmente pela conversa."
    guidance = OPERATION_GUIDANCE.get(operation, "Use a operação selecionada como contexto principal e conduza uma análise prática e segura.")
    return f"Operação ativa: {operation}. Orientação específica: {guidance}"


def build_system_prompt(operation: str | None) -> str:
    return f"{DOMNAI_CORE_INSTRUCTIONS}\n\nCONTEXTO DA OPERAÇÃO\n{_operation_instructions(operation)}"


def _normalized_history(history: list[dict], limit: int = 10) -> list[dict]:
    normalized = []
    for item in history[-limit:]:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        normalized.append({"role": role, "content": content[:6000]})
    return normalized


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int = 75) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    transient_codes = {500, 502, 503, 504}

    for attempt in range(2):
        http_request = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            # Consume the response body for connection reuse, but never expose provider
            # internals, request IDs or raw JSON in the user-facing chat.
            exc.read()
            if exc.code in transient_codes and attempt == 0:
                continue
            if exc.code in transient_codes:
                raise RuntimeError(
                    "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."
                ) from exc
            raise RuntimeError(
                "Não foi possível processar esta solicitação no momento. Tente novamente."
            ) from exc
        except error.URLError as exc:
            if attempt == 0:
                continue
            raise RuntimeError(
                "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."
            ) from exc

    raise RuntimeError(
        "O serviço de inteligência está temporariamente indisponível. Tente novamente em alguns segundos."
    )


def _integration_api_key() -> str:
    return (
        os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY", "").strip()
        or os.getenv("AI_INTEGRATION_OPENAI_API_KEY", "").strip()
    )


def _integration_base_url() -> str:
    return (
        os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "").strip()
        or os.getenv("AI_INTEGRATION_OPENAI_BASE_URL", "").strip()
    ).rstrip("/")


def _gateway_response(message: str, history: list[dict], operation: str | None) -> BrainResult:
    api_key = _integration_api_key()
    base_url = _integration_base_url()
    if not api_key or not base_url:
        raise RuntimeError("Integração OpenAI do gateway não configurada.")

    model = os.getenv("DOMNAI_GATEWAY_MODEL", "gpt-4o-mini").strip()
    messages = [{"role": "system", "content": build_system_prompt(operation)}]
    messages.extend(_normalized_history(history))
    messages.append({"role": "user", "content": message})

    data = _post_json(
        f"{base_url}/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 1200},
    )

    choices = data.get("choices") or []
    text = ""
    if choices:
        text = str((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError("O gateway não retornou uma resposta em texto.")
    return BrainResult(text=text, provider="replit-openai-gateway", model=model)


def _openai_response(message: str, history: list[dict], operation: str | None) -> BrainResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada.")

    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()
    input_messages = _normalized_history(history)
    input_messages.append({"role": "user", "content": message})
    payload = {
        "model": model,
        "instructions": build_system_prompt(operation),
        "input": input_messages,
        "temperature": 0.2,
        "max_output_tokens": 1800,
    }
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload,
    )

    text = str(data.get("output_text", "")).strip()
    if not text:
        parts = []
        for output in data.get("output", []):
            for content in output.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("O provedor não retornou uma resposta em texto.")
    return BrainResult(text=text, provider="openai", model=model)


def _anthropic_response(message: str, history: list[dict], operation: str | None) -> BrainResult:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada.")

    model = os.getenv("DOMNAI_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip()
    messages = _normalized_history(history)
    messages.append({"role": "user", "content": message})
    payload = {
        "model": model,
        "system": build_system_prompt(operation),
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        payload,
    )
    text = "\n".join(
        str(item.get("text", "")).strip()
        for item in data.get("content", [])
        if item.get("type") == "text" and item.get("text")
    ).strip()
    if not text:
        raise RuntimeError("O provedor não retornou uma resposta em texto.")
    return BrainResult(text=text, provider="anthropic", model=model)


def generate_domnai_response(message: str, history: list[dict], operation: str | None) -> BrainResult:
    provider = os.getenv("DOMNAI_AI_PROVIDER", "auto").strip().lower()

    if provider == "gateway":
        return _gateway_response(message, history, operation)
    if provider == "openai":
        return _openai_response(message, history, operation)
    if provider == "anthropic":
        return _anthropic_response(message, history, operation)
    if provider not in {"", "auto"}:
        raise RuntimeError("DOMNAI_AI_PROVIDER inválido. Use gateway, openai, anthropic ou auto.")

    if _integration_api_key() and _integration_base_url():
        return _gateway_response(message, history, operation)
    if os.getenv("OPENAI_API_KEY", "").strip():
        return _openai_response(message, history, operation)
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return _anthropic_response(message, history, operation)
    raise RuntimeError("Nenhum provedor de inteligência foi configurado.")
