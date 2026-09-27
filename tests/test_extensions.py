"""Tests for analyze / benchmark / infer (new subsystems, stdlib only)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from algocomp.benchmark import run_benchmark
from algocomp.cli import main
from algocomp.curve_fit import CANDIDATES, fit_points
from algocomp.static_analysis import analyze_source


def _write(tmp, name, code):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(code)
    return path


class TestStaticAnalysis(unittest.TestCase):
    def test_single_loop_is_linear(self):
        est = analyze_source("def main(a):\n    s = 0\n    for x in a:\n        s += x\n    return s\n")
        self.assertEqual(est.time_worst, "n")
        self.assertGreaterEqual(est.confidence, 0.5)
        self.assertTrue(est.notes)

    def test_nested_loop_is_quadratic(self):
        est = analyze_source(
            "def main(a):\n    n = len(a)\n"
            "    for i in range(n):\n        for j in range(n):\n            pass\n")
        self.assertEqual(est.time_worst, "n**2")

    def test_triangular_loop_is_still_quadratic(self):
        # range(i) sweeps ~n/2 elements per pass, so the nest stays quadratic
        est = analyze_source(
            "def main(n):\n    for i in range(n):\n"
            "        for j in range(i):\n            pass\n")
        self.assertEqual(est.time_worst, "n**2")

    def test_constant_stride_stays_quadratic(self):
        # a stride read from a local constant is not the harmonic case
        est = analyze_source(
            "def main(n):\n    k = 2\n    for i in range(n):\n"
            "        for j in range(0, n, k):\n            pass\n")
        self.assertEqual(est.time_worst, "n**2")

    def test_variable_stride_is_not_quadratic(self):
        # regression: sieve-style `range(i * i, n + 1, i)` is a harmonic sum
        est = analyze_source(
            "def main(n):\n    for i in range(n):\n"
            "        for j in range(i * i, n + 1, i):\n            pass\n")
        self.assertEqual(est.time_worst, "n*log2(n)")
        self.assertLess(est.confidence, 0.5)
        self.assertTrue(any("stride" in note for note in est.notes))

    def test_variable_stride_inside_while(self):
        # regression: the stride variable comes from an enclosing `while`,
        # which has no loop target of its own
        code = ("def main(n):\n"
                "    sieve = bytearray([1]) * (n + 1)\n"
                "    i = 2\n"
                "    while i * i <= n:\n"
                "        if sieve[i]:\n"
                "            for j in range(i * i, n + 1, i):\n"
                "                sieve[j] = 0\n"
                "        i += 1\n"
                "    return sieve\n")
        est = analyze_source(code)
        self.assertEqual(est.time_worst, "n*log2(n)")
        self.assertNotEqual(est.time_worst, "n**2")
        self.assertEqual(est.details["variable_stride_depths"], [2])

    def test_triple_nest_with_strided_inner(self):
        est = analyze_source(
            "def main(n):\n    i = 1\n    while n:\n"
            "        for x in range(n):\n"
            "            for y in range(i, n, i):\n                pass\n"
            "        i += 1\n")
        self.assertEqual(est.time_worst, "n**2*log2(n)")

    def test_halving_while_is_log(self):
        code = ("def main(a, t):\n    lo, hi = 0, len(a) - 1\n"
                "    while lo <= hi:\n        mid = (lo + hi) // 2\n"
                "        if a[mid] == t:\n            return mid\n"
                "        elif a[mid] < t:\n            lo = mid + 1\n"
                "        else:\n            hi = mid - 1\n    return -1\n")
        self.assertEqual(analyze_source(code).time_worst, "log2(n)")

    def test_exponential_recursion_flagged_uncertain(self):
        est = analyze_source(
            "def main(n):\n    if n <= 1:\n        return 1\n"
            "    return main(n-1) + main(n-2)\n")
        self.assertEqual(est.time_worst, "2**n")
        self.assertLess(est.confidence, 0.6)

    def test_sort_call_detected(self):
        est = analyze_source("def main(a):\n    return sorted(a)\n")
        self.assertEqual(est.time_worst, "n*log2(n)")

    def test_syntax_error_never_raises(self):
        est = analyze_source("def main(:\n  broken")
        self.assertEqual(est.confidence, 0.1)

    def test_sequence_multiplication_detected_as_linear(self):
        est = analyze_source("n = int(input())\nprint(n * '*')\n")
        self.assertEqual(est.time_worst, "n")
        self.assertEqual(est.space, "n")

    def test_list_multiplication_detected_as_linear(self):
        est = analyze_source("def build(n):\n    return [0] * n\n")
        self.assertEqual(est.time_worst, "n")
        self.assertEqual(est.space, "n")


class TestCurveFit(unittest.TestCase):
    def test_linear_data_fits_linear(self):
        rep = fit_points([(100, 0.01), (1000, 0.1), (10000, 1.0)])
        self.assertEqual(rep.best_fit, "O(n)")
        self.assertGreater(rep.fit_score, 0.9)

    def test_quadratic_data_fits_quadratic(self):
        rep = fit_points([(100, 0.05), (1000, 5.0), (10000, 500.0)])
        self.assertEqual(rep.best_fit, "O(n^2)")

    def test_dict_shape(self):
        rep = fit_points([(100, 0.01), (1000, 0.1), (10000, 1.0)])
        d = rep.to_dict()
        self.assertEqual(d["best_fit"], "O(n)")
        self.assertIn("ranking", d)
        self.assertIn("fit_score", d)

    def test_too_few_points_warns(self):
        rep = fit_points([(100, 0.01)])
        self.assertTrue(rep.warnings)

    def test_constant_data_fits_constant(self):
        # regression: constant measurements used to tie every model at R^2=1
        rep = fit_points([(100, 0.01), (1000, 0.01), (10000, 0.01)])
        self.assertEqual(rep.best_fit, "O(1)")

    def test_n_sqrt_n_data_fits_n_sqrt_n(self):
        # regression: n^1.5 used to be mislabelled as O(n^2)
        pts = [(n, 5e-7 * n ** 1.5) for n in (1000, 4000, 16000, 64000)]
        rep = fit_points(pts)
        self.assertEqual(rep.best_fit, "O(n sqrt(n))")
        self.assertAlmostEqual(rep.measured_exponent, 1.5, places=2)

    def test_measured_trial_division_profile(self):
        # real timings: is_prime(k) for every k in 1..n
        rep = fit_points([(1000, 0.00096), (4000, 0.00756),
                          (16000, 0.05918), (64000, 0.51624)])
        self.assertEqual(rep.best_fit, "O(n sqrt(n))")

    def test_measured_sieve_profile(self):
        # real timings: sieve of Eratosthenes, truly O(n log log n)
        rep = fit_points([(1000, 0.00141), (4000, 0.00663),
                          (16000, 0.03296), (64000, 0.11820)])
        self.assertEqual(rep.best_fit, "O(n log log n)")

    def test_measured_exponent_reported(self):
        rep = fit_points([(1000, 0.00096), (4000, 0.00756),
                          (16000, 0.05918), (64000, 0.51624)])
        self.assertAlmostEqual(rep.measured_exponent, 1.51, places=2)
        self.assertAlmostEqual(rep.to_dict()["measured_exponent"], 1.51, places=2)

    def test_candidate_set_covers_common_growth(self):
        labels = {label for label, _ in CANDIDATES}
        for expected in ("O(1)", "O(log n)", "O(n)", "O(n log n)",
                         "O(n sqrt(n))", "O(n^2)", "O(n^3)"):
            self.assertIn(expected, labels)


class TestBenchmark(unittest.TestCase):
    def test_benchmark_linear_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "t.py",
                          "def main(a):\n    s = 0\n    for x in a:\n        s += x\n    return s\n")
            res = run_benchmark(path, [50, 200, 800], repeats=2)
            self.assertGreaterEqual(len(res.points), 2)
            self.assertTrue(all(p.seconds >= 0 for p in res.points))
            self.assertTrue(all(p.peak_bytes >= 0 for p in res.points))

    def test_missing_function_reports_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "t.py", "x = 1\n")
            res = run_benchmark(path, [50, 200], repeats=1, function="nope")
            self.assertEqual(res.points, [])
            self.assertTrue(res.warnings)


class TestCLI(unittest.TestCase):
    def test_analyze_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "t.py", "def main(a):\n    return sum(a)\n")
            self.assertEqual(main(["analyze", path]), 0)
            self.assertEqual(main(["analyze", path, "--json"]), 0)

    def test_analyze_missing_file(self):
        self.assertEqual(main(["analyze", "no-such-file.py"]), 2)

    def test_benchmark_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "t.py", "def main(a):\n    return sum(a)\n")
            code = main(["benchmark", path, "--sizes", "50,200",
                         "--repeats", "2"])
            self.assertEqual(code, 0)

    def test_infer_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "t.py", "def main(a):\n    return sum(a)\n")
            code = main(["infer", path, "--sizes", "50,200,800",
                         "--repeats", "2"])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
