# DISPATCH — 2026-10-19T00:35:00Z

Você é o Worker 1 do Milestone 4 (Implementador da API REST FastAPI e Endpoints).
Seu diretório de trabalho exclusivo é: `e:\Programacao\JudAI\.agents\teamwork\worker_m4_1`

## Documentos Mandatórios para Leitura:
- `e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md`
- `e:\Programacao\JudAI\.agents\teamwork\explorer_m4_1\report_m4_api_structure.md`
- `e:\Programacao\JudAI\.agents\teamwork\explorer_m4_2\report_m4_validation.md`
- `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\spec_m4_validation.md`
- `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\verify_m4.py`

## Propriedade Exclusiva de Escrita (Write Ownership):
Você possui permissão exclusiva para criar/modificar apenas os seguintes arquivos:
- `src/api/main.py`
- `src/api/__init__.py`

## MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tarefas:
1. Criar `src/api/main.py`:
   - Instanciar `app = FastAPI(title="JudAI API", description="API REST do JudAI - Plataforma de RAG Híbrido Jurídico...", version="0.1.0", docs_url="/docs", openapi_url="/openapi.json")`.
   - Implementar o schema Pydantic `class QueryRequest(BaseModel): query: str = Field(...)`.
   - Implementar `GET /health` retornando `{"status": "ok"}` com status 200.
   - Implementar `POST /search/bm25` recebendo `request: QueryRequest` e retornando `{"model": "bm25", "query": request.query, "results": [], "detail": "not implemented"}` com status 200.
   - Implementar `POST /search/bert` recebendo `request: QueryRequest` e retornando `{"model": "bert", "query": request.query, "results": [], "detail": "not implemented"}` com status 200.
   - Adicionar bloco de execução condicional `if __name__ == "__main__": import uvicorn; uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)`.
2. Atualizar `src/api/__init__.py`:
   - Exportar `app` e `QueryRequest`.
3. Executar verificações de validação:
   - `python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\verify_m4.py`
   - `python -m pytest tests/test_tier1_feature_coverage.py -k "TestFastAPIEndpointsFeature" -v`
   - `python -m pytest tests/test_tier2_boundary_corner.py -k "TestBoundaryApiQueries or TestBoundaryApiValidationAndVerbs" -v`
   - `python -m pytest tests/test_tier3_cross_feature.py -k "TestFastApiAndModelIntegration" -v`
   - `python -m pytest tests/test_tier4_real_world.py -k "TestRealWorldApiWorkflow" -v`
4. Escrever relatório de handoff estruturado em: `e:\Programacao\JudAI\.agents\teamwork\worker_m4_1\handoff.md`.
5. Enviar mensagem de conclusão ao orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`).
