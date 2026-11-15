"""
Módulo CLI de Treinamento, Indexação e Verificação Unificada - JudAI
===================================================================
Executável via:
    python -m src.models.train_all [opções]

Etapas de Execução:
------------------
1. Conecta ao MongoDB via MongoConnection e valida 2.017 artigos vigentes do Código Civil (cc2002).
2. Treina o modelo clássico TFIDF_MLP (TfidfMLPSearch), avalia na base de validação (avaliacao_inicial.jsonl)
   e persiste artefatos em data/models/tfidf_mlp/.
3. Inicializa BERTSearch, indexa artigos no ChromaDB via ChromaConnection (reutiliza se count >= 2017),
   e calibra o limiar de abstenção.
4. Executa inferência end-to-end com pergunta de teste ("Com quantos anos a pessoa passa a ser plenamente
   capaz na vida civil?"), valida recuperação do Art. 5º em ambos os modelos e exibe relatório final.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Suporte nativo a UTF-8 no console do Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona a raiz do repositório ao sys.path se necessário
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Otimizações de CPU/GPU antes da carga de bibliotecas neurais
_CPU_THREADS = str(max(4, (os.cpu_count() or 8)))
os.environ["OMP_NUM_THREADS"] = _CPU_THREADS
os.environ["MKL_NUM_THREADS"] = _CPU_THREADS
os.environ["TOKENIZERS_PARALLELISM"] = "true"

import torch
torch.set_num_threads(int(_CPU_THREADS))

from src.database.mongo_connection import MongoConnection
from src.database.chroma_connection import ChromaConnection

# Configuração de Logger com formatação visual
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_all")


def parse_args() -> argparse.Namespace:
    """Configura e processa argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="JudAI - Pipeline Unificado de Treinamento e Indexação de Modelos Jurídicos",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=20,
        help="Número de épocas de treinamento para a rede neural TFIDF_MLP.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Tamanho do batch para o treinamento do modelo clássico.",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001,
        help="Taxa de aprendizado (learning rate) para o otimizador Adam.",
    )
    parser.add_argument(
        "--force-chroma",
        action="store_true",
        default=False,
        help="Força a recriação e re-indexação da base vetorial ChromaDB mesmo se já populada.",
    )
    parser.add_argument(
        "--skip-bert-index",
        action="store_true",
        default=False,
        help="Pula a indexação vetorial do ChromaDB no pipeline moderno.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Modo de simulação: valida conexões, dados e caminhos sem executar treinos pesados.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="data/dataset",
        help="Caminho relativo para a pasta contendo os datasets versionados em JSONL.",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="data/models",
        help="Diretório base para persistência dos modelos treinados.",
    )
    parser.add_argument(
        "--sample-query",
        type=str,
        default="Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
        help="Pergunta de teste utilizada na validação de fumaça de inferência ao final.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Quantidade de artigos a recuperar na consulta de verificação.",
    )
    return parser.parse_args()


def imprimir_cabecalho(args: argparse.Namespace) -> None:
    """Exibe banner informativo com a configuração de execução."""
    print("=" * 80)
    print("      JUDAI - PIPELINE UNIFICADO DE TREINAMENTO E INDEXAÇÃO DE MODELOS")
    print("=" * 80)
    print(f"  Diretório Raiz:       {ROOT_DIR}")
    print(f"  Dispositivo Torch:    CPU ({torch.get_num_threads()} threads ativas)")
    print(f"  Épocas MLP:           {args.epochs}")
    print(f"  Batch Size MLP:       {args.batch_size}")
    print(f"  Learning Rate:        {args.lr}")
    print(f"  Forçar ChromaDB:      {args.force_chroma}")
    print(f"  Pular Indexação BERT: {args.skip_bert_index}")
    print(f"  Modo Dry-Run:         {args.dry_run}")
    print(f"  Pergunta de Teste:    '{args.sample_query}'")
    print("=" * 80)


def step_1_verificar_mongodb() -> Any:
    """Etapa 1: Conecta ao MongoDB e confirma presença de artigos vigentes."""
    logger.info("[Etapa 1/4] Conectando ao MongoDB via MongoConnection...")
    t0 = time.perf_counter()
    db = MongoConnection().get_db()

    filtro = {"vigente": True}
    total_vigentes = db["artigos"].count_documents(filtro)
    total_leis = db["leis"].count_documents({})
    duracao = (time.perf_counter() - t0) * 1000

    if total_vigentes == 0:
        logger.error("ERRO FATAL: Coleção 'artigos' no MongoDB está vazia ou sem artigos vigentes!")
        logger.error("Execute primeiro: python -m src.scraper.carregar_mongo")
        raise RuntimeError("MongoDB não contém artigos vigentes para treinamento.")

    logger.info(
        f"[Etapa 1/4] Sucesso: MongoDB conectado ({duracao:.1f}ms). "
        f"Base completa: {total_leis} lei(s) | {total_vigentes} artigos vigentes encontrados."
    )
    return db


def step_2_treinar_tfidf_mlp(db: Any, args: argparse.Namespace) -> Any:
    """Etapa 2: Inicializa, treina e avalia o modelo clássico TFIDF_MLP."""
    logger.info("[Etapa 2/4] Iniciando pipeline do Modelo Clássico (TF-IDF + MLP)...")
    dataset_path = ROOT_DIR / args.dataset_dir
    save_path = ROOT_DIR / args.models_dir / "tfidf_mlp"

    # Validações prévias
    arquivo_pares = dataset_path / "pares_bert_inicial.jsonl"
    arquivo_aval = dataset_path / "avaliacao_inicial.jsonl"
    if not arquivo_pares.exists() or not arquivo_aval.exists():
        raise FileNotFoundError(
            f"Datasets necessários não encontrados em '{dataset_path}'. "
            f"Certifique-se de que 'pares_bert_inicial.jsonl' e 'avaliacao_inicial.jsonl' existam."
        )

    from src.models.tfidf_mlp_search import TfidfMLPSearch

    searcher_tfidf = TfidfMLPSearch(model_dir=save_path)

    if args.dry_run:
        logger.info("[Etapa 2/4] [DRY-RUN] Simulação ativada. Validação dos caminhos e datasets concluída com sucesso.")
        return searcher_tfidf

    t0 = time.perf_counter()
    historico = searcher_tfidf.fit(
        db=db,
        dataset_dir=dataset_path,
        save_dir=save_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
    duracao = time.perf_counter() - t0

    logger.info(
        f"[Etapa 2/4] Treinamento TFIDF_MLP concluído em {duracao:.2f}s! "
        f"Melhor época: {historico.get('best_epoch', args.epochs)} | "
        f"Val Loss: {historico.get('val_loss', 0.0):.4f} | "
        f"Val Acc: {historico.get('val_acc', 0.0) * 100:.2f}%"
    )
    logger.info(f"[Etapa 2/4] Artefatos salvos com sucesso em: {save_path}")

    # Avaliação out-of-sample
    metricas = searcher_tfidf.evaluate(dataset_dir=dataset_path)
    logger.info(
        f"[Etapa 2/4] Avaliação out-of-sample: Top-1 Acc = {metricas.get('top1_acc', 0.0)*100:.1f}%, "
        f"Top-3 Acc = {metricas.get('top3_acc', 0.0)*100:.1f}% ({metricas.get('total_samples', 0)} exemplos)"
    )

    return searcher_tfidf


def step_3_indexar_bert(db: Any, args: argparse.Namespace) -> Any:
    """Etapa 3: Inicializa BERTSearch, indexa artigos no ChromaDB e calibra limiar."""
    logger.info("[Etapa 3/4] Iniciando pipeline do Modelo Moderno (BERTimbau + ChromaDB + mT0)...")
    from src.models.bert_search import BERTSearch

    searcher_bert = BERTSearch()

    if args.dry_run:
        logger.info("[Etapa 3/4] [DRY-RUN] Simulação ativada. BERTSearch inicializado com sucesso.")
        return searcher_bert

    if args.skip_bert_index:
        logger.info("[Etapa 3/4] Flag --skip-bert-index fornecida. Indexação vetorial pulada.")
    else:
        t0 = time.perf_counter()
        resultado_index = searcher_bert.index_articles(db=db, force=args.force_chroma)
        duracao = time.perf_counter() - t0
        status_idx = resultado_index.get("status", "ok") if isinstance(resultado_index, dict) else "ok"
        total_vecs = resultado_index.get("total_vectors", int(resultado_index)) if isinstance(resultado_index, dict) else int(resultado_index)
        logger.info(
            f"[Etapa 3/4] Indexação vetorial concluída em {duracao:.2f}s! "
            f"Status: {status_idx} | "
            f"Total de vetores no ChromaDB: {total_vecs}"
        )

    # Calibração e validação do limiar de abstenção
    dataset_path = ROOT_DIR / args.dataset_dir
    limiar = searcher_bert.calibrate_threshold(dataset_dir=dataset_path)
    logger.info(f"[Etapa 3/4] Limiar de abstenção operacional calibrado: LIMIAR = {limiar:.3f}")
    return searcher_bert


def step_4_verificar_inferencia(
    searcher_tfidf: Any,
    searcher_bert: Any,
    args: argparse.Namespace,
) -> None:
    """Etapa 4: Executa inferência end-to-end com asserções estritas no Art. 5º do CC."""
    logger.info(f"[Etapa 4/4] Executando verificação de inferência para: '{args.sample_query}'...")

    if args.dry_run:
        logger.info("[Etapa 4/4] [DRY-RUN] Simulação ativada. Asserções de inferência puladas no modo dry-run.")
        return

    # 1. Inferência Modelo Clássico (TF-IDF + MLP)
    t0 = time.perf_counter()
    res_tfidf = searcher_tfidf.search(args.sample_query, top_k=args.top_k)
    lat_tfidf = (time.perf_counter() - t0) * 1000

    # 2. Inferência Modelo Moderno (BERTimbau + mT0)
    t1 = time.perf_counter()
    res_bert = searcher_bert.search(args.sample_query, top_k=args.top_k)
    lat_bert = (time.perf_counter() - t1) * 1000

    # Validações estruturais e semânticas
    artigos_tfidf = [r.get("artigo_id", "") for r in res_tfidf.get("results", [])]
    citacoes_tfidf = [r.get("citacao", "") for r in res_tfidf.get("results", [])]
    score_tfidf = res_tfidf["results"][0]["score"] if res_tfidf.get("results") else 0.0

    artigos_bert = [r.get("artigo_id", "") for r in res_bert.get("results", [])]
    citacoes_bert = [r.get("citacao", "") for r in res_bert.get("results", [])]
    score_bert = res_bert["results"][0]["similarity_score"] if res_bert.get("results") else 0.0
    resposta_mt0 = res_bert.get("resposta_gerada", "")
    abstencao = res_bert.get("abstenção", False)

    # Asserções no Art. 5º do Código Civil
    achou_art5_tfidf = any("art5" in a or "art. 5" in c.lower() for a, c in zip(artigos_tfidf, citacoes_tfidf))
    achou_art5_bert = any("art5" in a or "art. 5" in c.lower() for a, c in zip(artigos_bert, citacoes_bert))

    assert achou_art5_tfidf, (
        f"Falha na validação do Modelo Clássico: Art. 5º não encontrado no Top-{args.top_k}. "
        f"Resultados obtidos: {artigos_tfidf}"
    )
    assert achou_art5_bert, (
        f"Falha na validação do Modelo Moderno: Art. 5º não encontrado no Top-{args.top_k}. "
        f"Resultados obtidos: {artigos_bert}"
    )
    assert not abstencao, "Falha na validação do Modelo Moderno: o modelo absteve-se indevidamente para pergunta do escopo."
    assert len(resposta_mt0.strip()) > 0, "Falha na validação do Modelo Moderno: resposta gerada pelo mT0 está vazia."

    # Exibição do Quadro Comparativo de Verificação
    print("\n" + "=" * 80)
    print("                    QUADRO DE VERIFICAÇÃO END-TO-END")
    print("=" * 80)
    print(f"Consulta: '{args.sample_query}'\n")
    print("--- [1] MODELO CLÁSSICO (TF-IDF + MLP) ---")
    print(f"  Top-1 Recuperado:   {citacoes_tfidf[0]} ({artigos_tfidf[0]})")
    print(f"  Confiança Softmax:  {score_tfidf * 100:.2f}%")
    print(f"  Latência Total:     {lat_tfidf:.2f} ms")
    print(f"  Art. 5º Presente:   SIM [OK]")
    print("\n--- [2] MODELO MODERNO (BERTimbau + ChromaDB + mT0) ---")
    print(f"  Top-1 Recuperado:   {citacoes_bert[0]} ({artigos_bert[0]})")
    print(f"  Similaridade Coss:  {score_bert:.4f}")
    print(f"  Abstenção:          {abstencao} [OK]")
    print(f"  Latência Total:     {lat_bert:.2f} ms")
    print(f"  Resposta do mT0:    \"{resposta_mt0.strip()}\"")
    print(f"  Art. 5º Presente:   SIM [OK]")
    print("=" * 80)
    print("STATUS FINAL DA SUITE DE TREINAMENTO E VALIDAÇÃO: SUCESSO ABSOLUTO (PASS)")
    print("=" * 80 + "\n")


def train_all(args: argparse.Namespace) -> int:
    """Função orquestradora principal do CLI."""
    t_inicio_total = time.perf_counter()
    imprimir_cabecalho(args)

    try:
        # Etapa 1
        db = step_1_verificar_mongodb()

        # Etapa 2
        searcher_tfidf = step_2_treinar_tfidf_mlp(db, args)

        # Etapa 3
        searcher_bert = step_3_indexar_bert(db, args)

        # Etapa 4
        step_4_verificar_inferencia(searcher_tfidf, searcher_bert, args)

        tempo_total = time.perf_counter() - t_inicio_total
        logger.info(f"Pipeline train_all finalizado com êxito em {tempo_total:.2f} segundos.")
        return 0

    except Exception as exc:
        logger.exception(f"FALHA NO PIPELINE DE TREINAMENTO: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(train_all(parse_args()))
