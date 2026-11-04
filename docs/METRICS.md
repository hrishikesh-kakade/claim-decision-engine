# Metrics: what is measured, how, and how to quote it

Everything below is produced by one command and a handful of small, tested scripts (`eval/`):

```powershell
uv run python eval/run_all.py                                          # no API calls
uv run python eval/run_all.py --llm-judge --narration --with-llm-latency   # also uses your Groq key
```
Output: `eval/results/METRICS_REPORT.md` (+ JSON per benchmark). **Copy numbers from YOUR run, never from
someone else's**: latency and retrieval depend on the machine, the vector DB/embedding model and the LLM.
Every number is on a synthetic 18-case set (12 supplied + 6 custom) and a 30-query hand-labeled retrieval set.

## 1. Metric dictionary

| Metric | Question it answers | Formula / method | Script |
|---|---|---|---|
| **Decision accuracy + 95% Wilson CI** | How often is the status right, and how sure can I be with this few cases? | correct / n. Wilson score interval: centre = (p + z²/2n)/(1+z²/n), half-width = z·sqrt(p(1-p)/n + z²/4n²)/(1+z²/n), z = 1.96. 18/18 gives a lower bound of about 82%. | `decision_metrics.py` |
| **Macro-F1, per-class P/R/F1** | Is it good on every outcome class, not just the common one? | From the 5x5 confusion matrix. P = TP/(TP+FP), R = TP/(TP+FN), F1 = 2PR/(P+R), macro = mean over classes that occur. | `decision_metrics.py` |
| **Unsafe-approval rate** | How often would it pay a claim that should be rejected or escalated? (the costly error) | Among cases expected NOT_ADMISSIBLE or NEEDS_REVIEW, share predicted ADMISSIBLE / WITH_LIMITS / PARTIALLY. Reported with the 95% upper bound. | `decision_metrics.py` |
| **Abstention precision / recall** | When it says NEEDS_REVIEW, is it right, and does it catch every case that needs review? | Positive class = NEEDS_REVIEW. | `decision_metrics.py` |
| **Straight-through rate** | What share of claims did the system decide without a human? | predicted != NEEDS_REVIEW / n. Pair it with "accuracy on decided claims". | `decision_metrics.py` |
| **Payable-amount exact match, MAE** | Is the money right? | Predicted payable vs hand-computed gold (`eval/gold/payable_gold.json`, derivation per case). MAE = mean absolute INR error. | `decision_metrics.py` |
| **Hit@k** | Did a relevant policy chunk appear in the top k? | 1 if any gold chunk in top-k, averaged over queries. | `retrieval_eval.py` |
| **Recall@k** (~RAGAS context recall) | How much of the needed evidence was retrieved? | \|gold ∩ top-k\| / \|gold\| | `retrieval_eval.py` |
| **MRR@5** | How high is the first relevant chunk? | mean of 1/rank of first relevant chunk (0 if none in top 5) | `retrieval_eval.py` |
| **nDCG@5** | Are relevant chunks ranked above irrelevant ones? | DCG = Σ 1/log2(rank+1) over relevant hits, divided by the ideal DCG | `retrieval_eval.py` |
| **Context precision@5** (~RAGAS context precision) | Is the retrieved context clean and well ordered? | average precision: mean of precision@i at each relevant rank, divided by min(\|gold\|, 5) | `retrieval_eval.py` |
| **Retrieval ablation** | Does each component earn its place? | Same 30 queries through BM25-only, dense-only, hybrid (RRF, k=60), hybrid+rerank. Bootstrap 95% CI (2,000 resamples) on Recall@3. | `retrieval_eval.py` |
| **p50 / p95 / p99 latency** | How fast is a typical request, and how bad is the tail? | Percentile with linear interpolation over n timed requests after warm-up. p95 = 95% of requests were faster. Per-agent from the trace. | `perf_bench.py` |
| **Cold start** | How long until the service is ready? | Time to construct `ClaimEngine` (chunks, BM25, vector store, policy parameters). | `perf_bench.py` |
| **Throughput, error rate** | What does it do under concurrent load? | Successful requests / wall-clock seconds with N worker threads; error rate = non-200 or failed / total. HTTP mode only. | `perf_bench.py --api-url` |
| **Numeric citation support** | Do cited chunks really contain the numbers the system states? | Every number in a citation's claim must appear in the cited chunk text. supported / checked. Deterministic. | `faithfulness_eval.py` |
| **LLM-judge faithfulness** (RAGAS-style) | Does the cited excerpt support the claim, per an LLM judge? | supported / judged over unique (claim, chunk) pairs. This is the RAGAS faithfulness idea implemented directly (works with Groq). Noisy: read the unsupported list. | `faithfulness_eval.py --llm-judge` |
| **LLM narration guardrail** | Does the LLM keep the facts when it rephrases? | Acceptance rate (valid JSON array, right length) and share of lines whose numbers are all preserved. | `faithfulness_eval.py --narration` |
| **Manual-effort baseline** | How does it compare with a person? | Your own timed manual review of 6-10 cases vs system p50. Small study, one reviewer. | `manual_baseline.py` |

## 2. Honest limits (say these in interviews before you are asked)

- **Labels were not written by an independent insurance expert.** Expected decisions, payable amounts and retrieval gold were derived from the supplied policy by the developer (with AI assistance). Re-read them; report results as "hand-labeled".
- **Small sample.** 18 claims, 30 queries. Confidence intervals are wide on purpose.
- **`PARTIALLY_ADMISSIBLE` is never exercised** by the 18 cases (support = 0), and no case violates the pre/post-hospitalisation window. Add cases before claiming coverage of that class.
- **Retrieval does not drive the decision.** Numbers come from the rule engine (`policy_rules.py`, regex over the chunk store); retrieval surfaces evidence for the reviewer and is measured separately. Do not say the RAG "improved decision accuracy".
- **Hybrid is not automatically better.** The ablation can show hybrid ~ BM25 on this small, keyword-heavy policy. Only claim an improvement your own table shows.
- **Latency is machine-specific.** The deterministic core is milliseconds; the LLM narration call dominates end-to-end time on a hosted model. Report both, with the environment.
- **No business-impact metric exists without real data.** "Reduced manual effort by X%" or "saved Y hours" cannot be measured on a synthetic set. Use the manual-baseline study as a small measured comparison, or describe the benchmark metrics instead.

## 3. Resume wording templates (fill from your METRICS_REPORT.md)

- "Built a policy-grounded multi-agent RAG claim-adjudication engine; **<correct>/<n>** correct decisions on a hand-labeled 18-claim benchmark (95% CI <lo>-<hi>%), **<k>/<m>** unsafe approvals, abstaining on cases with missing evidence (abstention P/R <p>/<r>)."
- "Evaluated retrieval on 30 hand-labeled queries: hybrid BM25 + vector search with reranking reached **Hit@3 <x>, MRR@5 <y>** (BM25-only <z>); added citation checks (**<a>/<b>** cited figures verified against source text)."
- "Benchmarked the service: **p50 <a> ms / p95 <b> ms** for the deterministic core, **p50 <c> ms / p95 <d> ms** with LLM narration (n=<n>), cold start <s> ms."
- "Payable amounts exact on **<e>/<f>** claims against hand-computed gold; LLM output constrained to rephrasing with a JSON-schema guardrail (**<g>%** of responses accepted, figures preserved in **<h>%** of lines)."

## 4. Questions an interviewer may ask about these numbers

- *Why a confidence interval for 18/18?* With 18 samples, 100% only supports "probably above ~82%".
- *What does p95 mean and why not average?* Averages hide slow outliers; p95/p99 show what the slowest users experience.
- *MRR vs Recall@k?* MRR rewards ranking the first useful chunk high; Recall@k asks whether all the needed evidence was retrieved.
- *How do you know citations are right?* Deterministic number check against the chunk, plus an LLM judge on unique claim/chunk pairs, plus a hand review of anything judged unsupported.
- *How is this different from RAGAS?* Same ideas (faithfulness = supported claims / claims; context precision/recall), implemented directly against hand-labeled gold so results do not depend on an LLM judging retrieval.

## 5. Worth adding next

Cases that trigger `PARTIALLY_ADMISSIBLE` and window overruns; a second reviewer to label gold (report agreement); more natural-language retrieval queries; an RAGAS-library cross-check of the judge numbers; Locust/k6 load tests against the deployed URL.
