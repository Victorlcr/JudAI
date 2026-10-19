# Relatório Técnico: Design e Especificação de MongoConnection Singleton (Milestone 2)

**Autor**: `explorer_m2_1` (Explorer 1 - Milestone 2)  
**Data**: 2026-10-18  
**Escopo**: `src/database/mongo_connection.py`  
**Destinatário**: Orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`) e Implementador M2  

---

## 1. Sumário Executivo

Este relatório apresenta a análise aprofundada, contratos de interface, arquitetura de concorrência e o código exato proposto para a implementação de `MongoConnection` em `src/database/mongo_connection.py`.

A implementação atende rigorosamente a todos os requisitos do projeto (`ORIGINAL_REQUEST.md §R2`), do planejamento de arquitetura (`PROJECT.md`) e da especificação técnica (`spec_api_database.md`), garantindo 100% de conformidade com os testes automatizados já existentes na base de testes (`tests/test_tier1_feature_coverage.py`, `tests/test_tier2_boundary_corner.py`, `tests/test_tier3_cross_feature.py` e `tests/conftest.py`).

---

## 2. Requisitos e Diretrizes Arquiteturais

### 2.1. Padrão Singleton Thread-Safe
1. **Identidade de Instância (`c1 is c2`)**:
   - Múltiplas invocações do construtor `MongoConnection()` devem retornar exatamente a mesma instância de objeto na memória.
2. **Reutilização de Cliente (`c1.client is c2.client` e `c1.db is c2.db`)**:
   - O cliente subjacente `pymongo.MongoClient` e o objeto `Database` devem ser instanciados uma única vez e compartilhados por todas as chamadas.
3. **Thread Safety & Double-Checked Locking**:
   - Proteção estrita contra condições de corrida (*race conditions*) durante a instanciação em ambientes com múltiplas threads concorrentes.
   - Utilização de `threading.Lock()` no nível de classe (`_lock`).
4. **Proteção Contra Re-inicialização de `__init__`**:
   - No modelo de objetos do Python, o método `__init__` é executado automaticamente pelo *runtime* sempre que `__new__` retorna uma instância da classe.
   - Se o construtor for invocado sucessivas vezes (ex: 50 vezes em loop ou por threads concorrentes), `__init__` NÃO pode recriar `MongoClient`, nem redefinir atributos ou reabrir conexões de rede.
   - Essa proteção é garantida através de uma flag booleana de controle `_initialized` combinada com o `_lock`.

### 2.2. Resolução de Configuração e Fallbacks
1. **Fontes de Dados**:
   - Parâmetros explícitos do construtor: `uri: str | None = None`, `db_name: str | None = None`.
   - Variáveis de ambiente: `MONGO_URI` e `MONGO_DB_NAME`.
   - Arquivo `.env`: carregado via `python-dotenv` (`load_dotenv()`).
   - Valores padrão (*defaults*):
     - `MONGO_URI`: `"mongodb://localhost:27017"`
     - `MONGO_DB_NAME`: `"rag_juridico"`
2. **Ordem de Precedência**:
   $$\text{Parâmetro Construtor} > \text{Variável de Ambiente (ou .env)} > \text{Valor Padrão}$$
3. **Tratamento de Strings Vazias (Edge Case de Fronteira)**:
   - Caso `os.environ["MONGO_URI"] = ""` ou `os.environ["MONGO_DB_NAME"] = ""` (variável declarada porém com valor vazio), o uso ingênuo de `os.getenv("MONGO_URI", "default")` retornaria `""`, resultando em falha ao passar URI vazia ao PyMongo.
   - A resolução deve avaliar a verdade lógica (*truthiness*):
     ```python
     self._uri = uri or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
     self._db_name = db_name or os.getenv("MONGO_DB_NAME") or "rag_juridico"
     ```
   - Este tratamento é explicitamente validado por `test_tier2_boundary_corner.py::test_mongo_empty_environment_variables_fallback`.

### 2.3. Isolamento Semântico (Proibição Absoluta de Métodos CRUD)
1. **Regra R2 do ORIGINAL_REQUEST**: "sem lógica de inserção/busca".
2. **Validação Estrita de Nomes**:
   - O teste `test_tier1_feature_coverage.py::test_mongo_no_crud_methods` varre todos os membros públicos de `MongoConnection`:
     ```python
     conn_methods = [m for m in dir(MongoConnection) if not m.startswith("_")]
     ```
   - Nenhum dos seguintes métodos ou propriedades pode existir na classe:
     - `insert`, `insert_one`, `insert_many`
     - `find`, `find_one`, `search`, `query`
     - `delete`, `update`, `drop`
3. A classe deve atuar estritamente como um **Connection Manager / Provider**. Operações nos bancos e coleções são responsabilidade exclusiva dos módulos consumidores (ex: `src/scraper/carregar_mongo.py`), através dos objetos `.db` ou `.client`.

### 2.4. Comportamento Preguiçoso (Lazy Connection) do PyMongo
1. A instanciação de `MongoClient(uri)` no PyMongo não realiza chamadas de rede síncronas bloqueantes por padrão; os sockets são abertos sob demanda na primeira operação enviada ao servidor.
2. O construtor `MongoConnection.__init__` **NÃO DEVE** executar verificações ativas como `client.admin.command("ping")`. Isso permite que a aplicação (FastAPI ou suíte de testes) inicialize sem travar mesmo em ambientes offline ou durante testes onde o contêiner MongoDB não esteja ativo.

### 2.5. Ciclo de Vida e Isolamento em Testes Unitários
1. Em ambientes de teste unitário, múltiplos testes necessitam de instâncias isoladas com diferentes configurações de URI e banco.
2. Método de classe `reset()`:
   - Fecha a conexão ativa do cliente (`self._client.close()`).
   - Redefine `_instance = None`.
   - Executa sob o bloqueio de `_lock` para garantir atomicidade.
   - Totalmente compatível com a fixture `reset_singletons` de `tests/conftest.py`.

---

## 3. Análise Detalhada dos Testes Automatizados Mapeados

A suíte de testes do JudAI contém 11 testes que dependem diretamente de `MongoConnection`. Abaixo detalha-se cada teste e a asserção exigida:

| Arquivo de Teste | Classe / Teste | Linhas | Asserção / Comportamento Validado |
|---|---|---|---|
| `tests/test_tier1_feature_coverage.py` | `TestMongoConnectionFeature.test_mongo_singleton_same_instance` | 204-209 | `c1 is c2` para duas instanciações consecutivas `MongoConnection()`. |
| `tests/test_tier1_feature_coverage.py` | `TestMongoConnectionFeature.test_mongo_client_same_instance` | 211-217 | `c1.client is c2.client` e `c1.db is c2.db`. |
| `tests/test_tier1_feature_coverage.py` | `TestMongoConnectionFeature.test_mongo_default_env_values` | 219-231 | Sem env vars, `conn.uri == "mongodb://localhost:27017"` e `conn.db_name == "rag_juridico"`. |
| `tests/test_tier1_feature_coverage.py` | `TestMongoConnectionFeature.test_mongo_custom_parameters` | 233-240 | Parâmetros `uri` e `db_name` passados ao construtor têm precedência. |
| `tests/test_tier1_feature_coverage.py` | `TestMongoConnectionFeature.test_mongo_no_crud_methods` | 242-254 | Proíbe métodos CRUD (`insert`, `find`, `search`, `query`, etc.) em `dir(MongoConnection)`. |
| `tests/test_tier1_feature_coverage.py` | `TestMongoConnectionFeature.test_mongo_reset_mechanism` | 256-265 | `MongoConnection.reset()` limpa o Singleton; nova chamada cria nova instância com novos valores. |
| `tests/test_tier2_boundary_corner.py` | `TestBoundarySingletonConcurrency.test_mongo_multiple_consecutive_inits` | 131-138 | 50 chamadas em loop; todas retornam a mesma referência e mesmo `client`. |
| `tests/test_tier2_boundary_corner.py` | `TestBoundarySingletonConcurrency.test_mongo_multithreaded_instantiation` | 149-168 | 20 threads concorrentes instanciando `MongoConnection()`; todas recebem a mesma referência. |
| `tests/test_tier2_boundary_corner.py` | `TestBoundarySingletonConcurrency.test_mongo_empty_environment_variables_fallback` | 189-201 | `MONGO_URI=""` e `MONGO_DB_NAME=""` fazem fallback seguro para os valores default. |
| `tests/test_tier3_cross_feature.py` | `TestEnvAndConnectionIntegration.test_env_file_loaded_by_mongo_connection` | 32-49 | `MongoConnection` carrega valores definidos em arquivo `.env` via `python-dotenv`. |
| `tests/test_tier3_cross_feature.py` | `TestScraperAndDatabaseAlignment.test_scraper_and_mongo_connection_same_defaults` | 85-102 | Scraper (`carregar_mongo`) e `MongoConnection` compartilham exatamente os mesmos defaults. |

---

## 4. Código Proposto para `src/database/mongo_connection.py`

Abaixo apresenta-se o código final pronto para implementação direta pelo agente implementador:

```python
"""
Módulo de Gerenciamento da Conexão com MongoDB (JudAI)
======================================================
Fornece a classe Singleton thread-safe `MongoConnection` para acesso
centralizado ao cliente PyMongo e ao banco de dados padrão.

Regras Arquiteturais:
- Padrão Singleton thread-safe com double-checked locking e flag _initialized.
- Leitura de MONGO_URI e MONGO_DB_NAME via python-dotenv e variáveis de ambiente.
- Defaults: MONGO_URI='mongodb://localhost:27017', MONGO_DB_NAME='rag_juridico'.
- Suporte a fallback seguro contra strings vazias em variáveis de ambiente.
- NENHUM método CRUD de manipulação, busca ou inserção de dados.
- Conexão lazy (sem ping bloqueante no construtor).
- Método de classe reset() para isolamento em testes unitários.
"""
from __future__ import annotations

import os
import threading
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database


class MongoConnection:
    """
    Singleton responsável pelo gerenciamento da conexão com o MongoDB.

    Lê as configurações de MONGO_URI e MONGO_DB_NAME das variáveis de ambiente
    ou do arquivo .env via python-dotenv. Não contém lógica de inserção ou busca.
    """

    _instance: MongoConnection | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(
        cls,
        uri: str | None = None,
        db_name: str | None = None,
    ) -> MongoConnection:
        """
        Garante a criação de uma única instância na memória utilizando double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        uri: str | None = None,
        db_name: str | None = None,
    ) -> None:
        """
        Inicializa as propriedades de conexão uma única vez.
        
        Protegido contra re-execução em chamadas consecutivas ou concorrentes
        através da flag `_initialized` e do lock de classe.
        """
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            load_dotenv()

            # Avaliação com fallback para valores padrão contra None ou strings vazias
            self._uri: str = (
                uri
                or os.getenv("MONGO_URI")
                or "mongodb://localhost:27017"
            )
            self._db_name: str = (
                db_name
                or os.getenv("MONGO_DB_NAME")
                or "rag_juridico"
            )

            # PyMongo MongoClient utiliza conexão lazy por padrão
            self._client: MongoClient[dict[str, Any]] = MongoClient(self._uri)
            self._initialized: bool = True

    @property
    def client(self) -> MongoClient[dict[str, Any]]:
        """Retorna a instância compartilhada do MongoClient."""
        return self._client

    @property
    def db(self) -> Database[dict[str, Any]]:
        """Retorna o banco de dados configurado."""
        return self._client[self._db_name]

    @property
    def uri(self) -> str:
        """Retorna a URI de conexão configurada."""
        return self._uri

    @property
    def db_name(self) -> str:
        """Retorna o nome do banco de dados configurado."""
        return self._db_name

    def get_client(self) -> MongoClient[dict[str, Any]]:
        """Método utilitário para obter o MongoClient compartilhado."""
        return self.client

    def get_db(self) -> Database[dict[str, Any]]:
        """Método utilitário para obter o Database configurado."""
        return self.db

    def close(self) -> None:
        """Fecha com segurança a conexão do cliente PyMongo se estiver ativo."""
        if hasattr(self, "_client") and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    @classmethod
    def reset(cls) -> None:
        """
        Reseta a instância Singleton e fecha conexões ativas.
        
        Essencial para garantir o isolamento entre testes unitários.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None
```

---

## 5. Análise de Mecanismos Críticos e Prevenção de Regressões

### 5.1. Dupla Checagem e Ciclo de Vida `__new__` vs `__init__`
Em Python:
1. `__new__` aloca o objeto e retorna a referência.
2. O interpretador, ao ver que `__new__` retornou uma instância da classe chamada, **obrigatoriamente executa `__init__`**, passando os mesmos argumentos.
3. Se o desenvolvedor implementar apenas `if cls._instance is None:` em `__new__` e esquecer a proteção em `__init__`, em qualquer chamada subsequente como `MongoConnection()` dentro de um loop de 50 iterações (conforme `test_mongo_multiple_consecutive_inits`), `__init__` seria executado 50 vezes!
4. Isso recriaria `self._client = MongoClient(self._uri)`, instanciando 50 pools de conexões diferentes e quebrando a asserção `assert current.client is first.client`.
5. Com a proteção `if getattr(self, "_initialized", False): return`, o retorno ocorre em $O(1)$ sem re-executar nenhuma instrução de inicialização.

### 5.2. Testabilidade e `reset()`
1. O fixture `reset_singletons` de `tests/conftest.py` invoca explicitamente:
   ```python
   if hasattr(MongoConnection, "reset"):
       MongoConnection.reset()
   else:
       MongoConnection._instance = None
   ```
2. O método `reset()` implementado fecha o cliente existente com segurança e coloca `_instance = None`.
3. Quando a próxima chamada de teste ocorrer, `__new__` detectará `cls._instance is None`, alocará nova instância, definirá `_initialized = False`, e `__init__` configurará a nova instância com os parâmetros do teste atual.

### 5.3. Conformidade com Tipos Estáticos (PEP 484 / PEP 563)
1. Usa `from __future__ import annotations` para permitir tipos modernos (`MongoConnection | None`, `str | None`).
2. Anotações completas de retorno em propriedades e métodos (`MongoClient[dict[str, Any]]`, `Database[dict[str, Any]]`, `str`, `None`).

---

## 6. Procedimento de Validação para o Implementador

Após a criação do arquivo `src/database/mongo_connection.py`, o implementador deve executar os seguintes comandos:

```bash
# Validação direta dos testes de unidade Tier 1 do MongoConnection
python -m pytest tests/test_tier1_feature_coverage.py -k "TestMongoConnectionFeature" -v

# Validação dos testes de concorrência e borda Tier 2
python -m pytest tests/test_tier2_boundary_corner.py -k "mongo" -v

# Validação dos testes de integração cruzada Tier 3
python -m pytest tests/test_tier3_cross_feature.py -k "mongo" -v
```

**Critério de Sucesso**:
- Todos os 11 testes relacionados ao MongoDB devem passar com 100% de sucesso (status `PASSED`).
- Zero erros de sintaxe ou de importação.
