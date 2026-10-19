## 2026-10-18T22:00:06Z
Você é o Spec Miner (Survey API, Database & ML Specs).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md

Sua missão:
1. Extrair minuciosamente todas as especificações e contratos de interface para:
   - src/database/mongo_connection.py: padrão Singleton (pymongo MongoClient), carregamento de MONGO_URI e MONGO_DB_NAME via python-dotenv / os.environ, sem lógica de inserção/busca. Comportamento exato de instanciação múltipla retornando a mesma instância.
   - src/database/chroma_connection.py: padrão Singleton (chromadb.PersistentClient), carregamento de CHROMA_DB_PATH via python-dotenv / os.environ, criação da pasta se não existir, sem lógica de inserção/busca. Comportamento exato de instanciação múltipla.
   - src/models/bm25_search.py e bert_search.py: placeholders estritos com docstrings explicativas, sem lógica de ML.
   - src/api/main.py: aplicação FastAPI, modelo Pydantic QueryRequest(query: str), GET /health retornando status, POST /search/bm25 e POST /search/bert recebendo QueryRequest e retornando mock estruturado com status 200 ({model, query, results: [], detail: "not implemented"}).
   - Validações de aceitação para testes unitários e E2E.
2. Produzir uma especificação técnica detalhada em: e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\spec_api_database.md
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de especificação. NÃO modifique nem crie código do projeto.
