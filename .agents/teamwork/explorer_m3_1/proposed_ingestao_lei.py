#!/usr/bin/env python3
"""
Lê o HTML de uma lei do Portal da Legislação do Planalto (versão compilada),
extrai a estrutura (artigos, parágrafos, incisos, alíneas) e grava em MongoDB.

Coleções geradas
----------------
leis          1 documento por lei (metadados, hash do arquivo, data da coleta)
artigos       1 documento por artigo, com parágrafos/incisos/alíneas ANINHADOS
dispositivos  1 documento por artigo/§/inciso/alínea (estrutura "plana",
              útil para comparar granularidades de chunking e indexar)

Uso
---
  # a partir de um arquivo local, gravando no MongoDB local
  python -m src.scraper.ingestao_lei L10406.html --lei-id cc2002 --lei-nome "Código Civil"

  # baixando direto do Planalto (recomendado: preserva os acentos)
  python -m src.scraper.ingestao_lei https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm \
         --lei-id cc2002 --lei-nome "Código Civil"

  # sem MongoDB: só exporta JSON Lines para uma pasta
  python -m src.scraper.ingestao_lei L10406.html --sem-mongo --saida-jsonl saida/

Dependências: pip install beautifulsoup4 lxml pymongo requests
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Leitura do arquivo (atenção à codificação!)
# --------------------------------------------------------------------------
# O Planalto serve as páginas em windows-1252. Se o arquivo for salvo/lido como
# UTF-8 "com substituição", cada letra acentuada vira "" e NÃO há como
# recuperar. Por isso lemos os bytes brutos e escolhemos a codificação aqui.

FFFD = ""


def obter_bytes(entrada: str) -> tuple[bytes, str]:
    """Devolve (bytes_brutos, origem). Aceita caminho local ou URL."""
    if re.match(r"^https?://", entrada):
        import requests

        resp = requests.get(entrada, timeout=60, headers={"User-Agent": "pesquisa-rag-academica/1.0"})
        resp.raise_for_status()
        return resp.content, entrada  # .content = bytes, sem decodificar
    return Path(entrada).read_bytes(), entrada


def decodificar(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")  # estrito: falha se for windows-1252
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# --------------------------------------------------------------------------
# Expressões regulares
# --------------------------------------------------------------------------
# Tolerantes a "" (acento perdido) para que o código funcione também em
# arquivos danificados, mas o ideal é usar o arquivo com a codificação correta.

NUM = r"\d{1,3}(?:\.\d{3})+|\d+"                  # 5, 10, 1.368, 2046
ORD = r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"        # º, °, "o" sobrescrito
SUF = r"(?:\s*-\s*([A-Z])\b)?"                    # sufixo -A, -B ...

RE_ART = re.compile(rf"^Art\.?\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
RE_PAR = re.compile(rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)
RE_PUN = re.compile(r"^Par.grafo\s+.nico\s*[.\-–—]*\s*(.*)$", re.S | re.I)
RE_INC = re.compile(r"^([IVXLCDM]+(?:-[A-Z])?)\s*[-–—\ufffd]\s*(.*)$", re.S)
RE_ALI = re.compile(r"^([a-z])\)\s*(.*)$", re.S)
RE_HEAD = re.compile(
    r"^(?i:(LIVRO|SUBT.TULO|T.TULO|CAP.TULO|SUBSE..O|SE..O))\s+"
    r"([IVXLCDM]+(?:-[A-Z])?|(?i:.NICO|COMPLEMENTAR))\b\s*(.*)$",
    re.S,
)
RE_FIM = re.compile(r"^Bras.lia,", re.I)
# Notas entre parênteses ao fim dos dispositivos: (Redação dada pela Lei ...),
# (Incluído pela ...), (Revogado pela ...), (Vide ...), (Vigência) etc.
RE_NOTA = re.compile(
    r"\(\s*(?:Reda|Inclu|Revogad|Vide|Vig|Regulament|Produ|Renumerad|Vetad|Express|Declarad|Suprimid)[^()]*\)",
    re.I,
)

NIVEIS = ["parte", "livro", "titulo", "subtitulo", "capitulo", "secao", "subsecao"]
ROTULO_NIVEL = {
    "parte": "Parte", "livro": "Livro", "titulo": "Título", "subtitulo": "Subtítulo",
    "capitulo": "Capítulo", "secao": "Seção", "subsecao": "Subseção",
}


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------
def limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def proporcao_riscada(p) -> float:
    """Fração do texto do <p> que está dentro de <strike>/<s>/<del> (redação antiga)."""
    total = riscado = 0
    for no in p.find_all(string=True):
        s = no.strip()
        if not s:
            continue
        total += len(s)
        for anc in no.parents:
            if anc.name in ("strike", "s", "del") or "line-through" in (anc.get("style") or ""):
                riscado += len(s)
                break
    return riscado / total if total else 0.0


def separar_notas(texto: str) -> tuple[str, list[str]]:
    notas = [limpar(n) for n in RE_NOTA.findall(texto)]
    sem = limpar(RE_NOTA.sub(" ", texto))
    if re.fullmatch(r"[\s;.,:\-–—]*", sem):  # sobrou só pontuação
        sem = ""
    return sem, notas


def ordinal(n: str) -> str:
    return f"{n}º" if n.isdigit() and int(n) <= 9 else n


def fmt_numero(bruto: str, sufixo: str | None) -> str:
    n = bruto.replace(".", "")
    return f"{n}-{sufixo}" if sufixo else n


def rotulo_numero(numero: str) -> str:
    """'1368-A' -> '1.368-A' ; '5' -> '5º' (convenção: ordinal até o 9)."""
    base, _, suf = numero.partition("-")
    base = ordinal(base) if int(base) <= 9 else f"{int(base):,}".replace(",", ".")
    return f"{base}-{suf}" if suf else base


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------
def classificar_cabecalho(texto: str):
    """Reconhece PARTE / LIVRO / TÍTULO / CAPÍTULO / SEÇÃO / SUBSEÇÃO."""
    compacto = re.sub(r"\s+", "", texto).upper()  # "P A R T E  G E R A L" -> "PARTEGERAL"
    m = re.match(r"^PARTE\W*(GERAL|ESPECIAL)", compacto)
    if m:
        return "parte", m.group(1).capitalize(), ""
    m = RE_HEAD.match(texto)
    if not m:
        return None
    palavra = m.group(1).upper()
    if palavra.startswith("SUBT"):
        nivel = "subtitulo"
    elif palavra.startswith("SUBS"):
        nivel = "subsecao"
    elif palavra.startswith("SE"):
        nivel = "secao"
    elif palavra.startswith("LIV"):
        nivel = "livro"
    elif palavra.startswith("CAP"):
        nivel = "capitulo"
    else:
        nivel = "titulo"
    return nivel, m.group(2), limpar(m.group(3))


def novo_no(tipo, numero, texto, p, **extra):
    texto, notas = separar_notas(texto)
    riscado = proporcao_riscada(p) > 0.8
    revogado = any(re.match(r"\(\s*Revogad", n, re.I) for n in notas)
    if revogado:
        status = "revogado"
    elif riscado:
        status = "redacao_anterior"
    else:
        status = "vigente"
    no = {
        "tipo": tipo,
        "numero": numero,
        "texto": texto,
        "anotacoes": notas,
        "status": status,
        "vigente": status == "vigente",
    }
    no.update(extra)
    return no


def parsear(html: str):
    soup = BeautifulSoup(html, "lxml")
    linhas = [(p, limpar(p.get_text())) for p in soup.find_all("p")]
    linhas = [(p, t) for p, t in linhas if t]

    meta = {"titulo": None, "ementa": None}
    artigos: list[dict] = []
    contexto: dict[str, str] = {}
    art = par = inc = ultimo = None
    iniciou = False
    ignoradas: list[str] = []
    ordem = 0

    for i, (p, texto) in enumerate(linhas):
        # --- metadados antes do corpo da lei
        if not iniciou:
            if meta["titulo"] is None and re.match(r"^LEI\b", texto, re.I):
                meta["titulo"] = texto
            if re.match(r"^O PRESIDENTE", texto, re.I) and i > 0:
                meta["ementa"] = linhas[i - 1][1]

        if RE_FIM.match(texto) and art:
            break  # assinatura / fim do texto

        cab = classificar_cabecalho(texto)
        if cab and not RE_ART.match(texto):
            iniciou = True
            nivel, numero, titulo = cab
            idx = NIVEIS.index(nivel)
            for n in NIVEIS[idx:]:
                contexto.pop(n, None)
            contexto[nivel] = f"{ROTULO_NIVEL[nivel]} {numero}" + (f" - {titulo}" if titulo else "")
            art = par = inc = ultimo = None
            continue

        m = RE_ART.match(texto)
        if m:
            iniciou = True
            ordem += 1
            numero = fmt_numero(m.group(1), m.group(2))
            a = p.find("a", attrs={"name": re.compile(r"^art", re.I)})
            art = novo_no(
                "artigo", numero, m.group(3), p,
                rotulo=f"art. {rotulo_numero(numero)}",
                ancora=a["name"] if a else None,
                ordem=ordem,
                contexto=dict(contexto),
                incisos=[], paragrafos=[],
            )
            artigos.append(art)
            par = inc = None
            ultimo = art
            continue

        if not art:
            continue  # ainda no cabeçalho/índice

        ordem += 1
        m_par, m_pun = RE_PAR.match(texto), RE_PUN.match(texto)
        if m_par or m_pun:
            numero = "unico" if m_pun else fmt_numero(m_par.group(1), m_par.group(2))
            corpo = m_pun.group(1) if m_pun else m_par.group(3)
            rot = "parágrafo único" if m_pun else f"§ {ordinal(numero)}"
            par = novo_no("paragrafo", numero, corpo, p, rotulo=rot, ordem=ordem, incisos=[])
            art["paragrafos"].append(par)
            inc = None
            ultimo = par
            continue

        m = RE_INC.match(texto)
        if m:
            inc = novo_no("inciso", m.group(1), m.group(2), p,
                          rotulo=f"inciso {m.group(1)}", ordem=ordem, alineas=[])
            (par or art)["incisos"].append(inc)
            ultimo = inc
            continue

        m = RE_ALI.match(texto)
        if m and inc is not None:
            ali = novo_no("alinea", m.group(1), m.group(2), p, rotulo=f"alínea {m.group(1)}", ordem=ordem)
            inc["alineas"].append(ali)
            ultimo = ali
            continue

        # Linha sem marcador: nota solta, título sem rótulo ou continuação.
        corpo, notas = separar_notas(texto)
        if corpo.isupper() and len(corpo) < 80:
            # ex.: "DA LAJE (Incluído pela Lei ...)": título sem o rótulo "TÍTULO N".
            # Tratado como título sem número (nível assumido: título).
            for n in NIVEIS[NIVEIS.index("titulo"):]:
                contexto.pop(n, None)
            contexto["titulo"] = f"Título - {corpo.capitalize()}"
            art = par = inc = ultimo = None
            continue
        if ultimo is not None:
            ultimo["anotacoes"].extend(notas)
            if corpo:
                ultimo["texto"] = limpar(f"{ultimo['texto']} {corpo}")
            if any(re.match(r"\(\s*Revogad", n, re.I) for n in notas):
                ultimo["status"], ultimo["vigente"] = "revogado", False
            if corpo:
                ignoradas.append(texto[:80])  # só registra as que viraram texto
        else:
            ignoradas.append(texto[:80])

    return meta, artigos, ignoradas


# --------------------------------------------------------------------------
# Identificadores únicos e coleções de saída
# --------------------------------------------------------------------------
def nomes_unicos(nos: list[dict], chave) -> dict[int, str]:
    """
    Uma lei compilada traz a redação antiga (riscada) e a nova com o MESMO número.
    O dispositivo vigente fica com o id "limpo"; os demais recebem o sufixo ~h1, ~h2...
    """
    grupos = defaultdict(list)
    for n in nos:
        grupos[chave(n)].append(n)
    res: dict[int, str] = {}
    for k, grupo in grupos.items():
        vencedor = next((n for n in grupo if n["vigente"]), grupo[0])
        res[id(vencedor)] = k
        h = 0
        for n in grupo:
            if n is not vencedor:
                h += 1
                res[id(n)] = f"{k}~h{h}"
    return res


def texto_plano(art: dict) -> str:
    """Texto corrido do artigo somente com o que está vigente (para indexação)."""
    if not art["vigente"]:
        return ""
    partes = [f"Art. {rotulo_numero(art['numero'])} {art['texto']}".strip()]

    def incisos(lista):
        for i in lista:
            if i["vigente"] and i["texto"]:
                partes.append(f"{i['numero']} - {i['texto']}")
                for a in i["alineas"]:
                    if a["vigente"] and a["texto"]:
                        partes.append(f"{a['numero']}) {a['texto']}")

    incisos(art["incisos"])
    for p in art["paragrafos"]:
        if p["vigente"]:
            partes.append(f"{p['rotulo'][0].upper()}{p['rotulo'][1:]}. {p['texto']}".strip())
            incisos(p["incisos"])
    return "\n".join(partes)


def montar_colecoes(lei_id: str, lei_nome: str, meta: dict, artigos: list[dict],
                    fonte: str, sha256: str, tem_acento_perdido: bool):
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ids_art = nomes_unicos(artigos, lambda a: f"art{a['numero']}")
    planos: list[dict] = []

    def registrar(no, id_, artigo_id, pai_id, citacao, texto_pai, contexto):
        no["_id"] = id_
        planos.append({
            "_id": id_, "lei_id": lei_id, "artigo_id": artigo_id, "pai_id": pai_id,
            "tipo": no["tipo"], "numero": no["numero"], "rotulo": no["rotulo"],
            "citacao": citacao, "texto": no["texto"], "texto_pai": texto_pai,
            "status": no["status"], "vigente": no["vigente"], "anotacoes": no["anotacoes"],
            "caminho": " > ".join(contexto.values()), "contexto": contexto,
            "ordem": no["ordem"],
        })

    def descer_incisos(lista, base_id, artigo_id, pai_id, cit, texto_pai, ctx):
        nomes = nomes_unicos(lista, lambda i: f"inc-{i['numero']}")
        for i in lista:
            iid = f"{base_id}/{nomes[id(i)]}"
            icit = f"{cit}, {i['rotulo']}"
            registrar(i, iid, artigo_id, pai_id, icit, texto_pai, ctx)
            an = nomes_unicos(i["alineas"], lambda a: f"ali-{a['numero']}")
            for a in i["alineas"]:
                registrar(a, f"{iid}/{an[id(a)]}", artigo_id, iid,
                          f"{icit}, {a['rotulo']}", i["texto"], ctx)

    for art in artigos:
        aid = f"{lei_id}:{ids_art[id(art)]}"
        cit = f"{lei_nome}, {art['rotulo']}"
        ctx = art["contexto"]
        registrar(art, aid, aid, None, cit, "", ctx)
        descer_incisos(art["incisos"], aid, aid, aid, cit, art["texto"], ctx)
        nomes_p = nomes_unicos(art["paragrafos"], lambda p: f"par-{p['numero']}")
        for p in art["paragrafos"]:
            pid = f"{aid}/{nomes_p[id(p)]}"
            pcit = f"{cit}, {p['rotulo']}"
            registrar(p, pid, aid, aid, pcit, art["texto"], ctx)
            descer_incisos(p["incisos"], pid, aid, pid, pcit, p["texto"], ctx)
        art["lei_id"] = lei_id
        art["citacao"] = cit
        art["caminho"] = " > ".join(ctx.values())
        art["texto_vigente"] = texto_plano(art)

    lei = {
        "_id": lei_id, "nome": lei_nome, "titulo": meta.get("titulo") if isinstance(meta, dict) else None,
        "ementa": meta.get("ementa") if isinstance(meta, dict) else None,
        "fonte": fonte, "sha256": sha256, "coletado_em": agora,
        "acentos_preservados": not tem_acento_perdido,
        "n_artigos": len(artigos), "n_dispositivos": len(planos),
    }
    return {"leis": [lei], "artigos": artigos, "dispositivos": planos}


# --------------------------------------------------------------------------
# Verificações e relatório
# --------------------------------------------------------------------------
def relatorio(cols: dict, ignoradas: list[str], tem_acento_perdido: bool, n_fffd: int):
    arts, disp = cols["artigos"], cols["dispositivos"]
    por_tipo = defaultdict(int)
    por_status = defaultdict(int)
    for d in disp:
        por_tipo[d["tipo"]] += 1
        por_status[d["status"]] += 1
    print(f"Artigos: {len(arts)} | dispositivos: {len(disp)}")
    print("  por tipo:  ", dict(por_tipo))
    print("  por status:", dict(por_status))

    # lacunas na numeração dos artigos principais (sem sufixo -A)
    nums = sorted({int(a["numero"]) for a in arts if a["numero"].isdigit()})
    if nums:
        faltando = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
        print(f"  numeração: art. {nums[0]} a {nums[-1]}; lacunas: {faltando[:20] or 'nenhuma'}")
    if ignoradas:
        print(f"  {len(ignoradas)} linhas sem marcador anexadas ao dispositivo anterior (ex.: {ignoradas[:3]})")
    if tem_acento_perdido:
        print(
            f"\n[AVISO] {n_fffd} caracteres de substituição (\\ufffd) no arquivo: os acentos "
            "FORAM PERDIDOS na gravação do HTML e não podem ser recuperados.\n"
            "        Baixe novamente a página pelo script (passe a URL em vez do arquivo) ou "
            "salve o arquivo original sem reconverter a codificação."
        )


def gravar_jsonl(cols: dict, pasta: str):
    out = Path(pasta)
    out.mkdir(parents=True, exist_ok=True)
    for nome, docs in cols.items():
        with open(out / f"{nome}.jsonl", "w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"JSON Lines gravados em {out.resolve()}")


def salvar_mongo(db, cols: dict, lei_id: str):
    """Regrava a lei no banco (idempotente: apaga a versão anterior desta lei)."""
    from pymongo import ReplaceOne

    db["artigos"].delete_many({"lei_id": lei_id})
    db["dispositivos"].delete_many({"lei_id": lei_id})
    for nome, docs in cols.items():
        if docs:
            db[nome].bulk_write([ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs], ordered=False)
    db["artigos"].create_index([("lei_id", 1), ("numero", 1)])
    db["artigos"].create_index("vigente")
    db["dispositivos"].create_index([("lei_id", 1), ("artigo_id", 1)])
    db["dispositivos"].create_index([("tipo", 1), ("vigente", 1)])
    print({n: db[n].count_documents({}) for n in cols})


# --------------------------------------------------------------------------
# Funções de Interface do Módulo / Pipeline de Ingestão (API Pública)
# --------------------------------------------------------------------------
def baixar_legislacao(entrada: str) -> tuple[bytes, str]:
    """
    Obtém os bytes brutos da legislação informada (URL HTTP/HTTPS ou arquivo local).
    Retorna tupla (bytes_brutos, origem).
    """
    return obter_bytes(entrada)


def salvar_bruto(conteudo: bytes, caminho_destino: str | Path) -> Path:
    """
    Salva os bytes brutos da legislação em disco no caminho de destino especificado.
    Cria diretórios pais automaticamente se necessário.
    """
    p = Path(caminho_destino)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(conteudo)
    return p


def extrair_metadados(html: str, origem: str = "") -> dict:
    """
    Extrai metadados básicos (título da lei, ementa e origem) a partir do HTML.
    Complementa informações a partir da tag <title> caso não detectadas nos parágrafos.
    """
    meta, _, _ = parsear(html)
    if not meta.get("titulo"):
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            meta["titulo"] = limpar(title_tag.get_text(strip=True))
    if origem:
        meta["origem"] = origem
    return meta


def extrair_estrutura(html: str) -> list[dict]:
    """
    Extrai a árvore estrutural e aninhada de artigos da lei a partir do HTML.
    """
    _, artigos, _ = parsear(html)
    return artigos


def extrair_dispositivos(html: str, lei_id: str = "cc2002", lei_nome: str = "Código Civil") -> list[dict]:
    """
    Extrai a lista tabular/plana de dispositivos (artigos, parágrafos, incisos, alíneas)
    a partir do HTML da lei, pronta para chunking, embedding ou gravação no MongoDB.
    """
    meta, artigos, _ = parsear(html)
    if not artigos:
        return []
    cols = montar_colecoes(
        lei_id=lei_id,
        lei_nome=lei_nome,
        meta=meta,
        artigos=artigos,
        origem="",
        sha256="",
        tem_acento_perdido=False,
    )
    return cols.get("dispositivos", [])


# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", help="caminho do .html OU URL da página no Planalto")
    ap.add_argument("--lei-id", default="cc2002", help="identificador curto da lei (padrão: cc2002)")
    ap.add_argument("--lei-nome", default="Código Civil", help="nome usado nas citações")
    ap.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    ap.add_argument("--db", default="rag_juridico", help="nome do banco")
    ap.add_argument("--sem-mongo", action="store_true", help="não grava no MongoDB")
    ap.add_argument("--saida-jsonl", help="pasta para exportar JSON Lines (opcional)")
    ap.add_argument("--so-vigentes", action="store_true",
                    help="descarta redações anteriores e dispositivos revogados")
    args = ap.parse_args(argv)

    raw, origem = obter_bytes(args.entrada)
    html = decodificar(raw)
    n_fffd = html.count(FFFD)
    meta, artigos, ignoradas = parsear(html)
    if not artigos:
        sys.exit("Nenhum artigo encontrado: o HTML não tem o formato esperado.")

    if args.so_vigentes:
        def filtrar(lista):
            return [x for x in lista if x["vigente"]]
        artigos = filtrar(artigos)
        for a in artigos:
            a["incisos"] = filtrar(a["incisos"])
            for i in a["incisos"]:
                i["alineas"] = filtrar(i["alineas"])
            a["paragrafos"] = filtrar(a["paragrafos"])
            for p in a["paragrafos"]:
                p["incisos"] = filtrar(p["incisos"])
                for i in p["incisos"]:
                    i["alineas"] = filtrar(i["alineas"])

    cols = montar_colecoes(args.lei_id, args.lei_nome, meta, artigos, origem,
                           hashlib.sha256(raw).hexdigest(), n_fffd > 0)
    relatorio(cols, ignoradas, n_fffd > 0, n_fffd)

    if args.saida_jsonl:
        gravar_jsonl(cols, args.saida_jsonl)
    if not args.sem_mongo:
        from pymongo import MongoClient

        cliente = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000)
        cliente.admin.command("ping")  # falha cedo se o servidor não estiver no ar
        salvar_mongo(cliente[args.db], cols, args.lei_id)


if __name__ == "__main__":
    main()
