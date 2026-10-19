"""
Módulo de Gerenciamento da Conexão com MongoDB (JudAI)
======================================================
Fornece a classe Singleton thread-safe `MongoConnection` para acesso
centralizado ao cliente PyMongo e ao banco de dados padrão.

Regras Arquiteturais:
- Padrão Singleton thread-safe com double-checked locking e flag _initialized.
- Leitura de MONGO_URI e MONGO_DB_NAME via python-dotenv e variáveis de ambiente.
- Defaults: MONGO_URI='mongodb://localhost:27017', MONGO_DB_NAME='rag_juridico'.
- Suporte a fallback seguro contra strings vazias em variáveis de ambiente.
- NENHUM método CRUD de manipulação, busca ou inserção de dados.
- Conexão lazy (sem ping bloqueante no construtor).
- Método de classe reset() para isolamento em testes unitários.
"""
from __future__ import annotations

import os
import threading
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database


class MongoConnection:
    """
    Singleton responsável pelo gerenciamento da conexão com o MongoDB.

    Lê as configurações de MONGO_URI e MONGO_DB_NAME das variáveis de ambiente
    ou do arquivo .env via python-dotenv. Não contém lógica de inserção ou busca.
    """

    _instance: MongoConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(
        cls,
        uri: str | None = None,
        db_name: str | None = None,
    ) -> MongoConnection:
        """
        Garante a criação de uma única instância na memória utilizando double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        uri: str | None = None,
        db_name: str | None = None,
    ) -> None:
        """
        Inicializa as propriedades de conexão uma única vez.

        Protegido contra re-execução em chamadas consecutivas ou concorrentes
        através da flag `_initialized` e do lock de classe.
        """
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            load_dotenv()

            # Avaliação com fallback para valores padrão contra None ou strings vazias
            self._uri: str = (
                uri
                or os.getenv("MONGO_URI")
                or "mongodb://localhost:27017"
            )
            self._db_name: str = (
                db_name
                or os.getenv("MONGO_DB_NAME")
                or "rag_juridico"
            )

            # PyMongo MongoClient utiliza conexão lazy por padrão
            self._client: MongoClient[dict[str, Any]] = MongoClient(self._uri)
            self._db: Database[dict[str, Any]] = self._client[self._db_name]
            self._initialized: bool = True

    @property
    def client(self) -> MongoClient[dict[str, Any]]:
        """Retorna a instância compartilhada do MongoClient."""
        return self._client

    @property
    def db(self) -> Database[dict[str, Any]]:
        """Retorna o banco de dados configurado."""
        return self._db

    @property
    def uri(self) -> str:
        """Retorna a URI de conexão configurada."""
        return self._uri

    @property
    def db_name(self) -> str:
        """Retorna o nome do banco de dados configurado."""
        return self._db_name

    def get_client(self) -> MongoClient[dict[str, Any]]:
        """Método utilitário para obter o MongoClient compartilhado."""
        return self.client

    def get_db(self) -> Database[dict[str, Any]]:
        """Método utilitário para obter o Database configurado."""
        return self.db

    def close(self) -> None:
        """Fecha com segurança a conexão do cliente PyMongo se estiver ativo."""
        if hasattr(self, "_client") and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    @classmethod
    def reset(cls) -> None:
        """
        Reseta a instância Singleton e fecha conexões ativas.

        Essencial para garantir o isolamento entre testes unitários.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None
