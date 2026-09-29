"""Ground-truth corpus for :mod:`algocomp.static_analysis`.

Every entry is a small Python function whose asymptotic worst-case time is
known from the textbook, plus the space bound when it is unambiguous. The
estimator in :mod:`algocomp.static_analysis` is graded against this corpus by
``tests/test_big_o.py`` and by::

    python -m tests.big_o_corpus           # accuracy table

Tiers
-----
``exact``
    The estimator must return exactly the ground truth. A failure here is a
    bug in the analyzer.
``conservative``
    The estimator returns a *valid upper bound* that is one class above the
    truth, because the finer class is not decidable from the source shape
    (the sieve's O(n log log n) needs number theory; BFS's O(V+E) needs the
    edge count). Documented, not hidden.
``limit``
    The structure cannot be resolved at all from the AST (a loop whose trip
    count is a data value). The corpus records what the estimator does fall
    back to so the behaviour is pinned.

Ground truth is stored as an *expression* (``"n*log2(n)"``), the same
vocabulary the estimator speaks, so comparisons never depend on label text.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    """One algorithm plus its known complexity."""

    key: str
    source: str
    #: ground-truth worst-case time, as a growth expression
    time: str
    tier: str = "exact"
    #: what the estimator is expected to return (defaults to `time`)
    expect: str = ""
    #: ground-truth best case, when the corpus asserts it
    best: str | None = None
    #: ground-truth average case, when the corpus asserts it
    average: str | None = None
    #: ground-truth auxiliary space, when unambiguous
    space: str | None = None
    #: why the truth is what it is (or why the estimator differs)
    note: str = ""

    @property
    def expected(self) -> str:
        return self.expect or self.time

    @property
    def is_exact(self) -> bool:
        return self.tier == "exact"

    @property
    def is_holdout(self) -> bool:
        return self.tier == "holdout"


def _case(case: Case) -> Case:
    return case


CASES: tuple[Case, ...] = (
    # ------------------------------------------------------------------ O(1)
    Case(
        key="constant_access",
        time="1",
        space="1",
        note="indexing a sequence is a constant-time operation",
        source='''\
def main(a):
    return a[0]
''',
    ),
    Case(
        key="dict_lookup",
        time="1",
        space="1",
        note="hash lookup is amortised O(1)",
        source='''\
def main(d, key):
    return d[key]
''',
    ),
    Case(
        key="empty_function",
        time="1",
        space="1",
        note="no loops, no recursion",
        source='''\
def main(a):
    return None
''',
    ),
    # ------------------------------------------------------------------ O(n)
    Case(
        key="linear_sum",
        time="n",
        best="1",
        average="n",
        space="1",
        note="one pass over the input",
        source='''\
def main(a):
    total = 0
    for x in a:
        total += x
    return total
''',
    ),
    Case(
        key="linear_search",
        time="n",
        best="1",
        average="n",
        space="1",
        note="scans until it finds the target; O(1) if it is first",
        source='''\
def main(a, target):
    for i, x in enumerate(a):
        if x == target:
            return i
    return -1
''',
    ),
    Case(
        key="list_comprehension",
        time="n",
        space="n",
        note="a comprehension is a loop that builds a new list",
        source='''\
def main(a):
    return [x * 2 for x in a]
''',
    ),
    Case(
        key="two_sequential_loops",
        time="n",
        space="1",
        note="sequential loops add, they do not multiply",
        source='''\
def main(a):
    total = 0
    for x in a:
        total += x
    for x in a:
        total -= x
    return total
''',
    ),
    Case(
        key="constant_stride_loop",
        time="n",
        note="range(0, n, 2) is still a linear sweep: the stride is constant",
        source='''\
def main(n):
    total = 0
    for i in range(0, n, 2):
        total += i
    return total
''',
    ),
    Case(
        key="two_pointer",
        time="n",
        space="1",
        note="the two indices meet after at most n steps",
        source='''\
def main(a):
    lo, hi = 0, len(a) - 1
    while lo < hi:
        total = a[lo] + a[hi]
        if total == 0:
            return True
        if total < 0:
            lo += 1
        else:
            hi -= 1
    return False
''',
    ),
    Case(
        key="dutch_flag_single_pass",
        time="n",
        space="1",
        note="one while-loop, three-way partition, in place",
        source='''\
def main(a):
    lo, mid, hi = 0, 0, len(a) - 1
    while mid <= hi:
        if a[mid] == 0:
            a[lo], a[mid] = a[mid], a[lo]
            lo += 1
            mid += 1
        elif a[mid] == 1:
            mid += 1
        else:
            a[mid], a[hi] = a[hi], a[mid]
            hi -= 1
    return a
''',
    ),
    Case(
        key="linear_early_exit",
        time="n",
        note="a break does not change the worst case",
        source='''\
def main(a, target):
    found = False
    for x in a:
        if x == target:
            found = True
            break
    return found
''',
    ),
    Case(
        key="join_generator",
        time="n",
        space="n",
        note="join over a generator: one pass, one new string",
        source='''\
def main(a):
    return "".join(str(x) for x in a)
''',
    ),
    Case(
        key="module_level_loop",
        time="n",
        note="top-level code with no function definition",
        source='''\
total = 0
for i in range(int(input())):
    total += i
print(total)
''',
    ),
    # -------------------------------------------------------------- O(log n)
    Case(
        key="binary_search_iterative",
        time="log2(n)",
        best="1",
        average="log2(n)",
        space="1",
        note="halves the search interval every iteration",
        source='''\
def main(a, target):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        elif a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
    ),
    Case(
        key="binary_search_recursive",
        time="log2(n)",
        space="log2(n)",
        note="the two recursive calls are mutually exclusive returns, so only "
             "one runs per invocation: O(log n) depth, not O(n log n)",
        source='''\
def main(a, target, lo=0, hi=None):
    if hi is None:
        hi = len(a) - 1
    if lo > hi:
        return -1
    mid = (lo + hi) // 2
    if a[mid] == target:
        return mid
    if a[mid] < target:
        return main(a, target, mid + 1, hi)
    return main(a, target, lo, mid - 1)
''',
    ),
    Case(
        key="binary_search_bisect",
        time="log2(n)",
        space="1",
        note="bisect module call, no loops of its own",
        source='''\
import bisect


def main(a, target):
    i = bisect.bisect_left(a, target)
    return i < len(a) and a[i] == target
''',
    ),
    Case(
        key="exponentiation_by_squaring",
        time="log2(n)",
        space="1",
        note="the exponent is halved every iteration",
        source='''\
def main(base, exp):
    result = 1
    while exp > 0:
        if exp & 1:
            result *= base
        base *= base
        exp //= 2
    return result
''',
    ),
    Case(
        key="gcd_euclid",
        time="log2(n)",
        best="1",
        space="1",
        note="Euclid: a % b at least halves the larger operand every two rounds",
        source='''\
def main(a, b):
    while b:
        a, b = b, a % b
    return a
''',
    ),
    Case(
        key="gcd_recursive",
        time="log2(n)",
        space="log2(n)",
        note="same shrink as the iterative form, on the call stack",
        source='''\
def main(a, b):
    if b == 0:
        return a
    return main(b, a % b)
''',
    ),
    Case(
        key="doubling_loop",
        time="log2(n)",
        space="1",
        note="i *= 2 reaches n after log2(n) steps",
        source='''\
def main(n):
    i = 1
    while i < n:
        i *= 2
    return i
''',
    ),
    # ------------------------------------------------------------ O(sqrt(n))
    Case(
        key="trial_division_while",
        time="sqrt(n)",
        best="1",
        space="1",
        note="the loop stops at d*d > n, i.e. after sqrt(n) steps",
        source='''\
def main(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True
''',
    ),
    Case(
        key="trial_division_for",
        time="sqrt(n)",
        space="1",
        note="range() bound is int(n ** 0.5)",
        source='''\
def main(n):
    if n < 2:
        return False
    for d in range(2, int(n ** 0.5) + 1):
        if n % d == 0:
            return False
    return True
''',
    ),
    # --------------------------------------------------------------- O(n^2)
    Case(
        key="bubble_sort",
        time="n**2",
        best="n",
        average="n**2",
        space="1",
        note="nested passes over the array",
        source='''\
def main(a):
    n = len(a)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a
''',
    ),
    Case(
        key="insertion_sort",
        time="n**2",
        best="n",
        average="n**2",
        space="1",
        note="the inner while walks back over the sorted prefix",
        source='''\
def main(a):
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a
''',
    ),
    Case(
        key="selection_sort",
        time="n**2",
        space="1",
        note="for every position, scan the rest for the minimum",
        source='''\
def main(a):
    n = len(a)
    for i in range(n):
        best = i
        for j in range(i + 1, n):
            if a[j] < a[best]:
                best = j
        a[i], a[best] = a[best], a[i]
    return a
''',
    ),
    Case(
        key="max_subarray_bruteforce",
        time="n**2",
        space="1",
        note="all pairs (i, j)",
        source='''\
def main(a):
    n = len(a)
    best = 0
    for i in range(n):
        total = 0
        for j in range(i, n):
            total += a[j]
            best = max(best, total)
    return best
''',
    ),
    Case(
        key="nested_comprehension",
        time="n**2",
        space="n",
        note="a comprehension inside a comprehension is a nested loop",
        source='''\
def main(a):
    return [[x + y for y in a] for x in a]
''',
    ),
    Case(
        key="matrix_vector_product",
        time="n**2",
        space="n",
        note="n rows x n columns",
        source='''\
def main(A, x):
    n = len(A)
    out = [0] * n
    for i in range(n):
        for j in range(n):
            out[i] += A[i][j] * x[j]
    return out
''',
    ),
    # --------------------------------------------------------------- O(n^3)
    Case(
        key="matrix_multiply",
        time="n**3",
        space="n",
        note="schoolbook i-k-j triple loop",
        source='''\
def main(A, B):
    n = len(A)
    C = [[0] * n for _ in range(n)]
    for i in range(n):
        for k in range(n):
            for j in range(n):
                C[i][j] += A[i][k] * B[k][j]
    return C
''',
    ),
    Case(
        key="floyd_warshall",
        time="n**3",
        space="1",
        note="all-pairs shortest paths, in place",
        source='''\
def main(dist):
    n = len(dist)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
    return dist
''',
    ),
    Case(
        key="three_sum_bruteforce",
        time="n**3",
        space="1",
        note="all triples i < j < k",
        source='''\
def main(a):
    n = len(a)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if a[i] + a[j] + a[k] == 0:
                    return True
    return False
''',
    ),
    # ----------------------------------------------------------- O(n log n)
    Case(
        key="merge_sort",
        time="n*log2(n)",
        space="n",
        note="log n levels, each merging n elements",
        source='''\
def main(a):
    n = len(a)
    if n <= 1:
        return list(a)
    mid = n // 2
    left = main(a[:mid])
    right = main(a[mid:])
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out
''',
    ),
    Case(
        key="merge_sort_with_helper",
        time="n*log2(n)",
        space="n",
        note="two top-level functions; the recursive one dominates",
        source='''\
def merge(left, right):
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def merge_sort(a):
    if len(a) <= 1:
        return list(a)
    mid = len(a) // 2
    return merge(merge_sort(a[:mid]), merge_sort(a[mid:]))
''',
    ),
    Case(
        key="heap_sort",
        time="n*log2(n)",
        space="n",
        note="heapify then n heappops",
        source='''\
import heapq


def main(a):
    heapq.heapify(a)
    out = []
    while a:
        out.append(heapq.heappop(a))
    return out
''',
    ),
    Case(
        key="heap_push_loop",
        time="n*log2(n)",
        space="n",
        note="n pushes costing O(log n) each",
        source='''\
import heapq


def main(a):
    heap = []
    for x in a:
        heapq.heappush(heap, x)
    return heap
''',
    ),
    Case(
        key="builtin_sorted",
        time="n*log2(n)",
        space="n",
        note="sorted() is Timsort, and returns a new list",
        source='''\
def main(a):
    return sorted(a)
''',
    ),
    Case(
        key="binary_search_on_answer",
        time="n*log2(n)",
        space="1",
        note="a linear feasibility check inside a binary search over the answer",
        source='''\
def main(a, k):
    lo, hi = max(a), sum(a)
    while lo < hi:
        mid = (lo + hi) // 2
        groups = 1
        total = 0
        for x in a:
            if total + x > mid:
                groups += 1
                total = 0
            total += x
        if groups > k:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
    ),
    Case(
        key="binary_search_answer_quadratic_check",
        time="n**2*log2(n)",
        space="1",
        note="a binary search over the answer space wrapping an O(n^2) count",
        source='''\
def main(a, limit):
    lo, hi = 0, max(a) * len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        pairs = 0
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                if a[i] + a[j] <= mid:
                    pairs += 1
        if pairs < limit:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
    ),
    Case(
        key="binary_search_answer_cubic_check",
        time="n**3*log2(n)",
        space="1",
        note="a binary search over the answer space wrapping an O(n^3) count",
        source='''\
def main(a, limit):
    lo, hi = 0, max(a) * 3
    while lo < hi:
        mid = (lo + hi) // 2
        count = 0
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                for k in range(j + 1, len(a)):
                    if a[i] + a[j] + a[k] <= mid:
                        count += 1
        if count < limit:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
    ),
    # --------------------------------------------------------------- O(2^n)
    Case(
        key="naive_fibonacci",
        time="2**n",
        space="n",
        note="two overlapping subproblems, no memoisation",
        source='''\
def main(n):
    if n <= 1:
        return n
    return main(n - 1) + main(n - 2)
''',
    ),
    Case(
        key="subsets_backtracking",
        time="2**n",
        note="two branches per element",
        source='''\
def main(items):
    out = []

    def walk(i, path):
        if i == len(items):
            out.append(path)
            return
        walk(i + 1, path)
        walk(i + 1, path + [items[i]])

    walk(0, [])
    return out
''',
    ),
    # ---------------------------------------------------------------- O(n!)
    Case(
        key="permutations",
        time="factorial(n)",
        space="n",
        note="every ordering is enumerated: n choices, then n-1, then ...",
        source='''\
def main(items):
    out = []

    def walk(path, rest):
        if not rest:
            out.append(path)
            return
        for i, x in enumerate(rest):
            walk(path + [x], rest[:i] + rest[i + 1:])

    walk([], list(items))
    return out
''',
    ),
    Case(
        key="n_queens_backtracking",
        time="factorial(n)",
        space="n",
        note="row-by-row placement with column/diagonal pruning is O(n!)",
        source='''\
def main(n):
    cols = set()
    diag = set()
    anti = set()

    def place(row):
        if row == n:
            return 1
        total = 0
        for col in range(n):
            if col in cols or (row + col) in diag or (row - col) in anti:
                continue
            cols.add(col)
            diag.add(row + col)
            anti.add(row - col)
            total += place(row + 1)
            cols.remove(col)
            diag.discard(row + col)
            anti.discard(row - col)
        return total

    return place(0)
''',
    ),
    # ------------------------------------------- O(n) via memoisation / depth
    Case(
        key="fibonacci_memoised",
        time="n",
        space="n",
        note="the memo guard makes each of the n states cost O(1)",
        source='''\
def main(n, memo=None):
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = main(n - 1, memo) + main(n - 2, memo)
    return memo[n]
''',
    ),
    Case(
        key="factorial_recursive",
        time="n",
        space="n",
        note="a single recursive call per level: n levels",
        source='''\
def main(n):
    if n <= 1:
        return 1
    return n * main(n - 1)
''',
    ),
    Case(
        key="lcs_memoised",
        time="n**2",
        space="n**2",
        note="two arguments vary, so the memo table is n x n and each of the "
             "n^2 states costs O(1)",
        source='''\
def main(a, b, i=None, j=None, memo=None):
    if memo is None:
        memo = {}
        i, j = len(a), len(b)
    if i == 0 or j == 0:
        return 0
    if (i, j) in memo:
        return memo[(i, j)]
    if a[i - 1] == b[j - 1]:
        best = 1 + main(a, b, i - 1, j - 1, memo)
    else:
        best = max(main(a, b, i - 1, j, memo), main(a, b, i, j - 1, memo))
    memo[(i, j)] = best
    return best
''',
    ),
    Case(
        key="karatsuba",
        time="n**1.585",
        tier="conservative",
        expect="n**2",
        note="three half-size subproblems: O(n^log2(3)) = O(n^1.585) by the "
             "master theorem. The analyzer rounds up to the next class it can "
             "name, O(n^2), rather than under-state the bound. Space is not "
             "asserted: the analyzer sees the O(log n) call stack, while the "
             "true auxiliary space depends on how the big integers are held.",
        source='''\
def main(x, y):
    if x < 10 or y < 10:
        return x * y
    n = max(len(str(x)), len(str(y)))
    half = n // 2
    high_x, low_x = divmod(x, 10 ** half)
    high_y, low_y = divmod(y, 10 ** half)
    z0 = main(low_x, low_y)
    z2 = main(high_x, high_y)
    z1 = main(high_x + low_x, high_y + low_y) - z2 - z0
    return z2 * 10 ** (2 * half) + z1 * 10 ** half + z0
''',
    ),
    Case(
        key="strassen",
        time="n**2.807",
        tier="conservative",
        expect="n**3",
        space="n",
        note="seven half-size subproblems: O(n^log2(7)) = O(n^2.807). Reported "
             "as the next class up, O(n^3).",
        source='''\
def main(A, B):
    n = len(A)
    if n <= 1:
        return [[A[0][0] * B[0][0]]]
    half = n // 2
    A11, A12 = [row[:half] for row in A[:half]], [row[half:] for row in A[:half]]
    A21, A22 = [row[:half] for row in A[half:]], [row[half:] for row in A[half:]]
    B11, B12 = [row[:half] for row in B[:half]], [row[half:] for row in B[:half]]
    B21, B22 = [row[:half] for row in B[half:]], [row[half:] for row in B[half:]]
    m1 = main([[a + b for a, b in zip(A11r, A22r)] for A11r, A22r in zip(A11, A22)],
              [[a + b for a, b in zip(B11r, B22r)] for B11r, B22r in zip(B11, B22)])
    m2 = main([[a + b for a, b in zip(A21r, A22r)] for A21r, A22r in zip(A21, A22)], B11)
    m3 = main(A11, [[b - d for b, d in zip(B12r, B22r)] for B12r, B22r in zip(B12, B22)])
    m4 = main(A22, [[c - a for c, a in zip(B21r, B11r)] for B21r, B11r in zip(B21, B11)])
    m5 = main([[a + b for a, b in zip(A11r, A12r)] for A11r, A12r in zip(A11, A12)], B22)
    m6 = main([[c - a for c, a in zip(A21r, A11r)] for A21r, A11r in zip(A21, A11)],
              [[a + b for a, b in zip(B11r, B12r)] for B11r, B12r in zip(B11, B12)])
    m7 = main([[b - d for b, d in zip(A12r, A22r)] for A12r, A22r in zip(A12, A22)],
              [[c + d for c, d in zip(B21r, B22r)] for B21r, B22r in zip(B21, B22)])
    out = [[0] * n for _ in range(n)]
    for i in range(half):
        for j in range(half):
            out[i][j] = m1[i][j] + m4[i][j] - m5[i][j] + m7[i][j]
            out[i][j + half] = m3[i][j] + m5[i][j]
            out[i + half][j] = m2[i][j] + m4[i][j]
            out[i + half][j + half] = m1[i][j] - m2[i][j] + m3[i][j] + m6[i][j]
    return out
''',
    ),
    # --------------------------------------------- quicksort: worst != average
    Case(
        key="quick_sort",
        time="n**2",
        best="n*log2(n)",
        average="n*log2(n)",
        space="n",
        note="unbalanced partitions give O(n^2); balanced ones give O(n log n)",
        source='''\
def main(a):
    if len(a) <= 1:
        return a
    pivot = a[-1]
    less = [x for x in a[:-1] if x <= pivot]
    greater = [x for x in a[:-1] if x > pivot]
    return main(less) + [pivot] + main(greater)
''',
    ),
    Case(
        key="quick_sort_in_place",
        time="n**2",
        best="n*log2(n)",
        average="n*log2(n)",
        space="n",
        note="Lomuto partition around a pivot index, recursing on both sides",
        source='''\
def main(a, lo=0, hi=None):
    if hi is None:
        hi = len(a) - 1
    if lo >= hi:
        return a
    pivot = a[hi]
    i = lo
    for j in range(lo, hi):
        if a[j] <= pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]
    main(a, lo, i - 1)
    main(a, i + 1, hi)
    return a
''',
    ),
    # ------------------------------------------------------- conservative tier
    Case(
        key="sieve_of_eratosthenes",
        time="n*log2(log2(n))",
        tier="conservative",
        expect="n*log2(n)",
        space="n",
        note="the true bound is O(n log log n) - the sum only runs over primes. "
             "The analyzer sees a strided harmonic sweep and reports the next "
             "class up, O(n log n), at confidence < 0.5. Guessing the finer "
             "class from an `if` guard would risk under-estimating, so it "
             "deliberately stays conservative.",
        source='''\
def main(n):
    sieve = bytearray([1]) * (n + 1)
    i = 2
    while i * i <= n:
        if sieve[i]:
            for j in range(i * i, n + 1, i):
                sieve[j] = 0
        i += 1
    return sieve
''',
    ),
    Case(
        key="bfs",
        time="V + E",
        tier="conservative",
        expect="n**2",
        space="n",
        note="adjacency-list BFS is O(V+E); the analyzer cannot see the edge "
             "count, so it assumes the dense case O(V^2), which is a valid "
             "upper bound.",
        source='''\
from collections import deque


def main(graph, start):
    seen = {start}
    queue = deque([start])
    while queue:
        v = queue.popleft()
        for nb in graph[v]:
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return seen
''',
    ),
    # ------------------------------------------------------------- known limit
    Case(
        key="counting_sort",
        time="n + k",
        tier="limit",
        expect="n**2",
        space="n",
        note="the inner loop runs counts[v] times, and the sum of the counter "
             "array is n - a data-dependent bound no AST walk can recover. The "
             "analyzer falls back to the O(n^2) worst case for the nest.",
        source='''\
def main(a, k):
    counts = [0] * (k + 1)
    for x in a:
        counts[x] += 1
    out = []
    for v in range(k + 1):
        for _ in range(counts[v]):
            out.append(v)
    return out
''',
    ),
)


# --------------------------------------------------------------------------- #
# Holdout set
# --------------------------------------------------------------------------- #
# Cases that were written *after* the analyzer rules were settled: they are
# the generalization check, not the spec. Each carries the ground truth plus
# the class the analyzer returns today. The tests pin that output (so a
# regression fails) and assert the property that matters most: the analyzer
# never answers *below* the truth, even when it cannot name the exact class.

HOLDOUT: tuple[Case, ...] = (
    Case(
        key="count_inversions",
        time="n*log2(n)",
        note="merge sort with a counting step",
        source='''\
def main(a):
    def sort_count(xs):
        if len(xs) <= 1:
            return xs, 0
        mid = len(xs) // 2
        left, a_inv = sort_count(xs[:mid])
        right, b_inv = sort_count(xs[mid:])
        out, i, j, inv = [], 0, 0, a_inv + b_inv
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                out.append(left[i])
                i += 1
            else:
                out.append(right[j])
                j += 1
                inv += len(left) - i
        out.extend(left[i:])
        out.extend(right[j:])
        return out, inv

    return sort_count(a)[1]
''',
    ),
    Case(
        key="shell_sort",
        time="n**2",
        tier="holdout",
        expect="n**2*log2(n)",
        note="the gap loop halves, so the analyzer multiplies the quadratic "
             "body by log n. Shell sort's real worst case is O(n^2) for this "
             "gap sequence: the estimate is one log factor loose, i.e. a valid "
             "upper bound that is not tight.",
        source='''\
def main(a):
    n = len(a)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = a[i]
            j = i
            while j >= gap and a[j - gap] > temp:
                a[j] = a[j - gap]
                j -= gap
            a[j] = temp
        gap //= 2
    return a
''',
    ),
    Case(
        key="kmp_search",
        time="n",
        note="linear scan with a failure table",
        source='''\
def main(text, pattern):
    def build_lps(p):
        lps = [0] * len(p)
        length = 0
        i = 1
        while i < len(p):
            if p[i] == p[length]:
                length += 1
                lps[i] = length
                i += 1
            elif length:
                length = lps[length - 1]
            else:
                lps[i] = 0
                i += 1
        return lps

    lps = build_lps(pattern)
    i = j = 0
    hits = 0
    while i < len(text):
        if text[i] == pattern[j]:
            i += 1
            j += 1
            if j == len(pattern):
                hits += 1
                j = lps[j - 1]
        elif j:
            j = lps[j - 1]
        else:
            i += 1
    return hits
''',
    ),
    Case(
        key="edit_distance_dp",
        time="n**2",
        note="n x m table filled once (m == n here)",
        source='''\
def main(a, b):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            else:
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1,
                               dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    return dp[n][m]
''',
    ),
    Case(
        key="knapsack_01_dp",
        time="n**2",
        note="n items x n capacity cells (capacity ~ n here)",
        source='''\
def main(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i - 1][w],
                               dp[i - 1][w - weights[i - 1]] + values[i - 1])
            else:
                dp[i][w] = dp[i - 1][w]
    return dp[n][capacity]
''',
    ),
    Case(
        key="reverse_in_place",
        time="n",
        note="two indices converge after n/2 swaps",
        source='''\
def main(a):
    i, j = 0, len(a) - 1
    while i < j:
        a[i], a[j] = a[j], a[i]
        i += 1
        j -= 1
    return a
''',
    ),
    Case(
        key="heap_select_top_k",
        time="n*log2(n)",
        note="n heap operations, each O(log k)",
        source='''\
import heapq


def main(a, k):
    heap = []
    for x in a:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:
            heapq.heapreplace(heap, x)
    return heap
''',
    ),
    Case(
        key="recursive_flatten",
        time="n",
        note="every element is visited exactly once - a descent, not an "
             "enumeration, so it must not be reported as O(n!)",
        source='''\
def main(items):
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(main(item))
        else:
            out.append(item)
    return out
''',
    ),
    Case(
        key="rabin_karp",
        time="n",
        note="one rolling-hash pass over the text",
        source='''\
def main(text, pattern):
    n, m = len(text), len(pattern)
    base, mod = 256, 10 ** 9 + 7
    target = 0
    for ch in pattern:
        target = (target * base + ord(ch)) % mod
    window = 0
    hits = 0
    for i in range(n):
        window = (window * base + ord(text[i])) % mod
        if i >= m:
            window = (window - ord(text[i - m]) * pow(base, m, mod)) % mod
        if i >= m - 1 and window == target:
            if text[i - m + 1:i + 1] == pattern:
                hits += 1
    return hits
''',
    ),
    Case(
        key="interpolation_search",
        time="log2(n)",
        note="interpolates the probe position; O(log n) on uniform data",
        source='''\
def main(a, target):
    lo, hi = 0, len(a) - 1
    while lo <= hi and a[lo] <= target <= a[hi]:
        if a[hi] == a[lo]:
            break
        pos = lo + ((target - a[lo]) * (hi - lo)) // (a[hi] - a[lo])
        if a[pos] == target:
            return pos
        if a[pos] < target:
            lo = pos + 1
        else:
            hi = pos - 1
    return -1
''',
    ),
    Case(
        key="binary_gcd",
        time="log2(n)*log2(n)",
        tier="holdout",
        expect="n*log2(n)",
        note="Stein's algorithm is O(log^2 n) bit operations. The analyzer "
             "sees a nested shift loop inside the subtraction loop and "
             "reports O(n log n): a loose upper bound, flagged at confidence "
             "< 0.5, rather than a guess at the tighter class.",
        source='''\
def main(a, b):
    if a == 0:
        return b
    if b == 0:
        return a
    shift = 0
    while ((a | b) & 1) == 0:
        a >>= 1
        b >>= 1
        shift += 1
    while (a & 1) == 0:
        a >>= 1
    while b:
        while (b & 1) == 0:
            b >>= 1
        if a > b:
            a, b = b, a
        b = b - a
    return a << shift
''',
    ),
    Case(
        key="towers_of_hanoi",
        time="2**n",
        note="two recursive calls per disk, no halving of the problem",
        source='''\
def main(n):
    moves = []

    def move(k, src, dst, aux):
        if k == 0:
            return
        move(k - 1, src, aux, dst)
        moves.append((src, dst))
        move(k - 1, aux, dst, src)

    move(n, "A", "C", "B")
    return moves
''',
    ),
    Case(
        key="matrix_chain_dp",
        time="n**3",
        note="chain length x start x split point",
        source='''\
def main(dims):
    n = len(dims) - 1
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = min(dp[i][k] + dp[k + 1][j]
                           + dims[i] * dims[k + 1] * dims[j + 1]
                           for k in range(i, j))
    return dp[0][n - 1]
''',
    ),
    Case(
        key="boyer_moore_vote",
        time="n",
        note="single pass with constant work per element",
        source='''\
def main(a):
    candidate = None
    count = 0
    for x in a:
        if count == 0:
            candidate = x
        count += (1 if x == candidate else -1)
    return candidate
''',
    ),
    Case(
        key="segment_tree_build",
        time="n",
        note="a doubling loop to size the array, then two linear passes - the "
             "linear work dominates the O(log n) sizing loop",
        source='''\
def main(data):
    size = 1
    while size < len(data):
        size *= 2
    tree = [0] * (2 * size)
    for i, value in enumerate(data):
        tree[size + i] = value
    for i in range(size - 1, 0, -1):
        tree[i] = tree[2 * i] + tree[2 * i + 1]
    return tree
''',
    ),
)


# --------------------------------------------------------------------------- #
# Grading
# --------------------------------------------------------------------------- #

@dataclass
class Result:
    """One graded corpus entry."""

    case: Case
    got_time: str
    got_best: str
    got_average: str
    got_space: str
    confidence: float
    estimate: object = field(default=None, repr=False)

    @property
    def time_ok(self) -> bool:
        return self.got_time == self.case.expected

    @property
    def best_ok(self) -> bool:
        return self.case.best is None or self.got_best == self.case.best

    @property
    def average_ok(self) -> bool:
        return self.case.average is None or self.got_average == self.case.average

    @property
    def space_ok(self) -> bool:
        return self.case.space is None or self.got_space == self.case.space

    @property
    def ok(self) -> bool:
        return self.time_ok and self.best_ok and self.average_ok and self.space_ok


def grade(cases: tuple[Case, ...] = CASES) -> list[Result]:
    """Run the estimator over every corpus entry."""
    from algocomp.static_analysis import analyze_source

    out = []
    for case in cases:
        est = analyze_source(case.source)
        out.append(Result(
            case=case,
            got_time=est.time_worst,
            got_best=est.time_best,
            got_average=est.time_average,
            got_space=est.space,
            confidence=est.confidence,
            estimate=est,
        ))
    return out


def label(expr: str) -> str:
    """Big-O label for a growth expression."""
    from algocomp.complexity import Complexity

    return Complexity(expr).resolved_label


def summarize(results: list[Result] | None = None) -> dict:
    """Counts per tier plus the list of misses."""
    results = results if results is not None else grade()
    exact = [r for r in results if r.case.is_exact]
    return {
        "total": len(results),
        "exact_total": len(exact),
        "exact_pass": sum(1 for r in exact if r.ok),
        "conservative": sum(1 for r in results if r.case.tier == "conservative"
                            and r.time_ok),
        "limits": sum(1 for r in results if r.case.tier == "limit" and r.time_ok),
        "misses": [r for r in results if not r.ok],
        "results": results,
    }


def holdout_summary(results: list[Result] | None = None) -> dict:
    """How the estimator does on cases it was not tuned against."""
    from algocomp.complexity import Complexity

    results = results if results is not None else grade(HOLDOUT)
    under = [r for r in results
             if Complexity(r.got_time).rank < Complexity(r.case.time).rank]
    return {
        "total": len(results),
        "exact": sum(1 for r in results if r.got_time == r.case.time),
        "pinned": sum(1 for r in results if r.time_ok),
        "under_estimates": under,
        "results": results,
    }


def main() -> int:
    """Print the accuracy tables; return 0 when every entry matches."""
    from algocomp.static_analysis import expr_label

    def table(title, results):
        print("\n== %s ==" % title)
        print("%-26s %-14s %-14s %-10s %-5s %s" % (
            "case", "truth", "estimate", "space", "conf", "verdict"))
        print("-" * 100)
        for r in results:
            tier = "" if r.case.is_exact else r.case.tier
            print("%-26s %-14s %-14s %-10s %-5.2f %s" % (
                r.case.key, label(r.case.time), expr_label(r.got_time),
                expr_label(r.got_space), r.confidence,
                "ok" if r.ok else "MISS" + (" (%s)" % tier if tier else "")))

    report = summarize()
    table("spec corpus (the gate)", report["results"])
    hold = holdout_summary()
    table("holdout (generalization, not tuned against)", hold["results"])
    print("-" * 100)
    print("exact tier      : %d/%d  (must be perfect)"
          % (report["exact_pass"], report["exact_total"]))
    print("conservative    : %d  (documented upper bounds, not exact)"
          % report["conservative"])
    print("known limits    : %d  (documented fallbacks)" % report["limits"])
    print("holdout         : %d/%d exact, %d/%d pinned, %d under-estimates"
          % (hold["exact"], hold["total"], hold["pinned"], hold["total"],
             len(hold["under_estimates"])))
    for r in report["misses"]:
        print("\nMISS %s\n  expected %s / best %s / average %s / space %s\n"
              "  got      %s / best %s / average %s / space %s\n  %s"
              % (r.case.key,
                 label(r.case.time), r.case.best, r.case.average, r.case.space,
                 r.got_time, r.got_best, r.got_average, r.got_space, r.case.note))
    return 0 if not report["misses"] and not hold["under_estimates"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
