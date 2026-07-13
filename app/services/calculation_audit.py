from __future__ import annotations

import ast
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext

getcontext().prec = 28

_ALLOWED_BINARY = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
}
_ALLOWED_UNARY = {
    ast.UAdd: lambda a: a,
    ast.USub: lambda a: -a,
}


def _decimal_from_constant(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Constante inválida")
    return Decimal(str(value))


def _eval_node(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        return _decimal_from_constant(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINARY:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("Divisão por zero")
        if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > Decimal("1000000000")):
            raise ValueError("Potência fora do limite")
        return _ALLOWED_BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_node(node.operand))
    raise ValueError("Expressão não permitida")


def evaluate_expression(expression: str) -> Decimal:
    cleaned = str(expression or "").strip().replace("^", "**")
    if not cleaned or len(cleaned) > 300:
        raise ValueError("Expressão vazia ou longa demais")
    tree = ast.parse(cleaned, mode="eval")
    return _eval_node(tree)


def _money(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"


def parse_calculation_manifest(raw_text: str) -> list[dict]:
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = payload.get("calculations") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items[:30] if isinstance(item, dict)]


def audit_manifest(items: list[dict]) -> list[dict]:
    audited: list[dict] = []
    for item in items:
        label = str(item.get("label") or "Cálculo")[:120]
        expression = str(item.get("expression") or "").strip()
        stated = item.get("stated_value")
        if not expression:
            continue
        record = {"label": label, "expression": expression}
        try:
            computed = evaluate_expression(expression)
            record["computed_value"] = _money(computed)
            if stated is not None:
                try:
                    stated_decimal = Decimal(str(stated).replace(",", "."))
                    record["stated_value"] = _money(stated_decimal)
                    record["matches"] = abs(computed - stated_decimal) <= Decimal("0.01")
                except (InvalidOperation, ValueError):
                    record["stated_value"] = str(stated)
                    record["matches"] = False
            else:
                record["matches"] = None
        except Exception as exc:
            record["error"] = str(exc)
            record["matches"] = False
        audited.append(record)
    return audited


def format_audit_for_reviewer(audited: list[dict]) -> str:
    if not audited:
        return "Nenhum cálculo estruturado foi identificado para conferência determinística."
    lines = ["AUDITORIA MATEMÁTICA DETERMINÍSTICA:"]
    for item in audited:
        if item.get("error"):
            lines.append(f"- {item['label']}: expressão inválida ({item['expression']}).")
            continue
        status = "confere" if item.get("matches") is True else "diverge" if item.get("matches") is False else "calculado"
        stated = f"; valor declarado {item.get('stated_value')}" if item.get("stated_value") is not None else ""
        lines.append(
            f"- {item['label']}: {item['expression']} = {item['computed_value']}{stated}; status: {status}."
        )
    return "\n".join(lines)
