"""`algo-compare` — command line interface."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict

from . import __version__
from .algorithm import Algorithm
from .comparator import DEFAULT_SIZES, compare
from .expr import ExprError
from .matrix import rank_algorithms, render_matrix
from .registry import (Registry, default_registry, load_definitions_into,
                       register_custom, task_family)
from .reports import render

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:  # pragma: no cover
    HAS_RICH = False

    class Console:  # type: ignore[no-redef]
        def __init__(self, *a, **k):
            pass

        def print(self, *a, **k):
            print(*[str(x) for x in a])

        def rule(self, *a, **k):
            pass


CASES = ("best", "average", "worst")


# --------------------------------------------------------------------------- #
# Argument parsing helpers
# --------------------------------------------------------------------------- #


def parse_sizes(text: str) -> tuple[float, ...]:
    """`10:1e9:8`  -> 8 log-spaced sizes;  `10,100,1e6` -> literal list."""
    text = text.strip()
    if not text or text == "default":
        return DEFAULT_SIZES
    if ":" in text:
        lo_s, hi_s, count_s = (text.split(":") + ["8"])[:3]
        lo, hi, count = float(lo_s), float(hi_s), int(count_s)
        if count < 2:
            raise ValueError("need at least 2 sizes")
        step = (math.log10(hi) - math.log10(lo)) / (count - 1)
        return tuple(round(10 ** (math.log10(lo) + i * step)) for i in range(count))
    out = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    if len(out) < 2:
        raise ValueError("need at least 2 sizes")
    return tuple(sorted(out))


def parse_add(specs: list[str], registry: Registry) -> list[Algorithm]:
    """Parse `--add Name:time_avg:time_worst[:space_worst]` specifications."""
    added = []
    for spec in specs or []:
        parts = [p.strip() for p in spec.split(":")]
        if len(parts) < 3:
            raise ValueError(
                f"--add expects Name:time_average:time_worst[:space_worst], got {spec!r}"
            )
        name = parts[0]
        time_avg = parts[1] or None
        time_worst = parts[2] or time_avg
        space_worst = parts[3] if len(parts) > 3 and parts[3] else "1"
        rest = parts[4:]
        category = rest[0] if rest else "custom"
        task = rest[1] if len(rest) > 1 else "custom"
        added.append(register_custom(
            name,
            time_worst=time_worst,
            time_average=time_avg,
            space_worst=space_worst,
            category=category,
            task=task,
            registry=registry,
        ))
    return added


def build_registry(args) -> Registry:
    reg = default_registry()
    for path in getattr(args, "definitions", None) or []:
        if not os.path.exists(path):
            raise SystemExit(f"definitions file not found: {path}")
        load_definitions_into(path, reg)
    parse_add(getattr(args, "add", None) or [], reg)
    return reg


def emit(text: str, args) -> None:
    out = getattr(args, "out", None)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"written: {out}")
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def cmd_analyze(args) -> int:
    from .static_analysis import analyze_file

    if not os.path.exists(args.file):
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    est = analyze_file(args.file)
    if args.json:
        print(json.dumps(est.to_dict(), indent=2))
    else:
        print(f"Static estimate: {args.file}")
        print(f"  function : {est.details.get('function')}")
        print(f"  time best/avg/worst : {_lbl(est.time_best)} / "
              f"{_lbl(est.time_average)} / {_lbl(est.time_worst)}")
        print(f"  space: {_lbl(est.space)}   confidence: {est.confidence:.2f}")
        print("  notes:")
        for note in est.notes:
            print(f"    - {note}")
    if args.out:
        # `--json -o file` prints *and* saves, like the other subcommands
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(est.to_dict(), fh, indent=2)
        print(f"written: {args.out}")
    return 0


def _lbl(expr: str) -> str:
    from .static_analysis import expr_label

    return expr_label(expr)


def cmd_benchmark(args) -> int:
    from .benchmark import run_benchmark

    sizes = [int(s) for s in parse_sizes(args.sizes)]
    res = run_benchmark(args.file, sizes, function=args.function,
                        repeats=args.repeats, timeout=args.timeout,
                        input_kind=args.input, input_factory=args.input_factory,
                        max_time=args.max_time)
    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"Benchmark: {args.file} :: {res.function}")
        print(f"  {'n':>12} | {'seconds':>12} | {'peak bytes':>12}")
        for p in res.points:
            print(f"  {p.n:>12,} | {p.seconds:>12.6g} | {p.peak_bytes:>12,}")
        for w in res.warnings:
            print(f"  warning: {w}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(res.to_dict(), fh, indent=2)
        print(f"written: {args.out}")
    return 0 if res.points else 1


def cmd_infer(args) -> int:
    from .benchmark import run_benchmark
    from .curve_fit import fit_points
    from .static_analysis import analyze_file

    sizes = [int(s) for s in parse_sizes(args.sizes)]
    res = run_benchmark(args.file, sizes, function=args.function,
                        repeats=args.repeats, timeout=args.timeout,
                        input_kind=args.input, input_factory=args.input_factory,
                        max_time=args.max_time)
    pts = [(p.n, p.seconds) for p in res.points]
    fit = fit_points(pts)
    try:
        static_est = analyze_file(args.file)
        static = static_est.to_dict()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = {"file": args.file, "function": res.function,
               "static": static, "benchmark": res.to_dict(),
               "fit": fit.to_dict()}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Infer: {args.file} :: {res.function}")
        print(f"  static worst: {_lbl(static_est.time_worst)}"
              f" (confidence {static_est.confidence:.2f})")
        print(f"  empirical best fit: {fit.best_fit} (R^2={fit.fit_score:.3f})")
        if fit.measured_exponent is not None:
            print(f"  measured exponent : {fit.measured_exponent:.3f}"
                  "  (log-log slope: ~1 linear, ~1.5 n*sqrt(n), ~2 quadratic)")
        print("  ranking:")
        for m in fit.ranking:
            print(f"    {m.label:<10} R^2={m.r_squared:.3f}")
        for w in list(res.warnings) + list(fit.warnings):
            print(f"  warning: {w}")
        print("  NOTE: static result is a heuristic; empirical fit depends on")
        print("  sizes/repeats/machine. Confirm before quoting Big-O.")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"written: {args.out}")
    return 0 if res.points else 1


def cmd_compare(args) -> int:
    reg = build_registry(args)
    try:
        a = reg.get(args.a)
        b = reg.get(args.b)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sizes = parse_sizes(args.sizes)
    cases = CASES if args.case == "all" else (args.case,)
    verdict = compare(a, b, sizes=sizes, compare_space=not args.no_space, cases=cases)

    kw = {}
    if args.format in ("terminal", "markdown"):
        kw = {"growth_table": not args.no_table, "chart": not args.no_chart,
              "notes": not args.no_notes}
    if args.format == "terminal" and args.out:
        # a file should never contain ANSI escape sequences
        kw["color"] = False
    text = render(verdict, args.format, **kw)
    emit(text, args)
    return 0


def cmd_list(args) -> int:
    reg = build_registry(args)
    algos = reg.filter(category=args.category, task=args.task, query=args.search)
    if not algos:
        print("no algorithms matched those filters")
        return 1
    if args.json:
        print(json.dumps([
            {"key": a.key, "name": a.name, "category": a.category, "task": a.task,
             "time": {k: str(c) for k, c in a.time.items()},
             "space": {k: str(c) for k, c in a.space.items()} if a.space else None}
            for a in algos], indent=2, ensure_ascii=False))
        return 0

    if HAS_RICH:
        con = Console(width=args.width)
        t = Table(box=box.SIMPLE, title=f"{len(algos)} algorithms", title_style="bold cyan",
                  header_style="bold", expand=False)
        t.add_column("key", style="dim", no_wrap=True)
        t.add_column("name", style="bold")
        t.add_column("category")
        t.add_column("time avg", justify="center")
        t.add_column("time worst", justify="center")
        t.add_column("space", justify="center")
        for a in algos:
            sp = a.space.worst.short if a.space else "—"
            t.add_row(a.key, a.name, a.category,
                      (a.time.average or a.time.worst).short, a.time.worst.short, sp)
        con.print(t)
    else:
        print(f"{'key':<38}{'name':<44}{'avg':<16}{'worst':<16}{'space'}")
        for a in algos:
            sp = a.space.worst.short if a.space else "-"
            print(f"{a.key:<38}{a.name:<44}{(a.time.average or a.time.worst).short:<16}"
                  f"{a.time.worst.short:<16}{sp}")
    print(f"\n{len(algos)} of {len(reg)} algorithms. "
          f"Try: algo-compare compare <key1> <key2>")
    return 0


def cmd_show(args) -> int:
    reg = build_registry(args)
    try:
        a = reg.get(args.algo)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    lines = [
        f"{a.name}",
        f"  key        : {a.key}",
        f"  category   : {a.category}",
        f"  task       : {a.task}",
        "",
        "  TIME",
    ]
    for name, c in a.time.items():
        lines.append(f"    {name:<10} {c.resolved_label:<18} "
                     f"(growth class: {c.growth_class()}, exponent ≈ "
                     f"{'inf' if math.isinf(c.growth_exponent) else f'{c.growth_exponent:.3f}'})")
    lines.append("")
    lines.append("  SPACE")
    if a.space:
        for name, c in a.space.items():
            lines.append(f"    {name:<10} {c.resolved_label}")
    else:
        lines.append("    (not declared)")
    flags = []
    if a.stable is not None:
        flags.append("stable" if a.stable else "unstable")
    if a.in_place is not None:
        flags.append("in-place" if a.in_place else "extra memory")
    if a.time.is_case_sensitive:
        flags.append("input-order sensitive")
    if flags:
        lines += ["", "  PROPERTIES: " + ", ".join(flags)]
    if a.notes:
        lines += ["", "  NOTES", f"    {a.notes}"]
    peers = reg.comparable_with(a)
    if peers:
        lines += ["", f"  SAME TASK ({len(peers)} comparable algorithms):"]
        for p in rank_algorithms(peers, case="average"):
            lines.append(f"    - {p[0].key}  ({p[0].name}, avg {p[1]})")
        lines += ["", f"  Compare them: algo-compare compare {a.key} {peers[0].key}"]
    print("\n".join(lines))
    return 0


def cmd_matrix(args) -> int:
    reg = build_registry(args)
    if args.category:
        algos = reg.filter(category=args.category)
    elif args.task:
        algos = [a for a in reg.all() if args.task.lower() in a.task.lower()]
    else:
        try:
            algos = [reg.get(q) for q in args.algos]
        except LookupError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if not algos:
        print("no algorithms matched", file=sys.stderr)
        return 1
    cases = tuple(CASES) if args.case == "all" else (args.case,)
    text = render_matrix(algos, dimension=args.dimension, cases=cases,
                         include_space=args.space, width=args.width)
    emit(text, args)
    return 0


def cmd_suggest(args) -> int:
    reg = build_registry(args)
    groups: dict[str, list[Algorithm]] = defaultdict(list)
    for a in reg.all():
        groups[task_family(a.task)].append(a)
    def label(group: list[Algorithm], fam: str) -> str:
        # if every member spells the task identically, keep that exact wording
        # (it preserves punctuation); otherwise fall back to the family name
        first = group[0].task
        return first if all(a.task == first for a in group) else fam.replace("_", " ")

    pairs = [(label(g, fam), g) for fam, g in groups.items() if len(g) >= 2]
    pairs.sort(key=lambda tg: -len(tg[1]))
    if args.limit:
        pairs = pairs[: args.limit]
    if args.json:
        print(json.dumps([
            {"task": t, "algorithms": [a.key for a in g]} for t, g in pairs
        ], indent=2, ensure_ascii=False))
        return 0
    print(f"{len(pairs)} tasks have ≥2 algorithms in the catalogue — "
          f"these are the fair comparison pairs:\n")
    for task, group in pairs:
        ranked = rank_algorithms(group, case="average")
        names = ", ".join(f"{a.name} ({c.short})" for a, c in ranked)
        print(f"• {task}\n    {names}\n    e.g.  algo-compare compare "
              f"{ranked[0][0].key} {ranked[-1][0].key}")
    return 0


def cmd_categories(args) -> int:
    reg = build_registry(args)
    counts: dict[str, int] = defaultdict(int)
    for a in reg.all():
        counts[a.category] += 1
    for cat, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        slug = _cat_slug(cat)
        print(f"{cat:<34}{n:>4} algorithms   (algo-compare list --category {slug})")
    print(f"\ntotal: {len(reg)} algorithms")
    return 0


def cmd_benchmarks(args) -> int:
    from .verify import available_benchmarks

    print("Empirically verifiable algorithms (`algo-compare verify <key>`):\n")
    for key, name in available_benchmarks():
        print(f"  {key:<46}{name}")
    return 0


def cmd_verify(args) -> int:
    from .verify import verify as run_verify

    reg = build_registry(args)
    try:
        a = reg.get(args.algo)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sizes = [int(s) for s in parse_sizes(args.sizes)]
    print(f"Measuring {a.name}  ·  declared worst case {a.time.worst}")
    print(f"workload: (see catalogue)   sizes: {sizes}\n")
    report = run_verify(a, sizes=sizes, registry=reg, budget=args.budget,
                        progress=lambda m: print(m))
    if report is None:
        print(f"\nNo built-in benchmark implementation for {a.key!r}. "
              f"Run `algo-compare benchmarks` to see which are measurable.")
        return 1
    print()
    print(f"  declared worst-case : {report.declared.resolved_label} "
          f"(growth exponent ≈ {_num(report.declared.growth_exponent)})")
    print(f"  measured exponent   : {_num(report.fit.exponent)} "
          f"(log-log least squares, R² = {report.fit.r_squared:.3f})")
    print(f"  verdict             : {report.verdict}")
    print()
    print(f"  {'n':>12} | {'seconds':>12} | {'ratio to prev':>14}")
    print(f"  {'-'*12}-+-{'-'*12}-+-{'-'*14}")
    prev = None
    for m in report.fit.measurements:
        ratio = f"{m.seconds/prev:.2f}x" if prev else "—"
        print(f"  {m.n:>12,} | {m.seconds:>12.6g} | {ratio:>14}")
        prev = m.seconds
    print("\n  Interpretation: for T(n) ~ n^beta, doubling n multiplies time by 2^beta.")
    print("  beta ≈ 1 linear, ≈ 2 quadratic, ≈ 1.0x linearithmic, ≈ 0 logarithmic.")
    return 0


def _cat_slug(cat: str) -> str:
    from .registry import _slug

    return _slug(cat)


def _num(x: float) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{x:.3f}"


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="algo-compare",
        description="Theoretical comparison framework for algorithms that solve the same task.",
        epilog="examples:\n"
               "  algo-compare compare merge_sort quick_sort\n"
               "  algo-compare compare dijkstra_binary_heap bellman_ford --format markdown -o report.md\n"
               "  algo-compare list --category sorting\n"
               "  algo-compare suggest --limit 8\n"
               "  algo-compare matrix --category graph --space\n"
               "  algo-compare compare a b --add 'My Sort:n*log2(n):n**2:log2(n)':custom\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"algo-compare {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--definitions", "-D", action="append", metavar="FILE",
                        help="load extra algorithms from an INI-style definition file (repeatable)")
    p.add_argument("--definitions", "-D", action="append", metavar="FILE",
                   help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="command", required=True)

    # ---- compare
    c = sub.add_parser("compare", help="compare two algorithms (default: terminal report)", parents=[common])
    c.add_argument("a", help="first algorithm (key or name)")
    c.add_argument("b", help="second algorithm (key or name)")
    c.add_argument("--format", "-f", default="terminal",
                   choices=["terminal", "markdown", "json", "html"], help="report format")
    c.add_argument("--case", default="all", choices=[*CASES, "all"],
                   help="which case to compare (default: all three)")
    c.add_argument("--sizes", default="10:1e9:8",
                   help="input sizes: 'lo:hi:count' or 'n1,n2,n3' (default 10:1e9:8)")
    c.add_argument("--no-space", action="store_true", help="skip the memory comparison")
    c.add_argument("--no-table", action="store_true", help="skip the growth table")
    c.add_argument("--no-chart", action="store_true", help="skip the ASCII growth chart")
    c.add_argument("--no-notes", action="store_true", help="skip the caveats section")
    c.add_argument("--add", action="append", metavar="SPEC",
                   help="define a custom algorithm inline: Name:time_avg:time_worst[:space[:category[:task]]]")
    c.add_argument("--out", "-o", metavar="FILE", help="write the report to a file")
    c.add_argument("--width", type=int, default=112, help="terminal width (default 112)")
    c.set_defaults(func=cmd_compare)

    # ---- list
    l = sub.add_parser("list", help="list algorithms in the catalogue", parents=[common])
    l.add_argument("--category", help="filter by category")
    l.add_argument("--task", help="filter by task substring")
    l.add_argument("--search", help="free-text filter over name/key/task/category")
    l.add_argument("--json", action="store_true", help="machine-readable output")
    l.add_argument("--width", type=int, default=150)
    l.set_defaults(func=cmd_list)

    # ---- show
    s = sub.add_parser("show", help="full theoretical profile of one algorithm", parents=[common])
    s.add_argument("algo")
    s.set_defaults(func=cmd_show)

    # ---- matrix
    m = sub.add_parser("matrix", help="compare many algorithms at once", parents=[common])
    m.add_argument("algos", nargs="*", help="algorithm keys (or use --category/--task)")
    m.add_argument("--category", help="all algorithms in a category")
    m.add_argument("--task", help="all algorithms whose task contains this text")
    m.add_argument("--dimension", default="time", choices=["time", "space"])
    m.add_argument("--case", default="average", choices=[*CASES, "all"])
    m.add_argument("--space", action="store_true", help="also show space columns")
    m.add_argument("--out", "-o", metavar="FILE")
    m.add_argument("--width", type=int, default=150)
    m.set_defaults(func=cmd_matrix)

    # ---- suggest
    sg = sub.add_parser("suggest", help="list task groups that have ≥2 comparable algorithms", parents=[common])
    sg.add_argument("--limit", type=int, default=0)
    sg.add_argument("--json", action="store_true")
    sg.set_defaults(func=cmd_suggest)

    # ---- categories
    ct = sub.add_parser("categories", help="list categories with counts", parents=[common])
    ct.set_defaults(func=cmd_categories)

    # ---- verify (optional empirical cross-check)
    v = sub.add_parser("verify", help="measure real runtime growth and check it against the declared bound", parents=[common])
    v.add_argument("algo")
    v.add_argument("--sizes", default="64:16384:6", help="input sizes (default 64:16384:6)")
    v.add_argument("--budget", type=float, default=0.4,
                   help="max seconds per input size before stopping (default 0.4)")
    v.set_defaults(func=cmd_verify)

    b = sub.add_parser("benchmarks", help="list algorithms that can be empirically verified", parents=[common])
    b.set_defaults(func=cmd_benchmarks)

    a = sub.add_parser("analyze", help="estimate Big-O from Python source (heuristic)")
    a.add_argument("file", help="Python file to analyze")
    a.add_argument("--json", action="store_true", help="machine-readable output")
    a.add_argument("--out", "-o", metavar="FILE", help="write JSON estimate to file")
    a.set_defaults(func=cmd_analyze)

    bm = sub.add_parser("benchmark", help="time an arbitrary Python file in a subprocess")
    bm.add_argument("file", help="Python file defining function (default: main)")
    bm.add_argument("--function", default="main", help="entry function (default: main)")
    bm.add_argument("--sizes", default="100,1000,10000", help="input sizes")
    bm.add_argument("--repeats", type=int, default=5, help="repeats per size")
    bm.add_argument("--timeout", type=float, default=20.0, help="per-size timeout s")
    bm.add_argument("--input", default="list", choices=["list", "sorted", "string"],
                    help="default input builder")
    bm.add_argument("--input-factory", default="", help="fn(n) in file for custom input")
    bm.add_argument("--max-time", type=float, default=5.0, help="stop after slower size")
    bm.add_argument("--json", action="store_true")
    bm.add_argument("--out", "-o", metavar="FILE")
    bm.set_defaults(func=cmd_benchmark)

    inf = sub.add_parser("infer", help="static estimate + benchmark + curve fit")
    inf.add_argument("file", help="Python file defining function (default: main)")
    inf.add_argument("--function", default="main", help="entry function (default: main)")
    inf.add_argument("--sizes", default="100,1000,10000", help="input sizes")
    inf.add_argument("--repeats", type=int, default=5)
    inf.add_argument("--timeout", type=float, default=20.0)
    inf.add_argument("--input", default="list", choices=["list", "sorted", "string"])
    inf.add_argument("--input-factory", default="")
    inf.add_argument("--max-time", type=float, default=5.0)
    inf.add_argument("--json", action="store_true")
    inf.add_argument("--out", "-o", metavar="FILE")
    inf.set_defaults(func=cmd_infer)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ExprError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:  # pragma: no cover - piping into `head`
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
