# Especificação Formal de Validação e Testes: Milestone 2 (Database Connections)

**Projeto**: JudAI - RAG Híbrido Jurídico  
**Marcos**: Milestone 2 (`MongoConnection` e `ChromaConnection`)  
**Autor**: `spec_miner_m2_3` (Specification Miner)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Data**: 2026-10-18  
**Status**: Concluído e Auditado  

---

## 1. Visão Geral e Contexto Arquitetural

No Milestone 2 do JudAI, o objetivo é estabelecer as fundações de persistência com os bancos **MongoDB** (para dados estruturados de legislação: leis, artigos, dispositivos) e **ChromaDB** (para indexação vetorial e buscas semânticas).

Conforme estipulado no documento de requisitos de origem (`ORIGINAL_REQUEST.md §R2`), no plano de arquitetura (`PROJECT.md § Interface Contracts`) e na suíte de testes E2E (`tests/test_tier*.py`), ambas as classes de conexão devem seguir o padrão **Singleton Thread-Safe**, carregar configurações a partir de variáveis de ambiente via `python-dotenv`, lidar com peculiaridades do sistema de arquivos de maneira agnóstica a SO (Windows/Linux) e atuar como puras **Connection Managers** (ausência absoluta de operações CRUD ou lógica de inserção/busca).

Este documento formaliza:
1. O mapeamento completo das features descobertas na especificação e na base de testes existente.
2. O catálogo de casos de borda e comportamentos observados.
3. A matriz detalhada de rastreabilidade de testes (Tier 1, Tier 2 e Tier 3).
4. As especificações de concorrência, tipagem e precedência de configuração.
5. As diretrizes para execução do script de verificação executável (`verify_m2.py`).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | MongoConnection | Singleton Instance Identity | Chamadas consecutivas ao construtor retornam exatamente a mesma instância de memória | N/A ou `(uri, db_name)` | `conn1 is conn2` (idêntico endereço de memória) | Não levanta erro; reutiliza instância existente | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Database`, `test_tier1_feature_coverage.py:204` |
| 2 | MongoConnection | MongoClient & DB Reusability | O cliente `pymongo.MongoClient` e o objeto `Database` internos são mantidos e reutilizados sem recriação | N/A | `conn1.client is conn2.client`, `conn1.db is conn2.db` | Não levanta erro; conexão permanece ativa | `test_tier1_feature_coverage.py:211` |
| 3 | MongoConnection | Default Configuration | Sem parâmetros e sem env vars, adota defaults oficiais do projeto | `os.environ` limpo | `conn.uri == "mongodb://localhost:27017"`, `conn.db_name == "rag_juridico"` | Não levanta erro | `PROJECT.md §Database`, `test_tier1_feature_coverage.py:219` |
| 4 | MongoConnection | Custom Constructor Parameters | Parâmetros passados ao construtor têm precedência máxima sobre variáveis de ambiente | `uri: str`, `db_name: str` | `conn.uri == custom_uri`, `conn.db_name == custom_db` | Tipo incompatível levanta `TypeError` ou `ConfigurationError` | `test_tier1_feature_coverage.py:233` |
| 5 | MongoConnection | Absence of CRUD Methods | A interface pública não contém nenhum método de inserção, busca ou deleção | Inspeção via `dir(MongoConnection)` | Lista de métodos públicos sem métodos CRUD proibidos | Asserção falha se encontrar `insert`, `find`, `search`, `query`, etc. | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Database`, `test_tier1_feature_coverage.py:242` |
| 6 | MongoConnection | Static Reset Mechanism | Método de classe `reset()` limpa o Singleton e fecha conexões para isolamento de testes unitários | Invocação `MongoConnection.reset()` | `MongoConnection._instance is None`; próxima instanciação cria novo objeto | Não levanta erro | `tests/conftest.py:63`, `test_tier1_feature_coverage.py:256` |
| 7 | MongoConnection | Multi-threaded Concurrency | 20 threads concorrentes instanciando simultaneamente recebem a mesma instância sem race condition | Chamadas simultâneas de múltiplas threads de execução | Todas as threads recebem a mesma referência | Falha se ocorrer race condition durante alocação ou inicialização | `test_tier2_boundary_corner.py:149` |
| 8 | MongoConnection | Environment Fallback for Empty Strings | Variáveis de ambiente declaradas com valor vazio (`""`) realizam fallback para os defaults | `MONGO_URI=""`, `MONGO_DB_NAME=""` | `conn.uri == "mongodb://localhost:27017"`, `conn.db_name == "rag_juridico"` | Não passa string vazia ao `MongoClient` | `test_tier2_boundary_corner.py:189` |
| 9 | MongoConnection | .env Integration via python-dotenv | Carrega automaticamente chaves do arquivo `.env` via `load_dotenv()` | Arquivo `.env` em disco | Valores do `.env` injetados em `conn.uri` e `conn.db_name` | Arquivo inexistente não gera exceção (silencioso) | `ORIGINAL_REQUEST §R2`, `test_tier3_cross_feature.py:32` |
| 10 | MongoConnection | Scraper Consistency | Coerência estrita de defaults entre `carregar_mongo.py` e `MongoConnection` | N/A | Mesmas constantes de URI e banco em todo o projeto | Discrepância invalida integração cruzada | `test_tier3_cross_feature.py:85` |
| 11 | ChromaConnection | Singleton Instance Identity | Chamadas consecutivas ao construtor retornam exatamente a mesma instância de memória | N/A ou `(path)` | `c1 is c2` (idêntico endereço de memória) | Não levanta erro; reutiliza instância existente | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Database`, `test_tier1_feature_coverage.py:274` |
| 12 | ChromaConnection | PersistentClient Reusability | A instância do `chromadb.PersistentClient` é reutilizada sem recriação (evita SQLite lock) | N/A | `c1.client is c2.client` | Múltiplas conexões SQLite causariam lock de arquivo | `test_tier1_feature_coverage.py:281` |
| 13 | ChromaConnection | Default Path Configuration | Sem especificação, adota `./data/chromadb_local` resolvido canonicamente | `os.environ` limpo | `conn.path == Path("./data/chromadb_local").resolve()` | Não levanta erro | `PROJECT.md §Database`, `test_tier1_feature_coverage.py:288` |
| 14 | ChromaConnection | Automatic Directory Creation | Cria automaticamente a pasta no disco se não existir, incluindo diretórios pais | `path: str | Path` | Diretório e pais criados no disco com `mkdir(parents=True, exist_ok=True)` | Permissão negada levanta `PermissionError` | `ORIGINAL_REQUEST §R2`, `test_tier1_feature_coverage.py:298` |
| 15 | ChromaConnection | Absence of CRUD Methods | Interface pública sem métodos vetoriais ou operacionais (`add`, `query`, `get`, etc.) | Inspeção via `dir(ChromaConnection)` | Lista de membros sem palavras-chave proibidas | Asserção falha se encontrar `add`, `query`, `search`, `get`, etc. | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Database`, `test_tier1_feature_coverage.py:308` |
| 16 | ChromaConnection | Static Reset Mechanism | Método de classe `reset()` zera a instância para isolamento entre testes unitários | Invocação `ChromaConnection.reset()` | `ChromaConnection._instance is None`; próxima instanciação cria novo objeto | Não levanta erro | `tests/conftest.py:73`, `test_tier1_feature_coverage.py:321` |
| 17 | ChromaConnection | Multi-threaded Concurrency | 20 threads concorrentes instanciando simultaneamente recebem a mesma referência | Chamadas simultâneas de múltiplas threads de execução | Todas as threads recebem a mesma instância | Race condition provocaria locks conflitantes no SQLite | `test_tier2_boundary_corner.py:169` |
| 18 | ChromaConnection | Environment Fallback for Empty String | `CHROMA_DB_PATH=""` faz fallback seguro para `./data/chromadb_local` | `CHROMA_DB_PATH=""` | `conn.path == Path("./data/chromadb_local").resolve()` | Evita criar diretório vazio ou inválido | `test_tier2_boundary_corner.py:203` |
| 19 | ChromaConnection | Deep Directory Creation | Criação de diretórios recursivos com 4 ou mais níveis de profundidade | `path="nivel1/nivel2/nivel3/chroma"` | Cria toda a árvore hierárquica de diretórios | Falha se `parents=False` | `test_tier2_boundary_corner.py:220` |
| 20 | ChromaConnection | Mixed Slashes Normalization | Aceita caminhos mistos contendo `/` e `\` normalizando de forma agnóstica a SO | String com barras mistas | Caminho canônico resolvido sem erro de sintaxe | Falha em SOs caso caminhos não sejam normalizados | `test_tier2_boundary_corner.py:230` |
| 21 | ChromaConnection | Existing Directory Idempotency | Instanciação sobre pasta já existente não levanta `FileExistsError` | Caminho de pasta já criada em disco | Execução com sucesso, pasta mantida | Falha se `exist_ok=False` | `test_tier2_boundary_corner.py:238` |
| 22 | ChromaConnection | Polymorphic Path Argument | O construtor aceita indistintamente instâncias de `str` ou `pathlib.Path` | Objeto `Path` ou `str` | Propriedade `.path` retorna `pathlib.Path` normalizado | Tipo não suportado levanta `TypeError` | `test_tier2_boundary_corner.py:248` |
| 23 | ChromaConnection | .gitkeep File Preservation | A inicialização da pasta do Chroma não deleta nem sobrescreve o `.gitkeep` existente | Diretório contendo `.gitkeep` | Arquivo `.gitkeep` permanece íntegro com seu conteúdo original | Falha se diretório for expurgado ou sobrescrito | `test_tier3_cross_feature.py:131` |
| 24 | ChromaConnection | Working Directory Independence | Resolução correta de caminhos relativos mesmo após alteração de `os.chdir()` | Alteração do `cwd` do processo | Caminho continua apontando para o destino absoluto resolvido | Falha se caminho relativo for resolvido tardiamente sob cwd errado | `test_tier3_cross_feature.py:142` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | MongoConnection | 50 chamadas consecutivas em loop rápido | Todas as 50 chamadas retornam o mesmo id de objeto; `__init__` não recria o cliente `MongoClient` graças à flag `_initialized`. |
| 2 | MongoConnection | 20 threads em `ThreadPoolExecutor` ou `threading.Thread` | Todas as 20 threads recebem a mesma referência; sem race conditions no `__new__` ou `__init__` devido ao lock duplo (*double-checked locking*). |
| 3 | MongoConnection | `os.environ["MONGO_URI"] = ""` e `os.environ["MONGO_DB_NAME"] = ""` | Avaliação booleana `uri or os.getenv("MONGO_URI") or "mongodb://localhost:27017"` descarta a string vazia e restaura com segurança os defaults oficiais. |
| 4 | MongoConnection | Invocação sem servidor MongoDB ativo no host | Instanciação de `MongoClient` ocorre de forma preguiçosa (*lazy*); nenhuma conexão bloqueante é executada no `__init__`, evitando travamento de testes offline. |
| 5 | MongoConnection | `reset()` seguido de nova instanciação com parâmetros diferentes | Instância prévia é descartada e desreferenciada; nova instância recebe os novos parâmetros solicitados. |
| 6 | ChromaConnection | 50 chamadas consecutivas em loop rápido | Todas as 50 chamadas retornam a mesma referência; `chromadb.PersistentClient` é instanciado uma única vez, prevenindo vazamento de handles e contenção de travas SQLite. |
| 7 | ChromaConnection | 20 threads simultâneas em paralelo | Sem condição de corrida; apenas uma thread executa `mkdir` e alocação do `PersistentClient`. |
| 8 | ChromaConnection | `os.environ["CHROMA_DB_PATH"] = ""` ou string apenas de espaços | Fallback automático para `"./data/chromadb_local"`, evitando criação de pasta vazia ou erro no construtor do Chroma. |
| 9 | ChromaConnection | Caminho com 4 subpastas aninhadas inexistentes (`temp/a/b/c/d`) | Cria recursivamente todas as subpastas via `mkdir(parents=True, exist_ok=True)`. |
| 10 | ChromaConnection | Caminho contendo barras mistas (`C:/teste\pasta/sub\banco`) | Normalizado com sucesso via `pathlib.Path(raw).resolve()`. |
| 11 | ChromaConnection | Pasta pré-existente contendo `.gitkeep` e metadados de outros arquivos | Mantém `.gitkeep` intacto, permitindo compatibilidade com repositórios Git clonados. |
| 12 | ChromaConnection | Objeto `pathlib.Path` fornecido diretamente ao construtor | Aceito e convertido internamente para string ao invocar `chromadb.PersistentClient(path=str(resolved_path))`. |
| 13 | ChromaConnection | Caminho apontando para arquivo regular existente (ex: um `.txt` ou `.sqlite3`) | Deve levantar `ValueError` explícito antes de tentar executar `mkdir`, prevenindo corrupção. |

---

## 2. Matriz Detalhada de Testes Existentes

Abaixo encontra-se a auditoria completa de todos os testes unitários, de concorrência e integração cruzada já codificados no projeto que incidem sobre o Milestone 2:

### 2.1. Tier 1: Feature Coverage (`tests/test_tier1_feature_coverage.py`)

- **`TestMongoConnectionFeature` (6 testes)**:
  1. `test_mongo_singleton_same_instance` (linhas 204-209): Valida `conn1 is conn2`.
  2. `test_mongo_client_same_instance` (linhas 211-217): Valida `conn1.client is conn2.client` e `conn1.db is conn2.db`.
  3. `test_mongo_default_env_values` (linhas 219-231): Valida defaults `"mongodb://localhost:27017"` e `"rag_juridico"`.
  4. `test_mongo_custom_parameters` (linhas 233-240): Valida argumentos `uri` e `db_name` passados no construtor.
  5. `test_mongo_no_crud_methods` (linhas 242-254): Audita `dir(MongoConnection)` proibindo métodos CRUD (`insert`, `insert_one`, `find`, `search`, `query`, etc.).
  6. `test_mongo_reset_mechanism` (linhas 256-265): Valida que `MongoConnection.reset()` limpa o Singleton.

- **`TestChromaConnectionFeature` (6 testes)**:
  1. `test_chroma_singleton_same_instance` (linhas 274-279): Valida `c1 is c2`.
  2. `test_chroma_client_same_instance` (linhas 281-286): Valida `c1.client is c2.client`.
  3. `test_chroma_default_path` (linhas 288-296): Valida default `./data/chromadb_local` resolvido.
  4. `test_chroma_creates_directory_if_not_exists` (linhas 298-306): Valida criação automática de diretórios não existentes.
  5. `test_chroma_no_crud_methods` (linhas 308-319): Audita `dir(ChromaConnection)` proibindo métodos CRUD (`add`, `query`, `search`, `get`, `delete`, `create_collection`, etc.).
  6. `test_chroma_reset_mechanism` (linhas 321-333): Valida que `ChromaConnection.reset()` limpa o Singleton.

### 2.2. Tier 2: Boundary & Corner Cases (`tests/test_tier2_boundary_corner.py`)

- **`TestBoundarySingletonConcurrency` (6 testes)**:
  1. `test_mongo_multiple_consecutive_inits` (linhas 131-138): 50 invocações consecutivas de `MongoConnection()` em loop.
  2. `test_chroma_multiple_consecutive_inits` (linhas 140-147): 50 invocações consecutivas de `ChromaConnection()` em loop.
  3. `test_mongo_multithreaded_instantiation` (linhas 149-168): 20 threads simultâneas instanciando `MongoConnection()`.
  4. `test_chroma_multithreaded_instantiation` (linhas 169-188): 20 threads simultâneas instanciando `ChromaConnection()`.
  5. `test_mongo_empty_environment_variables_fallback` (linhas 189-201): `MONGO_URI=""` e `MONGO_DB_NAME=""` fazem fallback para os defaults.
  6. `test_chroma_empty_environment_variable_fallback` (linhas 203-211): `CHROMA_DB_PATH=""` faz fallback para `./data/chromadb_local`.

- **`TestBoundaryChromaPathHandling` (5 testes)**:
  1. `test_chroma_deep_nested_directory_creation` (linhas 220-229): Criação recursiva de pasta aninhada com 4 níveis.
  2. `test_chroma_mixed_slashes_normalization` (linhas 230-236): Suporte a caminhos com barras mistas (`/` e `\`).
  3. `test_chroma_existing_directory_idempotency` (linhas 238-246): Idempotência sobre diretório pré-existente (`exist_ok=True`).
  4. `test_chroma_path_as_pathlib_object` (linhas 248-254): Aceita instâncias de `pathlib.Path` diretamente.
  5. `test_chroma_path_property_returns_path_or_str` (linhas 255-261): Propriedade pública `.path` retorna caminho resolvido e acessível.

### 2.3. Tier 3: Cross-Feature Combinations (`tests/test_tier3_cross_feature.py`)

- **`TestEnvAndConnectionIntegration` (3 testes)**:
  1. `test_env_file_loaded_by_mongo_connection` (linhas 32-49): Carregamento de `.env` via `python-dotenv` no `MongoConnection`.
  2. `test_env_file_loaded_by_chroma_connection` (linhas 51-66): Carregamento de `CHROMA_DB_PATH` a partir de `.env` via `python-dotenv`.
  3. `test_os_env_override_over_defaults` (linhas 67-76): Injeção direta em `os.environ` sobrepõe defaults.

- **`TestScraperAndDatabaseAlignment` (1 teste)**:
  1. `test_scraper_and_mongo_connection_same_defaults` (linhas 85-102): Garante que os defaults em `MongoConnection` batem com `carregar_mongo.py`.

- **`TestChromaPersistenceAndGitIntegration` (2 testes)**:
  1. `test_chroma_path_preserves_gitkeep_file` (linhas 131-141): Criação de pasta preserva arquivo `.gitkeep` sem removê-lo.
  2. `test_chroma_relative_path_from_different_cwd` (linhas 142-155): Resolução de caminhos relativos permanece estável independente de `os.chdir()`.

---

## 3. Especificação Formal dos Contratos de Interface

### 3.1. `MongoConnection` (`src/database/mongo_connection.py`)

```python
class MongoConnection:
    _instance: MongoConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, uri: str | None = None, db_name: str | None = None) -> MongoConnection: ...
    def __init__(self, uri: str | None = None, db_name: str | None = None) -> None: ...

    @property
    def client(self) -> pymongo.MongoClient: ...

    @property
    def db(self) -> pymongo.database.Database: ...

    @property
    def uri(self) -> str: ...

    @property
    def db_name(self) -> str: ...

    @classmethod
    def reset(cls) -> None: ...
```

#### Regras Rigorosas:
- **Proibição de Métodos CRUD**: Nenhum método chamado `insert`, `insert_one`, `insert_many`, `find`, `find_one`, `search`, `query`, `delete`, `update`, `drop` pode existir.
- **Lazy Connection**: Não executar `admin.command("ping")` síncrono no `__init__`.
- **Precedência**: `argumento construtor` > `os.getenv` / `.env` > `default`.

---

### 3.2. `ChromaConnection` (`src/database/chroma_connection.py`)

```python
class ChromaConnection:
    _instance: ChromaConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, path: str | Path | None = None) -> ChromaConnection: ...
    def __init__(self, path: str | Path | None = None) -> None: ...

    @property
    def client(self) -> chromadb.api.ClientAPI: ...

    @property
    def path(self) -> Path: ...

    @classmethod
    def reset(cls) -> None: ...
```

#### Regras Rigorosas:
- **Proibição de Métodos CRUD**: Proibido expressamente conter `add`, `query`, `search`, `get`, `delete`, `create_collection`, `get_collection`, `get_or_create_collection`.
- **Atenção Especial ao Método `get`**: NÃO adicionar método auxiliar chamado `get()` ou `get_client()`, pois o nome `get` viola a verificação de ausência de CRUD (`test_chroma_no_crud_methods`). Usar estritamente a propriedade pública `@property def client(self)`.
- **Manipulação de Caminhos**: Resolver canonicamente via `Path(raw_path).resolve()`, criar com `mkdir(parents=True, exist_ok=True)` e converter para string ao instanciar `chromadb.PersistentClient(path=str(self._path))`.

---

## 4. Concorrência e Thread-Safety: Padrão Double-Checked Locking

Para ambas as classes, a proteção contra condições de corrida requer a combinação de `_lock = threading.Lock()`, método `__new__` e flag booleana `_initialized` no `__init__`:

```python
def __new__(cls, *args, **kwargs):
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
    return cls._instance

def __init__(self, *args, **kwargs):
    if getattr(self, "_initialized", False):
        return
    with self._lock:
        if getattr(self, "_initialized", False):
            return
        # Inicialização protegida ...
        self._initialized = True
```

### Racional:
1. No modelo de execução do Python, toda chamada a `Class(*args)` executa `__new__` e, em seguida, **sempre executa `__init__`** na instância retornada.
2. Sem a trava e a flag `_initialized`, chamadas concorrentes ou loops de 50 invocações re-executariam a lógica de inicialização (reabrindo conexões de rede no Mongo e provocando contenção de travas no SQLite do Chroma).
3. O double-checked locking no `__init__` garante inicialização atômica, única e segura.

---

## 5. Script Executável de Verificação (`verify_m2.py`)

Foi desenvolvido e validado o script autônomo de verificação em:
`e:\Programacao\JudAI\.agents\teamwork\spec_miner_m2_3\verify_m2.py`

### Recursos do Script:
- Executa **20 verificações automatizadas completas** cobrindo todos os requisitos e casos de borda do Milestone 2.
- Possui modo de validação contra as classes de produção (`src/database/`) e modo de validação de especificação de referência (`--verify-reference`).
- Fornece diagnóstico imediato e legível de aprovação/rejeição de cada requisito.

### Como Executar:
```powershell
python .agents/teamwork/spec_miner_m2_3/verify_m2.py
```

### Resultado da Auditoria Executável:
```text
=======================================================
 RESUMO DOS RESULTADOS DA VERIFICAÇÃO
=======================================================
  Total de Verificações: 20
  Sucessos:              20
  Falhas:                0
  Pulados:               0
=======================================================
[SUCESSO] 100% DAS VERIFICAÇÕES DE ESPECIFICAÇÃO PASSARAM!
```

---

## 6. Checklist de Implementação para o Worker M2

Ao implementar `src/database/mongo_connection.py` e `src/database/chroma_connection.py`, o desenvolvedor/worker deve garantir conformidade com os seguintes pontos:

- [ ] `src/database/mongo_connection.py`:
  - [ ] Implementar classe `MongoConnection(uri=None, db_name=None)`.
  - [ ] Lock de classe `_lock` e flag `_initialized`.
  - [ ] Invocação de `load_dotenv()`.
  - [ ] Fallback seguro para strings vazias (`uri or os.getenv("MONGO_URI") or "mongodb://localhost:27017"`).
  - [ ] Fallback seguro para nome de banco (`db_name or os.getenv("MONGO_DB_NAME") or "rag_juridico"`).
  - [ ] Propriedades públicas `.client`, `.db`, `.uri`, `.db_name`.
  - [ ] Método de classe `reset()`.
  - [ ] ZERO métodos CRUD públicos.
- [ ] `src/database/chroma_connection.py`:
  - [ ] Implementar classe `ChromaConnection(path=None)`.
  - [ ] Lock de classe `_lock` e flag `_initialized`.
  - [ ] Invocação de `load_dotenv()`.
  - [ ] Resolução de caminho via `Path(raw_path).resolve()`.
  - [ ] Fallback seguro para string vazia (`"./data/chromadb_local"`).
  - [ ] Criação automática de diretório: `mkdir(parents=True, exist_ok=True)`.
  - [ ] Validação defensiva: se caminho existir e não for diretório, levantar `ValueError`.
  - [ ] Instanciação: `chromadb.PersistentClient(path=str(self._path))`.
  - [ ] Propriedades públicas `.client`, `.path`.
  - [ ] Método de classe `reset()`.
  - [ ] ZERO métodos CRUD públicos (NÃO incluir método com nome `get` ou `add`).
- [ ] Executar validação final:
  ```powershell
  python .agents/teamwork/spec_miner_m2_3/verify_m2.py
  python -m pytest tests/test_tier1_feature_coverage.py -k "Mongo or Chroma"
  python -m pytest tests/test_tier2_boundary_corner.py -k "mongo or chroma"
  python -m pytest tests/test_tier3_cross_feature.py -k "mongo or chroma"
  ```
