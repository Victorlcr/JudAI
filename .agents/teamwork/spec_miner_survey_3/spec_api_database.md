# Especificação Técnica Detalhada: Banco de Dados, Modelos e API FastAPI (JudAI)

**Documento**: `spec_api_database.md`  
**Autor**: `spec_miner_survey_3` (Specification Miner)  
**Data**: 2026-10-18  
**Status**: Concluído / Aprovado para Implementação  
**Escopo**: `src/database/mongo_connection.py`, `src/database/chroma_connection.py`, `src/models/bm25_search.py`, `src/models/bert_search.py`, `src/api/main.py`, Contratos de Interface e Critérios de Aceitação para Testes Unitários e E2E.

---

## 1. Visão Geral e Fontes Autoritativas

Este documento formaliza as especificações técnicas, contratos de interface, assinaturas de classes e funções, modelos de dados Pydantic, variáveis de ambiente, comportamentos Singleton e regras de validação para os módulos de banco de dados, modelos e API do JudAI.

### Fontes Autoritativas Consultadas
1. **`ORIGINAL_REQUEST.md`** (Requisitos R1, R2, R3 e Critérios de Aceitação).
2. **`carregar_mongo.py`** e **`ingestao_lei.py`** (Codebase existente, analisando convenções de nomes, strings de conexão e bibliotecas de acesso).
3. **PyMongo 4.x Specification** (`pymongo.MongoClient`, padrões de conexão preguiçosa / lazy connection e topologia).
4. **ChromaDB 0.4.x/0.5.x Specification** (`chromadb.PersistentClient`, resolução de diretórios locais e persistência de coleções).
5. **FastAPI & Pydantic v2 Specification** (`fastapi.FastAPI`, `pydantic.BaseModel`, `TestClient`, validação de requisições e respostas HTTP).
6. **Python `python-dotenv` & `threading` Standards** (Carregamento de `.env`, thread safety com double-checked locking no padrão Singleton).

---

## 2. Features Discovered (Tabela de Funcionalidades Mapeadas)

| # | Categoria | Feature | Descrição | Entradas (Inputs) | Saídas (Outputs) | Comportamento de Erro | Descoberto Via |
|---|---|---|---|---|---|---|---|
| 1 | Database (Mongo) | `MongoConnection` Singleton | Garante instância única do cliente MongoDB em toda a aplicação. | `uri: str | None`, `db_name: str | None` | Instância idêntica (`c1 is c2`) | Reutiliza instância sem reconectar | ORIGINAL_REQUEST.md R2 |
| 2 | Database (Mongo) | Carregamento de Configuração `.env` | Carrega `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` / `os.environ`. | Variáveis de ambiente ou fallback padrão | Valores configurados (`mongodb://localhost:27017`, `rag_juridico`) | Usa defaults se vazias/ausentes | ORIGINAL_REQUEST.md R1, R2 |
| 3 | Database (Mongo) | Acesso ao Cliente e Banco | Expõe o cliente PyMongo e o objeto de banco de dados selecionado. | N/A | `.client` (`MongoClient`), `.db` (`Database`) | Erro na primeira operação se host inacessível | ORIGINAL_REQUEST.md R2 |
| 4 | Database (Mongo) | Isolamento Semântico (Sem CRUD) | Classe estritamente restrita a conexão e instanciação; sem lógica de inserção ou busca. | N/A | N/A | Tentativa de invocar métodos de busca/inserção resulta em `AttributeError` | ORIGINAL_REQUEST.md R2 |
| 5 | Database (Mongo) | Teardown / Reset para Testes | Método de classe `reset()` para fechar conexões e limpar a instância singleton entre testes unitários. | N/A | `None` (fecha client e reseta `_instance`) | Idempotente se instância for `None` | Boas práticas de Testabilidade |
| 6 | Database (Chroma) | `ChromaConnection` Singleton | Garante instância única do cliente ChromaDB persistente. | `path: str | Path | None` | Instância idêntica (`c1 is c2`) | Reutiliza instância | ORIGINAL_REQUEST.md R2 |
| 7 | Database (Chroma) | Carregamento de `CHROMA_DB_PATH` | Lê `CHROMA_DB_PATH` do `.env` com fallback para `./data/chromadb_local`. | Variável de ambiente ou fallback | Caminho resolvido de forma agnóstica de SO | Usa default se ausente/vazio | ORIGINAL_REQUEST.md R1, R2 |
| 8 | Database (Chroma) | Criação Automática de Diretório | Cria automaticamente o diretório de persistência do ChromaDB e pais caso não existam. | Caminho do diretório | Pasta criada no disco (`exist_ok=True`) | Lança `PermissionError` se sem permissão | ORIGINAL_REQUEST.md R2 |
| 9 | Database (Chroma) | Acesso ao PersistentClient | Inicializa e expõe `chromadb.PersistentClient` via `.client`. | N/A | `.client` (`chromadb.PersistentClient`) | Erro de inicialização se caminho for arquivo existente | ORIGINAL_REQUEST.md R2 |
| 10 | Database (Chroma) | Isolamento Semântico (Sem CRUD) | Sem criação de coleções ou métodos de adição/busca de vetores. | N/A | N/A | Tentativa de invocar busca/inserção direta resulta em `AttributeError` | ORIGINAL_REQUEST.md R2 |
| 11 | Database (Chroma) | Teardown / Reset para Testes | Método de classe `reset()` para permitir novos testes unitários com caminhos isolados. | N/A | `None` | Idempotente | Boas práticas de Testabilidade |
| 12 | ML Models | Placeholder BM25 (`bm25_search.py`) | Módulo placeholder com docstring explicativa da futura recuperação esparsa BM25; zero lógica de ML. | `query: str`, `top_k: int` | Docstrings e assinaturas planejadas | Invocar métodos não implementados lança `NotImplementedError` | ORIGINAL_REQUEST.md R2 |
| 13 | ML Models | Placeholder BERT (`bert_search.py`) | Módulo placeholder com docstring explicativa da futura busca semântica densa; zero lógica de ML. | `query: str`, `top_k: int` | Docstrings e assinaturas planejadas | Invocar métodos não implementados lança `NotImplementedError` | ORIGINAL_REQUEST.md R2 |
| 14 | ML Models | Zero Dependências Pesadas no Import | O import dos placeholders é imediato e leve, sem download de modelos nem inicialização de tensores. | N/A | Import bem-sucedido | Não causa lentidão nem requer download de pesos | ORIGINAL_REQUEST.md R2, Critérios |
| 15 | API (FastAPI) | Aplicação `FastAPI` Central | Instância principal configurada para execução via Uvicorn. | N/A | `app = FastAPI(...)` | Falha de inicialização caso rota ou middleware inválido | ORIGINAL_REQUEST.md R1, R2 |
| 16 | API (FastAPI) | Modelo Pydantic `QueryRequest` | Validação de payload com campo `query: str`. | `{"query": "texto"}` | Objeto validado `QueryRequest` | Retorna `422 Unprocessable Entity` se inválido | ORIGINAL_REQUEST.md R2 |
| 17 | API (FastAPI) | Endpoint `GET /health` | Rota de verificação de disponibilidade da API. | N/A | Status 200 e `{"status": "ok"}` | 405 se requisitado via POST | ORIGINAL_REQUEST.md R2 |
| 18 | API (FastAPI) | Endpoint `POST /search/bm25` | Rota mockada para busca BM25. | JSON `{"query": str}` | Status 200 e `{model, query, results, detail}` | 422 se `query` ausente; 405 se GET | ORIGINAL_REQUEST.md R2 |
| 19 | API (FastAPI) | Endpoint `POST /search/bert` | Rota mockada para busca semântica BERT. | JSON `{"query": str}` | Status 200 e `{model, query, results, detail}` | 422 se `query` ausente; 405 se GET | ORIGINAL_REQUEST.md R2 |
| 20 | API (FastAPI) | Documentação Interativa `/docs` | OpenAPI / Swagger gerado automaticamente pelo FastAPI. | N/A | Página HTML do Swagger UI | 200 OK | ORIGINAL_REQUEST.md R3 |
| 21 | Scraper / Ingestão | Conexão Configurável do Scraper | Leitura de `MONGO_URI` e `MONGO_DB_NAME` via `.env` no script do scraper. | Arquivo `.env` ou variáveis de ambiente | Configuração injetada no MongoClient do scraper | Sys.exit amigável se MongoDB inacessível | ORIGINAL_REQUEST.md R2 |

---

## 3. Edge Cases Observados e Tratamento Especificado

| # | Componente / Feature | Entrada (Input) | Comportamento Esperado / Observado | Tratamento Especificado |
|---|---|---|---|---|
| 1 | `MongoConnection` | Múltiplas chamadas consecutivas `MongoConnection()` | Construtor `__init__` do Python é chamado a cada instanciação mesmo quando `__new__` retorna o mesmo objeto. | Proteger `__init__` com flag `self._initialized` e `threading.Lock` para não reabrir conexões de rede nem sobrescrever propriedades. |
| 2 | `MongoConnection` | `MONGO_URI=""` ou `MONGO_DB_NAME=""` (variável presente mas vazia no ambiente) | `os.getenv("MONGO_URI", "default")` retorna `""` e causa erro de conexão ao passar URI vazia. | Utilizar padrão seguro: `os.getenv("MONGO_URI") or "mongodb://localhost:27017"` e `os.getenv("MONGO_DB_NAME") or "rag_juridico"`. |
| 3 | `MongoConnection` | MongoDB offline durante a inicialização da API | Conexão não deve travar a inicialização do container ou da API. | PyMongo por padrão adota conexão lazy. A instanciação de `MongoConnection()` não executa `ping()` bloqueante no `__init__`, permitindo que a API suba mesmo que o Mongo inicie alguns segundos depois. |
| 4 | `ChromaConnection` | Pasta `./data/chromadb_local` já existente no clone/execução | Criação de diretório pode falhar com `FileExistsError` se não protegida. | Executar `Path(self.path).mkdir(parents=True, exist_ok=True)`. |
| 5 | `ChromaConnection` | Caminhos com barras mistas ou Windows (`data\chromadb_local` vs `data/chromadb_local`) | Erros de resolução relativa se não normalizado. | Usar `pathlib.Path(caminho).resolve()` ou `os.path.normpath(caminho)` e converter para string ao passar para `chromadb.PersistentClient(path=str(path))`. |
| 6 | `ChromaConnection` | `CHROMA_DB_PATH` apontando para um arquivo existente em vez de pasta | `mkdir` lança `FileExistsError` ou `NotADirectoryError`. | Verificar se o caminho existe e é arquivo (`if p.exists() and not p.is_dir(): raise ValueError(...)`) ou deixar lançar exceção descritiva de configuração. |
| 7 | `Pydantic QueryRequest` | Payload JSON `{}` (campo `query` ausente) | Falha de validação do Pydantic. | FastAPI intercepta e retorna HTTP 422 Unprocessable Entity com `loc: ["body", "query"]` e mensagem `Field required`. |
| 8 | `Pydantic QueryRequest` | Payload com tipo incorreto: `{"query": 12345}` ou `{"query": ["termo"]}` | Pydantic v2 valida rigorosamente strings. | FastAPI intercepta e retorna HTTP 422 Unprocessable Entity com `Input should be a valid string`. |
| 9 | `Pydantic QueryRequest` | Query com caracteres especiais da língua portuguesa e jurídicos: `{"query": "reparação civil c/c art. 186 do CC/2002 § 1º"}` | Caracteres acentuados, barras e símbolos de parágrafo. | O FastAPI decodifica UTF-8 nativamente; o retorno mockado deve preservar a string exata sem perda de acentuação (`\u00e7` ou string legível UTF-8). |
| 10 | `Pydantic QueryRequest` | Query vazia `{"query": ""}` ou apenas espaços `{"query": "   "}` | Requisição tecnicamente válida para string, mas semanticamente vazia. | Como o requisito estrito é `QueryRequest(query: str)`, aceita e retorna HTTP 200 com a string informada, mantendo máxima compatibilidade com os testes. |
| 11 | `FastAPI Endpoints` | Método HTTP incorreto (ex: `GET /search/bm25` ou `POST /health`) | Rota não mapeada para esse verbo. | FastAPI responde automaticamente HTTP 405 Method Not Allowed. |
| 12 | `FastAPI Endpoints` | Header `Content-Type` incorreto ou body inválido (não-JSON) | Parse JSON falha. | FastAPI retorna HTTP 422 Unprocessable Entity. |
| 13 | `ML Placeholders` | Import de `src.models.bm25_search` ou `src.models.bert_search` em ambiente sem Torch/GPU | Falha caso haja imports estáticos pesados no topo do arquivo. | Placeholders NÃO devem importar pacotes de ML no nível do módulo. O topo do arquivo conterá apenas docstrings e classes puras em Python. |

---

## 4. Contratos de Interface e Especificação de Código

### 4.1. `src/database/mongo_connection.py`

#### Responsabilidades
- Fornecer acesso único e centralizado ao cliente MongoDB (`pymongo.MongoClient`) e ao banco de dados padrão.
- Ler variáveis de ambiente `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` e `os.environ`.
- Implementar o padrão Singleton de forma thread-safe.
- Proibir terminantemente métodos de manipulação de dados (sem lógica de inserção ou busca).

#### Interface Pública
```python
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

    def __new__(cls, uri: str | None = None, db_name: str | None = None) -> MongoConnection:
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
            load_dotenv()
            self._uri: str = uri or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
            self._db_name: str = db_name or os.getenv("MONGO_DB_NAME") or "rag_juridico"
            self._client: MongoClient[dict[str, Any]] = MongoClient(self._uri)
            self._initialized: bool = True

    @property
    def client(self) -> MongoClient[dict[str, Any]]:
        """Retorna a instância compartilhada do MongoClient."""
        return self._client

    @property
    def db(self) -> Database[dict[str, Any]]:
        """Retorna o banco de dados configurado."""
        return self._client[self._db_name]

    @property
    def uri(self) -> str:
        """Retorna a URI de conexão configurada."""
        return self._uri

    @property
    def db_name(self) -> str:
        """Retorna o nome do banco de dados configurado."""
        return self._db_name

    def get_client(self) -> MongoClient[dict[str, Any]]:
        """Método utilitário para obter o MongoClient."""
        return self.client

    def get_db(self) -> Database[dict[str, Any]]:
        """Método utilitário para obter o banco de dados."""
        return self.db

    def close(self) -> None:
        """Fecha a conexão do cliente MongoDB."""
        if hasattr(self, "_client") and self._client:
            self._client.close()

    @classmethod
    def reset(cls) -> None:
        """
        Reseta a instância singleton e fecha conexões ativas.
        Essencial para isolamento em testes unitários.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None
```

---

### 4.2. `src/database/chroma_connection.py`

#### Responsabilidades
- Fornecer acesso único e centralizado ao cliente persistente do ChromaDB (`chromadb.PersistentClient`).
- Ler a variável de ambiente `CHROMA_DB_PATH` via `python-dotenv` e `os.environ`.
- Criar automaticamente a pasta do banco se ela não existir (`mkdir(parents=True, exist_ok=True)`).
- Implementar o padrão Singleton de forma thread-safe.
- Proibir terminantemente métodos de inserção, busca ou manipulação de coleções.

#### Interface Pública
```python
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
    
    Lê a configuração CHROMA_DB_PATH das variáveis de ambiente ou do arquivo .env.
    Cria a pasta persistente caso não exista. Não contém lógica de inserção ou busca.
    """
    _instance: ChromaConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, path: str | Path | None = None) -> ChromaConnection:
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
            load_dotenv()
            raw_path = path or os.getenv("CHROMA_DB_PATH") or "./data/chromadb_local"
            self._path: Path = Path(raw_path).resolve()
            # Garante a criação da pasta e de pastas intermediárias caso não existam
            self._path.mkdir(parents=True, exist_ok=True)
            self._client: ClientAPI = chromadb.PersistentClient(path=str(self._path))
            self._initialized: bool = True

    @property
    def client(self) -> ClientAPI:
        """Retorna a instância compartilhada do PersistentClient."""
        return self._client

    @property
    def path(self) -> Path:
        """Retorna o caminho resolvido no sistema de arquivos."""
        return self._path

    def get_client(self) -> ClientAPI:
        """Método utilitário para obter o PersistentClient."""
        return self.client

    @classmethod
    def reset(cls) -> None:
        """
        Reseta a instância singleton.
        Essencial para isolamento em testes unitários.
        """
        with cls._lock:
            cls._instance = None
```

---

### 4.3. `src/models/bm25_search.py`

#### Responsabilidades
- Servir como módulo de placeholder declarativo para busca léxica esparsa.
- Conter docstrings arquiteturais detalhando o papel futuro do algoritmo BM25 (via `rank_bm25`) no pipeline de RAG híbrido.
- Não carregar bibliotecas pesadas nem implementar lógica ativa neste estágio de esqueleto.

#### Interface Pública
```python
"""
Módulo de Busca Léxica Esparsa (BM25) - JudAI
==============================================
Este módulo é um PLACEHOLDER estrutural para o motor de busca léxica esparsa
baseado no algoritmo BM25 (Okapi / BM25Plus via biblioteca rank_bm25).

Papel no RAG Híbrido:
---------------------
Em marcos futuros, este componente será responsável por:
1. Tokenização e remoção de stopwords jurídicas em língua portuguesa.
2. Indexação de dispositivos de leis (artigos, parágrafos, incisos).
3. Recuperação preliminar dos top-K candidatos com base em correspondência exata
   e frequências de termos jurídicos.
4. Fusão de rankings (Reciprocal Rank Fusion - RRF) com a busca semântica densa (BERT).

ATENÇÃO: Nenhuma lógica de Machine Learning ou indexação ativa está implementada
nesta fase de infraestrutura base.
"""
from typing import Any

class BM25Search:
    """
    Placeholder para o motor de busca léxica BM25.
    
    A implementação detalhada será desenvolvida nos marcos de ML.
    """
    def __init__(self, corpus: list[dict[str, Any]] | None = None) -> None:
        """Inicializa o placeholder de busca BM25."""
        pass

    def fit(self, corpus: list[dict[str, Any]]) -> None:
        """
        Planejado: Indexa o corpus de legislação.
        
        Args:
            corpus: Lista de dicionários representando dispositivos ou artigos.
        """
        raise NotImplementedError("BM25 indexing is not yet implemented.")

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Planejado: Executa busca léxica por relevância.
        
        Args:
            query: Termo de pesquisa jurídica.
            top_k: Número máximo de resultados retornados.
            
        Returns:
            Lista de resultados ordenados por score BM25.
        """
        raise NotImplementedError("BM25 search is not yet implemented.")
```

---

### 4.4. `src/models/bert_search.py`

#### Responsabilidades
- Servir como módulo de placeholder declarativo para busca semântica densa baseada em embeddings neurais.
- Conter docstrings arquiteturais detalhando o papel futuro de modelos como `sentence-transformers` ou BERT jurídico no ChromaDB.
- Não carregar pesos de rede neural nem bibliotecas pesadas na importação.

#### Interface Pública
```python
"""
Módulo de Busca Semântica Densa (BERT / Embeddings) - JudAI
===========================================================
Este módulo é um PLACEHOLDER estrutural para o motor de busca semântica densa
baseado em embeddings de linguagem natural (ex.: Sentence-BERT ou modelos
especializados em direito brasileiro como BERTimbau / Juridical BERT).

Papel no RAG Híbrido:
---------------------
Em marcos futuros, este componente será responsável por:
1. Geração de representações vetoriais densas (embeddings) de consultas do usuário.
2. Consulta vetorial por similaridade de cosseno na base ChromaDB (PersistentClient).
3. Recuperação de dispositivos e artigos com equivalência semântica e contextual,
   mesmo quando os termos exatos diferem da redação legal.
4. Combinação de pontuação com o BM25 para alimentar a etapa de síntese/RAG.

ATENÇÃO: Nenhuma lógica de Machine Learning ou modelo neural está carregado
nesta fase de infraestrutura base.
"""
from typing import Any

class BERTSearch:
    """
    Placeholder para o motor de busca semântica densa BERT.
    
    A implementação detalhada será desenvolvida nos marcos de ML.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        """Inicializa o placeholder de busca semântica."""
        self.model_name = model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Planejado: Gera embeddings vetoriais a partir de textos.
        
        Args:
            texts: Lista de sentenças ou dispositivos a vetorizar.
        """
        raise NotImplementedError("BERT embedding generation is not yet implemented.")

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Planejado: Executa busca semântica vetorial no ChromaDB.
        
        Args:
            query: Pergunta ou consulta conceitual em linguagem natural.
            top_k: Número máximo de resultados retornados.
            
        Returns:
            Lista de resultados ordenados por similaridade de cosseno.
        """
        raise NotImplementedError("BERT semantic search is not yet implemented.")
```

---

### 4.5. `src/api/main.py`

#### Responsabilidades
- Criar e configurar a instância da aplicação `FastAPI`.
- Definir o modelo Pydantic `QueryRequest(query: str)`.
- Definir o modelo Pydantic `SearchResponse` (ou estrutura equivalente) para respostas estruturadas mockadas.
- Expor endpoint `GET /health` retornando status 200 e payload de saúde.
- Expor endpoints `POST /search/bm25` e `POST /search/bert` aceitando `QueryRequest` e retornando status 200 com mocks estruturados:
  `{"model": "bm25"|"bert", "query": request.query, "results": [], "detail": "not implemented"}`.
- Fornecer documentação OpenAPI automática em `/docs` e `/redoc`.

#### Interface Pública e Implementação
```python
from __future__ import annotations
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Esquemas Pydantic
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Modelo de entrada para consultas jurídicas."""
    query: str = Field(..., description="Termo ou pergunta jurídica para busca")

class SearchResponse(BaseModel):
    """Modelo estruturado de resposta para os endpoints de busca mockados."""
    model: str = Field(..., description="Nome do modelo de busca executado")
    query: str = Field(..., description="Consulta original enviada na requisição")
    results: list[dict[str, Any]] = Field(default_factory=list, description="Lista de resultados encontrados")
    detail: str = Field(default="not implemented", description="Status de implementação da funcionalidade")

# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="JudAI API",
    version="0.1.0",
    description="API de RAG Híbrido Jurídico para busca e recuperação de dispositivos legais.",
)

@app.get("/health", status_code=200)
def health_check() -> dict[str, str]:
    """
    Retorna o status de saúde e disponibilidade da API.
    """
    return {"status": "ok"}

@app.post("/search/bm25", status_code=200, response_model=SearchResponse)
def search_bm25(request: QueryRequest) -> SearchResponse:
    """
    Endpoint mockado de busca léxica via BM25.
    """
    return SearchResponse(
        model="bm25",
        query=request.query,
        results=[],
        detail="not implemented",
    )

@app.post("/search/bert", status_code=200, response_model=SearchResponse)
def search_bert(request: QueryRequest) -> SearchResponse:
    """
    Endpoint mockado de busca semântica via BERT.
    """
    return SearchResponse(
        model="bert",
        query=request.query,
        results=[],
        detail="not implemented",
    )
```

---

## 5. Matriz de Validações de Aceitação e Casos de Teste (Unit & E2E)

### 5.1. Testes Unitários de Conexão com Bancos de Dados

| Teste | Arquivo de Teste | Ação Executada | Asserções Esperadas |
|---|---|---|---|
| `test_mongo_singleton_identity` | `tests/unit/test_mongo_connection.py` | `c1 = MongoConnection()`, `c2 = MongoConnection()` | `assert c1 is c2`<br>`assert c1.client is c2.client`<br>`assert c1.db is c2.db` |
| `test_mongo_env_defaults` | `tests/unit/test_mongo_connection.py` | Instancia sem definir `.env` ou variáveis de ambiente | `assert c1.uri == "mongodb://localhost:27017"`<br>`assert c1.db_name == "rag_juridico"` |
| `test_mongo_custom_env` | `tests/unit/test_mongo_connection.py` | Reset singleton, define `MONGO_URI="mongodb://custom:27018"` e `MONGO_DB_NAME="custom_db"`, instancia `c1` | `assert c1.uri == "mongodb://custom:27018"`<br>`assert c1.db_name == "custom_db"` |
| `test_mongo_no_crud_methods` | `tests/unit/test_mongo_connection.py` | Inspeciona métodos públicos de `MongoConnection` | Não possui métodos `insert`, `insert_one`, `find`, `find_one`, `search`, `query`. |
| `test_chroma_singleton_identity` | `tests/unit/test_chroma_connection.py` | `c1 = ChromaConnection()`, `c2 = ChromaConnection()` | `assert c1 is c2`<br>`assert c1.client is c2.client` |
| `test_chroma_creates_directory` | `tests/unit/test_chroma_connection.py` | Reset singleton, define caminho temporário novo em `CHROMA_DB_PATH`, instancia `c1` | `assert os.path.isdir(c1.path)` é `True` |
| `test_chroma_cross_platform_path` | `tests/unit/test_chroma_connection.py` | Passa caminhos com barras normais ou invertidas | O caminho é resolvido via `Path` sem gerar erros de separador de SO. |
| `test_chroma_no_crud_methods` | `tests/unit/test_chroma_connection.py` | Inspeciona métodos públicos de `ChromaConnection` | Não possui métodos `add`, `query`, `create_collection`, `get_collection`. |

### 5.2. Testes dos Placeholders de Modelos de ML

| Teste | Arquivo de Teste | Ação Executada | Asserções Esperadas |
|---|---|---|---|
| `test_bm25_placeholder_import` | `tests/unit/test_model_placeholders.py` | `import src.models.bm25_search as bm25` | Import ocorre em < 100ms; não lança erro; classe `bm25.BM25Search` existe. |
| `test_bm25_docstring_present` | `tests/unit/test_model_placeholders.py` | Inspeciona docstring do módulo e da classe | Contém termos descritivos de BM25 e placeholder. |
| `test_bert_placeholder_import` | `tests/unit/test_model_placeholders.py` | `import src.models.bert_search as bert` | Import ocorre em < 100ms; não lança erro; classe `bert.BERTSearch` existe. |
| `test_bert_docstring_present` | `tests/unit/test_model_placeholders.py` | Inspeciona docstring do módulo e da classe | Contém termos descritivos de BERT/embeddings e placeholder. |
| `test_placeholder_methods_raise_not_implemented` | `tests/unit/test_model_placeholders.py` | Instancia classes e invoca métodos de busca/indexação | Dispara `pytest.raises(NotImplementedError)`. |

### 5.3. Testes de API e End-to-End (E2E)

Utilizando `fastapi.testclient.TestClient(app)`:

| Teste | Arquivo de Teste | Método HTTP & Rota | Payload da Requisição | Status Esperado | Asserções no Payload de Resposta |
|---|---|---|---|---|---|
| `test_get_health_ok` | `tests/api/test_api_endpoints.py` | `GET /health` | Nenhum | `200 OK` | `assert response.json() == {"status": "ok"}` |
| `test_post_search_bm25_ok` | `tests/api/test_api_endpoints.py` | `POST /search/bm25` | `{"query": "direito civil prescricao"}` | `200 OK` | `body = response.json()`<br>`assert body["model"] == "bm25"`<br>`assert body["query"] == "direito civil prescricao"`<br>`assert body["results"] == []`<br>`assert body["detail"] == "not implemented"` |
| `test_post_search_bert_ok` | `tests/api/test_api_endpoints.py` | `POST /search/bert` | `{"query": "reparacao por danos morais"}` | `200 OK` | `body = response.json()`<br>`assert body["model"] == "bert"`<br>`assert body["query"] == "reparacao por danos morais"`<br>`assert body["results"] == []`<br>`assert body["detail"] == "not implemented"` |
| `test_search_missing_query` | `tests/api/test_api_endpoints.py` | `POST /search/bm25` | `{}` | `422 Unprocessable Entity` | Campo de erro indica ausência de `query`. |
| `test_search_invalid_type` | `tests/api/test_api_endpoints.py` | `POST /search/bert` | `{"query": 12345}` | `422 Unprocessable Entity` | Campo de erro indica tipo inválido (esperado string). |
| `test_search_method_not_allowed` | `tests/api/test_api_endpoints.py` | `GET /search/bm25` | Nenhum | `405 Method Not Allowed` | Status 405 retornado pelo roteador FastAPI. |
| `test_health_post_not_allowed` | `tests/api/test_api_endpoints.py` | `POST /health` | `{}` | `405 Method Not Allowed` | Status 405 retornado pelo roteador FastAPI. |
| `test_search_accents_and_special_chars` | `tests/api/test_api_endpoints.py` | `POST /search/bm25` | `{"query": "usucapião especial urbana art. 1.240 § 1º"}` | `200 OK` | `body["query"] == "usucapião especial urbana art. 1.240 § 1º"`. |

---

## 6. Checklist de Aceitação para Implementação (Milestone Gate)

- [ ] Arquivo `src/database/mongo_connection.py` implementa `MongoConnection` com padrão Singleton (`c1 is c2` e `c1.client is c2.client`).
- [ ] Leitura segura de `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` com defaults `"mongodb://localhost:27017"` e `"rag_juridico"`.
- [ ] `MongoConnection` NÃO contém métodos de inserção, busca ou manipulação de coleções.
- [ ] Arquivo `src/database/chroma_connection.py` implementa `ChromaConnection` com padrão Singleton.
- [ ] Leitura segura de `CHROMA_DB_PATH` com default `"./data/chromadb_local"`, criando o diretório caso não exista.
- [ ] `ChromaConnection` NÃO contém métodos de inserção, busca ou criação de coleções.
- [ ] Arquivos `src/models/bm25_search.py` e `src/models/bert_search.py` possuem docstrings completas e classes com métodos que lançam `NotImplementedError`, sem carregar modelos ou bibliotecas pesadas de ML.
- [ ] Arquivo `src/api/main.py` implementa `QueryRequest(query: str)`, rota `GET /health` respondendo 200 `{"status": "ok"}`, e rotas `POST /search/bm25` e `POST /search/bert` respondendo 200 com o mock estruturado especificado.
- [ ] Execução de `uvicorn src.api.main:app` sobe a API e permite consumo via HTTP/docs.
- [ ] Total compatibilidade entre sistemas operacionais (Windows e Linux) sem caminhos hardcoded com barras invertidas estáticas.
