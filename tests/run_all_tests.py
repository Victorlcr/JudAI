#!/usr/bin/env python3
"""
Test Runner Executável e Independente do JudAI.
==============================================
Permite executar todas as suítes de teste (Tiers 1 a 4) de forma unificada,
com suporte tanto ao Pytest nativo quanto a um runner autônomo baseado na
biblioteca padrão do Python.

Uso:
    python tests/run_all_tests.py
    python tests/run_all_tests.py --tier 1
    python tests/run_all_tests.py --tier 2
    python tests/run_all_tests.py --standalone
    python tests/run_all_tests.py -v
"""
from __future__ import annotations

import os
import sys
import time
import argparse
import unittest
import importlib
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TIER_FILES = {
    1: TESTS_DIR / "test_tier1_feature_coverage.py",
    2: TESTS_DIR / "test_tier2_boundary_corner.py",
    3: TESTS_DIR / "test_tier3_cross_feature.py",
    4: TESTS_DIR / "test_tier4_real_world.py",
}


def run_with_pytest(tier: int | None = None, verbose: bool = False) -> int:
    """Executa testes utilizando pytest."""
    try:
        import pytest
    except ImportError:
        print("[!] pytest não está instalado no ambiente. Usando runner autônomo...")
        return run_standalone(tier=tier, verbose=verbose)

    args = ["-q"]
    if verbose:
        args = ["-v"]

    if tier:
        target_file = TIER_FILES.get(tier)
        if not target_file or not target_file.exists():
            print(f"[ERRO] Arquivo de teste para Tier {tier} não encontrado: {target_file}")
            return 1
        args.append(str(target_file))
    else:
        for t, f in TIER_FILES.items():
            if f.exists():
                args.append(str(f))

    print("=" * 70)
    print(" Executando Suíte de Testes do JudAI via Pytest")
    print(f" Raiz do projeto: {ROOT_DIR}")
    print(f" Alvo: {'Tier ' + str(tier) if tier else 'Todos os Tiers (1 a 4)'}")
    print("=" * 70)

    exit_code = pytest.main(args)
    return int(exit_code)


def run_standalone(tier: int | None = None, verbose: bool = False) -> int:
    """
    Runner autônomo que descobre classes de teste ou funções de teste
    e as executa usando unittest ou inspeção direta.
    """
    print("=" * 70)
    print(" Executando Suíte de Testes do JudAI (Runner Autônomo)")
    print(f" Raiz do projeto: {ROOT_DIR}")
    print(f" Alvo: {'Tier ' + str(tier) if tier else 'Todos os Tiers (1 a 4)'}")
    print("=" * 70)

    targets = [TIER_FILES[tier]] if tier else [f for f in TIER_FILES.values() if f.exists()]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Como os testes foram escritos com classes padrão compatíveis com pytest e unittest,
    # carregamos via import dinâmico
    for file_path in targets:
        module_name = f"tests.{file_path.stem}"
        try:
            mod = importlib.import_module(module_name)
            # Descobre classes no módulo
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and (attr_name.startswith("Test") or issubclass(attr, unittest.TestCase)):
                    # Se não herda de unittest.TestCase, cria wrapper dinâmico para execução autônoma
                    if not issubclass(attr, unittest.TestCase):
                        # Cria subclasse de TestCase dinâmica com os métodos de teste
                        methods = [m for m in dir(attr) if m.startswith("test_")]
                        test_case_class = type(attr_name, (unittest.TestCase,), {})
                        for m in methods:
                            meth = getattr(attr, m)
                            # Wrap de fixture simples
                            setattr(test_case_class, m, lambda self, fn=meth, cls_inst=attr(): fn(cls_inst))
                        suite.addTests(loader.loadTestsFromTestCase(test_case_class))
                    else:
                        suite.addTests(loader.loadTestsFromTestCase(attr))
        except Exception as e:
            print(f"[!] Falha ao carregar módulo {module_name}: {e}")

    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    start_time = time.perf_counter()
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 70)
    print(" RESUMO DA EXECUÇÃO:")
    print(f" Total de Testes Executados: {result.testsRun}")
    print(f" Sucessos: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f" Falhas: {len(result.failures)}")
    print(f" Erros: {len(result.errors)}")
    print(f" Tempo total: {elapsed:.2f} segundos")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="JudAI Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], default=None, help="Executar apenas um Tier específico (1, 2, 3 ou 4)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Modo verboso com detalhes de cada teste")
    parser.add_argument("--standalone", action="store_true", help="Forçar o uso do runner autônomo sem pytest")
    args = parser.parse_args()

    if args.standalone:
        return run_standalone(tier=args.tier, verbose=args.verbose)
    else:
        return run_with_pytest(tier=args.tier, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
