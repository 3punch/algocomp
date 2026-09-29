"""Static complexity analyzer: estimate Big-O from Python source via `ast`.

Inspects loops, nesting, recursion shape and recognizable library calls,
producing an *estimate* (never a proof) using the same expression
language as :mod:`algocomp.complexity`.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field

from .complexity import Complexity

#: Canonical expressions the analyzer may emit, slowest-first.
TIME_EXPRS = (
    "1", "log2(n)", "sqrt(n)", "n", "n*log2(n)", "n**2", "n**2*log2(n)",
    "n**3", "n**3*log2(n)", "2**n", "factorial(n)",
)

_EXPR_TO_LABEL = {
    "1": "O(1)",
    "log2(n)": "O(log n)",
    "sqrt(n)": "O(sqrt(n))",
    "n": "O(n)",
    "n*log2(n)": "O(n log n)",
    "n**2": "O(n^2)",
    "n**2*log2(n)": "O(n^2 log n)",
    "n**3": "O(n^3)",
    "n**3*log2(n)": "O(n^3 log n)",
    "2**n": "O(2^n)",
    "factorial(n)": "O(n!)",
}

#: work done inside a geometrically shrinking loop, indexed by the nesting
#: depth of the loops it contains (0 -> O(log n), 1 -> O(n log n), ...)
_HALVING_PRODUCT = ("log2(n)", "n*log2(n)", "n**2*log2(n)", "n**3*log2(n)")

#: When the innermost loop of a nest has a non-constant stride (e.g.
#: ``range(i*i, n+1, i)``) it does not sweep n elements, so the depth-d product
#: collapses: n x n -> n log n, n x n x n -> n^2 log n.
_COLLAPSED_DEPTH = {2: "n*log2(n)", 3: "n**2*log2(n)"}

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
    #: recursive argument is *shrunk* by a factor (``//``, ``%``, ``>>``, ``/2``)
    shrinks_input: bool = False
    #: self-calls that are the whole value of a ``return`` (at most one runs)
    tail_self_calls: int = 0
    #: most self-calls inside a single ``return`` expression
    max_calls_in_one_return: int = 0
    #: a self-call happens inside a loop body
    self_call_in_loop: bool = False
    #: that loop sweeps the whole input size, e.g. `for col in range(n)`
    self_call_in_sized_loop: bool = False
    #: the recursive argument combines the loop item with the choices made so
    #: far (`walk(path + [x], rest[:i] + rest[i + 1:])`) - an enumeration
    combinatorial_arg: bool = False
    #: ``if n in memo: return memo[n]`` guard
    memoized: bool = False
    #: a recursive argument is a filtered/sliced part of the input
    derived_part: bool = False
    #: ``(kind, variable)`` pairs seen in recursive arguments, where *kind* is
    #: ``"add"`` for ``i + 1`` and ``"sub"`` for ``i - 1``; a variable that
    #: appears as both means the two calls split a range around it
    split_tokens: set[tuple[str, str]] = field(default_factory=set)
    #: source text of every recursive call's positional arguments, used to
    #: count how many of them actually vary (the dimensionality of a memo table)
    call_arg_texts: list[list[str]] = field(default_factory=list)
    #: while-loops that shrink or scale their bound geometrically
    halving_loops: int = 0
    #: deepest loop nest that is *not* inside a geometrically shrinking loop,
    #: so sequential work can still dominate the log factor
    plain_max_depth: int = 0
    #: deepest loop nest found inside a geometrically shrinking while-loop
    halving_inner_depth: int = 0
    #: loop whose bound is ``sqrt(n)`` (``while d*d <= n``, ``range(int(n**0.5))``)
    sqrt_loop: bool = False
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

    @property
    def divides_input(self) -> bool:
        """The recursive step provably shrinks the problem by a factor."""
        return self.halves_input or self.shrinks_input

    @property
    def enumerates_choices(self) -> bool:
        """The self-call in a loop enumerates orderings/subsets, not children.

        Recursing inside ``for col in range(n)`` branches n ways at every one
        of the n levels (n-queens), and passing ``path + [x]`` /
        ``rest[:i] + rest[i+1:]`` builds every ordering (permutations). A
        plain ``for child in node.children: walk(child)`` visits each node
        once, which is linear, not factorial.
        """
        if not self.self_call_in_loop:
            return False
        return self.combinatorial_arg or self.self_call_in_sized_loop

    @property
    def memo_dimensions(self) -> int:
        """How many arguments vary across the recursive calls.

        ``f(n - 1, memo)`` / ``f(n - 2, memo)`` varies one argument, so the
        memo table has O(n) entries; ``lcs(i - 1, j, memo)`` /
        ``lcs(i, j - 1, memo)`` varies two, so it has O(n^2).
        """
        if not self.call_arg_texts:
            return 1
        width = max(len(texts) for texts in self.call_arg_texts)
        dims = 0
        for i in range(width):
            column = {texts[i] for texts in self.call_arg_texts if i < len(texts)}
            if len(column) > 1 or (column and not next(iter(column)).isidentifier()):
                dims += 1
        return max(1, dims)

    @property
    def partition_split(self) -> bool:
        """The recursive calls split the input into two parts of unknown size.

        Two signals count: an argument that is a filtered or sliced *part* of
        the input (quick sort's ``less``/``greater``, ``a[:p]``/``a[p+1:]``),
        and two calls that recurse on complementary index ranges around a
        pivot (``f(a, lo, i - 1)`` and ``f(a, i + 1, hi)``). Neither proves
        the split is balanced, so callers report the pessimistic bound.
        """
        if self.derived_part:
            return True
        subs = {name for kind, name in self.split_tokens if kind == "sub"}
        adds = {name for kind, name in self.split_tokens if kind == "add"}
        return bool(subs & adds)

    @property
    def effective_branches(self) -> int:
        """How many recursive calls can run during one invocation.

        Calls that are each the value of their own ``return`` sit in mutually
        exclusive branches (binary search), so only one of them runs even
        though the source lists two. A single ``return f(n-1) + f(n-2)`` still
        fans out, because both calls are in the same expression.
        """
        if self.self_calls == 0:
            return 0
        if self.tail_self_calls == self.self_calls:
            return max(1, self.max_calls_in_one_return)
        return self.self_calls


class _Visitor(ast.NodeVisitor):
    def __init__(self, func_name: str) -> None:
        self.func_name = func_name
        self.info = _FuncInfo(name=func_name)
        self._depth = 0
        #: names bound by the loops we are currently inside of
        self._loop_vars: list[set[str]] = []
        #: what each enclosing loop iterates over: "size" | "collection" | "while"
        self._loop_kinds: list[str] = []
        #: is the loop we are inside of (transitively) a shrinking one?
        self._halving_active = False
        #: names of the functions we are currently inside of (outer -> inner),
        #: so a nested helper's self-calls count as recursion for the file
        self._func_names: list[str] = [func_name]
        #: value node of the `return` we are inside of (innermost last)
        self._return_values: list[ast.AST] = []
        #: self-calls counted inside the current return expression
        self._calls_in_return = 0
        #: name -> value for assignments seen in the analysed body
        self._assign_sources: dict[str, ast.AST] = {}
        #: names that hold (or are derived from) a halving quantity, so a
        #: recursive argument built from them is a half-size subproblem
        self._halving_names: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._func_names.append(node.name)
        self.generic_visit(node)
        self._func_names.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._func_names.append(node.name)
        self.generic_visit(node)
        self._func_names.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        names: set[str] = set()
        for target in node.targets:
            names |= _bound_names(target)
            for name in _bound_names(target):
                self._assign_sources[name] = node.value
        if _is_halving_value(node.value, self._halving_names):
            self._halving_names |= names
        elif any("mid" in n.lower() or "half" in n.lower() for n in names):
            self._halving_names |= names
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is None:
            self.generic_visit(node)
            return
        outer = self._calls_in_return
        self._calls_in_return = 0
        self._return_values.append(node.value)
        self.generic_visit(node)
        self._return_values.pop()
        self.info.max_calls_in_one_return = max(
            self.info.max_calls_in_one_return, self._calls_in_return)
        self._calls_in_return = outer

    def visit_If(self, node: ast.If) -> None:
        if _is_memo_guard(node):
            self.info.memoized = True
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._record_strided_loop(node)
        if _sqrt_range(node):
            self.info.sqrt_loop = True
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        if not self._halving_active:
            self.info.plain_max_depth = max(self.info.plain_max_depth, self._depth)
        self._loop_vars.append(_bound_names(node.target))
        self._loop_kinds.append("size" if _range_over_size(node) else "collection")
        self.generic_visit(node)
        self._loop_kinds.pop()
        self._loop_vars.pop()
        self._depth -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.info.loop_count += 1
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        self._loop_vars.append(_bound_names(node.target))
        self._loop_kinds.append("collection")
        self.generic_visit(node)
        self._loop_kinds.pop()
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
        halving = _looks_like_halving_loop(node) or _scales_bound(node)
        if halving:
            self.info.halving_loops += 1
            self.info.calls_bisect = True
            self.info.uncertain.append(
                "while loop scales its bound by a constant factor "
                "(e.g. //= 2, *= 2, a % b); treated as logarithmic"
            )
        elif _sqrt_while(node):
            self.info.sqrt_loop = True
        # measure the loop nest *inside* this while so a linear scan under a
        # halving loop multiplies instead of replaces (O(n) x O(log n))
        outer_max = self.info.max_loop_depth
        if not self._halving_active and not halving:
            # a shrinking loop is accounted for by the halving branch; only
            # the loops *outside* it can outgrow the log factor
            self.info.plain_max_depth = max(self.info.plain_max_depth, self._depth)
        outer_active = self._halving_active
        self._halving_active = self._halving_active or halving
        self.info.max_loop_depth = self._depth
        # a while loop has no target, but the names it mutates are its state and
        # can act as the stride of an inner loop (``while i*i <= n: for j in
        # range(i*i, n+1, i)``)
        self._loop_vars.append(_assigned_names(node))
        self._loop_kinds.append("while")
        self.generic_visit(node)
        self._loop_kinds.pop()
        self._loop_vars.pop()
        inner_depth = max(0, self.info.max_loop_depth - self._depth)
        self.info.max_loop_depth = max(outer_max, self.info.max_loop_depth)
        self._halving_active = outer_active
        if halving:
            self.info.halving_inner_depth = max(
                self.info.halving_inner_depth, inner_depth)
        self._depth -= 1

    def _visit_comp(self, node: ast.AST) -> None:
        self.info.loop_count += 1
        self.info.calls_linear = True
        self.info.allocates_list = True
        self._depth += 1
        self.info.max_loop_depth = max(self.info.max_loop_depth, self._depth)
        if not self._halving_active:
            self.info.plain_max_depth = max(self.info.plain_max_depth, self._depth)
        self._loop_kinds.append("collection")
        self.generic_visit(node)
        self._loop_kinds.pop()
        self._depth -= 1

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comp(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comp(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comp(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comp(node)

    def _is_self_call(self, fname: str, base: str) -> bool:
        """A call to the analysed function or to a helper defined inside it."""
        if not fname:
            return False
        return fname in self._func_names or base in self._func_names

    def visit_Call(self, node: ast.Call) -> None:
        fname = _call_name(node)
        base = fname.split(".")[-1] if fname else ""
        if self._is_self_call(fname, base):
            self.info.recursive = True
            self.info.self_calls += 1
            self._calls_in_return += 1
            if self._return_values and self._return_values[-1] is node:
                self.info.tail_self_calls += 1
            if self._depth > 0:
                self.info.self_call_in_loop = True
                if self._loop_kinds and self._loop_kinds[-1] == "size":
                    self.info.self_call_in_sized_loop = True
            if _combinatorial_arg(node, self._enclosing_names()):
                self.info.combinatorial_arg = True
            self.info.call_arg_texts.append([
                ast.unparse(arg) if hasattr(ast, "unparse") else ast.dump(arg)
                for arg in node.args
            ])
            self._inspect_recursive_call(node)
        elif base in _SORT_CALLS:
            self.info.calls_sort = True
            if base == "sorted":
                # `sorted()` returns a new list; `list.sort()` is in place
                self.info.allocates_list = True
        elif base in _HEAP_CALLS:
            self.info.calls_heap = True
            if self._depth > 0:
                # a heap driven from a loop holds up to n items
                self.info.allocates_list = True
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
        # `n * "*"`, `[0] * n` and `bytearray([1]) * (n + 1)` all build a
        # sequence whose length grows with n
        if _sequence_mult(node):
            self.info.calls_linear = True
            self.info.allocates_list = True
        self.generic_visit(node)


    def _inspect_recursive_call(self, node: ast.Call) -> None:
        for arg in node.args:
            rep = ast.unparse(arg) if hasattr(ast, "unparse") else ast.dump(arg)
            low = rep.lower()
            if "//" in rep or ">>" in rep or "/ 2" in rep or "/2" in rep:
                self.info.halves_input = True
            # `%` (Euclid), `//`, `>>`, `/2` all cut the problem by a factor
            if any(tok in rep for tok in ("//", ">>", "/ 2", "/2", "%")):
                self.info.shrinks_input = True
            if _names_in(arg) & self._halving_names:
                # e.g. `z0 = main(low_x, low_y)` where low_x came from a
                # `half = n // 2` split
                self.info.halves_input = True
                self.info.uncertain.append(
                    "recursive call passes a value derived from a halving "
                    "split; assumed divide-and-conquer"
                )
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
            # a part derived by filtering/slicing (quick sort's `less` /
            # `greater`) is a partition, whose balance cannot be proven
            if _is_derived_part(arg, self._assign_sources):
                self.info.derived_part = True
            # `f(a, lo, i - 1)` + `f(a, i + 1, hi)` recurse on the two sides
            # of a pivot index -> also a partition
            for child in ast.walk(arg):
                if (isinstance(child, ast.BinOp) and isinstance(child.left, ast.Name)
                        and isinstance(child.right, ast.Constant)
                        and child.right.value == 1):
                    kind = ("add" if isinstance(child.op, ast.Add)
                            else "sub" if isinstance(child.op, ast.Sub) else None)
                    if kind:
                        self.info.split_tokens.add((kind, child.left.id))


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


def _scales_bound(node: ast.While) -> bool:
    """True when the loop variable is cut down (or grown) by a constant factor.

    ``while exp > 0: exp //= 2``, ``while i < n: i *= 2`` and Euclid's
    ``while b: a, b = b, a % b`` each leave a constant fraction of the
    remaining range behind, so the trip count is logarithmic. A loop that
    merely steps (``i += 1``, ``j -= 1``) stays linear.
    """
    test_names = _names_in(node.test)
    if not test_names:
        return False
    for child in ast.walk(node):
        for name, op, value in _assignment_pairs(child):
            if name in test_names and _scales_op(op, value):
                return True
    return False


def _assignment_pairs(node: ast.AST) -> list[tuple[str, ast.AST | None, ast.AST]]:
    """(assigned name, augmented operator or None, value) of one assignment."""
    pairs: list[tuple[str, ast.AST | None, ast.AST]] = []
    if isinstance(node, ast.AugAssign):
        for name in _bound_names(node.target):
            pairs.append((name, node.op, node.value))
    elif isinstance(node, ast.Assign) and node.targets:
        targets = node.targets
        if isinstance(targets[0], ast.Tuple):
            elts = list(targets[0].elts)
            values = (list(node.value.elts)
                      if isinstance(node.value, ast.Tuple) else [])
            if len(elts) == len(values):
                for target, value in zip(elts, values):
                    pairs.extend((n, None, value) for n in _bound_names(target))
                return pairs
        for target in targets:
            pairs.extend((n, None, node.value) for n in _bound_names(target))
    return pairs


def _scales_op(op: ast.AST | None, value: ast.AST) -> bool:
    """Does ``<op> value`` cut the remaining range by a constant factor?

    Handles both ``x *= 2`` (augmented, only the right operand is stored) and
    ``x = x * 2`` (plain assignment, a full ``BinOp``).
    """
    if op is not None:
        if isinstance(op, (ast.Div, ast.FloorDiv, ast.LShift, ast.RShift, ast.Mod)):
            return True
        if isinstance(op, ast.Mult):
            return isinstance(value, (ast.Constant, ast.Name))
        return False
    return _scales_expr(value)


def _scales_expr(value: ast.AST) -> bool:
    """True for ``x * 2``, ``x // 2``, ``x >> 1``, ``a % b``, ``x / 10``."""
    if not isinstance(value, ast.BinOp):
        return False
    op = value.op
    if isinstance(op, (ast.Div, ast.FloorDiv, ast.LShift, ast.RShift, ast.Mod)):
        return True
    if isinstance(op, ast.Mult):
        other = value.right
        if isinstance(other, ast.Constant):
            return isinstance(other.value, (int, float)) and other.value not in (0, 1)
        return False
    return False


def _has_nested_loop(node: ast.AST) -> bool:
    return any(isinstance(child, (ast.For, ast.AsyncFor, ast.While))
               for child in ast.walk(node) if child is not node)


def _sqrt_while(node: ast.While) -> bool:
    """``while d * d <= n: d += 1`` walks O(sqrt n) steps."""
    if _has_nested_loop(node):
        return False
    for child in ast.walk(node.test):
        if not isinstance(child, ast.Compare):
            continue
        left = child.left
        if not isinstance(left, ast.BinOp):
            continue
        if not isinstance(left.op, (ast.Mult, ast.Pow)):
            continue
        names = _names_in(left)
        if len(names) == 1 and _steps_by_constant(node, names):
            return True
    return False


def _steps_by_constant(node: ast.AST, names: set[str]) -> bool:
    """The loop advances *names* with ``+= <constant>`` (not geometrically)."""
    for child in ast.walk(node):
        if isinstance(child, ast.AugAssign) and _bound_names(child.target) & names:
            return (isinstance(child.op, ast.Add)
                    and isinstance(child.value, ast.Constant))
    return False


_SEQUENCE_BUILDERS = frozenset({"list", "bytearray", "tuple", "str", "set", "dict"})


def _is_sequence_expr(node: ast.AST) -> bool:
    """The operand of a multiplication is (or builds) a sequence."""
    for child in ast.walk(node):
        if isinstance(child, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return True
        if isinstance(child, ast.Constant) and isinstance(child.value, (str, bytes)):
            return True
        if isinstance(child, ast.Call):
            base = _call_name(child).split(".")[-1]
            if base in _SEQUENCE_BUILDERS:
                return True
    return False


def _sequence_mult(node: ast.BinOp) -> bool:
    """``[0] * n`` / ``bytearray([1]) * (n + 1)`` — a sequence sized by n."""
    if not isinstance(node.op, ast.Mult):
        return False
    return _is_sequence_expr(node.left) or _is_sequence_expr(node.right)


def _sqrt_range(node: ast.For) -> bool:
    """``for d in range(2, int(n ** 0.5) + 1)`` — a sqrt-sized sweep."""
    it = node.iter
    if not isinstance(it, ast.Call) or _call_name(it) != "range" or not it.args:
        return False
    stop = it.args[1] if len(it.args) >= 2 else it.args[0]
    rep = ast.unparse(stop) if hasattr(ast, "unparse") else ""
    rep = rep.replace(" ", "")
    return ("sqrt(" in rep or "**0.5" in rep or "**(1/2)" in rep
            or "**(1.0/2.0)" in rep)


def _is_halving_value(value: ast.AST, halving_names: set[str]) -> bool:
    """The value is a half of something: ``n // 2`` or built from one."""
    names = _names_in(value)
    if names & halving_names:
        return True
    if isinstance(value, ast.BinOp) and isinstance(value.op, (ast.FloorDiv, ast.RShift)):
        right = value.right
        if isinstance(right, ast.Constant) and right.value == 2:
            return True
    return False


def _range_over_size(node: ast.For) -> bool:
    """``for i in range(n)`` / ``range(len(a))`` sweeps the whole input."""
    it = node.iter
    if not isinstance(it, ast.Call) or _call_name(it) != "range" or not it.args:
        return False
    stop = it.args[1] if len(it.args) >= 2 else it.args[0]
    if isinstance(stop, ast.Name):
        return True
    return isinstance(stop, ast.Call) and _call_name(stop) == "len"


def _combinatorial_arg(node: ast.Call, loop_names: set[str]) -> bool:
    """Does a recursive call build a *combination* out of the loop item?

    ``walk(path + [x], rest[:i] + rest[i + 1:])`` assembles every ordering:
    the loop item is merged into the choice list, or removed from the
    remaining pool. Plain ``walk(child)`` just descends.
    """
    if not loop_names:
        return False
    for arg in node.args:
        for child in ast.walk(arg):
            if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Add):
                sides = (child.left, child.right)
                if not ((_names_in(child.left) | _names_in(child.right))
                        & loop_names):
                    continue
                if any(isinstance(s, (ast.List, ast.Tuple, ast.Set, ast.Subscript,
                                      ast.ListComp, ast.GeneratorExp))
                       for s in sides):
                    return True
            elif isinstance(child, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
                if _names_in(child) & loop_names and any(g.ifs for g in child.generators):
                    return True
    return False


def _is_derived_part(arg: ast.AST, sources: dict[str, ast.AST]) -> bool:
    """True when a recursive argument is a filtered/sliced part of the input.

    Quick sort passes ``less``/``greater`` (built by a filtering
    comprehension) or ``a[:p]``/``a[p+1:]``; both are *parts* of the input,
    but nothing in the source proves they are balanced halves.
    """
    value = arg
    if isinstance(arg, ast.Name):
        value = sources.get(arg.id, arg)
    for child in ast.walk(value):
        if isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp,
                              ast.GeneratorExp)):
            if any(gen.ifs for gen in child.generators):
                return True
        elif isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Slice):
            return True
    return False


def _is_memo_guard(node: ast.If) -> bool:
    """``if n in memo: return memo[n]`` — a memoisation cache hit."""
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.In) or len(test.comparators) != 1:
        return False
    cache_names = {n.id for n in ast.walk(test.comparators[0])
                   if isinstance(n, ast.Name)}
    if not cache_names:
        return False
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and not isinstance(child.value, type(None)):
            value = child.value
            if (isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name)
                    and value.value.id in cache_names):
                return True
    return False


def _time_for_func(info):
    notes = []
    if info.recursive:
        return _time_for_recursion(info)
    if info.calls_sort:
        notes.append("detected sort/sorted call: O(n log n) dominates loops")
        return "n*log2(n)", 0.75, notes
    if info.halving_loops:
        inner = min(info.halving_inner_depth, len(_HALVING_PRODUCT) - 1)
        expr = _HALVING_PRODUCT[inner]
        if inner == 0:
            notes.append(
                "geometrically shrinking while-loop "
                "(binary-search / Euclid style) -> O(log n)"
            )
            conf = 0.7
        else:
            notes.append(
                "geometrically shrinking while-loop wrapping a %d-deep scan "
                "-> %s" % (inner, _label(expr))
            )
            conf = 0.5
        # loops *alongside* the shrinking one still cost their own class, and
        # they usually dwarf a log factor (`while size < n: size *= 2` followed
        # by a linear pass is O(n), not O(log n))
        if info.plain_max_depth >= 1:
            plain, plain_conf, plain_notes = _class_for_depth(
                info, info.plain_max_depth)
            if _EXPR_TO_RANK[plain] > _EXPR_TO_RANK[expr]:
                notes += plain_notes
                notes.append(
                    "work outside the shrinking loop dominates the log factor")
                return plain, min(conf, plain_conf), notes
        return expr, conf, notes
    if info.sqrt_loop and info.max_loop_depth <= 1:
        notes.append("loop bound is sqrt(n) -> O(sqrt n)")
        return "sqrt(n)", 0.55, notes
    if info.calls_bisect and info.max_loop_depth <= 1 and info.while_count >= 1:
        notes.append("halving while-loop (binary-search style) -> O(log n)")
        return "log2(n)", 0.7, notes
    if info.calls_bisect and info.max_loop_depth == 0 and info.loop_count == 0:
        notes.append("bisect helper with no loops: O(log n)")
        return "log2(n)", 0.75, notes
    if info.calls_heap and info.max_loop_depth >= 1:
        notes.append("heap op inside loop: O(n)*O(log n) -> O(n log n)")
        return "n*log2(n)", 0.65, notes
    return _class_for_depth(info, info.max_loop_depth)


def _class_for_depth(info, depth):
    """Class implied by a loop nesting depth (comprehensions included)."""
    notes = []
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


def _divide_conquer_class(exponent: float) -> str:
    """Cheapest canonical class that is at least ``n ** exponent``."""
    for expr in TIME_EXPRS:
        try:
            growth = Complexity(expr).growth_exponent
        except Exception:  # pragma: no cover - defensive
            continue
        if growth is not None and math.isfinite(growth) and growth >= exponent - 1e-9:
            return expr
    return "2**n"


def _time_for_recursion(info):
    notes = [u for u in info.uncertain if not u.startswith("recursive call passes")]
    weak = [u for u in info.uncertain if u.startswith("recursive call passes")]
    branches = info.effective_branches

    if info.memoized:
        dims = min(info.memo_dimensions, 3)
        expr = ("n", "n**2", "n**3")[dims - 1]
        shape = "O(n)" if dims == 1 else "O(n^%d)" % dims
        notes.append("memo table detected: a %d-dimensional state space (%s "
                     "entries), each solved once" % (dims, shape))
        return expr, 0.55, notes

    if branches >= 2:
        if info.divides_input:
            if branches == 2:
                notes.append(
                    "halving recursion over 2 subproblems at every level "
                    "-> O(n log n)"
                )
                return "n*log2(n)", 0.6, notes
            # T(n) = b*T(n/2) + O(n) is O(n^log2(b)) by the master theorem;
            # report the next canonical class up rather than under-estimate
            exponent = math.log2(branches)
            expr = _divide_conquer_class(exponent)
            notes.append(
                "%d subproblems of half size -> O(n^%.2f) by the master "
                "theorem; reported conservatively as %s"
                % (branches, exponent, _label(expr))
            )
            return expr, 0.45, notes
        if info.partition_split:
            notes = notes + weak
            notes.append(
                "recursion splits the input into two derived parts whose "
                "balance cannot be proven: worst case O(n^2) (adversarial "
                "splits), average/best O(n log n) (balanced splits)"
            )
            return "n**2", 0.4, notes
        if info.enumerates_choices:
            notes.append(
                "self-call inside a loop that enumerates choices -> O(n!) "
                "(every ordering is visited)"
            )
            return "factorial(n)", 0.3, notes
        notes = notes + weak
        notes.append("2+ self-calls without halving -> O(2^n); memoisation may help")
        return "2**n", 0.4, notes

    # a single recursive call per invocation: the cost is the recursion depth
    if info.enumerates_choices:
        notes.append(
            "self-call inside a loop that enumerates choices -> O(n!) "
            "(every ordering is visited)"
        )
        return "factorial(n)", 0.3, notes
    if info.divides_input:
        notes.append(
            "single call on a geometrically shrunk input -> O(log n) depth"
        )
        return "log2(n)", 0.6, notes
    notes.append("single self-recursion, no halving -> O(n) depth assumed")
    return "n", 0.4, notes


def _best_case(worst, info):
    if worst == "1":
        return "1", 0.8
    if worst == "factorial(n)":
        # every branch has to be walked, so the best case equals the worst
        return worst, 0.3
    if info.max_loop_depth == 1 and not info.recursive:
        # a single scan can exit on its first iteration
        return "1", 0.4
    if worst in ("n**2", "n**2*log2(n)", "n**3", "n**3*log2(n)"):
        return "n", 0.3
    if worst == "n*log2(n)":
        return "n", 0.35
    if worst == "log2(n)":
        return "1", 0.4
    if worst == "sqrt(n)":
        return "1", 0.4
    return worst, 0.3


def _space_for_func(info):
    if info.memoized:
        dims = min(info.memo_dimensions, 3)
        expr = ("n", "n**2", "n**3")[dims - 1]
        return expr, ["memo table of %s entries dominates the space" % _label(expr)]
    if info.recursive:
        depth = "log2(n)" if info.divides_input else "n"
        if info.allocates_list:
            # per-level copies/allocations dominate the O(log n) stack
            return "n", ["recursion depth implies %s stack; per-level "
                         "allocation raises it to O(n)" % _label(depth)]
        return depth, ["recursion depth implies " + _label(depth) + " stack"]
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
    average = worst
    if info.memoized:
        # one entry per state: best, average and worst are the table size
        best = average = worst
    elif info.partition_split and not info.divides_input and worst == "n**2":
        # unbalanced splits are adversarial, not typical
        best = average = "n*log2(n)"
    else:
        notes.append(
            "average case assumed equal to the worst case: nothing in the "
            "source describes the input distribution"
        )
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
        "effective_branches": info.effective_branches,
        "halves_input": info.halves_input,
        "shrinks_input": info.shrinks_input,
        "memoized": info.memoized,
        "partition_split": info.partition_split,
        "self_call_in_loop": info.self_call_in_loop,
        "halving_loops": info.halving_loops,
        "halving_inner_depth": info.halving_inner_depth,
        "sqrt_loop": info.sqrt_loop,
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
        notes=_dedupe([header] + notes + space_notes + info.uncertain),
        details=details,
    )


def _dedupe(items: list[str]) -> list[str]:
    """Notes in order of first appearance, without repeats.

    A recursive function trips the same heuristic once per call site, which
    makes the report say the same thing three times.
    """
    seen: set[str] = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


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
