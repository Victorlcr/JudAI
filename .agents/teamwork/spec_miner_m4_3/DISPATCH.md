## 2026-10-19T00:27:45Z
Você é o Spec Miner do Milestone 4 (Especificação de Testes e Validação da API FastAPI).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE analisar os testes existentes em:
- `tests/test_tier1_feature_coverage.py:TestFastAPIEndpointsFeature`
- `tests/test_tier2_boundary_corner.py:TestBoundaryApiQueries` e `TestBoundaryApiValidationAndVerbs`
- `tests/test_tier3_cross_feature.py:TestFastApiAndModelIntegration`
- `tests/test_tier4_real_world.py:TestRealWorldApiWorkflow`

Sua missão para o Milestone 4:
1. Mapear e especificar formalmente todos os critérios de aceitação e testes para o Milestone 4.
2. Criar um script de verificação executável e independente em: `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\verify_m4.py`.
   - O script deve testar diretamente via `fastapi.testclient.TestClient`:
     - Instanciação de `app` e tipo FastAPI.
     - `GET /health` -> 200 `{"status": "ok"}`.
     - `POST /search/bm25` -> 200 com payload mockado correto (`model`, `query`, `results`, `detail`).
     - `POST /search/bert` -> 200 com payload mockado correto.
     - `/docs` e `/openapi.json` -> 200 com `spec["info"]["title"] == "JudAI API"`.
     - Casos de borda: query vazia `""`, símbolos jurídicos brasileiros (`§`, `º`, `ª`), query com 10.000 caracteres.
     - Validação de erros: payload vazio -> 422, tipo inválido -> 422, verbo incorreto -> 405.
     - Execução de comandos pytest direcionados.
3. Produzir relatório de especificação em: `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\spec_m4_validation.md`.
4. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de especificação. NÃO modifique arquivos do projeto.
