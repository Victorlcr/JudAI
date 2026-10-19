#!/usr/bin/env python3
"""
Conecta ao MongoDB, lê a lei (URL do Planalto ou arquivo .html) e insere os
documentos nas coleções `leis`, `artigos` e `dispositivos`.

Pré-requisitos
  pip install beautifulsoup4 lxml pymongo requests python-dotenv
  - ingestao_lei.py no pacote src.scraper (contém o parser)
  - um MongoDB rodando. Opções:
      * Docker:  docker compose up -d (porta 27017:27017)
      * Atlas (nuvem): configure MONGO_URI no arquivo .env

Uso
  python -m src.scraper.carregar_mongo                  # baixa a lei da URL padrão
  python -m src.scraper.carregar_mongo L10406.html      # ou usa um arquivo local
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# Carrega variáveis do arquivo .env (se existir) sem sobrescrever o ambiente
load_dotenv()

# Import resiliente do parser (suporta invocação via módulo, relativa ou script direto)
try:
    from src.scraper import ingestao_lei as parser
except ImportError:
    try:
        from . import ingestao_lei as parser
    except ImportError:
        import ingestao_lei as parser

# ---------------------------- CONFIGURAÇÃO ---------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "rag_juridico")
NOME_BANCO = MONGO_DB_NAME  # Mantém compatibilidade com referências internas originais
LEI_ID = "cc2002"
LEI_NOME = "Código Civil"
FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
# ---------------------------------------------------------------------------


def conectar():
    """Abre a conexão e confirma que o servidor responde."""
    cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        cliente.admin.command("ping")
    except ServerSelectionTimeoutError:
        sys.exit(
            f"Não consegui conectar ao MongoDB em {MONGO_URI}.\n"
            "Verifique se o servidor está rodando "
            "(ex.: docker compose up -d) ou ajuste MONGO_URI."
        )
    print(f"Conectado ao MongoDB. Banco: '{NOME_BANCO}'")
    return cliente[NOME_BANCO]


def carregar_documentos(fonte: str):
    """Lê a fonte (URL ou arquivo) e devolve as três coleções prontas."""
    raw, origem = parser.obter_bytes(fonte)
    html = parser.decodificar(raw)
    n_fffd = html.count(parser.FFFD)
    meta, artigos, ignoradas = parser.parsear(html)
    if not artigos:
        sys.exit("Nenhum artigo encontrado: o HTML não tem o formato esperado.")
    colecoes = parser.montar_colecoes(
        LEI_ID, LEI_NOME, meta, artigos, origem,
        hashlib.sha256(raw).hexdigest(), n_fffd > 0,
    )
    parser.relatorio(colecoes, ignoradas, n_fffd > 0, n_fffd)
    return colecoes


def inserir(db, colecoes: dict):
    """Apaga a versão anterior desta lei e insere os documentos novos."""
    db["leis"].delete_many({"_id": LEI_ID})
    db["artigos"].delete_many({"lei_id": LEI_ID})
    db["dispositivos"].delete_many({"lei_id": LEI_ID})

    for nome in ("leis", "artigos", "dispositivos"):
        resultado = db[nome].insert_many(colecoes[nome], ordered=False)
        print(f"  {nome}: {len(resultado.inserted_ids)} documentos inseridos")

    # Índices para as consultas mais comuns
    db["artigos"].create_index([("lei_id", 1), ("numero", 1)])
    db["artigos"].create_index("vigente")
    db["dispositivos"].create_index([("lei_id", 1), ("artigo_id", 1)])
    db["dispositivos"].create_index([("tipo", 1), ("vigente", 1)])


def verificar(db):
    """Consulta de conferência: busca o art. 5º já gravado."""
    art = db["artigos"].find_one({"_id": f"{LEI_ID}:art5"})
    print("\nConferência:", art["citacao"], "->", art["caminho"])
    print(art["texto_vigente"][:300])
    print("\nTotais no banco:",
          {c: db[c].count_documents({}) for c in ("leis", "artigos", "dispositivos")})


def main(argv=None):
    """Ponto de entrada CLI para carregar documentos da lei no MongoDB."""
    parser_cli = argparse.ArgumentParser(
        prog="python -m src.scraper.carregar_mongo",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser_cli.add_argument(
        "fonte",
        nargs="?",
        default=FONTE_PADRAO,
        help=f"URL da lei compilada no Planalto ou caminho para arquivo HTML local (padrão: {FONTE_PADRAO})",
    )
    args = parser_cli.parse_args(argv)

    fonte = args.fonte
    colecoes = carregar_documentos(fonte)   # 1) lê e estrutura
    db = conectar()                         # 2) conecta
    inserir(db, colecoes)                   # 3) insere
    verificar(db)                           # 4) confere


if __name__ == "__main__":
    main()
