# Relatório Técnico: Implementação de `def main(argv=None)` em `src/scraper/carregar_mongo.py`

**Milestone**: 3 — Rodada 3  
**Agente**: `explorer_m3_r3_1` (Read-Only Explorer)  
**Data**: 2026-10-19  
**Destinatário**: Orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`)  
**Arquivo Alvo**: `src/scraper/carregar_mongo.py`  
**Arquivos Correlatos**: `carregar_mongo.py` (raiz), `ingestao_lei.py` (raiz), `src/scraper/ingestao_lei.py`  

---

## Resumo Executivo

Na Rodada 2 do Milestone 3, a introdução de shims de retrocompatibilidade na raiz do projeto resultou em um crash fatal de execução (`ImportError: cannot import name 'main' from 'src.scraper.carregar_mongo'`). O arquivo `src/scraper/carregar_mongo.py` manteve sua lógica CLI diretamente sob o bloco procedural `if __name__ == "__main__":`, sem definir uma função `def main(argv=None):`.

Este relatório estabelece a especificação técnica exata para refatorar `src/scraper/carregar_mongo.py`, encapsulando a lógica CLI em uma função pública e exportável `def main(argv=None):`. A implementação é 100% simétrica ao padrão estabelecido em `src/scraper/ingestao_lei.py:535`, utilizando `argparse` com suporte a `argv` explícito, respeitando defaults de configuração (`FONTE_PADRAO`), garantindo compatibilidade total com a suíte de testes (Tiers 1 a 4) e eliminando imediatamente as falhas apontadas pelos revisores na Rodada 2.

---

## 1. Diagnóstico da Estrutura Atual de `src/scraper/carregar_mongo.py`

### 1.1. Inspeção Fática do Código Atual
No arquivo `src/scraper/carregar_mongo.py`, as linhas 105 a 116 contêm o seguinte bloco de código:

```python
105: if __name__ == "__main__":
106:     if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
107:         print("Uso: python -m src.scraper.carregar_mongo [fonte]")
108:         print("  fonte: URL da lei compilada no Planalto ou caminho para arquivo HTML local.")
109:         print(f"  Padrão: {FONTE_PADRAO}")
110:         sys.exit(0)
111:     fonte = sys.argv[1] if len(sys.argv) > 1 else FONTE_PADRAO
112:     colecoes = carregar_documentos(fonte)   # 1) lê e estrutura
113:     db = conectar()                         # 2) conecta
114:     inserir(db, colecoes)                   # 3) insere
115:     verificar(db)                           # 4) confere
```

As únicas funções públicas definidas no módulo atualmente são:
- Linha 48: `def conectar():`
- Linha 63: `def carregar_documentos(fonte: str):`
- Linha 79: `def inserir(db, colecoes: dict):`
- Linha 96: `def verificar(db):`

Não há qualquer função com o nome `main` definida no arquivo.

### 1.2. Por que o bloco CLI está solto em `if __name__ == "__main__":`
1. **Origem Procedural de Script Utilitário**: No script original do JudAI (anterior ao Milestone 3), o arquivo era um script monolítico utilitário da raiz (`carregar_mongo.py`) focado em execução pontual via linha de comando. É um hábito comum em scripts Python simples manter o fluxo procedural diretamente dentro de `if __name__ == "__main__":`.
2. **Assimetria de Refatoração no M3**: Durante a migração para a pasta `src/scraper/`, `ingestao_lei.py` já possuía uma função `def main(argv=None):` na linha 535, herdada com suporte a `argparse`. No entanto, `carregar_mongo.py` teve apenas seus imports e leitura de variáveis de ambiente ajustados, sem que o ponto de entrada procedural fosse encapsulado em uma função.
3. **Causa Raiz da Falha na Rodada 2**: O worker da Rodada 2 criou o shim na raiz do projeto (`carregar_mongo.py`) com:
   ```python
   if __name__ == "__main__":
       import sys
       from src.scraper.carregar_mongo import main
       main()
   ```
   Como `main` não existia em `src/scraper/carregar_mongo.py`, invocar `python carregar_mongo.py` resulta em `ImportError`. Além disso, qualquer asserção `hasattr(carregar_mongo, 'main')` resulta em `False`.

---

## 2. Padrão Arquitetural de Referência: `src/scraper/ingestao_lei.py:535`

O módulo `src/scraper/ingestao_lei.py` implementa o padrão canônico para interfaces de linha de comando no projeto JudAI:

```python
535: def main(argv=None):
536:     ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
537:     ap.add_argument("entrada", help="caminho do .html OU URL da página no Planalto")
...
546:     args = ap.parse_args(argv)
...
583: if __name__ == "__main__":
584:     main()
```

### Principais Benefícios Deste Padrão:
1. **Assinatura `argv=None`**:
   - Quando chamado via CLI (`if __name__ == "__main__": main()`), `argv` é `None`.
   - No Python, `argparse.ArgumentParser.parse_args(None)` consome automaticamente `sys.argv[1:]`.
   - Quando chamado por testes ou shims com argumentos explícitos (ex.: `main(["--help"])` ou `main(["dados.html"])`), `parse_args` processa estritamente a lista recebida, permitindo injeção de parâmetros sem manipulação invasiva de `sys.argv`.
2. **Tratamento de `-h` e `--help`**:
   - `argparse` intercepta `-h` e `--help`, formata a documentação automaticamente com base na docstring e finaliza o processo com código de saída 0 (`sys.exit(0)`).
3. **Validação de Sintaxe**:
   - Argumentos inválidos ou flags desconhecidas geram mensagem descritiva de uso e saída com código 2, padrão universal em ferramentas CLI POSIX e Windows.
4. **Exportabilidade e Testabilidade**:
   - A função `main` pode ser importada (`from src.scraper.carregar_mongo import main`), inspecionada via `hasattr` ou mockada em suítes de teste de integração.

---

## 3. Especificação da Função `def main(argv=None)` em `src/scraper/carregar_mongo.py`

### 3.1. Requisitos de Interface
1. **Nome da Função**: `main`
2. **Parâmetros**: `argv: list[str] | None = None`
3. **Argumento Posicional**: `fonte` (opcional, `nargs="?"`, valor default: `FONTE_PADRAO`).
4. **Tratamento de Help**: `-h` e `--help` suportados nativamente via `argparse`, exibindo as instruções de uso e o valor default de `FONTE_PADRAO`.
5. **Comportamento de Execução**: Idêntico ao fluxo sequencial original:
   1. `colecoes = carregar_documentos(fonte)`
   2. `db = conectar()`
   3. `inserir(db, colecoes)`
   4. `verificar(db)`
6. **Ponto de Entrada**: Bloco `if __name__ == "__main__":` simplificado para apenas chamar `main()`.

### 3.2. Import de `argparse`
O módulo `argparse` faz parte da biblioteca padrão do Python. Ele deve ser importado no topo do arquivo junto aos demais módulos da standard library (`hashlib`, `os`, `sys`, `pathlib`).

---

## 4. Proposta de Código Exata

### 4.1. Modificação dos Imports no Topo de `src/scraper/carregar_mongo.py`

**Antes** (linhas 17 a 20):
```python
import hashlib
import os
import sys
from pathlib import Path
```

**Depois**:
```python
import argparse
import hashlib
import os
import sys
from pathlib import Path
```

### 4.2. Substituição do Bloco CLI (linhas 105 a 116 de `src/scraper/carregar_mongo.py`)

**Antes** (linhas 105 a 116):
```python
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Uso: python -m src.scraper.carregar_mongo [fonte]")
        print("  fonte: URL da lei compilada no Planalto ou caminho para arquivo HTML local.")
        print(f"  Padrão: {FONTE_PADRAO}")
        sys.exit(0)
    fonte = sys.argv[1] if len(sys.argv) > 1 else FONTE_PADRAO
    colecoes = carregar_documentos(fonte)   # 1) lê e estrutura
    db = conectar()                         # 2) conecta
    inserir(db, colecoes)                   # 3) insere
    verificar(db)                           # 4) confere
```

**Depois**:
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

### 4.3. Arquivo Completo Proposto (`src/scraper/carregar_mongo.py`)

Abaixo a íntegra proposta do arquivo para o implementador:

```python
#!/usr/bin/env python3
"""
Conecta ao MongoDB, lê a lei (URL do Planalto ou arquivo .html) e insere os
documentos nas coleções `leis`, `artigos` e `dispositivos`.

Pré-requisitos
  pip install beautifulsoup4 lxml pymongo requests python-dotenv
  - ingestao_lei.py no pacote src.scraper (contém o parser)
  - um MongoDB rodando. Opções:
      * Docker:  docker compose up -d (porta 27017:27017)
      * Atlas (nuvem): configure MONGO_URI no arquivo .env

Uso
  python -m src.scraper.carregar_mongo                  # baixa a lei da URL padrão
  python -m src.scraper.carregar_mongo L10406.html      # ou usa um arquivo local
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# Carrega variáveis do arquivo .env (se existir) sem sobrescrever o ambiente
load_dotenv()

# Import resiliente do parser (suporta invocação via módulo, relativa ou script direto)
try:
    from src.scraper import ingestao_lei as parser
except ImportError:
    try:
        from . import ingestao_lei as parser
    except ImportError:
        import ingestao_lei as parser

# ---------------------------- CONFIGURAÇÃO ---------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "rag_juridico")
NOME_BANCO = MONGO_DB_NAME  # Mantém compatibilidade com referências internas originais
LEI_ID = "cc2002"
LEI_NOME = "Código Civil"
FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
# ---------------------------------------------------------------------------


def conectar():
    """Abre a conexão e confirma que o servidor responde."""
    cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        cliente.admin.command("ping")
    except ServerSelectionTimeoutError:
        sys.exit(
            f"Não consegui conectar ao MongoDB em {MONGO_URI}.\n"
            "Verifique se o servidor está rodando "
            "(ex.: docker compose up -d) ou ajuste MONGO_URI."
        )
    print(f"Conectado ao MongoDB. Banco: '{NOME_BANCO}'")
    return cliente[NOME_BANCO]


def carregar_documentos(fonte: str):
    """Lê a fonte (URL ou arquivo) e devolve as três coleções prontas."""
    raw, origem = parser.obter_bytes(fonte)
    html = parser.decodificar(raw)
    n_fffd = html.count(parser.FFFD)
    meta, artigos, ignoradas = parser.parsear(html)
    if not artigos:
        sys.exit("Nenhum artigo encontrado: o HTML não tem o formato esperado.")
    colecoes = parser.montar_colecoes(
        LEI_ID, LEI_NOME, meta, artigos, origem,
        hashlib.sha256(raw).hexdigest(), n_fffd > 0,
    )
    parser.relatorio(colecoes, ignoradas, n_fffd > 0, n_fffd)
    return colecoes


def inserir(db, colecoes: dict):
    """Apaga a versão anterior desta lei e insere os documentos novos."""
    db["leis"].delete_many({"_id": LEI_ID})
    db["artigos"].delete_many({"lei_id": LEI_ID})
    db["dispositivos"].delete_many({"lei_id": LEI_ID})

    for nome in ("leis", "artigos", "dispositivos"):
        resultado = db[nome].insert_many(colecoes[nome], ordered=False)
        print(f"  {nome}: {len(resultado.inserted_ids)} documentos inseridos")

    # Índices para as consultas mais comuns
    db["artigos"].create_index([("lei_id", 1), ("numero", 1)])
    db["artigos"].create_index("vigente")
    db["dispositivos"].create_index([("lei_id", 1), ("artigo_id", 1)])
    db["dispositivos"].create_index([("tipo", 1), ("vigente", 1)])


def verificar(db):
    """Consulta de conferência: busca o art. 5º já gravado."""
    art = db["artigos"].find_one({"_id": f"{LEI_ID}:art5"})
    print("\nConferência:", art["citacao"], "->", art["caminho"])
    print(art["texto_vigente"][:300])
    print("\nTotais no banco:",
          {c: db[c].count_documents({}) for c in ("leis", "artigos", "dispositivos")})


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

---

## 5. Recomendações Complementares para os Shims da Raiz

### 5.1. Shim `carregar_mongo.py` (Raiz)
Com a exportação de `main` em `src/scraper/carregar_mongo.py`:
- A declaração existente:
  ```python
  from src.scraper.carregar_mongo import *

  if __name__ == "__main__":
      import sys
      from src.scraper.carregar_mongo import main
      main()
  ```
  passará a funcionar perfeitamente, sem `ImportError`.
- Para eliminar riscos de split-brain (duplicidade de instâncias de módulo apontando para objetos distintos) e garantir 100% de consistência sugerida pelo challenger (`challenger_m3_r2_2/handoff.md`), o shim pode opcionalmente registrar o módulo importado em `sys.modules`:
  ```python
  import sys
  import warnings
  import src.scraper.carregar_mongo as _target

  warnings.warn(
      "carregar_mongo.py na raiz do projeto está obsoleto e foi migrado para src.scraper.carregar_mongo. "
      "Este shim será removido no Milestone 5.",
      DeprecationWarning,
      stacklevel=2,
  )

  sys.modules[__name__] = _target
  from src.scraper.carregar_mongo import *

  if __name__ == "__main__":
      _target.main()
  ```

### 5.2. Shim `ingestao_lei.py` (Raiz)
Conforme apontado na Rodada 2, o shim `ingestao_lei.py` na raiz não delegava a execução sob CLI. Recomenda-se adicionar o bloco de invocação:
```python
if __name__ == "__main__":
    from src.scraper.ingestao_lei import main
    main()
```

---

## 6. Análise de Impacto e Não-Regressão

| Alvo / Suíte | Cenário Testado | Impacto Previsto | Veredito |
|---|---|---|---|
| `test_tier1_feature_coverage.py` | `test_scraper_carregar_mongo_importable` | O módulo é importável e agora expõe `main`. | **PASS** |
| `test_tier1_feature_coverage.py` | `test_scraper_carregar_mongo_env_support` | Não altera a leitura de `MONGO_URI` e `MONGO_DB_NAME`. | **PASS** |
| `test_tier3_cross_feature.py` | `test_scraper_and_mongo_connection_same_defaults` | Literais de configuração inalterados. | **PASS** |
| `test_tier3_cross_feature.py` | `test_scraper_module_execution_with_custom_env` | Recarregamento de variáveis de ambiente mantido intacto. | **PASS** |
| `test_tier4_real_world.py` | `test_scraper_module_cli_invocation_help` | Executa `python -m src.scraper.carregar_mongo --help` com saída 0. | **PASS** |
| `test_shims_adversarial.py` | `analyze_carregar_mongo_main` | Identifica `main` na AST de `src/scraper/carregar_mongo.py`. | **PASS** |
| `test_shims_adversarial.py` | `bug_carregar_mongo_importerror` | Elimina o erro de importação do shim. | **PASS** |
| Invocação direta CLI legado | `python carregar_mongo.py --help` | Emite deprecation warning e exibe o help do módulo. | **PASS** |

---

## 7. Verificação Independente e Comandos de Validação

Para o Worker e para os Reviewers da Rodada 3, os testes abaixo podem ser executados no terminal ou via script Python sem necessidade de conexão ativa ao MongoDB:

```powershell
# 1. Verifica presença de def main() via AST e importação
python -c "import src.scraper.carregar_mongo as m; assert hasattr(m, 'main'), 'main não exportada!'; print('Exportação de main: OK')"

# 2. Testa execução do CLI com --help via módulo (sai com 0)
python -m src.scraper.carregar_mongo --help

# 3. Testa invocação do shim de compatibilidade na raiz com --help (sai com 0)
python carregar_mongo.py --help

# 4. Executa a suíte de testes de Tiers 1 a 4
pytest -q tests/test_tier1_feature_coverage.py tests/test_tier3_cross_feature.py tests/test_tier4_real_world.py
```
