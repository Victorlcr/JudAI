"""Módulo de coleta, raspagem e ingestão de normas jurídicas do JudAI."""
try:
    from src.scraper import ingestao_lei, carregar_mongo
except ImportError:
    from . import ingestao_lei, carregar_mongo

__all__ = ["ingestao_lei", "carregar_mongo"]
