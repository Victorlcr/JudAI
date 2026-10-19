## 2026-10-18T22:09:00Z
Você é o E2E Test Suite Designer & Writer (E2E Testing Track).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\test_writer_e2e_1
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você pode consultar as especificações técnicas em: e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\spec_api_database.md e e:\Programacao\JudAI\.agents\teamwork\explorer_survey_2\survey_infra_git.md

Sua missão:
1. Criar a arquitetura e suíte completa de testes E2E opacos e orientados a requisitos (Tiers 1-4) para o JudAI:
   - Tier 1: Feature Coverage (>=5 testes por feature: docker compose config, gitignore, singletons mongo/chroma, placeholders bm25/bert, api endpoints /health, /search/bm25, /search/bert, migração do scraper).
   - Tier 2: Boundary & Corner Cases (>=5 por feature: queries vazias, espaços, caracteres com acentos/símbolos jurídicos §, unicode, tipos inválidos, inicializações consecutivas do singleton).
   - Tier 3: Cross-Feature Combinations (integração entre .env e classes de conexão, api chamando modelos, persistência do chroma no caminho especificado).
   - Tier 4: Real-World Scenarios (fluxo de consulta ponta a ponta na API, execução do scraper em módulo).
2. Escrever os arquivos de teste no diretório do projeto `tests/`:
   - `tests/conftest.py`
   - `tests/test_tier1_feature_coverage.py`
   - `tests/test_tier2_boundary_corner.py`
   - `tests/test_tier3_cross_feature.py`
   - `tests/test_tier4_real_world.py`
   - E um test runner executável / independente `tests/run_all_tests.py` para executar os testes e reportar saída clara.
3. Criar a documentação de infraestrutura de testes em: e:\Programacao\JudAI\.agents\teamwork\TEST_INFRA.md
4. Ao concluir e validar a suíte de testes, criar o arquivo de sinalização e resumo de cobertura em: e:\Programacao\JudAI\.agents\teamwork\TEST_READY.md
5. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e os caminhos dos arquivos.
Lembre-se: Você escreve APENAS os testes e documentação de teste. NÃO modifique o código da implementação (src/).
