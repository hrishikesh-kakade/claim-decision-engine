# Policy-Aware Multi-Agent RAG Claim Decision Engine

A small, evidence-grounded claims-decision system for the USGIC "CSC –
Individual Health Insurance" policy (UNIHLIP18004V011718). Given a claim
case, it returns a structured decision (`ADMISSIBLE`,
`ADMISSIBLE_WITH_LIMITS`, `PARTIALLY_ADMISSIBLE`, `NOT_ADMISSIBLE`, or
`NEEDS_REVIEW`), with every material statement traceable to a page/section
of the supplied policy PDF.

See `docs/ARCHITECTURE.md` for the design note (agent boundaries, state
flow, retrieval design, trade-offs).

## Why this looks a little different from "LLM reads PDF, LLM decides"

Waiting-period arithmetic, percentage sub-limits, and day/month windows are
exactly where an LLM asked to "remember the policy" quietly gets a number
wrong — which is the assignment's own stated red flag ("confident
unsupported decisions"). So the numeric/date reasoning here is **plain,
auditable Python**, driven by parameters that are **regex-extracted from
the actual retrieved policy chunks at startup** (see
`backend/policy_rules.py`), each tied to the `chunk_id` it came from. If a
parameter can't be found in the supplied text, its value is `None` and the
Coverage & Exclusion Agent treats that dimension as missing evidence
instead of guessing. An LLM is used, optionally, only to rephrase the
already-computed findings into more readable prose (`backend/agents/llm_writer.py`)
— never to invent a number, and its output is discarded if it doesn't
round-trip back to the same number of findings.

This also means the whole pipeline runs and is fully reproducible **with
zero API keys and zero network calls** (`LLM_PROVIDER=none`, the default
when no key is set), which is what the evaluation script relies on.

## Repository layout

```
backend/
  main.py                FastAPI app (POST /analyze, GET /health, GET /policy/chunks/{id})
  models.py               Pydantic schemas (input + all inter-agent state + response contract)
  orchestrator.py         Wires the 5 agents together, builds the trace
  retrieval.py            Hybrid retrieval: BM25 (sparse) + embeddings/TF-IDF (dense) + RRF fusion
  rerank.py               Reranking stage (lexical by default; cross-encoder if available)
  policy_rules.py         Regex-extracts policy numbers from chunks, each with a source chunk_id
  llm.py                  Pluggable LLM client (Anthropic / OpenAI-compatible / none)
  agents/
    case_analysis.py       Case Analysis Agent
    coverage_exclusion.py  Coverage & Exclusion Agent (the rule engine)
    decision.py            Decision Agent
    validation.py          Validation Agent
    llm_writer.py           optional narration polish used by the Decision Agent
scripts/ingest_policy.py  Policy ingestion + chunking (page/section/chunk_id metadata)
data/policy_chunks.json   Pre-built chunk store (regenerate with the script above)
policy/                   The supplied policy source file
frontend/streamlit_app.py Reviewer UI
eval/
  run_eval.py             Reproducible evaluation script
  expected_outcomes.json  Hand-established expected decision per case, with rationale
  cases/custom_cases.json 6 candidate-created cases (>= the required 5)
  results/                Written by run_eval.py
tests/                    unittest-based regression tests
docs/ARCHITECTURE.md      1-2 page design note
```

## Setup (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # optional: add an LLM key, or leave blank for rule-only mode

# (re)build the policy chunk store from the supplied source (already committed under data/, this is optional)
python scripts/ingest_policy.py --pdf policy/USGIC-CSCIndividualHealthInsurance_2017-2018.pdf

# run the API
uvicorn backend.main:app --reload --port 8000

# in another shell, run the frontend
CLAIM_API_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py
```

Health check:
```bash
curl http://localhost:8000/health
# {"status": "ok", "engine_ready": true}
```

## API

### `POST /analyze`

Request body: one claim case, following `claim_case_schema.md` (extra
fields are tolerated). Example:

```json
{
  "case_id": "PUB-001",
  "policy_id": "USGIC-CSC-2017-2018",
  "policy_start_date": "2025-01-01",
  "claim_date": "2026-03-14",
  "sum_insured_inr": 500000,
  "continuous_coverage_months": 14,
  "prior_insurer_continuous_years": 0,
  "patient": {"age": 34},
  "hospital": {"name": "Sunrise Multispeciality", "network_provider": true},
  "treatment": {
    "type": "inpatient", "admission_hours": 96,
    "diagnosis": "Acute appendicitis", "procedure": "Appendectomy",
    "pre_existing": false, "experimental": false
  },
  "expenses_inr": {
    "room": 30000, "doctor_fees": 30000, "medicines_diagnostics": 90000,
    "pre_hospitalization": 5000, "post_hospitalization": 7000, "ambulance": 1200
  },
  "documents": ["claim_form", "discharge_summary", "itemized_bill", "doctor_prescription"],
  "task": "Determine whether the hospitalization is admissible..."
}
```

Response (abridged; see `docs/sample_response.json` for the full example):

```json
{
  "case_id": "PUB-001",
  "decision": "ADMISSIBLE_WITH_LIMITS",
  "confidence": 0.85,
  "key_findings": [
    "The insured has 14 months of continuous coverage ..., satisfying the exception to the 30-day initial waiting period.",
    "The facility is a network provider, which is treated as satisfying the Hospital definition absent contrary evidence.",
    "Category sub-limits cap payable room/doctor/other-expense amounts at INR 126,000 against INR 151,200 claimed under those categories",
    "Pre/post-hospitalisation expenses (INR 5,000 / INR 7,000) are claimed without documented dates; they are assumed to fall within the 30/60-day windows pending confirmation."
  ],
  "applicable_limits": [
    {"limit_name": "Room, boarding & nursing expenses", "cap_pct_of_sum_insured": 0.01, "cap_inr": 5000.0, "claimed_inr": 30000, "payable_inr": 5000.0, "chunk_id": "SCOPE_OF_COVER-001"}
  ],
  "missing_evidence": [],
  "payable_estimate_inr": 138000.0,
  "citations": [
    {"claim": "Room, boarding & nursing expenses capped at 1.0% of Sum Insured", "source": "USGIC-CSCIndividualHealthInsurance_2017-2018.pdf", "page": 7, "section": "SCOPE_OF_COVER", "subsection": "1. Room, Boarding and Nursing Expense ...", "chunk_id": "SCOPE_OF_COVER-001"}
  ],
  "validation": {"status": "PASS", "unsupported_claims": []},
  "trace": [
    {"agent": "CaseAnalysisAgent", "action": "extract_facts_and_plan", "detail": "5 decision dimensions identified; 0 missing-field flag(s).", "elapsed_ms": 0.1},
    {"agent": "PolicyEvidenceAgent", "action": "hybrid_retrieve_and_rerank", "detail": "Ran 5 quer(y/ies) through BM25 + tfidf dense retrieval, fused with RRF, reranked.", "retrieval_count": 20, "elapsed_ms": 12.4},
    {"agent": "CoverageExclusionAgent", "action": "apply_policy_rules", "detail": "5 finding(s), 6 applicable limit(s). Citation/retrieval overlap: 6/8 (75%)", "elapsed_ms": 0.3},
    {"agent": "DecisionAgent", "action": "combine_findings", "detail": "Decision: ADMISSIBLE_WITH_LIMITS (confidence 0.85)", "elapsed_ms": 0.05},
    {"agent": "ValidationAgent", "action": "verify_citations", "detail": "PASS; 0 unsupported claim(s).", "elapsed_ms": 0.02}
  ]
}
```

### `GET /health`
`{"status": "ok", "engine_ready": true}`

### Malformed input
A request missing a required field returns HTTP 422 with the Pydantic
validation errors; an internal failure returns HTTP 500 with a message —
neither crashes the process.

## Evaluation

```bash
python eval/run_eval.py                       # in-process (fast, no server needed)
python eval/run_eval.py --api-url http://localhost:8000   # against a running deployment
```

Current results (`eval/results/eval_results.json`, regenerated by the
command above):

| Metric | Value |
|---|---|
| Cases evaluated | 18 (12 supplied + 6 candidate-created) |
| Decision accuracy vs. hand-established expected outcome | **100%** (18/18) |
| NEEDS_REVIEW cases (required: ≥ 2) | **4** |
| Validation Agent PASS rate | **100%** |
| Citation ⟷ hybrid-retrieval overlap ("citation hit rate") | **95.3%** |

**How expected outcomes were established:** by a human reading the actual
supplied policy PDF against each case's facts (see the `_method` note and
per-case `rationale` in `eval/expected_outcomes.json`) — not derived from
the system under test. Where the supplied text is genuinely silent or
ambiguous (e.g. no explicit exclusion clause for "experimental treatment"),
the expected outcome is `NEEDS_REVIEW`, matching the assignment's
abstention requirement rather than encoding a guess as ground truth.

**Retrieval quality / citation correctness:** for every decision, the
orchestrator checks whether the chunk_ids actually used in citations were
present in the hybrid-retrieval result set for that case's queries
(`trace[2].detail`, "Citation/retrieval overlap: X/Y"). This is the
citation-hit-rate metric surfaced in the eval summary. The Validation
Agent additionally rejects (auto-downgrades to `NEEDS_REVIEW`) any response
where a material finding lacks a citation, or a citation points at a
chunk_id that doesn't exist in the policy store — i.e. citation
correctness is enforced structurally, not just measured.

## Failure analysis (found during development — see git history / this
section for what changed)

1. **Day-care citation silently missing → false PASS/FAIL flip.**
   `PolicyParameters._chunk_for_text(...)` returns the matching *chunk
   dict*, but `day_care_admission_duration`'s citation-building code
   treated the stored value as if it were a bare `chunk_id` string and
   compared a string to a dict — so the comparison never matched, the
   finding was emitted with zero citations, and the Validation Agent
   correctly caught it and downgraded PUB-005 / PUB-010 to `NEEDS_REVIEW`
   (both should have been `ADMISSIBLE`/`ADMISSIBLE_WITH_LIMITS`). **Root
   cause:** an ambiguous variable name (`..._chunk_id` holding a dict, not
   an id) let a type mismatch slip past. **Fix:** renamed the attribute to
   `day_care_chunk` (holds the chunk dict) and used it directly instead of
   re-searching by id. This is exactly the kind of case the Validation
   Agent exists to catch before it reaches a reviewer — it did its job,
   the underlying bug still needed a real fix.

2. **Sub-limit deductions were miscategorised as `PARTIALLY_ADMISSIBLE`.**
   The sub-limit finding's verdict was set to `"unfavorable"` whenever any
   category deduction applied, which the Decision Agent's mapping treats
   as "part of the claim is excluded" (`PARTIALLY_ADMISSIBLE`) rather than
   "the claim is admissible subject to a normal policy cap"
   (`ADMISSIBLE_WITH_LIMITS`) — these are different statuses in the
   assignment's own contract, and conflating them mislabels every
   sub-limit case (PUB-001, PUB-007, PUB-009 were all one status too
   pessimistic). **Fix:** sub-limit findings are now always `"neutral"`;
   only a genuinely excluded portion (e.g. a pre/post-hospitalisation
   window overrun) drives `PARTIALLY_ADMISSIBLE`.

3. **Domiciliary claims were incorrectly gated on the Hospital
   definition.** The Case Analysis Agent added a `hospital_definition`
   dimension to every case, including domiciliary-treatment claims — but
   Domiciliary Treatment is defined in the policy as treatment *at home*,
   precisely because a Hospital bed isn't available; asking "does this
   home-care provider meet the Hospital definition" is a category error,
   and (because no evidence_context is normally supplied for it) it was
   spuriously downgrading valid domiciliary claims to `NEEDS_REVIEW`
   (PUB-004). **Fix:** the `hospital_definition` dimension is now skipped
   for `treatment.type == "domiciliary"`.

4. **(Caught by the eval script, not a code bug) One hand-authored
   expected outcome contradicted its own rationale.** `CUST-002`'s
   rationale said "no material deduction is expected" but its
   `expected_decision` was still labeled `ADMISSIBLE_WITH_LIMITS`. Running
   the eval script surfaced the mismatch immediately (the engine's
   `ADMISSIBLE` was in fact correct); the expected-outcomes label was
   corrected. This is included deliberately to show the eval script
   catches errors in either direction, not just engine bugs.

5. **Citations pointed at the wrong section/page for several rule-engine
   findings.** `_cite_param` and the sub-limit / domiciliary citation
   builders originally hardcoded `section="SCOPE_OF_COVER"` and, in one
   place, `page=0`, regardless of which section/page the cited chunk_id
   actually lived on (several of the relevant numbers, e.g. the ambulance
   and pre/post-hospitalisation windows, are physically laid out under the
   `EXCLUSIONS` heading in the source due to the document's column
   layout). A citation with the wrong section label is exactly the kind
   of "evidence that doesn't really support the claim" the Validation
   Agent and the assignment's citation-correctness requirement are meant
   to catch. **Fix:** every citation is now built by looking up the real
   chunk by `chunk_id` and reading its actual `section`/`page_start`
   (`_cite_by_id`), never hardcoded.

## Known limitations

- **Day-care Annexure not supplied.** The policy references an Annexure
  listing ~140 day-care procedures that is not included in the supplied
  PDF. For a `<24h` treatment not on the small explicit list found in the
  main text (dialysis, chemotherapy, radiotherapy, eye surgery,
  lithotripsy, tonsillectomy, D&C), the system correctly abstains
  (`NEEDS_REVIEW`) rather than guessing whether it's on the missing list.
- **Room sub-limit "per day" ambiguity.** The supplied text states the
  room cap as "1.0% of Basic Sum Insured" without the words "per day"
  (unlike the ICU sub-limit, which explicitly says "per day"). Many real
  Indian health policies apply room caps per day; this system applies the
  cap literally as written (a single 1% cap, not multiplied by length of
  stay) rather than importing an assumption the supplied text doesn't
  state. This is flagged as a design decision, not resolved by inventing
  a "per day" reading.
- **Experimental-treatment exclusion has no direct clause.** See failure
  analysis and `eval/expected_outcomes.json` (PUB-012) — the system
  abstains here by design.
- **Dense retrieval fallback.** If `sentence-transformers` isn't
  installed/reachable, dense retrieval falls back to TF-IDF cosine
  (still a genuinely different ranking signal from BM25, so RRF fusion
  remains meaningful) — logged via `dense_backend` in the retrieval trace.
- **LLM narration is best-effort and always safe to disable.** With no
  API key configured, `key_findings` are the exact deterministic sentences
  the rule engine produced — this is the mode the eval script runs in.

## Trade-offs

- **Deterministic rule engine over "let the LLM read the policy and
  decide."** Slightly more upfront engineering (regexes per parameter),
  in exchange for reproducibility, auditability, and eliminating an
  entire class of numeric hallucination. The LLM is kept in a narrow,
  fact-preserving role.
- **Vendored BM25/TF-IDF fallbacks** so the system runs with zero paid
  dependencies if `rank_bm25`/`scikit-learn` aren't installed; the real
  libraries are preferred automatically when present.
- **A small number of well-separated agents** rather than a larger swarm:
  the assignment explicitly warns against "multiple prompts presented as
  agents without meaningful separation" — each of the five agents here has
  a genuinely distinct input/output type and responsibility.


