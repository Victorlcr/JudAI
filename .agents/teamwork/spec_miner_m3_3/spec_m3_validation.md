# Especificação Formal de Validação e Testes: Milestone 3 (Scraper & ML Placeholders)

**Projeto**: JudAI - RAG Híbrido Jurídico  
**Marco**: Milestone 3 (`src/scraper/` e `src/models/`)  
**Autor**: `spec_miner_m3_3` (Specification Miner)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Data**: 2026-10-18  
**Status**: Concluído e Auditado  

---

## 1. Visão Geral e Contexto Arquitetural

No Milestone 3 do JudAI, a arquitetura evolui na consolidação de dois pilares fundamentais:
1. **Camada de Ingestão e Raspagem Jurídica (`src/scraper/`)**: Migração definitiva dos scripts originais legados (`ingestao_lei.py` e `carregar_mongo.py`) da raiz do projeto para o pacote modular `src/scraper/`, com preservação integral de comentários, docstrings e algoritmos do parser do Planalto, padronização da leitura de configurações via `.env` (`MONGO_URI` e `MONGO_DB_NAME`), garantia de execução como módulo CLI (`python -m src.scraper.carregar_mongo`) e exposição das funções essenciais de parsing exigidas pela suíte de testes.
2. **Camada de Modelos e Recuperação (`src/models/`)**: Estabelecimento dos módulos estruturais placeholders de busca léxica (`bm25_search.py` com a classe `BM25Search`) e busca semântica densa (`bert_search.py` com a classe `BERTSearch`), cumprindo estritamente a diretriz do usuário de **zero código ativo de ML** nesta fase de infraestrutura base, fornecendo docstrings conceituais sobre o RAG híbrido, garantindo imports instantâneos (< 1.0s) sem carregar bibliotecas pesadas (`torch`, `sentence-transformers`, `transformers`) em tempo de importação e lançando `NotImplementedError` em todas as operações de busca, treinamento e codificação.

Conforme preconizado em `ORIGINAL_REQUEST.md (§R2 e Critérios de Aceitação)` e no planejamento `PROJECT.md (§Interface Contracts e Milestones)`:
- `python -c "import src.scraper.ingestao_lei"` deve funcionar sem erros.
- `python -c "import src.scraper.carregar_mongo"` deve funcionar sem erros.
- `python -m src.scraper.carregar_mongo --help` (ou sem parâmetros) deve responder sem `ModuleNotFoundError`.
- Os arquivos originais na raiz (`ingestao_lei.py` e `carregar_mongo.py`) devem ser removidos após a migração.
- As classes `BM25Search` e `BERTSearch` devem ser puras cascas estruturais (*placeholders*).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Scraper Migration | Pacote `src/scraper/` Estruturado | Diretório `src/scraper/` possui `__init__.py` e atua como pacote Python válido | N/A | Pacote importável no `sys.modules` | Falha se `__init__.py` ausente | `ORIGINAL_REQUEST §R1`, `PROJECT.md §Code Layout`, `test_tier1_feature_coverage.py:479` |
| 2 | Scraper Migration | Importabilidade de `ingestao_lei` | `src.scraper.ingestao_lei` é importável de forma isolada e em scripts | `import src.scraper.ingestao_lei` | Módulo carregado com sucesso | Não deve lançar `ImportError` ou `ModuleNotFoundError` | `ORIGINAL_REQUEST §Acceptance`, `test_tier1_feature_coverage.py:485` |
| 3 | Scraper Migration | Importabilidade de `carregar_mongo` | `src.scraper.carregar_mongo` é importável de forma isolada e em scripts | `import src.scraper.carregar_mongo` | Módulo carregado com sucesso | Não deve lançar `ImportError` ou `ModuleNotFoundError` | `ORIGINAL_REQUEST §R2`, `test_tier1_feature_coverage.py:491` |
| 4 | Scraper Migration | Remoção de Scripts da Raiz | Comprovação de que `ingestao_lei.py` e `carregar_mongo.py` foram excluídos da raiz | `not exists("ingestao_lei.py")`, `not exists("carregar_mongo.py")` | Arquivos ausentes da raiz do projeto | Falha se arquivos duplicados continuarem na raiz | `ORIGINAL_REQUEST §R2`, `PROJECT.md §M3`, `test_tier1_feature_coverage.py:520` |
| 5 | Scraper Migration | Preservação de Lógica e Docstrings | Comentários, docstrings e lógica original de parsing do Planalto integralmente mantidos | Código fonte de `ingestao_lei.py` e `carregar_mongo.py` | Texto e algoritmos preservados | Falha se funções históricas forem destruídas | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 9 e 10` |
| 6 | Scraper Migration | Import Modular com Fallback | `carregar_mongo.py` importa o parser via `from src.scraper import ingestao_lei as parser` com fallback para import local | N/A | Alias `parser` funcional em qualquer modo de invocação | Falha se import for hardcoded apenas relativo ou absoluto sem suporte CLI | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Interface Contracts` |
| 7 | Scraper Migration | Configuração via `.env` em `carregar_mongo` | Leitura de `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` com suporte a variáveis de ambiente | `.env` ou `os.environ` | `MONGO_URI` e `MONGO_DB_NAME` refletem o ambiente | Falha se não ler `.env` ou não possuir fallback | `ORIGINAL_REQUEST §R2`, `test_tier1_feature_coverage.py:512`, `test_tier3_cross_feature.py:104` |
| 8 | Scraper Migration | Defaults Idênticos a `MongoConnection` | Defaults de conexão idênticos: `MONGO_URI="mongodb://localhost:27017"` e `MONGO_DB_NAME="rag_juridico"` | Ambiente sem variáveis | Constantes iguais a `mongodb://localhost:27017` e `rag_juridico` | Inconsistência de defaults falha teste de integração cruzada | `PROJECT.md §Interface Contracts`, `test_tier3_cross_feature.py:85` |
| 9 | Scraper Migration | Execução CLI como Módulo | Invocação via linha de comando através de `python -m src.scraper.carregar_mongo` | Argumentos CLI (ex: `--help` ou fonte de lei) | Processo executa normalmente sem erro de importação | `ModuleNotFoundError` provoca falha imediata | `ORIGINAL_REQUEST §R2`, `test_tier4_real_world.py:137` |
| 10 | Scraper Migration | Fachada de Funções Essenciais de Parsing | `src.scraper.ingestao_lei` expõe as 5 funções requeridas: `baixar_legislacao`, `salvar_bruto`, `extrair_metadados`, `extrair_estrutura`, `extrair_dispositivos` | Strings HTML, URLs ou caminhos | Metadados (`dict`), dispositivos (`list`), estrutura (`list`), bytes | Falha se qualquer uma das 5 funções não existir ou não for chamável | `test_tier1_feature_coverage.py:498` |
| 11 | Scraper Migration | Funções Originais do Parser Mantidas | Mantidas as funções originais: `obter_bytes`, `decodificar`, `parsear`, `montar_colecoes`, `relatorio`, `salvar_mongo`, etc. | Bytes brutos, HTML | Documentos estruturados para MongoDB | `carregar_mongo` falha se essas funções forem renomeadas ou omitidas | `carregar_mongo.py:51-61`, `PROJECT.md §Feature 9` |
| 12 | Scraper Migration | Parsing Funcional de HTML do Planalto | Extração precisa de metadados e dispositivos a partir de fragmento HTML real de legislação | String HTML com tags do Planalto (`<p class="ementa">`, `<p id="art1">`, etc.) | `dict` de metadados e `list[dict]` de dispositivos não-vazia | Retorno vazio ou exceção não tratada falha o teste | `test_tier4_real_world.py:102-136` |
| 13 | ML Placeholders | Existência do Módulo `bm25_search` | Criação de `src/models/bm25_search.py` contendo a classe `BM25Search` | `from src.models.bm25_search import BM25Search` | Classe `BM25Search` instanciável | `ImportError` ou `AttributeError` se ausente | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 11`, `test_tier1_feature_coverage.py:342` |
| 14 | ML Placeholders | Docstring Explicativa em `bm25_search` | Docstrings do módulo e da classe detalham o papel do BM25 (recuperação léxica esparsa) e declaram que é um placeholder | Inspeção via `inspect.getdoc` | Docstrings contendo termos "bm25" e ("placeholder" ou "não implementad" ou "not implemented") | Falha se docstrings forem omitidas ou superficiais | `test_tier1_feature_coverage.py:350` |
| 15 | ML Placeholders | Método `BM25Search.fit()` Não Implementado | Método `fit(corpus)` existe com assinatura esperada e lança `NotImplementedError` | Lista de documentos ou corpus | `raise NotImplementedError` | Falha se executar treinamento ou levantar exceção incorreta | `test_tier1_feature_coverage.py:362` |
| 16 | ML Placeholders | Método `BM25Search.search()` Não Implementado | Método `search(query, top_k=5)` existe com parâmetro `query` e lança `NotImplementedError` | Query string e opcional `top_k` | `raise NotImplementedError` | Falha se executar busca ou omitir `query` da assinatura | `test_tier1_feature_coverage.py:362`, `test_tier3_cross_feature.py:164` |
| 17 | ML Placeholders | Existência do Módulo `bert_search` | Criação de `src/models/bert_search.py` contendo a classe `BERTSearch` | `from src.models.bert_search import BERTSearch` | Classe `BERTSearch` instanciável | `ImportError` ou `AttributeError` se ausente | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 11`, `test_tier1_feature_coverage.py:371` |
| 18 | ML Placeholders | Docstring Explicativa em `bert_search` | Docstrings do módulo e da classe detalham busca semântica densa/embeddings e declaram ser placeholder | Inspeção via `inspect.getdoc` | Docstrings contendo termos ("bert" ou "embedding" ou "semântic") e ("placeholder" ou "não implementad" ou "not implemented") | Falha se docstrings forem omitidas ou superficiais | `test_tier1_feature_coverage.py:378` |
| 19 | ML Placeholders | Método `BERTSearch.encode()` Não Implementado | Método `encode(texts)` existe com assinatura esperada e lança `NotImplementedError` | Lista de strings | `raise NotImplementedError` | Falha se executar inferência ou levantar exceção incorreta | `test_tier1_feature_coverage.py:392` |
| 20 | ML Placeholders | Método `BERTSearch.search()` Não Implementado | Método `search(query, top_k=5)` existe com parâmetro `query` e lança `NotImplementedError` | Query string e opcional `top_k` | `raise NotImplementedError` | Falha se executar busca ou omitir `query` da assinatura | `test_tier1_feature_coverage.py:392`, `test_tier3_cross_feature.py:175` |
| 21 | ML Placeholders | Atributo `model_name` em `BERTSearch` | Construtor aceita `model_name` customizado e o expõe publicamente via atributo | `model_name="neuralmind/bert-base-portuguese-cased"` | `bert.model_name == custom_model` | Falha se não aceitar parâmetro ou não armazenar o valor | `test_tier2_boundary_corner.py:298` |
| 22 | ML Placeholders | Desacoplamento e Import Leve | Imports dos módulos de modelos são instantâneos (< 1.0s) sem carregar bibliotecas pesadas | `import src.models.bm25_search`, `import src.models.bert_search` | Execução em fração de segundo (< 1.0s) | Falha se carregar PyTorch, HuggingFace ou baixar pesos da rede estaticamente | `ORIGINAL_REQUEST §R1-R2`, `test_tier1_feature_coverage.py:401` |
| 23 | ML Placeholders | Ausência de Pacotes Pesados no `sys.modules` | A importação de `src.models.*` NÃO carrega `torch`, `sentence_transformers` ou `transformers` | Inspeção de `sys.modules` | Pacotes pesados ausentes do `sys.modules` | Se presentes, indica importação desnecessária e pesada | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Models` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | BM25Search | `bm25.search("", top_k=0)` | Lança `NotImplementedError` imediatamente sem falhar por validação de tamanho de string ou divisão por zero em `top_k`. |
| 2 | BM25Search | `bm25.fit([])` | Lança `NotImplementedError` com corpus vazio, preservando o contrato de placeholder. |
| 3 | BM25Search | `bm25.fit(None)` ou corpus malformado | Lança `NotImplementedError` antes de qualquer verificação profunda de tipos. |
| 4 | BERTSearch | `bert.search("", top_k=0)` | Lança `NotImplementedError` imediatamente para query vazia e limite zero. |
| 5 | BERTSearch | `bert.encode([])` | Lança `NotImplementedError` para lista vazia de textos. |
| 6 | BERTSearch | `BERTSearch(model_name="custom/model-id")` | Atribui corretamente `self.model_name = "custom/model-id"`; chamadas a `search()` subsequentes continuam lançando `NotImplementedError`. |
| 7 | BERTSearch | `BERTSearch()` sem argumentos | Utiliza um modelo padrão brasileiro documentado (ex: `"neuralmind/bert-base-portuguese-cased"` ou `"sentence-transformers/paraphrase-multilingual-mpnet-base-v2"`) sem tentar carregar pesos da rede. |
| 8 | Model Imports | `time.perf_counter()` medindo `import src.models.bm25_search` e `import src.models.bert_search` | Tempo total de importação estritamente inferior a 1.0 segundo (normalmente < 50ms). |
| 9 | Scraper CLI | `python -m src.scraper.carregar_mongo --help` | ArgumentParser exibe a mensagem de ajuda sem lançar `ModuleNotFoundError`, saindo com código de término 0. |
| 10 | Scraper CLI | `python -m src.scraper.carregar_mongo` sem argumentos | Inicia fluxo padrão utilizando `FONTE_PADRAO` (URL do Código Civil compilado) e variáveis do `.env`. |
| 11 | Scraper Env | `os.environ["MONGO_URI"] = "mongodb://custom_host:27017"` e `os.environ["MONGO_DB_NAME"] = "custom_db"` | `carregar_mongo` adota os valores injetados dinamicamente no ambiente, sobrescrevendo defaults. |
| 12 | Scraper Env | Variáveis de ambiente ausentes no sistema | `carregar_mongo` adota `"mongodb://localhost:27017"` e `"rag_juridico"` como fallbacks seguros idênticos a `MongoConnection`. |
| 13 | Parser Parsing | HTML do Planalto com tags `<strike>` e `<p class="ementa">` | `extrair_metadados` extrai título e ementa; `extrair_dispositivos` extrai artigos ativos identificando redação anterior ou revogado. |
| 14 | Root Cleanup | Verificação da raiz do repositório após migração | `ROOT_DIR / "ingestao_lei.py"` e `ROOT_DIR / "carregar_mongo.py"` retornam `exists() == False`. |

---

## 2. Matriz Detalhada de Testes Existentes

Abaixo encontra-se a auditoria completa de todas as suítes e classes de teste que incidem sobre o Milestone 3:

### 2.1. Tier 1: Feature Coverage (`tests/test_tier1_feature_coverage.py`)

#### A. `TestMLModelPlaceholders` (7 testes automatizados)
1. `test_bm25_search_module_and_class_exist` (linhas 342-348):
   - Importa `src.models.bm25_search as bm25_mod`.
   - Verifica existência do atributo `BM25Search`.
   - Instancia `bm25_mod.BM25Search()` e valida que não é `None`.
2. `test_bm25_search_docstrings_present` (linhas 350-360):
   - Inspeciona docstrings do módulo e da classe via `inspect.getdoc`.
   - Valida menção ao termo `"bm25"`.
   - Valida presença de `"placeholder"`, `"não implementad"` ou `"not implemented"`.
3. `test_bm25_search_methods_raise_not_implemented` (linhas 362-369):
   - Valida que `bm25.fit([{"id": 1, "texto": "artigo 1"}])` lança `NotImplementedError`.
   - Valida que `bm25.search("prescrição", top_k=5)` lança `NotImplementedError`.
4. `test_bert_search_module_and_class_exist` (linhas 371-377):
   - Importa `src.models.bert_search as bert_mod`.
   - Verifica existência do atributo `BERTSearch`.
   - Instancia `bert_mod.BERTSearch()` e valida que não é `None`.
5. `test_bert_search_docstrings_present` (linhas 378-390):
   - Inspeciona docstrings do módulo e da classe via `inspect.getdoc`.
   - Valida menção a `"bert"`, `"embedding"` ou `"semântic"`.
   - Valida presença de `"placeholder"`, `"não implementad"` ou `"not implemented"`.
6. `test_bert_search_methods_raise_not_implemented` (linhas 392-399):
   - Valida que `bert.encode(["texto de dispositivo legal"])` lança `NotImplementedError`.
   - Valida que `bert.search("reparação civil", top_k=5)` lança `NotImplementedError`.
7. `test_models_import_fast_without_heavy_ml` (linhas 401-408):
   - Cronometra o import de `src.models.bm25_search` e `src.models.bert_search`.
   - Garante tempo de importação `< 1.0` segundo, atestando ausência de dependências pesadas carregadas estaticamente.

#### B. `TestScraperMigrationFeature` (6 testes automatizados)
1. `test_scraper_package_structure` (linhas 479-484):
   - Valida que o diretório `ROOT_DIR / "src" / "scraper"` existe.
   - Valida que `src/scraper/__init__.py` existe.
2. `test_scraper_ingestao_lei_importable` (linhas 486-490):
   - Valida que `import src.scraper.ingestao_lei as parser` é bem-sucedido e é um módulo Python.
3. `test_scraper_carregar_mongo_importable` (linhas 492-496):
   - Valida que `import src.scraper.carregar_mongo as loader` é bem-sucedido e é um módulo Python.
4. `test_scraper_parser_essential_functions_preserved` (linhas 498-510):
   - Valida que `ingestao_lei` possui e expõe as 5 funções essenciais de parsing:
     - `baixar_legislacao`
     - `salvar_bruto`
     - `extrair_metadados`
     - `extrair_estrutura`
     - `extrair_dispositivos`
   - Garante que todas são objetos chamáveis (`callable`).
5. `test_scraper_carregar_mongo_env_support` (linhas 512-518):
   - Lê o código de `src/scraper/carregar_mongo.py`.
   - Valida referências textuais a `"MONGO_URI"` e `"MONGO_DB_NAME"`.
   - Valida chamada de recuperação de ambiente (`"getenv"` ou `"environ"`).
6. `test_scraper_no_scripts_left_in_root` (linhas 520-527):
   - Valida que os scripts não permanecem na raiz (`ingestao_lei.py` e `carregar_mongo.py`).

---

### 2.2. Tier 2: Boundary & Corner Cases (`tests/test_tier2_boundary_corner.py`)

- **`TestBoundaryModelPlaceholdersInputs` (5 testes)**:
  1. `test_bm25_search_empty_query_raises_not_implemented` (linhas 270-276): `bm25.search("", top_k=0)` lança `NotImplementedError`.
  2. `test_bm25_fit_empty_corpus_raises_not_implemented` (linhas 277-283): `bm25.fit([])` com lista vazia lança `NotImplementedError`.
  3. `test_bert_search_empty_query_raises_not_implemented` (linhas 284-290): `bert.search("", top_k=0)` lança `NotImplementedError`.
  4. `test_bert_encode_empty_list_raises_not_implemented` (linhas 291-297): `bert.encode([])` lança `NotImplementedError`.
  5. `test_bert_custom_model_name_raises_not_implemented` (linhas 298-306):
     - Instanciação com `custom_model = "neuralmind/bert-base-portuguese-cased"`.
     - Asserção `assert bert.model_name == custom_model`.
     - `bert.search("relação de consumo", top_k=10)` lança `NotImplementedError`.

---

### 2.3. Tier 3: Cross-Feature Combinations (`tests/test_tier3_cross_feature.py`)

- **`TestScraperAndDatabaseAlignment` (2 testes)**:
  1. `test_scraper_and_mongo_connection_same_defaults` (linhas 85-103):
     - Assegura coerência absoluta entre os defaults do `MongoConnection` (`"mongodb://localhost:27017"` e `"rag_juridico"`) e as constantes do scraper `carregar_mongo.py`.
  2. `test_scraper_module_execution_with_custom_env` (linhas 104-123):
     - Injeta `MONGO_URI` e `MONGO_DB_NAME` customizados em `os.environ`.
     - Recarrega `src.scraper.carregar_mongo` e verifica que `scraper_module.MONGO_URI` e `scraper_module.MONGO_DB_NAME` refletem os valores do ambiente.

- **`TestFastApiAndModelIntegration` (3 testes)**:
  1. `test_api_bm25_contract_matches_model_signature` (linhas 164-174):
     - Inspeciona a assinatura de `BM25Search.search`: deve conter o parâmetro `"query"`.
  2. `test_api_bert_contract_matches_model_signature` (linhas 175-185):
     - Inspeciona a assinatura de `BERTSearch.search`: deve conter o parâmetro `"query"`.
  3. `test_api_mock_detail_signals_implementation_pending` (linhas 186-194):
     - Valida consistência conceitual entre o retorno `detail: "not implemented"` da API e os `NotImplementedError` dos modelos.

---

### 2.4. Tier 4: Real-World Scenarios (`tests/test_tier4_real_world.py`)

- **`TestRealWorldScraperExecution` (2 testes)**:
  1. `test_parser_real_html_snippet` (linhas 102-136):
     - Submete um snippet HTML do Código Civil (Lei 10.406/2002) com ementa e Artigos 1º a 3º e § 1º ao parser `src.scraper.ingestao_lei`.
     - Executa `meta = ingestao_lei.extrair_metadados(html_content, str(html_file))` e valida que é `dict`.
     - Executa `dispositivos = ingestao_lei.extrair_dispositivos(html_content)` e valida que é `list` com tamanho `> 0`.
  2. `test_scraper_module_cli_invocation_help` (linhas 137-154):
     - Executa via subprocesso: `python -m src.scraper.carregar_mongo --help`.
     - Valida ausência de `ModuleNotFoundError` no `stderr` e terminação limpa do comando.

---

## 3. Especificação de Contratos de Interface

### 3.1. `src/scraper/ingestao_lei.py`

#### Interface Histórica Preservada
Deve conter todas as funções originais para garantir que `carregar_mongo.py` e scripts legados continuem funcionando:
- `obter_bytes(entrada: str) -> tuple[bytes, str]`
- `decodificar(raw: bytes) -> str`
- `limpar(texto: str) -> str`
- `proporcao_riscada(p) -> float`
- `separar_notas(texto: str) -> tuple[str, list[str]]`
- `ordinal(n: str) -> str`
- `fmt_numero(bruto: str, sufixo: str | None) -> str`
- `rotulo_numero(numero: str) -> str`
- `classificar_cabecalho(texto: str)`
- `novo_no(tipo, numero, texto, p, **extra)`
- `parsear(html: str) -> tuple[dict, list[dict], list[str]]`
- `nomes_unicos(nos: list[dict], chave) -> dict[int, str]`
- `texto_plano(art: dict) -> str`
- `montar_colecoes(lei_id: str, lei_nome: str, meta: dict, artigos: list[dict], fonte: str, sha256: str, tem_acento_perdido: bool) -> dict`
- `relatorio(cols: dict, ignoradas: list[str], tem_acento_perdido: bool, n_fffd: int)`
- `gravar_jsonl(cols: dict, pasta: str)`
- `salvar_mongo(db, cols: dict, lei_id: str)`
- `main(argv=None)`
- Constante `FFFD = ""`

#### Interface Exposta para Testes (Fachada)
Para satisfazer `test_scraper_parser_essential_functions_preserved` e `test_parser_real_html_snippet`:
```python
def baixar_legislacao(url: str) -> bytes:
    """Baixa o conteúdo bruto (bytes) da legislação a partir de uma URL do Planalto."""
    conteudo, _ = obter_bytes(url)
    return conteudo

def salvar_bruto(conteudo: bytes | str, destino: str | Path) -> Path:
    """Salva os bytes brutos ou texto em disco no caminho especificado."""
    p = Path(destino)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, bytes):
        p.write_bytes(conteudo)
    else:
        p.write_text(conteudo, encoding="utf-8")
    return p

def extrair_metadados(html: str, caminho_ou_origem: str = "") -> dict[str, Any]:
    """Extrai metadados básicos (título, ementa, origem) do HTML da lei."""
    meta, _, _ = parsear(html)
    if caminho_ou_origem:
        meta["origem"] = str(caminho_ou_origem)
    return meta

def extrair_estrutura(html: str) -> list[dict[str, Any]]:
    """Extrai a estrutura hierárquica dos artigos, parágrafos, incisos e alíneas."""
    _, artigos, _ = parsear(html)
    return artigos

def extrair_dispositivos(html: str) -> list[dict[str, Any]]:
    """Extrai a coleção plana de dispositivos legais normalizados (vigentes e históricos)."""
    meta, artigos, _ = parsear(html)
    cols = montar_colecoes(
        lei_id="temp_lei",
        lei_nome=meta.get("titulo") or "Lei",
        meta=meta,
        artigos=artigos,
        fonte="snippet_html",
        sha256=hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest(),
        tem_acento_perdido=False
    )
    return cols["dispositivos"]
```

---

### 3.2. `src/scraper/carregar_mongo.py`

#### Configuração e Imports
```python
import os
import sys
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Import modular com fallback
try:
    from src.scraper import ingestao_lei as parser
except ImportError:
    try:
        import ingestao_lei as parser
    except ImportError:
        from . import ingestao_lei as parser

# Leitura dinâmica de ambiente com fallbacks oficiais
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", os.getenv("NOME_BANCO", "rag_juridico"))
NOME_BANCO = MONGO_DB_NAME
LEI_ID = "cc2002"
LEI_NOME = "Código Civil"
FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
```

---

### 3.3. `src/models/bm25_search.py`

```python
"""
Módulo de Busca Léxica BM25 (Placeholder Estrutural).
=====================================================
O algoritmo BM25 (Best Matching 25) atua na camada de recuperação esparsa (lexical retrieval)
do JudAI, realizando o casamento exato de termos jurídicos, números de artigos, citações
normativas e jargões processuais a partir de um índice invertido.

Nota de Arquitetura:
    Este módulo é um placeholder estrutural (não implementado).
    A lógica de tokenização jurídica, cálculo de pesos IDF e indexação BM25 será implementada
    em marcos futuros. Não carrega dependências pesadas em nível de módulo.
"""
from __future__ import annotations
from typing import Any


class BM25Search:
    """
    Placeholder estrutural para busca léxica via BM25.
    
    Responsável pela indexação e ranqueamento esparso de dispositivos legais.
    Atualmente não implementado (placeholder).
    """

    def __init__(self) -> None:
        """Inicializa o componente placeholder BM25."""
        pass

    def fit(self, corpus: list[dict[str, Any]]) -> None:
        """
        Treina / indexa o corpus de dispositivos normativos no índice BM25.
        
        Args:
            corpus: Lista de dicionários contendo os documentos a indexar.
            
        Raises:
            NotImplementedError: Sempre lançado (placeholder estrutural).
        """
        raise NotImplementedError("BM25Search.fit não está implementado na infraestrutura base.")

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Executa consulta léxica BM25 retornando os documentos mais relevantes.
        
        Args:
            query: Termo de busca ou citação legal (ex: 'art. 1.238 usucapião').
            top_k: Número máximo de resultados a retornar.
            
        Raises:
            NotImplementedError: Sempre lançado (placeholder estrutural).
        """
        raise NotImplementedError("BM25Search.search não está implementado na infraestrutura base.")
```

---

### 3.4. `src/models/bert_search.py`

```python
"""
Módulo de Busca Semântica Densa BERT (Placeholder Estrutural).
==============================================================
O modelo BERT (Bidirectional Encoder Representations from Transformers) atua na camada
de recuperação densa (semantic vector search) do JudAI, mapeando consultas em linguagem natural
e dispositivos legais para um espaço de embeddings semânticos densos, permitindo encontrar
artigos pertinentes mesmo quando não há sobreposição textual exata.

Nota de Arquitetura:
    Este módulo é um placeholder estrutural (não implementado).
    A lógica de geração de embeddings via sentence-transformers / bi-encoders e busca vetorial
    no ChromaDB será implementada em marcos futuros. Nenhum modelo neural é carregado na memória
    e nenhuma chamada de rede é realizada durante a importação.
"""
from __future__ import annotations
from typing import Any


class BERTSearch:
    """
    Placeholder estrutural para busca semântica densa via embeddings BERT.
    
    Responsável pela codificação vetorial e busca semântica em modelos de linguagem.
    Atualmente não implementado (placeholder).
    """

    DEFAULT_MODEL = "neuralmind/bert-base-portuguese-cased"

    def __init__(self, model_name: str | None = None) -> None:
        """
        Inicializa o componente placeholder BERT com modelo configurável.
        
        Args:
            model_name: Identificador do modelo HuggingFace (opcional).
        """
        self.model_name: str = model_name or self.DEFAULT_MODEL

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings densos para a lista de textos fornecida.
        
        Args:
            texts: Lista de sentenças ou dispositivos a codificar.
            
        Raises:
            NotImplementedError: Sempre lançado (placeholder estrutural).
        """
        raise NotImplementedError("BERTSearch.encode não está implementado na infraestrutura base.")

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Executa busca vetorial semântica densa a partir da query em linguagem natural.
        
        Args:
            query: Consulta em linguagem natural (ex: 'qual o prazo de reparação civil?').
            top_k: Número máximo de vizinhos mais próximos a recuperar.
            
        Raises:
            NotImplementedError: Sempre lançado (placeholder estrutural).
        """
        raise NotImplementedError("BERTSearch.search não está implementado na infraestrutura base.")
```

---

## 4. Instruções e Regras de Transição para o Worker M3

1. **Movimentação dos Arquivos**:
   - Copiar `ingestao_lei.py` -> `src/scraper/ingestao_lei.py` enriquecendo com a fachada de funções essenciais.
   - Copiar `carregar_mongo.py` -> `src/scraper/carregar_mongo.py` ajustando os imports e leitura de `.env`.
   - **Remover** definitivamente os arquivos `ingestao_lei.py` e `carregar_mongo.py` da raiz do repositório (`e:\Programacao\JudAI\`).
2. **Criação dos Modelos Placeholders**:
   - Criar `src/models/bm25_search.py` conforme contrato acima.
   - Criar `src/models/bert_search.py` conforme contrato acima.
3. **Restrições Absolutas de ML**:
   - PROIBIDO importar `torch`, `sentence_transformers` ou `transformers` no escopo global de `bm25_search.py` ou `bert_search.py`.
   - PROIBIDO realizar qualquer chamada de rede ou download de pesos.
4. **Validação**:
   - Executar `verify_m3.py` para atestar 100% de conformidade com todos os critérios do Milestone 3.
