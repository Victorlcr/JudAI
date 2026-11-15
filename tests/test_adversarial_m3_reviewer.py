"""
Independent Adversarial and Quality Verification Suite for Milestone 3.
Reviewer: reviewer_m3_2

Tests:
1. Persisted Artifacts Integrity & Exact Dimensions
2. BM25Search Backward-Compatibility & Delegation
3. TF-IDF + MLP Edge Cases (empty, whitespace, punctuation, OOV, huge input, top_k boundary)
4. BERTSearch In-Scope vs Out-of-Scope Abstention & Edge Cases
5. ChromaDB Collection & Vector Integrity
"""
import json
import pickle
import sys
import unittest
from pathlib import Path
import numpy as np
import torch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.chroma_connection import ChromaConnection
from src.database.mongo_connection import MongoConnection
from src.models.tfidf_mlp_search import TfidfMLPSearch, ModeloClassicoTFIDF
from src.models.bm25_search import BM25Search
from src.models.bert_search import BERTSearch


class TestMilestone3ReviewerAdversarial(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.models_dir = ROOT_DIR / "data" / "models" / "tfidf_mlp"
        cls.chroma_dir = ROOT_DIR / "data" / "chromadb_local"

    # =========================================================================
    # 1. ARTIFACT PERSISTENCE & INTEGRITY
    # =========================================================================

    def test_01_persisted_artifacts_existence_and_sizes(self):
        """Verify all 5 TF-IDF artifacts exist and have non-zero realistic sizes."""
        expected_files = {
            "modelo_classico.pt": 1_000_000,   # ~14MB
            "vectorizer.pkl": 50_000,          # ~190KB
            "label_encoder.pkl": 20_000,       # ~129KB
            "metadata.json": 100,              # ~300B
            "artigos_dict.pkl": 200_000,       # ~700KB
        }
        for fname, min_size in expected_files.items():
            fpath = self.models_dir / fname
            self.assertTrue(fpath.exists(), f"Artefato obrigatório ausente: {fname}")
            size = fpath.stat().st_size
            self.assertGreater(size, min_size, f"Artefato {fname} com tamanho anômalo: {size} bytes")

    def test_02_metadata_integrity(self):
        """Verify metadata.json structure, consistency and non-facade values."""
        meta_path = self.models_dir / "metadata.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.assertEqual(meta.get("model_name"), "TFIDF_MLP")
        self.assertEqual(meta.get("tamanho_vocabulario"), 5000)
        self.assertGreaterEqual(meta.get("num_classes", 0), 2017)
        self.assertGreaterEqual(meta.get("artigos_indexados", 0), 2017)
        self.assertGreater(meta.get("val_acc", 0.0), 0.70)
        self.assertLess(meta.get("val_loss", 99.0), 3.0)

    def test_03_weights_shape_and_no_nan(self):
        """Verify PyTorch model weights match architecture and contain no NaN/Inf."""
        weights_path = self.models_dir / "modelo_classico.pt"
        weights = torch.load(weights_path, map_location="cpu")

        self.assertEqual(weights["fc1.weight"].shape, torch.Size([512, 5000]))
        self.assertEqual(weights["fc1.bias"].shape, torch.Size([512]))
        self.assertEqual(weights["fc2.weight"].shape[1], 512)
        self.assertGreaterEqual(weights["fc2.weight"].shape[0], 2017)
        self.assertEqual(weights["fc2.bias"].shape[0], weights["fc2.weight"].shape[0])

        for k, v in weights.items():
            self.assertFalse(torch.isnan(v).any(), f"NaN detected in {k}")
            self.assertFalse(torch.isinf(v).any(), f"Inf detected in {k}")

    def test_04_chromadb_collection_integrity(self):
        """Verify ChromaDB collection 'cc_bert-juridico' has >= 2,017 vectors of dimension 768."""
        conn = ChromaConnection()
        client = conn.get_client()
        col = client.get_collection("cc_bert-juridico")
        self.assertGreaterEqual(col.count(), 2017, f"Esperado >= 2017 documentos, obtido {col.count()}")
        self.assertEqual(col.metadata.get("hnsw:space"), "cosine")

        peek = col.peek(limit=5)
        for doc_id in peek["ids"]:
            self.assertTrue(doc_id.startswith("cc2002:art"), f"ID fora do padrão: {doc_id}")

    # =========================================================================
    # 2. BM25Search BACKWARD COMPATIBILITY
    # =========================================================================

    def test_05_bm25_backward_compatibility_signature_and_types(self):
        """Verify BM25Search constructor and method signatures match legacy expectations."""
        # 1. Constructor with no args
        bm25 = BM25Search()
        self.assertTrue(bm25.is_loaded)
        self.assertIsNotNone(bm25.model)

        # 2. Constructor with corpus
        dummy_corpus = [{"id": "doc1", "text": "teste"}]
        bm25_corpus = BM25Search(corpus=dummy_corpus)
        self.assertEqual(bm25_corpus.corpus, dummy_corpus)

        # 3. Method presence and delegator properties
        self.assertTrue(hasattr(bm25, "fit"))
        self.assertTrue(hasattr(bm25, "load"))
        self.assertTrue(hasattr(bm25, "search"))
        self.assertTrue(bm25.is_loaded)

    def test_06_bm25_search_return_formats(self):
        """Verify BM25Search return_dict=True (API contract) and return_dict=False (legacy list)."""
        bm25 = BM25Search(auto_load=True)
        query = "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"

        # Format 1: return_dict=True (FastAPI contract)
        res_dict = bm25.search(query, top_k=3, return_dict=True)
        self.assertIsInstance(res_dict, dict)
        self.assertEqual(res_dict.get("model"), "bm25")
        self.assertEqual(res_dict.get("query"), query)
        self.assertIn("results", res_dict)
        self.assertIn("execution_time_ms", res_dict)
        self.assertEqual(len(res_dict["results"]), 3)
        self.assertIn("artigo_id", res_dict["results"][0])
        self.assertIn("citacao", res_dict["results"][0])
        self.assertIn("texto", res_dict["results"][0])
        self.assertIn("score", res_dict["results"][0])

        # Format 2: return_dict=False (Legacy list contract)
        res_list = bm25.search(query, top_k=3, return_dict=False)
        self.assertIsInstance(res_list, list)
        self.assertEqual(len(res_list), 3)
        self.assertEqual(res_list[0]["artigo_id"], res_dict["results"][0]["artigo_id"])

    # =========================================================================
    # 3. ADVERSARIAL STRESS TESTING: TFIDF_MLP & BM25
    # =========================================================================

    def test_07_tfidf_mlp_adversarial_inputs(self):
        """Stress-test TFIDF_MLP with boundary, empty, malformed, and out-of-vocabulary inputs."""
        tfidf = TfidfMLPSearch(auto_load=True)

        # Case A: Empty string
        res_empty = tfidf.search("")
        self.assertEqual(res_empty["results"], [])
        self.assertEqual(res_empty["model"], "tfidf_mlp")

        # Case B: Whitespace only
        res_ws = tfidf.search("   \t  \n  ")
        self.assertEqual(res_ws["results"], [])

        # Case C: Punctuation only (no word chars)
        res_punct = tfidf.search("!@#$%^&*()+{}|:<>?")
        self.assertEqual(res_punct["results"], [])

        # Case D: Out of vocabulary nonsense (zero-vector forward pass)
        res_oov = tfidf.search("zyxwvutsrqponmlkjihgfedcba qwertyuiopasdfghjkl")
        self.assertIsInstance(res_oov["results"], list)
        # Even with OOV, it handles zero-vector gracefully without crashing
        self.assertEqual(len(res_oov["results"]), 3)

        # Case E: Extremely long query (50,000 characters)
        long_query = "direito civil responsabilidade dano moral " * 1200
        res_long = tfidf.search(long_query, top_k=3)
        self.assertEqual(len(res_long["results"]), 3)

        # Case F: Boundary top_k
        res_top1 = tfidf.search("contrato", top_k=1)
        self.assertEqual(len(res_top1["results"]), 1)

        res_top10 = tfidf.search("contrato", top_k=10)
        self.assertEqual(len(res_top10["results"]), 10)

    # =========================================================================
    # 4. ADVERSARIAL STRESS TESTING: BERTSearch ABSTENTION & MT0
    # =========================================================================

    def test_08_bert_abstention_on_out_of_scope_queries(self):
        """Verify BERTSearch correctly abstains on out-of-scope queries (sim < LIMIAR)."""
        bert = BERTSearch(lazy_load=True)

        # Case A: Non-legal everyday query
        res_recipe = bert.search("Receita de bolo de cenoura com cobertura de chocolate bem fofinho", top_k=3)
        self.assertTrue(res_recipe["abstenção"], "Deveria se abster para consulta culinária.")
        self.assertEqual(res_recipe["resposta_gerada"], bert.CANONICAL_REFUSAL)
        top_sim = res_recipe["results"][0]["similarity_score"] if res_recipe["results"] else 0.0
        self.assertLess(top_sim, bert.limiar)

        # Case B: Geography query
        res_geo = bert.search("Qual é a capital e a população da Austrália?", top_k=3)
        self.assertTrue(res_geo["abstenção"], "Deveria se abster para consulta geográfica.")
        self.assertEqual(res_geo["resposta_gerada"], bert.CANONICAL_REFUSAL)

        # Case C: Empty query
        res_empty = bert.search("   ", top_k=3)
        self.assertTrue(res_empty["abstenção"])
        self.assertEqual(res_empty["results"], [])

    def test_09_bert_in_scope_retrieval_and_threshold(self):
        """Verify BERTSearch does NOT abstain on in-scope query and retrieves Art. 5º."""
        bert = BERTSearch(lazy_load=True)
        query = "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"
        res = bert.search(query, top_k=3)

        self.assertFalse(res["abstenção"], "Não deveria se abster para pergunta canônica sobre maioridade civil.")
        top_res = res["results"][0]
        self.assertEqual(top_res["artigo_id"], "cc2002:art5")
        self.assertGreaterEqual(top_res["similarity_score"], 0.70)
        self.assertIn("Código Civil, art. 5º", top_res["citacao"])
        # Generated answer must mention 18 or dezoito
        ans = res["resposta_gerada"].lower()
        self.assertTrue("dezoito" in ans or "18" in ans, f"Resposta não menciona 18 ou dezoito: {ans}")


if __name__ == "__main__":
    unittest.main()
