
"""Shared loaders/runners for the benchmark scripts."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CASES_PUBLIC = ROOT / "data" / "public_test_cases.json"
CASES_CUSTOM = ROOT / "eval" / "cases" / "custom_cases.json"
CASES_EXPANDED = ROOT / "eval" / "cases" / "expanded_cases.json"

# Current decision evaluation uses policy-aware expectations.
EXPECTED = ROOT / "eval" / "policy_aware_expected_outcomes.json"

# Legacy payable gold is retained for historical comparison only.
# Retrieval benchmark datasets
GOLD_DIR = ROOT / "eval" / "gold"

RETRIEVAL_GOLD_ORIGINAL = GOLD_DIR / "retrieval_gold.json"
RETRIEVAL_GOLD_DEV = ROOT / "eval" / "retrieval_dev_gold.json"
RETRIEVAL_GOLD_HELDOUT = ROOT / "eval" / "eval" / "retrieval_heldout_gold.json"

OUT_DIR = ROOT / "eval" / "results"
CHUNKS = ROOT / "data" / "policy_chunks.json"


def load_env() -> None:
    """Pick up GROQ_API_KEY etc. from the repo-root .env if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass


def load_cases() -> list[dict]:
    return (
        json.loads(CASES_PUBLIC.read_text(encoding="utf-8"))
        + json.loads(CASES_CUSTOM.read_text(encoding="utf-8"))
        + json.loads(CASES_EXPANDED.read_text(encoding="utf-8"))
    )


def build_engine():
    """Returns (engine, cold_start_ms)."""
    from backend.orchestrator import ClaimEngine

    t0 = time.perf_counter()
    engine = ClaimEngine()
    return engine, (time.perf_counter() - t0) * 1000


def run_in_process(engine, cases: list[dict]) -> list[dict]:
    from backend.models import ClaimCase

    out = []
    for raw in cases:
        resp = engine.analyze(ClaimCase.model_validate(raw))
        out.append(json.loads(resp.model_dump_json()))
    return out


def write_json(name: str, obj) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / name
    p.write_text(json.dumps(obj, indent=2, default=str))
    return p


def fmt(x, digits=3):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)
