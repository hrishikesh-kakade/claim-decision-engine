"""Case Analysis Agent.

Extracts structured facts from the raw claim case, decides which policy
decision dimensions actually apply to this case (a domiciliary case does
not need a day-care check; a case with no pre-existing flag does not need
the PED waiting-period dimension), flags missing fields, and produces the
natural-language search queries the Policy Evidence Agent will run.
"""
from __future__ import annotations

from datetime import date

from ..models import CaseAnalysis, ClaimCase, InvestigationDimension


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def analyze_case(case: ClaimCase) -> CaseAnalysis:
    t = case.treatment
    diag_proc = f"{t.diagnosis or ''} {t.procedure or ''}".lower()

    dims: list[InvestigationDimension] = [
        InvestigationDimension(
            dimension="initial_waiting_period",
            question="Does the 30-day initial waiting period bar this claim?",
        ),
    ]
    if t.type != "domiciliary":
        dims.append(InvestigationDimension(
            dimension="hospital_definition",
            question="Does the treating facility meet the Policy's definition of Hospital?",
        ))

    if t.pre_existing:
        dims.append(InvestigationDimension(
            dimension="pre_existing_disease_waiting",
            question="Has the 48-month pre-existing-disease waiting period elapsed (with any portability credit)?",
        ))

    first_year_disease_terms = [
        "cataract", "prostat", "myomectomy", "hysterectomy", "hernia", "hydrocele",
        "fistula", "piles", "arthritis", "gout", "rheumatism", "joint replacement",
        "sinusitis", "stone in", "urinary", "biliary", "dilatation and curettage",
        "tumor", "tumour", "cyst", "nodule", "polyp", "adenoid", "hemorrhoid",
        "dialysis", "tonsil", "gastric", "duodenal ulcer",
    ]
    if any(term in diag_proc for term in first_year_disease_terms):
        dims.append(InvestigationDimension(
            dimension="first_year_named_disease_waiting",
            question="Does the 1st-year specified-disease waiting period bar this claim (subject to portability credit)?",
        ))

    if t.type != "domiciliary" and ((t.admission_hours is not None and t.admission_hours < 24) or (t.type == "day_care")):
        dims.append(InvestigationDimension(
            dimension="day_care_admission_duration",
            question="Does the treatment qualify for the <24-hour day-care waiver?",
        ))

    if t.type == "domiciliary":
        dims.append(InvestigationDimension(
            dimension="domiciliary_treatment_conditions",
            question="Are the Policy's Domiciliary Treatment conditions satisfied, and what sub-limit applies?",
        ))
    else:
        dims.append(InvestigationDimension(
            dimension="sub_limits_and_deductions",
            question="What category sub-limits apply to the claimed expenses, and what is payable?",
        ))

    if "cosmetic" in diag_proc or "aesthetic" in diag_proc:
        dims.append(InvestigationDimension(
            dimension="cosmetic_exclusion",
            question="Is the treatment excluded as cosmetic/aesthetic treatment?",
        ))

    if t.experimental:
        dims.append(InvestigationDimension(
            dimension="experimental_treatment_exclusion",
            question="Is the treatment excluded/unsupported as unproven or experimental treatment?",
        ))

    exp_timing = case.expense_timing or {}
    if exp_timing or case.expenses_inr.pre_hospitalization or case.expenses_inr.post_hospitalization:
        dims.append(InvestigationDimension(
            dimension="pre_post_hospitalization_window",
            question="Do the pre/post-hospitalisation expenses fall within the Policy's time windows?",
        ))

    prior_policy = case.prior_policy or {}
    if prior_policy or (case.prior_insurer_continuous_years or 0) > 0:
        dims.append(InvestigationDimension(
            dimension="portability_credit",
            question="What waiting-period credit applies from prior continuous coverage / portability?",
        ))

    dims.append(InvestigationDimension(
        dimension="other_named_exclusions",
        question="Does the diagnosis/procedure fall under maternity, self-injury/alcohol, or war/terrorism exclusions?",
    ))

    missing_fields = []
    ev = case.evidence_context or {}
    if "hospital_registered" in ev and ev.get("hospital_registered") is None:
        missing_fields.append("evidence_context.hospital_registered (unknown)")
    if "medical_necessity_confirmed" in ev and ev.get("medical_necessity_confirmed") is None:
        missing_fields.append("evidence_context.medical_necessity_confirmed (unknown)")
    if ev.get("hospital_minimum_criteria_documented") is False:
        missing_fields.append("evidence_context.hospital_minimum_criteria_documented=false")
    if not case.hospital.network_provider and "hospital_registered" not in ev and t.type != "domiciliary":
        missing_fields.append("hospital registration/minimum-criteria evidence not supplied for a non-network facility")

    checklist = [f"[{d.dimension}] {d.question}" for d in dims]
    queries = _build_queries(dims, diag_proc)

    irrelevant = []
    if case.hospital.name:
        irrelevant.append(
            "hospital.name: the facility's name does not itself affect coverage under the supplied "
            "policy wording -- only its Hospital-definition status and network status do."
        )
    if case.patient.age is not None:
        irrelevant.append(
            "patient.age: the supplied policy wording contains no age-banded eligibility clause "
            "relevant to this claim type, so age does not change this decision."
        )

    facts = {
        "sum_insured_inr": case.sum_insured_inr,
        "policy_start_date": case.policy_start_date,
        "claim_date": case.claim_date,
        "days_since_policy_start": (_parse_date(case.claim_date) - _parse_date(case.policy_start_date)).days,
        "continuous_coverage_months": case.continuous_coverage_months or 0,
        "prior_insurer_continuous_years": case.prior_insurer_continuous_years or 0,
        "treatment_type": t.type,
        "admission_hours": t.admission_hours,
        "diagnosis": t.diagnosis,
        "procedure": t.procedure,
        "pre_existing": bool(t.pre_existing),
        "experimental": bool(t.experimental),
        "network_provider": case.hospital.network_provider,
        "total_expenses_claimed_inr": case.expenses_inr.total,
    }

    return CaseAnalysis(
        case_id=case.case_id,
        facts=facts,
        decision_dimensions=dims,
        missing_fields=missing_fields,
        investigation_checklist=checklist,
        search_queries=queries,
        irrelevant_attributes=irrelevant,
    )


def _build_queries(dims: list[InvestigationDimension], diag_proc: str) -> list[str]:
    q = []
    base = {
        "initial_waiting_period": "initial 30 day waiting period exception continuous coverage",
        "hospital_definition": "definition of Hospital registered minimum criteria in-patient beds",
        "pre_existing_disease_waiting": "pre-existing diseases waiting period 48 months portability reduction",
        "first_year_named_disease_waiting": f"first year waiting period specified diseases {diag_proc}",
        "day_care_admission_duration": "day care treatment less than 24 hours specified procedures Eye Surgery Dialysis",
        "domiciliary_treatment_conditions": "domiciliary treatment definition room unavailable sub-limit",
        "sub_limits_and_deductions": "room boarding nursing expenses sub-limit surgeon fees limit sum insured",
        "cosmetic_exclusion": "cosmetic aesthetic treatment exclusion",
        "other_named_exclusions": "maternity pregnancy self injury alcohol war terrorism exclusion",
        "experimental_treatment_exclusion": "unproven experimental treatment medically necessary definition",
        "pre_post_hospitalization_window": "pre hospitalisation post hospitalisation days maximum",
        "portability_credit": "portability continuous coverage waiting period reduction previous insurer",
    }
    for d in dims:
        if base.get(d.dimension):
            q.append(base[d.dimension])
    return q
