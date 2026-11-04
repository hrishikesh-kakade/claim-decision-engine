"""Focused tests for policy monetary-limit calculations."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.agents.coverage_exclusion import _domiciliary, _sub_limits
from backend.models import ClaimCase
from backend.policy_rules import Param, PolicyParameters

CHUNKS = ROOT / "data" / "policy_chunks.json"


class TestCoverageCalculations(unittest.TestCase):

    def setUp(self):
        # Each test gets fresh policy parameters to avoid shared mutations.
        self.pp = PolicyParameters(CHUNKS)

    def test_icu_limit_uses_basic_sum_insured(self):
        case = self.make_case(
            basic_sum_insured_inr=300_000,
            expenses_inr={
                "room": 0,
                "icu": 20_000,
                "doctor_fees": 0,
                "medicines_diagnostics": 0,
                "ambulance": 0,
            },
        )
        self.pp.icu_pct = Param(0.02, "ICU-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)
        icu = self.get_limit(
            limits, "Intensive Care Unit (ICU) expenses"
        )

        self.assertEqual(icu["cap_inr"], 6_000)
        self.assertEqual(icu["payable_inr"], 6_000)
        self.assertEqual(icu["cap_basis"], "Basic Sum Insured")
        self.assertFalse(self.has_uncertainty(findings))

    def test_missing_basic_sum_insured_does_not_calculate_icu_cap(self):
        case = self.make_case(
            basic_sum_insured_inr=None,
            expenses_inr={
                "room": 0,
                "icu": 20_000,
                "doctor_fees": 0,
                "medicines_diagnostics": 0,
                "ambulance": 0,
            },
        )
        self.pp.icu_pct = Param(0.02, "ICU-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)

        icu_limits = [
            x for x in limits
            if x["limit_name"] == "Intensive Care Unit (ICU) expenses"
        ]

        self.assertEqual(icu_limits, [])
        self.assertTrue(self.has_uncertainty(findings))

    def test_icu_is_included_in_expenses_total(self):
        case = self.make_case(
            expenses_inr={
                "room": 10_000,
                "icu": 20_000,
                "doctor_fees": 30_000,
                "medicines_diagnostics": 40_000,
                "ambulance": 1_000,
            },
        )

        self.assertEqual(case.expenses_inr.total, 101_000)


    def make_case(self, **overrides):
        data = {
            "case_id": "TEST-001",
            "policy_id": "POL-001",
            "policy_start_date": "2025-01-01",
            "claim_date": "2026-01-01",
            "sum_insured_inr": 500_000,
            "expenses_inr": {
                "room": 20_000,
                "doctor_fees": 30_000,
                "medicines_diagnostics": 40_000,
                "ambulance": 2_000,
            },
        }
        data.update(overrides)
        return ClaimCase(**data)

    def get_limit(self, limits, name):
        return next(x for x in limits if x["limit_name"] == name)

    def has_uncertainty(self, findings):
        return any(f.supports_decision == "uncertain" for f in findings)

    def test_room_limit_uses_basic_sum_insured(self):
        case = self.make_case(
            basic_sum_insured_inr=300_000,
            expenses_inr={
                "room": 20_000,
                "doctor_fees": 0,
                "medicines_diagnostics": 0,
                "ambulance": 0,
            },
        )
        self.pp.room_pct = Param(0.01, "ROOM-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)
        room = self.get_limit(
            limits, "Room, boarding & nursing expenses"
        )

        self.assertEqual(room["cap_inr"], 3_000)
        self.assertEqual(room["payable_inr"], 3_000)
        self.assertEqual(room["cap_basis"], "Basic Sum Insured")
        self.assertFalse(self.has_uncertainty(findings))

    def test_doctor_fee_limit_uses_sum_assured(self):
        case = self.make_case(
            sum_assured_inr=200_000,
            expenses_inr={
                "room": 0,
                "doctor_fees": 30_000,
                "medicines_diagnostics": 0,
                "ambulance": 0,
            },
        )
        self.pp.doctor_fee_pct = Param(0.25, "DOCTOR-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)
        doctor = self.get_limit(
            limits, "Doctor/surgeon/consultant fees"
        )

        self.assertEqual(doctor["cap_inr"], 50_000)
        self.assertEqual(doctor["payable_inr"], 30_000)
        self.assertEqual(doctor["cap_basis"], "Sum Assured")
        self.assertFalse(self.has_uncertainty(findings))

    def test_other_expenses_limit_uses_sum_insured(self):
        case = self.make_case(
            expenses_inr={
                "room": 0,
                "doctor_fees": 0,
                "medicines_diagnostics": 40_000,
                "ambulance": 0,
            },
        )
        self.pp.other_expenses_pct = Param(0.40, "OTHER-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)
        other = self.get_limit(
            limits, "Medicines, diagnostics & similar expenses"
        )

        self.assertEqual(other["cap_inr"], 200_000)
        self.assertEqual(other["payable_inr"], 40_000)
        self.assertEqual(other["cap_basis"], "Sum Insured")
        self.assertFalse(self.has_uncertainty(findings))

    def test_domiciliary_limit_uses_basic_sum_insured(self):
        case = self.make_case(
            basic_sum_insured_inr=300_000,
            treatment={"hospital_room_unavailable": True},
        )
        self.pp.domiciliary_pct = Param(0.20, "DOM-TEST", 1)

        finding, limit = _domiciliary(case, {}, self.pp)

        self.assertEqual(limit["cap_inr"], 60_000)
        self.assertEqual(limit["payable_inr"], 60_000)
        self.assertEqual(limit["cap_basis"], "Basic Sum Insured")
        self.assertNotEqual(finding.supports_decision, "uncertain")

    def test_ambulance_limit_uses_lower_of_basic_si_percentage_and_flat_cap(self):
        case = self.make_case(
            basic_sum_insured_inr=50_000,
            expenses_inr={
                "room": 0,
                "doctor_fees": 0,
                "medicines_diagnostics": 0,
                "ambulance": 2_000,
            },
        )
        self.pp.ambulance_pct = Param(0.01, "AMB-PCT-TEST", 1)
        self.pp.ambulance_flat = Param(1_000, "AMB-FLAT-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)
        ambulance = self.get_limit(limits, "Ambulance charges")

        self.assertEqual(ambulance["cap_inr"], 500)
        self.assertEqual(ambulance["payable_inr"], 500)
        self.assertEqual(ambulance["cap_basis"], "Basic Sum Insured")
        self.assertFalse(self.has_uncertainty(findings))

    def test_missing_basic_sum_insured_does_not_calculate_room_cap(self):
        case = self.make_case(basic_sum_insured_inr=None)
        self.pp.room_pct = Param(0.01, "ROOM-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)

        room_limits = [
            x for x in limits
            if x["limit_name"] == "Room, boarding & nursing expenses"
        ]

        self.assertEqual(room_limits, [])
        self.assertTrue(self.has_uncertainty(findings))

    def test_missing_sum_assured_does_not_calculate_doctor_fee_cap(self):
        case = self.make_case(sum_assured_inr=None)
        self.pp.doctor_fee_pct = Param(0.25, "DOCTOR-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)

        doctor_limits = [
            x for x in limits
            if x["limit_name"] == "Doctor/surgeon/consultant fees"
        ]

        self.assertEqual(doctor_limits, [])
        self.assertTrue(self.has_uncertainty(findings))

    def test_missing_basic_sum_insured_does_not_calculate_ambulance_cap(self):
        case = self.make_case(
            basic_sum_insured_inr=None,
            expenses_inr={
                "room": 0,
                "doctor_fees": 0,
                "medicines_diagnostics": 0,
                "ambulance": 2_000,
            },
        )
        self.pp.ambulance_pct = Param(0.01, "AMB-PCT-TEST", 1)
        self.pp.ambulance_flat = Param(1_000, "AMB-FLAT-TEST", 1)

        findings, limits = _sub_limits(case, {}, self.pp)

        ambulance_limits = [
            x for x in limits
            if x["limit_name"] == "Ambulance charges"
        ]

        self.assertEqual(ambulance_limits, [])
        self.assertTrue(self.has_uncertainty(findings))

    def test_missing_basic_sum_insured_does_not_calculate_domiciliary_cap(self):
        case = self.make_case(
            basic_sum_insured_inr=None,
            treatment={"hospital_room_unavailable": True},
        )
        self.pp.domiciliary_pct = Param(0.20, "DOM-TEST", 1)

        finding, limit = _domiciliary(case, {}, self.pp)

        self.assertIsNone(limit)
        self.assertEqual(finding.supports_decision, "uncertain")

    def test_missing_domiciliary_percentage_is_uncertain(self):
        case = self.make_case(
            basic_sum_insured_inr=300_000,
            treatment={"hospital_room_unavailable": True},
        )
        self.pp.domiciliary_pct = Param(None, None, None)

        finding, limit = _domiciliary(case, {}, self.pp)

        self.assertIsNone(limit)
        self.assertEqual(finding.supports_decision, "uncertain")


if __name__ == "__main__":
    unittest.main()
