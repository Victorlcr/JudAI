# DISPATCH — 2026-10-19T00:15:00Z

Você é o Worker 3 do Milestone 3 (Implementador da Rodada 3: def main em carregar_mongo e aliasing anti-split-brain nos shims da raiz).
Seu diretório de trabalho exclusivo é: `e:\Programacao\JudAI\.agents\teamwork\worker_m3_3`

## Documentos Mandatórios para Leitura:
- `e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md`
- `e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1\report_m3_r3_main_func.md`
- `e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_2\report_m3_r3_shims_aliasing.md`
- `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3\spec_m3_r3_validation.md`
- `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3\verify_m3_r3.py`

## Propriedade Exclusiva de Escrita (Write Ownership):
Você possui permissão exclusiva para modificar apenas os seguintes arquivos:
- `src/scraper/carregar_mongo.py`
- `carregar_mongo.py` (na raiz de `e:\Programacao\JudAI`)
- `ingestao_lei.py` (na raiz de `e:\Programacao\JudAI`)

## MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tarefas:
1. Em `src/scraper/carregar_mongo.py`:
   - Importar `argparse`.
   - Implementar `def main(argv=None):` conforme especificado no relatório de `explorer_m3_r3_1`, utilizando `argparse.ArgumentParser` com o argumento posicional opcional `fonte` (default `FONTE_PADRAO`), chamando sequencialmente `carregar_documentos(fonte)`, `conectar()`, `inserir(db, colecoes)` e `verificar(db)`.
   - Atualizar a guarda de execução para:
     ```python
     if __name__ == "__main__":
         main()
     ```
2. Em `carregar_mongo.py` (na raiz):
   - Atualizar o shim com:
     ```python
     """
     DEPRECATED: Este arquivo foi migrado para src/scraper/carregar_mongo.py.
     A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
     """
     import sys
     import warnings

     warnings.warn(
         "carregar_mongo.py na raiz do projeto está obsoleto e foi migrado para src.scraper.carregar_mongo. "
         "Este shim será removido no Milestone 5.",
         DeprecationWarning,
         stacklevel=2,
     )

     import src.scraper.carregar_mongo as _target  # noqa: E402

     # Re-exportação explícita para suporte a IDEs, linters e análise estática (AST)
     from src.scraper.carregar_mongo import *  # noqa: E402, F401, F403

     # Aliasing de módulo em sys.modules para prevenção estrita de split-brain
     sys.modules[__name__] = _target
     sys.modules.setdefault("carregar_mongo", _target)

     if __name__ == "__main__":
         _target.main()
     ```
3. Em `ingestao_lei.py` (na raiz):
   - Atualizar o shim com:
     ```python
     """
     DEPRECATED: Este arquivo foi migrado para src/scraper/ingestao_lei.py.
     A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
     """
     import sys
     import warnings

     warnings.warn(
         "ingestao_lei.py na raiz do projeto está obsoleto e foi migrado para src.scraper.ingestao_lei. "
         "Este shim será removido no Milestone 5.",
         DeprecationWarning,
         stacklevel=2,
     )

     import src.scraper.ingestao_lei as _target  # noqa: E402

     # Re-exportação explícita para suporte a IDEs, linters e análise estática (AST)
     from src.scraper.ingestao_lei import *  # noqa: E402, F401, F403

     # Aliasing de módulo em sys.modules para prevenção estrita de split-brain
     sys.modules[__name__] = _target
     sys.modules.setdefault("ingestao_lei", _target)

     if __name__ == "__main__":
         _target.main()
     ```
4. Executar os testes de validação:
   - `python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3\verify_m3_r3.py`
   - `python -m pytest tests/test_tier1_feature_coverage.py -k "TestMLModelPlaceholders or TestScraperMigrationFeature" -v`
   - `python -m pytest tests/test_tier2_boundary_corner.py -k "TestBoundaryModelPlaceholdersInputs" -v`
   - `python -m pytest tests/test_tier3_cross_feature.py -k "TestScraperAndDatabaseAlignment or TestFastApiAndModelIntegration" -v`
5. Escrever relatório de handoff estruturado em: `e:\Programacao\JudAI\.agents\teamwork\worker_m3_3\handoff.md`.
6. Enviar mensagem de conclusão ao orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`).
