#!/usr/bin/env python3
"""
Indexador otimizado de todos os códigos do corpus.jsonl para o ChromaDB com bert-juridico.
"""
import json, time, sys, torch
from pathlib import Path

# Adiciona raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sentence_transformers import SentenceTransformer
from src.database.chroma_connection import ChromaConnection

torch.set_num_threads(8)

print("Iniciando indexador de códigos para ChromaDB...", flush=True)
t0 = time.time()

conn = ChromaConnection()
client = conn.get_client()
coll = client.get_or_create_collection(
    name="cc_bert-juridico",
    metadata={"hnsw:space": "cosine"}
)

existing_ids = set(coll.get(include=["metadatas"])["ids"])
print(f"ChromaDB possui atualmente {len(existing_ids)} artigos.", flush=True)

# Ordem de prioridade dos códigos
PRIORIDADE = [
    "cp1940",   # Código Penal
    "cpc2015",  # Código de Processo Civil
    "cpp1941",  # Código de Processo Penal
    "ctn1966",  # Código Tributário Nacional
    "ctb1997",  # Código de Trânsito Brasileiro
    "cdc1990",  # Código de Defesa do Consumidor
    "ce1965",   # Código Eleitoral
    "ccom1850", # Código Comercial
    "cflo2012", # Código Florestal
    "cmin1967", # Código de Mineração
    "cba1986",  # Código Brasileiro de Aeronáutica
    "cpm1969",  # Código Penal Militar
    "cppm1969", # Código de Processo Penal Militar
    "cbt1962",  # Código de Telecomunicações
    "cagu1934", # Código de Águas
    "ccaaf",    # Alta Administração Federal
]

docs_por_lei = {}
with open("data/dataset/corpus.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        aid = d["artigo_id"]
        if aid not in existing_ids:
            lid = d.get("lei_id", "outros")
            if lid not in docs_por_lei:
                docs_por_lei[lid] = []
            cit = d.get("citacao", aid)
            txt = d.get("texto", "").strip()
            docs_por_lei[lid].append({
                "id": aid,
                "embed_text": f"[{cit}] {txt[:350]}",
                "doc_text": f"[{cit}] {txt[:900]}",
                "metadata": {
                    "citacao": cit,
                    "artigo_id": aid,
                    "lei_id": lid
                }
            })

total_novos = sum(len(v) for v in docs_por_lei.values())
print(f"Total de artigos pendentes para indexação: {total_novos}", flush=True)

if total_novos == 0:
    print("Todos os artigos já estão indexados no ChromaDB!", flush=True)
    sys.exit(0)

print("Carregando encoder fine-tuned bert-juridico...", flush=True)
model = SentenceTransformer("data/models/bert_juridico", device="cpu")
# Ajusta max_seq_length para embedding rápido do caput
model.max_seq_length = 96

# Processar por ordem de relevância
leis_ordenadas = [l for l in PRIORIDADE if l in docs_por_lei] + [l for l in docs_por_lei if l not in PRIORIDADE]

indexados_total = 0
for lid in leis_ordenadas:
    itens = docs_por_lei[lid]
    if not itens:
        continue
    t_lei = time.time()
    batch_size = 128
    for i in range(0, len(itens), batch_size):
        lote = itens[i:i + batch_size]
        ids = [x["id"] for x in lote]
        embed_texts = [x["embed_text"] for x in lote]
        docs = [x["doc_text"] for x in lote]
        metas = [x["metadata"] for x in lote]

        embs = model.encode(embed_texts, normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False).tolist()

        coll.upsert(
            ids=ids,
            embeddings=embs,
            documents=docs,
            metadatas=metas
        )

    indexados_total += len(itens)
    dur_lei = time.time() - t_lei
    print(f"[{lid}] {len(itens)} artigos indexados em {dur_lei:.1f}s | Total acumulado: {coll.count()}", flush=True)

print(f"\nIndexação finalizada com sucesso! ChromaDB agora possui {coll.count()} artigos.", flush=True)
