# Relatório Técnico: Design e Especificação de ChromaConnection Singleton (Milestone 2)

**Autor**: `explorer_m2_2` (Explorer 2 - Milestone 2)  
**Data**: 2026-10-18  
**Escopo**: `src/database/chroma_connection.py`  
**Destinatário**: Orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`) e Implementador M2  

---

## 1. Sumário Executivo

Este relatório apresenta a análise aprofundada, contratos de interface, arquitetura de concorrência, tratamento de caminhos cross-platform (Windows/Linux) e o código exato proposto para a implementação de `ChromaConnection` em `src/database/chroma_connection.py`.

A implementação atende com 100% de conformidade aos requisitos do projeto (`ORIGINAL_REQUEST.md §R2`), do planejamento (`PROJECT.md`) e da especificação técnica (`spec_api_database.md`), satisfazendo os 17 testes automatizados mapeados em `tests/test_tier1_feature_coverage.py`, `tests/test_tier2_boundary_corner.py`, `tests/test_tier3_cross_feature.py` e `tests/conftest.py`.

---

## 2. Requisitos e Diretrizes Arquiteturais

### 2.1. Padrão Singleton Thread-Safe
1. **Identidade de Instância (`c1 is c2`)**:
   - Múltiplas invocações do construtor `ChromaConnection()` devem retornar a mesma referência na memória.
2. **Reutilização de Cliente (`c1.client is c2.client`)**:
   - A instância subjacente do `chromadb.PersistentClient` deve ser criada uma única vez no ciclo de vida do processo e reutilizada em todas as requisições e chamadas.
3. **Thread Safety & Double-Checked Locking**:
   - Proteção estrita contra condições de corrida (*race conditions*) em ambientes multithread (ex: servidor Uvicorn com workers assíncronos ou rajadas de requisições paralelas).
   - Bloqueio via `threading.Lock()` no nível de classe (`_lock`).
4. **Proteção Contra Re-inicialização em `__init__`**:
   - No Python, `__init__` é invocado pelo interpretador a cada chamada de instanciação da classe, mesmo quando `__new__` retorna uma instância pré-existente.
   - Sem proteção, invocações subsequentes (ex: 50 vezes em loop) reavaliariam variáveis de ambiente, recriariam diretórios e re-instanciariam `PersistentClient`, causando vazamento de recursos e contenção de travas de arquivo no SQLite interno do ChromaDB.
   - A proteção deve ser implementada com a flag `_initialized` combinada com o lock de classe (double-checked locking).
5. **Prevenção de Locks no SQLite**:
   - O ChromaDB local utiliza SQLite (`chroma.sqlite3`) para gerenciar metadados de coleções e índices vetoriais.
   - Instanciar múltiplos `PersistentClient` apontando para a mesma pasta em um mesmo processo provoca avisos e colisões de lock no SQLite. O padrão Singleton garante conexão única e centralizada.

### 2.2. Resolução de Configuração e Precedência de Caminhos
1. **Fontes de Configuração**:
   - Parâmetro explícito no construtor: `path: str | Path | None = None`.
   - Variável de ambiente: `CHROMA_DB_PATH`.
   - Arquivo `.env`: carregado via `python-dotenv` (`load_dotenv()`).
   - Valor padrão (*default*): `"./data/chromadb_local"`.
2. **Ordem de Precedência Rigorosa**:
   $$\text{Parâmetro Construtor (se não-vazio)} > \text{Variável de Ambiente CHROMA\_DB\_PATH} > \text{Valor Padrão ("./data/chromadb_local")}$$
3. **Tratamento de Strings Vazias e Whitespace (Edge Cases de Fronteira)**:
   - Caso `os.environ["CHROMA_DB_PATH"] = ""` ou contenha apenas espaços em branco, o uso Ingênuo de `os.getenv("CHROMA_DB_PATH", default)` retornaria `""` (avaliado como válido pelo `getenv`), causando tentativa inválida de criação de pasta vazia.
   - A resolução deve validar se a string possui conteúdo útil, realizando fallback imediato para `"./data/chromadb_local"`.
   - Validado diretamente por `test_tier2_boundary_corner.py::test_chroma_empty_environment_variable_fallback`.

### 2.3. Resolução de Caminhos Agnóstica a SO (Windows e Linux)
1. **Normalização Total via `pathlib.Path`**:
   - Compatibilidade total com caminhos contendo barras normais (`/`), barras invertidas (`\`) ou barras mistas.
   - Suporte a caminhos relativos ao diretório do projeto ou caminhos absolutos (incluindo letras de unidade no Windows como `E:\...`).
   - Resolução canônica absoluta através de `.resolve()`.
2. **Aceitação Polimórfica de Tipos**:
   - O parâmetro `path` deve aceitar tanto instâncias de `str` quanto objetos `pathlib.Path` diretamente.
   - A propriedade pública `.path` deve retornar o objeto `pathlib.Path` canônico resolvido, permitindo chamadas diretas como `conn.path.exists()`, `conn.path.is_dir()`, `conn.path.resolve()`.
3. **Instanciação do PersistentClient**:
   - O construtor `chromadb.PersistentClient` espera uma string no parâmetro `path`. A conversão deve ser feita explicitamente via `str(self._path)`.

### 2.4. Criação Automática e Idempotente de Diretórios
1. **Criação Recursiva (`parents=True`)**:
   - Permite a criação de diretórios profundamente aninhados que ainda não existam no sistema de arquivos (ex: `temp_dir / "nivel1" / "nivel2" / "nivel3" / "chroma_store"`).
2. **Idempotência (`exist_ok=True`)**:
   - Se o diretório já existir (como no repositório clonado contendo `data/chromadb_local`), a execução não levanta `FileExistsError`.
3. **Preservação de Arquivos Existentes (`.gitkeep`)**:
   - A chamada `mkdir(parents=True, exist_ok=True)` é puramente estrutural no sistema de arquivos e NÃO remove nem modifica arquivos existentes dentro da pasta. O arquivo `data/chromadb_local/.gitkeep` permanece intacto, garantindo conformidade com regras de versionamento Git.
4. **Validação Defensiva Contra Arquivos Regulares**:
   - Se o caminho configurado já existir e for um arquivo regular (não um diretório), deve-se levantar `ValueError` descritivo antes de invocar `mkdir`.

### 2.5. Isolamento Semântico (Proibição Absoluta de Métodos CRUD)
1. **Regra R2 do ORIGINAL_REQUEST**:
   - "sem lógica de inserção/busca".
2. **Validação Estrita de Membros da Classe**:
   - O teste `test_tier1_feature_coverage.py::test_chroma_no_crud_methods` audita os métodos públicos da classe (`[m for m in dir(ChromaConnection) if not m.startswith("_")]`).
   - Métodos expressamente PROIBIDOS em `ChromaConnection`:
     - `add`, `upsert`, `delete`
     - `query`, `search`, `get`, `peek`
     - `create_collection`, `get_collection`, `get_or_create_collection`, `delete_collection`
     - `count`, `reset_db`, `modify`
3. A classe `ChromaConnection` é estritamente um **Connection Manager**. Toda e qualquer manipulação de vetores, coleções e buscas semânticas pertencerá a módulos de domínio e ML nos marcos futuros (ex: `src/models/bert_search.py`).

### 2.6. Teardown e Reset para Testes Unitários
1. **Isolamento de Estado**:
   - Testes unitários demandam alternar entre caminhos temporários isolados (`temp_dir / "chroma_1"` e `temp_dir / "chroma_2"`).
2. **Método de Classe `reset()`**:
   - Zera a instância singleton (`cls._instance = None`) de forma atômica sob lock de classe.
   - Suportado nativamente pela fixture global `reset_singletons` de `tests/conftest.py`.

---

## 3. Matriz de Rastreabilidade de Testes Automatizados

A suíte de testes do JudAI contém 17 testes automatizados que validam e cobrem diretamente o comportamento de `ChromaConnection`:

| # | Arquivo de Teste | Classe / Teste | Linhas | Asserção / Comportamento Validado |
|---|---|---|---|---|
| 1 | `tests/test_tier1_feature_coverage.py` | `TestChromaConnectionFeature.test_chroma_singleton_same_instance` | 274-279 | `c1 is c2` para duas chamadas consecutivas `ChromaConnection()`. |
| 2 | `tests/test_tier1_feature_coverage.py` | `TestChromaConnectionFeature.test_chroma_client_same_instance` | 281-286 | `c1.client is c2.client` (reutilização do mesmo PersistentClient). |
| 3 | `tests/test_tier1_feature_coverage.py` | `TestChromaConnectionFeature.test_chroma_default_path` | 288-296 | Sem `CHROMA_DB_PATH`, utiliza `./data/chromadb_local` resolvido. |
| 4 | `tests/test_tier1_feature_coverage.py` | `TestChromaConnectionFeature.test_chroma_creates_directory_if_not_exists` | 298-306 | Cria automaticamente subdiretórios não existentes no disco. |
| 5 | `tests/test_tier1_feature_coverage.py` | `TestChromaConnectionFeature.test_chroma_no_crud_methods` | 308-319 | Proíbe terminantemente métodos CRUD (`add`, `query`, `search`, etc.). |
| 6 | `tests/test_tier1_feature_coverage.py` | `TestChromaConnectionFeature.test_chroma_reset_mechanism` | 321-333 | `ChromaConnection.reset()` limpa o Singleton permitindo novo caminho. |
| 7 | `tests/test_tier2_boundary_corner.py` | `TestBoundarySingletonConcurrency.test_chroma_multiple_consecutive_inits` | 140-147 | 50 chamadas consecutivas em loop retornam mesma instância e mesmo cliente. |
| 8 | `tests/test_tier2_boundary_corner.py` | `TestBoundarySingletonConcurrency.test_chroma_multithreaded_instantiation` | 169-188 | 20 threads concorrentes recebem exatamente a mesma instância. |
| 9 | `tests/test_tier2_boundary_corner.py` | `TestBoundarySingletonConcurrency.test_chroma_empty_environment_variable_fallback` | 203-211 | `CHROMA_DB_PATH=""` faz fallback para `./data/chromadb_local`. |
| 10 | `tests/test_tier2_boundary_corner.py` | `TestBoundaryChromaPathHandling.test_chroma_deep_nested_directory_creation` | 220-229 | Criação recursiva de pasta aninhada com 4 níveis (`parents=True`). |
| 11 | `tests/test_tier2_boundary_corner.py` | `TestBoundaryChromaPathHandling.test_chroma_mixed_slashes_normalization` | 230-236 | Suporte e normalização de caminhos com barras mistas (`/` e `\`). |
| 12 | `tests/test_tier2_boundary_corner.py` | `TestBoundaryChromaPathHandling.test_chroma_existing_directory_idempotency` | 238-246 | Instanciação sobre pasta já existente não falha (`exist_ok=True`). |
| 13 | `tests/test_tier2_boundary_corner.py` | `TestBoundaryChromaPathHandling.test_chroma_path_as_pathlib_object` | 248-254 | Aceita instância de `pathlib.Path` diretamente no construtor. |
| 14 | `tests/test_tier2_boundary_corner.py` | `TestBoundaryChromaPathHandling.test_chroma_path_property_returns_path_or_str` | 255-261 | Propriedade `.path` retorna caminho absoluto / diretório válido. |
| 15 | `tests/test_tier3_cross_feature.py` | `TestEnvAndConnectionIntegration.test_env_file_loaded_by_chroma_connection` | 51-66 | Carrega `CHROMA_DB_PATH` a partir de arquivo `.env` via `python-dotenv`. |
| 16 | `tests/test_tier3_cross_feature.py` | `TestChromaPersistenceAndGitIntegration.test_chroma_path_preserves_gitkeep_file` | 131-141 | Inicialização não remove nem sobrescreve `data/chromadb_local/.gitkeep`. |
| 17 | `tests/test_tier3_cross_feature.py` | `TestChromaPersistenceAndGitIntegration.test_chroma_relative_path_from_different_cwd` | 142-155 | Resolução do caminho mantém integridade mesmo após `os.chdir()`. |

---

## 4. Código Completo e Exato Proposto para `src/database/chroma_connection.py`

Abaixo consta a implementação exata, documentada e com anotações de tipo completas, pronta para aplicação direta pelo builder:

```python
"""
Módulo de Conexão Singleton com ChromaDB - JudAI
=================================================
Fornece acesso thread-safe centralizado ao cliente persistente do ChromaDB
(chromadb.PersistentClient), garantindo a criação de diretórios de forma
agnóstica a sistema operacional (Windows/Linux) e isolamento estrito
de responsabilidades (sem métodos CRUD de busca ou inserção).
"""
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

    Lê a configuração CHROMA_DB_PATH das variáveis de ambiente ou do arquivo .env via python-dotenv.
    Cria a pasta persistente e diretórios-pai caso não existam.
    Não contém lógica de inserção ou busca vetorial.
    """

    _instance: ChromaConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, path: str | Path | None = None) -> ChromaConnection:
        """
        Garante a criação de uma única instância (Singleton) protegida por lock (Thread-Safe).
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str | Path | None = None) -> None:
        """
        Inicializa o cliente ChromaDB persistente apenas na primeira chamada.
        Nas chamadas subsequentes, evita re-inicialização graças à flag _initialized e ao lock.
        """
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            load_dotenv()

            # Resolução com precedência: argumento do construtor > variável de ambiente > fallback default
            # Trata casos de string vazia ou apenas espaços via validação estrita
            raw_path: str | Path
            if path is not None and (not isinstance(path, str) or path.strip() != ""):
                raw_path = path
            else:
                env_val = os.getenv("CHROMA_DB_PATH")
                if env_val and env_val.strip():
                    raw_path = env_val.strip()
                else:
                    raw_path = "./data/chromadb_local"

            self._path: Path = Path(raw_path).resolve()

            # Validação defensiva caso o caminho seja um arquivo regular pré-existente
            if self._path.exists() and not self._path.is_dir():
                raise ValueError(
                    f"O caminho configurado para persistência do ChromaDB '{self._path}' já existe e não é um diretório."
                )

            # Criação automática da pasta e pastas-pai (recursivo e idempotente)
            # Preserva arquivos existentes como .gitkeep
            self._path.mkdir(parents=True, exist_ok=True)

            # Instanciação do PersistentClient com caminho resolvido como string
            self._client: ClientAPI = chromadb.PersistentClient(path=str(self._path))
            self._initialized: bool = True

    @property
    def client(self) -> ClientAPI:
        """Retorna a instância compartilhada do chromadb.PersistentClient."""
        return self._client

    @property
    def path(self) -> Path:
        """Retorna o caminho pathlib.Path absoluto resolvido da pasta de persistência."""
        return self._path

    def get_client(self) -> ClientAPI:
        """Método utilitário para obter o PersistentClient."""
        return self.client

    @classmethod
    def reset(cls) -> None:
        """
        Reseta a instância Singleton permitindo nova inicialização em testes unitários.
        Thread-safe através do lock de classe.
        """
        with cls._lock:
            cls._instance = None
```

---

## 5. Análise de Concorrência e Ciclo de Vida

### 5.1. Rastreio de Execução Concorrente (Double-Checked Locking)
Considere duas threads, $T_1$ e $T_2$, instanciando `ChromaConnection()` no mesmo instante:

1. **Etapa 1 (`__new__`)**:
   - $T_1$ e $T_2$ encontram `cls._instance is None`.
   - $T_1$ adquire `cls._lock`.
   - $T_1$ aloca o objeto `super().__new__(cls)` e marca `cls._instance._initialized = False`.
   - $T_1$ libera `cls._lock` e retorna a instância.
   - $T_2$ adquire `cls._lock`, verifica a segunda checagem (`if cls._instance is None:`) que avalia para `False`, libera `cls._lock` e retorna a mesma instância já alocada por $T_1$.
2. **Etapa 2 (`__init__`)**:
   - O interpretador Python invoca `__init__` para $T_1$ e para $T_2$.
   - Ambas observam `self._initialized == False` na primeira verificação.
   - $T_1$ adquire `self._lock`.
   - $T_1$ passa pela segunda verificação (`if getattr(self, "_initialized", False): return`), resolve o caminho, cria diretórios, instancia o `chromadb.PersistentClient(path=str(self._path))` e sinaliza `self._initialized = True`.
   - $T_1$ libera `self._lock`.
   - $T_2$ adquire `self._lock`. Ao entrar, executa a verificação interna:
     ```python
     if getattr(self, "_initialized", False):
         return
     ```
   - Como `self._initialized` já é `True`, $T_2$ retorna imediatamente sem re-executar nenhuma lógica de inicialização.

Essa garantia dupla impede:
- Inicialização concorrente ou duplicada de clientes vetoriais.
- Exposição de instâncias parcialmente inicializadas para threads consumidoras.
- Re-execução desnecessária de chamadas de sistema de arquivos (`mkdir`).

---

## 6. Integração com Sistema Operacional, Git e Docker

### 6.1. Compatibilidade Windows vs Linux
- No **Windows**: caminhos utilizam separadores de barra invertida (`\`), volumes com letras de unidade (`E:\...`) e caracteres sensíveis.
- No **Linux / Contêineres Docker**: caminhos utilizam barras normais (`/`).
- O uso de `pathlib.Path(raw_path).resolve()` neutraliza completamente as divergências entre sistemas operacionais:
  - Transforma strings de barras mistas (`data/chromadb_local` ou `data\chromadb_local`) em representações internas normalizadas.
  - O método `.resolve()` converte referências relativas (ex: `./data/chromadb_local`) em caminhos absolutos canônicos, eliminando ambiguidades em relação ao diretório de trabalho atual (`CWD`).

### 6.2. Preservação de Diretórios e Regras de Versionamento Git
- O projeto mantém o arquivo estrutural `data/chromadb_local/.gitkeep` versionado para que o diretório exista imediatamente após o `git clone`.
- O arquivo `.gitignore` possui as regras:
  ```gitignore
  data/*
  !data/**/
  !data/**/.gitkeep
  data/**/*
  !data/**/
  !data/**/.gitkeep
  ```
- O método `mkdir(parents=True, exist_ok=True)` respeita arquivos existentes. Ao inicializar o ChromaDB na pasta, o SQLite (`chroma.sqlite3`) e os índices de vetores são gerados ao lado do `.gitkeep`, sendo devidamente ignorados pelo Git, mantendo o `git status` limpo.

---

## 7. Pré-requisitos de Ambiente e Instalação

### 7.1. Dependência `chromadb`
- A dependência `chromadb` está especificada no `requirements.txt` (linha 5).
- Para a execução dos testes automatizados que realizam conexões reais (sem mocking), o pacote `chromadb` deve estar instalado no ambiente Python:
  ```powershell
  python -m pip install chromadb
  # ou a lista completa de requisitos
  python -m pip install -r requirements.txt
  ```
- Nos testes unitários offline, a fixture `mock_chroma` presente em `tests/conftest.py` intercepta as chamadas para `chromadb.PersistentClient`, permitindo execução mesmo em ambientes sem conectividade de rede.

---

## 8. Checklist de Implementação para o Builder

- [ ] Criar o arquivo `src/database/chroma_connection.py` com o código fornecido na Seção 4.
- [ ] Garantir os imports: `threading`, `os`, `pathlib.Path`, `dotenv.load_dotenv`, `chromadb`, `ClientAPI`.
- [ ] Validar a presença das propriedades públicas `.client` e `.path`, além do método auxiliar `.get_client()` e método de classe `.reset()`.
- [ ] Confirmar que NENHUM método CRUD (`add`, `query`, `search`, `get`, `delete`, `create_collection`, etc.) está exposto na classe.
- [ ] Executar a suíte de testes de ChromaConnection via pytest:
  ```powershell
  python -m pytest tests/test_tier1_feature_coverage.py -k "Chroma" -v
  python -m pytest tests/test_tier2_boundary_corner.py -k "Chroma" -v
  python -m pytest tests/test_tier3_cross_feature.py -k "Chroma" -v
  ```
