# JudAI — Infraestrutura Base de RAG Jurídico Híbrido

Repositório base do projeto **JudAI**, voltado para **Retrieval-Augmented Generation (RAG) híbrido** aplicado à legislação brasileira (Portal da Legislação do Planalto). O objetivo do projeto é comparar abordagens de recuperação léxica (**BM25**) e semântica densa (**BERT**) restritas estritamente aos documentos legislativos da base.

> **Nota:** Esta etapa contempla **exclusivamente a infraestrutura base** (esqueleto de diretórios, conexões Singleton com MongoDB e ChromaDB, scrapers de ingestão de leis e boilerplate da API FastAPI). A lógica dos modelos de Machine Learning será implementada nas próximas etapas.

---

## Estrutura do Projeto

```text
JudAI/
├── data/
│   ├── raw/
│   └── chromadb_local/
├── notebooks/
├── src/
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── ingestao_lei.py
│   │   └── carregar_mongo.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── mongo_connection.py
│   │   └── chroma_connection.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── bm25_search.py
│   │   └── bert_search.py
│   └── api/
│       ├── __init__.py
│       └── main.py
├── .env.example
├── .gitattributes
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Pré-requisitos

- **Python 3.10+**
- **Docker** e **Docker Compose** (para execução local do MongoDB)
- **Git**

---

## 1. Configuração do Ambiente Virtual e Dependências

Clone o repositório e acesse a pasta do projeto:

```bash
git clone git@github.com:Victorlcr/JundAI.git
cd JundAI
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

- **Linux / macOS:**
  ```bash
  cp .env.example .env
  ```
- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```

Valores padrão configurados no `.env`:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=rag_juridico
CHROMA_DB_PATH=./data/chromadb_local
```

---

## 3. Subindo o Banco de Dados (MongoDB via Docker)

Inicie o container do MongoDB em segundo plano:

```bash
docker compose up -d
```

Para verificar se o container está ativo na porta `27017`:

```bash
docker compose ps
```

---

## 4. Ingestão de Leis do Planalto (Crawler e Scraper)

Com o MongoDB em execução, o módulo `src.scraper.carregar_mongo` funciona como um **crawler automático** que varre as páginas de índice do Portal da Legislação do Planalto (Constituição, Códigos, Estatutos, Leis Complementares, Leis Delegadas e Leis Ordinárias por ano), segue automaticamente os links de *"Texto compilado"* e estrutura cada diploma nas coleções `leis`, `artigos` e `dispositivos`:

```bash
# Varre e baixa TODAS as leis dos quadros do Planalto (Constituição, Códigos, Estatutos, Complementares e Ordinárias)
python -m src.scraper.carregar_mongo

# Baixar apenas Constituição, Códigos e Estatutos principais (~38 diplomas fundamentais)
python -m src.scraper.carregar_mongo --escopo codigos

# Filtrar anos das Leis Ordinárias, limitar quantidade e pular leis já gravadas no banco
python -m src.scraper.carregar_mongo --anos 2020-2026 --limite 100 --pular-existentes

# Ou baixar uma única lei específica (URL do Planalto ou arquivo .html local)
python -m src.scraper.carregar_mongo https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm
```

---

## 5. Executando a API (FastAPI + Uvicorn)

Na raiz do projeto, inicie o servidor de desenvolvimento:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints Disponíveis

- **Documentação Interativa (Swagger UI):** `http://localhost:8000/docs`
- **`GET /health`**: Verifica o status operacional da API (`{"status": "ok"}`).
- **`POST /search/bm25`**: Endpoint mockado para busca léxica (`{"query": "sua consulta"}`).
- **`POST /search/bert`**: Endpoint mockado para busca semântica (`{"query": "sua consulta"}`).
