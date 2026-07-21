from __future__ import annotations

from pathlib import Path


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


# Teste executável do caso que falhou em produção. Não é busca por marcador:
# importa o runtime final e executa cálculo + renderização determinística.
from app.services.labor_termination import calculate
from app.services.labor_pipeline import _deterministic_labor_answer

base_case = {
    'admission_date': '2025-04-01',
    'termination_date': '2026-05-17',
    'monthly_salary': '2134',
    'termination_reason': 'employer_without_cause',
    'vacation_periods_already_paid': 0,
    'vacation_periods_already_taken': 0,
}

unknown = calculate({**base_case, 'notice_type': 'not_informed'})
if unknown.ready or 'notice_type' not in unknown.missing_fields:
    raise RuntimeError('aviso não informado ainda permitiu cálculo trabalhista')

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

print('Integridade do aviso-prévio validada por execução real do cálculo e da resposta.')
