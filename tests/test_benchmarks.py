import json, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "eval"))
import faithfulness_eval as F   # noqa: E402
import perf_bench as P          # noqa: E402


class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps({"decision": "ADMISSIBLE", "llm_narration": {"succeeded": True}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


class TestFaithfulness(unittest.TestCase):
    def test_numbers_and_preservation(self):
        self.assertEqual(F.numbers("capped at 1.0% or INR 5,000"), {1.0, 5000.0})
        self.assertTrue(F.numbers_preserved("Room: INR 5,000 of 30,000 (1.0%)", "Only 5000 of 30000 is paid, a 1% cap"))
        self.assertFalse(F.numbers_preserved("capped at 25%", "capped at a quarter"))

    def test_numeric_support_detects_bad_citation(self):
        chunks = {"A": "Room expenses: 1.0% of Sum Insured", "B": "nothing numeric here"}
        resp = [{"citations": [{"claim": "capped at 1.0% of Sum Insured", "chunk_id": "A"},
                               {"claim": "30-day waiting period", "chunk_id": "B"}]}]
        d = F.deterministic(resp, chunks)
        self.assertEqual((d["numeric_checked"], d["numeric_supported"]), (2, 1))
        self.assertEqual(d["numeric_failures"][0]["chunk_id"], "B")

    def test_judge_parsing_and_scoring(self):
        self.assertIs(F.parse_judge('noise {"supported": true, "reason": "x"}'), True)
        self.assertIsNone(F.parse_judge("no json"))
        chunks = {"A": "text a", "B": "text b"}
        resp = [{"citations": [{"claim": "c1", "chunk_id": "A"}, {"claim": "c2", "chunk_id": "B"}]}]
        r = F.llm_judge(resp, chunks, judge=lambda claim, ex: claim == "c1")
        self.assertEqual((r["supported"], r["judged"]), (1, 2))

        detail = F.parse_judge_detail(
            '{"supported": false, "reason": "The excerpt does not mention this exclusion."}'
        )

        self.assertEqual(detail["supported"], False)
        self.assertEqual(
            detail["reason"],
            "The excerpt does not mention this exclusion."
        )


class TestPerf(unittest.TestCase):
    def test_api_benchmark_against_stub_server(self):
        srv = HTTPServer(("127.0.0.1", 0), _Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            r = P.run_api(f"http://127.0.0.1:{srv.server_address[1]}", requests_total=12, concurrency=3, warmup=1)
        finally:
            srv.shutdown()
        self.assertEqual(r["concurrent"]["error_rate"], 0)
        self.assertGreater(r["concurrent"]["throughput_rps"], 0)
        self.assertEqual(r["sequential"]["llm_narration_success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
