"""Curve fitting: match benchmark timings to Big-O growth models (stdlib only)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

CANDIDATES = (
    ("O(1)", "1"),
    ("O(log n)", "log2(n)"),
    ("O(n)", "n"),
    ("O(n log log n)", "n*log2(log2(n))"),
    ("O(n log n)", "n*log2(n)"),
    ("O(n log^2 n)", "n*log2(n)**2"),
    ("O(n sqrt(n))", "n*sqrt(n)"),
    ("O(n^2)", "n**2"),
    ("O(n^3)", "n**3"),
)

#: shapes that do not grow like a power of n, so the slope check is skipped
_FLAT_SHAPES = frozenset({"1", "log2(n)"})

#: relative tolerance used to call a constant data set "exactly constant"
_CONST_EPS = 1e-9


def _shape(expr, n):
    n = float(n)
    if expr == "1":
        return 1.0
    if expr == "log2(n)":
        return math.log2(max(n, 2.0))
    if expr == "n":
        return n
    if expr == "n*log2(log2(n))":
        # log log n is only positive from n >= 4 (sieve-style growth)
        return n * math.log2(max(math.log2(max(n, 4.0)), 2.0))
    if expr == "n*log2(n)":
        return n * math.log2(max(n, 2.0))
    if expr == "n*log2(n)**2":
        lg = math.log2(max(n, 2.0))
        return n * lg * lg
    if expr == "n*sqrt(n)":
        return n * math.sqrt(n)
    if expr == "n**2":
        return n * n
    if expr == "n**3":
        return n * n * n
    return n


@dataclass
class ModelFit:
    label: str
    expr: str
    r_squared: float = 0.0
    scale: float = 0.0

    def to_dict(self):
        rsq = None if self.r_squared != self.r_squared else round(self.r_squared, 4)
        return {"label": self.label, "expr": self.expr,
                "r_squared": rsq, "scale": self.scale}


@dataclass
class FitReport:
    best_fit: str
    best_expr: str
    ranking: list = field(default_factory=list)
    fit_score: float = 0.0
    warnings: list = field(default_factory=list)
    #: OLS slope of log T vs log n — the empirical growth exponent
    measured_exponent: float | None = None

    def to_dict(self):
        exp = self.measured_exponent
        return {"best_fit": self.best_fit, "best_expr": self.best_expr,
                "ranking": [m.to_dict() for m in self.ranking],
                "fit_score": round(self.fit_score, 4),
                "measured_exponent": None if exp is None else round(exp, 4),
                "warnings": list(self.warnings)}


def _slope_penalty(expr, xs, ys):
    """Small penalty when a growing model's log-log slope is far from 1.

    A *correct* power-law model fits ``log T = log c + slope * log shape`` with
    ``slope ~ 1``; a wrong model shows a slope that is not 1. Shapes that do not
    grow like a power of n are exempt.
    """
    if expr in _FLAT_SHAPES:
        return 0.0
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    k = len(lx)
    mx = sum(lx) / k
    my = sum(ly) / k
    sxx = sum((x - mx) ** 2 for x in lx)
    if sxx == 0:
        return 0.0
    slope = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sxx
    return min(0.3, abs(slope - 1.0) * 0.2)


def _fit_one(expr, points):
    """Least-squares fit of ``y ~= c * shape`` (through the origin)."""
    xs = [_shape(expr, n) for n, _ in points]
    ys = [float(t) for _, t in points]
    # a shape that is zero/undefined at one of the sizes cannot be judged
    if len(xs) < 2 or any(x <= 0 or y <= 0 for x, y in zip(xs, ys)):
        return ModelFit("?", expr, float("nan"), 0.0)
    den = sum(x * x for x in xs)
    c = (sum(x * y for x, y in zip(xs, ys)) / den) if den else 0.0
    ss_res = sum((y - c * x) ** 2 for x, y in zip(xs, ys))
    mean = sum(ys) / len(ys)
    ss_tot = sum((y - mean) ** 2 for y in ys)
    if ss_tot > 0:
        r2 = 1 - ss_res / ss_tot
    else:
        # constant measurements: only a constant model is an exact fit, so the
        # growing candidates must not all tie at R^2 = 1.
        r2 = 1.0 if ss_res <= _CONST_EPS * max(1.0, abs(mean)) else 0.0
    return ModelFit("?", expr, max(-1.0, r2 - _slope_penalty(expr, xs, ys)), c)


def _log_log_slope(points):
    """OLS slope of log T vs log n, i.e. the measured growth exponent."""
    pts = [(math.log(n), math.log(t)) for n, t in points if n > 1 and t > 0]
    if len(pts) < 2:
        return None
    k = len(pts)
    mx = sum(x for x, _ in pts) / k
    my = sum(y for _, y in pts) / k
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pts) / sxx


def fit_points(points):
    """Fit (n, seconds) points; returns FitReport."""
    pts = [(int(n), float(t)) for n, t in points if n > 0 and t > 0]
    rep = FitReport(best_fit="?", best_expr="n", fit_score=0.0)
    if len(pts) < 3:
        rep.warnings.append("need >=3 positive points; got %d" % len(pts))
        if len(pts) == 2:
            # still rank, but flag uncertainty
            pass
        else:
            return rep
    fits = []
    for label, expr in CANDIDATES:
        m = _fit_one(expr, pts)
        m.label = label
        fits.append(m)
    fits.sort(key=lambda m: (m.r_squared if m.r_squared == m.r_squared else -2),
              reverse=True)
    best = fits[0]
    rep.best_fit = best.label
    rep.best_expr = best.expr
    rep.ranking = fits
    rep.fit_score = best.r_squared if best.r_squared == best.r_squared else 0.0
    rep.measured_exponent = _log_log_slope(pts)
    if rep.fit_score < 0.9:
        rep.warnings.append("best R^2=%.3f; timing noise or model gap" % rep.fit_score)
    # tie warning
    if len(fits) > 1 and abs(fits[0].r_squared - fits[1].r_squared) < 0.02:
        rep.warnings.append("close call: %s vs %s; use larger sizes" % (
            fits[0].label, fits[1].label))
    return rep


__all__ = ["CANDIDATES", "ModelFit", "FitReport", "fit_points"]
