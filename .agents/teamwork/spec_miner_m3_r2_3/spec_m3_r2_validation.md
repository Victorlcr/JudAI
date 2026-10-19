# Especificação Formal de Validação e Testes: Milestone 3 - Rodada 2

**Projeto**: JudAI - RAG Híbrido Jurídico  
**Marco**: Milestone 3 - Rodada 2 (Correção de `RE_PAR`, Tolerância a `\ufffd` e Remoção de Scripts Legados na Raiz)  
**Autor**: `spec_miner_m3_r2_3` (Specification Miner)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Data**: 2026-10-18T23:48:00Z  
**Status**: Especificação Concluída para Implementação e Verificação  

---

## 1. Visão Geral e Contexto da Rodada 2

Na Rodada 1 do Milestone 3, a migração dos scripts `ingestao_lei.py` e `carregar_mongo.py` para `src/scraper/` e a criação dos modelos placeholders em `src/models/` foram aprovadas quanto à arquitetura e integridade forense. No entanto, os relatórios de revisão (`reviewer_m3_1`) e auditoria (`auditor_m3_1`) identificaram dois problemas que motivaram a abertura da Rodada 2:

1. **Defeito Crítico de Regex em `RE_PAR` (`src/scraper/ingestao_lei.py`)**:
   - A substituição do caractere corrompido resultou na expressão `(?:§|)` na linha 79 e na remoção de `\ufffd` de `ORD` na linha 75.
   - O ramo vazio `|)` em `(?:§|)` casa com a string vazia no início da linha (`^`), provocando **falsos positivos massivos** onde qualquer linha que inicie com numerais (ex.: `"1. Princípio fundamental"`, datas `"2002. Disposição transitória"`, prazos `"10 dias"`) é incorretamente capturada como um dispositivo de parágrafo (`§ 1º`, `§ 2002º`), corrompendo a estrutura jurídica do banco de dados.
   - Simultaneamente, parágrafos reais danificados com o caractere de substituição `\ufffd` (ex.: `"\ufffd 1º Texto"`) deixaram de ser casados, quebrando a tolerância a mojibake documentada no parser original.
2. **Coexistência de Scripts Legados na Raiz do Repositório**:
   - Os arquivos `e:\Programacao\JudAI\ingestao_lei.py` e `e:\Programacao\JudAI\carregar_mongo.py` permaneceram na raiz do projeto, violando a diretriz mandatória de migração do `ORIGINAL_REQUEST.md §R2`.
   - O teste existente em `tests/test_tier1_feature_coverage.py:519` continha uma instrução `pass` condicional em vez de uma asserção estrita de ausência.

Esta especificação define com precisão matemática as regras de casamento, tabelas de features, casos de borda adversariais, asserções de teste estritas e o plano de verificação executável.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Scraper Regex | Rejeição de Numerais Isolados em `RE_PAR` | Linhas numéricas sem marcador de parágrafo NÃO devem casar com `RE_PAR` | `"1. Princípio fundamental"`, `"2. Item"`, `"10 dias..."`, `"2002. Disposições"` | `RE_PAR.match(line) is None` | Falha crítica se retornar `Match` e criar nó `paragrafo` | `reviewer_m3_1 Finding 1`, `ORIGINAL_REQUEST §R2` |
| 2 | Scraper Regex | Casamento de Parágrafos Danificados (`\ufffd`) | Linhas iniciadas por `\ufffd` representando `§` corrompido devem ser reconhecidas como parágrafos | `"\ufffd 1º Texto"`, `"\ufffd 2° Texto"`, `"\ufffd 10. Texto"` | `Match` com `group(1) == "1"`, rótulo formatado como `"§ 1º"` | Falha se retornar `None` e descartar parágrafo corrompido | `reviewer_m3_1 Finding 1`, `ingestao_lei.py:71-72` |
| 3 | Scraper Regex | Tolerância a `\ufffd` no Ordinal (`ORD`) | Indicadores ordinais corrompidos (`\ufffd` no lugar de `º` ou `°`) devem ser consumidos por `ORD` | `"\ufffd 1\ufffd Texto"`, `"§ 1\ufffd Texto"` | `Match` com número `"1"` e corpo `"Texto"` | Falha se `\ufffd` bloquear a captura de `{NUM}` ou do corpo | `reviewer_m3_1 Finding 1`, `ingestao_lei.py:75` |
| 4 | Scraper Regex | Preservação de 100% dos Parágrafos Normais (`§`) | Todos os formatos legais de parágrafo com `§` devem continuar casando perfeitamente | `"§ 1º Texto"`, `"§ 2°"`, `"§ 3ª"`, `"§ 4o"`, `"§ 5º-A"`, `"§ 10."`, `"§1º"` | `Match` com grupos válidos (`NUM`, `SUF`, texto) | Falha se qualquer formato padrão deixar de casar | `PROJECT.md §Feature 9`, suíte de testes existente |
| 5 | Scraper Parsing | Continuação Textual de Itens Numéricos | Linhas iniciadas por números dentro de um artigo devem permanecer como continuação do texto (caput) | Fragmento HTML com caput seguido de `1. Item A\n2. Item B` | Documento do artigo acumula o texto; zero nós de parágrafo criados para 1 e 2 | Falha se criar nós de parágrafo espúrios | Análise do bloco `parsear()` linhas 257-285 |
| 6 | Scraper Parsing | Extração Correta de Parágrafos Reais e Danificados em HTML | Parser deve extrair tanto `§ 1º` quanto `\ufffd 2º` como dispositivos de tipo `paragrafo` | Fragmento HTML contendo `§ 1º Normal` e `\ufffd 2º Danificado` | Lista com 2 dispositivos de tipo `paragrafo` com rótulos `"§ 1º"` e `"§ 2º"` | Falha se omitir o parágrafo danificado | `test_tier4_real_world.py:102-136` |
| 7 | Workspace Hygiene | Remoção Estrita de `ingestao_lei.py` da Raiz | `ingestao_lei.py` não pode existir no diretório raiz do projeto | `ROOT_DIR / "ingestao_lei.py"` | `exists() == False` | Falha se o arquivo legado persistir na raiz | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 9` |
| 8 | Workspace Hygiene | Remoção Estrita de `carregar_mongo.py` da Raiz | `carregar_mongo.py` não pode existir no diretório raiz do projeto | `ROOT_DIR / "carregar_mongo.py"` | `exists() == False` | Falha se o arquivo legado persistir na raiz | `ORIGINAL_REQUEST §R2`, `PROJECT.md §Feature 10` |
| 9 | Test Automation | Asserção Ativa em `test_scraper_no_scripts_left_in_root` | O teste unitário deve conter asserções `assert not path.exists()` sem corpo vazio `pass` | Execução do teste em `test_tier1_feature_coverage.py` | Teste executa asserções reais e passa | Falha se contiver `pass` ou se arquivos ainda existirem | `reviewer_m3_1 Finding 2`, `test_tier1_feature_coverage.py:519` |

---

## Edge Cases

| # | Feature | Input | Observed / Expected Behavior |
|---|---------|-------|------------------------------|
| 1 | RE_PAR Negative | `"1. Princípio fundamental"` | `RE_PAR.match(...) is None`. Linha tratada como texto/continuação, NÃO como parágrafo. |
| 2 | RE_PAR Negative | `"1 - Primeiro requisito"` | `RE_PAR.match(...) is None`. |
| 3 | RE_PAR Negative | `"10 dias a contar da citação"` | `RE_PAR.match(...) is None`. Evita que prazos processuais se transformem em parágrafos. |
| 4 | RE_PAR Negative | `"2002. Disposições transitórias"` | `RE_PAR.match(...) is None`. Evita falso positivo em anos ou referências numéricas longas. |
| 5 | RE_PAR Negative | `"100. Valor em reais"` | `RE_PAR.match(...) is None`. |
| 6 | RE_PAR Negative | `"10.406/2002"` | `RE_PAR.match(...) is None`. Evita falso positivo em número de lei. |
| 7 | RE_PAR Negative | `"Art. 1º Caput do artigo"` | `RE_PAR.match(...) is None`. Casado exclusivamente por `RE_ART`. |
| 8 | RE_PAR Negative | `"Parágrafo único. Disposição"` | `RE_PAR.match(...) is None`. Casado exclusivamente por `RE_PUN`. |
| 9 | RE_PAR Negative | `"I - Inciso primeiro"` | `RE_PAR.match(...) is None`. Casado exclusivamente por `RE_INC`. |
| 10 | RE_PAR Negative | `"a) Alínea textual"` | `RE_PAR.match(...) is None`. Casado exclusivamente por `RE_ALI`. |
| 11 | RE_PAR Negative | `""` (string vazia) | `RE_PAR.match(...) is None`. |
| 12 | RE_PAR Positive | `"§ 1º Texto padrão"` | Match com `group(1) == "1"`, `group(2) is None`, `group(3) == "Texto padrão"`. |
| 13 | RE_PAR Positive | `"§ 2° Texto com grau"` | Match com `group(1) == "2"`, `group(2) is None`, `group(3) == "Texto com grau"`. |
| 14 | RE_PAR Positive | `"§ 3ª Texto com ordinal feminino"` | Match com `group(1) == "3"`, `group(2) is None`, `group(3) == "Texto com ordinal feminino"`. |
| 15 | RE_PAR Positive | `"§ 4o Texto com o minúsculo"` | Match com `group(1) == "4"`, `group(2) is None`, `group(3) == "Texto com o minúsculo"`. |
| 16 | RE_PAR Positive | `"§ 5º-A Texto com sufixo alfabético"` | Match com `group(1) == "5"`, `group(2) == "A"`, `group(3) == "Texto com sufixo alfabético"`. |
| 17 | RE_PAR Positive | `"§ 10. Texto com ponto"` | Match com `group(1) == "10"`, `group(2) is None`, `group(3) == "Texto com ponto"`. |
| 18 | RE_PAR Positive | `"§1º Sem espaço após símbolo"` | Match com `group(1) == "1"`, `group(2) is None`, `group(3) == "Sem espaço após símbolo"`. |
| 19 | RE_PAR Positive | `"\ufffd 1º Texto com símbolo corrompido"` | Match com `group(1) == "1"`, `group(2) is None`, `group(3) == "Texto com símbolo corrompido"`. |
| 20 | RE_PAR Positive | `"\ufffd 1\ufffd Texto com ambos corrompidos"` | Match com `group(1) == "1"`, `group(2) is None`, `group(3) == "Texto com ambos corrompidos"`. |
| 21 | RE_PAR Positive | `"\ufffd 2° Texto corrompido com grau"` | Match com `group(1) == "2"`, `group(2) is None`, `group(3) == "Texto corrompido com grau"`. |
| 22 | RE_PAR Positive | `"\ufffd 5º-A Texto corrompido com sufixo"` | Match com `group(1) == "5"`, `group(2) == "A"`, `group(3) == "Texto corrompido com sufixo"`. |
| 23 | RE_PAR Positive | `"\ufffd1º Texto corrompido sem espaço"` | Match com `group(1) == "1"`, `group(2) is None`, `group(3) == "Texto corrompido sem espaço"`. |
| 24 | RE_PAR Negative | `"\ufffd Texto sem número"` | `RE_PAR.match(...) is None`. Corrompido sem numeral não casa. |
| 25 | Parser HTML | HTML com caput + itens numéricos 1 e 2 + `§ 1º` + `\ufffd 2º` | 1 artigo extraído com caput; exatamente 2 parágrafos extraídos (`§ 1º` e `§ 2º`). Itens numéricos não viram parágrafos. |

---

## 2. Análise Técnica e Especificação das Expressões Regulares

### 2.1. O Defeito do Ramo Vazio em `RE_PAR`

Em `src/scraper/ingestao_lei.py`:
```python
# LINHA 75 ATUAL:
ORD = r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito

# LINHA 79 ATUAL:
RE_PAR = re.compile(rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
```

No padrão regex `^(?:§|)`, a alternância possui dois ramos:
- Ramo 1: `§`
- Ramo 2: ` ` (vazio, string nula)

De acordo com o motor de expressões regulares do Python (módulo `re`):
1. O motor testa o Ramo 1 contra a primeira posição de uma string como `"1. Princípio fundamental"`. O primeiro caractere é `'1'`, logo o Ramo 1 não casa.
2. O motor testa o Ramo 2. Sendo a alternativa nula, ela **sempre tem sucesso** sem consumir nenhum caractere na posição 0 (`^`).
3. Em seguida, `\s*` consome 0 espaços em branco.
4. `({NUM})` testa `\d+` contra `'1'`, casando perfeitamente `'1'`.
5. `{ORD}` e `{SUF}` são grupos opcionais `(?:...)?`, casando a string vazia.
6. `\s*[.\-–—]*\s*` consome o ponto e o espaço `". "`.
7. `(.*)$` captura o restante `"Princípio fundamental"`.
8. **Resultado**: O regex casa com sucesso! `m_par` é verdadeiro e a linha se transforma no nó `§ 1º` no banco de dados.

Simultaneamente, ao testar uma string danificada como `"\ufffd 1º Texto"`:
1. Ramo 1 (`§`) falha (primeiro caractere é `\ufffd`).
2. Ramo 2 (vazio) tem sucesso na posição 0.
3. O próximo caractere a ser consumido é `\ufffd`.
4. `\s*` consome 0 espaços.
5. `({NUM})` requer dígitos (`\d`). Como o caractere corrente é `\ufffd`, a captura falha!
6. **Resultado**: O regex falha em casar um parágrafo que deveria ter sido recuperado.

### 2.2. A Correção Canônica

A correção consiste em restaurar o escape Unicode `\ufffd` em ambos os pontos:

```python
# LINHA 75 CORRIGIDA:
ORD = r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito, tolerante a \ufffd

# LINHA 79 CORRIGIDA:
RE_PAR = re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
```

**Propriedades Formais da Correção**:
1. `^(?:§|\ufffd)` exige obrigatoriamente que o primeiro caractere seja ou `§` (U+00A7) ou `\ufffd` (U+FFFD). Nenhuma string iniciando por dígito, letra ou espaço poderá casar.
2. `[º°ª\ufffd]+` em `ORD` permite que, se o caractere ordinal também tiver sido substituído por `\ufffd` (situação frequente em codificações duplamente corrompidas como `\ufffd 1\ufffd`), ele seja absorvido como indicador ordinal e não quebre a leitura do sufixo ou do corpo.
3. Compatibilidade total com `RE_ART`, que reutiliza `{ORD}` e se beneficia da mesma resiliência.

---

## 3. Matriz de Casos de Teste para o Worker

O agente implementador (Worker) deve certificar-se de que a suíte atenda a todos os seguintes testes unitários e de integração:

### 3.1. Testes Negativos de `RE_PAR`
Devem retornar `None`:
```python
negative_cases = [
    "1. Princípio fundamental",
    "1 - Primeiro requisito",
    "2. Erradicação da pobreza",
    "3. Garantia do desenvolvimento",
    "10 dias a contar da citação",
    "2002. Disposições transitórias",
    "100. Valor estipulado",
    "10.406/2002",
    "Art. 1º Caput",
    "I - Inciso",
    "a) Alínea",
    "Parágrafo único. Dispositivo único",
    "",
    "   ",
    "\ufffd Texto sem numeral",
    "Nota explicativa (Incluído pela Lei nº 10.000)",
]
for text in negative_cases:
    assert RE_PAR.match(text) is None, f"Falso positivo em RE_PAR: {text!r}"
```

### 3.2. Testes Positivos de `RE_PAR` para `§`
Devem casar e capturar os grupos corretos:
```python
standard_cases = [
    ("§ 1º Texto padrão", "1", None, "Texto padrão"),
    ("§ 2° Texto com grau", "2", None, "Texto com grau"),
    ("§ 3ª Texto ordinal feminino", "3", None, "Texto ordinal feminino"),
    ("§ 4o Texto com o minúsculo", "4", None, "Texto com o minúsculo"),
    ("§ 5º-A Texto com sufixo A", "5", "A", "Texto com sufixo A"),
    ("§ 10. Texto com ponto", "10", None, "Texto com ponto"),
    ("§ 100 - Texto com traço", "100", None, "Texto com traço"),
    ("§1º Sem espaço", "1", None, "Sem espaço"),
    ("§ 1.368-A Multipropriedade", "1.368", "A", "Multipropriedade"),
]
for text, exp_num, exp_suf, exp_corpo in standard_cases:
    m = RE_PAR.match(text)
    assert m is not None, f"Falha no casamento padrão: {text!r}"
    assert m.group(1) == exp_num, f"Número incorreto em {text!r}: {m.group(1)} != {exp_num}"
    assert m.group(2) == exp_suf, f"Sufixo incorreto em {text!r}: {m.group(2)} != {exp_suf}"
    assert m.group(3) == exp_corpo, f"Corpo incorreto em {text!r}: {m.group(3)} != {exp_corpo}"
```

### 3.3. Testes Positivos de `RE_PAR` para `\ufffd`
Devem casar dispositivos danificados:
```python
corrupted_cases = [
    ("\ufffd 1º Texto danificado", "1", None, "Texto danificado"),
    ("\ufffd 1\ufffd Texto duplamente danificado", "1", None, "Texto duplamente danificado"),
    ("\ufffd 2° Texto danificado com grau", "2", None, "Texto danificado com grau"),
    ("\ufffd 3ª Texto danificado feminino", "3", None, "Texto danificado feminino"),
    ("\ufffd 4o Texto danificado com o", "4", None, "Texto danificado com o"),
    ("\ufffd 5º-A Texto danificado com sufixo", "5", "A", "Texto danificado com sufixo"),
    ("\ufffd 10. Texto danificado dez", "10", None, "Texto danificado dez"),
    ("\ufffd1º Danificado colado", "1", None, "Danificado colado"),
]
for text, exp_num, exp_suf, exp_corpo in corrupted_cases:
    m = RE_PAR.match(text)
    assert m is not None, f"Falha no casamento corrompido: {text!r}"
    assert m.group(1) == exp_num, f"Número incorreto em {text!r}: {m.group(1)} != {exp_num}"
    assert m.group(2) == exp_suf, f"Sufixo incorreto em {text!r}: {m.group(2)} != {exp_suf}"
    assert m.group(3) == exp_corpo, f"Corpo incorreto em {text!r}: {m.group(3)} != {exp_corpo}"
```

### 3.4. Teste de Integração em HTML Real com Enumeração e Parágrafos
O parser completo (`extrair_dispositivos`) deve processar:
```html
<p id="art1">Art. 1º São princípios da organização:</p>
<p>1. Princípio da legalidade estrita;</p>
<p>2. Princípio da impessoalidade administrativa;</p>
<p>§ 1º O disposto neste artigo aplica-se a todos os entes.</p>
<p>\ufffd 2º A regulamentação caberá ao Poder Executivo.</p>
```

**Comportamento Esperado**:
- Exatamente **3 dispositivos** extraídos no total:
  1. `artigo` (número `"1"`, rótulo `"art. 1º"`): o caput inclui ou continua com os textos dos itens 1 e 2.
  2. `paragrafo` (número `"1"`, rótulo `"§ 1º"`, texto `"O disposto neste artigo aplica-se a todos os entes."`).
  3. `paragrafo` (número `"2"`, rótulo `"§ 2º"`, texto `"A regulamentação caberá ao Poder Executivo."`).
- **Nenhum** dispositivo de parágrafo pode ter número `"1"` com o texto `"Princípio da legalidade estrita;"`.
- O total de parágrafos extraídos deve ser estritamente igual a **2**.

---

## 4. Especificação de Limpeza e Validação de Arquivos na Raiz

### 4.1. Remoção Obrigatória dos Arquivos Legados
Os arquivos legados na raiz do projeto devem ser excluídos:
- `e:\Programacao\JudAI\ingestao_lei.py` -> DEVE SER REMOVIDO
- `e:\Programacao\JudAI\carregar_mongo.py` -> DEVE SER REMOVIDO

### 4.2. Atualização Estrita do Teste de Cobertura
Em `tests/test_tier1_feature_coverage.py`, o método `test_scraper_no_scripts_left_in_root` (linha 519) deve ser atualizado para validação estrita sem corpo vazio:

```python
    def test_scraper_no_scripts_left_in_root(self):
        """7.6 Verifica que os scripts ingestao_lei.py e carregar_mongo.py não permanecem na raiz após migração."""
        root_ingestao = ROOT_DIR / "ingestao_lei.py"
        root_carregar = ROOT_DIR / "carregar_mongo.py"
        assert not root_ingestao.exists(), f"Arquivo legado ingestao_lei.py ainda existe na raiz: {root_ingestao}"
        assert not root_carregar.exists(), f"Arquivo legado carregar_mongo.py ainda existe na raiz: {root_carregar}"
        assert (ROOT_DIR / "src" / "scraper" / "ingestao_lei.py").exists(), "src/scraper/ingestao_lei.py deve existir"
        assert (ROOT_DIR / "src" / "scraper" / "carregar_mongo.py").exists(), "src/scraper/carregar_mongo.py deve existir"
```

---

## 5. Script de Verificação Rápida: `verify_m3_r2.py`

Foi construído o script de verificação independente:
`e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\verify_m3_r2.py`

Este script valida:
1. **Verificação Léxica do Código-Fonte**: Inspeciona `src/scraper/ingestao_lei.py` e valida a presença de `\ufffd` em `ORD` e em `RE_PAR` (e a ausência do ramo vazio `(?:§|)`).
2. **Suíte Negativa de Regex**: Valida que nenhum numeral solto casa com `RE_PAR`.
3. **Suíte Positiva de Parágrafos Danificados**: Valida o casamento de parágrafos com `\ufffd`.
4. **Suíte Positiva de Parágrafos Normais**: Valida o casamento de parágrafos com `§`.
5. **Integração de Extração em HTML**: Valida que fragmento com lista numérica e parágrafos danificados gera contagem exata e nós íntegros.
6. **Remoção dos Arquivos da Raiz**: Assegura `assert not root_ingestao.exists()` e `assert not root_carregar.exists()`.
7. **Asserção Estrita no Teste Unitário**: Assegura que `test_tier1_feature_coverage.py` não contém o corpo vazio `pass` e valida ativamente os caminhos.

---

## 6. Checklist de Aceitação para o Milestone 3 - Rodada 2

- [ ] `ORD` em `src/scraper/ingestao_lei.py` definido como `r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"`.
- [ ] `RE_PAR` em `src/scraper/ingestao_lei.py` definido como `re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)`.
- [ ] `ROOT_DIR / "ingestao_lei.py"` removido da raiz.
- [ ] `ROOT_DIR / "carregar_mongo.py"` removido da raiz.
- [ ] `tests/test_tier1_feature_coverage.py` atualizado com asserções estritas de ausência na raiz.
- [ ] `tests/test_tier2_boundary_corner.py` enriquecido com os testes de `RE_PAR` (negativos e com `\ufffd`).
- [ ] Execução de `verify_m3_r2.py` com 100% de aprovação.
