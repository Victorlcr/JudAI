## 2026-10-19T00:40:36Z

Você é o Challenger 2 do Milestone 4 (Verificação Adversarial de Validação de Schemas e Concorrência).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\challenger_m4_2
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md

Sua missão:
1. Desafiar adversarialmente a validação Pydantic e a concorrência da API FastAPI:
   - Payload sem o campo `query` (`{}`): deve retornar HTTP 422 Unprocessable Entity.
   - Campo `query` com tipo inteiro (`{"query": 12345}`): deve retornar HTTP 422.
   - Campo `query` com tipo lista (`{"query": ["artigo", "186"]}`): deve retornar HTTP 422.
   - Campo `query` com valor nulo (`{"query": null}`): deve retornar HTTP 422.
   - JSON malformado no corpo da requisição: deve retornar HTTP 422.
   - Rajada de concorrência com 30 requisições simultâneas via `ThreadPoolExecutor` (conforme `test_concurrent_client_requests_burst` em `tests/test_tier4_real_world.py`).
   - Executar o script de verificação formal: `python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m4_3\verify_m4.py`.
2. Escrever relatório em: e:\Programacao\JudAI\.agents\teamwork\challenger_m4_2\handoff.md com veredito explícito: APPROVE ou REQUEST_CHANGES.
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando o veredito e o caminho do relatório.
Lembre-se: NÃO modifique arquivos do projeto.
