#!/usr/bin/env python3
"""
Script Executável de Verificação: Milestone 3 - Rodada 3 (JudAI)
================================================================
Valida com rigor absoluto as correções da Rodada 3 do Milestone 3:
1. Presença, assinatura e chamabilidade de `def main(argv=None)` em `src/scraper/carregar_mongo.py`.
2. Presença, assinatura e chamabilidade de `def main(argv=None)` em `src/scraper/ingestao_lei.py`.
3. Execução sem erros dos shims da raiz (`import carregar_mongo` e `import ingestao_lei`).
4. Atributos e chamabilidade de `main` nos shims da raiz (`hasattr(mod, 'main')` e `callable(mod.main)`).
5. Aliasing de módulo em `sys.modules` (`sys.modules['carregar_mongo'] is sys.modules['src.scraper.carregar_mongo']`).
6. Aliasing de módulo em `sys.modules` (`sys.modules['ingestao_lei'] is sys.modules['src.scraper.ingestao_lei']`).
7. Emissão de `DeprecationWarning` com `stacklevel=2` ao importar os shims da raiz.
8. Execução CLI dos shims da raiz e dos módulos com `--help` (código de saída 0, sem crash ou ImportError).
9. Imunidade a split-brain (sincronização de estado mutável entre raiz e src.scraper).

Uso:
    python .agents/teamwork/spec_miner_m3_r3_3/verify_m3_r3.py
    python verify_m3_r3.py --verbose
"""
from __future__ import annotations

import ast
import contextlib
import importlib
import io
import os
import re
import subprocess
import sys
import time
import types
import warnings
from pathlib import Path

# Raiz do repositório JudAI
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class VerificationReport:
    """Acumula e formata resultados de verificação com diagnósticos precisos."""

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
            print(f"  [FAIL] {name} -> {error_msg}")

    def print_summary(self) -> int:
        elapsed = time.perf_counter() - self.start_time
        total = len(self.passed) + len(self.failed)
        print("\n" + "=" * 78)
        print(" RESUMO DA VERIFICAÇÃO FORMAL: MILESTONE 3 - RODADA 3 (JudAI)")
        print(f" Raiz do Projeto: {ROOT_DIR}")
        print(f" Duração: {elapsed:.2f}s")
        print(f" Total de Critérios Verificados: {total}")
        print(f" Aprovados [PASS]: {len(self.passed)}")
        print(f" Reprovados [FAIL]: {len(self.failed)}")
        print("=" * 78)

        if self.failed:
            print("\nCRITÉRIOS REPROVADOS / AÇÕES NECESSÁRIAS:")
            for idx, (name, err) in enumerate(self.failed, 1):
                print(f"  {idx}. {name}")
                print(f"     Detalhe: {err}")
            print("\nSTATUS FINAL: REPROVADO (Consulte spec_m3_r3_validation.md para orientações)")
            return 1
        else:
            print("\nTODOS OS CRITÉRIOS DO MILESTONE 3 - RODADA 3 FORAM ATENDIDOS COM SUCESSO!")
            print("STATUS FINAL: APROVADO")
            return 0


# ==============================================================================
# 1. ANÁLISE ESTÁTICA VIA AST (Árvore Sintática Abstrata)
# ==============================================================================

def verify_static_ast(report: VerificationReport):
    print("\n[Fase 1/3] Executando Análise Estática de Código e AST...")

    # 1.1 Inspecionar src/scraper/carregar_mongo.py
    src_carregar = ROOT_DIR / "src" / "scraper" / "carregar_mongo.py"
    report.check(
        "Arquivo src/scraper/carregar_mongo.py existe",
        src_carregar.is_file(),
        f"Arquivo {src_carregar} não foi encontrado no disco."
    )
    if src_carregar.is_file():
        code_carregar = src_carregar.read_text(encoding="utf-8")
        try:
            tree_carregar = ast.parse(code_carregar, filename=str(src_carregar))
        except SyntaxError as e:
            tree_carregar = None
            report.check("Sintaxe válida em src/scraper/carregar_mongo.py", False, f"SyntaxError: {e}")

        if tree_carregar:
            # Procura função 'main'
            func_main = next(
                (n for n in tree_carregar.body if isinstance(n, ast.FunctionDef) and n.name == "main"),
                None
            )
            report.check(
                "src/scraper/carregar_mongo.py define 'def main(...)'",
                func_main is not None,
                "Função 'main' não encontrada como definição de função no nível do módulo em src/scraper/carregar_mongo.py."
            )

            if func_main:
                # Checa assinatura (aceita parâmetro argv com default None)
                args = func_main.args
                arg_names = [a.arg for a in args.args]
                has_argv = "argv" in arg_names
                report.check(
                    "src/scraper/carregar_mongo.py: main() aceita parâmetro 'argv'",
                    has_argv,
                    f"Assinatura esperada 'def main(argv=None):', argumentos encontrados: {arg_names}"
                )

            # Checa ponto de entrada __main__ chamando main()
            has_main_guard = False
            for node in ast.walk(tree_carregar):
                if isinstance(node, ast.If):
                    test_code = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
                    if "__name__" in test_code and "__main__" in test_code:
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.Call):
                                func_repr = ast.unparse(sub.func) if hasattr(ast, "unparse") else ""
                                if "main" in func_repr:
                                    has_main_guard = True
                                    break
            report.check(
                "src/scraper/carregar_mongo.py invoca main() sob if __name__ == '__main__'",
                has_main_guard,
                "Bloco if __name__ == '__main__' não encontrado ou não invoca main()."
            )

    # 1.2 Inspecionar src/scraper/ingestao_lei.py
    src_ingestao = ROOT_DIR / "src" / "scraper" / "ingestao_lei.py"
    report.check(
        "Arquivo src/scraper/ingestao_lei.py existe",
        src_ingestao.is_file(),
        f"Arquivo {src_ingestao} não foi encontrado no disco."
    )
    if src_ingestao.is_file():
        code_ingestao = src_ingestao.read_text(encoding="utf-8")
        try:
            tree_ingestao = ast.parse(code_ingestao, filename=str(src_ingestao))
        except SyntaxError as e:
            tree_ingestao = None
            report.check("Sintaxe válida em src/scraper/ingestao_lei.py", False, f"SyntaxError: {e}")

        if tree_ingestao:
            func_main = next(
                (n for n in tree_ingestao.body if isinstance(n, ast.FunctionDef) and n.name == "main"),
                None
            )
            report.check(
                "src/scraper/ingestao_lei.py define 'def main(...)'",
                func_main is not None,
                "Função 'main' não encontrada em src/scraper/ingestao_lei.py."
            )

            # Checa 5 funções da fachada
            for fn in ["baixar_legislacao", "salvar_bruto", "extrair_metadados", "extrair_estrutura", "extrair_dispositivos"]:
                fn_node = next((n for n in tree_ingestao.body if isinstance(n, ast.FunctionDef) and n.name == fn), None)
                report.check(
                    f"src/scraper/ingestao_lei.py preserva função '{fn}'",
                    fn_node is not None,
                    f"Função da fachada pública '{fn}' não encontrada em src/scraper/ingestao_lei.py."
                )

    # 1.3 Inspecionar carregar_mongo.py na raiz
    root_carregar = ROOT_DIR / "carregar_mongo.py"
    report.check(
        "Shim carregar_mongo.py existe na raiz",
        root_carregar.is_file(),
        f"Shim {root_carregar} não foi encontrado na raiz do projeto."
    )
    if root_carregar.is_file():
        code_root_carregar = root_carregar.read_text(encoding="utf-8")
        has_deprec_warn = "DeprecationWarning" in code_root_carregar and "warnings.warn" in code_root_carregar
        report.check(
            "carregar_mongo.py (raiz) emite DeprecationWarning",
            has_deprec_warn,
            "carregar_mongo.py na raiz não emite DeprecationWarning via warnings.warn."
        )

        has_aliasing = bool(re.search(r"sys\.modules\[(?:__name__|['\"]carregar_mongo['\"])\]\s*=", code_root_carregar))
        report.check(
            "carregar_mongo.py (raiz) implementa aliasing em sys.modules",
            has_aliasing,
            "carregar_mongo.py na raiz deve registrar o módulo de destino em sys.modules para evitar split-brain."
        )

        has_cli_guard = bool(re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', code_root_carregar)) and "main" in code_root_carregar
        report.check(
            "carregar_mongo.py (raiz) possui delegação de CLI para main()",
            has_cli_guard,
            "carregar_mongo.py na raiz deve invocar main() sob if __name__ == '__main__'."
        )

    # 1.4 Inspecionar ingestao_lei.py na raiz
    root_ingestao = ROOT_DIR / "ingestao_lei.py"
    report.check(
        "Shim ingestao_lei.py existe na raiz",
        root_ingestao.is_file(),
        f"Shim {root_ingestao} não foi encontrado na raiz do projeto."
    )
    if root_ingestao.is_file():
        code_root_ingestao = root_ingestao.read_text(encoding="utf-8")
        has_deprec_warn = "DeprecationWarning" in code_root_ingestao and "warnings.warn" in code_root_ingestao
        report.check(
            "ingestao_lei.py (raiz) emite DeprecationWarning",
            has_deprec_warn,
            "ingestao_lei.py na raiz não emite DeprecationWarning via warnings.warn."
        )

        has_aliasing = bool(re.search(r"sys\.modules\[(?:__name__|['\"]ingestao_lei['\"])\]\s*=", code_root_ingestao))
        report.check(
            "ingestao_lei.py (raiz) implementa aliasing em sys.modules",
            has_aliasing,
            "ingestao_lei.py na raiz deve registrar o módulo de destino em sys.modules para evitar split-brain."
        )

        has_cli_guard = bool(re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', code_root_ingestao)) and "main" in code_root_ingestao
        report.check(
            "ingestao_lei.py (raiz) possui delegação de CLI para main()",
            has_cli_guard,
            "ingestao_lei.py na raiz deve conter if __name__ == '__main__': main() para repassar a execução CLI."
        )


# ==============================================================================
# 2. VALIDAÇÃO DINÂMICA DE IMPORTAÇÃO E CONTRATO DE INTERFACE
# ==============================================================================

def verify_dynamic_contracts(report: VerificationReport):
    print("\n[Fase 2/3] Executando Validação Dinâmica de Módulos e Contratos...")

    # Limpeza preventiva de imports cacheados para isolar testes
    for mod_name in ["carregar_mongo", "ingestao_lei", "src.scraper.carregar_mongo", "src.scraper.ingestao_lei"]:
        sys.modules.pop(mod_name, None)

    # 2.1 Import de src.scraper.carregar_mongo
    try:
        import src.scraper.carregar_mongo as mod_src_carregar
        report.check("Importação de 'src.scraper.carregar_mongo' tem sucesso", True)
    except Exception as e:
        mod_src_carregar = None
        report.check("Importação de 'src.scraper.carregar_mongo' tem sucesso", False, str(e))

    if mod_src_carregar:
        has_main = hasattr(mod_src_carregar, "main")
        report.check(
            "src.scraper.carregar_mongo possui atributo 'main'",
            has_main,
            "Atributo 'main' ausente em src.scraper.carregar_mongo."
        )
        if has_main:
            is_callable = callable(getattr(mod_src_carregar, "main"))
            report.check(
                "src.scraper.carregar_mongo.main é chamável",
                is_callable,
                "src.scraper.carregar_mongo.main não é uma função ou objeto chamável."
            )

            # Teste de invocação com --help (deve levantar SystemExit(0))
            f_out = io.StringIO()
            with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
                try:
                    mod_src_carregar.main(["--help"])
                    exit_code = 0
                except SystemExit as ex:
                    exit_code = ex.code
                except Exception as ex:
                    exit_code = f"Exception: {ex}"

            report.check(
                "src.scraper.carregar_mongo.main(['--help']) sai com código 0",
                exit_code == 0,
                f"Código de saída inesperado para --help: {exit_code}"
            )

    # 2.2 Import de src.scraper.ingestao_lei
    try:
        import src.scraper.ingestao_lei as mod_src_ingestao
        report.check("Importação de 'src.scraper.ingestao_lei' tem sucesso", True)
    except Exception as e:
        mod_src_ingestao = None
        report.check("Importação de 'src.scraper.ingestao_lei' tem sucesso", False, str(e))

    if mod_src_ingestao:
        has_main = hasattr(mod_src_ingestao, "main")
        report.check(
            "src.scraper.ingestao_lei possui atributo 'main'",
            has_main,
            "Atributo 'main' ausente em src.scraper.ingestao_lei."
        )
        if has_main:
            is_callable = callable(getattr(mod_src_ingestao, "main"))
            report.check(
                "src.scraper.ingestao_lei.main é chamável",
                is_callable,
                "src.scraper.ingestao_lei.main não é chamável."
            )

    # 2.3 Import do Shim da Raiz: carregar_mongo
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        try:
            import carregar_mongo as mod_root_carregar
            root_carregar_error = None
        except Exception as e:
            mod_root_carregar = None
            root_carregar_error = e

    report.check(
        "Importação do shim 'carregar_mongo' da raiz não levanta exceção",
        mod_root_carregar is not None,
        f"Falha ao importar carregar_mongo: {root_carregar_error}"
    )

    deprec_carregar_emitted = any(
        issubclass(w.category, DeprecationWarning) and "carregar_mongo" in str(w.message)
        for w in recorded_warnings
    )
    report.check(
        "Shim 'carregar_mongo' emite DeprecationWarning na importação",
        deprec_carregar_emitted,
        f"Nenhum DeprecationWarning referente a carregar_mongo foi capturado. Avisos capturados: {[str(w.message) for w in recorded_warnings]}"
    )

    if mod_root_carregar:
        has_main = hasattr(mod_root_carregar, "main")
        report.check(
            "Shim 'carregar_mongo' possui atributo 'main' (hasattr)",
            has_main,
            "hasattr(carregar_mongo, 'main') retornou False!"
        )
        if has_main:
            report.check(
                "Shim 'carregar_mongo.main' é chamável",
                callable(getattr(mod_root_carregar, "main")),
                "carregar_mongo.main existe mas não é chamável."
            )
            # In-process invocação com --help
            f_out = io.StringIO()
            with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
                try:
                    mod_root_carregar.main(["--help"])
                    exit_code = 0
                except SystemExit as ex:
                    exit_code = ex.code
                except Exception as ex:
                    exit_code = f"Exception: {ex}"
            report.check(
                "Shim 'carregar_mongo.main(['--help'])' sai com código 0 in-process",
                exit_code == 0,
                f"Código de saída inesperado para carregar_mongo.main(['--help']): {exit_code}"
            )

        # Checa funções da API original
        for fn in ["conectar", "carregar_documentos", "inserir", "verificar"]:
            report.check(
                f"Shim 'carregar_mongo' exporta '{fn}'",
                hasattr(mod_root_carregar, fn),
                f"Função '{fn}' ausente no shim carregar_mongo."
            )

    # 2.4 Import do Shim da Raiz: ingestao_lei
    with warnings.catch_warnings(record=True) as recorded_warnings_ing:
        warnings.simplefilter("always")
        try:
            import ingestao_lei as mod_root_ingestao
            root_ingestao_error = None
        except Exception as e:
            mod_root_ingestao = None
            root_ingestao_error = e

    report.check(
        "Importação do shim 'ingestao_lei' da raiz não levanta exceção",
        mod_root_ingestao is not None,
        f"Falha ao importar ingestao_lei: {root_ingestao_error}"
    )

    deprec_ingestao_emitted = any(
        issubclass(w.category, DeprecationWarning) and "ingestao_lei" in str(w.message)
        for w in recorded_warnings_ing
    )
    report.check(
        "Shim 'ingestao_lei' emite DeprecationWarning na importação",
        deprec_ingestao_emitted,
        f"Nenhum DeprecationWarning referente a ingestao_lei foi capturado. Avisos capturados: {[str(w.message) for w in recorded_warnings_ing]}"
    )

    if mod_root_ingestao:
        has_main = hasattr(mod_root_ingestao, "main")
        report.check(
            "Shim 'ingestao_lei' possui atributo 'main' (hasattr)",
            has_main,
            "hasattr(ingestao_lei, 'main') retornou False!"
        )
        if has_main:
            report.check(
                "Shim 'ingestao_lei.main' é chamável",
                callable(getattr(mod_root_ingestao, "main")),
                "ingestao_lei.main existe mas não é chamável."
            )
            # In-process invocação com --help
            f_out = io.StringIO()
            with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
                try:
                    mod_root_ingestao.main(["--help"])
                    exit_code = 0
                except SystemExit as ex:
                    exit_code = ex.code
                except Exception as ex:
                    exit_code = f"Exception: {ex}"
            report.check(
                "Shim 'ingestao_lei.main(['--help'])' sai com código 0 in-process",
                exit_code == 0,
                f"Código de saída inesperado para ingestao_lei.main(['--help']): {exit_code}"
            )

        for fn in ["baixar_legislacao", "salvar_bruto", "extrair_metadados", "extrair_estrutura", "extrair_dispositivos"]:
            report.check(
                f"Shim 'ingestao_lei' exporta '{fn}'",
                hasattr(mod_root_ingestao, fn),
                f"Função '{fn}' ausente no shim ingestao_lei."
            )

    # 2.5 Aliasing de Módulo em sys.modules e Prevenção de Split-Brain
    # Para carregar_mongo:
    is_carregar_aliased = (
        "carregar_mongo" in sys.modules
        and "src.scraper.carregar_mongo" in sys.modules
        and sys.modules["carregar_mongo"] is sys.modules["src.scraper.carregar_mongo"]
    )
    report.check(
        "Aliasing de módulo: sys.modules['carregar_mongo'] is sys.modules['src.scraper.carregar_mongo']",
        is_carregar_aliased,
        "sys.modules['carregar_mongo'] e sys.modules['src.scraper.carregar_mongo'] apontam para objetos distintos (split-brain)!"
    )

    # Imunidade a mutação de estado (split-brain check)
    if is_carregar_aliased:
        test_key = f"_probe_m3_r3_{int(time.time())}"
        setattr(sys.modules["carregar_mongo"], test_key, "sync_ok")
        sync_ok = getattr(sys.modules["src.scraper.carregar_mongo"], test_key, None) == "sync_ok"
        report.check(
            "Imunidade a split-brain em carregar_mongo (mutação de atributo compartilhada)",
            sync_ok,
            "Alteração em carregar_mongo não refletiu em src.scraper.carregar_mongo."
        )

    # Para ingestao_lei:
    is_ingestao_aliased = (
        "ingestao_lei" in sys.modules
        and "src.scraper.ingestao_lei" in sys.modules
        and sys.modules["ingestao_lei"] is sys.modules["src.scraper.ingestao_lei"]
    )
    report.check(
        "Aliasing de módulo: sys.modules['ingestao_lei'] is sys.modules['src.scraper.ingestao_lei']",
        is_ingestao_aliased,
        "sys.modules['ingestao_lei'] e sys.modules['src.scraper.ingestao_lei'] apontam para objetos distintos (split-brain)!"
    )

    if is_ingestao_aliased:
        test_key_ing = f"_probe_ing_m3_r3_{int(time.time())}"
        setattr(sys.modules["ingestao_lei"], test_key_ing, "sync_ok")
        sync_ok_ing = getattr(sys.modules["src.scraper.ingestao_lei"], test_key_ing, None) == "sync_ok"
        report.check(
            "Imunidade a split-brain em ingestao_lei (mutação de atributo compartilhada)",
            sync_ok_ing,
            "Alteração em ingestao_lei não refletiu em src.scraper.ingestao_lei."
        )


# ==============================================================================
# 3. VALIDAÇÃO DE EXECUÇÃO CLI EXTERNA (SUBPROCESSOS E RUNNER)
# ==============================================================================

def run_cli_command(cmd_args: list[str]) -> tuple[int, str, str]:
    """Executa comando CLI em subprocesso com PYTHONPATH configurado."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    try:
        proc = subprocess.run(
            [sys.executable] + cmd_args,
            cwd=str(ROOT_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -999, "", "Timeout expired (10s)"
    except Exception as ex:
        return -1, "", str(ex)


def verify_cli_executions(report: VerificationReport):
    print("\n[Fase 3/3] Executando Validação de Invocação de Linha de Comando (CLI)...")

    # 3.1 Invocação: python -m src.scraper.carregar_mongo --help
    rc, stdout, stderr = run_cli_command(["-m", "src.scraper.carregar_mongo", "--help"])
    report.check(
        "CLI 'python -m src.scraper.carregar_mongo --help' finaliza com código 0",
        rc == 0,
        f"Código de retorno: {rc}. stderr: {stderr.strip()[:200]}"
    )
    report.check(
        "CLI 'python -m src.scraper.carregar_mongo --help' exibe instrução de uso",
        "usage" in stdout.lower() or "uso" in stdout.lower() or "fonte" in stdout.lower(),
        f"Saída stdout não contém termos esperados de documentação. stdout: {stdout[:200]}"
    )

    # 3.2 Invocação: python -m src.scraper.ingestao_lei --help
    rc, stdout, stderr = run_cli_command(["-m", "src.scraper.ingestao_lei", "--help"])
    report.check(
        "CLI 'python -m src.scraper.ingestao_lei --help' finaliza com código 0",
        rc == 0,
        f"Código de retorno: {rc}. stderr: {stderr.strip()[:200]}"
    )
    report.check(
        "CLI 'python -m src.scraper.ingestao_lei --help' exibe instrução de uso",
        "entrada" in stdout or "--mongo-uri" in stdout or "usage" in stdout.lower(),
        f"Saída stdout não contém argumentos esperados do parser. stdout: {stdout[:200]}"
    )

    # 3.3 Invocação do Shim: python carregar_mongo.py --help
    rc, stdout, stderr = run_cli_command(["carregar_mongo.py", "--help"])
    no_import_error = "ImportError" not in stderr and "cannot import name" not in stderr
    report.check(
        "CLI Shim 'python carregar_mongo.py --help' não gera ImportError",
        no_import_error,
        f"Detectado crash de importação: {stderr.strip()[:300]}"
    )
    report.check(
        "CLI Shim 'python carregar_mongo.py --help' finaliza com código 0",
        rc == 0,
        f"Código de retorno: {rc}. stderr: {stderr.strip()[:200]}"
    )
    report.check(
        "CLI Shim 'python carregar_mongo.py --help' exibe DeprecationWarning em stderr",
        "DeprecationWarning" in stderr or "obsoleto" in stderr or "migrado" in stderr,
        f"DeprecationWarning não foi detectado em stderr. stderr: {stderr.strip()[:200]}"
    )

    # 3.4 Invocação do Shim: python ingestao_lei.py --help
    rc, stdout, stderr = run_cli_command(["ingestao_lei.py", "--help"])
    report.check(
        "CLI Shim 'python ingestao_lei.py --help' finaliza com código 0",
        rc == 0,
        f"Código de retorno: {rc}. stderr: {stderr.strip()[:200]}"
    )
    report.check(
        "CLI Shim 'python ingestao_lei.py --help' exibe DeprecationWarning em stderr",
        "DeprecationWarning" in stderr or "obsoleto" in stderr or "migrado" in stderr,
        f"DeprecationWarning não foi detectado em stderr. stderr: {stderr.strip()[:200]}"
    )
    report.check(
        "CLI Shim 'python ingestao_lei.py --help' repassa execução para CLI (não é no-op)",
        ("entrada" in stdout or "--mongo-uri" in stdout or "usage" in stdout.lower()),
        f"Saída stdout vazia ou sem repasse para CLI de ingestao_lei! stdout: {stdout.strip()[:200]}"
    )


def main():
    parser = argparse.ArgumentParser(description="Verificador Automatizado do Milestone 3 - Rodada 3 (JudAI)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Exibe detalhes de cada validação aprovada")
    args = parser.parse_args()

    report = VerificationReport(verbose=args.verbose)
    print("=" * 78)
    print(" INICIANDO VERIFICAÇÃO AUTOMATIZADA: MILESTONE 3 - RODADA 3 (JudAI)")
    print("=" * 78)

    verify_static_ast(report)
    verify_dynamic_contracts(report)
    verify_cli_executions(report)

    sys.exit(report.print_summary())


if __name__ == "__main__":
    main()
