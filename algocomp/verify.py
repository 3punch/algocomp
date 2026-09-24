"""Optional empirical check: do the declared Big-O bounds match reality?

This module is *not* the core of the system (the core is the theoretical
comparator) — it exists so you can validate the catalogue, or your own declared
complexities, against measured growth.

It measures wall-clock time for growing input sizes, fits

    log T(n) = alpha + beta * log n      ->  T(n) ~ n^beta

and compares the fitted exponent `beta` with the exponent of the declared
complexity. Agreement within ~0.25 means the declared bound is consistent with
observation.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Callable, Sequence

from .algorithm import Algorithm
from .complexity import Complexity
from .registry import Registry, default_registry

# --------------------------------------------------------------------------- #
# Benchmark implementations (pure Python, stdlib only)
# --------------------------------------------------------------------------- #

BenchFn = Callable[[int, random.Random], None]


def _sorted_ints(n: int, rng: random.Random) -> list[int]:
    return sorted(rng.randrange(10 * n + 1) for _ in range(n))


def _random_ints(n: int, rng: random.Random) -> list[int]:
    return [rng.randrange(10 * n + 1) for _ in range(n)]


# ---- sorting ------------------------------------------------------------- #

def _bubble(a: list[int]) -> None:
    n = len(a)
    for i in range(n):
        swapped = False
        for j in range(n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break


def _selection(a: list[int]) -> None:
    n = len(a)
    for i in range(n):
        m = i
        for j in range(i + 1, n):
            if a[j] < a[m]:
                m = j
        a[i], a[m] = a[m], a[i]


def _insertion(a: list[int]) -> None:
    for i in range(1, len(a)):
        k = a[i]
        j = i - 1
        while j >= 0 and a[j] > k:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = k


def _merge(a: list[int]) -> None:
    if len(a) < 2:
        return
    mid = len(a) // 2
    left, right = a[:mid], a[mid:]
    _merge(left)
    _merge(right)
    i = j = k = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            a[k] = left[i]; i += 1
        else:
            a[k] = right[j]; j += 1
        k += 1
    while i < len(left):
        a[k] = left[i]; i += 1; k += 1
    while j < len(right):
        a[k] = right[j]; j += 1; k += 1


def _quick(a: list[int], lo: int = 0, hi: int | None = None) -> None:
    """Iterative randomised quicksort (avoids recursion limits)."""
    if hi is None:
        hi = len(a) - 1
    stack = [(lo, hi)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        p = random.randrange(lo, hi + 1)
        a[p], a[hi] = a[hi], a[p]
        pivot = a[hi]
        i = lo
        for j in range(lo, hi):
            if a[j] < pivot:
                a[i], a[j] = a[j], a[i]
                i += 1
        a[i], a[hi] = a[hi], a[i]
        stack.append((lo, i - 1))
        stack.append((i + 1, hi))


def _heap(a: list[int]) -> None:
    n = len(a)

    def sift(start: int, end: int) -> None:
        root = start
        while True:
            child = 2 * root + 1
            if child > end:
                return
            if child + 1 <= end and a[child] < a[child + 1]:
                child += 1
            if a[root] < a[child]:
                a[root], a[child] = a[child], a[root]
                root = child
            else:
                return

    for start in range(n // 2 - 1, -1, -1):
        sift(start, n - 1)
    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        sift(0, end - 1)


# ---- searching ----------------------------------------------------------- #

def _linear(a: list[int], target: int) -> int:
    for i, v in enumerate(a):
        if v == target:
            return i
    return -1


def _binary(a: list[int], target: int) -> int:
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


# ---- graph --------------------------------------------------------------- #

def _grid_graph(n: int) -> dict[int, list[int]]:
    """A sqrt(n) x sqrt(n) grid: V ≈ n, E ≈ 2n."""
    side = max(2, int(math.isqrt(n)))
    g: dict[int, list[int]] = {}
    for r in range(side):
        for c in range(side):
            v = r * side + c
            g[v] = []
            if c + 1 < side:
                g[v].append(v + 1)
                g[v + 1].append(v)
            if r + 1 < side:
                g[v].append(v + side)
                g[v + side].append(v)
    return g


def _bfs(g: dict[int, list[int]], src: int) -> dict[int, int]:
    from collections import deque

    dist = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        for w in g[u]:
            if w not in dist:
                dist[w] = dist[u] + 1
                q.append(w)
    return dist


def _dfs(g: dict[int, list[int]], src: int) -> set[int]:
    seen = {src}
    stack = [src]
    while stack:
        u = stack.pop()
        for w in g[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return seen


def _dijkstra(g: dict[int, list[int]], src: int) -> dict[int, int]:
    import heapq

    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        for w in g[u]:
            nd = d + 1
            if nd < dist.get(w, math.inf):
                dist[w] = nd
                heapq.heappush(pq, (nd, w))
    return dist


def _bellman(g: dict[int, list[int]], src: int) -> dict[int, int]:
    dist = {v: math.inf for v in g}
    dist[src] = 0
    edges = [(u, w) for u in g for w in g[u]]
    for _ in range(len(g) - 1):
        changed = False
        for u, w in edges:
            if dist[u] + 1 < dist[w]:
                dist[w] = dist[u] + 1
                changed = True
        if not changed:
            break
    return dist


def _union_find_ops(n: int, rng: random.Random) -> None:
    parent = list(range(n))
    rank = [0] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _ in range(n):
        a, b = rng.randrange(n), rng.randrange(n)
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1


# ---- strings / numbers --------------------------------------------------- #

def _gcd_euclid(n: int, rng: random.Random) -> None:
    from math import gcd

    for _ in range(n):
        gcd(rng.randrange(10**9), rng.randrange(10**9))


def _naive_match(n: int, rng: random.Random) -> None:
    text = "a" * (n - 3) + "b"
    pat = "aaab"
    m = len(pat)
    for i in range(len(text) - m + 1):
        j = 0
        while j < m and text[i + j] == pat[j]:
            j += 1


def _kmp(n: int, rng: random.Random) -> None:
    text = "a" * (n - 3) + "b"
    pat = "aaab"
    fail = [0] * len(pat)
    k = 0
    for i in range(1, len(pat)):
        while k and pat[k] != pat[i]:
            k = fail[k - 1]
        if pat[k] == pat[i]:
            k += 1
        fail[i] = k
    k = 0
    for ch in text:
        while k and pat[k] != ch:
            k = fail[k - 1]
        if pat[k] == ch:
            k += 1
        if k == len(pat):
            k = fail[k - 1]


def _fib_naive(n: int, rng: random.Random) -> int:
    def f(k: int) -> int:
        return k if k < 2 else f(k - 1) + f(k - 2)

    return f(min(n, 24))


def _fib_memo(n: int, rng: random.Random) -> int:
    import sys

    sys.setrecursionlimit(max(10000, n * 3))
    memo: dict[int, int] = {0: 0, 1: 1}

    def f(k: int) -> int:
        if k not in memo:
            memo[k] = f(k - 1) + f(k - 2)
        return memo[k]

    return f(min(n, 3000))


def _fib_fast_doubling(n: int, rng: random.Random) -> int:
    def f(k: int) -> tuple[int, int]:
        if k == 0:
            return (0, 1)
        a, b = f(k >> 1)
        c = a * (2 * b - a)
        d = a * a + b * b
        return (c, d) if k & 1 == 0 else (d, c + d)

    return f(min(n, 100000))[0]


# --------------------------------------------------------------------------- #
# Registry of benchmarks
# --------------------------------------------------------------------------- #

#: key -> (prepare(n, rng) -> work(), label)
BENCHMARKS: dict[str, tuple[Callable[[int, random.Random], Callable[[], None]], str]] = {}


def _bench(key: str, label: str):
    def deco(fn):
        BENCHMARKS[key] = (fn, label)
        return fn

    return deco


@_bench("bubble_sort", "sort n random ints")
def _b_bubble(n, rng):
    a = _random_ints(n, rng)
    return lambda: _bubble(list(a))


@_bench("selection_sort", "sort n random ints")
def _b_selection(n, rng):
    a = _random_ints(n, rng)
    return lambda: _selection(list(a))


@_bench("insertion_sort", "sort n random ints")
def _b_insertion(n, rng):
    a = _random_ints(n, rng)
    return lambda: _insertion(list(a))


@_bench("merge_sort", "sort n random ints")
def _b_merge(n, rng):
    a = _random_ints(n, rng)
    return lambda: _merge(list(a))


@_bench("quick_sort", "sort n random ints")
def _b_quick(n, rng):
    a = _random_ints(n, rng)
    return lambda: _quick(list(a))


@_bench("heap_sort", "sort n random ints")
def _b_heap(n, rng):
    a = _random_ints(n, rng)
    return lambda: _heap(list(a))


@_bench("timsort", "sort n random ints (built-in)")
def _b_timsort(n, rng):
    a = _random_ints(n, rng)
    return lambda: sorted(a)


@_bench("linear_search", "find a key in n random ints")
def _b_linear(n, rng):
    a = _random_ints(n, rng)
    target = a[-1]
    return lambda: _linear(a, target)


@_bench("binary_search", "find a key in n sorted ints")
def _b_binary(n, rng):
    a = _sorted_ints(n, rng)
    target = a[-1]
    return lambda: _binary(a, target)


@_bench("bfs", "traverse a grid graph with V≈n")
def _b_bfs(n, rng):
    g = _grid_graph(n)
    return lambda: _bfs(g, 0)


@_bench("dfs", "traverse a grid graph with V≈n")
def _b_dfs(n, rng):
    g = _grid_graph(n)
    return lambda: _dfs(g, 0)


@_bench("dijkstra_binary_heap", "SSSP on a grid graph with V≈n")
def _b_dijkstra(n, rng):
    g = _grid_graph(n)
    return lambda: _dijkstra(g, 0)


@_bench("bellman_ford", "SSSP on a grid graph with V≈n")
def _b_bellman(n, rng):
    g = _grid_graph(n)
    return lambda: _bellman(g, 0)


@_bench("union_find_path_compression_union_by_rank", "n random union ops")
def _b_uf(n, rng):
    return lambda: _union_find_ops(n, random.Random(1234))


@_bench("euclidean_gcd", "n gcd computations on 30-bit ints")
def _b_gcd(n, rng):
    return lambda: _gcd_euclid(n, random.Random(7))


@_bench("naive_string_matching", "search 'aaab' in a^n b (worst case)")
def _b_naive(n, rng):
    return lambda: _naive_match(max(8, n), rng)


@_bench("knuth_morris_pratt", "search 'aaab' in a^n b (worst case)")
def _b_kmp(n, rng):
    return lambda: _kmp(max(8, n), rng)


@_bench("fibonacci_naive_recursion", "naive recursive fib(min(n,24))")
def _b_fib_naive(n, rng):
    return lambda: _fib_naive(n, rng)


@_bench("fibonacci_memoisation_bottom_up", "memoised fib(min(n,3000))")
def _b_fib_memo(n, rng):
    return lambda: _fib_memo(n, rng)


@_bench("sieve_of_eratosthenes", "sieve primes up to n")
def _b_sieve(n, rng):
    def work():
        N = max(4, n)
        sieve = bytearray([1]) * N
        sieve[0:2] = b"\x00\x00"
        for i in range(2, int(N ** 0.5) + 1):
            if sieve[i]:
                sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
        return sum(sieve)

    return work


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #


@dataclass
class Measurement:
    n: int
    seconds: float
    repeats: int


@dataclass
class FitResult:
    exponent: float
    r_squared: float
    measurements: list[Measurement]

    @property
    def ok(self) -> bool:
        return self.r_squared > 0.85


def measure(work: Callable[[], None], *, min_time: float = 0.02,
            max_time: float = 2.0, max_repeats: int = 2000) -> float:
    """Return best-of seconds for one call, auto-calibrating the repeat count."""
    work()  # warm up (JIT-free, but primes caches / imports)
    t0 = time.perf_counter()
    work()
    single = time.perf_counter() - t0
    if single >= min_time:
        return single
    reps = max(2, min(max_repeats, int(min_time / max(single, 1e-9))))
    best = math.inf
    deadline = time.perf_counter() + max_time
    while time.perf_counter() < deadline:
        t0 = time.perf_counter()
        for _ in range(reps):
            work()
        dt = (time.perf_counter() - t0) / reps
        best = min(best, dt)
        if dt > min_time * 4:
            break
        reps = min(max_repeats, reps * 4)
    return best


def fit_exponent(measurements: Sequence[Measurement]) -> FitResult:
    pts = [(math.log(m.n), math.log(m.seconds)) for m in measurements
           if m.n > 0 and m.seconds > 0]
    if len(pts) < 2:
        return FitResult(float("nan"), float("nan"), list(measurements))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    k = len(pts)
    mx = sum(xs) / k
    my = sum(ys) / k
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return FitResult(float("nan"), float("nan"), list(measurements))
    beta = sxy / sxx
    alpha = my - beta * mx
    ss_res = sum((y - (alpha + beta * x)) ** 2 for x, y in pts)
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return FitResult(beta, r2, list(measurements))



@dataclass
class VerificationReport:
    algorithm: Algorithm
    declared: Complexity
    fit: FitResult
    workload: str
    verdict: str
    agreement: float

    @property
    def consistent(self) -> bool:
        return abs(self.agreement) <= 0.35


def verify(algorithm: Algorithm, *, sizes: Sequence[int], registry: Registry | None = None,
           min_time: float = 0.01, budget: float = 0.4, seed: int = 20240924,
           progress: Callable[[str], None] | None = None) -> VerificationReport | None:
    """Benchmark `algorithm` and compare its measured growth with the declared bound.

    `budget` caps the wall-clock seconds spent on any single input size; sizes
    that would exceed it (or that fail to allocate) stop the sweep early, which
    keeps quadratic/exponential entries from hanging the tool.
    """
    entry = BENCHMARKS.get(algorithm.key)
    if entry is None:
        return None
    prepare, workload = entry
    rng = random.Random(seed)
    declared = algorithm.time.worst

    measurements: list[Measurement] = []
    stopped: str | None = None
    for n in sizes:
        n = int(n)
        if n < 2:
            continue
        try:
            work = prepare(n, rng)
        except (MemoryError, RecursionError, OverflowError):
            stopped = f"setup failed at n={n}"
            break
        if progress:
            progress(f"  n={n} ...")
        t0 = time.perf_counter()
        try:
            work()  # trial call: detect blow-ups before committing to repeats
        except (RecursionError, MemoryError):
            stopped = f"input size n={n} too large for this implementation"
            break
        trial = time.perf_counter() - t0
        if trial > budget:
            measurements.append(Measurement(n, trial, 1))
            stopped = f"budget {budget:g}s exceeded at n={n}"
            break
        try:
            secs = measure(work, min_time=min_time, max_time=budget)
        except (RecursionError, MemoryError):
            stopped = f"failed at n={n}"
            break
        measurements.append(Measurement(n, secs, 1))

    if stopped and progress:
        progress(f"  (stopped: {stopped})")
    if len(measurements) < 2:
        return None
    fit = fit_exponent(measurements)
    agreement = fit.exponent - declared.growth_exponent
    if math.isnan(agreement):
        verdict = "inconclusive"
    elif abs(agreement) <= 0.15:
        verdict = "matches"
    elif abs(agreement) <= 0.35:
        verdict = "roughly matches"
    elif agreement > 0:
        verdict = "measured worse than declared"
    else:
        verdict = "measured better than declared"
    return VerificationReport(algorithm, declared, fit, workload, verdict, agreement)


def available_benchmarks(registry: Registry | None = None) -> list[tuple[str, str]]:
    reg = registry or default_registry()
    out = []
    for key in sorted(BENCHMARKS):
        try:
            name = reg.get(key).name
        except LookupError:
            name = key
        out.append((key, name))
    return out


__all__ = ["verify", "measure", "fit_exponent", "VerificationReport", "FitResult",
           "Measurement", "BENCHMARKS", "available_benchmarks"]
