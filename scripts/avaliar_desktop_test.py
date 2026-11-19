#!/usr/bin/env python3
"""
Avaliação Quantitativa Real nos datasets da pasta Desktop/test
(test_formal.jsonl, test_informal.jsonl, val_formal.jsonl, val_informal.jsonl).

Calcula Top-1, Top-3 e Top-5 reais para:
- Modelo Clássico: TF-IDF + MLP (src.models.tfidf_mlp_search.TfidfMLPSearch)
- Modelo Moderno: BERT-Jurídico + ChromaDB (data/models/bert_juridico + cc_bert-juridico)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tfidf_mlp_search import TfidfMLPSearch

PASTA_TEST = Path(r"C:\Users\victo\Desktop\test")
ARQUIVOS = [
    "test_formal.jsonl",
    "test_informal.jsonl",
    "val_formal.jsonl",
    "val_informal.jsonl",
]


def carregar_jsonl(caminho: Path) -> list[dict]:
    with open(caminho, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def avaliar_tfidf(modelo: TfidfMLPSearch, registros: list[dict]) -> dict:
    top1 = top3 = top5 = 0
    total = len(registros)
    t0 = time.perf_counter()

    for item in registros:
        esperado = item["artigo_id"]
        res = modelo.search(item["pergunta"], top_k=5)
        ids = [str(r.get("artigo_id", "")) for r in res.get("results", [])]

        if ids and ids[0] == esperado:
            top1 += 1
        if esperado in ids[:3]:
            top3 += 1
        if esperado in ids[:5]:
            top5 += 1

    tempo_s = time.perf_counter() - t0
    return {
        "total": total,
        "top1": round((top1 / total) * 100.0, 2) if total else 0.0,
        "top3": round((top3 / total) * 100.0, 2) if total else 0.0,
        "top5": round((top5 / total) * 100.0, 2) if total else 0.0,
        "acertos_top1": top1,
        "acertos_top3": top3,
        "acertos_top5": top5,
        "tempo_s": round(tempo_s, 2),
    }


def avaliar_bert(
    encoder: SentenceTransformer,
    colecao,
    registros: list[dict],
) -> dict:
    top1 = top3 = top5 = 0
    total = len(registros)
    t0 = time.perf_counter()

    perguntas = [r["pergunta"] for r in registros]
    embeddings = encoder.encode(
        perguntas,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=False,
    )

    # Consulta em lotes no ChromaDB para rapidez
    batch_size = 100
    for ini in range(0, total, batch_size):
        fim = min(ini + batch_size, total)
        emb_lote = embeddings[ini:fim].tolist()
        res = colecao.query(query_embeddings=emb_lote, n_results=5)
        for offset, retrieved_ids in enumerate(res["ids"]):
            esperado = registros[ini + offset]["artigo_id"]
            if retrieved_ids and retrieved_ids[0] == esperado:
                top1 += 1
            if esperado in retrieved_ids[:3]:
                top3 += 1
            if esperado in retrieved_ids[:5]:
                top5 += 1

    tempo_s = time.perf_counter() - t0
    return {
        "total": total,
        "top1": round((top1 / total) * 100.0, 2) if total else 0.0,
        "top3": round((top3 / total) * 100.0, 2) if total else 0.0,
        "top5": round((top5 / total) * 100.0, 2) if total else 0.0,
        "acertos_top1": top1,
        "acertos_top3": top3,
        "acertos_top5": top5,
        "tempo_s": round(tempo_s, 2),
    }


def main():
    print("[1/2] Carregando TF-IDF + MLP...", flush=True)
    tfidf = TfidfMLPSearch()
    tfidf.load()

    print("[2/2] Carregando BERT-Jurídico e ChromaDB...", flush=True)
    encoder = SentenceTransformer(str(PROJECT_ROOT / "data" / "models" / "bert_juridico"))
    client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "data" / "chromadb_local"))
    colecao = client.get_collection("cc_bert-juridico")

    resultados = {"por_arquivo": {}, "consolidado": {}}
    todos_test = []
    todos_val = []
    todos_geral = []

    for nome in ARQUIVOS:
        caminho = PASTA_TEST / nome
        dados = carregar_jsonl(caminho)
        if nome.startswith("test_"):
            todos_test.extend(dados)
        elif nome.startswith("val_"):
            todos_val.extend(dados)
        todos_geral.extend(dados)

        print(f"\nAvaliando {nome} ({len(dados)} perguntas)...", flush=True)
        r_tfidf = avaliar_tfidf(tfidf, dados)
        r_bert = avaliar_bert(encoder, colecao, dados)

        print(
            f"  TF-IDF+MLP   -> Top-1: {r_tfidf['top1']:6.2f}% | Top-3: {r_tfidf['top3']:6.2f}% | Top-5: {r_tfidf['top5']:6.2f}% ({r_tfidf['tempo_s']}s)",
            flush=True,
        )
        print(
            f"  BERT-Jurídico-> Top-1: {r_bert['top1']:6.2f}% | Top-3: {r_bert['top3']:6.2f}% | Top-5: {r_bert['top5']:6.2f}% ({r_bert['tempo_s']}s)",
            flush=True,
        )

        resultados["por_arquivo"][nome] = {
            "tfidf_mlp": r_tfidf,
            "bert_juridico": r_bert,
        }

    # Consolidados (Test, Val, Geral) somando os acertos exatos
    def consolidar(nomes_filtro: list[str]) -> dict:
        out = {}
        for mod in ("tfidf_mlp", "bert_juridico"):
            tot = sum(resultados["por_arquivo"][n][mod]["total"] for n in nomes_filtro)
            a1 = sum(resultados["por_arquivo"][n][mod]["acertos_top1"] for n in nomes_filtro)
            a3 = sum(resultados["por_arquivo"][n][mod]["acertos_top3"] for n in nomes_filtro)
            a5 = sum(resultados["por_arquivo"][n][mod]["acertos_top5"] for n in nomes_filtro)
            out[mod] = {
                "total": tot,
                "top1": round((a1 / tot) * 100.0, 2) if tot else 0.0,
                "top3": round((a3 / tot) * 100.0, 2) if tot else 0.0,
                "top5": round((a5 / tot) * 100.0, 2) if tot else 0.0,
            }
        return out

    resultados["consolidado"]["test (formal + informal)"] = consolidar(["test_formal.jsonl", "test_informal.jsonl"])
    resultados["consolidado"]["val (formal + informal)"] = consolidar(["val_formal.jsonl", "val_informal.jsonl"])
    resultados["consolidado"]["todos (1198 perguntas)"] = consolidar(ARQUIVOS)

    print("\n=== CONSOLIDADO ===", flush=True)
    print(json.dumps(resultados["consolidado"], indent=2, ensure_ascii=False), flush=True)

    saida = PROJECT_ROOT / "data" / "resultados" / "metricas_desktop_test.json"
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nSalvo em: {saida}", flush=True)


if __name__ == "__main__":
    main()
