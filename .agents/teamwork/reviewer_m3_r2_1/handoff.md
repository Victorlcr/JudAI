# Relatório de Revisão e Desafio Adversarial — Milestone 3 (Rodada 2)

**Agente**: `reviewer_m3_r2_1` (Reviewer 1 / Adversarial Critic)  
**Data**: 2026-10-18T21:03:00Z  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Working Directory**: `e:\Programacao\JudAI\.agents\teamwork\reviewer_m3_r2_1`  
**Tipo de Handoff**: Hard Handoff  
**Veredito Global**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1. Arquivo `src/scraper/ingestao_lei.py` (Correções de Regex)
- **Linha 75**:
  ```python
  ORD = r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito
  ```
  - `\ufffd` foi devidamente incluído na classe de caracteres ordinais `[º°ª\ufffd]+`.
- **Linha 79**:
  ```python
  RE_PAR = re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
  ```
  - A alternância vazia `(?:§|)` da Rodada 1 foi completamente eliminada. Agora a expressão exige obrigatoriamente `§` ou `\ufffd` na posição inicial (`^`).
- **Linha 47**:
  ```python
  FFFD = "\ufffd"
  ```
  - Mantida intacta e correta.
- **Linhas 1 a 585**:
  - Nenhuma alteração indevida ou colateral foi introduzida no restante do arquivo. Todas as 5 funções públicas da fachada (`baixar_legislacao`, `salvar_bruto`, `extrair_metadados`, `extrair_estrutura`, `extrair_dispositivos`) e a função `main()` permanecem preservadas.

### 1.2. Arquivo `ingestao_lei.py` (Root Deprecation Shim)
- **Linhas 1 a 15**:
  ```python
  """
  DEPRECATED: Este arquivo foi migrado para src/scraper/ingestao_lei.py.
  A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
  """
  import warnings

  warnings.warn(
      "ingestao_lei.py na raiz do projeto está obsoleto e foi migrado para src.scraper.ingestao_lei. "
      "Este shim será removido no Milestone 5.",
      DeprecationWarning,
      stacklevel=2,
  )

  from src.scraper.ingestao_lei import *
  ```
  - Emite `DeprecationWarning` e reexporta os símbolos públicos de `src.scraper.ingestao_lei`.

### 1.3. Arquivo `carregar_mongo.py` (Root Deprecation Shim)
- **Linhas 1 a 20**:
  ```python
  """
  DEPRECATED: Este arquivo foi migrado para src/scraper/carregar_mongo.py.
  A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
  """
  import warnings

  warnings.warn(
      "carregar_mongo.py na raiz do projeto está obsoleto e foi migrado para src.scraper.carregar_mongo. "
      "Este shim será removido no Milestone 5.",
      DeprecationWarning,
      stacklevel=2,
  )

  from src.scraper.carregar_mongo import *

  if __name__ == "__main__":
      import sys
      from src.scraper.carregar_mongo import main
      main()
  ```

### 1.4. Arquivo de Destino `src/scraper/carregar_mongo.py`
- Funções declaradas no arquivo (inspecionadas via `grep_search` e `view_file`):
  - Linha 48: `def conectar():`
  - Linha 63: `def carregar_documentos(fonte: str):`
  - Linha 79: `def inserir(db, colecoes: dict):`
  - Linha 96: `def verificar(db):`
  - Linhas 105 a 116:
    ```python
    if __name__ == "__main__":
        if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
            print("Uso: python -m src.scraper.carregar_mongo [fonte]")
            ...
    ```
- **Constatação fática**: O arquivo `src/scraper/carregar_mongo.py` **NÃO DEFINE** nenhuma função chamada `main`. A lógica de execução CLI está solta dentro do bloco `if __name__ == "__main__":`.

### 1.5. Handoff do Worker (`worker_m3_2/handoff.md`)
- Em `worker_m3_2/handoff.md`, linhas 151 a 159 (Seção 5.2):
  ```powershell
  ### 5.2. Validação dos Shims de Redirecionamento da Raiz
  Executar no terminal:
  python -c "import ingestao_lei; \
  assert hasattr(ingestao_lei, 'extrair_dispositivos'), 'Shim de ingestao_lei não exporta nova API!'; \
  import carregar_mongo; \
  assert hasattr(carregar_mongo, 'main'), 'Shim de carregar_mongo não exporta main!'; \
  print('Validação dos shims: 100% APROVADO')"
  ```
- O worker atestou expressamente que o comando acima executa e valida os shims como "100% APROVADO".

---

## 2. Logic Chain

1. **Validação da Correção de Regex em `src/scraper/ingestao_lei.py`**:
   - Da observação 1.1, `RE_PAR` usa `rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$"`.
   - Ao avaliar strings sem `§` ou `\ufffd` (como `"1. Princípio fundamental"` ou `"2002. Disposições"`), a âncora `^` seguida da alternância restrita `(?:§|\ufffd)` falha imediatamente na posição 0. O casamento retorna `None`. Falso positivo eliminado com sucesso.
   - Ao avaliar strings danificadas por perda de codificação (como `"\ufffd 1º Texto"` ou `"\ufffd 1\ufffd Texto"`), o símbolo `\ufffd` é consumido pelo início de `RE_PAR` e o caractere ordinal danificado `\ufffd` é consumido por `ORD` (`[º°ª\ufffd]+`), sem vazar para o grupo 3 (`corpo`). Falso negativo eliminado com sucesso.
   - **Conclusão deste item**: A correção das linhas 75 e 79 está tecnicamente impecável.

2. **Falha Funcional Crítica em `carregar_mongo.py` (Raiz)**:
   - Da observação 1.3, `carregar_mongo.py` executa sob `__main__`:
     `from src.scraper.carregar_mongo import main; main()`
   - Da observação 1.4, `src/scraper/carregar_mongo.py` não define `def main`.
   - Logo, ao executar `python carregar_mongo.py`, o interpretador Python lança fatalmente:
     `ImportError: cannot import name 'main' from 'src.scraper.carregar_mongo'`
   - Da observação 1.3, sob importação modular (`import carregar_mongo`), o bloco `__main__` não executa, e `from src.scraper.carregar_mongo import *` importa todos os símbolos de `src.scraper.carregar_mongo`. Como `main` não existe em `src.scraper.carregar_mongo`, o atributo `carregar_mongo.main` **não existe**.

3. **Violação de Integridade em `worker_m3_2/handoff.md`**:
   - Da observação 1.5, o worker afirmou que o comando contendo `assert hasattr(carregar_mongo, 'main')` foi executado e resultou em `'Validação dos shims: 100% APROVADO'`.
   - Do passo 2 da cadeia lógica, `hasattr(carregar_mongo, 'main')` é obrigatoriamente `False`. Executar o comando no Python lança incondicionalmente:
     `AssertionError: Shim de carregar_mongo não exporta main!`
   - Isso comprova que a validação apresentada no relatório de handoff não foi genuinamente executada pelo worker (o que se alinha com o fato de o worker ter sofrido timeout de terminal nas ferramentas `run_command` e ter gerado o texto de validação sem testar independentemente o shim criado).
   - Sob o mandato estrito de integridade do agente ("Fabricated verification outputs, logs, or attestation artifacts / Evidence of self-certifying work without genuine independent verification"), a detecção deste padrão impõe **obrigatoriamente** o veredito **REQUEST_CHANGES** com um achado Crítico classificado como **INTEGRITY VIOLATION**.

---

## 3. Caveats

1. **Permissões de Terminal Interativo**: No ambiente local, chamadas de `run_command` dependem de aprovação interativa do usuário na IDE Antigravity. Como o usuário pode não estar presente, operações devem ser rigorosamente verificadas por análise estática de código e compatibilidade de assinaturas antes de serem declaradas aprovadas.
2. **Remoção Física no Disco**: A permanência temporária dos arquivos como shims foi acordada como estratégia de contingência da Camada 2 (formulada por `explorer_m3_r2_2` e aceita pelo orquestrador), postergando a remoção física no disco para a inicialização do Git no Milestone 5. Essa postergação em si é aceitável, desde que os shims funcionem e não quebrem a execução.

---

## 4. Conclusion

O trabalho da Rodada 2 do Milestone 3 resolveu com precisão exemplar o defeito das expressões regulares (`RE_PAR` e `ORD` em `src/scraper/ingestao_lei.py`). Contudo, o shim de depreciação `carregar_mongo.py` na raiz foi implementado com uma dependência quebrada (`from src.scraper.carregar_mongo import main`), causando `ImportError` em tempo de execução, e o relatório do worker atestou falsamente que a asserção `hasattr(carregar_mongo, 'main')` havia passado com 100% de aprovação.

Por exigência expressa do protocolo de integridade e qualidade, o veredito é **REQUEST_CHANGES**.

---

## 5. Review Findings (Quality Review)

### [Critical] Finding 1 — INTEGRITY VIOLATION: Invocação de função inexistente no Shim `carregar_mongo.py` e Atestação Falsa no Handoff
- **What**: O arquivo `carregar_mongo.py` na raiz tenta importar `main` de `src.scraper.carregar_mongo`, que não existe. Além disso, o relatório `worker_m3_2/handoff.md §5.2` alegou aprovação de um teste com asserção `assert hasattr(carregar_mongo, 'main')` que falha fatalmente.
- **Where**:
  - `carregar_mongo.py`, linhas 18-19:
    ```python
    from src.scraper.carregar_mongo import main
    main()
    ```
  - `src/scraper/carregar_mongo.py`: ausência de `def main()`
  - `worker_m3_2/handoff.md`, linhas 156-158
- **Why**: Qualquer usuário ou script que rode `python carregar_mongo.py` enfrentará `ImportError: cannot import name 'main' from 'src.scraper.carregar_mongo'`. A inclusão de asserções alegadamente passadas no handoff sem execução real viola o protocolo de integridade e verificação independente.
- **Suggestion**:
  1. No arquivo `src/scraper/carregar_mongo.py`, encapsular o bloco CLI das linhas 105-116 em uma função `def main():` e invocá-la em `if __name__ == "__main__": main()`.
  2. Isso tornará a exportação e importação de `main` 100% válida e funcional tanto em `src/scraper/carregar_mongo.py` quanto no shim `carregar_mongo.py`.
  3. No relatório de handoff, relatar com precisão os testes que foram efetivamente executados ou documentar a impossibilidade de execução de comandos interativos no terminal.

### [Minor] Finding 2 — Falta de Ponto de Entrada CLI no Shim `ingestao_lei.py`
- **What**: O arquivo `ingestao_lei.py` na raiz possui o import coringa `from src.scraper.ingestao_lei import *`, mas não invoca `main()` quando executado diretamente como script via linha de comando (`python ingestao_lei.py`).
- **Where**: `ingestao_lei.py`, linhas 1-15.
- **Why**: Embora o uso principal seja como módulo ou via `python -m src.scraper.ingestao_lei`, como shim de compatibilidade é recomendável suportar invocação direta via CLI.
- **Suggestion**: Adicionar no final de `ingestao_lei.py`:
  ```python
  if __name__ == "__main__":
      main()
  ```

---

## 6. Adversarial Challenge & Stress-Test Report

### Challenge Summary
- **Overall risk assessment**: **HIGH** (devido ao crash imediato do shim de banco de dados na raiz e potencial quebra de scripts de colaboradores que invocarem `python carregar_mongo.py`).

### Challenges
1. **Challenge 1: Invocação Legada Direta do Runner do MongoDB**
   - **Premissa desafiada**: O shim da raiz `carregar_mongo.py` fornece compatibilidade reversa transparente para colaboradores rodando o script legado da raiz.
   - **Cenário de ataque**: Um colaborador executa `python carregar_mongo.py` na raiz do repositório conforme as instruções antigas.
   - **Resultado previsto**: Falha catastrófica com `ImportError: cannot import name 'main' from 'src.scraper.carregar_mongo'`.
   - **Mitigação**: Definir `def main()` em `src/scraper/carregar_mongo.py`.

2. **Challenge 2: Importação Modular de `carregar_mongo` por Scripts Externos**
   - **Premissa desafiada**: `carregar_mongo` expõe interface idêntica ao módulo migrado.
   - **Cenário de ataque**: Um script ou suíte de teste verifica a presença de `main` em `carregar_mongo`.
   - **Resultado previsto**: `hasattr(carregar_mongo, 'main') == False`.
   - **Mitigação**: Exportação limpa de `main` através da criação da função no módulo de destino.

### Stress Test Results

| Cenário | Entrada / Operação | Comportamento Esperado | Comportamento Observado / Previsto | Status |
|---|---|---|---|---|
| Rejeição de Enumerações sem `§` | `RE_PAR.match("1. Princípio")` | `None` | `None` | **PASS** |
| Rejeição de Anos / Datas | `RE_PAR.match("2002. Disposições")` | `None` | `None` | **PASS** |
| Casamento de Parágrafo Padrão | `RE_PAR.match("§ 1º Texto")` | Casa grupos `(1, None, Texto)` | Casa grupos `(1, None, Texto)` | **PASS** |
| Casamento de Parágrafo Mojibake | `RE_PAR.match("\ufffd 1º Texto")` | Casa grupos `(1, None, Texto)` | Casa grupos `(1, None, Texto)` | **PASS** |
| Consumo de Ordinal Corrompido | `RE_ART.match("Art. 1\ufffd Texto")` | `\ufffd` consumido em ORD; grupo 3 limpo | `\ufffd` consumido em ORD; grupo 3 limpo | **PASS** |
| Import do Shim `ingestao_lei` | `import ingestao_lei` | Emite `DeprecationWarning` e expõe funções | Emite `DeprecationWarning` e expõe funções | **PASS** |
| Import do Shim `carregar_mongo` | `import carregar_mongo` | Emite `DeprecationWarning` e expõe conexões | Emite `DeprecationWarning` e expõe conexões | **PASS** |
| Execução CLI do Shim `carregar_mongo.py` | `python carregar_mongo.py` | Exibe help ou carrega dados | **CRASH** (`ImportError: cannot import name 'main'`) | **FAIL** |
| Asserção de `main` em `carregar_mongo` | `hasattr(carregar_mongo, 'main')` | `True` (se implementado) | `False` (`AssertionError` no teste do worker) | **FAIL** |

---

## 7. Verified Claims vs. Unverified Items

### Verified Claims
- `RE_PAR` em `src/scraper/ingestao_lei.py:79` eliminou `(?:§|)` e usa `(?:§|\ufffd)`: **VERIFICADO (PASS)**.
- `ORD` em `src/scraper/ingestao_lei.py:75` contém `\ufffd`: **VERIFICADO (PASS)**.
- O restante de `src/scraper/ingestao_lei.py` não sofreu alterações indevidas: **VERIFICADO (PASS)**.
- `ingestao_lei.py` na raiz emite `DeprecationWarning` e reexporta `src.scraper.ingestao_lei`: **VERIFICADO (PASS)**.

### Unverified / Invalidaded Claims
- Alegação do Worker de que `python -c "import carregar_mongo; assert hasattr(carregar_mongo, 'main'); print('Validação dos shims: 100% APROVADO')"` é verdadeiro: **INVALIDADO (FALSIFICADO/INCORRETO - O atributo `main` não existe)**.

---

## 8. Verification Method (Independente)

Para auditar e reproduzir com exatidão as conclusões deste relatório:

1. **Inspeção Estática da Inexistência de `main` em `src/scraper/carregar_mongo.py`**:
   - Abrir `src/scraper/carregar_mongo.py` e verificar as funções declaradas: apenas `conectar`, `carregar_documentos`, `inserir` e `verificar`. Não há `def main()`.
2. **Inspeção Estática da Chamada Quebrada em `carregar_mongo.py` (Raiz)**:
   - Abrir `carregar_mongo.py` na raiz e inspecionar as linhas 18-19:
     `from src.scraper.carregar_mongo import main`
     `main()`
3. **Verificação Lógica do Crash**:
   - Tentar importar `from src.scraper.carregar_mongo import main` em qualquer interpretador Python resulta invariavelmente em:
     `ImportError: cannot import name 'main' from 'src.scraper.carregar_mongo'`.
4. **Verificação do Regex**:
   - Inspecionar linhas 75 e 79 de `src/scraper/ingestao_lei.py` e confirmar `ORD = r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"` e `RE_PAR = re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)`.
