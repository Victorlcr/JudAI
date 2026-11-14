"""
Suíte Completa de Testes Automatizados para a API FastAPI do JudAI (Milestone 4)
================================================================================
Alvo de Verificação: `src.api.main:app`
Compatibilidade: Executável nativamente via `pytest tests/test_api.py -v`
                 E via `python -m unittest tests/test_api.py -v`

Cenários Cobertos:
1. GET /health -> HTTP 200, status "ok", headers JSON.
2. GET /models/status -> HTTP 200, status "ready", métricas de ambos os modelos (TF-IDF+MLP e BERTimbau+mT0).
3. GET / -> HTTP 200, Content-Type text/html, títulos das 3 visões e chips de exemplo no DOM.
4. POST /search/tfidf (consulta canônica) -> HTTP 200, modelo tfidf_mlp, cc2002:art5 no Top-1, citação e texto do Art. 5º, score e execution_time_ms.
5. POST /search/bm25 (consulta canônica) -> HTTP 200, modelo bm25, paridade com o clássico, cc2002:art5 no Top-1.
6. POST /search/bert (consulta canônica in-domain) -> HTTP 200, modelo bert_mt0, cc2002:art5 no Top-1, resposta_gerada não vazia, abstenção=False.
7. POST /search/bert (consulta fora de escopo - culinária) -> HTTP 200, abstenção=True, frase canônica de recusa.
8. POST /search/compare (consulta canônica) -> HTTP 200, chaves query, classico e moderno, validação de ambos os resultados.
9. Casos de borda: query vazia/espaços (HTTP 400 ou 422).
10. Casos de borda: payload inválido, tipos incorretos ou ausentes (HTTP 422).
11. Casos de borda: top_k customizado (top_k=1 e top_k=5).
12. CORS: cabeçalhos Access-Control-Allow-Origin na resposta.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para importação de src.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api.main import app


class TestJudAIAPI(unittest.TestCase):
    """Suíte unificada de testes de integração da API FastAPI do JudAI."""

    CANONICAL_QUERY = "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"
    OUT_OF_SCOPE_QUERY = "Receita de bolo de fubá com goiabada"
    CANONICAL_REFUSAL = "Não encontrei informação suficiente no Código Civil para responder a essa pergunta."

    @classmethod
    def setUpClass(cls):
        """Inicializa o TestClient com suporte a lifespan context manager."""
        # Usando context manager do TestClient para ativar startup/lifespan
        cls._client_context = TestClient(app)
        cls.client = cls._client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        """Encerra o TestClient e libera recursos."""
        cls._client_context.__exit__(None, None, None)

    # =========================================================================
    # 1. Endpoint /health
    # =========================================================================

    def test_01_get_health(self):
        """Valida que GET /health retorna HTTP 200, status 'ok' e Content-Type JSON."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.headers.get("content-type", ""))

        data = response.json()
        self.assertEqual(data.get("status"), "ok")

    # =========================================================================
    # 2. Endpoint /models/status
    # =========================================================================

    def test_02_get_models_status(self):
        """Valida que GET /models/status retorna HTTP 200 com status e métricas de ambos os modelos."""
        response = self.client.get("/models/status")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.headers.get("content-type", ""))

        data = response.json()
        self.assertIn("classico", data)
        self.assertIn("moderno", data)

        # Validação do Modelo Clássico (TF-IDF + MLP)
        classico = data["classico"]
        self.assertIn(classico.get("status"), ("ready", "loaded", "ok"))
        self.assertGreaterEqual(classico.get("artigos_indexados", 0), 2000)
        if "val_acc" in classico and classico["val_acc"] is not None:
            self.assertGreater(classico["val_acc"], 0.70)

        # Validação do Modelo Moderno (BERTimbau + ChromaDB + mT0)
        moderno = data["moderno"]
        self.assertIn(moderno.get("status"), ("ready", "loaded", "ok"))
        self.assertGreaterEqual(moderno.get("artigos_indexados", 0), 2000)
        self.assertAlmostEqual(moderno.get("limiar", 0.70), 0.70, places=2)

    # =========================================================================
    # 3. Endpoint GET / (Interface Web)
    # =========================================================================

    def test_03_get_root_web_interface(self):
        """Valida que GET / serve HTML5 responsivo com as 3 visões e chips de exemplo."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))

        html = response.text
        self.assertTrue(len(html) > 500, "O HTML retornado é muito curto ou está vazio.")
        self.assertIn("JudAI", html)

        # Verificação da presença dos títulos das 3 visões navegáveis
        self.assertTrue(
            "Modelo Moderno" in html or "BERTimbau" in html,
            "Título da visão Modelo Moderno ausente no HTML."
        )
        self.assertTrue(
            "Modelo Clássico" in html or "TF-IDF" in html,
            "Título da visão Modelo Clássico ausente no HTML."
        )
        self.assertTrue(
            "Comparação" in html or "Lado a Lado" in html,
            "Título da visão Comparação Lado a Lado ausente no HTML."
        )

        # Verificação da presença dos chips de perguntas de exemplo
        self.assertTrue(
            "Com quantos anos a pessoa passa a ser plenamente capaz" in html or "Maioridade Civil" in html,
            "Chip da consulta canônica (Art. 5º) ausente no HTML."
        )
        self.assertTrue(
            "Receita de bolo" in html or "bolo de fubá" in html or "Abstenção" in html,
            "Chip de teste de abstenção ausente no HTML."
        )

    # =========================================================================
    # 4. POST /search/tfidf (Consulta Canônica)
    # =========================================================================

    def test_04_post_search_tfidf_canonical(self):
        """Valida busca clássica TF-IDF+MLP com consulta canônica sobre capacidade civil."""
        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}
        response = self.client.post("/search/tfidf", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data.get("model"), "tfidf_mlp")
        self.assertEqual(data.get("query"), self.CANONICAL_QUERY)
        self.assertIsInstance(data.get("results"), list)
        self.assertEqual(len(data["results"]), 3)

        # Top-1 deve ser rigorosamente o Artigo 5º do Código Civil
        top1 = data["results"][0]
        self.assertEqual(top1.get("artigo_id"), "cc2002:art5")
        self.assertIn("Código Civil", top1.get("citacao", ""))
        self.assertIn("5", top1.get("citacao", ""))
        self.assertTrue(
            "menoridade cessa" in top1.get("texto", "").lower() or
            "dezoito anos" in top1.get("texto", "").lower(),
            f"Texto do Art. 5º não condizente: {top1.get('texto')}"
        )
        self.assertGreater(top1.get("score", 0.0), 0.0)
        self.assertLessEqual(top1.get("score", 0.0), 1.0)
        self.assertGreater(data.get("execution_time_ms", 0.0), 0.0)

    # =========================================================================
    # 5. POST /search/bm25 (Consulta Canônica e Paridade)
    # =========================================================================

    def test_05_post_search_bm25_canonical(self):
        """Valida que o alias BM25 executa a busca clássica com paridade e model='bm25'."""
        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}
        response = self.client.post("/search/bm25", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data.get("model"), "bm25")
        self.assertEqual(data.get("query"), self.CANONICAL_QUERY)
        self.assertIsInstance(data.get("results"), list)
        self.assertGreater(len(data["results"]), 0)

        # Top-1 mantém paridade rigorosa com o clássico (Art. 5º)
        top1 = data["results"][0]
        self.assertEqual(top1.get("artigo_id"), "cc2002:art5")
        self.assertGreater(data.get("execution_time_ms", 0.0), 0.0)

    # =========================================================================
    # 6. POST /search/bert (Consulta Canônica In-Domain)
    # =========================================================================

    def test_06_post_search_bert_canonical_in_domain(self):
        """Valida busca semântica BERT+mT0 in-domain: Art. 5º no Top-1, resposta gerada e abstenção=False."""
        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}
        response = self.client.post("/search/bert", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data.get("model"), "bert_mt0")
        self.assertEqual(data.get("query"), self.CANONICAL_QUERY)

        # Verifica abstenção False (suporta com e sem acento)
        abstencao = data.get("abstenção", data.get("abstencao"))
        self.assertFalse(abstencao, "Modelo moderno não deveria abster-se na consulta canônica.")

        # Resposta gerada não vazia e informativa
        resposta = data.get("resposta_gerada", "")
        self.assertTrue(len(resposta.strip()) > 10, f"Resposta gerada vazia ou truncada: '{resposta}'")
        self.assertNotIn(self.CANONICAL_REFUSAL, resposta)

        # Top-1 no ChromaDB deve ser o Artigo 5º com similaridade >= 0.70
        results = data.get("results", [])
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].get("artigo_id"), "cc2002:art5")
        self.assertGreaterEqual(results[0].get("similarity_score", 0.0), 0.70)
        self.assertGreater(data.get("execution_time_ms", 0.0), 0.0)

    # =========================================================================
    # 7. POST /search/bert (Consulta Fora de Escopo - Abstenção)
    # =========================================================================

    def test_07_post_search_bert_out_of_scope_abstention(self):
        """Valida que pergunta fora do escopo jurídico aciona abstenção=True e recusa canônica."""
        payload = {"query": self.OUT_OF_SCOPE_QUERY, "top_k": 3}
        response = self.client.post("/search/bert", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data.get("model"), "bert_mt0")

        # Verifica abstenção True
        abstencao = data.get("abstenção", data.get("abstencao"))
        self.assertTrue(abstencao, "Modelo moderno deveria ter se abstido para pergunta culinária.")

        # Valida frase canônica de recusa exata
        self.assertEqual(data.get("resposta_gerada"), self.CANONICAL_REFUSAL)

        # Caso retorne artigos do ChromaDB, a similaridade deve ser inferior ao limiar 0.70
        results = data.get("results", [])
        if results:
            self.assertLess(results[0].get("similarity_score", 0.0), 0.70)
        self.assertGreater(data.get("execution_time_ms", 0.0), 0.0)

    # =========================================================================
    # 8. POST /search/compare (Consulta Canônica Lado a Lado)
    # =========================================================================

    def test_08_post_search_compare_canonical(self):
        """Valida comparação lado a lado contendo resultados válidos de ambos os modelos."""
        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}
        response = self.client.post("/search/compare", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("query", data)
        self.assertIn("classico", data)
        self.assertIn("moderno", data)
        self.assertEqual(data["query"], self.CANONICAL_QUERY)

        # Valida bloco clássico
        classico = data["classico"]
        self.assertIn(classico.get("model"), ("tfidf_mlp", "bm25"))
        self.assertGreater(len(classico.get("results", [])), 0)
        self.assertEqual(classico["results"][0].get("artigo_id"), "cc2002:art5")
        self.assertGreater(classico.get("execution_time_ms", 0.0), 0.0)

        # Valida bloco moderno
        moderno = data["moderno"]
        self.assertEqual(moderno.get("model"), "bert_mt0")
        abstencao = moderno.get("abstenção", moderno.get("abstencao"))
        self.assertFalse(abstencao)
        self.assertTrue(len(moderno.get("resposta_gerada", "")) > 10)
        self.assertGreater(len(moderno.get("results", [])), 0)
        self.assertEqual(moderno["results"][0].get("artigo_id"), "cc2002:art5")
        self.assertGreater(moderno.get("execution_time_ms", 0.0), 0.0)

    # =========================================================================
    # 9. Casos de Borda: Queries Vazias e Espaços
    # =========================================================================

    def test_09_edge_case_empty_and_whitespace_query(self):
        """Valida rejeição elegante (HTTP 400 ou 422) para query vazia ou whitespace."""
        for invalid_query in ("", "   ", "\t\n"):
            payload = {"query": invalid_query, "top_k": 3}
            # Teste no endpoint clássico
            res_tfidf = self.client.post("/search/tfidf", json=payload)
            self.assertIn(
                res_tfidf.status_code,
                (400, 422),
                f"Status code inesperado para query vazia em /search/tfidf: {res_tfidf.status_code}"
            )

            # Teste no endpoint moderno
            res_bert = self.client.post("/search/bert", json=payload)
            self.assertIn(
                res_bert.status_code,
                (400, 422),
                f"Status code inesperado para query vazia em /search/bert: {res_bert.status_code}"
            )

    # =========================================================================
    # 10. Casos de Borda: Payloads Inválidos e Tipos Incorretos
    # =========================================================================

    def test_10_edge_case_invalid_payload_schema(self):
        """Valida retorno HTTP 422 Unprocessable Entity para requisições malformadas."""
        # Payload sem campo obrigatório 'query'
        res1 = self.client.post("/search/tfidf", json={"top_k": 3})
        self.assertEqual(res1.status_code, 422)

        # Payload com tipo inválido para 'query' (número inteiro)
        res2 = self.client.post("/search/tfidf", json={"query": 12345, "top_k": 3})
        self.assertEqual(res2.status_code, 422)

        # Payload com tipo inválido para 'top_k' (string)
        res3 = self.client.post("/search/tfidf", json={"query": "Artigo 5", "top_k": "cinco"})
        self.assertEqual(res3.status_code, 422)

    # =========================================================================
    # 11. Casos de Borda: top_k Customizado (1 e 5)
    # =========================================================================

    def test_11_edge_case_custom_top_k(self):
        """Valida retorno do número exato de artigos conforme top_k solicitado."""
        # Teste com top_k = 1
        res_k1 = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": 1})
        self.assertEqual(res_k1.status_code, 200)
        self.assertEqual(len(res_k1.json().get("results", [])), 1)

        # Teste com top_k = 5
        res_k5 = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": 5})
        self.assertEqual(res_k5.status_code, 200)
        self.assertEqual(len(res_k5.json().get("results", [])), 5)

    # =========================================================================
    # 12. Middleware CORS
    # =========================================================================

    def test_12_cors_headers(self):
        """Valida que cabeçalhos CORS permitem integração externa."""
        headers = {"Origin": "http://localhost:3000"}
        response = self.client.get("/health", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.headers.get("access-control-allow-origin"), ("*", "http://localhost:3000"))



if __name__ == "__main__":
    unittest.main(verbosity=2)
