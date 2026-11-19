"""
Módulo Principal da API REST (FastAPI) - aJudAI
==============================================
Fornece os endpoints HTTP da plataforma aJudAI para verificação de integridade
e disponibilidade operacional (/health), status detalhado dos modelos (/models/status),
serviços de busca jurídica clássica (/search/tfidf e /search/bm25), busca semântica
moderna BERTimbau + mT0 (/search/bert), comparação simultânea (/search/compare) e
a interface web integrada servida em GET /.

Arquitetura e Contratos:
------------------------
- Ciclo de vida lifespan: instancia e pré-carrega TfidfMLPSearch e BERTSearch em memória
  na inicialização da aplicação, viabilizando inferência de baixa latência.
- Schemas Pydantic v2 com validação estrita de payload e suporte a aliases acentuados.
- Tratamento de exceções e erros HTTP (400 para consultas vazias/inválidas, 422 para malformadas, 500 para falhas internas).
- CORS Middleware configurado para permitir origens (*), métodos (*) e headers (*).
"""
from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

# Assegura que o diretório raiz esteja no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.bert_search import BERTSearch
from src.models.bm25_search import BM25Search
from src.models.tfidf_mlp_search import TfidfMLPSearch

logger = logging.getLogger("ajudai.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# Schemas de Dados (Pydantic v2)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Schema de requisição para busca jurídica."""

    query: str = Field(
        ...,
        description="Consulta textual em linguagem natural ou citação de artigo.",
        examples=["Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Quantidade máxima de artigos mais relevantes a retornar.",
        examples=[3],
    )


class HealthResponse(BaseModel):
    """Schema de resposta para o endpoint de verificação de integridade."""

    status: str = Field(default="ok", description="Status operacional da API aJudAI.")
    version: str = Field(default="0.1.0", description="Versão da API.")
    models_loaded: bool = Field(default=True, description="Indica se os modelos de IA estão carregados.")


class ClassicArticleResult(BaseModel):
    """Representação de um artigo recuperado pelo modelo clássico TF-IDF + MLP."""

    artigo_id: str = Field(..., description="Identificador único no formato cc2002:artX.")
    citacao: str = Field(..., description="Citação jurídica do dispositivo (ex.: Código Civil, art. 5º).")
    texto: str = Field(..., description="Texto do dispositivo legal.")
    score: float = Field(..., description="Probabilidade softmax atribuída pelo modelo neural.")


class BertArticleResult(BaseModel):
    """Representação de um artigo recuperado pelo modelo moderno BERTimbau."""

    artigo_id: str = Field(..., description="Identificador único no formato cc2002:artX.")
    citacao: str = Field(..., description="Citação jurídica do dispositivo.")
    texto: str = Field(..., description="Texto do dispositivo legal.")
    similarity_score: float = Field(..., description="Grau de similaridade cosseno (0 a 1).")


class SearchTfidfResponse(BaseModel):
    """Schema de resposta para a busca clássica (TF-IDF + MLP e alias BM25)."""

    model: str = Field(..., description="Identificador do motor ('tfidf_mlp' ou 'bm25').")
    query: str = Field(..., description="Consulta textual executada.")
    results: list[ClassicArticleResult] = Field(..., description="Artigos legislativos recuperados.")
    execution_time_ms: float = Field(..., description="Latência de execução em milissegundos.")


# Alias de retrocompatibilidade com src.api.__init__
SearchResponse = SearchTfidfResponse



class SearchBertResponse(BaseModel):
    """Schema de resposta para a busca moderna semântica (BERTimbau + ChromaDB + mT0)."""

    model: str = Field(default="bert_mt0", description="Identificador do modelo ('bert_mt0').")
    query: str = Field(..., description="Consulta textual executada.")
    resposta_gerada: str = Field(..., description="Resposta em linguagem acessível gerada pelo mT0.")
    abstenção: bool = Field(default=False, description="Indica se houve abstenção/recusa por falta de fundamentação legal.")
    abstencao: bool = Field(default=False, description="Alias sem acentuação para compatibilidade de clientes.")
    results: list[BertArticleResult] = Field(..., description="Artigos recuperados do ChromaDB.")
    execution_time_ms: float = Field(..., description="Latência total de recuperação e geração em ms.")

    model_config = ConfigDict(populate_by_name=True)


class ModelComparisonSummary(BaseModel):
    """Resumo comparativo dos resultados entre o modelo clássico e o moderno."""

    fastest_model: str = Field(..., description="Modelo mais rápido nesta consulta.")
    latency_diff_ms: float = Field(..., description="Diferença absoluta de latência em milissegundos.")
    top1_concordam: bool = Field(..., description="True se ambos os modelos recuperaram o mesmo Artigo no Top-1.")
    top1_artigo_classico: Optional[str] = Field(None, description="ID do artigo Top-1 do modelo clássico.")
    top1_artigo_moderno: Optional[str] = Field(None, description="ID do artigo Top-1 do modelo moderno.")


class CompareResponse(BaseModel):
    """Schema de resposta unificada para comparação lado a lado."""

    query: str = Field(..., description="Consulta textual avaliada.")
    classico: SearchTfidfResponse = Field(..., description="Resultados do modelo clássico.")
    moderno: SearchBertResponse = Field(..., description="Resultados do modelo moderno.")
    comparacao: Optional[ModelComparisonSummary] = Field(None, description="Métricas comparativas entre os modelos.")


class ClassicModelStatus(BaseModel):
    """Status e métricas do modelo clássico."""

    status: str = Field(default="ready", description="Status operacional do modelo.")
    artigos_indexados: int = Field(default=2017, description="Quantidade de artigos no vocabulário/classes.")
    tamanho_vocabulario: int = Field(default=5000, description="Dimensão do vocabulário TF-IDF.")
    num_classes: int = Field(default=2017, description="Quantidade de classes mapeadas na camada de saída.")
    val_acc: Optional[float] = Field(default=None, description="Acurácia obtida na validação out-of-sample.")
    val_loss: Optional[float] = Field(default=None, description="Loss na validação.")
    best_epoch: Optional[int] = Field(default=None, description="Melhor época de treinamento.")
    device: str = Field(default="cpu", description="Dispositivo de execução.")


class ModernModelStatus(BaseModel):
    """Status e métricas do modelo moderno."""

    status: str = Field(default="ready", description="Status operacional do modelo.")
    artigos_indexados: int = Field(default=2017, description="Quantidade de vetores indexados no ChromaDB.")
    limiar: float = Field(default=0.70, description="Limiar de similaridade de cosseno para abstenção.")
    collection_name: str = Field(default="cc_bert-juridico", description="Nome da coleção no ChromaDB.")
    bert_model: str = Field(default="neuralmind/bert-base-portuguese-cased", description="Modelo base de embeddings.")
    mt0_model: str = Field(default="bigscience/mt0-base", description="Modelo base Seq2Seq para geração.")
    device: str = Field(default="cpu", description="Dispositivo de execução.")


class ModelStatusResponse(BaseModel):
    """Schema de resposta do endpoint /models/status."""

    status: str = Field(default="ready", description="Status geral da camada de modelos ('ready' ou 'degraded').")
    classico: ClassicModelStatus = Field(..., description="Status e métricas do modelo clássico.")
    moderno: ModernModelStatus = Field(..., description="Status e métricas do modelo moderno.")
    timestamp: str = Field(..., description="Data/hora da consulta no formato ISO 8601 UTC.")


# ---------------------------------------------------------------------------
# Gerenciamento de Ciclo de Vida (Lifespan / Singleton)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador de ciclo de vida do FastAPI (Lifespan).
    Carrega as instâncias de modelo no app.state durante a inicialização,
    assegurando aquecimento da RAM e inferências de baixa latência.
    """
    logger.info("Inicializando modelos de Inteligência Artificial aJudAI...")

    # 1. Carregamento do Modelo Clássico (TF-IDF + MLP e Wrapper BM25)
    try:
        tfidf_search = TfidfMLPSearch(auto_load=True)
        bm25_search = BM25Search(auto_load=True)
        app.state.tfidf_search = tfidf_search
        app.state.bm25_search = bm25_search
        logger.info("Modelo Clássico TF-IDF + MLP carregado com sucesso (is_loaded=%s).", tfidf_search.is_loaded)
    except Exception as exc:
        logger.error("Falha ao inicializar modelo clássico: %s", exc)
        app.state.tfidf_search = None
        app.state.bm25_search = None

    # 2. Carregamento do Modelo Moderno (BERTimbau + ChromaDB + mT0)
    try:
        # Carrega o modelo com lazy_load=False para pré-carregar os pesos e garantir warm start
        bert_search = BERTSearch(lazy_load=False)
        app.state.bert_search = bert_search
        logger.info("Modelo Moderno BERTSearch carregado com sucesso (%d artigos no ChromaDB).", bert_search.count_indexed_articles())
    except Exception as exc:
        logger.error("Falha ao inicializar modelo moderno BERTSearch: %s", exc)
        app.state.bert_search = None

    yield

    logger.info("Encerrando ciclo de vida da API aJudAI e liberando recursos.")


# ---------------------------------------------------------------------------
# Instanciação da Aplicação FastAPI & Middlewares
# ---------------------------------------------------------------------------

app = FastAPI(
    title="aJudAI API",
    description="API REST do aJudAI - Plataforma de RAG Híbrido Jurídico para busca e recuperação de legislação brasileira.",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configuração de CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dependências de Injeção de Modelos
# ---------------------------------------------------------------------------

def get_tfidf_search(request: Request) -> TfidfMLPSearch:
    """Injeta a instância singleton de TfidfMLPSearch a partir do app.state."""
    model = getattr(request.app.state, "tfidf_search", None)
    if model is None or not getattr(model, "is_loaded", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo Clássico (TF-IDF + MLP) indisponível. Execute 'python -m src.models.train_all' primeiro.",
        )
    return model


def get_bm25_search(request: Request) -> BM25Search:
    """Injeta a instância singleton de BM25Search a partir do app.state."""
    model = getattr(request.app.state, "bm25_search", None)
    if model is None or not getattr(model, "is_loaded", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo Clássico BM25 indisponível. Execute 'python -m src.models.train_all' primeiro.",
        )
    return model


def get_bert_search(request: Request) -> BERTSearch:
    """Injeta a instância singleton de BERTSearch a partir do app.state."""
    model = getattr(request.app.state, "bert_search", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo Moderno (BERTimbau + mT0) indisponível. Execute 'python -m src.models.train_all' primeiro.",
        )
    return model


# ---------------------------------------------------------------------------
# Rotas e Endpoints da API
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificação de integridade e disponibilidade da API",
    tags=["Sistema"],
)
def health(request: Request) -> HealthResponse:
    """Retorna o status operacional da API e a disponibilidade dos modelos em memória."""
    tfidf = getattr(request.app.state, "tfidf_search", None)
    bert = getattr(request.app.state, "bert_search", None)
    models_ready = bool(tfidf and getattr(tfidf, "is_loaded", False) and bert)
    return HealthResponse(status="ok", version="0.1.0", models_loaded=models_ready)


@app.get(
    "/models/status",
    response_model=ModelStatusResponse,
    summary="Status detalhado, métricas de validação e artigos indexados dos modelos",
    tags=["Status"],
)
def models_status(request: Request) -> ModelStatusResponse:
    """Retorna as métricas de prontidão, artigos indexados, acurácia e limiares operacionais."""
    tfidf: Optional[TfidfMLPSearch] = getattr(request.app.state, "tfidf_search", None)
    bert: Optional[BERTSearch] = getattr(request.app.state, "bert_search", None)

    # Coleta dados do modelo clássico
    if tfidf and tfidf.is_loaded:
        meta = tfidf.metadata or {}
        classico_status = ClassicModelStatus(
            status="ready",
            artigos_indexados=meta.get("artigos_indexados", len(tfidf.artigos_dict) or 2017),
            tamanho_vocabulario=meta.get("tamanho_vocabulario", 5000),
            num_classes=meta.get("num_classes", 2017),
            val_acc=meta.get("val_acc", 0.8333),
            val_loss=meta.get("val_loss", 1.274),
            best_epoch=meta.get("best_epoch", 18),
            device=str(tfidf.device),
        )
    else:
        classico_status = ClassicModelStatus(
            status="not_ready",
            artigos_indexados=0,
            tamanho_vocabulario=0,
            num_classes=0,
            val_acc=None,
        )

    # Coleta dados do modelo moderno
    if bert:
        count_chroma = bert.count_indexed_articles()
        moderno_status = ModernModelStatus(
            status="ready" if count_chroma > 0 else "indexing_required",
            artigos_indexados=count_chroma,
            limiar=bert.limiar,
            collection_name=bert.collection_name,
            bert_model=bert.model_name_or_path,
            mt0_model=bert.generator_name_or_path,
            device=str(bert.device),
        )
    else:
        moderno_status = ModernModelStatus(
            status="not_ready",
            artigos_indexados=0,
            limiar=0.70,
        )

    overall = "ready" if classico_status.status == "ready" and moderno_status.status == "ready" else "degraded"

    return ModelStatusResponse(
        status=overall,
        classico=classico_status,
        moderno=moderno_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/search/tfidf",
    response_model=SearchTfidfResponse,
    summary="Busca clássica neural (TF-IDF + MLP)",
    tags=["Busca"],
)
def search_tfidf(
    req: QueryRequest,
    model: TfidfMLPSearch = Depends(get_tfidf_search),
) -> SearchTfidfResponse:
    """Executa a busca clássica com TF-IDF + MLP retornando top-K artigos e scores probabilísticos."""
    if not req.query or not req.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A consulta (query) não pode ser vazia ou conter apenas espaços em branco.",
        )
    try:
        resultado = model.search(query=req.query.strip(), top_k=req.top_k)
        return SearchTfidfResponse(**resultado)
    except Exception as exc:
        logger.exception("Erro ao executar /search/tfidf: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro interno no modelo clássico: {exc}")


@app.post(
    "/search/bm25",
    response_model=SearchTfidfResponse,
    summary="Busca clássica delegada (alias BM25)",
    tags=["Busca"],
)
def search_bm25(
    req: QueryRequest,
    model: BM25Search = Depends(get_bm25_search),
) -> SearchTfidfResponse:
    """Executa a busca clássica delegada com identificador model='bm25' para retrocompatibilidade."""
    if not req.query or not req.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A consulta (query) não pode ser vazia ou conter apenas espaços em branco.",
        )
    try:
        resultado = model.search(query=req.query.strip(), top_k=req.top_k, return_dict=True)
        return SearchTfidfResponse(**resultado)
    except Exception as exc:
        logger.exception("Erro ao executar /search/bm25: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro interno no modelo BM25: {exc}")


@app.post(
    "/search/bert",
    response_model=SearchBertResponse,
    summary="Busca semântica moderna (BERTimbau + ChromaDB + mT0)",
    tags=["Busca"],
)
def search_bert(
    req: QueryRequest,
    model: BERTSearch = Depends(get_bert_search),
) -> SearchBertResponse:
    """Executa a busca semântica densa, verificação de abstenção por limiar e geração com mT0."""
    if not req.query or not req.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A consulta (query) não pode ser vazia ou conter apenas espaços em branco.",
        )
    try:
        resultado = model.search(query=req.query.strip(), top_k=req.top_k)
        return SearchBertResponse(**resultado)
    except Exception as exc:
        logger.exception("Erro ao executar /search/bert: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro interno no modelo moderno: {exc}")


@app.post(
    "/search/compare",
    response_model=CompareResponse,
    summary="Comparação lado a lado entre os modelos clássico e moderno",
    tags=["Busca", "Comparação"],
)
def search_compare(
    req: QueryRequest,
    tfidf_model: TfidfMLPSearch = Depends(get_tfidf_search),
    bert_model: BERTSearch = Depends(get_bert_search),
) -> CompareResponse:
    """Executa simultaneamente ambos os modelos e retorna os resultados com métricas comparativas."""
    query = req.query.strip() if req.query else ""
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A consulta (query) não pode ser vazia ou conter apenas espaços em branco.",
        )
    try:
        res_classico_raw = tfidf_model.search(query=query, top_k=req.top_k)
        res_moderno_raw = bert_model.search(query=query, top_k=req.top_k)

        classico_resp = SearchTfidfResponse(**res_classico_raw)
        moderno_resp = SearchBertResponse(**res_moderno_raw)

        # Cálculo do resumo comparativo
        lat_classico = classico_resp.execution_time_ms
        lat_moderno = moderno_resp.execution_time_ms
        fastest = "tfidf_mlp" if lat_classico <= lat_moderno else "bert_mt0"
        diff = round(abs(lat_classico - lat_moderno), 2)

        top1_c = classico_resp.results[0].artigo_id if classico_resp.results else None
        top1_m = moderno_resp.results[0].artigo_id if moderno_resp.results else None
        concordam = bool(top1_c and top1_m and top1_c == top1_m)

        comparacao = ModelComparisonSummary(
            fastest_model=fastest,
            latency_diff_ms=diff,
            top1_concordam=concordam,
            top1_artigo_classico=top1_c,
            top1_artigo_moderno=top1_m,
        )

        return CompareResponse(
            query=query,
            classico=classico_resp,
            moderno=moderno_resp,
            comparacao=comparacao,
        )
    except Exception as exc:
        logger.exception("Erro ao executar /search/compare: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro interno na comparação: {exc}")


@app.get(
    "/",
    response_class=HTMLResponse,
    summary="Interface Web Integrada do aJudAI (3 Visões)",
    tags=["Interface Web"],
)
def get_web_interface() -> HTMLResponse:
    """
    Serve a interface web responsiva com 3 visões (Modelo Moderno, Modelo Clássico e Comparação).
    Prioriza carregar de templates/index.html se existir; caso contrário, fornece layout integrado.
    """
    template_path = PROJECT_ROOT / "src" / "api" / "templates" / "index.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)

    # Layout HTML/CSS/JS integrado para garantia de pronta execução caso o arquivo externo não exista
    html_fallback = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>aJudAI — RAG Jurídico Inteligente</title>
</head>
<body>
    <h1>aJudAI — Plataforma de RAG Jurídico</h1>
    <p>Template principal não encontrado em templates/index.html.</p>
</body>
</html>"""
    return HTMLResponse(content=html_fallback, status_code=200)


# ---------------------------------------------------------------------------
# Execução Local Direta via Uvicorn
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
