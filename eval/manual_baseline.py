"""Optional, honest 'manual effort' baseline.

You CANNOT claim 'reduced manual effort by X%' without a measured human baseline. This script turns a
small time-and-motion study into numbers:
  1. Copy eval/gold/manual_timing_template.csv to eval/manual_timing.csv.
  2. For 6-10 cases: open ONLY the case JSON + the policy PDF (not the system output), decide the claim,
     write the minutes it took and your decision (one of the 5 statuses).
  3. Run this script. It reports median/mean minutes, your accuracy vs the hand-labeled expected
     outcomes, and the ratio to the system's p50 latency.
Report it as 'small timing study, n=<k>, one reviewer', never as an industry figure.
"""
from __future__ import annotations

import csv
import json
import statistics

import common


def run(csv_path=None, perf_json=None) -> dict:
    csv_path = csv_path or (common.ROOT / "eval" / "manual_timing.csv")
    perf_json = perf_json or (common.OUT_DIR / "perf_bench.json")
    if not csv_path.exists():
        return {"skipped": f"{csv_path.name} not found; copy eval/gold/manual_timing_template.csv and fill it in"}
    expected = json.loads(common.EXPECTED.read_text())
    mins, correct, judged = [], 0, 0
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                m = float(row["minutes"])
            except (ValueError, KeyError, TypeError):
                continue
            mins.append(m)
            d = (row.get("my_decision") or "").strip().upper()
            if d and row["case_id"] in expected:
                judged += 1
                correct += d == expected[row["case_id"]]["expected_decision"]
    if not mins:
        return {"skipped": "no filled rows in manual_timing.csv"}
    out = {"n": len(mins), "median_minutes": statistics.median(mins), "mean_minutes": statistics.mean(mins),
           "manual_accuracy": correct / judged if judged else None, "manual_judged": judged}
    if perf_json.exists():
        p50_s = json.loads(perf_json.read_text())["end_to_end"]["p50_ms"] / 1000
        out["system_p50_seconds"] = p50_s
        out["speedup_vs_median_manual"] = out["median_minutes"] * 60 / p50_s if p50_s else None
        out["note"] = "speedup compares the system's core latency (LLM off) with one person's median review time; it excludes document intake, data entry and human re-checks of NEEDS_REVIEW cases."
    return out


def to_markdown(r: dict) -> str:
    if "skipped" in r:
        return f"- Manual baseline: skipped ({r['skipped']})"
    c = common.fmt
    s = (f"- Manual baseline (n={r['n']}, one reviewer): median {r['median_minutes']:.1f} min, mean {r['mean_minutes']:.1f} min; "
         f"manual accuracy {c(r['manual_accuracy'])} on {r['manual_judged']} judged cases")
    if "system_p50_seconds" in r:
        s += f"; system p50 {r['system_p50_seconds']*1000:.0f} ms -> ~{r['speedup_vs_median_manual']:.0f}x faster per decided claim. {r['note']}"
    return s


if __name__ == "__main__":
    print(to_markdown(run()))
