# Original User Request

## 2026-10-18T21:58:03Z

Criar a infraestrutura base (esqueleto, configuração, Docker, boilerplate FastAPI) do JudAI, um projeto RAG híbrido jurídico que será clonado e executado por colaboradores em Linux e Windows. NÃO implementar lógica de ML (BM25, BERT, T5). Responda em português.

Working directory: e:\Programacao\JudAI
Integrity mode: development

## Requirements

### R1. Estrutura e configuração
Árvore de diretórios: data/raw/.gitkeep, data/chromadb_local/.gitkeep, notebooks/.gitkeep, src/__init__.py, src/scraper/__init__.py, src/database/{__init__,mongo_connection,chroma_connection}.py, src/models/{__init__,bm25_search,bert_search}.py, src/api/{__init__,main}.py, .env.example, .gitignore, .gitattributes, docker-compose.yml, requirements.txt, README.md. .gitignore ignora venv/ (e .venv/), data/ inteira (usar data/* com exceção de !data/**/.gitkeep para que as pastas existam após clone), .env, __pycache__/. requirements.txt: fastapi, uvicorn[standard], pydantic, pymongo, chromadb, rank_bm25, sentence-transformers, nltk, python-dotenv, beautifulsoup4, lxml, requests (sem pin). docker-compose.yml: serviço mongodb com imagem mongo:latest, porta 27017:27017, volume nomeado persistente montado em /data/db. .env.example: MONGO_URI=mongodb://localhost:27017, MONGO_DB_NAME=rag_juridico, CHROMA_DB_PATH=./data/chromadb_local. .gitattributes: * text=auto eol=lf.

### R2. Código base
- src/api/main.py: FastAPI, Pydantic QueryRequest(query: str), GET /health retorna status da API, POST /search/bm25 e POST /search/bert com retorno mockado (ex.: {model, query, results: [], detail: not implemented}).
- mongo_connection.py e chroma_connection.py: classes Singleton (pymongo MongoClient; chromadb.PersistentClient) usando variáveis de ambiente via python-dotenv; criar a pasta do Chroma se não existir; sem lógica de inserção/busca.
- bm25_search.py e bert_search.py: apenas placeholders com docstring.
- Mover os scripts existentes e:\Programacao\JudAI\ingestao_lei.py e carregar_mongo.py para src/scraper/ (manter nomes e lógica do parser), ajustando o import em carregar_mongo.py para funcionar via `python -m src.scraper.carregar_mongo` e lendo MONGO_URI/MONGO_DB_NAME do .env (com os valores atuais como default). Preserve comentários/docstrings existentes.

### R3. README e Git
README.md breve em português: criar venv (Windows PowerShell e Linux/macOS), pip install -r requirements.txt, copiar .env.example para .env, docker compose up -d, iniciar com uvicorn src.api.main:app --reload (docs em /docs), uso do scraper. Rodar git init, branch main, commit inicial. NÃO fazer push (URL remota ainda não informada).

## Acceptance Criteria
- [ ] `docker compose config` valida sem erros.
- [ ] Com dependências leves instaladas (fastapi, uvicorn, pydantic, pymongo, chromadb, python-dotenv, beautifulsoup4, lxml, requests), uvicorn src.api.main:app sobe e /health, /search/bm25, /search/bert respondem 200 (POST com {"query":"x"}).
- [ ] Duas instanciações de cada classe de conexão retornam o mesmo objeto.
- [ ] Após o commit, git status limpo; data/ e .env ignorados, .gitkeep versionados.
- [ ] Nenhum código de ML além de placeholders; `python -c "import src.scraper.ingestao_lei"` funciona.
- [ ] README e caminhos sem separadores específicos de SO hardcoded; compatível com Windows e Linux.
