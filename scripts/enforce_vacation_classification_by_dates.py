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

print('Classificação de férias aplicada por datas e validador final reforçado.')
