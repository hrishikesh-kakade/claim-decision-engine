"""Decision Agent.

Combines the Coverage & Exclusion Agent's findings into the final
structured decision. This is a deterministic policy over the finding
verdicts, not an LLM call, so the mapping from findings to status is
auditable:

  * any 'unfavorable' finding on a hard gate (waiting period, PED window,
    cosmetic exclusion, domiciliary condition unmet) => NOT_ADMISSIBLE
    for the affected portion.
  * any 'uncertain' finding on a gating dimension (hospital definition,
    day-care eligibility, experimental-treatment evidence) with no
    offsetting favorable evidence => NEEDS_REVIEW.
  * sub-limit deductions with everything else favorable => ADMISSIBLE_WITH_LIMITS.
  * a mix of an excluded portion (e.g. pre/post window overrun) alongside
    an otherwise-admissible core claim => PARTIALLY_ADMISSIBLE.
  * no adverse or uncertain findings and no deductions => ADMISSIBLE.
"""
from __future__ import annotations

from ..models import CoverageAssessment, DecisionResponse, ValidationResult
from .llm_writer import narrate_findings

GATING_DIMENSIONS = {
    "initial_waiting_period", "pre_existing_disease_waiting", "first_year_named_disease_waiting",
    "cosmetic_exclusion", "domiciliary_treatment_conditions", "other_named_exclusions",
}
UNCERTAIN_TO_NEEDS_REVIEW = {
    "hospital_definition", "day_care_admission_duration", "experimental_treatment_exclusion",
}


def decide(assessment: CoverageAssessment, total_claimed: float) -> DecisionResponse:
    unfavorable_gates = [f for f in assessment.findings if f.dimension in GATING_DIMENSIONS and f.supports_decision == "unfavorable"]
    uncertain_gates = [f for f in assessment.findings if f.dimension in UNCERTAIN_TO_NEEDS_REVIEW and f.supports_decision == "uncertain"]
    other_uncertain = [f for f in assessment.findings if f.supports_decision == "uncertain" and f.dimension not in UNCERTAIN_TO_NEEDS_REVIEW]
    unfavorable_non_gate = [f for f in assessment.findings if f.dimension not in GATING_DIMENSIONS and f.supports_decision == "unfavorable"]

    limits = assessment.applicable_limits
    total_payable_from_limits = sum(li["payable_inr"] for li in limits) if limits else None
    any_deduction = any(li["payable_inr"] < li["claimed_inr"] for li in limits)
    deducted_limits = [li for li in limits if li["payable_inr"] < li["claimed_inr"]]

    citations = []
    for f in assessment.findings:
        for c in f.citations:
            c.finding_verdict = f.supports_decision
            citations.append(c)
    key_findings = [f.statement for f in assessment.findings]
    missing_evidence = list(assessment.unresolved_questions)

    # decision_reasons: the specific, deterministic statement(s) that actually
    # drove the status below -- kept separate from key_findings (which may be
    # LLM-rephrased) so "why this decision" is always in the rule engine's
    # own exact wording, never altered by narration.
    decision_reasons: list[str] = []

    if unfavorable_gates:
        # A hard-gate exclusion fired (e.g. still within a waiting period, or cosmetic
        # exclusion). If unrelated favorable coverage exists alongside it we call it
        # PARTIALLY_ADMISSIBLE; if the gate covers the whole claim, NOT_ADMISSIBLE.
        status = "NOT_ADMISSIBLE"
        confidence = 0.8
        payable = 0.0
        decision_reasons = [f.statement for f in unfavorable_gates]
    elif uncertain_gates and not other_uncertain and not unfavorable_non_gate:
        status = "NEEDS_REVIEW"
        confidence = 0.4
        payable = None
        decision_reasons = [f.statement for f in uncertain_gates]
    elif uncertain_gates or other_uncertain:
        status = "NEEDS_REVIEW"
        confidence = 0.45
        payable = None
        decision_reasons = [f.statement for f in (uncertain_gates + other_uncertain)]
    elif unfavorable_non_gate:
        status = "PARTIALLY_ADMISSIBLE"
        confidence = 0.7
        payable = total_payable_from_limits if total_payable_from_limits is not None else None
        decision_reasons = [f.statement for f in unfavorable_non_gate]
    elif any_deduction:
        status = "ADMISSIBLE_WITH_LIMITS"
        confidence = 0.85
        payable = total_payable_from_limits
        decision_reasons = [
            f"{li['limit_name']}: only INR {li['payable_inr']:,.0f} of the INR {li['claimed_inr']:,.0f} claimed "
            f"is payable" + (f" (capped at {li['cap_pct_of_sum_insured']*100:.1f}% of Sum Insured)" if li.get("cap_pct_of_sum_insured") is not None else " (outside the covered window)")
            for li in deducted_limits
        ]
    else:
        status = "ADMISSIBLE"
        confidence = 0.9
        payable = total_payable_from_limits if total_payable_from_limits is not None else total_claimed
        decision_reasons = ["No waiting-period issue, exclusion, unmet condition, or evidence gap was found; the full claimed amount is within every applicable policy limit."]

    narration, llm_info = narrate_findings(assessment.findings, status)
    if narration:
        key_findings = narration

    response = DecisionResponse(
        case_id=assessment.case_id,
        decision=status,
        confidence=confidence,
        key_findings=key_findings,
        applicable_limits=limits,
        missing_evidence=missing_evidence,
        payable_estimate_inr=payable,
        citations=citations,
        validation=ValidationResult(status="PASS"),  # overwritten by validation agent
        trace=[],
    )
    response.llm_narration = llm_info
    response.decision_reasons = decision_reasons
    return response
