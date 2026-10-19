# Especificação de Validação e Critérios de Aceitação — Milestone 1 (JudAI)

**Data**: 2026-10-18  
**Agente**: Spec Miner (Milestone 1 — Infraestrutura e Governança Base)  
**Status**: Aprovado para Validação / Autorizativo  
**Alvo**: Worker M1, Reviewers M1 e Challengers M1  
**Fontes Autoritativas**: `ORIGINAL_REQUEST.md` (§R1, §Acceptance Criteria) e `orchestrator_1/PROJECT.md` (Features 1 a 6)

---

## 1. Visão Geral e Arquitetura de Validação

O Milestone 1 (M1) estabelece as bases estruturais, operacionais e de versionamento do projeto **JudAI** (plataforma RAG híbrido jurídico). O objetivo deste documento é definir a matriz completa de especificações mineradas, casos de borda empíricos observados e comandos exatos de teste a serem executados por todos os agentes envolvidos no ciclo de vida (Worker para auto-validação, Reviewers para auditoria estática e Challengers para verificação adversarial).

A estratégia de testes de validação cobre 5 pilares fundamentais:
1. **Orquestração Docker Compose**: Sintaxe, conformidade com a especificação Compose Spec e persistência via volume nomeado para MongoDB.
2. **Topologia de Diretórios e Pacotes**: Criação da árvore de dados, notebooks e pacotes Python sob `src/` com integridade de `__init__.py` e `.gitkeep`.
3. **Governança Git e Normalização**: Regras rigorosas de `.gitignore` (com des-exclusão segura de `.gitkeep`) e `.gitattributes` para terminação de linha LF multiplataforma.
4. **Catálogo de Dependências**: Conjunto estrito de 12 dependências em `requirements.txt` sem fixação de versão (*sem pin*).
5. **Configuração de Ambiente**: Arquivo template `.env.example` com chaves e defaults canônicos para MongoDB e ChromaDB.

---

## 2. Features Discovered

| # | Categoria | Feature | Descrição | Entradas (Inputs) | Saídas Esperadas (Outputs) | Comportamento de Erro (Error Behavior) | Descoberto Via |
|---|-----------|---------|-----------|-------------------|----------------------------|---------------------------------------|----------------|
| 1 | Docker | Orquestração do MongoDB | Serviço `mongodb` oficial com persistência desacoplada em volume nomeado e mapeamento de porta `27017:27017` | `docker-compose.yml` contendo `image: mongo:latest`, `ports: ["27017:27017"]`, `volumes: [mongo_data:/data/db]` | Validação limpa via `docker compose config` (exit code 0); mapeamento de volume nomeado persistente | Falha de schema no `docker compose config` ou erro de sintaxe YAML (exit code 1) | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F4` |
| 2 | Docker | Declaração de Volume Top-Level | Definição da seção raiz `volumes: mongo_data:` no Compose | Chave `volumes:` no nível 0 do YAML referenciando `mongo_data:` | Reconhecimento do volume nomeado pelo Compose runtime | Erro de validação: "service mongodb.volumes contains undeclared volume mongo_data" | Compose Spec Reference, `PROJECT.md §F4` |
| 3 | File System | Preservação de Diretórios Vazios (.gitkeep) | Arquivos sentinela `.gitkeep` em `data/raw/`, `data/chromadb_local/` e `notebooks/` para viabilizar clone limpo | Criação dos arquivos `.gitkeep` com 0 bytes ou LF | Pastas existem e permanecem indexáveis no Git após o clone em novas máquinas | Diretórios vazios deixam de existir após clone se `.gitkeep` não for versionado | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F1` |
| 4 | File System | Modularização Python (__init__.py) | Criação de `__init__.py` em `src/`, `src/scraper/`, `src/database/`, `src/models/` e `src/api/` | Arquivos `__init__.py` com docstrings e zero imports prematuros | Todos os 5 pacotes importáveis via Python standard import mechanism | `SyntaxError` se mal formatado ou `ModuleNotFoundError` se importar classes de M2/M3 precocemente | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F1` |
| 5 | Git Governance | Exclusão de Ambientes Virtuais | Ignorar diretórios de ambientes locais (`venv/`, `.venv/`, `env/`) no controle de versão | Diretório local criado por desenvolvedor | Não listado em `git status`, ignorado em `git check-ignore` | Vazamento de binários e pacotes compilados locais no repositório | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F2` |
| 6 | Git Governance | Exclusão de Segredos e Cache | Ignorar arquivos de segredo `.env` e bytecode `__pycache__/` | Criação de `.env` ou execução do Python gerando `.pyc` | Arquivos ignorados automaticamente pelo Git | Exposição inadvertida de credenciais de produção no histórico do Git | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F2` |
| 7 | Git Governance | Des-exclusão Seletiva em data/ | Ignorar todos os dados gerados em tempo de execução dentro de `data/`, preservando exclusivamente as subpastas e os arquivos `.gitkeep` | Regras compostas no `.gitignore` permitindo recursão em diretórios e exceção `!data/**/.gitkeep` | `data/raw/.gitkeep` e `data/chromadb_local/.gitkeep` são rastreados; bancos SQLite e HTMLs são ignorados | Falha no tracking das pastas no clone ou vazamento de dumps de banco no commit | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F2` |
| 8 | Git Governance | Normalização Universal LF | Diretiva `* text=auto eol=lf` no `.gitattributes` para checkout consistente entre Windows e Linux | Qualquer arquivo de texto submetido ao Git | Conversão e gravação de quebras de linha estritamente em LF (`\n`) | Conflitos falsos de diff (CRLF vs LF), dirty status e problemas de execução de scripts Bash | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F3` |
| 9 | Dependencies | Especificação sem Pinning | Declaração das 12 dependências centrais do projeto em `requirements.txt` sem versão fixa (`sem pin`) | Arquivo `requirements.txt` contendo exatamente as 12 bibliotecas especificadas | Cada linha é parseável por PEP 508 sem operadores de versão (`==`, `>=`, etc.) | `AssertionError` se faltar biblioteca, se houver pin de versão ou biblioteca estranha | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F5` |
| 10 | Dependencies | Suporte a Extras em Dependências | Suporte sintático para a declaração `uvicorn[standard]` com extras de performance | Linha `uvicorn[standard]` no `requirements.txt` | Extração do pacote `uvicorn` com `extras={'standard'}` sem falha de parsing | `InvalidRequirement` se regex ingênuo rejeitar colchetes | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F5` |
| 11 | Environment | Template de Variáveis de Ambiente | Modelo `.env.example` com chaves para MongoDB e ChromaDB para configuração rápida pós-clone | Arquivo `.env.example` com `MONGO_URI`, `MONGO_DB_NAME` e `CHROMA_DB_PATH` | Leitura determinística via `python-dotenv` ou analisador chave-valor | Falha na inicialização das conexões no Milestone 2 por ausência de chaves padrão | `ORIGINAL_REQUEST.md §R1`, `PROJECT.md §F6` |
| 12 | Test & Verification | Verificador Autônomo Multi-Ambiente | Script de validação `verify_m1.py` executável em ambientes com ou sem Docker daemon e com ou sem `.git` inicializado | Invocação via `python verify_m1.py` | Relatório consolidado com códigos de saída determinísticos (0 = Sucesso, 1 = Falha) | Retorno claro dos diagnósticos linha a linha de cada não-conformidade | Sindicância do ambiente Windows atual |

---

## 3. Edge Cases

| # | Feature Relacionada | Cenário de Teste / Entrada (Input) | Comportamento Observado / Armadilha Técnica | Mitigação / Critério de Aceitação Mandatório |
|---|---------------------|-----------------------------------|---------------------------------------------|----------------------------------------------|
| 1 | Docker Compose | Máquina de desenvolvimento sem Docker CLI no PATH (`docker compose version` retorna `CommandNotFoundException`) | O comando nativo falha imediatamente impedindo a validação do schema antes do deploy em CI | O validador deve executar a checagem estrutural estática (via parser Python do Compose Spec) garantindo integridade das seções `services`, `mongodb`, `image`, `ports` e `volumes`, executando `docker compose config` somente se o binário estiver presente |
| 2 | .gitignore | Aplicação ingênua de `data/*` seguido de `!data/**/.gitkeep` | **Armadilha do Pruning no Git**: O Git interpreta `data/*` como match no diretório `data/raw/`. Como o diretório pai foi excluído, o Git nunca desce nele e ignora a regra `!data/**/.gitkeep`. Como resultado, `git add .` não rastreia nenhum `.gitkeep`! | O `.gitignore` DEVE des-excluir os diretórios explicitamente antes de re-incluir o `.gitkeep`. Exemplo comprovado: `data/*`, `!data/**/`, `!data/**/.gitkeep`, `data/**/*`, `!data/**/`, `!data/**/.gitkeep` (ou `data/**`, `!data/**/`, `!data/**/.gitkeep`) |
| 3 | .gitignore | Execução de comandos Git antes da inicialização do repositório (`git init` planejado apenas para M5) | `git check-ignore` e `git check-attr` falham com `fatal: not a git repository` se executados na raiz de desenvolvimento | A suite de testes do M1 deve testar a semântica do `.gitignore` dentro de um repositório Git isolado em diretório temporário (`tempfile.TemporaryDirectory`), permitindo validação 100% fiel sem sujar o workspace antes de M5 |
| 4 | __init__.py | Tentativa precoce de exportar classes em `src/database/__init__.py` (`from .mongo_connection import MongoConnection`) | Falha catastrófica de importação (`ModuleNotFoundError: No module named 'src.database.mongo_connection'`), pois os módulos de negócio só serão criados em M2/M3 | Em M1, todos os arquivos `__init__.py` devem conter ESTRITAMENTE docstrings descritivas e metadados básicos, sem qualquer import relativo ou absoluto de módulos inexistentes |
| 5 | requirements.txt | Presença de especificação de versão disfarçada (ex: `pydantic>=2.0` ou `fastapi==0.110.0`) | Violação direta da restrição contratual `sem pin` de `ORIGINAL_REQUEST.md §R1` | O parser de verificação deve inspecionar o atributo `Requirement.specifier` de cada entrada e rejeitar qualquer especificador diferente de string vazia |
| 6 | requirements.txt | Dependências com sufixos de extras (`uvicorn[standard]`) | Parsers simplificados que dividem linhas por regex alfanumérico podem quebrar nos caracteres `[` e `]` ou interpretar `standard` como dependência separada | Utilização mandatória de `packaging.requirements.Requirement` para validação formal de tokens PEP 508 |
| 7 | .gitattributes | Criação de arquivo com finais de linha Windows CRLF em editores locais | Risco de inconsistência de hash e commits com diffs espúrios de `\r` | O arquivo `.gitattributes` deve conter a linha canônica `* text=auto eol=lf`, forçando o Git a converter todos os arquivos textuais para LF no armazenamento interno e checkout |
| 8 | .env.example | Inclusão inadvertida de credenciais de produção ou senhas mockadas | Risco de desenvolvedores utilizarem credenciais inseguras em homologação | O arquivo deve conter exclusivamente as variáveis locais seguras especificadas (`mongodb://localhost:27017`, `rag_juridico` e `./data/chromadb_local`) |

---

## 4. Especificação Detalhada por Pilar de Validação

### 4.1 Pilar 1: Docker Compose (`docker-compose.yml`)

#### Requisitos de Conformidade
- Localização: `e:\Programacao\JudAI\docker-compose.yml`
- Schema Compose Spec:
  - Top-level `services:`
  - Serviço obrigatório: `mongodb:`
  - Imagem: `image: mongo:latest`
  - Mapeamento de portas: `ports: - "27017:27017"` (ou array equivalente com string)
  - Mapeamento de volume: `volumes: - mongo_data:/data/db` (volume nomeado montado no ponto oficial do Mongo)
  - Top-level `volumes:` declarando explicitamente `mongo_data:`

#### Comandos de Validação
1. **Validação Nativa Docker (quando Docker estiver instalado)**:
   ```powershell
   # PowerShell (Windows)
   docker compose config
   ```
   ```bash
   # Bash (Linux/macOS)
   docker compose config
   ```
   *Critério de Sucesso*: Exit code 0, saída contendo a árvore resolvida sem warnings ou erros de validação.

2. **Validação Estrutural Estática Multiplataforma**:
   ```powershell
   python -c "from pathlib import Path; import re; c = Path('docker-compose.yml').read_text(encoding='utf-8'); assert 'mongodb:' in c; assert 'mongo:latest' in c; assert '27017:27017' in c; assert 'mongo_data:/data/db' in c; assert re.search(r'^volumes:\s*$', c, re.M); print('DOCKER COMPOSE SCHEMA VALID')"
   ```

---

### 4.2 Pilar 2: Estrutura de Diretórios, `.gitkeep` e Pacotes Python

#### Requisitos de Conformidade
Devem existir exatamente na raiz do projeto:
- Diretórios:
  1. `data/raw/`
  2. `data/chromadb_local/`
  3. `notebooks/`
  4. `src/`
  5. `src/scraper/`
  6. `src/database/`
  7. `src/models/`
  8. `src/api/`
- Arquivos `.gitkeep`:
  1. `data/raw/.gitkeep` (0 bytes ou LF)
  2. `data/chromadb_local/.gitkeep` (0 bytes ou LF)
  3. `notebooks/.gitkeep` (0 bytes ou LF)
- Arquivos `__init__.py`:
  1. `src/__init__.py`
  2. `src/scraper/__init__.py`
  3. `src/database/__init__.py`
  4. `src/models/__init__.py`
  5. `src/api/__init__.py`

#### Comandos de Validação
1. **Verificação de Existência (PowerShell)**:
   ```powershell
   $paths = @(
     'data/raw/.gitkeep', 'data/chromadb_local/.gitkeep', 'notebooks/.gitkeep',
     'src/__init__.py', 'src/scraper/__init__.py', 'src/database/__init__.py',
     'src/models/__init__.py', 'src/api/__init__.py'
   )
   $missing = $paths | Where-Object { -not (Test-Path $_) }
   if ($missing) { Write-Error "Arquivos ausentes: $missing"; exit 1 } else { Write-Host "Todos os 8 arquivos existem!" }
   ```

2. **Verificação de Compilação Sintática dos Pacotes**:
   ```powershell
   python -m compileall src/
   ```
   *Critério de Sucesso*: Exit code 0, sem `SyntaxError`.

3. **Verificação de Importabilidade Limpa (Zero Imports Prematuros)**:
   ```powershell
   python -c "import sys; sys.path.insert(0, '.'); import src, src.scraper, src.database, src.models, src.api; print('TODOS OS PACOTES IMPORTADOS COM SUCESSO')"
   ```

---

### 4.3 Pilar 3: Governança do Repositório Git (`.gitignore` e `.gitattributes`)

#### Requisitos de Conformidade
- **`.gitignore`**:
  - Deve conter regras para: `venv/`, `.venv/`, `.env`, `__pycache__/`.
  - Deve tratar `data/` de modo que qualquer arquivo de dados (HTMLs brutos, bancos SQLite/Chroma, vetores) seja ignorado, enquanto os marcadores `.gitkeep` em subpastas permanecem rastreados.
- **`.gitattributes`**:
  - Deve conter a diretiva `* text=auto eol=lf`.

#### Comandos de Validação
1. **Validação do `.gitattributes` (PowerShell)**:
   ```powershell
   $ga = Get-Content .gitattributes -Raw
   if ($ga -match '\*\s+text=auto\s+eol=lf') { Write-Host "gitattributes CONFORME" } else { Write-Error "gitattributes NÃO CONFORME"; exit 1 }
   ```

2. **Validação Funcional do `.gitignore` (Repositório Isolado de Teste)**:
   Executado automaticamente pelo script `verify_m1.py`, simulando uma árvore de desenvolvimento completa e garantindo que:
   - `data/raw/.gitkeep` -> RASTREADO
   - `data/chromadb_local/.gitkeep` -> RASTREADO
   - `notebooks/.gitkeep` -> RASTREADO
   - `.env` -> IGNORADO
   - `data/raw/exemplo.html` -> IGNORADO
   - `data/chromadb_local/chroma.sqlite3` -> IGNORADO
   - `venv/qualquer_binario` -> IGNORADO

---

### 4.4 Pilar 4: Especificação de Dependências (`requirements.txt`)

#### Requisitos de Conformidade
- O arquivo `requirements.txt` deve conter exatamente 12 dependências:
  1. `fastapi`
  2. `uvicorn[standard]`
  3. `pydantic`
  4. `pymongo`
  5. `chromadb`
  6. `rank_bm25`
  7. `sentence-transformers`
  8. `nltk`
  9. `python-dotenv`
  10. `beautifulsoup4`
  11. `lxml`
  12. `requests`
- NENHUMA dependência pode conter operador de versão (`==`, `>=`, `<=`, `~=`, `!=`, `<`, `>`).

#### Comandos de Validação
1. **Validação Formal via Python PEP 508**:
   ```powershell
   python -c "
   from packaging.requirements import Requirement
   from pathlib import Path
   expected = {'fastapi': set(), 'uvicorn': {'standard'}, 'pydantic': set(), 'pymongo': set(), 'chromadb': set(), 'rank_bm25': set(), 'sentence-transformers': set(), 'nltk': set(), 'python-dotenv': set(), 'beautifulsoup4': set(), 'lxml': set(), 'requests': set()}
   lines = [l.strip() for l in Path('requirements.txt').read_text().splitlines() if l.strip() and not l.startswith('#')]
   assert len(lines) == 12, f'Esperado 12 dependências, obtido {len(lines)}'
   for line in lines:
       req = Requirement(line)
       norm = req.name.lower().replace('_', '-')
       target = next((k for k in expected if k.lower().replace('_', '-') == norm), None)
       assert target is not None, f'Dependência não autorizada: {req.name}'
       assert req.extras == expected[target], f'Extras incorretos para {target}: {req.extras}'
       assert str(req.specifier) == '', f'Dependência fixada proibida em {req.name}: {req.specifier}'
   print('REQUIREMENTS.TXT 100% CONFORME (12 DEPENDÊNCIAS SEM PIN)')
   "
   ```

---

### 4.5 Pilar 5: Template de Variáveis de Ambiente (`.env.example`)

#### Requisitos de Conformidade
- O arquivo `.env.example` deve conter rigorosamente:
  - `MONGO_URI=mongodb://localhost:27017`
  - `MONGO_DB_NAME=rag_juridico`
  - `CHROMA_DB_PATH=./data/chromadb_local`

#### Comandos de Validação
1. **Validação Chave-Valor (PowerShell)**:
   ```powershell
   python -c "
   from pathlib import Path
   lines = [l.strip() for l in Path('.env.example').read_text().splitlines() if l.strip() and not l.startswith('#')]
   d = dict(l.split('=', 1) for l in lines)
   assert d.get('MONGO_URI') == 'mongodb://localhost:27017', 'MONGO_URI inválido'
   assert d.get('MONGO_DB_NAME') == 'rag_juridico', 'MONGO_DB_NAME inválido'
   assert d.get('CHROMA_DB_PATH') == './data/chromadb_local', 'CHROMA_DB_PATH inválido'
   print('.ENV.EXAMPLE 100% CONFORME')
   "
   ```

---

## 5. Script de Verificação Automatizada Integrada (`verify_m1.py`)

Para assegurar reprodutibilidade absoluta por Worker, Reviewers e Challengers, o script de validação canônico está disponibilizado em:
`e:\Programacao\JudAI\.agents\teamwork\spec_miner_m1_3\verify_m1.py`

### Como Executar o Validador
A partir da raiz do projeto (`e:\Programacao\JudAI`):

```powershell
# Execução no Windows PowerShell
python .agents/teamwork/spec_miner_m1_3/verify_m1.py
```

```bash
# Execução no Linux / macOS / WSL
python3 .agents/teamwork/spec_miner_m1_3/verify_m1.py
```

### Critério de Sucesso do Script
- Saída: `MILESTONE 1: 100% DAS ESPECIFICAÇÕES ATENDIDAS!`
- Código de Saída (Exit Code): `0` (Zero).
- Se houver qualquer falha ou arquivo faltando, o script retorna código `1` com a enumeração detalhada das não-conformidades.

---

## 6. Portões de Qualidade e Critérios Go/No-Go para o Milestone 1

| Portão (Gate) | Componente Auditado | Critério de Aceitação Binário (Pass/Fail) | Responsável |
|---|---|---|---|
| **Gate 1: Estrutura** | 8 diretórios e 8 arquivos (`.gitkeep`, `__init__.py`) | 100% dos arquivos presentes; compilação sem erro; importação de `src.*` limpa | Worker / Reviewer 1 |
| **Gate 2: Docker Compose** | `docker-compose.yml` | Serviço `mongodb`, imagem `mongo:latest`, porta `27017:27017`, volume `mongo_data:/data/db` declarado na raiz `volumes:` | Worker / Reviewer 2 |
| **Gate 3: Governança Git** | `.gitignore` e `.gitattributes` | Diretiva `* text=auto eol=lf`; exclusão de `.env`, `venv/`, `__pycache__/`; rastreamento garantido de `.gitkeep` em teste de isolamento | Challenger 1 |
| **Gate 4: Dependências** | `requirements.txt` | Exatamente 12 bibliotecas especificadas; sem pin de versão; `uvicorn[standard]` com extra preservado | Reviewer 1 / Challenger 1 |
| **Gate 5: Ambiente** | `.env.example` | As 3 chaves presentes com os valores padrão canônicos; sintaxe livre de erros | Reviewer 2 |
| **Gate 6: Auditoria Final** | Suite Completa M1 | Execução do runner `verify_m1.py` com exit code 0 e zero avisos | Orchestrator |
