#!/usr/bin/env python3
"""
Crawler e carregador de legislação do Portal da Legislação do Planalto para o MongoDB.

Varre automaticamente as páginas de índice do Planalto (Constituição, Códigos,
Estatutos, Leis Complementares, Leis Delegadas e Leis Ordinárias por ano),
detecta automaticamente os links de "Texto compilado", extrai a estrutura
(artigos, parágrafos, incisos, alíneas) e insere nas coleções `leis`, `artigos`
e `dispositivos` do MongoDB.

Exemplos de uso:
  # Varre e armazena todas as leis (Constituição, Códigos, Estatutos, Leis Complementares e Ordinárias)
  python -m src.scraper.carregar_mongo

  # Baixar apenas Constituição, Códigos e Estatutos principais (~35 diplomas fundamentais)
  python -m src.scraper.carregar_mongo --escopo codigos

  # Baixar com limite de quantidade ou filtrando anos das Leis Ordinárias
  python -m src.scraper.carregar_mongo --anos 2020-2026 --limite 100

  # Pular leis que já foram inseridas anteriormente no banco (útil para retomar execução)
  python -m src.scraper.carregar_mongo --pular-existentes

  # Baixar uma única lei específica (URL ou arquivo HTML local)
  python -m src.scraper.carregar_mongo https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

load_dotenv()

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
NOME_BANCO = MONGO_DB_NAME
LEI_ID = "cc2002"
LEI_NOME = "Código Civil"
FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"

URL_QUADRO_CODIGOS = "https://www.planalto.gov.br/ccivil_03/Codigos/quadro_cod.htm"
URL_QUADRO_LCP = "https://www.planalto.gov.br/ccivil_03/Leis/LCP/Quadro_Lcp.htm"
URL_QUADRO_LDL = "https://www.planalto.gov.br/ccivil_03/Leis/Ldl/Quadro_LDL.htm"
URL_INDICE_ORDINARIAS = "https://www.planalto.gov.br/ccivil_03/Leis/_Lei-Ordinaria.htm"

# Estatutos e leis estruturais com links diretos no Planalto (ccivil_03)
ESTATUTOS_BASE: list[tuple[str, str, str]] = [
    ("cf1988", "Constituição Federal de 1988", "https://www.planalto.gov.br/ccivil_03/Constituicao/ConstituicaoCompilado.htm"),
    ("l8069", "Estatuto da Criança e do Adolescente (Lei nº 8.069/1990)", "https://www.planalto.gov.br/ccivil_03/leis/l8069.htm"),
    ("l10741", "Estatuto da Pessoa Idosa (Lei nº 10.741/2003)", "https://www.planalto.gov.br/ccivil_03/leis/2003/l10.741.htm"),
    ("l13146", "Estatuto da Pessoa com Deficiência (Lei nº 13.146/2015)", "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm"),
    ("l8906", "Estatuto da Advocacia e a OAB (Lei nº 8.906/1994)", "https://www.planalto.gov.br/ccivil_03/leis/l8906.htm"),
    ("l10257", "Estatuto da Cidade (Lei nº 10.257/2001)", "https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10257.htm"),
    ("l12288", "Estatuto da Igualdade Racial (Lei nº 12.288/2010)", "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12288.htm"),
    ("l10826", "Estatuto do Desarmamento (Lei nº 10.826/2003)", "https://www.planalto.gov.br/ccivil_03/leis/2003/l10.826.htm"),
    ("l4504", "Estatuto da Terra (Lei nº 4.504/1964)", "https://www.planalto.gov.br/ccivil_03/leis/l4504.htm"),
    ("l6001", "Estatuto do Índio (Lei nº 6.001/1973)", "https://www.planalto.gov.br/ccivil_03/leis/l6001.htm"),
    ("l12852", "Estatuto da Juventude (Lei nº 12.852/2013)", "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12852.htm"),
    ("l6880", "Estatuto dos Militares (Lei nº 6.880/1980)", "https://www.planalto.gov.br/ccivil_03/leis/l6880.htm"),
    ("lcp123", "Estatuto Nacional da Microempresa e da Empresa de Pequeno Porte (LC nº 123/2006)", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm"),
    ("l13709", "Lei Geral de Proteção de Dados Pessoais - LGPD (Lei nº 13.709/2018)", "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"),
    ("l12965", "Marco Civil da Internet (Lei nº 12.965/2014)", "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm"),
    ("l14133", "Nova Lei de Licitações e Contratos Administrativos (Lei nº 14.133/2021)", "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"),
]
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


def normalizar_url_planalto(url: str) -> str:
    """Converte http://www.planalto.gov.br para https:// e remove fragmentos."""
    url = url.split("#")[0].strip()
    if url.startswith("http://www.planalto.gov.br"):
        url = "https://" + url[len("http://"):]
    return url


def extrair_id_da_url(url: str) -> str:
    """Extrai um identificador curto e único a partir da URL da lei no Planalto."""
    parsed = urlparse(url)
    stem = Path(parsed.path).stem.lower()
    # Remove sufixos como 'compilada', 'compilado', 'consolidado'
    stem = re.sub(r"(compilad[ao]|consolidad[ao])$", "", stem)
    stem = re.sub(r"[^a-z0-9]+", "", stem)
    if not stem or stem == "constituicao":
        return "cf1988"
    return stem


def descobrir_url_compilada(html: str, url_base: str) -> str | None:
    """
    Procura no HTML da lei um link para 'Texto compilado' no domínio do Planalto.
    Se encontrar, retorna a URL absoluta da versão compilada.
    """
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        texto_link = parser.limpar(a.get_text()).lower()
        if "compilad" in texto_link or "compilad" in href.lower():
            candidata = normalizar_url_planalto(urljoin(url_base, href))
            if "planalto.gov.br/ccivil_03" in candidata.lower() and candidata.lower().endswith((".htm", ".html")):
                return candidata
    return None


def link_eh_lei_valida(url: str, texto: str = "") -> bool:
    """Filtra apenas páginas HTML de leis/códigos/decretos dentro de ccivil_03, ignorando vetos e índices."""
    u = url.lower()
    t = texto.lower()
    if "planalto.gov.br/ccivil_03/" not in u:
        return False
    if not u.endswith((".htm", ".html")):
        return False
    bloqueados = (
        "quadro",
        "principal",
        "_lei",
        "_dec",
        "/msg/",
        "/vep",
        "veto",
        "portaria",
        "resenha",
        "cartilha",
    )
    if any(b in u for b in bloqueados):
        return False
    if "mensagem de veto" in t or "veto" in t:
        return False
    return True


def coletar_codigos() -> list[tuple[str, str, str]]:
    """Varre o Quadro de Códigos do Planalto e retorna lista de (lei_id, lei_nome, url)."""
    resultados: list[tuple[str, str, str]] = []
    try:
        raw, _ = parser.obter_bytes(URL_QUADRO_CODIGOS)
        soup = BeautifulSoup(parser.decodificar(raw), "html.parser")
        for tr in soup.find_all("tr"):
            tds = [parser.limpar(td.get_text()) for td in tr.find_all("td")]
            if len(tds) < 2:
                continue
            nome_codigo = tds[0].rstrip(".")
            for a in tr.find_all("a"):
                href = a.get("href") or ""
                texto_lei = parser.limpar(a.get_text())
                url = normalizar_url_planalto(urljoin(URL_QUADRO_CODIGOS, href))
                if not link_eh_lei_valida(url, texto_lei):
                    continue
                lei_id = extrair_id_da_url(url)
                if lei_id == "l10406":
                    lei_id = "cc2002"
                nome_completo = f"{nome_codigo} ({texto_lei})" if texto_lei and texto_lei != nome_codigo else nome_codigo
                resultados.append((lei_id, nome_completo, url))
    except Exception as exc:
        print(f"[AVISO] Falha ao varrer Quadro de Códigos ({URL_QUADRO_CODIGOS}): {exc}")
    return resultados


def coletar_quadro_tabela(url_quadro: str, prefixo_padrao: str) -> list[tuple[str, str, str]]:
    """Varre uma página de tabela de leis do Planalto (ex: Leis Complementares, Delegadas ou de um ano)."""
    resultados: list[tuple[str, str, str]] = []
    try:
        raw, _ = parser.obter_bytes(url_quadro)
        soup = BeautifulSoup(parser.decodificar(raw), "html.parser")
        for tr in soup.find_all("tr"):
            for a in tr.find_all("a"):
                href = a.get("href") or ""
                texto_link = parser.limpar(a.get_text())
                url = normalizar_url_planalto(urljoin(url_quadro, href))
                if not link_eh_lei_valida(url, texto_link):
                    continue
                lei_id = extrair_id_da_url(url)
                # Limpa data de publicação extra do texto do link
                nome = re.split(r"\s+Publicad[ao]\s+no\s+DOU", texto_link, flags=re.I)[0].strip()
                if not nome:
                    nome = f"{prefixo_padrao} ({lei_id.upper()})"
                resultados.append((lei_id, nome, url))
    except Exception as exc:
        print(f"[AVISO] Falha ao varrer índice {url_quadro}: {exc}")
    return resultados


def coletar_leis_ordinarias(ano_min: int | None = None, ano_max: int | None = None) -> list[tuple[str, str, str]]:
    """Varre o índice de Leis Ordinárias por ano no Planalto."""
    resultados: list[tuple[str, str, str]] = []
    try:
        raw, _ = parser.obter_bytes(URL_INDICE_ORDINARIAS)
        soup = BeautifulSoup(parser.decodificar(raw), "html.parser")
        paginas_anos: list[tuple[int, str]] = []
        vistos: set[str] = set()
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            texto = parser.limpar(a.get_text())
            url_ano = normalizar_url_planalto(urljoin(URL_INDICE_ORDINARIAS, href))
            if url_ano in vistos or "planalto.gov.br/ccivil_03" not in url_ano.lower():
                continue
            m_ano = re.search(r"\b(19\d{2}|20\d{2})\b", texto) or re.search(r"(19\d{2}|20\d{2})", url_ano)
            if m_ano and url_ano.lower().endswith((".htm", ".html")) and "_lei-principal" not in url_ano.lower():
                ano = int(m_ano.group(1))
                if ano_min is not None and ano < ano_min:
                    continue
                if ano_max is not None and ano > ano_max:
                    continue
                vistos.add(url_ano)
                paginas_anos.append((ano, url_ano))

        # Ordena dos anos mais recentes para os mais antigos
        paginas_anos.sort(key=lambda x: x[0], reverse=True)
        for ano, url_ano in paginas_anos:
            print(f"Descobrindo Leis Ordinárias de {ano} ({url_ano})...")
            leis_ano = coletar_quadro_tabela(url_ano, f"Lei Ordinária ({ano})")
            resultados.extend(leis_ano)
    except Exception as exc:
        print(f"[AVISO] Falha ao varrer índice de Leis Ordinárias: {exc}")
    return resultados


def montar_fila_crawler(
    escopo: str = "tudo",
    ano_min: int | None = None,
    ano_max: int | None = None,
) -> list[tuple[str, str, str]]:
    """Monta a fila deduplicada de (lei_id, lei_nome, url) conforme o escopo escolhido."""
    fila_bruta: list[tuple[str, str, str]] = []

    print("Varrendo índices de Códigos e Estatutos do Planalto...")
    fila_bruta.extend(ESTATUTOS_BASE)
    fila_bruta.extend(coletar_codigos())

    if escopo in ("tudo", "complementares"):
        print("Varrendo Quadro de Leis Complementares e Delegadas...")
        fila_bruta.extend(coletar_quadro_tabela(URL_QUADRO_LCP, "Lei Complementar"))
        fila_bruta.extend(coletar_quadro_tabela(URL_QUADRO_LDL, "Lei Delegada"))

    if escopo in ("tudo", "ordinarias"):
        fila_bruta.extend(coletar_leis_ordinarias(ano_min=ano_min, ano_max=ano_max))

    fila_unica: list[tuple[str, str, str]] = []
    ids_vistos: set[str] = set()
    for lei_id, lei_nome, url in fila_bruta:
        if lei_id not in ids_vistos:
            ids_vistos.add(lei_id)
            fila_unica.append((lei_id, lei_nome, url))

    return fila_unica


def carregar_documentos(
    fonte: str,
    lei_id: str = LEI_ID,
    lei_nome: str = LEI_NOME,
    seguir_compilado: bool = True,
    falhar_se_vazio: bool = True,
) -> dict | None:
    """Lê a fonte (URL ou arquivo), segue versão compilada se disponível e devolve as coleções."""
    raw, origem = parser.obter_bytes(fonte)
    html = parser.decodificar(raw)

    # Se for URL remota e não for ainda o link compilado, verifica se há link para "Texto compilado"
    if seguir_compilado and re.match(r"^https?://", origem) and "compilad" not in origem.lower():
        url_comp = descobrir_url_compilada(html, origem)
        if url_comp and url_comp != origem:
            try:
                raw_comp, origem_comp = parser.obter_bytes(url_comp)
                html_comp = parser.decodificar(raw_comp)
                raw, origem, html = raw_comp, origem_comp, html_comp
            except Exception:
                pass  # Mantém o HTML original se o link compilado estiver quebrado

    n_fffd = html.count(parser.FFFD)
    meta, artigos, ignoradas = parser.parsear(html)
    if not artigos:
        if falhar_se_vazio:
            sys.exit("Nenhum artigo encontrado: o HTML não tem o formato esperado.")
        return None

    colecoes = parser.montar_colecoes(
        lei_id,
        lei_nome,
        meta,
        artigos,
        origem,
        hashlib.sha256(raw).hexdigest(),
        n_fffd > 0,
    )
    parser.relatorio(colecoes, ignoradas, n_fffd > 0, n_fffd)
    return colecoes


def inserir(db, colecoes: dict, lei_id: str | None = None):
    """Apaga a versão anterior desta lei específica e insere os documentos novos."""
    alvo_id = lei_id or (colecoes["leis"][0]["_id"] if colecoes.get("leis") else LEI_ID)
    parser.salvar_mongo(db, colecoes, alvo_id)


def verificar(db, lei_id: str = LEI_ID):
    """Consulta de conferência e exibe os totais acumulados no banco."""
    art = db["artigos"].find_one({"_id": f"{lei_id}:art5"}) or db["artigos"].find_one({"lei_id": lei_id})
    if art:
        print("\nConferência:", art["citacao"], "->", art["caminho"])
        print((art.get("texto_vigente") or art.get("texto") or "")[:300])
    print(
        "\nTotais no banco:",
        {c: db[c].count_documents({}) for c in ("leis", "artigos", "dispositivos")},
    )


def parse_faixa_anos(valor: str | None) -> tuple[int | None, int | None]:
    """Interpreta strings como '2020-2026' ou '2024'."""
    if not valor:
        return None, None
    m = re.match(r"^\s*(\d{4})\s*-\s*(\d{4})\s*$", valor)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)
    if valor.strip().isdigit():
        a = int(valor.strip())
        return a, a
    raise ValueError(f"Formato de ano inválido: '{valor}'. Use ex.: 2020-2026 ou 2025.")


def main(argv=None):
    """Ponto de entrada CLI para carregar uma lei específica ou varrer todo o Planalto."""
    parser_cli = argparse.ArgumentParser(
        prog="python -m src.scraper.carregar_mongo",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser_cli.add_argument(
        "fonte",
        nargs="?",
        default=None,
        help="Opcional: URL de uma lei específica ou caminho local .html. Se omitido, executa o crawler do Planalto.",
    )
    parser_cli.add_argument(
        "--escopo",
        choices=["tudo", "codigos", "complementares", "ordinarias"],
        default="tudo",
        help="Escopo do crawler quando nenhuma fonte única é informada (padrão: tudo).",
    )
    parser_cli.add_argument(
        "--anos",
        default=None,
        help="Filtra faixa de anos para Leis Ordinárias (ex.: 2020-2026 ou 2025).",
    )
    parser_cli.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Quantidade máxima de leis a processar nesta execução.",
    )
    parser_cli.add_argument(
        "--pular-existentes",
        action="store_true",
        help="Pula leis cujo lei_id já esteja gravado na coleção `leis` do MongoDB.",
    )
    parser_cli.add_argument("--lei-id", default=None, help="Identificador curto (ao passar fonte única).")
    parser_cli.add_argument("--lei-nome", default=None, help="Nome da lei (ao passar fonte única).")
    args = parser_cli.parse_args(argv)

    # Modo 1: Fonte única explícita (URL ou arquivo HTML local)
    if args.fonte:
        lei_id = args.lei_id or (LEI_ID if args.fonte == FONTE_PADRAO else extrair_id_da_url(args.fonte))
        lei_nome = args.lei_nome or (LEI_NOME if args.fonte == FONTE_PADRAO else lei_id.upper())
        colecoes = carregar_documentos(args.fonte, lei_id=lei_id, lei_nome=lei_nome, falhar_se_vazio=True)
        db = conectar()
        inserir(db, colecoes, lei_id=lei_id)
        verificar(db, lei_id=lei_id)
        return

    # Modo 2: Crawler automático dos quadros do Planalto
    ano_min, ano_max = parse_faixa_anos(args.anos)
    db = conectar()
    existentes: set[str] = set()
    if args.pular_existentes:
        existentes = {doc["_id"] for doc in db["leis"].find({}, {"_id": 1})}
        print(f"Leis já presentes no banco: {len(existentes)}")

    fila = montar_fila_crawler(escopo=args.escopo, ano_min=ano_min, ano_max=ano_max)
    if args.pular_existentes:
        fila = [item for item in fila if item[0] not in existentes]
    if args.limite is not None:
        fila = fila[: args.limite]

    total = len(fila)
    print(f"\nTotal de leis na fila para ingestão: {total}\n" + "=" * 70)

    sucesso = 0
    falhas = 0
    ultimo_id = LEI_ID

    try:
        for idx, (lei_id, lei_nome, url) in enumerate(fila, start=1):
            print(f"\n[{idx}/{total}] {lei_id} | {lei_nome}\n  URL: {url}")
            try:
                colecoes = carregar_documentos(
                    url,
                    lei_id=lei_id,
                    lei_nome=lei_nome,
                    seguir_compilado=True,
                    falhar_se_vazio=False,
                )
                if not colecoes:
                    print(f"  [IGNORADO] Nenhum artigo estruturado encontrado em {url}")
                    falhas += 1
                    continue
                inserir(db, colecoes, lei_id=lei_id)
                sucesso += 1
                ultimo_id = lei_id
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"  [ERRO] Falha ao processar {lei_id} ({url}): {exc}")
                falhas += 1
    except KeyboardInterrupt:
        print("\n\n[INTERROMPIDO PELO USUÁRIO] Finalizando com os dados já gravados no MongoDB...")

    print("\n" + "=" * 70)
    print(f"Resumo do Crawler: {sucesso} leis gravadas com sucesso | {falhas} ignoradas/Com erro.")
    verificar(db, lei_id=ultimo_id)


if __name__ == "__main__":
    main()
