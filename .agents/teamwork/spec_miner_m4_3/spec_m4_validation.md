# Especificação Formal de Validação e Testes: Milestone 4 (FastAPI API & Pydantic Validation)

**Projeto**: JudAI - RAG Híbrido Jurídico  
**Marco**: Milestone 4 (`src/api/` e Endpoints de Consulta)  
**Autor**: `spec_miner_m4_3` (Specification Miner)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Data**: 2026-10-18  
**Status**: Concluído e Auditado  

---

## 1. Visão Geral e Contexto Arquitetural

No Milestone 4 do JudAI, a infraestrutura atinge a camada de apresentação e interface de rede através do framework **FastAPI**:
1. **Camada de Apresentação e Roteamento (`src/api/main.py`)**:
   - Criação da instância central `app = FastAPI(...)` com metadados estruturados (título `"JudAI API"`, descrição da arquitetura de RAG híbrido jurídico e versão).
   - Disponibilização automática da documentação Swagger UI interativa em `/docs` e do esquema em `/openapi.json`.
   - Endpoint de verificação de disponibilidade operacional `GET /health` respondendo HTTP 200 com `{"status": "ok"}`.
   - Endpoints mockados de busca `POST /search/bm25` (recuperação léxica esparsa) e `POST /search/bert` (recuperação semântica densa), respondendo HTTP 200 com a estrutura canônica:
     ```json
     {
       "model": "bm25",
       "query": "<texto_da_query>",
       "results": [],
       "detail": "not implemented"
     }
     ```
2. **Validação de Dados e Schemas Pydantic (`QueryRequest`)**:
   - Modelo de entrada `QueryRequest(BaseModel)` com campo `query: str`.
   - Validação nativa que aceita queries de texto vazias `""`, consultas com múltiplos whitespaces/newlines, acentuação e caracteres jurídicos brasileiros (`§`, `º`, `ª`, `c/c`), Unicode e consultas extensas de até 10.000 caracteres.
   - Rejeição automática com HTTP 422 Unprocessable Entity para payloads sem a chave `query`, tipos primitivos incompatíveis (int, list, null) ou corpos JSON sintaticamente malformados.
3. **Restrição Semântica de Verbos HTTP**:
   - Rejeição nativa com HTTP 405 Method Not Allowed para verbos não autorizados (`GET /search/bm25`, `GET /search/bert`, `POST /health`, `PUT /health`, `DELETE /search/bm25`).
4. **Desacoplamento e Alinhamento com Modelos ML**:
   - Compatibilidade de assinaturas entre a query da API e o método `search(query, ...)` de `BM25Search` e `BERTSearch` (`src/models/`).
   - Sinalização clara de `detail: "not implemented"` em conformidade com o lançamento de `NotImplementedError` pelos placeholders.

Conforme especificado em `ORIGINAL_REQUEST.md (§R2 e Critérios de Aceitação)` e no planejamento `PROJECT.md (§Interface Contracts e Milestones)`:
- `uvicorn src.api.main:app` deve subir e responder 200 em `/health`, `/search/bm25` e `/search/bert`.
- Nenhuma lógica real de IA/ML deve ser executada nas rotas mockadas.
- O título no esquema OpenAPI (`spec["info"]["title"]`) deve ser obrigatoriamente `"JudAI API"`.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | API Core | Instanciação de `app` FastAPI | O módulo `src.api.main` instancia `app = FastAPI(...)` | `from src.api.main import app` | Instância válida de `fastapi.FastAPI` | `ImportError` ou falha de tipo se não for FastAPI | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 12`, `test_tier1_feature_coverage.py:417` |
| 2 | API Core | Título da Aplicação OpenAPI | A instância possui metadado `title="JudAI API"` exposto no OpenAPI | `GET /openapi.json` | `spec["info"]["title"] == "JudAI API"` | Falha de assertiva se diferente ou omitido | `PROJECT.md §Feature 12`, `test_tier4_real_world.py:72` |
| 3 | API Core | Endpoint `GET /health` | Rota de healthcheck que atesta integridade da API | `GET /health` | HTTP 200 com JSON `{"status": "ok"}` | 405 para métodos não-GET | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 13`, `test_tier1_feature_coverage.py:423` |
| 4 | API Core | Endpoint `POST /search/bm25` | Rota mockada de busca léxica BM25 | `POST /search/bm25` com `QueryRequest` | HTTP 200 com `{model: "bm25", query, results: [], detail: "not implemented"}` | 422 para payload inválido; 405 para GET | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 14`, `test_tier1_feature_coverage.py:431` |
| 5 | API Core | Endpoint `POST /search/bert` | Rota mockada de busca semântica BERT | `POST /search/bert` com `QueryRequest` | HTTP 200 com `{model: "bert", query, results: [], detail: "not implemented"}` | 422 para payload inválido; 405 para GET | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 14`, `test_tier1_feature_coverage.py:442` |
| 6 | Pydantic Schema | Modelo `QueryRequest` | Classe `QueryRequest(BaseModel)` contendo campo `query: str` | `QueryRequest(query="termo")` | Objeto válido com atributo `.query` | `ValidationError` se instanciado sem argumento | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 12`, `test_tier1_feature_coverage.py:453` |
| 7 | Documentation | Swagger UI em `/docs` | Interface gráfica interativa Swagger documentando a API | `GET /docs` | HTTP 200 com HTML text/html | 404 se desabilitado | `ORIGINAL_REQUEST §R3`, `test_tier1_feature_coverage.py:461` |
| 8 | Documentation | Esquema OpenAPI em `/openapi.json` | Especificação completa em JSON documentando endpoints | `GET /openapi.json` | HTTP 200 com JSON schema contendo caminhos `/health`, `/search/bm25`, `/search/bert` | 404 se desabilitado | `test_tier1_feature_coverage.py:464` |
| 9 | Boundary Cases | Query Vazia (`""`) | Aceitação de consulta com string vazia | `{"query": ""}` | HTTP 200 com `query == ""` | Não deve retornar 422 se não houver restrição min_length | `test_tier2_boundary_corner.py:36` |
| 10 | Boundary Cases | Whitespaces e Newlines | Consulta composta unicamente por espaços, tabs e quebras de linha | `{"query": "   \t\n   \r\n   "}` | HTTP 200 preservando o conteúdo exato de whitespace | Não deve colapsar ou disparar erro de validação | `test_tier2_boundary_corner.py:43` |
| 11 | Boundary Cases | Símbolos Jurídicos e Acentos | Preservação de símbolos do direito brasileiro: `§`, `º`, `ª`, `c/c`, acentos graves/agudos | `{"query": "... § 1º, inc. II..."}` | HTTP 200 com string intacta e sem mojibake | Caracteres corrompidos provocam falha | `test_tier2_boundary_corner.py:51` |
| 12 | Boundary Cases | Unicode Extremo, Aspas e Emojis | Preservação de aspas duplas, travessões (`—`) e emojis (`📚`, `🔍`) | `{"query": "... \"Dano moral\" — \U0001F4DA"}` | HTTP 200 com preservação exata | Falha se decodificação UTF-8 quebrar | `test_tier2_boundary_corner.py:59` |
| 13 | Boundary Cases | Payload Extremo (10.000 chars) | Carga pesada de texto de lei com 10.000 caracteres | `{"query": "Artigo 186..." * 180}` | HTTP 200 com len(query) == 10000 | Falha se truncar ou lançar timeout | `test_tier2_boundary_corner.py:67` |
| 14 | Error Handling | Payload Sem Campo `query` | Requisição POST com corpo vazio `{}` | `POST /search/bm25` com `{}` | HTTP 422 Unprocessable Entity | 200 ou 500 configuram violação grave | `test_tier2_boundary_corner.py:83` |
| 15 | Error Handling | Tipo Incorreto Inteiro | Campo `query` com tipo numérico `12345` em vez de string | `POST /search/bm25` com `{"query": 12345}` | HTTP 422 Unprocessable Entity | Rejeitado por coerção estrita ou validação Pydantic | `test_tier2_boundary_corner.py:88` |
| 16 | Error Handling | Tipo Incorreto Lista | Campo `query` com array de strings `["artigo", "186"]` | `POST /search/bert` com `{"query": [...]}` | HTTP 422 Unprocessable Entity | Falha se não rejeitar lista | `test_tier2_boundary_corner.py:93` |
| 17 | Error Handling | Valor Nulo (`null`/`None`) | Campo `query` com valor explícito `null` | `POST /search/bm25` com `{"query": null}` | HTTP 422 Unprocessable Entity | Falha se tratar null como string "None" | `test_tier2_boundary_corner.py:98` |
| 18 | Error Handling | JSON Malformado | Corpo HTTP com sintaxe inválida de JSON | `content=b"{query: invalid..."` com header `application/json` | HTTP 422 Unprocessable Entity | 500 configura erro de servidor não tratado | `test_tier2_boundary_corner.py:114` |
| 19 | HTTP Verbs | Verbo Incorreto em `/search/bm25` | Invocação via método `GET` em rota configurada para `POST` | `GET /search/bm25` | HTTP 405 Method Not Allowed | Falha se responder 404 ou 200 | `test_tier2_boundary_corner.py:105` |
| 20 | HTTP Verbs | Verbo Incorreto em `/search/bert` | Invocação via método `GET` em rota configurada para `POST` | `GET /search/bert` | HTTP 405 Method Not Allowed | Falha se responder 404 ou 200 | `test_tier2_boundary_corner.py:108` |
| 21 | HTTP Verbs | Verbo Incorreto em `/health` | Invocação via método `POST` em rota de healthcheck configurada para `GET` | `POST /health` com `{}` | HTTP 405 Method Not Allowed | Falha se responder 200 ou 404 | `test_tier2_boundary_corner.py:111` |
| 22 | Model Alignment | Paridade com `BM25Search.search` | A rota `/search/bm25` recebe a mesma chave `query` esperada por `BM25Search.search(query, ...)` | `inspect.signature(BM25Search.search)` | Parâmetro `"query"` presente na assinatura | Falha se assinatura for incompatível | `test_tier3_cross_feature.py:164` |
| 23 | Model Alignment | Paridade com `BERTSearch.search` | A rota `/search/bert` recebe a mesma chave `query` esperada por `BERTSearch.search(query, ...)` | `inspect.signature(BERTSearch.search)` | Parâmetro `"query"` presente na assinatura | Falha se assinatura for incompatível | `test_tier3_cross_feature.py:175` |
| 24 | Model Alignment | Semântica de `detail` Não Implementado | O detalhe retornado `not implemented` reflete o estado dos placeholders que lançam `NotImplementedError` | Resposta de `/search/bm25` e `/search/bert` | `data["detail"] == "not implemented"` | Falha se detail omitido ou divergente | `test_tier3_cross_feature.py:186` |
| 25 | E2E Lifecycle | Ciclo Completo de Consulta | Execução encadeada: Healthcheck -> Busca BM25 -> Busca BERT -> Inspeção OpenAPI | Sequência de 4 requisições | Todas respondem HTTP 200 com schemas íntegros | Falha se qualquer etapa intermediária quebrar | `test_tier4_real_world.py:38` |
| 26 | Concurrency | Rajada Concorrente Multi-Thread | Execução paralela de 30 requisições simultâneas distribuídas em 10 threads de trabalho | 30 requisições concorrentes intercaladas entre BM25 e BERT | Todas respondem HTTP 200 com detail 'not implemented' sem race condition | Travamento, 500 ou race condition reprovam o teste | `test_tier4_real_world.py:74` |
| 27 | Execution Block | Suporte a Execução Local `__main__` | `src/api/main.py` pode ser invocado via linha de comando direta com `uvicorn.run` condicional | `if __name__ == "__main__": uvicorn.run(...)` | Inicialização do servidor em porta 8000 | Falha se uvicorn executar durante importação de testes | `ORIGINAL_REQUEST §R3`, `PROJECT.md §Feature 12` |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | POST /search/bm25 | `{"query": ""}` | HTTP 200 retornado; campo `"query"` no JSON de resposta é a string vazia `""`. |
| 2 | POST /search/bert | `{"query": "   \t\n   \r\n   "}` | HTTP 200 retornado; todos os caracteres de espaço, tabulação e newlines permanecem intactos. |
| 3 | POST /search/bm25 | `{"query": "Ação de usucapião extraordinária c/c art. 1.238, parágrafo único § 1º, inc. II e alínea 'a' do CC/2002"}` | HTTP 200 retornado; acentos (`ã`, `á`, `ú`) e símbolos (`§`, `º`, `'`, `/`) preservados sem corrupção UTF-8. |
| 4 | POST /search/bert | `{"query": "Recurso Especial: \"Dano moral in re ipsa\" — Art. 186 & 927 do CC/2002 \u2014 \u00a7 2\u00ba \U0001F4DA \U0001F50D"}` | HTTP 200 retornado; aspas duplas, travessões Unicode e emojis preservados. |
| 5 | POST /search/bm25 | `{"query": ("Artigo 186. Aquele que, por ação ou omissão voluntária... " * 180)[:10000]}` | HTTP 200 retornado; tamanho da string retornada é exatamente 10.000 caracteres, processado sem latência excessiva. |
| 6 | POST /search/bm25 | `{}` (dicionário vazio sem chave `query`) | HTTP 422 Unprocessable Entity retornado pelo validador Pydantic; corpo de resposta detalha campo ausente (`loc: ['body', 'query']`). |
| 7 | POST /search/bm25 | `{"query": 12345}` | HTTP 422 Unprocessable Entity retornado (tipo inteiro incompatível com `str`). |
| 8 | POST /search/bert | `{"query": ["artigo", "186"]}` | HTTP 422 Unprocessable Entity retornado (tipo lista incompatível com `str`). |
| 9 | POST /search/bm25 | `{"query": null}` | HTTP 422 Unprocessable Entity retornado (valor nulo incompatível com campo obrigatório não-opcional). |
| 10 | POST /search/bm25 | Payload com sintaxe JSON malformada `b"{query: invalid_json_syntax"` | HTTP 422 Unprocessable Entity retornado na fase de decodificação do corpo JSON. |
| 11 | GET /search/bm25 | Método GET enviado para rota POST | HTTP 405 Method Not Allowed; cabeçalho `allow` inclui `POST`. |
| 12 | GET /search/bert | Método GET enviado para rota POST | HTTP 405 Method Not Allowed. |
| 13 | POST /health | Método POST enviado para rota GET | HTTP 405 Method Not Allowed. |
| 14 | PUT /health | Método PUT enviado para rota GET | HTTP 405 Method Not Allowed. |
| 15 | DELETE /search/bm25 | Método DELETE enviado para rota POST | HTTP 405 Method Not Allowed. |
| 16 | Concurrency Burst | 30 requisições disparadas simultaneamente por 10 threads paralelas | Todas as 30 requisições retornam HTTP 200 com payloads corretos em tempo inferior a 2.0s no total. |

---

## 4. Matriz Detalhada de Testes Existentes no Projeto

As classes de teste existentes no JudAI que incidem diretamente sobre a API FastAPI distribuem-se em 4 tiers:

### 4.1. Tier 1: Feature Coverage (`tests/test_tier1_feature_coverage.py`)
Classe `TestFastAPIEndpointsFeature` (linhas 414-470):
1. `test_fastapi_app_initialization`:
   - Verifica `from src.api.main import app` e assegura `isinstance(app, FastAPI)`.
2. `test_api_health_endpoint_returns_200`:
   - Envia `GET /health` via `api_client`.
   - Assegura `status_code == 200`, resposta do tipo dict e `data.get("status") == "ok"`.
3. `test_api_search_bm25_returns_200_mock`:
   - Envia `POST /search/bm25` com `{"query": "prescrição reparação civil"}`.
   - Assegura `status_code == 200`, `data["model"] == "bm25"`, `data["query"] == payload["query"]`, `data["results"] == []` e `data["detail"] == "not implemented"`.
4. `test_api_search_bert_returns_200_mock`:
   - Envia `POST /search/bert` com `{"query": "responsabilidade civil objetiva"}`.
   - Assegura `status_code == 200`, `data["model"] == "bert"`, `data["query"] == payload["query"]`, `data["results"] == []` e `data["detail"] == "not implemented"`.
5. `test_api_query_request_model`:
   - Importa `from src.api.main import QueryRequest`.
   - Instancia `QueryRequest(query="consulta teste")` e valida que `req.query == "consulta teste"`.
6. `test_api_openapi_and_docs_available`:
   - Envia `GET /docs` e valida `status_code == 200`.
   - Envia `GET /openapi.json`, valida `status_code == 200` e verifica que `schema["paths"]` contém `/health`, `/search/bm25` e `/search/bert`.

### 4.2. Tier 2: Boundary & Corner Cases (`tests/test_tier2_boundary_corner.py`)

#### Classe `TestBoundaryApiQueries` (linhas 33-75):
1. `test_query_empty_string`:
   - Envia `POST /search/bm25` com `{"query": ""}`.
   - Assegura `status_code == 200` e `json()["query"] == ""`.
2. `test_query_whitespace_and_newlines_only`:
   - Envia `POST /search/bert` com espaços, tabs e newlines `   \t\n   \r\n   `.
   - Assegura `status_code == 200` e preservação integral dos caracteres.
3. `test_query_brazilian_legal_symbols_and_accents`:
   - Envia `POST /search/bm25` com símbolos legais (`§`, `º`, `ª`, `c/c`) e termos jurídicos acentuados.
   - Assegura `status_code == 200` e ausência total de mojibake.
4. `test_query_unicode_extreme_and_quotes`:
   - Envia `POST /search/bert` com aspas duplas, travessão (`—`) e emojis (`📚`, `🔍`).
   - Assegura `status_code == 200` e preservação literal.
5. `test_query_large_payload_stress`:
   - Envia `POST /search/bm25` com string contínua de 10.000 caracteres de texto legislativo.
   - Assegura `status_code == 200` e `len(response.json()["query"]) == 10000`.

#### Classe `TestBoundaryApiValidationAndVerbs` (linhas 80-123):
1. `test_payload_missing_query_field`:
   - Envia `POST /search/bm25` com `{}`.
   - Assegura `status_code == 422`.
2. `test_payload_query_wrong_type_integer`:
   - Envia `POST /search/bm25` com `{"query": 12345}`.
   - Assegura `status_code == 422`.
3. `test_payload_query_wrong_type_list`:
   - Envia `POST /search/bert` com `{"query": ["artigo", "186"]}`.
   - Assegura `status_code == 422`.
4. `test_payload_query_null_value`:
   - Envia `POST /search/bm25` com `{"query": None}`.
   - Assegura `status_code == 422`.
5. `test_http_verbs_method_not_allowed`:
   - Envia `GET /search/bm25` -> valida `405`.
   - Envia `GET /search/bert` -> valida `405`.
   - Envia `POST /health` -> valida `405`.
6. `test_payload_malformed_json_body`:
   - Envia `POST /search/bm25` com `content=b"{query: invalid_json_syntax"` e header `application/json`.
   - Assegura `status_code == 422`.

### 4.3. Tier 3: Cross-Feature Combinations (`tests/test_tier3_cross_feature.py`)
Classe `TestFastApiAndModelIntegration` (linhas 161-194):
1. `test_api_bm25_contract_matches_model_signature`:
   - Inspeciona `BM25Search.search` e valida existência do parâmetro `"query"`.
   - Envia `POST /search/bm25` com `{"query": "art. 186"}` -> valida 200 e eco da query.
2. `test_api_bert_contract_matches_model_signature`:
   - Inspeciona `BERTSearch.search` e valida existência do parâmetro `"query"`.
   - Envia `POST /search/bert` com `{"query": "responsabilidade extracontratual"}` -> valida 200 e eco da query.
3. `test_api_mock_detail_signals_implementation_pending`:
   - Valida que ambas as rotas retornam `detail == "not implemented"`, alinhado ao comportamento de placeholder de ML.

### 4.4. Tier 4: Real-World Scenarios (`tests/test_tier4_real_world.py`)
Classe `TestRealWorldApiWorkflow` (linhas 35-94):
1. `test_complete_client_session_flow`:
   - Passo 1: `GET /health` -> 200, status "ok".
   - Passo 2: `POST /search/bm25` -> 200, mock léxico estruturado.
   - Passo 3: `POST /search/bert` -> 200, mock semântico estruturado.
   - Passo 4: `GET /openapi.json` -> 200, `spec["info"]["title"] == "JudAI API"`.
2. `test_concurrent_client_requests_burst`:
   - Dispara rajada de 30 requisições simultâneas em 10 threads paralelas alternando BM25 e BERT.
   - Assegura status 200 e ausência de falhas concorrentes.

---

## 5. Especificação Técnica Canônica de Interface

Para orientar a implementação pelo `worker_m4_1`, os contratos canônicos exatos são descritos a seguir:

### 5.1. Esquemas Pydantic
```python
from typing import Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., description="Termo ou texto da consulta jurídica")

class HealthResponse(BaseModel):
    status: str = "ok"

class SearchResponse(BaseModel):
    model: str
    query: str
    results: list[dict[str, Any]] = []
    detail: str = "not implemented"
```

### 5.2. Instância FastAPI
```python
app = FastAPI(
    title="JudAI API",
    description="API REST para busca e recuperação híbrida de legislação brasileira (JudAI)",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)
```

### 5.3. Endpoints Canônicos
```python
@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return {"status": "ok"}

@app.post("/search/bm25", response_model=SearchResponse, tags=["Search"])
def search_bm25(request: QueryRequest):
    return {
        "model": "bm25",
        "query": request.query,
        "results": [],
        "detail": "not implemented"
    }

@app.post("/search/bert", response_model=SearchResponse, tags=["Search"])
def search_bert(request: QueryRequest):
    return {
        "model": "bert",
        "query": request.query,
        "results": [],
        "detail": "not implemented"
    }
```

### 5.4. Bloco de Inicialização Local
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 6. Ferramenta de Verificação Independente (`verify_m4.py`)

Foi concebido e codificado o script independente executável:
`e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\verify_m4.py`

### Recursos do Script:
1. **Conexão Dinâmica e Auto-Suficiência**:
   - Detecta e testa `src.api.main:app` quando presente.
   - Fornece implementação de referência canônica embutida (`--use-reference`) para provar a validade do conjunto de 36 verificações de especificação antes ou durante o desenvolvimento.
2. **Cobertura Completa**:
   - 36 asserções divididas em 11 categorias cobrindo todos os requisitos e casos de borda.
3. **Execução Programática das Classes Pytest**:
   - Invoca os métodos de teste diretamente contra o cliente de teste, simulando 100% da suíte oficial sem depender de subprocessos bloqueados.

---

## 7. Checklist de Aceitação para o Milestone 4

| Item | Critério de Aceitação | Verificado por |
|---|---|---|
| 1 | Arquivo `src/api/main.py` existe com permissões corretas | `TestFastAPIEndpointsFeature` |
| 2 | `app` é instância de `fastapi.FastAPI` | `test_fastapi_app_initialization` |
| 3 | Título OpenAPI é estritamente `"JudAI API"` | `test_complete_client_session_flow` |
| 4 | `GET /health` responde HTTP 200 com `{"status": "ok"}` | `test_api_health_endpoint_returns_200` |
| 5 | `POST /search/bm25` responde HTTP 200 com payload estruturado | `test_api_search_bm25_returns_200_mock` |
| 6 | `POST /search/bert` responde HTTP 200 com payload estruturado | `test_api_search_bert_returns_200_mock` |
| 7 | `QueryRequest` exige `query: str` e valida tipos | `test_api_query_request_model`, `TestBoundaryApiValidationAndVerbs` |
| 8 | `/docs` e `/openapi.json` ativos e documentando todas as rotas | `test_api_openapi_and_docs_available` |
| 9 | Query vazia `""` aceita com HTTP 200 | `test_query_empty_string` |
| 10 | Símbolos jurídicos (`§`, `º`, `ª`) preservados sem mojibake | `test_query_brazilian_legal_symbols_and_accents` |
| 11 | Query com 10.000 caracteres aceita sem estouro | `test_query_large_payload_stress` |
| 12 | Payload vazio `{}` ou tipos int/list/null retornam HTTP 422 | `TestBoundaryApiValidationAndVerbs` |
| 13 | Verbos incorretos (GET em busca, POST em health) retornam HTTP 405 | `test_http_verbs_method_not_allowed` |
| 14 | Zero dependências pesadas carregadas estaticamente | Arquitetura desacoplada e mockada |
| 15 | Execução com uvicorn documentada e sem efeitos colaterais | Bloco `if __name__ == '__main__':` protegido |
