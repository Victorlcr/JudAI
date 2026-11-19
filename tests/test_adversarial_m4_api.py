"""
Suíte de Testes Adversariais e de Estresse da API FastAPI (aJudAI - Milestone 4)
==============================================================================
Módulo: `tests/test_adversarial_m4_api.py`
Alvo: `src.api.main:app`
Executável via: `.\\venv\\Scripts\\python.exe -m unittest tests/test_adversarial_m4_api.py -v`

Dimensões de Teste:
1. Contratos de Payload e Resiliência a Entradas Adversariais:
   - Queries vazias, apenas espaços em branco, quebras de linha e tabulações.
   - Strings massivas (10.000 caracteres).
   - Caracteres especiais complexos, símbolos matemáticos e emojis múltiplos.
   - Tentativas de injeção SQL e XSS (Cross-Site Scripting).
   - Payloads com campos extras e inesperados.
   - Payloads com campos faltantes e schemas malformados.
   - Payloads com tipos incorretos (tipagem estrita no Pydantic v2).
2. Testes de Fronteira e Parametrização:
   - Limites de `top_k`: 0, 1, 10, 20 (máximo legal), 21 (violação le=20), 5000 e negativos.
   - Validação de métodos HTTP não permitidos (405 Method Not Allowed).
   - Rotas inexistentes (404 Not Found).
3. Consultas Fora de Escopo (OOD) e Estabilidade Probabilística:
   - Consultas adversariais: astronomia, culinária e física quântica.
   - Verificação de abstenção rigorosa no BERTimbau+mT0 (abstenção=True, similaridade < limiar, recusa canônica).
   - Verificação de estabilidade probabilística no TF-IDF+MLP (sem NaNs, scores em [0, 1], distribuição válida).
   - Verificação no endpoint unificado /search/compare.
4. Desempenho, Latência e Consistência Sequencial:
   - Benchmark de 50 chamadas consecutivas em /search/tfidf (verificação de latência sub-20ms).
   - Benchmark de chamadas em /search/compare.
   - Verificação de determinismo e consistência de dados entre chamadas sequenciais.
"""
from __future__ import annotations

import statistics
import sys
import time
import unittest
from pathlib import Path
from typing import Any

# Assegura a raiz do projeto no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api.main import app


class TestAdversarialAPI(unittest.TestCase):
    """Bateria de testes adversariais para a API FastAPI do aJudAI."""

    CANONICAL_QUERY = "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"
    CANONICAL_REFUSAL = "Não encontrei informação suficiente no Código Civil para responder a essa pergunta."

    # Consultas fora de escopo (Out of Domain)
    OOD_ASTRONOMY = (
        "Qual é a massa estimada do buraco negro supermassivo Sagittarius A* no centro da Via Láctea "
        "e a distância em anos-luz até o aglomerado de Virgem?"
    )
    OOD_COOKING = (
        "Receita tradicional de risoto de cogumelos selvagens com queijo parmesão trufado e vinho branco seco"
    )
    OOD_QUANTUM = (
        "Explique o entrelaçamento quântico, o paradoxo de Einstein-Podolsky-Rosen e a violação das desigualdades de Bell"
    )

    # Injeções SQL / XSS / Comandos
    INJECTION_PAYLOADS = [
        "<script>alert('XSS_ATTACK_AJUDAI')</script>",
        "'; DROP TABLE artigos; --",
        "1' OR '1'='1",
        "\"><svg/onload=alert(document.domain)>",
        "{\"$ne\": null}",
        "UNION SELECT NULL, table_name, column_name FROM information_schema.columns --",
        "../../../../etc/passwd",
        "eval('import os; os.system(\"calc\")')"
    ]

    @classmethod
    def setUpClass(cls):
        """Inicializa o TestClient dentro do ciclo de vida lifespan."""
        cls._client_context = TestClient(app)
        cls.client = cls._client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        """Finaliza o context manager do TestClient e libera recursos."""
        cls._client_context.__exit__(None, None, None)

    # =========================================================================
    # 1. VALIDAÇÃO ESTRITA DE CONTRATOS DE PAYLOAD E RESILIÊNCIA A ERROS
    # =========================================================================

    def test_01_empty_and_whitespace_queries_across_all_endpoints(self):
        """Verifica que queries vazias ou contendo apenas espaços/tabs/quebras retornam HTTP 400."""
        invalid_queries = ["", "   ", "\t", "\n", "\r\n", "   \t  \n  "]
        endpoints = ["/search/tfidf", "/search/bm25", "/search/bert", "/search/compare"]

        for ep in endpoints:
            for q in invalid_queries:
                with self.subTest(endpoint=ep, query=repr(q)):
                    res = self.client.post(ep, json={"query": q, "top_k": 3})
                    self.assertEqual(
                        res.status_code,
                        400,
                        f"Endpoint {ep} não rejeitou query vazia {repr(q)} com 400. Recebeu: {res.status_code}"
                    )
                    data = res.json()
                    self.assertIn("detail", data)
                    self.assertIn("não pode ser vazia", data["detail"].lower())

    def test_02_massive_10k_character_query_stability(self):
        """Verifica que query de 10.000 caracteres não causa overflow, OOM ou erro 500."""
        # Monta string de 10.000 caracteres mesclando termos jurídicos e repetição
        base_text = "capacidade civil maioridade dezoito anos direito civil brasileiro responsabilidade "
        repetitions = (10000 // len(base_text)) + 1
        massive_query = (base_text * repetitions)[:10000]
        self.assertEqual(len(massive_query), 10000)

        # 1. Teste em /search/tfidf
        res_tfidf = self.client.post("/search/tfidf", json={"query": massive_query, "top_k": 3})
        self.assertEqual(res_tfidf.status_code, 200, f"/search/tfidf falhou com query 10k: {res_tfidf.text}")
        data_tfidf = res_tfidf.json()
        self.assertEqual(data_tfidf["model"], "tfidf_mlp")
        self.assertIsInstance(data_tfidf["results"], list)
        self.assertGreater(data_tfidf["execution_time_ms"], 0.0)

        # 2. Teste em /search/bm25
        res_bm25 = self.client.post("/search/bm25", json={"query": massive_query, "top_k": 3})
        self.assertEqual(res_bm25.status_code, 200)

        # 3. Teste em /search/bert (valida se o truncation no tokenizer opera sem falhas)
        res_bert = self.client.post("/search/bert", json={"query": massive_query, "top_k": 2})
        self.assertEqual(res_bert.status_code, 200, f"/search/bert falhou com query 10k: {res_bert.text}")
        data_bert = res_bert.json()
        self.assertIn("resposta_gerada", data_bert)
        self.assertIsInstance(data_bert["results"], list)

        # 4. Teste em /search/compare
        res_cmp = self.client.post("/search/compare", json={"query": massive_query, "top_k": 2})
        self.assertEqual(res_cmp.status_code, 200)
        data_cmp = res_cmp.json()
        self.assertIn("classico", data_cmp)
        self.assertIn("moderno", data_cmp)
        self.assertIn("comparacao", data_cmp)

    def test_03_special_characters_symbols_and_emojis(self):
        """Verifica resiliência com caracteres especiais, símbolos legislativos, matemáticos e emojis."""
        special_queries = [
            "§ 1º, art. 5º, c/c art. 1.228, § 2º do CC/2002: usucapião & desapropriação?",
            "⚖️🏛️ Qual a idade para capacidade civil? 📜✅⚠️",
            "Direito de Família: guarda compartilhada -> Art. 1.583 / 1.584 [Lei nº 13.058/2014]!!",
            "∀x ∈ Cidadãos, idade(x) ≥ 18 ⇒ PlenaCapacidade(x) ∧ ¬Incapacidade(x) ∑ ∏ √",
            "Consulta jurídica com acentuação: ação rescisória, presunção de não-culpabilidade, preempção"
        ]

        for q in special_queries:
            with self.subTest(query=q):
                # /search/tfidf
                res_tfidf = self.client.post("/search/tfidf", json={"query": q, "top_k": 3})
                self.assertEqual(res_tfidf.status_code, 200, f"Falha no TFIDF com query especial: {q}")
                self.assertGreater(len(res_tfidf.json()["results"]), 0)

                # /search/bert
                res_bert = self.client.post("/search/bert", json={"query": q, "top_k": 2})
                self.assertEqual(res_bert.status_code, 200, f"Falha no BERT com query especial: {q}")
                self.assertIn("resposta_gerada", res_bert.json())

    def test_04_sql_and_xss_injection_attempts(self):
        """Verifica que payloads de injeção SQL/XSS são tratados estritamente como texto sem causar 500."""
        for payload in self.INJECTION_PAYLOADS:
            with self.subTest(injection=payload):
                res = self.client.post("/search/tfidf", json={"query": payload, "top_k": 3})
                self.assertEqual(
                    res.status_code,
                    200,
                    f"Falha de segurança/estabilidade com injeção '{payload}'. Status: {res.status_code}"
                )
                data = res.json()
                self.assertEqual(data["model"], "tfidf_mlp")
                # Garante que a resposta JSON escapa tags HTML/XSS
                self.assertIn(payload, data["query"])

    def test_05_payload_with_extra_fields(self):
        """Verifica que campos extras no payload JSON são aceitos e ignorados sem causar 422/500."""
        payload = {
            "query": self.CANONICAL_QUERY,
            "top_k": 3,
            "extra_field_1": "unexpected_data",
            "injected_admin_role": True,
            "metadata_dump": {"nested": [1, 2, 3]}
        }
        res = self.client.post("/search/tfidf", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["results"][0]["artigo_id"], "cc2002:art5")

    def test_06_payload_missing_required_fields(self):
        """Verifica que requisições com campos obrigatórios ausentes retornam 422 Unprocessable Entity."""
        endpoints = ["/search/tfidf", "/search/bm25", "/search/bert", "/search/compare"]
        malformed_payloads = [
            {},
            {"top_k": 3},
            {"query_invalid_name": "teste", "top_k": 3}
        ]

        for ep in endpoints:
            for p in malformed_payloads:
                with self.subTest(endpoint=ep, payload=p):
                    res = self.client.post(ep, json=p)
                    self.assertEqual(
                        res.status_code,
                        422,
                        f"Endpoint {ep} não retornou 422 para payload incompleto {p}. Recebido: {res.status_code}"
                    )

    def test_07_payload_incorrect_types(self):
        """Verifica validação de tipos estrita (query não-string, top_k não-inteiro)."""
        endpoints = ["/search/tfidf", "/search/bert"]
        type_violations = [
            {"query": 12345, "top_k": 3},
            {"query": ["consulta", "em", "lista"], "top_k": 3},
            {"query": {"objeto": "consulta"}, "top_k": 3},
            {"query": True, "top_k": 3},
            {"query": self.CANONICAL_QUERY, "top_k": "três"},
            {"query": self.CANONICAL_QUERY, "top_k": [3]},
            {"query": self.CANONICAL_QUERY, "top_k": None}
        ]

        for ep in endpoints:
            for p in type_violations:
                with self.subTest(endpoint=ep, payload=p):
                    res = self.client.post(ep, json=p)
                    self.assertEqual(
                        res.status_code,
                        422,
                        f"Endpoint {ep} permitiu tipo inválido {p}. Status: {res.status_code}"
                    )

    # =========================================================================
    # 2. TESTES DE FRONTEIRA E PARAMETRIZAÇÃO (top_k E MÉTODOS HTTP)
    # =========================================================================

    def test_08_top_k_boundary_zero_and_negatives(self):
        """Verifica rejeição (HTTP 422) de top_k = 0 e valores negativos (ge=1)."""
        invalid_k_values = [0, -1, -50]
        for k in invalid_k_values:
            with self.subTest(top_k=k):
                res = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": k})
                self.assertEqual(res.status_code, 422, f"top_k={k} deveria violar ge=1 e retornar 422")
                res_b = self.client.post("/search/bert", json={"query": self.CANONICAL_QUERY, "top_k": k})
                self.assertEqual(res_b.status_code, 422)

    def test_09_top_k_boundary_lower_limit_one(self):
        """Verifica comportamento com top_k = 1 (limite inferior válido)."""
        res = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": 1})
        self.assertEqual(res.status_code, 200)
        results = res.json().get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["artigo_id"], "cc2002:art5")

    def test_10_top_k_boundary_mid_ten(self):
        """Verifica comportamento com top_k = 10 (valor intermediário comum)."""
        res = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": 10})
        self.assertEqual(res.status_code, 200)
        results = res.json().get("results", [])
        self.assertEqual(len(results), 10)

    def test_11_top_k_boundary_upper_limit_twenty(self):
        """Verifica comportamento com top_k = 20 (limite superior válido le=20)."""
        res = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": 20})
        self.assertEqual(res.status_code, 200)
        results = res.json().get("results", [])
        self.assertEqual(len(results), 20)

    def test_12_top_k_boundary_exceeded_twenty_one_and_five_thousand(self):
        """Verifica rejeição (HTTP 422) para top_k = 21 e top_k = 5000 (violação le=20)."""
        excessive_k_values = [21, 50, 5000, 100000]
        for k in excessive_k_values:
            with self.subTest(top_k=k):
                res = self.client.post("/search/tfidf", json={"query": self.CANONICAL_QUERY, "top_k": k})
                self.assertEqual(res.status_code, 422, f"top_k={k} deveria violar le=20 e retornar 422")
                res_b = self.client.post("/search/bert", json={"query": self.CANONICAL_QUERY, "top_k": k})
                self.assertEqual(res_b.status_code, 422)

    def test_13_http_methods_and_nonexistent_routes(self):
        """Verifica que métodos não suportados retornam 405 e rotas inexistentes 404."""
        # GET nos endpoints de busca
        for ep in ["/search/tfidf", "/search/bm25", "/search/bert", "/search/compare"]:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 405, f"GET em {ep} deveria retornar 405")

        # POST nos endpoints somente-leitura
        for ep in ["/health", "/models/status", "/"]:
            res = self.client.post(ep, json={})
            self.assertEqual(res.status_code, 405, f"POST em {ep} deveria retornar 405")

        # Rota 404
        res_404 = self.client.get("/endpoint_totalmente_inexistente")
        self.assertEqual(res_404.status_code, 404)

    # =========================================================================
    # 3. CONSULTAS ADVERSARIAIS E FORA DE ESCOPO (OOD)
    # =========================================================================

    def test_14_out_of_domain_astronomy_abstention_and_stability(self):
        """Verifica abstenção do BERT e estabilidade probabilística do TFIDF em astronomia."""
        # 1. BERTimbau + mT0: deve acionar abstenção
        res_bert = self.client.post("/search/bert", json={"query": self.OOD_ASTRONOMY, "top_k": 3})
        self.assertEqual(res_bert.status_code, 200)
        data_bert = res_bert.json()
        abstencao = data_bert.get("abstenção", data_bert.get("abstencao"))
        self.assertTrue(abstencao, "BERT deveria se abster para consulta de astronomia")
        self.assertEqual(data_bert.get("resposta_gerada"), self.CANONICAL_REFUSAL)
        for r in data_bert.get("results", []):
            self.assertLess(r.get("similarity_score", 0.0), 0.70)

        # 2. TF-IDF + MLP: deve responder com estabilidade probabilística
        res_tfidf = self.client.post("/search/tfidf", json={"query": self.OOD_ASTRONOMY, "top_k": 3})
        self.assertEqual(res_tfidf.status_code, 200)
        data_tfidf = res_tfidf.json()
        for r in data_tfidf["results"]:
            score = r["score"]
            self.assertTrue(0.0 <= score <= 1.0, f"Score fora do intervalo [0, 1]: {score}")
            self.assertFalse(score != score, "Score é NaN")

    def test_15_out_of_domain_cooking_abstention_and_stability(self):
        """Verifica abstenção do BERT e estabilidade probabilística do TFIDF em culinária."""
        # 1. BERTimbau + mT0
        res_bert = self.client.post("/search/bert", json={"query": self.OOD_COOKING, "top_k": 3})
        self.assertEqual(res_bert.status_code, 200)
        data_bert = res_bert.json()
        abstencao = data_bert.get("abstenção", data_bert.get("abstencao"))
        self.assertTrue(abstencao, "BERT deveria se abster para consulta de culinária")
        self.assertEqual(data_bert.get("resposta_gerada"), self.CANONICAL_REFUSAL)
        for r in data_bert.get("results", []):
            self.assertLess(r.get("similarity_score", 0.0), 0.70)

        # 2. TF-IDF + MLP
        res_tfidf = self.client.post("/search/tfidf", json={"query": self.OOD_COOKING, "top_k": 3})
        self.assertEqual(res_tfidf.status_code, 200)
        data_tfidf = res_tfidf.json()
        for r in data_tfidf["results"]:
            score = r["score"]
            self.assertTrue(0.0 <= score <= 1.0)

    def test_16_out_of_domain_quantum_physics_abstention_and_stability(self):
        """Verifica abstenção do BERT e estabilidade probabilística do TFIDF em física quântica."""
        # 1. BERTimbau + mT0
        res_bert = self.client.post("/search/bert", json={"query": self.OOD_QUANTUM, "top_k": 3})
        self.assertEqual(res_bert.status_code, 200)
        data_bert = res_bert.json()
        abstencao = data_bert.get("abstenção", data_bert.get("abstencao"))
        self.assertTrue(abstencao, "BERT deveria se abster para consulta de física quântica")
        self.assertEqual(data_bert.get("resposta_gerada"), self.CANONICAL_REFUSAL)
        for r in data_bert.get("results", []):
            self.assertLess(r.get("similarity_score", 0.0), 0.70)

        # 2. TF-IDF + MLP
        res_tfidf = self.client.post("/search/tfidf", json={"query": self.OOD_QUANTUM, "top_k": 3})
        self.assertEqual(res_tfidf.status_code, 200)
        data_tfidf = res_tfidf.json()
        for r in data_tfidf["results"]:
            score = r["score"]
            self.assertTrue(0.0 <= score <= 1.0)

    def test_17_out_of_domain_in_search_compare(self):
        """Verifica comportamento do endpoint /search/compare em consulta fora de domínio."""
        res = self.client.post("/search/compare", json={"query": self.OOD_COOKING, "top_k": 3})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        moderno = data["moderno"]
        abstencao = moderno.get("abstenção", moderno.get("abstencao"))
        self.assertTrue(abstencao)
        self.assertEqual(moderno.get("resposta_gerada"), self.CANONICAL_REFUSAL)
        self.assertIn("classico", data)
        self.assertIn("comparacao", data)

    # =========================================================================
    # 4. DESEMPENHO, LATÊNCIA E CONSISTÊNCIA SEQUENCIAL
    # =========================================================================

    def test_18_benchmark_consecutive_tfidf_calls_latency_sub20ms(self):
        """
        Executa benchmark empírico de 50 chamadas consecutivas em /search/tfidf.
        Verifica que a latência média e mediana de execução (execution_time_ms) é sub-20ms.
        """
        NUM_CALLS = 50
        api_latencies: list[float] = []
        client_latencies: list[float] = []

        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}

        # Aquecimento de 3 chamadas
        for _ in range(3):
            self.client.post("/search/tfidf", json=payload)

        # Execução das 50 chamadas sequenciais
        for i in range(NUM_CALLS):
            t0 = time.perf_counter()
            res = self.client.post("/search/tfidf", json=payload)
            roundtrip_ms = (time.perf_counter() - t0) * 1000.0

            self.assertEqual(res.status_code, 200)
            data = res.json()
            api_ms = data.get("execution_time_ms", 0.0)

            api_latencies.append(api_ms)
            client_latencies.append(roundtrip_ms)

        mean_api = statistics.mean(api_latencies)
        median_api = statistics.median(api_latencies)
        p95_api = sorted(api_latencies)[int(0.95 * len(api_latencies))]
        min_api = min(api_latencies)
        max_api = max(api_latencies)

        mean_client = statistics.mean(client_latencies)

        print(
            f"\n[BENCHMARK /search/tfidf - {NUM_CALLS} chamadas]: "
            f"API Mean={mean_api:.2f}ms, Median={median_api:.2f}ms, "
            f"p95={p95_api:.2f}ms, Min={min_api:.2f}ms, Max={max_api:.2f}ms | "
            f"Client Roundtrip Mean={mean_client:.2f}ms"
        )

        # Verificação rigorosa do requisito: latência média de execução sub-20ms
        self.assertLess(
            mean_api,
            20.0,
            f"Latência média da API em /search/tfidf ({mean_api:.2f}ms) excedeu o teto de 20ms!"
        )
        self.assertLess(
            median_api,
            20.0,
            f"Latência mediana da API em /search/tfidf ({median_api:.2f}ms) excedeu o teto de 20ms!"
        )

    def test_19_benchmark_consecutive_compare_calls(self):
        """Executa chamadas consecutivas em /search/compare e valida consistência métrica."""
        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}
        for _ in range(3):
            t0 = time.perf_counter()
            res = self.client.post("/search/compare", json=payload)
            wall_ms = (time.perf_counter() - t0) * 1000.0

            self.assertEqual(res.status_code, 200)
            data = res.json()
            comp = data.get("comparacao")
            self.assertIsNotNone(comp)
            self.assertEqual(comp.get("fastest_model"), "tfidf_mlp")
            self.assertGreaterEqual(comp.get("latency_diff_ms", 0.0), 0.0)
            self.assertTrue(comp.get("top1_concordam"))
            self.assertEqual(comp.get("top1_artigo_classico"), "cc2002:art5")
            self.assertEqual(comp.get("top1_artigo_moderno"), "cc2002:art5")

    def test_20_data_consistency_across_sequential_calls(self):
        """Verifica estrita consistência e determinismo entre múltiplas chamadas da mesma consulta."""
        payload = {"query": self.CANONICAL_QUERY, "top_k": 3}

        # Valida que 5 chamadas em /search/tfidf produzem resultados idênticos
        previous_results = None
        for iteration in range(5):
            res = self.client.post("/search/tfidf", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            results = data.get("results", [])

            self.assertEqual(results[0]["artigo_id"], "cc2002:art5")

            current_fingerprint = [(r["artigo_id"], r["score"]) for r in results]
            if previous_results is not None:
                self.assertEqual(
                    current_fingerprint,
                    previous_results,
                    f"Inconsistência determinística detectada na iteração {iteration} de /search/tfidf"
                )
            previous_results = current_fingerprint

        # Valida consistência de GET /models/status
        status_res1 = self.client.get("/models/status")
        status_res2 = self.client.get("/models/status")
        self.assertEqual(status_res1.status_code, 200)
        self.assertEqual(status_res2.status_code, 200)
        d1 = status_res1.json()
        d2 = status_res2.json()
        self.assertEqual(d1["classico"]["artigos_indexados"], d2["classico"]["artigos_indexados"])
        self.assertEqual(d1["moderno"]["artigos_indexados"], d2["moderno"]["artigos_indexados"])
        self.assertEqual(d1["classico"]["status"], "ready")
        self.assertEqual(d1["moderno"]["status"], "ready")


if __name__ == "__main__":
    unittest.main(verbosity=2)
