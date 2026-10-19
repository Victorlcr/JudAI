# Handoff Report: ChromaConnection Singleton Design (Milestone 2)

**Agente**: `explorer_m2_2` (Explorer 2 - Milestone 2)  
**Parent / Destinatário**: Orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`)  
**Data**: 2026-10-18T22:42:00Z  
**Artefato Principal Produzido**: `e:\Programacao\JudAI\.agents\teamwork\explorer_m2_2\report_m2_chroma.md`  

---

## 1. Observation (O que foi diretamente observado)

1. **Requisitos de Negócio e Arquitetura**:
   - `ORIGINAL_REQUEST.md` (§R2, linhas 17): `"mongo_connection.py e chroma_connection.py: classes Singleton (pymongo MongoClient; chromadb.PersistentClient) usando variáveis de ambiente via python-dotenv; criar a pasta do Chroma se não existir; sem lógica de inserção/busca."`
   - `ORIGINAL_REQUEST.md` (Critérios de Aceitação, linha 27): `"- [ ] Duas instanciações de cada classe de conexão retornam o mesmo objeto."`
   - `PROJECT.md` (Interface Contracts, linhas 57-64): Especifica `ChromaConnection(path: str | Path | None = None)` com propriedades `client` (`chromadb.api.ClientAPI`), `path` (`pathlib.Path`), configuração `CHROMA_DB_PATH` (default `"./data/chromadb_local"`), criação via `mkdir(parents=True, exist_ok=True)` e proibição de métodos CRUD.
   - `spec_api_database.md` (linhas 170-244): Define interface de `ChromaConnection` com padrão Singleton, double-checked locking e método `reset()`.

2. **Testes Automatizados Pré-existentes**:
   - Foram localizados 17 testes automatizados que cobrem diretamente `ChromaConnection`:
     - `tests/test_tier1_feature_coverage.py` (linhas 271-333): 6 testes de identidade Singleton (`c1 is c2`), cliente idêntico (`c1.client is c2.client`), path default, criação de diretório, ausência de métodos CRUD e método `reset()`.
     - `tests/test_tier2_boundary_corner.py` (linhas 140-147, 169-188, 203-211, 220-261): 8 testes de concorrência com 20 threads simultâneas, 50 inits consecutivos, fallback de variável vazia `CHROMA_DB_PATH=""`, diretórios aninhados em 4 níveis (`parents=True`), barras mistas (`/` e `\`), diretório pré-existente e polimorfismo com `pathlib.Path`.
     - `tests/test_tier3_cross_feature.py` (linhas 51-66, 131-155): 3 testes de integração com arquivo `.env` via `load_dotenv()`, preservação do arquivo `data/chromadb_local/.gitkeep` e estabilidade de resolução sob alteração de diretório de trabalho (`os.chdir()`).
   - `tests/conftest.py` (linhas 70-78): O fixture `reset_singletons` executa `ChromaConnection.reset()` se a classe possuir tal método, ou redefine `ChromaConnection._instance = None`.

3. **Estado Atual do Codebase e Ambiente**:
   - `src/database/chroma_connection.py` ainda não existe no repositório.
   - `data/chromadb_local/.gitkeep` existe e está devidamente configurado com 1 byte.
   - Execução de `python -m pytest tests/test_tier1_feature_coverage.py -k "Chroma"` resultou em 6 falhas por `ModuleNotFoundError: No module named 'src.database.chroma_connection'`.
   - No ambiente Python 3.11 do sistema (`pip list`), `fastapi`, `uvicorn`, `pydantic`, `pymongo`, `python-dotenv` e `pytest` estão instalados; o pacote `chromadb` não estava presente no cache local do Python global, devendo ser instalado para testes com persistência real em disco.

---

## 2. Logic Chain (Cadeia de Raciocínio Passo a Passo)

1. **Premissa 1 (Padrão Singleton e Concorrência)**:
   - Como `tests/test_tier2_boundary_corner.py` (linhas 169-188) executa 20 threads simultâneas instanciando `ChromaConnection()`, e o interpretador Python sempre executa `__init__` após `__new__`, a classe exige double-checked locking tanto em `__new__` (para garantir uma única alocação de memória) quanto em `__init__` (com flag `_initialized` sob `_lock`) para evitar re-inicializações e travamentos concorrentes de arquivo no SQLite interno do ChromaDB.

2. **Premissa 2 (Resolução Cross-Platform e Fallbacks)**:
   - A especificação exige compatibilidade absoluta entre Windows e Linux.
   - O teste `test_tier2_boundary_corner.py::test_chroma_empty_environment_variable_fallback` exige que quando `CHROMA_DB_PATH=""` (string vazia), a classe faça fallback seguro para `"./data/chromadb_local"`.
   - Utilizar `Path(raw_path).resolve()` normaliza barras normais (`/`), barras invertidas (`\`) e converte caminhos relativos para absolutos canônicos, suportando polimorficamente `str` e `Path`.

3. **Premissa 3 (Criação Idempotente de Pastas e .gitkeep)**:
   - O teste `test_tier1_feature_coverage.py::test_chroma_creates_directory_if_not_exists` e `test_tier2_boundary_corner.py::test_chroma_deep_nested_directory_creation` exigem que caminhos inexistentes e aninhados sejam criados automaticamente.
   - Executar `self._path.mkdir(parents=True, exist_ok=True)` cria pastas intermediárias recursivamente e não lança exceção caso a pasta já exista.
   - Adicionalmente, `mkdir` não altera nem apaga arquivos já existentes no diretório, preservando integralmente `data/chromadb_local/.gitkeep` conforme testado em `test_tier3_cross_feature.py::test_chroma_path_preserves_gitkeep_file`.

4. **Premissa 4 (Isolamento Semântico)**:
   - A regra de negócio R2 e o teste `test_tier1_feature_coverage.py::test_chroma_no_crud_methods` proíbem expressamente qualquer método de busca, inserção ou coleção (`add`, `query`, `search`, `get`, `delete`, `create_collection`, etc.) em `ChromaConnection`.
   - Portanto, a classe deve expor unicamente as propriedades de conexão (`client`, `path`), o utilitário `get_client()` e o método de ciclo de vida `reset()`.

5. **Premissa 5 (Código Final Pronto para Aplicação)**:
   - Unificando essas premissas, a implementação completa foi projetada e documentada na Seção 4 de `report_m2_chroma.md`, pronta para ser aplicada pelo agente construtor do Milestone 2.

---

## 3. Caveats (Ressalvas e Suposições)

1. **Instalação da Dependência `chromadb`**:
   - `chromadb` consta no `requirements.txt`. Para a execução completa dos testes que instanciam o cliente real sem mock, o builder ou orquestrador deve garantir a execução de `pip install chromadb` no ambiente.
2. **Validação contra arquivos regulares**:
   - Caso um usuário configure `CHROMA_DB_PATH` apontando para um arquivo existente (ex: um `.txt` ou `.sqlite3`), `Path.mkdir` lançaria `FileExistsError`. Foi incluída uma validação defensiva que levanta `ValueError` explícito antes do `mkdir`.
3. **Escopo Read-Only**:
   - Como agente de exploração, nenhuma alteração em `src/` foi realizada nesta etapa.

---

## 4. Conclusion (Conclusão)

A arquitetura, os contratos de interface, as regras de concorrência e o código exato de `src/database/chroma_connection.py` estão 100% definidos, auditados contra os 17 testes existentes e documentados em `report_m2_chroma.md`. O Milestone 2 está pronto para a etapa de implementação pelo builder.

---

## 5. Verification Method (Método de Verificação Independente)

1. **Inspeção do Relatório Técnico**:
   - Verificar a existência e o conteúdo detalhado de:
     `e:\Programacao\JudAI\.agents\teamwork\explorer_m2_2\report_m2_chroma.md`
2. **Execução dos Testes Automatizados (pós-implementação pelo builder)**:
   ```powershell
   # Executar testes unitários do ChromaConnection (Tier 1)
   python -m pytest tests/test_tier1_feature_coverage.py -k "Chroma" -v

   # Executar testes de concorrência e fronteira (Tier 2)
   python -m pytest tests/test_tier2_boundary_corner.py -k "Chroma" -v

   # Executar testes cross-feature e integração com .env (Tier 3)
   python -m pytest tests/test_tier3_cross_feature.py -k "Chroma" -v
   ```
3. **Condição de Invalidação**:
   - O design seria invalidado se:
     - `ChromaConnection` expusesse qualquer método CRUD em `dir(ChromaConnection)`.
     - 20 threads simultâneas gerassem mais de uma instância na memória.
     - A criação de diretório removesse o arquivo `data/chromadb_local/.gitkeep`.
