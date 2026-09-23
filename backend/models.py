"""Pydantic schemas shared across agents, API, and evaluation.

Agents exchange these typed objects (not free-form strings) as they hand
off work -- this is the "structured state" the assignment asks for.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# --------------------------------------------------------------------------- input
class Patient(BaseModel):
    model_config = ConfigDict(extra="allow")
    age: Optional[int] = None


class Hospital(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: Optional[str] = None
    network_provider: Optional[bool] = None


class Treatment(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Optional[str] = None
    admission_hours: Optional[float] = None
    diagnosis: Optional[str] = None
    procedure: Optional[str] = None
    pre_existing: Optional[bool] = None
    experimental: Optional[bool] = None
    hospital_room_unavailable: Optional[bool] = None
    patient_cannot_be_moved: Optional[bool] = None


class Expenses(BaseModel):
    model_config = ConfigDict(extra="allow")
    room: float = 0
    doctor_fees: float = 0
    medicines_diagnostics: float = 0
    pre_hospitalization: float = 0
    post_hospitalization: float = 0
    ambulance: float = 0

    @property
    def total(self) -> float:
        return sum(
            v for v in (
                self.room, self.doctor_fees, self.medicines_diagnostics,
                self.pre_hospitalization, self.post_hospitalization, self.ambulance,
            ) if isinstance(v, (int, float))
        )


class ClaimCase(BaseModel):
    """Mirrors claim_case_schema.md. Tolerant of unknown/extra fields."""
    model_config = ConfigDict(extra="allow")

    case_id: str
    policy_id: str
    policy_start_date: str
    claim_date: str
    sum_insured_inr: float
    continuous_coverage_months: Optional[float] = 0
    prior_insurer_continuous_years: Optional[float] = 0
    patient: Patient = Field(default_factory=Patient)
    hospital: Hospital = Field(default_factory=Hospital)
    treatment: Treatment = Field(default_factory=Treatment)
    expenses_inr: Expenses = Field(default_factory=Expenses)
    documents: list[str] = Field(default_factory=list)
    task: str = ""
    prior_policy: Optional[dict[str, Any]] = None
    evidence_context: Optional[dict[str, Any]] = None
    expense_timing: Optional[dict[str, Any]] = None


# --------------------------------------------------------------------- agent state
class InvestigationDimension(BaseModel):
    dimension: str
    question: str
    relevant: bool = True


class CaseAnalysis(BaseModel):
    """Output of the Case Analysis Agent."""
    case_id: str
    facts: dict[str, Any]
    decision_dimensions: list[InvestigationDimension]
    missing_fields: list[str] = Field(default_factory=list)
    investigation_checklist: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    irrelevant_attributes: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    claim: str
    source: str
    page: int
    section: str
    subsection: Optional[str] = None
    chunk_id: str
    finding_verdict: Optional[Literal["favorable", "unfavorable", "uncertain", "neutral"]] = None
    """Whether the Finding this citation supports counted FOR the claim
    ('favorable'), AGAINST it ('unfavorable'), was inconclusive
    ('uncertain', e.g. missing evidence), or was a routine limit
    application with no pass/fail judgment ('neutral', e.g. a standard
    sub-limit cap). Set once, when citations are flattened for the final
    response (see decision.py) -- this is what lets a reviewer-facing UI
    show, per cited clause, whether it passed or failed."""


class EvidenceBundle(BaseModel):
    """Output of the Policy Evidence Agent."""
    query: str
    results: list[dict[str, Any]]  # raw retrieval metadata (chunk_id, section, page, scores)


class Finding(BaseModel):
    dimension: str
    statement: str
    supports_decision: Literal["favorable", "unfavorable", "neutral", "uncertain"]
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.7


class CoverageAssessment(BaseModel):
    """Output of the Coverage & Exclusion Agent."""
    case_id: str
    findings: list[Finding]
    applicable_limits: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


DecisionStatus = Literal[
    "ADMISSIBLE",
    "ADMISSIBLE_WITH_LIMITS",
    "PARTIALLY_ADMISSIBLE",
    "NOT_ADMISSIBLE",
    "NEEDS_REVIEW",
]


class ValidationResult(BaseModel):
    status: Literal["PASS", "FAIL"]
    unsupported_claims: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class TraceStep(BaseModel):
    agent: str
    action: str
    detail: str = ""
    retrieval_count: Optional[int] = None
    elapsed_ms: Optional[float] = None


class DecisionResponse(BaseModel):
    """The final /analyze response contract."""
    case_id: str
    decision: DecisionStatus
    confidence: float
    key_findings: list[str]
    applicable_limits: list[dict[str, Any]]
    missing_evidence: list[str]
    payable_estimate_inr: Optional[float] = None
    citations: list[Citation]
    validation: ValidationResult
    trace: list[TraceStep]
    llm_narration: Optional[dict[str, Any]] = None
    """Diagnostic info about whether/how an LLM was used to phrase
    key_findings for THIS request: {provider, model, called, succeeded,
    error}. `succeeded: true` means the LLM actually rewrote the findings;
    otherwise key_findings are the deterministic rule-engine sentences.
    See also GET /llm-status for a standalone connectivity check."""
    decision_reasons: list[str] = Field(default_factory=list)
    """The specific statement(s) that actually drove `decision`, always in
    the rule engine's own exact wording (never affected by LLM narration,
    even when key_findings above is LLM-rephrased). Empty only if decision
    could not be reached (should not happen in practice). This is what a
    reviewer-facing UI should show as "why this decision" -- key_findings
    is the full list of everything checked, decision_reasons is just the
    part that mattered for the outcome."""
