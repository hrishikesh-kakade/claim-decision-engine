"""Unit tests. Run with: python -m unittest discover -s tests
(or `pytest tests` once pytest is installed -- unittest-style tests work
under pytest too)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.policy_rules import PolicyParameters  # noqa: E402

CHUNKS = ROOT / "data" / "policy_chunks.json"


class TestPolicyParameterExtraction(unittest.TestCase):
    """Every numeric parameter the rule engine depends on must be found in
    the supplied policy text, with a valid page/chunk citation -- if any of
    these ever come back None, the coverage agent will (by design) treat
    that dimension as missing evidence rather than silently using a wrong
    default, so this test is really a regression guard on the regexes."""

    @classmethod
    def setUpClass(cls):
        cls.pp = PolicyParameters(CHUNKS)

    def test_sub_limit_percentages(self):
        self.assertAlmostEqual(self.pp.room_pct.value, 0.01)
        self.assertAlmostEqual(self.pp.icu_pct.value, 0.02)
        self.assertAlmostEqual(self.pp.doctor_fee_pct.value, 0.25)
        self.assertAlmostEqual(self.pp.other_expenses_pct.value, 0.40)
        self.assertAlmostEqual(self.pp.domiciliary_pct.value, 0.20)

    def test_windows_and_waiting_periods(self):
        self.assertEqual(self.pp.pre_hosp_days.value, 30)
        self.assertEqual(self.pp.post_hosp_days.value, 60)
        self.assertEqual(self.pp.initial_waiting_days.value, 30)
        self.assertEqual(self.pp.pre_existing_months.value, 48)

    def test_every_param_has_a_traceable_chunk_id(self):
        for name in ("room_pct", "doctor_fee_pct", "other_expenses_pct", "pre_hosp_days", "post_hosp_days"):
            p = getattr(self.pp, name)
            self.assertIsNotNone(p.chunk_id, f"{name} has no source chunk_id")
            self.assertTrue(any(c["chunk_id"] == p.chunk_id for c in self.pp.chunks))


if __name__ == "__main__":
    unittest.main()
