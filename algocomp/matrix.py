"""Multi-algorithm comparison grids (`matrix` command)."""

from __future__ import annotations

import io
import math
from typing import Sequence

from .algorithm import Algorithm
from .complexity import Complexity

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:  # pragma: no cover
    HAS_RICH = False


def _rank_key(c: Complexity) -> tuple[float, float]:
    """Sort key: primary hierarchy rank, tie-broken by measured growth exponent.

    The tie-break matters because several distinct classes share a rank bucket
    (O(1), O(log log n) and O(log n) are all Θ(n^0)).
    """
    e = c.growth_exponent
    return (c.rank, e if not math.isnan(e) else math.inf)


def rank_algorithms(
    algos: Sequence[Algorithm], *, dimension: str = "time", case: str = "average"
) -> list[tuple[Algorithm, Complexity]]:
    """Sort best (fastest / smallest) first."""
    rows: list[tuple[Algorithm, Complexity]] = []
    for a in algos:
        prof = a.time if dimension == "time" else a.space
        if prof is None:
            continue
        mapping = dict(prof.items())
        c = mapping.get(case) or mapping.get("worst")
        if c is None:
            continue
        rows.append((a, c))
    rows.sort(key=lambda t: _rank_key(t[1]))
    return rows


_ANSI = __import__("re").compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (used when writing reports to a file)."""
    return _ANSI.sub("", text)


def render_matrix(
    algos: Sequence[Algorithm],
    *,
    dimension: str = "time",
    cases: Sequence[str] = ("best", "average", "worst"),
    include_space: bool = False,
    title: str | None = None,
    width: int = 118,
    color: bool | None = None,
) -> str:
    """Render a grid: rows = algorithms, columns = cases.

    `color=None` auto-detects: colours only when stdout is a TTY, so piping or
    redirecting to a file produces clean text.
    """
    if color is None:
        import sys

        color = bool(getattr(sys.stdout, "isatty", lambda: False)())
    if not algos:
        return "No algorithms matched."
    title = title or f"{dimension.capitalize()} complexity matrix ({len(algos)} algorithms)"

    columns: list[tuple[str, str]] = [(dimension, c) for c in cases]
    if include_space:
        columns += [("space", c) for c in cases]

    def cell(a: Algorithm, dim: str, case: str) -> Complexity | None:
        prof = a.time if dim == "time" else a.space
        if prof is None:
            return None
        mapping = dict(prof.items())
        return mapping.get(case) or (mapping.get("worst") if case == "average" else None)

    # best value per column, for highlighting
    best: dict[tuple[str, str], float] = {}
    for dim, case in columns:
        vals = [_rank_key(c)[0] for a in algos if (c := cell(a, dim, case)) is not None]
        if vals:
            best[(dim, case)] = min(vals)

    if HAS_RICH and color is not False:
        buf = io.StringIO()
        con = Console(width=width, file=buf, force_terminal=False,
                      color_system="standard" if color else None)
        t = Table(box=box.SIMPLE_HEAVY, title=title, title_style="bold cyan",
                  header_style="bold", expand=False, pad_edge=False)
        t.add_column("algorithm", style="bold", no_wrap=True)
        t.add_column("category", style="dim", no_wrap=True)
        for dim, case in columns:
            t.add_column(f"{dim}/{case}", justify="center")
        for a in algos:
            row = [a.name, a.category]
            for dim, case in columns:
                c = cell(a, dim, case)
                if c is None:
                    row.append("—")
                else:
                    txt = c.short
                    if best.get((dim, case)) is not None and _rank_key(c)[0] == best[(dim, case)]:
                        txt = f"[green]{txt} ★[/green]"
                    row.append(txt)
            t.add_row(*row)
        con.print(t)
        con.print("[dim]★ = best asymptotic bound in that column. Ranking uses the "
                  "growth hierarchy, so ties share the mark.[/dim]")
        return buf.getvalue()

    # ---- plain-text fallback
    headers = ["algorithm"] + [f"{d}/{c}" for d, c in columns]
    grid = []
    for a in algos:
        row = [a.name]
        for dim, case in columns:
            c = cell(a, dim, case)
            if c is None:
                row.append("-")
            else:
                mark = "*" if best.get((dim, case)) is not None and _rank_key(c)[0] == best[(dim, case)] else " "
                row.append(c.short + mark)
        grid.append(row)
    widths = [max(len(str(r[i])) for r in [headers] + grid) for i in range(len(headers))]
    line = lambda r: "  ".join(str(v).ljust(widths[i]) for i, v in enumerate(r))
    out = [title, line(headers), "  ".join("-" * w for w in widths)]
    out += [line(r) for r in grid]
    out.append("* = best asymptotic bound in that column")
    return "\n".join(out)


__all__ = ["render_matrix", "rank_algorithms", "strip_ansi"]
