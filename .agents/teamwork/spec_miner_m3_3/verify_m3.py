#!/usr/bin/env python3
"""
Script Executável de Verificação e Aceitação: Milestone 3 (JudAI).
================================================================
Valida de ponta a ponta todos os requisitos, contratos de interface e
critérios de aceitação para o Milestone 3 (Scraper e Modelos Placeholders):

1. Estrutura de Arquivos e Pacotes (src/scraper e src/models)
2. Remoção Comprovada dos Arquivos Legados da Raiz (ingestao_lei.py e carregar_mongo.py)
3. Importabilidade Modular e Resiliência
4. Funções Essenciais do Parser de Legislação (ingestao_lei.py)
5. Parsing Funcional de Fragmento HTML Real do Planalto
6. Configuração e Variáveis de Ambiente do Scraper (carregar_mongo.py)
7. Execução CLI como Módulo (`python -m src.scraper.carregar_mongo --help`)
8. Isolamento, Velocidade (<1.0s) e Ausência de Dependências Pesadas de ML
9. Contratos, Assinaturas e Exceções de BM25Search (fit, search)
10. Contratos, Assinaturas e Exceções de BERTSearch (encode, search, model_name)
11. Execução dos Testes Pytest Oficiais (Tiers 1 a 4)

Uso:
    python verify_m3.py
    python verify_m3.py --verbose
    python verify_m3.py --skip-pytest
"""
from __future__ import annotations

import os
import re
import sys
import time
import inspect
import argparse
import subprocess
from pathlib import Path
from typing import Callable, Any

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
        self.warnings: list[str] = []
        self.start_time = time.perf_counter()

    def check(self, name: str, condition: bool, error_msg: str = ""):
        if condition:
            self.passed.append(name)
            if self.verbose:
                print(f"  [PASS] {name}")
        else:
            self.failed.append((name, error_msg))
            print(f"  [FAIL] {name}: {error_msg}")

    def warn(self, name: str, msg: str):
        self.warnings.append(f"{name}: {msg}")
        print(f"  [WARN] {name}: {msg}")

    def print_summary(self) -> int:
        elapsed = time.perf_counter() - self.start_time
        total = len(self.passed) + len(self.failed)
        print("\n" + "=" * 70)
        print(" RESUMO DA VERIFICAÇÃO DO MILESTONE 3 (JudAI)")
        print(f" Raiz do projeto: {ROOT_DIR}")
        print(f" Duração: {elapsed:.2f}s")
        print(f" Total de Validações: {total}")
        print(f" Sucessos: {len(self.passed)}")
        print(f" Falhas: {len(self.failed)}")
        print(f" Avisos: {len(self.warnings)}")
        print("=" * 70)

        if self.failed:
            print("\nITENS COM FALHA:")
            for idx, (name, err) in enumerate(self.failed, 1):
                print(f"  {idx}. {name} -> {err}")
            print("\nSTATUS: REPROVADO (Consulte spec_m3_validation.md para orientações)")
            return 1
        else:
            print("\nTODOS OS CRITÉRIOS DO MILESTONE 3 FORAM ATENDIDOS COM SUCESSO!")
            print("STATUS: APROVADO")
            return 0


def verify_file_structure(report: VerificationReport):
    print("\n[1/10] Verificando estrutura de arquivos e pacotes...")
    scraper_dir = ROOT_DIR / "src" / "scraper"
    models_dir = ROOT_DIR / "src" / "models"

    report.check(
        "Pacote src/scraper existe",
        scraper_dir.exists() and scraper_dir.is_dir(),
        f"Diretório {scraper_dir} não encontrado."
    )
    report.check(
        "src/scraper/__init__.py existe",
        (scraper_dir / "__init__.py").exists(),
        "src/scraper/__init__.py não encontrado."
    )
    report.check(
        "src/scraper/ingestao_lei.py existe",
        (scraper_dir / "ingestao_lei.py").exists(),
        "Arquivo src/scraper/ingestao_lei.py não encontrado (migração pendente)."
    )
    report.check(
        "src/scraper/carregar_mongo.py existe",
        (scraper_dir / "carregar_mongo.py").exists(),
        "Arquivo src/scraper/carregar_mongo.py não encontrado (migração pendente)."
    )
    report.check(
        "Pacote src/models existe",
        models_dir.exists() and models_dir.is_dir(),
        f"Diretório {models_dir} não encontrado."
    )
    report.check(
        "src/models/__init__.py existe",
        (models_dir / "__init__.py").exists(),
        "src/models/__init__.py não encontrado."
    )
    report.check(
        "src/models/bm25_search.py existe",
        (models_dir / "bm25_search.py").exists(),
        "Arquivo src/models/bm25_search.py não encontrado."
    )
    report.check(
        "src/models/bert_search.py existe",
        (models_dir / "bert_search.py").exists(),
        "Arquivo src/models/bert_search.py não encontrado."
    )


def verify_root_file_removal(report: VerificationReport):
    print("\n[2/10] Verificando remoção de scripts legados da raiz...")
    root_ingestao = ROOT_DIR / "ingestao_lei.py"
    root_carregar = ROOT_DIR / "carregar_mongo.py"

    report.check(
        "ingestao_lei.py removido da raiz",
        not root_ingestao.exists(),
        f"Arquivo legado 'ingestao_lei.py' ainda existe na raiz ({root_ingestao}). Deve ser removido após migração."
    )
    report.check(
        "carregar_mongo.py removido da raiz",
        not root_carregar.exists(),
        f"Arquivo legado 'carregar_mongo.py' ainda existe na raiz ({root_carregar}). Deve ser removido após migração."
    )


def verify_scraper_imports_and_cli(report: VerificationReport):
    print("\n[3/10] Verificando imports do scraper e invocação CLI...")
    # Import ingestao_lei
    try:
        import src.scraper.ingestao_lei as parser
        report.check("Import src.scraper.ingestao_lei", parser is not None, "Objeto de módulo é None")
    except Exception as e:
        report.check("Import src.scraper.ingestao_lei", False, str(e))

    # Import carregar_mongo
    try:
        import src.scraper.carregar_mongo as loader
        report.check("Import src.scraper.carregar_mongo", loader is not None, "Objeto de módulo é None")
    except Exception as e:
        report.check("Import src.scraper.carregar_mongo", False, str(e))

    # Execução CLI como módulo
    cmd = [sys.executable, "-m", "src.scraper.carregar_mongo", "--help"]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, timeout=10)
        report.check(
            "CLI `python -m src.scraper.carregar_mongo --help` sem ModuleNotFoundError",
            "ModuleNotFoundError" not in proc.stderr,
            f"Erro de módulo no stderr: {proc.stderr}"
        )
        report.check(
            "CLI `python -m src.scraper.carregar_mongo --help` código de retorno 0",
            proc.returncode == 0,
            f"Código de retorno inesperado: {proc.returncode}, stderr: {proc.stderr}"
        )
    except Exception as e:
        report.check("CLI `python -m src.scraper.carregar_mongo --help`", False, str(e))


def verify_scraper_parser_functions(report: VerificationReport):
    print("\n[4/10] Verificando funções do parser e compatibilidade (ingestao_lei)...")
    try:
        from src.scraper import ingestao_lei
    except ImportError as e:
        report.check("Módulo src.scraper.ingestao_lei acessível", False, str(e))
        return

    required_functions = [
        "baixar_legislacao",
        "salvar_bruto",
        "extrair_metadados",
        "extrair_estrutura",
        "extrair_dispositivos",
    ]
    for fn in required_functions:
        exists = hasattr(ingestao_lei, fn)
        is_call = callable(getattr(ingestao_lei, fn, None))
        report.check(
            f"Função essencial '{fn}' exposta e chamável",
            exists and is_call,
            f"Função '{fn}' ausente ou não chamável em src.scraper.ingestao_lei"
        )

    # Verifica funções originais essenciais do parser
    original_functions = [
        "obter_bytes",
        "decodificar",
        "parsear",
        "montar_colecoes",
        "relatorio",
        "salvar_mongo",
    ]
    for fn in original_functions:
        exists = hasattr(ingestao_lei, fn)
        is_call = callable(getattr(ingestao_lei, fn, None))
        report.check(
            f"Função original preservada '{fn}'",
            exists and is_call,
            f"Função histórica '{fn}' ausente em src.scraper.ingestao_lei"
        )


def verify_scraper_parsing_real_html(report: VerificationReport):
    print("\n[5/10] Verificando parsing de fragmento HTML real de legislação...")
    try:
        from src.scraper import ingestao_lei
    except ImportError:
        report.check("Parsing de HTML de teste", False, "Módulo ingestao_lei não disponível")
        return

    html_snippet = """
    <!DOCTYPE html>
    <html>
    <head><title>LEI Nº 10.406, DE 10 DE JANEIRO DE 2002</title></head>
    <body>
        <p class="ementa">Institui o Código Civil.</p>
        <p><strong>O PRESIDENTE DA REPÚBLICA</strong> Faço saber que o Congresso Nacional decreta e eu sanciono a seguinte Lei:</p>
        <p id="art1">Art. 1<u>o</u> Toda pessoa é capaz de direitos e deveres na ordem civil.</p>
        <p id="art2">Art. 2<u>o</u> A personalidade civil da pessoa começa do nascimento com vida; mas a lei põe a salvo, desde a concepção, os direitos do nascituro.</p>
        <p id="art3">Art. 3<u>o</u> São absolutamente incapazes de exercer pessoalmente os atos da vida civil os menores de 16 (dezesseis) anos.</p>
        <p>§ 1<u>o</u> (Revogado pela Lei nº 13.146, de 2015)</p>
    </body>
    </html>
    """
    try:
        meta = ingestao_lei.extrair_metadados(html_snippet, "teste_snippet.html")
        report.check(
            "extrair_metadados retorna dict",
            isinstance(meta, dict),
            f"Retorno esperado dict, obtido {type(meta)}"
        )
        report.check(
            "extrair_metadados extrai título ou ementa",
            bool(meta.get("titulo") or meta.get("ementa")),
            f"Metadados vazios: {meta}"
        )
    except Exception as e:
        report.check("extrair_metadados executa sem erros", False, str(e))

    try:
        dispositivos = ingestao_lei.extrair_dispositivos(html_snippet)
        report.check(
            "extrair_dispositivos retorna list",
            isinstance(dispositivos, list),
            f"Retorno esperado list, obtido {type(dispositivos)}"
        )
        report.check(
            "extrair_dispositivos contém artigos extraídos (> 0)",
            len(dispositivos) > 0,
            f"Nenhum dispositivo extraído do HTML de teste"
        )
    except Exception as e:
        report.check("extrair_dispositivos executa sem erros", False, str(e))


def verify_scraper_env_and_db_alignment(report: VerificationReport):
    print("\n[6/10] Verificando configuração por ambiente e alinhamento com DB...")
    carregar_file = ROOT_DIR / "src" / "scraper" / "carregar_mongo.py"
    if not carregar_file.exists():
        report.check("Arquivo carregar_mongo.py presente para análise", False, "Arquivo não existe")
        return

    content = carregar_file.read_text(encoding="utf-8")
    report.check(
        "carregar_mongo.py contém referência a 'MONGO_URI'",
        "MONGO_URI" in content,
        "Referência a 'MONGO_URI' ausente no código"
    )
    report.check(
        "carregar_mongo.py contém referência a 'MONGO_DB_NAME'",
        "MONGO_DB_NAME" in content,
        "Referência a 'MONGO_DB_NAME' ausente no código"
    )
    report.check(
        "carregar_mongo.py usa os.getenv ou os.environ",
        "getenv" in content or "environ" in content,
        "Chamada a getenv ou environ não encontrada"
    )

    try:
        import src.scraper.carregar_mongo as scraper_mod
        report.check(
            "Default de MONGO_URI no scraper é 'mongodb://localhost:27017'",
            getattr(scraper_mod, "MONGO_URI", None) == "mongodb://localhost:27017",
            f"Obtido: {getattr(scraper_mod, 'MONGO_URI', None)}"
        )
        report.check(
            "Default de MONGO_DB_NAME no scraper é 'rag_juridico'",
            getattr(scraper_mod, "MONGO_DB_NAME", None) == "rag_juridico",
            f"Obtido: {getattr(scraper_mod, 'MONGO_DB_NAME', None)}"
        )
    except Exception as e:
        report.check("Inspeção de variáveis do módulo carregar_mongo", False, str(e))


def verify_models_lightweight_import(report: VerificationReport):
    print("\n[7/10] Verificando velocidade de import e isolamento de ML pesada...")
    # Registra módulos carregados antes do import
    pre_modules = set(sys.modules.keys())

    start = time.perf_counter()
    try:
        import src.models.bm25_search as bm25_mod
        import src.models.bert_search as bert_mod
        elapsed = time.perf_counter() - start
        report.check(
            "Import de src.models.* é rápido (< 1.0s)",
            elapsed < 1.0,
            f"Import levou {elapsed:.3f}s (limite máximo é 1.0s)"
        )
    except Exception as e:
        report.check("Import de src.models.* sem erros", False, str(e))
        return

    # Garante que bibliotecas pesadas de ML não foram importadas estaticamente
    post_modules = set(sys.modules.keys())
    new_modules = post_modules - pre_modules
    forbidden = ["torch", "sentence_transformers", "transformers"]
    for pkg in forbidden:
        loaded = any(m == pkg or m.startswith(f"{pkg}.") for m in new_modules)
        report.check(
            f"Biblioteca pesada '{pkg}' NÃO carregada estaticamente no import",
            not loaded,
            f"Pacote '{pkg}' foi importado no escopo global dos módulos de modelo!"
        )


def verify_bm25_search_placeholder(report: VerificationReport):
    print("\n[8/10] Verificando especificações de BM25Search...")
    try:
        import src.models.bm25_search as bm25_mod
    except ImportError as e:
        report.check("Módulo src.models.bm25_search acessível", False, str(e))
        return

    report.check(
        "Classe 'BM25Search' existe em bm25_search",
        hasattr(bm25_mod, "BM25Search"),
        "Classe BM25Search ausente"
    )

    BM25Search = getattr(bm25_mod, "BM25Search", None)
    if not BM25Search:
        return

    # Docstrings
    mod_doc = inspect.getdoc(bm25_mod) or ""
    class_doc = inspect.getdoc(BM25Search) or ""
    full_doc = f"{mod_doc} {class_doc}".lower()

    report.check(
        "Docstrings mencionam 'bm25'",
        "bm25" in full_doc,
        "Docstring deve detalhar o papel do BM25"
    )
    report.check(
        "Docstrings indicam que é placeholder / não implementado",
        any(w in full_doc for w in ["placeholder", "não implementad", "not implemented"]),
        "Docstring deve indicar expressamente status de placeholder"
    )

    # Assinatura de search
    search_sig = inspect.signature(BM25Search.search)
    report.check(
        "BM25Search.search possui parâmetro 'query'",
        "query" in search_sig.parameters,
        f"Parâmetros encontrados: {list(search_sig.parameters.keys())}"
    )

    # Comportamento de métodos (NotImplementedError)
    bm25 = BM25Search()
    try:
        bm25.fit([{"id": 1, "texto": "artigo 1"}])
        report.check("BM25Search.fit lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BM25Search.fit lança NotImplementedError", True)
    except Exception as e:
        report.check("BM25Search.fit lança NotImplementedError", False, f"Lançou {type(e)}: {e}")

    try:
        bm25.search("prescrição", top_k=5)
        report.check("BM25Search.search lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BM25Search.search lança NotImplementedError", True)
    except Exception as e:
        report.check("BM25Search.search lança NotImplementedError", False, f"Lançou {type(e)}: {e}")

    # Casos de borda (Tier 2)
    try:
        bm25.search("", top_k=0)
        report.check("BM25Search.search('', top_k=0) lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BM25Search.search('', top_k=0) lança NotImplementedError", True)
    except Exception as e:
        report.check("BM25Search.search('', top_k=0) lança NotImplementedError", False, f"Lançou {type(e)}")

    try:
        bm25.fit([])
        report.check("BM25Search.fit([]) corpus vazio lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BM25Search.fit([]) corpus vazio lança NotImplementedError", True)
    except Exception as e:
        report.check("BM25Search.fit([]) corpus vazio lança NotImplementedError", False, f"Lançou {type(e)}")


def verify_bert_search_placeholder(report: VerificationReport):
    print("\n[9/10] Verificando especificações de BERTSearch...")
    try:
        import src.models.bert_search as bert_mod
    except ImportError as e:
        report.check("Módulo src.models.bert_search acessível", False, str(e))
        return

    report.check(
        "Classe 'BERTSearch' existe em bert_search",
        hasattr(bert_mod, "BERTSearch"),
        "Classe BERTSearch ausente"
    )

    BERTSearch = getattr(bert_mod, "BERTSearch", None)
    if not BERTSearch:
        return

    # Docstrings
    mod_doc = inspect.getdoc(bert_mod) or ""
    class_doc = inspect.getdoc(BERTSearch) or ""
    full_doc = f"{mod_doc} {class_doc}".lower()

    report.check(
        "Docstrings mencionam 'bert', 'embedding' ou 'semântic'",
        any(w in full_doc for w in ["bert", "embedding", "semântic"]),
        "Docstring deve detalhar o papel do BERT / busca semântica densa"
    )
    report.check(
        "Docstrings indicam que é placeholder / não implementado",
        any(w in full_doc for w in ["placeholder", "não implementad", "not implemented"]),
        "Docstring deve indicar expressamente status de placeholder"
    )

    # Assinatura de search
    search_sig = inspect.signature(BERTSearch.search)
    report.check(
        "BERTSearch.search possui parâmetro 'query'",
        "query" in search_sig.parameters,
        f"Parâmetros encontrados: {list(search_sig.parameters.keys())}"
    )

    # Construtor com model_name customizado
    custom_model = "neuralmind/bert-base-portuguese-cased"
    try:
        bert_custom = BERTSearch(model_name=custom_model)
        report.check(
            "BERTSearch aceita model_name customizado e armazena em .model_name",
            getattr(bert_custom, "model_name", None) == custom_model,
            f"Obtido: {getattr(bert_custom, 'model_name', None)}"
        )
    except Exception as e:
        report.check("BERTSearch construtor com model_name customizado", False, str(e))

    # Comportamento de métodos (NotImplementedError)
    bert = BERTSearch()
    try:
        bert.encode(["texto de dispositivo legal"])
        report.check("BERTSearch.encode lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BERTSearch.encode lança NotImplementedError", True)
    except Exception as e:
        report.check("BERTSearch.encode lança NotImplementedError", False, f"Lançou {type(e)}: {e}")

    try:
        bert.search("reparação civil", top_k=5)
        report.check("BERTSearch.search lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BERTSearch.search lança NotImplementedError", True)
    except Exception as e:
        report.check("BERTSearch.search lança NotImplementedError", False, f"Lançou {type(e)}: {e}")

    # Casos de borda (Tier 2)
    try:
        bert.search("", top_k=0)
        report.check("BERTSearch.search('', top_k=0) lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BERTSearch.search('', top_k=0) lança NotImplementedError", True)
    except Exception as e:
        report.check("BERTSearch.search('', top_k=0) lança NotImplementedError", False, f"Lançou {type(e)}")

    try:
        bert.encode([])
        report.check("BERTSearch.encode([]) lista vazia lança NotImplementedError", False, "Não lançou exceção")
    except NotImplementedError:
        report.check("BERTSearch.encode([]) lista vazia lança NotImplementedError", True)
    except Exception as e:
        report.check("BERTSearch.encode([]) lista vazia lança NotImplementedError", False, f"Lançou {type(e)}")


def verify_official_pytest_classes(report: VerificationReport, skip_pytest: bool = False):
    print("\n[10/10] Executando suíte oficial do pytest para Milestone 3...")
    if skip_pytest:
        report.warn("Pytest", "Execução do pytest ignorada (--skip-pytest)")
        return

    try:
        import pytest
    except ImportError:
        report.warn("Pytest", "pytest não instalado no ambiente; pulando execução direta do pytest")
        return

    # Executa classes de teste do Tier 1 correspondentes ao M3
    test_file = ROOT_DIR / "tests" / "test_tier1_feature_coverage.py"
    if not test_file.exists():
        report.check("Arquivo test_tier1_feature_coverage.py presente", False, "Arquivo não encontrado")
        return

    targets = [
        f"{test_file}::TestMLModelPlaceholders",
        f"{test_file}::TestScraperMigrationFeature",
    ]
    for target in targets:
        class_name = target.split("::")[-1]
        exit_code = pytest.main(["-q", target])
        report.check(
            f"Suíte pytest {class_name}",
            exit_code == 0,
            f"pytest saiu com código {exit_code}"
        )


def main():
    parser = argparse.ArgumentParser(description="JudAI Milestone 3 Verification Suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Exibe detalhes de cada asserção")
    parser.add_argument("--skip-pytest", action="store_true", help="Pula execução da suíte do pytest")
    args = parser.parse_args()

    print("=" * 70)
    print(" Executando Validador Oficial: Milestone 3 (Scraper e Modelos)")
    print(f" Raiz do Projeto: {ROOT_DIR}")
    print("=" * 70)

    report = VerificationReport(verbose=args.verbose)

    verify_file_structure(report)
    verify_root_file_removal(report)
    verify_scraper_imports_and_cli(report)
    verify_scraper_parser_functions(report)
    verify_scraper_parsing_real_html(report)
    verify_scraper_env_and_db_alignment(report)
    verify_models_lightweight_import(report)
    verify_bm25_search_placeholder(report)
    verify_bert_search_placeholder(report)
    verify_official_pytest_classes(report, skip_pytest=args.skip_pytest)

    exit_code = report.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
