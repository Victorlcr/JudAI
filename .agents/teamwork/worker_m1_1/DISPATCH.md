## 2026-10-18T22:19:20Z

Você é o Worker 1 do Milestone 1 (Implementador de Estrutura e Configuração Base do JudAI).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\worker_m1_1

Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE ler os relatórios dos exploradores:
- e:\Programacao\JudAI\.agents\teamwork\explorer_m1_1\report_m1_structure.md
- e:\Programacao\JudAI\.agents\teamwork\explorer_m1_2\report_m1_config.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m1_3\spec_m1_validation.md

Propriedade Exclusiva de Escrita (Write Ownership):
Você possui permissão exclusiva para criar/modificar apenas os seguintes arquivos:
- data/raw/.gitkeep
- data/chromadb_local/.gitkeep
- notebooks/.gitkeep
- src/__init__.py
- src/scraper/__init__.py
- src/database/__init__.py
- src/models/__init__.py
- src/api/__init__.py
- .gitignore
- .gitattributes
- docker-compose.yml
- requirements.txt
- .env.example

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Sua missão para o Milestone 1:
1. Criar a árvore de diretórios e arquivos .gitkeep e __init__.py exatamente conforme especificado (conteúdos mínimos e limpos nos __init__.py, sem imports prematuros).
2. Criar .gitignore com as regras completas para venv/, .venv/, data/* com exceção para manter .gitkeep rastreáveis (!data/**/ e !data/**/.gitkeep), .env, __pycache__/.
3. Criar .gitattributes com `* text=auto eol=lf`.
4. Criar docker-compose.yml com serviço mongodb (imagem mongo:latest, porta 27017:27017, volume nomeado mongo_data montado em /data/db e definição de volume no topo).
5. Criar requirements.txt com as 12 dependências exatas sem versão fixada:
fastapi
uvicorn[standard]
pydantic
pymongo
chromadb
rank_bm25
sentence-transformers
nltk
python-dotenv
beautifulsoup4
lxml
requests
6. Criar .env.example com:
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=rag_juridico
CHROMA_DB_PATH=./data/chromadb_local
7. Executar a validação dos arquivos criados executando o script:
`python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m1_3\verify_m1.py`
e `docker compose config` (se o docker estiver instalado no host).
8. Gerar relatório de handoff detalhado em: e:\Programacao\JudAI\.agents\teamwork\worker_m1_1\handoff.md documentando todos os arquivos criados e os resultados dos comandos de verificação.
9. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do handoff.md.
