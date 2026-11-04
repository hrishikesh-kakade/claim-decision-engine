"""Latency / throughput benchmark.

In-process mode (default): times ClaimEngine.analyze() on all 18 cases x RUNS after WARMUP passes,
and reads per-agent timings from each response's trace. Reports cold start, p50/p90/p95/p99.
  --llm-off   disables the LLM narration so you measure the deterministic core only.
API mode (--api-url): measures what a real client sees over HTTP, optionally under concurrency:
  throughput = successful requests / wall-clock seconds; error rate = non-200 or failed requests.

Run: python eval/perf_bench.py [--runs 5] [--llm-off]
     python eval/perf_bench.py --api-url http://localhost:8000 --requests 60 --concurrency 4
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import common
import metrics_lib as M


def run_in_process(engine, cold_start_ms: float, runs: int = 5, warmup: int = 1, llm_off: bool = False) -> dict:
    import backend.agents.llm_writer as writer
    from backend.models import ClaimCase
    old = os.environ.get("LLM_PROVIDER")
    if llm_off:
        os.environ["LLM_PROVIDER"] = "none"
        writer._client = None
    try:
        cases = [ClaimCase.model_validate(c) for c in common.load_cases()]
        for _ in range(warmup):
            for c in cases:
                engine.analyze(c)
        e2e, stages, per_case = [], defaultdict(list), defaultdict(list)
        llm_called = llm_ok = 0
        for _ in range(runs):
            for c in cases:
                t0 = time.perf_counter()
                resp = engine.analyze(c)
                ms = (time.perf_counter() - t0) * 1000
                e2e.append(ms); per_case[c.case_id].append(ms)
                for s in resp.trace:
                    if s.elapsed_ms is not None:
                        stages[s.agent].append(s.elapsed_ms)
                info = resp.llm_narration or {}
                llm_called += bool(info.get("called")); llm_ok += bool(info.get("succeeded"))
        slowest = sorted(((sum(v) / len(v), k) for k, v in per_case.items()), reverse=True)[:3]
        return {"mode": "in_process", "llm": "off" if llm_off else (os.environ.get("LLM_PROVIDER") or "auto"),
                "cold_start_ms": cold_start_ms, "runs": runs, "warmup_passes": warmup, "n_cases": len(cases),
                "end_to_end": M.summarize_latency(e2e),
                "stages": {k: M.summarize_latency(v) for k, v in stages.items()},
                "llm_calls": {"called": llm_called, "succeeded": llm_ok, "total_requests": len(e2e)},
                "slowest_cases_mean_ms": [{"case_id": k, "mean_ms": v} for v, k in slowest]}
    finally:
        if llm_off:
            if old is None:
                os.environ.pop("LLM_PROVIDER", None)
            else:
                os.environ["LLM_PROVIDER"] = old
            writer._client = None


def _post(url: str, payload: dict, timeout: float = 120.0):
    req = urllib.request.Request(url.rstrip("/") + "/analyze", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body, status = json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        body, status = None, e.code
    except Exception:
        body, status = None, 0
    return status, (time.perf_counter() - t0) * 1000, body


def run_api(api_url: str, requests_total: int = 60, concurrency: int = 4, warmup: int = 3) -> dict:
    cases = common.load_cases()
    for i in range(warmup):                       # first hit may be a cold start on free hosting
        _post(api_url, cases[i % len(cases)])
    out = {"mode": "api", "api_url": api_url, "requests": requests_total}
    for label, conc in (("sequential", 1), ("concurrent", concurrency)):
        payloads = [cases[i % len(cases)] for i in range(requests_total)]
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=conc) as ex:
            results = list(ex.map(lambda p: _post(api_url, p), payloads))
        wall = time.perf_counter() - t0
        ok = [r for r in results if r[0] == 200]
        llm_ok = sum(1 for r in ok if (r[2] or {}).get("llm_narration", {}) and r[2]["llm_narration"].get("succeeded"))
        out[label] = {"concurrency": conc, "wall_s": wall, "throughput_rps": len(ok) / wall if wall else None,
                      "error_rate": 1 - len(ok) / len(results), "latency": M.summarize_latency([r[1] for r in ok]),
                      "llm_narration_success_rate": llm_ok / len(ok) if ok else None}
    return out


def to_markdown(r: dict) -> str:
    f = common.fmt
    if r["mode"] == "api":
        L = [f"HTTP benchmark against `{r['api_url']}` ({r['requests']} requests per scenario):", "",
             "| Scenario | Concurrency | p50 ms | p95 ms | p99 ms | Throughput req/s | Error rate | LLM narration success |",
             "|---|---|---|---|---|---|---|---|"]
        for k in ("sequential", "concurrent"):
            s = r[k]; l = s["latency"]
            L.append(f"| {k} | {s['concurrency']} | {f(l.get('p50_ms'),1)} | {f(l.get('p95_ms'),1)} | {f(l.get('p99_ms'),1)} | "
                     f"{f(s['throughput_rps'],2)} | {s['error_rate']:.1%} | {f(s['llm_narration_success_rate'],2)} |")
        return "\n".join(L)
    e = r["end_to_end"]
    L = [f"In-process `ClaimEngine.analyze()`; LLM narration: **{r['llm']}**; {r['n_cases']} cases x {r['runs']} runs "
         f"(n={e['n']}) after {r['warmup_passes']} warm-up pass(es). Cold start (engine init): **{r['cold_start_ms']:.0f} ms**.", "",
         "| Stage | n | p50 ms | p95 ms | p99 ms | mean ms | max ms |", "|---|---|---|---|---|---|---|",
         f"| **End-to-end** | {e['n']} | {e['p50_ms']:.1f} | {e['p95_ms']:.1f} | {e['p99_ms']:.1f} | {e['mean_ms']:.1f} | {e['max_ms']:.1f} |"]
    for k, s in r["stages"].items():
        L.append(f"| {k} | {s['n']} | {s['p50_ms']:.2f} | {s['p95_ms']:.2f} | {s['p99_ms']:.2f} | {s['mean_ms']:.2f} | {s['max_ms']:.2f} |")
    lc = r["llm_calls"]
    L.append(f"\nLLM narration calls: {lc['called']}/{lc['total_requests']} requests attempted, {lc['succeeded']} succeeded.")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--llm-off", action="store_true")
    ap.add_argument("--api-url")
    ap.add_argument("--requests", type=int, default=60)
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    common.load_env()
    if a.api_url:
        res = run_api(a.api_url, a.requests, a.concurrency)
    else:
        engine, cold = common.build_engine()
        res = run_in_process(engine, cold, runs=a.runs, llm_off=a.llm_off)
    common.write_json("perf_bench_api.json" if a.api_url else "perf_bench.json", res)
    print(to_markdown(res))
