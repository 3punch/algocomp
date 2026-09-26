"""Tests for analyze / benchmark / infer (new subsystems, stdlib only)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from algocomp.benchmark import run_benchmark
from algocomp.cli import main
from algocomp.curve_fit import fit_points
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
