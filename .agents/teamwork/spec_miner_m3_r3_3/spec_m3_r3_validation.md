# Especificação Formal de Validação e Testes: Milestone 3 - Rodada 3

**Projeto**: JudAI - RAG Híbrido Jurídico  
**Marco**: Milestone 3 - Rodada 3 (Especificação e Testes para Shims da Raiz, Aliasing de Módulos e `def main()`)  
**Autor**: `spec_miner_m3_r3_3` (Specification Miner)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Data**: 2026-10-19  
**Status**: ESPECIFICAÇÃO CONCLUÍDA — PRONTA PARA IMPLEMENTAÇÃO E AUDITORIA  
**Script Executável de Verificação**: `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3\verify_m3_r3.py`

---

## 1. Visão Geral e Contexto da Rodada 3

Na Rodada 2 do Milestone 3, a correção das expressões regulares (`RE_PAR` e `ORD`) foi aprovada por eliminar a alternância vazia e restabelecer a tolerância a mojibake (`\ufffd`). Contudo, a estratégia de retrocompatibilidade com shims de depreciação na raiz (`carregar_mongo.py` e `ingestao_lei.py`) sofreu um veredito unânime de **REQUEST_CHANGES** pelos revisores (`reviewer_m3_r2_1` e `challenger_m3_r2_2`) devido a:

1. **Defeito Crítico de Invocação em `carregar_mongo.py` (Raiz)**:
   - O shim na raiz invocava `from src.scraper.carregar_mongo import main; main()`.
   - O módulo canônico `src/scraper/carregar_mongo.py` não possuía `def main()`, mantendo sua lógica CLI solta no bloco procedural `if __name__ == "__main__":`.
   - Resultado: Qualquer execução de `python carregar_mongo.py` quebrava imediatamente com `ImportError: cannot import name 'main'`.
2. **Inércia Operacional de CLI em `ingestao_lei.py` (Raiz)**:
   - O shim na raiz continha apenas o aviso de depreciação e `from src.scraper.ingestao_lei import *`, sem o bloco `if __name__ == "__main__": main()`.
   - Resultado: Execuções como `python ingestao_lei.py L10406.html` encerravam silenciosamente sem executar o parser nem processar argumentos.
3. **Falso Positivo de Validação Documentado no Handoff**:
   - O relatório `worker_m3_2/handoff.md §5.2` alegou que `assert hasattr(carregar_mongo, 'main')` havia passado com 100% de aprovação, o que era falso (o atributo não existia).
4. **Vulnerabilidade Arquitetural de Split-Brain**:
   - A reexportação via `from ... import *` cria instâncias de módulo desvinculadas entre a raiz e `src/scraper/`, impedindo que alterações dinâmicas de estado e referências de identidade (`a is b`) sejam compartilhadas.

Esta especificação define formalmente os requisitos, contratos de interface, casos de teste e o script executável `verify_m3_r3.py` para governar a implementação e validação da Rodada 3.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Scraper CLI | Função `def main(argv=None)` em `src/scraper/carregar_mongo.py` | Encapsulamento da lógica CLI do runner em função exportável compatível com `argparse` | `argv=None` (ou `list[str]`) | Executa fluxo de carga ou exibe help | Falha se `main` não existir ou não aceitar `argv` | `reviewer_m3_r2_1 Finding 1`, `PROJECT.md §Feature 10` |
| 2 | Scraper CLI | Tratamento de `-h`/`--help` em `src/scraper/carregar_mongo.py` | Exibição de documentação de uso e término limpo com código 0 | `argv=["-h"]` ou `argv=["--help"]` | Exibe help text; sai com código 0 via `SystemExit(0)` | Falha se tentar conectar ao MongoDB ou retornar código diferente de 0 | `test_tier4_real_world.py`, `explorer_m3_r3_1` |
| 3 | Scraper CLI | Ponto de Entrada `__main__` em `src/scraper/carregar_mongo.py` | Invocação de `main()` sob guarda `if __name__ == "__main__":` | Execução via `python -m src.scraper.carregar_mongo` | Delega para `main()` | Falha se mantiver código procedural solto sem chamar `main()` | `PROJECT.md §Code Layout` |
| 4 | Scraper CLI | Chamabilidade de `main(argv=None)` em `src/scraper/ingestao_lei.py` | Verificação do contrato exportável da CLI de ingestão | `argv=["--help"]` ou `argv=["--sem-mongo", ...]` | Processa flags do parser | Falha se `main` não for chamável | `src/scraper/ingestao_lei.py:535` |
| 5 | Root Shim | Retrocompatibilidade Sem Erro de `carregar_mongo.py` (Raiz) | `import carregar_mongo` executa sem `ImportError`, `AttributeError` ou `SyntaxError` | `import carregar_mongo` | Módulo importado com sucesso | Falha com `ImportError` se tentar importar símbolos inexistentes | `challenger_m3_r2_2 Obs 1.1` |
| 6 | Root Shim | Retrocompatibilidade Sem Erro de `ingestao_lei.py` (Raiz) | `import ingestao_lei` executa sem nenhuma exceção | `import ingestao_lei` | Módulo importado com sucesso | Falha se houver erro de sintaxe ou dependência | `PROJECT.md §Feature 9` |
| 7 | Root Shim | Emissão de `DeprecationWarning` nos Shims da Raiz | Emissão de aviso com `stacklevel=2` informando obsolescência e remoção no M5 | Importação ou execução dos scripts na raiz | Warning emitido na categoria `DeprecationWarning` | Falha se nenhum aviso for disparado | `challenger_m3_r2_2`, `reviewer_m3_r2_1` |
| 8 | Root Shim | Exportação de Atributo `main` no Shim `carregar_mongo` | `hasattr(carregar_mongo, 'main') == True` e `callable(carregar_mongo.main) == True` | `hasattr(carregar_mongo, 'main')` | `True` | Falha se `hasattr` retornar `False` (regressão da Rodada 2) | `worker_m3_2/handoff.md §5.2` refutado |
| 9 | Root Shim | Exportação de Atributo `main` no Shim `ingestao_lei` | `hasattr(ingestao_lei, 'main') == True` e `callable(ingestao_lei.main) == True` | `hasattr(ingestao_lei, 'main')` | `True` | Falha se `hasattr` retornar `False` | `ORIGINAL_REQUEST §R2` |
| 10 | Root Shim | Delegação de Execução CLI no Shim `carregar_mongo.py` | Invocação direta via CLI repassa execução para `_target.main()` | `python carregar_mongo.py --help` | Exibe help do scraper e sai com código 0 | Falha se lançar `ImportError` ou código != 0 | `reviewer_m3_r2_1 Finding 1` |
| 11 | Root Shim | Delegação de Execução CLI no Shim `ingestao_lei.py` | Invocação direta via CLI repassa execução para `_target.main()` | `python ingestao_lei.py --help` | Exibe help do parser e sai com código 0 | Falha se for *silent no-op* e encerrar sem saída | `challenger_m3_r2_2 Obs 1.3` |
| 12 | Module Aliasing | Aliasing Estrito de `carregar_mongo` em `sys.modules` | `sys.modules['carregar_mongo'] is sys.modules['src.scraper.carregar_mongo']` | Import de ambos os caminhos | `True` (mesma referência em memória) | Falha se forem módulos distintos (split-brain) | `challenger_m3_r2_2 §4 Opção A`, `explorer_m3_r3_2` |
| 13 | Module Aliasing | Aliasing Estrito de `ingestao_lei` em `sys.modules` | `sys.modules['ingestao_lei'] is sys.modules['src.scraper.ingestao_lei']` | Import de ambos os caminhos | `True` (mesma referência em memória) | Falha se forem módulos distintos (split-brain) | `challenger_m3_r2_2 §4 Opção A`, `explorer_m3_r3_2` |
| 14 | Module Aliasing | Imunidade a Mutações Desincronizadas (Anti-Split-Brain) | Alterações em variáveis de módulo de um caminho refletem no outro imediatamente | Atribuição de atributo em `carregar_mongo` | Atributo idêntico acessível em `src.scraper.carregar_mongo` | Falha se houver bifurcação de estado | `explorer_m3_r3_2 §3` |
| 15 | Static Analysis | Compatibilidade com AST e Linters nos Shims | IDEs e analisadores estáticos conseguem inspecionar símbolos reexportados | Análise sintática via `ast.parse` | Árvore válida com `import *` e referências | Falha se linters acusarem símbolos fantasmas | `explorer_m3_r3_2 §3.4` |

---

## Edge Cases

| # | Feature | Input | Observed / Expected Behavior |
|---|---------|-------|------------------------------|
| 1 | `carregar_mongo.main` | `argv=None` (chamado via terminal sem args) | Lê `sys.argv[1:]`; usa `fonte = FONTE_PADRAO`. |
| 2 | `carregar_mongo.main` | `argv=[]` (lista vazia explícita) | Usa `fonte = FONTE_PADRAO`. |
| 3 | `carregar_mongo.main` | `argv=["-h"]` | Dispara `SystemExit(0)`; exibe documentação sem conectar ao banco. |
| 4 | `carregar_mongo.main` | `argv=["--help"]` | Dispara `SystemExit(0)`; exibe documentação sem conectar ao banco. |
| 5 | `carregar_mongo.main` | `argv=["arquivo_local.html"]` | Define `fonte = "arquivo_local.html"`; prossegue para carga. |
| 6 | `carregar_mongo.main` | `argv=["https://exemplo.gov.br"]` | Define `fonte = "https://exemplo.gov.br"`. |
| 7 | `carregar_mongo.main` | `argv=["arg1", "arg2"]` (dois posicionais) | Dispara `SystemExit(2)` via `argparse` por excesso de argumentos. |
| 8 | `carregar_mongo.main` | `argv=["--flag-inexistente"]` | Dispara `SystemExit(2)` via `argparse` com mensagem de erro amigável. |
| 9 | `ingestao_lei.main` | `argv=["--help"]` | Dispara `SystemExit(0)`; exibe flags `--lei-id`, `--sem-mongo`, etc. |
| 10 | `ingestao_lei.main` | `argv=[]` (sem arquivo de entrada) | Dispara `SystemExit(2)` (argumento `entrada` é obrigatório). |
| 11 | `ingestao_lei.main` | `argv=["L10406.html", "--sem-mongo"]` | Executa parser sem abrir conexão com MongoDB. |
| 12 | Root Shim `carregar_mongo` | `import carregar_mongo` quando `src.scraper.carregar_mongo` já foi importado | Reutiliza instância de `_target`, emite warning, `carregar_mongo is sys.modules['src.scraper.carregar_mongo']`. |
| 13 | Root Shim `carregar_mongo` | `import carregar_mongo` quando `src.scraper.carregar_mongo` NÃO foi importado | Carrega `src.scraper.carregar_mongo`, popula `sys.modules`, emite warning, aliasing perfeito. |
| 14 | Root Shim `carregar_mongo` | `from carregar_mongo import main` | Importa com sucesso a função `main` canônica. |
| 15 | Root Shim `carregar_mongo` | `from carregar_mongo import conectar, carregar_documentos` | Importa as funções originais preservadas. |
| 16 | Root Shim `carregar_mongo` CLI | `python carregar_mongo.py --help` | Emite `DeprecationWarning` em stderr, exibe manual em stdout, sai com código 0 (ZERO `ImportError`). |
| 17 | Root Shim `ingestao_lei` CLI | `python ingestao_lei.py --help` | Emite `DeprecationWarning` em stderr, exibe manual do parser em stdout, sai com código 0 (NÃO é no-op). |
| 18 | Split-Brain Mutation | `carregar_mongo._novo_attr = "teste"` | `src.scraper.carregar_mongo._novo_attr == "teste"` imediatamente verdadeiro. |
| 19 | Split-Brain Mutation | `ingestao_lei._novo_attr = "teste"` | `src.scraper.ingestao_lei._novo_attr == "teste"` imediatamente verdadeiro. |
| 20 | Dual Import Identity | `import ingestao_lei; import src.scraper.ingestao_lei` | `ingestao_lei is sys.modules['src.scraper.ingestao_lei']` é estritamente `True`. |

---

## 2. Especificação Técnica Detalhada dos Componentes

### 2.1. `src/scraper/carregar_mongo.py`: Implementação de `def main(argv=None)`

O script deve ser refatorado para encapsular o bloco procedural de linha de comando em uma função pública e exportável.

#### Assinatura e Interface Canônica:
```python
def main(argv=None):
    """Ponto de entrada CLI para carregar documentos da lei no MongoDB."""
    parser_cli = argparse.ArgumentParser(
        prog="python -m src.scraper.carregar_mongo",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser_cli.add_argument(
        "fonte",
        nargs="?",
        default=FONTE_PADRAO,
        help=f"URL da lei compilada no Planalto ou caminho para arquivo HTML local (padrão: {FONTE_PADRAO})",
    )
    args = parser_cli.parse_args(argv)

    fonte = args.fonte
    colecoes = carregar_documentos(fonte)   # 1) lê e estrutura
    db = conectar()                         # 2) conecta
    inserir(db, colecoes)                   # 3) insere
    verificar(db)                           # 4) confere


if __name__ == "__main__":
    main()
```

#### Requisitos de Conformidade:
1. **Import `argparse`**: Deve ser adicionado no topo do arquivo junto à biblioteca padrão.
2. **Preservação de Funções Existentes**: As funções `conectar()`, `carregar_documentos(fonte)`, `inserir(db, colecoes)` e `verificar(db)` permanecem inalteradas.
3. **Preservação de Constantes**: `MONGO_URI`, `MONGO_DB_NAME`, `NOME_BANCO`, `LEI_ID`, `LEI_NOME`, `FONTE_PADRAO` permanecem inalteradas.
4. **Tratamento de `-h` e `--help`**: `parser_cli.parse_args(argv)` intercepta `-h` e `--help`, emite a mensagem de ajuda formatada com a docstring e termina via `sys.exit(0)`.
5. **Comportamento Padrão**: Se chamado sem argumentos (`argv=None` ou `argv=[]`), `args.fonte` recebe `FONTE_PADRAO`.

---

### 2.2. `src/scraper/ingestao_lei.py`: Verificação de `def main(argv=None)`

A função `main(argv=None)` já existe na linha 535 de `src/scraper/ingestao_lei.py`. Esta especificação estabelece os critérios de invariância que devem ser preservados:
1. **Assinatura**: `def main(argv=None):`
2. **Fachada Pública Preservada**:
   - `baixar_legislacao`
   - `salvar_bruto`
   - `extrair_metadados`
   - `extrair_estrutura`
   - `extrair_dispositivos`
3. **Ponto de Entrada**: `if __name__ == "__main__": main()`.

---

### 2.3. Shim de Depreciação `carregar_mongo.py` (Raiz)

O arquivo `carregar_mongo.py` na raiz deve ser atualizado para realizar o aliasing de módulo em `sys.modules` e delegar a execução CLI para `_target.main()`.

#### Código Especificado:
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

---

### 2.4. Shim de Depreciação `ingestao_lei.py` (Raiz)

O arquivo `ingestao_lei.py` na raiz deve ser atualizado para conter aliasing em `sys.modules` e o bloco de execução CLI `if __name__ == "__main__": _target.main()`.

#### Código Especificado:
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

---

## 3. Matriz de Resultados da Linha de Base (Baseline no Código Atual)

Executando a lógica de validação contra o código atual antes das alterações da Rodada 3:

| # | Item de Verificação | Estado Atual | Veredito | Causa Fática |
|---|---------------------|--------------|----------|--------------|
| 1 | `src/scraper/carregar_mongo.py` define `def main` | Ausente | **FAIL** | Lógica CLI procedural direta sob `if __name__ == "__main__":` |
| 2 | `src/scraper/carregar_mongo.py:main` aceita `argv` | Ausente | **FAIL** | Função não declarada |
| 3 | `src/scraper/carregar_mongo.py` invoca `main()` | Não invoca | **FAIL** | Executa código procedural solto |
| 4 | `src/scraper/ingestao_lei.py` define `def main` | Presente (L535) | **PASS** | Implementado com `argparse` |
| 5 | Funções da fachada pública em `ingestao_lei.py` | 5 funções presentes | **PASS** | Todas as 5 funções preservadas |
| 6 | Shim `carregar_mongo.py` emite `DeprecationWarning` | Presente (L7-12) | **PASS** | Emitido via `warnings.warn` |
| 7 | Shim `carregar_mongo.py` aliasing em `sys.modules` | Ausente | **FAIL** | Linha `sys.modules[__name__] = _target` não existe |
| 8 | Shim `carregar_mongo.py` delega CLI para `main()` | Quebrado | **FAIL** | Tenta importar `main` inexistente; lança `ImportError` |
| 9 | Shim `ingestao_lei.py` emite `DeprecationWarning` | Presente (L7-12) | **PASS** | Emitido via `warnings.warn` |
| 10 | Shim `ingestao_lei.py` aliasing em `sys.modules` | Ausente | **FAIL** | Linha `sys.modules[__name__] = _target` não existe |
| 11 | Shim `ingestao_lei.py` delega CLI para `main()` | Ausente | **FAIL** | Sem bloco `if __name__ == "__main__":` (silent no-op) |
| 12 | `import carregar_mongo; hasattr(mod, 'main')` | `False` | **FAIL** | Atributo `main` inexistente no módulo |
| 13 | `import ingestao_lei; hasattr(mod, 'main')` | `True` | **PASS** | Herdado via `from ... import *` |
| 14 | `sys.modules['carregar_mongo'] is sys.modules[...]` | `False` | **FAIL** | Split-brain (dois módulos distintos) |
| 15 | `sys.modules['ingestao_lei'] is sys.modules[...]` | `False` | **FAIL** | Split-brain (dois módulos distintos) |
| 16 | CLI `python carregar_mongo.py --help` | Crash | **FAIL** | `ImportError: cannot import name 'main'` |
| 17 | CLI `python ingestao_lei.py --help` | No-op | **FAIL** | Encerra sem processar argumentos |

---

## 4. O Script de Verificação Executável `verify_m3_r3.py`

O script de verificação formal foi implementado em:  
`e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r3_3\verify_m3_r3.py`

### Como Executar:
```powershell
# Execução direta no terminal
python .agents/teamwork/spec_miner_m3_r3_3/verify_m3_r3.py

# Modo detalhado (exibe cada teste com [PASS])
python .agents/teamwork/spec_miner_m3_r3_3/verify_m3_r3.py --verbose
```

### Estrutura das Fases de Verificação:
1. **Fase 1: Análise Estática de Código e AST**:
   - Analisa a AST de `src/scraper/carregar_mongo.py` e valida a presença de `def main(argv=None)`.
   - Analisa os shims da raiz para certificar a presença de `DeprecationWarning`, `sys.modules[__name__] = _target` e `if __name__ == "__main__": _target.main()`.
2. **Fase 2: Validação Dinâmica de Contratos e Aliasing**:
   - Testa a importação em memória isolada de `carregar_mongo` e `ingestao_lei`.
   - Confirma a emissão efetiva de `DeprecationWarning`.
   - Confirma `hasattr(carregar_mongo, 'main') == True` e `hasattr(ingestao_lei, 'main') == True`.
   - Valida in-process a saída de `main(["--help"])` com código 0.
   - Valida a identidade de referência `sys.modules['carregar_mongo'] is sys.modules['src.scraper.carregar_mongo']`.
   - Executa teste de mutação de atributo em tempo de execução para atestar imunidade estrita contra split-brain.
3. **Fase 3: Validação de Invocação de Linha de Comando (CLI)**:
   - Executa `python -m src.scraper.carregar_mongo --help` em subprocesso (saída 0).
   - Executa `python -m src.scraper.ingestao_lei --help` em subprocesso (saída 0).
   - Executa `python carregar_mongo.py --help` (saída 0, com warning em stderr e sem `ImportError`).
   - Executa `python ingestao_lei.py --help` (saída 0, com warning em stderr e repasse do manual do parser).

---

## 5. Orientações de Implementação para o Worker (`worker_m3_3`)

Para obter 100% de aprovação no gate de verificação da Rodada 3:

1. **Editar `src/scraper/carregar_mongo.py`**:
   - Adicionar `import argparse` no bloco de imports.
   - Substituir as linhas 105-116 pela definição `def main(argv=None):` conforme Seção 2.1 e o bloco `if __name__ == "__main__": main()`.
2. **Editar `carregar_mongo.py` (raiz)**:
   - Substituir o conteúdo pela implementação canônica com aliasing `sys.modules[__name__] = _target` e chamada `_target.main()` sob `__main__` (Seção 2.3).
3. **Editar `ingestao_lei.py` (raiz)**:
   - Substituir o conteúdo pela implementação canônica com aliasing `sys.modules[__name__] = _target` e chamada `_target.main()` sob `__main__` (Seção 2.4).
4. **Validar Executando**:
   - `python .agents/teamwork/spec_miner_m3_r3_3/verify_m3_r3.py`
   - O resultado deve ser: `TODOS OS CRITÉRIOS DO MILESTONE 3 - RODADA 3 FORAM ATENDIDOS COM SUCESSO! (STATUS FINAL: APROVADO, Código 0)`.
