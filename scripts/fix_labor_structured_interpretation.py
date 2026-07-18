from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


path = Path('/app/app/services/labor_termination.py')
text = path.read_text(encoding='utf-8')

text = replace_once(
    text,
    '''  "vacation_periods_already_paid":"inteiro ou null",
  "vacation_periods_already_taken":"inteiro ou null",
  "vacation_proportional_months":"inteiro de 0 a 12 ou null",
  "vacation_proportional_pending":"boolean ou null",
  "variable_pay_average":"número decimal ou null",
''',
    '''  "vacation_periods_already_paid":"inteiro ou null",
  "vacation_periods_already_taken":"inteiro ou null",
  "vacation_overdue_periods_informed":"inteiro ou null",
  "vacation_proportional_months":"inteiro de 0 a 12 ou null",
  "vacation_proportional_pending":"boolean ou null",
  "variable_pay_average":"número decimal ou null",
''',
    'schema vacation overdue field',
)

text = replace_once(
    text,
    '''  "fgts_information_status":"provided|unavailable|null",
  "fgts_balance":"número decimal ou null"
''',
    '''  "fgts_information_status":"provided|unavailable|null",
  "fgts_balance":"número decimal ou null",
  "fgts_deposits_confirmed":"boolean ou null",
  "fgts_40_percent_penalty_confirmed":"boolean ou null"
''',
    'schema fgts confirmation fields',
)

text = replace_once(
    text,
    '''- Quando o usuário disser que uma verba está pendente, não pergunte novamente se ela foi paga sem existir contradição real.
- Uma correção mais recente do usuário substitui informação anterior incompatível.
''',
    '''- Quando o usuário disser que uma verba está pendente, não pergunte novamente se ela foi paga sem existir contradição real.
- Quando o usuário disser “tenho uma férias vencida”, “há 1 férias vencida” ou expressão equivalente, registre vacation_overdue_periods_informed=1. Não converta essa declaração em dois períodos vencidos nem descarte a informação porque a frase é informal.
- Diferencie férias vencidas, férias integrais adquiridas ainda dentro do prazo concessivo e férias proporcionais. São categorias distintas.
- Quando o usuário disser “FGTS e 40% depositado”, “FGTS mais multa pagos” ou equivalente, registre fgts_deposits_confirmed=true e fgts_40_percent_penalty_confirmed=true. Isso confirma a declaração do usuário, mas não inventa valores.
- Uma correção mais recente do usuário substitui informação anterior incompatível.
''',
    'semantic extraction rules',
)

text = replace_once(
    text,
    '''    paid_periods_raw = _int_or_none(data.get("vacation_periods_already_paid"))
    taken_periods_raw = _int_or_none(data.get("vacation_periods_already_taken"))
    explicit_vacation_avos = _int_or_none(data.get("vacation_proportional_months"))

    variable_raw = _decimal(data.get("variable_pay_average"))
''',
    '''    paid_periods_raw = _int_or_none(data.get("vacation_periods_already_paid"))
    taken_periods_raw = _int_or_none(data.get("vacation_periods_already_taken"))
    overdue_periods_raw = _int_or_none(data.get("vacation_overdue_periods_informed"))
    explicit_vacation_avos = _int_or_none(data.get("vacation_proportional_months"))

    variable_raw = _decimal(data.get("variable_pay_average"))
''',
    'parse vacation overdue field',
)

text = replace_once(
    text,
    '''    fgts_status = str(data.get("fgts_information_status") or "").strip()
    fgts_balance = _decimal(data.get("fgts_balance"))

    supplied_date = termination or communication
''',
    '''    fgts_status = str(data.get("fgts_information_status") or "").strip()
    fgts_balance = _decimal(data.get("fgts_balance"))
    fgts_deposits_confirmed = _bool_or_none(data.get("fgts_deposits_confirmed"))
    fgts_penalty_confirmed = _bool_or_none(data.get("fgts_40_percent_penalty_confirmed"))

    supplied_date = termination or communication
''',
    'parse fgts confirmation fields',
)

text = replace_once(
    text,
    '''    completed_periods, calculated_vacation_avos, current_period_start = vacation_position(admission, projected_end)
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
''',
    '''    completed_periods, calculated_vacation_avos, current_period_start = vacation_position(admission, projected_end)
    vacation_avos = (
        max(0, min(12, explicit_vacation_avos))
        if explicit_vacation_avos is not None
        else calculated_vacation_avos
    )
    vacation_source = "explicitly_informed" if explicit_vacation_avos is not None else "calculated_from_dates"

    resolved_completed = max(paid_periods, taken_periods)
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
    completed_vacation_base = overdue_vacation_base + regular_completed_vacation_base
    proportional_vacation_base = _money(base * Decimal(vacation_avos) / Decimal("12"))
    vacation_base_due = completed_vacation_base + proportional_vacation_base
    vacation_third = _money(vacation_base_due / Decimal("3"))
''',
    'vacation classification and blocking',
)

text = replace_once(
    text,
    '''            "completed_vacation_periods_due": outstanding_completed,
            "current_vacation_period_start": current_period_start.isoformat(),
''',
    '''            "completed_vacation_periods_due": outstanding_completed,
            "overdue_vacation_periods_due": overdue_periods,
            "regular_completed_vacation_periods_due": regular_completed_periods,
            "overdue_vacation_base_including_double": str(overdue_vacation_base),
            "regular_completed_vacation_base": str(regular_completed_vacation_base),
            "current_vacation_period_start": current_period_start.isoformat(),
''',
    'vacation report fields',
)

text = replace_once(
    text,
    '''            "fgts_information_status": fgts_status or "not_informed",
            "fgts_balance_informed": str(_money(fgts_balance)) if fgts_balance is not None else None,
            "fgts_40_percent_penalty": str(fgts_penalty) if fgts_penalty is not None else None,
''',
    '''            "fgts_information_status": fgts_status or "not_informed",
            "fgts_balance_informed": str(_money(fgts_balance)) if fgts_balance is not None else None,
            "fgts_deposits_confirmed_by_user": fgts_deposits_confirmed,
            "fgts_40_percent_penalty_confirmed_by_user": fgts_penalty_confirmed,
            "fgts_40_percent_penalty": str(fgts_penalty) if fgts_penalty is not None else None,
''',
    'fgts report fields',
)

text = replace_once(
    text,
    '''Aceite respostas equivalentes, correções e linguagem informal, mas trate férias e 13º como verbas com calendários diferentes.
Quando a única data informada estiver realmente ambígua entre início do aviso e último dia do contrato, pergunte apenas: “Essa data foi o início do aviso ou o último dia do contrato?”.
''',
    '''Aceite respostas equivalentes, correções e linguagem informal, mas trate férias e 13º como verbas com calendários diferentes.
Quando missing_fields contiver vacation_history_for_remaining_completed_periods, pergunte apenas se, além das férias vencidas já informadas, houve outro período completo de férias tirado ou pago. Não repita as demais perguntas.
Quando a única data informada estiver realmente ambígua entre início do aviso e último dia do contrato, pergunte apenas: “Essa data foi o início do aviso ou o último dia do contrato?”.
''',
    'missing vacation question rule',
)

text = replace_once(
    text,
    '''Apresente em português claro: dados confirmados, base remuneratória, tratamento da data de término, eventual projeção do aviso, memória de cálculo por verba, total direto, FGTS separado e limitações.
''',
    '''Apresente em português claro: dados confirmados, base remuneratória, tratamento da data de término, eventual projeção do aviso, memória de cálculo por verba, total direto, FGTS separado e limitações.
Diferencie expressamente férias vencidas pagas em dobro, férias integrais simples e férias proporcionais. Nunca agrupe essas categorias como se fossem iguais.
Quando o usuário tiver confirmado depósitos de FGTS ou multa de 40%, registre essa confirmação em linguagem natural, mas deixe claro que valores exatos só entram no total quando houver saldo ou base numérica informada.
''',
    'render vacation and fgts distinctions',
)

path.write_text(text, encoding='utf-8')
