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


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().casefold()
    if normalized in {"true", "sim", "yes", "1"}:
        return True
    if normalized in {"false", "não", "nao", "no", "0"}:
        return False
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
Extraia os dados confirmados no caso de rescisão trabalhista usando toda a conversa e a memória. Entenda linguagem natural, respostas curtas, correções e formas equivalentes de dizer a mesma coisa. Retorne JSON válido, sem markdown:
{
  "admission_date":"AAAA-MM-DD ou null",
  "termination_communication_date":"AAAA-MM-DD ou null",
  "monthly_salary":"número decimal ou null",
  "termination_reason":"employer_without_cause|employee_resignation|mutual_agreement|just_cause|fixed_term_end|other|null",
  "notice_type":"indemnified|worked|waived|not_informed|null",
  "notice_days_explicit":"inteiro ou null",
  "salary_balance_days":"inteiro ou null",
  "thirteenth_already_paid":"número decimal ou null",
  "thirteenth_proportional_months":"inteiro de 0 a 12 ou null",
  "thirteenth_pending":"boolean ou null",
  "vacation_periods_already_paid":"inteiro ou null",
  "vacation_periods_already_taken":"inteiro ou null",
  "vacation_proportional_months":"inteiro de 0 a 12 ou null",
  "vacation_proportional_pending":"boolean ou null",
  "variable_pay_average":"número decimal ou null",
  "other_salary_additions":"número decimal ou null",
  "deductions":"número decimal ou null",
  "fgts_information_status":"provided|unavailable|null",
  "fgts_balance":"número decimal ou null"
}

REGRAS
- Não invente datas, valores ou fatos.
- Interprete o sentido da resposta, não apenas palavras exatas.
- Nunca copie automaticamente a mesma quantidade de avos para férias e 13º. Férias seguem o período aquisitivo iniciado na admissão; o 13º segue exclusivamente o ano civil da data final projetada do contrato.
- Preencha thirteenth_proportional_months somente quando o usuário informar de forma inequívoca os avos referentes ao ano civil da rescisão. Uma quantidade que represente todo o tempo de contrato, atravesse a virada do ano ou tenha sido dita conjuntamente para férias e décimo não deve ser usada como avos do 13º.
- Uma eventual pendência de 13º de ano anterior não deve ser somada aos avos do ano da rescisão; apenas marque thirteenth_pending como true e preserve os avos do ano anterior separados na conversa.
- Quando o usuário disser que uma verba está pendente, não pergunte novamente se ela foi paga sem existir contradição real.
- Uma correção mais recente do usuário substitui informação anterior incompatível.
- Use null quando a informação realmente não estiver disponível.
- Só registre 0 quando o usuário afirmar claramente zero, ausência ou que não recebeu.
- notice_days_explicit registra apenas prazo claramente informado; o backend aplicará o prazo legal proporcional quando cabível.
- fgts_information_status=unavailable somente quando o usuário disser que não possui extrato ou saldo.
""".strip()


def missing_data_prompt_instructions() -> str:
    return """
Você é o DomnAI conduzindo uma conversa natural sobre rescisão trabalhista.
Peça somente os dados essenciais realmente ausentes indicados pelo backend.
Antes de perguntar, confira known_data, a mensagem atual e o plano para não repetir informação já fornecida de outra forma.
Aceite respostas equivalentes, correções e linguagem informal, mas trate férias e 13º como verbas com calendários diferentes.
Não siga roteiro fixo, não transforme a conversa em formulário e não exponha nomes técnicos dos campos.
Faça no máximo duas perguntas curtas e contextualizadas.
Dados complementares que não impedem uma estimativa inicial não devem bloquear a conversa.
Não calcule valores nesta etapa e não interprete silêncio como confirmação.
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

    thirteenth_paid_raw = _decimal(data.get("thirteenth_already_paid"))
    thirteenth_pending = _bool_or_none(data.get("thirteenth_pending"))
    explicit_thirteenth_avos = _int_or_none(data.get("thirteenth_proportional_months"))

    paid_periods_raw = _int_or_none(data.get("vacation_periods_already_paid"))
    taken_periods_raw = _int_or_none(data.get("vacation_periods_already_taken"))
    vacation_pending = _bool_or_none(data.get("vacation_proportional_pending"))
    explicit_vacation_avos = _int_or_none(data.get("vacation_proportional_months"))

    variable_raw = _decimal(data.get("variable_pay_average"))
    additions_raw = _decimal(data.get("other_salary_additions"))
    deductions_raw = _decimal(data.get("deductions"))
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
    if missing_fields:
        return LaborCalculationResult(False, missing_fields)

    assert admission is not None and communication is not None and salary is not None
    if communication < admission:
        return LaborCalculationResult(False, ["invalid_date_order"])

    assumptions: list[str] = []
    variable = variable_raw if variable_raw is not None else Decimal("0")
    additions = additions_raw if additions_raw is not None else Decimal("0")
    deductions = deductions_raw if deductions_raw is not None else Decimal("0")
    if variable_raw is None:
        assumptions.append("Média de remuneração variável não informada; não incluída nesta estimativa.")
    if additions_raw is None:
        assumptions.append("Adicionais salariais não informados; não incluídos nesta estimativa.")
    if deductions_raw is None:
        assumptions.append("Descontos não informados; não abatidos nesta estimativa.")

    if thirteenth_paid_raw is not None:
        thirteenth_paid = thirteenth_paid_raw
    elif thirteenth_pending is True or explicit_thirteenth_avos is not None:
        thirteenth_paid = Decimal("0")
    else:
        thirteenth_paid = Decimal("0")
        assumptions.append("Valor de 13º já pago não informado; a estimativa considera nenhum adiantamento e deve ser conferida.")

    paid_periods = max(0, paid_periods_raw or 0)
    taken_periods = max(0, taken_periods_raw or 0)
    if paid_periods_raw is None or taken_periods_raw is None:
        assumptions.append("Histórico completo de férias pagas ou usufruídas não informado; períodos vencidos devem ser conferidos.")

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

    # O 13º é sempre apurado pelo ano civil da data final projetada.
    # Um número extraído da conversa nunca pode substituir o cálculo por datas,
    # pois pode representar férias ou meses acumulados de anos anteriores.
    calculated_thirteenth_avos = thirteenth_months(admission, projected_end)
    thirteenth_avos = calculated_thirteenth_avos
    thirteenth_source = "calculated_from_dates"
    if explicit_thirteenth_avos is not None and explicit_thirteenth_avos != calculated_thirteenth_avos:
        assumptions.append(
            "Quantidade de avos de 13º informada na conversa divergiu das datas; "
            "foi aplicado o ano civil da rescisão sem somar períodos de anos anteriores."
        )
    thirteenth_gross = _money(base * Decimal(thirteenth_avos) / Decimal("12"))
    thirteenth_due = _money(max(Decimal("0"), thirteenth_gross - thirteenth_paid))

    completed_periods, calculated_vacation_avos, current_period_start = vacation_position(admission, projected_end)
    vacation_avos = (
        max(0, min(12, explicit_vacation_avos))
        if explicit_vacation_avos is not None
        else calculated_vacation_avos
    )
    vacation_source = "explicitly_informed" if explicit_vacation_avos is not None else "calculated_from_dates"
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

    limitations = [
        "O total direto não inclui cálculo definitivo de INSS, IRRF, convenção coletiva, multas específicas ou fatos não apresentados.",
        "O saldo e a multa do FGTS só são exatos quando o saldo da conta vinculada é informado a partir do extrato.",
        "O resultado deve ser confrontado com o TRCT, holerites, extrato do FGTS e documentos da empresa antes de qualquer medida jurídica.",
    ]
    limitations.extend(assumptions)

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
            "thirteenth_rule": "O 13º é apurado por ano civil; cada mês do ano da data final projetada com 15 dias ou mais de contrato conta 1/12, sem somar anos anteriores.",
            "vacation_rule": "Cada período mensal completo ou fração final de 15 dias ou mais conta 1/12 dentro do período aquisitivo.",
            "unconfirmed_values_assumed_zero": bool(assumptions),
        },
        "amounts": {
            "salary_balance_days": balance_days,
            "salary_balance": str(salary_balance),
            "notice_indemnity": str(notice_amount),
            "thirteenth_avos": thirteenth_avos,
            "thirteenth_avos_source": thirteenth_source,
            "thirteenth_gross": str(thirteenth_gross),
            "thirteenth_already_paid": str(_money(thirteenth_paid)),
            "thirteenth_due": str(thirteenth_due),
            "completed_vacation_periods_due": outstanding_completed,
            "current_vacation_period_start": current_period_start.isoformat(),
            "proportional_vacation_avos": vacation_avos,
            "proportional_vacation_avos_source": vacation_source,
            "vacation_base_due": str(_money(vacation_base_due)),
            "vacation_one_third": str(vacation_third),
            "deductions_confirmed": str(_money(deductions)),
            "estimated_direct_total_before_statutory_tax_withholding": str(direct_total),
            "fgts_information_status": fgts_status or "not_informed",
            "fgts_balance_informed": str(_money(fgts_balance)) if fgts_balance is not None else None,
            "fgts_40_percent_penalty": str(fgts_penalty) if fgts_penalty is not None else None,
        },
        "limitations": limitations,
    }
    return LaborCalculationResult(True, [], report)


def render_instructions() -> str:
    return """
Você é o redator final do cálculo de rescisão do DomnAI. Use exclusivamente o relatório determinístico fornecido pelo backend.
Não altere datas, avos, fórmulas, prazo de aviso ou valores. Não recalcule por conta própria.
Apresente em português claro: dados confirmados, base remuneratória, projeção do aviso, memória de cálculo por verba, total direto, FGTS separado e limitações.
Os avos do 13º vêm obrigatoriamente do cálculo por datas e do ano civil da rescisão. Não some meses de anos anteriores e não reutilize os avos de férias para o 13º.
Quando os avos de férias tiverem sido informados diretamente pelo usuário, respeite essa informação e deixe claro que ela foi usada.
Não transforme limitações em novas perguntas quando já for possível apresentar uma estimativa útil.
Destaque quando o aviso legal proporcional for diferente do prazo inicialmente citado pelo usuário.
Nunca chame estimativa de valor definitivo. Quando o FGTS estiver indisponível ou não informado, diga que essa parcela não foi fechada.
Não mencione JSON, backend, modelo ou processo interno.
""".strip()
