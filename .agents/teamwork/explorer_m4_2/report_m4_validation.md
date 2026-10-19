# Relatório Técnico: Modelos Pydantic, Validação e Casos de Borda (Milestone 4)

**Agente**: Explorer 2 (`explorer_m4_2`)  
**Data**: 2026-10-19  
**Objetivo**: Analisar os modelos Pydantic, regras de validação de payload, integridade de codificação/Unicode e comportamento nativo de verbos HTTP para o módulo `src/api/main.py` do JudAI.

---

## 1. Sumário Executivo

A infraestrutura da API do JudAI (Milestone 4) baseia-se em FastAPI (v0.146.0) e Pydantic v2 (v2.9.2). O módulo `src/api/main.py` deve expor:
1. `GET /health`: retorna `{"status": "ok"}` com HTTP 200.
2. `POST /search/bm25`: consome payload com modelo `QueryRequest(query: str)` e retorna mock `{ "model": "bm25", "query": ..., "results": [], "detail": "not implemented" }`.
3. `POST /search/bert`: consome payload com modelo `QueryRequest(query: str)` e retorna mock `{ "model": "bert", "query": ..., "results": [], "detail": "not implemented" }`.

A análise aprofundada dos testes unitários, de borda (Tier 2), de integração cruzada (Tier 3) e de fluxos reais (Tier 4) estabelece critérios rigorosos para o modelo `QueryRequest`, para os schemas de resposta (`SearchResponse`, `HealthResponse`) e para o tratamento de erros HTTP (422 Unprocessable Entity e 405 Method Not Allowed).

---

## 2. Requisitos e Mapeamento de Testes

### 2.1. Casos de Borda de Queries (`TestBoundaryApiQueries` - `tests/test_tier2_boundary_corner.py`)

| Teste | Entrada Enviada | Comportamento Esperado | Justificativa / Validação |
| :--- | :--- | :--- | :--- |
| `1.1 test_query_empty_string` | `{"query": ""}` | HTTP 200, `query == ""` | Queries vazias são válidas sintaticamente no contrato da API. Não pode haver `min_length=1`. |
| `1.2 test_query_whitespace_and_newlines_only` | `{"query": "   \t\n   \r\n   "}` | HTTP 200, `query == "   \t\n   \r\n   "` | Whitespace e newlines devem ser preservados integralmente sem strip (`strip_whitespace=False`). |
| `1.3 test_query_brazilian_legal_symbols_and_accents` | `{"query": "Ação de usucapião extraordinária c/c art. 1.238, parágrafo único § 1º, inc. II e alínea 'a' do CC/2002"}` | HTTP 200, string idêntica | Preservação total de acentuação gráfica e caracteres do jargão jurídico brasileiro (§, º, ª, c/c, apóstrofos). |
| `1.4 test_query_unicode_extreme_and_quotes` | `{"query": 'Recurso Especial: "Dano moral in re ipsa" — Art. 186 & 927 do CC/2002 \u2014 \u00a7 2\u00ba \U0001F4DA \U0001F50D'}` | HTTP 200, string idêntica | Suporte total a aspas, travessões (em-dash), entidades Unicode e emojis sem quebra de serialização JSON. |
| `1.5 test_query_large_payload_stress` | `{"query": ("Artigo 186... " * 180)[:10000]}` (10.000 chars) | HTTP 200, `len(query) == 10000` | Não deve haver truncamento de payload ou limite arbitrário de caracteres inferior a 10.000 (`max_length` não deve ser restritivo). |

### 2.2. Validação de Payload e Verbos HTTP (`TestBoundaryApiValidationAndVerbs` - `tests/test_tier2_boundary_corner.py`)

| Teste | Entrada Enviada | Comportamento Esperado | Mecanismo de Execução |
| :--- | :--- | :--- | :--- |
| `2.1 test_payload_missing_query_field` | `{}` | HTTP 422 Unprocessable Entity | Pydantic acusa campo obrigatório ausente (`type='missing'`). `query: str` não deve ter valor default. |
| `2.2 test_payload_query_wrong_type_integer` | `{"query": 12345}` | HTTP 422 Unprocessable Entity | Pydantic v2 não realiza coerção permissiva de `int` para `str` em validação JSON (`type='string_type'`). |
| `2.3 test_payload_query_wrong_type_list` | `{"query": ["artigo", "186"]}` | HTTP 422 Unprocessable Entity | Pydantic v2 rejeita `list` onde se espera `str` (`type='string_type'`). |
| `2.4 test_payload_query_null_value` | `{"query": None}` | HTTP 422 Unprocessable Entity | Pydantic rejeita `None` pois `query` não é `Optional[str]`. |
| `2.5 test_http_verbs_method_not_allowed` | `GET /search/bm25`<br>`GET /search/bert`<br>`POST /health` | HTTP 405 Method Not Allowed | Roteador nativo do FastAPI/Starlette retorna 405 quando o método HTTP não está registrado na rota. |
| `2.6 test_payload_malformed_json_body` | `content=b"{query: invalid_json_syntax"` | HTTP 422 Unprocessable Entity | Parser de corpo do FastAPI falha na decodificação do JSON antes da validação do schema, gerando HTTP 422. |

### 2.3. Requisitos Contratuais Globais (Tiers 1, 3 e 4)

1. **Título da API no OpenAPI**: `test_tier4_real_world.py` (linha 72) exige expressamente:
   ```python
   assert spec["info"]["title"] == "JudAI API"
   ```
   Portanto, a instância deve ser obrigatoriamente instanciada como `FastAPI(title="JudAI API", ...)`.
2. **Import direto de `QueryRequest`**: `test_tier1_feature_coverage.py` (linha 455) faz:
   ```python
   from src.api.main import QueryRequest
   ```
   O modelo deve residir em `src.api.main` (e opcionalmente ser reexportado em `src/api/__init__.py`).
3. **Assinatura e campos do mock de busca**:
   Campos obrigatórios retornados em `/search/bm25` e `/search/bert`:
   - `model`: `"bm25"` ou `"bert"`
   - `query`: string exata recebida na requisição
   - `results`: `[]` (lista vazia)
   - `detail`: `"not implemented"`

---

## 3. Especificação Detalhada dos Modelos Pydantic

### 3.1. Modelo de Requisição: `QueryRequest`

```python
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    """
    Modelo de entrada para consultas na API JudAI.
    
    Regras de Validação:
    - Campo 'query' é estritamente obrigatório (sem valor default).
    - Tipo aceito: unicamente str (rejeita int, list, None e payloads vazios com 422).
    - Preserva integralmente espaços em branco, quebras de linha e caracteres especiais.
    - Suporta textos extensos de legislação (>= 10.000 caracteres).
    """
    query: str = Field(
        ...,
        description="Texto da consulta jurídica a ser processada pelos modelos de busca.",
        examples=["Ação de usucapião extraordinária c/c art. 1.238 do CC/2002"]
    )
```

#### Análise das Configurações do Campo `query`:
- **Por que `query: str` sem default?** Se colocássemos `query: str = ""`, requisições com `{}` passariam com valor `""`, violando o teste 2.1 que exige `422` para payload sem a chave `query`.
- **Por que NÃO usar `strip_whitespace=True`?** Se strip_whitespace fosse habilitado, a query `"   \t\n   \r\n   "` seria reduzida a `""` ou alterada, violando o teste 1.2 que exige retorno idêntico da query com espaços.
- **Por que NÃO usar `min_length=1`?** Pois o teste 1.1 envia explicitamente `{"query": ""}` e exige HTTP 200 com retorno de query vazia `""`.
- **Por que NÃO definir `max_length` restritivo?** O teste 1.5 valida uma query com 10.000 caracteres gerada a partir da repetição de artigos de lei. Deixar `query: str` sem limite superior artificial atende perfeitamente ao teste e evita truncamento.

---

### 3.2. Modelo de Resposta: `SearchResponse` (Swagger & Documentação)

Para garantir que a documentação OpenAPI gerada em `/docs` e `/openapi.json` seja rica, tipada e transparente para desenvolvedores, propõe-se o modelo estruturado de resposta:

```python
from typing import Any, List
from pydantic import BaseModel, Field

class SearchResponse(BaseModel):
    """
    Modelo padronizado de resposta para os endpoints de busca mockados.
    Documenta a estrutura contratual para os clientes da API JudAI.
    """
    model: str = Field(
        ...,
        description="Identificador do mecanismo de busca utilizado ('bm25' ou 'bert').",
        examples=["bm25", "bert"]
    )
    query: str = Field(
        ...,
        description="A query textual exata fornecida na requisição.",
        examples=["Ação de usucapião extraordinária"]
    )
    results: List[Any] = Field(
        default_factory=list,
        description="Lista de documentos legais recuperados (mockada como lista vazia na fase de infraestrutura)."
    )
    detail: str = Field(
        default="not implemented",
        description="Mensagem informativa sobre o estágio de implementação do endpoint.",
        examples=["not implemented"]
    )
```

### 3.3. Modelo de Resposta: `HealthResponse`

```python
class HealthResponse(BaseModel):
    """Modelo de resposta para verificação de disponibilidade operacional."""
    status: str = Field(
        default="ok",
        description="Status operacional da API JudAI.",
        examples=["ok"]
    )
```

---

## 4. Análise de Comportamento dos Verbos HTTP (HTTP 405)

O teste `test_http_verbs_method_not_allowed` em `tests/test_tier2_boundary_corner.py` valida:
1. `GET /search/bm25` -> `405 Method Not Allowed`
2. `GET /search/bert` -> `405 Method Not Allowed`
3. `POST /health` -> `405 Method Not Allowed`

### Como o FastAPI/Starlette Trata Métodos Inválidos Nativamente:
- No FastAPI, cada decorador (`@app.get(...)`, `@app.post(...)`) registra uma rota associada a um método HTTP específico no roteador (`starlette.routing.Router`).
- Quando uma requisição é recebida:
  1. O roteador busca um match de caminho (path).
  2. Se o caminho existe (ex: `/search/bm25`), mas o método da requisição (`GET`) não consta na lista de métodos permitidos para aquele caminho (`POST`), o Starlette retorna imediatamente uma resposta com código `405 Method Not Allowed` e insere o cabeçalho `Allow: POST, OPTIONS`.
  3. Da mesma forma, para `/health` registrado com `@app.get`, uma requisição `POST /health` resulta nativamente em `405 Method Not Allowed` com cabeçalho `Allow: GET, HEAD, OPTIONS`.
- **Conclusão**: Nenhuma lógica de middleware customizada ou interceptor de exceção é necessária. A declaração padrão das rotas no FastAPI satisfaz nativamente 100% dos requisitos do teste 2.5.

---

## 5. Implementação Completa Recomendada para `src/api/main.py`

Com base em todas as observações e regras validadas, a implementação exata para `src/api/main.py` recomendada para o worker de implementação é:

```python
"""
Módulo principal da API FastAPI do JudAI.
=========================================
Fornece os endpoints de disponibilidade (/health) e busca mockada (/search/bm25, /search/bert),
além da validação de payloads via modelos Pydantic e documentação OpenAPI/Swagger.
"""
from __future__ import annotations

from typing import Any, List
from fastapi import FastAPI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Modelos Pydantic (Entrada e Saída)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """
    Modelo de entrada para consultas na API JudAI.
    
    Validação:
    - O campo 'query' é obrigatório (ausência gera HTTP 422).
    - Deve ser uma string válida (tipos incorretos como int, list ou null geram HTTP 422).
    - Aceita strings vazias, com espaços/newlines, acentuação e caracteres jurídicos (§, º, ª).
    - Preserva integralmente o conteúdo da consulta sem truncamento.
    """
    query: str = Field(
        ...,
        description="Texto da consulta jurídica a ser processada.",
        examples=["Ação de usucapião extraordinária c/c art. 1.238 do CC/2002"]
    )


class SearchResponse(BaseModel):
    """Modelo estruturado de resposta para os endpoints de busca mockados."""
    model: str = Field(
        ...,
        description="Mecanismo de busca ('bm25' ou 'bert').",
        examples=["bm25"]
    )
    query: str = Field(
        ...,
        description="Query exata submetida na consulta."
    )
    results: List[Any] = Field(
        default_factory=list,
        description="Lista de dispositivos ou trechos legislativos recuperados."
    )
    detail: str = Field(
        default="not implemented",
        description="Status de implementação da camada de modelos."
    )


class HealthResponse(BaseModel):
    """Modelo de resposta para o endpoint de health check."""
    status: str = Field(
        default="ok",
        description="Status de prontidão da API."
    )


# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="JudAI API",
    description="API de Busca Híbrida e Recuperação de Legislação Jurídica Brasileira (RAG)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Rotas e Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["Monitoramento"],
    description="Verifica a disponibilidade operacional e prontidão da API JudAI."
)
def health() -> dict[str, str]:
    """Retorna o status operacional da API."""
    return {"status": "ok"}


@app.post(
    "/search/bm25",
    response_model=SearchResponse,
    summary="Busca Léxica (BM25)",
    tags=["Busca"],
    description="Executa busca léxica por termos em legislação (mock estrutural na infraestrutura base)."
)
def search_bm25(payload: QueryRequest) -> dict[str, Any]:
    """Endpoint mockado para busca BM25."""
    return {
        "model": "bm25",
        "query": payload.query,
        "results": [],
        "detail": "not implemented",
    }


@app.post(
    "/search/bert",
    response_model=SearchResponse,
    summary="Busca Semântica (BERT)",
    tags=["Busca"],
    description="Executa busca semântica em linguagem natural (mock estrutural na infraestrutura base)."
)
def search_bert(payload: QueryRequest) -> dict[str, Any]:
    """Endpoint mockado para busca BERT."""
    return {
        "model": "bert",
        "query": payload.query,
        "results": [],
        "detail": "not implemented",
    }
```

---

## 6. Verificação de Conformidade com a Suíte de Testes

| Requisito do Teste | Código Correspondente | Status da Análise |
| :--- | :--- | :---: |
| `app` é instância de `FastAPI` | `app = FastAPI(title="JudAI API", ...)` | ✅ Compatível |
| `spec["info"]["title"] == "JudAI API"` | `title="JudAI API"` | ✅ Compatível |
| `from src.api.main import QueryRequest` | `class QueryRequest(BaseModel)` exportada no topo | ✅ Compatível |
| `GET /health` responde 200 `{"status": "ok"}` | `@app.get("/health")` retornando `{"status": "ok"}` | ✅ Compatível |
| `POST /search/bm25` responde 200 mock | `@app.post("/search/bm25")` com payload | ✅ Compatível |
| `POST /search/bert` responde 200 mock | `@app.post("/search/bert")` com payload | ✅ Compatível |
| Query vazia `""` retorna 200 | `query: str` sem `min_length` | ✅ Compatível |
| Query só com whitespace/newlines | `query: str` sem `strip_whitespace` | ✅ Compatível |
| Símbolos jurídicos (§, º, ª) | UTF-8 nativo em JSONResponse | ✅ Compatível |
| Query longa de 10.000 chars | Sem `max_length` restritivo | ✅ Compatível |
| Payload `{}` ausente retorna 422 | `query: str = Field(...)` obrigatório | ✅ Compatível |
| Tipos int, list, null retornam 422 | Validador estrito de string do Pydantic v2 | ✅ Compatível |
| Verbos incorretos retornam 405 | Tratamento nativo Starlette/FastAPI | ✅ Compatível |
| JSON malformado retorna 422 | Parser nativo de requisição do FastAPI | ✅ Compatível |
| `/docs` e `/openapi.json` respondem 200 | Rotas Swagger nativas do FastAPI | ✅ Compatível |

---

## 7. Recomendações para o Worker e Auditor do Milestone 4

1. **Evitar qualquer manipulação manual da string da query**: Não realizar `strip()`, `clean()` ou conversões em `payload.query` dentro dos endpoints, pois os testes verificam a igualdade exata do texto enviado e retornado (`assert response.json()["query"] == payload["query"]`).
2. **Não adicionar middlewares complexos de validação de erro**: A validação padrão do FastAPI e Starlette já entrega exatamente os códigos HTTP (422 e 405) e a estrutura esperada pelo `TestClient`.
3. **Preservar `title="JudAI API"`**: Esse valor literal exato é validado em `test_tier4_real_world.py` (linha 72).
4. **Reexportar em `src/api/__init__.py`**: Adicionar imports de conveniência em `src/api/__init__.py`:
   ```python
   """Módulo de API REST (FastAPI) e rotas de consulta do JudAI."""
   from src.api.main import app, QueryRequest, SearchResponse, HealthResponse

   __all__ = ["app", "QueryRequest", "SearchResponse", "HealthResponse"]
   ```
