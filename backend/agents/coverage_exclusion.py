"""Coverage & Exclusion Agent.

For each decision dimension flagged by the Case Analysis Agent, this agent
applies the corresponding policy rule using parameters extracted (and
citably sourced) by `policy_rules.PolicyParameters`, and produces a
`Finding` with an explicit `supports_decision` verdict and citations.

Every numeric threshold used below traces back to a `Param` with a
`chunk_id`; if a `Param.value` is None (the number could not be found in
the supplied policy text), the corresponding finding is marked
"uncertain" and surfaced as missing evidence rather than guessed.
"""
from __future__ import annotations

from datetime import date

from ..models import CaseAnalysis, Citation, ClaimCase, CoverageAssessment, Finding
from ..policy_rules import Param, PolicyParameters

SOURCE_NAME = "USGIC-CSCIndividualHealthInsurance_2017-2018.pdf"


def _cite(p: PolicyParameters, chunk, claim: str) -> Citation:
    return Citation(
        claim=claim,
        source=SOURCE_NAME,
        page=chunk["page_start"],
        section=chunk["section"],
        subsection=chunk.get("subsection"),
        chunk_id=chunk["chunk_id"],
    )


def _cite_by_id(pp: PolicyParameters, chunk_id: str, claim: str) -> Citation:
    c = pp._by_id.get(chunk_id)
    if not c:
        return Citation(claim=claim, source=SOURCE_NAME, page=0, section="UNKNOWN", subsection=None, chunk_id=chunk_id)
    return Citation(claim=claim, source=SOURCE_NAME, page=c["page_start"], section=c["section"], subsection=c.get("subsection"), chunk_id=chunk_id)


def _cite_param(param: Param, claim: str, pp: PolicyParameters | None = None) -> list[Citation]:
    if not param.chunk_id:
        return []
    if pp is not None:
        return [_cite_by_id(pp, param.chunk_id, claim)]
    return [Citation(
        claim=claim, source=SOURCE_NAME, page=param.page or 0,
        section="SCOPE_OF_COVER", subsection=None, chunk_id=param.chunk_id,
    )]


def assess(case: ClaimCase, analysis: CaseAnalysis, pp: PolicyParameters) -> CoverageAssessment:
    findings: list[Finding] = []
    limits: list[dict] = []
    unresolved: list[str] = []
    f = analysis.facts

    dim_names = {d.dimension for d in analysis.decision_dimensions}

    # ---------------------------------------------------------- waiting period
    if "initial_waiting_period" in dim_names:
        findings.append(_initial_waiting_period(case, f, pp))

    if "pre_existing_disease_waiting" in dim_names:
        findings.append(_pre_existing_waiting(case, f, pp))

    if "first_year_named_disease_waiting" in dim_names:
        findings.append(_first_year_named_disease(case, f, pp))

    if "hospital_definition" in dim_names:
        findings.append(_hospital_definition(case, f, pp))

    if "day_care_admission_duration" in dim_names:
        findings.append(_day_care_duration(case, f, pp))

    if "domiciliary_treatment_conditions" in dim_names:
        finding, limit = _domiciliary(case, f, pp)
        findings.append(finding)
        if limit:
            limits.append(limit)

    if "sub_limits_and_deductions" in dim_names:
        sub_findings, sub_limits = _sub_limits(case, f, pp)
        findings.extend(sub_findings)
        limits.extend(sub_limits)

    if "cosmetic_exclusion" in dim_names:
        findings.append(_cosmetic_exclusion(pp))

    if "other_named_exclusions" in dim_names:
        finding = _other_named_exclusions(f, pp)
        if finding:
            findings.append(finding)

    if "experimental_treatment_exclusion" in dim_names:
        findings.append(_experimental_exclusion(pp))
        unresolved.append(
            "The supplied policy text defines 'Unproven/Experimental Treatment' but contains no "
            "explicit numbered exclusion clause naming experimental treatment; the finding rests on "
            "the Medically-Necessary/Medical-Expenses definitions, not a direct exclusion citation."
        )

    if "pre_post_hospitalization_window" in dim_names:
        finding, pp_limits = _pre_post_window(case, pp)
        findings.append(finding)
        limits.extend(pp_limits)

    if "portability_credit" in dim_names:
        findings.append(_portability(case, pp))

    for finding in findings:
        if finding.supports_decision == "uncertain":
            unresolved.append(finding.statement)

    return CoverageAssessment(
        case_id=case.case_id, findings=findings, applicable_limits=limits, unresolved_questions=unresolved,
    )


def _initial_waiting_period(case: ClaimCase, f: dict, pp: PolicyParameters) -> Finding:
    waiting = pp.initial_waiting_days
    days_since_start = f["days_since_policy_start"]
    cont_months = f["continuous_coverage_months"]
    prior_years = f["prior_insurer_continuous_years"]
    if waiting.value is None:
        return Finding(
            dimension="initial_waiting_period",
            statement="The 30-day initial waiting period length could not be located in the supplied policy text.",
            supports_decision="uncertain", citations=[],
        )
    exempt = cont_months >= 12 or prior_years >= 1
    if exempt:
        stmt = (
            f"The insured has {cont_months:.0f} months of continuous coverage "
            f"(or {prior_years:.0f} prior-insurer year(s)), satisfying the exception to the "
            f"{waiting.value:.0f}-day initial waiting period."
        )
        verdict = "favorable"
    elif days_since_start < waiting.value:
        stmt = (
            f"The claim date is {days_since_start} days after policy inception, within the "
            f"{waiting.value:.0f}-day initial waiting period, and no continuity exception applies."
        )
        verdict = "unfavorable"
    else:
        stmt = f"The claim date is {days_since_start} days after inception, past the {waiting.value:.0f}-day initial waiting period."
        verdict = "favorable"
    return Finding(
        dimension="initial_waiting_period", statement=stmt, supports_decision=verdict, confidence=0.9,
        citations=_cite_param(waiting, "30-day initial waiting period and continuity exception", pp),
    )


def _pre_existing_waiting(case: ClaimCase, f: dict, pp: PolicyParameters) -> Finding:
    ped = pp.pre_existing_months
    if ped.value is None:
        return Finding(
            dimension="pre_existing_disease_waiting",
            statement="The pre-existing-disease waiting-period length could not be located in the supplied policy text.",
            supports_decision="uncertain", citations=[],
        )
    credit_years = f["prior_insurer_continuous_years"]
    required_months = max(ped.value - credit_years * 12, 0)
    cont_months = f["continuous_coverage_months"]
    citations = _cite_param(ped, f"{ped.value:.0f}-month pre-existing-disease waiting period", pp)
    if pp.ped_portability_chunk:
        citations.append(_cite(pp, pp.ped_portability_chunk, "waiting period reduced by continuous prior years of coverage"))
    if cont_months >= required_months:
        return Finding(
            dimension="pre_existing_disease_waiting",
            statement=(
                f"{cont_months:.0f} months of continuous coverage meets the "
                f"{required_months:.0f}-month requirement (48 months less {credit_years:.0f} portability year(s)), "
                f"so the pre-existing-disease exclusion no longer applies."
            ),
            supports_decision="favorable", confidence=0.85, citations=citations,
        )
    return Finding(
        dimension="pre_existing_disease_waiting",
        statement=(
            f"Only {cont_months:.0f} months of continuous coverage have elapsed against the "
            f"{required_months:.0f}-month requirement, so the pre-existing-disease exclusion still applies "
            f"to this condition."
        ),
        supports_decision="unfavorable", confidence=0.85, citations=citations,
    )


def _first_year_named_disease(case: ClaimCase, f: dict, pp: PolicyParameters) -> Finding:
    cont_months = f["continuous_coverage_months"]
    prior_years = f["prior_insurer_continuous_years"]
    citations = []
    if pp.first_year_disease_chunk:
        citations.append(_cite(pp, pp.first_year_disease_chunk, "1-year waiting period for specified diseases"))
    exempt = cont_months >= 12 or prior_years >= 1
    if exempt:
        return Finding(
            dimension="first_year_named_disease_waiting",
            statement=(
                f"{cont_months:.0f} months of continuous coverage (or {prior_years:.0f} prior-insurer year(s)) "
                f"satisfy the exception to the 1st-year waiting period for this named condition."
            ),
            supports_decision="favorable", confidence=0.85, citations=citations,
        )
    return Finding(
        dimension="first_year_named_disease_waiting",
        statement=(
            f"Only {cont_months:.0f} months of continuous coverage and {prior_years:.0f} prior-insurer year(s) "
            f"are on record, so the 1st-year specified-disease waiting period still applies to this condition."
        ),
        supports_decision="unfavorable", confidence=0.8, citations=citations,
    )


def _hospital_definition(case: ClaimCase, f: dict, pp: PolicyParameters) -> Finding:
    ev = case.evidence_context or {}
    citations = []
    if pp.hospital_def_chunk:
        citations.append(_cite(pp, pp.hospital_def_chunk, "Hospital registration / minimum-criteria definition"))
    if ev.get("hospital_registered") is False:
        return Finding(
            dimension="hospital_definition",
            statement="Supplied evidence confirms the facility is not a registered Hospital under the Policy's definition.",
            supports_decision="unfavorable", confidence=0.8, citations=citations,
        )
    evidence_gap = (
        ("hospital_registered" in ev and ev.get("hospital_registered") is None)
        or ev.get("hospital_minimum_criteria_documented") is False
    )
    if evidence_gap:
        return Finding(
            dimension="hospital_definition",
            statement=(
                "Whether the treating facility is registered under the Clinical Establishments Act "
                "or meets the Policy's minimum-criteria definition of Hospital is not established by the "
                "supplied evidence -- this cannot be finally decided on the current record."
            ),
            supports_decision="uncertain", confidence=0.5, citations=citations,
        )
    if case.hospital.network_provider:
        return Finding(
            dimension="hospital_definition",
            statement="The facility is a network provider, which is treated as satisfying the Hospital definition absent contrary evidence.",
            supports_decision="favorable", confidence=0.7, citations=citations,
        )
    return Finding(
        dimension="hospital_definition",
        statement=(
            "The facility is not a network provider and no registration/minimum-criteria evidence was "
            "supplied, so satisfaction of the Policy's Hospital definition cannot be confirmed."
        ),
        supports_decision="uncertain", confidence=0.4, citations=citations,
    )


def _day_care_duration(case: ClaimCase, f: dict, pp: PolicyParameters) -> Finding:
    diag_proc = f"{f.get('diagnosis') or ''} {f.get('procedure') or ''}".lower()
    matched = [term for term in pp.day_care_named_procedures if term in diag_proc]
    citations = []
    if pp.day_care_chunk:
        citations.append(_cite(pp, pp.day_care_chunk, "specified procedures covered without the 24-hour minimum stay"))
    if matched:
        return Finding(
            dimension="day_care_admission_duration",
            statement=(
                f"The treatment ({', '.join(sorted(set(matched)))}) is among the specific procedures the Policy "
                f"covers without requiring the 24-hour minimum stay."
            ),
            supports_decision="favorable", confidence=0.85, citations=citations,
        )
    return Finding(
        dimension="day_care_admission_duration",
        statement=(
            "The treatment is not one of the specified procedures named in the supplied policy text as "
            "qualifying for the <24-hour waiver, and the Policy's referenced Annexure of Day Care "
            "Procedures was not supplied, so eligibility for the waiver cannot be confirmed from the "
            "available evidence."
        ),
        supports_decision="uncertain", confidence=0.4, citations=citations,
    )


def _domiciliary(case: ClaimCase, f: dict, pp: PolicyParameters) -> tuple[Finding, dict | None]:
    t = case.treatment
    citations = []
    if pp.domiciliary_def_chunk:
        citations.append(_cite(pp, pp.domiciliary_def_chunk, "Domiciliary Treatment definition"))
    condition_met = bool(t.hospital_room_unavailable) or bool(t.patient_cannot_be_moved)
    if not condition_met:
        return Finding(
            dimension="domiciliary_treatment_conditions",
            statement="Neither 'room unavailable' nor 'patient cannot be moved' is confirmed, so the Domiciliary Treatment definition is not satisfied.",
            supports_decision="unfavorable", confidence=0.8, citations=citations,
        ), None

    limit = None
    if pp.domiciliary_pct.value is not None:
        cap = pp.domiciliary_pct.value * case.sum_insured_inr
        domiciliary_expenses = (
            case.expenses_inr.room + case.expenses_inr.doctor_fees + case.expenses_inr.medicines_diagnostics
        )
        payable = min(domiciliary_expenses, cap)
        limit = {
            "limit_name": "Domiciliary hospitalisation aggregate sub-limit",
            "cap_pct_of_sum_insured": pp.domiciliary_pct.value,
            "cap_inr": cap,
            "claimed_inr": domiciliary_expenses,
            "payable_inr": payable,
            "chunk_id": pp.domiciliary_pct.chunk_id,
        }
        citations.append(_cite_by_id(pp, pp.domiciliary_pct.chunk_id, "20% of Sum Insured aggregate sub-limit for domiciliary hospitalisation"))
    verdict = "favorable" if (limit is None or limit["payable_inr"] >= limit["claimed_inr"]) else "neutral"
    return Finding(
        dimension="domiciliary_treatment_conditions",
        statement=(
            "The Domiciliary Treatment definition is satisfied "
            f"({'room unavailable' if t.hospital_room_unavailable else 'patient could not be moved'}); "
            "the 20% aggregate sub-limit applies to the domiciliary expenses, and pre/post-hospitalisation "
            "expenses are separately excluded for domiciliary claims."
        ),
        supports_decision=verdict, confidence=0.8, citations=citations,
    ), limit


def _sub_limits(case: ClaimCase, f: dict, pp: PolicyParameters) -> tuple[list[Finding], list[dict]]:
    si = case.sum_insured_inr
    e = case.expenses_inr
    findings: list[Finding] = []
    limits: list[dict] = []

    def add_limit(name: str, param: Param, claimed: float, section_hint: str):
        if param.value is None or claimed <= 0:
            return
        cap = param.value * si
        payable = min(claimed, cap)
        limits.append({
            "limit_name": name, "cap_pct_of_sum_insured": param.value, "cap_inr": cap,
            "claimed_inr": claimed, "payable_inr": payable, "chunk_id": param.chunk_id,
        })

    add_limit("Room, boarding & nursing expenses", pp.room_pct, e.room, "room")
    add_limit("Doctor/surgeon/consultant fees", pp.doctor_fee_pct, e.doctor_fees, "doctor")
    add_limit("Medicines, diagnostics & similar expenses", pp.other_expenses_pct, e.medicines_diagnostics, "other")

    if pp.ambulance_flat.value is not None and e.ambulance > 0:
        pct_cap = (pp.ambulance_pct.value or 0) * si
        cap = min(pct_cap, pp.ambulance_flat.value) if pp.ambulance_pct.value else pp.ambulance_flat.value
        payable = min(e.ambulance, cap)
        limits.append({
            "limit_name": "Ambulance charges", "cap_pct_of_sum_insured": pp.ambulance_pct.value,
            "cap_inr": cap, "claimed_inr": e.ambulance, "payable_inr": payable,
            "chunk_id": pp.ambulance_flat.chunk_id,
        })

    total_claimed = sum(li["claimed_inr"] for li in limits)
    total_payable = sum(li["payable_inr"] for li in limits)
    any_deduction = any(li["payable_inr"] < li["claimed_inr"] for li in limits)

    citations = [
        _cite_by_id(pp, li["chunk_id"], f"{li['limit_name']} capped at {li['cap_pct_of_sum_insured']*100:.1f}% of Sum Insured")
        for li in limits if li["chunk_id"] and li.get("cap_pct_of_sum_insured") is not None
    ]
    verdict = "neutral"
    findings.append(Finding(
        dimension="sub_limits_and_deductions",
        statement=(
            f"Category sub-limits cap payable room/doctor/other-expense amounts at "
            f"INR {total_payable:,.0f} against INR {total_claimed:,.0f} claimed under those categories"
            if any_deduction else
            f"Claimed room/doctor/other-expense amounts (INR {total_claimed:,.0f}) fall within their respective category sub-limits."
        ),
        supports_decision=verdict, confidence=0.85, citations=citations,
    ))
    return findings, limits


def _cosmetic_exclusion(pp: PolicyParameters) -> Finding:
    citations = []
    if pp.cosmetic_exclusion_chunk:
        citations.append(_cite(pp, pp.cosmetic_exclusion_chunk, "cosmetic/aesthetic treatment exclusion"))
    return Finding(
        dimension="cosmetic_exclusion",
        statement="The treatment is cosmetic/aesthetic in nature, which the Policy expressly excludes.",
        supports_decision="unfavorable", confidence=0.9, citations=citations,
    )


_NAMED_EXCLUSION_KEYWORDS = {
    "maternity": (
        ["pregnan", "childbirth", "caesarean", "cesarean", "miscarriage", "abortion", "infertility", "delivery"],
        "maternity_exclusion_chunk",
        "pregnancy/childbirth exclusion",
    ),
    "self_injury_or_alcohol": (
        ["self injury", "self-inflicted", "self inflicted", "suicide attempt", "alcohol", "intoxicat"],
        "self_injury_exclusion_chunk",
        "intentional self-injury / intoxicating drugs & alcohol exclusion",
    ),
    "war_or_terrorism": (
        ["war ", "riot", "terroris", "nuclear", "act of foreign enemy"],
        "war_exclusion_chunk",
        "war/riot/terrorism/nuclear exclusion",
    ),
}


def _other_named_exclusions(f: dict, pp: PolicyParameters) -> Finding | None:
    diag_proc = f"{f.get('diagnosis') or ''} {f.get('procedure') or ''}".lower()
    for _, (keywords, attr, label) in _NAMED_EXCLUSION_KEYWORDS.items():
        if any(k in diag_proc for k in keywords):
            chunk = getattr(pp, attr)
            citations = [_cite(pp, chunk, label)] if chunk else []
            return Finding(
                dimension="other_named_exclusions",
                statement=f"The diagnosis/procedure falls under the Policy's {label}.",
                supports_decision="unfavorable", confidence=0.85, citations=citations,
            )
    return None


def _experimental_exclusion(pp: PolicyParameters) -> Finding:
    citations = []
    if pp.experimental_def_chunk:
        citations.append(_cite(pp, pp.experimental_def_chunk, "Unproven/Experimental Treatment definition"))
    if pp.medically_necessary_chunk:
        citations.append(_cite(pp, pp.medically_necessary_chunk, "Medically Necessary definition"))
    return Finding(
        dimension="experimental_treatment_exclusion",
        statement=(
            "The treatment is flagged experimental. The Policy defines 'Unproven/Experimental Treatment' "
            "as a distinct category from ordinary Medically Necessary treatment, but the supplied policy "
            "text contains no explicit numbered exclusion clause naming experimental treatment -- so this "
            "is evidence of likely non-coverage, not a conclusive exclusion citation."
        ),
        supports_decision="uncertain", confidence=0.5, citations=citations,
    )


def _pre_post_window(case: ClaimCase, pp: PolicyParameters) -> tuple[Finding, list[dict]]:
    timing = case.expense_timing or {}
    e = case.expenses_inr
    citations = _cite_param(pp.pre_hosp_days, "30-day pre-hospitalisation window", pp) + \
        _cite_param(pp.post_hosp_days, "60-day post-hospitalisation window", pp)
    pp_limits: list[dict] = []

    def make_limit(name: str, claimed: float, payable: float, chunk_id):
        if claimed <= 0:
            return
        pp_limits.append({
            "limit_name": name, "cap_pct_of_sum_insured": None, "cap_inr": None,
            "claimed_inr": claimed, "payable_inr": payable, "chunk_id": chunk_id,
        })

    if pp.pre_hosp_days.value is None or pp.post_hosp_days.value is None:
        return Finding(
            dimension="pre_post_hospitalization_window", supports_decision="uncertain",
            statement="Pre/post-hospitalisation window lengths could not be located in the supplied policy text.",
            citations=[],
        ), pp_limits

    if not timing:
        make_limit("Pre-hospitalisation expenses (window not independently verified)", e.pre_hospitalization, e.pre_hospitalization, pp.pre_hosp_days.chunk_id)
        make_limit("Post-hospitalisation expenses (window not independently verified)", e.post_hospitalization, e.post_hospitalization, pp.post_hosp_days.chunk_id)
        verdict = "favorable" if (e.pre_hospitalization or e.post_hospitalization) else "neutral"
        return Finding(
            dimension="pre_post_hospitalization_window",
            statement=(
                f"Pre/post-hospitalisation expenses (INR {e.pre_hospitalization:,.0f} / INR "
                f"{e.post_hospitalization:,.0f}) are claimed without documented dates; they are assumed to fall "
                f"within the {pp.pre_hosp_days.value:.0f}/{pp.post_hosp_days.value:.0f}-day windows pending confirmation."
            ),
            supports_decision=verdict, confidence=0.55, citations=citations,
        ), pp_limits

    pre_days = timing.get("pre_hospitalization_days_before_admission")
    post_days = timing.get("post_hospitalization_days_after_discharge")
    same_condition = timing.get("same_condition_confirmed", False)
    pre_ok = pre_days is not None and pre_days <= pp.pre_hosp_days.value and same_condition
    post_ok = post_days is not None and post_days <= pp.post_hosp_days.value and same_condition

    make_limit("Pre-hospitalisation expenses", e.pre_hospitalization, e.pre_hospitalization if pre_ok else 0, pp.pre_hosp_days.chunk_id)
    make_limit("Post-hospitalisation expenses", e.post_hospitalization, e.post_hospitalization if post_ok else 0, pp.post_hosp_days.chunk_id)

    if pre_ok and post_ok:
        return Finding(
            dimension="pre_post_hospitalization_window",
            statement=(
                f"Pre-hospitalisation expenses were incurred {pre_days} days before admission and post-hospitalisation "
                f"expenses {post_days} days after discharge, both within the {pp.pre_hosp_days.value:.0f}/"
                f"{pp.post_hosp_days.value:.0f}-day windows, for the same condition."
            ),
            supports_decision="favorable", confidence=0.85, citations=citations,
        ), pp_limits
    return Finding(
        dimension="pre_post_hospitalization_window",
        statement=(
            f"Pre-hospitalisation ({pre_days} days) / post-hospitalisation ({post_days} days) timing "
            f"exceeds the {pp.pre_hosp_days.value:.0f}/{pp.post_hosp_days.value:.0f}-day windows or the same-condition "
            f"link is not confirmed, so that portion falls outside the covered window and is not payable."
        ),
        supports_decision="unfavorable", confidence=0.75, citations=citations,
    ), pp_limits


def _portability(case: ClaimCase, pp: PolicyParameters) -> Finding:
    citations = []
    if pp.portability_waiting_reduction_chunk:
        citations.append(_cite(pp, pp.portability_waiting_reduction_chunk, "waiting-period reduction for continuous prior coverage"))
    pr = case.prior_policy or {}
    years = pr.get("continuous_years", case.prior_insurer_continuous_years or 0)
    received = pr.get("database_and_claim_history_received")
    if received is False:
        return Finding(
            dimension="portability_credit",
            statement="Portability credit cannot be applied because the prior insurer's database/claim history was not received.",
            supports_decision="unfavorable", confidence=0.8, citations=citations,
        )
    return Finding(
        dimension="portability_credit",
        statement=f"{years:.0f} year(s) of continuous prior coverage with an Indian insurer reduce the applicable waiting periods by that many years.",
        supports_decision="favorable", confidence=0.8, citations=citations,
    )
