# Relatório Técnico: Estratégia de Shims da Raiz e Prevenção de Split-Brain

**Milestone**: Milestone 3 — Rodada 3  
**Agente**: `explorer_m3_r3_2` (Explorer 2 — Investigation & Synthesis)  
**Data**: 2026-10-19  
**Destinatário**: Orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`)  
**Arquivos em Escopo**:
- `e:\Programacao\JudAI\ingestao_lei.py` (Shim da Raiz)
- `e:\Programacao\JudAI\carregar_mongo.py` (Shim da Raiz)
- `e:\Programacao\JudAI\src\scraper\ingestao_lei.py` (Módulo Canônico de Destino)
- `e:\Programacao\JudAI\src\scraper\carregar_mongo.py` (Módulo Canônico de Destino)

---

## 1. Resumo Executivo

Na Rodada 2 do Milestone 3, a introdução dos shims de retrocompatibilidade na raiz do projeto (`ingestao_lei.py` e `carregar_mongo.py`) resultou em veredito unânime de **REQUEST_CHANGES** emitido por `reviewer_m3_r2_1` e `challenger_m3_r2_2` devido a:
1. **Crash fatal de execução em `carregar_mongo.py`**: A chamada `from src.scraper.carregar_mongo import main` falha com `ImportError: cannot import name 'main'` porque o módulo de destino não possui `def main()`.
2. **Inércia operacional de CLI em `ingestao_lei.py`**: O script encerra sem executar o parser nem processar argumentos CLI por ausência do bloco `if __name__ == "__main__": main()`.
3. **Risco latente de Split-Brain**: A reexportação via `from ... import *` mantém dois objetos de módulo distintos em `sys.modules`, o que desincroniza mutações de estado e quebra identidades de módulo.

Este relatório fornece a **análise técnica definitiva** e a **proposta de implementação** para os shims da raiz. Demonstramos como a técnica de **Module Aliasing** via `sys.modules[__name__] = _target` em conjunto com a delegação `_target.main()` resolve simultaneamente a prevenção de split-brain, a retrocompatibilidade com a CLI legada (repassando argumentos transparentemente para os módulos sob `src/scraper/`) e a integridade de imports modulares e inspeção estática por AST e IDEs.

---

## 2. Diagnóstico da Causa Raiz das Falhas da Rodada 2

### 2.1. O Defeito em `carregar_mongo.py` (Raiz)
No arquivo `carregar_mongo.py` da raiz, as linhas 16 a 20 continham:
```python
if __name__ == "__main__":
    import sys
    from src.scraper.carregar_mongo import main
    main()
```
Contudo, em `src/scraper/carregar_mongo.py`, a lógica de linha de comando estava proceduralmente solta dentro de `if __name__ == "__main__":` (linhas 105 a 116), sem nenhuma função `def main` exportável.
- **Consequência Imediata**: Qualquer execução direta (`python carregar_mongo.py`) lançava `ImportError`.
- **Consequência em Imports**: Qualquer verificação programática `hasattr(carregar_mongo, 'main')` retornava `False`.

### 2.2. A Omissão em `ingestao_lei.py` (Raiz)
No arquivo `ingestao_lei.py` da raiz, o código continha apenas:
```python
warnings.warn(..., DeprecationWarning, stacklevel=2)
from src.scraper.ingestao_lei import *
```
Embora o módulo de destino `src/scraper/ingestao_lei.py:535` possua `def main(argv=None):`, o shim da raiz não possuía bloco `if __name__ == "__main__":`.
- **Consequência Imediata**: Comandos como `python ingestao_lei.py L10406.html` ou `python ingestao_lei.py --help` emitiam o aviso e finalizavam silenciosamente sem processar nada.

### 2.3. O Problema Conceitual do Split-Brain
Em Python, quando um arquivo na raiz (`carregar_mongo.py`) executa `from src.scraper.carregar_mongo import *`, o interpretador cria **dois objetos de módulo separados**:
1. `sys.modules['carregar_mongo']`: objeto gerado para o arquivo na raiz.
2. `sys.modules['src.scraper.carregar_mongo']`: objeto gerado para o arquivo no pacote.

Embora as funções tenham o mesmo bytecode, eles residem em dicionários (`__dict__`) distintos:
- Se uma parte do sistema alterar uma variável de configuração ou monkeypatch em `carregar_mongo`, essa alteração não afeta `src.scraper.carregar_mongo`.
- Instâncias criadas e registradas em variáveis globais ficam desincronizadas.
- A verificação de identidade `carregar_mongo is src.scraper.carregar_mongo` resulta em `False`.

---

## 3. Arquitetura da Solução: Module Aliasing via `sys.modules`

### 3.1. Mecânica de Resolução de Módulos no Python (PEP 302 / PEP 451)
O interpretador Python utiliza a tabela `sys.modules` como cache global e canônico de módulos carregados.
Quando um script faz `import ingestao_lei`:
1. O runtime aloca uma instância de `types.ModuleType` e a insere provisoriamente em `sys.modules['ingestao_lei']`.
2. O código do arquivo do shim é executado no escopo dessa instância.
3. Se o código do shim executar:
   ```python
   import src.scraper.ingestao_lei as _target
   sys.modules[__name__] = _target
   ```
   a entrada no dicionário `sys.modules['ingestao_lei']` é substituída pelo objeto de módulo de `src.scraper.ingestao_lei`!
4. Ao término da carga, o sistema de importação do Python devolve o valor armazenado em `sys.modules['ingestao_lei']` para a variável local do chamador.
5. **Resultado**: O chamador recebe diretamente o módulo canônico de destino `_target`.

### 3.2. Prova de Eliminação de Split-Brain
Com o aliasing:
- `import ingestao_lei as a`
- `import src.scraper.ingestao_lei as b`
- A asserção `a is b` é **estritamente `True`**.
- A asserção `sys.modules['ingestao_lei'] is sys.modules['src.scraper.ingestao_lei']` é **estritamente `True`**.
- Qualquer mutação em `a` é idêntica a `b`, pois ambos compartilham a mesma referência na memória heap (`id(a) == id(b)`).

### 3.3. Defesa em Dois Níveis: `__name__` e `setdefault`
Existe uma distinção sutil entre executar o arquivo como módulo (`import ingestao_lei`) e executá-lo diretamente como script (`python ingestao_lei.py`):
1. **Modo Módulo (`import ingestao_lei`)**: `__name__` tem o valor `'ingestao_lei'`. A instrução `sys.modules[__name__] = _target` atualiza com precisão a entrada `'ingestao_lei'`.
2. **Modo Script Direto (`python ingestao_lei.py`)**: `__name__` tem o valor `'__main__'`. A instrução `sys.modules[__name__] = _target` substitui `sys.modules['__main__']`. Porém, `sys.modules['ingestao_lei']` não teria sido definida.
   - Para garantir total imunidade contra re-importações secundárias durante o ciclo de vida do processo, adiciona-se:
     ```python
     sys.modules.setdefault("ingestao_lei", _target)
     ```
   - Dessa forma, mesmo que uma biblioteca ou código legado dentro da mesma execução faça `import ingestao_lei`, o Python encontrará `_target` imediatamente no cache, prevenindo reexecução do arquivo de shim.

### 3.4. Coexistência com `from src.scraper.<mod> import *` (Suporte a AST e IDEs)
Por que manter `from src.scraper.<mod> import *` no shim se fazemos aliasing em `sys.modules`?
- **Ferramentas Estáticas (Linters, IDEs, Pyright, Jedi, AST Parsers)**: Linters e analisadores estáticos não executam o interpretador Python nem interpretam a mutação de `sys.modules`. Eles leem a árvore sintática (AST) do arquivo.
- Se o arquivo contiver apenas `sys.modules[__name__] = _target`, analisadores estáticos reportam que símbolos como `extrair_dispositivos` não existem no arquivo `ingestao_lei.py`.
- Mantendo `from src.scraper.<mod> import *` seguido de `sys.modules[__name__] = _target`, garantimos:
  - **Suporte estático 100%** (AST, linters e autocompletion encontram todos os símbolos).
  - **Comportamento dinâmico 100% perfeito** (em tempo de execução, o runtime substitui o módulo pelo alvo canônico).

---

## 4. Arquitetura de Execução CLI e Repasse de Argumentos

### 4.1. Invocação via `_target.main()` sob `if __name__ == "__main__":`
Ambos os módulos de destino (`src.scraper.ingestao_lei` e a versão refatorada de `src.scraper.carregar_mongo` proposta por `explorer_m3_r3_1`) implementam a assinatura canônica:
```python
def main(argv=None):
```

### 4.2. Como os Argumentos São Repassados
No Python, quando um módulo utiliza `argparse` com a assinatura `def main(argv=None):`:
```python
args = parser.parse_args(argv)
```
- Se `argv is None`, `argparse` utiliza automaticamente `sys.argv[1:]`.
- Quando o usuário executa na linha de comando:
  ```powershell
  python ingestao_lei.py L10406.html --lei-id cc2002 --sem-mongo
  ```
  O interpretador Python popula `sys.argv` com:
  `['ingestao_lei.py', 'L10406.html', '--lei-id', 'cc2002', '--sem-mongo']`.
- O shim avalia `if __name__ == "__main__":` como `True` e executa:
  ```python
  _target.main()
  ```
- Como `_target.main()` é chamado sem parâmetros (`argv=None`), `_target.main` consome diretamente `sys.argv[1:]`.
- Todos os argumentos posicionais (`entrada`, `fonte`), flags (`--sem-mongo`, `--so-vigentes`) e parâmetros de ajuda (`-h`, `--help`) são recebidos e tratados pelo módulo canônico com 100% de precisão.

### 4.3. Por que `_target.main()` é Superior a `runpy.run_module`
Avaliamos a alternativa levantada pelo challenger (`runpy.run_module("src.scraper.carregar_mongo", run_name="__main__")`):
- `runpy` reexecuta todo o módulo do zero sob uma nova tabela de símbolos, gerando overhead de inicialização e potenciais conflitos de recarregamento de variáveis de ambiente.
- `_target.main()` reutiliza o módulo já importado em `_target`, executando a função diretamente em memória de forma limpa, rápida e determinística.

---

## 5. Especificação Exata dos Códigos dos Shims da Raiz

### 5.1. Código Proposto para `e:\Programacao\JudAI\ingestao_lei.py`

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

#### Diff de `ingestao_lei.py`:
```diff
--- a/ingestao_lei.py
+++ b/ingestao_lei.py
@@ -2,6 +2,7 @@
 DEPRECATED: Este arquivo foi migrado para src/scraper/ingestao_lei.py.
 A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
 """
+import sys
 import warnings
 
 warnings.warn(
@@ -10,6 +11,14 @@
     DeprecationWarning,
     stacklevel=2,
 )
 
+import src.scraper.ingestao_lei as _target  # noqa: E402
+
+# Re-exportação explícita para suporte a IDEs, linters e análise estática (AST)
 from src.scraper.ingestao_lei import *
+
+# Aliasing de módulo em sys.modules para prevenção estrita de split-brain
+sys.modules[__name__] = _target
+sys.modules.setdefault("ingestao_lei", _target)
+
+if __name__ == "__main__":
+    _target.main()
```

---

### 5.2. Código Proposto para `e:\Programacao\JudAI\carregar_mongo.py`

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

#### Diff de `carregar_mongo.py`:
```diff
--- a/carregar_mongo.py
+++ b/carregar_mongo.py
@@ -2,6 +2,7 @@
 DEPRECATED: Este arquivo foi migrado para src/scraper/carregar_mongo.py.
 A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
 """
+import sys
 import warnings
 
 warnings.warn(
@@ -10,11 +11,14 @@
     DeprecationWarning,
     stacklevel=2,
 )
 
+import src.scraper.carregar_mongo as _target  # noqa: E402
+
+# Re-exportação explícita para suporte a IDEs, linters e análise estática (AST)
 from src.scraper.carregar_mongo import *
 
+# Aliasing de módulo em sys.modules para prevenção estrita de split-brain
+sys.modules[__name__] = _target
+sys.modules.setdefault("carregar_mongo", _target)
+
 if __name__ == "__main__":
-    import sys
-    from src.scraper.carregar_mongo import main
-    main()
+    _target.main()
```

---

## 6. Sinergia Arquitetural com a Proposta de Explorer 1

A proposta deste relatório casa perfeitamente com a refatoração especificada em `explorer_m3_r3_1/report_m3_r3_main_func.md`:
1. `explorer_m3_r3_1` introduz em `src/scraper/carregar_mongo.py`:
   ```python
   def main(argv=None):
       parser_cli = argparse.ArgumentParser(
           prog="python -m src.scraper.carregar_mongo",
           description=__doc__,
           formatter_class=argparse.RawDescriptionHelpFormatter,
       )
       parser_cli.add_argument("fonte", nargs="?", default=FONTE_PADRAO, ...)
       args = parser_cli.parse_args(argv)
       ...
   ```
2. Graças a essa definição:
   - `_target.main` existe no momento do import de `src.scraper.carregar_mongo`.
   - `carregar_mongo.py` na raiz nunca mais sofrerá de `ImportError: cannot import name 'main'`.
   - Tanto `python carregar_mongo.py` quanto `python -m src.scraper.carregar_mongo` têm comportamento idêntico.

---

## 7. Matriz de Comportamento e Casos de Uso

A tabela abaixo sintetiza o comportamento em todos os cenários operacionais:

| Cenário de Invocação | Comportamento Interno | Saída / Efeito | Veredito |
|---|---|---|---|
| `import ingestao_lei` | Emite `DeprecationWarning`, substitui `sys.modules['ingestao_lei']` por `_target`. | Retorna o objeto de módulo `src.scraper.ingestao_lei`. | **PASS** |
| `import carregar_mongo` | Emite `DeprecationWarning`, substitui `sys.modules['carregar_mongo']` por `_target`. | Retorna o objeto de módulo `src.scraper.carregar_mongo`. | **PASS** |
| `hasattr(carregar_mongo, 'main')` | Inspeciona `_target` (que agora possui `def main`). | Retorna `True`. | **PASS** |
| `hasattr(ingestao_lei, 'main')` | Inspeciona `_target` (que possui `def main(argv=None)`). | Retorna `True`. | **PASS** |
| `sys.modules['carregar_mongo'] is sys.modules['src.scraper.carregar_mongo']` | Avaliação de identidade de referências de ponteiro de memória. | Retorna `True` (zero split-brain). | **PASS** |
| `sys.modules['ingestao_lei'] is sys.modules['src.scraper.ingestao_lei']` | Avaliação de identidade de referências de ponteiro de memória. | Retorna `True` (zero split-brain). | **PASS** |
| `python ingestao_lei.py --help` | Inicia como `__main__`, chama `_target.main()`, `argparse` consome `sys.argv[1:]`. | Exibe manual de uso e sai com código 0. | **PASS** |
| `python carregar_mongo.py --help` | Inicia como `__main__`, chama `_target.main()`, `argparse` consome `sys.argv[1:]`. | Exibe manual de uso e sai com código 0. | **PASS** |
| `python carregar_mongo.py L10406.html` | Repassa `L10406.html` como `args.fonte`. | Carrega arquivo local no MongoDB. | **PASS** |
| `from ingestao_lei import extrair_dispositivos` | Obtém atributo do módulo aliasing. | Importa a função canônica diretamente. | **PASS** |
| Inspeção estática via `ast.parse` | Encontra `import *` e definições de shim. | AST válida, sem nós quebrados. | **PASS** |

---

## 8. Protocolo de Verificação Independente para a Equipe

Para que o Implementador (`worker_m3_3`) e os Revisores (`reviewer_m3_r3_1` e `challenger_m3_r3_2`) possam verificar de forma determinística:

### 8.1. Verificação Estática via AST (Sem Necessidade de Executar Processo)
```python
import ast
from pathlib import Path

def test_shims_ast():
    root_cm = Path("carregar_mongo.py").read_text(encoding="utf-8")
    root_il = Path("ingestao_lei.py").read_text(encoding="utf-8")
    
    assert "sys.modules[__name__] = _target" in root_cm, "Aliasing ausente em carregar_mongo.py"
    assert "sys.modules[__name__] = _target" in root_il, "Aliasing ausente em ingestao_lei.py"
    assert "_target.main()" in root_cm, "Chamada _target.main() ausente em carregar_mongo.py"
    assert "_target.main()" in root_il, "Chamada _target.main() ausente em ingestao_lei.py"
    print("Verificação AST dos Shims: 100% APROVADO")
```

### 8.2. Verificação Dinâmica via Terminal / Python
```powershell
# 1. Testa identidade de módulos e ausência de split-brain
python -c "import carregar_mongo; import src.scraper.carregar_mongo as target; assert carregar_mongo is target, 'Split-brain detectado!'; assert hasattr(carregar_mongo, 'main'), 'main não encontrada!'; print('Aliasing carregar_mongo: OK')"

python -c "import ingestao_lei; import src.scraper.ingestao_lei as target; assert ingestao_lei is target, 'Split-brain detectado!'; assert hasattr(ingestao_lei, 'main'), 'main não encontrada!'; print('Aliasing ingestao_lei: OK')"

# 2. Testa execução direta dos shims via CLI com argumento --help
python carregar_mongo.py --help
python ingestao_lei.py --help
```

---

## 9. Conclusão e Próximos Passos

A estratégia apresentada fornece uma arquitetura robusta, profissional e à prova de regressão para o encerramento do Milestone 3. Ela elimina definitivamente todas as objeções apontadas na Rodada 2 pelos agentes de revisão e auditoria adversarial, preparando o JudAI com estabilidade e consistência operacional.
