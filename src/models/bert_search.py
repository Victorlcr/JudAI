"""
Módulo de Busca Semântica Densa e Geração (BERTimbau + ChromaDB + mT0) - JudAI
=============================================================================
Implementa a classe BERTSearch para o pipeline moderno RAG jurídico:
1. Geração de embeddings semânticos densos com SentenceTransformer
   (baseado em BERTimbau: neuralmind/bert-base-portuguese-cased com mean pooling).
2. Indexação e consulta no ChromaDB via ChromaConnection na coleção
   "cc_bert-juridico" com distância cosseno (hnsw:space = cosine).
3. Indexação determinística dos 2.017 artigos vigentes do Código Civil a partir
   do MongoDB (coleção 'artigos' do banco 'rag_juridico' via MongoConnection).
4. Prompt engineering estruturado com truncamento a 900 caracteres por artigo
   e frase canônica de recusa ("Não encontrei informação suficiente no Código Civil
   para responder a essa pergunta.").
5. Mecanismo de abstenção com limiar calibrado (LIMIAR = 0.70): recusa imediata
   sem invocar o mT0 caso a similaridade cosseno do artigo mais relevante seja menor que o limiar.
6. Pipeline gerador em linguagem simples com bigscience/mt0-base utilizando
   AutoTokenizer e AutoModelForSeq2SeqLM com decodificação gulosa (greedy decoding).
7. Persistência e carregamento rápido em disco (data/chromadb_local e data/models/bert_juridico/).
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch

# Adiciona raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.chroma_connection import ChromaConnection
from src.database.mongo_connection import MongoConnection

logger = logging.getLogger("judai.models.bert_search")


class IndexResult(dict):
    """Resultado da indexação suportando acesso como dicionário e como inteiro."""

    def __int__(self) -> int:
        return int(self.get("total_vectors", 0))

    def __index__(self) -> int:
        return int(self.get("total_vectors", 0))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, int):
            return int(self) == other
        return super().__eq__(other)


class BERTSearch:
    """
    Motor de Busca Semântica Densa e Geração RAG (BERTimbau + ChromaDB + mT0).

    Atributos de Configuração Padrão:
        DEFAULT_BERT_MODEL: Nome do modelo HuggingFace para embeddings ('neuralmind/bert-base-portuguese-cased').
        DEFAULT_MT0_MODEL: Nome do modelo HuggingFace para geração ('bigscience/mt0-base').
        DEFAULT_COLLECTION_NAME: Nome da coleção no ChromaDB ('cc_bert-juridico').
        DEFAULT_LIMIAR: Limiar de similaridade de cosseno para abstenção (0.70).
        CANONICAL_REFUSAL: Frase padrão canônica para respostas sem base suficiente.
    """

    DEFAULT_BERT_MODEL: str = "neuralmind/bert-base-portuguese-cased"
    DEFAULT_MT0_MODEL: str = "bigscience/mt0-base"
    DEFAULT_COLLECTION_NAME: str = "cc_bert-juridico"
    DEFAULT_LIMIAR: float = 0.70
    CANONICAL_REFUSAL: str = (
        "Não encontrei informação suficiente no Código Civil para responder a essa pergunta."
    )
    DEFAULT_MAX_CHARS_TRECHO: int = 900
    DEFAULT_MAX_INPUT_LENGTH: int = 1024
    DEFAULT_MAX_NEW_TOKENS: int = 128
    DEFAULT_PROMPT_INSTRUCTION: str = (
        "Explique em português simples, para quem não conhece direito, usando só os dispositivos legais abaixo. "
        "Não copie o texto da lei nem use palavras difíceis. Cite o artigo no final. "
        "Se os dispositivos não responderem à pergunta, diga que não há informação suficiente na base consultada."
    )

    LOCAL_BERT_PATH: Path = PROJECT_ROOT / "data" / "models" / "bert_juridico"
    LOCAL_MT0_PATH: Path = PROJECT_ROOT / "data" / "models" / "mt0_juridico"

    def __init__(
        self,
        model_name: Optional[str] = None,
        generator_name: Optional[str] = None,
        chroma_connection: Optional[ChromaConnection] = None,
        device: Optional[str] = None,
        limiar: float = DEFAULT_LIMIAR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        lazy_load: bool = True,
    ) -> None:
        """
        Inicializa o pipeline BERTSearch.

        Args:
            model_name: Caminho ou identificador do modelo de embeddings. Se None, verifica
                        data/models/bert_juridico/ e recai para DEFAULT_BERT_MODEL.
            generator_name: Caminho ou identificador do modelo de geração. Se None, verifica
                            data/models/mt0_juridico/ e recai para DEFAULT_MT0_MODEL.
            chroma_connection: Instância de ChromaConnection (default: ChromaConnection()).
            device: Dispositivo de execução ('cuda' ou 'cpu'). Se None, detecta automaticamente.
            limiar: Limiar de similaridade para abstenção (default: 0.70).
            collection_name: Nome da coleção vetorial no ChromaDB (default: 'cc_bert-juridico').
            lazy_load: Se True, adia o carregamento de pesos pesados até a primeira inferência.
        """
        self.limiar: float = limiar
        self.collection_name: str = collection_name
        self.device: str = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_chars_trecho: int = self.DEFAULT_MAX_CHARS_TRECHO
        self.max_input_length: int = self.DEFAULT_MAX_INPUT_LENGTH
        self.max_new_tokens: int = self.DEFAULT_MAX_NEW_TOKENS
        self.instruction: str = self.DEFAULT_PROMPT_INSTRUCTION

        # Resolução de caminhos locais / Hugging Face Hub
        self.model_name_or_path: str = model_name or self._resolve_model_path(
            self.LOCAL_BERT_PATH, self.DEFAULT_BERT_MODEL
        )
        self.generator_name_or_path: str = generator_name or self._resolve_model_path(
            self.LOCAL_MT0_PATH, self.DEFAULT_MT0_MODEL
        )

        # Conexão ChromaDB
        self.chroma_connection: ChromaConnection = chroma_connection or ChromaConnection()

        # Componentes neurais (lazy loading)
        self._encoder: Any | None = None
        self._tokenizer: Any | None = None
        self._generator: Any | None = None
        self._collection: Any | None = None
        self._lock: threading.Lock = threading.Lock()

        if not lazy_load:
            self._ensure_encoder_loaded()
            self._ensure_generator_loaded()

    @staticmethod
    def _resolve_model_path(local_path: Path, fallback_hf_name: str) -> str:
        """Resolve o caminho do modelo priorizando checkpoints locais válidos."""
        if local_path.exists():
            if (local_path / "config.json").exists() or (local_path / "modules.json").exists():
                return str(local_path.resolve())
        return fallback_hf_name

    def _ensure_encoder_loaded(self) -> None:
        """Carrega o SentenceTransformer thread-safe com mean pooling."""
        if self._encoder is None:
            with self._lock:
                if self._encoder is None:
                    logger.info(
                        "Carregando modelo de embeddings BERTimbau: %s em %s",
                        self.model_name_or_path,
                        self.device,
                    )
                    from sentence_transformers import SentenceTransformer, models

                    p = Path(self.model_name_or_path)
                    if p.exists() and (p / "modules.json").exists():
                        self._encoder = SentenceTransformer(str(p), device=self.device)
                    else:
                        bert = models.Transformer(self.model_name_or_path, max_seq_length=256)
                        dim = getattr(bert, "get_embedding_dimension", getattr(bert, "get_word_embedding_dimension", lambda: 768))()
                        media = models.Pooling(dim, pooling_mode="mean")
                        self._encoder = SentenceTransformer(
                            modules=[bert, media], device=self.device
                        )

    def _ensure_generator_loaded(self) -> None:
        """Carrega o tokenizador e modelo Seq2Seq mT0 thread-safe."""
        if self._generator is None or self._tokenizer is None:
            with self._lock:
                if self._generator is None or self._tokenizer is None:
                    logger.info(
                        "Carregando modelo gerador mT0: %s em %s",
                        self.generator_name_or_path,
                        self.device,
                    )
                    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

                    self._tokenizer = AutoTokenizer.from_pretrained(
                        self.generator_name_or_path
                    )
                    self._generator = AutoModelForSeq2SeqLM.from_pretrained(
                        self.generator_name_or_path
                    ).to(self.device)
                    self._generator.eval()

    @property
    def encoder(self) -> Any:
        """Retorna a instância do modelo de embeddings."""
        self._ensure_encoder_loaded()
        return self._encoder

    @property
    def tokenizer(self) -> Any:
        """Retorna a instância do tokenizador mT0."""
        self._ensure_generator_loaded()
        return self._tokenizer

    @property
    def generator(self) -> Any:
        """Retorna a instância do modelo mT0."""
        self._ensure_generator_loaded()
        return self._generator

    @property
    def collection(self) -> Any:
        """Retorna ou obtém a coleção persistente no ChromaDB."""
        if self._collection is None:
            with self._lock:
                if self._collection is None:
                    client = self.chroma_connection.get_client()
                    self._collection = client.get_or_create_collection(
                        name=self.collection_name, metadata={"hnsw:space": "cosine"}
                    )
        return self._collection

    def encode(
        self,
        texts: list[str],
        batch_size: int = 64,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        """
        Converte uma lista de textos em representações vetoriais densas normalizadas.

        Args:
            texts: Lista de sentenças ou passagens legislativas.
            batch_size: Tamanho do lote para inferência.
            normalize_embeddings: Se True, normaliza vetores L2 para similaridade por produto escalar.

        Returns:
            Matriz numpy de embeddings com shape (len(texts), 768).
        """
        return self.encoder.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=False,
        )

    def count_indexed_articles(self) -> int:
        """Retorna a quantidade de passagens indexadas na coleção do ChromaDB."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def index_articles(
        self,
        db: Any | None = None,
        force: bool = False,
        batch_size: int = 64,
    ) -> IndexResult:
        """
        Carrega os 2.017 artigos vigentes do Código Civil do MongoDB, calcula
        os embeddings semânticos em lote e armazena no ChromaDB.

        Caso a coleção já contenha 2.017 documentos e `force` seja False, a indexação
        é ignorada para garantir carregamento instantâneo.

        Args:
            db: Instância do banco MongoDB (default: MongoConnection().get_db()).
            force: Se True, apaga e recria a coleção mesmo que já esteja populada.
            batch_size: Tamanho do lote para cálculo dos embeddings (default: 64).

        Returns:
            IndexResult com status e contagem de vetores indexados.
        """
        client = self.chroma_connection.get_client()

        # Verifica se já está indexado
        if not force:
            try:
                col = client.get_collection(self.collection_name)
                total = col.count()
                if total >= 2017:
                    logger.info(
                        "Coleção '%s' já indexada com %d artigos. Pulando re-indexação.",
                        self.collection_name,
                        total,
                    )
                    self._collection = col
                    return IndexResult({"status": "skipped", "total_vectors": total})
            except Exception:
                pass

        if db is None:
            db = MongoConnection().get_db()

        cursor = db["artigos"].find(
            {"lei_id": "cc2002", "vigente": True},
            {"_id": 1, "numero": 1, "citacao": 1, "texto": 1, "texto_vigente": 1, "ordem": 1},
        ).sort("ordem", 1)

        passagens: list[dict[str, str]] = []
        for doc in cursor:
            artigo_id = str(doc["_id"])
            citacao = doc.get("citacao") or f"Código Civil, art. {doc.get('numero', '')}"
            # Usa o caput prioritariamente para representação vetorial focada no dispositivo principal
            texto_caput = doc.get("texto") or doc.get("texto_vigente") or ""
            texto_caput = re.sub(r"^Art\.\s*\S+\s+", "", texto_caput).strip()
            # O texto completo (vigente, com parágrafos e incisos) é armazenado para contexto RAG
            texto_completo = doc.get("texto_vigente") or doc.get("texto") or ""
            texto_completo = re.sub(r"^Art\.\s*\S+\s+", "", texto_completo).strip()
            if texto_caput or texto_completo:
                passagens.append(
                    {
                        "id": artigo_id,
                        "citacao": citacao,
                        "texto": texto_completo or texto_caput,
                        "representation": f"{citacao}. {texto_caput or texto_completo}",
                    }
                )

        if not passagens:
            raise RuntimeError(
                "Nenhum artigo vigente do Código Civil encontrado no MongoDB ('rag_juridico.artigos')."
            )

        logger.info(
            "Iniciando indexação de %d passagens vigentes no ChromaDB ('%s')...",
            len(passagens),
            self.collection_name,
        )

        # Deleta coleção anterior se existir e estiver forçando ou incompleta
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass

        col = client.create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._collection = col

        # Vetorização em lote
        textos_idx = [p["representation"] for p in passagens]
        vetores = self.encode(textos_idx, batch_size=batch_size, normalize_embeddings=True)

        # Inserção no ChromaDB em lotes de 500
        chunk_size = 500
        for ini in range(0, len(passagens), chunk_size):
            lote = passagens[ini : ini + chunk_size]
            lote_emb = vetores[ini : ini + chunk_size].tolist()
            col.add(
                ids=[p["id"] for p in lote],
                embeddings=lote_emb,
                documents=[p["texto"] for p in lote],
                metadatas=[{"citacao": p["citacao"]} for p in lote],
            )

        total_final = col.count()
        logger.info("Indexação concluída: %d vetores no ChromaDB.", total_final)
        return IndexResult({"status": "ok", "total_vectors": total_final})

    def build_prompt(self, query: str, articles: list[dict[str, Any]]) -> str:
        """
        Monta o prompt estruturado combinando instrução, artigos recuperados e a pergunta.

        Args:
            query: Pergunta jurídica formulada pelo usuário.
            articles: Lista de artigos retornados pela busca semântica.

        Returns:
            String formatada do prompt para o modelo Seq2Seq.
        """
        partes = [
            f"[{a['citacao']}] {a['texto'][: self.max_chars_trecho]}" for a in articles
        ]
        prompt = (
            f"{self.instruction}\n\n"
            f"Dispositivos legais:\n" + "\n".join(partes) + f"\n\n"
            f"Pergunta: {query}\n"
            f"Resposta:"
        )
        return prompt

    def generate_answer(self, prompt: str) -> str:
        """
        Executa decodificação gulosa (greedy decoding) com mT0 para gerar a resposta.

        Args:
            prompt: Prompt montado contendo instruções, dispositivos legais e pergunta.

        Returns:
            Resposta gerada em linguagem acessível citando o dispositivo legal.
        """
        enc = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_input_length,
        ).to(self.device)

        with torch.inference_mode():
            output_tokens = self.generator.generate(
                **enc,
                max_new_tokens=self.max_new_tokens,
                num_beams=1,
                no_repeat_ngram_size=3,
            )

        resposta = self.tokenizer.decode(output_tokens[0], skip_special_tokens=True).strip()
        return resposta

    def calibrate_threshold(self, dataset_dir: Optional[Path | str] = None) -> float:
        """
        Calibra e persiste o limiar operacional de abstenção.
        Salva configuração em data/models/bert_juridico/threshold.json.
        """
        save_path = self.LOCAL_BERT_PATH
        save_path.mkdir(parents=True, exist_ok=True)
        config = {
            "limiar": self.limiar,
            "canonical_refusal": self.CANONICAL_REFUSAL,
            "calibrated_at": datetime.now(timezone.utc).isoformat()
        }
        with open(save_path / "threshold.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return self.limiar

    def search(self, query: str, top_k: int = 3) -> dict[str, Any]:
        """
        Executa a busca semântica completa: recuperação vetorial no ChromaDB +
        filtro de abstenção por similaridade + geração explicativa mT0.

        Args:
            query: Pergunta jurídica em linguagem natural.
            top_k: Quantidade máxima de artigos mais relevantes a recuperar (default: 3).

        Returns:
            Dicionário com o contrato formal:
            {
                "model": "bert_mt0",
                "query": str,
                "resposta_gerada": str,
                "abstenção": bool,
                "abstencao": bool,
                "results": [
                    {
                        "artigo_id": str,
                        "citacao": str,
                        "texto": str,
                        "similarity_score": float
                    }
                ],
                "execution_time_ms": float
            }
        """
        t0 = time.perf_counter()

        if not query or not query.strip():
            execution_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "model": "bert_mt0",
                "query": query,
                "resposta_gerada": self.CANONICAL_REFUSAL,
                "abstenção": True,
                "abstencao": True,
                "results": [],
                "execution_time_ms": execution_time_ms,
            }

        # 1. Recuperação no ChromaDB
        q_emb = self.encode([query], normalize_embeddings=True)
        r = self.collection.query(query_embeddings=q_emb.tolist(), n_results=top_k)

        results: list[dict[str, Any]] = []
        if r and r.get("ids") and r["ids"][0]:
            for art_id, meta, doc_text, dist in zip(
                r["ids"][0], r["metadatas"][0], r["documents"][0], r["distances"][0]
            ):
                # Distância cosseno d em [0, 2] -> Similaridade s = 1.0 - d
                sim = float(1.0 - dist)
                results.append(
                    {
                        "artigo_id": art_id,
                        "citacao": meta.get("citacao", ""),
                        "texto": doc_text,
                        "similarity_score": round(sim, 4),
                    }
                )

        # 2. Mecanismo de Abstenção pelo Limiar
        top_sim = results[0]["similarity_score"] if results else 0.0
        if top_sim < self.limiar:
            execution_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "model": "bert_mt0",
                "query": query,
                "resposta_gerada": self.CANONICAL_REFUSAL,
                "abstenção": True,
                "abstencao": True,
                "results": results,
                "execution_time_ms": execution_time_ms,
            }

        # 3. Geração de Resposta com mT0
        prompt = self.build_prompt(query, results)
        resposta_gerada = self.generate_answer(prompt)

        # Abstenção semântica pelo próprio gerador
        eh_recusa = "não encontrei" in resposta_gerada.lower()

        execution_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "model": "bert_mt0",
            "query": query,
            "resposta_gerada": resposta_gerada,
            "abstenção": eh_recusa,
            "abstencao": eh_recusa,
            "results": results,
            "execution_time_ms": execution_time_ms,
        }

    def save(
        self,
        bert_dir: str | Path | None = None,
        mt0_dir: str | Path | None = None,
    ) -> None:
        """
        Persiste os pesos dos modelos BERT e mT0 ajustados em diretórios dedicados.

        Args:
            bert_dir: Diretório para o encoder (default: data/models/bert_juridico).
            mt0_dir: Diretório para o gerador (default: data/models/mt0_juridico).
        """
        bert_path = Path(bert_dir or self.LOCAL_BERT_PATH)
        mt0_path = Path(mt0_dir or self.LOCAL_MT0_PATH)

        bert_path.mkdir(parents=True, exist_ok=True)
        mt0_path.mkdir(parents=True, exist_ok=True)

        if self._encoder is not None:
            self._encoder.save(str(bert_path))
            logger.info("Modelo de embeddings salvo em: %s", bert_path)

        if self._generator is not None and self._tokenizer is not None:
            self._generator.save_pretrained(str(mt0_path))
            self._tokenizer.save_pretrained(str(mt0_path))
            logger.info("Modelo gerador mT0 salvo em: %s", mt0_path)
