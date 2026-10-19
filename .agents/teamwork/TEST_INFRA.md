# Infraestrutura e Arquitetura de Testes E2E: JudAI

**Documento**: `TEST_INFRA.md`  
**Autor**: `test_writer_e2e_1` (E2E Test Suite Designer & Writer)  
**Data**: 2026-10-18  
**Versão**: 1.0.0  
**Status**: Concluído e Validado  

---

## 1. Visão Geral da Arquitetura de Testes

A suíte de testes do JudAI foi concebida sob uma abordagem **opaca, desacoplada e orientada a contratos e requisitos**. Ela valida o comportamento observável do sistema sem se acoplar a implementações internas efêmeras.

A suíte organiza-se em uma hierarquia de **4 Tiers de Teste** cobrindo desde a conformidade da infraestrutura e configuração até cenários reais e de estresse:

```text
tests/
├── conftest.py                   # Fixtures compartilhadas, isolamento de ambiente (.env) e teardown de Singletons
├── test_tier1_feature_coverage.py # Tier 1: Cobertura exaustiva por feature (>=5 testes por feature)
├── test_tier2_boundary_corner.py  # Tier 2: Casos de borda, concorrência, símbolos jurídicos, Unicode, tipos
├── test_tier3_cross_feature.py   # Tier 3: Combinações entre subsistemas (.env, banco, scraper, API, Docker)
├── test_tier4_real_world.py      # Tier 4: Cenários de ponta a ponta (E2E client workflow, parser real, dev setup)
└── run_all_tests.py              # Runner executável e independente (CLI unificada via Pytest ou standalone)
```

---

## 2. Estrutura dos Tiers de Teste

| Tier | Nome | Foco de Validação | Quantidade de Testes | Arquivo de Origem |
|---|---|---|---|---|
| **Tier 1** | **Feature Coverage** | Validação direta de contratos funcionais de cada feature base (Docker, Git, Singletons, Placeholders, API, Scraper). Mínimo de 5 testes por feature. | 42 | `tests/test_tier1_feature_coverage.py` |
| **Tier 2** | **Boundary & Corner Cases** | Entradas extremas, strings vazias, caracteres acentuados da língua portuguesa, símbolos jurídicos (`§`, `º`, `ª`), injeção de tipos inválidos, concorrência multi-thread e caminhos de SO. | 27 | `tests/test_tier2_boundary_corner.py` |
| **Tier 3** | **Cross-Feature Combinations** | Integração entre arquivo `.env` e Singletons, paridade de portas entre Docker e `.env.example`, conformidade de contratos entre API e modelos, isolamento do Chroma com `.gitkeep`. | 13 | `tests/test_tier3_cross_feature.py` |
| **Tier 4** | **Real-World Scenarios** | Fluxo de vida completo de cliente da API (`/health` -> `/search/bm25` -> `/search/bert`), carga concorrente com rajada de requisições, parsing real de fragmento de lei e onboarding. | 6 | `tests/test_tier4_real_world.py` |
| **Total** | **Suíte Completa** | **Cobertura 100% dos requisitos R1, R2, R3 e Critérios de Aceitação** | **88** | `tests/` |

---

## 3. Fixtures e Mecanismos de Isolamento (`conftest.py`)

Para assegurar testes herméticos, independentes e livres de efeitos colaterais entre execuções:

1. **`clean_env`**:
   - Salva uma captura completa do dicionário `os.environ` antes de cada teste.
   - Restaura o estado original no teardown, prevenindo vazamento de variáveis como `MONGO_URI`, `MONGO_DB_NAME` e `CHROMA_DB_PATH`.
2. **`reset_singletons`**:
   - Executa o reset estático de `MongoConnection` e `ChromaConnection` antes e depois de cada teste (via método de classe `.reset()` ou `_instance = None`).
   - Garante que cada teste execute com uma instância limpa, sem reaproveitamento acidental de clientes fechados.
3. **`temp_dir`**:
   - Gera diretórios temporários isolados no sistema de arquivos para validação de criação de pastas pelo ChromaDB ou geração de arquivos de lei de teste.
   - Garante remoção segura após a execução.
4. **`api_client`**:
   - Fornece um `fastapi.testclient.TestClient` conectado a `src.api.main:app`.
   - Gerencia skips amigáveis caso módulos da API ainda estejam em desenvolvimento em marcos anteriores.
5. **`mock_mongo` & `mock_chroma`**:
   - Permitem interceptar e simular chamadas de rede ao `pymongo.MongoClient` e `chromadb.PersistentClient` para testes de integração rápidos e sem dependência de containers ativos.

---

## 4. Test Runner Executável e Independente (`tests/run_all_tests.py`)

O runner foi desenvolvido para funcionar tanto em ambientes de desenvolvimento com `pytest` instalado quanto em ambientes mínimos via Python puro.

### Modos de Execução:

1. **Executar todos os testes (Tiers 1 a 4)**:
   ```bash
   python tests/run_all_tests.py
   ```
   *(ou via pytest diretamente: `python -m pytest tests/`)*

2. **Executar por Tier específico**:
   ```bash
   python tests/run_all_tests.py --tier 1
   python tests/run_all_tests.py --tier 2
   python tests/run_all_tests.py --tier 3
   python tests/run_all_tests.py --tier 4
   ```

3. **Modo Verboso (exibe cada teste com status individual)**:
   ```bash
   python tests/run_all_tests.py -v
   ```

4. **Modo Standalone (sem dependência do framework pytest)**:
   ```bash
   python tests/run_all_tests.py --standalone
   ```

---

## 5. Matriz de Rastreabilidade e Cobertura de Requisitos

| Requisito Original | Feature / Componente | Tiers que Cobrem | Asserções Principais |
|---|---|---|---|
| **R1. Estrutura** | `data/raw/.gitkeep`, `data/chromadb_local/.gitkeep`, `notebooks/.gitkeep` | Tier 1, Tier 3 | Existência dos 3 arquivos `.gitkeep`, não exclusão após instanciação do Chroma |
| **R1. Gitignore** | Exclusão de `venv/`, `.venv/`, `.env`, `__pycache__/`, `data/*` preservando `.gitkeep` | Tier 1, Tier 3 | Validação de regras e exceções no `.gitignore` |
| **R1. Gitattributes** | `* text=auto eol=lf` | Tier 1 | Verificação de normalização de quebra de linha LF |
| **R1. Docker** | `docker-compose.yml` (mongo:latest, 27017:27017, volume /data/db) | Tier 1, Tier 3 | Validação estrutural de serviço, mapeamento de portas e persistência em volume nomeado |
| **R1. Dependências** | `requirements.txt` (12 pacotes sem pin de versão) | Tier 1 | Verificação exata da lista de 12 dependências e ausência de operador `==` |
| **R1. Variáveis** | `.env.example` (`MONGO_URI`, `MONGO_DB_NAME`, `CHROMA_DB_PATH`) | Tier 1, Tier 3, Tier 4 | Template completo de variáveis, paridade de portas e teste de cópia para `.env` |
| **R2. Conexões** | `MongoConnection` (Singleton, .env, sem CRUD) | Tier 1, Tier 2, Tier 3 | `c1 is c2`, `c1.client is c2.client`, fallback de defaults, concorrência de 20 threads, ausência de CRUD |
| **R2. Conexões** | `ChromaConnection` (Singleton, .env, cria pasta, sem CRUD) | Tier 1, Tier 2, Tier 3 | `c1 is c2`, resolução agnóstica de path, criação recursiva de diretórios, concorrência, ausência de CRUD |
| **R2. Modelos** | `bm25_search.py` e `bert_search.py` (placeholders) | Tier 1, Tier 2, Tier 3 | Docstrings arquiteturais completas, `NotImplementedError` em fit/search/encode, import leve sem GPU |
| **R2. API** | `FastAPI`, `QueryRequest`, `GET /health`, `POST /search/bm25`, `POST /search/bert` | Tier 1, Tier 2, Tier 3, Tier 4 | Respostas 200 OK, mock estruturado `{model, query, results: [], detail: "not implemented"}`, validação 422 em inputs inválidos |
| **R2. Scraper** | Migração de `ingestao_lei.py` e `carregar_mongo.py` para `src/scraper/` | Tier 1, Tier 3, Tier 4 | Imports como módulo `src.scraper.*`, suporte a `.env`, preservação integral da lógica do parser |
| **R3. Onboarding** | Instruções Windows & Linux, inicialização sem separadores de SO hardcoded | Tier 1, Tier 4 | Validação de ausência de barras invertidas em caminhos de configuração |

---

## 6. Diretrizes de Execução Progressiva Durante os Marcos (Milestones)

Durante o desenvolvimento dos marcos M1 a M5, os testes fornecem feedback incremental:
- **Ao concluir M1**: Os testes de Docker Compose, `.gitignore`, `.gitattributes`, `.gitkeep`, `requirements.txt` e `.env.example` passam imediatamente.
- **Ao concluir M2**: Os testes de `MongoConnection` e `ChromaConnection` passam (Tiers 1, 2, 3).
- **Ao concluir M3**: Os testes de migração do scraper e placeholders ML passam (Tiers 1, 2, 3, 4).
- **Ao concluir M4**: Os testes de API FastAPI (`/health`, `/search/bm25`, `/search/bert`) passam (Tiers 1, 2, 3, 4).
- **No Milestone 5**: Todos os 88 testes passam com 100% de sucesso.
