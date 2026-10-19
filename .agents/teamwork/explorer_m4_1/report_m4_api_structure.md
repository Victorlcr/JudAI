# Relatório Técnico: Especificação e Estrutura da API FastAPI e Endpoints (Milestone 4)

**Data**: 2026-10-19  
**Autor**: Explorer 1 (Milestone 4)  
**Status**: Concluído / Pronto para Implementação  
**Escopo**: Análise arquitetural e proposta exata de código para `src/api/main.py` e `src/api/__init__.py`.

---

## 1. Sumário Executivo

O Milestone 4 do projeto JudAI estabelece a camada de apresentação e API REST utilizando **FastAPI**, servindo como interface de consulta para a plataforma de RAG Híbrido Jurídico. A API provê:
1. Verificação de integridade e liveness via `GET /health` (retornando `{"status": "ok"}`).
2. Rota de busca léxica esparsa via `POST /search/bm25` (payload Pydantic `QueryRequest`, retornando mock estruturado com `detail="not implemented"`).
3. Rota de busca semântica densa via `POST /search/bert` (payload Pydantic `QueryRequest`, retornando mock estruturado com `detail="not implemented"`).
4. Documentação interativa Swagger UI (`/docs`) e especificação OpenAPI 3.x (`/openapi.json`) com título `"JudAI API"`.
5. Bloco de execução local direta via Uvicorn (`if __name__ == "__main__": uvicorn.run(...)`).

A investigação confirmou que os testes dos Tiers 1 a 4 cobrem exaustivamente os contratos, tipos, verbos HTTP (rejeição 405), limites de payload (strings vazias, espaços, acentuação e símbolos jurídicos como `§` e `º`), validação estrita (rejeição 422 para inteiros, listas, valores nulos e payloads malformados) e concorrência sob rajada de requisições.

---

## 2. Análise de Requisitos e Evidências Contratuais

### 2.1 Requisitos Originais (`ORIGINAL_REQUEST.md`)
- **Linha 16**: `src/api/main.py: FastAPI, Pydantic QueryRequest(query: str), GET /health retorna status da API, POST /search/bm25 e POST /search/bert com retorno mockado (ex.: {model, query, results: [], detail: not implemented}).`
- **Linha 26**: `Com dependências leves instaladas (fastapi, uvicorn, pydantic, pymongo, chromadb, python-dotenv, beautifulsoup4, lxml, requests), uvicorn src.api.main:app sobe e /health, /search/bm25, /search/bert respondem 200 (POST com {"query":"x"}).`
- **Linha 22**: Invocação padrão via CLI: `uvicorn src.api.main:app --reload` (documentação disponível em `/docs`).

### 2.2 Requisitos do Plano do Projeto (`PROJECT.md`)
- **Linhas 76-87**:
  - Aplicação: `src.api.main:app`
  - Modelo de Entrada:
    ```python
    class QueryRequest(BaseModel):
        query: str
    ```
  - Rotas:
    - `GET /health` -> 200 OK `{"status": "ok"}`
    - `POST /search/bm25` (Body: `QueryRequest`) -> 200 OK `{"model": "bm25", "query": request.query, "results": [], "detail": "not implemented"}`
    - `POST /search/bert` (Body: `QueryRequest`) -> 200 OK `{"model": "bert", "query": request.query, "results": [], "detail": "not implemented"}`

### 2.3 Contratos Mapeados na Suíte de Testes

| Arquivo de Teste | Classe / Teste | Requisito / Contrato Validado |
|---|---|---|
| `tests/test_tier1_feature_coverage.py` | `TestFastAPIEndpointsFeature.test_fastapi_app_initialization` | `from src.api.main import app`; `isinstance(app, FastAPI)` |
| `tests/test_tier1_feature_coverage.py` | `TestFastAPIEndpointsFeature.test_api_health_endpoint_returns_200` | `GET /health` retorna HTTP 200 e `data.get("status") == "ok"` |
| `tests/test_tier1_feature_coverage.py` | `TestFastAPIEndpointsFeature.test_api_search_bm25_returns_200_mock` | `POST /search/bm25` retorna HTTP 200, `model="bm25"`, `query=payload["query"]`, `results=[]`, `detail="not implemented"` |
| `tests/test_tier1_feature_coverage.py` | `TestFastAPIEndpointsFeature.test_api_search_bert_returns_200_mock` | `POST /search/bert` retorna HTTP 200, `model="bert"`, `query=payload["query"]`, `results=[]`, `detail="not implemented"` |
| `tests/test_tier1_feature_coverage.py` | `TestFastAPIEndpointsFeature.test_api_query_request_model` | `from src.api.main import QueryRequest`; `req = QueryRequest(query="consulta teste")`; `req.query == "consulta teste"` |
| `tests/test_tier1_feature_coverage.py` | `TestFastAPIEndpointsFeature.test_api_openapi_and_docs_available` | `GET /docs` responde 200; `GET /openapi.json` responde 200 e possui paths `/health`, `/search/bm25`, `/search/bert` |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiQueries.test_query_empty_string` | Query vazia `""` aceita com HTTP 200 e preservada |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiQueries.test_query_whitespace_and_newlines_only` | Query com espaços e `\n\t` aceita com HTTP 200 e preservada |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiQueries.test_query_brazilian_legal_symbols_and_accents` | Símbolos como `§`, `º`, `ª`, `c/c` e acentos rigorosamente preservados |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiQueries.test_query_unicode_extreme_and_quotes` | Aspas duplas/simples, travessões e emojis preservados |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiQueries.test_query_large_payload_stress` | Query de 10.000 caracteres aceita com HTTP 200 |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiValidationAndVerbs.test_payload_missing_query_field` | Payload `{}` sem campo `query` retorna HTTP 422 |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiValidationAndVerbs.test_payload_query_wrong_type_integer` | Tipo inteiro (`{"query": 12345}`) retorna HTTP 422 |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiValidationAndVerbs.test_payload_query_wrong_type_list` | Tipo lista (`{"query": ["artigo", "186"]}`) retorna HTTP 422 |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiValidationAndVerbs.test_payload_query_null_value` | Campo `query` nulo (`{"query": null}`) retorna HTTP 422 |
| `tests/test_tier2_boundary_corner.py` | `TestBoundaryApiValidationAndVerbs.test_http_verbs_method_not_allowed` | `GET /search/bm25` -> 405; `GET /search/bert` -> 405; `POST /health` -> 405 |
| `tests/test_tier3_cross_feature.py` | `TestFastApiAndModelIntegration` | Assinatura de `query` alinhada com `BM25Search.search` e `BERTSearch.search`; sinalização de `detail="not implemented"` consistente |
| `tests/test_tier4_real_world.py` | `TestRealWorldApiWorkflow.test_complete_client_session_flow` | Fluxo ponta a ponta: Health -> BM25 -> BERT -> OpenAPI (`spec["info"]["title"] == "JudAI API"`) |
| `tests/test_tier4_real_world.py` | `TestRealWorldApiWorkflow.test_concurrent_client_requests_burst` | Rajada de 30 requisições simultâneas em threads concorrentes sem falhas |

---

## 3. Decisões Arquiteturais

1. **Título e Metadados OpenAPI**:
   A instância FastAPI deve ser explicitamente instanciada com `title="JudAI API"`, conforme exigido pelo teste `test_complete_client_session_flow` (linha 72 de `tests/test_tier4_real_world.py`). Uma descrição rica da plataforma jurídica e versão `"0.1.0"` complementam a especificação.

2. **Desacoplamento de ML**:
   Os endpoints `/search/bm25` e `/search/bert` retornam diretamente o JSON mockado sem instanciar `BM25Search` ou `BERTSearch`. Isso garante conformidade com o requisito de não inicializar modelos pesados ou disparar `NotImplementedError`, além de manter tempos de resposta em microssegundos para as 30 requisições concorrentes do Tier 4.

3. **Validação Pydantic de `QueryRequest`**:
   O modelo `QueryRequest(BaseModel)` define `query: str`.
   - No Pydantic v2 (versão instalada `2.9.2`), tipos não compatíveis com string (como inteiros, listas e valores `None`) falham na validação e geram HTTP 422 automaticamente.
   - Não foi adicionada restrição de tamanho mínimo (`min_length`), permitindo queries vazias `""` e apenas com whitespace, em estrita conformidade com os testes de fronteira do Tier 2.

4. **Verbos HTTP e Roteamento**:
   - `/health` decorado apenas com `@app.get(...)`, fazendo com que requisições `POST` retornem automaticamente HTTP 405 Method Not Allowed.
   - `/search/bm25` e `/search/bert` decorados apenas com `@app.post(...)`, fazendo com que requisições `GET` retornem automaticamente HTTP 405 Method Not Allowed.

5. **Execução Local Condicional**:
   Adição do bloco `if __name__ == "__main__":` com import lazy de `uvicorn` e execução parametrizada (`host="0.0.0.0"`, `port=8000`, `reload=True`), permitindo iniciar a aplicação diretamente com `python -m src.api.main` ou `python src/api/main.py`.

---

## 4. Código Proposto para os Módulos

### 4.1 `src/api/__init__.py`

```python
"""Módulo de API REST (FastAPI) e rotas de consulta do JudAI."""
from __future__ import annotations

from src.api.main import QueryRequest, app

__all__ = ["app", "QueryRequest"]
```

### 4.2 `src/api/main.py`

```python
"""
Módulo Principal da API REST (FastAPI) - JudAI
==============================================
Fornece os endpoints HTTP da plataforma JudAI para verificação de disponibilidade
(healthcheck) e serviços de busca jurídica híbrida (léxica BM25 e semântica BERT).

Regras Arquiteturais e Contratuais:
- Título OpenAPI fixado em "JudAI API" para conformidade contratual.
- Documentação interativa em /docs (Swagger UI) e esquema em /openapi.json.
- Endpoints de busca retornam mocks estruturados {model, query, results: [], detail: "not implemented"}.
- Desacoplamento total de modelos de ML pesados nesta fase de infraestrutura base.
- Validação robusta de requisição via Pydantic QueryRequest(query: str).
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Schemas de Dados (Pydantic)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """
    Schema de requisição para busca jurídica (léxica BM25 ou semântica BERT).

    Atributos:
        query: Consulta textual em linguagem natural, citação de artigo ou termo jurídico.
    """

    query: str = Field(
        ...,
        description="Termo, citação de artigo (ex.: 'Art. 186') ou consulta jurídica em linguagem natural.",
        examples=["prescrição reparação civil", "Art. 1.240 Usucapião Especial Urbana"],
    )


# ---------------------------------------------------------------------------
# Instanciação da Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="JudAI API",
    description="API REST do JudAI - Plataforma de RAG Híbrido Jurídico para busca e recuperação de legislação brasileira.",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Endpoints da API
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    summary="Verificação de integridade e disponibilidade da API",
    tags=["Sistema"],
)
def health() -> dict[str, str]:
    """
    Retorna o status operacional da API.

    Returns:
        JSON com status 'ok' (HTTP 200).
    """
    return {"status": "ok"}


@app.post(
    "/search/bm25",
    summary="Busca léxica esparsa (BM25) em legislação",
    tags=["Busca"],
)
def search_bm25(request: QueryRequest) -> dict[str, Any]:
    """
    Endpoint mockado para busca léxica via BM25 (palavras-chave e artigos específicos).

    Args:
        request: Payload contendo a consulta jurídica textual.

    Returns:
        Dicionário estruturado com modelo 'bm25', query recebida, lista vazia
        de resultados e detalhe 'not implemented'.
    """
    return {
        "model": "bm25",
        "query": request.query,
        "results": [],
        "detail": "not implemented",
    }


@app.post(
    "/search/bert",
    summary="Busca semântica densa (BERT) em legislação",
    tags=["Busca"],
)
def search_bert(request: QueryRequest) -> dict[str, Any]:
    """
    Endpoint mockado para busca semântica via embeddings densos (BERT).

    Args:
        request: Payload contendo a consulta jurídica em linguagem natural.

    Returns:
        Dicionário estruturado com modelo 'bert', a query recebida, lista vazia
        de resultados e detalhe 'not implemented'.
    """
    return {
        "model": "bert",
        "query": request.query,
        "results": [],
        "detail": "not implemented",
    }


# ---------------------------------------------------------------------------
# Execução Local Direta
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 5. Plano de Validação Pós-Implementação

Após a implementação pelo agente responsável (executor), os seguintes passos devem ser executados para validar o Milestone 4:

1. **Execução da suíte de testes de FastAPI**:
   ```bash
   pytest tests/test_tier1_feature_coverage.py -k "TestFastAPIEndpointsFeature" -v
   pytest tests/test_tier2_boundary_corner.py -k "TestBoundaryApiQueries or TestBoundaryApiValidationAndVerbs" -v
   pytest tests/test_tier3_cross_feature.py -k "TestFastApiAndModelIntegration" -v
   pytest tests/test_tier4_real_world.py -k "TestRealWorldApiWorkflow" -v
   ```

2. **Verificação de Inicialização do Uvicorn**:
   Validar que o comando `python -c "from src.api.main import app; print(app.title)"` retorna `JudAI API`.

3. **Verificação dos Schemas OpenAPI**:
   Confirmar que `/docs` e `/openapi.json` incluem as 3 rotas documentadas (`/health`, `/search/bm25`, `/search/bert`).
