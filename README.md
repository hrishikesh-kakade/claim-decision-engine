# Policy-Aware Multi-Agent RAG Claim Decision Engine

## 🌐 Live Deployments

- **Live Streamlit Frontend (Reviewer UI):** [https://claim-decision-engine-frontend.streamlit.app/](https://claim-decision-engine-frontend.streamlit.app/)
  

## 📚 Architecture & Design
For details on agent boundaries, state flow, hybrid RAG strategy, and architectural trade-offs, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

A small, evidence-grounded claims-decision system for the USGIC "CSC –
Individual Health Insurance" policy (UNIHLIP18004V011718). Given a claim
case, it returns a structured decision (`ADMISSIBLE`,
`ADMISSIBLE_WITH_LIMITS`, `PARTIALLY_ADMISSIBLE`, `NOT_ADMISSIBLE`, or
`NEEDS_REVIEW`), with every material statement traceable to a page/section
of the supplied policy PDF, and a plain-English "why" for every outcome.

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
— never to invent a number or a decision — and its output is discarded if
it isn't a clean JSON array with exactly the expected number of items.

This also means the whole pipeline runs and is fully reproducible **with
zero API keys and zero network calls** (`LLM_PROVIDER=none`, the default
when no key is set), which is what the evaluation script relies on.

## Repository layout

```
backend/
  main.py                 FastAPI app: POST /analyze, GET /health,
                           GET /llm-status[?test=true], GET /policy/chunks/{id}
  models.py                Pydantic schemas (input + all inter-agent state + response contract)
  orchestrator.py          Wires the 5 agents together, builds the trace
  retrieval.py             Hybrid retrieval: BM25 (sparse) + Chroma/embeddings/TF-IDF (dense) + RRF fusion
  vector_store.py          Persistent Chroma vector store wrapper (free, open-source, embedded)
  rerank.py                Reranking stage (lexical by default; cross-encoder if available)
  policy_rules.py          Regex-extracts policy numbers from chunks, each with a source chunk_id
  llm.py                   Pluggable LLM client (Anthropic / Groq / OpenAI-compatible / none)
  agents/
    case_analysis.py        Case Analysis Agent
    coverage_exclusion.py   Coverage & Exclusion Agent (the rule engine)
    decision.py             Decision Agent
    validation.py           Validation Agent
    llm_writer.py            optional narration polish used by the Decision Agent
scripts/ingest_policy.py   Policy ingestion + chunking (page/section/chunk_id metadata)
data/
  policy_chunks.json        Pre-built chunk store (regenerate with the script above)
  chroma/                   Persistent vector DB directory (gitignored; rebuilt automatically on first run)
policy/                    The supplied policy source file
frontend/streamlit_app.py  Reviewer UI
eval/
  run_eval.py               Reproducible evaluation script
  expected_outcomes.json   Hand-established expected decision per case, with rationale
  cases/custom_cases.json  6 candidate-created cases (>= the required 5)
  results/                 Written by run_eval.py
tests/                     unittest-based regression tests
docs/
  ARCHITECTURE.md           1-2 page design note
  sample_response.json      Full example /analyze response
Dockerfile.backend         Backend container (Render/HF Spaces/any Docker host)
Dockerfile.frontend        Frontend container (optional; Streamlit Community Cloud needs no Docker)
render.yaml                One-click Render Blueprint for the backend
```

## Setup (local, using `uv`)

```powershell
# 0. install uv (skip if already installed)
irm https://astral.sh/uv/install.ps1 | iex

# 1. project setup
cd repo
uv init --bare
uv venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt

# 2. environment (must sit at the repo root, next to this README)
Copy-Item .env.example .env
notepad .env
# fill in LLM_PROVIDER=groq / GROQ_API_KEY / GROQ_MODEL, or leave all blank
# for pure rule-engine mode (no LLM calls at all -- fully deterministic)

# 3. sanity check
uv run python -m unittest discover -s tests -v
uv run python eval/run_eval.py

# 4. run the backend (keep this terminal open)
uv run uvicorn backend.main:app --reload --port 8000
```

In a **second** terminal:
```powershell
# confirm the LLM is actually wired up (if you configured one)
Invoke-RestMethod "http://localhost:8000/llm-status"
Invoke-RestMethod "http://localhost:8000/llm-status?test=true"

# run the frontend
$env:CLAIM_API_URL = "http://localhost:8000"
uv run streamlit run frontend/streamlit_app.py
```

Equivalent for macOS/Linux: same commands, `source .venv/bin/activate`
instead of the `Activate.ps1` line, `export CLAIM_API_URL=...` instead of
`$env:...`.

**Windows footgun to know about:** Notepad/Explorer hide known file
extensions by default, so a file you save as `.env` can silently become
`.env.txt`. `backend/main.py` detects this at startup and logs a loud
warning if it happens; `GET /llm-status` also reports `env_file_found` and
`env_txt_fallback_found` so this is never a silent failure. Always verify
with `Get-ChildItem -Force -Filter ".env*"` (PowerShell, not Explorer) if
`/llm-status` shows `provider: none` unexpectedly.

**`--reload` does not reload `.env`.** If you edit `.env` while uvicorn is
running, restart it — env vars are only read once at process startup.

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
    "Claimed room/doctor/other-expense amounts fall within their respective category sub-limits, except where noted.",
    "Pre/post-hospitalisation expenses are claimed without documented dates; assumed within the 30/60-day windows pending confirmation."
  ],
  "decision_reasons": [
    "Room, boarding & nursing expenses: only INR 5,000 of the INR 30,000 claimed is payable (capped at 1.0% of Sum Insured)",
    "Ambulance charges: only INR 1,000 of the INR 1,200 claimed is payable (capped at 1.0% of Sum Insured)"
  ],
  "applicable_limits": [
    {"limit_name": "Room, boarding & nursing expenses", "cap_pct_of_sum_insured": 0.01, "cap_inr": 5000.0, "claimed_inr": 30000, "payable_inr": 5000.0, "chunk_id": "SCOPE_OF_COVER-001"}
  ],
  "missing_evidence": [],
  "payable_estimate_inr": 138000.0,
  "citations": [
    {
      "claim": "Room, boarding & nursing expenses capped at 1.0% of Sum Insured",
      "source": "USGIC-CSCIndividualHealthInsurance_2017-2018.pdf",
      "page": 7, "section": "SCOPE_OF_COVER",
      "subsection": "1. Room, Boarding and Nursing Expense ...",
      "chunk_id": "SCOPE_OF_COVER-001",
      "finding_verdict": "neutral"
    }
  ],
  "validation": {"status": "PASS", "unsupported_claims": []},
  "llm_narration": {"provider": "groq", "model": "llama-3.1-8b-instant", "called": true, "succeeded": true, "error": null},
  "trace": [
    {"agent": "CaseAnalysisAgent", "action": "extract_facts_and_plan", "detail": "5 decision dimensions identified; 0 missing-field flag(s).", "elapsed_ms": 0.2},
    {"agent": "PolicyEvidenceAgent", "action": "hybrid_retrieve_and_rerank", "detail": "Ran 5 quer(y/ies) through BM25 + chromadb (persistent) / sentence-transformers/all-MiniLM-L6-v2 dense retrieval, fused with RRF, reranked.", "retrieval_count": 20, "elapsed_ms": 210.4},
    {"agent": "CoverageExclusionAgent", "action": "apply_policy_rules", "detail": "5 finding(s), 6 applicable limit(s). Citation/retrieval overlap: 7/8 (88%)", "elapsed_ms": 0.3},
    {"agent": "DecisionAgent", "action": "combine_findings", "detail": "Decision: ADMISSIBLE_WITH_LIMITS (confidence 0.85). LLM narration USED (provider=groq, model=llama-3.1-8b-instant).", "elapsed_ms": 950.1},
    {"agent": "ValidationAgent", "action": "verify_citations", "detail": "PASS; 0 unsupported claim(s).", "elapsed_ms": 0.05}
  ]
}
```

Two fields worth calling out, both added for interpretability:

- **`decision_reasons`** — unlike `key_findings` (everything the system
  checked, which may be LLM-rephrased), this is the exact deterministic
  statement(s) that actually *drove* the status. This is what a
  reviewer-facing UI should show as "why this decision", and it's what the
  Streamlit frontend's colored "Why" box is built from.
- **`citations[].finding_verdict`** — `favorable` / `unfavorable` /
  `uncertain` / `neutral`, tagging whether the cited clause counted *for*
  the claim, *against* it, was inconclusive, or was a routine limit
  application. Lets a reviewer scan the citation table and immediately see
  which clause passed and which one failed, without reading every sentence.

### `GET /health`
`{"status": "ok", "engine_ready": true}`

### `GET /llm-status` / `GET /llm-status?test=true`
Diagnostic endpoint, independent of running a full claim: reports which
provider is configured, whether `.env` was actually found (and the
`.env.txt` Windows footgun specifically), and with `?test=true` makes one
real "reply with OK" call and reports whether it actually succeeded —
including `finish_reason`, which is what surfaced the reasoning-model
token-budget issue during development (see Failure analysis, #6).

### Malformed input
A request missing a required field returns HTTP 422 with the Pydantic
validation errors; an internal failure returns HTTP 500 with a message —
neither crashes the process.

## Evaluation

```bash
uv run python eval/run_eval.py                       # in-process (fast, no server needed)
uv run python eval/run_eval.py --api-url http://localhost:8000   # against a running deployment
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
("Citation/retrieval overlap: X/Y" in the trace). This is the
citation-hit-rate metric surfaced in the eval summary. The Validation
Agent additionally rejects (auto-downgrades to `NEEDS_REVIEW`) any response
where a material finding lacks a citation, or a citation points at a
chunk_id that doesn't exist in the policy store — i.e. citation
correctness is enforced structurally, not just measured.

## Failure analysis (found during development, in order)

1. **Day-care citation silently missing → false PASS/FAIL flip.**
   `PolicyParameters._chunk_for_text(...)` returns the matching *chunk
   dict*, but the citation-building code treated the stored value as a bare
   `chunk_id` string and compared a string to a dict — the comparison never
   matched, the finding was emitted with zero citations, and the
   Validation Agent correctly downgraded PUB-005/PUB-010 to `NEEDS_REVIEW`
   (both should have been `ADMISSIBLE`/`ADMISSIBLE_WITH_LIMITS`). **Fix:**
   renamed the attribute to `day_care_chunk` and used it directly.

2. **Sub-limit deductions were miscategorised as `PARTIALLY_ADMISSIBLE`.**
   The sub-limit finding's verdict was `"unfavorable"` whenever any
   category deduction applied, which the Decision Agent maps to "part of
   the claim is excluded" rather than "admissible subject to a normal
   policy cap" — conflating two different statuses in the assignment's own
   contract (PUB-001, PUB-007, PUB-009 were all one status too pessimistic).
   **Fix:** sub-limit findings are now always `"neutral"`.

3. **Domiciliary claims were incorrectly gated on the Hospital
   definition.** Domiciliary Treatment is, by definition, treatment *at
   home* because a hospital bed isn't available — checking "does this
   home-care provider meet the Hospital definition" is a category error,
   and it was spuriously downgrading valid domiciliary claims to
   `NEEDS_REVIEW` (PUB-004). **Fix:** skipped for
   `treatment.type == "domiciliary"`.

4. **(Caught by the eval script, not a code bug) One hand-authored
   expected outcome contradicted its own rationale.** `CUST-002`'s
   rationale said "no material deduction is expected" but was labeled
   `ADMISSIBLE_WITH_LIMITS`. The eval script surfaced the mismatch
   immediately (the engine's `ADMISSIBLE` was correct); the
   expected-outcomes label was fixed. Included deliberately to show the
   eval catches errors in either direction, not just engine bugs.

5. **Citations pointed at the wrong section/page.** `_cite_param` and the
   sub-limit/domiciliary citation builders hardcoded `section="SCOPE_OF_COVER"`
   and, in one place, `page=0`, regardless of which section/page the cited
   chunk actually lived on (several numbers, e.g. ambulance and
   pre/post-hospitalisation windows, are physically laid out under the
   `EXCLUSIONS` heading due to the source document's column layout). A
   citation with the wrong section label is exactly the kind of
   unsupported evidence the Validation Agent exists to catch. **Fix:**
   every citation is now built by looking up the real chunk by `chunk_id`
   (`_cite_by_id`), never hardcoded.

6. **LLM narration failed with an unhelpful bare `None` error.** Groq's
   `openai/gpt-oss-20b` is a reasoning model that spends tokens on hidden
   "thinking" before writing the visible answer, out of the same
   `max_tokens` budget. With a budget sized for a non-reasoning model, it
   returned empty content with `finish_reason='length'` — but the code had
   no exception to catch (the call itself succeeded), so `error` stayed
   `None` with no way to diagnose it. **Fix:** `llm.py` now captures
   `finish_reason` explicitly, detects reasoning models by name and sets
   `reasoning_effort="low"` with a larger token budget for them, and always
   sets a real error message when content comes back empty.

7. **LLM narration also failed on exact line-count matching.** Once the
   Groq call itself started succeeding, its plain-text response sometimes
   had a different line count than expected (a preamble, a wrapped
   sentence) and got rejected by a strict `len(lines) == len(findings)`
   check — safe, but avoidably fragile. **Fix:** switched the narration
   contract to a JSON array of strings (`["...", "..."]`) with an explicit
   expected-count instruction; JSON is a format LLMs reliably hit exactly,
   with markdown-fence stripping and a regex-extraction fallback for any
   stray text the model adds around the array.

## Known limitations

- **Day-care Annexure not supplied.** The policy references an Annexure
  listing ~140 day-care procedures not included in the supplied PDF. For a
  `<24h` treatment not on the small explicit list in the main text
  (dialysis, chemotherapy, radiotherapy, eye surgery, lithotripsy,
  tonsillectomy, D&C), the system correctly abstains (`NEEDS_REVIEW`)
  rather than guessing.
- **Room sub-limit "per day" ambiguity.** The supplied text states the room
  cap as "1.0% of Basic Sum Insured" without "per day" (unlike the ICU
  sub-limit, which explicitly says "per day"). This system applies the cap
  literally as written (a single 1% cap, not multiplied by length of stay)
  rather than importing an assumption the text doesn't state.
- **Experimental-treatment exclusion has no direct clause.** See failure
  analysis and PUB-012 — the system abstains here by design.
- **Dense retrieval fallback chain.** Chroma (persistent) →
  sentence-transformers (in-memory) → TF-IDF/sklearn → TF-IDF/vendored, in
  that order, depending on what's installed — logged via `dense_backend`
  in the retrieval trace so it's never silently misrepresented.
- **LLM narration is best-effort and always safe to disable.** With no API
  key configured, `key_findings` are the exact deterministic sentences the
  rule engine produced, and `decision_reasons` is *always* the
  deterministic wording regardless — this is the mode the eval script
  runs in.
- **Chroma persistence is process-local.** `data/chroma/` is gitignored
  and rebuilt automatically on first run if missing/stale (cheap at 110
  chunks); on ephemeral hosts (e.g. Render free tier, which spins the
  container down after inactivity) this means a slower first request after
  a cold start, not an error.

## Trade-offs

- **Deterministic rule engine over "let the LLM read the policy and
  decide."** More upfront engineering (regexes per parameter), in exchange
  for reproducibility, auditability, and eliminating an entire class of
  numeric hallucination. The LLM is kept in a narrow, fact-preserving,
  JSON-constrained role.
- **A real, persistent vector store (Chroma)** rather than an in-memory
  matrix rebuilt every process start — with automatic fallback to
  in-memory sentence-transformers/TF-IDF if `chromadb` isn't installed.
- **Vendored BM25/TF-IDF fallbacks** so the system runs with zero paid
  dependencies if `rank_bm25`/`scikit-learn` aren't installed.
- **A small number of well-separated agents** rather than a larger swarm:
  the assignment explicitly warns against "multiple prompts presented as
  agents without meaningful separation" — each of the five agents here has
  a genuinely distinct input/output type and responsibility.


## Deployment Architecture & Setup

                      ┌────────────────────────┐
                      │   Streamlit Cloud      │
                      │   (Frontend UI)        │
                      └───────────┬────────────┘
                                  │
                     REST API Requests (HTTPS)
                     `POST /analyze`
                     `GET /policy/chunks/{id}`
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │   Railway Container    │
                      │   (FastAPI Backend)    │
                      └───────────┬────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        ┌───────────────────────┐   ┌───────────────────────┐
        │ Persistent Vector DB  │   │   Groq LLM Service    │
        │  (Chroma / BM25 RAG)  │   │ (Narration Layer Only)│
        └───────────────────────┘   └───────────────────────┘

---

### Production Deployment Pipeline

#### 1. Repository Source Control
* **GitHub Repository:** [`hrishikesh-kakade/claim-decision-engine`](https://github.com/hrishikesh-kakade/claim-decision-engine)
* Multi-stage build support with separate container instructions for backend services (`Dockerfile.backend`) and frontend apps (`Dockerfile.frontend`).

---

#### 2. Backend Engine Deployment (Railway)
* **Hosting Platform:** Railway (Docker Container Runtime)
* **Entry Specification:** Built via `Dockerfile.backend` exposing port `8000`.
* **Index Initialization:** The Docker build phase automatically builds and mounts the Chroma persistent vector database alongside the sparse BM25 index on startup.
* **Environment & Security Management:** Sensitive credentials are securely injected via Railway's Service Environment Settings:
  * `GROQ_API_KEY`: API key for Groq LLM inference.
  * `GROQ_MODEL`: Specified model (e.g., `llama-3.3-70b`).
  * `PORT`: Dynamically bound by the container orchestrator.

---

#### 3. Reviewer Dashboard Deployment (Streamlit Community Cloud)
* **Hosting Platform:** Streamlit Community Cloud
* **Entry Point:** `frontend/streamlit_app.py`
* **Configuration & Secret Injection:**
  * Configured via **App Settings → Secrets** to securely connect to the Railway instance:
    ```toml
    CLAIM_API_URL = "[https://claim-decision-engine-production-8083.up.railway.app](https://claim-decision-engine-production-8083.up.railway.app)"
    ```
* **Continuous Deployment:** Configured with GitHub webhooks for automatic re-deployment upon pushes to the `main` branch.

---

### Alternative Deployment Topology (Containerized Dual-Space)

For environments requiring single-provider isolation or containerized edge hosting (e.g., Hugging Face Spaces):
* **Backend Container Space:** Deployed using `Dockerfile.backend` with dynamic `$PORT` shell execution (`CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT`).
* **Frontend Container Space:** Deployed using `Dockerfile.frontend` configured with environment variable binding `CLAIM_API_URL` pointing to the backend Space's public URL.
