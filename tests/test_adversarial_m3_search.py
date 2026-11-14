"""
Adversarial Empirical Stress Test Suite for Milestone 3 (TfidfMLPSearch & BM25Search)
=====================================================================================
Author: challenger_m3_1 (Empirical Challenger)
Target Components:
  - src.models.tfidf_mlp_search.TfidfMLPSearch
  - src.models.bm25_search.BM25Search
Verification Dimensions:
  1. Top-1 and Top-3 accuracy on all 12 questions of data/dataset/avaliacao_inicial.jsonl.
  2. Contract schema conformity (model, query, results, execution_time_ms, artigo_id, citacao, texto, score).
  3. Edge cases: empty string, whitespace, 1-char queries, punctuation-only, out-of-domain words,
     extreme length, special characters, unicode/emojis.
  4. Parameter stress: top_k=0, top_k=1, top_k=5, top_k=3000.
  5. Latency profiling: mean, p50, p95, p99 across multiple queries.
  6. Ground-truth reference query verification (Art. 5º do Código Civil).
"""

import json
import re
import sys
import time
import unittest
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tfidf_mlp_search import TfidfMLPSearch
from src.models.bm25_search import BM25Search


class TestAdversarialM3Search(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tfidf_search = TfidfMLPSearch(auto_load=True)
        assert cls.tfidf_search.is_loaded, "TfidfMLPSearch failed to load saved artifacts"

        cls.bm25_search = BM25Search(auto_load=True)
        assert cls.bm25_search.is_loaded, "BM25Search failed to load delegate artifacts"

        cls.eval_dataset_path = PROJECT_ROOT / "data" / "dataset" / "avaliacao_inicial.jsonl"
        assert cls.eval_dataset_path.exists(), f"Evaluation dataset not found at {cls.eval_dataset_path}"

        cls.eval_samples: list[dict[str, str]] = []
        with open(cls.eval_dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cls.eval_samples.append(json.loads(line))
        assert len(cls.eval_samples) == 12, f"Expected 12 eval samples, found {len(cls.eval_samples)}"

    def test_01_accuracy_all_12_questions_tfidf_mlp(self):
        """Evaluate Top-1 and Top-3 accuracy on all 12 questions from avaliacao_inicial.jsonl."""
        top1_hits = 0
        top3_hits = 0
        details = []

        for idx, item in enumerate(self.eval_samples):
            query = item["pergunta"]
            expected_artigo = item["artigo_id"]

            resp = self.tfidf_search.search(query, top_k=3)
            self.assertEqual(resp["model"], "tfidf_mlp")
            self.assertEqual(resp["query"], query)

            results = resp.get("results", [])
            retrieved_ids = [r["artigo_id"] for r in results]

            is_top1 = bool(retrieved_ids and retrieved_ids[0] == expected_artigo)
            is_top3 = bool(expected_artigo in retrieved_ids)

            if is_top1:
                top1_hits += 1
            if is_top3:
                top3_hits += 1

            details.append({
                "idx": idx + 1,
                "pergunta": query,
                "expected": expected_artigo,
                "retrieved": retrieved_ids,
                "top1_match": is_top1,
                "top3_match": is_top3,
                "top1_score": results[0]["score"] if results else 0.0,
                "latency_ms": resp["execution_time_ms"]
            })

        total = len(self.eval_samples)
        top1_acc = top1_hits / total
        top3_acc = top3_hits / total

        print(f"\n--- [TfidfMLPSearch] AVALIAÇÃO DOS 12 CASOS ---")
        for d in details:
            status = "TOP-1 HIT" if d["top1_match"] else ("TOP-3 HIT" if d["top3_match"] else "MISS")
            print(f"[{d['idx']:02d}] {status:10s} | Exp: {d['expected']:14s} | Top: {d['retrieved']} | Score: {d['top1_score']:.4f} | {d['latency_ms']:.2f}ms")

        print(f"Top-1 Accuracy: {top1_acc * 100:.1f}% ({top1_hits}/{total})")
        print(f"Top-3 Accuracy: {top3_acc * 100:.1f}% ({top3_hits}/{total})")

        # Acceptance thresholds: Top-3 must be at least 90%, Top-1 at least 75%
        self.assertGreaterEqual(top3_acc, 0.90, f"Top-3 accuracy too low: {top3_acc}")
        self.assertGreaterEqual(top1_acc, 0.75, f"Top-1 accuracy too low: {top1_acc}")

    def test_02_accuracy_all_12_questions_bm25_delegation(self):
        """Evaluate Top-1 and Top-3 accuracy on all 12 questions through BM25Search delegator."""
        top1_hits = 0
        top3_hits = 0

        for item in self.eval_samples:
            query = item["pergunta"]
            expected_artigo = item["artigo_id"]

            resp = self.bm25_search.search(query, top_k=3, return_dict=True)
            self.assertEqual(resp["model"], "bm25")
            self.assertEqual(resp["query"], query)

            retrieved_ids = [r["artigo_id"] for r in resp["results"]]
            if retrieved_ids and retrieved_ids[0] == expected_artigo:
                top1_hits += 1
            if expected_artigo in retrieved_ids:
                top3_hits += 1

        total = len(self.eval_samples)
        top1_acc = top1_hits / total
        top3_acc = top3_hits / total

        self.assertGreaterEqual(top3_acc, 0.90)
        self.assertGreaterEqual(top1_acc, 0.75)

    def test_03_contract_fields_and_types(self):
        """Strictly verify contract fields, types, and constraints on responses."""
        query = "Como funciona a emancipação aos 16 anos?"
        resp = self.tfidf_search.search(query, top_k=3)

        # Root dictionary fields
        self.assertIn("model", resp)
        self.assertEqual(resp["model"], "tfidf_mlp")
        self.assertIn("query", resp)
        self.assertEqual(resp["query"], query)
        self.assertIn("results", resp)
        self.assertIsInstance(resp["results"], list)
        self.assertIn("execution_time_ms", resp)
        self.assertIsInstance(resp["execution_time_ms"], (float, int))
        self.assertGreater(resp["execution_time_ms"], 0.0)

        # Result item fields
        self.assertGreater(len(resp["results"]), 0)
        for r in resp["results"]:
            self.assertIn("artigo_id", r)
            self.assertTrue(re.match(r"^cc2002:art\d+", r["artigo_id"]), f"Invalid artigo_id: {r['artigo_id']}")
            self.assertIn("citacao", r)
            self.assertIsInstance(r["citacao"], str)
            self.assertTrue(r["citacao"].startswith("Código Civil"), f"Invalid citacao: {r['citacao']}")
            self.assertIn("texto", r)
            self.assertIsInstance(r["texto"], str)
            self.assertGreater(len(r["texto"].strip()), 0)
            self.assertIn("score", r)
            self.assertIsInstance(r["score"], float)
            self.assertGreaterEqual(r["score"], 0.0)
            self.assertLessEqual(r["score"], 1.0)

        # BM25 return_dict=False contract
        legacy_results = self.bm25_search.search(query, top_k=3, return_dict=False)
        self.assertIsInstance(legacy_results, list)
        self.assertEqual(len(legacy_results), len(resp["results"]))
        self.assertEqual(legacy_results[0]["artigo_id"], resp["results"][0]["artigo_id"])

    def test_04_edge_case_empty_and_whitespace(self):
        """Stress-test empty strings and whitespace-only queries."""
        empty_queries = ["", "   ", "\t", "\n\n   \t "]
        for q in empty_queries:
            resp_tfidf = self.tfidf_search.search(q, top_k=3)
            self.assertEqual(resp_tfidf["model"], "tfidf_mlp")
            self.assertEqual(resp_tfidf["query"], q)
            self.assertEqual(resp_tfidf["results"], [])
            self.assertIsInstance(resp_tfidf["execution_time_ms"], (float, int))

            resp_bm25 = self.bm25_search.search(q, top_k=3)
            self.assertEqual(resp_bm25["model"], "bm25")
            self.assertEqual(resp_bm25["query"], q)
            self.assertEqual(resp_bm25["results"], [])

            resp_bm25_legacy = self.bm25_search.search(q, top_k=3, return_dict=False)
            self.assertEqual(resp_bm25_legacy, [])

    def test_05_edge_case_one_character_and_punctuation(self):
        """Stress-test single-character and punctuation-only queries."""
        one_char_queries = ["a", "z", "1", "?", "!", ".", "-", "_"]
        for q in one_char_queries:
            resp = self.tfidf_search.search(q, top_k=3)
            self.assertIsInstance(resp, dict)
            self.assertIn("results", resp)
            self.assertIn("execution_time_ms", resp)
            self.assertIsInstance(resp["results"], list)
            # Should not crash; if tokens were dropped by tokenizer, either returns empty or top neural bias
            if resp["results"]:
                for r in resp["results"]:
                    self.assertIn("artigo_id", r)
                    self.assertIn("citacao", r)
                    self.assertIn("score", r)

        punct_queries = ["!@#$%^&*()", "???...;;;,,,---", "--> <--- /\\"]
        for q in punct_queries:
            resp = self.tfidf_search.search(q, top_k=3)
            self.assertIsInstance(resp, dict)
            self.assertEqual(resp["results"], [])

    def test_06_edge_case_out_of_domain_words(self):
        """Stress-test out-of-domain words and completely unknown vocabulary."""
        ood_queries = [
            "quantum chromodynamics entanglement higgs boson supersymmetry",
            "receita culinária de bolo de cenoura com cobertura de chocolate e calda",
            "supercalifragilisticexpialidocious xyzwqplkjmnbvcxz",
            "1234567890 0987654321 555555555"
        ]
        for q in ood_queries:
            resp = self.tfidf_search.search(q, top_k=3)
            self.assertIsInstance(resp, dict)
            self.assertIn("results", resp)
            self.assertIn("execution_time_ms", resp)
            # Model must not crash or throw exceptions
            self.assertLessEqual(len(resp["results"]), 3)

    def test_07_edge_case_extreme_inputs(self):
        """Stress-test extremely long queries, SQL-injection patterns, and unicode/emojis."""
        # Extreme length (10,000 characters)
        long_query = "contrato de locação urbana inadimplemento rescisão " * 200
        resp_long = self.tfidf_search.search(long_query, top_k=3)
        self.assertIsInstance(resp_long, dict)
        self.assertGreater(len(resp_long["results"]), 0)

        # Injection-like strings
        inj_query = "'; DROP TABLE artigos; SELECT * FROM users WHERE '1'='1"
        resp_inj = self.tfidf_search.search(inj_query, top_k=3)
        self.assertIsInstance(resp_inj, dict)

        # Unicode and emojis invariance
        base_query = "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"
        emoji_query = f"⚖️📜 {base_query} 🏛️👶🧑"
        resp_base = self.tfidf_search.search(base_query, top_k=3)
        resp_emoji = self.tfidf_search.search(emoji_query, top_k=3)

        self.assertIsInstance(resp_emoji, dict)
        ids_base = [r["artigo_id"] for r in resp_base["results"]]
        ids_emoji = [r["artigo_id"] for r in resp_emoji["results"]]

        self.assertEqual(ids_base, ids_emoji, "Emoji stripping should yield identical results to clean query")
        self.assertEqual(ids_emoji[0], "cc2002:art5", "Emojis must not prevent recovering Art. 5º")

    def test_08_top_k_parameter_variations(self):
        """Stress-test variations of top_k: 0, 1, 5, 2017, and oversized values."""
        query = "A menoridade cessa aos dezoito anos?"

        # top_k = 0
        resp_0 = self.tfidf_search.search(query, top_k=0)
        self.assertEqual(len(resp_0["results"]), 0)

        # top_k = 1
        resp_1 = self.tfidf_search.search(query, top_k=1)
        self.assertEqual(len(resp_1["results"]), 1)
        self.assertEqual(resp_1["results"][0]["artigo_id"], "cc2002:art5")

        # top_k = 5
        resp_5 = self.tfidf_search.search(query, top_k=5)
        self.assertEqual(len(resp_5["results"]), 5)

        # top_k = 5000 (oversized)
        total_classes = self.tfidf_search.metadata.get("num_classes", 2017)
        resp_oversized = self.tfidf_search.search(query, top_k=5000)
        self.assertEqual(len(resp_oversized["results"]), total_classes)

    def test_09_ground_truth_reference_query_art5(self):
        """Explicitly verify the project's canonical reference query for Art. 5º."""
        ref_query = "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"

        resp_tfidf = self.tfidf_search.search(ref_query, top_k=3)
        self.assertGreater(len(resp_tfidf["results"]), 0)
        top1 = resp_tfidf["results"][0]
        self.assertEqual(top1["artigo_id"], "cc2002:art5", f"Expected cc2002:art5 at Top-1, got {top1['artigo_id']}")
        self.assertIn("art. 5", top1["citacao"])
        self.assertIn("dezoito anos", top1["texto"].lower())
        self.assertGreaterEqual(top1["score"], 0.90, f"Expected confidence >= 90%, got {top1['score']}")

        resp_bm25 = self.bm25_search.search(ref_query, top_k=3)
        self.assertEqual(resp_bm25["results"][0]["artigo_id"], "cc2002:art5")

    def test_10_latency_benchmark(self):
        """Profile execution latency over 50 consecutive queries."""
        queries = [
            "Quem é absolutamente incapaz de exercer pessoalmente os atos da vida civil?",
            "Como se dá a sucessão legítima entre os descendentes e o cônjuge?",
            "Qual o prazo prescricional para reparação civil?",
            "Quais os requisitos de validade do negócio jurídico?",
            "O que caracteriza a responsabilidade civil objetiva?"
        ] * 10  # 50 queries

        latencies = []
        for q in queries:
            t0 = time.perf_counter()
            _ = self.tfidf_search.search(q, top_k=3)
            dt_ms = (time.perf_counter() - t0) * 1000
            latencies.append(dt_ms)

        mean_lat = sum(latencies) / len(latencies)
        sorted_lat = sorted(latencies)
        p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        p99 = sorted_lat[int(len(sorted_lat) * 0.99)]

        print(f"\n--- [TfidfMLPSearch] LATÊNCIA ({len(queries)} consultas) ---")
        print(f"Média: {mean_lat:.2f} ms | p50: {p50:.2f} ms | p95: {p95:.2f} ms | p99: {p99:.2f} ms")

        # Performance constraint: mean latency must be under 30ms, p95 under 50ms
        self.assertLess(mean_lat, 30.0, f"Mean latency exceeds 30ms: {mean_lat:.2f}ms")
        self.assertLess(p95, 50.0, f"p95 latency exceeds 50ms: {p95:.2f}ms")


if __name__ == "__main__":
    unittest.main()
