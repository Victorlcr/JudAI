# BRIEFING — 2026-10-18T22:07:15Z

## Mission
Extrair e documentar minuciosamente todas as especificações e contratos de interface para src/database, src/models e src/api conforme ORIGINAL_REQUEST.md.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Spec Miner (Survey API, Database & ML Specs)
- Working directory: e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3
- Original parent: 842a2a88-b148-48d8-9385-f2322710bb06
- Milestone: Survey & Specifications

## 🔒 Key Constraints
- Read-only: NÃO modificar nem criar código do projeto (apenas artefatos de documentação/especificação dentro do diretório de trabalho do agente).
- Extrair contratos exatos para: mongo_connection.py, chroma_connection.py, bm25_search.py, bert_search.py, src/api/main.py.
- Entregar relatório em spec_api_database.md e handoff.md.

## Current Parent
- Conversation ID: 842a2a88-b148-48d8-9385-f2322710bb06
- Updated: 2026-10-18T22:07:15Z

## Task Summary
- **What to build**: Especificação técnica para database connections (Mongo, Chroma), modelos placeholders e FastAPI endpoints.
- **Success criteria**: Especificação completa cobrindo classes, métodos, assinaturas, tipos, variáveis de ambiente, comportamento Singleton com thread-safety e proteção a `__init__`, tratamento de erros e critérios de aceitação para testes unitários/E2E.
- **Interface contracts**: e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md
- **Code layout**: e:\Programacao\JudAI

## Key Decisions Made
- Especificação formal do padrão Singleton utilizando guarda de inicialização (`_initialized`) com `threading.Lock()`, evitando re-inicializações e garantindo que múltiplas chamadas retornem o mesmo objeto sem abrir sockets redundantes.
- Utilização de `pathlib.Path(path).resolve()` e `mkdir(parents=True, exist_ok=True)` no `ChromaConnection` para garantir portabilidade completa entre Windows e Linux.
- Padrão de fallback para variáveis de ambiente: `os.getenv("VAR") or "default"` para contornar strings vazias no `.env`.
- Modelo Pydantic `QueryRequest(query: str)` com validação nativa e resposta estruturada para `/search/bm25` e `/search/bert` com status 200 e campos `{model, query, results: [], detail: "not implemented"}`.
- Especificação dos módulos `bm25_search.py` e `bert_search.py` sem imports pesados de ML no escopo de módulo para permitir inicialização rápida e testes leves.

## Artifact Index
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\spec_api_database.md — Technical Specification Document (Completo)
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\handoff.md — 5-Component Handoff Report
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\progress.md — Progress Heartbeat (Concluído)
- e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\DISPATCH.md — Dispatch log
