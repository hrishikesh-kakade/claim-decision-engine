import math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
import metrics_lib as m


class TestMetrics(unittest.TestCase):
    def test_percentile_matches_numpy_definition(self):
        self.assertEqual(m.percentile([1, 2, 3, 4, 5], 50), 3)
        self.assertAlmostEqual(m.percentile(list(range(1, 101)), 95), 95.05)
        self.assertEqual(m.percentile([7], 99), 7)

    def test_wilson_18_of_18(self):
        lo, hi = m.wilson_interval(18, 18)
        self.assertTrue(0.82 < lo < 0.83)
        self.assertAlmostEqual(hi, 1.0, places=6)

    def test_retrieval_metrics(self):
        ranked = ["a", "b", "c", "d", "e"]
        rel = ["c", "z"]
        self.assertEqual(m.hit_at_k(ranked, rel, 2), 0.0)
        self.assertEqual(m.hit_at_k(ranked, rel, 3), 1.0)
        self.assertEqual(m.recall_at_k(ranked, rel, 5), 0.5)
        self.assertAlmostEqual(m.reciprocal_rank(ranked, rel), 1 / 3)
        self.assertAlmostEqual(m.precision_at_k(ranked, rel, 5), 0.2)
        self.assertAlmostEqual(m.ndcg_at_k(["c", "z"], ["c", "z"], 5), 1.0)
        self.assertAlmostEqual(m.average_precision_at_k(["c"], ["c"], 5), 1.0)
        # relevant at rank 3 only, 1 relevant: AP = (1/3)/1
        self.assertAlmostEqual(m.average_precision_at_k(["a", "b", "c"], ["c"], 5), 1 / 3)

    def test_prf(self):
        r = m.prf(0, 2, 3)
        self.assertEqual(r["precision"], 0.0)
        self.assertEqual(r["recall"], 0.0)
        self.assertEqual(r["f1"], 0.0)


if __name__ == "__main__":
    unittest.main()
