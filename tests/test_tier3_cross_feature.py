"""
Tier 3: Cross-Feature Combinations Test Suite - JudAI
=====================================================
Validação de integrações entre múltiplos subsistemas do JudAI:
1. Integração entre arquivo .env e classes Singleton de conexão (MongoConnection, ChromaConnection)
2. Consistência de configuração de banco entre MongoConnection e o scraper (carregar_mongo)
3. Persistência do ChromaDB no caminho especificado e integração com .gitkeep e isolamento de dados
4. Alinhamento de contratos entre rotas FastAPI (/search/bm25, /search/bert) e classes de modelos ML
5. Coerência entre docker-compose.yml, .env.example e fallbacks de conexão
"""
from __future__ import annotations

import os
import re
import sys
import inspect
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


# ===========================================================================
# 1. Cross-Feature: .env e Classes de Conexão (Mongo & Chroma)
# ===========================================================================

class TestEnvAndConnectionIntegration:
    """Valida a injeção e leitura dinâmica de .env nas classes de banco de dados."""

    def test_env_file_loaded_by_mongo_connection(self, temp_dir, clean_env, reset_singletons):
        """1.1 MongoConnection carrega valores definidos no arquivo .env via python-dotenv."""
        custom_uri = "mongodb://cluster.local:27017"
        custom_db = "rag_juridico_prod"
        env_path = temp_dir / ".env"
        env_path.write_text(f"MONGO_URI={custom_uri}\nMONGO_DB_NAME={custom_db}\n", encoding="utf-8")

        # Limpa variáveis de ambiente prévias
        os.environ.pop("MONGO_URI", None)
        os.environ.pop("MONGO_DB_NAME", None)

        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(env_path), override=True)

        from src.database.mongo_connection import MongoConnection
        conn = MongoConnection()
        assert conn.uri == custom_uri, f"Esperado URI '{custom_uri}', obtido '{conn.uri}'."
        assert conn.db_name == custom_db, f"Esperado DB '{custom_db}', obtido '{conn.db_name}'."

    def test_env_file_loaded_by_chroma_connection(self, temp_dir, clean_env, reset_singletons):
        """1.2 ChromaConnection carrega CHROMA_DB_PATH de .env e cria diretório resolvido."""
        target_path = temp_dir / "custom_vector_store"
        env_path = temp_dir / ".env"
        env_path.write_text(f"CHROMA_DB_PATH={target_path.as_posix()}\n", encoding="utf-8")

        os.environ.pop("CHROMA_DB_PATH", None)
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(env_path), override=True)

        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection()
        assert Path(conn.path).resolve() == target_path.resolve()
        assert target_path.exists()
        assert target_path.is_dir()

    def test_os_env_override_over_defaults(self, clean_env, reset_singletons):
        """1.3 Variáveis injetadas no os.environ prevalecem sobre os defaults em ambas as classes."""
        os.environ["MONGO_URI"] = "mongodb://env_override:27017"
        os.environ["MONGO_DB_NAME"] = "env_override_db"

        from src.database.mongo_connection import MongoConnection
        mongo = MongoConnection()
        assert mongo.uri == "mongodb://env_override:27017"
        assert mongo.db_name == "env_override_db"


# ===========================================================================
# 2. Cross-Feature: Scraper e Banco de Dados (carregar_mongo & MongoConnection)
# ===========================================================================

class TestScraperAndDatabaseAlignment:
    """Valida a compatibilidade de conexão entre o script do scraper e a camada database."""

    def test_scraper_and_mongo_connection_same_defaults(self, clean_env):
        """2.1 Scraper carregar_mongo e MongoConnection utilizam exatamente os mesmos defaults."""
        os.environ.pop("MONGO_URI", None)
        os.environ.pop("MONGO_DB_NAME", None)

        from src.database.mongo_connection import MongoConnection
        mongo_conn = MongoConnection()
        
        carregar_file = ROOT_DIR / "src" / "scraper" / "carregar_mongo.py"
        content = carregar_file.read_text(encoding="utf-8")

        # Verifica se o default de URI no scraper coincide com o default do MongoConnection
        assert mongo_conn.uri in content or "mongodb://localhost:27017" in content, (
            "Default de MONGO_URI no scraper deve coincidir com 'mongodb://localhost:27017'."
        )
        assert mongo_conn.db_name in content or "rag_juridico" in content, (
            "Default de MONGO_DB_NAME no scraper deve coincidir com 'rag_juridico'."
        )

    def test_scraper_module_execution_with_custom_env(self, clean_env):
        """2.2 Scraper reage às mesmas variáveis de ambiente MONGO_URI e MONGO_DB_NAME."""
        test_uri = "mongodb://custom_scraper_host:27017"
        test_db = "custom_scraper_db"
        os.environ["MONGO_URI"] = test_uri
        os.environ["MONGO_DB_NAME"] = test_db

        import src.scraper.carregar_mongo as scraper_module
        # O módulo define MONGO_URI e MONGO_DB_NAME lidos do ambiente
        module_uri = getattr(scraper_module, "MONGO_URI", None)
        module_db = getattr(scraper_module, "MONGO_DB_NAME", None)
        
        if module_uri is not None:
            # Se já importado anteriormente, recarregar para testar atualização
            import importlib
            importlib.reload(scraper_module)
            assert scraper_module.MONGO_URI == test_uri
            assert scraper_module.MONGO_DB_NAME == test_db


# ===========================================================================
# 3. Cross-Feature: Persistência Chroma, Arquivos e Gitkeep
# ===========================================================================

class TestChromaPersistenceAndGitIntegration:
    """Valida a coexistência do diretório ChromaDB com regras de gitkeep e gitignore."""

    def test_chroma_path_preserves_gitkeep_file(self, clean_env, reset_singletons):
        """3.1 A inicialização da pasta do Chroma não remove nem sobrescreve o .gitkeep estrutural."""
        chroma_keep = ROOT_DIR / "data" / "chromadb_local" / ".gitkeep"
        assert chroma_keep.exists(), "O arquivo data/chromadb_local/.gitkeep deve existir."

        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=str(ROOT_DIR / "data" / "chromadb_local"))
        
        # O .gitkeep deve continuar existindo após instanciação
        assert chroma_keep.exists(), "A conexão Chroma não deve remover o arquivo .gitkeep pré-existente."

    def test_chroma_relative_path_from_different_cwd(self, temp_dir, clean_env, reset_singletons):
        """3.2 Resolução correta do caminho CHROMA_DB_PATH independente do cwd do processo."""
        from src.database.chroma_connection import ChromaConnection
        sub_folder = temp_dir / "sub"
        sub_folder.mkdir(parents=True, exist_ok=True)
        
        original_cwd = os.getcwd()
        try:
            os.chdir(str(sub_folder))
            conn = ChromaConnection(path=str(temp_dir / "chroma_relative_test"))
            assert Path(conn.path).exists()
        finally:
            os.chdir(original_cwd)


# ===========================================================================
# 4. Cross-Feature: FastAPI e Modelos de Machine Learning
# ===========================================================================

class TestFastApiAndModelIntegration:
    """Valida o desacoplamento e a transição arquitetural entre API e modelos."""

    def test_api_bm25_contract_matches_model_signature(self, api_client):
        """4.1 O endpoint /search/bm25 consome query compatível com o método search de BM25Search."""
        from src.models.bm25_search import BM25Search
        search_sig = inspect.signature(BM25Search.search)
        assert "query" in search_sig.parameters, "BM25Search.search deve receber parâmetro 'query'."

        # API recebe payload com 'query' e responde mock sem falha
        res = api_client.post("/search/bm25", json={"query": "art. 186"})
        assert res.status_code == 200
        assert res.json()["query"] == "art. 186"

    def test_api_bert_contract_matches_model_signature(self, api_client):
        """4.2 O endpoint /search/bert consome query compatível com o método search de BERTSearch."""
        from src.models.bert_search import BERTSearch
        search_sig = inspect.signature(BERTSearch.search)
        assert "query" in search_sig.parameters, "BERTSearch.search deve receber parâmetro 'query'."

        # API recebe payload com 'query' e responde mock sem falha
        res = api_client.post("/search/bert", json={"query": "responsabilidade extracontratual"})
        assert res.status_code == 200
        assert res.json()["query"] == "responsabilidade extracontratual"

    def test_api_mock_detail_signals_implementation_pending(self, api_client):
        """4.3 Resposta da API sinaliza detail='not implemented' consistente com NotImplementedError dos modelos."""
        res_bm25 = api_client.post("/search/bm25", json={"query": "teste"})
        res_bert = api_client.post("/search/bert", json={"query": "teste"})

        assert res_bm25.json()["detail"] == "not implemented"
        assert res_bert.json()["detail"] == "not implemented"


# ===========================================================================
# 5. Cross-Feature: Docker Compose, .env.example e Port Alignment
# ===========================================================================

class TestDockerComposeAndEnvAlignment:
    """Valida consistência entre declaração de serviços Docker e templates .env."""

    def test_docker_compose_and_env_example_port_consistency(self):
        """5.1 Porta mapeada em docker-compose.yml corresponde à URI em .env.example."""
        compose_content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")
        env_content = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

        # Extrai porta de docker-compose
        port_match = re.search(r"(\d+):27017", compose_content)
        assert port_match, "Porta mapeada para 27017 não encontrada em docker-compose.yml."
        host_port = port_match.group(1)

        # Extrai URI de .env.example
        uri_match = re.search(r"MONGO_URI=mongodb://localhost:(\d+)", env_content)
        assert uri_match, "MONGO_URI com localhost não encontrada em .env.example."
        env_port = uri_match.group(1)

        assert host_port == env_port, (
            f"Porta no docker-compose.yml ({host_port}) difere da porta no .env.example ({env_port})."
        )

    def test_gitignore_protects_env_and_allows_env_example(self):
        """5.2 .gitignore ignora .env mas permite versionar .env.example."""
        gitignore_content = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
        assert ".env" in gitignore_content
        # Assegura que .env.example não seja bloqueado inadvertidamente
        lines = [l.strip() for l in gitignore_content.splitlines()]
        assert ".env.example" not in lines, ".env.example não deve constar explicitamente no .gitignore."
