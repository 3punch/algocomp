"""Test suite for algo-compare. Run with:  python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algocomp import __version__, compare, registry
from algocomp.algorithm import Algorithm
from algocomp.catalog import ALL_ALGORITHMS
from algocomp.cli import main, parse_sizes
from algocomp.complexity import Complexity, coerce
from algocomp.expr import ExprError, evaluate, free_variables
from algocomp.matrix import rank_algorithms, render_matrix
from algocomp.registry import (Registry, load_definitions, load_definitions_into,
                               register_custom)
from algocomp.reports import ascii_chart, render_html, render_json, render_markdown, render_terminal


class TestExpressions(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(evaluate("n", n=5), 5)
        self.assertEqual(evaluate("n**2", n=5), 25)
        self.assertEqual(evaluate("n*log2(n)", n=1024), 10240)
        self.assertEqual(evaluate("1", n=99), 1)
        self.assertEqual(evaluate("(V+E)*log2(V)", V=8, E=16), 24 * 3)

    def test_functions_and_constants(self):
        self.assertAlmostEqual(evaluate("sqrt(n)", n=16), 4)
        self.assertEqual(evaluate("factorial(n)", n=5), 120)
        self.assertEqual(evaluate("comb(n,2)", n=6), 15)
        self.assertAlmostEqual(evaluate("phi", n=1), (1 + 5 ** 0.5) / 2)

    def test_free_variables(self):
        self.assertEqual(free_variables("n*log2(n)"), ("n",))
        self.assertEqual(free_variables("E+V*log2(V)"), ("E", "V"))
        self.assertEqual(free_variables("n+m+z"), ("m", "n", "z"))
        self.assertEqual(free_variables("1"), ())

    def test_rejects_dangerous_input(self):
        for bad in ("__import__('os')", "open('x')", "n.attr", "[n]", "{1:2}",
                    "lambda: 1", "n if n else 1", "'text'", "print(1)"):
            with self.assertRaises(ExprError, msg=f"{bad!r} should be rejected"):
                evaluate(bad, n=1)

    def test_rejects_unknown_names(self):
        with self.assertRaises(ExprError):
            free_variables("foo(n)")
        with self.assertRaises(ExprError):
            evaluate("n @ 2", n=1)

    def test_overflow_is_contained(self):
        with self.assertRaises(ExprError):
            evaluate("n**1000", n=10)


class TestComplexity(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(Complexity("n*log2(n)").resolved_label, "O(n log n)")
        self.assertEqual(Complexity("factorial(n)").resolved_label, "O(n!)")
        self.assertEqual(Complexity("1").resolved_label, "O(1)")
        self.assertEqual(str(Complexity("n**2")), "O(n^2)")
        self.assertEqual(Complexity("V*E", "O(VE)").resolved_label, "O(VE)")

    def test_growth_exponents(self):
        cases = {
            "1": 0.0, "log2(n)": 0.0, "sqrt(n)": 0.5, "n": 1.0,
            "n**2": 2.0, "n**3": 3.0,
        }
        for expr, expected in cases.items():
            self.assertAlmostEqual(Complexity(expr).growth_exponent, expected, places=2,
                                   msg=expr)
        self.assertAlmostEqual(Complexity("n*log2(n)").growth_exponent, 1.06, delta=0.01)
        self.assertTrue(math.isinf(Complexity("2**n").growth_exponent))
        self.assertTrue(math.isinf(Complexity("factorial(n)").growth_exponent))

    def test_growth_classes(self):
        self.assertEqual(Complexity("n").growth_class(), "linear")
        self.assertEqual(Complexity("n**2").growth_class(), "polynomial (degree ≈ 2.00)")
        self.assertEqual(Complexity("n*log2(n)").growth_class(), "linearithmic")
        self.assertEqual(Complexity("2**n").growth_class(), "exponential")
        self.assertEqual(Complexity("factorial(n)").growth_class(), "factorial")
        self.assertEqual(Complexity("1").growth_class(), "constant")
        self.assertEqual(Complexity("log2(n)").growth_class(), "logarithmic")

    def test_hierarchy_rank_ordering(self):
        ordered = ["1", "log2(log2(n))", "log2(n)", "sqrt(n)", "n",
                   "n*log2(n)", "n**2", "n**3", "2**n", "factorial(n)"]
        ranks = [Complexity(e).rank for e in ordered]
        self.assertEqual(ranks, sorted(ranks), f"ranks not monotone: {ranks}")
        self.assertEqual(len(set(ranks)), len(ranks), "ranks must be distinct")

    def test_coerce_accepts_labels(self):
        self.assertEqual(coerce("O(n log n)").expr, "n*log2(n)")
        self.assertEqual(coerce("O(n^2)").expr, "n**2")
        self.assertEqual(coerce("n**2").expr, "n**2")
        self.assertEqual(coerce("Θ(n)").expr, "n")
        self.assertEqual(coerce("O(2n)").expr, "2*n")
        self.assertIsInstance(coerce(Complexity("n")), Complexity)

    def test_secondary_parameters_default_to_n(self):
        c = Complexity("n+k")
        self.assertEqual(c.value(100), 200)
        self.assertEqual(c.value(100, k=5), 105)

    def test_value_never_raises(self):
        self.assertTrue(math.isinf(Complexity("factorial(n)").value(1000)))
        self.assertTrue(math.isinf(Complexity("2**n").value(5000)))


class TestCatalogue(unittest.TestCase):
    def test_every_entry_is_well_formed(self):
        seen = set()
        for a in ALL_ALGORITHMS:
            self.assertTrue(a.name and a.key and a.category and a.task, a)
            self.assertNotIn(a.key, seen, f"duplicate key {a.key}")
            seen.add(a.key)
            # every declared complexity must evaluate without error
            for _, c in a.time.items():
                self.assertGreater(c.value(64), 0, f"{a.key} time {c.expr}")
            if a.space:
                for _, c in a.space.items():
                    self.assertGreaterEqual(c.value(64), 0, f"{a.key} space {c.expr}")

    def test_catalogue_is_substantial(self):
        self.assertGreaterEqual(len(ALL_ALGORITHMS), 150)
        self.assertGreaterEqual(len({a.category for a in ALL_ALGORITHMS}), 10)

    def test_known_bounds(self):
        reg = registry()
        expectations = {
            ("merge_sort", "worst"): "n*log2(n)",
            ("quick_sort", "worst"): "n**2",
            ("binary_search", "worst"): "log2(n)",
            ("bubble_sort", "average"): "n**2",
            ("dijkstra_binary_heap", "worst"): "(V+E)*log2(V)",
            ("bellman_ford", "worst"): "V*E",
            ("floyd_warshall", "worst"): "V**3",
            ("fibonacci_naive_recursion", "worst"): "2**n",
        }
        for (key, case), expr in expectations.items():
            self.assertEqual(dict(reg.get(key).time.items())[case].expr, expr, key)

    def test_sorting_stability_flags(self):
        reg = registry()
        self.assertTrue(reg.get("merge_sort").stable)
        self.assertFalse(reg.get("quick_sort").stable)
        self.assertTrue(reg.get("heap_sort").in_place)
        self.assertFalse(reg.get("merge_sort").in_place)


class TestComparator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = registry()

    def v(self, a, b, **kw):
        return compare(self.reg.get(a), self.reg.get(b), **kw)

    def test_quadratic_loses_to_linearithmic(self):
        c = self.v("bubble_sort", "timsort").headline
        self.assertEqual(c.winner, "B")
        # the two curves do cross, but only below n=8 — reported as not meaningful
        self.assertIn(c.dominance, ("strict", "crossover"))
        self.assertFalse(c.crossover_meaningful)
        self.assertGreater(c.exponent_gap, 0.8)

    def test_equal_complexities_tie(self):
        c = self.v("merge_sort", "timsort").headline
        self.assertEqual(c.winner, "tie")
        self.assertEqual(c.dominance, "equal")
        self.assertEqual(c.gap_label, "equal")

    def test_log_beats_sqrt_with_crossover(self):
        c = self.v("jump_search", "binary_search").headline
        self.assertEqual(c.winner, "B")           # log n beats sqrt n asymptotically
        self.assertEqual(c.dominance, "crossover")  # but sqrt n wins for tiny n
        self.assertIsNotNone(c.crossover)
        self.assertTrue(c.crossover_meaningful)
        self.assertLess(c.crossover, 100)

    def test_constant_factor_detected(self):
        c = self.v("kruskal_union_find", "prim_binary_heap").headline
        self.assertEqual(c.dominance, "constant")
        self.assertNotEqual(c.winner, "tie")

    def test_exponential_vs_polynomial(self):
        c = self.v("fibonacci_naive_recursion", "fibonacci_memoisation_bottom_up").headline
        self.assertEqual(c.winner, "B")
        # the two curves do cross, but only below n=8 — reported as not meaningful
        self.assertIn(c.dominance, ("strict", "crossover"))
        self.assertFalse(c.crossover_meaningful)
        self.assertTrue(math.isinf(c.exponent_gap))

    def test_factorial_ranks_above_exponential(self):
        # worst case: n! vs 2^n·n^2 — the exponential DP wins
        v = self.v("hamiltonian_path_backtracking", "held_karp_tsp_exact_dp",
                   cases=("worst",))
        c = v.headline
        self.assertEqual(c.a.expr, "factorial(n)")
        self.assertEqual(c.b.expr, "2**n*n**2")
        self.assertEqual(c.winner, "B")
        # the two curves do cross, but only below n=8 — reported as not meaningful
        self.assertIn(c.dominance, ("strict", "crossover"))
        self.assertFalse(c.crossover_meaningful)

    def test_space_is_compared(self):
        v = self.v("merge_sort", "heap_sort")
        space = {c.case: c for c in v.space_cases}
        self.assertIn("worst", space)
        self.assertEqual(space["worst"].winner, "B")   # heap sort is O(1), merge is O(n)

    def test_no_space_flag(self):
        v = self.v("merge_sort", "heap_sort", compare_space=False)
        self.assertEqual(v.space_cases, [])

    def test_case_filter(self):
        v = self.v("quick_sort", "merge_sort", cases=("worst",))
        self.assertEqual([c.case for c in v.time_cases], ["worst"])

    def test_incomparable_tasks_warn(self):
        v = self.v("merge_sort", "binary_search")
        self.assertFalse(v.comparable)
        self.assertTrue(any("Different tasks" in w for w in v.warnings))

    def test_missing_case_warns(self):
        a = Algorithm.build("X", time_worst="n**2", space_worst="n")
        b = Algorithm.build("Y", time_worst="n", time_best="1", space_worst="1")
        v = compare(a, b)
        self.assertTrue(any("declared only for" in w for w in v.warnings))

    def test_custom_expression_roundtrip(self):
        a = Algorithm.build("Mine", time_worst="n**1.5", time_average="n**1.5",
                            space_worst="1", category="custom", task="t")
        b = Algorithm.build("Theirs", time_worst="n**2", time_average="n**2",
                            space_worst="n", category="custom", task="t")
        v = compare(a, b)
        self.assertEqual(v.headline.winner, "A")
        self.assertTrue(v.comparable)

    def test_overall_winner_and_conclusion(self):
        v = self.v("bubble_sort", "timsort")
        winner, reason = v.overall_winner
        self.assertEqual(winner, "timsort")
        self.assertIn("score", reason)
        self.assertIsInstance(v.conclusion(), str)
        self.assertGreater(len(v.conclusion()), 40)

    def test_samples_cover_requested_sizes(self):
        sizes = (10.0, 100.0, 1000.0)
        v = self.v("linear_search", "binary_search", sizes=sizes)
        self.assertEqual([n for n, _, _ in v.headline.samples], list(sizes))

    def test_to_dict_is_json_serialisable(self):
        payload = json.dumps(self.v("merge_sort", "quick_sort").to_dict(), default=str)
        self.assertIn("merge_sort", payload)


class TestRegistry(unittest.TestCase):
    def test_lookup_by_key_name_and_alias(self):
        reg = Registry()
        self.assertEqual(reg.get("merge_sort").name, "Merge Sort")
        self.assertEqual(reg.get("Merge Sort").key, "merge_sort")
        self.assertEqual(reg.get("merge-sort").key, "merge_sort")
        self.assertEqual(reg.get("MERGESORT").key, "merge_sort")

    def test_fuzzy_lookup_suggests(self):
        reg = Registry()
        with self.assertRaises(LookupError) as ctx:
            reg.get("marge_sort")
        self.assertIn("merge_sort", str(ctx.exception))

    def test_unknown_lookup(self):
        with self.assertRaises(LookupError):
            Registry().get("definitely_not_an_algorithm_xyz")

    def test_filters(self):
        reg = Registry()
        self.assertTrue(all(a.category == "sorting" for a in reg.filter(category="sorting")))
        self.assertGreater(len(reg.filter(category="sorting")), 5)
        self.assertTrue(reg.filter(query="dijkstra"))
        self.assertEqual(reg.comparable_with(reg.get("merge_sort"))[0].category, "sorting")

    def test_register_custom(self):
        reg = Registry()
        algo = register_custom("My Sort", time_worst="n*log2(n)", time_average="n*log2(n)",
                               space_worst="1", registry=reg)
        self.assertEqual(reg.get("my_sort").key, algo.key)
        self.assertEqual(algo.headline_time.resolved_label, "O(n log n)")

    def test_load_definitions_file(self):
        text = """
        [thing_one]
        name = Thing One
        category = demo
        task = do the thing
        time_worst = n**2
        time_average = n*log2(n)
        space_worst = n
        stable = true
        notes = insert below 32 elements   # trailing comment is stripped
        [thing_two]
        name = Thing Two
        task = do the thing
        time = n
        space = 1
        """
        reg = Registry()
        with tempfile.NamedTemporaryFile("w", suffix=".defs", delete=False) as fh:
            fh.write(text)
            path = fh.name
        try:
            loaded = load_definitions_into(path, reg)
        finally:
            os.unlink(path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(reg.get("thing_one").time.worst.expr, "n**2")
        self.assertTrue(reg.get("thing_one").stable)
        self.assertEqual(reg.get("thing_two").time.worst.expr, "n")
        # the trailing "# ..." is treated as a comment, the value survives
        self.assertEqual(reg.get("thing_one").notes, "insert below 32 elements")

    def test_definitions_file_requires_time(self):
        reg = Registry()
        with tempfile.NamedTemporaryFile("w", suffix=".defs", delete=False) as fh:
            fh.write("[broken]\nname = Broken\nspace_worst = n\n")
            path = fh.name
        try:
            with self.assertRaises(ValueError):
                load_definitions(path, reg)
        finally:
            os.unlink(path)


class TestReports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reg = registry()
        cls.v = compare(reg.get("merge_sort"), reg.get("quick_sort"))
        cls.v2 = compare(reg.get("bubble_sort"), reg.get("timsort"))

    def test_markdown(self):
        md = render_markdown(self.v2)
        for needle in ("# Algorithm comparison", "## Conclusion", "## Case-by-case verdict",
                       "| dimension |", "O(n^2)", "Timsort"):
            self.assertIn(needle, md)

    def test_json(self):
        data = json.loads(render_json(self.v2))
        self.assertEqual(data["a"]["key"], "bubble_sort")
        self.assertEqual(data["b"]["key"], "timsort")
        self.assertEqual(data["overall_winner"], "timsort")
        self.assertTrue(data["cases"])
        self.assertIn("growth_exponent", data["cases"][0]["a"])

    def test_html_is_self_contained(self):
        doc = render_html(self.v2)
        self.assertTrue(doc.startswith("<!doctype html>"))
        self.assertIn("<svg", doc)
        self.assertIn("Bubble Sort", doc)
        for banned in ("http://", "https://", "<script src", "<link "):
            self.assertNotIn(banned, doc, f"HTML must not reference external assets ({banned})")

    def test_terminal(self):
        text = render_terminal(self.v2, width=100)
        self.assertIn("Bubble Sort", text)
        self.assertIn("Conclusion", text)

    def test_ascii_chart_has_both_series(self):
        chart = ascii_chart(self.v2.headline, width=70, height=16)
        self.assertIn("A =", chart)
        self.assertIn("B =", chart)
        self.assertTrue(any(ch in chart for ch in "ABX"))

    def test_ascii_chart_degenerate(self):
        a = Algorithm.build("A", time_worst="2**n", space_worst="1", task="t")
        b = Algorithm.build("B", time_worst="n", space_worst="1", task="t")
        v = compare(a, b, sizes=(1e6, 1e9))
        self.assertIn("not enough finite samples", ascii_chart(v.headline))


class TestMatrix(unittest.TestCase):
    def test_ranking_orders_best_first(self):
        reg = registry()
        ranked = rank_algorithms(reg.filter(category="sorting"), case="worst")
        keys = [(c.rank, c.growth_exponent) for _, c in ranked]
        self.assertEqual(keys, sorted(keys), "ranking must be monotone")
        # the winner is linear-ish (counting sort's O(n+k)), never quadratic
        self.assertLess(ranked[0][1].growth_exponent, 1.1)
        self.assertGreater(ranked[-1][1].growth_exponent, 1.5)

    def test_matrix_renders(self):
        reg = registry()
        algos = reg.filter(category="sorting")[:6]
        coloured = render_matrix(algos, include_space=True, color=True)
        self.assertIn("algorithm", coloured)
        self.assertIn("★", coloured)
        plain = render_matrix(algos, include_space=True, color=False)
        self.assertNotIn("\x1b[", plain, "plain output must carry no ANSI codes")
        self.assertIn("*", plain)


class TestVerify(unittest.TestCase):
    def test_fit_exponent_recovers_quadratic(self):
        from algocomp.verify import Measurement, fit_exponent

        ms = [Measurement(n, 1e-6 * n ** 2, 1) for n in (100, 200, 400, 800, 1600)]
        fit = fit_exponent(ms)
        self.assertAlmostEqual(fit.exponent, 2.0, places=3)
        self.assertGreater(fit.r_squared, 0.99)

    def test_fit_exponent_recovers_linear(self):
        from algocomp.verify import Measurement, fit_exponent

        ms = [Measurement(n, 3e-7 * n, 1) for n in (1000, 2000, 4000, 8000)]
        self.assertAlmostEqual(fit_exponent(ms).exponent, 1.0, places=3)

    def test_verify_a_real_benchmark(self):
        from algocomp.verify import verify as run_verify

        reg = registry()
        report = run_verify(reg.get("bubble_sort"), sizes=(64, 128, 256, 512), budget=0.3)
        self.assertIsNotNone(report)
        self.assertIn(report.verdict,
                      {"matches", "roughly matches", "measured worse than declared",
                       "measured better than declared", "inconclusive"})
        self.assertGreater(report.fit.exponent, 1.3)   # clearly superlinear


class TestCli(unittest.TestCase):
    def test_parse_sizes(self):
        self.assertEqual(len(parse_sizes("10:1e6:4")), 4)
        self.assertEqual(parse_sizes("10,100,1000"), (10.0, 100.0, 1000.0))
        self.assertEqual(parse_sizes("default")[0], 10)
        with self.assertRaises(ValueError):
            parse_sizes("5")

    def test_cli_runs(self):
        for argv in (
            ["compare", "merge_sort", "quick_sort", "--format", "json"],
            ["compare", "bubble_sort", "timsort", "--format", "markdown", "--no-chart"],
            ["list", "--category", "sorting"],
            ["show", "binary_search"],
            ["matrix", "--category", "graph"],
            ["suggest", "--limit", "3"],
            ["categories"],
            ["benchmarks"],
        ):
            code = main(argv)
            self.assertIn(code, (0, None), f"{argv} exited {code}")

    def test_cli_version(self):
        with self.assertRaises(SystemExit):
            main(["--version"])

    def test_cli_definitions_flag(self):
        reg = Registry()
        self.assertIs(reg.get("merge_sort").category, "sorting")

    def test_cli_unknown_algorithm(self):
        self.assertEqual(main(["compare", "nope_a", "nope_b"]), 2)

    def test_cli_custom_add(self):
        code = main([
            "compare", "my_algo", "merge_sort", "--format", "json",
            "--add", "My Algo:n**3:n**3:n:custom:sort a list of comparable items",
        ])
        self.assertEqual(code, 0)

    def test_cli_out_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.md")
            code = main(["compare", "dijkstra_binary_heap", "bellman_ford",
                         "--format", "markdown", "--out", out])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertIn("Dijkstra", fh.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
