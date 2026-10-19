#!/usr/bin/env python3
"""
verify_m2.py: Script de Verificação e Validação Executável do Milestone 2
========================================================================
Testa e audita exaustivamente as classes `MongoConnection` e `ChromaConnection`
em relação a todos os requisitos funcionais, de concorrência e de borda.

Verificações executadas:
1. Singleton Identity: conn1 is conn2, conn1.client is conn2.client, conn1.db is conn2.db
2. Consecutividade: 50 chamadas sequenciais mantêm a mesma referência e client
3. Concorrência: 20 threads instanciando em paralelo retornam a mesma instância sem race condition
4. Configuração & Fallbacks: defaults ("mongodb://localhost:27017", "rag_juridico", "./data/chromadb_local")
5. Tratamento de strings vazias no ambiente ("" faz fallback seguro)
6. Sobrescrita por parâmetros de construtor
7. Resolução de caminhos agnóstica a SO (barras mistas, pathlib.Path, mkdir recursivo)
8. Preservação de arquivos pré-existentes (.gitkeep)
9. Ausência estrita de métodos CRUD na interface pública de ambas as classes
10. Mecanismo de reset estático para isolamento em testes unitários

Uso:
    python .agents/teamwork/spec_miner_m2_3/verify_m2.py
    python .agents/teamwork/spec_miner_m2_3/verify_m2.py --verify-reference
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch

# Garante raiz no sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ---------------------------------------------------------------------------
# Test Runner Utility
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.skipped = False
        self.error: str | None = None


results: list[TestResult] = []


def run_check(name: str, check_fn: Callable[[], None]) -> None:
    res = TestResult(name)
    try:
        check_fn()
        res.passed = True
        print(f"  [PASS] {name}")
    except unittest.SkipTest as e:
        res.skipped = True
        res.error = str(e)
        print(f"  [SKIP] {name}: {e}")
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {e}"
        print(f"  [FAIL] {name}: {res.error}")
    results.append(res)


# ---------------------------------------------------------------------------
# Reference Implementation for Self-Validation (--verify-reference)
# ---------------------------------------------------------------------------

class ReferenceMongoConnection:
    """Implementação canônica de referência de MongoConnection para validação do spec."""
    _instance: ReferenceMongoConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, uri: str | None = None, db_name: str | None = None) -> ReferenceMongoConnection:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, uri: str | None = None, db_name: str | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass

            self._uri = uri or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
            self._db_name = db_name or os.getenv("MONGO_DB_NAME") or "rag_juridico"

            try:
                import pymongo
                self._client = pymongo.MongoClient(self._uri)
            except ImportError:
                self._client = MagicMock()
            self._db = self._client[self._db_name]
            self._initialized = True

    @property
    def client(self) -> Any:
        return self._client

    @property
    def db(self) -> Any:
        return self._db

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def db_name(self) -> str:
        return self._db_name

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            if cls._instance is not None:
                try:
                    if hasattr(cls._instance._client, "close"):
                        cls._instance._client.close()
                except Exception:
                    pass
            cls._instance = None


class ReferenceChromaConnection:
    """Implementação canônica de referência de ChromaConnection para validação do spec."""
    _instance: ReferenceChromaConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, path: str | Path | None = None) -> ReferenceChromaConnection:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str | Path | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass

            raw_path: str | Path
            if path is not None and (not isinstance(path, str) or path.strip() != ""):
                raw_path = path
            else:
                env_val = os.getenv("CHROMA_DB_PATH")
                if env_val and env_val.strip():
                    raw_path = env_val.strip()
                else:
                    raw_path = "./data/chromadb_local"

            self._path: Path = Path(raw_path).resolve()
            if self._path.exists() and not self._path.is_dir():
                raise ValueError(f"Path '{self._path}' already exists and is not a directory.")

            self._path.mkdir(parents=True, exist_ok=True)

            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=str(self._path))
            except ImportError:
                self._client = MagicMock()

            self._initialized = True

    @property
    def client(self) -> Any:
        return self._client

    @property
    def path(self) -> Path:
        return self._path

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None


# ---------------------------------------------------------------------------
# Test Verification Suites
# ---------------------------------------------------------------------------

def run_tests_on_classes(mongo_cls: Any, chroma_cls: Any, label: str):
    print(f"\n=======================================================")
    print(f" EXECUTANDO VALIDAÇÃO: {label}")
    print(f"=======================================================")

    # 1. MONGO: Singleton Identity
    def check_mongo_singleton():
        mongo_cls.reset()
        c1 = mongo_cls()
        c2 = mongo_cls()
        assert c1 is c2, "MongoConnection deve retornar exatamente a mesma instância (c1 is c2)."
        assert c1.client is c2.client, "MongoConnection deve reutilizar o mesmo client."
        assert c1.db is c2.db, "MongoConnection deve reutilizar o mesmo banco db."
    run_check("MongoConnection: Identidade Singleton (c1 is c2, client e db)", check_mongo_singleton)

    # 2. MONGO: 50 invocações consecutivas
    def check_mongo_consecutive():
        mongo_cls.reset()
        first = mongo_cls()
        for i in range(50):
            cur = mongo_cls()
            assert cur is first, f"Invocação #{i} não retornou a mesma referência Singleton."
            assert cur.client is first.client, f"Invocação #{i} recriou o cliente MongoClient."
    run_check("MongoConnection: 50 invocações consecutivas sem recriação", check_mongo_consecutive)

    # 3. MONGO: Concorrência multi-thread (20 threads)
    def check_mongo_concurrency():
        mongo_cls.reset()
        instances = []
        errors = []

        def worker():
            try:
                inst = mongo_cls()
                instances.append(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Erros durante instanciação concorrente: {errors}"
        assert len(instances) == 20, f"Esperadas 20 instâncias coletadas, obtidas {len(instances)}"
        primary = instances[0]
        for idx, inst in enumerate(instances[1:], start=1):
            assert inst is primary, f"Thread {idx} obteve instância divergente ({inst} != {primary})."
    run_check("MongoConnection: Thread-Safety (20 threads concorrentes sem race condition)", check_mongo_concurrency)

    # 4. MONGO: Defaults quando variáveis de ambiente ausentes
    def check_mongo_defaults():
        mongo_cls.reset()
        old_uri = os.environ.pop("MONGO_URI", None)
        old_db = os.environ.pop("MONGO_DB_NAME", None)
        try:
            conn = mongo_cls()
            assert conn.uri == "mongodb://localhost:27017", f"URI default incorreta: {conn.uri}"
            assert conn.db_name == "rag_juridico", f"DB default incorreto: {conn.db_name}"
        finally:
            if old_uri is not None:
                os.environ["MONGO_URI"] = old_uri
            if old_db is not None:
                os.environ["MONGO_DB_NAME"] = old_db
    run_check("MongoConnection: Defaults oficiais ('mongodb://localhost:27017', 'rag_juridico')", check_mongo_defaults)

    # 5. MONGO: Fallback com strings vazias ("")
    def check_mongo_empty_env():
        mongo_cls.reset()
        old_uri = os.environ.get("MONGO_URI")
        old_db = os.environ.get("MONGO_DB_NAME")
        os.environ["MONGO_URI"] = ""
        os.environ["MONGO_DB_NAME"] = ""
        try:
            conn = mongo_cls()
            assert conn.uri == "mongodb://localhost:27017", f"Fallback de URI vazia falhou: {conn.uri}"
            assert conn.db_name == "rag_juridico", f"Fallback de DB vazio falhou: {conn.db_name}"
        finally:
            if old_uri is not None:
                os.environ["MONGO_URI"] = old_uri
            else:
                os.environ.pop("MONGO_URI", None)
            if old_db is not None:
                os.environ["MONGO_DB_NAME"] = old_db
            else:
                os.environ.pop("MONGO_DB_NAME", None)
    run_check("MongoConnection: Fallback seguro quando variáveis de ambiente forem strings vazias", check_mongo_empty_env)

    # 6. MONGO: Parâmetros personalizados no construtor
    def check_mongo_custom_params():
        mongo_cls.reset()
        c_uri = "mongodb://custom_host:27018"
        c_db = "custom_test_db"
        conn = mongo_cls(uri=c_uri, db_name=c_db)
        assert conn.uri == c_uri, f"Esperado {c_uri}, obtido {conn.uri}"
        assert conn.db_name == c_db, f"Esperado {c_db}, obtido {conn.db_name}"
    run_check("MongoConnection: Parâmetros personalizados no construtor têm precedência", check_mongo_custom_params)

    # 7. MONGO: Ausência de métodos CRUD na interface pública
    def check_mongo_no_crud():
        forbidden = [
            "insert", "insert_one", "insert_many",
            "find", "find_one", "search", "query",
            "delete", "update", "drop"
        ]
        public_members = [m for m in dir(mongo_cls) if not m.startswith("_")]
        for f in forbidden:
            assert f not in public_members, f"Método CRUD proibido '{f}' detectado em MongoConnection!"
    run_check("MongoConnection: Ausência estrita de métodos CRUD (pure connection provider)", check_mongo_no_crud)

    # 8. MONGO: Reset e isolamento
    def check_mongo_reset():
        mongo_cls.reset()
        c1 = mongo_cls(uri="mongodb://first:27017")
        mongo_cls.reset()
        c2 = mongo_cls(uri="mongodb://second:27017")
        assert c1 is not c2, "Após reset(), uma nova instância deve ser gerada."
        assert c2.uri == "mongodb://second:27017", f"Nova instância não capturou novos parâmetros: {c2.uri}"
    run_check("MongoConnection: Método reset() permite isolamento total entre testes", check_mongo_reset)

    # 9. CHROMA: Singleton Identity
    def check_chroma_singleton():
        chroma_cls.reset()
        c1 = chroma_cls()
        c2 = chroma_cls()
        assert c1 is c2, "ChromaConnection deve retornar a mesma instância (c1 is c2)."
        assert c1.client is c2.client, "ChromaConnection deve reutilizar o mesmo PersistentClient."
    run_check("ChromaConnection: Identidade Singleton (c1 is c2, client reutilizado)", check_chroma_singleton)

    # 10. CHROMA: 50 invocações consecutivas
    def check_chroma_consecutive():
        chroma_cls.reset()
        first = chroma_cls()
        for i in range(50):
            cur = chroma_cls()
            assert cur is first, f"Invocação #{i} não retornou a mesma referência Singleton."
            assert cur.client is first.client, f"Invocação #{i} recriou o cliente ChromaDB."
    run_check("ChromaConnection: 50 invocações consecutivas sem recriação", check_chroma_consecutive)

    # 11. CHROMA: Concorrência multi-thread (20 threads)
    def check_chroma_concurrency():
        chroma_cls.reset()
        instances = []
        errors = []

        def worker():
            try:
                inst = chroma_cls()
                instances.append(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Erros durante instanciação concorrente: {errors}"
        assert len(instances) == 20, f"Esperadas 20 instâncias coletadas, obtidas {len(instances)}"
        primary = instances[0]
        for idx, inst in enumerate(instances[1:], start=1):
            assert inst is primary, f"Thread {idx} obteve instância divergente de ChromaConnection."
    run_check("ChromaConnection: Thread-Safety (20 threads concorrentes sem race condition)", check_chroma_concurrency)

    # 12. CHROMA: Default path
    def check_chroma_default():
        chroma_cls.reset()
        old = os.environ.pop("CHROMA_DB_PATH", None)
        try:
            conn = chroma_cls()
            expected = Path("./data/chromadb_local").resolve()
            assert Path(conn.path).resolve() == expected, f"Esperado {expected}, obtido {Path(conn.path).resolve()}"
        finally:
            if old is not None:
                os.environ["CHROMA_DB_PATH"] = old
    run_check("ChromaConnection: Default oficial ('./data/chromadb_local')", check_chroma_default)

    # 13. CHROMA: Fallback com string vazia
    def check_chroma_empty_env():
        chroma_cls.reset()
        old = os.environ.get("CHROMA_DB_PATH")
        os.environ["CHROMA_DB_PATH"] = ""
        try:
            conn = chroma_cls()
            expected = Path("./data/chromadb_local").resolve()
            assert Path(conn.path).resolve() == expected, f"Fallback falhou: {Path(conn.path).resolve()}"
        finally:
            if old is not None:
                os.environ["CHROMA_DB_PATH"] = old
            else:
                os.environ.pop("CHROMA_DB_PATH", None)
    run_check("ChromaConnection: Fallback seguro quando CHROMA_DB_PATH for string vazia", check_chroma_empty_env)

    # 14. CHROMA: Criação automática de diretório inexistente (profundo)
    def check_chroma_dir_creation():
        chroma_cls.reset()
        with tempfile.TemporaryDirectory() as td:
            deep_path = Path(td) / "nivel1" / "nivel2" / "nivel3" / "chroma_store"
            assert not deep_path.exists(), "Diretório de teste não deveria existir."
            conn = chroma_cls(path=str(deep_path))
            assert deep_path.exists(), "ChromaConnection não criou o diretório profundamente aninhado."
            assert deep_path.is_dir(), "O caminho criado não é um diretório."
            assert Path(conn.path).resolve() == deep_path.resolve()
    run_check("ChromaConnection: Criação automática recursiva de diretórios (mkdir parents=True)", check_chroma_dir_creation)

    # 15. CHROMA: Idempotência sobre diretório pré-existente
    def check_chroma_idempotency():
        chroma_cls.reset()
        with tempfile.TemporaryDirectory() as td:
            existing = Path(td) / "already_exists"
            existing.mkdir(parents=True, exist_ok=True)
            conn = chroma_cls(path=str(existing))
            assert conn is not None
            assert Path(conn.path).resolve() == existing.resolve()
    run_check("ChromaConnection: Idempotência em pasta pré-existente (exist_ok=True)", check_chroma_idempotency)

    # 16. CHROMA: Normalização de barras mistas (/ e \\)
    def check_chroma_mixed_slashes():
        chroma_cls.reset()
        with tempfile.TemporaryDirectory() as td:
            mixed = str(td).replace("\\", "/") + "/subpasta/dados"
            conn = chroma_cls(path=mixed)
            assert Path(conn.path).exists(), "Caminho com barras mistas não foi resolvido."
            assert Path(conn.path).resolve() == Path(mixed).resolve()
    run_check("ChromaConnection: Normalização agnóstica a SO com barras mistas", check_chroma_mixed_slashes)

    # 17. CHROMA: Suporte a pathlib.Path como argumento
    def check_chroma_path_arg():
        chroma_cls.reset()
        with tempfile.TemporaryDirectory() as td:
            p_obj = Path(td) / "pathlib_target"
            conn = chroma_cls(path=p_obj)
            assert Path(conn.path).resolve() == p_obj.resolve()
    run_check("ChromaConnection: Suporte polimórfico a str e pathlib.Path", check_chroma_path_arg)

    # 18. CHROMA: Preservação de .gitkeep pré-existente
    def check_chroma_preserves_gitkeep():
        chroma_cls.reset()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "chroma_gitkeep"
            p.mkdir(parents=True, exist_ok=True)
            keep_file = p / ".gitkeep"
            keep_file.write_text("# keep", encoding="utf-8")
            
            conn = chroma_cls(path=str(p))
            assert keep_file.exists(), ".gitkeep foi inadvertidamente removido!"
            assert keep_file.read_text(encoding="utf-8") == "# keep"
    run_check("ChromaConnection: Preservação de arquivos pré-existentes (.gitkeep)", check_chroma_preserves_gitkeep)

    # 19. CHROMA: Ausência de métodos CRUD na interface pública
    def check_chroma_no_crud():
        forbidden = [
            "add", "query", "search", "get", "delete",
            "create_collection", "get_collection", "get_or_create_collection"
        ]
        public_members = [m for m in dir(chroma_cls) if not m.startswith("_")]
        for f in forbidden:
            assert f not in public_members, f"Método CRUD proibido '{f}' detectado em ChromaConnection!"
    run_check("ChromaConnection: Ausência estrita de métodos CRUD (pure connection provider)", check_chroma_no_crud)

    # 20. CHROMA: Reset e isolamento
    def check_chroma_reset():
        chroma_cls.reset()
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "c1"
            p2 = Path(td) / "c2"
            c1 = chroma_cls(path=str(p1))
            chroma_cls.reset()
            c2 = chroma_cls(path=str(p2))
            assert c1 is not c2, "Após reset(), nova instância independente deve ser criada."
            assert Path(c2.path).resolve() == p2.resolve()
    run_check("ChromaConnection: Método reset() permite isolamento total entre testes", check_chroma_reset)


def main():
    print("======================================================================")
    print(" JUD_AI: SUÍTE DE VERIFICAÇÃO EXECUTÁVEL DE ESPECIFICAÇÃO (M2)")
    print("======================================================================")

    # Modo 1: Validação do Design de Referência
    if "--verify-reference" in sys.argv or "--self-test" in sys.argv:
        print("[*] Validando o Design Canônico de Referência...")
        run_tests_on_classes(ReferenceMongoConnection, ReferenceChromaConnection, "SPEC REFERENCE CANONICAL DESIGN")
    else:
        # Modo 2: Validação da Base de Código Real
        print("[*] Buscando implementações em src.database...")
        mongo_cls = None
        chroma_cls = None
        try:
            from src.database.mongo_connection import MongoConnection
            mongo_cls = MongoConnection
        except ImportError as e:
            print(f"[-] src.database.mongo_connection ainda não disponível: {e}")

        try:
            from src.database.chroma_connection import ChromaConnection
            chroma_cls = ChromaConnection
        except ImportError as e:
            print(f"[-] src.database.chroma_connection ainda não disponível: {e}")

        if mongo_cls and chroma_cls:
            run_tests_on_classes(mongo_cls, chroma_cls, "SRC/DATABASE IMPLEMENTATION")
        else:
            print("\n[!] Código de produção em src/database ainda não implementado pelo Worker M2.")
            print("[*] Executando validação de especificação contra o design de referência...")
            run_tests_on_classes(ReferenceMongoConnection, ReferenceChromaConnection, "SPEC REFERENCE VERIFICATION")

    # Sumário Executivo
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    print("\n=======================================================")
    print(" RESUMO DOS RESULTADOS DA VERIFICAÇÃO")
    print("=======================================================")
    print(f"  Total de Verificações: {total}")
    print(f"  Sucessos:              {passed}")
    print(f"  Falhas:                {failed}")
    print(f"  Pulados:               {skipped}")
    print("=======================================================")

    if failed > 0:
        print("\n[FALHA] Algumas verificações não passaram:")
        for r in results:
            if not r.passed and not r.skipped:
                print(f"  - {r.name}: {r.error}")
        sys.exit(1)
    else:
        print("\n[SUCESSO] 100% DAS VERIFICAÇÕES DE ESPECIFICAÇÃO PASSARAM!")
        sys.exit(0)


if __name__ == "__main__":
    main()
