"""Static complexity analyzer: estimate Big-O from Python source via `ast`.

Inspects loops, nesting, recursion shape and recognizable library calls,
producing an *estimate* (never a proof) using the same expression
language as :mod:`algocomp.complexity`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

#: Canonical expressions the analyzer may emit, slowest-first.
TIME_EXPRS = ("1", "log2(n)", "n", "n*log2(n)", "n**2", "n**3", "2**n")

_EXPR_TO_LABEL = {
    "1": "O(1)",
    "log2(n)": "O(log n)",
    "n": "O(n)",
    "n*log2(n)": "O(n log n)",
    "n**2": "O(n^2)",
    "n**3": "O(n^3)",
    "2**n": "O(2^n)",
}

_EXPR_TO_RANK = {e: i for i, e in enumerate(TIME_EXPRS)}


@dataclass
class StaticEstimate:
    """Estimated complexity for one file (or its dominant function)."""

    time_best: str = "1"
    time_average: str = "n"
    time_worst: str = "n"
    space: str = "1"
    confidence: float = 0.5
    notes: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        def lbl(e: str) -> str:
            return _EXPR_TO_LABEL.get(e, f"O({e})")

        return {
            "time_best": lbl(self.time_best),
            "time_average": lbl(self.time_average),
            "time_worst": lbl(self.time_worst),
            "space": lbl(self.space),
            "expressions": {
                "time_best": self.time_best,
                "time_average": self.time_average,
                "time_worst": self.time_worst,
                "space": self.space,
            },
            "confidence": round(float(self.confidence), 3),
            "notes": list(self.notes),
            "details": dict(self.details),
        }


def _label(expr: str) -> str:
    return _EXPR_TO_LABEL.get(expr, f"O({expr})")


_LINEAR_CALLS = frozenset({
    "sum", "min", "max", "any", "all", "len", "list", "tuple", "set",
    "sorted", "reversed", "enumerate", "map", "filter", "join",
})
_SORT_CALLS = frozenset({"sort", "sorted"})
_HEAP_CALLS = frozenset({"heappush", "heappop", "heapify", "heappushpop", "heapreplace"})
_BISECT_CALLS = frozenset({"bisect", "bisect_left", "bisect_right", "insort"})
@dataclass
class _FuncInfo:
    name: str
    max_loop_depth: int = 0
    loop_count: int = 0
    while_count: int = 0
    recursive: bool = False
    self_calls: int = 0
    halves_input: bool = False
    has_merge_loop: bool = False
    calls_sort: bool = False
    calls_heap: bool = False
    calls_bisect: bool = False
    calls_linear: bool = False
    allocates_list: bool = False
    uncertain: list[str] = field(default_factory=list)


class _Visitor(ast.NodeVisitor):
    def __init__(self, func_name: str) -> None:
        self.func_name = func_name
        self.info = _FuncInfo(name=func_name)
        self._depth = 0

    def visit_For(self, node: ast.For) -> None:
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self.info.while_count += 1
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        if _looks_like_halving_loop(node):
            self.info.uncertain.append(
                "while loop shrinks bound (e.g. //= 2); treated as logarithmic"
            )
            self.info.calls_bisect = True
        self.generic_visit(node)
        self._depth -= 1

    def _visit_comp(self, node: ast.AST) -> None:
        self.info.loop_count += 1
        self.info.calls_linear = True
        self.info.allocates_list = True
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        self.generic_visit(node)
        self._depth -= 1

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comp(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comp(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comp(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comp(node)

    def visit_Call(self, node: ast.Call) -> None:
        fname = _call_name(node)
        base = fname.split(".")[-1] if fname else ""
        if fname == self.func_name or fname.endswith("." + self.func_name):
            self.info.recursive = True
            self.info.self_calls += 1
            self._inspect_recursive_call(node)
        elif base in _SORT_CALLS:
            self.info.calls_sort = True
        elif base in _HEAP_CALLS:
            self.info.calls_heap = True
        elif base in _BISECT_CALLS:
            self.info.calls_bisect = True
        elif base in _LINEAR_CALLS or fname in _LINEAR_CALLS:
            self.info.calls_linear = True
        elif base in ("copy", "append", "extend") or fname in ("list", "dict", "set"):
            self.info.allocates_list = True
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.slice, ast.Slice):
            self.info.allocates_list = True
        self.generic_visit(node)

    def _inspect_recursive_call(self, node: ast.Call) -> None:
        for arg in node.args:
            rep = ast.unparse(arg) if hasattr(ast, "unparse") else ast.dump(arg)
            low = rep.lower()
            if "//" in rep or ">>" in rep or "/ 2" in rep or "/2" in rep:
                self.info.halves_input = True
            if any(t in low for t in ("mid", "half", "left", "right")):
                if "left" in low or "right" in low:
                    # variable named left/right alone is weak evidence (merge
                    # step uses them, but so does unrelated code) -> keep count
                    # but do not claim divide-and-conquer from it.
                    self.info.uncertain.append(
                        "recursive call passes '%s'; weak divide-and-conquer hint" % rep[:40]
                    )
                else:
                    self.info.halves_input = True
                    self.info.uncertain.append(
                        "recursive call uses midpoint-like arg; assumed divide-and-conquer"
                    )


def _call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        if isinstance(f.value, ast.Name):
            return f.value.id + "." + f.attr
        return f.attr
    return ""


def _looks_like_halving_loop(node: ast.While) -> bool:
    src = ast.dump(node)
    has_shrink = any(op in src for op in ("FloorDiv", "RShift", "Div"))
    has_names = any(nm in src for nm in ("mid", "half", "lo", "hi", "low", "high"))
    return has_shrink and has_names


def _time_for_func(info):
    notes = []
    if info.recursive:
        return _time_for_recursion(info)
    if info.calls_sort:
        notes.append("detected sort/sorted call: O(n log n) dominates loops")
        return "n*log2(n)", 0.75, notes
    if info.calls_bisect and info.max_loop_depth <= 1 and info.while_count >= 1:
        notes.append("halving while-loop (binary-search style) -> O(log n)")
        return "log2(n)", 0.7, notes
    if info.calls_bisect and info.max_loop_depth == 0 and info.loop_count == 0:
        notes.append("bisect helper with no loops: O(log n)")
        return "log2(n)", 0.75, notes
    if info.calls_heap and info.max_loop_depth >= 1:
        notes.append("heap op inside loop: O(n)*O(log n) -> O(n log n)")
        return "n*log2(n)", 0.65, notes
    depth = info.max_loop_depth
    if depth == 0:
        if info.calls_linear:
            notes.append("no loops; linear scan helper -> O(n)")
            return "n", 0.7, notes
        notes.append("no loops or recursion -> O(1)")
        return "1", 0.8, notes
    if depth == 1:
        notes.append("single loop level -> O(n)")
        conf = 0.85 if info.while_count == 0 else 0.6
        if info.while_count:
            notes.append("while-loop bound unproven; assumed linear")
        return "n", conf, notes
    if depth == 2:
        notes.append("doubly nested loops -> O(n^2)")
        return "n**2", 0.8, notes
    if depth == 3:
        notes.append("triply nested loops -> O(n^3)")
        return "n**3", 0.75, notes
    notes.append("nesting depth exceeds cubic model; O(2^n) upper bound")
    return "2**n", 0.3, notes


def _time_for_recursion(info):
    notes = [u for u in info.uncertain if not u.startswith("recursive call passes")]
    weak = [u for u in info.uncertain if u.startswith("recursive call passes")]
    if info.halves_input or any("midpoint" in u for u in notes):
        if info.self_calls >= 2 or info.has_merge_loop:
            notes.append("halving recursion + branches/merge loop -> O(n log n)")
            return "n*log2(n)", 0.6, notes
        notes.append("single call on halved input -> O(log n)")
        return "log2(n)", 0.6, notes
    if info.self_calls >= 2:
        notes = notes + weak
        notes.append("2+ self-calls without halving -> O(2^n); memoisation may help")
        return "2**n", 0.4, notes
    notes.append("single self-recursion, no halving -> O(n) depth assumed")
    return "n", 0.4, notes


def _best_case(worst, info):
    if worst == "1":
        return "1", 0.8
    if info.max_loop_depth == 1 and not info.recursive:
        return "1", 0.4
    if worst in ("n**2", "n**3"):
        return "n", 0.3
    if worst == "n*log2(n)":
        return "n", 0.35
    if worst == "log2(n)":
        return "1", 0.4
    return worst, 0.3


def _space_for_func(info):
    if info.recursive:
        space = "log2(n)" if info.halves_input else "n"
        extra = ["plus list/slice copies; lower bound"] if info.allocates_list else []
        return space, ["recursion depth implies " + _label(space) + " stack"] + extra
    if info.allocates_list:
        return "n", ["list/slice allocation -> O(n)"]
    return "1", ["no allocation or recursion -> O(1)"]


def _analyze_block(node, name):
    visitor = _Visitor(name)
    visitor.visit(node)
    if visitor.info.recursive and visitor.info.loop_count > 0:
        visitor.info.has_merge_loop = True
    return visitor.info


def _build_estimate(info, name, extra_names):
    worst, conf, notes = _time_for_func(info)
    best, best_conf = _best_case(worst, info)
    space, space_notes = _space_for_func(info)
    ranks = _EXPR_TO_RANK
    avg_rank = (ranks[best] + ranks[worst]) // 2
    avg_rank = min(ranks[worst], max(ranks[best], avg_rank))
    if ranks[worst] - ranks[best] >= 2:
        avg_rank = ranks[worst]
    average = TIME_EXPRS[avg_rank]
    confidence = max(0.1, min(0.95, conf * 0.7 + best_conf * 0.3))
    header = ("static estimate for %r: worst %s (confidence %.2f); "
              "heuristic only, not a proof" % (name, _label(worst), confidence))
    details = {
        "function": name,
        "functions": extra_names or [name],
        "max_loop_depth": info.max_loop_depth,
        "loops": info.loop_count,
        "while_loops": info.while_count,
        "recursive": info.recursive,
        "self_calls": info.self_calls,
        "halves_input": info.halves_input,
        "calls": {
            "sort": info.calls_sort,
            "heap": info.calls_heap,
            "bisect": info.calls_bisect,
            "linear_scan": info.calls_linear,
        },
    }
    return StaticEstimate(
        time_best=best, time_average=average, time_worst=worst,
        space=space, confidence=round(confidence, 3),
        notes=[header] + notes + space_notes + info.uncertain,
        details=details,
    )


def analyze_source(source, *, filename="<string>"):
    """Analyze source text; never raises on syntax errors."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return StaticEstimate(
            time_best="n", time_average="n", time_worst="n", space="1",
            confidence=0.1,
            notes=["syntax error, could not parse: %s; defaulted to O(n)" % exc],
            details={"error": str(exc), "functions": []},
        )
    funcs = [n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not funcs:
        return _build_estimate(_analyze_block(tree, "<module>"), "<module>", [])
    infos = [(fn.name, _analyze_block(fn, fn.name)) for fn in funcs]
    dom_name, dom = max(infos, key=lambda kv: _EXPR_TO_RANK[_time_for_func(kv[1])[0]])
    est = _build_estimate(dom, dom_name, [n for n, _ in infos])
    if len(infos) > 1:
        est.notes.append("file defines %d functions; dominant: %s" % (len(infos), dom_name))
        est.details["all_functions"] = {n: _time_for_func(i)[0] for n, i in infos}
    return est


def analyze_file(path):
    """Read *path* and analyze it."""
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    est = analyze_source(source, filename=path)
    est.details["path"] = path
    return est


def estimate_to_algorithm_kwargs(est):
    """Convert an estimate to Algorithm.build kwargs."""
    return {
        "time_worst": est.time_worst,
        "time_average": est.time_average,
        "time_best": est.time_best,
        "space_worst": est.space,
        "notes": "STATIC ESTIMATE (unverified): " + "; ".join(est.notes[:3]),
    }


__all__ = [
    "StaticEstimate", "analyze_source", "analyze_file",
    "estimate_to_algorithm_kwargs", "TIME_EXPRS",
]
