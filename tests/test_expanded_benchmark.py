"""Structural checks for the 36-case policy-aware decision benchmark."""
from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
import common  # noqa: E402


class TestExpandedDecisionBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = common.load_cases()
        cls.expected = json.loads(common.EXPECTED.read_text(encoding="utf-8"))

    def test_exactly_36_unique_cases_and_complete_gold(self):
        ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(ids), 36)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(self.expected) - {"_method"})

    def test_all_five_decision_classes_are_represented(self):
        counts = Counter(
            self.expected[case["case_id"]]["expected_decision"]
            for case in self.cases
        )
        self.assertEqual(counts["ADMISSIBLE"], 6)
        self.assertEqual(counts["ADMISSIBLE_WITH_LIMITS"], 6)
        self.assertEqual(counts["PARTIALLY_ADMISSIBLE"], 6)
        self.assertEqual(counts["NOT_ADMISSIBLE"], 6)
        self.assertEqual(counts["NEEDS_REVIEW"], 12)

    def test_new_cases_have_distinct_monetary_bases(self):
        new_cases = [c for c in self.cases if c["case_id"].startswith("NEW-")]
        self.assertEqual(len(new_cases), 18)
        for case in new_cases:
            self.assertIsNotNone(case.get("basic_sum_insured_inr"))
            self.assertIsNotNone(case.get("sum_assured_inr"))
            self.assertIsNotNone(case.get("sum_insured_inr"))

    def test_partial_cases_have_explicit_out_of_window_evidence(self):
        partial = [c for c in self.cases if c["case_id"].startswith("NEW-PAR-")]
        self.assertEqual(len(partial), 6)
        for case in partial:
            self.assertTrue(case.get("expense_timing"))
            self.assertTrue(case["expense_timing"]["same_condition_confirmed"])


if __name__ == "__main__":
    unittest.main()
