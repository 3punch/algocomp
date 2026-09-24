"""Safe symbolic expression evaluator for asymptotic (Big-O) formulas.

Complexity expressions are written as plain Python-like math strings, e.g.:

    "1"
    "log2(n)"
    "n*log2(n)"
    "n**2"
    "n*2**n"
    "factorial(n)"

Only a whitelisted set of operators, functions and constants is allowed, and the
AST is validated before evaluation, so arbitrary code can never be executed
(this matters because `--add` accepts expressions from the command line).
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Callable

# --------------------------------------------------------------------------- #
# Whitelists
# --------------------------------------------------------------------------- #

_EXACT_LIMIT = 170  # beyond this a factorial no longer fits in a float64


def _factorial(x: float) -> float:
    xi = int(x)
    if xi < 0:
        raise ValueError("factorial of a negative number")
    if xi <= _EXACT_LIMIT:
        return float(math.factorial(xi))
    if xi < 1e7:
        try:
            return math.exp(math.lgamma(xi + 1))
        except OverflowError:
            return math.inf
    # Stirling in log space, then exponentiate (inf once it no longer fits)
    try:
        return math.exp(xi * (math.log(xi) - 1) + 0.5 * math.log(2 * math.pi * xi))
    except (OverflowError, ValueError):
        return math.inf


def _perm(n: float, k: float) -> float:
    ni, ki = int(n), int(k)
    if ki <= _EXACT_LIMIT and ni <= 10000:
        return float(math.perm(ni, ki))
    try:
        return math.exp(math.lgamma(ni + 1) - math.lgamma(ni - ki + 1))
    except (OverflowError, ValueError):
        return math.inf


def _comb(n: float, k: float) -> float:
    ni, ki = int(n), int(k)
    if ni <= 1000 and ki <= _EXACT_LIMIT:
        return float(math.comb(ni, ki))
    try:
        return math.exp(math.lgamma(ni + 1) - math.lgamma(ki + 1) - math.lgamma(ni - ki + 1))
    except (OverflowError, ValueError):
        return math.inf


_BINOPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS: dict[type, Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _log(n: float, base: float = 2.0) -> float:
    return math.log(n, base)


_FUNCS: dict[str, Callable[..., float]] = {
    # logarithms (base 2 is the CS default; base only changes constants)
    "log": _log,
    "log2": lambda n: math.log2(n),
    "lg": lambda n: math.log2(n),
    "ln": math.log,
    "log10": math.log10,
    # roots / powers
    "sqrt": math.sqrt,
    "cbrt": lambda n: n ** (1.0 / 3.0),
    # combinatorial (for backtracking / brute-force costs)
    # combinatorial helpers: exact for small arguments, log-space (Stirling /
    # lgamma) beyond that so huge sample sizes stay finite and fast
    "factorial": _factorial,
    "perm": _perm,
    "comb": _comb,
    # misc
    "exp": math.exp,
    "abs": abs,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
}

_CONSTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "phi": (1 + math.sqrt(5)) / 2,
    "inf": math.inf,
}

_VARS = {"n", "m", "k", "V", "E", "W", "d", "b"}

#: Any valid identifier may be used as a parameter (the catalogue documents what
#: each one means per algorithm), except these reserved words, which would shadow
#: functions/constants or Python keywords.
_RESERVED = frozenset(_FUNCS) | frozenset(_CONSTS) | frozenset(
    {"and", "or", "not", "if", "else", "for", "in", "is", "lambda", "None", "True", "False"}
)


def is_variable(name: str) -> bool:
    return name.isidentifier() and name not in _RESERVED


class ExprError(ValueError):
    """Raised when an expression string is malformed or uses disallowed syntax."""


_AST_CACHE: dict[str, ast.Expression] = {}
_CACHE_LIMIT = 4096


def _cached_parse(expr: str) -> ast.Expression:
    """Parse + validate once per distinct expression string.

    Ranking and sampling evaluate the same handful of expressions thousands of
    times, so this cache is what keeps the tool interactive.
    """
    tree = _AST_CACHE.get(expr)
    if tree is None:
        tree = _parse(expr)
        if len(_AST_CACHE) >= _CACHE_LIMIT:
            _AST_CACHE.clear()
        _AST_CACHE[expr] = tree
    return tree


# --------------------------------------------------------------------------- #
# Evaluator
# --------------------------------------------------------------------------- #


def evaluate(expr: str, default: float = 1.0, **env: float) -> float:
    """Evaluate `expr`.

    Every variable must be supplied in `env`; any that is missing falls back to
    `default` (1.0 by default, so a bare call still works for quick estimates).
    """
    tree = _cached_parse(expr)
    variables: dict[str, float] = {}
    for name in free_variables(expr):
        variables[name] = float(env[name]) if name in env else float(default)
    return _eval_node(tree, variables)


def free_variables(expr: str) -> tuple[str, ...]:
    """Return the sorted names of variables used in `expr` (function names excluded)."""
    tree = _cached_parse(expr)
    call_funcs = {
        id(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and id(node) not in call_funcs
    }
    names -= set(_CONSTS)
    unknown = {nm for nm in names if not is_variable(nm)}
    if unknown:
        raise ExprError(
            f"disallowed name(s) {sorted(unknown)} in {expr!r}; names must be valid "
            f"identifiers and must not shadow functions ({sorted(_FUNCS)})"
        )
    return tuple(sorted(names))


def _parse(expr: str) -> ast.Expression:
    if not isinstance(expr, str) or not expr.strip():
        raise ExprError("expression must be a non-empty string")
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as exc:  # pragma: no cover - message varies by input
        raise ExprError(f"cannot parse {expr!r}: {exc.msg}") from exc
    _validate(tree)
    return tree


_ALLOWED_OPS = tuple(_BINOPS) + tuple(_UNARYOPS)


def _validate(tree: ast.AST) -> None:
    call_funcs = {
        id(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Expression):
            continue
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
                raise ExprError(f"only numeric literals are allowed, got {node.value!r}")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in _BINOPS:
                raise ExprError(f"operator {type(node.op).__name__} is not allowed")
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in _UNARYOPS:
                raise ExprError(f"unary operator {type(node.op).__name__} is not allowed")
        elif isinstance(node, ast.Name):
            if id(node) in call_funcs:
                if node.id not in _FUNCS:
                    raise ExprError(
                        f"unknown function {node.id!r}; allowed: {sorted(_FUNCS)}"
                    )
            elif node.id not in _CONSTS and not is_variable(node.id):
                raise ExprError(
                    f"disallowed name {node.id!r}: must be a valid identifier and must "
                    f"not shadow a function ({sorted(_FUNCS)})"
                )
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
                raise ExprError(
                    f"unknown or disallowed function; allowed: {sorted(_FUNCS)}"
                )
            if node.keywords:
                raise ExprError("keyword arguments are not allowed")
        elif isinstance(node, _ALLOWED_OPS) or isinstance(node, ast.Load):
            continue  # operator markers / contexts, already checked above
        else:
            raise ExprError(f"syntax element {type(node).__name__} is not allowed")


def _eval_node(node: ast.AST, env: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id in env:
            return float(env[node.id])
        return float(_CONSTS[node.id])
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, env)
        right = _eval_node(node.right, env)
        if isinstance(node.op, ast.Pow) and right > 100:
            raise ExprError("exponent too large (would overflow)")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        return _UNARYOPS[type(node.op)](_eval_node(node.operand, env))
    if isinstance(node, ast.Call):
        args = [_eval_node(a, env) for a in node.args]
        return float(_FUNCS[node.func.id](*args))  # type: ignore[arg-type]
    raise ExprError(f"cannot evaluate {type(node).__name__}")  # pragma: no cover


__all__ = ["evaluate", "free_variables", "is_variable", "ExprError", "_FUNCS", "_VARS",
           "_cached_parse"]
