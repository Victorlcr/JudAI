"""
Configurações Globais e Fixtures do Pytest para JudAI.
======================================================
Este módulo provê fixtures de isolamento de ambiente (.env), limpeza de
Singletons (MongoConnection e ChromaConnection), criação de diretórios
temporários e clientes de teste para a API FastAPI.
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Generator, Any
from unittest.mock import MagicMock, patch

import pytest

# Adiciona a raiz do projeto ao sys.path para garantir imports relativos e absolutos
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Retorna o caminho absoluto da raiz do projeto."""
    return ROOT_DIR


@pytest.fixture
def clean_env() -> Generator[dict[str, str], None, None]:
    """
    Salva uma cópia das variáveis de ambiente antes do teste
    e restaura o estado original após a execução.
    """
    old_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Cria um diretório temporário isolado e garante sua remoção após o teste.
    """
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def reset_singletons() -> Generator[None, None, None]:
    """
    Reseta as instâncias Singleton de MongoConnection e ChromaConnection
    antes e depois do teste, garantindo isolamento total.
    """
    def _do_reset():
        # Reset MongoConnection se importável
        try:
            from src.database.mongo_connection import MongoConnection
            if hasattr(MongoConnection, "reset"):
                MongoConnection.reset()
            else:
                MongoConnection._instance = None
        except (ImportError, AttributeError):
            pass

        # Reset ChromaConnection se importável
        try:
            from src.database.chroma_connection import ChromaConnection
            if hasattr(ChromaConnection, "reset"):
                ChromaConnection.reset()
            else:
                ChromaConnection._instance = None
        except (ImportError, AttributeError):
            pass

    _do_reset()
    yield
    _do_reset()


@pytest.fixture
def mock_mongo():
    """
    Fixture que intercepta chamadas ao MongoClient para testes offline.
    """
    with patch("pymongo.MongoClient") as mock_client:
        mock_instance = MagicMock()
        mock_db = MagicMock()
        mock_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_instance
        yield mock_client


@pytest.fixture
def mock_chroma():
    """
    Fixture que intercepta chamadas ao PersistentClient do chromadb para testes offline.
    """
    with patch("chromadb.PersistentClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_client


@pytest.fixture
def api_client(clean_env, reset_singletons):
    """
    Retorna uma instância de TestClient para testar os endpoints da API FastAPI.
    """
    try:
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)
    except ImportError as e:
        pytest.skip(f"Módulos da API ainda não disponíveis: {e}")
