"""
Módulo de Conexão Singleton com ChromaDB - JudAI
=================================================
Fornece acesso thread-safe centralizado ao cliente persistente do ChromaDB
(chromadb.PersistentClient), garantindo a criação de diretórios de forma
agnóstica a sistema operacional (Windows/Linux) e isolamento estrito
de responsabilidades (sem métodos CRUD de busca ou inserção).
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import chromadb
from chromadb.api import ClientAPI


class ChromaConnection:
    """
    Singleton responsável pelo gerenciamento da conexão com o ChromaDB local persistente.

    Lê a configuração CHROMA_DB_PATH das variáveis de ambiente ou do arquivo .env via python-dotenv.
    Cria a pasta persistente e diretórios-pai caso não existam.
    Não contém lógica de inserção ou busca vetorial.
    """

    _instance: ChromaConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, path: str | Path | None = None) -> ChromaConnection:
        """
        Garante a criação de uma única instância (Singleton) protegida por lock (Thread-Safe).
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str | Path | None = None) -> None:
        """
        Inicializa o caminho e diretórios na primeira chamada.
        Nas chamadas subsequentes, evita re-inicialização graças à flag _initialized e ao lock.
        """
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            load_dotenv()

            # Resolução com precedência: argumento do construtor > variável de ambiente > fallback default
            # Trata casos de string vazia ou apenas espaços via validação estrita
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

            # Validação defensiva caso o caminho seja um arquivo regular pré-existente
            if self._path.exists() and not self._path.is_dir():
                raise ValueError(
                    f"O caminho configurado para persistência do ChromaDB '{self._path}' já existe e não é um diretório."
                )

            # Criação automática da pasta e pastas-pai (recursivo e idempotente)
            # Preserva arquivos existentes como .gitkeep
            self._path.mkdir(parents=True, exist_ok=True)

            # Inicialização lazy do cliente para evitar bloqueio antecipado de arquivos no SO
            self._client: ClientAPI | None = None
            self._initialized: bool = True

    @property
    def client(self) -> ClientAPI:
        """Retorna a instância compartilhada do chromadb.PersistentClient com inicialização lazy thread-safe."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = chromadb.PersistentClient(path=str(self._path))
        return self._client

    @property
    def path(self) -> Path:
        """Retorna o caminho pathlib.Path absoluto resolvido da pasta de persistência."""
        return self._path

    def get_client(self) -> ClientAPI:
        """Método utilitário para obter o PersistentClient."""
        return self.client

    @classmethod
    def reset(cls) -> None:
        """
        Reseta a instância Singleton permitindo nova inicialização em testes unitários.
        Thread-safe através do lock de classe.
        """
        with cls._lock:
            if cls._instance is not None:
                if getattr(cls._instance, "_client", None) is not None:
                    if hasattr(cls._instance._client, "close"):
                        try:
                            cls._instance._client.close()
                        except Exception:
                            pass
                cls._instance = None
