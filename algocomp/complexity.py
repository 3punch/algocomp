"""The `Complexity` value object: an asymptotic growth function plus metadata.

A Complexity knows:
  * its growth function g(n)   (evaluated with `value(n)`)
  * a canonical Big-O label     (O(n log n), O(2^n), ...)
  * its rank in the growth hierarchy
  * its empirical growth exponent (slope of log g vs log n)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Iterable

from .expr import ExprError, evaluate, free_variables

# --------------------------------------------------------------------------- #
# Canonical hierarchy (used for ranking + pretty labels)
# --------------------------------------------------------------------------- #

#: (rank, canonical label, matching expression). Ordered slowest -> fastest growth.
HIERARCHY: tuple[tuple[int, str, str], ...] = (
    (0, "O(1)", "1"),
    (1, "O(log log n)", "log2(log2(n))"),
    (2, "O(log n)", "log2(n)"),
    (3, "O(sqrt(n))", "sqrt(n)"),
    (4, "O(n)", "n"),
    (5, "O(n log n)", "n*log2(n)"),
    (6, "O(n log^2 n)", "n*log2(n)**2"),
    (7, "O(n sqrt(n))", "n*sqrt(n)"),
    (8, "O(n^2)", "n**2"),
    (9, "O(n^2 log n)", "n**2*log2(n)"),
    (10, "O(n^3)", "n**3"),
    (11, "O(n^4)", "n**4"),
    (12, "O(2^n)", "2**n"),
    (13, "O(n!)", "factorial(n)"),
    (14, "O(n^n)", "n**n"),   # n^n = 2^(n log n) outgrows n! ≈ (n/e)^n
)

_RANK_OF_LABEL = {label: rank for rank, label, _ in HIERARCHY}
_RANK_OF_EXPR = {expr: rank for rank, _, expr in HIERARCHY}
_LABEL_TO_EXPR = {label: expr for _, label, expr in HIERARCHY}
_REF_CACHE: dict[int, "Complexity"] = {}
_HIERARCHY_EXPONENTS: tuple[tuple[int, float], ...] = ()

#: sizes where exponentials and factorials still fit in a float64, used to order
#: explosive bounds against each other
_SMALL_PROBES = (12.0, 40.0, 100.0, 140.0)
#: sizes used for the ordinary (non-explosive) rank interpolation
_LARGE_PROBES = (1e3, 1e4, 1e5, 1e6)
#: exponent difference below which a bound counts as a canonical class
_EXP_TOL_RANK = 0.004


def _ref(rank: int) -> "Complexity":
    """Cached Complexity for a hierarchy entry (used by rank interpolation)."""
    if rank not in _REF_CACHE:
        label, expr = next((l, e) for r, l, e in HIERARCHY if r == rank)
        _REF_CACHE[rank] = Complexity(expr, label)
    return _REF_CACHE[rank]

_PRETTY = {
    "log2(n)": "log n",
    "log2(log2(n))": "log log n",
    "n*log2(n)": "n log n",
    "n*log2(n)**2": "n log² n",
    "n*sqrt(n)": "n√n",
}


def _pretty(expr: str) -> str:
    """Turn `n**2*log2(n)` into `n² log n`-style text."""
    if expr in _PRETTY:
        return _PRETTY[expr]
    out = expr
    out = re.sub(r"\*\*(\d+(?:\.\d+)?)", lambda m: "^" + m.group(1), out)
    out = out.replace("factorial(n)", "n!").replace("factorial(", "fact(")
    out = out.replace("log2(n)", "log n").replace("log2(", "log(")
    out = out.replace("sqrt(n)", "√n").replace("**", "^").replace("*", "·")
    return out


@dataclass(frozen=True)
class Complexity:
    """An asymptotic cost function of the input size `n`.

    Parameters
    ----------
    expr:
        Growth function as a string, e.g. ``"n*log2(n)"``.
    label:
        Optional canonical label. When omitted it is inferred from the hierarchy
        if the expression matches, otherwise pretty-printed from the expression.
    """

    expr: str
    label: str | None = None
    #: memoised evaluations; excluded from init/repr/eq so it stays invisible
    _value_cache: dict = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Validate syntax + allowed names. Constants are legal: O(1) is a real
        # complexity class, and several space bounds are genuinely constant.
        self.variables  # raises ExprError on unknown names / bad syntax
        # normalise the stored expression (strip whitespace)
        object.__setattr__(self, "expr", re.sub(r"\s+", "", self.expr))

    # ---------------------------------------------------------------- basics

    @cached_property
    def variables(self) -> tuple[str, ...]:
        return free_variables(self.expr)

    def value(self, n: float, **others: float) -> float:  # noqa: D102 (cached below)
        """Evaluate the growth function at input size `n`.

        Any secondary parameter (m, k, V, E, ...) that is not supplied defaults
        to `n`, which is the convention the comparator reports in its warnings.
        """
        env: dict[str, float] = {name: float(n) for name in self.variables}
        env["n"] = float(n)
        env.update({k: float(v) for k, v in others.items()})
        ck = tuple(sorted(env.items()))
        cache = self._value_cache
        hit = cache.get(ck)
        if hit is not None:
            return hit
        try:
            result = evaluate(self.expr, **env)
        except (ExprError, OverflowError, ValueError, ZeroDivisionError, TypeError):
            result = math.inf
        if len(cache) > 8192:
            cache.clear()
        cache[ck] = result
        return result

    def series(self, sizes: Iterable[float], **others: float) -> list[float]:
        return [self.value(n, **others) for n in sizes]

    # ------------------------------------------------------------- labelling

    @cached_property
    def resolved_label(self) -> str:
        if self.label:
            return self.label
        return _LABEL_TO_EXPR.get(self.expr) or f"O({_pretty(self.expr)})"

    @cached_property
    def short(self) -> str:
        """Label without the O() wrapper, for table cells."""
        lbl = self.resolved_label
        return lbl[2:-1].replace(" ", "") if lbl.startswith("O(") else lbl

    @cached_property
    def rank(self) -> float:
        """Position in the growth hierarchy (higher = grows faster).

        Exact for canonical classes; otherwise interpolated between the two
        canonical neighbours the expression falls between, so arbitrary custom
        bounds still sort correctly. Returns ``inf`` for explosive growth that
        outgrows every canonical class.
        """
        if self.label and self.label in _RANK_OF_LABEL:
            return float(_RANK_OF_LABEL[self.label])
        if self.expr in _RANK_OF_EXPR:
            return float(_RANK_OF_EXPR[self.expr])
        return self._interpolate_rank()

    #: two bounds within this log-ratio count as the same growth class
    _RANK_EPS = 0.02

    def _votes(self, probes) -> dict[int, tuple[int, float | None]]:
        """Compare against every canonical class at several input sizes.

        Returns ``{rank: (sign, mean_log_ratio)}``. The sign is derived from the
        *mean log ratio over the large probes*, i.e. from asymptotic behaviour —
        not from a per-size majority, which would be decided by small-input
        crossovers (log n beats n^0.25 below n ≈ 65 000, but loses above it).

        ``sign``: -1 the reference outgrows us, 0 equivalent, +1 we outgrow it.
        ``mean_log_ratio``: average of the finite log(g_self / g_ref) samples, or
        None when every sample overflowed.
        """
        eps = self._RANK_EPS
        out: dict[int, tuple[int, float | None]] = {}
        for rank, _label, _ref_expr in HIERARCHY:
            ref = _ref(rank)
            logs: list[float] = []
            pos_inf = neg_inf = 0
            for n in probes:
                a, b = self.value(n), ref.value(n)
                if b == 0 or a <= 0:
                    continue
                if math.isinf(b):
                    if not math.isinf(a):
                        neg_inf += 1          # reference explodes first
                    continue
                if math.isinf(a):
                    pos_inf += 1              # we explode first
                    continue
                logs.append(math.log(a / b))

            mean = sum(logs) / len(logs) if logs else None
            if mean is not None:
                score = mean
            elif pos_inf and not neg_inf:
                score = math.inf
            elif neg_inf and not pos_inf:
                score = -math.inf
            else:
                continue                      # no usable evidence

            if math.isinf(score):
                sign = 1 if score > 0 else -1
            elif abs(score) <= eps:
                sign = 0
            else:
                sign = 1 if score > 0 else -1
            out[rank] = (sign, mean)
        return out

    def _interpolate_rank(self, probes=_LARGE_PROBES) -> float:
        """Place a non-canonical bound between two canonical growth classes.

        Primary method: compare *growth exponents* (the slope of log g vs log n),
        which is asymptotic and immune to small-input crossovers. Explosive
        bounds all have an infinite exponent, so they fall back to a magnitude
        comparison at sizes where they still fit in a float64.

        This is a heuristic used for *sorting* the matrix view; the verdict
        engine in `comparator` never depends on it.
        """
        if self.expr in _RANK_OF_EXPR:
            return float(_RANK_OF_EXPR[self.expr])

        e = self.growth_exponent
        if not math.isinf(e) and not math.isnan(e):
            table = _HIERARCHY_EXPONENTS
            # `table` is sorted by exponent, so the entries either side of our
            # exponent bracket us. Their *ranks* need not be adjacent integers
            # (O(1), O(log log n) and O(log n) all have exponent 0).
            hi_idx = next((i for i, (_, ex) in enumerate(table) if ex > e), None)
            if hi_idx is None:
                return table[-1][0] + 0.5
            if hi_idx == 0:
                return table[0][0] - 0.5
            lo_rank, lo_ex = table[hi_idx - 1]
            hi_rank, hi_ex = table[hi_idx]
            if not (lo_ex <= e < hi_ex) or hi_ex == lo_ex:
                return float(lo_rank)
            t = (e - lo_ex) / (hi_ex - lo_ex)
            return lo_rank + min(max(t, 0.02), 0.98) * (hi_rank - lo_rank)

        return self._magnitude_rank(probes)

    def _magnitude_rank(self, probes=_LARGE_PROBES) -> float:
        """Rank an explosive bound by comparing magnitudes (see `_votes`)."""
        votes = self._votes(probes)
        if not votes:
            return math.inf
        lower = [r for r, (sgn, mean) in votes.items()
                 if sgn > 0 and mean is not None and not math.isinf(mean)]
        upper = [r for r, (sgn, mean) in votes.items()
                 if sgn < 0 and mean is not None and not math.isinf(mean)]
        if len(lower) >= 2 and len(upper) >= 2:
            lo, hi = max(lower), min(upper)
            if hi > lo:
                s_lo, s_hi = votes[lo][1], votes[hi][1]
                if s_hi != s_lo:
                    t = (0 - s_lo) / (s_hi - s_lo)
                    return lo + min(max(t, 0.02), 0.98) * (hi - lo)
        if probes is not _SMALL_PROBES:
            small = self._magnitude_rank(_SMALL_PROBES)
            if not math.isinf(small):
                return small
        below = [r for r, (sgn, _) in votes.items() if sgn > 0]
        above = [r for r, (sgn, _) in votes.items() if sgn < 0]
        if below and above:
            lo, hi = max(below), min(above)
            return (lo + hi) / 2 if hi > lo else hi + 0.5
        if below:
            return max(below) + 0.5
        if above:
            return min(above) - 0.5
        return math.inf

    # ------------------------------------------------------------ growth rate

    @cached_property
    def is_polylog(self) -> bool:
        """True for log n, log log n and products of logs — all Θ(n^0)."""
        stripped = re.sub(r"[\d.]+\s*\*\s*", "", self.expr)
        return bool(re.fullmatch(r"(log2?|lg|ln|log10)\(.*\)", stripped))

    @cached_property
    def is_log_only(self) -> bool:
        """True when the bound is a single logarithm: log n, ln n, log10 n, 3·log n."""
        return re.fullmatch(
            r"([\d.]+\s*\*\s*)?(log2?|lg|ln|log10)\(\s*[A-Za-z_]\w*\s*\)",
            self.expr,
        ) is not None

    @cached_property
    def is_exponential(self) -> bool:
        """True for genuinely explosive growth: factorial, n^n, or a**n."""
        expr = self.expr
        if "factorial(" in expr or "perm(" in expr or "comb(" in expr:
            return True
        tree = None
        try:
            import ast as _ast

            tree = _ast.parse(expr, mode="eval")
        except SyntaxError:  # pragma: no cover
            return False
        for node in _ast.walk(tree):
            if isinstance(node, _ast.BinOp) and isinstance(node.op, _ast.Pow):
                # a**n, n**n, n**(k/2) — anything with a variable in the exponent
                names = {x.id for x in _ast.walk(node.right) if isinstance(x, _ast.Name)}
                if names:
                    return True
        return False

    @cached_property
    def growth_exponent(self) -> float:
        """Slope of log g(n) vs log n between n=10^4 and n=10^12.

        ~1.0 for O(n), ~2.0 for O(n²), ~1.06 for O(n log n), 0.5 for O(√n),
        0.0 for O(log n) and O(1), and ``inf`` for exponential/factorial growth.
        """
        if self.is_exponential:
            return math.inf
        if self.is_polylog:
            # log n and log log n are both Theta(n^0); measuring the slope over a
            # finite span would report log(log n) instead, so state the exact value.
            return 0.0
        lo, hi = 1e4, 1e12
        a, b = self.value(lo), self.value(hi)
        if a <= 0 or b <= 0:
            return math.inf if (math.isinf(a) or math.isinf(b)) else float("nan")
        if math.isinf(a) and math.isinf(b):
            return math.inf
        if math.isinf(b):
            return math.inf
        if math.isinf(a):
            return -math.inf
        return (math.log(b) - math.log(a)) / (math.log(hi) - math.log(lo))

    def growth_class(self) -> str:
        """Human-readable bucket: constant / logarithmic / linear / ... / factorial."""
        expr = self.expr
        if "factorial(" in expr:
            return "factorial"
        if self.is_exponential:
            if expr.startswith("n**") and expr.endswith("n"):
                return "n^n (super-exponential)"
            return "exponential"
        e = self.growth_exponent
        if math.isnan(e) or math.isinf(e):
            return "explosive"
        if e > 1.35:
            return "polynomial (degree ≈ %.2f)" % e
        if e > 1.005:
            return "linearithmic"
        if e > 0.995:
            return "linear"
        if e > 0.05:
            return "sublinear polynomial"
        if self.is_log_only:
            return "logarithmic"
        if e > 0.005:
            return "polylogarithmic"
        return "constant"

    # --------------------------------------------------------------- helpers

    def __str__(self) -> str:
        return self.resolved_label

    def __repr__(self) -> str:  # pragma: no cover
        return f"Complexity({self.expr!r}) -> {self.resolved_label}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Complexity):
            return NotImplemented
        return self.expr == other.expr and (self.label or "") == (other.label or "")

    def __hash__(self) -> int:
        return hash((self.expr, self.label or ""))

    def as_expr(self) -> str:
        """Expression suitable for re-feeding into `--add`."""
        return self.expr


def coerce(value: str | Complexity) -> Complexity:
    """Accept either a Complexity or an expression/label string.

    Handles ``"O(n log n)"`` (canonical label), ``"O(n*log2(n))"`` (wrapped
    expression) and bare expressions like ``"n**2"``. Only a *matching* pair of
    outer parentheses is stripped, so inner function calls survive.
    """
    if isinstance(value, Complexity):
        return value
    text = value.strip()
    if text in _LABEL_TO_EXPR:  # "O(n log n)"
        return Complexity(_LABEL_TO_EXPR[text], text)

    m = re.fullmatch(r"[OoΘθΩω]\s*\((?P<body>.*)\)", text, re.DOTALL)
    if m:
        text = m.group("body").strip()
    else:
        text = re.sub(r"^[OoΘθΩω]\s*", "", text).strip()

    if not text:
        raise ExprError(f"cannot interpret {value!r} as a complexity")
    if text.startswith("(") and _balanced_outer(text):
        text = text[1:-1].strip()

    # tolerate pretty-printed labels coming from reports: "n log n", "n^2"
    text = _deprettify(text)
    return Complexity(text)


def _balanced_outer(text: str) -> bool:
    """True when the leading '(' matches the trailing ')'."""
    if not (text.startswith("(") and text.endswith(")")):
        return False
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i == len(text) - 1
    return False


_PRETTY_REVERSE = {
    "n log n": "n*log2(n)",
    "nlogn": "n*log2(n)",
    "log n": "log2(n)",
    "logn": "log2(n)",
    "log log n": "log2(log2(n))",
    "n log² n": "n*log2(n)**2",
    "n√n": "n*sqrt(n)",
    "√n": "sqrt(n)",
}


def _deprettify(text: str) -> str:
    """Accept human-written labels (n^2, n log n) as well as raw expressions."""
    key = text.replace(" ", "")
    for pretty, expr in _PRETTY_REVERSE.items():
        if key == pretty.replace(" ", ""):
            return expr
    if "^" in text:  # n^2 -> n**2
        text = re.sub(r"\^\s*(\d+(?:\.\d+)?)", r"**\1", text)
    # implicit multiplication: "2n" -> "2*n", "3(k+1)" -> "3*(k+1)".
    # The lookbehind keeps digits that are already part of an identifier
    # (log2, min, d2) untouched.
    text = re.sub(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?=[nNmkVEWdb(])", r"\1*", text)
    text = text.replace("·", "*").replace("×", "*").replace("−", "-")
    return text


def _build_exponent_table() -> None:
    """Cache each canonical class's growth exponent (called once, lazily)."""
    global _HIERARCHY_EXPONENTS
    if _HIERARCHY_EXPONENTS:
        return
    table = []
    for rank, label, expr in HIERARCHY:
        c = _ref(rank)
        ex = c.growth_exponent
        table.append((rank, ex if not math.isnan(ex) else math.inf))
    # Classes that share an exponent (1, log n, log log n are all Θ(n^0), and
    # every explosive class has exponent ∞) are ordered by their measured slope
    # at finite n, which still separates them correctly.
    def tiebreak(item):
        rank, ex = item
        c = _ref(rank)
        if math.isinf(ex) or ex == 0.0:
            lo, hi = 1e4, 1e12
            a, b = c.value(lo), c.value(hi)
            if a > 0 and b > 0 and not math.isinf(a) and not math.isinf(b):
                return (math.log(b) - math.log(a)) / (math.log(hi) - math.log(lo))
            return math.inf if math.isinf(b) else -math.inf
        return ex

    _HIERARCHY_EXPONENTS = tuple(sorted(table, key=tiebreak))


def _bootstrap() -> None:
    _build_exponent_table()


__all__ = ["Complexity", "HIERARCHY", "coerce", "_LABEL_TO_EXPR", "_RANK_OF_EXPR"]

_bootstrap()
