# Metrics report

Generated 2026-11-04 on `Windows-11-10.0.26300-SP0`, Python 3.14.7. Sparse=`rank_bm25.BM25Okapi`, dense=`chromadb (persistent) / sentence-transformers/all-MiniLM-L6-v2`, reranker=`lexical-overlap-rerank-v1`, LLM provider=`groq`.

> **These numbers are valid only for the environment above and this synthetic benchmark.** Decision metrics use policy-aware expected outcomes. Historical payable comparison uses legacy gold and is not a policy-aware payable accuracy score. See docs/METRICS.md.

## Headline numbers

- Decision accuracy **36/36** (95% CI 90%-100%); macro-F1 1.00
- Unsafe approvals **0/18** should-not-pay cases (95% upper bound 0.18)
- Auto-decided **67%** of claims; abstention precision/recall 1.00/1.00
- Legacy payable comparison only (not policy-aware): 6/14 predictions; exact match 6; MAE INR 0
- Retrieval (hybrid RRF production, 70 labeled queries): Hit@3 0.84, Recall@3 0.77, MRR@5 0.75 (BM25-only MRR@5 0.68; experimental reranker MRR@5 0.65)
- Latency, deterministic core: p50 47 ms, p95 104 ms, p99 178 ms (n=180); cold start 8760 ms
- Citation numeric support: 11/11

## 1. Decision quality

- Decision accuracy: **36/36 = 100.0%** (95% Wilson CI 90.4% to 100.0%); macro-F1 1.000 (5/5 represented classes)
- Unsafe-approval rate: **0/18** (95% upper bound 0.2) - cases that should not be paid but were
- False-rejection rate: 0/18; over-abstention: 0/24 (0.0)
- Abstention (NEEDS_REVIEW) precision 1.000 / recall 1.000 / F1 1.000
- Straight-through rate: **66.7%**; accuracy on auto-decided cases: 1.000

**Legacy payable comparison only — not policy-aware ground truth.**
- Legacy gold eligible: 14; predictions available: 6; exact match: 6; MAE INR: 0.0

Confusion matrix (rows = expected, columns = predicted):

| expected \ predicted | ADMISSIBLE | ADMISSIBLE W | PARTIALLY AD | NOT ADMISSIB | NEEDS REVIEW |
|---|---|---|---|---|---|
| ADMISSIBLE | 6 | 0 | 0 | 0 | 0 |
| ADMISSIBLE_WITH_LIMITS | 0 | 6 | 0 | 0 | 0 |
| PARTIALLY_ADMISSIBLE | 0 | 0 | 6 | 0 | 0 |
| NOT_ADMISSIBLE | 0 | 0 | 0 | 6 | 0 |
| NEEDS_REVIEW | 0 | 0 | 0 | 0 | 12 |

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| ADMISSIBLE | 1.000 | 1.000 | 1.000 | 6 |
| ADMISSIBLE_WITH_LIMITS | 1.000 | 1.000 | 1.000 | 6 |
| PARTIALLY_ADMISSIBLE | 1.000 | 1.000 | 1.000 | 6 |
| NOT_ADMISSIBLE | 1.000 | 1.000 | 1.000 | 6 |
| NEEDS_REVIEW | 1.000 | 1.000 | 1.000 | 12 |

## 2. Retrieval (ablation)

Dataset: **dev**.
Production retrieval: **hybrid**. Experimental comparison: **hybrid_rerank**.

Backends: sparse=`rank_bm25.BM25Okapi`, dense=`chromadb (persistent) / sentence-transformers/all-MiniLM-L6-v2`, experimental reranker=`lexical-overlap-rerank-v1`; 70 hand-labeled queries, top-5.

| Retriever | Hit@3 | Hit@5 | Recall@3 (95% CI) | Recall@5 | MRR@5 | nDCG@5 | p50 ms |
|---|---|---|---|---|---|---|---|
| BM25 only | 0.757 | 0.843 | 0.660 (0.56-0.75) | 0.752 | 0.684 | 0.675 | 9.9 |
| Dense only | 0.771 | 0.829 | 0.683 (0.59-0.78) | 0.745 | 0.675 | 0.665 | 9.8 |
| Hybrid (BM25+dense, RRF) — production | 0.843 | 0.914 | 0.771 (0.68-0.85) | 0.845 | 0.755 | 0.756 | 9.8 |
| Hybrid + lexical rerank (experimental) | 0.800 | 0.829 | 0.705 (0.61-0.80) | 0.767 | 0.652 | 0.649 | 10.4 |

By query group (production retriever = Hybrid RRF):

| Group | Hit@3 | Recall@3 | MRR@5 |
|---|---|---|---|
| pipeline (32 q) | 0.969 | 0.891 | 0.859 |
| natural (38 q) | 0.737 | 0.671 | 0.666 |

Queries where production retrieval found NO relevant chunk in the top 5:
- N06 "can I claim for tests done a month before admission" expected ['EXCLUSIONS-002', 'DEFINITIONS-035'] got ['CLAIMS_PROCEDURE-001', 'STANDARD_TERMS-005', 'STANDARD_TERMS-011', 'STANDARD_TERMS-024', 'DEFINITIONS-020']
- N07 "claim made soon after buying the policy" expected ['EXCLUSIONS-005'] got ['DEFINITIONS-034', 'CLAIMS_PROCEDURE-001', 'STANDARD_TERMS-016', 'STANDARD_TERMS-009', 'STANDARD_TERMS-020']
- N11 "injury caused by drinking alcohol or deliberately hurting oneself" expected ['EXCLUSIONS-011'] got ['DEFINITIONS-023', 'EXCLUSIONS-015', 'DEFINITIONS-002', 'EXCLUSIONS-007', 'DEFINITIONS-001']
- N13 "treatment from a doctor of alternative medicine" expected ['EXCLUSIONS-017'] got ['DEFINITIONS-005', 'DEFINITIONS-028', 'DEFINITIONS-003', 'DEFINITIONS-029', 'EXCLUSIONS-023']
- D14 "Does the domiciliary cap apply per day or to the whole claim?" expected ['SCOPE_OF_COVER-003'] got ['CLAIMS_PROCEDURE-001', 'STANDARD_TERMS-020', 'EXCLUSIONS-005', 'EXCLUSIONS-013', 'DEFINITIONS-033']
- D37 "What happens when the sum insured for a policy section has been fully used?" expected ['CLAIMS_PROCEDURE-002'] got ['EXCLUSIONS-003', 'EXTENSIONS-001', 'EXCLUSIONS-005', 'EXCLUSIONS-001', 'PREAMBLE-001']

## 3. Citation correctness / faithfulness

- Numeric consistency check: **11/11** unique claim/chunk pairs with numbers pass the number-presence check (1.000)
- Unresolvable chunk ids: 0 (of 20 unique claim/chunk pairs, 193 citations total)

## 4. Latency

In-process `ClaimEngine.analyze()`; LLM narration: **off**; 36 cases x 5 runs (n=180) after 1 warm-up pass(es). Cold start (engine init): **8760 ms**.

| Stage | n | p50 ms | p95 ms | p99 ms | mean ms | max ms |
|---|---|---|---|---|---|---|
| **End-to-end** | 180 | 47.4 | 104.0 | 177.7 | 55.1 | 416.4 |
| CaseAnalysisAgent | 180 | 0.05 | 0.06 | 0.28 | 0.05 | 0.51 |
| PolicyEvidenceAgent | 180 | 47.11 | 102.15 | 177.28 | 54.80 | 415.82 |
| CoverageExclusionAgent | 180 | 0.12 | 0.16 | 0.72 | 0.14 | 1.00 |
| DecisionAgent | 180 | 0.05 | 0.06 | 0.28 | 0.05 | 0.44 |
| ValidationAgent | 180 | 0.03 | 0.04 | 0.16 | 0.03 | 0.21 |

LLM narration calls: 0/180 requests attempted, 0 succeeded.

## 5. Manual-effort baseline

- Manual baseline: skipped (manual_timing.csv not found; copy eval/gold/manual_timing_template.csv and fill it in)
