"""Does the estimator actually get Big-O right?

`tests/big_o_corpus.py` holds ~48 algorithms with textbook-known complexity.
These tests grade `algocomp.static_analysis` against that corpus:

* **exact tier** — the estimate must equal the ground truth, exactly. Any
  failure is a real bug in the analyzer, so this test is the gate.
* **conservative tier** — the finer class is not decidable from the AST shape
  (O(n log log n) for the sieve, O(V+E) for BFS). The estimator must still
  return a genuine *upper* bound, and it must return the class the corpus
  documents, so a change in behaviour fails loudly.
* **known limits** — a loop whose trip count is a data value (counting sort).
  The fallback is pinned so the limitation stays visible instead of drifting.

Plus the invariants that hold for every entry (ordering, JSON shape, no
crashes) and an end-to-end check through the `analyze` CLI.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from algocomp.cli import main
from algocomp.complexity import Complexity
from algocomp.static_analysis import (TIME_EXPRS, analyze_file, analyze_source,
                                      expr_label)

from .big_o_corpus import CASES, HOLDOUT, grade, holdout_summary, label, summarize


def _rank(expr: str) -> float:
    """Growth rank of an expression (higher = grows faster)."""
    return Complexity(expr).rank


class TestCorpus(unittest.TestCase):
    """The corpus itself must stay well formed."""

    def test_keys_are_unique(self):
        keys = [c.key for c in CASES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_sources_parse(self):
        for case in CASES:
            with self.subTest(case=case.key):
                est = analyze_source(case.source)
                self.assertNotIn("syntax error", " ".join(est.notes))

    def test_tiers_are_known(self):
        for case in CASES:
            with self.subTest(case=case.key):
                self.assertIn(case.tier, ("exact", "conservative", "limit"))

    def test_non_exact_cases_are_documented(self):
        for case in CASES:
            if case.tier == "exact":
                continue
            with self.subTest(case=case.key):
                self.assertTrue(
                    case.expect, "%s must state what the estimator returns" % case.key)
                self.assertGreater(
                    len(case.note), 40,
                    "%s must explain the gap in its note" % case.key)

    def test_corpus_covers_every_class_the_estimator_can_emit(self):
        covered = {c.expected for c in CASES}
        for expr in TIME_EXPRS:
            with self.subTest(expr=expr):
                self.assertIn(expr, covered,
                              "no corpus entry exercises %s" % expr)

    def test_corpus_has_enough_mass_to_be_meaningful(self):
        self.assertGreaterEqual(len(CASES), 40)
        self.assertGreaterEqual(
            sum(1 for c in CASES if c.is_exact), 40,
            "the exact tier is the gate; keep it broad")


class TestEstimatorAccuracy(unittest.TestCase):
    """The headline: every exact-tier case must match its ground truth."""

    @classmethod
    def setUpClass(cls):
        cls.report = summarize()

    def test_exact_tier_is_perfect(self):
        report = self.report
        self.assertEqual(
            report["exact_pass"], report["exact_total"],
            "%d/%d exact cases matched; misses: %s"
            % (report["exact_pass"], report["exact_total"],
               ", ".join(r.case.key for r in report["misses"])))

    def test_worst_case_matches_ground_truth(self):
        for r in self.report["results"]:
            with self.subTest(case=r.case.key):
                self.assertEqual(
                    r.got_time, r.case.expected,
                    "%s: expected %s, got %s (%s)"
                    % (r.case.key, label(r.case.expected), expr_label(r.got_time),
                       r.case.note))

    def test_best_and_average_match_when_the_corpus_states_them(self):
        for r in self.report["results"]:
            with self.subTest(case=r.case.key):
                self.assertTrue(r.best_ok, "%s: best %s != %s"
                                % (r.case.key, r.got_best, r.case.best))
                self.assertTrue(r.average_ok, "%s: average %s != %s"
                                % (r.case.key, r.got_average, r.case.average))

    def test_space_matches_when_the_corpus_states_it(self):
        checked = 0
        for r in self.report["results"]:
            if r.case.space is None:
                continue
            checked += 1
            with self.subTest(case=r.case.key):
                self.assertEqual(r.got_space, r.case.space,
                                 "%s: space %s != %s"
                                 % (r.case.key, expr_label(r.got_space),
                                    label(r.case.space)))
        self.assertGreaterEqual(checked, 25)


class TestConservativeAndLimitTiers(unittest.TestCase):
    """Documented gaps: valid upper bounds, pinned fallbacks, low confidence."""

    def test_conservative_results_are_real_upper_bounds(self):
        for r in grade():
            if r.case.tier != "conservative":
                continue
            with self.subTest(case=r.case.key):
                self.assertGreaterEqual(
                    _rank(r.got_time), _rank(r.case.time),
                    "%s: %s is below the true %s"
                    % (r.case.key, expr_label(r.got_time), label(r.case.time)))

    def test_conservative_and_limit_results_match_the_documented_value(self):
        for r in grade():
            if r.case.tier == "exact":
                continue
            with self.subTest(case=r.case.key):
                self.assertEqual(r.got_time, r.case.expect)
                self.assertEqual(expr_label(r.got_time),
                                 expr_label(r.case.expect))

    def test_low_confidence_cases_are_the_uncertain_ones(self):
        for r in grade():
            if r.case.tier != "exact":
                with self.subTest(case=r.case.key):
                    self.assertLess(r.confidence, 0.7,
                                    "%s is a documented gap; it should say so "
                                    "with a low confidence" % r.case.key)

    def test_every_estimate_says_it_is_a_heuristic(self):
        for r in grade():
            with self.subTest(case=r.case.key):
                joined = " ".join(r.estimate.notes).lower()
                self.assertIn("heuristic", joined)


class TestHoldout(unittest.TestCase):
    """Cases written after the rules were settled: the generalization check."""

    @classmethod
    def setUpClass(cls):
        cls.report = holdout_summary()

    def test_holdout_matches_the_pinned_output(self):
        for r in self.report["results"]:
            with self.subTest(case=r.case.key):
                self.assertEqual(
                    r.got_time, r.case.expected,
                    "%s: the analyzer changed its answer on unseen code "
                    "(truth %s)" % (r.case.key, label(r.case.time)))

    def test_holdout_never_under_estimates(self):
        under = [r.case.key for r in self.report["under_estimates"]]
        self.assertEqual(under, [],
                         "these are reported *below* the true complexity: %s"
                         % ", ".join(under))

    def test_holdout_exact_rate_stays_high(self):
        report = self.report
        self.assertGreaterEqual(
            report["exact"] / report["total"], 0.8,
            "only %d/%d holdout cases landed on the exact class"
            % (report["exact"], report["total"]))

    def test_holdout_is_a_real_sample(self):
        self.assertGreaterEqual(len(HOLDOUT), 12)


class TestEstimatorInvariants(unittest.TestCase):
    """Properties that must hold for any input, ground truth or not."""

    def test_best_average_worst_are_ordered(self):
        for r in grade():
            with self.subTest(case=r.case.key):
                self.assertLessEqual(_rank(r.got_best), _rank(r.got_average))
                self.assertLessEqual(_rank(r.got_average), _rank(r.got_time))

    def test_confidence_stays_in_range(self):
        for r in grade():
            with self.subTest(case=r.case.key):
                self.assertGreaterEqual(r.confidence, 0.0)
                self.assertLessEqual(r.confidence, 1.0)

    def test_to_dict_is_json_serialisable_and_complete(self):
        for r in grade():
            est = r.estimate
            with self.subTest(case=r.case.key):
                payload = json.loads(json.dumps(est.to_dict()))
                self.assertEqual(payload["expressions"]["time_worst"], r.got_time)
                self.assertEqual(payload["time_worst"], expr_label(r.got_time))
                self.assertTrue(payload["notes"])
                self.assertIn("function", payload["details"])

    def test_emitted_expressions_are_from_the_canonical_set(self):
        for r in grade():
            for expr in (r.got_best, r.got_average, r.got_time, r.got_space):
                with self.subTest(case=r.case.key, expr=expr):
                    self.assertIn(expr, TIME_EXPRS)

    def test_unparsable_source_never_raises(self):
        est = analyze_source("def main(:\n  broken(\n")
        self.assertEqual(est.confidence, 0.1)
        self.assertEqual(est.time_worst, "n")
        self.assertTrue(any("syntax error" in n for n in est.notes))

    def test_empty_source_is_constant(self):
        est = analyze_source("")
        self.assertEqual(est.time_worst, "1")
        self.assertEqual(est.space, "1")

    def test_analysis_is_deterministic(self):
        for case in CASES:
            with self.subTest(case=case.key):
                first = analyze_source(case.source).to_dict()
                second = analyze_source(case.source).to_dict()
                self.assertEqual(first, second)


class TestCLIAnalyze(unittest.TestCase):
    """`algo-compare analyze` on real files from the corpus."""

    def test_cli_analyze_agrees_with_the_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in CASES:
                with self.subTest(case=case.key):
                    path = os.path.join(tmp, case.key + ".py")
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(case.source)
                    est = analyze_file(path)
                    self.assertEqual(est.time_worst, case.expected)
                    self.assertEqual(est.details["path"], path)

    def test_cli_analyze_json_emits_the_expected_class(self):
        case = next(c for c in CASES if c.key == "merge_sort")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(case.source)
            out = os.path.join(tmp, "m.json")
            self.assertEqual(main(["analyze", path, "--json", "-o", out]), 0)
            with open(out, encoding="utf-8") as fh:
                payload = json.load(fh)
        self.assertEqual(payload["time_worst"], "O(n log n)")
        self.assertEqual(payload["space"], "O(n)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
