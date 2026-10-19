"""
Harness de Teste Adversarial para Shims da Raiz e Resolução de Módulos (JudAI)
Autor: challenger_m3_r2_2
"""
import ast
import inspect
import sys
from pathlib import Path

ROOT_DIR = Path("e:/Programacao/JudAI")

def analyze_carregar_mongo_main():
    """Verifica se src/scraper/carregar_mongo.py possui a função main()."""
    target = ROOT_DIR / "src" / "scraper" / "carregar_mongo.py"
    tree = ast.parse(target.read_text(encoding="utf-8"))
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    has_main = "main" in functions
    return has_main, functions

def analyze_root_carregar_mongo_shim():
    """Analisa o shim carregar_mongo.py na raiz."""
    shim = ROOT_DIR / "carregar_mongo.py"
    tree = ast.parse(shim.read_text(encoding="utf-8"))
    imports_main = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "src.scraper.carregar_mongo":
                for alias in node.names:
                    if alias.name == "main":
                        imports_main = True
    return imports_main

def analyze_root_ingestao_lei_shim():
    """Analisa o shim ingestao_lei.py na raiz."""
    shim = ROOT_DIR / "ingestao_lei.py"
    tree = ast.parse(shim.read_text(encoding="utf-8"))
    has_main_call = False
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # check if __name__ == '__main__'
            has_main_call = True
    return has_main_call

def analyze_facade_functions():
    """Verifica se src/scraper/ingestao_lei.py define todas as 5 funções da fachada pública."""
    target = ROOT_DIR / "src" / "scraper" / "ingestao_lei.py"
    tree = ast.parse(target.read_text(encoding="utf-8"))
    functions = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    required = [
        "baixar_legislacao",
        "salvar_bruto",
        "extrair_metadados",
        "extrair_estrutura",
        "extrair_dispositivos",
    ]
    missing = [fn for fn in required if fn not in functions]
    return missing, list(functions.keys())

def analyze_regex_patterns():
    """Analisa estaticamente as regexes ORD e RE_PAR em src/scraper/ingestao_lei.py."""
    target = ROOT_DIR / "src" / "scraper" / "ingestao_lei.py"
    content = target.read_text(encoding="utf-8")
    empty_branch = "(?:§|)" in content
    has_ufffd_ord = r"\ufffd" in content and "ORD =" in content
    has_ufffd_re_par = r"\ufffd" in content and "RE_PAR =" in content
    return {
        "empty_branch_detected": empty_branch,
        "has_ufffd_ord": has_ufffd_ord,
        "has_ufffd_re_par": has_ufffd_re_par,
    }

def analyze_tier1_test():
    """Verifica o teste test_scraper_no_scripts_left_in_root em test_tier1_feature_coverage.py."""
    test_file = ROOT_DIR / "tests" / "test_tier1_feature_coverage.py"
    content = test_file.read_text(encoding="utf-8")
    tree = ast.parse(content)
    test_body_has_assert = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "test_scraper_no_scripts_left_in_root":
            for child in ast.walk(node):
                if isinstance(child, ast.Assert):
                    test_body_has_assert = True
    return test_body_has_assert

def run_all_challenges():
    results = {}
    
    # 1. Checagem de main em carregar_mongo
    has_main, functions = analyze_carregar_mongo_main()
    imports_main = analyze_root_carregar_mongo_shim()
    results["carregar_mongo_has_main"] = has_main
    results["root_shim_imports_main"] = imports_main
    results["bug_carregar_mongo_importerror"] = (imports_main and not has_main)
    
    # 2. Checagem de CLI em ingestao_lei
    has_cli = analyze_root_ingestao_lei_shim()
    results["root_ingestao_lei_has_cli"] = has_cli
    
    # 3. Funções da fachada
    missing_fns, all_fns = analyze_facade_functions()
    results["facade_missing_functions"] = missing_fns
    
    # 4. Regex
    regex_res = analyze_regex_patterns()
    results["regex_analysis"] = regex_res
    
    # 5. Tier 1 Test
    has_assert = analyze_tier1_test()
    results["test_scraper_no_scripts_left_in_root_has_assert"] = has_assert
    
    return results

if __name__ == "__main__":
    res = run_all_challenges()
    import pprint
    pprint.pprint(res)
