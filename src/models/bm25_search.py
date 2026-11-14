"""
Módulo de Busca Léxica / Clássica (BM25 / TFIDF-MLP Wrapper) - JudAI
====================================================================
Atua como DELEGADOR e WRAPPER retrocompatível para o motor de busca clássica.
Conforme arquitetura estabelecida em ORIGINAL_REQUEST e PROJECT.md, redireciona
as requisições de busca clássica para o classificador neural TF-IDF + MLP (TfidfMLPSearch).

Retrocompatibilidade:
- Preserva a assinatura BM25Search(corpus=...) e search(query, top_k=...).
- Suporta retorno tanto no formato padrão da API ({model, query, results, execution_time_ms})
  quanto formato em lista pura de dicionários para eventuais chamadas legadas.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from src.models.tfidf_mlp_search import TfidfMLPSearch, ModeloClassicoTFIDF


class BM25Search:
    """
    Wrapper e Delegador para busca clássica retrocompatível com a interface BM25.
    Delega a execução para TfidfMLPSearch garantindo reutilização de código e artefatos.
    """

    def __init__(
        self,
        corpus: Optional[list[dict[str, Any]]] = None,
        model_dir: Optional[Path | str] = None,
        auto_load: bool = True
    ) -> None:
        self.corpus: list[dict[str, Any]] = corpus or []
        self._delegate: TfidfMLPSearch = TfidfMLPSearch(model_dir=model_dir, auto_load=auto_load)

    @property
    def is_loaded(self) -> bool:
        return self._delegate.is_loaded

    @property
    def model(self) -> Optional[ModeloClassicoTFIDF]:
        return self._delegate.model

    def fit(
        self,
        corpus: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """
        Ajusta o modelo de busca clássica delegando para TfidfMLPSearch.fit().
        """
        if corpus is not None:
            self.corpus = corpus
        return self._delegate.fit(**kwargs)

    def load(self, save_dir: Optional[Path | str] = None) -> bool:
        """Carrega os artefatos treinados delegando para TfidfMLPSearch.load()."""
        return self._delegate.load(save_dir)

    def search(
        self,
        query: str,
        top_k: int = 3,
        return_dict: bool = True
    ) -> Union[dict[str, Any], list[dict[str, Any]]]:
        """
        Executa a busca clássica delegada.

        Args:
            query: Termo, citação ou consulta jurídica em linguagem natural.
            top_k: Quantidade máxima de resultados (default: 3).
            return_dict: Se True, retorna o dicionário completo do contrato da API com model='bm25';
                         se False, retorna apenas a lista de resultados compatível com a interface legada.
        """
        response = self._delegate.search(query=query, top_k=top_k)

        if return_dict:
            # Retorna o dicionário compatível com o endpoint POST /search/bm25
            return {
                "model": "bm25",
                "query": query,
                "results": response["results"],
                "execution_time_ms": response["execution_time_ms"]
            }

        return response["results"]


# Exporta TfidfMLPSearch no mesmo namespace para conveniência
__all__ = ["BM25Search", "TfidfMLPSearch", "ModeloClassicoTFIDF"]
