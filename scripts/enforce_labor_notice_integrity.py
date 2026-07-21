from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/app")

TERMINATION_PATH = Path('/app/app/services/labor_termination.py')
PIPELINE_PATH = Path('/app/app/services/labor_pipeline.py')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f'{label}: trecho esperado não encontrado')


termination = TERMINATION_PATH.read_text(encoding='utf-8')
termination = replace_once(
    termination,
    '''  "monthly_salary":"número decimal ou null",
''',
    '''  "monthly_salary":"número decimal ou null",
  "monthly_salary_basis":"gross|net|not_informed|null",
''',
    'campo de natureza do salário',
)
termination = replace_once(
    termination,
    '''- Só registre 0 quando o usuário afirmar claramente zero, ausência ou que não recebeu.
- notice_days_explicit registra apenas prazo claramente informado; o backend aplicará o prazo legal proporcional quando cabível.
''',
    '''- Só registre 0 quando o usuário afirmar claramente zero, ausência ou que não recebeu.
- monthly_salary_basis=gross somente quando o usuário confirmar salário bruto, base mensal sem descontos ou valor registrado no contracheque antes dos descontos.
- monthly_salary_basis=net quando o usuário disser salário líquido, limpo, valor recebido em conta, depois dos descontos ou equivalente.
- Nunca transforme salário líquido em bruto e nunca use valor líquido como base de cálculo.
- notice_days_explicit registra apenas prazo claramente informado; o backend aplicará o prazo legal proporcional quando cabível.
''',
    'regras de salário bruto e líquido',
)
termination = replace_once(
    termination,
    '''    salary = _decimal(data.get("monthly_salary"))
    reason = str(data.get("termination_reason") or "").strip()
''',
    '''    salary = _decimal(data.get("monthly_salary"))
    salary_basis = str(data.get("monthly_salary_basis") or "").strip()
    reason = str(data.get("termination_reason") or "").strip()
''',
    'leitura da natureza do salário',
)
termination = replace_once(
    termination,
    '''    if salary is None or salary <= 0:
        missing_fields.append("monthly_salary")
    if not reason:
''',
    '''    if salary is None or salary <= 0:
        missing_fields.append("monthly_salary")
    elif salary_basis != "gross":
        missing_fields.append("gross_monthly_salary")
    if not reason:
''',
    'bloqueio de salário não bruto',
)
termination = replace_once(
    termination,
    '''    if not notice_type:
        missing_fields.append("notice_type")
''',
    '''    # "not_informed" é ausência de dado, não um tipo de aviso válido.
    # Sem essa confirmação o cálculo não pode decidir se existe indenização.
    if notice_type not in {"indemnified", "worked", "waived"}:
        missing_fields.append("notice_type")
''',
    'bloqueio de aviso não confirmado',
)
termination = replace_once(
    termination,
    '''    elif termination is not None and notice_type == "indemnified" and employer_termination:
        notice_amount = _money(base / Decimal("30") * Decimal(notice_days))

    balance_days_raw = _int_or_none(data.get("salary_balance_days"))
''',
    '''    elif termination is not None and notice_type == "indemnified" and employer_termination:
        notice_amount = _money(base / Decimal("30") * Decimal(notice_days))

    # Quando já existe período aquisitivo completo, não é seguro presumir que
    # nenhuma férias foi gozada ou paga. Esse histórico altera diretamente a
    # existência de férias integrais e vencidas.
    completed_periods_preview, _, _ = vacation_position(admission, projected_end)
    if completed_periods_preview > 0 and (
        paid_periods_raw is None or taken_periods_raw is None
    ):
        return LaborCalculationResult(False, ["vacation_history"])

    balance_days_raw = _int_or_none(data.get("salary_balance_days"))
''',
    'bloqueio de histórico de férias ausente',
)
termination = replace_once(
    termination,
    '''Faça no máximo duas perguntas curtas e contextualizadas.
Dados complementares que não impedem uma estimativa inicial não devem bloquear a conversa.
''',
    '''Faça no máximo duas perguntas curtas e contextualizadas.
- Se missing_fields contiver gross_monthly_salary, explique que valor líquido recebido em conta não pode ser usado e peça somente o salário bruto mensal antes dos descontos.
- Se missing_fields contiver notice_type, pergunte claramente se o aviso-prévio foi trabalhado, indenizado ou dispensado.
- Se missing_fields contiver vacation_history, pergunte se houve férias integrais já gozadas ou pagas e quantos períodos; aceite "nenhuma" como zero confirmado.
- Agrupe no mesmo turno os campos indispensáveis ainda ausentes, sem repetir o que já foi confirmado.
Dados complementares que não impedem uma estimativa inicial não devem bloquear a conversa, mas salário bruto, aviso e histórico de férias são indispensáveis quando alteram diretamente as verbas.
''',
    'perguntas obrigatórias de salário, aviso e férias',
)
TERMINATION_PATH.write_text(termination, encoding='utf-8')


pipeline = PIPELINE_PATH.read_text(encoding='utf-8')
notice_helper = '''def _notice_line(report: dict) -> str:
    inputs = report.get("inputs") or {}
    amounts = report.get("amounts") or {}
    notice_type = str(inputs.get("notice_type") or "").strip()
    notice_days = int(inputs.get("notice_days") or 0)
    if notice_type == "indemnified":
        return f"- Aviso-prévio indenizado ({notice_days} dias): {_money_pt(amounts.get('notice_indemnity'))}"
    if notice_type == "worked":
        return f"- Aviso-prévio trabalhado ({notice_days} dias): sem indenização separada"
    if notice_type == "waived":
        return "- Aviso-prévio dispensado: sem indenização separada"
    raise RuntimeError("Relatório trabalhista pronto sem tipo de aviso confirmado.")


'''
if 'def _notice_line(report: dict)' not in pipeline:
    anchor = 'def _deterministic_labor_answer(report: dict) -> str:\n'
    if anchor not in pipeline:
        raise RuntimeError('âncora da resposta trabalhista determinística não encontrada')
    pipeline = pipeline.replace(anchor, notice_helper + anchor, 1)

pipeline = replace_once(
    pipeline,
    '''        f"- Aviso-prévio indenizado ({notice_days} dias): {_money_pt(amounts.get('notice_indemnity'))}",
''',
    '''        _notice_line(report),
''',
    'linha dinâmica do aviso-prévio',
)

start = pipeline.index('def _labor_response_matches_report(')
end = pipeline.index('\n\ndef generate_labor_response(', start)
validator = '''def _labor_response_matches_report(text: str, report: dict) -> bool:
    inputs = report.get("inputs") or {}
    amounts = report.get("amounts") or {}
    normalized = " ".join(str(text or "").casefold().split())
    notice_type = str(inputs.get("notice_type") or "").strip()
    notice_days = str(inputs.get("notice_days") or "")

    required = [
        _money_pt(amounts.get("estimated_direct_total_before_statutory_tax_withholding")).casefold(),
    ]
    if notice_type == "indemnified":
        required.extend([
            notice_days,
            "aviso-prévio indenizado",
            _money_pt(amounts.get("notice_indemnity")).casefold(),
        ])
    elif notice_type == "worked":
        required.extend([notice_days, "aviso-prévio trabalhado"])
        if "aviso-prévio indenizado" in normalized:
            return False
    elif notice_type == "waived":
        required.append("aviso-prévio dispensado")
        if "aviso-prévio indenizado" in normalized:
            return False
    else:
        return False

    if not all(item and item in normalized for item in required):
        return False

    overdue = int(amounts.get("overdue_vacation_periods_due") or 0)
    regular = int(amounts.get("regular_completed_vacation_periods_due") or 0)
    mentions_overdue = "férias vencid" in normalized or "ferias vencid" in normalized
    mentions_regular = any(
        marker in normalized
        for marker in (
            "férias integrais", "ferias integrais",
            "férias adquiridas", "ferias adquiridas",
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
pipeline = pipeline[:start] + validator.rstrip() + pipeline[end:]
PIPELINE_PATH.write_text(pipeline, encoding='utf-8')


from app.services.labor_termination import calculate
from app.services.labor_pipeline import _deterministic_labor_answer

minimal_case = {
    'admission_date': '2025-04-01',
    'termination_date': '2026-05-17',
    'monthly_salary': '2134',
    'termination_reason': 'employer_without_cause',
}

net_salary = calculate({
    **minimal_case,
    'monthly_salary_basis': 'net',
    'notice_type': 'indemnified',
    'vacation_periods_already_paid': 0,
    'vacation_periods_already_taken': 0,
})
if net_salary.ready or 'gross_monthly_salary' not in net_salary.missing_fields:
    raise RuntimeError('salário líquido ainda permitiu cálculo trabalhista')

unknown_notice = calculate({**minimal_case, 'monthly_salary_basis': 'gross', 'notice_type': 'not_informed'})
if unknown_notice.ready or 'notice_type' not in unknown_notice.missing_fields:
    raise RuntimeError('aviso não informado ainda permitiu cálculo trabalhista')

unknown_vacation = calculate({**minimal_case, 'monthly_salary_basis': 'gross', 'notice_type': 'indemnified'})
if unknown_vacation.ready or 'vacation_history' not in unknown_vacation.missing_fields:
    raise RuntimeError('histórico de férias ausente ainda permitiu cálculo trabalhista')

base_case = {
    **minimal_case,
    'monthly_salary_basis': 'gross',
    'vacation_periods_already_paid': 0,
    'vacation_periods_already_taken': 0,
}

indemnified = calculate({**base_case, 'notice_type': 'indemnified'})
if not indemnified.ready or not indemnified.report:
    raise RuntimeError('caso indenizado válido não ficou pronto')
if indemnified.report['amounts']['notice_indemnity'] != '2347.40':
    raise RuntimeError('indenização de 33 dias divergiu do valor determinístico esperado')
indemnified_text = _deterministic_labor_answer(indemnified.report)
if 'Aviso-prévio indenizado (33 dias): R$ 2.347,40' not in indemnified_text:
    raise RuntimeError('resposta indenizada não refletiu tipo e valor corretos')

worked = calculate({**base_case, 'notice_type': 'worked'})
if not worked.ready or not worked.report:
    raise RuntimeError('caso trabalhado válido não ficou pronto')
worked_text = _deterministic_labor_answer(worked.report)
if 'Aviso-prévio trabalhado (33 dias): sem indenização separada' not in worked_text:
    raise RuntimeError('resposta de aviso trabalhado foi rotulada incorretamente')
if 'Aviso-prévio indenizado' in worked_text:
    raise RuntimeError('aviso trabalhado ainda foi apresentado como indenizado')

print('Salário bruto, aviso e histórico de férias validados antes do cálculo.')