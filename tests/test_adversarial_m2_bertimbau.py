"""
Adversarial and empirical verification suite for Milestone 2:
notebooks/01_transformer_bertimbau_mt0.ipynb data loading and dataset splitting.

Author: challenger_m2_1 (Empirical Challenger)
"""

import json
import re
import sys
import unittest
from pathlib import Path

# Ensure JudAI root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.mongo_connection import MongoConnection


class TestAdversarialNotebookBertimbau(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb_path = ROOT_DIR / "notebooks" / "01_transformer_bertimbau_mt0.ipynb"
        assert cls.nb_path.exists(), f"Notebook file not found at {cls.nb_path}"

        with open(cls.nb_path, "r", encoding="utf-8") as f:
            cls.nb = json.load(f)

        cls.cells = cls.nb.get("cells", [])

    def test_01_notebook_structure_and_no_legacy_paths(self):
        """Verify notebook is valid nbformat v4 and has no prohibited Colab/Drive/local-json paths."""
        self.assertIn("nbformat", self.nb)
        self.assertEqual(self.nb["nbformat"], 4)
        self.assertGreaterEqual(len(self.cells), 30)

        prohibited_patterns = [
            r"/content/drive",
            r"drive\.mount",
            r"data/artigos",
            r"busca_treino\.jsonl",  # legacy requirement of 7 external jsonl files
            r"gerador_treino\.jsonl",
        ]

        for idx, cell in enumerate(self.cells):
            source = "".join(cell.get("source", []))
            for pattern in prohibited_patterns:
                self.assertIsNone(
                    re.search(pattern, source),
                    f"Cell {idx} contains prohibited pattern '{pattern}'"
                )

    def test_02_mongo_connection_active_articles_count(self):
        """Empirically verify MongoConnection returns exactly 2,017 active cc2002 articles."""
        conn = MongoConnection()
        db = conn.get_db()
        self.assertIsNotNone(db, "Failed to connect to MongoDB")

        total_docs = db["artigos"].count_documents({})
        self.assertEqual(total_docs, 2083, f"Expected 2083 total documents in artigos collection, got {total_docs}")

        query = {"lei_id": "cc2002", "vigente": True}
        active_count = db["artigos"].count_documents(query)
        self.assertEqual(active_count, 2017, f"Expected exactly 2017 active articles, got {active_count}")

        # Test field integrity on active articles
        sample = list(db["artigos"].find(query).limit(50))
        for doc in sample:
            self.assertTrue(doc["_id"].startswith("cc2002:art"), f"Invalid _id format: {doc['_id']}")
            self.assertTrue(doc.get("vigente") is True, f"Article not vigente: {doc['_id']}")
            self.assertTrue(doc.get("citacao"), f"Missing citacao: {doc['_id']}")
            texto = doc.get("texto_vigente") or doc.get("texto")
            self.assertTrue(texto and len(texto.strip()) > 0, f"Empty text for {doc['_id']}")

    def test_03_extract_and_execute_cell7_mongo_loading(self):
        """Extract and execute Cell 7 from notebook, verifying 2,017 articles and passagens."""
        cell7_source = "".join(self.cells[7]["source"])
        self.assertIn("MongoConnection", cell7_source)
        self.assertIn("db[\"artigos\"].find", cell7_source)

        env = {"__file__": str(self.nb_path), "re": re}
        exec(cell7_source, env)

        artigos = env.get("artigos")
        passagens = env.get("passagens")
        ids_passagens = env.get("ids_passagens")
        indice_de = env.get("indice_de")
        passagem_por_id = env.get("passagem_por_id")
        textos_idx = env.get("textos_idx")

        self.assertIsInstance(artigos, dict)
        self.assertEqual(len(artigos), 2017, f"Expected 2017 articles in cell 7, got {len(artigos)}")

        self.assertIsInstance(passagens, list)
        self.assertEqual(len(passagens), 2017, f"Expected 2017 passagens in cell 7, got {len(passagens)}")

        self.assertEqual(len(ids_passagens), 2017)
        self.assertEqual(len(indice_de), 2017)
        self.assertEqual(len(passagem_por_id), 2017)
        self.assertEqual(len(textos_idx), 2017)

        # Check that no passage has empty text or empty citation
        for p in passagens:
            self.assertTrue(p["id"].startswith("cc2002:art"))
            self.assertGreater(len(p["citacao"]), 0)
            self.assertGreater(len(p["texto"]), 0)

    def test_04_extract_and_execute_cell9_zero_leakage_split(self):
        """Extract and execute Cell 9 from notebook in an execution environment chained from Cell 5 and Cell 7."""
        cell5_source = "".join(self.cells[5]["source"])
        cell7_source = "".join(self.cells[7]["source"])
        cell9_source = "".join(self.cells[9]["source"])

        # Execute Cell 5, 7, 9 in a fresh context
        exec_globals = {
            "__file__": str(self.nb_path),
        }
        exec(cell5_source, exec_globals)
        exec(cell7_source, exec_globals)
        exec(cell9_source, exec_globals)

        # Retrieve outputs from Cell 9
        pares_raw = exec_globals["pares_raw"]
        aval_raw = exec_globals["aval_raw"]
        art_pares = exec_globals["art_pares"]
        art_aval = exec_globals["art_aval"]
        art_exclusivos_pares = exec_globals["art_exclusivos_pares"]
        art_treino = exec_globals["art_treino"]
        art_val = exec_globals["art_val"]
        art_novo = exec_globals["art_novo"]

        busca_treino = exec_globals["busca_treino"]
        busca_val = exec_globals["busca_val"]
        busca_teste_visto = exec_globals["busca_teste_visto"]
        busca_teste_novo = exec_globals["busca_teste_novo"]

        gerador_treino = exec_globals["gerador_treino"]
        gerador_val = exec_globals["gerador_val"]
        gerador_teste_visto = exec_globals["gerador_teste_visto"]
        gerador_teste = exec_globals["gerador_teste"]

        # 1. Dataset sizes
        self.assertEqual(len(pares_raw), 72, "pares_raw must have 72 pairs")
        self.assertEqual(len(aval_raw), 12, "aval_raw must have 12 questions")
        self.assertEqual(len(art_pares), 24, "art_pares must have 24 distinct articles")
        self.assertEqual(len(art_aval), 12, "art_aval must have 12 distinct articles")
        self.assertEqual(len(art_exclusivos_pares), 12, "art_exclusivos_pares must have 12 distinct articles")

        # 2. Article partition mutual exclusivity (Zero Article Leakage)
        self.assertEqual(len(art_treino), 16, f"Expected 16 training articles, got {len(art_treino)}")
        self.assertEqual(len(art_val), 4, f"Expected 4 validation articles, got {len(art_val)}")
        self.assertEqual(len(art_novo), 4, f"Expected 4 test_novo articles, got {len(art_novo)}")

        self.assertEqual(art_treino & art_val, set(), "Leakage detected: art_treino & art_val not empty!")
        self.assertEqual(art_treino & art_novo, set(), "Leakage detected: art_treino & art_novo not empty!")
        self.assertEqual(art_val & art_novo, set(), "Leakage detected: art_val & art_novo not empty!")
        self.assertEqual(art_treino | art_val | art_novo, set(art_pares), "Partition does not cover all 24 articles!")

        # 3. Search sets sizes and leak-free checks
        self.assertEqual(len(busca_treino), 48, f"Expected 48 busca_treino pairs (16 * 3), got {len(busca_treino)}")
        self.assertEqual(len(busca_val), 12, f"Expected 12 busca_val pairs (4 * 3), got {len(busca_val)}")
        self.assertEqual(len(busca_teste_novo), 12, f"Expected 12 busca_teste_novo pairs (4 * 3), got {len(busca_teste_novo)}")
        self.assertEqual(len(busca_teste_visto), 12, f"Expected 12 busca_teste_visto pairs, got {len(busca_teste_visto)}")

        art = lambda linhas: {l["artigo_id"] for l in linhas if l["artigo_id"]}
        perg = lambda linhas: {l["pergunta"].strip().lower() for l in linhas}

        self.assertEqual(art(busca_treino) & art(busca_val), set(), "Article leakage: busca_treino & busca_val")
        self.assertEqual(art(busca_treino) & art(busca_teste_novo), set(), "Article leakage: busca_treino & busca_teste_novo")
        self.assertEqual(art(busca_val) & art(busca_teste_novo), set(), "Article leakage: busca_val & busca_teste_novo")

        # Test visto: articles must be seen in training
        self.assertTrue(art(busca_teste_visto).issubset(art(busca_treino)), "All articles in teste_visto must be in treino")

        # Question uniqueness across sets: zero question leakage
        p_treino = perg(busca_treino)
        p_val = perg(busca_val)
        p_teste_visto = perg(busca_teste_visto)
        p_teste_novo = perg(busca_teste_novo)

        self.assertEqual(p_treino & p_val, set(), "Question leakage: p_treino & p_val")
        self.assertEqual(p_treino & p_teste_visto, set(), "Question leakage: p_treino & p_teste_visto")
        self.assertEqual(p_treino & p_teste_novo, set(), "Question leakage: p_treino & p_teste_novo")
        self.assertEqual(p_val & p_teste_visto, set(), "Question leakage: p_val & p_teste_visto")
        self.assertEqual(p_val & p_teste_novo, set(), "Question leakage: p_val & p_teste_novo")
        self.assertEqual(p_teste_visto & p_teste_novo, set(), "Question leakage: p_teste_visto & p_teste_novo")

        # 4. Generator sets sizes and out-of-scope integrity
        self.assertEqual(len(gerador_treino), 48 + 6)
        self.assertEqual(len(gerador_val), 12 + 3)
        self.assertEqual(len(gerador_teste), 12 + 3)
        self.assertEqual(len(gerador_teste_visto), 12)

        fora_treino = [l for l in gerador_treino if l["artigo_id"] is None]
        fora_val = [l for l in gerador_val if l["artigo_id"] is None]
        fora_teste = [l for l in gerador_teste if l["artigo_id"] is None]
        self.assertEqual(len(fora_treino), 6)
        self.assertEqual(len(fora_val), 3)
        self.assertEqual(len(fora_teste), 3)

        perg_fora = lambda linhas: {l["pergunta"].strip().lower() for l in linhas}
        self.assertEqual(perg_fora(fora_treino) & perg_fora(fora_val), set())
        self.assertEqual(perg_fora(fora_treino) & perg_fora(fora_teste), set())
        self.assertEqual(perg_fora(fora_val) & perg_fora(fora_teste), set())

    def test_05_adversarial_discard_check(self):
        """Adversarially check if any raw pairs or evaluation items are dropped by so_validas."""
        pares_path = ROOT_DIR / "data" / "dataset" / "pares_bert_inicial.jsonl"
        aval_path = ROOT_DIR / "data" / "dataset" / "avaliacao_inicial.jsonl"

        with open(pares_path, "r", encoding="utf-8") as f:
            raw_pares = [json.loads(line) for line in f if line.strip()]
        with open(aval_path, "r", encoding="utf-8") as f:
            raw_aval = [json.loads(line) for line in f if line.strip()]

        conn = MongoConnection()
        active_ids = set(conn.get_db()["artigos"].distinct("_id", {"lei_id": "cc2002", "vigente": True}))

        # Assert zero drops
        pares_invalid_ids = [p["artigo_id"] for p in raw_pares if p.get("artigo_id") not in active_ids]
        aval_invalid_ids = [a["artigo_id"] for a in raw_aval if a.get("artigo_id") not in active_ids]

        self.assertEqual(len(pares_invalid_ids), 0, f"Unmatched article IDs in pares_raw: {pares_invalid_ids}")
        self.assertEqual(len(aval_invalid_ids), 0, f"Unmatched article IDs in aval_raw: {aval_invalid_ids}")


if __name__ == "__main__":
    unittest.main()
