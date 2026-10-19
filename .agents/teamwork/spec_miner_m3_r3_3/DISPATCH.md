## 2026-10-19T00:03:48Z
Você é o Spec Miner da Rodada 3 do Milestone 3 (Especificação e Testes para Shims e def main).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE ler os relatórios de falha da Rodada 2:
- e:\Programacao\JudAI\.agents\teamwork\reviewer_m3_r2_1\handoff.md
- e:\Programacao\JudAI\.agents\teamwork\challenger_m3_r2_2\handoff.md

Sua missão:
1. Especificar os testes e criar um script de verificação executável `verify_m3_r3.py` para atestar:
   - Presença e chamabilidade de `def main()` em `src/scraper/carregar_mongo.py`.
   - Presença e chamabilidade de `def main()` em `src/scraper/ingestao_lei.py`.
   - Execução sem erros dos shims da raiz (`import carregar_mongo`, `import ingestao_lei`, `hasattr(carregar_mongo, 'main') == True`, `hasattr(ingestao_lei, 'main') == True`).
   - Aliasing de módulo (`sys.modules['carregar_mongo'] is sys.modules['src.scraper.carregar_mongo']`).
2. Produzir o relatório de especificação em: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3\spec_m3_r3_validation.md e `verify_m3_r3.py`.
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de especificação. NÃO modifique código do projeto.
