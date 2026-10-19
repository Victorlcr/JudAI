# Handoff Report — Milestone 4: Estrutura da API FastAPI e Endpoints

**Agent**: explorer_m4_1  
**Working Directory**: `e:\Programacao\JudAI\.agents\teamwork\explorer_m4_1`  
**Milestone**: Milestone 4 (Estrutura da API FastAPI e Endpoints)  
**Target Files**: `src/api/main.py`, `src/api/__init__.py`  
**Handoff Type**: Hard (Investigation complete, actionable code specification ready)

---

## 1. Observation

1. **Requisitos de Negócio e Arquitetura**:
   - `e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md`, linhas 16 e 26:
     > "src/api/main.py: FastAPI, Pydantic QueryRequest(query: str), GET /health retorna status da API, POST /search/bm25 e POST /search/bert com retorno mockado (ex.: {model, query, results: [], detail: not implemented})."
     > "Com dependências leves instaladas (fastapi, uvicorn, pydantic, pymongo, chromadb, python-dotenv, beautifulsoup4, lxml, requests), uvicorn src.api.main:app sobe e /health, /search/bm25, /search/bert respondem 200 (POST com {\"query\":\"x\"})."
   - `e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md`, linhas 76-87:
     > "API: FastAPI: Aplicação: `src.api.main:app`; Modelo de Entrada: `class QueryRequest(BaseModel): query: str`; Rotas: `GET /health` -> 200 OK `{\"status\": \"ok\"}`; `POST /search/bm25` -> 200 OK `{\"model\": \"bm25\", \"query\": request.query, \"results\": [], \"detail\": \"not implemented\"}`; `POST /search/bert` -> 200 OK `{\"model\": \"bert\", \"query\": request.query, \"results\": [], \"detail\": \"not implemented\"}`."

2. **Requisitos dos Testes Automatizados**:
   - `tests/test_tier1_feature_coverage.py`, linhas 417-470:
     - `test_fastapi_app_initialization`: requer `from src.api.main import app` e `isinstance(app, FastAPI)`.
     - `test_api_health_endpoint_returns_200`: `GET /health` deve retornar 200 e `data.get("status") == "ok"`.
     - `test_api_search_bm25_returns_200_mock`: `POST /search/bm25` com `{"query": "prescrição reparação civil"}` retorna 200 com chaves `"model": "bm25"`, `"query"`, `"results": []`, `"detail": "not implemented"`.
     - `test_api_search_bert_returns_200_mock`: `POST /search/bert` com `{"query": "responsabilidade civil objetiva"}` retorna 200 com chaves `"model": "bert"`, `"query"`, `"results": []`, `"detail": "not implemented"`.
     - `test_api_query_request_model`: requer `from src.api.main import QueryRequest`; instanciação `QueryRequest(query="consulta teste")` com `req.query == "consulta teste"`.
     - `test_api_openapi_and_docs_available`: `GET /docs` e `GET /openapi.json` respondem 200; paths `/health`, `/search/bm25`, `/search/bert` documentados.
   - `tests/test_tier2_boundary_corner.py`, linhas 33-122:
     - `test_query_empty_string`: aceita `query=""` retornando 200 e preservando `query`.
     - `test_query_whitespace_and_newlines_only`: aceita `query="   \t\n   \r\n   "` retornando 200.
     - `test_query_brazilian_legal_symbols_and_accents`: caracteres como `§`, `º`, `ª`, `c/c` e acentos preservados integralmente sem mojibake.
     - `test_query_large_payload_stress`: payload de 10.000 caracteres aceito com 200.
     - `test_payload_missing_query_field`: `{}` retorna 422.
     - `test_payload_query_wrong_type_integer`: `{"query": 12345}` retorna 422.
     - `test_payload_query_wrong_type_list`: `{"query": ["artigo", "186"]}` retorna 422.
     - `test_payload_query_null_value`: `{"query": None}` retorna 422.
     - `test_http_verbs_method_not_allowed`: `GET /search/bm25` -> 405, `GET /search/bert` -> 405, `POST /health` -> 405.
     - `test_payload_malformed_json_body`: JSON quebrado retorna 422.
   - `tests/test_tier3_cross_feature.py`, linhas 164-193:
     - Os métodos e campos dos endpoints e do modelo `QueryRequest` refletem os parâmetros esperados pelos métodos futuros `BM25Search.search(query, ...)` e `BERTSearch.search(query, ...)`.
   - `tests/test_tier4_real_world.py`, linhas 38-94:
     - `test_complete_client_session_flow`: valida o ciclo completo de cliente e checa estritamente `spec["info"]["title"] == "JudAI API"`.
     - `test_concurrent_client_requests_burst`: rajada de 30 requisições simultâneas em threads paralelas sem falhas ou contenção.
   - `tests/conftest.py`, linhas 110-120:
     - Fixture `api_client` importa `from src.api.main import app` e encapsula em `TestClient(app)`.

3. **Estado Atual do Filesystem**:
   - `src/api/__init__.py`: Existe apenas docstring de uma linha `"""Módulo de API REST (FastAPI) e rotas de consulta do JudAI."""`.
   - `src/api/main.py`: Ainda não existe.

---

## 2. Logic Chain

1. **Título da Instância FastAPI** (Observação 2 / `test_tier4_real_world.py` linha 72):
   - O teste requer expressamente `spec["info"]["title"] == "JudAI API"`.
   - Logo, a instanciação em `src/api/main.py` DEVE ser `app = FastAPI(title="JudAI API", ...)`.

2. **Modelo Pydantic `QueryRequest`** (Observações 1 e 2):
   - Os testes importam diretamente `from src.api.main import QueryRequest`.
   - Deve herdar de `pydantic.BaseModel` e ter o atributo `query: str`.
   - Como deve aceitar strings vazias e com whitespace (`test_query_empty_string`, `test_query_whitespace_and_newlines_only`), não deve ser usado validador customizado restritivo ou `min_length > 0`.
   - Pydantic v2 (instalado `2.9.2`) rejeita tipos incompatíveis (int, list, None) com `ValidationError`, fazendo o FastAPI retornar HTTP 422 conforme exigido pelos testes do Tier 2.

3. **Endpoints e Verbos HTTP** (Observação 2 / `test_tier2_boundary_corner.py` linha 104):
   - `/health` decorado exclusivamente com `@app.get(...)` para que qualquer outro método (como `POST /health`) retorne 405 Method Not Allowed.
   - `/search/bm25` e `/search/bert` decorados exclusivamente com `@app.post(...)` para que qualquer outro método (como `GET /search/bm25` ou `GET /search/bert`) retorne 405 Method Not Allowed.

4. **Payload Mockado Desacoplado** (Observações 1 e 2):
   - As respostas dos endpoints de busca devem retornar HTTP 200 com `model`, `query`, `results: []` e `detail: "not implemented"`.
   - A API não deve tentar instanciar ou chamar `BM25Search.search()` ou `BERTSearch.search()`, pois estes métodos propositalmente disparam `NotImplementedError` nesta fase de infraestrutura. Retornar os dicionários estruturados mockados cumpre 100% dos critérios de aceitação e suporta rajadas concorrentes em alta velocidade.

5. **Rotas de Documentação OpenAPI** (Observação 2 / `test_tier1_feature_coverage.py` linha 460):
   - As rotas padrão do FastAPI (`/docs` e `/openapi.json`) devem permanecer habilitadas (`docs_url="/docs"`, `openapi_url="/openapi.json"`).

6. **Bloco de Execução Uvicorn**:
   - O bloco condicional `if __name__ == "__main__":` deve conter import de `uvicorn` e `uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)` para permitir inicialização direta rápida.

---

## 3. Caveats

- **Autenticação e Rate Limiting**: Não foram solicitados para esta fase inicial de infraestrutura base (marcos futuros podem introduzir middlewares).
- **Semântica e Indexação de ML**: Zero lógica de ML foi conectada à API, respeitando o isolamento do escopo do RAG híbrido previsto para marcos posteriores.
- **Ambiente Pydantic**: A validação assume Pydantic v2 (instalado no ambiente como 2.9.2). Em Pydantic v2, `query: str` garante integridade estrita de tipo na desserialização de JSON.

---

## 4. Conclusion

A especificação técnica e o código proposto para `src/api/main.py` e `src/api/__init__.py` estão completamente definidos, documentados no relatório técnico `report_m4_api_structure.md` e 100% alinhados com todos os testes automatizados (Tiers 1 a 4) e com o plano do projeto. O executor do Milestone 4 pode aplicar as implementações propostas sem qualquer ambiguidade.

---

## 5. Verification Method

Após o executor escrever os arquivos `src/api/main.py` e `src/api/__init__.py`, a verificação deve ser realizada executando:

1. **Testes do Milestone 4 (FastAPI)**:
   ```powershell
   pytest tests/test_tier1_feature_coverage.py -k "TestFastAPIEndpointsFeature" -v
   pytest tests/test_tier2_boundary_corner.py -k "TestBoundaryApiQueries or TestBoundaryApiValidationAndVerbs" -v
   pytest tests/test_tier3_cross_feature.py -k "TestFastApiAndModelIntegration" -v
   pytest tests/test_tier4_real_world.py -k "TestRealWorldApiWorkflow" -v
   ```

2. **Verificação de Import e Título**:
   ```powershell
   python -c "from src.api.main import app, QueryRequest; assert app.title == 'JudAI API'; req = QueryRequest(query='art 186'); assert req.query == 'art 186'; print('API e Schemas OK!')"
   ```

3. **Condições de Invalidação**:
   - `spec["info"]["title"] != "JudAI API"` (falhará no Tier 4).
   - Ausência de `QueryRequest` em `src.api.main` (falhará no Tier 1).
   - Retorno de status diferente de 200 em `/health`, `/search/bm25` ou `/search/bert`.
   - Falha ao retornar 405 em `GET /search/bm25`, `GET /search/bert` ou `POST /health`.
   - Falha ao retornar 422 para payloads inválidos ou nulos.
