# Project: JudAI

## Architecture
JudAI é uma plataforma de RAG Híbrido Jurídico projetada para busca e recuperação de dispositivos legais brasileiros (ex: Código Civil).
A arquitetura base de infraestrutura compõe-se de:
1. **Infraestrutura e Contêineres**: MongoDB oficial em Docker Compose com persistência via volume nomeado; ChromaDB local persistente em `./data/chromadb_local`.
2. **Camada de Dados e Scraper**: `src/scraper/` contendo parser de legislação do Planalto (`ingestao_lei.py`) e runner de carga no MongoDB (`carregar_mongo.py`).
3. **Camada de Persistência (Database)**: `src/database/` com classes Singleton `MongoConnection` e `ChromaConnection` carregando configurações via `.env`.
4. **Camada de Modelos e Recuperação (Models)**: `src/models/` com placeholders estruturais `bm25_search.py` e `bert_search.py` (zero lógica de ML na infraestrutura base).
5. **Camada de Apresentação e API (API)**: `src/api/` com FastAPI (`main.py`), validação Pydantic (`QueryRequest`), health check e endpoints mockados de busca.
6. **Governança, Controle de Versão e Documentação**: `.gitignore`, `.gitattributes` (LF normalizado), `.env.example`, `requirements.txt`, `README.md` bilíngue para SOs (PowerShell e Bash) e repositório Git local (branch `main`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Estrutura de Diretórios e .gitkeep | Criação de data/raw/.gitkeep, data/chromadb_local/.gitkeep, notebooks/.gitkeep e todos os pacotes sob src/ | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Configuração .gitignore | Regras para venv/, .venv/, data/* com exceção de !data/**/.gitkeep, .env, __pycache__/ | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Normalização .gitattributes | Linhas LF universais via `* text=auto eol=lf` para Windows e Linux | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Orquestração Docker Compose | `docker-compose.yml` com serviço `mongodb` (imagem `mongo:latest`, porta `27017:27017`, volume `mongo_data:/data/db`) | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Dependências requirements.txt | Lista exata de 12 dependências sem versão fixa (fastapi, uvicorn[standard], pydantic, pymongo, chromadb, rank_bm25, sentence-transformers, nltk, python-dotenv, beautifulsoup4, lxml, requests) | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Variáveis de Ambiente .env.example | Template com `MONGO_URI`, `MONGO_DB_NAME` e `CHROMA_DB_PATH` | M1 | ORIGINAL_REQUEST §R1 |
| 7 | Conexão Singleton MongoDB | `src/database/mongo_connection.py` com classe Singleton `MongoConnection`, sem CRUD, configurado por .env | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Conexão Singleton ChromaDB | `src/database/chroma_connection.py` com classe Singleton `ChromaConnection`, criação automática de pasta, sem CRUD, configurado por .env | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Scraper - Migração ingestao_lei | Mover `ingestao_lei.py` para `src/scraper/ingestao_lei.py` preservando lógica e docstrings | M3 | ORIGINAL_REQUEST §R2 |
| 10 | Scraper - Migração carregar_mongo | Mover `carregar_mongo.py` para `src/scraper/carregar_mongo.py` ajustando import para módulo e lendo .env com fallbacks | M3 | ORIGINAL_REQUEST §R2 |
| 11 | Placeholders de Modelos ML | `src/models/bm25_search.py` e `src/models/bert_search.py` com docstrings e zero lógica de ML | M3 | ORIGINAL_REQUEST §R2 |
| 12 | API FastAPI & Pydantic | `src/api/main.py` com instância FastAPI e modelo `QueryRequest(query: str)` | M4 | ORIGINAL_REQUEST §R2 |
| 13 | Endpoint GET /health | Rota de disponibilidade retornando HTTP 200 e status da API | M4 | ORIGINAL_REQUEST §R2 |
| 14 | Endpoints Mockados POST /search | Rotas `POST /search/bm25` e `POST /search/bert` retornando mock `{model, query, results: [], detail: "not implemented"}` com HTTP 200 | M4 | ORIGINAL_REQUEST §R2 |
| 15 | Documentação README.md | Instruções claras e concisas em português para Windows PowerShell e Linux/macOS | M5 | ORIGINAL_REQUEST §R3 |
| 16 | Inicialização Git & Commit Inicial | Inicializar repositório Git local na branch `main`, commit inicial atômico com status limpo, sem push | M5 | ORIGINAL_REQUEST §R3 |
| 17 | Testes E2E Tiers 1-4 | Suíte de testes automatizados E2E cobrindo 100% dos requisitos de aceitação | M5 | Acceptance Criteria |
| 18 | Adversarial Coverage Hardening (Tier 5) | Testes de robustez, edge cases, injeções, caracteres especiais e integridade de tipos | M5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Estrutura e Configuração Base | Árvore de diretórios, .gitkeep, .gitignore, .gitattributes, docker-compose.yml, requirements.txt, .env.example | none | DONE |
| M2 | Banco de Dados Singleton | `src/database/mongo_connection.py` e `src/database/chroma_connection.py` com Singleton, dotenv e criação de diretório | M1 | DONE |
| M3 | Scraper e Placeholders ML | Migração de `ingestao_lei.py` e `carregar_mongo.py` para `src/scraper/` e criação de `src/models/{bm25_search,bert_search}.py` | M1 | DONE |
| M4 | API FastAPI Boilerplate | `src/api/main.py` com FastAPI, `QueryRequest`, `/health`, `/search/bm25`, `/search/bert` e documentação Swagger | M1, M2, M3 | DONE |
| M5 | Final Milestone: E2E Tests, Git & Docs | Execução 100% testes E2E Tiers 1-4, Tier 5 Adversarial Hardening, `README.md`, `git init` e commit inicial limpo | M1, M2, M3, M4 | IN_PROGRESS |

## Interface Contracts

### Database: MongoConnection
- **Classe**: `src.database.mongo_connection.MongoConnection(uri: str | None = None, db_name: str | None = None)`
- **Padrão**: Singleton thread-safe (`c1 is c2`, `c1.client is c2.client`).
- **Propriedades**:
  - `client`: `pymongo.MongoClient[dict[str, Any]]`
  - `db`: `pymongo.database.Database[dict[str, Any]]`
  - `uri`: `str`
  - `db_name`: `str`
- **Configuração**: Lê `MONGO_URI` (default: `"mongodb://localhost:27017"`) e `MONGO_DB_NAME` (default: `"rag_juridico"`).
- **Restrição**: NENHUM método CRUD de inserção ou busca.

### Database: ChromaConnection
- **Classe**: `src.database.chroma_connection.ChromaConnection(path: str | Path | None = None)`
- **Padrão**: Singleton thread-safe (`c1 is c2`, `c1.client is c2.client`).
- **Propriedades**:
  - `client`: `chromadb.api.ClientAPI` (PersistentClient)
  - `path`: `pathlib.Path`
- **Configuração**: Lê `CHROMA_DB_PATH` (default: `"./data/chromadb_local"`). Cria a pasta e pais com `mkdir(parents=True, exist_ok=True)`.
- **Restrição**: NENHUM método CRUD de adição, consulta ou criação de coleções.

### Scraper: carregar_mongo & ingestao_lei
- **Localização**: `src/scraper/ingestao_lei.py` e `src/scraper/carregar_mongo.py`.
- **Invocação**: `python -m src.scraper.carregar_mongo [fonte]`
- **Import em carregar_mongo**: `from src.scraper import ingestao_lei as parser` (com fallback para `.`).
- **Configuração**: Lê `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` mantendo defaults originais.

### Models: Placeholders BM25 e BERT
- **Localização**: `src/models/bm25_search.py` e `src/models/bert_search.py`.
- **Restrição**: Zero código de ML ativo. Classes `BM25Search` e `BERTSearch` com métodos lançando `NotImplementedError` e docstrings detalhadas. Imports leves sem dependências pesadas em nível de módulo.

### API: FastAPI
- **Aplicação**: `src.api.main:app`
- **Modelo de Entrada**:
  ```python
  class QueryRequest(BaseModel):
      query: str
  ```
- **Rotas**:
  - `GET /health` -> 200 OK `{"status": "ok"}`
  - `POST /search/bm25` (Body: `QueryRequest`) -> 200 OK `{"model": "bm25", "query": request.query, "results": [], "detail": "not implemented"}`
  - `POST /search/bert` (Body: `QueryRequest`) -> 200 OK `{"model": "bert", "query": request.query, "results": [], "detail": "not implemented"}`

## Code Layout
```text
e:\Programacao\JudAI\
├── .env.example
├── .gitignore
├── .gitattributes
├── docker-compose.yml
├── requirements.txt
├── README.md
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── chromadb_local/
│       └── .gitkeep
├── notebooks/
│   └── .gitkeep
└── src/
    ├── __init__.py
    ├── scraper/
    │   ├── __init__.py
    │   ├── ingestao_lei.py
    │   └── carregar_mongo.py
    ├── database/
    │   ├── __init__.py
    │   ├── mongo_connection.py
    │   └── chroma_connection.py
    ├── models/
    │   ├── __init__.py
    │   ├── bm25_search.py
    │   └── bert_search.py
    └── api/
        ├── __init__.py
        └── main.py
```
