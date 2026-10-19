"""
Módulo Principal da API REST (FastAPI) - JudAI
==============================================
Fornece os endpoints HTTP da plataforma JudAI para verificação de integridade
e disponibilidade operacional (/health) e serviços de busca jurídica híbrida
(léxica BM25 em /search/bm25 e semântica densa BERT em /search/bert).

Contratos Arquiteturais:
- Título da API fixado em 'JudAI API' para documentação OpenAPI/Swagger UI.
- Documentação interativa Swagger em /docs e especificação em /openapi.json.
- Endpoints de busca retornam mocks estruturados {model, query, results: [], detail: "not implemented"}.
- Desacoplamento total de modelos de IA/ML nesta fase de infraestrutura base.
- Validação robusta de payload de entrada via Pydantic QueryRequest(query: str).
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Schemas de Dados (Pydantic)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """
    Schema de requisição para busca jurídica (léxica BM25 ou semântica BERT).

    Atributos:
        query: Consulta textual em linguagem natural, citação de artigo ou termo jurídico.
    """

    query: str = Field(
        ...,
        description="Termo, citação de artigo (ex.: 'Art. 186') ou consulta jurídica em linguagem natural.",
        examples=["prescrição reparação civil", "Art. 1.240 Usucapião Especial Urbana"],
    )


class HealthResponse(BaseModel):
    """Schema de resposta para o endpoint de verificação de integridade."""

    status: str = Field(
        default="ok",
        description="Status operacional da API JudAI.",
        examples=["ok"],
    )


class SearchResponse(BaseModel):
    """Schema de resposta estruturada para endpoints mockados de busca jurídica."""

    model: str = Field(
        ...,
        description="Identificador do mecanismo de recuperação ('bm25' ou 'bert').",
        examples=["bm25", "bert"],
    )
    query: str = Field(
        ...,
        description="A query textual exata fornecida na requisição.",
        examples=["Art. 1.240 Usucapião Especial Urbana"],
    )
    results: list[Any] = Field(
        default_factory=list,
        description="Lista de documentos legislativos recuperados (vazia na infraestrutura base).",
    )
    detail: str = Field(
        default="not implemented",
        description="Status indicativo de implementação da camada de modelos.",
        examples=["not implemented"],
    )


# ---------------------------------------------------------------------------
# Instanciação da Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="JudAI API",
    description="API REST do JudAI - Plataforma de RAG Híbrido Jurídico para busca e recuperação de legislação brasileira.",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Rotas e Endpoints da API
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificação de integridade e disponibilidade da API",
    tags=["Sistema"],
)
def health() -> dict[str, str]:
    """
    Retorna o status operacional da API.

    Returns:
        JSON com status 'ok' (HTTP 200).
    """
    return {"status": "ok"}


@app.post(
    "/search/bm25",
    response_model=SearchResponse,
    summary="Busca léxica esparsa (BM25) em legislação",
    tags=["Busca"],
)
def search_bm25(request: QueryRequest) -> dict[str, Any]:
    """
    Endpoint mockado para busca léxica via BM25 (palavras-chave e artigos específicos).

    Args:
        request: Payload contendo a consulta jurídica textual.

    Returns:
        Dicionário estruturado com modelo 'bm25', query recebida, lista vazia
        de resultados e detalhe 'not implemented'.
    """
    return {
        "model": "bm25",
        "query": request.query,
        "results": [],
        "detail": "not implemented",
    }


@app.post(
    "/search/bert",
    response_model=SearchResponse,
    summary="Busca semântica densa (BERT) em legislação",
    tags=["Busca"],
)
def search_bert(request: QueryRequest) -> dict[str, Any]:
    """
    Endpoint mockado para busca semântica via embeddings densos (BERT).

    Args:
        request: Payload contendo a consulta jurídica em linguagem natural.

    Returns:
        Dicionário estruturado com modelo 'bert', a query recebida, lista vazia
        de resultados e detalhe 'not implemented'.
    """
    return {
        "model": "bert",
        "query": request.query,
        "results": [],
        "detail": "not implemented",
    }


# ---------------------------------------------------------------------------
# Execução Local Direta via Uvicorn
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
