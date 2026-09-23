"""End-to-end regression test: every supplied public case must reproduce
its expected decision (see eval/expected_outcomes.json), every response
must pass the Validation Agent, and abstention must actually happen for
the cases that require it. This is deliberately the same check the eval
script does, kept here too so `python -m unittest` alone catches a
regression without needing to run the full eval/reporting pipeline."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.models import ClaimCase  # noqa: E402
from backend.orchestrator import ClaimEngine  # noqa: E402

PUBLIC_CASES = ROOT / "data" / "public_test_cases.json"
EXPECTED = ROOT / "eval" / "expected_outcomes.json"


class TestPublicCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ClaimEngine()
        cls.cases = json.loads(PUBLIC_CASES.read_text())
        cls.expected = json.loads(EXPECTED.read_text())

    def test_all_public_cases_match_expected_decision(self):
        mismatches = []
        for raw in self.cases:
            case = ClaimCase.model_validate(raw)
            resp = self.engine.analyze(case)
            expected_decision = self.expected[case.case_id]["expected_decision"]
            if resp.decision != expected_decision:
                mismatches.append((case.case_id, expected_decision, resp.decision))
        self.assertEqual(mismatches, [], f"Decision mismatches: {mismatches}")

    def test_all_public_cases_pass_validation(self):
        failures = []
        for raw in self.cases:
            case = ClaimCase.model_validate(raw)
            resp = self.engine.analyze(case)
            if resp.validation.status != "PASS":
                failures.append((case.case_id, resp.validation.unsupported_claims))
        self.assertEqual(failures, [], f"Validation failures: {failures}")

    def test_at_least_two_needs_review_cases(self):
        n = 0
        for raw in self.cases:
            case = ClaimCase.model_validate(raw)
            resp = self.engine.analyze(case)
            if resp.decision == "NEEDS_REVIEW":
                n += 1
        self.assertGreaterEqual(n, 2)


if __name__ == "__main__":
    unittest.main()
