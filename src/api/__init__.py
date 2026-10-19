"""Módulo de API REST (FastAPI) e rotas de consulta do JudAI."""
from __future__ import annotations

from src.api.main import HealthResponse, QueryRequest, SearchResponse, app

__all__ = ["app", "QueryRequest", "SearchResponse", "HealthResponse"]
