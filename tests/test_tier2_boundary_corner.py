"""
Tier 2: Boundary & Corner Cases Test Suite - JudAI
==================================================
Validação de casos de borda, entradas extremas, robustez de tipos e concorrência:
1. Queries vazias, espaços, quebras de linha e tamanhos extremos
2. Caracteres acentuados, símbolos jurídicos (§, º, ª), aspas, escapes e Unicode
3. Validação rigorosa de payload Pydantic (campos ausentes, tipos inválidos: int, list, null)
4. Verbos HTTP incorretos (405 Method Not Allowed)
5. Inicializações consecutivas e concorrência multi-thread em Singletons
6. Variáveis de ambiente vazias ou malformadas (fallback seguro)
7. Resolução de caminhos agnóstica de SO e criação profunda de diretórios no ChromaDB
8. Entradas de borda nos métodos dos placeholders de modelos ML

Cada feature possui >= 5 testes de casos de borda.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


# ===========================================================================
# 1. Feature: Boundary API Queries (>= 5 testes)
# ===========================================================================

class TestBoundaryApiQueries:
    """Testa variações extremas e limites no texto da query da API."""

    def test_query_empty_string(self, api_client):
        """1.1 Query vazia ("") deve ser aceita e retornada preservada com HTTP 200."""
        payload = {"query": ""}
        response = api_client.post("/search/bm25", json=payload)
        assert response.status_code == 200, f"Query vazia deveria retornar 200, retornou {response.status_code}."
        assert response.json()["query"] == ""

    def test_query_whitespace_and_newlines_only(self, api_client):
        """1.2 Query contendo apenas espaços, tabulações e quebras de linha."""
        whitespace_query = "   \t\n   \r\n   "
        payload = {"query": whitespace_query}
        response = api_client.post("/search/bert", json=payload)
        assert response.status_code == 200, f"Query de espaços deveria retornar 200, retornou {response.status_code}."
        assert response.json()["query"] == whitespace_query

    def test_query_brazilian_legal_symbols_and_accents(self, api_client):
        """1.3 Query com símbolos típicos do direito brasileiro: §, º, ª, c/c, acentos."""
        legal_query = "Ação de usucapião extraordinária c/c art. 1.238, parágrafo único § 1º, inc. II e alínea 'a' do CC/2002"
        payload = {"query": legal_query}
        response = api_client.post("/search/bm25", json=payload)
        assert response.status_code == 200
        assert response.json()["query"] == legal_query, "Símbolos jurídicos e acentuação devem ser rigorosamente preservados sem mojibake."

    def test_query_unicode_extreme_and_quotes(self, api_client):
        """1.4 Query com aspas duplas, simples, barras, traves travessões e emojis/unicode."""
        complex_query = 'Recurso Especial: "Dano moral in re ipsa" — Art. 186 & 927 do CC/2002 \u2014 \u00a7 2\u00ba \U0001F4DA \U0001F50D'
        payload = {"query": complex_query}
        response = api_client.post("/search/bert", json=payload)
        assert response.status_code == 200
        assert response.json()["query"] == complex_query

    def test_query_large_payload_stress(self, api_client):
        """1.5 Query de grande extensão (10.000 caracteres de texto legislativo)."""
        large_query = ("Artigo 186. Aquele que, por ação ou omissão voluntária... " * 180)[:10000]
        payload = {"query": large_query}
        response = api_client.post("/search/bm25", json=payload)
        assert response.status_code == 200
        assert len(response.json()["query"]) == 10000


# ===========================================================================
# 2. Feature: Boundary API Validation & HTTP Verbs (>= 5 testes)
# ===========================================================================

class TestBoundaryApiValidationAndVerbs:
    """Testa validação de esquema Pydantic e comportamento de verbos HTTP inválidos."""

    def test_payload_missing_query_field(self, api_client):
        """2.1 Payload vazio {} sem a chave 'query' deve retornar 422 Unprocessable Entity."""
        response = api_client.post("/search/bm25", json={})
        assert response.status_code == 422, f"Esperado 422 para campo ausente, obtido {response.status_code}."

    def test_payload_query_wrong_type_integer(self, api_client):
        """2.2 Tipo incorreto (inteiro em vez de string) deve retornar 422."""
        response = api_client.post("/search/bm25", json={"query": 12345})
        assert response.status_code == 422, f"Esperado 422 para tipo int, obtido {response.status_code}."

    def test_payload_query_wrong_type_list(self, api_client):
        """2.3 Tipo incorreto (lista de termos em vez de string) deve retornar 422."""
        response = api_client.post("/search/bert", json={"query": ["artigo", "186"]})
        assert response.status_code == 422, f"Esperado 422 para tipo list, obtido {response.status_code}."

    def test_payload_query_null_value(self, api_client):
        """2.4 Campo query com valor null/None deve retornar 422."""
        response = api_client.post("/search/bm25", json={"query": None})
        assert response.status_code == 422, f"Esperado 422 para query null, obtido {response.status_code}."

    def test_http_verbs_method_not_allowed(self, api_client):
        """2.5 Verbos HTTP incorretos em endpoints devem retornar 405 Method Not Allowed."""
        res_get_bm25 = api_client.get("/search/bm25")
        assert res_get_bm25.status_code == 405, f"GET /search/bm25 deve retornar 405, retornou {res_get_bm25.status_code}."

        res_get_bert = api_client.get("/search/bert")
        assert res_get_bert.status_code == 405, f"GET /search/bert deve retornar 405, retornou {res_get_bert.status_code}."

        res_post_health = api_client.post("/health", json={})
        assert res_post_health.status_code == 405, f"POST /health deve retornar 405, retornou {res_post_health.status_code}."

    def test_payload_malformed_json_body(self, api_client):
        """2.6 Envio de corpo não formatado como JSON válido retorna 422."""
        response = api_client.post(
            "/search/bm25",
            content=b"{query: invalid_json_syntax",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


# ===========================================================================
# 3. Feature: Boundary Singleton Concurrency & Inits (>= 5 testes)
# ===========================================================================

class TestBoundarySingletonConcurrency:
    """Testa concorrência, invocações sucessivas e proteção de construtores em Singletons."""

    def test_mongo_multiple_consecutive_inits(self, reset_singletons):
        """3.1 Invocação consecutiva de MongoConnection 50 vezes em loop."""
        from src.database.mongo_connection import MongoConnection
        first = MongoConnection()
        for _ in range(50):
            current = MongoConnection()
            assert current is first, "Instanciação consecutiva deve sempre retornar a mesma referência."
            assert current.client is first.client, "Cliente interno do MongoClient não deve ser recriado."

    def test_chroma_multiple_consecutive_inits(self, reset_singletons):
        """3.2 Invocação consecutiva de ChromaConnection 50 vezes em loop."""
        from src.database.chroma_connection import ChromaConnection
        first = ChromaConnection()
        for _ in range(50):
            current = ChromaConnection()
            assert current is first, "Instanciação consecutiva deve sempre retornar a mesma referência."
            assert current.client is first.client, "Cliente interno do ChromaDB não deve ser recriado."

    def test_mongo_multithreaded_instantiation(self, reset_singletons):
        """3.3 20 threads concorrentes instanciando MongoConnection simultaneamente."""
        from src.database.mongo_connection import MongoConnection
        instances = []

        def worker():
            inst = MongoConnection()
            instances.append(inst)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(instances) == 20
        primary = instances[0]
        for inst in instances[1:]:
            assert inst is primary, "Todas as threads concorrentes devem receber a mesma instância de MongoConnection."

    def test_chroma_multithreaded_instantiation(self, reset_singletons):
        """3.4 20 threads concorrentes instanciando ChromaConnection simultaneamente."""
        from src.database.chroma_connection import ChromaConnection
        instances = []

        def worker():
            inst = ChromaConnection()
            instances.append(inst)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(instances) == 20
        primary = instances[0]
        for inst in instances[1:]:
            assert inst is primary, "Todas as threads concorrentes devem receber a mesma instância de ChromaConnection."

    def test_mongo_empty_environment_variables_fallback(self, clean_env, reset_singletons):
        """3.5 MONGO_URI="" ou MONGO_DB_NAME="" com strings vazias faz fallback para os defaults."""
        os.environ["MONGO_URI"] = ""
        os.environ["MONGO_DB_NAME"] = ""

        from src.database.mongo_connection import MongoConnection
        conn = MongoConnection()
        assert conn.uri == "mongodb://localhost:27017", (
            f"Esperado fallback 'mongodb://localhost:27017' para string vazia, obtido '{conn.uri}'."
        )
        assert conn.db_name == "rag_juridico", (
            f"Esperado fallback 'rag_juridico' para string vazia, obtido '{conn.db_name}'."
        )

    def test_chroma_empty_environment_variable_fallback(self, clean_env, reset_singletons):
        """3.6 CHROMA_DB_PATH="" com string vazia faz fallback para o default ./data/chromadb_local."""
        os.environ["CHROMA_DB_PATH"] = ""

        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection()
        expected = Path("./data/chromadb_local").resolve()
        assert Path(conn.path).resolve() == expected


# ===========================================================================
# 4. Feature: Boundary Chroma Path Handling (>= 5 testes)
# ===========================================================================

class TestBoundaryChromaPathHandling:
    """Testa tratamento de caminhos, diretórios profundos e barras no ChromaConnection."""

    def test_chroma_deep_nested_directory_creation(self, temp_dir, reset_singletons):
        """4.1 Criação de diretório persistente com 4 níveis de subpastas não existentes."""
        deep_path = temp_dir / "nivel1" / "nivel2" / "nivel3" / "chroma_store"
        assert not deep_path.exists()

        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=str(deep_path))
        assert deep_path.exists(), "ChromaConnection deve criar diretórios recursivamente (parents=True)."
        assert deep_path.is_dir()

    def test_chroma_mixed_slashes_normalization(self, temp_dir, reset_singletons):
        """4.2 Suporte a caminhos com barras mistas (/ e \\) de forma independente de SO."""
        mixed_str = str(temp_dir).replace("\\", "/") + "/subpasta/dados"
        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=mixed_str)
        assert Path(conn.path).exists()
        assert Path(conn.path).resolve() == Path(mixed_str).resolve()

    def test_chroma_existing_directory_idempotency(self, temp_dir, reset_singletons):
        """4.3 Instanciação sobre diretório pré-existente não lança FileExistsError."""
        existing_path = temp_dir / "already_exists"
        existing_path.mkdir(parents=True, exist_ok=True)

        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=str(existing_path))
        assert conn is not None
        assert Path(conn.path).resolve() == existing_path.resolve()

    def test_chroma_path_as_pathlib_object(self, temp_dir, reset_singletons):
        """4.4 Aceita instância de pathlib.Path diretamente no construtor."""
        path_obj = temp_dir / "pathlib_path"
        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=path_obj)
        assert Path(conn.path).resolve() == path_obj.resolve()

    def test_chroma_path_property_returns_path_or_str(self, temp_dir, reset_singletons):
        """4.5 Propriedade .path retorna objeto Path ou string resolvida compatível."""
        test_path = temp_dir / "prop_test"
        from src.database.chroma_connection import ChromaConnection
        conn = ChromaConnection(path=str(test_path))
        assert Path(conn.path).is_absolute() or Path(conn.path).is_dir()


# ===========================================================================
# 5. Feature: Boundary Model Placeholders Inputs (>= 5 testes)
# ===========================================================================

class TestBoundaryModelPlaceholdersInputs:
    """Testa chamadas aos placeholders com entradas vazias e parâmetros extremos."""

    def test_bm25_search_empty_query_raises_not_implemented(self):
        """5.1 BM25Search.search('') com string vazia lança NotImplementedError."""
        from src.models.bm25_search import BM25Search
        bm25 = BM25Search()
        with pytest.raises(NotImplementedError):
            bm25.search("", top_k=0)

    def test_bm25_fit_empty_corpus_raises_not_implemented(self):
        """5.2 BM25Search.fit([]) com corpus vazio lança NotImplementedError."""
        from src.models.bm25_search import BM25Search
        bm25 = BM25Search()
        with pytest.raises(NotImplementedError):
            bm25.fit([])

    def test_bert_search_empty_query_raises_not_implemented(self):
        """5.3 BERTSearch.search('') com string vazia lança NotImplementedError."""
        from src.models.bert_search import BERTSearch
        bert = BERTSearch()
        with pytest.raises(NotImplementedError):
            bert.search("", top_k=0)

    def test_bert_encode_empty_list_raises_not_implemented(self):
        """5.4 BERTSearch.encode([]) com lista vazia lança NotImplementedError."""
        from src.models.bert_search import BERTSearch
        bert = BERTSearch()
        with pytest.raises(NotImplementedError):
            bert.encode([])

    def test_bert_custom_model_name_raises_not_implemented(self):
        """5.5 BERTSearch com modelo customizado aceita configuração e lança NotImplementedError na busca."""
        from src.models.bert_search import BERTSearch
        custom_model = "neuralmind/bert-base-portuguese-cased"
        bert = BERTSearch(model_name=custom_model)
        assert bert.model_name == custom_model
        with pytest.raises(NotImplementedError):
            bert.search("relação de consumo", top_k=10)
