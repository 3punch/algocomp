"""Static complexity analyzer: estimate Big-O from Python source via `ast`.

Inspects loops, nesting, recursion shape and recognizable library calls,
producing an *estimate* (never a proof) using the same expression
language as :mod:`algocomp.complexity`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

#: Canonical expressions the analyzer may emit, slowest-first.
TIME_EXPRS = (
    "1", "log2(n)", "n", "n*log2(n)", "n**2", "n**2*log2(n)", "n**3", "2**n",
)

_EXPR_TO_LABEL = {
    "1": "O(1)",
    "log2(n)": "O(log n)",
    "n": "O(n)",
    "n*log2(n)": "O(n log n)",
    "n**2": "O(n^2)",
    "n**2*log2(n)": "O(n^2 log n)",
    "n**3": "O(n^3)",
    "2**n": "O(2^n)",
}

#: When the innermost loop of a nest has a non-constant stride (e.g.
#: ``range(i*i, n+1, i)``) it does not sweep n elements, so the depth-d product
#: collapses: n x n -> n log n, n x n x n -> n^2 log n.
_COLLAPSED_DEPTH = {2: "n*log2(n)", 3: "n**2*log2(n)"}

#: growth classes that a collapsed nest can never exceed
_COLLAPSE_LABELS = {
    2: "O(n log n)",
    3: "O(n^2 log n)",
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


def expr_label(expr: str) -> str:
    """Canonical Big-O label for one of :data:`TIME_EXPRS` (or any expression)."""
    return _label(expr)


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
    #: depths whose innermost loop had a non-constant stride
    variable_stride_depths: list[int] = field(default_factory=list)

    @property
    def variable_stride_at_max_depth(self) -> bool:
        """True when the innermost loop is a strided scan, not a full sweep."""
        return self.max_loop_depth in self.variable_stride_depths


class _Visitor(ast.NodeVisitor):
    def __init__(self, func_name: str) -> None:
        self.func_name = func_name
        self.info = _FuncInfo(name=func_name)
        self._depth = 0
        #: names bound by the loops we are currently inside of
        self._loop_vars: list[set[str]] = []

    def visit_For(self, node: ast.For) -> None:
        self._record_strided_loop(node)
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        self._loop_vars.append(_bound_names(node.target))
        self.generic_visit(node)
        self._loop_vars.pop()
        self._depth -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        self._loop_vars.append(_bound_names(node.target))
        self.generic_visit(node)
        self._loop_vars.pop()
        self._depth -= 1

    def _record_strided_loop(self, node: ast.For) -> None:
        """A loop whose stride is not a literal is not a full n-element sweep.

        ``for j in range(i * i, n + 1, i)`` walks about ``n / i`` elements, so
        summing over the enclosing loop gives a harmonic total (O(n log n))
        instead of a full n x n product. ``for j in range(i)`` still averages
        ~n/2 elements, so it correctly stays quadratic.
        """
        if _variable_stride(node, self._enclosing_names()):
            depth = self._depth + 1
            self.info.variable_stride_depths.append(depth)

    def _enclosing_names(self) -> set[str]:
        names: set[str] = set()
        for bound in self._loop_vars:
            names |= bound
        return names

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
        # a while loop has no target, but the names it mutates are its state and
        # can act as the stride of an inner loop (``while i*i <= n: for j in
        # range(i*i, n+1, i)``)
        self._loop_vars.append(_assigned_names(node))
        self.generic_visit(node)
        self._loop_vars.pop()
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

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Mult):
            left_seq = isinstance(node.left, (ast.Constant, ast.List, ast.Tuple)) and (
                isinstance(getattr(node.left, "value", None), (str, bytes))
                or isinstance(node.left, (ast.List, ast.Tuple))
            )
            right_seq = isinstance(node.right, (ast.Constant, ast.List, ast.Tuple)) and (
                isinstance(getattr(node.right, "value", None), (str, bytes))
                or isinstance(node.right, (ast.List, ast.Tuple))
            )
            if left_seq or right_seq:
                self.info.calls_linear = True
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


def _bound_names(target: ast.AST) -> set[str]:
    """Names truly bound by an assignment/loop target.

    Handles plain names, tuple/list unpacking and starred targets; a subscript
    or attribute target binds nothing, so it yields an empty set.
    """
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for elt in target.elts:
            names |= _bound_names(elt)
        return names
    if isinstance(target, ast.Starred):
        return _bound_names(target.value)
    return set()


def _assigned_names(node: ast.AST) -> set[str]:
    """Names assigned anywhere inside *node* — a loop's mutable state.

    Used to recognise that a ``while`` loop drives a variable (``i += 1``) even
    though a ``while`` has no loop target of its own.
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                names |= _bound_names(target)
        elif isinstance(child, ast.AugAssign):
            names |= _bound_names(child.target)
        elif isinstance(child, ast.AnnAssign):
            names |= _bound_names(child.target)
    return names


def _names_in(node: ast.AST) -> set[str]:
    """Names *read* inside an expression node."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _variable_stride(node: ast.For, enclosing: set[str]) -> bool:
    """True when a loop's stride is a variable of an *enclosing* loop.

    ``for i in ...: for j in range(i * i, n + 1, i)`` walks about ``n / i``
    elements, so summing over the enclosing loop gives a harmonic total
    (O(n log n)) instead of a full n x n product.

    Requiring the stride to come from an enclosing loop keeps the common
    quadratic patterns quadratic: ``range(n)`` has no step, ``range(i)`` sweeps
    ~n/2 elements on average, and a stride read from a local constant
    (``k = 2; range(0, n, k)``) still yields ~n/k elements per pass.
    """
    it = node.iter
    if isinstance(it, ast.Call):
        if _call_name(it) != "range" or len(it.args) != 3:
            return False
        step = it.args[2]
        return not isinstance(step, ast.Constant) and bool(
            _names_in(step) & enclosing
        )
    if isinstance(it, ast.Subscript) and isinstance(it.slice, ast.Slice):
        step = it.slice.step
        if step is None or isinstance(step, ast.Constant):
            return False
        return bool(_names_in(step) & enclosing)
    return False


def _looks_like_halving_loop(node: ast.While) -> bool:  # noqa: D401
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
        if info.variable_stride_at_max_depth:
            notes.append(
                "inner loop has a stride that depends on the enclosing loop "
                "(e.g. `range(i * i, n + 1, i)`), so this is a harmonic sum, "
                "not a full n x n product; estimated as O(n log n) - verify "
                "empirically"
            )
            return _COLLAPSED_DEPTH[2], 0.35, notes
        notes.append("doubly nested loops -> O(n^2)")
        return "n**2", 0.8, notes
    if depth == 3:
        if info.variable_stride_at_max_depth:
            notes.append(
                "innermost of three nested loops has a stride that depends on "
                "an enclosing loop; estimated as O(n^2 log n), not O(n^3)"
            )
            return _COLLAPSED_DEPTH[3], 0.35, notes
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
    if worst in ("n**2", "n**2*log2(n)", "n**3"):
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
        "variable_stride_depths": list(info.variable_stride_depths),
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
    "estimate_to_algorithm_kwargs", "TIME_EXPRS", "expr_label",
]
