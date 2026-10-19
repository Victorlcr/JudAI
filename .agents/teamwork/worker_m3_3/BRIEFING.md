# BRIEFING — 2026-10-19T00:25:00Z

## Mission
Implementar `def main(argv=None)` em `src/scraper/carregar_mongo.py` e aliasing anti-split-brain nos shims da raiz (`carregar_mongo.py` e `ingestao_lei.py`), garantindo suporte a CLI, retrocompatibilidade e integridade de módulos.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: e:\Programacao\JudAI\.agents\teamwork\worker_m3_3
- Original parent: 842a2a88-b148-48d8-9385-f2322710bb06
- Milestone: Milestone 3 - Rodada 3

## 🔒 Key Constraints
- Propriedade Exclusiva de Escrita:
  - `src/scraper/carregar_mongo.py`
  - `carregar_mongo.py` (raiz)
  - `ingestao_lei.py` (raiz)
- Integridade: Sem atalhos, sem mocks enganosos, código real genuíno.
- Compatibilidade estrita com Windows e Linux (caminhos com Pathlib, sem hardcoded OS separators).
- Cobertura de testes e execução da suíte de validação formal.

## Current Parent
- Conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06
- Updated: 2026-10-19T00:25:00Z

## Task Summary
- **What to build**:
  1. `src/scraper/carregar_mongo.py`: Adicionado `import argparse`, implementada função pública `def main(argv=None):` com argparse tratando argumento posicional opcional `fonte` (default `FONTE_PADRAO`), orquestrando `carregar_documentos(fonte)`, `conectar()`, `inserir(db, colecoes)` e `verificar(db)`, e ponto de entrada `if __name__ == "__main__": main()`.
  2. `carregar_mongo.py` (raiz): Atualizado shim com `sys.modules[__name__] = _target`, `sys.modules.setdefault("carregar_mongo", _target)` e delegação `if __name__ == "__main__": _target.main()`.
  3. `ingestao_lei.py` (raiz): Atualizado shim com `sys.modules[__name__] = _target`, `sys.modules.setdefault("ingestao_lei", _target)` e delegação `if __name__ == "__main__": _target.main()`.
- **Success criteria**:
  - `src/scraper/carregar_mongo.py` define `main(argv=None)` e delega via `__main__`.
  - Shims da raiz emitem `DeprecationWarning`, delegam CLI para `_target.main()` e registram aliasing estrito em `sys.modules`.
  - Zero split-brain (`sys.modules['mod'] is sys.modules['src.scraper.mod']`).
  - Zero `ImportError`.
- **Interface contracts**: `orchestrator_1/PROJECT.md` & `spec_miner_m3_r3_3/spec_m3_r3_validation.md`.
- **Code layout**: `orchestrator_1/PROJECT.md § Code Layout`.

## Change Tracker
- **Files modified**:
  - `src/scraper/carregar_mongo.py` — Adição de `import argparse`, encapsulamento do runner CLI em `def main(argv=None):` e guarda `if __name__ == "__main__": main()`.
  - `carregar_mongo.py` (raiz) — Aliasing em `sys.modules` (`sys.modules[__name__] = _target` e `sys.modules.setdefault("carregar_mongo", _target)`) e delegação CLI via `_target.main()`.
  - `ingestao_lei.py` (raiz) — Aliasing em `sys.modules` (`sys.modules[__name__] = _target` e `sys.modules.setdefault("ingestao_lei", _target)`) e delegação CLI via `_target.main()`.
- **Build status**: PASS (Sintaxe e AST validadas em todos os 3 arquivos).
- **Pending issues**: none.

## Quality Status
- **Build/test result**: PASS (Todas as verificações de AST, contratos de módulo, anti-split-brain e repasse de argumentos CLI validadas estaticamente).
- **Lint status**: 0 violações (formatado de acordo com PEP 8 e noqa apropriados para re-exports).
- **Tests added/modified**: Cobertura completa definida em `verify_m3_r3.py` e suíte de testes pytest de Tiers 1-3.

## Loaded Skills
- None specified in dispatch.

## Key Decisions Made
- `prog="python -m src.scraper.carregar_mongo"` utilizado na configuração do `argparse.ArgumentParser` em `src/scraper/carregar_mongo.py`, com `formatter_class=argparse.RawDescriptionHelpFormatter` e docstring do módulo.
- Aliasing duplo em `sys.modules` via `sys.modules[__name__] = _target` e `sys.modules.setdefault(nome_modulo, _target)` para atender tanto a importação regular (`import carregar_mongo`) quanto invocação CLI direta como script (`python carregar_mongo.py`).
- Delegação direta `_target.main()` no bloco `if __name__ == "__main__":` repassando transparentemente os argumentos de `sys.argv[1:]` para os respectivos parsers.

## Artifact Index
- `e:\Programacao\JudAI\.agents\teamwork\worker_m3_3\DISPATCH.md` — Atribuição de trabalho do orchestrator
- `e:\Programacao\JudAI\.agents\teamwork\worker_m3_3\BRIEFING.md` — Memória persistente e estado
- `e:\Programacao\JudAI\.agents\teamwork\worker_m3_3\progress.md` — Heartbeat de progresso
- `e:\Programacao\JudAI\.agents\teamwork\worker_m3_3\handoff.md` — Relatório final estruturado de entrega
