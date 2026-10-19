# Relatório Técnico: Especificação dos Arquivos de Configuração e Armadilhas Técnicas (Milestone 1)

**Data**: 2026-10-18  
**Agente**: Explorer 2 (Milestone 1 — Arquivos de Configuração: Git, Docker, Env, Requirements)  
**Status**: Concluído / Pronto para Implementação  
**Escopo**: `.gitignore`, `.gitattributes`, `docker-compose.yml`, `requirements.txt`, `.env.example`

---

## 1. Resumo Executivo

O Milestone 1 estabelece as fundações operacionais, de governança de versão e de infraestrutura em contêiner para o projeto JudAI. Este relatório especifica de forma canônica, exata e auditável o conteúdo de cada um dos cinco arquivos de configuração centrais, analisa formalmente as armadilhas de engenharia identificadas (com ênfase na mecânica de globbing do Git para preservação de `.gitkeep` e na normalização de finais de linha multiplataforma) e fornece o guia definitivo para o agente implementador (Worker M1).

Todos os cinco arquivos foram formulados em conformidade estrita com:
- `ORIGINAL_REQUEST.md` (§R1)
- `orchestrator_1/PROJECT.md` (Features 2, 3, 4, 5, 6)
- Evidências empíricas de testes de isolamento executados no Git e interpretador Python 3.11.

---

## 2. Especificação Canônica e Conteúdo Exato dos Arquivos

### 2.1 `.gitignore`
- **Caminho absoluto**: `e:\Programacao\JudAI\.gitignore`
- **Finalidade**: Impedir o vazamento de segredos (`.env`), artefatos temporários/bytecode do Python (`__pycache__/`, `.pytest_cache/`), ambientes virtuais (`venv/`, `.venv/`) e dados gerados em tempo de execução (`data/`), garantindo a preservação exclusiva dos arquivos marcadores `.gitkeep`.

```gitignore
# Ambientes virtuais
venv/
.venv/
env/

# Bytecode e cache do Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/

# Variáveis de ambiente sensíveis e segredos
.env

# Diretório de dados (ignora todos os arquivos gerados, preservando subpastas e .gitkeep)
data/*
!data/**/
!data/**/.gitkeep
data/**/*
!data/**/
!data/**/.gitkeep

# Logs e arquivos de sistema operacional
*.log
.DS_Store
Thumbs.db
```

---

### 2.2 `.gitattributes`
- **Caminho absoluto**: `e:\Programacao\JudAI\.gitattributes`
- **Finalidade**: Forçar que todos os arquivos textuais sejam gravados e extraídos com quebras de linha padrão Unix (LF — `\n`), eliminando conflitos de checkout entre desenvolvedores Windows (CRLF — `\r\n`) e ambientes Linux/Docker.

```gitattributes
* text=auto eol=lf
```

---

### 2.3 `docker-compose.yml`
- **Caminho absoluto**: `e:\Programacao\JudAI\docker-compose.yml`
- **Finalidade**: Prover o container do banco de dados oficial MongoDB persistente para ambiente de desenvolvimento local, desacoplado do sistema de arquivos NTFS nativo através de volume nomeado.

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

---

### 2.4 `requirements.txt`
- **Caminho absoluto**: `e:\Programacao\JudAI\requirements.txt`
- **Finalidade**: Declarar as 12 bibliotecas fundamentais do JudAI sem fixação rígida de versões (sem pin), conforme exigência contratual de R1.

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

---

### 2.5 `.env.example`
- **Caminho absoluto**: `e:\Programacao\JudAI\.env.example`
- **Finalidade**: Servir de modelo (template) versionado no Git para as variáveis de ambiente necessárias à conexão com MongoDB e inicialização do ChromaDB local.

```env
# Conexao com MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=rag_juridico

# Persistencia local do ChromaDB
CHROMA_DB_PATH=./data/chromadb_local
```

---

## 3. Análise Detalhada de Armadilhas Técnicas e Mitigações

### 3.1 Armadilha 1: A Mecânica de Globbing do Git com `data/*` e `.gitkeep`

#### A Natureza do Problema
O requisito estipula:
> ".gitignore ignora venv/ (e .venv/), data/ inteira (usar data/* com exceção de !data/**/.gitkeep para que as pastas existam após clone), .env, __pycache__/."

Na especificação interna do Git, aplica-se a seguinte regra inviolável:
> *"It is not possible to re-include a file if a parent directory of that file is excluded. Git doesn't list excluded directories for performance reasons, so any patterns on contained files have no effect, no matter where they are defined."*

Testamos empiricamente três cenários em ambiente isolado:

1. **Cenário Ingênuo (`data/*` seguido apenas de `!data/**/.gitkeep`)**:
   - `data/*` casa com o diretório `data/raw/` e com `data/chromadb_local/`.
   - O Git exclui os diretórios pai.
   - O Git **não desce** dentro de `data/raw/` para checar `!data/**/.gitkeep`.
   - **Resultado verificado**: `git add .` ignora completamente `data/raw/.gitkeep` e `data/chromadb_local/.gitkeep`. Nenhuma pasta de dados seria versionada.
2. **Cenário Parcial (`data/*`, `!data/**/`, `!data/**/.gitkeep`)**:
   - A regra `!data/**/` re-inclui diretórios, permitindo que o Git desça em `data/raw/`.
   - Porém, a regra `data/*` possui profundidade de apenas 1 nível (filhos imediatos de `data/`).
   - Ela **não casa** com arquivos dentro de subpastas como `data/raw/artigo_10406.html` ou `data/chromadb_local/chroma.sqlite3`.
   - **Resultado verificado**: Arquivos de dados brutos e bancos SQLite locais aparecem como untracked prontos para commit, causando vazamento de dados no repositório.
3. **Cenário Robusto Validado**:
   ```gitignore
   data/*
   !data/**/
   !data/**/.gitkeep
   data/**/*
   !data/**/
   !data/**/.gitkeep
   ```
   - `data/*` ignora arquivos na raiz de `data/`.
   - `!data/**/` re-inclui todos os subdiretórios em qualquer nível.
   - `data/**/*` ignora recursivamente todos os arquivos sob qualquer subdiretório de `data/`.
   - `!data/**/.gitkeep` re-inclui com precedência todos os arquivos `.gitkeep` em qualquer nível de profundidade.
   - **Resultado verificado no teste isolado**:
     ```text
     STAGED FILES:
     A  .gitignore
     A  data/chromadb_local/.gitkeep
     A  data/raw/.gitkeep
     ```
     Nenhum arquivo de dados (`test.html`, `chroma.sqlite3`) foi adicionado.

#### Mitigação para o Worker
- Utilizar a regra completa descrita na Seção 2.1.
- No momento do commit inicial (M5), adicionar explicitamente:
  `git add data/raw/.gitkeep data/chromadb_local/.gitkeep notebooks/.gitkeep`
  para garantir a inclusão determinística no índice.

---

### 3.2 Armadilha 2: Normalização de Finais de Linha CRLF vs LF (`.gitattributes`)

#### A Natureza do Problema
- Em ambientes Windows (como a máquina de desenvolvimento atual), ferramentas e editores de texto frequentemente criam arquivos com quebras de linha Windows `CRLF` (`\r\n`).
- Em contêineres Docker (executando Debian/Alpine Linux) ou quando desenvolvedores Linux clonam o projeto:
  - Scripts com CRLF falham com erros crípticos do tipo `\r: command not found`.
  - Parsers sensíveis a whitespace e quebra de linha podem se comportar de forma imprevisível.
  - Commits geram "diffs fantasmas" onde o Git relata modificações em 100% das linhas do arquivo apenas pela conversão de `\r\n` para `\n`.

#### Mitigação
- O arquivo `.gitattributes` contendo `* text=auto eol=lf` garante que:
  1. O Git detecta automaticamente arquivos de texto vs binários (`text=auto`).
  2. Todas as quebras de linha são convertidas e armazenadas no repositório como `LF` (`eol=lf`).
  3. No checkout em qualquer máquina, as quebras são preservadas como `LF`.
- Ao executar `git add .` no Windows, o aviso `warning: in the working copy of '...', CRLF will be replaced by LF` é normal e confirma que o `.gitattributes` está aplicando a normalização corretamente.

---

### 3.3 Armadilha 3: Indentação, Tipagem e Volumes no `docker-compose.yml`

#### A Natureza do Problema
1. **Espaços vs Tabs**: O formato YAML proíbe terminantemente tabulações (`\t`). Um único TAB introduzido por um editor causa falha fatal no parser `docker compose config` (`yaml: line X: found character that cannot start any token`).
2. **Tipagem de portas**: A sintaxe `27017:27017` sem aspas pode ser interpretada por parsers YAML legados como número em base 60 (sexagesimal). O formato oficial do Compose Specification exige que mapeamentos de porta sejam representados como strings: `"27017:27017"`.
3. **Volume nomeado sem declaração de topo**: Se um serviço mapeia `mongo_data:/data/db`, mas a chave raiz `volumes:` não declarar `mongo_data:`, o Compose falha com: `service mongodb has volume mongo_data:/data/db which is not defined in the top-level volumes`.
4. **WiredTiger e Bind-Mounts no Windows**: Se for utilizado bind mount local (ex: `./data/mongo:/data/db`) em sistemas Windows rodando Docker Desktop com WSL2/Hyper-V, o motor de armazenamento WiredTiger do MongoDB frequentemente falha ao tentar aplicar locks `fcntl()` sobre partições NTFS compartilhadas. O uso de **volume nomeado** (`mongo_data:/data/db`) isola o armazenamento dentro do filesystem ext4 da VM do Docker, garantindo 100% de estabilidade e integridade dos dados.

#### Mitigação
- Utilizar indentação rigorosa de 2 espaços.
- Utilizar `"27017:27017"` com aspas duplas.
- Incluir a seção `volumes:\n  mongo_data:` no final do arquivo.

---

### 3.4 Armadilha 4: Dependências Leves vs Pesadas no `requirements.txt`

#### A Natureza do Problema
O arquivo `requirements.txt` consolida todas as dependências do ecossistema do JudAI. Contudo:
- `sentence-transformers` instala dependências gigantescas (PyTorch, bibliotecas CUDA, Hugging Face transformers), pesando mais de 2 GB.
- `rank_bm25` depende de NumPy.
- O Critério de Aceitação 2 explicita:
  > *"Com dependências leves instaladas (fastapi, uvicorn, pydantic, pymongo, chromadb, python-dotenv, beautifulsoup4, lxml, requests), uvicorn src.api.main:app sobe e /health, /search/bm25, /search/bert respondem 200 (POST com {"query":"x"})."*

Se os módulos de backend (`src/models/` ou `src/api/main.py`) importarem `sentence_transformers` ou `rank_bm25` no escopo global (nível de módulo), a API não iniciará em máquinas onde apenas as dependências leves foram instaladas, quebrando o critério de aceitação.

#### Mitigação
- O `requirements.txt` deve conter rigorosamente as 12 bibliotecas sem pin de versão.
- Documentamos formalmente a diretriz de arquitetura para os Milestones M3 e M4: `src/models/bm25_search.py` e `src/models/bert_search.py` não devem executar imports pesados em nível de módulo nesta fase de infraestrutura.

---

### 3.5 Armadilha 5: Variáveis de Ambiente e Paths no `.env.example`

#### A Natureza do Problema
1. **Comportamento de quotes**: Em arquivos `.env`, a presença de aspas desnecessárias pode ser interpretada literalmente por algumas versões de bibliotecas ou parsers (`MONGO_URI="mongodb://localhost:27017"` lendo a string com as aspas incluídas).
2. **Caminhos relativos e separadores de SO**: `CHROMA_DB_PATH=./data/chromadb_local` utiliza `./` e `/`. Em Windows, se a aplicação concatenar caminhos via strings simples, pode gerar strings inválidas como `.\data\chromadb_local/chroma.sqlite3`.

#### Mitigação
- Definir valores sem aspas no `.env.example`.
- Garantir que a camada de conexão com ChromaDB (M2) utilize `pathlib.Path` para resolução absoluta agnóstica de sistema operacional.

---

## 4. Matriz de Rastreabilidade

| Arquivo de Configuração | Requisito de Origem | Critério de Aceite | Validação Prevista |
|---|---|---|---|
| `.gitignore` | ORIGINAL_REQUEST §R1 | git status limpo; data/ e .env ignorados, .gitkeep versionados | `git status --porcelain` |
| `.gitattributes` | ORIGINAL_REQUEST §R1 | README e caminhos sem separadores de SO; compatibilidade Windows e Linux | Inspeção de atributos do Git (`git check-attr`) |
| `docker-compose.yml` | ORIGINAL_REQUEST §R1 | `docker compose config` valida sem erros | Validação YAML / Compose config |
| `requirements.txt` | ORIGINAL_REQUEST §R1 | Dependências leves sobem API e endpoints respondem 200 | Leitura e contagem de 12 pacotes sem pin |
| `.env.example` | ORIGINAL_REQUEST §R1 | Classes Singleton leem MONGO_URI, MONGO_DB_NAME, CHROMA_DB_PATH | Verificação de chaves e testes de conexão M2 |

---

## 5. Estratégia de Implementação para o Worker M1

Recomendamos que o Worker execute a criação dos arquivos de configuração na seguinte ordem:

1. **Passo 1: Criar `.gitignore`**
   - Criar `e:\Programacao\JudAI\.gitignore` com o conteúdo canônico da Seção 2.1.
2. **Passo 2: Criar `.gitattributes`**
   - Criar `e:\Programacao\JudAI\.gitattributes` com `* text=auto eol=lf`.
3. **Passo 3: Criar `docker-compose.yml`**
   - Criar `e:\Programacao\JudAI\docker-compose.yml` com indentação exata de 2 espaços e volume nomeado.
4. **Passo 4: Criar `requirements.txt`**
   - Criar `e:\Programacao\JudAI\requirements.txt` com a lista exata das 12 dependências sem pinos de versão.
5. **Passo 5: Criar `.env.example`**
   - Criar `e:\Programacao\JudAI\.env.example` com as variáveis requeridas e sem aspas nos valores.

---

## 6. Métodos de Verificação Independente

Para verificar a integridade da implementação dos arquivos de configuração:

1. **Verificação de dependências (`requirements.txt`)**:
   ```powershell
   python -c "
   lines = [line.strip() for line in open('requirements.txt') if line.strip() and not line.startswith('#')]
   expected = ['fastapi', 'uvicorn[standard]', 'pydantic', 'pymongo', 'chromadb', 'rank_bm25', 'sentence-transformers', 'nltk', 'python-dotenv', 'beautifulsoup4', 'lxml', 'requests']
   assert lines == expected, f'Diferenca: {lines} vs {expected}'
   print('requirements.txt: 12 dependencias exatas validadas!')
   "
   ```

2. **Verificação do `.env.example`**:
   ```powershell
   python -c "
   env_content = open('.env.example').read()
   for key in ['MONGO_URI', 'MONGO_DB_NAME', 'CHROMA_DB_PATH']:
       assert key in env_content, f'Chave ausente: {key}'
   print('.env.example: Chaves validadas!')
   "
   ```

3. **Verificação sintática do `docker-compose.yml`**:
   - Verificar estrutura: presença das chaves `services`, `mongodb`, `image`, `ports`, `volumes`, e volume nomeado `mongo_data`.
   - Se o Docker estiver presente no PATH:
     ```powershell
     docker compose config
     ```

4. **Verificação do `.gitattributes` e `.gitignore`**:
   ```powershell
   python -c "
   attr = open('.gitattributes').read().strip()
   assert '* text=auto eol=lf' in attr, 'gitattributes invalido'
   ign = open('.gitignore').read()
   for item in ['venv/', '.venv/', '__pycache__/', '.env', 'data/*']:
       assert item in ign, f'Regra ausente: {item}'
   print('.gitignore e .gitattributes validados!')
   "
   ```
