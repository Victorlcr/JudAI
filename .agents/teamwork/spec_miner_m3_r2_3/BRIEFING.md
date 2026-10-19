# BRIEFING — 2026-10-18T23:50:00Z

## Mission
Mapear e especificar com rigor testes e critérios de validação para a Rodada 2 do Milestone 3 (regex de parágrafos/numeração e remoção de scripts obsoletos na raiz).

## 🔒 My Identity
- Archetype: Spec Miner
- Roles: Specification Mining, Test Specification
- Working directory: e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3
- Original parent: 842a2a88-b148-48d8-9385-f2322710bb06
- Milestone: Milestone 3 - Round 2

## 🔒 Key Constraints
- Agente read-only: NÃO modificar código ou testes do projeto principal.
- Escrever apenas no próprio diretório de trabalho: `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\`.
- Nunca colocar código-fonte de produção em `.agents/teamwork/`.
- Linhas numéricas sem indicador de parágrafo (ex: `"1. Princípio fundamental"`) NÃO devem casar como parágrafos por `RE_PAR`.
- Parágrafos danificados com `\ufffd` (ex: `"\ufffd 1º Texto"`) devem casar corretamente como parágrafos.
- Parágrafos normais `§ 1º` ou `Parágrafo único.` devem continuar funcionando 100%.
- A remoção de `ingestao_lei.py` e `carregar_mongo.py` da raiz deve ser validada por asserção estrita `assert not Path("ingestao_lei.py").exists()` e `assert not Path("carregar_mongo.py").exists()`.

## Current Parent
- Conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06
- Updated: 2026-10-18T23:50:00Z

## Task Summary
- **What to build**: Relatório de especificação `spec_m3_r2_validation.md` e script de teste rápido `verify_m3_r2.py`.
- **Success criteria**: Especificações completas com tabelas de features, edge cases, contratos de regex, casos de teste com entradas/saídas esperadas e asserções estritas de limpeza de arquivos obsoletos.
- **Interface contracts**: `PROJECT.md` e `ORIGINAL_REQUEST.md`
- **Code layout**: Projeto JudAI (`src/`, `tests/`)

## Key Decisions Made
- Analisado defeito do ramo vazio `(?:§|)` em `src/scraper/ingestao_lei.py` linha 79 e ausência de `\ufffd` em `ORD` linha 75.
- Especificada a correção formal para `(?:§|\ufffd)` e `[º°ª\ufffd]+`.
- Mapeadas 9 features descobertas e 25 edge cases cobrindo rejeições numéricas, parágrafos padrão e corrompidos, além de integração HTML.
- Especificada asserção estrita para `test_scraper_no_scripts_left_in_root` em `tests/test_tier1_feature_coverage.py`.
- Criado script executável `verify_m3_r2.py` para teste ponta a ponta.

## Artifact Index
- `spec_m3_r2_validation.md` — Relatório formal de especificação de testes da Rodada 2
- `verify_m3_r2.py` — Script executável de verificação rápida da Rodada 2
- `handoff.md` — Relatório de handoff formal de 5 componentes
