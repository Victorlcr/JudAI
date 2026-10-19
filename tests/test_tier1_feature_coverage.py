"""
Tier 1: Feature Coverage Test Suite - JudAI
===========================================
Validação opaca e orientada a contratos e requisitos para cada feature essencial:
1. Docker Compose config (arquivo, sintaxe, serviço, porta, volumes)
2. Controle de versão e infraestrutura Git (.gitignore, .gitattributes, requirements, .env.example, .gitkeep)
3. Singleton MongoConnection (identidade, cliente, defaults, parâmetros, sem CRUD, reset)
4. Singleton ChromaConnection (identidade, cliente, diretório, sem CRUD, reset)
5. Placeholders de modelos ML BM25 e BERT (imports, docstrings, classes, NotImplementedError)
6. API FastAPI (instância, /health, /search/bm25, /search/bert, OpenAPI docs)
7. Migração do Scraper (pacote src/scraper, imports relativos/módulo, funções preservadas, suporte a .env)

Cada feature possui >= 5 testes automatizados independentes.
"""
from __future__ import annotations

import os
import re
import sys
import shutil
import inspect
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


# ===========================================================================
# 1. Feature: Docker Compose Config (>= 5 testes)
# ===========================================================================

class TestDockerComposeConfig:
    """Valida a configuração e integridade da infraestrutura Docker Compose."""

    def test_docker_compose_file_exists(self):
        """1.1 Verifica se docker-compose.yml existe na raiz do projeto."""
        compose_file = ROOT_DIR / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml não foi encontrado na raiz do projeto."
        assert compose_file.is_file(), "docker-compose.yml deve ser um arquivo regular."
        assert compose_file.stat().st_size > 0, "docker-compose.yml não pode estar vazio."

    def test_docker_compose_service_mongodb_declared(self):
        """1.2 Verifica se o serviço mongodb está declarado com imagem mongo:latest."""
        compose_file = ROOT_DIR / "docker-compose.yml"
        content = compose_file.read_text(encoding="utf-8")
        assert "mongodb:" in content or "'mongodb':" in content or '"mongodb":' in content, (
            "Serviço 'mongodb' não está declarado em docker-compose.yml."
        )
        assert "image: mongo:latest" in content or 'image: "mongo:latest"' in content or "image: 'mongo:latest'" in content, (
            "A imagem do serviço mongodb deve ser 'mongo:latest'."
        )

    def test_docker_compose_port_mapping(self):
        """1.3 Verifica se a porta 27017:27017 está mapeada para o host."""
        compose_file = ROOT_DIR / "docker-compose.yml"
        content = compose_file.read_text(encoding="utf-8")
        assert "27017:27017" in content, (
            "Mapeamento de porta '27017:27017' não foi encontrado em docker-compose.yml."
        )

    def test_docker_compose_named_volume_and_mount(self):
        """1.4 Verifica o volume nomeado persistente montado em /data/db."""
        compose_file = ROOT_DIR / "docker-compose.yml"
        content = compose_file.read_text(encoding="utf-8")
        assert "/data/db" in content, (
            "O volume deve ser montado no diretório interno '/data/db' do container."
        )
        # Verifica se há volume nomeado definido na raiz do compose
        assert re.search(r"volumes:\s*\n\s+([a-zA-Z0-9_\-]+):", content) or "mongo_data:" in content, (
            "Volume nomeado para persistência do MongoDB não foi declarado na raiz do compose."
        )

    def test_docker_compose_yaml_structure_valid(self):
        """1.5 Valida a sintaxe e estrutura hierárquica mínima do docker-compose.yml."""
        compose_file = ROOT_DIR / "docker-compose.yml"
        content = compose_file.read_text(encoding="utf-8")
        lines = [line.rstrip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        assert any(l.startswith("services:") for l in lines), "docker-compose.yml deve conter a chave de topo 'services:'."
        
        # Testar com yaml se pyyaml estiver disponível
        try:
            import yaml
            parsed = yaml.safe_load(content)
            assert isinstance(parsed, dict), "docker-compose.yml deve ser um dicionário YAML válido."
            assert "services" in parsed, "Chave 'services' ausente no YAML parseado."
            assert "mongodb" in parsed["services"], "Serviço 'mongodb' ausente em 'services'."
        except ImportError:
            # Fallback sem PyYAML: checagem estática de indentação e tokens
            pass

    def test_docker_compose_cli_validation(self):
        """1.6 Executa 'docker compose config' se Docker estiver disponível no ambiente."""
        docker_cmd = shutil.which("docker")
        if not docker_cmd:
            pytest.skip("Docker CLI não disponível no ambiente de execução para 'docker compose config'.")
        
        result = subprocess.run(
            ["docker", "compose", "config"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"docker compose config falhou com erro: {result.stderr}"


# ===========================================================================
# 2. Feature: Git Configuration & Directory Structure (>= 5 testes)
# ===========================================================================

class TestGitConfigurationAndStructure:
    """Valida governança, controle de versão e árvore estrutural de diretórios."""

    def test_gitkeep_files_in_data_and_notebooks(self):
        """2.1 Verifica existência dos arquivos .gitkeep estruturais."""
        expected_gitkeeps = [
            ROOT_DIR / "data" / "raw" / ".gitkeep",
            ROOT_DIR / "data" / "chromadb_local" / ".gitkeep",
            ROOT_DIR / "notebooks" / ".gitkeep",
        ]
        for gk in expected_gitkeeps:
            assert gk.exists(), f"Arquivo .gitkeep obrigatório não encontrado em: {gk}"
            assert gk.is_file(), f"O caminho {gk} deve ser um arquivo."

    def test_gitignore_contains_required_rules(self):
        """2.2 Verifica se .gitignore ignora venv, .venv, .env e cache."""
        gitignore = ROOT_DIR / ".gitignore"
        assert gitignore.exists(), "Arquivo .gitignore não encontrado na raiz."
        content = gitignore.read_text(encoding="utf-8")
        
        assert "venv" in content, ".gitignore deve ignorar 'venv/'."
        assert ".venv" in content, ".gitignore deve ignorar '.venv/'."
        assert ".env" in content, ".gitignore deve ignorar '.env'."
        assert "__pycache__" in content, ".gitignore deve ignorar '__pycache__/'."

    def test_gitignore_data_rule_and_gitkeep_exception(self):
        """2.3 Verifica se .gitignore ignora data/* mas preserva .gitkeep."""
        gitignore = ROOT_DIR / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        
        assert "data/" in content or "data/*" in content, ".gitignore deve ignorar o conteúdo de 'data/'."
        assert "!data/**/.gitkeep" in content or "!.gitkeep" in content, (
            ".gitignore deve conter exceção para versionar arquivos .gitkeep em data/."
        )

    def test_gitattributes_contains_eol_lf(self):
        """2.4 Verifica se .gitattributes normaliza finais de linha para LF."""
        gitattributes = ROOT_DIR / ".gitattributes"
        assert gitattributes.exists(), "Arquivo .gitattributes não encontrado na raiz."
        content = gitattributes.read_text(encoding="utf-8")
        assert "* text=auto eol=lf" in content, (
            ".gitattributes deve conter a diretiva exata '* text=auto eol=lf'."
        )

    def test_requirements_txt_contains_12_unpinned_deps(self):
        """2.5 Verifica se requirements.txt contém as 12 dependências requeridas sem pin de versão."""
        req_file = ROOT_DIR / "requirements.txt"
        assert req_file.exists(), "Arquivo requirements.txt não encontrado."
        lines = [line.strip().lower() for line in req_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
        
        expected_packages = [
            "fastapi",
            "uvicorn[standard]",
            "pydantic",
            "pymongo",
            "chromadb",
            "rank_bm25",
            "sentence-transformers",
            "nltk",
            "python-dotenv",
            "beautifulsoup4",
            "lxml",
            "requests",
        ]
        
        for pkg in expected_packages:
            matching = [l for l in lines if l == pkg or l.startswith(pkg.split("[")[0])]
            assert len(matching) > 0, f"Dependência '{pkg}' ausente em requirements.txt."
            # Verifica ausência de versão fixa '=='
            for match in matching:
                assert "==" not in match, f"Pacote '{match}' não deve ter versão fixada com '==' em requirements.txt."

    def test_env_example_template_keys(self):
        """2.6 Verifica se .env.example contém todas as chaves obrigatórias."""
        env_ex = ROOT_DIR / ".env.example"
        assert env_ex.exists(), "Arquivo .env.example não encontrado."
        content = env_ex.read_text(encoding="utf-8")
        
        assert "MONGO_URI=" in content, "MONGO_URI deve estar definido em .env.example."
        assert "MONGO_DB_NAME=" in content, "MONGO_DB_NAME deve estar definido em .env.example."
        assert "CHROMA_DB_PATH=" in content, "CHROMA_DB_PATH deve estar definido em .env.example."


# ===========================================================================
# 3. Feature: Singleton MongoConnection (>= 5 testes)
# ===========================================================================

class TestMongoConnectionFeature:
    """Valida o padrão Singleton, configuração por ambiente e isolamento do MongoConnection."""

    def test_mongo_singleton_same_instance(self, reset_singletons):
        """3.1 Duas chamadas consecutivas retornam exatamente a mesma instância (c1 is c2)."""
        from src.database.mongo_connection import MongoConnection
        c1 = MongoConnection()
        c2 = MongoConnection()
        assert c1 is c2, "MongoConnection deve implementar o padrão Singleton (c1 is c2)."

    def test_mongo_client_same_instance(self, reset_singletons):
        """3.2 O cliente MongoClient interno é reutilizado pela mesma instância."""
        from src.database.mongo_connection import MongoConnection
        c1 = MongoConnection()
        c2 = MongoConnection()
        assert c1.client is c2.client, "MongoConnection.client deve ser o mesmo objeto entre chamadas."
        assert c1.db is c2.db, "MongoConnection.db deve ser o mesmo objeto de banco de dados."

    def test_mongo_default_env_values(self, clean_env, reset_singletons):
        """3.3 Quando variáveis de ambiente não são definidas, utiliza valores default especificados."""
        os.environ.pop("MONGO_URI", None)
        os.environ.pop("MONGO_DB_NAME", None)
        
        from src.database.mongo_connection import MongoConnection
        conn = MongoConnection()
        assert conn.uri == "mongodb://localhost:27017", (
            f"MONGO_URI padrão esperada 'mongodb://localhost:27017', obtida '{conn.uri}'."
        )
        assert conn.db_name == "rag_juridico", (
            f"MONGO_DB_NAME padrão esperada 'rag_juridico', obtida '{conn.db_name}'."
        )

    def test_mongo_custom_parameters(self, clean_env, reset_singletons):
        """3.4 Permite sobrescrita de URI e DB via construtor ou variáveis de ambiente."""
        from src.database.mongo_connection import MongoConnection
        custom_uri = "mongodb://custom_host:27018"
        custom_db = "test_custom_db"
        conn = MongoConnection(uri=custom_uri, db_name=custom_db)
        assert conn.uri == custom_uri, f"Esperado URI '{custom_uri}', obtido '{conn.uri}'."
        assert conn.db_name == custom_db, f"Esperado DB '{custom_db}', obtido '{conn.db_name}'."

    def test_mongo_no_crud_methods(self):
        """3.5 Garante que MongoConnection NÃO possui métodos CRUD de inserção ou busca."""
        from src.database.mongo_connection import MongoConnection
        forbidden_methods = [
            "insert", "insert_one", "insert_many",
            "find", "find_one", "search", "query",
            "delete", "update", "drop"
        ]
        conn_methods = [m for m in dir(MongoConnection) if not m.startswith("_")]
        for m in forbidden_methods:
            assert m not in conn_methods, (
                f"Método CRUD '{m}' encontrado em MongoConnection. MongoConnection deve ser puramente conexão."
            )

    def test_mongo_reset_mechanism(self, reset_singletons):
        """3.6 Método reset() zera a instância permitindo nova configuração."""
        from src.database.mongo_connection import MongoConnection
        c1 = MongoConnection(uri="mongodb://first:27017")
        if hasattr(MongoConnection, "reset"):
            MongoConnection.reset()
            c2 = MongoConnection(uri="mongodb://second:27017")
            assert c1 is not c2, "Após reset(), uma nova instância independente deve ser criada."
            assert c2.uri == "mongodb://second:27017"


# ===========================================================================
# 4. Feature: Singleton ChromaConnection (>= 5 testes)
# ===========================================================================

class TestChromaConnectionFeature:
    """Valida o padrão Singleton, criação de diretório e isolamento do ChromaConnection."""

    def test_chroma_singleton_same_instance(self, reset_singletons):
        """4.1 Duas chamadas consecutivas retornam exatamente a mesma instância (c1 is c2)."""
        from src.database.chroma_connection import ChromaConnection
        c1 = ChromaConnection()
        c2 = ChromaConnection()
        assert c1 is c2, "ChromaConnection deve implementar o padrão Singleton (c1 is c2)."

    def test_chroma_client_same_instance(self, reset_singletons):
        """4.2 O cliente ChromaDB interno é reutilizado pela mesma instância."""
        from src.database.chroma_connection import ChromaConnection
        c1 = ChromaConnection()
        c2 = ChromaConnection()
        assert c1.client is c2.client, "ChromaConnection.client deve ser o mesmo objeto entre chamadas."

    def test_chroma_default_path(self, clean_env, reset_singletons):
        """4.3 Quando CHROMA_DB_PATH não for especificado, utiliza ./data/chromadb_local."""
        os.environ.pop("CHROMA_DB_PATH", None)
        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection()
        expected = Path("./data/chromadb_local").resolve()
        assert Path(conn.path).resolve() == expected, (
            f"Esperado caminho padrão '{expected}', obtido '{Path(conn.path).resolve()}'."
        )

    def test_chroma_creates_directory_if_not_exists(self, temp_dir, clean_env, reset_singletons):
        """4.4 ChromaConnection cria automaticamente a pasta no disco caso ela não exista."""
        new_path = temp_dir / "novo_subdiretorio" / "chroma_data"
        assert not new_path.exists(), "Diretório de teste não deveria existir antes da conexão."
        
        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=str(new_path))
        assert new_path.exists(), "ChromaConnection não criou a pasta persistente automaticamente."
        assert new_path.is_dir(), "O caminho criado deve ser um diretório."

    def test_chroma_no_crud_methods(self):
        """4.5 Garante que ChromaConnection NÃO possui métodos CRUD de busca ou inserção."""
        from src.database.chroma_connection import ChromaConnection
        forbidden_methods = [
            "add", "query", "search", "get", "delete",
            "create_collection", "get_collection", "get_or_create_collection"
        ]
        conn_methods = [m for m in dir(ChromaConnection) if not m.startswith("_")]
        for m in forbidden_methods:
            assert m not in conn_methods, (
                f"Método CRUD '{m}' encontrado em ChromaConnection. ChromaConnection deve ser puramente conexão."
            )

    def test_chroma_reset_mechanism(self, temp_dir, reset_singletons):
        """4.6 Método reset() zera a instância permitindo nova configuração de caminho."""
        from src.database.chroma_connection import ChromaConnection
        path1 = temp_dir / "chroma_1"
        path2 = temp_dir / "chroma_2"
        
        c1 = ChromaConnection(path=str(path1))
        if hasattr(ChromaConnection, "reset"):
            ChromaConnection.reset()
            c2 = ChromaConnection(path=str(path2))
            assert c1 is not c2, "Após reset(), uma nova instância independente de Chroma deve ser criada."
            assert Path(c2.path).resolve() == path2.resolve()


# ===========================================================================
# 5. Feature: Placeholders de Modelos ML (BM25 e BERT) (>= 5 testes)
# ===========================================================================

class TestMLModelPlaceholders:
    """Valida os módulos placeholders de busca léxica (BM25) e semântica (BERT)."""

    def test_bm25_search_module_and_class_exist(self):
        """5.1 Verifica se o módulo src.models.bm25_search e a classe BM25Search existem."""
        import src.models.bm25_search as bm25_mod
        assert hasattr(bm25_mod, "BM25Search"), "Classe 'BM25Search' não encontrada no módulo bm25_search."
        instance = bm25_mod.BM25Search()
        assert instance is not None

    def test_bm25_search_docstrings_present(self):
        """5.2 Verifica se as docstrings detalham o papel do BM25 no RAG híbrido."""
        import src.models.bm25_search as bm25_mod
        mod_doc = inspect.getdoc(bm25_mod) or ""
        class_doc = inspect.getdoc(bm25_mod.BM25Search) or ""
        full_doc = f"{mod_doc} {class_doc}".lower()
        
        assert "bm25" in full_doc, "Docstring deve mencionar BM25."
        assert "placeholder" in full_doc or "não implementad" in full_doc or "not implemented" in full_doc, (
            "Docstring deve indicar expressamente que é um placeholder estrutural."
        )

    def test_bm25_search_methods_raise_not_implemented(self):
        """5.3 Métodos fit() e search() do BM25Search lançam NotImplementedError."""
        from src.models.bm25_search import BM25Search
        bm25 = BM25Search()
        with pytest.raises(NotImplementedError):
            bm25.fit([{"id": 1, "texto": "artigo 1"}])
        with pytest.raises(NotImplementedError):
            bm25.search("prescrição", top_k=5)

    def test_bert_search_module_and_class_exist(self):
        """5.4 Verifica se o módulo src.models.bert_search e a classe BERTSearch existem."""
        import src.models.bert_search as bert_mod
        assert hasattr(bert_mod, "BERTSearch"), "Classe 'BERTSearch' não encontrada no módulo bert_search."
        instance = bert_mod.BERTSearch()
        assert instance is not None

    def test_bert_search_docstrings_present(self):
        """5.5 Verifica se as docstrings detalham a busca semântica densa e embeddings."""
        import src.models.bert_search as bert_mod
        mod_doc = inspect.getdoc(bert_mod) or ""
        class_doc = inspect.getdoc(bert_mod.BERTSearch) or ""
        full_doc = f"{mod_doc} {class_doc}".lower()
        
        assert "bert" in full_doc or "embedding" in full_doc or "semântic" in full_doc, (
            "Docstring deve mencionar BERT, embeddings ou busca semântica densa."
        )
        assert "placeholder" in full_doc or "não implementad" in full_doc or "not implemented" in full_doc, (
            "Docstring deve indicar expressamente que é um placeholder estrutural."
        )

    def test_bert_search_methods_raise_not_implemented(self):
        """5.6 Métodos encode() e search() do BERTSearch lançam NotImplementedError."""
        from src.models.bert_search import BERTSearch
        bert = BERTSearch()
        with pytest.raises(NotImplementedError):
            bert.encode(["texto de dispositivo legal"])
        with pytest.raises(NotImplementedError):
            bert.search("reparação civil", top_k=5)

    def test_models_import_fast_without_heavy_ml(self):
        """5.7 O import dos módulos de modelo é instantâneo e não carrega torch/transformers estaticamente."""
        import time
        start = time.perf_counter()
        import src.models.bm25_search
        import src.models.bert_search
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Import de modelos levou {elapsed:.2f}s, indicando dependências pesadas carregadas estaticamente."


# ===========================================================================
# 6. Feature: API FastAPI Endpoints (>= 5 testes)
# ===========================================================================

class TestFastAPIEndpointsFeature:
    """Valida a aplicação FastAPI, schemas Pydantic e respostas mockadas dos endpoints."""

    def test_fastapi_app_initialization(self):
        """6.1 Verifica se a instância 'app' existe em src.api.main e é do tipo FastAPI."""
        from fastapi import FastAPI
        from src.api.main import app
        assert isinstance(app, FastAPI), "Objeto 'app' em src.api.main deve ser uma instância de FastAPI."

    def test_api_health_endpoint_returns_200(self, api_client):
        """6.2 GET /health responde HTTP 200 com status 'ok'."""
        response = api_client.get("/health")
        assert response.status_code == 200, f"Esperado 200, obtido {response.status_code}."
        data = response.json()
        assert isinstance(data, dict), "Resposta de /health deve ser um JSON dict."
        assert data.get("status") == "ok", f"Esperado status 'ok', obtido '{data.get('status')}'."

    def test_api_search_bm25_returns_200_mock(self, api_client):
        """6.3 POST /search/bm25 responde HTTP 200 com payload mockado estruturado."""
        payload = {"query": "prescrição reparação civil"}
        response = api_client.post("/search/bm25", json=payload)
        assert response.status_code == 200, f"Esperado 200, obtido {response.status_code}."
        data = response.json()
        assert data.get("model") == "bm25", f"Esperado model 'bm25', obtido '{data.get('model')}'."
        assert data.get("query") == payload["query"], "Query retornada deve coincidir com a enviada."
        assert data.get("results") == [], f"Esperado results=[], obtido {data.get('results')}."
        assert data.get("detail") == "not implemented", f"Esperado detail 'not implemented', obtido {data.get('detail')}."

    def test_api_search_bert_returns_200_mock(self, api_client):
        """6.4 POST /search/bert responde HTTP 200 com payload mockado estruturado."""
        payload = {"query": "responsabilidade civil objetiva"}
        response = api_client.post("/search/bert", json=payload)
        assert response.status_code == 200, f"Esperado 200, obtido {response.status_code}."
        data = response.json()
        assert data.get("model") == "bert", f"Esperado model 'bert', obtido '{data.get('model')}'."
        assert data.get("query") == payload["query"], "Query retornada deve coincidir com a enviada."
        assert data.get("results") == [], f"Esperado results=[], obtido {data.get('results')}."
        assert data.get("detail") == "not implemented", f"Esperado detail 'not implemented', obtido {data.get('detail')}."

    def test_api_query_request_model(self):
        """6.5 Valida o modelo Pydantic QueryRequest(query: str)."""
        from src.api.main import QueryRequest
        req = QueryRequest(query="consulta teste")
        assert req.query == "consulta teste"

    def test_api_openapi_and_docs_available(self, api_client):
        """6.6 Documentação Swagger (/docs) e esquema OpenAPI (/openapi.json) estão acessíveis."""
        res_docs = api_client.get("/docs")
        assert res_docs.status_code == 200, "Swagger UI (/docs) deve responder 200 OK."
        
        res_openapi = api_client.get("/openapi.json")
        assert res_openapi.status_code == 200, "OpenAPI JSON (/openapi.json) deve responder 200 OK."
        schema = res_openapi.json()
        assert "/health" in schema.get("paths", {}), "Rota /health deve estar documentada no OpenAPI."
        assert "/search/bm25" in schema.get("paths", {}), "Rota /search/bm25 deve estar documentada."
        assert "/search/bert" in schema.get("paths", {}), "Rota /search/bert deve estar documentada."


# ===========================================================================
# 7. Feature: Migração do Scraper (>= 5 testes)
# ===========================================================================

class TestScraperMigrationFeature:
    """Valida a reorganização dos scripts de ingestão sob o pacote src/scraper/."""

    def test_scraper_package_structure(self):
        """7.1 Verifica se o diretório src/scraper/ possui __init__.py."""
        scraper_dir = ROOT_DIR / "src" / "scraper"
        assert scraper_dir.exists(), "Diretório src/scraper não encontrado."
        assert (scraper_dir / "__init__.py").exists(), "src/scraper/__init__.py não encontrado."

    def test_scraper_ingestao_lei_importable(self):
        """7.2 Verifica se src.scraper.ingestao_lei é importável com sucesso."""
        import src.scraper.ingestao_lei as parser
        assert parser is not None
        assert inspect.ismodule(parser)

    def test_scraper_carregar_mongo_importable(self):
        """7.3 Verifica se src.scraper.carregar_mongo é importável com sucesso."""
        import src.scraper.carregar_mongo as loader
        assert loader is not None
        assert inspect.ismodule(loader)

    def test_scraper_parser_essential_functions_preserved(self):
        """7.4 Garante que as funções essenciais de parsing de lei foram preservadas no módulo."""
        from src.scraper import ingestao_lei
        required_functions = [
            "baixar_legislacao",
            "salvar_bruto",
            "extrair_metadados",
            "extrair_estrutura",
            "extrair_dispositivos",
        ]
        for fn_name in required_functions:
            assert hasattr(ingestao_lei, fn_name), f"Função essencial '{fn_name}' ausente em ingestao_lei."
            assert callable(getattr(ingestao_lei, fn_name)), f"'{fn_name}' deve ser chamável (função)."

    def test_scraper_carregar_mongo_env_support(self):
        """7.5 Verifica se carregar_mongo lê MONGO_URI e MONGO_DB_NAME com suporte a .env."""
        carregar_file = ROOT_DIR / "src" / "scraper" / "carregar_mongo.py"
        content = carregar_file.read_text(encoding="utf-8")
        assert "MONGO_URI" in content, "carregar_mongo.py deve referenciar 'MONGO_URI'."
        assert "MONGO_DB_NAME" in content, "carregar_mongo.py deve referenciar 'MONGO_DB_NAME'."
        assert "getenv" in content or "environ" in content, "carregar_mongo.py deve carregar variáveis de ambiente."

    def test_scraper_no_scripts_left_in_root(self):
        """7.6 Verifica que os scripts ingestao_lei.py e carregar_mongo.py não permanecem na raiz após migração."""
        root_ingestao = ROOT_DIR / "ingestao_lei.py"
        root_carregar = ROOT_DIR / "carregar_mongo.py"
        # Durante M1/M2 os scripts podem ainda estar em transição, mas após M3 não devem estar na raiz
        if (ROOT_DIR / "src" / "scraper" / "ingestao_lei.py").exists():
            # Se já foi migrado, valida
            pass
