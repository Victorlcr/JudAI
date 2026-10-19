## 2026-10-18T22:46:32Z
Você é o Worker 1 do Milestone 2 (Implementador das Conexões de Banco de Dados: MongoConnection & ChromaConnection).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\worker_m2_1

Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE ler as especificações dos exploradores:
- e:\Programacao\JudAI\.agents\teamwork\explorer_m2_1\report_m2_mongo.md
- e:\Programacao\JudAI\.agents\teamwork\explorer_m2_2\report_m2_chroma.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m2_3\spec_m2_validation.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m2_3\verify_m2.py

Propriedade Exclusiva de Escrita (Write Ownership):
Você possui permissão exclusiva para criar/modificar apenas os seguintes arquivos:
- src/database/mongo_connection.py
- src/database/chroma_connection.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Sua missão para o Milestone 2:
1. Implementar `src/database/mongo_connection.py`:
   - Padrão Singleton thread-safe com `_lock` e flag `_initialized`.
   - Carregamento de `MONGO_URI` (default: `"mongodb://localhost:27017"`) e `MONGO_DB_NAME` (default: `"rag_juridico"`) via `python-dotenv` e `os.environ`.
   - Conexão lazy com `pymongo.MongoClient`.
   - Propriedades `.client`, `.db`, `.uri`, `.db_name` e métodos utilitários `.get_client()`, `.get_db()`, `.close()`, `.reset()`.
   - NENHUM método CRUD público (sem insert, find, etc.).
2. Implementar `src/database/chroma_connection.py`:
   - Padrão Singleton thread-safe com `_lock` e flag `_initialized`.
   - Carregamento de `CHROMA_DB_PATH` (default: `"./data/chromadb_local"`) via `python-dotenv` e `os.environ`.
   - Resolução de caminho agnóstica de SO via `pathlib.Path(caminho).resolve()`.
   - Criação da pasta de persistência se não existir (`Path.mkdir(parents=True, exist_ok=True)`).
   - Instanciação de `chromadb.PersistentClient(path=str(path))`.
   - Propriedades `.client`, `.path` e métodos `.get_client()`, `.reset()`.
   - NENHUM método CRUD público (sem add, query, create_collection, etc.).
3. Executar as verificações:
   - `python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m2_3\verify_m2.py`
   - `python -m pytest tests/test_tier1_feature_coverage.py -k "TestMongoConnectionFeature or TestChromaConnectionFeature" -v`
   - `python -m pytest tests/test_tier2_boundary_corner.py -k "TestSingletonBoundaryAndConcurrency" -v`
   - `python -m pytest tests/test_tier3_cross_feature.py -k "TestEnvironmentVariablesAndConnections" -v`
4. Gerar relatório de handoff detalhado em: e:\Programacao\JudAI\.agents\teamwork\worker_m2_1\handoff.md documentando os arquivos criados e os resultados dos comandos de verificação.
5. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do handoff.md.
