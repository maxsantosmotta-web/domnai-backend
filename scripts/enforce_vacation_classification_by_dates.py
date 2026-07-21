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
helper = '''\n\ndef _is_explicit_topic_switch(message: str) -> bool:\n    normalized = " ".join(\n        "".join(\n            char if char.isalnum() or char.isspace() else " "\n            for char in _normalized_text(message)\n        ).split()\n    )\n    markers = (\n        "vamos mudar de assunto",\n        "vou mudar de assunto",\n        "mudando de assunto",\n        "quero mudar de assunto",\n        "quero falar de outra coisa",\n        "vamos falar de outra coisa",\n        "agora outro assunto",\n        "encerra esse assunto",\n        "deixa esse assunto",\n        "nao quero mais falar disso",\n        "vou mudar de ramo de atividades",\n    )\n    return any(marker in normalized for marker in markers)\n'''
anchor = '\n\ndef _specialized_engine('
if '_is_explicit_topic_switch' not in orchestrator:
    if anchor not in orchestrator:
        raise RuntimeError('specialized engine anchor not found')
    orchestrator = orchestrator.replace(anchor, helper + anchor, 1)

old_route = '''    if _specialized_engine({}, operation, message) is None:
        base_result = generate_metered_response(
            message=message,
            history=history,
            operation=operation,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
        )
'''
new_route = '''    if _is_explicit_topic_switch(message):
        base_result = generate_metered_response(
            message=message,
            history=[],
            operation=None,
            attachments=safe_attachments,
            diagnosis_state=None,
        )
        return MeteredBrainResult(
            text=base_result.text,
            provider=f"topic-switch:{base_result.provider}",
            model=base_result.model,
            input_tokens=base_result.input_tokens,
            output_tokens=base_result.output_tokens,
            cached_input_tokens=base_result.cached_input_tokens,
            diagnosis_state=base_result.diagnosis_state,
            timings={"orchestrator_ms": 0, **(base_result.timings or {})},
        )

    if _specialized_engine({}, operation, message) is None:
        base_result = generate_metered_response(
            message=message,
            history=history,
            operation=operation,
            attachments=safe_attachments,
            diagnosis_state=diagnosis_state,
        )
'''
orchestrator = replace_once(orchestrator, old_route, new_route, 'explicit topic switch routing')
orchestrator_path.write_text(orchestrator, encoding='utf-8')

print('Classificação de férias e troca explícita de assunto aplicadas no runtime final.')
