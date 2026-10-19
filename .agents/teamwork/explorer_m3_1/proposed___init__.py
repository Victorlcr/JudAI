"""Módulo de coleta, raspagem e ingestão de normas jurídicas do JudAI."""
from src.scraper import ingestao_lei
from src.scraper import carregar_mongo

__all__ = ["ingestao_lei", "carregar_mongo"]
