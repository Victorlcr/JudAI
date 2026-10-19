## 2026-10-18T23:43:29Z
Você é o Spec Miner da Rodada 2 do Milestone 3 (Especificação de Testes para Correções da Rodada 2).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE ler os relatórios de revisão e auditoria da Rodada 1:
- e:\Programacao\JudAI\.agents\teamwork\reviewer_m3_1\handoff.md
- e:\Programacao\JudAI\.agents\teamwork\auditor_m3_1\handoff.md

Sua missão:
1. Mapear testes específicos para assegurar que:
   - Linhas numéricas sem indicador de parágrafo (ex: `"1. Princípio fundamental"`) NÃO sejam casadas como parágrafos por `RE_PAR`.
   - Parágrafos danificados com `\ufffd` (ex: `"\ufffd 1º Texto"`) sejam casados corretamente como parágrafos.
   - Parágrafos normais `§ 1º` continuem funcionando 100%.
   - A remoção de `ingestao_lei.py` e `carregar_mongo.py` da raiz seja validada por asserção estrita `assert not Path("ingestao_lei.py").exists()`.
2. Produzir o relatório de especificação em: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\spec_m3_r2_validation.md e um script de verificação rápido `verify_m3_r2.py`.
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de especificação. NÃO modifique arquivos do projeto.
