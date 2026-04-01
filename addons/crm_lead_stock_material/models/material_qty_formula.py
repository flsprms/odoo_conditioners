# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

"""Safe evaluation of material quantity formulas using variable x only."""

import ast
import math
import operator
from typing import Optional

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _validate_safe_expr(node: ast.AST) -> None:
    """Reject anything that is not a safe arithmetic / round / abs / ceil / floor."""
    if isinstance(node, ast.Expression):
        return _validate_safe_expr(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
        return
    if isinstance(node, ast.Num):
        return
    if isinstance(node, ast.Name):
        if node.id != "x":
            raise ValueError("only variable x is allowed")
        return
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNARY_OPS:
            raise ValueError("unsupported unary operator")
        return _validate_safe_expr(node.operand)
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINARY_OPS:
            raise ValueError("unsupported binary operator")
        _validate_safe_expr(node.left)
        _validate_safe_expr(node.right)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("only simple function calls are allowed")
        fn = node.func.id
        allowed = {"round", "ceil", "floor", "abs", "int", "float"}
        if fn not in allowed:
            raise ValueError("unsupported function")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        for arg in node.args:
            _validate_safe_expr(arg)
        return
    raise ValueError("unsupported expression")


def _eval_node(node: ast.AST, x: float) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, x)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError
        return float(node.value)
    if isinstance(node, ast.Num):
        return float(node.n)
    if isinstance(node, ast.Name):
        if node.id == "x":
            return float(x)
        raise ValueError
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS[type(node.op)]
        return op(_eval_node(node.operand, x))
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS[type(node.op)]
        left = _eval_node(node.left, x)
        right = _eval_node(node.right, x)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError
        if isinstance(node.op, ast.Mod) and right == 0:
            raise ZeroDivisionError
        return op(left, right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = node.func.id
        args = [_eval_node(a, x) for a in node.args]
        if fn == "round":
            if len(args) == 1:
                return float(round(args[0]))
            if len(args) == 2:
                return float(round(args[0], int(args[1])))
            raise ValueError
        if fn == "ceil" and len(args) == 1:
            return float(math.ceil(args[0]))
        if fn == "floor" and len(args) == 1:
            return float(math.floor(args[0]))
        if fn == "abs" and len(args) == 1:
            return float(abs(args[0]))
        if fn == "int" and len(args) == 1:
            return float(int(args[0]))
        if fn == "float" and len(args) == 1:
            return float(args[0])
    raise ValueError


def eval_material_qty_formula(
    formula: Optional[str], x: float, fallback: float
) -> float:
    """Evaluate formula with variable x. On any failure return fallback."""
    if formula is None:
        return fallback
    text = str(formula).strip()
    if not text:
        return fallback
    try:
        tree = ast.parse(text, mode="eval")
        _validate_safe_expr(tree)
        result = _eval_node(tree, float(x))
        if not isinstance(result, (int, float)) or math.isnan(result):
            return fallback
        return float(result)
    except Exception:
        return fallback
