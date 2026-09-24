"""Built-in catalogue of algorithms with their theoretical complexity profiles.

Every entry declares best / average / worst-case **time** and **space**, so the
comparator can reason about the full picture rather than a single Big-O number.

Convention: `n` is the primary input size. Secondary parameters (k, V, E, W, d,
b, m) are documented in each entry's notes and used where the classic bound
depends on them (e.g. counting sort O(n+k), Dijkstra O(E + V log V)).
"""

from __future__ import annotations

from .algorithm import Algorithm

# Shorthands ---------------------------------------------------------------- #
_S = "sorting"
_SR = "search / retrieval"
_G = "graph"
_ST = "string"
_DP = "dynamic programming"
_NT = "number theory"
_LIN = "linear algebra"
_ML = "machine learning"
_OPT = "optimisation"
_CG = "computational geometry"
_CRY = "cryptography / hashing"
_DS = "data structure operations"
_CMP = "compression"
_DB = "database / systems"
_BT = "backtracking / puzzle"


def _a(*args, **kwargs) -> Algorithm:
    return Algorithm.build(*args, **kwargs)


# --------------------------------------------------------------------------- #
# 1. SORTING
# --------------------------------------------------------------------------- #

SORTING = [
    _a("Bubble Sort", category=_S, task="sort a list of comparable items",
       time_worst="n**2", time_average="n**2", time_best="n",
       space_worst="1", stable=True, in_place=True,
       notes="Best case O(n) only with an early-exit flag on an already sorted input. "
             "Terrible constant factor and cache behaviour; teaching example only."),
    _a("Selection Sort", category=_S, task="sort a list of comparable items",
       time_worst="n**2", time_average="n**2", time_best="n**2",
       space_worst="1", stable=False, in_place=True,
       notes="Input-order independent: always n(n-1)/2 comparisons. Minimises the number "
             "of swaps (at most n-1), so it can win when writing is expensive."),
    _a("Insertion Sort", category=_S, task="sort a list of comparable items",
       time_worst="n**2", time_average="n**2", time_best="n",
       space_worst="1", stable=True, in_place=True,
       notes="O(n+d) where d = number of inversions; excellent on nearly sorted or tiny "
             "arrays, which is why Timsort/introsort switch to it below a cutoff."),
    _a("Shell Sort", category=_S, task="sort a list of comparable items",
       time_worst="n**2", time_average="n*log2(n)**2", time_best="n",
       space_worst="1", stable=False, in_place=True,
       notes="Bound depends entirely on the gap sequence: Ciura gaps ≈ O(n^4/3) worst case, "
             "Pratt O(n log² n), Hibbard O(n^1.5). No general tight worst-case proof."),
    _a("Merge Sort", category=_S, task="sort a list of comparable items",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n", space_average="n", space_best="n", stable=True, in_place=False,
       notes="Guaranteed O(n log n) in every case; needs O(n) aux memory for arrays "
             "(O(log n) on linked lists). Excellent for external / streaming sort."),
    _a("Quick Sort", category=_S, task="sort a list of comparable items",
       time_worst="n**2", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n", space_average="log2(n)", space_best="log2(n)",
       stable=False, in_place=True,
       notes="Worst case O(n²) with a bad pivot (sorted input + first-element pivot); "
             "randomised or median-of-three pivots make it O(n log n) with high "
             "probability. Fastest general sort in practice: tiny constants, cache friendly."),
    _a("Heap Sort", category=_S, task="sort a list of comparable items",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="1", space_average="1", space_best="1", stable=False, in_place=True,
       notes="In-place with a guaranteed O(n log n) worst case, but ~2x slower than "
             "quicksort in practice due to poor cache locality."),
    _a("Introsort", category=_S, task="sort a list of comparable items",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n",
       space_worst="log2(n)", stable=False, in_place=True,
       notes="Quicksort + depth limit → heapsort fallback + insertion sort for small "
             "partitions. Used by the C++ STL; removes quicksort's O(n²) worst case."),
    _a("Timsort", category=_S, task="sort a list of comparable items",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n",
       space_worst="n", stable=True, in_place=False,
       notes="Adaptive merge sort exploiting existing runs. O(n) on already-sorted input. "
             "Default in Python (list.sort) and Java (Arrays.sort for objects)."),
    _a("Counting Sort", category=_S, task="sort integers from a bounded range",
       time_worst="n+k", time_average="n+k", time_best="n+k",
       space_worst="n+k", stable=True, in_place=False,
       notes="k = size of the value range. Linear only when k = O(n); otherwise the "
             "range dominates. Not a comparison sort — bypasses the Ω(n log n) bound."),
    _a("Bucket Sort", category=_S, task="sort uniformly distributed keys",
       time_worst="n**2", time_average="n+k", time_best="n",
       space_worst="n*k", stable=True, in_place=False,
       notes="k = number of buckets. Average O(n) assumes uniform distribution; "
             "degrades to O(n²) when all keys land in one bucket."),
    _a("Radix Sort (LSD, base b)", category=_S, task="sort fixed-length integer keys",
       time_worst="d*(n+k)", time_average="d*(n+k)", time_best="d*(n+k)",
       space_worst="n+k", stable=True, in_place=False,
       notes="d = number of digits/passes, k = base (bucket count). O(d·n) for constant "
             "d and k. Requires a stable inner sort, usually counting sort."),
    _a("Cycle Sort", category=_S, task="sort a list of comparable items",
       time_worst="n**2", time_average="n**2", time_best="n",
       space_worst="1", stable=False, in_place=True,
       notes="Provably optimal in the number of *writes* — useful for flash/EEPROM where "
             "writes are costly. Very slow otherwise."),
]

# --------------------------------------------------------------------------- #
# 2. SEARCHING / SELECTION
# --------------------------------------------------------------------------- #

SEARCHING = [
    _a("Linear Search", category=_SR, task="find a key in an unsorted array",
       time_worst="n", time_average="n", time_best="1",
       space_worst="1",
       notes="No preprocessing, works on unsorted data and on streams. Average n/2 probes."),
    _a("Binary Search", category=_SR, task="find a key in a sorted array",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1", space_average="log2(n)",
       notes="Requires sorted, random-access data. Iterative version is O(1) space; "
             "recursive is O(log n) stack. Cache-unfriendly on huge arrays (random jumps)."),
    _a("Jump Search", category=_SR, task="find a key in a sorted array",
       time_worst="sqrt(n)", time_average="sqrt(n)", time_best="1",
       space_worst="1",
       notes="Block jumps of √n then linear scan. Better than binary search on media "
             "where seeking backwards is expensive (tapes, some databases)."),
    _a("Interpolation Search", category=_SR, task="find a key in a sorted, uniformly distributed array",
       time_worst="n", time_average="log2(log2(n))", time_best="1",
       space_worst="1",
       notes="O(log log n) average on uniform data — better than binary search — but "
             "degrades to O(n) on skewed distributions."),
    _a("Exponential Search", category=_SR, task="find a key in a sorted array of unknown length",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1",
       notes="Doubling probe then binary search on the bracket; O(log i) where i is the "
             "target index — good for unbounded/lazy sequences."),
    _a("Fibonacci Search", category=_SR, task="find a key in a sorted array",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1",
       notes="Divides using Fibonacci numbers; only additions/subtractions, so historically "
             "useful when multiplication was slow. Same asymptotics as binary search."),
    _a("Ternary Search (unimodal)", category=_SR, task="find the extremum of a unimodal function",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1", space_average="log2(n)",
       notes="log₃ n iterations × 2 evaluations per iteration → more comparisons than "
             "binary search in practice despite a smaller iteration count."),
    _a("Hash Table Lookup", category=_SR, task="find a key by exact match",
       time_worst="n", time_average="1", time_best="1",
       space_worst="n",
       notes="O(1) expected; O(n) worst case when every key collides. Assume a good hash "
             "function and load factor < 1. Needs O(n) memory for the table."),
    _a("BFS on a tree/graph", category=_SR, task="find a node by value (unweighted)",
       time_worst="V+E", time_average="V+E", time_best="1",
       space_worst="V",
       notes="Finds the shallowest match first. Space is the frontier width — O(V) worst "
             "case, which is much worse than DFS on wide graphs."),
    _a("DFS on a tree/graph", category=_SR, task="find a node by value (unweighted)",
       time_worst="V+E", time_average="V+E", time_best="1",
       space_worst="V", space_average="log2(n)",
       notes="Space is the depth, so O(log n) on balanced trees — much cheaper than BFS "
             "there. No shortest-path guarantee."),
    _a("Quickselect", category=_SR, task="find the k-th smallest element",
       time_worst="n**2", time_average="n", time_best="n",
       space_worst="n", space_average="1",
       notes="Average O(n) — far better than sorting (O(n log n)) when you only need one "
             "order statistic. Worst case O(n²); use randomised pivots or median-of-medians."),
    _a("Median of Medians (BFPRT)", category=_SR, task="find the k-th smallest element",
       time_worst="n", time_average="n", time_best="n",
       space_worst="log2(n)",
       notes="Deterministic worst-case O(n) selection, but the hidden constant (~5.4n "
             "comparisons) makes it slower than quickselect in practice."),
    _a("Binary Search Tree Search", category=_SR, task="find a key in a BST",
       time_worst="n", time_average="log2(n)", time_best="1",
       space_worst="log2(n)",
       notes="Worst case O(n) on a degenerate (linked-list shaped) tree; O(log n) expected "
             "on random insertion order. Use a self-balancing tree to guarantee it."),
]

# --------------------------------------------------------------------------- #
# 3. GRAPH
# --------------------------------------------------------------------------- #

GRAPH = [
    _a("BFS", category=_G, task="traverse / shortest path in an unweighted graph",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="Optimal for unweighted single-source shortest paths: O(V+E)."),
    _a("DFS", category=_G, task="traverse a graph",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="O(V+E) with an adjacency list, O(V²) with an adjacency matrix. Foundation "
             "for topological sort, SCC and cycle detection."),
    _a("Dijkstra (binary heap)", category=_G, task="single-source shortest path, non-negative weights",
       time_worst="(V+E)*log2(V)", time_average="(V+E)*log2(V)", time_best="(V+E)*log2(V)",
       space_worst="V",
       notes="The standard choice. Cannot handle negative edge weights."),
    _a("Dijkstra (Fibonacci heap)", category=_G, task="single-source shortest path, non-negative weights",
       time_worst="E+V*log2(V)", time_average="E+V*log2(V)", time_best="E+V*log2(V)",
       space_worst="V",
       notes="Asymptotically better on dense graphs, but huge constants and poor cache "
             "behaviour — a binary heap or a d-ary heap is faster in reality."),
    _a("Bellman-Ford", category=_G, task="single-source shortest path, possibly negative weights",
       time_worst="V*E", time_average="V*E", time_best="V*E",
       space_worst="V",
       notes="O(VE) — much slower than Dijkstra, but the only simple SSSP algorithm that "
             "handles negative edges and detects negative cycles."),
    _a("SPFA (queue-based Bellman-Ford)", category=_G, task="single-source shortest path, possibly negative weights",
       time_worst="V*E", time_average="E", time_best="E",
       space_worst="V",
       notes="Fast in practice on sparse random graphs (≈O(E)) but retains the O(VE) worst "
             "case and is vulnerable to adversarial inputs."),
    _a("Floyd-Warshall", category=_G, task="all-pairs shortest paths",
       time_worst="V**3", time_average="V**3", time_best="V**3",
       space_worst="V**2",
       notes="Simplest APSP; handles negative edges (not negative cycles). Very good "
             "constant factor and trivially parallelisable."),
    _a("Johnson's Algorithm", category=_G, task="all-pairs shortest paths",
       time_worst="V*E*log2(V)", time_average="V*E*log2(V)", time_best="V*E*log2(V)",
       space_worst="V**2",
       notes="Bellman-Ford reweighting + Dijkstra from every vertex. Beats Floyd-Warshall "
             "on sparse graphs (E ≪ V²)."),
    _a("A* Search", category=_G, task="single-source shortest path with a heuristic",
       time_worst="2**n", time_average="n", time_best="1",
       space_worst="n",
       notes="Cost is governed by the heuristic: O(b^d) worst case, but O(d) with a "
             "perfect (exact) heuristic. Space (the open list) is usually the bottleneck."),
    _a("Bidirectional Dijkstra", category=_G, task="point-to-point shortest path, non-negative weights",
       time_worst="(V+E)*log2(V)", time_average="(V+E)*log2(V)", time_best="(V+E)*log2(V)",
       space_worst="V",
       notes="Same worst-case asymptotics as Dijkstra but searches two half-radius balls — "
             "typically ~2x fewer settled nodes for point-to-point queries."),
    _a("Kruskal (union-find)", category=_G, task="minimum spanning tree",
       time_worst="E*log2(E)", time_average="E*log2(E)", time_best="E*log2(E)",
       space_worst="V+E",
       notes="Dominated by sorting the edges. Best for sparse graphs and for streaming "
             "edge input."),
    _a("Prim (binary heap)", category=_G, task="minimum spanning tree",
       time_worst="(V+E)*log2(V)", time_average="(V+E)*log2(V)", time_best="(V+E)*log2(V)",
       space_worst="V+E",
       notes="Grows one tree from a start vertex; better than Kruskal on dense graphs "
             "(E ≈ V²) where the sort would dominate."),
    _a("Boruvka", category=_G, task="minimum spanning tree",
       time_worst="E*log2(V)", time_average="E*log2(V)", time_best="E*log2(V)",
       space_worst="V+E",
       notes="log V parallel phases, each finding the cheapest outgoing edge per component "
             "— the most parallel-friendly MST algorithm."),
    _a("Topological Sort (Kahn)", category=_G, task="topologically order a DAG",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="Iterative, detects cycles for free (leftover in-degree > 0 nodes)."),
    _a("Topological Sort (DFS)", category=_G, task="topologically order a DAG",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="Same asymptotics as Kahn; recursion depth is the practical limit."),
    _a("Tarjan SCC", category=_G, task="find strongly connected components",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="Single DFS pass, components emitted in reverse topological order."),
    _a("Kosaraju SCC", category=_G, task="find strongly connected components",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V+E",
       notes="Two DFS passes (needs the transpose graph). Easier to understand, same "
             "asymptotics as Tarjan but touches memory twice."),
    _a("Bridges & Articulation Points", category=_G, task="find cut edges / cut vertices",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="One DFS with discovery/low timestamps."),
    _a("Bipartite Check (2-colouring)", category=_G, task="test whether a graph is bipartite",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="BFS colouring; equivalent to detecting an odd cycle."),
    _a("Hierholzer (Eulerian path)", category=_G, task="find an Eulerian circuit",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V+E",
       notes="Linear, provided the degree conditions for existence are met."),
    _a("Hamiltonian Path (backtracking)", category=_G, task="find a Hamiltonian path",
       time_worst="factorial(n)", time_average="2**n", time_best="n",
       space_worst="n",
       notes="NP-complete. Held-Karp DP gives O(2^n · n²) — exponentially better than "
             "factorial but still intractable beyond n ≈ 25."),
    _a("Held-Karp (TSP exact DP)", category=_G, task="solve TSP exactly",
       time_worst="2**n*n**2", time_average="2**n*n**2", time_best="2**n*n**2",
       space_worst="2**n*n",
       notes="Beats brute force O(n!) but the O(2^n · n) memory is the real limit."),
    _a("Edmonds-Karp (max flow)", category=_G, task="maximum s-t flow",
       time_worst="V*E**2", time_average="V*E**2", time_best="V*E**2",
       space_worst="V+E",
       notes="Ford-Fulkerson with BFS augmenting paths; independent of capacities."),
    _a("Dinic (max flow)", category=_G, task="maximum s-t flow",
       time_worst="V**2*E", time_average="V**2*E", time_best="V**2*E",
       space_worst="V+E",
       notes="O(E√V) on unit-capacity networks (bipartite matching). Usually the "
             "practical default for max-flow."),
    _a("Push-Relabel (max flow)", category=_G, task="maximum s-t flow",
       time_worst="V**3", time_average="V**2*sqrt(E)", time_best="V**2*sqrt(E)",
       space_worst="V+E",
       notes="With gap + global relabel heuristics it is often the fastest in practice on "
             "dense graphs, despite the weaker theoretical bound."),
    _a("Hungarian Algorithm", category=_G, task="minimum-cost bipartite assignment",
       time_worst="V**3", time_average="V**3", time_best="V**3",
       space_worst="V**2",
       notes="Optimal O(n³) assignment. Auction / JV variants are faster in practice."),
    _a("Hopcroft-Karp", category=_G, task="maximum bipartite matching",
       time_worst="E*sqrt(V)", time_average="E*sqrt(V)", time_best="E*sqrt(V)",
       space_worst="V",
       notes="Improves on the O(VE) augmenting-path approach."),
    _a("Union-Find (path compression + union by rank)", category=_G, task="dynamic connectivity queries",
       time_worst="log2(n)", time_average="1", time_best="1",
       space_worst="n",
       notes="Strictly O(α(n)) — inverse Ackermann — which is < 5 for any conceivable n, "
             "so effectively constant. Naive union-find without the heuristics is O(n)."),
]

# --------------------------------------------------------------------------- #
# 4. STRINGS
# --------------------------------------------------------------------------- #

STRINGS = [
    _a("Naive String Matching", category=_ST, task="find a pattern of length m in a text of length n",
       time_worst="n*m", time_average="n", time_best="n",
       space_worst="1",
       notes="Worst case hits on repetitive text (e.g. pattern 'aaab' in 'aaaa...'). "
             "Average case is near-linear because mismatches occur early."),
    _a("Knuth-Morris-Pratt", category=_ST, task="find a pattern of length m in a text of length n",
       time_worst="n+m", time_average="n+m", time_best="n+m",
       space_worst="m",
       notes="Linear worst case; the O(m) failure-function build is amortised away. "
             "Poor cache behaviour from the table lookups."),
    _a("Rabin-Karp", category=_ST, task="find a pattern of length m in a text of length n",
       time_worst="n*m", time_average="n+m", time_best="n+m",
       space_worst="1",
       notes="Rolling hash; O((n+m)) expected, O(nm) on many hash collisions. Shines for "
             "multi-pattern search (match k patterns in O(nk) → O(n+k))."),
    _a("Boyer-Moore", category=_ST, task="find a pattern of length m in a text of length n",
       time_worst="n*m", time_average="n/m", time_best="1",
       space_worst="m",
       notes="Sublinear average case — skips whole blocks using bad-character/good-suffix "
             "shifts. Longer patterns are *faster*. Worst case needs the Galil rule fix."),
    _a("Z-Algorithm", category=_ST, task="find a pattern of length m in a text of length n",
       time_worst="n+m", time_average="n+m", time_best="n+m",
       space_worst="n+m",
       notes="Linear, simpler to implement correctly than KMP; also solves all "
             "occurrences / prefix-function style problems."),
    _a("Aho-Corasick", category=_ST, task="find k patterns simultaneously in a text of length n",
       time_worst="n+m+z", time_average="n+m+z", time_best="n+m+z",
       space_worst="m",
       notes="m = total pattern length, z = number of matches. One automaton pass over the "
             "text; the classic multi-pattern solution."),
    _a("Suffix Array (DC3 / SA-IS)", category=_ST, task="index a text for substring queries",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n",
       notes="SA-IS builds in O(n); naive prefix-doubling is O(n log n) but usually faster "
             "in practice. Queries then cost O(m log n) with binary search."),
    _a("Suffix Automaton", category=_ST, task="index a text for substring queries",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n",
       notes="At most 2n-1 states; answers O(m) substring queries and many counting "
             "problems in linear time."),
    _a("Backtracking Regex Matching", category=_ST, task="match a regular expression",
       time_worst="2**n", time_average="n", time_best="n",
       space_worst="n",
       notes="The source of catastrophic backtracking / ReDoS. Thompson NFA simulation is "
             "O(n·m) worst case and immune to it."),
    _a("Thompson NFA Simulation", category=_ST, task="match a regular expression",
       time_worst="n*m", time_average="n*m", time_best="n*m",
       space_worst="m",
       notes="n = text length, m = pattern size. No exponential blow-up; the basis of RE2."),
    _a("Hamming Distance (brute force)", category=_ST, task="count differing positions of equal-length strings",
       time_worst="n", time_average="n", time_best="n",
       space_worst="1",
       notes="Already optimal; SIMD/popcount implementations cut the constant drastically."),
    _a("LCS (dynamic programming)", category=_ST, task="longest common subsequence of two strings",
       time_worst="n*m", time_average="n*m", time_best="n*m",
       space_worst="n*m",
       notes="Space drops to O(min(n,m)) with Hirschberg/rolling rows if only the length is "
             "needed. Hirschberg recovers the alignment in O(nm) time and O(min(n,m)) space."),
]

# --------------------------------------------------------------------------- #
# 5. DYNAMIC PROGRAMMING
# --------------------------------------------------------------------------- #

DYNAMIC = [
    _a("Fibonacci (memoisation / bottom-up)", category=_DP, task="compute the n-th Fibonacci number",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n", space_average="1",
       notes="Space reduces to O(1) keeping only the last two values. Fast doubling gives "
             "O(log n) arithmetic steps (but numbers have O(n) bits, so bit complexity is higher)."),
    _a("Fibonacci (naive recursion)", category=_DP, task="compute the n-th Fibonacci number",
       time_worst="2**n", time_average="1.618**n", time_best="1.618**n",
       space_worst="n",
       notes="The canonical example of exponential blow-up from overlapping subproblems: "
             "Θ(φⁿ) ≈ Θ(1.618ⁿ) calls."),
    _a("Matrix Chain Multiplication", category=_DP, task="find the cheapest multiplication order",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Beats the O(2^n) / O(n!) brute-force enumeration of parenthesisations."),
    _a("0/1 Knapsack (DP)", category=_DP, task="0/1 knapsack",
       time_worst="n*W", time_average="n*W", time_best="n*W",
       space_worst="n*W", space_average="W",
       notes="W = capacity. Pseudo-polynomial: polynomial in the *value* of W, not its "
             "bit length, so knapsack remains NP-hard. FPTAS gives (1-ε) approximation "
             "in O(n²/ε)."),
    _a("Unbounded Knapsack (DP)", category=_DP, task="unbounded knapsack",
       time_worst="n*W", time_average="n*W", time_best="n*W",
       space_worst="W",
       notes="One-dimensional rolling array suffices."),
    _a("Subset Sum (DP)", category=_DP, task="decide whether a subset sums to a target",
       time_worst="n*T", time_average="n*T", time_best="n*T",
       space_worst="T",
       notes="T = target sum. Pseudo-polynomial; meet-in-the-middle gives O(2^(n/2)) which "
             "wins when T is astronomically large."),
    _a("Edit Distance (Levenshtein)", category=_DP, task="edit distance between two strings",
       time_worst="n*m", time_average="n*m", time_best="n*m",
       space_worst="n*m", space_average="m",
       notes="O(min(n,m)) space with two rolling rows. Ukkonen's banded version runs in "
             "O(d·min(n,m)) where d is the actual distance."),
    _a("Longest Increasing Subsequence (patience / binary search)", category=_DP, task="longest increasing subsequence",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Improves the O(n²) DP. Optimal for comparisons; O(n log log n) is possible "
             "with a van Emde Boas structure."),
    _a("Longest Increasing Subsequence (O(n²) DP)", category=_DP, task="longest increasing subsequence",
       time_worst="n**2", time_average="n**2", time_best="n**2",
       space_worst="n",
       notes="Simpler, fine for n ≤ a few thousand."),
    _a("Coin Change (min coins)", category=_DP, task="minimum number of coins for an amount",
       time_worst="n*A", time_average="n*A", time_best="n*A",
       space_worst="A",
       notes="n = number of denominations, A = amount. Pseudo-polynomial; greedy is O(n log n) "
             "but only correct for canonical coin systems."),
    _a("Rod Cutting", category=_DP, task="maximise revenue from cutting a rod",
       time_worst="n**2", time_average="n**2", time_best="n**2",
       space_worst="n",
       notes="Beats the O(2^n) naive recursion."),
    _a("Optimal BST", category=_DP, task="build a BST minimising expected search cost",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Knuth's optimisation (monotone opt split point) reduces it to O(n²)."),
    _a("Longest Palindromic Subsequence", category=_DP, task="longest palindromic subsequence",
       time_worst="n**2", time_average="n**2", time_best="n**2",
       space_worst="n**2", space_average="n",
       notes="Equivalent to LCS of the string and its reverse."),
    _a("Bitmask DP (subset enumeration)", category=_DP, task="optimise over all subsets",
       time_worst="2**n*n", time_average="2**n*n", time_best="2**n*n",
       space_worst="2**n",
       notes="Standard trick for n ≤ 20; the 2^n table is the memory limit."),
]

# --------------------------------------------------------------------------- #
# 6. NUMBER THEORY
# --------------------------------------------------------------------------- #

NUMTHEORY = [
    _a("Euclidean GCD", category=_NT, task="greatest common divisor of two integers",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1", space_average="log2(n)",
       notes="O(log min(a,b)) divisions; worst case is consecutive Fibonacci numbers. "
             "Recursive version costs O(log n) stack."),
    _a("Binary GCD (Stein)", category=_NT, task="greatest common divisor of two integers",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1",
       notes="Same asymptotics as Euclid but uses only shifts and subtraction — faster "
             "on hardware without a fast divider, and for big integers."),
    _a("Extended Euclid", category=_NT, task="gcd plus Bezout coefficients / modular inverse",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="1",
       notes="The workhorse behind modular inverses and the Chinese Remainder Theorem."),
    _a("Trial Division Factorisation", category=_NT, task="integer factorisation",
       time_worst="sqrt(n)", time_average="sqrt(n)", time_best="1",
       space_worst="1",
       notes="Fine for n up to ~10^12; hopeless for cryptographic sizes."),
    _a("Pollard's Rho", category=_NT, task="integer factorisation",
       time_worst="n**(1/4)", time_average="n**(1/4)", time_best="1",
       space_worst="1",
       notes="Expected O(p^(1/2)) where p is the smallest prime factor — sub-exponential "
             "in the number of digits. Brent's variant cuts the gcd count."),
    _a("Sieve of Eratosthenes", category=_NT, task="enumerate all primes up to N",
       time_worst="N*log2(log2(N))", time_average="N*log2(log2(N))", time_best="N*log2(log2(N))",
       space_worst="N",
       notes="The log log N factor comes from the harmonic sum over primes."),
    _a("Linear Sieve (Euler)", category=_NT, task="enumerate all primes up to N",
       time_worst="N", time_average="N", time_best="N",
       space_worst="N",
       notes="Each composite is crossed out exactly once → strictly O(N), plus you get the "
             "smallest prime factor table for free. Slightly worse constant than Eratosthenes "
             "in practice."),
    _a("Segmented Sieve", category=_NT, task="enumerate primes in a large range",
       time_worst="N*log2(log2(N))", time_average="N*log2(log2(N))", time_best="N*log2(log2(N))",
       space_worst="sqrt(N)",
       notes="Same time as Eratosthenes but O(√N) memory — the only way to sieve huge ranges."),
    _a("Miller-Rabin Primality Test", category=_NT, task="primality testing",
       time_worst="k*log2(n)**3", time_average="k*log2(n)**3", time_best="k*log2(n)**3",
       space_worst="log2(n)",
       notes="k rounds → error ≤ 4^-k. Deterministic for n < 3.3·10^24 with a fixed witness "
             "set. Cost assumes schoolbook modular multiplication; fast multiplication lowers it."),
    _a("AKS Primality Test", category=_NT, task="primality testing",
       time_worst="log2(n)**6", time_average="log2(n)**6", time_best="log2(n)**6",
       space_worst="log2(n)",
       notes="First *unconditionally* deterministic polynomial-time test, but the constants "
             "make it slower than Miller-Rabin for every practical input."),
    _a("Fast Modular Exponentiation", category=_NT, task="compute a^b mod m",
       time_worst="log2(b)*log2(m)**2", time_average="log2(b)*log2(m)**2", time_best="log2(b)*log2(m)**2",
       space_worst="1",
       notes="O(log b) modular multiplications — the difference between feasible and "
             "impossible for RSA-sized exponents."),
    _a("Karatsuba Multiplication", category=_NT, task="multiply two n-digit integers",
       time_worst="n**1.585", time_average="n**1.585", time_best="n**1.585",
       space_worst="n",
       notes="Beats schoolbook O(n²) from ~a few hundred digits up."),
    _a("FFT-based Multiplication (Schonhage-Strassen)", category=_NT, task="multiply two n-digit integers",
       time_worst="n*log2(n)*log2(log2(n))", time_average="n*log2(n)*log2(log2(n))", time_best="n*log2(n)*log2(log2(n))",
       space_worst="n",
       notes="Best known for decades; Harvey–van der Hoeven (2019) achieved the conjectured "
             "O(n log n) bound."),
]

# --------------------------------------------------------------------------- #
# 7. CRYPTOGRAPHY / HASHING
# --------------------------------------------------------------------------- #

CRYPTO = [
    _a("SHA-256", category=_CRY, task="hash an arbitrary-length message",
       time_worst="n", time_average="n", time_best="n",
       space_worst="1",
       notes="O(n/64) compression rounds; constant memory. Hardware acceleration (SHA-NI) "
             "changes the constant by an order of magnitude."),
    _a("HMAC", category=_CRY, task="keyed message authentication",
       time_worst="n", time_average="n", time_best="n",
       space_worst="1",
       notes="Two hash passes over the message plus key padding — same asymptotics as the "
             "underlying hash."),
    _a("AES Encryption (per block)", category=_CRY, task="encrypt data",
       time_worst="n", time_average="n", time_best="n",
       space_worst="1",
       notes="10/12/14 rounds per 16-byte block depending on key size → constant per block, "
             "linear overall. AES-NI makes it memory-bandwidth bound."),
    _a("RSA (modular exponentiation)", category=_CRY, task="asymmetric encrypt/sign",
       time_worst="k**3", time_average="k**3", time_best="k**3",
       space_worst="k",
       notes="k = key size in bits (2048–4096). Cubic from schoolbook modexp on big ints; "
             "asymmetric ops are ~1000x slower than AES — hence hybrid encryption."),
    _a("Diffie-Hellman Key Exchange", category=_CRY, task="establish a shared secret",
       time_worst="k**3", time_average="k**3", time_best="k**3",
       space_worst="k",
       notes="Same modexp cost profile as RSA; ECDH reduces it to O(k²) with much smaller keys."),
    _a("Elliptic Curve Scalar Multiplication", category=_CRY, task="EC point multiplication",
       time_worst="k**2", time_average="k**2", time_best="k**2",
       space_worst="k",
       notes="k = field size in bits. Double-and-add over 256-bit curves gives 128-bit "
             "security — far cheaper than the 3072-bit RSA equivalent."),
    _a("PBKDF2", category=_CRY, task="derive a key from a password",
       time_worst="c*n", time_average="c*n", time_best="c*n",
       space_worst="n",
       notes="c = iteration count (deliberately huge). Slowness is a *feature* here; it is "
             "still fast on GPUs, hence Argon2/scrypt."),
    _a("Argon2id", category=_CRY, task="derive a key from a password",
       time_worst="c*m", time_average="c*m", time_best="c*m",
       space_worst="m",
       notes="m = memory in KiB (memory-hard by design), c = passes. Resists ASIC/GPU "
             "attacks precisely because of the O(m) memory requirement."),
    _a("Open Addressing Hash Table (linear probing)", category=_CRY, task="insert / lookup with O(1) expected cost",
       time_worst="n", time_average="1/(1-a)**2", time_best="1",
       space_worst="n",
       notes="a = load factor. Expected successful probe ≈ ½(1 + 1/(1-a)); the asymptotic "
             "blow-up as a→1 is why tables resize at ~70-80% load."),
    _a("Separate Chaining Hash Table", category=_CRY, task="insert / lookup with O(1) expected cost",
       time_worst="n", time_average="1+a", time_best="1",
       space_worst="n+a",
       notes="a = load factor (may exceed 1). More tolerant of high load factors and of a "
             "poor hash function than open addressing, but pointer-chasing hurts cache."),
]

# --------------------------------------------------------------------------- #
# 8. DATA STRUCTURE OPERATIONS
# --------------------------------------------------------------------------- #

STRUCTURES = [
    _a("Dynamic Array (amortised)", category=_DS, task="append / index / search operations",
       time_worst="n", time_average="1", time_best="1",
       space_worst="n",
       notes="Amortised O(1) append; a single push can cost O(n) during a resize. O(1) "
             "random access, O(n) search, O(n) insert in the middle."),
    _a("Singly Linked List", category=_DS, task="insert / delete / search operations",
       time_worst="n", time_average="n", time_best="1",
       space_worst="n",
       notes="O(1) insert/delete *given a pointer to the node*; O(n) to find it. Terrible "
             "cache locality versus an array."),
    _a("Doubly Linked List", category=_DS, task="insert / delete / search operations",
       time_worst="n", time_average="n", time_best="1",
       space_worst="n",
       notes="Adds O(1) deletion of a known node and backwards traversal at the cost of "
             "one extra pointer per node."),
    _a("Binary Heap", category=_DS, task="priority queue operations",
       time_worst="log2(n)", time_average="log2(n)", time_best="1",
       space_worst="n",
       notes="O(1) peek, O(log n) push/pop, O(n) build (heapify). Cache-friendlier than "
             "balanced trees because it is an array."),
    _a("AVL Tree", category=_DS, task="ordered map operations",
       time_worst="log2(n)", time_average="log2(n)", time_best="log2(n)",
       space_worst="n",
       notes="Strictly balanced (height ≤ 1.44 log n) → faster lookups than red-black, "
             "slightly more rebalancing on writes. Read-heavy workloads prefer AVL."),
    _a("Red-Black Tree", category=_DS, task="ordered map operations",
       time_worst="log2(n)", time_average="log2(n)", time_best="log2(n)",
       space_worst="n",
       notes="Looser balance (height ≤ 2 log n) → at most 2 rotations per insert, 3 per "
             "delete. Write-heavy workloads prefer red-black (std::map, Java TreeMap)."),
    _a("Splay Tree", category=_DS, task="ordered map operations",
       time_worst="n", time_average="log2(n)", time_best="1",
       space_worst="n",
       notes="Amortised O(log n); self-adjusting so recently accessed items are fast. "
             "Individual operations can be O(n)."),
    _a("B-Tree / B+ Tree", category=_DS, task="disk-backed ordered index operations",
       time_worst="log2(n)", time_average="log2(n)", time_best="log2(n)",
       space_worst="n",
       notes="High fan-out (hundreds of children) shrinks the height to 3-4 for billions "
             "of keys — minimising disk seeks, which is what actually matters here."),
    _a("Skip List", category=_DS, task="ordered map operations",
       time_worst="n", time_average="log2(n)", time_best="1",
       space_worst="n", space_average="n",
       notes="O(log n) *with high probability*; worst case O(n) if the random levels go "
             "badly. Much simpler to implement than a balanced tree and lock-free friendly."),
    _a("Trie (prefix tree)", category=_DS, task="string prefix lookup",
       time_worst="L", time_average="L", time_best="L",
       space_worst="n*L*sigma",
       notes="L = key length, sigma = alphabet size. Lookup is independent of the number "
             "of keys; the space cost is the problem — use a compressed/radix trie."),
    _a("Segment Tree", category=_DS, task="range query + point/range update",
       time_worst="log2(n)", time_average="log2(n)", time_best="log2(n)",
       space_worst="n",
       notes="O(log n) query/update, 2-4n memory. Lazy propagation extends it to range "
             "updates in O(log n)."),
    _a("Fenwick Tree (BIT)", category=_DS, task="prefix sum query + point update",
       time_worst="log2(n)", time_average="log2(n)", time_best="log2(n)",
       space_worst="n",
       notes="Same asymptotics as a segment tree with ~half the memory and far smaller "
             "constants, but only for invertible prefix operations."),
    _a("Sparse Table", category=_DS, task="static range-minimum queries",
       time_worst="1", time_average="1", time_best="1",
       space_worst="n*log2(n)",
       notes="O(1) idempotent RMQ after O(n log n) preprocessing. Immutable — any update "
             "costs a full rebuild."),
    _a("SQRT Decomposition", category=_DS, task="range query + point update",
       time_worst="sqrt(n)", time_average="sqrt(n)", time_best="sqrt(n)",
       space_worst="n",
       notes="Simpler than a segment tree and good enough when log n vs √n does not matter."),
    _a("Hash Map (std / dict)", category=_DS, task="key-value insert / lookup",
       time_worst="n", time_average="1", time_best="1",
       space_worst="n",
       notes="Expected O(1); worst case O(n) under adversarial collisions. No ordering — "
             "use a tree map when you need sorted iteration or range queries."),
]

# --------------------------------------------------------------------------- #
# 9. LINEAR ALGEBRA
# --------------------------------------------------------------------------- #

LINALG = [
    _a("Matrix Multiplication (schoolbook)", category=_LIN, task="multiply two n×n matrices",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Still the fastest for small n; blocked/tiled versions exploit cache without "
             "changing the asymptotics."),
    _a("Strassen Matrix Multiplication", category=_LIN, task="multiply two n×n matrices",
       time_worst="n**2.807", time_average="n**2.807", time_best="n**2.807",
       space_worst="n**2",
       notes="Wins from roughly n ≥ 500-1000 depending on implementation. Numerically less "
             "stable than the schoolbook method."),
    _a("Coppersmith-Winograd", category=_LIN, task="multiply two n×n matrices",
       time_worst="n**2.373", time_average="n**2.373", time_best="n**2.373",
       space_worst="n**2",
       notes="Best known exponent (~2.37286, Williams et al.) but the constants are so "
             "astronomical it is purely theoretical."),
    _a("Gaussian Elimination", category=_LIN, task="solve a dense linear system",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="With partial pivoting for stability. O(n²) for sparse/banded systems."),
    _a("LU Decomposition", category=_LIN, task="factorise a matrix to solve many systems",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="One O(n³) factorisation, then O(n²) per right-hand side — the win when "
             "solving Ax=b for many b."),
    _a("QR Decomposition (Householder)", category=_LIN, task="orthogonal factorisation / least squares",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Numerically stable least squares; Gram-Schmidt is also O(n³) but less stable."),
    _a("Cholesky Decomposition", category=_LIN, task="solve a symmetric positive-definite system",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Half the flops of LU (n³/3 vs 2n³/3) and uses half the storage — always "
             "prefer it when the matrix is SPD."),
    _a("Matrix Inversion (Gauss-Jordan)", category=_LIN, task="compute an explicit inverse",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Same cost as solving, but numerically inferior: solve Ax=b directly instead "
             "of computing A⁻¹ whenever possible."),
    _a("Determinant (cofactor expansion)", category=_LIN, task="compute a determinant",
       time_worst="factorial(n)", time_average="factorial(n)", time_best="factorial(n)",
       space_worst="n",
       notes="Useless beyond n ≈ 10; LU-based determinant is O(n³)."),
    _a("Eigenvalues (QR iteration)", category=_LIN, task="compute all eigenvalues",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="O(n³) per iteration in the naive form; with shifts and Hessenberg reduction "
             "it converges in a handful of iterations in practice."),
    _a("SVD", category=_LIN, task="singular value decomposition",
       time_worst="n**3", time_average="n**3", time_best="n**3",
       space_worst="n**2",
       notes="Golub-Kahan bidiagonalisation + QR iteration; ~10-20x the flops of a "
             "Cholesky, hence the popularity of truncated/randomised SVD."),
    _a("FFT", category=_LIN, task="discrete Fourier transform of length n",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Exponential speedup over the O(n²) DFT definition; the foundation of signal "
             "processing and fast multiplication/convolution."),
    _a("Naive Convolution", category=_LIN, task="convolve two length-n signals",
       time_worst="n**2", time_average="n**2", time_best="n**2",
       space_worst="n",
       notes="FFT convolution is O(n log n) — better for n beyond ~50."),
    _a("Conjugate Gradient", category=_LIN, task="solve a sparse SPD system iteratively",
       time_worst="n*sqrt(k)", time_average="n*sqrt(k)", time_best="n*sqrt(k)",
       space_worst="n",
       notes="k = condition number; each iteration is one sparse matvec. Preconditioning "
             "cuts k dramatically — usually the single biggest practical speedup."),
    _a("Gauss-Seidel", category=_LIN, task="solve a sparse system iteratively",
       time_worst="n**2*k", time_average="n**2*k", time_best="n**2*k",
       space_worst="n**2",
       notes="Simple and memory-light per sweep, but converges much more slowly than CG "
             "for ill-conditioned systems."),
]

# --------------------------------------------------------------------------- #
# 10. MACHINE LEARNING
# --------------------------------------------------------------------------- #

MACHINE_LEARNING = [
    _a("Linear Regression (normal equation)", category=_ML, task="fit a linear model",
       time_worst="m*d**2+d**3", time_average="m*d**2+d**3", time_best="m*d**2+d**3",
       space_worst="d**2",
       notes="m = samples, d = features. Exact but needs the O(d³) inverse; fails when "
             "XᵀX is singular."),
    _a("Linear Regression (gradient descent)", category=_ML, task="fit a linear model",
       time_worst="m*d*i", time_average="m*d*i", time_best="m*d*i",
       space_worst="d",
       notes="i = iterations. Scales to huge d and to streaming data; convergence depends "
             "on the learning rate and feature scaling."),
    _a("Logistic Regression", category=_ML, task="binary classification",
       time_worst="m*d*i", time_average="m*d*i", time_best="m*d*i",
       space_worst="d",
       notes="Same cost profile as linear regression GD; convex, so convergence is "
             "guaranteed (L-BFGS usually needs far fewer passes)."),
    _a("k-Means Clustering", category=_ML, task="cluster points into k groups",
       time_worst="m*d*k*i", time_average="m*d*k*i", time_best="m*d*k*i",
       space_worst="m*d+k*d",
       notes="i = iterations (usually < 50). NP-hard in general; Lloyd's converges to a "
             "local optimum. k-means++ seeding gives an O(log k) approximation."),
    _a("k-NN (brute force)", category=_ML, task="classify by nearest neighbours",
       time_worst="m*d", time_average="m*d", time_best="m*d",
       space_worst="m*d",
       notes="Zero training cost, O(md) per query. Unusable at scale — use a KD-tree "
             "(O(d log m) expected) or an ANN index."),
    _a("k-NN (KD-tree)", category=_ML, task="classify by nearest neighbours",
       time_worst="m", time_average="d*log2(m)", time_best="d*log2(m)",
       space_worst="m*d",
       notes="Logarithmic in low dimensions but degrades toward O(m) brute force beyond "
             "~20 dimensions (curse of dimensionality)."),
    _a("Decision Tree (CART)", category=_ML, task="learn a tree classifier",
       time_worst="m*d*depth", time_average="m*d*log2(m)", time_best="m*d*log2(m)",
       space_worst="m*d",
       notes="Sorting features dominates. Pruning/max-depth is essential — an unpruned "
             "tree overfits and can grow to O(m) leaves."),
    _a("Random Forest", category=_ML, task="ensemble classification / regression",
       time_worst="T*m*d*log2(m)", time_average="T*m*d*log2(m)", time_best="T*m*d*log2(m)",
       space_worst="T*m",
       notes="T = trees. Trivially parallel across trees, and feature subsampling cuts "
             "each split to O(√d) candidates."),
    _a("Gradient Boosting", category=_ML, task="ensemble classification / regression",
       time_worst="T*m*d", time_average="T*m*d", time_best="T*m*d",
       space_worst="T*m",
       notes="Sequential (not parallelisable across trees) — T is typically 100-5000. "
             "Histogram-based implementations (LightGBM/XGBoost) cut d to the bin count."),
    _a("SVM (kernel, SMO)", category=_ML, task="maximum-margin classification",
       time_worst="m**3", time_average="m**2", time_best="m**2",
       space_worst="m**2",
       notes="The O(m²) kernel matrix is the memory wall. Linear SVM solvers (liblinear, "
             "SDCA) are O(md) and scale far better."),
    _a("PCA (exact SVD)", category=_ML, task="dimensionality reduction",
       time_worst="min(m*d**2, m**2*d)", time_average="min(m*d**2, m**2*d)", time_best="min(m*d**2, m**2*d)",
       space_worst="m*d",
       notes="Pick the cheaper of the two orders depending on whether m or d is larger."),
    _a("Randomised PCA / SVD", category=_ML, task="dimensionality reduction to k components",
       time_worst="m*d*k", time_average="m*d*k", time_best="m*d*k",
       space_worst="m*k",
       notes="Linear in m and d for small k — the standard choice for large matrices."),
    _a("Naive Bayes", category=_ML, task="probabilistic classification",
       time_worst="m*d", time_average="m*d", time_best="m*d",
       space_worst="d*c",
       notes="One pass over the data; c = classes. Among the cheapest classifiers to train, "
             "surprisingly strong on text."),
    _a("Neural Net Forward Pass", category=_ML, task="inference on a fully connected net",
       time_worst="L*d**2", time_average="L*d**2", time_best="L*d**2",
       space_worst="L*d",
       notes="L = layers, d = width; exact cost is Σ d_i·d_(i+1) over layers. Dominated by "
             "the matmuls — the backward pass costs ~2x the forward pass."),
    _a("Neural Net Training (SGD, 1 epoch)", category=_ML, task="train a network",
       time_worst="m*F", time_average="m*F", time_best="m*F",
       space_worst="m*F",
       notes="F = flops per sample (~3x the forward pass), m = batch/epoch size. "
             "Activations dominate memory, which is why gradient checkpointing exists."),
    _a("Transformer Self-Attention", category=_ML, task="attention over a length-L sequence",
       time_worst="L**2*d", time_average="L**2*d", time_best="L**2*d",
       space_worst="L**2+L*d",
       notes="Quadratic in sequence length L — the scaling bottleneck of LLMs. FlashAttention "
             "keeps O(L²d) time but cuts memory to O(L) via tiling."),
    _a("Beam Search Decoding", category=_ML, task="sequence generation",
       time_worst="T*B*V", time_average="T*B*V", time_best="T*B*V",
       space_worst="B*T",
       notes="T = generated tokens, B = beam width, V = vocabulary. Greedy decoding is the "
             "B=1 special case."),
]

# --------------------------------------------------------------------------- #
# 11. OPTIMISATION / SOLVERS
# --------------------------------------------------------------------------- #

OPTIMISATION = [
    _a("Gradient Descent", category=_OPT, task="minimise a differentiable function",
       time_worst="i*d", time_average="i*d", time_best="i*d",
       space_worst="d",
       notes="i = iterations, d = dimension. Convergence O(1/k) for convex L-smooth "
             "functions; zig-zags badly on ill-conditioned problems."),
    _a("Gradient Descent with Momentum", category=_OPT, task="minimise a differentiable function",
       time_worst="i*d", time_average="i*d", time_best="i*d",
       space_worst="d",
       notes="Same per-iteration cost as vanilla GD, but far fewer iterations on ravines; "
             "accelerated methods reach O(1/k²)."),
    _a("Adam", category=_OPT, task="minimise a differentiable function",
       time_worst="i*d", time_average="i*d", time_best="i*d",
       space_worst="d",
       notes="Two extra O(d) moment buffers. Robust to scaling/learning rate, though SGD+momentum "
             "often generalises better on CV tasks."),
    _a("Newton's Method", category=_OPT, task="minimise a twice-differentiable function",
       time_worst="i*d**3", time_average="i*d**3", time_best="i*d**3",
       space_worst="d**2",
       notes="Quadratic convergence → very few iterations, but each needs an O(d³) Hessian "
             "solve plus O(d²) memory. Only viable for d in the hundreds."),
    _a("BFGS (quasi-Newton)", category=_OPT, task="minimise a smooth function",
       time_worst="i*d**2", time_average="i*d**2", time_best="i*d**2",
       space_worst="d**2",
       notes="Approximates the Hessian: superlinear convergence without computing second "
             "derivatives. L-BFGS cuts memory to O(md) with a limited history."),
    _a("Nelder-Mead Simplex", category=_OPT, task="minimise a function without derivatives",
       time_worst="i*d", time_average="i*d", time_best="i*d",
       space_worst="d",
       notes="Derivative-free; no convergence guarantee in d > 1 and slows badly as the "
             "dimension grows. Fine for d ≤ 10 noisy objectives."),
    _a("Simulated Annealing", category=_OPT, task="global optimisation of a black-box objective",
       time_worst="i", time_average="i", time_best="i",
       space_worst="1",
       notes="i = samples (schedule length). No polynomial guarantee; quality depends "
             "entirely on the cooling schedule."),
    _a("Genetic Algorithm", category=_OPT, task="global optimisation of a black-box objective",
       time_worst="g*p*f", time_average="g*p*f", time_best="g*p*f",
       space_worst="p*f",
       notes="g = generations, p = population, f = fitness evaluation cost (often the "
             "dominant term). Embarrassingly parallel across the population."),
    _a("Simplex Method (linear programming)", category=_OPT, task="solve a linear program",
       time_worst="2**n", time_average="n**3", time_best="n**3",
       space_worst="n*m",
       notes="Exponential worst case (Klee-Minty cube) yet polynomial in practice on "
             "almost every real problem. Interior-point methods give a guaranteed "
             "O(n^3.5) polynomial bound."),
    _a("Branch and Bound", category=_OPT, task="solve a combinatorial optimisation problem exactly",
       time_worst="2**n", time_average="2**n", time_best="n",
       space_worst="2**n",
       notes="Worst case explores the whole tree; a good bound prunes most of it. Memory "
             "for the open node list is often the binding constraint."),
    _a("Tabu Search", category=_OPT, task="local search with memory",
       time_worst="i*n", time_average="i*n", time_best="i*n",
       space_worst="t",
       notes="t = tabu list size. Escapes local optima at the cost of a memory of recent moves."),
    _a("Ant Colony Optimisation", category=_OPT, task="combinatorial optimisation via pheromone trails",
       time_worst="i*a*n**2", time_average="i*a*n**2", time_best="i*a*n**2",
       space_worst="n**2",
       notes="a = ants per iteration; the pheromone matrix is O(n²)."),
]

# --------------------------------------------------------------------------- #
# 12. COMPUTATIONAL GEOMETRY
# --------------------------------------------------------------------------- #

GEOMETRY = [
    _a("Convex Hull (Graham Scan)", category=_CG, task="convex hull of n points",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Optimal in the comparison model. O(n) if the input is already sorted by x."),
    _a("Convex Hull (Jarvis March)", category=_CG, task="convex hull of n points",
       time_worst="n**2", time_average="n*h", time_best="n*h",
       space_worst="h",
       notes="h = hull size. Output-sensitive: beats Graham scan when h ≪ n (e.g. h = O(log n))."),
    _a("Convex Hull (Divide & Conquer)", category=_CG, task="convex hull of n points",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Same bound as Graham scan; parallelises well and extends to 3D as O(n log n)."),
    _a("Convex Hull (Chan's Algorithm)", category=_CG, task="convex hull of n points",
       time_worst="n*log2(h)", time_average="n*log2(h)", time_best="n*log2(h)",
       space_worst="n",
       notes="Optimal output-sensitive bound — the best of both worlds."),
    _a("Closest Pair (Divide & Conquer)", category=_CG, task="closest pair of n points",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Beats the O(n²) brute force; the strip only ever needs 7 neighbours checked."),
    _a("Line Segment Intersection (Bentley-Ottmann)", category=_CG, task="report all segment intersections",
       time_worst="(n+k)*log2(n)", time_average="(n+k)*log2(n)", time_best="(n+k)*log2(n)",
       space_worst="n",
       notes="k = number of intersections. Output-sensitive versus O(n² + k) brute force."),
    _a("Delaunay Triangulation (incremental)", category=_CG, task="triangulate n points",
       time_worst="n**2", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Expected O(n log n) with randomised insertion order; worst case O(n²) on "
             "adversarial (e.g. cocircular) inputs."),
    _a("Polygon Triangulation", category=_CG, task="triangulate a simple polygon",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n",
       notes="Chazelle's O(n) algorithm is famously complex; practical code uses "
             "O(n log n) ear clipping or monotone decomposition."),
    _a("Voronoi Diagram (Fortune)", category=_CG, task="Voronoi diagram of n sites",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Optimal (sorting lower bound). Dual of the Delaunay triangulation."),
    _a("Point in Polygon (ray casting)", category=_CG, task="test point containment",
       time_worst="n", time_average="n", time_best="n",
       space_worst="1",
       notes="O(log n) per query is possible for convex polygons with binary search."),
]

# --------------------------------------------------------------------------- #
# 13. COMPRESSION / ENCODING
# --------------------------------------------------------------------------- #

COMPRESSION = [
    _a("Huffman Coding", category=_CMP, task="lossless entropy coding",
       time_worst="n+k*log2(k)", time_average="n+k*log2(k)", time_best="n+k*log2(k)",
       space_worst="n+k",
       notes="k = distinct symbols. Optimal prefix code for known symbol frequencies; "
             "package-merge gives a length-limited variant in O(nk)."),
    _a("Arithmetic Coding", category=_CMP, task="lossless entropy coding",
       time_worst="n", time_average="n", time_best="n",
       space_worst="k",
       notes="Approaches the entropy bound more tightly than Huffman (no integer bit-length "
             "rounding) at the cost of slower per-symbol arithmetic and patent history."),
    _a("Run-Length Encoding", category=_CMP, task="lossless compression of repetitive data",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n",
       notes="O(n) time; can *expand* data with few runs — only useful for highly "
             "repetitive streams (bitmaps, sparse matrices)."),
    _a("LZW / LZ77 family (gzip, DEFLATE)", category=_CMP, task="general-purpose lossless compression",
       time_worst="n", time_average="n", time_best="n",
       space_worst="W",
       notes="W = window size (32 KiB for DEFLATE). Linear in input; the compression level "
             "trades match-search effort for ratio, not asymptotics."),
    _a("LZ78 / LZW (dictionary)", category=_CMP, task="general-purpose lossless compression",
       time_worst="n", time_average="n", time_best="n",
       space_worst="D",
       notes="D = dictionary entries. Hash-table lookups keep it linear; used by GIF, "
             "compress, and early modems."),
    _a("Burrows-Wheeler Transform (bzip2)", category=_CMP, task="lossless compression via sorting",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="n",
       notes="Sorting the rotations dominates. Better ratio than DEFLATE, slower both ways."),
    _a("Base64 Encoding", category=_CMP, task="binary-to-text encoding",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n",
       notes="O(n) with a 33% size *increase* — encoding, not compression."),
]

# --------------------------------------------------------------------------- #
# 14. BACKTRACKING / PUZZLES / MISC
# --------------------------------------------------------------------------- #

BACKTRACKING = [
    _a("N-Queens (backtracking)", category=_BT, task="place n non-attacking queens",
       time_worst="n**n", time_average="n**n", time_best="n**n",
       space_worst="n",
       notes="Bitmask pruning brings the practical cost far below n! — solutions exist up "
             "to n = 27 with heavy optimisation."),
    _a("Sudoku Solver (backtracking + constraint propagation)", category=_BT, task="solve a 9×9 sudoku",
       time_worst="9**81", time_average="1", time_best="1",
       space_worst="81",
       notes="Astronomical worst case, but MRV heuristic + propagation solves typical "
             "puzzles in milliseconds. Dancing Links (Algorithm X) is the classic exact-cover "
             "formulation."),
    _a("Permutation Generation", category=_BT, task="enumerate all permutations",
       time_worst="n*factorial(n)", time_average="n*factorial(n)", time_best="n*factorial(n)",
       space_worst="n",
       notes="Heap's algorithm generates each in O(1) amortised swaps → Θ(n!) total, which "
             "is output-size optimal."),
    _a("Subset / Power Set Generation", category=_BT, task="enumerate all subsets",
       time_worst="n*2**n", time_average="n*2**n", time_best="n*2**n",
       space_worst="n",
       notes="2^n subsets of average size n/2 → Θ(n·2^n) output; iterative bit tricks "
             "generate each in O(1) amortised."),
    _a("Maze Solving (BFS)", category=_BT, task="shortest path through a grid maze",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="Guarantees the shortest path on an unweighted grid."),
    _a("Maze Solving (DFS)", category=_BT, task="find any path through a grid maze",
       time_worst="V+E", time_average="V+E", time_best="V+E",
       space_worst="V",
       notes="Finds *a* path, not the shortest; less memory on long corridors."),
    _a("Iterative Deepening DFS", category=_BT, task="depth-limited search with bounded memory",
       time_worst="b**d", time_average="b**d", time_best="b**d",
       space_worst="d",
       notes="Re-expands nodes but only by a constant factor (≈ b/(b-1)); gets BFS's "
             "optimality with DFS's O(d) memory."),
    _a("Bidirectional Search", category=_BT, task="shortest path between two known endpoints",
       time_worst="b**d", time_average="b**(d/2)", time_best="b**(d/2)",
       space_worst="b**(d/2)",
       notes="Two searches of depth d/2 instead of one of depth d — a square-root "
             "reduction, at the cost of matching memory."),
    _a("Meet in the Middle", category=_BT, task="exact search over 2^n combinations",
       time_worst="2**(n/2)*n", time_average="2**(n/2)*n", time_best="2**(n/2)*n",
       space_worst="2**(n/2)",
       notes="Splits the problem to get √ of the brute-force time, paying 2^(n/2) memory "
             "— the standard trick for n ≈ 40."),
]

# --------------------------------------------------------------------------- #
# 15. DATABASES / SYSTEMS
# --------------------------------------------------------------------------- #

SYSTEMS = [
    _a("Nested Loop Join", category=_DB, task="join two relations",
       time_worst="n*m", time_average="n*m", time_best="n*m",
       space_worst="n+m",
       notes="n, m = row counts. Fine when the inner relation fits in memory and is indexed."),
    _a("Block Nested Loop Join", category=_DB, task="join two relations",
       time_worst="n*m/B", time_average="n*m/B", time_best="n*m/B",
       space_worst="B",
       notes="B = buffer pages. Amortises the inner scan over a block, cutting I/O by a "
             "factor of B versus plain nested loop."),
    _a("Hash Join", category=_DB, task="join two relations on an equality predicate",
       time_worst="n+m", time_average="n+m", time_best="n+m",
       space_worst="min(n,m)",
       notes="Build a hash table on the smaller relation, then probe. Optimal for "
             "equi-joins when the build side fits in memory (grace hash join spills)."),
    _a("Sort-Merge Join", category=_DB, task="join two relations on an equality predicate",
       time_worst="n*log2(n)+m*log2(m)", time_average="n*log2(n)+m*log2(m)", time_best="n+m",
       space_worst="n+m",
       notes="Linear if both inputs are already sorted/indexed on the join key — the usual "
             "case in a well-indexed database. Handles very large inputs by streaming."),
    _a("Index Nested Loop Join", category=_DB, task="join using an index on the inner relation",
       time_worst="n*log2(m)", time_average="n*log2(m)", time_best="n*log2(m)",
       space_worst="n",
       notes="One index probe per outer row — beats hash join when the index already exists "
             "and n is small."),
    _a("B-Tree Index Scan", category=_DB, task="range or point query on an indexed column",
       time_worst="log2(n)+k", time_average="log2(n)+k", time_best="log2(n)+k",
       space_worst="1",
       notes="k = matching rows. Height 3-4 for billions of rows; leaf pages are linked "
             "for efficient range scans (B+ tree)."),
    _a("Full Table Scan", category=_DB, task="query without a usable index",
       time_worst="n", time_average="n", time_best="n",
       space_worst="1",
       notes="Sequential I/O — can beat an index scan when the query touches a large "
             "fraction of the table."),
    _a("External Merge Sort", category=_DB, task="sort data larger than memory",
       time_worst="n*log2(n)", time_average="n*log2(n)", time_best="n*log2(n)",
       space_worst="B",
       notes="B = buffer pages. I/O cost is O((n/B) log_{B-1}(n/B)) page transfers — "
             "the dominant term on disk, not the comparisons."),
    _a("Raft Consensus", category=_DB, task="replicate a log across nodes",
       time_worst="n", time_average="1", time_best="1",
       space_worst="n",
       notes="Per entry: O(1) messages in the happy path (one RTT), O(n) on leader "
             "election/catch-up. n = cluster size; latency, not CPU, is the bottleneck."),
    _a("Paxos (single-decree)", category=_DB, task="agree on one value across nodes",
       time_worst="n", time_average="1", time_best="1",
       space_worst="n",
       notes="Two phases, 2 RTTs, O(n) messages. Multi-Paxos amortises phase 1 across "
             "proposals, effectively becoming Raft-like."),
    _a("Mark-Sweep Garbage Collection", category=_DB, task="reclaim unreachable heap objects",
       time_worst="n", time_average="n", time_best="n",
       space_worst="n",
       notes="n = live + dead objects. Non-generational, stop-the-world in the naive form; "
             "cost scales with heap size, not allocation rate."),
    _a("Generational GC (young collection)", category=_DB, task="reclaim unreachable heap objects",
       time_worst="n", time_average="L", time_best="L",
       space_worst="n",
       notes="L = live set in the young generation (usually tiny). Exploits the weak "
             "generational hypothesis — the reason nursery collections are milliseconds."),
]


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

ALL_ALGORITHMS: tuple[Algorithm, ...] = tuple(
    SORTING + SEARCHING + GRAPH + STRINGS + DYNAMIC + NUMTHEORY + CRYPTO
    + STRUCTURES + LINALG + MACHINE_LEARNING + OPTIMISATION + GEOMETRY
    + COMPRESSION + BACKTRACKING + SYSTEMS
)

CATEGORIES: tuple[str, ...] = tuple(
    dict.fromkeys(a.category for a in ALL_ALGORITHMS)
)

__all__ = ["ALL_ALGORITHMS", "CATEGORIES", "SORTING", "SEARCHING", "GRAPH", "STRINGS",
           "DYNAMIC", "NUMTHEORY", "CRYPTO", "STRUCTURES", "LINALG", "MACHINE_LEARNING",
           "OPTIMISATION", "GEOMETRY", "COMPRESSION", "BACKTRACKING", "SYSTEMS"]
