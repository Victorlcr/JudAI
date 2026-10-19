#!/usr/bin/env python3
"""
Script Executável de Verificação Rápida: Milestone 3 - Rodada 2 (JudAI).
========================================================================
Valida rigorosamente:
1. Correção estática e dinâmica de RE_PAR e ORD em src/scraper/ingestao_lei.py
2. Rejeição de linhas numéricas isoladas sem símbolo de parágrafo (Negative Tests)
3. Casamento e captura correta de parágrafos normais com '§' (Regression Tests)
4. Casamento e captura correta de parágrafos danificados com '\ufffd' (Corrupted Tests)
5. Parsing completo de HTML com itens numéricos e parágrafos danificados
6. Remoção comprovada dos arquivos legados da raiz (ingestao_lei.py e carregar_mongo.py)
7. Asserção estrita em tests/test_tier1_feature_coverage.py

Uso:
    python verify_m3_r2.py
    python verify_m3_r2.py --verbose
"""
from __future__ import annotations

import os
import re
import sys
import time
import argparse
from pathlib import Path

# Localização da raiz do projeto JudAI
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class VerificationReport:
    """Acumula e formata resultados de checagem."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.start_time = time.perf_counter()

    def check(self, name: str, condition: bool, error_msg: str = ""):
        if condition:
            self.passed.append(name)
            if self.verbose:
                print(f"  [PASS] {name}")
        else:
            self.failed.append((name, error_msg))
            print(f"  [FAIL] {name}: {error_msg}")

    def print_summary(self) -> int:
        elapsed = time.perf_counter() - self.start_time
        total = len(self.passed) + len(self.failed)
        print("\n" + "=" * 70)
        print(" RESUMO DA VERIFICAÇÃO DO MILESTONE 3 - RODADA 2 (JudAI)")
        print(f" Raiz do projeto: {ROOT_DIR}")
        print(f" Duração: {elapsed:.2f}s")
        print(f" Total de Validações: {total}")
        print(f" Sucessos: {len(self.passed)}")
        print(f" Falhas: {len(self.failed)}")
        print("=" * 70)

        if self.failed:
            print("\nITENS COM FALHA:")
            for idx, (name, err) in enumerate(self.failed, 1):
                print(f"  {idx}. {name} -> {err}")
            print("\nSTATUS: REPROVADO (Consulte spec_m3_r2_validation.md para correções)")
            return 1
        else:
            print("\nTODOS OS CRITÉRIOS DA RODADA 2 FORAM ATENDIDOS COM SUCESSO!")
            print("STATUS: APROVADO")
            return 0


def verify_static_regex_patterns(report: VerificationReport):
    print("\n[1/6] Inspecionando código-fonte de src/scraper/ingestao_lei.py...")
    scraper_path = ROOT_DIR / "src" / "scraper" / "ingestao_lei.py"
    if not scraper_path.exists():
        report.check("Arquivo src/scraper/ingestao_lei.py existe", False, "Arquivo não encontrado")
        return

    content = scraper_path.read_text(encoding="utf-8")

    # Verifica ausência do ramo vazio em RE_PAR
    has_empty_branch = re.search(r"RE_PAR\s*=.*r[fF]?[\"']\^?\(\?:\§\|[\)\]]", content)
    report.check(
        "RE_PAR não contém ramo vazio '(?:§|)'",
        not bool(has_empty_branch) and "(?:§|)" not in content,
        "Detectado ramo vazio '(?:§|)' em RE_PAR que causa falsos positivos em números soltos!"
    )

    # Verifica presença de \ufffd em RE_PAR
    has_ufffd_in_re_par = bool(re.search(r"RE_PAR\s*=.*(?:\\ufffd|\ufffd)", content))
    report.check(
        "RE_PAR contém escape ou caractere '\\ufffd'",
        has_ufffd_in_re_par,
        "RE_PAR deve conter '\\ufffd' para reconhecer parágrafos danificados do Planalto."
    )

    # Verifica presença de \ufffd em ORD
    has_ufffd_in_ord = bool(re.search(r"ORD\s*=.*(?:\\ufffd|\ufffd)", content))
    report.check(
        "ORD contém escape ou caractere '\\ufffd'",
        has_ufffd_in_ord,
        "ORD deve conter '\\ufffd' para tolerar indicadores ordinais corrompidos."
    )


def verify_regex_negative_cases(report: VerificationReport):
    print("\n[2/6] Testando rejeição de numerais e linhas sem parágrafo (Negative Tests)...")
    try:
        from src.scraper import ingestao_lei
    except ImportError as e:
        report.check("Import src.scraper.ingestao_lei", False, str(e))
        return

    re_par = getattr(ingestao_lei, "RE_PAR", None)
    if re_par is None:
        report.check("Atributo RE_PAR em ingestao_lei", False, "RE_PAR não encontrado")
        return

    negative_cases = [
        "1. Princípio fundamental",
        "1 - Primeiro requisito",
        "2. Erradicação da pobreza",
        "3. Garantia do desenvolvimento",
        "10 dias a contar da citação",
        "2002. Disposições transitórias",
        "100. Valor estipulado",
        "10.406/2002",
        "Art. 1º Caput do artigo",
        "I - Inciso primeiro",
        "a) Alínea textual",
        "Parágrafo único. Dispositivo único",
        "",
        "   ",
        "\ufffd Texto sem numeral",
        "Nota explicativa (Redação dada pela Lei)",
    ]

    for item in negative_cases:
        m = re_par.match(item)
        report.check(
            f"RE_PAR rejeita {item!r}",
            m is None,
            f"RE_PAR casou indevidamente com {item!r} (gerou falso positivo de parágrafo)!"
        )


def verify_regex_standard_cases(report: VerificationReport):
    print("\n[3/6] Testando casamento de parágrafos padrão '§' (Regression Tests)...")
    try:
        from src.scraper import ingestao_lei
    except ImportError as e:
        report.check("Import src.scraper.ingestao_lei", False, str(e))
        return

    re_par = getattr(ingestao_lei, "RE_PAR", None)
    if re_par is None:
        report.check("Atributo RE_PAR em ingestao_lei", False, "RE_PAR não encontrado")
        return

    standard_cases = [
        ("§ 1º Texto padrão do parágrafo", "1", None, "Texto padrão do parágrafo"),
        ("§ 2° Texto com símbolo de grau", "2", None, "Texto com símbolo de grau"),
        ("§ 3ª Texto com ordinal feminino", "3", None, "Texto com ordinal feminino"),
        ("§ 4o Texto com letra 'o' minúscula", "4", None, "Texto com letra 'o' minúscula"),
        ("§ 5º-A Texto com sufixo alfabético", "5", "A", "Texto com sufixo alfabético"),
        ("§ 10. Texto com ponto após numeral", "10", None, "Texto com ponto após numeral"),
        ("§ 100 - Texto com traço separador", "100", None, "Texto com traço separador"),
        ("§1º Texto colado sem espaço", "1", None, "Texto colado sem espaço"),
        ("§ 1.368-A Condomínio em multipropriedade", "1.368", "A", "Condomínio em multipropriedade"),
    ]

    for text, exp_num, exp_suf, exp_corpo in standard_cases:
        m = re_par.match(text)
        report.check(f"RE_PAR casa {text!r}", m is not None, f"Falha no casamento de {text!r}")
        if m is not None:
            report.check(
                f"Número correto em {text!r} ({exp_num})",
                m.group(1) == exp_num,
                f"Obtido {m.group(1)!r}, esperado {exp_num!r}"
            )
            report.check(
                f"Sufixo correto em {text!r} ({exp_suf})",
                m.group(2) == exp_suf,
                f"Obtido {m.group(2)!r}, esperado {exp_suf!r}"
            )
            report.check(
                f"Corpo correto em {text!r}",
                m.group(3) == exp_corpo,
                f"Obtido {m.group(3)!r}, esperado {exp_corpo!r}"
            )


def verify_regex_corrupted_cases(report: VerificationReport):
    print("\n[4/6] Testando casamento de parágrafos danificados com '\\ufffd'...")
    try:
        from src.scraper import ingestao_lei
    except ImportError as e:
        report.check("Import src.scraper.ingestao_lei", False, str(e))
        return

    re_par = getattr(ingestao_lei, "RE_PAR", None)
    if re_par is None:
        report.check("Atributo RE_PAR em ingestao_lei", False, "RE_PAR não encontrado")
        return

    corrupted_cases = [
        ("\ufffd 1º Texto danificado", "1", None, "Texto danificado"),
        ("\ufffd 1\ufffd Texto duplamente danificado", "1", None, "Texto duplamente danificado"),
        ("\ufffd 2° Texto danificado com grau", "2", None, "Texto danificado com grau"),
        ("\ufffd 3ª Texto danificado feminino", "3", None, "Texto danificado feminino"),
        ("\ufffd 4o Texto danificado com o", "4", None, "Texto danificado com o"),
        ("\ufffd 5º-A Texto danificado com sufixo", "5", "A", "Texto danificado com sufixo"),
        ("\ufffd 10. Texto danificado dez", "10", None, "Texto danificado dez"),
        ("\ufffd1º Danificado sem espaço", "1", None, "Danificado sem espaço"),
    ]

    for text, exp_num, exp_suf, exp_corpo in corrupted_cases:
        m = re_par.match(text)
        report.check(f"RE_PAR casa danificado {text!r}", m is not None, f"Falha no casamento de {text!r}")
        if m is not None:
            report.check(
                f"Número correto em {text!r} ({exp_num})",
                m.group(1) == exp_num,
                f"Obtido {m.group(1)!r}, esperado {exp_num!r}"
            )
            report.check(
                f"Sufixo correto em {text!r} ({exp_suf})",
                m.group(2) == exp_suf,
                f"Obtido {m.group(2)!r}, esperado {exp_suf!r}"
            )
            report.check(
                f"Corpo correto em {text!r}",
                m.group(3) == exp_corpo,
                f"Obtido {m.group(3)!r}, esperado {exp_corpo!r}"
            )


def verify_parser_html_integration(report: VerificationReport):
    print("\n[5/6] Testando extração de dispositivos em fragmento HTML real...")
    try:
        from src.scraper import ingestao_lei
    except ImportError as e:
        report.check("Import src.scraper.ingestao_lei", False, str(e))
        return

    html_fragment = """
    <!DOCTYPE html>
    <html>
    <body>
        <p id="art1">Art. 1º São princípios da organização:</p>
        <p>1. Princípio da legalidade estrita;</p>
        <p>2. Princípio da impessoalidade administrativa;</p>
        <p>§ 1º O disposto neste artigo aplica-se a todos os entes federados.</p>
        <p>\ufffd 2º A regulamentação caberá ao Poder Executivo competente.</p>
    </body>
    </html>
    """

    try:
        dispositivos = ingestao_lei.extrair_dispositivos(html_fragment)
        report.check(
            "extrair_dispositivos executa sem erro",
            isinstance(dispositivos, list),
            f"Tipo retornado inválido: {type(dispositivos)}"
        )

        paragrafos = [d for d in dispositivos if d.get("tipo") == "paragrafo"]
        report.check(
            "Exatamente 2 parágrafos extraídos (itens numéricos 1 e 2 rejeitados)",
            len(paragrafos) == 2,
            f"Esperado 2 parágrafos, obtido {len(paragrafos)}. Detalhe: {[p.get('rotulo') for p in paragrafos]}"
        )

        # Verifica se algum parágrafo pegou indevidamente o item '1.'
        par_falso = [p for p in paragrafos if "legalidade estrita" in p.get("texto", "")]
        report.check(
            "Item numérico '1.' NÃO virou parágrafo",
            len(par_falso) == 0,
            "Item '1. Princípio da legalidade estrita;' foi indevidamente convertido em parágrafo!"
        )

        # Valida rótulos dos parágrafos legítimos
        rotulos = [p.get("rotulo") for p in paragrafos]
        report.check(
            "Parágrafo normal '§ 1º' extraído",
            any("1" in r for r in rotulos),
            f"Rótulo '§ 1º' não encontrado em: {rotulos}"
        )
        report.check(
            "Parágrafo danificado '\\ufffd 2º' extraído como '§ 2º'",
            any("2" in r for r in rotulos),
            f"Rótulo '§ 2º' não encontrado em: {rotulos}"
        )

    except Exception as e:
        report.check("extrair_dispositivos processa fragmento HTML", False, str(e))


def verify_root_file_removal_and_test(report: VerificationReport):
    print("\n[6/6] Verificando remoção de scripts legados da raiz e asserção em testes...")
    root_ingestao = ROOT_DIR / "ingestao_lei.py"
    root_carregar = ROOT_DIR / "carregar_mongo.py"

    report.check(
        "ingestao_lei.py não existe na raiz",
        not root_ingestao.exists(),
        f"Arquivo legado 'ingestao_lei.py' ainda existe na raiz ({root_ingestao}). Deve ser excluído."
    )
    report.check(
        "carregar_mongo.py não existe na raiz",
        not root_carregar.exists(),
        f"Arquivo legado 'carregar_mongo.py' ainda existe na raiz ({root_carregar}). Deve ser excluído."
    )

    # Verifica se os arquivos de destino existem em src/scraper/
    src_ingestao = ROOT_DIR / "src" / "scraper" / "ingestao_lei.py"
    src_carregar = ROOT_DIR / "src" / "scraper" / "carregar_mongo.py"
    report.check("src/scraper/ingestao_lei.py existe", src_ingestao.exists(), "src/scraper/ingestao_lei.py ausente!")
    report.check("src/scraper/carregar_mongo.py existe", src_carregar.exists(), "src/scraper/carregar_mongo.py ausente!")

    # Inspeciona tests/test_tier1_feature_coverage.py
    test_file = ROOT_DIR / "tests" / "test_tier1_feature_coverage.py"
    if test_file.exists():
        content = test_file.read_text(encoding="utf-8")
        # Procura pelo método test_scraper_no_scripts_left_in_root
        match = re.search(r"def test_scraper_no_scripts_left_in_root\(self\):.*?(?=\n    def |\Z)", content, re.S)
        if match:
            test_body = match.group(0)
            report.check(
                "test_scraper_no_scripts_left_in_root contém 'assert not root_ingestao.exists()'",
                "assert not root_ingestao.exists()" in test_body or "assert not (ROOT_DIR / \"ingestao_lei.py\").exists()" in test_body,
                "O teste de raiz em test_tier1_feature_coverage.py não possui asserção estrita para ingestao_lei.py!"
            )
            report.check(
                "test_scraper_no_scripts_left_in_root contém 'assert not root_carregar.exists()'",
                "assert not root_carregar.exists()" in test_body or "assert not (ROOT_DIR / \"carregar_mongo.py\").exists()" in test_body,
                "O teste de raiz em test_tier1_feature_coverage.py não possui asserção estrita para carregar_mongo.py!"
            )


def main():
    parser = argparse.ArgumentParser(description="Verificador Rápido Milestone 3 - Rodada 2")
    parser.add_argument("--verbose", action="store_true", help="Exibe detalhes de cada asserção executada")
    args = parser.parse_args()

    report = VerificationReport(verbose=args.verbose)
    verify_static_regex_patterns(report)
    verify_regex_negative_cases(report)
    verify_regex_standard_cases(report)
    verify_regex_corrupted_cases(report)
    verify_parser_html_integration(report)
    verify_root_file_removal_and_test(report)

    return report.print_summary()


if __name__ == "__main__":
    sys.exit(main())
