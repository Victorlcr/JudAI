## 2026-10-18T22:00:06Z
Você é o Explorer 2 (Survey Infra, Config & Git).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\explorer_survey_2
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md

Sua missão:
1. Mapear todos os requisitos e regras de infraestrutura, configuração e controle de versão:
   - Estrutura completa de diretórios e arquivos .gitkeep requeridos (data/raw, data/chromadb_local, notebooks, etc.).
   - Regras exatas do .gitignore (venv/, .venv/, data/* com exceção de !data/**/.gitkeep, .env, __pycache__/).
   - Regras do .gitattributes (* text=auto eol=lf) para compatibilidade Windows e Linux.
   - Especificação do docker-compose.yml (mongo:latest, porta 27017:27017, volume nomeado /data/db).
   - Especificação do .env.example (MONGO_URI, MONGO_DB_NAME, CHROMA_DB_PATH).
   - Lista exata de dependências para requirements.txt (sem pin).
   - Requisitos do README.md e instruções de execução/comandos para Windows PowerShell e Linux/macOS.
   - Requisitos de inicialização git (git init, branch main, commit inicial limpo, sem push).
2. Produzir um relatório detalhado em: e:\Programacao\JudAI\.agents\teamwork\explorer_survey_2\survey_infra_git.md
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de exploração. NÃO modifique nem crie código do projeto.
