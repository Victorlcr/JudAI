## 2026-10-18T23:17:02Z
Você é o Spec Miner do Milestone 3 (Validação e Testes de Scraper e Modelos).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_3
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE analisar os testes existentes em: `tests/test_tier1_feature_coverage.py` (classes `TestMLModelPlaceholders` e `TestScraperMigrationFeature`), `tests/test_tier3_cross_feature.py` e `tests/test_tier4_real_world.py`.

Sua missão para o Milestone 3:
1. Mapear e especificar todos os testes unitários e critérios de aceitação para o Milestone 3:
   - `python -c "import src.scraper.ingestao_lei"` funciona sem erros.
   - `python -c "import src.scraper.carregar_mongo"` funciona sem erros.
   - `python -m src.scraper.carregar_mongo --help` ou execução sem parâmetros.
   - Remoção dos arquivos da raiz comprovada (`not exists("ingestao_lei.py")` e `not exists("carregar_mongo.py")`).
   - Import leve e instantâneo dos placeholders de ML sem dependências de PyTorch ou rede.
   - Testes de pytest para `TestMLModelPlaceholders` e `TestScraperMigrationFeature`.
2. Produzir o relatório de especificação em `spec_m3_validation.md` e um script de verificação executável em `verify_m3.py`.
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de especificação. NÃO modifique arquivos do projeto.
