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
        text = str(value).strip()
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
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
Extraia exclusivamente os dados confirmados no caso de rescisão trabalhista, considerando a conversa e a memória. Retorne JSON válido, sem markdown:
{
  "admission_date":"AAAA-MM-DD ou null",
  "termination_communication_date":"AAAA-MM-DD ou null",
  "monthly_salary":"número decimal ou null",
  "termination_reason":"employer_without_cause|employee_resignation|mutual_agreement|just_cause|fixed_term_end|other|null",
  "notice_type":"indemnified|worked|waived|not_informed|null",
  "notice_days_explicit":"inteiro ou null",
  "salary_balance_days":"inteiro ou null",
  "thirteenth_already_paid":"número decimal ou null",
  "vacation_periods_already_paid":"inteiro ou null",
  "vacation_periods_already_taken":"inteiro ou null",
  "variable_pay_average":"número decimal ou null",
  "other_salary_additions":"número decimal ou null",
  "deductions":"número decimal ou null",
  "fgts_information_status":"provided|unavailable|null",
  "fgts_balance":"número decimal ou null"
}

REGRAS
- Não invente, complete ou presuma nenhum valor.
- Use null quando o usuário não confirmou a informação, inclusive quando o valor poderia ser zero.
- Só registre 0 quando o usuário afirmou claramente que não recebeu, não possui ou não existe aquele item.
- Não trate silêncio como ausência de comissão, adicional, desconto, férias pagas ou 13º antecipado.
- notice_days_explicit registra apenas prazo comprovado ou claramente informado; o backend aplicará o prazo legal proporcional quando cabível.
- fgts_information_status=unavailable somente quando o usuário disser que não possui extrato ou saldo; não inferir.
""".strip()


def missing_data_prompt_instructions() -> str:
    return """
Você é o DomnAI conduzindo uma análise real de rescisão trabalhista.
Formule uma resposta natural, curta e contextual para obter somente os dados realmente faltantes indicados pelo backend.
Não siga roteiro fixo, não repita pergunta já respondida, não transforme a conversa em formulário e não exponha nomes técnicos dos campos.
Explique brevemente por que uma confirmação pode alterar o resultado quando isso for útil.
Faça no máximo três perguntas, agrupando informações relacionadas de maneira natural.
Não calcule ainda, não sugira valores e não interprete silêncio como zero.
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
    reason = str(data.get("termination_reason") or "").strip()
    notice_type = str(data.get("notice_type") or "").strip()

    thirteenth_paid = _decimal(data.get("thirteenth_already_paid"))
    paid_periods = _int_or_none(data.get("vacation_periods_already_paid"))
    taken_periods = _int_or_none(data.get("vacation_periods_already_taken"))
    variable = _decimal(data.get("variable_pay_average"))
    additions = _decimal(data.get("other_salary_additions"))
    deductions = _decimal(data.get("deductions"))
    fgts_status = str(data.get("fgts_information_status") or "").strip()
    fgts_balance = _decimal(data.get("fgts_balance"))

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
    if thirteenth_paid is None:
        missing_fields.append("thirteenth_already_paid_or_confirmed_zero")
    if paid_periods is None or taken_periods is None:
        missing_fields.append("vacation_history")
    if variable is None:
        missing_fields.append("variable_pay_average_or_confirmed_zero")
    if additions is None:
        missing_fields.append("salary_additions_or_confirmed_zero")
    if deductions is None:
        missing_fields.append("deductions_or_confirmed_zero")
    if fgts_status not in {"provided", "unavailable"}:
        missing_fields.append("fgts_balance_or_unavailability")
    if fgts_status == "provided" and fgts_balance is None:
        missing_fields.append("fgts_balance")
    if missing_fields:
        return LaborCalculationResult(False, missing_fields[:8])

    assert admission is not None and communication is not None and salary is not None
    assert thirteenth_paid is not None and paid_periods is not None and taken_periods is not None
    assert variable is not None and additions is not None and deductions is not None

    if communication < admission:
        return LaborCalculationResult(False, ["invalid_date_order"])

    base = salary + variable + additions
    employer_termination = reason == "employer_without_cause"

    legal_notice_days = statutory_notice_days(admission, communication)
    explicit_notice_days = _int_or_none(data.get("notice_days_explicit"))
    if employer_termination:
        notice_days = legal_notice_days
        notice_days_source = "statutory_proportional"
    elif explicit_notice_days is not None:
        notice_days = max(0, min(90, explicit_notice_days))
        notice_days_source = "explicitly_informed"
    else:
        notice_days = 30 if notice_type in {"indemnified", "worked"} else 0
        notice_days_source = "default_non_employer_termination"

    projected_end = communication
    notice_amount = Decimal("0")
    if notice_type == "indemnified" and employer_termination:
        projected_end = communication + timedelta(days=notice_days)
        notice_amount = _money(base / Decimal("30") * Decimal(notice_days))
    elif notice_type == "worked":
        projected_end = communication + timedelta(days=notice_days)

    balance_days_raw = _int_or_none(data.get("salary_balance_days"))
    balance_days = communication.day if balance_days_raw is None else balance_days_raw
    balance_days = max(0, min(30, balance_days))
    salary_balance = _money(base / Decimal("30") * Decimal(balance_days))

    thirteenth_avos = thirteenth_months(admission, projected_end)
    thirteenth_gross = _money(base * Decimal(thirteenth_avos) / Decimal("12"))
    thirteenth_due = _money(max(Decimal("0"), thirteenth_gross - thirteenth_paid))

    completed_periods, vacation_avos, current_period_start = vacation_position(admission, projected_end)
    paid_periods = max(0, paid_periods)
    taken_periods = max(0, taken_periods)
    outstanding_completed = max(0, completed_periods - max(paid_periods, taken_periods))
    completed_vacation_base = _money(base * Decimal(outstanding_completed))
    proportional_vacation_base = _money(base * Decimal(vacation_avos) / Decimal("12"))
    vacation_base_due = completed_vacation_base + proportional_vacation_base
    vacation_third = _money(vacation_base_due / Decimal("3"))

    direct_total = _money(
        salary_balance
        + notice_amount
        + thirteenth_due
        + vacation_base_due
        + vacation_third
        - deductions
    )

    fgts_penalty = (
        _money(fgts_balance * Decimal("0.40"))
        if fgts_status == "provided" and fgts_balance is not None and employer_termination
        else None
    )

    report = {
        "inputs": {
            "admission_date": admission.isoformat(),
            "termination_communication_date": communication.isoformat(),
            "projected_contract_end": projected_end.isoformat(),
            "monthly_salary": str(_money(salary)),
            "variable_pay_average": str(_money(variable)),
            "other_salary_additions": str(_money(additions)),
            "calculation_base": str(_money(base)),
            "termination_reason": reason,
            "notice_type": notice_type,
            "notice_days": notice_days,
            "notice_days_source": notice_days_source,
            "legal_notice_days": legal_notice_days,
        },
        "rules_applied": {
            "notice_projection_applied": notice_type in {"indemnified", "worked"},
            "notice_rule": "Na dispensa sem justa causa pelo empregador, o prazo foi calculado proporcionalmente ao tempo de serviço, limitado a 90 dias.",
            "thirteenth_rule": "Cada mês civil com 15 dias ou mais de contrato conta 1/12.",
            "vacation_rule": "Cada período mensal completo ou fração final de 15 dias ou mais conta 1/12.",
            "unconfirmed_values_assumed_zero": False,
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
            "deductions_confirmed": str(_money(deductions)),
            "estimated_direct_total_before_statutory_tax_withholding": str(direct_total),
            "fgts_information_status": fgts_status,
            "fgts_balance_informed": str(_money(fgts_balance)) if fgts_balance is not None else None,
            "fgts_40_percent_penalty": str(fgts_penalty) if fgts_penalty is not None else None,
        },
        "limitations": [
            "O total direto não inclui cálculo definitivo de INSS, IRRF, convenção coletiva, multas específicas ou fatos não apresentados.",
            "O saldo e a multa do FGTS só são exatos quando o saldo da conta vinculada é informado a partir do extrato.",
            "O resultado deve ser confrontado com o TRCT, holerites, extrato do FGTS e documentos da empresa antes de qualquer medida jurídica.",
        ],
    }
    return LaborCalculationResult(True, [], report)


def render_instructions() -> str:
    return """
Você é o redator final do cálculo de rescisão do DomnAI. Use exclusivamente o relatório determinístico fornecido pelo backend.
Não altere datas, avos, fórmulas, prazo de aviso ou valores. Não recalcule por conta própria.
Apresente em português claro: dados confirmados, base remuneratória, projeção do aviso, memória de cálculo por verba, total direto, FGTS separado e limitações.
Destaque quando o aviso legal proporcional for diferente do prazo inicialmente citado pelo usuário.
Nunca chame estimativa de valor definitivo. Quando o FGTS estiver indisponível, diga que essa parcela não foi fechada.
Não mencione JSON, backend, modelo ou processo interno.
""".strip()
