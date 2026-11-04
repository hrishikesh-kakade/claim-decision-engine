"""Pure-Python metric helpers (no third-party deps) shared by every benchmark.

Every formula used on the resume lives here, in one place, with unit tests in
tests/test_metrics_lib.py, so each number can be explained and re-derived.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Sequence


# ------------------------------------------------------------------ latency
def percentile(values: Sequence[float], p: float) -> float:
    """p-th percentile (0-100) using linear interpolation between closest ranks
    (identical to numpy.percentile's default). p50 = median, p95 = the value
    95% of requests were faster than."""
    if not values:
        raise ValueError("percentile of empty sequence")
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(xs[int(k)])
    return float(xs[lo] + (xs[hi] - xs[lo]) * (k - lo))


def summarize_latency(values_ms: Sequence[float]) -> dict:
    if not values_ms:
        return {"n": 0}
    return {
        "n": len(values_ms),
        "mean_ms": sum(values_ms) / len(values_ms),
        "p50_ms": percentile(values_ms, 50),
        "p90_ms": percentile(values_ms, 90),
        "p95_ms": percentile(values_ms, 95),
        "p99_ms": percentile(values_ms, 99),
        "min_ms": min(values_ms),
        "max_ms": max(values_ms),
    }


# --------------------------------------------------------------- statistics
def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Used instead of 'accuracy =
    100%' because 18/18 on a small set only proves accuracy is *probably* above
    ~82%, not that it is 100%."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(values: Sequence[float], n_resamples: int = 2000, seed: int = 7,
                 alpha: float = 0.05,
                 stat: Callable[[Sequence[float]], float] | None = None) -> tuple[float, float]:
    """Percentile bootstrap CI for a statistic (default: mean)."""
    if not values:
        return (0.0, 0.0)
    stat = stat or (lambda xs: sum(xs) / len(xs))
    rng = random.Random(seed)
    n = len(values)
    stats = sorted(stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples))
    return (stats[int(alpha / 2 * n_resamples)], stats[int((1 - alpha / 2) * n_resamples) - 1])


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    f1 = (
            2 * p * r / (p + r)
            if p is not None and r is not None and (p + r) > 0
            else 0.0 if p is not None and r is not None
            else None
        )
    return {"precision": p, "recall": r, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


# ---------------------------------------------------------------- retrieval
def hit_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """1 if at least one relevant chunk is in the top-k, else 0."""
    return 1.0 if set(ranked[:k]) & set(relevant) else 0.0


def recall_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Share of ALL relevant chunks found in the top-k (RAGAS 'context recall' analogue)."""
    rel = set(relevant)
    return len(set(ranked[:k]) & rel) / len(rel) if rel else 0.0


def precision_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    rel = set(relevant)
    return sum(1 for c in ranked[:k] if c in rel) / k


def reciprocal_rank(ranked: Sequence[str], relevant: Sequence[str], k: int | None = None) -> float:
    """1/rank of the first relevant chunk (0 if none in top-k). Mean over queries = MRR."""
    rel = set(relevant)
    for i, c in enumerate(ranked[:k] if k else ranked, start=1):
        if c in rel:
            return 1.0 / i
    return 0.0


def average_precision_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Rank-aware precision: mean of precision@i at every rank i holding a relevant
    chunk, normalised by min(#relevant, k). This is the same idea as RAGAS
    'context precision' (relevant chunks should be ranked above irrelevant ones)."""
    rel = set(relevant)
    hits, score = 0, 0.0
    for i, c in enumerate(ranked[:k], start=1):
        if c in rel:
            hits += 1
            score += hits / i
    denom = min(len(rel), k)
    return score / denom if denom else 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Binary-gain nDCG: DCG = sum 1/log2(rank+1) over relevant hits, divided by the
    best possible DCG for that query."""
    rel = set(relevant)
    dcg = sum(1.0 / math.log2(i + 1) for i, c in enumerate(ranked[:k], start=1) if c in rel)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(rel), k) + 1))
    return dcg / idcg if idcg else 0.0
