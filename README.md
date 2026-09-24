# algocomp · `algo-compare`

**A theoretical complexity-comparison framework for algorithms that solve the same task.**

![tests](https://github.com/3punch/algocomp/actions/workflows/tests.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

Give it two algorithms. It tells you who wins asymptotically, by how much, from which
input size the advantage actually matters, where the trade-offs are (memory, stability,
worst case), and what the caveats are — all from the *declared* Big-O profiles, with no
benchmark noise.

```
$ algo-compare compare merge_sort quick_sort
```

```
╭─────────────────────────────────────────────────────╮
│ Algorithm Comparison  ·  Merge Sort  vs  Quick Sort │
╰─────────────────────────────────────────────────────╯
                                             Complexity profiles

                       Merge Sort                                  Quick Sort
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  category             sorting                                     sorting
  task                 sort a list of comparable items             sort a list of comparable items
  time best            O(n log n)                                  O(n log n)
  time average         O(n log n)                                  O(n log n)
  time worst           O(n log n)                                  O(n^2)
  space best           O(n)                                        O(log n)
  space average        O(n)                                        O(log n)
  space worst          O(n)                                        O(n)
  stable               yes                                         no
  in place             no                                          yes
  input sensitive      —                                           yes — best/average/worst differ

                                             Case-by-case verdict
╭─────────────┬───────────┬──────────────┬──────────────┬───────────────┬──────────────────────┬─────────────╮
│ dimension   │ case      │   Merge Sort │   Quick Sort │    winner     │           A/B as n→∞ │ crossover n │
├─────────────┼───────────┼──────────────┼──────────────┼───────────────┼──────────────────────┼─────────────┤
│ time        │ best      │   O(n log n) │   O(n log n) │      tie      │                equal │           — │
│ time        │ average   │   O(n log n) │   O(n log n) │      tie      │                equal │           — │
│ time        │ worst     │   O(n log n) │       O(n^2) │ ◀ Merge Sort  │   A/B → 0 (≈ n^0.94) │           — │
│ space       │ best      │         O(n) │     O(log n) │ Quick Sort ▶  │   A/B → ∞ (≈ n^1.00) │           — │
│ space       │ average   │         O(n) │     O(log n) │ Quick Sort ▶  │   A/B → ∞ (≈ n^1.00) │           — │
│ space       │ worst     │         O(n) │         O(n) │      tie      │                equal │           — │
╰─────────────┴───────────┴──────────────┴──────────────┴───────────────┴──────────────────────┴─────────────╯
                                  Operation-count growth (time/average case)

                   n           Merge Sort  O(n log n)           Quick Sort  O(n log n)     A ÷ B    cheaper
 ────────────────────────────────────────────────────────────────────────────────────────────────────────────
                  10                             33.2                             33.2         1       =
                 100                              664                              664         1       =
               1,000                         9.97e+03                         9.97e+03         1       =
              10,000                         1.33e+05                         1.33e+05         1       =
             100,000                         1.66e+06                         1.66e+06         1       =
           1,000,000                         1.99e+07                         1.99e+07         1       =
          10,000,000                         2.33e+08                         2.33e+08         1       =
       1,000,000,000                         2.99e+10                         2.99e+10         1       =

╭────────────────────────────────────────────── log-log growth ──────────────────────────────────────────────╮
│   1.6e+11 │                                                                                                │
│           │                                                                                                │
│ XXX                                                                                                        │
│           │                                                                                                │
│ XXXXXXXX                                                                                                   │
│           │                                                                                      XXXXXXXX  │
│   5.6e+08 │                                                                              XXXXXXXX          │
│           │                                                                       XXXXXXXX                 │
│           │                                                                XXXXXXX                         │
│           │                                                        XXXXXXXX                                │
│   2.0e+06 │                                                 XXXXXXXX                                       │
│           │                                          XXXXXXXX                                              │
│           │                                   XXXXXXXX                                                     │
│           │                            XXXXXXX                                                             │
│   7.2e+03 │                     XXXXXXX                                                                    │
│           │              XXXXXXXX                                                                          │
│           │        XXXXXXX                                                                                 │
│           │  XXXXXXX                                                                                       │
│   2.6e+01 │XX                                                                                              │
│           │                                                                                                │
│           └─────────────────────────────────────────────────────────────────────────────────────────────── │
│ ─────────                                                                                                  │
│            10           100          1,000        10,000       100,000     1,000,000    10,000,000   ← n   │
│   A = O(n log n)   B = O(n log n)   X = the two curves cross/coincide here                                 │
│   (time/average case · both axes log-scaled · y = operations)                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────── Reasoning ─────────────────────────────────────────────────╮
│  →   time/best: Merge Sort O(n log n) vs Quick Sort O(n log n) → asymptotically equivalent (same growth    │
│      class).                                                                                               │
│  →   time/average: Merge Sort O(n log n) vs Quick Sort O(n log n) → asymptotically equivalent (same        │
│      growth class).                                                                                        │
│  →   time/worst: Merge Sort O(n log n) vs Quick Sort O(n^2) → Merge Sort is asymptotically better. the     │
│      cost ratio grows like n^0.94, so the advantage widens without bound as n grows.                       │
│  →   space/best: Merge Sort O(n) vs Quick Sort O(log n) → Quick Sort is asymptotically better. the cost    │
│      ratio grows like n^1.00, so the advantage widens without bound as n grows.                            │
│  →   space/average: Merge Sort O(n) vs Quick Sort O(log n) → Quick Sort is asymptotically better. the      │
│      cost ratio grows like n^1.00, so the advantage widens without bound as n grows.                       │
│  →   space/worst: Merge Sort O(n) vs Quick Sort O(n) → asymptotically equivalent (same growth class).      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────── Conclusion ────────────────────────────────────────────────╮
│ Merge Sort and Quick Sort are in the same asymptotic class for average-case time (O(n log n)). Any real    │
│ difference comes from constant factors, cache behaviour and allocation — measure before choosing. Worst    │
│ case favours Merge Sort (O(n log n) vs O(n^2)); stability differs (Merge Sort: stable, Quick Sort:         │
│ unstable); in-place-ness differs (Merge Sort: extra memory, Quick Sort: in-place).                         │
│                                                                                                            │
│ overall winner: Merge Sort (weighted score A=2 vs B=1.5)                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

---

## Contents

- [What it does](#what-it-does)
- [Install / run](#install--run)
- [Command reference](#command-reference)
- [How the comparison works](#how-the-comparison-works)
- [Report formats](#report-formats)
- [Extending it](#extending-it)
- [Optional: empirical verification](#optional-empirical-verification)
- [Project layout](#project-layout)
- [Catalogue](#catalogue)
- [Design notes & limitations](#design-notes--limitations)

---

## What it does

| Capability | Detail |
|---|---|
| **Case-by-case verdicts** | best / average / worst case **time** *and* **space**, never a single number |
| **Asymptotic winner + margin** | derived from log-log growth exponents, so `n²` vs `n log n` is classified as *strictly worse*, not "constant factor" |
| **Crossover detection** | finds the input size where the ordering flips (`O(√n)` really does beat `O(log n)` below n≈16) |
| **Constant-factor detection** | says "same growth class, ~2× apart" instead of pretending there's no difference |
| **Comparability checks** | warns when two entries solve different tasks or use incommensurable parameters |
| **Trade-off flags** | stability, in-place-ness, input-order sensitivity, extra memory |
| **200 algorithms, 15 families** | sorting, searching, graphs, strings, DP, number theory, crypto, data structures, linear algebra, ML, optimisation, geometry, compression, backtracking, systems |
| **4 report formats** | terminal (rich), Markdown, JSON, self-contained HTML with an SVG chart |
| **Zero dependencies** | pure standard library; rich is an optional nicety |

---

## Install / run

Nothing to install — run it straight from the source tree:

```bash
cd algo-compare
python3 algo-compare compare merge_sort quick_sort     # or ./algo-compare ...
python3 -m algocomp.cli compare merge_sort quick_sort  # equivalent
```

Optional install (gives you an `algo-compare` command anywhere):

```bash
git clone https://github.com/3punch/algocomp.git
cd algocomp
pip install -e .              # distribution: algocomp, command: algo-compare
pip install -e ".[pretty]"    # + rich, for nicer terminal tables
```

Run the test suite:

```bash
python3 -m unittest discover -s tests -t . -v     # 57 tests
```

---

## Command reference

### `compare` — the main event

```bash
algo-compare compare <A> <B> [options]
```

| Option | Meaning |
|---|---|
| `--format, -f {terminal,markdown,json,html}` | report format (default `terminal`) |
| `--case {best,average,worst,all}` | restrict which cases are compared |
| `--sizes lo:hi:count` or `n1,n2,n3` | input sizes for the growth table & crossover search (default `10:1e9:8`) |
| `--no-space` / `--no-table` / `--no-chart` / `--no-notes` | trim the report |
| `--add "Name:time_avg:time_worst[:space[:category[:task]]]"` | define an algorithm inline |
| `--out, -o FILE` | write to a file instead of stdout |
| `--definitions, -D FILE` | load extra algorithms from a definition file (repeatable) |

Examples:

```bash
# strict JSON for another tool
algo-compare compare dijkstra_binary_heap bellman_ford -f json

# Markdown for a PR description or README
algo-compare compare bubble_sort timsort -f markdown -o bubble.md

# self-contained HTML with a hand-drawn SVG chart
algo-compare compare jump_search binary_search -f html -o crossover.html

# compare your own algorithm against a library one
algo-compare compare bogosort merge_sort \
  --add "Bogosort:factorial(n):factorial(n):1:custom:sort a list of comparable items"
```

### `list`, `show`, `matrix`, `suggest`, `categories`, `benchmarks`

```bash
algo-compare list --category sorting          # the catalogue
algo-compare list --search dijkstra --json
algo-compare show quick_sort                  # full profile + peers
algo-compare matrix --category graph --space  # 28 graph algorithms at a glance
algo-compare matrix merge_sort quick_sort heap_sort counting_sort
algo-compare suggest --limit 10               # task groups with ≥2 algorithms = fair pairs
algo-compare categories
algo-compare benchmarks                       # which entries can be measured empirically
```

### `verify` — optional empirical cross-check

Measures real runtime growth and fits `log T(n) = α + β log n`, then compares the measured
`β` with the declared growth exponent:

```bash
algo-compare verify bubble_sort --sizes 128:4096:5
```

```
  declared worst-case : O(n^2) (growth exponent ≈ 2.000)
  measured exponent   : 1.992 (log-log least squares, R² = 1.000)
  verdict             : matches

             n |      seconds |  ratio to prev
  -------------+--------------+---------------
           128 |   0.00029     |              —
           331 |   0.00198     |          6.79x
           859 |   0.01295     |          6.53x
          2229 |   0.08770     |          6.77x
          4096 |   0.17501     |          2.00x
```

A doubling of `n` multiplies the time by `2^β`: ~2× for linear, ~4× for quadratic.

---

## How the comparison works

### 1. Every bound is a real function of `n`

Complexities are stored as expressions, not labels:

```python
Complexity("n*log2(n)")      # -> O(n log n)
Complexity("(V+E)*log2(V)")  # -> O((V+E)·log(V))
Complexity("factorial(n)")   # -> O(n!)
```

Expressions are parsed with a validated AST (function calls, arithmetic and a whitelist of
variables only — no `eval`), and evaluated in log space where needed so that
`factorial(10⁶)` doesn't explode.

### 2. Growth exponents, not raw ratios

Each bound has a **growth exponent** — the slope of `log g(n)` vs `log n` measured between
`n = 10⁴` and `10¹²`:

| bound | exponent | reading |
|---|---|---|
| `O(1)` | 0.00 | flat |
| `O(log n)` | 0.00 | Θ(n⁰) — special-cased, since the finite-span slope of a log is ~0.06 |
| `O(√n)` | 0.50 | square-root |
| `O(n)` | 1.00 | linear |
| `O(n log n)` | 1.06 | linearithmic |
| `O(n²)` | 2.00 | quadratic |
| `O(2ⁿ)`, `O(n!)` | ∞ | explosive |

Two bounds are compared by their **exponent difference**, with the raw ratio used only as
supporting evidence. This is what makes the tool robust: a float64 ratio underflows to `0`
or saturates long before `n → ∞`, so a naive `gA(n)/gB(n)` would call `n²` vs `n log n` a
"constant factor" at any finite probe.

### 3. Dominance classification

Every case lands in exactly one bucket:

| Dominance | Meaning | Example |
|---|---|---|
| `strict` | one side wins at every realistic size, gap widens without bound | `O(n²)` vs `O(n log n)` |
| `constant` | same growth class, a constant factor apart | Kruskal vs Prim (both ≈ n log n) |
| `equal` | identical class *and* identical leading constant | merge sort vs Timsort |
| `crossover` | the ordering flips at some finite `n` | `O(√n)` beats `O(log n)` below n≈16 |
| `incomparable` | different tasks / different parameter meaning | sort vs search |

A slow-drifting log factor is caught even when the exponents are within tolerance: a
five-decade monotone drift of the ratio (the signature of `log n`) is upgraded from
`constant` to `strict`.

### 4. Crossovers

For `crossover` cases the tool bisects on `gA(n) − gB(n)` to find the flip point, and
suppresses crossings below `n = 8` as artefacts of dropping constant factors (where they
exist, the report says so rather than quoting a meaningless number).

### 5. Comparability

Comparing things that aren't comparable is a common way to get a confidently wrong answer,
so the tool pushes back:

- different `task` strings → **"Not strictly comparable"** banner listing why;
- bounds expressed in different parameter sets (`n` vs `V,E`) → warning that numeric
  samples assume all secondary parameters equal `n`, so read them as shapes, not values;
- a case declared on only one side → that case is skipped, with a warning instead of a
  silent gap.

### 6. Overall winner

A weighted score across the cases (average time ×3, worst time ×2, worst space ×1.5,
average space ×1, best time ×0.5) picks a single winner, and `conclusion()` writes the
2–4 sentence summary you see in the report.

---

## Report formats

| Format | Use it for |
|---|---|
| `terminal` | reading now, with colours, tables and an ASCII log-log chart |
| `markdown` | pasting into a README, PR, issue or notebook |
| `json` | driving another program (`winner`, `dominance`, `crossover_n`, per-case samples, …) |
| `html` | sharing: one file, no external assets, inline SVG chart, dark theme |

Pre-generated samples live in [`reports/`](reports/) (open `reports/index.html`):

- `sorting-merge-vs-quick` — same Big-O, different trade-offs
- `sorting-bubble-vs-timsort` — quadratic vs linearithmic
- `search-jump-vs-binary` — a genuine crossover
- `graph-dijkstra-vs-bellman` — asymptotics with different parameters
- `dp-fib-naive-vs-memo` — exponential vs linear
- plus complexity matrices for sorting, graphs, data structures and DP

---

## Extending it

### Inline, from the command line

```bash
algo-compare compare "My Sorter" merge_sort \
  --add "My Sorter:n*log2(n):n**2:n:custom:sort a list of comparable items"
```

Spec shape: `Name:time_average:time_worst[:space_worst[:category[:task]]]`.
Comparable only if the `task` matches the other side's.

### Definition files (best for a project's own algorithms)

```ini
# my_algorithms.defs
[hybrid_sort]
name = Hybrid Sort (insertion + merge)
category = sorting
task = sort a list of comparable items
time_worst = n*log2(n)
time_average = n*log2(n)
time_best = n
space_worst = n
stable = true
in_place = false
notes = Insertion sort below 32 elements, merge sort above.
```

```bash
algo-compare -D examples/my_algorithms.defs list --category custom
algo-compare -D examples/my_algorithms.defs compare hybrid_sort timsort
```

Allowed syntax in expressions: `+ - * / // % **`, parentheses, variables (`n`, `m`, `k`,
`V`, `E`, `W`, `d`, …), and `log2`, `log`, `ln`, `log10`, `sqrt`, `cbrt`, `exp`,
`factorial`, `perm`, `comb`, `abs`, `min`, `max`, `floor`, `ceil`, plus `pi`, `e`, `phi`.
Labels like `O(n log n)`, `n^2` and `2n` are accepted too.

### From Python

```python
from algocomp import compare, registry
from algocomp.algorithm import Algorithm

reg = registry()
verdict = compare(reg.get("merge_sort"), reg.get("quick_sort"))

print(verdict.conclusion())
winner, why = verdict.overall_winner
for case in verdict.cases:
    print(case.explain("Merge Sort", "Quick Sort"))

# your own algorithm
mine = Algorithm.build(
    "My Sort", time_worst="n*log2(n)", time_average="n*log2(n)",
    space_worst="1", category="custom", task="sort a list of comparable items",
)
print(compare(mine, reg.get("quick_sort")).conclusion())
```

---

## Optional: empirical verification

Theory and wall-clock time disagree for good reasons (constant factors, cache behaviour,
allocation). `verify` exists to keep the catalogue honest — it ships pure-Python
benchmarks for 20 entries and reports the measured exponent next to the declared one.

```bash
algo-compare benchmarks
algo-compare verify quick_sort --sizes 512:16384:6 --budget 0.5
```

Each size is capped by `--budget` seconds, so quadratic and exponential entries stop early
instead of hanging the tool.

---

## Project layout

```
algo-compare/
├── algo-compare                     # standalone launcher (no install needed)
├── algocomp/
│   ├── expr.py                      # safe expression parser/evaluator (AST whitelist)
│   ├── complexity.py                # Complexity: expression + label + rank + growth exponent
│   ├── algorithm.py                 # Algorithm & ComplexityProfile records
│   ├── catalog.py                   # 200 algorithms with best/avg/worst time & space
│   ├── registry.py                  # lookup, fuzzy search, custom definition files
│   ├── comparator.py                # the verdict engine (dominance, crossovers, warnings)
│   ├── matrix.py                    # multi-algorithm comparison grids
│   ├── reports.py                   # terminal / Markdown / JSON / HTML renderers
│   ├── verify.py                    # optional empirical benchmark + curve fitting
│   └── cli.py                       # argument parsing and commands
├── examples/
│   ├── my_algorithms.defs           # sample custom definitions
│   └── generate_reports.py          # regenerates reports/
├── reports/                         # pre-generated sample reports (HTML/MD/txt)
├── tests/test_algocomp.py           # 57 unit tests
├── pyproject.toml
└── Makefile                         # make test | demo | reports | matrix
```

---

## Catalogue

200 algorithms across 15 families. Every entry carries best/average/worst **time** and
**space**, plus stability, in-place-ness and a note about constant factors and edge cases.

| Family | Examples |
|---|---|
| Sorting (13) | bubble, insertion, selection, shell, merge, quick, heap, introsort, Timsort, counting, bucket, radix, cycle |
| Search / retrieval (13) | linear, binary, jump, interpolation, exponential, Fibonacci, hash lookup, BFS/DFS search, quickselect, median-of-medians |
| Graphs (28) | BFS/DFS, Dijkstra (binary heap & Fibonacci heap), Bellman-Ford, SPFA, Floyd-Warshall, Johnson, A\*, bidirectional Dijkstra, Kruskal, Prim, Borůvka, topological sort, Tarjan, Kosaraju, bridges, bipartite check, Hierholzer, Hamiltonian path, Held-Karp, Edmonds-Karp, Dinic, push-relabel, Hungarian, Hopcroft-Karp, union-find |
| Strings (12) | naive, KMP, Rabin-Karp, Boyer-Moore, Z-algorithm, Aho-Corasick, suffix array, suffix automaton, backtracking regex, Thompson NFA, LCS |
| Dynamic programming (14) | Fibonacci (naive/memo), matrix chain, knapsack (0/1 and unbounded), subset sum, edit distance, LIS (O(n²) and O(n log n)), coin change, rod cutting, optimal BST, LPS, bitmask DP |
| Number theory (13) | Euclid, binary GCD, extended Euclid, trial division, Pollard's rho, Eratosthenes, linear sieve, segmented sieve, Miller-Rabin, AKS, fast modexp, Karatsuba, FFT multiplication |
| Crypto & hashing (10) | SHA-256, HMAC, AES, RSA, Diffie-Hellman, ECC scalar mult, PBKDF2, Argon2id, open addressing, separate chaining |
| Data structures (15) | dynamic array, singly/doubly linked list, binary heap, AVL, red-black, splay, B-tree, skip list, trie, segment tree, Fenwick, sparse table, sqrt decomposition, hash map |
| Linear algebra (15) | schoolbook/Strassen/Coppersmith-Winograd matmul, Gaussian elimination, LU, QR, Cholesky, inversion, determinant, QR iteration, SVD, FFT, convolution, conjugate gradient, Gauss-Seidel |
| Machine learning (17) | linear regression (normal equation & GD), logistic regression, k-means, k-NN (brute force & KD-tree), CART, random forest, gradient boosting, SVM, PCA, randomised SVD, naive Bayes, forward pass, SGD training, self-attention, beam search |
| Optimisation (12) | GD, GD+momentum, Adam, Newton, BFGS, Nelder-Mead, simulated annealing, genetic algorithm, simplex, branch & bound, tabu search, ACO |
| Computational geometry (10) | Graham scan, Jarvis march, divide & conquer hull, Chan's algorithm, closest pair, Bentley-Ottmann, Delaunay, polygon triangulation, Fortune's algorithm, point in polygon |
| Compression (7) | Huffman, arithmetic coding, RLE, LZ77/DEFLATE, LZW, BWT, Base64 |
| Backtracking & puzzles (9) | N-Queens, Sudoku, permutations, subsets, maze BFS/DFS, IDDFS, bidirectional search, meet in the middle |
| Databases & systems (12) | nested loop, block nested loop, hash join, sort-merge join, index nested loop, B-tree scan, full scan, external merge sort, Raft, Paxos, mark-sweep GC, generational GC |

---

## Design notes & limitations

**What the numbers mean.** The growth tables list *abstract operation counts* from the
declared formulas — they are not seconds, and they deliberately exclude constant factors,
cache behaviour and allocation cost. The tool says so in every report.

**Why everything is symbolically evaluated.** Storing `n²` as "O(n²)" throws away the
ability to compute, plot or compare. Storing it as an expression lets the same data drive
the growth table, the crossover search, the JSON output and the charts.

**Known approximations.**

- Bounds with secondary parameters (`O(n+k)`, `O(VE)`, `O(b^d)`) are sampled with every
  non-`n` parameter set to `n`. The tool warns about this and treats those cells as shape
  comparisons; the *classification* (strict/constant/crossover) still comes from the
  asymptotic order, which is parameter-agnostic.
- `rank` is a display heuristic for sorting entries in the matrix view; the verdict engine
  never uses it.
- Amortised bounds are recorded at their amortised value, with the per-operation worst case
  (e.g. dynamic-array growth) noted in the entry's notes.
- Constants inside expressions are treated as given; the tool will not tell you that your
  `O(n)` has a 10⁶ loop count.

**Verifying rather than trusting.** `verify` closes the loop for 20 entries; for the rest,
the theoretical bound is what a textbook says, and the report's caveat notes say when the
constant factor is the real story.

---

## License

MIT — use it, fork it, extend the catalogue.
