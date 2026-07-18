from app.services.labor_termination import calculate, statutory_notice_days


def complete_payload(**overrides):
    payload = {
        "admission_date": "2024-01-01",
        "termination_communication_date": "2026-01-31",
        "monthly_salary": "3000",
        "termination_reason": "employer_without_cause",
        "notice_type": "indemnified",
        "notice_days_explicit": None,
        "salary_balance_days": 30,
        "thirteenth_already_paid": "0",
        "vacation_periods_already_paid": 0,
        "vacation_periods_already_taken": 0,
        "variable_pay_average": "0",
        "other_salary_additions": "0",
        "deductions": "0",
        "fgts_information_status": "provided",
        "fgts_balance": "10000",
    }
    payload.update(overrides)
    return payload


def test_missing_optional_variable_pay_produces_explicit_estimate_limitation():
    result = calculate(complete_payload(variable_pay_average=None))

    assert result.ready is True
    assert result.missing_fields == []
    assert result.report["inputs"]["variable_pay_average"] == "0.00"
    assert result.report["rules_applied"]["unconfirmed_values_assumed_zero"] is True
    assert any(
        "Média de remuneração variável não informada" in limitation
        for limitation in result.report["limitations"]
    )


def test_multiple_optional_unknowns_do_not_block_estimate_and_are_disclosed():
    result = calculate(complete_payload(
        thirteenth_already_paid=None,
        vacation_periods_already_paid=None,
        variable_pay_average=None,
        other_salary_additions=None,
        deductions=None,
        fgts_information_status=None,
    ))

    assert result.ready is True
    assert result.missing_fields == []
    assert result.report["rules_applied"]["unconfirmed_values_assumed_zero"] is True
    limitations = " ".join(result.report["limitations"])
    assert "Valor de 13º já pago não informado" in limitations
    assert "Histórico completo de férias" in limitations
    assert "Média de remuneração variável não informada" in limitations
    assert "Adicionais salariais não informados" in limitations
    assert "Descontos não informados" in limitations
    assert result.report["amounts"]["fgts_information_status"] == "not_informed"
    assert result.report["amounts"]["fgts_40_percent_penalty"] is None


def test_brazilian_currency_format_is_parsed_correctly():
    result = calculate(complete_payload(
        monthly_salary="3.000,00",
        variable_pay_average="500,00",
        other_salary_additions="250,00",
    ))

    assert result.ready is True
    assert result.report["inputs"]["monthly_salary"] == "3000.00"
    assert result.report["inputs"]["calculation_base"] == "3750.00"


def test_invalid_date_order_is_rejected():
    result = calculate(complete_payload(
        admission_date="2026-02-01",
        termination_communication_date="2026-01-31",
    ))

    assert result.ready is False
    assert result.missing_fields == ["invalid_date_order"]


def test_employer_termination_uses_statutory_notice_not_user_value():
    payload = complete_payload(notice_days_explicit=30)
    result = calculate(payload)

    expected_days = statutory_notice_days(
        __import__("datetime").date.fromisoformat(payload["admission_date"]),
        __import__("datetime").date.fromisoformat(payload["termination_communication_date"]),
    )

    assert result.ready is True
    assert result.report["inputs"]["notice_days"] == expected_days
    assert result.report["inputs"]["notice_days_source"] == "statutory_proportional"
    assert result.report["rules_applied"]["unconfirmed_values_assumed_zero"] is False


def test_notice_is_limited_to_ninety_days():
    result = calculate(complete_payload(
        admission_date="1990-01-01",
        termination_communication_date="2026-01-31",
    ))

    assert result.ready is True
    assert result.report["inputs"]["notice_days"] == 90


def test_fgts_penalty_is_calculated_separately():
    result = calculate(complete_payload(fgts_balance="10.000,00"))

    assert result.ready is True
    assert result.report["amounts"]["fgts_balance_informed"] == "10000.00"
    assert result.report["amounts"]["fgts_40_percent_penalty"] == "4000.00"


def test_unavailable_fgts_does_not_invent_balance_or_penalty():
    result = calculate(complete_payload(
        fgts_information_status="unavailable",
        fgts_balance=None,
    ))

    assert result.ready is True
    assert result.report["amounts"]["fgts_balance_informed"] is None
    assert result.report["amounts"]["fgts_40_percent_penalty"] is None


def test_non_employer_termination_respects_explicit_notice_days():
    result = calculate(complete_payload(
        termination_reason="employee_resignation",
        notice_type="worked",
        notice_days_explicit=45,
        fgts_information_status="unavailable",
        fgts_balance=None,
    ))

    assert result.ready is True
    assert result.report["inputs"]["notice_days"] == 45
    assert result.report["inputs"]["notice_days_source"] == "explicitly_informed"


def test_salary_balance_days_are_capped_at_thirty():
    result = calculate(complete_payload(salary_balance_days=45))

    assert result.ready is True
    assert result.report["amounts"]["salary_balance_days"] == 30
