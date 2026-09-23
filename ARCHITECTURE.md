# Architecture & Design Specification: Claim Decision Engine

## 1. System Overview & Principles

The **Policy-Aware Multi-Agent RAG Claim Decision Engine** is an automated insurance claim adjudication system designed to evaluate individual health insurance claims against policy documents (e.g., *USGIC – CSC Individual Health Insurance*).

### Core Principles
1. **Zero-Hallucination Adjudication:** Adjudication rules, policy limits, and financial calculations are 100% deterministic. AI/LLM components are never permitted to make claim decisions or modify financial numbers.
2. **Citation Auditability:** Every decision reason and finding must be anchored to an exact policy clause (`section`, `page`, and `chunk_id`). Unbacked assertions are flagged during validation.
3. **Decoupled Frontend/Backend:** The Streamlit reviewer UI communicates strictly over REST (`POST /analyze`, `GET /policy/chunks/{chunk_id}`), ensuring independent deployment and scaling.
4. **Graceful Degradation:** The engine functions fully in pure rule-engine mode without an external LLM configured (`LLM_PROVIDER=none`).

---

## 2. Agent Boundaries & Responsibilities

The system divides claim processing into specialized functional agents managed by a central orchestrator (`ClaimEngine`).

                ┌─────────────────────────┐
                │  ClaimCase Input JSON   │
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │ Intake & Parsing Agent  │
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │ Policy Retrieval Agent  │
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │ Coverage/Exclusion Agent│
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │  Financial Adjudicator  │
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │   Validation Auditor    │
                └────────────┬────────────┘
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
      [LLM Configured?]           [Pure Rule Engine]
               │                           │
               ▼                           │
    ┌─────────────────────┐                │
    │ Narration LLM Agent │                │
    └──────────┬──────────┘                │
               │                           │
               └─────────────┬─────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │    DecisionResponse     │
                └─────────────────────────┘

| Agent | Responsibility | Primary Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **Intake & Parsing Agent** | Schema validation, normalizing medical codes, and extracting structured claim lines. | Raw payload | `ClaimCase` Pydantic model |
| **Policy Retrieval Agent** | Retrieves precise policy clauses, sub-limits, and exclusions via hybrid search. | Diagnostic codes, claim items | Filtered policy chunks (`citations`) |
| **Coverage & Exclusion Agent** | Evaluates waiting periods, pre-existing conditions, and standard exclusions deterministically. | Claim lines + policy chunks | Verdicts (`favorable`, `unfavorable`), decision reasons |
| **Financial Adjudication Agent** | Calculates payable amounts in INR, applying room rent caps, ICU limits, and co-pays. | Itemized costs + limit rules | `payable_estimate_inr`, `applicable_limits` |
| **Validation & Auditor Agent** | Performs post-adjudication sanity checks; verifies all findings against retrieved citations. | Complete decision state | `validation` status (`PASS`/`FAIL`), unsupported claims |
| **Narration Agent (Optional LLM)** | Formats deterministic findings into concise, readable summaries for reviewers. | Final decision object | Plain-language narrative summary |

---

## 3. State Flow & Pipeline Execution

Every claim follows a sequential execution pipeline in `ClaimEngine.analyze()`:

1. **Schema Validation:** Ingestion of `ClaimCase`. Invalid schemas fail fast with HTTP 422.
2. **Context Retrieval:** `Policy Retrieval Agent` queries BM25 + dense vector indexes for applicable policy clauses.
3. **Deterministic Evaluation:** `Coverage & Exclusion Agent` inspects diagnostic codes against pre-existing condition rules, waiting periods, and room rent caps.
4. **Financial Computation:** `Financial Adjudication Agent` aggregates line items, applies caps, and computes the final `payable_estimate_inr`.
5. **Auditing Guardrails:** `Validation Agent` checks that all unfavorable or limited findings map to at least one valid policy citation. If unbacked assertions are detected, the status falls back to `NEEDS_REVIEW`.
6. **Optional Narration:** If `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY` is provided, `LLMClient` generates a polished narrative while leaving decision codes, confidence levels, and financial values untouched.
7. **Trace Logging:** Execution time (`elapsed_ms`) and retrieval counts (`retrieval_count`) are logged per agent step into the `trace` payload array.

---

## 4. Retrieval Architecture (RAG Design)

- **Chunking Strategy:** Policy documents are parsed into granular chunks (200–400 words) tied to specific policy structure (`section`, `subsection`, `page_start`, `page_end`).
- **Hybrid Retrieval:**
  - **Sparse Retrieval (BM25):** Matches exact policy clause numbers, disease terms, and waiting period durations.
  - **Dense Retrieval (Embeddings):** Matches semantic descriptions of medical procedures and treatments.
- **Citation Mapping:** Each retrieved chunk carries a unique `chunk_id` exposed via `GET /policy/chunks/{chunk_id}`, enabling human reviewers to view exact source text directly within the UI.

---

## 5. Key Trade-offs & Engineering Decisions

1. **Deterministic Rule Engine vs. End-to-End LLM Adjudication:**
   - *Trade-off:* Requires explicit rule definitions rather than relying on an LLM to read policy text directly.
   - *Rationale:* Eliminates hallucinations in financial payout calculations and ensures compliance and legal auditability.

2. **Sequential Orchestration Pipeline vs. Autonomous Swarm Agents:**
   - *Trade-off:* Fixed execution flow with less dynamic agent interaction.
   - *Rationale:* Predictable execution timings, straightforward debugging, and explicit step-by-step trace generation.

3. **Strict Validation Fallback (`NEEDS_REVIEW`):**
   - *Trade-off:* The system abstains on ambiguous cases rather than making a best-guess estimate.
   - *Rationale:* In insurance adjudication, precision takes priority over recall. Pushing uncertain cases to human reviewers prevents erroneous payout approvals or unfair rejections.

---

## 6. API Interface Reference

- `POST /analyze` — Primary entry point. Accepts `ClaimCase` payload and returns `DecisionResponse`.
- `GET /health` — Readiness check verifying orchestrator state (`_engine is not None`).
- `GET /llm-status` — Diagnostics check for LLM availability and environment key verification.
- `GET /policy/chunks/{chunk_id}` — Inspects full policy chunk text for review UI citations.
