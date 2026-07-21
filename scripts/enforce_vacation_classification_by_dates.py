from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


termination_path = Path('/app/app/services/labor_termination.py')
termination = termination_path.read_text(encoding='utf-8')

old_classification = '''    resolved_completed = max(paid_periods, taken_periods)
    outstanding_completed = max(0, completed_periods - resolved_completed)
    overdue_periods = 0
    if overdue_periods_raw is not None:
        overdue_periods = max(0, min(outstanding_completed, overdue_periods_raw))
        unclassified_completed = max(0, completed_periods - overdue_periods - resolved_completed)
        if unclassified_completed > 0 and paid_periods_raw is None and taken_periods_raw is None:
            return LaborCalculationResult(False, ["vacation_history_for_remaining_completed_periods"])

    regular_completed_periods = max(0, outstanding_completed - overdue_periods)
    overdue_vacation_base = _money(base * Decimal(overdue_periods) * Decimal("2"))
    regular_completed_vacation_base = _money(base * Decimal(regular_completed_periods))
'''

new_classification = '''    resolved_completed = max(paid_periods, taken_periods)
    outstanding_completed = max(0, completed_periods - resolved_completed)

    # Classificação jurídica pelas datas, não pelo rótulo usado pelo usuário.
    # Para cada período aquisitivo completo, o prazo concessivo termina 12 meses
    # depois. Consideramos quitados/gozados primeiro os períodos mais antigos.
    expired_completed_periods = 0
    for period_index in range(completed_periods):
        acquisition_start = _add_months(admission, period_index * 12)
        concession_deadline = _add_months(acquisition_start, 24) - timedelta(days=1)
        if projected_end > concession_deadline:
            expired_completed_periods += 1

    overdue_periods = max(0, expired_completed_periods - resolved_completed)
    overdue_periods = min(outstanding_completed, overdue_periods)
    regular_completed_periods = max(0, outstanding_completed - overdue_periods)

    if overdue_periods_raw is not None and overdue_periods_raw != overdue_periods:
        assumptions.append(
            "A classificação informal de férias vencidas divergiu das datas; "
            "foi aplicada a contagem legal dos períodos aquisitivo e concessivo."
        )

    overdue_vacation_base = _money(base * Decimal(overdue_periods) * Decimal("2"))
    regular_completed_vacation_base = _money(base * Decimal(regular_completed_periods))
'''
termination = replace_once(
    termination,
    old_classification,
    new_classification,
    'date-based vacation classification',
)

termination = replace_once(
    termination,
    '''            "completed_vacation_periods_due": outstanding_completed,
            "overdue_vacation_periods_due": overdue_periods,
''',
    '''            "completed_vacation_periods_due": outstanding_completed,
            "expired_completed_vacation_periods_by_dates": expired_completed_periods,
            "overdue_vacation_periods_due": overdue_periods,
''',
    'vacation date classification report field',
)

termination = replace_once(
    termination,
    '''            "vacation_rule": "Cada período mensal completo ou fração final de 15 dias ou mais conta 1/12 dentro do período aquisitivo.",
''',
    '''            "vacation_rule": "Férias proporcionais seguem o período aquisitivo. Um período completo é integral adquirido durante o prazo concessivo e só é vencido após o término desse prazo sem quitação ou gozo.",
''',
    'vacation rule description',
)
termination_path.write_text(termination, encoding='utf-8')


pipeline_path = Path('/app/app/services/labor_pipeline.py')
pipeline = pipeline_path.read_text(encoding='utf-8')
start = pipeline.index('def _labor_response_matches_report(')
end = pipeline.index('\n\ndef generate_labor_response(', start)
strict_validator = '''def _labor_response_matches_report(text: str, report: dict) -> bool:
    inputs = report.get("inputs") or {}
    amounts = report.get("amounts") or {}
    normalized = " ".join(str(text or "").casefold().split())
    required = [
        str(inputs.get("notice_days") or ""),
        _money_pt(amounts.get("notice_indemnity")).casefold(),
        _money_pt(amounts.get("estimated_direct_total_before_statutory_tax_withholding")).casefold(),
    ]
    if not all(item and item in normalized for item in required):
        return False

    overdue = int(amounts.get("overdue_vacation_periods_due") or 0)
    regular = int(amounts.get("regular_completed_vacation_periods_due") or 0)
    mentions_overdue = "férias vencid" in normalized or "ferias vencid" in normalized
    mentions_regular = any(
        marker in normalized
        for marker in (
            "férias integrais",
            "ferias integrais",
            "férias adquiridas",
            "ferias adquiridas",
        )
    )

    if overdue == 0 and mentions_overdue:
        return False
    if overdue > 0 and not mentions_overdue:
        return False
    if regular > 0 and not mentions_regular:
        return False
    return True
'''
pipeline = pipeline[:start] + strict_validator.rstrip() + pipeline[end:]
pipeline_path.write_text(pipeline, encoding='utf-8')


orchestrator_path = Path('/app/app/services/orchestrated_brain.py')
orchestrator = orchestrator_path.read_text(encoding='utf-8')

# REGRA ABSOLUTA DE ROTEAMENTO:
# - a mensagem atual e o plano semântico decidem;
# - a operação selecionada é apenas contexto para o planejador;
# - a operação isolada nunca força um especialista;
# - conversa geral nunca recebe o rótulo da operação na geração final.
engine_start = orchestrator.index('def _specialized_engine(')
engine_end = orchestrator.index('\n\ndef generate_orchestrated_response(', engine_start)
message_first_engine = '''def _specialized_engine(plan: dict, operation: str | None, message: str) -> str | None:
    del operation
    engine_text = _normalized_text(plan.get("specialized_engine"))
    message_text = _normalized_text(message)

    if any(marker in engine_text for marker in ("labor_termination", "rescisao", "trabalhista", "labor")):
        return "labor_termination"

    explicit_labor_requests = (
        "calcular minha rescisao",
        "calculo de rescisao",
        "recalcular minha rescisao",
        "revisar calculo trabalhista",
        "verbas rescisorias",
        "demissao sem justa causa",
        "pedido de demissao",
        "aviso previo proporcional",
        "ferias proporcionais na rescisao",
        "decimo terceiro proporcional na rescisao",
    )
    if any(marker in message_text for marker in explicit_labor_requests):
        return "labor_termination"

    return None
'''
orchestrator = orchestrator[:engine_start] + message_first_engine.rstrip() + orchestrator[engine_end:]

generate_start = orchestrator.index('def generate_orchestrated_response(')
api_key_anchor = orchestrator.index('    api_key = os.getenv("OPENAI_API_KEY", "").strip()', generate_start)
light_anchor = orchestrator.rfind('    if _is_light_conversation(message, safe_attachments):', generate_start, api_key_anchor)
if light_anchor < 0:
    raise RuntimeError('bloco de conversa leve não encontrado')
light_return = orchestrator.index('        return _light_conversation_response(', light_anchor)
light_return_end = orchestrator.index('\n', light_return) + 1
orchestrator = orchestrator[:light_return_end] + '\n' + orchestrator[api_key_anchor:]

old_general = '''    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=operation,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )
'''
new_general = '''    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=None,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )
'''
last_general = orchestrator.rfind(old_general)
if last_general >= 0:
    orchestrator = orchestrator[:last_general] + new_general + orchestrator[last_general + len(old_general):]
elif new_general not in orchestrator:
    raise RuntimeError('rota geral final não encontrada')

for forbidden in (
    'if operation_text == labor_operation:',
    'if _is_explicit_topic_switch(message):',
    'if _specialized_engine({}, operation, message) is None:',
):
    if forbidden in orchestrator:
        raise RuntimeError(f'regra antiga permaneceu no runtime: {forbidden}')

for required in (
    'del operation',
    'engine = _specialized_engine(plan, operation, message)',
    'operation=None,',
):
    if required not in orchestrator:
        raise RuntimeError(f'regra message-first ausente: {required}')

orchestrator_path.write_text(orchestrator, encoding='utf-8')


# O planejador não pode transformar a seleção visual em intenção atual.
planner_path = Path('/app/app/services/intelligence_orchestrator.py')
planner = planner_path.read_text(encoding='utf-8')
planner = replace_once(
    planner,
    '- Se a operação ativa ou a intenção real for cálculo de rescisão trabalhista, use exatamente specialized_engine="labor_termination".',
    '- A operação ativa é apenas uma preferência visual e nunca basta para escolher motor. Use specialized_engine="labor_termination" somente quando a mensagem atual, interpretada com o histórico recente, mostrar que o usuário quer tratar de rescisão trabalhista agora.',
    'planner operation authority',
)
planner = replace_once(
    planner,
    '- Entenda intenção, não apenas palavras isoladas ou o nome enviado pelo frontend.',
    '''- Entenda a intenção atual, não apenas palavras isoladas, memória antiga ou o nome enviado pelo frontend.
- A mensagem atual tem prioridade sobre histórico, memória e operação; esses elementos só ajudam a resolver referências e continuidade.
- Sofrimento emocional e possível risco à vida têm prioridade absoluta sobre qualquer operação, relatório, cálculo ou especialista.
- Quando o usuário pedir conversa, conselho ou apoio pessoal, primeiro escute e faça no máximo uma pergunta aberta; não entregue relatório, plano ou lista antes de entender.
- Não trate uma mudança semântica de assunto como continuação automática da tarefa anterior.
- Para números, estatísticas, leis, preços ou fatos atuais, planeje pesquisa verificável ou exija linguagem explicitamente cautelosa; nunca aceite precisão sem evidência.''',
    'planner global priority policy',
)
for required in (
    'A operação ativa é apenas uma preferência visual',
    'A mensagem atual tem prioridade sobre histórico, memória e operação',
    'Sofrimento emocional e possível risco à vida têm prioridade absoluta',
    'nunca aceite precisão sem evidência',
):
    if required not in planner:
        raise RuntimeError(f'política global ausente no planejador: {required}')
planner_path.write_text(planner, encoding='utf-8')


# A memória semântica não pode transformar a operação visual em estado factual.
memory_path = Path('/app/app/services/diagnosis_memory.py')
memory = memory_path.read_text(encoding='utf-8')
memory = replace_once(
    memory,
    '        "operation": _clean_text(operation or source.get("operation"), 180) or None,',
    '        "operation": None,',
    'memory operation neutrality',
)
memory = replace_once(
    memory,
    '''    # A operação muda o foco, mas não apaga a memória do mesmo problema.
    state = sanitize_diagnosis_state(payload, operation)
    if operation:
        state["operation"] = operation
    return state
''',
    '''    # A operação visual não altera nem reclassifica a memória semântica.
    return sanitize_diagnosis_state(payload)
''',
    'memory load neutrality',
)
memory = replace_once(
    memory,
    '        + "\nREGRAS: respeite correções mais recentes, não repita perguntas registradas como respondidas e trate a operação apenas como foco atual."',
    '        + "\nREGRAS: respeite correções mais recentes, não repita perguntas registradas como respondidas e use esta memória apenas para continuidade; ela nunca decide a intenção da mensagem atual."',
    'memory context authority',
)
memory = replace_once(
    memory,
    '- Preserve contexto útil ao mudar de operação; a operação muda o foco, não reinicia automaticamente o problema.',
    '- Preserve apenas contexto semanticamente compatível com a mensagem atual. Mudança real de assunto interrompe o foco anterior, mesmo que a operação visual permaneça selecionada.',
    'memory topic transition policy',
)
for required in (
    '"operation": None,',
    'ela nunca decide a intenção da mensagem atual',
    'Mudança real de assunto interrompe o foco anterior',
):
    if required not in memory:
        raise RuntimeError(f'neutralidade de memória ausente: {required}')
memory_path.write_text(memory, encoding='utf-8')

print('Regras finais aplicadas: férias por datas, mensagem atual soberana, operação neutra e memória não roteadora.')
