from __future__ import annotations

import ast
import math
import operator
import re

from app.domnai_core.tools import ToolRegistry

_ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_MAX_EXPRESSION_LENGTH = 200
_MAX_POWER = 12
_MAX_ABSOLUTE_RESULT = 1e100


def build_builtin_tool_registry() -> ToolRegistry:
    """Ferramentas determinísticas, locais e sem efeitos externos."""
    registry = ToolRegistry()
    registry.register(
        "calculate_expression",
        _calculate_expression,
        description=(
            "Calcula uma expressão aritmética segura com números, parênteses e os "
            "operadores +, -, *, /, //, %, **."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "minLength": 1, "maxLength": 200}
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    )
    registry.register(
        "analyze_text",
        _analyze_text,
        description=(
            "Conta caracteres, palavras, linhas e frases de um texto sem alterar o conteúdo."
        ),
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "maxLength": 20000}
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    )
    return registry


def _calculate_expression(arguments: dict) -> dict:
    expression = str(arguments.get("expression") or "").strip()
    if not expression:
        raise ValueError("expression não pode ser vazia.")
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError("expression excede o limite de 200 caracteres.")

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Expressão aritmética inválida.") from exc

    value = _evaluate_node(parsed.body)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("A expressão não produziu um número válido.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("O resultado não é finito.")
    if abs(value) > _MAX_ABSOLUTE_RESULT:
        raise ValueError("O resultado excede o limite permitido.")
    return {"expression": expression, "value": value}


def _evaluate_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("A expressão aceita apenas números.")
        return node.value

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPERATORS:
        return _ALLOWED_UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand))

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINARY_OPERATORS:
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POWER:
            raise ValueError("Expoente excede o limite permitido.")
        try:
            return _ALLOWED_BINARY_OPERATORS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise ValueError("Divisão por zero não é permitida.") from exc
        except OverflowError as exc:
            raise ValueError("A operação excedeu o limite numérico.") from exc

    raise ValueError("A expressão contém operação não permitida.")


def _analyze_text(arguments: dict) -> dict:
    text = str(arguments.get("text") or "")
    if len(text) > 20000:
        raise ValueError("text excede o limite de 20.000 caracteres.")
    words = re.findall(r"\b[\wÀ-ÖØ-öø-ÿ]+(?:['’-][\wÀ-ÖØ-öø-ÿ]+)?\b", text, flags=re.UNICODE)
    sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
    return {
        "characters": len(text),
        "characters_without_spaces": len(re.sub(r"\s", "", text)),
        "words": len(words),
        "lines": 0 if not text else text.count("\n") + 1,
        "sentences": len(sentences),
    }
