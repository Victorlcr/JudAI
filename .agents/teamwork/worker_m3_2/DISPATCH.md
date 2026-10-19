## 2026-10-18T23:49:49Z
Você é o Worker 2 do Milestone 3 (Implementador de Correções da Rodada 2: Regex de Ingestão e Limpeza de Arquivos Legados).
Seu diretório de trabalho é: e:\Programacao\JudAI\.agents\teamwork\worker_m3_2

Você DEVE ler o arquivo de requisição original em: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
Você DEVE ler o plano do projeto em: e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md
Você DEVE ler os relatórios dos exploradores da Rodada 2:
- e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r2_1\report_m3_r2_regex.md
- e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r2_2\report_m3_r2_legacy_files.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\spec_m3_r2_validation.md
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\verify_m3_r2.py

Propriedade Exclusiva de Escrita (Write Ownership):
Você possui permissão exclusiva para criar/modificar apenas os seguintes arquivos:
- src/scraper/ingestao_lei.py
- ingestao_lei.py (na raiz)
- carregar_mongo.py (na raiz)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Sua missão para a Rodada 2 do Milestone 3:
1. No arquivo `src/scraper/ingestao_lei.py`:
   - Atualizar a linha 75 (`ORD`):
     `ORD = r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito`
   - Atualizar a linha 79 (`RE_PAR`):
     `RE_PAR = re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)`
   - Garantir que `FFFD = "\ufffd"` e todas as outras 16 regexes e funções essenciais permaneçam perfeitamente intactas.
2. Tratamento dos arquivos legados na raiz (`e:\Programacao\JudAI`):
   - Seguir o protocolo de duas camadas de `explorer_m3_r2_2`:
     - **Camada 1 (Prioritária)**: Executar a exclusão direta via comando Python não-interativo:
       `python -c "import os, stat, pathlib; [os.chmod(p, stat.S_IWRITE) for p in (pathlib.Path('ingestao_lei.py'), pathlib.Path('carregar_mongo.py')) if p.exists()]; [p.unlink() for p in (pathlib.Path('ingestao_lei.py'), pathlib.Path('carregar_mongo.py')) if p.exists()]; print('Remocao concluida')"`
     - **Camada 2 (Contingência)**: Caso o terminal registre timeout interativo, sobrescrever os arquivos na raiz via `write_to_file` com Deprecation Proxy Shims que reexportam de `src.scraper.ingestao_lei` e `src.scraper.carregar_mongo` (eliminando qualquer risco de split-brain e postergando a remoção física para a etapa de git init no Milestone 5).
3. Executar o validador da Rodada 2:
   `python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\verify_m3_r2.py`
4. Gerar relatório de handoff estruturado em: e:\Programacao\JudAI\.agents\teamwork\worker_m3_2\handoff.md documentando as alterações e resultados.
5. Enviar mensagem ao orchestrator (conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06) informando a conclusão e o caminho do handoff.md.
