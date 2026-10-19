# BRIEFING — 2026-10-19T00:07:00Z

## Mission
Investigar a estrutura de `carregar_mongo.py` e projetar a refatoração segura da interface CLI em `def main(argv=None):`, compatível com `ingestao_lei.py:535` e protegida contra regressões de CLI e testes.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1
- Original parent: 842a2a88-b148-48d8-9385-f2322710bb06
- Milestone: Milestone 3 - Rodada 3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / do NOT modify source code files
- Only write in e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1
- Output technical report to `report_m3_r3_main_func.md`
- Output handoff report to `handoff.md`
- Communicate completion to orchestrator via `send_message`

## Current Parent
- Conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06
- Updated: 2026-10-19T00:07:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`
  - `reviewer_m3_r2_1/handoff.md`, `challenger_m3_r2_2/handoff.md`, `test_shims_adversarial.py`
  - `src/scraper/carregar_mongo.py`, `src/scraper/ingestao_lei.py`
  - `carregar_mongo.py` (root), `ingestao_lei.py` (root)
  - `tests/test_tier1_feature_coverage.py`, `tests/test_tier3_cross_feature.py`, `tests/test_tier4_real_world.py`
- **Key findings**:
  - Causa raiz do `ImportError`: `src/scraper/carregar_mongo.py` possui a lógica CLI puramente procedural em `if __name__ == "__main__":` (linhas 105-116), sem definir `main(argv=None)`.
  - Em contraste, `src/scraper/ingestao_lei.py:535` define `def main(argv=None):` com `argparse`.
  - A encapsulação com `argparse` em `src/scraper/carregar_mongo.py` resolve 100% da quebra dos shims, passa em todas as suítes e permite testes sem dependência de banco em `--help`.
- **Unexplored areas**: Nenhuma pendência em aberto para o escopo desta rodada.

## Key Decisions Made
- Especificação formal com `argparse` adotada (simetria idêntica a `ingestao_lei.py:535`).
- Definição exata do código e diff para o implementador/worker em `report_m3_r3_main_func.md`.
- Recomendações preventivas de split-brain e repasse de CLI incluídas para os shims da raiz.

## Artifact Index
- `DISPATCH.md` — Registro de entrada da missão
- `BRIEFING.md` — Memória persistente de identidade e estado
- `progress.md` — Heartbeat de execução
- `report_m3_r3_main_func.md` — Relatório técnico com proposta exata de código
- `handoff.md` — Handoff formal nos 5 componentes
