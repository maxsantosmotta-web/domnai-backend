from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

OPERATION = "Cálculo de Rescisão Trabalhista"
CENT = Decimal("0.01")


@dataclass(frozen=True)
class LaborCalculationResult:
    ready: bool
    missing_fields: list[str]
    report: dict[str, Any] | None = None


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(".", "").replace(",", ".") if isinstance(value, str) and "," in value else str(value))
    except (InvalidOperation, ValueError):
        return None


def _date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for order in ("iso", "br"):
        try:
            if order == "iso":
                return date.fromisoformat(text)
            day, month, year = [int(part) for part in text.split("/")]
            return date(year, month, day)
        except (ValueError, TypeError):
            continue
    return None


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _completed_years(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return max(0, years)


def statutory_notice_days(admission: date, communication: date) -> int:
    completed = _completed_years(admission, communication)
    return min(90, 30 + (3 * completed))


def _days_in_month_under_contract(start: date, end: date, year: int, month: int) -> int:
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    overlap_start = max(start, month_start)
    overlap_end = min(end, month_end)
    if overlap_end < overlap_start:
        return 0
    return (overlap_end - overlap_start).days + 1


def thirteenth_months(admission: date, projected_end: date) -> int:
    year = projected_end.year
    return sum(
        1
        for month in range(1, 13)
        if _days_in_month_under_contract(admission, projected_end, year, month) >= 15
    )


def vacation_position(admission: date, projected_end: date) -> tuple[int, int, date]:
    completed_periods = 0
    period_start = admission
    while _add_months(period_start, 12) <= projected_end:
        completed_periods += 1
        period_start = _add_months(period_start, 12)

    avos = 0
    cursor = period_start
    for _ in range(12):
        next_cursor = _add_months(cursor, 1)
        period_end = next_cursor - timedelta(days=1)
        if projected_end >= period_end:
            avos += 1
            cursor = next_cursor
            continue
        partial_days = (projected_end - cursor).days + 1 if projected_end >= cursor else 0
        if partial_days >= 15:
            avos += 1
        break
    return completed_periods, min(12, avos), period_start


def extraction_instructions() -> str:
    return """
Extraia exclusivamente os dados do caso de rescisão trabalhista presentes na conversa e na memória. Retorne JSON válido, sem markdown:
{
  "admission_date":"AAAA-MM-DD ou null",
  "termination_communication_date":"AAAA-MM-DD ou null",
  "monthly_salary":"número decimal ou null",
  "termination_reason":"employer_without_cause|employee_resignation|mutual_agreement|just_cause|fixed_term_end|other|null",
  "notice_type":"indemnified|worked|waived|not_informed|null",
  "notice_days":"inteiro ou null",
  "salary_balance_days":"inteiro ou null",
  "thirteenth_already_paid":"número decimal ou 0",
  "vacation_periods_already_paid":"inteiro ou 0",
  "vacation_periods_already_taken":"inteiro ou 0",
  "variable_pay_average":"número decimal ou 0",
  "other_salary_additions":"número decimal ou 0",
  "deductions":"número decimal ou 0",
  "fgts_balance":"número decimal ou null"
}
Não invente dados. Use null quando não estiver confirmado. O salário base para cálculo é salário mensal + médias/adicionais habituais confirmados.
""".strip()


def missing_data_prompt_instructions() -> str:
    return """
Você é o DomnAI conduzindo uma análise real de rescisão trabalhista.
Formule uma resposta natural, curta e contextual para obter somente os dados realmente faltantes indicados pelo backend.
Não siga roteiro fixo, não repita pergunta já respondida, não transforme a conversa em formulário e não enumere campos técnicos.
Explique em uma frase por que a informação é necessária quando isso ajudar o usuário.
Faça no máximo três perguntas objetivas, combinando dados relacionados quando fizer sentido.
Não calcule ainda e não invente nenhum dado.
""".strip()


def parse_extracted_data(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip() if len(lines) >= 3 else text
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def calculate(data: dict[str, Any]) -> LaborCalculationResult:
    admission = _date(data.get("admission_date"))
    communication = _date(data.get("termination_communication_date"))
    salary = _decimal(data.get("monthly_salary"))
    variable = _decimal(data.get("variable_pay_average")) or Decimal("0")
    additions = _decimal(data.get("other_salary_additions")) or Decimal("0")
    reason = str(data.get("termination_reason") or "").strip()
    notice_type = str(data.get("notice_type") or "").strip()

    missing_fields: list[str] = []
    if admission is None:
        missing_fields.append("admission_date")
    if communication is None:
        missing_fields.append("termination_communication_date")
    if salary is None or salary <= 0:
        missing_fields.append("monthly_salary")
    if not reason:
        missing_fields.append("termination_reason")
    if not notice_type:
        missing_fields.append("notice_type")
    if missing_fields:
        return LaborCalculationResult(False, missing_fields[:5])

    assert admission is not None and communication is not None and salary is not None
    if communication < admission:
        return LaborCalculationResult(False, ["invalid_date_order"])

    base = salary + variable + additions
    notice_days_value = data.get("notice_days")
    try:
        notice_days = int(notice_days_value) if notice_days_value is not None else statutory_notice_days(admission, communication)
    except (TypeError, ValueError):
        notice_days = statutory_notice_days(admission, communication)
    notice_days = max(0, min(90, notice_days))

    employer_termination = reason == "employer_without_cause"
    projected_end = communication
    notice_amount = Decimal("0")
    if notice_type == "indemnified" and employer_termination:
        projected_end = communication + timedelta(days=notice_days)
        notice_amount = _money(base / Decimal("30") * Decimal(notice_days))
    elif notice_type == "worked":
        projected_end = communication + timedelta(days=notice_days)

    balance_days_raw = data.get("salary_balance_days")
    if balance_days_raw is None:
        balance_days = communication.day
    else:
        try:
            balance_days = int(balance_days_raw)
        except (TypeError, ValueError):
            balance_days = communication.day
    balance_days = max(0, min(30, balance_days))
    salary_balance = _money(base / Decimal("30") * Decimal(balance_days))

    thirteenth_avos = thirteenth_months(admission, projected_end)
    thirteenth_gross = _money(base * Decimal(thirteenth_avos) / Decimal("12"))
    thirteenth_paid = _decimal(data.get("thirteenth_already_paid")) or Decimal("0")
    thirteenth_due = _money(max(Decimal("0"), thirteenth_gross - thirteenth_paid))

    completed_periods, vacation_avos, current_period_start = vacation_position(admission, projected_end)
    paid_periods = max(0, int(data.get("vacation_periods_already_paid") or 0))
    taken_periods = max(0, int(data.get("vacation_periods_already_taken") or 0))
    outstanding_completed = max(0, completed_periods - max(paid_periods, taken_periods))
    completed_vacation_base = _money(base * Decimal(outstanding_completed))
    proportional_vacation_base = _money(base * Decimal(vacation_avos) / Decimal("12"))
    vacation_base_due = completed_vacation_base + proportional_vacation_base
    vacation_third = _money(vacation_base_due / Decimal("3"))

    deductions = _decimal(data.get("deductions")) or Decimal("0")
    direct_total = _money(
        salary_balance
        + notice_amount
        + thirteenth_due
        + vacation_base_due
        + vacation_third
        - deductions
    )

    fgts_balance = _decimal(data.get("fgts_balance"))
    fgts_penalty = _money(fgts_balance * Decimal("0.40")) if fgts_balance is not None and employer_termination else None

    report = {
        "inputs": {
            "admission_date": admission.isoformat(),
            "termination_communication_date": communication.isoformat(),
            "projected_contract_end": projected_end.isoformat(),
            "monthly_salary": str(_money(salary)),
            "calculation_base": str(_money(base)),
            "termination_reason": reason,
            "notice_type": notice_type,
            "notice_days": notice_days,
        },
        "rules_applied": {
            "notice_projection_applied": notice_type in {"indemnified", "worked"},
            "thirteenth_rule": "Cada mês civil com 15 dias ou mais de contrato conta 1/12.",
            "vacation_rule": "Cada período mensal completo ou fração final de 15 dias ou mais conta 1/12.",
        },
        "amounts": {
            "salary_balance_days": balance_days,
            "salary_balance": str(salary_balance),
            "notice_indemnity": str(notice_amount),
            "thirteenth_avos": thirteenth_avos,
            "thirteenth_gross": str(thirteenth_gross),
            "thirteenth_already_paid": str(_money(thirteenth_paid)),
            "thirteenth_due": str(thirteenth_due),
            "completed_vacation_periods_due": outstanding_completed,
            "current_vacation_period_start": current_period_start.isoformat(),
            "proportional_vacation_avos": vacation_avos,
            "vacation_base_due": str(_money(vacation_base_due)),
            "vacation_one_third": str(vacation_third),
            "deductions_informed": str(_money(deductions)),
            "estimated_direct_total_before_statutory_tax_withholding": str(direct_total),
            "fgts_balance_informed": str(_money(fgts_balance)) if fgts_balance is not None else None,
            "fgts_40_percent_penalty": str(fgts_penalty) if fgts_penalty is not None else None,
        },
        "limitations": [
            "O total direto não inclui cálculo de INSS, IRRF, convenção coletiva, multas específicas ou descontos não informados.",
            "O saldo e a multa do FGTS só são exatos com o extrato da conta vinculada.",
            "O resultado é estimativo e deve ser confrontado com o TRCT e documentos da empresa antes de qualquer medida jurídica.",
        ],
    }
    return LaborCalculationResult(True, [], report)


def render_instructions() -> str:
    return """
Você é o redator final do cálculo de rescisão do DomnAI. Use exclusivamente o relatório determinístico fornecido pelo backend.
Não altere datas, avos, fórmulas nem valores. Não recalcule por conta própria.
Apresente em português claro: dados considerados, projeção do aviso, memória de cálculo por verba, total direto, FGTS separado e limitações.
Nunca chame estimativa de valor definitivo. Quando o FGTS não tiver saldo informado, diga que não pode ser fechado com exatidão.
Não mencione JSON, backend, modelo ou processo interno.
""".strip()
