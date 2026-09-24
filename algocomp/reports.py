"""Report rendering: terminal (rich), Markdown, HTML and JSON.

All renderers take the same `Verdict` produced by `comparator.compare`.
"""

from __future__ import annotations

import html
import io
import json
import math
import sys
from typing import Sequence

from .algorithm import Algorithm
from .comparator import CaseVerdict, Verdict, _fmt
from .complexity import Complexity

try:  # rich is optional — plain-text fallback keeps the tool dependency-free
    from rich import box
    from rich.console import Console, Group
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:  # pragma: no cover
    HAS_RICH = False


WIN_COLOR = {"A": "green", "B": "magenta", "tie": "yellow"}


# --------------------------------------------------------------------------- #
# Shared data shaping
# --------------------------------------------------------------------------- #


def _rows(v: Verdict) -> list[dict]:
    rows = []
    for c in v.cases:
        rows.append(
            {
                "dim": c.dimension,
                "case": c.case,
                "a": c.a.resolved_label,
                "b": c.b.resolved_label,
                "winner": c.winner,
                "ratio": c.gap_label,
                "class_a": c.a.growth_class(),
                "class_b": c.b.growth_class(),
                "exp_a": _fmt(c.a.growth_exponent, 3),
                "exp_b": _fmt(c.b.growth_exponent, 3),
                "cross": _fmt(c.crossover) if c.crossover and c.crossover_meaningful else "—",
                "dominance": c.dominance,
            }
        )
    return rows


def _algo_lines(a: Algorithm) -> list[tuple[str, str]]:
    out = [("category", a.category), ("task", a.task)]
    for name, c in a.time.items():
        out.append((f"time {name}", c.resolved_label))
    if a.space:
        for name, c in a.space.items():
            out.append((f"space {name}", c.resolved_label))
    if a.stable is not None:
        out.append(("stable", "yes" if a.stable else "no"))
    if a.in_place is not None:
        out.append(("in place", "yes" if a.in_place else "no"))
    if a.time.is_case_sensitive:
        out.append(("input sensitive", "yes — best/average/worst differ"))
    return out


# --------------------------------------------------------------------------- #
# Terminal (rich)
# --------------------------------------------------------------------------- #


def render_terminal(v: Verdict, *, growth_table: bool = True, chart: bool = True,
                    notes: bool = True, width: int = 100,
                    color: bool | None = None) -> str:
    """Render the full terminal report.

    `color=None` auto-detects: ANSI colours only when stdout is a TTY, so
    `--out report.txt` and piping both produce clean text.
    """
    if not HAS_RICH:  # pragma: no cover
        return render_markdown(v, growth_table=growth_table, chart=chart, notes=notes)

    if color is None:
        color = bool(getattr(sys.stdout, "isatty", lambda: False)())
    buf = io.StringIO()
    con = Console(width=width, file=buf, force_terminal=False,
                  color_system="standard" if color else None)

    A, B = v.a, v.b
    con.print(Panel.fit(
        f"[bold]Algorithm Comparison[/bold]  ·  [cyan]{A.name}[/cyan]  [dim]vs[/dim]  [magenta]{B.name}[/magenta]",
        border_style="cyan",
    ))

    if not v.comparable:
        con.print(Panel("[bold red]⚠ Not strictly comparable[/bold red]\n" +
                        "\n".join(f"• {w}" for w in v.warnings), border_style="red"))
    elif v.warnings:
        con.print(Panel("\n".join(f"[yellow]•[/yellow] {w}" for w in v.warnings),
                        title="warnings", border_style="yellow"))

    # ---- side by side profile
    t = Table(box=box.SIMPLE_HEAVY, expand=True, show_header=True,
              header_style="bold", title="Complexity profiles", title_style="bold cyan")
    t.add_column("", style="dim", width=18)
    t.add_column(A.name, style="cyan", ratio=1)
    t.add_column(B.name, style="magenta", ratio=1)
    la, lb = _algo_lines(A), _algo_lines(B)
    keys = list(dict.fromkeys([k for k, _ in la] + [k for k, _ in lb]))
    da, db = dict(la), dict(lb)
    for k in keys:
        t.add_row(k, da.get(k, "—"), db.get(k, "—"))
    con.print(t)

    # ---- verdict table
    t2 = Table(box=box.ROUNDED, expand=True, title="Case-by-case verdict",
               title_style="bold cyan", header_style="bold")
    t2.add_column("dimension", style="dim")
    t2.add_column("case")
    t2.add_column(A.name, justify="right")
    t2.add_column(B.name, justify="right")
    t2.add_column("winner", justify="center")
    t2.add_column("A/B as n→∞", justify="right", style="dim")
    t2.add_column("crossover n", justify="right", style="dim")
    for r in _rows(v):
        w = r["winner"]
        colour = WIN_COLOR[w]
        label = {"A": f"[{colour}]◀ {A.name}[/{colour}]",
                 "B": f"[{colour}]{B.name} ▶[/{colour}]",
                 "tie": f"[{colour}]tie[/{colour}]"}[w]
        t2.add_row(r["dim"], r["case"], r["a"], r["b"], label, r["ratio"], r["cross"])
    con.print(t2)

    # ---- growth table
    if growth_table:
        head = v.headline or v.time_cases[0]
        gt = Table(box=box.SIMPLE, expand=True,
                   title=f"Operation-count growth ({head.dimension}/{head.case} case)",
                   title_style="bold cyan", header_style="bold")
        gt.add_column("n", justify="right", style="dim")
        gt.add_column(f"{A.name}  {head.a}", justify="right", style="cyan")
        gt.add_column(f"{B.name}  {head.b}", justify="right", style="magenta")
        gt.add_column("A ÷ B", justify="right")
        gt.add_column("cheaper", justify="center")
        for n, x, y in head.samples:
            ratio = x / y if y else math.inf
            if math.isinf(ratio):
                rt, cheaper = "∞", ("B" if not math.isinf(y) else "—")
            elif ratio == 0:
                rt, cheaper = "0", "A"
            else:
                rt = _fmt(ratio, 3)
                cheaper = "A" if ratio < 1 else ("B" if ratio > 1 else "=")
            gt.add_row(_fmt(n), _sci(x), _sci(y), rt,
                       f"[{WIN_COLOR.get({'A': 'A', 'B': 'B', '=': 'tie'}[cheaper])}]{cheaper}[/]")
        con.print(gt)

    # ---- chart
    if chart:
        head = v.headline or v.time_cases[0]
        con.print(Panel(ascii_chart(head, width=width - 6), title="log-log growth",
                        border_style="blue"))

    # ---- explanations
    ex = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    ex.add_column(style="dim", width=2)
    ex.add_column(ratio=1)
    for c in v.cases:
        ex.add_row("→", c.explain(A.name, B.name))
    con.print(Panel(ex, title="Reasoning", border_style="blue"))

    # ---- conclusion
    winner, reason = v.overall_winner
    wname = A.name if winner == A.key else (B.name if winner == B.key else "neither")
    con.print(Panel(
        f"[bold]{v.conclusion()}[/bold]\n\n"
        f"[dim]overall winner: [bold]{wname}[/bold] ({reason})[/dim]",
        title="Conclusion", border_style="green",
    ))

    if notes and (A.notes or B.notes):
        nt = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold",
                   title="Caveats & constant factors", title_style="bold yellow")
        nt.add_column("algorithm", width=max(12, len(A.name)))
        nt.add_column("notes", ratio=1)
        for algo in (A, B):
            if algo.notes:
                nt.add_row(algo.name, algo.notes)
        con.print(nt)

    con.print(f"[dim]Theoretical analysis only — Big-O hides constant factors, cache "
              f"behaviour and allocation cost. Verify with `verify` before deciding.[/dim]")
    return buf.getvalue()


def _sci(x: float) -> str:
    if x is None:
        return "—"
    if math.isinf(x):
        return "∞"
    if x != x:
        return "n/a"
    if x == 0:
        return "0"
    if x >= 1e12 or x < 1e-4:
        return f"{x:.2e}"
    return f"{x:,.3g}"


# --------------------------------------------------------------------------- #
# ASCII log-log chart
# --------------------------------------------------------------------------- #


def ascii_chart(c: CaseVerdict, *, width: int = 76, height: int = 18) -> str:
    """Render gA(n) and gB(n) on a log-log grid (both axes logarithmic)."""
    pts = [(n, x, y) for n, x, y in c.samples if _finite(x) and _finite(y) and x > 0 and y > 0]
    if len(pts) < 2:
        return "(not enough finite samples to plot)"

    lx = [math.log10(n) for n, _, _ in pts]
    la = [math.log10(x) for _, x, _ in pts]
    lb = [math.log10(y) for _, _, y in pts]
    x0, x1 = min(lx), max(lx)
    y0 = min(min(la), min(lb))
    y1 = max(max(la), max(lb))
    if x1 - x0 < 1e-9:
        return "(all samples at the same n)"
    pad = (y1 - y0) * 0.08 or 1.0
    y0, y1 = y0 - pad, y1 + pad

    grid = [[" "] * width for _ in range(height)]

    def put(px: float, py: float, ch: str) -> None:
        col = int(round((px - x0) / (x1 - x0) * (width - 1)))
        row = int(round((1 - (py - y0) / (y1 - y0)) * (height - 1)))
        if not (0 <= col < width and 0 <= row < height):
            return
        cur = grid[row][col]
        if cur == " ":
            grid[row][col] = ch
        elif cur != ch:
            # two different curves occupy this cell: they cross or coincide
            grid[row][col] = "X" if cur in "AB" else "X"

    def curve(vals: Sequence[float], ch: str) -> None:
        for i in range(len(vals) - 1):
            steps = max(2, int((lx[i + 1] - lx[i]) / (x1 - x0) * width * 2))
            for k in range(steps + 1):
                t = k / steps
                put(lx[i] + t * (lx[i + 1] - lx[i]),
                    vals[i] + t * (vals[i + 1] - vals[i]), ch)

    curve(la, "A")
    curve(lb, "B")

    lines = []
    for r, row in enumerate(grid):
        frac = 1 - r / (height - 1)
        val = 10 ** (y0 + frac * (y1 - y0))
        label = f"{val:>9.1e}" if r % 4 == 0 else " " * 9
        lines.append(f"{label} │{''.join(row)}")
    lines.append(" " * 10 + "└" + "─" * width)

    # x-axis ticks: place only when the previous label has ended
    tick_row = [" "] * (width + 2)
    cursor = 0
    for i, (n, _, _) in enumerate(pts):
        col = int(round((lx[i] - x0) / (x1 - x0) * (width - 1))) + 1
        txt = _fmt(n)
        if col < cursor or col + len(txt) > width + 1:
            continue
        for j, ch in enumerate(txt):
            tick_row[col + j] = ch
        cursor = col + len(txt) + 3
    lines.append(" " * 10 + "".join(tick_row).rstrip() + "   ← n")
    lines.append(f"  A = {c.a}   B = {c.b}   X = the two curves cross/coincide here")
    lines.append(f"  ({c.dimension}/{c.case} case · both axes log-scaled · y = operations)")
    return "\n".join(lines)


def _finite(x: float) -> bool:
    return x is not None and not math.isinf(x) and not math.isnan(x)


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #


def render_markdown(v: Verdict, *, growth_table: bool = True, chart: bool = True,
                    notes: bool = True) -> str:
    A, B = v.a, v.b
    out: list[str] = []
    out.append(f"# Algorithm comparison: {A.name} vs {B.name}\n")
    out.append(f"> **Task:** {A.task}  ·  **Family:** {A.category}\n")

    if not v.comparable:
        out.append("\n> ⚠️ **Not strictly comparable** — see warnings below.\n")
    if v.warnings:
        out.append("\n**Warnings**\n")
        out.extend(f"- {w}" for w in v.warnings)
        out.append("")

    out.append("\n## Conclusion\n")
    out.append(v.conclusion() + "\n")
    winner, reason = v.overall_winner
    wname = A.name if winner == A.key else (B.name if winner == B.key else "Neither (tie)")
    out.append(f"**Overall winner: {wname}** ({reason})\n")

    out.append("\n## Complexity profiles\n")
    out.append(f"| | {A.name} | {B.name} |")
    out.append("|---|---|---|")
    la, lb = dict(_algo_lines(A)), dict(_algo_lines(B))
    for k in dict.fromkeys([x[0] for x in _algo_lines(A)] + [x[0] for x in _algo_lines(B)]):
        out.append(f"| **{k}** | {la.get(k, '—')} | {lb.get(k, '—')} |")

    out.append("\n## Case-by-case verdict\n")
    out.append(f"| dimension | case | {A.name} | {B.name} | winner | A÷B as n→∞ | crossover n |")
    out.append("|---|---|---|---|---|---|---|")
    for r in _rows(v):
        w = {"A": A.name, "B": B.name, "tie": "tie"}[r["winner"]]
        out.append(f"| {r['dim']} | {r['case']} | `{r['a']}` | `{r['b']}` | **{w}** | {r['ratio']} | {r['cross']} |")

    head = v.headline or v.time_cases[0]
    if growth_table:
        out.append(f"\n## Growth of the operation count ({head.dimension}/{head.case} case)\n")
        out.append(f"| n | {A.name} `{head.a}` | {B.name} `{head.b}` | A ÷ B | cheaper |")
        out.append("|---|---|---|---|---|")
        for n, x, y in head.samples:
            ratio = x / y if y else math.inf
            rt = "∞" if math.isinf(ratio) else ("0" if ratio == 0 else _fmt(ratio, 3))
            cheaper = "A" if ratio and ratio < 1 else ("B" if ratio and ratio > 1 else "=")
            out.append(f"| {_fmt(n)} | {_sci(x)} | {_sci(y)} | {rt} | {cheaper} |")
        out.append("\n*Values are the declared growth functions evaluated at n — they "
                   "count abstract operations, not seconds.*\n")

    out.append("\n## Reasoning\n")
    for c in v.cases:
        out.append(f"- {c.explain(A.name, B.name)}")

    out.append("\n## Growth classes\n")
    out.append(f"| case | {A.name} | class | growth exponent | {B.name} | class | growth exponent |")
    out.append("|---|---|---|---|---|---|---|")
    for r in _rows(v):
        out.append(f"| {r['dim']}/{r['case']} | `{r['a']}` | {r['class_a']} | {r['exp_a']} | "
                   f"`{r['b']}` | {r['class_b']} | {r['exp_b']} |")
    out.append("\n*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and "
               "10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, "
               "≫2 exponential/factorial.*\n")

    if chart:
        out.append("\n## Growth chart (log-log, ASCII)\n")
        out.append("```text")
        out.append(ascii_chart(head, width=76))
        out.append("```")

    if notes and (A.notes or B.notes):
        out.append("\n## Caveats & constant factors\n")
        for algo in (A, B):
            if algo.notes:
                out.append(f"- **{algo.name}:** {algo.notes}")

    out.append("\n---\n")
    out.append("*Theoretical comparison generated by `algo-compare`. Big-O notation hides "
               "constant factors, memory-hierarchy effects and allocation cost — always "
               "confirm with an empirical benchmark (`algo-compare verify`) before making "
               "a production decision.*\n")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #


def render_json(v: Verdict, *, indent: int = 2) -> str:
    return json.dumps(v.to_dict(), indent=indent, default=str, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# HTML (self-contained, no external assets)
# --------------------------------------------------------------------------- #


def render_html(v: Verdict, *, notes: bool = True) -> str:
    A, B = v.a, v.b
    head = v.headline or v.time_cases[0]
    rows = _rows(v)
    winner, reason = v.overall_winner
    wname = A.name if winner == A.key else (B.name if winner == B.key else "Tie")

    la, lb = dict(_algo_lines(A)), dict(_algo_lines(B))
    profile_rows = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(la.get(k, '—'))}</td>"
        f"<td>{html.escape(lb.get(k, '—'))}</td></tr>"
        for k in dict.fromkeys([x[0] for x in _algo_lines(A)] + [x[0] for x in _algo_lines(B)])
    )
    verdict_rows = "".join(
        f"<tr><td>{r['dim']}</td><td>{r['case']}</td><td class='mono'>{html.escape(r['a'])}</td>"
        f"<td class='mono'>{html.escape(r['b'])}</td>"
        f"<td class='win win-{r['winner']}'>{html.escape(A.name if r['winner'] == 'A' else (B.name if r['winner'] == 'B' else 'tie'))}</td>"
        f"<td class='mono dim'>{r['ratio']}</td><td class='mono dim'>{r['cross']}</td></tr>"
        for r in rows
    )

    growth_rows = ""
    maxlog = max(
        [math.log10(max(x, y)) for _, x, y in head.samples if _finite(x) and _finite(y) and max(x, y) > 0]
        or [1]
    ) or 1
    for n, x, y in head.samples:
        ratio = x / y if y else math.inf
        rt = "∞" if math.isinf(ratio) else ("0" if ratio == 0 else _fmt(ratio, 3))
        cheaper = "A" if ratio and ratio < 1 else ("B" if ratio > 1 else "=")
        wa = 0 if not _finite(x) or x <= 0 else max(1, math.log10(x) / maxlog * 100)
        wb = 0 if not _finite(y) or y <= 0 else max(1, math.log10(y) / maxlog * 100)
        growth_rows += (
            f"<tr><td class='mono dim'>{_fmt(n)}</td>"
            f"<td><div class='barwrap'><div class='bar a' style='width:{wa:.1f}%'></div>"
            f"<span class='mono'>{_sci(x)}</span></div></td>"
            f"<td><div class='barwrap'><div class='bar b' style='width:{wb:.1f}%'></div>"
            f"<span class='mono'>{_sci(y)}</span></div></td>"
            f"<td class='mono'>{rt}</td><td class='win'>{cheaper}</td></tr>"
        )

    svg = _svg_chart(head)
    warn = "".join(f"<li>{html.escape(w)}</li>" for w in v.warnings)
    reasoning = "".join(f"<li>{html.escape(c.explain(A.name, B.name))}</li>" for c in v.cases)
    notes_html = ""
    if notes and (A.notes or B.notes):
        notes_html = "<h2>Caveats &amp; constant factors</h2><ul>" + "".join(
            f"<li><b>{html.escape(algo.name)}:</b> {html.escape(algo.notes)}</li>"
            for algo in (A, B) if algo.notes) + "</ul>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(A.name)} vs {html.escape(B.name)} — complexity comparison</title>
<style>
:root {{ --a:#2f6fed; --b:#c026d3; --bg:#0f1117; --fg:#e6e8ef; --muted:#8b90a3;
        --card:#171a23; --line:#262b39; --green:#2ecc71; --yellow:#f1c40f; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:32px 20px 64px; background:var(--bg); color:var(--fg);
       font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
.wrap {{ max-width:1000px; margin:0 auto; }}
h1 {{ font-size:26px; margin:0 0 4px; letter-spacing:-.02em; }}
h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.09em; color:var(--muted);
     margin:36px 0 12px; border-bottom:1px solid var(--line); padding-bottom:8px; }}
.sub {{ color:var(--muted); margin:0 0 24px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
        padding:18px 20px; margin-bottom:16px; }}
.conclusion {{ font-size:17px; line-height:1.65; }}
.badge {{ display:inline-block; padding:3px 11px; border-radius:999px; font-size:12.5px;
         font-weight:600; background:#1f2534; border:1px solid var(--line); margin-top:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:middle; }}
th {{ color:var(--muted); font-weight:600; font-size:12.5px; text-transform:uppercase; letter-spacing:.06em; }}
.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
.dim {{ color:var(--muted); }}
.a-col {{ color:#9dbcff; }} .b-col {{ color:#f0a6f7; }}
.win {{ font-weight:600; }} .win-A {{ color:#7fd6a2; }} .win-B {{ color:#e79bf0; }} .win-tie {{ color:var(--yellow); }}
ul {{ padding-left:20px; }} li {{ margin:5px 0; }}
.warn {{ border-left:3px solid var(--yellow); background:#20202b; }}
.barwrap {{ position:relative; background:#10131b; border-radius:4px; height:22px; min-width:160px; }}
.bar {{ position:absolute; left:0; top:0; bottom:0; border-radius:4px; opacity:.55; }}
.bar.a {{ background:var(--a); }} .bar.b {{ background:var(--b); }}
.barwrap span {{ position:relative; z-index:1; padding-left:8px; font-size:12.5px; line-height:22px; }}
.legend span {{ display:inline-flex; align-items:center; gap:6px; margin-right:16px; font-size:13px; }}
.sw {{ width:11px; height:11px; border-radius:3px; display:inline-block; }}
footer {{ color:var(--muted); font-size:12.5px; margin-top:32px; border-top:1px solid var(--line); padding-top:14px; }}
</style></head><body><div class="wrap">
<h1>{html.escape(A.name)} <span class="dim">vs</span> {html.escape(B.name)}</h1>
<p class="sub">Task: {html.escape(A.task)} &nbsp;·&nbsp; family: {html.escape(A.category)}
 &nbsp;·&nbsp; theoretical (asymptotic) comparison</p>

{f'<div class="card warn"><b>Warnings</b><ul>{warn}</ul></div>' if warn else ''}

<div class="card">
  <div class="conclusion">{html.escape(v.conclusion())}</div>
  <div class="badge">Overall winner: {html.escape(wname)} — {html.escape(reason)}</div>
</div>

<h2>Complexity profiles</h2>
<div class="card"><table>
<tr><th></th><th class="a-col">{html.escape(A.name)}</th><th class="b-col">{html.escape(B.name)}</th></tr>
{profile_rows}
</table></div>

<h2>Case-by-case verdict</h2>
<div class="card"><table>
<tr><th>dimension</th><th>case</th><th>{html.escape(A.name)}</th><th>{html.escape(B.name)}</th>
<th>winner</th><th>A÷B as n&rarr;&infin;</th><th>crossover n</th></tr>
{verdict_rows}
</table></div>

<h2>Operation-count growth — {head.dimension}/{head.case} case</h2>
<div class="card">
<div class="legend"><span><i class="sw" style="background:var(--a)"></i>{html.escape(A.name)} · {html.escape(str(head.a))}</span>
<span><i class="sw" style="background:var(--b)"></i>{html.escape(B.name)} · {html.escape(str(head.b))}</span></div>
{svg}
<table style="margin-top:14px">
<tr><th>n</th><th>{html.escape(A.name)}</th><th>{html.escape(B.name)}</th><th>A ÷ B</th><th>cheaper</th></tr>
{growth_rows}
</table>
<p class="dim" style="font-size:12.5px;margin-top:10px">Bar lengths are log-scaled.
Values are abstract operation counts from the declared growth functions, not seconds.</p>
</div>

<h2>Reasoning</h2><div class="card"><ul>{reasoning}</ul></div>

{notes_html}

<footer>Generated by <b>algo-compare</b>. Asymptotic notation hides constant factors,
memory-hierarchy effects and allocation cost — confirm with an empirical benchmark before
deciding.</footer>
</div></body></html>"""


def _svg_chart(c: CaseVerdict, *, w: int = 940, h: int = 300) -> str:
    pts = [(n, x, y) for n, x, y in c.samples if _finite(x) and _finite(y) and x > 0 and y > 0]
    if len(pts) < 2:
        return "<p class='dim'>No plottable samples.</p>"
    lx = [math.log10(n) for n, _, _ in pts]
    la = [math.log10(x) for _, x, _ in pts]
    lb = [math.log10(y) for _, _, y in pts]
    x0, x1 = min(lx), max(lx)
    y0 = min(min(la), min(lb))
    y1 = max(max(la), max(lb))
    pad = (y1 - y0) * 0.08 or 1
    y0, y1 = y0 - pad, y1 + pad
    ml, mr, mt, mb = 62, 16, 14, 34
    iw, ih = w - ml - mr, h - mt - mb

    def X(v: float) -> float:
        return ml + (v - x0) / (x1 - x0) * iw

    def Y(v: float) -> float:
        return mt + (1 - (v - y0) / (y1 - y0)) * ih

    def path(vals: Sequence[float]) -> str:
        return " ".join(
            ("M" if i == 0 else "L") + f"{X(lx[i]):.1f},{Y(vals[i]):.1f}" for i in range(len(vals))
        )

    grid = []
    steps = 5
    for i in range(steps + 1):
        yy = mt + ih * i / steps
        val = y1 - (y1 - y0) * i / steps
        grid.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml+iw}" y2="{yy:.1f}" stroke="#262b39"/>')
        grid.append(f'<text x="{ml-8}" y="{yy+4:.1f}" text-anchor="end" fill="#8b90a3" '
                    f'font-size="10" font-family="ui-monospace,monospace">1e{val:.0f}</text>')
    xticks = "".join(
        f'<text x="{X(lx[i]):.1f}" y="{mt+ih+18:.1f}" text-anchor="middle" fill="#8b90a3" '
        f'font-size="10" font-family="ui-monospace,monospace">n={_fmt(pts[i][0])}</text>'
        for i in range(len(pts))
    )
    dots = "".join(
        f'<circle cx="{X(lx[i]):.1f}" cy="{Y(la[i]):.1f}" r="3" fill="#2f6fed"/>'
        f'<circle cx="{X(lx[i]):.1f}" cy="{Y(lb[i]):.1f}" r="3" fill="#c026d3"/>'
        for i in range(len(pts))
    )
    return f"""<svg viewBox="0 0 {w} {h}" width="100%" style="margin-top:10px" role="img"
 aria-label="log-log growth chart">
{''.join(grid)}
<path d="{path(la)}" fill="none" stroke="#2f6fed" stroke-width="2.4"/>
<path d="{path(lb)}" fill="none" stroke="#c026d3" stroke-width="2.4" stroke-dasharray="6 4"/>
{dots}{xticks}
<line x1="{ml}" y1="{mt+ih}" x2="{ml+iw}" y2="{mt+ih}" stroke="#3a4054"/>
<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ih}" stroke="#3a4054"/>
</svg>"""


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #


def render(v: Verdict, fmt: str, **kw) -> str:
    fmt = (fmt or "terminal").lower()
    if fmt in ("terminal", "console", "text", "rich"):
        return render_terminal(v, **kw)
    if fmt in ("md", "markdown"):
        return render_markdown(v, **kw)
    if fmt == "json":
        return render_json(v)
    if fmt == "html":
        return render_html(v)
    raise ValueError(f"unknown format {fmt!r} (terminal|markdown|json|html)")


__all__ = ["render", "render_terminal", "render_markdown", "render_json", "render_html",
           "ascii_chart"]
