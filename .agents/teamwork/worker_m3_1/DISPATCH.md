## 2026-10-18T23:24:44Z
Você é o Worker 1 do Milestone 3 (Scraper Migration e Placeholders de ML).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\worker_m3_1

Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE ler os relatórios dos exploradores e códigos propostos:
- e:\Programacao\JudAI\.agents\teamwork\explorer_m3_1\report_m3_scraper.md
- e:\Programacao\JudAI\.agents\teamwork\explorer_m3_1\proposed_ingestao_lei.py
- e:\Programacao\JudAI\.agents\teamwork\explorer_m3_1\proposed_carregar_mongo.py
- e:\Programacao\JudAI\.agents\teamwork\explorer_m3_2\report_m3_models.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_3\spec_m3_validation.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_3\verify_m3.py

Propriedade Exclusiva de Escrita (Write Ownership):
Você possui permissão exclusiva para criar/modificar/remover apenas os seguintes arquivos:
- src/scraper/ingestao_lei.py
- src/scraper/carregar_mongo.py
- src/scraper/__init__.py
- src/models/bm25_search.py
- src/models/bert_search.py
- Remoção de ingestao_lei.py e carregar_mongo.py da raiz do projeto.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Sua missão para o Milestone 3:
1. Mover `ingestao_lei.py` para `src/scraper/ingestao_lei.py`: preservar 100% da lógica do parser, regex, constantes e docstrings.
2. Mover `carregar_mongo.py` para `src/scraper/carregar_mongo.py`:
   - Ajustar o import de ingestao_lei para:
     ```python
     try:
         from src.scraper import ingestao_lei as parser
     except ImportError:
         from . import ingestao_lei as parser
     ```
   - Carregar variáveis `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` / `os.getenv` mantendo fallbacks padrão ("mongodb://localhost:27017" e "rag_juridico").
   - Preservar todos os comentários e docstrings existentes.
3. Remover os arquivos `ingestao_lei.py` e `carregar_mongo.py` da raiz de `e:\Programacao\JudAI`.
4. Criar `src/models/bm25_search.py` com docstrings completas de busca léxica BM25 no RAG híbrido, classe `BM25Search` com métodos `__init__`, `fit`, `search` lançando `NotImplementedError`. ZERO lógica de ML ativa, ZERO import pesado no topo (sem torch, sem transformers).
5. Criar `src/models/bert_search.py` com docstrings completas de busca semântica densa BERT no ChromaDB, classe `BERTSearch` com métodos `__init__`, `encode`, `search` lançando `NotImplementedError`. ZERO lógica de ML ativa, ZERO import pesado no topo.
6. Executar as verificações:
   - `python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_3\verify_m3.py`
   - `python -m pytest tests/test_tier1_feature_coverage.py -k "TestMLModelPlaceholders or TestScraperMigrationFeature" -v`
   - `python -m pytest tests/test_tier2_boundary_corner.py -k "TestBoundaryModelPlaceholdersInputs" -v`
   - `python -m pytest tests/test_tier3_cross_feature.py -k "TestScraperAndDatabaseAlignment or TestFastApiAndModelIntegration" -v`
7. Gerar relatório de handoff detalhado em: e:\Programacao\JudAI\.agents\teamwork\worker_m3_1\handoff.md documentando todas as alterações realizadas e os resultados dos comandos de verificação.
8. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do handoff.md.
