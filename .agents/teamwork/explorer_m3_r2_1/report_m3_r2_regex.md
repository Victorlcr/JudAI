# Relatório Técnico de Engenharia Reversa e Estratégia de Correção de Regex: Milestone 3 (Rodada 2)

**Agente**: `explorer_m3_r2_1` (Teamwork Explorer / Read-Only Investigation)  
**Data**: 2026-10-18T23:48:00Z  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Alvo Principal**: `src/scraper/ingestao_lei.py` (Linhas 75 e 79)  
**Contexto**: Análise de regressão apontada pelo `reviewer_m3_1` no Gate do Milestone 3, formulação de recomendação cirúrgica para o Worker e verificação de integridade Unicode em todo o parser.

---

## 1. Sumário Executivo

A investigação confirmou com 100% de precisão o achado do revisor (`reviewer_m3_1`):
1. **Regressão Crítica em `RE_PAR` (Linha 79)**: Ao tentar sanitizar os caracteres não-ASCII literais do arquivo histórico original (`ingestao_lei.py`), o caractere de substituição Unicode (`\ufffd`) foi acidentalmente deletado em vez de ser convertido para sua sequência de escape `\ufffd`. Isso gerou a subexpressão `(?:§|)`, cuja alternância vazia (`|`) casa com a string vazia (`^`) em qualquer linha. Como efeito colateral catastrófico:
   - **Falsos Positivos**: Qualquer linha dentro de um artigo que inicie por dígitos (listas numéricas `"1. ... "`, datas `"2002. ..."`, prazos `"15 dias..."`) é erroneamente capturada como um novo parágrafo (`§ 1º`, `§ 2002º`, `§ 15º`), corrompendo a hierarquia legislativa.
   - **Falsos Negativos**: Parágrafos em arquivos com codificação danificada (mojibake onde o `§` virou `\ufffd`) deixam de casar, pois `\ufffd` não é um dígito e o ramo vazio consome zero caracteres antes de `{NUM}` falhar.
2. **Regressão em `ORD` (Linha 75)**: A remoção de `\ufffd` da classe de caracteres ordinais `[º°ª]` faz com que números ordinais danificados (ex.: `Art. 1` ou `§ 1`) não capturem o símbolo ordinal, vazando o caractere de substituição para o início do texto do dispositivo (`corpo`).
3. **Auditoria Geral de `\ufffd` no Parser**: Todas as demais expressões regulares (`RE_INC`, `RE_PUN`, `RE_HEAD`, `RE_FIM`, `RE_NOTA`) e a constante `FFFD = "\ufffd"` (linha 47) estão corretas, resilientes e devidamente protegidas contra mojibake.
4. **Resolução**: A correção cirúrgica consiste na substituição de exatamente 2 linhas em `src/scraper/ingestao_lei.py` e na exclusão dos 2 scripts legados da raiz (`ingestao_lei.py` e `carregar_mongo.py`).

---

## 2. Anatomia Detalhada da Regressão (Linhas 75 e 79)

### 2.1. O Problema da Alternância Vazia em `RE_PAR` (Linha 79)

No arquivo histórico `e:\Programacao\JudAI\ingestao_lei.py`:
```python
RE_PAR = re.compile(rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
```
*(onde `` era o byte literal UTF-8 `\xef\xbf\xbd`, correspondente a `\ufffd`)*.

No arquivo migrado `src/scraper/ingestao_lei.py`:
```python
RE_PAR = re.compile(rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
```

#### Análise Léxica e Semântica do Regex:
- O grupo `(?:§|)` define uma alternância não-capturadora com dois ramos:
  1. Ramo 1: `§` (símbolo de seção / parágrafo, `U+00A7`).
  2. Ramo 2: ` ` (cadeia vazia de 0 caracteres, à direita do pipe `|`).
- **Mecanismo da Falha (Falsos Positivos)**:
  - Quando a linha avaliada começa com qualquer caractere diferente de `§`, o Ramo 1 falha.
  - O motor de regex do Python (`re`) avalia o Ramo 2: a cadeia vazia **sempre casa com sucesso na posição 0** (`^`).
  - Em seguida, `\s*` consome espaços iniciais opcionais.
  - Se o texto começar por um numeral (reconhecido por `{NUM} = r"\d{1,3}(?:\.\d{3})+|\d+"`), `{NUM}` captura esse numeral.
  - `{ORD}` e `{SUF}` possuem quantificadores opcionais (`?`), casando cadeia vazia.
  - `\s*[.\-–—]*\s*` consome pontuações típicas de enumeração (como ponto `.` ou travessão `-`).
  - `(.*)` captura o restante da linha como texto do parágrafo.
- **Exemplos Reais Afetados**:
  1. Enumeração pós-caput: `"1. São princípios fundamentais..."` -> Casa como Parágrafo com número `"1"` e rótulo `"§ 1º"`.
  2. Ano/Data em disposições: `"2002. Disposição transitória..."` -> Casa como Parágrafo com número `"2002"` e rótulo `"§ 2002"`.
  3. Prazos processuais/materiais: `"10 dias após a notificação..."` -> Casa como Parágrafo com número `"10"` e rótulo `"§ 10º"`.
- **Mecanismo da Falha (Falsos Negativos em Mojibake)**:
  - Texto de entrada: `"\ufffd 1º O casamento é civil..."` (onde `§` virou `\ufffd` por má decodificação do Windows-1252).
  - Posição 0: `^(?:§|)` testa `§` (falso). Testa o ramo vazio: casa com 0 caracteres na posição 0.
  - Próximo token no regex: `\s*({NUM})`.
  - O ponteiro do texto ainda está na posição 0! O caractere na posição 0 é `\ufffd`.
  - Como `\ufffd` não é dígito (`\d`), a subexpressão `({NUM})` falha.
  - Conclusão: `RE_PAR.match(...)` retorna `None`. O parágrafo danificado não é reconhecido como parágrafo, sendo incorretamente anexado ao texto do dispositivo anterior como resíduo (`ultimo["texto"]`).

---

### 2.2. A Omissão de `\ufffd` em `ORD` (Linha 75)

No arquivo histórico `e:\Programacao\JudAI\ingestao_lei.py`:
```python
ORD = r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito
```

No arquivo migrado `src/scraper/ingestao_lei.py`:
```python
ORD = r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito
```

#### Análise Léxica e Efeito Colateral:
- `{ORD}` é interpolado tanto em `RE_ART` quanto em `RE_PAR`:
  - `RE_ART = re.compile(rf"^Art\.?\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)`
  - `RE_PAR = re.compile(rf"^(?:§|...)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)`
- Quando um documento HTML do Planalto é decodificado com perda de acentos, os caracteres ordinais (`º` = `0xBA`, `ª` = `0xAA`, `°` = `0xB0` em CP1252) são substituídos por `\ufffd`.
- **Cenário de Teste**: `"Art. 1\ufffd Toda pessoa..."`
  - Com `ORD` sem `\ufffd`:
    - `Art\.?\s*` consome `"Art. "`
    - `({NUM})` consome `"1"`
    - `{ORD}` avalia `[º°ª]+`: falha em casar `\ufffd`. Como possui `?`, casa vazio.
    - `{SUF}` casa vazio.
    - `\s*[.\-–—]*\s*`: o caractere seguinte é `\ufffd`. Não pertence a `[.\-–—]`. Casa vazio.
    - `(.*)` captura `"\ufffd Toda pessoa..."`.
    - **Resultado Anômalo**: O número extraído é `"1"`, mas o corpo do artigo (`m.group(3)`) herda o lixo `"\ufffd Toda pessoa..."` em vez de `"Toda pessoa..."`.
- **Com a Correção (`[º°ª\ufffd]+`)**:
  - `{ORD}` consome `"\ufffd"`.
  - `\s*[.\-–—]*\s*` consome os espaços/pontuações subsequentes.
  - `(.*)` captura estritamente `"Toda pessoa..."`.
  - O texto do dispositivo permanece limpo.

---

## 3. Varredura Completa do Parser por Omissões de `\ufffd`

Foi realizada uma auditoria exaustiva em todas as expressões regulares e constantes de `src/scraper/ingestao_lei.py` e `src/scraper/carregar_mongo.py`.

### 3.1. Tabela de Auditoria de Regex do Parser

| Identificador | Expressão Atual em `src/scraper/ingestao_lei.py` | Suporte a Mojibake / `\ufffd` | Diagnóstico |
|---|---|---|---|
| `NUM` (l. 74) | `r"\d{1,3}(?:\.\d{3})+|\d+"` | Não aplicável (apenas dígitos) | **CORRETO** |
| `ORD` (l. 75) | `r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"` | **Ausente** (removido no M3 Round 1) | **REGRESSÃO — Requer `\ufffd`** |
| `SUF` (l. 76) | `r"(?:\s*-\s*([A-Z])\b)?"` | Não aplicável (letras ASCII de sufixo -A, -B) | **CORRETO** |
| `RE_ART` (l. 78) | `rf"^Art\.?\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$"` | Depende de `ORD` | **Corrigido via `ORD`** |
| `RE_PAR` (l. 79) | `rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$"` | **Quebrado** (`|)` vazio, sem `\ufffd`) | **REGRESSÃO CRÍTICA — Requer `(?:§\|\ufffd)`** |
| `RE_PUN` (l. 80) | `r"^Par.grafo\s+.nico\s*[.\-–—]*\s*(.*)$"` | Usa coringa `.`, casando `á`, `\ufffd`, etc. | **CORRETO** |
| `RE_INC` (l. 81) | `r"^([IVXLCDM]+(?:-[A-Z])?)\s*[-–—\ufffd]\s*(.*)$"` | Já possui `\ufffd` explicitado no separador | **CORRETO** |
| `RE_ALI` (l. 82) | `r"^([a-z])\)\s*(.*)$"` | Não aplicável (letras minúsculas ASCII) | **CORRETO** |
| `RE_HEAD` (l. 83-87) | `r"^(?i:(LIVRO|SUBT.TULO|...))\s+..."` | Usa coringas `.` (`SUBT.TULO`, `.NICO`) | **CORRETO** |
| `RE_FIM` (l. 88) | `r"^Bras.lia,"` | Usa coringa `.` (`Bras.lia`) | **CORRETO** |
| `RE_NOTA` (l. 91-94) | `r"\(\s*(?:Reda|Inclu|Revogad|...)[^()]*\)"` | Prefixos sem caracteres acentuados | **CORRETO** |
| `FFFD` (l. 47) | `FFFD = "\ufffd"` | Sequência de escape correta | **CORRETO** |
| `html.count(FFFD)` (l. 550) | `n_fffd = html.count(FFFD)` | Usa a constante `FFFD` | **CORRETO** |

**Conclusão da Varredura**: Não existem outros locais corrompidos ou omissos no código do parser. Os únicos dois pontos com defeito são estritamente as **linhas 75 e 79**.

---

## 4. Matriz Comparativa de Casos de Teste (Stress Testing)

A tabela abaixo compara o comportamento das regexes antes e depois da correção cirúrgica recomendada:

| Cenário de Teste | Texto de Entrada | Comportamento Atual (Com Bug) | Comportamento com a Correção Recomendada | Status Atual |
|---|---|---|---|---|
| **1. Parágrafo Padrão com `§`** | `"§ 1º O casamento é civil..."` | Casa: num=`"1"`, corpo=`"O casamento é civil..."` | Casa: num=`"1"`, corpo=`"O casamento é civil..."` | PASS |
| **2. Parágrafo com `o` sobrescrito** | `"§ 1 o O casamento é civil..."` | Casa: num=`"1"`, corpo=`"O casamento é civil..."` | Casa: num=`"1"`, corpo=`"O casamento é civil..."` | PASS |
| **3. Parágrafo Mojibake com `\ufffd`** | `"\ufffd 1º O casamento é civil..."` | **NÃO casa** (falha em `{NUM}` por causa do `|)` vazio) | **Casa**: num=`"1"`, corpo=`"O casamento é civil..."` | **FAIL -> PASS** |
| **4. Parágrafo com Ordinal Danificado** | `"§ 1\ufffd O casamento é civil..."` | Casa, mas corpo vira `"\ufffd O casamento é civil..."` | **Casa**: num=`"1"`, corpo limpo `"O casamento é civil..."` | **FAIL -> PASS** |
| **5. Parágrafo Totalmente Danificado** | `"\ufffd 1\ufffd O casamento é civil..."` | **NÃO casa** | **Casa**: num=`"1"`, corpo limpo `"O casamento é civil..."` | **FAIL -> PASS** |
| **6. Enumeração Numérica Comum** | `"1. São direitos da personalidade..."` | **FALSO POSITIVO**: Cria um `§ 1º` indevido | **Rejeita**: Cai no tratamento de texto da linha 283 | **FAIL -> PASS** |
| **7. Ano / Disposição Numérica** | `"2002. Disposições transitórias..."` | **FALSO POSITIVO**: Cria um `§ 2002` indevido | **Rejeita**: Permanece texto explicativo | **FAIL -> PASS** |
| **8. Artigo com Ordinal Danificado** | `"Art. 1\ufffd Toda pessoa é capaz..."` | Casa, mas corpo vira `"\ufffd Toda pessoa é capaz..."` | **Casa**: num=`"1"`, corpo limpo `"Toda pessoa é capaz..."` | **FAIL -> PASS** |

---

## 5. Recomendação Técnica Cirúrgica para o Worker

O Worker da Rodada 2 do Milestone 3 deverá executar duas ações atômicas e seguras:

### Ação 1: Ajuste Cirúrgico em `src/scraper/ingestao_lei.py`

Substituir as linhas 75 e 79 no arquivo `e:\Programacao\JudAI\src\scraper\ingestao_lei.py`:

```python
<<<<<<< BEFORE (Linhas 75 e 79 atuais)
ORD = r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito
...
RE_PAR = re.compile(rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
=======
>>>>>>> AFTER (Linhas 75 e 79 corrigidas)
ORD = r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito
...
RE_PAR = re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
>>>>>>>
```

*Nota sobre a sintaxe*: O uso da sequência de escape `\ufffd` em `r"..."` e `rf"..."` é interpretado nativamente pelo compilador de expressões regulares do Python (`re.compile`) como o caractere Unicode `U+FFFD`. Isso evita bytes literais binários no arquivo fonte `.py`, garantindo portabilidade em Windows e Linux (conforme `.gitattributes: * text=auto eol=lf`).

---

### Ação 2: Remoção dos Scripts Legados na Raiz

Para cumprir `ORIGINAL_REQUEST.md §R2` (*"Mover os scripts existentes e:\Programacao\JudAI\ingestao_lei.py e carregar_mongo.py para src/scraper/"*) e satisfazer a verificação `verify_root_file_removal` em `verify_m3.py`:

Remover os arquivos:
- `e:\Programacao\JudAI\ingestao_lei.py`
- `e:\Programacao\JudAI\carregar_mongo.py`

*Dica de execução sem risco de timeout de terminal interativo*:
O Worker pode efetuar a remoção via script Python direto ou via comando não-interativo seguro:
```powershell
python -c "import pathlib; [p.unlink() for p in (pathlib.Path('ingestao_lei.py'), pathlib.Path('carregar_mongo.py')) if p.exists()]"
```

---

## 6. Procedimento de Verificação Pós-Correção

O Worker e os auditores devem executar os seguintes passos para validação imediata:

1. **Validação do Regex em Linha de Comando (Zero Falsos Positivos e Tolerância a `\ufffd`)**:
   ```powershell
   python -c "from src.scraper.ingestao_lei import RE_PAR, ORD, RE_ART;\
   assert RE_PAR.match('1. Item numerado') is None, 'Regressão de alternância vazia persiste!';\
   assert RE_PAR.match('§ 1º Texto') is not None, 'Parágrafo regular falhou!';\
   assert RE_PAR.match('\ufffd 1º Texto') is not None, 'Parágrafo com \ufffd falhou!';\
   assert RE_PAR.match('§ 1\ufffd Texto') is not None, 'Ordinal com \ufffd falhou!';\
   m = RE_ART.match('Art. 1\ufffd Texto do artigo');\
   assert m and m.group(3) == 'Texto do artigo', 'Vazamento de \ufffd para o corpo do artigo!';\
   print('Todas as asserções de regex passaram com sucesso!')"
   ```

2. **Validação de Inexistência de Arquivos na Raiz**:
   ```powershell
   python -c "import pathlib;\
   assert not pathlib.Path('ingestao_lei.py').exists(), 'ingestao_lei.py ainda reside na raiz!';\
   assert not pathlib.Path('carregar_mongo.py').exists(), 'carregar_mongo.py ainda reside na raiz!';\
   print('Arquivos legados da raiz devidamente removidos!')"
   ```

3. **Execução do Validador Oficial do Milestone 3**:
   ```powershell
   python .agents/teamwork/spec_miner_m3_3/verify_m3.py --skip-pytest
   ```

4. **Execução dos Testes Pytest do Projeto**:
   ```powershell
   pytest tests/test_tier1_feature_coverage.py -k "Scraper or MLModel" -v
   ```
