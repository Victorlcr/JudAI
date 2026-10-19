# Relatório de Levantamento do Codebase — JudAI

**Data**: 2026-10-18  
**Agente**: explorer_survey_1 (Survey Codebase & Scraper)  
**Status**: Concluído  

---

## 1. Visão Geral do Workspace

Uma inspeção minuciosa no diretório de trabalho `e:\Programacao\JudAI` revelou o seguinte estado inicial:

### Arquivos e Diretórios Existentes
| Caminho Relativo | Tipo | Tamanho | Linhas | Descrição |
|---|---|---|---|---|
| `carregar_mongo.py` | Arquivo | 3.769 bytes | 97 | Script runner para ingestão do Código Civil no MongoDB |
| `ingestao_lei.py` | Arquivo | 20.636 bytes | 513 | Parser de legislação compilada do Planalto e exportador Mongo/JSONL |
| `.agents/` | Diretório | - | - | Metadados e coordenação de agentes autônomos (`.agents/teamwork/`) |

### Ausências Relevantes (A serem criadas conforme R1, R2, R3)
- **Git**: Repositório Git inexistente (`fatal: not a git repository (or any of the parent directories): .git`). Não há `.git`, `.gitignore`, `.gitattributes`, branches ou commits.
- **Estrutura de Código Fonte**: Não existem os diretórios `src/`, `src/scraper/`, `src/database/`, `src/models/`, `src/api/` e seus respectivos `__init__.py`.
- **Estrutura de Dados e Cadernos**: Não existem `data/raw/`, `data/chromadb_local/`, `notebooks/` nem seus respectivos arquivos `.gitkeep`.
- **Configuração e Ambiente**: Não existem `.env`, `.env.example`, `docker-compose.yml`, `requirements.txt`, `README.md`.
- **Ambiente Virtual**: Não existe `venv/` ou `.venv/`.
- **Python no Ambiente**: Python 3.11.9 está instalado no sistema operacional, porém os pacotes específicos (`pymongo`, `beautifulsoup4`, `lxml`, `requests`, `python-dotenv`, `fastapi`, `uvicorn`, `chromadb`) ainda não estão instalados no interpretador global.

---

## 2. Análise Detalhada dos Scripts Existentes

### 2.1. `ingestao_lei.py` (513 linhas)

#### O que o script faz
Trata-se do motor principal de parsing estrutural de legislação compilada do Portal da Legislação do Planalto (HTML ou URL). Ele é capaz de:
1. Obter HTML bruto via HTTP GET (com timeout e User-Agent) ou ler arquivo local `.html`.
2. Lidar com codificação legada do Planalto (Windows-1252/cp1252 vs UTF-8) com detecção e aviso de perda de acentos (`` / `\ufffd`).
3. Parsear com BeautifulSoup (`lxml`) e classificar blocos textuais via expressões regulares robustas para:
   - Metadados: número/ano da lei e ementa.
   - Cabeçalhos hierárquicos: Livro, Título, Subtítulo, Capítulo, Seção, Subseção, Parte Geral/Especial.
   - Dispositivos: Artigos, Parágrafos (numerados e parágrafo único), Incisos e Alíneas.
   - Status de vigência: detecção de redação anterior (marcada com tags `<strike>`, `<s>`, `<del>` ou estilo CSS `line-through`) e revogações expressas `(Revogado pela Lei ...)`.
4. Construir três coleções relacionais/documentais:
   - **`leis`**: metadados da lei, hash SHA-256 do arquivo original, timestamp de coleta ISO UTC, contagens totais e flag de acentos preservados.
   - **`artigos`**: visão aninhada (artigo contendo parágrafos e incisos), com texto consolidado vigente (`texto_vigente`) e trilha de contexto hierárquico (`caminho`).
   - **`dispositivos`**: visão tabular e plana de cada dispositivo individual (artigo, parágrafo, inciso, alínea), contendo referências de árvore (`_id`, `lei_id`, `artigo_id`, `pai_id`, `tipo`, `status`, `vigente`, `ordem`).
5. Gerar relatório estatístico no console sobre contagem de nós, dispositivos por status, lacunas numéricas e integridade.
6. Gravar diretamente no MongoDB ou exportar em formato JSON Lines (`.jsonl`).

#### Imports Atuais
- No topo do arquivo:
  - `from __future__ import annotations`
  - `import argparse`
  - `import hashlib`
  - `import json`
  - `import re`
  - `import sys`
  - `from collections import defaultdict`
  - `from datetime import datetime, timezone`
  - `from pathlib import Path`
  - `from bs4 import BeautifulSoup`
- Imports lazy (sob demanda no corpo das funções):
  - Linha 53 (função `obter_bytes`): `import requests`
  - Linha 448 (função `salvar_mongo`): `from pymongo import ReplaceOne`
  - Linha 504 (função `main`): `from pymongo import MongoClient`

---

### 2.2. `carregar_mongo.py` (97 linhas)

#### O que o script faz
É um runner/script orquestrador focado na carga do Código Civil (`cc2002`, Lei nº 10.406/2002) no MongoDB local ou remoto.
Ele executa 4 passos na função principal `__main__`:
1. `carregar_documentos(fonte)`: invoca as funções do `ingestao_lei` para baixar/ler o HTML, decodificar, parsear e montar as 3 coleções.
2. `conectar()`: abre conexão com o MongoDB via `pymongo.MongoClient`, valida com `ping`, e retorna o database.
3. `inserir(db, colecoes)`: apaga versões anteriores da lei (`delete_many` filtrando por `lei_id`) nas 3 coleções, realiza inserção em lote (`insert_many(..., ordered=False)`) e cria índices no MongoDB.
4. `verificar(db)`: executa uma consulta de conferência buscando o Artigo 5º (`cc2002:art5`) e imprime o texto, citação e totais no banco.

#### Imports Atuais
- Linha 17: `import hashlib`
- Linha 18: `import sys`
- Linha 20: `from pymongo import MongoClient`
- Linha 21: `from pymongo.errors import ServerSelectionTimeoutError`
- Linha 23: `import ingestao_lei as parser` *(import direto local)*

#### Configurações Hardcoded Atuais
- Linha 26: `MONGO_URI = "mongodb://localhost:27017"`
- Linha 27: `NOME_BANCO = "rag_juridico"`
- Linha 28: `LEI_ID = "cc2002"`
- Linha 29: `LEI_NOME = "Código Civil"`
- Linha 30: `FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"`

---

## 3. Dependência e Conexão entre os Scripts

### Como `carregar_mongo.py` depende de `ingestao_lei.py`
Na linha 23 de `carregar_mongo.py`:
```python
import ingestao_lei as parser
```
O script `carregar_mongo.py` utiliza extensivamente os seguintes símbolos exportados por `ingestao_lei`:
- `parser.FFFD`: constante indicadora de caractere de substituição ``.
- `parser.obter_bytes(fonte)`: download HTTP ou leitura de arquivo local.
- `parser.decodificar(raw)`: decodificação de bytes para texto.
- `parser.parsear(html)`: extração de nós e estrutura da lei.
- `parser.montar_colecoes(lei_id, lei_nome, meta, artigos, origem, sha256, tem_acento_perdido)`: montagem das 3 coleções estruturadas.
- `parser.relatorio(colecoes, ignoradas, tem_acento_perdido, n_fffd)`: exibição de sumário estatístico.

### Como a Conexão ao MongoDB é Realizada
- **URI de conexão**: `mongodb://localhost:27017`
- **Nome do banco**: `rag_juridico`
- **Coleções manipuladas**:
  1. `leis`
  2. `artigos`
  3. `dispositivos`
- **Índices criados**:
  - Em `artigos`:
    - `[("lei_id", 1), ("numero", 1)]`
    - `"vigente"`
  - Em `dispositivos`:
    - `[("lei_id", 1), ("artigo_id", 1)]`
    - `[("tipo", 1), ("vigente", 1)]`

---

## 4. Requisitos de Ajuste para Migração (M3 / R2)

Para cumprir o requisito R2:
> *"Mover os scripts existentes e:\Programacao\JudAI\ingestao_lei.py e carregar_mongo.py para src/scraper/ (manter nomes e lógica do parser), ajustando o import em carregar_mongo.py para funcionar via `python -m src.scraper.carregar_mongo` e lendo MONGO_URI/MONGO_DB_NAME do .env (com os valores atuais como default). Preserve comentários/docstrings existentes."*

### 4.1. Movimentação de Arquivos
- Mover `e:\Programacao\JudAI\ingestao_lei.py` para `e:\Programacao\JudAI\src\scraper\ingestao_lei.py`.
- Mover `e:\Programacao\JudAI\carregar_mongo.py` para `e:\Programacao\JudAI\src\scraper\carregar_mongo.py`.
- Assegurar a presença de `src/__init__.py` e `src/scraper/__init__.py`.

### 4.2. Ajuste do Import em `src/scraper/carregar_mongo.py`
Substituir a linha 23:
```python
# ANTES:
import ingestao_lei as parser

# DEPOIS (Recomendado para compatibilidade plena com python -m src.scraper.carregar_mongo):
try:
    from src.scraper import ingestao_lei as parser
except ImportError:
    from . import ingestao_lei as parser
```
Dessa forma, funciona tanto via `python -m src.scraper.carregar_mongo` (executado da raiz do projeto) quanto caso importado relativamente ou como script.

### 4.3. Integração com Variáveis de Ambiente (`.env`)
Adicionar a leitura via `python-dotenv`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------- CONFIGURAÇÃO ---------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
NOME_BANCO = os.getenv("MONGO_DB_NAME", "rag_juridico")
LEI_ID = "cc2002"
LEI_NOME = "Código Civil"
FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
# ---------------------------------------------------------------------------
```
*Atenção aos nomes*: O `.env.example` exigido no R1 define `MONGO_URI` e `MONGO_DB_NAME`. Em `carregar_mongo.py`, a variável interna era `NOME_BANCO`. O ajuste para `os.getenv("MONGO_DB_NAME", "rag_juridico")` alinha perfeitamente a chave do ambiente mantendo o fallback padrão.

### 4.4. Preservação de Comentários e Docstrings
Todos os comentários de cabeçalho, explicações de regex, parâmetros e funções devem ser preservados integralmente. O docstring de uso de `carregar_mongo.py` pode ser complementado com a invocação canônica:
```
python -m src.scraper.carregar_mongo
```

### 4.5. Verificação de Import em `ingestao_lei.py`
O Critério de Aceitação exige:
```bash
python -c "import src.scraper.ingestao_lei"
```
Como `ingestao_lei.py` não realiza imports circulares e seus imports de topo são da biblioteca padrão mais `BeautifulSoup`, uma vez instaladas as dependências leves (`beautifulsoup4`, `lxml`), o comando funcionará sem nenhum erro.

---

## 5. Mapeamento de Dependências e Docker

### Dependências necessárias para os scripts de scraper:
- `beautifulsoup4`
- `lxml`
- `pymongo`
- `requests`
- `python-dotenv`

Todas constam expressamente na especificação de `requirements.txt` do R1:
`fastapi, uvicorn[standard], pydantic, pymongo, chromadb, rank_bm25, sentence-transformers, nltk, python-dotenv, beautifulsoup4, lxml, requests`.

### MongoDB no Docker (`docker-compose.yml`):
- O serviço `mongodb` na porta `27017:27017` com volume persistente para `/data/db` atende diretamente aos requisitos de conexão dos dois scripts de ingestão (`mongodb://localhost:27017`).

---

## 6. Conclusão do Levantamento

1. O workspace está limpo e no estado pré-esqueleto.
2. Os scripts `ingestao_lei.py` e `carregar_mongo.py` estão intactos, funcionais e totalmente mapeados.
3. As alterações necessárias para `src/scraper/` são cirúrgicas, bem delimitadas e não violam nenhuma lógica de negócio ou parser existente.
4. O repositório Git precisará ser inicializado na raiz com branch `main`.
