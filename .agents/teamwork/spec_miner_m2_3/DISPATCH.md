## 2026-10-18T22:34:26Z
Você é o Spec Miner do Milestone 2 (Validação e Testes das Conexões de Banco de Dados).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m2_3
Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE analisar os testes já existentes em `tests/test_tier1_feature_coverage.py`, `tests/test_tier2_boundary_corner.py` e `tests/test_tier3_cross_feature.py`.

Sua missão para o Milestone 2:
1. Mapear e especificar todos os testes unitários, de concorrência e de borda necessários para validar `MongoConnection` e `ChromaConnection`:
   - Duas instanciações retornam exatamente o mesmo objeto (`conn1 is conn2`, `conn1.client is conn2.client`).
   - Múltiplas threads instanciando concorrentemente retornam a mesma instância sem race condition.
   - Variáveis de ambiente personalizadas são respeitadas após reset.
   - Diretório do ChromaDB é criado no disco se não existir.
   - Ausência de métodos CRUD na interface pública de ambas as classes.
2. Produzir relatório de especificação de testes em: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m2_3\spec_m2_validation.md e um script de verificação executável em `verify_m2.py`.
3. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do relatório.
Lembre-se: Você é um agente read-only de especificação. NÃO modifique arquivos do projeto (apenas em seu diretório de trabalho).
