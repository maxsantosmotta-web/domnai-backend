from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


path = Path('/app/app/services/labor_pipeline.py')
text = path.read_text(encoding='utf-8')

helper = '''\n\ndef _money_pt(value: object) -> str:\n    from decimal import Decimal\n    amount = Decimal(str(value or \"0\"))\n    formatted = f\"{amount:,.2f}\"\n    return \"R$ \" + formatted.replace(\",\", \"X\").replace(\".\", \",\").replace(\"X\", \".\")\n\n\ndef _deterministic_labor_answer(report: dict) -> str:\n    inputs = report.get(\"inputs\") or {}\n    amounts = report.get(\"amounts\") or {}\n    rules = report.get(\"rules_applied\") or {}\n    notice_days = int(inputs.get(\"notice_days\") or 0)\n    lines = [\n        \"## Resumo validado da rescisão\",\n        f\"- Admissão: {inputs.get('admission_date') or 'não informada'}\",\n        f\"- Término considerado: {inputs.get('projected_contract_end') or inputs.get('termination_date') or 'não informado'}\",\n        f\"- Base remuneratória: {_money_pt(inputs.get('calculation_base'))}\",\n        \"\",\n        \"## Memória de cálculo\",\n        f\"- Saldo de salário ({amounts.get('salary_balance_days', 0)} dias): {_money_pt(amounts.get('salary_balance'))}\",\n        f\"- Aviso-prévio indenizado ({notice_days} dias): {_money_pt(amounts.get('notice_indemnity'))}\",\n        f\"- 13º proporcional ({amounts.get('thirteenth_avos', 0)}/12): {_money_pt(amounts.get('thirteenth_due'))}\",\n    ]\n    overdue = int(amounts.get(\"overdue_vacation_periods_due\") or 0)\n    regular = int(amounts.get(\"regular_completed_vacation_periods_due\") or 0)\n    avos = int(amounts.get(\"proportional_vacation_avos\") or 0)\n    if overdue:\n        lines.append(f\"- Férias vencidas em dobro ({overdue} período(s), base): {_money_pt(amounts.get('overdue_vacation_base_including_double'))}\")\n    if regular:\n        lines.append(f\"- Férias integrais adquiridas ({regular} período(s), base): {_money_pt(amounts.get('regular_completed_vacation_base'))}\")\n    lines.extend([\n        f\"- Férias proporcionais ({avos}/12, incluídas na base de férias): {_money_pt(amounts.get('vacation_base_due'))}\",\n        f\"- Terço constitucional de férias: {_money_pt(amounts.get('vacation_one_third'))}\",\n        \"\",\n        f\"**Total direto bruto estimado: {_money_pt(amounts.get('estimated_direct_total_before_statutory_tax_withholding'))}**\",\n        \"\",\n        \"FGTS e multa de 40% permanecem separados do total quando não houver saldo numérico do extrato.\",\n        \"Esta é uma estimativa e deve ser conferida com TRCT, holerites e extrato do FGTS.\",\n    ])\n    if rules.get(\"notice_projection_applied\"):\n        lines.insert(4, \"- Houve projeção do aviso-prévio porque a data informada foi tratada como comunicação/início do aviso.\")\n    return \"\\n\".join(lines)\n\n\ndef _labor_response_matches_report(text: str, report: dict) -> bool:\n    inputs = report.get(\"inputs\") or {}\n    amounts = report.get(\"amounts\") or {}\n    normalized = \" \".join(str(text or \"\").casefold().split())\n    required = [\n        str(inputs.get(\"notice_days\") or \"\"),\n        _money_pt(amounts.get(\"notice_indemnity\")).casefold(),\n        _money_pt(amounts.get(\"estimated_direct_total_before_statutory_tax_withholding\")).casefold(),\n    ]\n    return all(item and item in normalized for item in required)\n'''

anchor = '\n\ndef generate_labor_response(\n'
if '_deterministic_labor_answer' not in text:
    if anchor not in text:
        raise RuntimeError('labor pipeline anchor not found')
    text = text.replace(anchor, helper + anchor, 1)

old = '''    return MeteredBrainResult(\n        text=final_text,\n        provider="openai-orchestrated-labor-deterministic-refined-memory",\n'''
new = '''    validated_text = final_text if _labor_response_matches_report(final_text, calculation.report or {}) else _deterministic_labor_answer(calculation.report or {})\n    provider = (\n        "openai-orchestrated-labor-deterministic-refined-memory"\n        if validated_text == final_text\n        else "local-labor-deterministic-fallback"\n    )\n    return MeteredBrainResult(\n        text=validated_text,\n        provider=provider,\n'''
text = replace_once(text, old, new, 'final labor validation')
path.write_text(text, encoding='utf-8')
