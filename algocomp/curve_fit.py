"""Curve fitting: match benchmark timings to Big-O growth models (stdlib only)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

CANDIDATES = (
    ("O(1)", "1"),
    ("O(log n)", "log2(n)"),
    ("O(n)", "n"),
    ("O(n log n)", "n*log2(n)"),
    ("O(n^2)", "n**2"),
    ("O(n^3)", "n**3"),
)


def _shape(expr, n):
    if expr == "1":
        return 1.0
    if expr == "log2(n)":
        return math.log2(max(n, 2))
    if expr == "n":
        return float(n)
    if expr == "n*log2(n)":
        return float(n) * math.log2(max(n, 2))
    if expr == "n**2":
        return float(n) ** 2
    if expr == "n**3":
        return float(n) ** 3
    return float(n)


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

    def to_dict(self):
        return {"best_fit": self.best_fit, "best_expr": self.best_expr,
                "ranking": [m.to_dict() for m in self.ranking],
                "fit_score": round(self.fit_score, 4),
                "warnings": list(self.warnings)}


def _fit_one(expr, points):
    xs = [_shape(expr, n) for n, _ in points]
    ys = [t for _, t in points]
    use = [(x, y) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(use) < 2:
        return ModelFit("?", expr, float("nan"), 0.0)
    lx = [math.log(x) for x, _ in use]
    ly = [math.log(y) for _, y in use]
    k = len(use)
    mx = sum(lx) / k
    my = sum(ly) / k
    sxx = sum((x - mx) ** 2 for x in lx)
    if sxx == 0:
        return ModelFit("?", expr, float("nan"), 0.0)
    sxy = sum((x - mx) * (y - my) for x, y in zip(lx, ly))
    slope = sxy / sxx
    # ideal slope: 0 for O(1)/O(log n) in n-space is wrong, so instead fit
    # y = c * shape in linear space via least squares through origin.
    num = sum(x * y for x, y in zip(xs, ys))
    den = sum(x * x for x in xs)
    c = num / den if den else 0.0
    ss_res = sum((y - c * x) ** 2 for x, y in zip(xs, ys))
    mean = sum(ys) / len(ys)
    ss_tot = sum((y - mean) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    # penalize models whose log-log slope is far from 1 (except O(1)/log).
    penalty = 0.0
    if expr in ("n", "n*log2(n)", "n**2", "n**3"):
        penalty = min(0.3, abs(slope - 1.0) * 0.2)
    return ModelFit("?", expr, max(-1.0, r2 - penalty), c)


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
    if rep.fit_score < 0.9:
        rep.warnings.append("best R^2=%.3f; timing noise or model gap" % rep.fit_score)
    # tie warning
    if len(fits) > 1 and abs(fits[0].r_squared - fits[1].r_squared) < 0.02:
        rep.warnings.append("close call: %s vs %s; use larger sizes" % (
            fits[0].label, fits[1].label))
    return rep


__all__ = ["CANDIDATES", "ModelFit", "FitReport", "fit_points"]
