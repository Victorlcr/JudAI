# JudAI — Plataforma de RAG Jurídico Híbrido

Plataforma inteligente de **Retrieval-Augmented Generation (RAG) Híbrido** especializada na legislação brasileira, com foco no **Código Civil (Lei nº 10.406/2002)**. 

O projeto compara e integra duas abordagens fundamentais de inteligência artificial aplicada ao Direito:
1. **Modelo Moderno (`BERTimbau + ChromaDB + mT0`)**: Recuperação semântica densa baseada em embeddings neurais (`neuralmind/bert-base-portuguese-cased`), indexação vetorial no ChromaDB e geração explicativa em linguagem simples com `bigscience/mt0-base`, equipada com filtro de abstenção calibrado para consultas fora do escopo jurídico.
2. **Modelo Clássico (`TF-IDF + Rede Neural MLP`)**: Classificador neural Supervisionado em PyTorch alimentado por vetorizador esparso TF-IDF (com até 5.000 termos jurídicos e geração de variações sintéticas), oferecendo inferência ultra rápida em milissegundos e compatibilidade com buscas léxicas (**BM25**).

---

## 🏛️ Arquitetura do Sistema

```text
JudAI/
├── data/
│   ├── dataset/                  # Datasets versionados (pares_bert_inicial.jsonl, avaliacao_inicial.jsonl)
│   ├── chromadb_local/           # Banco vetorial persistente do ChromaDB (2.017 vetores 768d)
│   └── models/
│       ├── tfidf_mlp/            # modelo_classico.pt, vectorizer.pkl, label_encoder.pkl, metadata.json
│       └── bert_juridico/        # threshold.json (calibração do limiar de abstenção)
├── notebooks/
│   ├── 01_transformer_bertimbau_mt0.ipynb   # Notebook adaptado para consumo via MongoConnection
│   └── TFIDF_MLP.ipynb                      # Notebook clássico adaptado para consumo via MongoConnection
├── src/
│   ├── database/
│   │   ├── mongo_connection.py   # Conexão Singleton thread-safe com MongoDB (coleção 'artigos')
│   │   └── chroma_connection.py  # Conexão Singleton thread-safe com ChromaDB local
│   ├── scraper/
│   │   ├── ingestao_lei.py       # Parser semântico de HTMLs compilados do Planalto
│   │   └── carregar_mongo.py     # Crawler e populador de leis no MongoDB
│   ├── models/
│   │   ├── tfidf_mlp_search.py   # Motor clássico TF-IDF + MLP (PyTorch)
│   │   ├── bm25_search.py        # Wrapper/delegador compatível com busca léxica BM25
│   │   ├── bert_search.py        # Motor moderno BERTimbau + ChromaDB + gerador mT0
│   │   └── train_all.py          # CLI unificado de treino, indexação e validação
│   └── api/
│       ├── main.py               # API REST FastAPI, lifespan de modelos e rotas /search/*
│       └── templates/            # Template HTML da interface web responsiva (GET /)
├── tests/                        # Suíte de testes automatizados e empíricos
│   ├── test_api.py               # Testes de integração da API FastAPI e interface web
│   └── test_adversarial_*.py     # Testes empíricos e de estresse dos modelos
├── docker-compose.yml            # Infraestrutura de banco de dados MongoDB
├── requirements.txt              # Dependências do projeto
└── README.md                     # Documentação de execução e referência
```

---

## 🖥️ As 3 Visões da Interface Web (`GET /`)

A aplicação disponibiliza na rota raiz `http://localhost:8000/` uma interface web moderna, responsiva e de alta densidade informativa (Legal Tech design system):

1. **⚖️ Comparação Lado a Lado (Visão Principal)**:
   - Permite submeter qualquer dúvida jurídica em linguagem natural ou selecionar consultas canônicas pré-definidas.
   - Exibe em duas colunas sincronizadas as respostas, os artigos recuperados no MongoDB, os scores de similaridade/probabilidade e os tempos de execução em milissegundos de ambos os modelos.
   - Apresenta banner de resumo com indicador de concordância Top-1 e diferencial de latência.
2. **🧠 Modelo Moderno (`BERTimbau + mT0`)**:
   - Focado na busca semântica densa no ChromaDB e na síntese explicativa em português claro pelo modelo Seq2Seq `mT0`.
   - Exibe a resposta sintetizada em destaque ("Hero card"), badge de similaridade e dispositivos legais citados expansíveis.
   - Em caso de pergunta fora de escopo, sinaliza visualmente a **abstenção** e exibe a justificativa canônica de recusa.
3. **⚡ Modelo Clássico (`TF-IDF + MLP`)**:
   - Consulta dedicada ao classificador neural clássico em PyTorch.
   - Exibe os Top-K artigos previstos, barras de probabilidade softmax (0% a 100%), citações oficiais e texto normativo integral.

---

## ⚙️ Pré-requisitos

- **Python 3.10+** (recomendado Python 3.10 ou 3.11)
- **Docker** e **Docker Compose** (para execução local do container MongoDB)
- **Git**

---

## 🚀 1. Configuração do Ambiente e Instalação

Clone o repositório e configure o ambiente virtual:

```bash
git clone git@github.com:Victorlcr/JundAI.git
cd JundAI
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
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

## 🗄️ 2. Variáveis de Ambiente e Banco de Dados (MongoDB)

Copie o modelo de variáveis de ambiente:

- **Linux / macOS:** `cp .env.example .env`
- **Windows (PowerShell):** `Copy-Item .env.example .env`

Configuração padrão no `.env`:
```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=rag_juridico
CHROMA_DB_PATH=./data/chromadb_local
```

Inicie o container MongoDB via Docker Compose:

```bash
docker compose up -d
```

Verifique se o container está ativo:

```bash
docker compose ps
```

---

## 📦 3. Ingestão de Leis e Treinamento Unificado

### Ingestão do Código Civil no MongoDB
Popule a coleção `artigos` do MongoDB com os dispositivos do Código Civil (`cc2002`):

```bash
python -m src.scraper.carregar_mongo --escopo codigos
```

### Treinamento e Indexação Unificada dos Modelos
Execute o comando CLI único que treina o classificador neural TF-IDF + MLP, calcula e indexa os embeddings BERTimbau no ChromaDB e calibra o limiar de abstenção:

```bash
python -m src.models.train_all
```

Ao término, os artefatos estarão gravados em `data/models/tfidf_mlp/`, `data/models/bert_juridico/` e `data/chromadb_local/`.

---

## 🌐 4. Inicialização da API e Acesso à Interface Web

Inicie o servidor de aplicação Uvicorn:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Como Acessar no Navegador:
- **Interface Web Integrada (3 Visões):** [http://localhost:8000/](http://localhost:8000/)
- **Documentação Interativa Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Especificação OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 📡 5. Referência de Endpoints e Exemplos cURL

### 1. `GET /health`
Verifica a integridade operacional da API.
```bash
curl -X GET http://localhost:8000/health
```
**Resposta (200 OK):**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "models_loaded": true
}
```

---

### 2. `GET /models/status`
Retorna métricas de validação, status e contagem de artigos indexados em ambos os modelos.
```bash
curl -X GET http://localhost:8000/models/status
```
**Resposta (200 OK):**
```json
{
  "status": "ready",
  "classico": {
    "status": "ready",
    "artigos_indexados": 2017,
    "tamanho_vocabulario": 5000,
    "num_classes": 2017,
    "val_acc": 0.8333,
    "device": "cpu"
  },
  "moderno": {
    "status": "ready",
    "artigos_indexados": 2017,
    "limiar": 0.70,
    "collection_name": "cc_bert-juridico",
    "bert_model": "neuralmind/bert-base-portuguese-cased",
    "mt0_model": "bigscience/mt0-base",
    "device": "cpu"
  },
  "timestamp": "2026-11-14T20:45:00.000000+00:00"
}
```

---

### 3. `POST /search/tfidf` (Busca Clássica TF-IDF + MLP)
Executa a busca clássica com a rede neural supervisionada.
```bash
curl -X POST http://localhost:8000/search/tfidf \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
    "top_k": 3
  }'
```
**Resposta (200 OK):**
```json
{
  "model": "tfidf_mlp",
  "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
  "results": [
    {
      "artigo_id": "cc2002:art5",
      "citacao": "Código Civil, art. 5º",
      "texto": "A menoridade cessa aos dezoito anos completos, quando a pessoa fica habilitada à prática de todos os atos da vida civil.",
      "score": 0.9854
    }
  ],
  "execution_time_ms": 14.2
}
```

---

### 4. `POST /search/bm25` (Alias Clássico Retrocompatível)
```bash
curl -X POST http://localhost:8000/search/bm25 \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
    "top_k": 3
  }'
```

---

### 5. `POST /search/bert` (Busca Semântica Moderna - Pergunta In-Domain)
Recupera artigos no ChromaDB e sintetiza resposta em linguagem simples via mT0.
```bash
curl -X POST http://localhost:8000/search/bert \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
    "top_k": 3
  }'
```
**Resposta (200 OK):**
```json
{
  "model": "bert_mt0",
  "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
  "resposta_gerada": "A capacidade civil plena é atingida aos 18 anos completos (Código Civil, art. 5º).",
  "abstenção": false,
  "abstencao": false,
  "results": [
    {
      "artigo_id": "cc2002:art5",
      "citacao": "Código Civil, art. 5º",
      "texto": "A menoridade cessa aos dezoito anos completos...",
      "similarity_score": 0.8921
    }
  ],
  "execution_time_ms": 1420.5
}
```

---

### 6. `POST /search/bert` (Teste de Abstenção - Fora de Escopo)
```bash
curl -X POST http://localhost:8000/search/bert \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Receita de bolo de fubá com goiabada",
    "top_k": 3
  }'
```
**Resposta (200 OK com Abstenção Ativada):**
```json
{
  "model": "bert_mt0",
  "query": "Receita de bolo de fubá com goiabada",
  "resposta_gerada": "Não encontrei informação suficiente no Código Civil para responder a essa pergunta.",
  "abstenção": true,
  "abstencao": true,
  "results": [
    {
      "artigo_id": "cc2002:art...",
      "similarity_score": 0.5213
    }
  ],
  "execution_time_ms": 185.3
}
```

---

### 7. `POST /search/compare` (Comparação Lado a Lado)
Compara ambos os modelos simultaneamente para a mesma pergunta.
```bash
curl -X POST http://localhost:8000/search/compare \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
    "top_k": 3
  }'
```
**Resposta (200 OK):**
```json
{
  "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
  "classico": {
    "model": "tfidf_mlp",
    "results": [{"artigo_id": "cc2002:art5", "score": 0.9854}],
    "execution_time_ms": 14.2
  },
  "moderno": {
    "model": "bert_mt0",
    "resposta_gerada": "A capacidade civil plena é atingida aos 18 anos completos (Código Civil, art. 5º).",
    "abstenção": false,
    "results": [{"artigo_id": "cc2002:art5", "similarity_score": 0.8921}],
    "execution_time_ms": 1420.5
  },
  "comparacao": {
    "fastest_model": "classico",
    "latency_diff_ms": 1406.3,
    "top1_concordam": true,
    "top1_artigo_classico": "cc2002:art5",
    "top1_artigo_moderno": "cc2002:art5"
  }
}
```

---

## 🧪 6. Testes Automatizados

A suíte de testes pode ser executada tanto via `pytest` quanto diretamente via `unittest` da biblioteca padrão do Python:

### Execução via unittest (Padrão)
```bash
python -m unittest tests/test_api.py -v
```

### Execução via pytest
```bash
pytest tests/test_api.py -v
```

### Execução de toda a suíte de testes do projeto
```bash
python -m unittest discover tests -v
```
