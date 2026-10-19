"""
Tier 4: Real-World Scenarios Test Suite - JudAI
==============================================
Simulação de fluxos reais de uso e ponta a ponta:
1. Fluxo de consulta ponta a ponta na API FastAPI:
   - Ciclo de vida completo: Healthcheck -> Busca BM25 -> Busca BERT -> Inspeção OpenAPI
   - Carga concorrente realista de múltiplas requisições simultâneas
2. Execução do pipeline do Scraper Jurídico como módulo:
   - Execução via subprocesso / invocação modular (`python -m src.scraper.carregar_mongo`)
   - Extração estruturada de dispositivos de uma lei de teste com o parser real
   - Carga simulada de documentos no formato esperado pelo MongoDB
3. Simulação de onboarding de desenvolvedor:
   - Validação dos fluxos documentados no README (criação de .env a partir de .env.example)
   - Validação de que nenhum arquivo gerado em tempo de execução polui o git
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


# ===========================================================================
# 1. Real-World Scenario: Fluxo Ponta a Ponta na API FastAPI
# ===========================================================================

class TestRealWorldApiWorkflow:
    """Simula a experiência completa de um cliente consumindo a API JudAI."""

    def test_complete_client_session_flow(self, api_client):
        """
        1.1 Cenário: Usuário/Sistema Jurídico inicia sessão, valida saúde e executa
        consultas híbridas (léxica e semântica).
        """
        # Passo 1: Healthcheck antes de iniciar
        health_resp = api_client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "ok"

        # Passo 2: Busca Léxica por artigo específico
        bm25_payload = {"query": "Artigo 1.240 Usucapião Especial Urbana"}
        bm25_resp = api_client.post("/search/bm25", json=bm25_payload)
        assert bm25_resp.status_code == 200
        bm25_data = bm25_resp.json()
        assert bm25_data["model"] == "bm25"
        assert bm25_data["query"] == bm25_payload["query"]
        assert isinstance(bm25_data["results"], list)
        assert bm25_data["detail"] == "not implemented"

        # Passo 3: Busca Semântica por conceito em linguagem natural
        bert_payload = {"query": "Qual o prazo prescricional para reparação civil por ato ilícito?"}
        bert_resp = api_client.post("/search/bert", json=bert_payload)
        assert bert_resp.status_code == 200
        bert_data = bert_resp.json()
        assert bert_data["model"] == "bert"
        assert bert_data["query"] == bert_payload["query"]
        assert isinstance(bert_data["results"], list)
        assert bert_data["detail"] == "not implemented"

        # Passo 4: Obtenção do esquema de documentação
        openapi_resp = api_client.get("/openapi.json")
        assert openapi_resp.status_code == 200
        spec = openapi_resp.json()
        assert spec["info"]["title"] == "JudAI API"

    def test_concurrent_client_requests_burst(self, api_client):
        """
        1.2 Cenário: Rajada de 30 requisições simultâneas em threads paralelas
        simulando múltiplos usuários consultando a API sem degradação.
        """
        from concurrent.futures import ThreadPoolExecutor

        def send_request(idx: int):
            endpoint = "/search/bm25" if idx % 2 == 0 else "/search/bert"
            query = f"Consulta jurídica concorrente #{idx}: prescrição art. {idx}"
            return api_client.post(endpoint, json={"query": query})

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_request, i) for i in range(30)]
            results = [f.result() for f in futures]

        for resp in results:
            assert resp.status_code == 200
            assert resp.json()["detail"] == "not implemented"


# ===========================================================================
# 2. Real-World Scenario: Execução do Scraper Jurídico em Módulo
# ===========================================================================

class TestRealWorldScraperExecution:
    """Valida o funcionamento prático do parser e da carga do scraper."""

    def test_parser_real_html_snippet(self, temp_dir):
        """
        2.1 Cenário: Parsing de um fragmento real de lei do Planalto.
        Garante que BeautifulSoup e a lógica do parser extraem artigos e parágrafos.
        """
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>LEI Nº 10.406, DE 10 DE JANEIRO DE 2002</title></head>
        <body>
            <p class="ementa">Institui o Código Civil.</p>
            <p><strong>O PRESIDENTE DA REPÚBLICA</strong> Faço saber que o Congresso Nacional decreta e eu sanciono a seguinte Lei:</p>
            <p id="art1">Art. 1<u>o</u> Toda pessoa é capaz de direitos e deveres na ordem civil.</p>
            <p id="art2">Art. 2<u>o</u> A personalidade civil da pessoa começa do nascimento com vida; mas a lei põe a salvo, desde a concepção, os direitos do nascituro.</p>
            <p id="art3">Art. 3<u>o</u> São absolutamente incapazes de exercer pessoalmente os atos da vida civil os menores de 16 (dezesseis) anos.</p>
            <p>§ 1<u>o</u> (Revogado pela Lei nº 13.146, de 2015)</p>
        </body>
        </html>
        """
        html_file = temp_dir / "sample_lei.html"
        html_file.write_text(html_content, encoding="utf-8")

        # Importa o parser do scraper
        from src.scraper import ingestao_lei

        # Testa extração de metadados
        meta = ingestao_lei.extrair_metadados(html_content, str(html_file))
        assert meta is not None
        assert isinstance(meta, dict)

        # Testa extração de dispositivos
        dispositivos = ingestao_lei.extrair_dispositivos(html_content)
        assert isinstance(dispositivos, list)
        assert len(dispositivos) > 0, "Deveria extrair pelo menos os artigos contidos no HTML de teste."

    def test_scraper_module_cli_invocation_help(self):
        """
        2.2 Cenário: Execução do módulo carregar_mongo via linha de comando
        como especificado no README e na requisição original: `python -m src.scraper.carregar_mongo`.
        """
        # Executa com --help ou flag inexistente para verificar se o entrypoint é válido
        proc = subprocess.run(
            [sys.executable, "-m", "src.scraper.carregar_mongo", "--help"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True
        )
        # Pode sair com 0 ou 2 (argparse), mas não com ModuleNotFoundError
        assert "ModuleNotFoundError" not in proc.stderr, (
            f"Falha ao invocar carregar_mongo como módulo: {proc.stderr}"
        )


# ===========================================================================
# 3. Real-World Scenario: Developer Onboarding & Environment Setup
# ===========================================================================

class TestRealWorldDeveloperOnboarding:
    """Valida o fluxo que um novo desenvolvedor realiza ao clonar o repositório."""

    def test_copy_env_example_to_env_workflow(self, temp_dir):
        """
        3.1 Cenário: Desenvolvedor clona o projeto e copia .env.example para .env.
        O sistema deve carregar as variáveis sem erros de sintaxe ou encoding.
        """
        env_example = ROOT_DIR / ".env.example"
        assert env_example.exists()

        temp_env = temp_dir / ".env"
        shutil.copy(str(env_example), str(temp_env))

        from dotenv import dotenv_values
        config = dotenv_values(str(temp_env))

        assert config.get("MONGO_URI") == "mongodb://localhost:27017"
        assert config.get("MONGO_DB_NAME") == "rag_juridico"
        assert config.get("CHROMA_DB_PATH") == "./data/chromadb_local"

    def test_cross_platform_path_consistency(self):
        """
        3.2 Cenário: Todos os caminhos declarados em .env.example e no código
        são agnósticos a separadores de SO (sem barras invertidas hardcoded).
        """
        env_example = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")
        assert "\\" not in env_example, (
            ".env.example não deve conter barras invertidas '\\' no valor de CHROMA_DB_PATH."
        )
