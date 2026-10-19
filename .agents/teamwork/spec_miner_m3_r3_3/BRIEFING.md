# BRIEFING — 2026-10-19T00:13:00Z

## Mission
Especificar requisitos, casos de teste e script de validação executável `verify_m3_r3.py` para Shims da raiz e funções `def main()` de `src/scraper/carregar_mongo.py` e `src/scraper/ingestao_lei.py`.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Spec Miner, Test Specification Expert
- Working directory: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3
- Original parent: 842a2a88-b148-48d8-9385-f2322710bb06
- Milestone: Milestone 3 (Round 3)

## 🔒 Key Constraints
- Read-only on project source code (do NOT modify code in src/ or tests/ or root shims directly).
- Write all findings, specifications and verification script inside .agents/teamwork/spec_miner_m3_r3_3/.
- Send completion message to orchestrator (842a2a88-b148-48d8-9385-f2322710bb06).

## Current Parent
- Conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06
- Updated: 2026-10-19T00:13:00Z

## Task Summary
- **What to build**: Specification document (`spec_m3_r3_validation.md`), executable verification script (`verify_m3_r3.py`), and handoff report (`handoff.md`).
- **Success criteria**:
  1. Exact specifications for `def main(argv=None)` in `src/scraper/carregar_mongo.py` and `src/scraper/ingestao_lei.py` (signature, docstring, return code/behavior, error handling, `if __name__ == "__main__": main()`).
  2. Exact specifications for root shims (`carregar_mongo.py` and `ingestao_lei.py`) including deprecation warning (`DeprecationWarning`), sys.modules aliasing (`sys.modules[__name__] = _target`), attribute forwarding / re-export and CLI delegation (`_target.main()`).
  3. Verifiable testing suite / test cases covering normal execution, edge cases, module aliasing, main presence and callable contract.
  4. Executable `verify_m3_r3.py` that checks existing codebase status and serves as gatekeeper for Milestone 3 Round 3.
- **Interface contracts**: PROJECT.md, ORIGINAL_REQUEST.md
- **Code layout**: .agents/teamwork/spec_miner_m3_r3_3/

## Key Decisions Made
- `src/scraper/carregar_mongo.py`: Encapsulate procedural CLI code into `def main(argv=None):` using `argparse`, matching `ingestao_lei.py:535`, handling `-h`/`--help` cleanly with exit code 0 without touching Mongo.
- Root shims: Implement dual mechanism: `from src.scraper.<mod> import *` (for AST/IDE static support) combined with `sys.modules[__name__] = _target` and `sys.modules.setdefault(name, _target)` (for runtime module aliasing and split-brain prevention), plus `if __name__ == "__main__": _target.main()`.
- Created robust 3-phase automated verification script `verify_m3_r3.py` (Static AST, Dynamic Contracts & Aliasing, CLI Subprocess) that acts as the authoritative pass/fail gatekeeper.

## Artifact Index
- DISPATCH.md — Initial dispatch assignment
- BRIEFING.md — Situational awareness and identity
- progress.md — Liveness heartbeat and step tracking
- spec_m3_r3_validation.md — Specification & test criteria report
- verify_m3_r3.py — Executable verification script
- handoff.md — 5-component handoff report
