"""The heart of the system: compare two algorithms that solve the same task.

`compare(a, b)` produces a `Verdict` containing:

  * per-case time & space comparison (best / average / worst)
  * asymptotic winner for each case, with the growth-ratio evidence
  * a dominance classification (strictly faster / equivalent / crossover)
  * the practical crossover input size, when one exists
  * comparability warnings (different tasks, incommensurable parameters)
  * a plain-language conclusion

Everything is derived from the *declared* complexities — no timing involved.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from .algorithm import Algorithm, ComplexityProfile
from .complexity import Complexity
from .expr import free_variables
from .registry import task_family

Order = Literal["faster", "slower", "equivalent"]

#: sizes used for the "what happens as n grows" table
DEFAULT_SIZES: tuple[float, ...] = (
    10, 100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000, 1_000_000_000,
)

#: beyond this the two growth curves are considered "asymptotically equal"
_EQ_TOL = 1e-6
#: Growth-exponent difference below which two bounds count as the same class.
#: Set to ~log2(log2(1e12)) so that a pure log factor (O(n) vs O(n log n)) lands
#: in the "same class, drifting apart" branch instead of being called a constant
#: factor. A real polynomial difference (n^1.2 vs n, n^2 vs n log n) is larger.
_EXP_TOL = 0.08
#: ratio-drift slope below which the gap is a pure constant factor
_TREND_TOL = 0.10
#: crossovers at or below this input size are meaningless in practice
_MIN_CROSSOVER = 8.0
#: below this relative separation the two curves count as tied (float64 noise)
_CROSS_EPS = 1e-9
#: where we sample to decide asymptotic dominance (kept below float64 overflow
#: for factorial/exponential entries)
_PROBE_SIZES = (1e2, 1e3, 1e4, 1e5)


@dataclass(frozen=True)
class CaseVerdict:
    """Comparison of A vs B for a single case (e.g. average time)."""

    dimension: str            # "time" | "space"
    case: str                 # "best" | "average" | "worst" | custom
    a: Complexity
    b: Complexity
    order: Order              # from A's point of view: "faster" means A wins
    growth_ratio: float       # gA/gB measured at a large finite n (evidence, not the limit)
    exponent_gap: float       # beta_A - beta_B from log-log growth exponents
    dominance: str            # see DOMINANCE_* below
    crossover: float | None   # smallest n where the ordering flips (None = never)
    crossover_meaningful: bool = False  # False when the flip happens below n=8
    gap: str = ""             # how the A/B cost limit behaves, e.g. "→ 0.5×"
    samples: list[tuple[float, float, float]] = field(default_factory=list)  # (n, a, b)

    # ------------------------------------------------------------ narratives

    @property
    def gap_label(self) -> str:
        """Short description of how the A/B cost ratio behaves as n grows."""
        return self.gap or _gap_label(self.dominance, self.growth_ratio, self.exponent_gap)

    @property
    def winner(self) -> Literal["A", "B", "tie"]:
        if self.order == "equivalent":
            return "tie"
        return "A" if self.order == "faster" else "B"

    def explain(self, name_a: str = "A", name_b: str = "B") -> str:
        wa, wb = (name_a, name_b) if self.winner == "A" else (name_b, name_a)
        base = f"{self.dimension}/{self.case}: {name_a} {self.a} vs {name_b} {self.b}"
        if self.winner == "tie":
            return f"{base} → asymptotically equivalent (same growth class)."
        ratio_txt = ""
        if self.dominance == DOMINANCE_CROSSOVER and self.crossover:
            if self.crossover_meaningful:
                ratio_txt = (
                    f" the ordering flips at n ≈ {_fmt(self.crossover)}: below it {wb} is "
                    f"cheaper, above it {wa} takes over and stays ahead."
                )
            else:
                ratio_txt = (
                    f" the curves touch only near n ≈ {_fmt(self.crossover)} (too small to "
                    f"matter), so {wa} is effectively ahead everywhere."
                )
        elif self.dominance == DOMINANCE_STRICT:
            if math.isinf(self.exponent_gap):
                ratio_txt = (
                    f" {wb} is explosive (exponential/factorial) while {wa} is not, so the "
                    f"advantage widens without bound."
                )
            else:
                ratio_txt = (
                    f" the cost ratio grows like n^{abs(self.exponent_gap):.2f}, so the "
                    f"advantage widens without bound as n grows."
                )
        elif self.dominance == DOMINANCE_CONSTANT:
            ratio_txt = (
                f" same growth class — a constant factor of about {_fmt(self.growth_ratio, 3)} "
                f"separates them, which Big-O hides."
            )
        return f"{base} → {wa} is asymptotically better.{ratio_txt}"


DOMINANCE_STRICT = "strict"        # one is better for all large n, ratio → 0 or ∞
DOMINANCE_CONSTANT = "constant"    # same growth class, ratio → finite constant ≠ 1
DOMINANCE_EQUAL = "equal"          # ratio → 1
DOMINANCE_CROSSOVER = "crossover"  # ordering flips at some finite n
DOMINANCE_INCOMPARABLE = "incomparable"


@dataclass(frozen=True)
class Verdict:
    """Full comparison result between two algorithms."""

    a: Algorithm
    b: Algorithm
    cases: list[CaseVerdict]
    warnings: list[str] = field(default_factory=list)
    comparable: bool = True

    # ------------------------------------------------------------- accessors

    def case(self, dimension: str, name: str) -> CaseVerdict | None:
        for c in self.cases:
            if c.dimension == dimension and c.case == name:
                return c
        return None

    @property
    def time_cases(self) -> list[CaseVerdict]:
        return [c for c in self.cases if c.dimension == "time"]

    @property
    def space_cases(self) -> list[CaseVerdict]:
        return [c for c in self.cases if c.dimension == "space"]

    @property
    def headline(self) -> CaseVerdict | None:
        """The single most quotable comparison: average time, else worst time."""
        return self.case("time", "average") or self.case("time", "worst")

    @property
    def overall_winner(self) -> tuple[str | None, str]:
        """Pick a winner across average-time, worst-time and worst-space.

        Returns (winner_key_or_None, reason).
        """
        scores = {"A": 0.0, "B": 0.0}
        weights = {("time", "average"): 3.0, ("time", "worst"): 2.0,
                   ("time", "best"): 0.5, ("space", "worst"): 1.5,
                   ("space", "average"): 1.0}
        for c in self.cases:
            w = weights.get((c.dimension, c.case), 0.5)
            if c.winner == "A":
                scores["A"] += w
            elif c.winner == "B":
                scores["B"] += w
        if scores["A"] > scores["B"]:
            return self.a.key, f"weighted score A={scores['A']:g} vs B={scores['B']:g}"
        if scores["B"] > scores["A"]:
            return self.b.key, f"weighted score A={scores['A']:g} vs B={scores['B']:g}"
        return None, "tie on every dimension"

    def conclusion(self) -> str:
        """A 2-4 sentence plain-language summary."""
        caveat = ""
        if not self.comparable:
            caveat = (
                f"These two do not solve the same task ({self.a.name}: {self.a.task}; "
                f"{self.b.name}: {self.b.task}), so read this as a reference comparison "
                f"rather than a like-for-like verdict. "
            )
        h = self.headline
        if h is None:  # pragma: no cover - always present in practice
            return "No comparable time complexity was declared."
        a_name, b_name = self.a.name, self.b.name
        if h.winner == "tie":
            first = (f"{a_name} and {b_name} are in the same asymptotic class for "
                     f"{h.case}-case time ({h.a}).")
            second = ("Any real difference comes from constant factors, cache behaviour "
                      "and allocation — measure before choosing.")
        else:
            win, lose = (a_name, b_name) if h.winner == "A" else (b_name, a_name)
            wc = h.a if h.winner == "A" else h.b
            lc = h.b if h.winner == "A" else h.a
            first = f"For {h.case}-case time, {win} ({wc}) beats {lose} ({lc})."
            if h.crossover:
                second = (f"The advantage only materialises above n ≈ {_fmt(h.crossover)}: "
                          f"for smaller inputs the theoretically worse algorithm can still win "
                          f"on constant factors.")
            else:
                second = f"{win} is better at every input size, not just asymptotically."

        extras: list[str] = []
        wt = self.case("time", "worst")
        if wt and wt.winner != "tie" and (h.winner == "tie" or wt.winner != h.winner):
            wn = a_name if wt.winner == "A" else b_name
            extras.append(f"worst case favours {wn} ({wt.a} vs {wt.b})")
        ws = self.case("space", "worst")
        if ws and ws.winner != "tie":
            wn = a_name if ws.winner == "A" else b_name
            extras.append(f"memory favours {wn} ({ws.a} vs {ws.b})")
        if self.a.stable is not None and self.b.stable is not None and self.a.stable != self.b.stable:
            extras.append(f"stability differs ({a_name}: {'stable' if self.a.stable else 'unstable'}, "
                          f"{b_name}: {'stable' if self.b.stable else 'unstable'})")
        if self.a.in_place is not None and self.b.in_place is not None and self.a.in_place != self.b.in_place:
            extras.append(f"in-place-ness differs ({a_name}: {'in-place' if self.a.in_place else 'extra memory'}, "
                          f"{b_name}: {'in-place' if self.b.in_place else 'extra memory'})")
        if extras:
            tail = "; ".join(extras)
            tail = tail[0].upper() + tail[1:] + "."
        else:
            tail = ""
        return f"{caveat}{first} {second} {tail}".strip()

    def to_dict(self) -> dict:
        """JSON-serialisable form (used by `--format json`)."""

        def cv(c: CaseVerdict) -> dict:
            return {
                "dimension": c.dimension,
                "case": c.case,
                "a": {"expr": c.a.expr, "label": c.a.resolved_label,
                      "growth_exponent": _round(c.a.growth_exponent),
                      "growth_class": c.a.growth_class()},
                "b": {"expr": c.b.expr, "label": c.b.resolved_label,
                      "growth_exponent": _round(c.b.growth_exponent),
                      "growth_class": c.b.growth_class()},
                "winner": c.winner,
                "dominance": c.dominance,
                "growth_ratio": _round(c.growth_ratio, 6) if not math.isinf(c.growth_ratio) else "inf",
                "exponent_gap": _round(c.exponent_gap, 6),
                "gap_label": c.gap_label,
                "crossover_n": c.crossover if c.crossover_meaningful else None,
                "crossover_raw_n": c.crossover,
                "samples": [[n, _round(x), _round(y)] for n, x, y in c.samples],
                "explanation": c.explain(self.a.name, self.b.name),
            }

        winner, reason = self.overall_winner
        return {
            "a": _algo_dict(self.a),
            "b": _algo_dict(self.b),
            "comparable": self.comparable,
            "warnings": self.warnings,
            "cases": [cv(c) for c in self.cases],
            "overall_winner": winner,
            "overall_reason": reason,
            "conclusion": self.conclusion(),
        }


def _algo_dict(a: Algorithm) -> dict:
    def prof(p: ComplexityProfile | None) -> dict | None:
        if p is None:
            return None
        return {name: {"expr": c.expr, "label": c.resolved_label} for name, c in p.items()}

    return {
        "key": a.key,
        "name": a.name,
        "category": a.category,
        "task": a.task,
        "time": prof(a.time),
        "space": prof(a.space),
        "stable": a.stable,
        "in_place": a.in_place,
        "notes": a.notes,
    }


# --------------------------------------------------------------------------- #
# Comparison engine
# --------------------------------------------------------------------------- #


def compare(
    a: Algorithm,
    b: Algorithm,
    *,
    sizes: tuple[float, ...] = DEFAULT_SIZES,
    compare_space: bool = True,
    cases: tuple[str, ...] = ("best", "average", "worst"),
) -> Verdict:
    """Compare two algorithms theoretically.

    Parameters
    ----------
    sizes:
        Input sizes used to build the growth table and to locate crossovers.
    compare_space:
        Also compare auxiliary memory.
    cases:
        Which named cases to compare; unknown cases present on only one side are
        reported as a warning rather than silently dropped.
    """
    warnings: list[str] = []
    comparable = True

    if task_family(a.task) != task_family(b.task):
        comparable = False
        warnings.append(
            f"Different tasks: {a.name} solves \"{a.task}\" while {b.name} solves "
            f"\"{b.task}\". The comparison below is only meaningful if you consider "
            f"these tasks equivalent."
        )
    elif _slug(a.task) != _slug(b.task):
        warnings.append(
            f"Same problem, different preconditions: \"{a.task}\" vs \"{b.task}\". "
            f"Check that your workload satisfies both before trusting the verdict."
        )
    if a.category != b.category:
        warnings.append(f"Different families: {a.category} vs {b.category}.")

    cases_out: list[CaseVerdict] = []

    # ---- time
    cases_out += _compare_profile(
        "time", a.time, b.time, cases, sizes, warnings, a.name, b.name
    )
    # ---- space
    if compare_space:
        if a.space is None or b.space is None:
            missing = a.name if a.space is None else b.name
            warnings.append(f"No space complexity declared for {missing}; memory not compared.")
        else:
            cases_out += _compare_profile(
                "space", a.space, b.space, cases, sizes, warnings, a.name, b.name
            )

    if not cases_out:  # pragma: no cover
        raise ValueError("nothing to compare: no matching complexity cases")

    # ---- parameter mismatch check
    _check_parameters(a, b, cases_out, warnings)

    return Verdict(a=a, b=b, cases=cases_out, warnings=warnings, comparable=comparable)


def _compare_profile(
    dimension: str,
    pa: ComplexityProfile,
    pb: ComplexityProfile,
    cases: tuple[str, ...],
    sizes: tuple[float, ...],
    warnings: list[str],
    name_a: str,
    name_b: str,
) -> list[CaseVerdict]:
    out: list[CaseVerdict] = []
    avail_a = dict(pa.items())
    avail_b = dict(pb.items())
    # honour the requested cases exactly; if none of them exist on either side,
    # fall back to everything both sides declare in common.
    wanted = [c for c in cases if c in avail_a or c in avail_b]
    if not wanted:
        wanted = [c for c, _ in pa.items() if c in avail_b]

    for case in wanted:
        ca, cb = avail_a.get(case), avail_b.get(case)
        if ca is None and cb is None:
            continue
        if ca is None or cb is None:
            present = name_a if ca is not None else name_b
            absent = name_b if ca is not None else name_a
            known = ca or cb
            if dimension == "space":
                # Memory is normally quoted as an upper bound, so a missing case
                # can safely fall back to that algorithm's worst-case space
                # instead of silently dropping the row.
                if ca is None:
                    ca, sub_for, sub_val = pa.worst, name_a, pa.worst
                else:
                    cb, sub_for, sub_val = pb.worst, name_b, pb.worst
                warnings.append(
                    f"space/{case} is not declared for {sub_for}; its worst-case "
                    f"bound ({sub_val.resolved_label}) is used as a conservative stand-in."
                )
            else:
                warnings.append(
                    f"{dimension}/{case} declared only for {present} ({known}); "
                    f"{absent} has no {case}-case bound, so this case is skipped."
                )
                continue
        out.append(_compare_case(dimension, case, ca, cb, sizes))
    return out


def _compare_case(
    dimension: str, case: str, ca: Complexity, cb: Complexity, sizes: tuple[float, ...]
) -> CaseVerdict:
    samples = [(n, ca.value(n), cb.value(n)) for n in sizes]

    # asymptotic ratio  gA/gB  using the largest sizes where both are finite
    ratio = _asymptotic_ratio(ca, cb)
    dominance, order, gap = _classify(ratio, ca, cb)
    crossover = _find_crossover(ca, cb, order, dominance)
    gap_label = _gap_label(dominance, ratio, gap)

    return CaseVerdict(
        dimension=dimension,
        case=case,
        a=ca,
        b=cb,
        order=order,
        growth_ratio=ratio,
        exponent_gap=gap,
        dominance=dominance,
        crossover=crossover,
        crossover_meaningful=crossover is not None and crossover >= _MIN_CROSSOVER,
        gap=gap_label,
        samples=samples,
    )


def _asymptotic_ratio(ca: Complexity, cb: Complexity) -> float:
    """Estimate lim_{n→∞} gA(n)/gB(n) at the largest n where both stay finite.

    The ratio can oscillate when a lower-order term is numerically swamped by
    float64 (e.g. `n+k` with k=n looks like exactly 2n), so we take the median
    over the top probes rather than the single largest one.
    """
    ratios: list[float] = []
    for n in _PROBE_SIZES:
        va, vb = ca.value(n), cb.value(n)
        if vb == 0:
            continue
        if math.isinf(va) and math.isinf(vb):
            continue  # both overflowed — try a smaller n
        if math.isinf(va):
            ratios.append(math.inf)
        elif math.isinf(vb):
            ratios.append(0.0)
        elif va > 0:
            ratios.append(va / vb)
    if not ratios:
        ea, eb = ca.growth_exponent, cb.growth_exponent
        if math.isnan(ea) or math.isnan(eb):
            return 1.0
        if ea > eb + _EQ_TOL:
            return math.inf
        if eb > ea + _EQ_TOL:
            return 0.0
        return 1.0

    finite = sorted(r for r in ratios if not math.isinf(r) and r > 0)
    n_inf = sum(1 for r in ratios if math.isinf(r))
    n_zero = sum(1 for r in ratios if r == 0.0)
    if n_inf >= n_zero and n_inf >= max(1, len(ratios) // 2):
        return math.inf
    if n_zero > n_inf and n_zero >= max(1, len(ratios) // 2):
        return 0.0
    if not finite:
        return 1.0
    mid = len(finite) // 2
    return finite[mid] if len(finite) % 2 else math.sqrt(finite[mid - 1] * finite[mid])


def _classify(ratio: float, ca: Complexity, cb: Complexity) -> tuple[str, Order, float]:
    """Classify the asymptotic relationship between two growth functions.

    Returns ``(dominance, order, exponent_gap)`` where ``exponent_gap`` is
    ``beta_A - beta_B`` for the log-log growth exponents.

    Classification is driven by the *growth exponents* rather than the raw
    ratio: a float64 ratio underflows to 0 or saturates long before n→∞, so
    ``n²`` vs ``n log n`` would look like a constant factor at any finite probe.
    Exponents are computed over a decade span, so they are stable.
    """
    ea, eb = ca.growth_exponent, cb.growth_exponent
    gap = ea - eb

    if math.isinf(ea) or math.isinf(eb):
        dominance, order, gap = _explosive_order(ca, cb)
        if order != "equivalent" and _crosses(ca, cb):
            dominance = DOMINANCE_CROSSOVER
        return dominance, order, gap

    if math.isnan(gap):
        order = "equivalent" if ratio == 1.0 else ("slower" if ratio > 1.0 else "faster")
        dominance = DOMINANCE_CONSTANT if order != "equivalent" else DOMINANCE_EQUAL
    elif abs(gap) <= _EXP_TOL:
        # Same growth exponent. The limit is normally a finite constant, but a
        # slowly drifting factor (log n, log log n) can hide a strict gap, so we
        # look at how the ratio behaves across three decades before deciding.
        if abs(ratio - 1.0) <= _EQ_TOL and _is_flat(ca, cb):
            order, dominance = "equivalent", DOMINANCE_EQUAL
        elif _drifts_apart(ca, cb):
            # a log-like factor that keeps compounding: strictly better, slowly
            trend = _ratio_trend(ca, cb)
            order = "faster" if trend < 0 else "slower"
            dominance = DOMINANCE_STRICT
        else:
            order = "faster" if ratio < 1.0 else "slower"
            dominance = DOMINANCE_CONSTANT
    else:
        order = "faster" if gap < 0 else "slower"
        dominance = DOMINANCE_STRICT

    if order != "equivalent" and _crosses(ca, cb):
        dominance = DOMINANCE_CROSSOVER
    return dominance, order, gap


def _explosive_order(ca: Complexity, cb: Complexity) -> tuple[str, Order, float]:
    """Order two explosive bounds (factorial, n^n, a^n) by magnitude.

    They all have an infinite growth exponent, so the exponent cannot separate
    them — and a naive comparison at a single probe is wrong whenever one side
    overflows (`n!` is still finite at n=120 while `2^n` is not). So we take the
    largest probe where *both* values remain finite and compare there.
    """
    for n in reversed((20, 40, 80, 120, 170, 300, 500, 1000)):
        va, vb = ca.value(n), cb.value(n)
        if math.isinf(va) or math.isinf(vb) or va <= 0 or vb <= 0:
            continue
        rel = abs(va - vb) / max(va, vb)
        if rel <= _EQ_TOL:
            return DOMINANCE_EQUAL, "equivalent", 0.0
        if va > vb:
            return DOMINANCE_STRICT, "slower", math.inf    # A grows faster
        return DOMINANCE_STRICT, "faster", -math.inf
    # No size made both finite: treat them as the same explosive class.
    return DOMINANCE_EQUAL, "equivalent", 0.0


def _drift_series(ca: Complexity, cb: Complexity) -> list[float]:
    """gA/gB sampled across decades where both sides stay finite and positive."""
    out = []
    for n in (1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7):
        va, vb = ca.value(n), cb.value(n)
        if va <= 0 or vb <= 0 or math.isinf(va) or math.isinf(vb):
            continue
        out.append(va / vb)
    return out


def _is_flat(ca: Complexity, cb: Complexity) -> bool:
    """True when gA/gB stays within a hair of 1 across every usable decade."""
    series = _drift_series(ca, cb)
    return bool(series) and all(abs(r - 1.0) <= _EQ_TOL for r in series)


def _drifts_apart(ca: Complexity, cb: Complexity) -> bool:
    """True when gA/gB moves monotonically away from a constant by a real margin.

    A log n factor separating `n log n` from `n` shrinks (or grows) by ~2x over
    five decades; noise and lower-order wobble do not move monotonically that far.
    """
    series = _drift_series(ca, cb)
    if len(series) < 4:
        return False
    monotone_down = all(y < x for x, y in zip(series, series[1:]))
    monotone_up = all(y > x for x, y in zip(series, series[1:]))
    if not (monotone_down or monotone_up):
        return False
    total = series[0] / series[-1] if monotone_down else series[-1] / series[0]
    return total > 1.5


def _ratio_trend(ca: Complexity, cb: Complexity) -> float:
    """Slope of log(gA/gB) against log n across three decades.

    < 0 means A pulls ahead as n grows, > 0 means A falls behind, ≈ 0 means the
    ratio settles on a constant (a pure constant-factor difference).
    """
    pts: list[tuple[float, float]] = []
    for n in (1e2, 1e4, 1e6):
        va, vb = ca.value(n), cb.value(n)
        if va <= 0 or vb <= 0 or math.isinf(va) or math.isinf(vb):
            continue
        pts.append((math.log(n), math.log(va / vb)))
    if len(pts) < 2:
        return 0.0
    k = len(pts)
    mx = sum(x for x, _ in pts) / k
    my = sum(y for _, y in pts) / k
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in pts) / sxx


def _gap_label(dominance: str, ratio: float, gap: float) -> str:
    """How the A/B cost ratio behaves as n grows — the 'asymptotic advantage'."""
    if dominance == DOMINANCE_EQUAL:
        return "equal"
    if dominance == DOMINANCE_CONSTANT:
        return f"→ {_fmt(ratio, 3)}×"
    if math.isinf(gap):
        return "A/B → ∞ (explosive)" if gap > 0 else "A/B → 0 (explosive)"
    if math.isnan(gap):
        return "n/a"
    return f"A/B → ∞ (≈ n^{abs(gap):.2f})" if gap > 0 else f"A/B → 0 (≈ n^{abs(gap):.2f})"


def _crosses(ca: Complexity, cb: Complexity) -> bool:
    """Does the sign of (gA - gB) change over the sampled range?

    Points where the two curves are numerically tied are ignored: an exact tie
    at n=2 is an artefact of dropping constant factors, not a real crossover.
    """
    signs = set()
    for n in (2, 4, 8, 16, 64, 256, 1024, 4096, 65536, 1e6, 1e8):
        va, vb = ca.value(n), cb.value(n)
        if math.isinf(va) or math.isinf(vb):
            continue
        scale = max(abs(va), abs(vb))
        if scale <= 0 or abs(va - vb) <= _CROSS_EPS * scale:
            continue
        signs.add(1 if va > vb else -1)
    return len(signs) == 2


def _find_crossover(
    ca: Complexity, cb: Complexity, order: Order, dominance: str
) -> float | None:
    """Smallest n where the asymptotically worse side starts losing.

    Returns None when no meaningful crossing exists (one side wins at every
    realistic input size).
    """
    if order == "equivalent":
        return None
    worse, better = (ca, cb) if order == "slower" else (cb, ca)

    grid = [2.0]
    v = 2.0
    while v < 1e18:
        v *= 1.2589  # ~10 steps per decade
        grid.append(v)

    prev_sign: int | None = None
    prev_n = grid[0]
    for n in grid:
        wa, wb = worse.value(n), better.value(n)
        if math.isinf(wa) or math.isinf(wb) or wb <= 0:
            continue
        rel = abs(wa - wb) / max(abs(wa), abs(wb))
        if rel <= _CROSS_EPS:            # numerically tied — keep scanning
            continue
        sign = 1 if wa > wb else -1
        if prev_sign is not None and prev_sign < 0 and sign > 0:
            return _bisect(lambda x: worse.value(x) - better.value(x), prev_n, n)
        prev_sign, prev_n = sign, n
    return None


def _bisect(f, lo: float, hi: float, iters: int = 80) -> float:
    """Bisection on a sign change of f between lo and hi."""
    flo = f(lo)
    for _ in range(iters):
        mid = math.sqrt(lo * hi) if lo > 0 and hi > 0 else (lo + hi) / 2
        if mid <= lo or mid >= hi:
            break
        fmid = f(mid)
        if math.isnan(fmid):
            break
        if (flo < 0) == (fmid < 0):
            lo, flo = mid, fmid
        else:
            hi = mid
    return math.sqrt(lo * hi) if lo > 0 and hi > 0 else (lo + hi) / 2


def _check_parameters(
    a: Algorithm, b: Algorithm, cases: list[CaseVerdict], warnings: list[str]
) -> None:
    """Warn when the two sides are expressed in different variables."""
    va: set[str] = set()
    vb: set[str] = set()
    for c in cases:
        va |= set(free_variables(c.a.expr))
        vb |= set(free_variables(c.b.expr))
    only_a, only_b = va - vb, vb - va
    if only_a or only_b:
        warnings.append(
            "The two bounds use different parameters "
            f"({a.name}: {sorted(va)}, {b.name}: {sorted(vb)}). "
            "Numeric samples below assume every non-`n` parameter equals n, so "
            "read them as shape comparisons, not exact values."
        )


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def _slug(text: str) -> str:
    import re

    return re.sub(r"_+", "_", "".join(ch if ch.isalnum() else "_" for ch in str(text).lower())).strip("_")


def _fmt(x: float, sig: int = 3) -> str:
    if x is None:
        return "-"
    if math.isinf(x):
        return "∞"
    if x != x:  # NaN
        return "n/a"
    if x >= 1e6:
        return f"{x:,.0f}"
    if x >= 100 or abs(x - round(x)) < 1e-9:
        return f"{x:,.0f}"
    return f"{x:.{sig}g}"


def _round(x: float | None, digits: int = 4) -> float | str | None:
    if x is None:
        return None
    if math.isinf(x):
        return "inf"
    if math.isnan(x):
        return None
    return round(x, digits)


__all__ = [
    "compare", "Verdict", "CaseVerdict", "DEFAULT_SIZES",
    "DOMINANCE_STRICT", "DOMINANCE_CONSTANT", "DOMINANCE_EQUAL",
    "DOMINANCE_CROSSOVER", "DOMINANCE_INCOMPARABLE",
]
