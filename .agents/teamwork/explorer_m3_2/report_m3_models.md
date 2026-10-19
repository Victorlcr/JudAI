# Relatório Técnico: Especificação Arquitetural de Placeholders de ML (BM25 e BERT)

**Projeto**: JudAI - RAG Híbrido Jurídico  
**Milestone**: M3 (Scraper e Placeholders ML)  
**Autor**: Explorer 2 (ML Placeholders: BM25 e BERT)  
**Data**: 2026-10-18  
**Status**: Concluído / Pronto para Implementação  
**Alvos**: `src/models/bm25_search.py` e `src/models/bert_search.py`  

---

## 1. Sumário Executivo

Este relatório apresenta a especificação técnica formal e a arquitetura dos módulos de busca léxica e semântica (`src/models/bm25_search.py` e `src/models/bert_search.py`) para a plataforma **JudAI**. 

Na presente fase (Milestone 3 - Infraestrutura Base), ambos os módulos atuam **estritamente como placeholders estruturais declarativos**. Conforme o plano arquitetural do projeto (`PROJECT.md`) e os requisitos mandatórios (`ORIGINAL_REQUEST.md`), estes arquivos devem estabelecer os contratos de interface e a fundamentação conceitual do RAG híbrido sem introduzir qualquer lógica ativa de Machine Learning nem carregar pesos ou bibliotecas pesadas (`torch`, `transformers`, `sentence-transformers`, `rank_bm25`) no nível de módulo.

---

## 2. Contexto Arquitetural: O RAG Híbrido Jurídico no JudAI

### 2.1. Desafios da Recuperação no Domínio Jurídico Brasileiro
A recuperação de legislação brasileira (ex.: Código Civil - Lei 10.406/2002) apresenta desafios singulares que tornam insuficiente o uso exclusivo de busca puramente léxica ou puramente vetorial:
1. **Estrutura Hierárquica e Articulação**: Leis são compostas por Livros, Títulos, Capítulos, Seções, Artigos, Parágrafos, Incisos e Alíneas. Consultas frequentemente mencionam números exatos ("art. 186", "artigo 927 do CC").
2. **Vocabulário Técnico e Termos em Latim**: Expressões como *"pacta sunt servanda"*, *"erga omnes"*, *"usucapião"*, *"evicção"* e *"vício redibitório"* requerem correspondência léxica exata e precisa.
3. **Descompasso de Vocabulário (Vocabulary Mismatch)**: Cidadãos e advogados frequentemente consultam a base com descrições fáticas em linguagem natural (ex.: *"comprei um carro que veio com defeito mecânico oculto"*), enquanto o texto legal expressa *"coisa recebida em virtude de contrato comutativo com vícios redibitórios"* (Art. 441).

### 2.2. Divisão de Papéis no Pipeline RAG Híbrido

```text
                                  +---------------------------------------+
                                  |         Consulta do Usuário           |
                                  | ("reparação por dano moral em vício") |
                                  +---------------------------------------+
                                                     |
                         +---------------------------+---------------------------+
                         |                                                       |
                         v                                                       v
        +-----------------------------------+                   +-----------------------------------+
        |       Busca Léxica (BM25)         |                   |     Busca Semântica (BERT)        |
        |      src/models/bm25_search       |                   |      src/models/bert_search       |
        +-----------------------------------+                   +-----------------------------------+
        | • Correspondência exata de termos |                   | • Embeddings densos multilinguais |
        | • BM25Okapi / BM25Plus            |                   | • Similaridade de cosseno         |
        | • Corpus MongoDB (leis indexadas) |                   | • Base vetorial ChromaDB          |
        | • Pontuação por frequência/TF-IDF |                   | • Compreensão contextual/fática   |
        +-----------------------------------+                   +-----------------------------------+
                         |                                                       |
                         | Top-K Candidatos Léxicos                              | Top-K Candidatos Semânticos
                         |                                                       |
                         +---------------------------+---------------------------+
                                                     |
                                                     v
                                  +---------------------------------------+
                                  |     Fusão e Reclassificação (RRF)     |
                                  |        (Reciprocal Rank Fusion)       |
                                  +---------------------------------------+
                                                     |
                                                     v
                                  +---------------------------------------+
                                  |      Contexto Enriquecido -> LLM      |
                                  | (Geração de resposta fundamentada)    |
                                  +---------------------------------------+
```

| Componente | Motor Planejado | Base de Dados Associada | Força Primária | Papel no JudAI |
|---|---|---|---|---|
| **BM25Search** (`bm25_search.py`) | `rank_bm25` (BM25Okapi / BM25Plus) | MongoDB (`MongoConnection`) | Alta precisão em números de artigos, termos técnicos e termos latinos | Recuperação esparsa preliminar de candidatos exatos |
| **BERTSearch** (`bert_search.py`) | `sentence-transformers` / BERTimbau | ChromaDB (`ChromaConnection`) | Captura de equivalência semântica e intenções contextuais | Recuperação densa de candidatos por similaridade conceitual |
| **Fusão (Futura)** | RRF (Reciprocal Rank Fusion) | Em memória / Pipeline RAG | Equilíbrio e desempate entre precisão léxica e recall semântico | Síntese do contexto final fornecido à LLM |

---

## 3. Diretrizes e Restrições Mandatórias da Infraestrutura Base

De acordo com `ORIGINAL_REQUEST.md` (§R1, §R2 e Critérios de Aceitação) e os testes automatizados já estabelecidos no repositório (`tests/test_tier1_feature_coverage.py`, `tests/test_tier2_boundary_corner.py`, `tests/test_tier3_cross_feature.py`), os módulos devem respeitar rigorosamente as seguintes restrições:

1. **Zero Lógica Ativa de ML**:
   - Nenhum modelo de rede neural, pipeline do Hugging Face, modelo spaCy ou cálculo matricial deve ser inicializado.
   - Nenhum download de pesos (`weights.bin`, `safetensors`) ou download de pacotes NLTK (`punkt`, `stopwords`) pode ocorrer durante a importação ou instanciação.
2. **Zero Imports Pesados em Nível de Módulo**:
   - É **estritamente proibido** importar `torch`, `transformers`, `sentence_transformers` ou `rank_bm25` no topo dos arquivos.
   - Os arquivos devem conter exclusivamente imports da biblioteca padrão do Python (`typing`, `__future__`).
   - Tempo de importação deve ser inferior a 1 segundo (`test_models_import_fast_without_heavy_ml`).
3. **Exceções Declarativas**:
   - Todos os métodos de execução e inferência (`fit`, `search`, `encode`) devem lançar `NotImplementedError` com mensagens claras indicando a pendência de implementação.
4. **Alinhamento de Contrato com a API**:
   - A assinatura do método `search(self, query: str, top_k: int = 10)` deve conter obrigatoriamente o parâmetro `query` para total interoperabilidade com o schema Pydantic `QueryRequest(query: str)` da API FastAPI (`src/api/main.py`).
5. **Docstrings Arquiteturais Obrigatórias**:
   - Devem conter as palavras-chave validadas pela suíte de testes:
     - `bm25_search.py`: Termos `"bm25"` e `"placeholder"` (ou `"não implementado"` / `"not implemented"`).
     - `bert_search.py`: Termos `"bert"`, `"embedding"` ou `"semântic"` e `"placeholder"` (ou `"não implementado"` / `"not implemented"`).

---

## 4. Especificação Técnica Detalhada de `src/models/bm25_search.py`

### 4.1. Responsabilidades
- Definir a classe `BM25Search`.
- Fornecer documentação de módulo e de classe detalhando o papel do algoritmo BM25 no RAG híbrido.
- Expor os métodos `__init__`, `fit` e `search`.

### 4.2. Assinaturas e Tipagem
```python
from __future__ import annotations
from typing import Any

class BM25Search:
    def __init__(self, corpus: list[dict[str, Any]] | None = None) -> None:
        ...

    def fit(self, corpus: list[dict[str, Any]]) -> None:
        ...

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        ...
```

### 4.3. Código Proposto para Implementação
```python
"""
Módulo de Busca Léxica Esparsa (BM25) - JudAI
==============================================
Este módulo é um PLACEHOLDER estrutural para o motor de busca léxica esparsa
baseado no algoritmo BM25 (Okapi / BM25Plus via biblioteca rank_bm25).

Papel no RAG Híbrido:
---------------------
Em marcos futuros, este componente será responsável por:
1. Tokenização de consultas e dispositivos legais com remoção de stopwords jurídicas.
2. Indexação esparsa de dispositivos extraídos da base MongoDB (artigos, parágrafos, incisos).
3. Recuperação preliminar dos top-K candidatos com base em correspondência exata
   e frequência de termos técnicos e números de artigos.
4. Integração na etapa de fusão de rankings (Reciprocal Rank Fusion - RRF)
   com a busca semântica densa (BERT).

ATENÇÃO: Nenhuma lógica de Machine Learning ou indexação ativa está implementada
nesta fase de infraestrutura base (placeholder estrutural / not implemented).
"""
from __future__ import annotations

from typing import Any


class BM25Search:
    """
    Placeholder estrutural para o motor de busca léxica BM25 no pipeline do JudAI.

    Esta classe define a interface pública para tokenização, indexação de corpus
    legislativo e busca por relevância textual. Na presente fase de infraestrutura base,
    todos os métodos lançam NotImplementedError para evitar dependências pesadas e
    inicializações desnecessárias.
    """

    def __init__(self, corpus: list[dict[str, Any]] | None = None) -> None:
        """
        Inicializa o placeholder do motor de busca BM25.

        Args:
            corpus: Lista opcional de dicionários representando dispositivos legais
                    a serem futuramente indexados.
        """
        self.corpus = corpus or []

    def fit(self, corpus: list[dict[str, Any]]) -> None:
        """
        Planejado: Processa e indexa o corpus de legislação.

        Em versões futuras, executará a tokenização e o cálculo de frequências de termos
        (TF-IDF/BM25) sobre os artigos legislativos.

        Args:
            corpus: Lista de dicionários representando documentos ou dispositivos.

        Raises:
            NotImplementedError: Funcionalidade reservada para os marcos de ML.
        """
        raise NotImplementedError("BM25 indexing is not yet implemented.")

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Planejado: Executa busca léxica com pontuação BM25 sobre o corpus indexado.

        Args:
            query: Termo, número de artigo ou expressão jurídica a pesquisar.
            top_k: Quantidade máxima de resultados relevantes a retornar (default: 10).

        Returns:
            Lista de dicionários com os dispositivos ordenados por pontuação BM25.

        Raises:
            NotImplementedError: Funcionalidade reservada para os marcos de ML.
        """
        raise NotImplementedError("BM25 search is not yet implemented.")
```

---

## 5. Especificação Técnica Detalhada de `src/models/bert_search.py`

### 5.1. Responsabilidades
- Definir a classe `BERTSearch`.
- Fornecer documentação de módulo e de classe detalhando a busca semântica densa baseada em embeddings neurais e a integração com o ChromaDB.
- Expor os métodos `__init__`, `encode` e `search`.
- Suportar configuração customizada de modelo através do atributo `model_name`.

### 5.2. Assinaturas e Tipagem
```python
from __future__ import annotations
from typing import Any

class BERTSearch:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        ...

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        ...
```

### 5.3. Código Proposto para Implementação
```python
"""
Módulo de Busca Semântica Densa (BERT / Embeddings) - JudAI
===========================================================
Este módulo é um PLACEHOLDER estrutural para o motor de busca semântica densa
baseado em embeddings de linguagem natural (ex.: Sentence-BERT ou modelos
jurídicos em língua portuguesa como BERTimbau / Juridical BERT).

Papel no RAG Híbrido:
---------------------
Em marcos futuros, este componente será responsável por:
1. Geração de representações vetoriais densas (embeddings) para consultas do usuário.
2. Consulta por similaridade de cosseno na coleção de vetores do ChromaDB local persistente.
3. Recuperação de dispositivos e artigos com equivalência semântica e contextual,
   mesmo quando os termos exatos diferem da redação legal formal.
4. Fornecimento de pontuações densas normalizadas para composição no ranking híbrido (RRF).

ATENÇÃO: Nenhuma lógica de Machine Learning ou modelo neural está carregado
nesta fase de infraestrutura base (placeholder estrutural / not implemented).
"""
from __future__ import annotations

from typing import Any


class BERTSearch:
    """
    Placeholder estrutural para o motor de busca semântica densa BERT no JudAI.

    Esta classe define a interface pública para vetorização de sentenças e busca
    por similaridade semântica no banco vetorial ChromaDB. Na presente fase de
    infraestrutura base, métodos operacionais lançam NotImplementedError para garantir
    inicialização instantânea sem necessidade de pesos de redes neurais ou aceleradores de hardware.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        """
        Inicializa o placeholder do motor de busca semântica BERT.

        Args:
            model_name: Identificador do modelo de embeddings a ser utilizado futuramente
                        (default: "sentence-transformers/all-MiniLM-L6-v2").
        """
        self.model_name: str = model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Planejado: Converte uma lista de textos em representações vetoriais densas (embeddings).

        Em versões futuras, utilizará PyTorch / Transformers / Sentence-Transformers
        para gerar tensores de dimensões compatíveis com o ChromaDB.

        Args:
            texts: Lista de sentenças ou artigos legislativos a vetorizar.

        Returns:
            Lista de vetores numéricos de ponto flutuante.

        Raises:
            NotImplementedError: Funcionalidade reservada para os marcos de ML.
        """
        raise NotImplementedError("BERT embedding generation is not yet implemented.")

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Planejado: Realiza busca por similaridade semântica de cosseno no ChromaDB.

        Args:
            query: Consulta conceitual em linguagem natural enviada pelo usuário.
            top_k: Quantidade máxima de resultados mais próximos a retornar (default: 10).

        Returns:
            Lista de dispositivos com scores de similaridade e metadados legais.

        Raises:
            NotImplementedError: Funcionalidade reservada para os marcos de ML.
        """
        raise NotImplementedError("BERT semantic search is not yet implemented.")
```

---

## 6. Mapeamento de Testes Unitários e Casos de Borda

Abaixo está o mapeamento detalhado dos testes existentes na base de código contra os requisitos dos placeholders:

| Arquivo de Teste | Método de Teste | O Que É Validado | Comportamento Requerido |
|---|---|---|---|
| `test_tier1_feature_coverage.py` | `test_bm25_search_module_and_class_exist` | Módulo `src.models.bm25_search` e classe `BM25Search` | Importável; instanciação sem argumentos bem-sucedida |
| `test_tier1_feature_coverage.py` | `test_bm25_search_docstrings_present` | Docstrings do módulo e da classe | Conter `"bm25"` e (`"placeholder"` ou `"não implementad"` ou `"not implemented"`) |
| `test_tier1_feature_coverage.py` | `test_bm25_search_methods_raise_not_implemented` | Métodos `fit` e `search` | Disparar `NotImplementedError` em chamadas normais |
| `test_tier1_feature_coverage.py` | `test_bert_search_module_and_class_exist` | Módulo `src.models.bert_search` e classe `BERTSearch` | Importável; instanciação sem argumentos bem-sucedida |
| `test_tier1_feature_coverage.py` | `test_bert_search_docstrings_present` | Docstrings do módulo e da classe | Conter (`"bert"` ou `"embedding"` ou `"semântic"`) e (`"placeholder"` ou `"não implementad"` ou `"not implemented"`) |
| `test_tier1_feature_coverage.py` | `test_bert_search_methods_raise_not_implemented` | Métodos `encode` e `search` | Disparar `NotImplementedError` em chamadas normais |
| `test_tier1_feature_coverage.py` | `test_models_import_fast_without_heavy_ml` | Tempo de importação de ambos os módulos | Tempo total de importação < 1.0 segundo (sem torch/transformers) |
| `test_tier2_boundary_corner.py` | `test_bm25_search_empty_query_raises_not_implemented` | `bm25.search("", top_k=0)` | Disparar `NotImplementedError` sem erro prévio de validação |
| `test_tier2_boundary_corner.py` | `test_bm25_fit_empty_corpus_raises_not_implemented` | `bm25.fit([])` | Disparar `NotImplementedError` sem erro prévio |
| `test_tier2_boundary_corner.py` | `test_bert_search_empty_query_raises_not_implemented` | `bert.search("", top_k=0)` | Disparar `NotImplementedError` sem erro prévio |
| `test_tier2_boundary_corner.py` | `test_bert_encode_empty_list_raises_not_implemented` | `bert.encode([])` | Disparar `NotImplementedError` sem erro prévio |
| `test_tier2_boundary_corner.py` | `test_bert_custom_model_name_raises_not_implemented` | Atributo `model_name` e busca | `bert.model_name == custom_model` e `search()` lança `NotImplementedError` |
| `test_tier3_cross_feature.py` | `test_api_bm25_contract_matches_model_signature` | Parâmetro do método de busca | `inspect.signature(BM25Search.search)` contém parâmetro `"query"` |
| `test_tier3_cross_feature.py` | `test_api_bert_contract_matches_model_signature` | Parâmetro do método de busca | `inspect.signature(BERTSearch.search)` contém parâmetro `"query"` |

---

## 7. Verificação Independente e Instruções de Teste

Para o agente implementador verificar a conformidade dos arquivos criados, os seguintes comandos devem ser executados a partir da raiz do repositório (`e:\Programacao\JudAI`):

1. **Validação de Imports Rápidos e Sintaxe**:
   ```bash
   python -c "import time; t0 = time.perf_counter(); import src.models.bm25_search as bm, src.models.bert_search as bt; t1 = time.perf_counter(); assert t1 - t0 < 1.0; print(f'Import OK: {t1-t0:.4f}s'); b1 = bm.BM25Search(); b2 = bt.BERTSearch(); assert b1 is not None and b2 is not None"
   ```

2. **Execução de Testes Específicos de Modelos**:
   ```bash
   pytest tests/test_tier1_feature_coverage.py -k "test_bm25 or test_bert or test_models" -v
   pytest tests/test_tier2_boundary_corner.py -k "TestBoundaryModelPlaceholdersInputs" -v
   pytest tests/test_tier3_cross_feature.py -k "TestFastApiAndModelIntegration" -v
   ```

3. **Verificação de Ausência de Módulos Pesados no Sys.modules**:
   ```bash
   python -c "import src.models.bm25_search, src.models.bert_search, sys; assert 'torch' not in sys.modules, 'torch foi carregado!'; assert 'transformers' not in sys.modules, 'transformers foi carregado!'; assert 'rank_bm25' not in sys.modules, 'rank_bm25 foi carregado!'; print('Auditoria de dependências limpa: zero módulos pesados carregados.')"
   ```

---

## 8. Conclusão

A especificação aqui apresentada atende com 100% de precisão aos requisitos do Milestone 3, respeitando o papel de esqueleto de infraestrutura rápida e leve do JudAI. As interfaces propostas garantem a transição futura suave para os marcos de implementação de ML sem retrabalho de rotas de API nem quebra de tipagens.
