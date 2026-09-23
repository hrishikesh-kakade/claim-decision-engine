# Architecture & Design Note

## 1. System overview

```
                         ┌─────────────────────────────────────────────┐
                         │              scripts/ingest_policy.py         │
                         │  policy PDF (or OCR-zip) → 110 chunks         │
                         │  (page, section, subsection, chunk_id)        │
                         └───────────────────┬───────────────────────────┘
                                              ▼
                                 data/policy_chunks.json
                                              │
        ┌─────────────────────────────────────┼─────────────────────────────────┐
        ▼                                     ▼                                 ▼
 backend/retrieval.py               backend/policy_rules.py             (both loaded once at
 BM25 + dense embeddings            regex-extracts every numeric        ClaimEngine startup,
 → RRF fusion → rerank.py           policy parameter (%, days,          shared across requests)
 (Policy Evidence Agent)            months), each tied to a chunk_id


 POST /analyze (backend/main.py)
        │
        ▼
 ┌────────────────────┐   CaseAnalysis    ┌─────────────────────┐  {query:[chunks]}  ┌────────────────────────┐
 │ Case Analysis Agent │ ───────────────► │ Policy Evidence Agent│ ─────────────────► │ Coverage & Exclusion   │
 │ case_analysis.py    │                   │ (retriever.search_*) │                    │ Agent                  │
 └────────────────────┘                   └─────────────────────┘                    │ coverage_exclusion.py  │
                                                                                       │ (uses policy_rules.py) │
                                                                                       └───────────┬────────────┘
                                                                                                    │ CoverageAssessment
                                                                                                    ▼
                                                                                       ┌────────────────────────┐
                                                                                       │ Decision Agent         │
                                                                                       │ decision.py            │
                                                                                       └───────────┬────────────┘
                                                                                                    │ DecisionResponse (draft)
                                                                                                    ▼
                                                                                       ┌────────────────────────┐
                                                                                       │ Validation Agent       │
                                                                                       │ validation.py          │
                                                                                       └───────────┬────────────┘
                                                                                                    │ final DecisionResponse
                                                                                                    ▼
                                                                                       backend/main.py → JSON response
                                                                                                    │
                                                                                                    ▼
                                                                                       frontend/streamlit_app.py
```

Orchestration lives in `backend/orchestrator.py` (`ClaimEngine.analyze`) —
a plain Python function calling five agent functions in sequence, timing
each step into a `TraceStep`. No agent framework dependency; "agent" here
means a function/module with its own single responsibility and its own
typed input/output (`backend/models.py`), not a wrapper around an LLM
call.

## 2. Agent boundaries and why they're separated this way

| Agent | Input | Output | Why it's separate |
|---|---|---|---|
| Case Analysis | `ClaimCase` | `CaseAnalysis` (facts, applicable decision dimensions, missing fields, search queries) | Decides *what needs investigating* for this specific case (a domiciliary claim doesn't need a day-care check; a non-PED claim doesn't need the 48-month check) — this is a planning step, distinct from actually applying rules. |
| Policy Evidence | `CaseAnalysis.search_queries` | `{query: [RetrievedChunk]}` | Pure retrieval — hybrid search + rerank — with no claim-specific reasoning at all. Kept separate so retrieval quality (recall, hit-rate) can be measured independently of decision quality. |
| Coverage & Exclusion | `ClaimCase`, `CaseAnalysis`, `PolicyParameters` | `CoverageAssessment` (per-dimension `Finding`s with citations, applicable limits) | The actual rule engine: one function per decision dimension, each producing a verdict + citation. This is where policy text meets claim facts. |
| Decision | `CoverageAssessment` | `DecisionResponse` (draft) | A pure, auditable mapping from finding verdicts → status. Kept separate so the mapping logic (what combination of findings yields `NOT_ADMISSIBLE` vs `NEEDS_REVIEW` vs `PARTIALLY_ADMISSIBLE`) is one small function, not entangled with rule evaluation. |
| Validation | `DecisionResponse`, `CoverageAssessment` | `ValidationResult` | An independent, structural check that every material statement has a real citation to a real chunk_id. Auto-downgrades to `NEEDS_REVIEW` on failure. Kept separate so it can never be skipped or short-circuited by the Decision Agent's own logic. |

## 3. State flow

All hand-offs are typed Pydantic models (`backend/models.py`):
`ClaimCase → CaseAnalysis → {retrieval results} → CoverageAssessment →
DecisionResponse → (validated) DecisionResponse`. Nothing is passed as a
free-text blob between agents; the Coverage & Exclusion Agent never sees
raw retrieved text as its source of truth for numbers — it reads
`PolicyParameters` (itself sourced from the same chunk store), and cross-
checks its citations against what was actually retrieved (the
"citation/retrieval overlap" logged in the trace and the eval's
citation-hit-rate metric).

## 4. Retrieval design

- **Chunking** (`scripts/ingest_policy.py`): section-aware, not fixed-size.
  DEFINITIONS is split per defined term (`"<Term> means ..."` regex);
  WHAT WE COVER / WHAT WE EXCLUDE / EXTENSIONS / CLAIMS PROCEDURE /
  STANDARD TERMS are split per numbered clause; everything else falls back
  to paragraph-bounded chunks capped at ~900 chars. Every chunk carries
  `chunk_id`, `section`, `subsection`, `page_start/end`.
- **Sparse**: BM25 (`rank_bm25`, vendored fallback if unavailable).
- **Dense**: sentence-transformers `all-MiniLM-L6-v2` cosine similarity,
  falling back to TF-IDF cosine (sklearn, vendored fallback) if
  sentence-transformers isn't installed — logged via `dense_backend` so
  it's never silently misrepresented.
- **Fusion**: Reciprocal Rank Fusion (`k=60`) over the two ranked lists.
- **Rerank**: a lexical-overlap + section-prior reranker by default
  (auditable, zero-dependency); swaps automatically for a real
  cross-encoder (`sentence-transformers.CrossEncoder`) if installed.

## 5. Numeric grounding (the core trade-off)

Rather than asking an LLM to recall "room is capped at 1% of sum insured"
from a page of prose, `policy_rules.py` regex-extracts that number (and
every other percentage/day-count/month-count the rule engine needs)
directly from the ingested chunks at startup, keeping the source
`chunk_id` on every value. `coverage_exclusion.py` then does the actual
arithmetic (caps, deductions, waiting-period date math) in plain Python.
This means:
- numbers are never hallucinated — they're either found in the supplied
  text (and cited) or `None` (and the dimension is flagged as missing
  evidence, driving `NEEDS_REVIEW`);
- the whole pipeline is deterministic and reproducible without any LLM
  API calls at all (`LLM_PROVIDER=none`, the default with no key set) —
  this is the mode the evaluation script runs in;
- an LLM, if configured, is used *only* in `agents/llm_writer.py` to
  rephrase the already-computed finding sentences for readability, and
  its output is discarded (falling back to the deterministic sentences)
  if it doesn't preserve the same number of findings.

## 6. Decision-status mapping (`agents/decision.py`)

- Any **gating dimension** (waiting period, PED, cosmetic/maternity/
  alcohol/war exclusion, domiciliary conditions) with an `unfavorable`
  verdict → `NOT_ADMISSIBLE`.
- Any gating dimension `uncertain` (hospital definition unconfirmed,
  day-care eligibility unconfirmed, experimental-treatment evidence
  ambiguous) with no offsetting unfavorable finding → `NEEDS_REVIEW`.
- A genuinely excluded *portion* of an otherwise-admissible claim (e.g. a
  pre/post-hospitalisation window overrun) → `PARTIALLY_ADMISSIBLE`.
- Ordinary category sub-limit deductions on an otherwise-clean claim →
  `ADMISSIBLE_WITH_LIMITS`.
- No adverse/uncertain findings and no deductions → `ADMISSIBLE`.

## 7. Reliability scenarios, mapped to mechanism

| Scenario (from the assignment) | How it's handled |
|---|---|
| Clause buried in a long document | Section-aware chunking + hybrid retrieval + rerank surfaces it; `policy_rules.py` finds it independent of retrieval ranking. |
| Decision needs multiple sections combined | Coverage & Exclusion Agent runs independent dimension checks (e.g. portability credit + first-year waiting period) and combines their verdicts. |
| Waiting period changes an otherwise-covered outcome | `initial_waiting_period` / `pre_existing_disease_waiting` / `first_year_named_disease_waiting` are gating dimensions evaluated before sub-limits. |
| Category sub-limit changes payable amount | `_sub_limits` computes per-category caps vs. claimed amounts; feeds `applicable_limits` and `payable_estimate_inr`. |
| Insufficient evidence | `evidence_context` gaps (nulls, `false` flags) map to `uncertain` findings → `NEEDS_REVIEW`. |
| Irrelevant input attribute | Case Analysis Agent's `irrelevant_attributes` list (e.g. `hospital.name`, `patient.age` — no age-banded clause in this policy). |
| Can't confirm a required condition | Hospital-definition and day-care-eligibility checks return `uncertain`, not a guessed favorable/unfavorable. |
| LLM tries to assert something the policy doesn't support | Structurally prevented: numbers/verdicts come from the rule engine, not LLM generation; the Validation Agent rejects any finding lacking a real citation and downgrades the response. |

## 8. Trade-offs

- Deterministic rule engine over pure LLM reasoning: more upfront regex
  work, in exchange for reproducibility and eliminating numeric
  hallucination as a failure mode entirely.
- A handful of well-separated agents rather than many: each has a
  genuinely distinct typed input/output, which the assignment's own rubric
  flags as the difference between "real" and "cosmetic" multi-agent design.
- Vendored BM25/TF-IDF fallbacks trade a little code for zero hard
  dependency on `rank_bm25`/`scikit-learn` being installed.

## 9. Known limitations

- The policy's day-care Annexure (~140 procedures) isn't in the supplied
  PDF; unlisted `<24h` procedures correctly abstain rather than guess.
- The room sub-limit is applied as written (a flat 1% cap, not "per day")
  because the supplied text doesn't say "per day" for that line item
  (unlike the ICU sub-limit, which does).
- No explicit exclusion clause names "experimental treatment" in the
  supplied text — handled as `NEEDS_REVIEW`, not inferred as excluded.
