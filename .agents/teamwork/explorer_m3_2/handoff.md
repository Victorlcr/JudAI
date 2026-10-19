# Handoff Report - Explorer 2 (Milestone 3: ML Placeholders BM25 & BERT)

**Target Directory**: `e:\Programacao\JudAI\.agents\teamwork\explorer_m3_2`  
**Date**: 2026-10-18  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

1. **Requisitos de Negócio e Restrições**:
   - `e:\Programacao\JudAI\.agents\teamwork\ORIGINAL_REQUEST.md`, linhas 18 e 29:
     - Linha 18: `"bm25_search.py e bert_search.py: apenas placeholders com docstring."`
     - Linha 29: `"Nenhum código de ML além de placeholders; python -c \"import src.scraper.ingestao_lei\" funciona."`
     - Linha 5: `"NÃO implementar lógica de ML (BM25, BERT, T5)."`
     - Linha 26: `"Com dependências leves instaladas (fastapi, uvicorn, pydantic, pymongo, chromadb, python-dotenv, beautifulsoup4, lxml, requests), uvicorn src.api.main:app sobe..."`
   - `e:\Programacao\JudAI\.agents\teamwork\orchestrator_1\PROJECT.md`, linhas 72-74:
     - `"Localização: src/models/bm25_search.py e src/models/bert_search.py."`
     - `"Restrição: Zero código de ML ativo. Classes BM25Search e BERTSearch com métodos lançando NotImplementedError e docstrings detalhadas. Imports leves sem dependências pesadas em nível de módulo."`

2. **Estado Atual do Repositório**:
   - `find_by_name` em `e:\Programacao\JudAI\src\models` revelou apenas `__init__.py` e `__pycache__`. Os arquivos `bm25_search.py` e `bert_search.py` ainda não existem fisicamente em `src/models/`.

3. **Expectativas Assertivas na Suíte de Testes Existente**:
   - `tests/test_tier1_feature_coverage.py`:
     - Linhas 344-347: `import src.models.bm25_search as bm25_mod; assert hasattr(bm25_mod, "BM25Search"); instance = bm25_mod.BM25Search(); assert instance is not None`
     - Linhas 354-359: `assert "bm25" in full_doc; assert "placeholder" in full_doc or "não implementad" in full_doc or "not implemented" in full_doc`
     - Linhas 363-368: `bm25.fit([{"id": 1, "texto": "artigo 1"}])` e `bm25.search("prescrição", top_k=5)` devem disparar `pytest.raises(NotImplementedError)`.
     - Linhas 372-375: `import src.models.bert_search as bert_mod; assert hasattr(bert_mod, "BERTSearch"); instance = bert_mod.BERTSearch(); assert instance is not None`
     - Linhas 382-389: `assert "bert" in full_doc or "embedding" in full_doc or "semântic" in full_doc; assert "placeholder" in full_doc or "não implementad" in full_doc or "not implemented" in full_doc`
     - Linhas 393-398: `bert.encode(["texto de dispositivo legal"])` e `bert.search("reparação civil", top_k=5)` devem disparar `pytest.raises(NotImplementedError)`.
     - Linhas 400-407: `test_models_import_fast_without_heavy_ml`: Import de ambos os modelos deve demorar `< 1.0` segundo.
   - `tests/test_tier2_boundary_corner.py`:
     - Linhas 272-282: `BM25Search().search("", top_k=0)` e `BM25Search().fit([])` disparam `NotImplementedError`.
     - Linhas 286-296: `BERTSearch().search("", top_k=0)` e `BERTSearch().encode([])` disparam `NotImplementedError`.
     - Linhas 300-305: `bert = BERTSearch(model_name=custom_model); assert bert.model_name == custom_model; bert.search("relação de consumo", top_k=10)` dispara `NotImplementedError`.
   - `tests/test_tier3_cross_feature.py`:
     - Linhas 167-168: `inspect.signature(BM25Search.search)` deve conter parâmetro `"query"`.
     - Linhas 178-179: `inspect.signature(BERTSearch.search)` deve conter parâmetro `"query"`.

---

## 2. Logic Chain

1. **Premissa 1 (Restrição de Peso e Isolamento de ML)**: Com base na Observação 1 (ORIGINAL_REQUEST §R1/R2) e Observação 3 (`test_models_import_fast_without_heavy_ml`), o ambiente de CI e desenvolvimento base opera com dependências mínimas. A importação de pacotes como `torch`, `sentence_transformers` ou `transformers` acarretaria overhead inaceitável (> 1s) ou erros de `ModuleNotFoundError` em ambientes sem essas bibliotecas instaladas.
   - *Inferência*: Nenhuma biblioteca de terceiros (pesada) deve ser importada no topo de `src/models/bm25_search.py` e `src/models/bert_search.py`. Apenas módulos padrão (`typing`, `__future__`) devem ser utilizados.

2. **Premissa 2 (Assinaturas e Comportamento Operacional)**: Com base na Observação 3 (testes dos Tiers 1, 2 e 3):
   - `BM25Search` deve possuir `__init__(self, corpus: list[dict[str, Any]] | None = None)`, `fit(self, corpus: list[dict[str, Any]])` e `search(self, query: str, top_k: int = 10)`.
   - `BERTSearch` deve possuir `__init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2")`, armazenar `self.model_name = model_name`, e expor `encode(self, texts: list[str])` e `search(self, query: str, top_k: int = 10)`.
   - Todos os métodos de busca e processamento (`fit`, `search`, `encode`) devem invocar `raise NotImplementedError(...)`.

3. **Premissa 3 (Docstrings Arquiteturais e Papel no RAG Híbrido)**: Conforme Observação 1 e 3, as docstrings dos módulos e das classes devem documentar formalmente o papel da busca esparsa (BM25 com MongoDB) e densa (BERT com ChromaDB) e a futura fusão RRF (Reciprocal Rank Fusion), contendo expressamente as palavras-chave `"bm25"`, `"bert"`, `"embedding"`, `"semântic"` e `"placeholder"` (ou `"not implemented"`).

4. **Premissa 4 (Desacoplamento com a API)**: A API FastAPI mockada (`POST /search/bm25` e `POST /search/bert`) recebe o payload com `"query": str` e responde com `{detail: "not implemented"}`. O alinhamento com os métodos `search(query: str, ...)` garante compatibilidade direta para quando a lógica de ML for ativada nos marcos posteriores.

---

## 3. Caveats

- **Ambiente de Execução**: Não testamos o carregamento de tensores reais de modelos neurais em GPU nem modelos de linguagem grandes, uma vez que esta fase é estritamente de infraestrutura base sem bibliotecas pesadas.
- **Exportação em `src/models/__init__.py`**: Embora `src/models/__init__.py` possa opcionalmente expor `BM25Search` e `BERTSearch`, os testes atuais importam diretamente de `src.models.bm25_search` e `src.models.bert_search`. A exportação em `__init__.py` é segura desde que os módulos permaneçam leves.
- **Implementação do Código**: Como agente explorador, este handoff provê a especificação completa e os templates de código prontos para uso em `report_m3_models.md`. A criação dos arquivos no diretório `src/models/` deve ser executada pelo agente implementador.

---

## 4. Conclusion

A análise dos requisitos e testes do JudAI estabeleceu a especificação exata e definitiva para os arquivos `src/models/bm25_search.py` e `src/models/bert_search.py`.
O relatório técnico completo com as propostas de código na íntegra, justificativas arquiteturais e mapeamento contra os Tiers 1-3 foi salvo em:
`e:\Programacao\JudAI\.agents\teamwork\explorer_m3_2\report_m3_models.md`

O agente implementador pode copiar fielmente as classes especificadas nas seções 4.3 e 5.3 do relatório técnico, garantindo 100% de aprovação nos testes automatizados e total conformidade arquitetural.

---

## 5. Verification Method

Para verificar a conformidade dos módulos assim que forem criados pelo agente implementador:

1. **Comandos de Teste Pytest**:
   ```powershell
   pytest tests/test_tier1_feature_coverage.py -k "BM25 or BERT or models" -v
   pytest tests/test_tier2_boundary_corner.py -k "ModelPlaceholders" -v
   pytest tests/test_tier3_cross_feature.py -k "FastApiAndModelIntegration" -v
   ```
2. **Inspeção de Latência de Import e Módulos Carregados**:
   ```powershell
   python -c "import time, sys; t0 = time.perf_counter(); import src.models.bm25_search, src.models.bert_search; t1 = time.perf_counter(); assert t1 - t0 < 1.0, 'Import lento!'; assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules; print(f'Módulos leves e rápidos: {t1-t0:.4f}s')"
   ```
3. **Condição de Invalidação**:
   - Falha se qualquer importação de `torch`, `transformers`, `sentence_transformers` ou `rank_bm25` ocorrer em nível de módulo.
   - Falha se `BM25Search().search("teste")` ou `BERTSearch().search("teste")` não lançar `NotImplementedError`.
   - Falha se a assinatura de `search` não contiver o argumento `query`.
