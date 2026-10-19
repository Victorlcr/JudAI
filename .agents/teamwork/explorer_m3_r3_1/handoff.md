# Relatório de Handoff — Milestone 3 (Rodada 3)

**Agente**: `explorer_m3_r3_1` (Read-Only Explorer)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Diretório de Trabalho**: `e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1`  
**Tipo de Handoff**: Hard Handoff  
**Artefato Principal Gerado**: `e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1\report_m3_r3_main_func.md`

---

## 1. Observation

### 1.1. Arquivo `src/scraper/carregar_mongo.py`
- **Linhas 48 a 104**: Funções declaradas no módulo:
  - Linha 48: `def conectar():`
  - Linha 63: `def carregar_documentos(fonte: str):`
  - Linha 79: `def inserir(db, colecoes: dict):`
  - Linha 96: `def verificar(db):`
- **Linhas 105 a 116**: Ponto de entrada CLI atual:
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
- **Constatação**: Nenhuma função `def main` existe no arquivo. O código CLI é executado proceduralmente apenas sob o bloco `if __name__ == "__main__":`.

### 1.2. Padrão Canônico em `src/scraper/ingestao_lei.py`
- **Linhas 535 a 547**:
  ```python
  def main(argv=None):
      ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
      ap.add_argument("entrada", help="caminho do .html OU URL da página no Planalto")
      ...
      args = ap.parse_args(argv)
  ```
- **Linhas 583 a 584**:
  ```python
  if __name__ == "__main__":
      main()
  ```
- **Constatação**: O ponto de entrada CLI recebe `argv=None` por padrão e delega a resolução para `ap.parse_args(argv)`.

### 1.3. Arquivo de Shim `carregar_mongo.py` (Raiz do Projeto)
- **Linhas 16 a 20**:
  ```python
  if __name__ == "__main__":
      import sys
      from src.scraper.carregar_mongo import main
      main()
  ```
- **Constatação**: O shim tenta importar incondicionalmente `main` de `src.scraper.carregar_mongo`.

### 1.4. Relatórios de Falha da Rodada 2
- `reviewer_m3_r2_1/handoff.md`: Linha 120: `ImportError: cannot import name 'main' from 'src.scraper.carregar_mongo'` ao invocar `python carregar_mongo.py`.
- `challenger_m3_r2_2/handoff.md`: Linha 43: Confirma ausência de `def main` e constata também a inércia de CLI no shim `ingestao_lei.py` da raiz.

---

## 2. Logic Chain

1. **Da Obs 1.1 e 1.3**: O shim da raiz tenta importar `from src.scraper.carregar_mongo import main`, mas `src/scraper/carregar_mongo.py` não define `def main`. Logo, invocar `python carregar_mongo.py` resulta fatalmente em `ImportError`.
2. **Da Obs 1.1**: Como o bloco CLI de `carregar_mongo.py` é código solto procedural sob `if __name__ == "__main__":`, nenhuma rotina externa consegue invocar ou inspecionar o fluxo de linha de comando sem executar o script como subprocesso completo.
3. **Da Obs 1.2**: `src/scraper/ingestao_lei.py:535` utiliza o padrão canônico do projeto com `def main(argv=None):` e `argparse.ArgumentParser.parse_args(argv)`. Esse padrão trata nativamente `-h` e `--help` (saindo com código 0 e texto descritivo), suporta argumentos posicionais opcionais (`nargs="?"`), e permite passagem determinística de argumentos tanto via terminal quanto por testes unitários e shims.
4. **Da análise de compatibilidade**: Encapsular a lógica de `carregar_mongo.py` em `def main(argv=None):` usando `argparse` com argumento opcional `fonte` (default: `FONTE_PADRAO`):
   - Não altera os literais `MONGO_URI` e `MONGO_DB_NAME` (preservando testes de cobertura de variáveis de ambiente em `test_tier1_feature_coverage.py` e `test_tier3_cross_feature.py`).
   - Mantém o comportamento de `--help` testado em `test_tier4_real_world.py:144` (`[sys.executable, "-m", "src.scraper.carregar_mongo", "--help"]`).
   - Fornece imediatamente o símbolo `main` para `carregar_mongo.py` na raiz, eliminando o `ImportError` e fazendo `hasattr(carregar_mongo, 'main')` retornar `True`.
5. **Conclusão Lógica**: A refatoração proposta em `report_m3_r3_main_func.md` resolve a causa raiz de todas as falhas reportadas na Rodada 2 sem risco de quebra colateral.

---

## 3. Caveats

- **Ambiente Read-Only**: Como agente Explorer, nenhuma modificação foi aplicada diretamente nos arquivos do projeto (`src/scraper/carregar_mongo.py` ou shims). A implementação física deverá ser executada pelo Worker designado da Rodada 3 com base no relatório técnico.
- **MongoDB Offline**: Em invocações sem `--help` onde MongoDB não esteja em execução, `conectar()` aciona `ServerSelectionTimeoutError` e encerra o processo via `sys.exit(...)`. Isso é o comportamento original planejado e esperado pelo sistema JudAI.

---

## 4. Conclusion

A análise detalhada e a especificação técnica para a implementação de `def main(argv=None):` em `src/scraper/carregar_mongo.py` foram concluídas com sucesso e registradas na íntegra no relatório:
`e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1\report_m3_r3_main_func.md`

A proposta fornece:
1. Diagnóstico completo da causa do erro.
2. Assinatura e especificação funcional idêntica e compatível com `src/scraper/ingestao_lei.py:535`.
3. Tratamento robusto de `-h`/`--help` e argumento opcional `fonte` com fallback para `FONTE_PADRAO`.
4. Trecho exato de código (diff e arquivo completo).
5. Recomendações preventivas de split-brain para os shims da raiz.
6. Guia de verificação independente para os avaliadores.

---

## 5. Verification Method

Para verificar independentemente a proposta técnica:

1. **Inspeção do Relatório Técnico**:
   - Abrir `e:\Programacao\JudAI\.agents\teamwork\explorer_m3_r3_1\report_m3_r3_main_func.md` e verificar as Seções 3 e 4.
2. **Inspeção Estática dos Arquivos de Código**:
   - Verificar ausência de `main` em `src/scraper/carregar_mongo.py:105-116`.
   - Verificar estrutura de `src/scraper/ingestao_lei.py:535-585`.
   - Verificar tentativa de import de `main` em `carregar_mongo.py:18` (raiz).
3. **Critério de Invalidação**:
   - Se a nova assinatura de `def main(argv=None):` falhar ao processar `python -m src.scraper.carregar_mongo --help` ou `python carregar_mongo.py --help` com código 0, a proposta estará invalidada.
