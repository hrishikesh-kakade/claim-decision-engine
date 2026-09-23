"""Validation Agent.

Checks that every material decision statement in the response is actually
backed by at least one citation, and that no citation's chunk_id is
missing from the policy chunk store (i.e. nothing was fabricated). This
is a structural/programmatic check rather than an LLM self-critique,
which is deliberate: the assignment's own red flag is "confident
unsupported decisions", and the cheapest way to guarantee that never
reaches the response is to make it structurally impossible, not to ask
another LLM call to please notice it.
"""
from __future__ import annotations

from ..models import CoverageAssessment, DecisionResponse, ValidationResult
from ..policy_rules import PolicyParameters


def validate(response: DecisionResponse, assessment: CoverageAssessment, pp: PolicyParameters) -> ValidationResult:
    unsupported: list[str] = []
    valid_chunk_ids = {c["chunk_id"] for c in pp.chunks}

    for finding in assessment.findings:
        if finding.supports_decision in ("favorable", "unfavorable") and not finding.citations:
            unsupported.append(finding.statement)
        for c in finding.citations:
            if c.chunk_id not in valid_chunk_ids:
                unsupported.append(f"citation references unknown chunk_id {c.chunk_id!r}: {c.claim}")

    if response.decision in ("ADMISSIBLE", "ADMISSIBLE_WITH_LIMITS", "NOT_ADMISSIBLE", "PARTIALLY_ADMISSIBLE"):
        if not response.citations:
            unsupported.append("Final decision has no supporting citations at all.")

    status = "FAIL" if unsupported else "PASS"
    notes = None
    if status == "FAIL":
        notes = "One or more material statements lack a traceable policy citation; treat this response as provisional."
    return ValidationResult(status=status, unsupported_claims=unsupported, notes=notes)
