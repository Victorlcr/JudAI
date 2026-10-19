# Relatório de Levantamento: Infraestrutura, Configuração e Git (JudAI)

**Data**: 2026-10-18  
**Autor**: Explorer 2 (Survey Infra, Config & Git)  
**Escopo**: Levantamento e especificação completa de infraestrutura, arquivos de configuração, dependências, controle de versão e documentação para o projeto JudAI.

---

## 1. Visão Geral e Resumo Executivo

O JudAI é uma plataforma de RAG (Retrieval-Augmented Generation) híbrido voltada ao domínio jurídico brasileiro. O objetivo desta etapa de infraestrutura é prover o esqueleto base de código, configuração, persistência e governança de repositório para que desenvolvedores e pesquisadores em ambientes **Windows** e **Linux/macOS** possam clonar o repositório e executar a aplicação de forma uniforme e sem fricção.

Princípios fundamentais identificados:
- **Zero código de ML real nesta fase**: Módulos de busca (BM25, BERT) devem conter apenas placeholders mockados.
- **Portabilidade estrita multiplataforma**: Fim de linha normalizado em LF via `.gitattributes`, paths agnósticos a sistema operacional (`pathlib.Path`), instruções no README para PowerShell e Bash.
- **Persistência desacoplada**: MongoDB via container Docker oficial com volume nomeado; ChromaDB em diretório local ignorado pelo Git, mas com pastas estruturais preservadas via `.gitkeep`.
- **Git estritamente local**: Inicialização na branch `main`, commit inicial atômico e limpo, sem execução de `git push`.

---

## 2. Estrutura de Diretórios e Arquivos Requeridos

A árvore completa do projeto deve seguir rigorosamente a especificação do `ORIGINAL_REQUEST.md`:

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
    │   ├── ingestao_lei.py     (movido da raiz)
    │   └── carregar_mongo.py   (movido da raiz, imports e env ajustados)
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

### 2.1 Detalhamento de Diretórios e Arquivos `.gitkeep`
O Git não rastreia diretórios vazios. Para garantir que pastas de armazenamento de dados e notebooks existam imediatamente após o `git clone`, devem ser criados arquivos vazios `.gitkeep` em:
1. `data/raw/.gitkeep`: Diretório destinado ao download e armazenamento de arquivos brutos (HTMLs de leis, JSONs brutos).
2. `data/chromadb_local/.gitkeep`: Diretório onde o ChromaDB gravará seus arquivos persistentes locais (`chroma.sqlite3`, índices vetoriais).
3. `notebooks/.gitkeep`: Diretório reservado para notebooks de prototipação e análise exploratória.

### 2.2 Movimentação e Reorganização dos Scripts Existentes
Atualmente, encontram-se na raiz do projeto os arquivos:
- `ingestao_lei.py` (20.6 KB, 513 linhas): Parser de leis do Planalto.
- `carregar_mongo.py` (3.7 KB, 97 linhas): Script que orquestra a leitura e inserção no MongoDB.

**Regras de migração**:
1. Ambos devem ser movidos para `src/scraper/`.
2. Preservar a lógica do parser e todos os comentários e docstrings originais.
3. Em `carregar_mongo.py`:
   - O import `import ingestao_lei as parser` deve ser ajustado para suportar execução como módulo: `from src.scraper import ingestao_lei as parser` (ou import relativo `from . import ingestao_lei as parser` caso executado com `python -m src.scraper.carregar_mongo`).
   - Carregar variáveis `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` ou `os.getenv`, mantendo os valores originais (`"mongodb://localhost:27017"` e `"rag_juridico"`) como fallbacks padrão.

---

## 3. Especificação do Controle de Versão: `.gitignore`

### 3.1 Regras Requeridas
O `.gitignore` deve cobrir:
1. Ambientes virtuais: `venv/` e `.venv/`.
2. Cache e temporários do Python: `__pycache__/`, `*.py[cod]`, `*$py.class`.
3. Variáveis de ambiente sensíveis: `.env`.
4. Dados locais em `data/`: ignorar todo conteúdo gerado/armazenado, exceto os arquivos `.gitkeep`.

### 3.2 Análise Técnica Crítica do Comportamento Git com `data/*`
No Git, existe uma regra fundamental:
> *"It is not possible to re-include a file if a parent directory of that file is excluded."*

Se o `.gitignore` contiver estritamente:
```gitignore
data/*
!data/**/.gitkeep
```
O Git interpreta `data/*` como correspondendo a `data/raw/` e `data/chromadb_local/`. Como essas pastas foram excluídas, o Git **não desce** dentro de `data/raw/` para avaliar a regra `!data/**/.gitkeep`. Como resultado, `data/raw/.gitkeep` seria ignorado em `git status` e não seria versionado automaticamente.

### 3.3 Solução Validada e Testada
Para atender fielmente ao requisito e garantir que o Git entre nas pastas e rastreie os `.gitkeep` sem rastrear nenhum arquivo de dados (como `.html`, `.json`, `chroma.sqlite3`), o padrão comprovado em nossos testes é:

```gitignore
# Ambientes virtuais
venv/
.venv/
env/

# Cache Python
__pycache__/
*.py[cod]
*$py.class
*.so
.pytest_cache/

# Configurações e segredos
.env

# Diretório de dados (ignora todos os arquivos e pastas internas, exceto .gitkeep)
data/*
!data/**/
!data/**/.gitkeep
data/**/*
!data/**/
!data/**/.gitkeep

# Logs e arquivos do sistema operacional
*.log
.DS_Store
Thumbs.db
```

**Resultado testado e verificado**:
- Arquivos de dados como `data/raw/sample.json` e `data/chromadb_local/chroma.sqlite3` são ignorados.
- Arquivos `.gitkeep` em qualquer nível dentro de `data/` são identificados como untracked prontos para commit.
- Caso o implementador utilize `git add -f data/raw/.gitkeep data/chromadb_local/.gitkeep`, eles se tornam rastreados independentemente de variações no engine de globbing do Git.

---

## 4. Especificação de Normalização de Linhas: `.gitattributes`

### 4.1 Conteúdo Requerido
```gitattributes
* text=auto eol=lf
```

### 4.2 Justificativa Técnica
O projeto será clonado por colaboradores em ambientes mistos (**Windows**, **Linux**, **macOS**):
- Por padrão, o Git no Windows frequentemente converte finais de linha para CRLF (`\r\n`).
- Em contêineres Docker (Linux), scripts ou arquivos de configuração com CRLF geram erros silenciosos ou mensagens como `\r: command not found`.
- Diffs artificiais poluídos com alteração de quebras de linha em múltiplos commits.
- A diretiva `* text=auto eol=lf` força o Git a identificar automaticamente arquivos de texto e normalizá-los com quebra de linha LF (`\n`) no repositório e no checkout em todas as plataformas.

---

## 5. Especificação do `docker-compose.yml`

### 5.1 Requisitos do Serviço
- **Serviço**: `mongodb`
- **Imagem**: `mongo:latest`
- **Mapeamento de Portas**: `27017:27017`
- **Armazenamento**: Volume nomeado persistente montado em `/data/db`
- **Validação**: Deve passar no comando `docker compose config` sem erros sintáticos.

### 5.2 Conteúdo Recomendado do `docker-compose.yml`
```yaml
services:
  mongodb:
    image: mongo:latest
    container_name: judai-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

### 5.3 Notas de Arquitetura
1. O uso de **volume nomeado** (`mongo_data:/data/db`) em vez de bind-mount local no Windows evita problemas conhecidos de permissão do NTFS e incompatibilidade de locking do motor WiredTiger do MongoDB.
2. Não são configuradas credenciais de root por padrão para simplificar a execução em ambiente de desenvolvimento local, alinhando-se à URI `mongodb://localhost:27017` definida no `.env.example`.

---

## 6. Especificação do `.env.example`

### 6.1 Conteúdo Requerido
```env
# Conexão com MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=rag_juridico

# Persistência local do ChromaDB
CHROMA_DB_PATH=./data/chromadb_local
```

### 6.2 Uso no Código da Aplicação
- `src/database/mongo_connection.py`: Deve ler `MONGO_URI` (default: `"mongodb://localhost:27017"`) e `MONGO_DB_NAME` (default: `"rag_juridico"`).
- `src/database/chroma_connection.py`: Deve ler `CHROMA_DB_PATH` (default: `"./data/chromadb_local"`). Deve utilizar `pathlib.Path(caminho).mkdir(parents=True, exist_ok=True)` para criar a pasta se ela não existir.
- `src/scraper/carregar_mongo.py`: Deve ler `MONGO_URI` e `MONGO_DB_NAME` do `.env` mantendo os valores originais como fallback.

---

## 7. Especificação de Dependências: `requirements.txt`

### 7.1 Lista Completa e Exata (sem pin de versão)
Conforme especificação do `ORIGINAL_REQUEST.md`, o arquivo `requirements.txt` deve conter exatamente as seguintes 12 bibliotecas, sem fixação de versão (`==`):

```text
fastapi
uvicorn[standard]
pydantic
pymongo
chromadb
rank_bm25
sentence-transformers
nltk
python-dotenv
beautifulsoup4
lxml
requests
```

### 7.2 Análise e Categorização das Dependências

| Pacote | Categoria | Finalidade no JudAI | Impacto / Tamanho |
|---|---|---|---|
| `fastapi` | Web Framework | API REST e endpoints de busca e saúde | Leve |
| `uvicorn[standard]` | Servidor ASGI | Execução do servidor HTTP assíncrono | Leve |
| `pydantic` | Validação | Schemas de request e response | Leve |
| `pymongo` | Banco de Dados | Driver oficial do MongoDB | Leve |
| `chromadb` | Banco Vetorial | Cliente vetorial local persistente | Médio |
| `python-dotenv` | Configuração | Carga automática de variáveis do `.env` | Leve |
| `beautifulsoup4` | Web Scraping | Parser de HTML de legislações do Planalto | Leve |
| `lxml` | Web Scraping | Parser C de alta performance para BeautifulSoup | Leve |
| `requests` | HTTP Client | Requisições HTTP para download de leis | Leve |
| `rank_bm25` | ML / Busca Lexical | Algoritmo BM25 para busca por palavras-chave | Leve (depende de numpy) |
| `nltk` | NLP | Tokenização e stopwords em português | Médio (baixa dados extras) |
| `sentence-transformers`| ML / Vetorial | Embeddings neurais (BERT) para busca semântica | Pesado (PyTorch / CUDA) |

### 7.3 Consideração para Testes Rápidos e Ambientes Leves
Conforme critério de aceite:
> *"Com dependências leves instaladas (fastapi, uvicorn, pydantic, pymongo, chromadb, python-dotenv, beautifulsoup4, lxml, requests), uvicorn src.api.main:app sobe e /health, /search/bm25, /search/bert respondem 200"*

A API FastAPI não deve importar `sentence-transformers` ou `rank_bm25` em nível de módulo no startup enquanto esses recursos forem mockados. Isso permite que colaboradores subam a API rapidamente mesmo em máquinas sem GPU ou sem o PyTorch instalado.

---

## 8. Especificação do `README.md`

O `README.md` deve ser conciso, redigido em **português**, sem comandos específicos de apenas um sistema operacional e estruturado nas seguintes seções:

### 8.1 Seções Obrigatórias
1. **Título e Descrição do JudAI**: Contextualização do projeto (RAG híbrido lexical BM25 + neural BERT para documentos jurídicos).
2. **Pré-requisitos**:
   - Python 3.10+ (ou 3.11+)
   - Docker e Docker Compose (para o MongoDB)
3. **Instalação e Configuração Passo a Passo**:
   - **Passo 1: Clonar o repositório**
   - **Passo 2: Criar e ativar o ambiente virtual**
     - Windows PowerShell:
       ```powershell
       python -m venv venv
       .\venv\Scripts\Activate.ps1
       ```
       *(Nota para PowerShell: se houver restrição de scripts, executar `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*
     - Linux / macOS:
       ```bash
       python3 -m venv venv
       source venv/bin/activate
       ```
   - **Passo 3: Instalar as dependências**
     ```bash
     pip install -r requirements.txt
     ```
   - **Passo 4: Configurar variáveis de ambiente**
     - Windows PowerShell:
       ```powershell
       Copy-Item .env.example .env
       ```
     - Linux / macOS:
       ```bash
       cp .env.example .env
       ```
   - **Passo 5: Subir o banco de dados MongoDB**
     ```bash
     docker compose up -d
     ```
   - **Passo 6: Executar a API FastAPI**
     ```bash
     uvicorn src.api.main:app --reload
     ```
     - Endpoints disponíveis:
       - `http://localhost:8000/health` (Healthcheck)
       - `http://localhost:8000/docs` (Swagger UI interativo)
       - `http://localhost:8000/redoc` (ReDoc)
4. **Execução do Scraper Jurídico**:
   - Explicação de como rodar a ingestão da legislação:
     ```bash
     python -m src.scraper.carregar_mongo
     ```
     Ou com arquivo/URL específica:
     ```bash
     python -m src.scraper.carregar_mongo caminho/para/lei.html
     ```
5. **Estrutura do Projeto**: Breve descrição das pastas (`src/api`, `src/database`, `src/models`, `src/scraper`, `data/`, `notebooks/`).

---

## 9. Protocolo de Inicialização do Git

### 9.1 Sequência de Comandos
1. Inicializar o repositório com branch principal `main`:
   ```bash
   git init -b main
   ```
2. Assegurar que os arquivos de configuração do Git estão presentes:
   - `.gitignore`
   - `.gitattributes`
3. Criar a estrutura completa de pastas e arquivos `.gitkeep`.
4. Mover `ingestao_lei.py` e `carregar_mongo.py` para `src/scraper/`.
5. Adicionar todos os arquivos ao controle de versão:
   ```bash
   git add .
   ```
6. Verificar o status para garantir que `.env` e arquivos sob `data/` (exceto `.gitkeep`) não foram adicionados:
   ```bash
   git status
   ```
7. Criar o commit inicial:
   ```bash
   git commit -m "feat: initial commit - JudAI skeleton and infra setup"
   ```
8. **Restrição Crítica**: **NÃO EXECUTAR `git push`**. Nenhuma URL de repositório remoto foi informada ou configurada.

---

## 10. Matriz de Rastreabilidade e Critérios de Aceite

| Critério de Aceite | Requisito Relacionado | Método de Verificação |
|---|---|---|
| `docker compose config` valida sem erros | R1 (docker-compose.yml) | Execução do comando `docker compose config` em ambiente com Docker instalado ou validação por schema YAML. |
| Dependências instaladas e API responde 200 em `/health`, `/search/bm25`, `/search/bert` | R1, R2 | Testes unitários/integração via `pytest` e chamadas HTTP com `TestClient(app)`. |
| Singletons de MongoDB e ChromaDB retornam mesma instância | R2 (mongo_connection, chroma_connection) | Script de teste verificando `conn1 is conn2` para ambas as conexões. |
| `git status` limpo após commit; `data/` e `.env` ignorados, `.gitkeep` versionados | R1, R3 | `git status --porcelain` retorna vazio após commit; `git ls-files` lista `.gitkeep` mas não `.env` nem dados. |
| Zero lógica de ML além de placeholders; `python -c "import src.scraper.ingestao_lei"` funciona | R2 | Importação do módulo via Python sem erros de sintaxe ou dependência ausente. |
| Sem separadores de SO hardcoded (`\\` ou `/`); compatibilidade Windows e Linux | R1, R3 | Inspeção estática de código com `pathlib.Path` e `.gitattributes` ativo. |

---

## 11. Conclusão e Próximos Passos

A investigação detalhada de infraestrutura, configuração e controle de versão está concluída e validada. Todas as armadilhas comuns (especialmente a interação de `.gitignore` com `data/*` e a compatibilidade de quebras de linha com `.gitattributes`) foram identificadas, testadas e solucionadas.

O relatório serve como especificação direta para o Planner e para os agentes implementadores.
