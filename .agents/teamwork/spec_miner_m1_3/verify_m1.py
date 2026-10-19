"""JudAI Milestone 1 Verification Script.

Executa a validação completa dos 5 pilares do Milestone 1:
1. docker-compose.yml (sintaxe, imagem mongo:latest, porta 27017, volume persistente nomeado)
2. Estrutura de diretórios, .gitkeep e __init__.py
3. .gitignore e .gitattributes (regras de exclusão e normalização LF)
4. requirements.txt (12 dependências exatas sem pin)
5. .env.example (chaves e valores canônicos)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def log_pass(msg: str) -> None:
    print(f"[\033[92mPASS\033[0m] {msg}")


def log_fail(msg: str) -> None:
    print(f"[\033[91mFAIL\033[0m] {msg}")


def log_warn(msg: str) -> None:
    print(f"[\033[93mWARN\033[0m] {msg}")


def log_info(msg: str) -> None:
    print(f"[\033[94mINFO\033[0m] {msg}")


def verify_docker_compose(root: Path) -> list[str]:
    errors = []
    compose_path = root / "docker-compose.yml"
    if not compose_path.is_file():
        errors.append("docker-compose.yml não existe na raiz do projeto.")
        return errors

    content = compose_path.read_text(encoding="utf-8", errors="replace")

    # 1. Checagem de seções essenciais
    if not re.search(r"^services:\s*$", content, re.MULTILINE):
        errors.append("docker-compose.yml não define a seção raiz 'services:'.")

    if not re.search(r"^\s+mongodb:\s*$", content, re.MULTILINE):
        errors.append("docker-compose.yml não define o serviço 'mongodb:'.")

    if not re.search(r"image:\s*['\"]?mongo:latest['\"]?", content):
        errors.append("Serviço mongodb não utiliza a imagem 'mongo:latest'.")

    if not re.search(r"['\"]?27017:27017['\"]?", content):
        errors.append("Serviço mongodb não expõe a porta '27017:27017'.")

    # Volume mount para /data/db com volume nomeado
    vol_match = re.search(r"-\s*['\"]?([a-zA-Z0-9_-]+):/data/db['\"]?", content)
    if not vol_match:
        errors.append("Serviço mongodb não mapeia volume persistente para '/data/db'.")
    else:
        vol_name = vol_match.group(1)
        # Checar se o volume nomeado está na seção raiz 'volumes:'
        if not re.search(r"^volumes:\s*$", content, re.MULTILINE):
            errors.append("docker-compose.yml não declara a seção raiz 'volumes:' para o volume nomeado.")
        elif not re.search(rf"^\s+{re.escape(vol_name)}:\s*$", content, re.MULTILINE):
            errors.append(f"Volume nomeado '{vol_name}' não foi declarado na seção raiz 'volumes:'.")

    # 2. Se docker estiver disponível, roda docker compose config
    if shutil.which("docker"):
        try:
            res = subprocess.run(
                ["docker", "compose", "config"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode != 0:
                errors.append(f"'docker compose config' falhou com código {res.returncode}:\n{res.stderr}")
            else:
                log_pass("docker compose config validou o arquivo com sucesso.")
        except Exception as e:
            log_warn(f"Erro ao executar 'docker compose config': {e}")
    else:
        log_info("Docker CLI não detectado no PATH do sistema. Validação estática executada.")

    return errors


def verify_structure(root: Path) -> list[str]:
    errors = []
    expected_dirs = [
        root / "data" / "raw",
        root / "data" / "chromadb_local",
        root / "notebooks",
        root / "src",
        root / "src" / "scraper",
        root / "src" / "database",
        root / "src" / "models",
        root / "src" / "api",
    ]
    for d in expected_dirs:
        if not d.is_dir():
            errors.append(f"Diretório obrigatório ausente: {d.relative_to(root)}")

    expected_gitkeeps = [
        root / "data" / "raw" / ".gitkeep",
        root / "data" / "chromadb_local" / ".gitkeep",
        root / "notebooks" / ".gitkeep",
    ]
    for gk in expected_gitkeeps:
        if not gk.is_file():
            errors.append(f"Arquivo .gitkeep obrigatório ausente: {gk.relative_to(root)}")

    expected_inits = [
        root / "src" / "__init__.py",
        root / "src" / "scraper" / "__init__.py",
        root / "src" / "database" / "__init__.py",
        root / "src" / "models" / "__init__.py",
        root / "src" / "api" / "__init__.py",
    ]
    for init_f in expected_inits:
        if not init_f.is_file():
            errors.append(f"Arquivo __init__.py obrigatório ausente: {init_f.relative_to(root)}")
        else:
            # Validar compilação sintática
            try:
                content = init_f.read_text(encoding="utf-8")
                compile(content, str(init_f), "exec")
            except Exception as e:
                errors.append(f"Erro de sintaxe em {init_f.relative_to(root)}: {e}")

    # Verificar importabilidade limpa dos pacotes no M1 (não deve quebrar por imports prematuros)
    sys_path_mod = False
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
            sys_path_mod = True
        for mod in ["src", "src.scraper", "src.database", "src.models", "src.api"]:
            try:
                __import__(mod)
            except Exception as e:
                errors.append(f"Falha ao importar pacote base '{mod}': {e}")
    finally:
        if sys_path_mod and str(root) in sys.path:
            sys.path.remove(str(root))

    return errors


def verify_git_rules(root: Path) -> list[str]:
    errors = []
    gitignore_path = root / ".gitignore"
    gitattributes_path = root / ".gitattributes"

    if not gitignore_path.is_file():
        errors.append(".gitignore não existe na raiz do projeto.")
    else:
        gi_content = gitignore_path.read_text(encoding="utf-8", errors="replace")
        for req_pattern in ["venv/", ".venv/", ".env", "__pycache__/"]:
            if req_pattern not in gi_content:
                errors.append(f".gitignore não contém o padrão mandatório '{req_pattern}'.")

        # Testar regras do gitignore em repositório temporário
        if shutil.which("git"):
            try:
                with tempfile.TemporaryDirectory() as td:
                    temp_dir = Path(td)
                    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
                    (temp_dir / ".gitignore").write_text(gi_content, encoding="utf-8")

                    # Criar estrutura de teste
                    (temp_dir / "data" / "raw").mkdir(parents=True)
                    (temp_dir / "data" / "raw" / ".gitkeep").write_text("", encoding="utf-8")
                    (temp_dir / "data" / "raw" / "dummy.html").write_text("raw", encoding="utf-8")

                    (temp_dir / "data" / "chromadb_local").mkdir(parents=True)
                    (temp_dir / "data" / "chromadb_local" / ".gitkeep").write_text("", encoding="utf-8")
                    (temp_dir / "data" / "chromadb_local" / "test.sqlite3").write_text("db", encoding="utf-8")

                    (temp_dir / "notebooks").mkdir(parents=True)
                    (temp_dir / "notebooks" / ".gitkeep").write_text("", encoding="utf-8")
                    (temp_dir / "notebooks" / "draft.ipynb").write_text("{}", encoding="utf-8")

                    (temp_dir / ".env").write_text("SECRET=1", encoding="utf-8")
                    (temp_dir / "venv").mkdir()
                    (temp_dir / "venv" / "bin_file").write_text("bin", encoding="utf-8")

                    # Rodar git status
                    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
                    res = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                    )
                    staged_files = [line.strip().split()[-1] for line in res.stdout.strip().splitlines() if line.strip()]

                    # Validar arquivos que DEVEM ser rastreados
                    must_track = [
                        ".gitignore",
                        "data/raw/.gitkeep",
                        "data/chromadb_local/.gitkeep",
                        "notebooks/.gitkeep",
                    ]
                    for mf in must_track:
                        if mf not in staged_files:
                            errors.append(f"Regra do Git falhou: '{mf}' NÃO foi rastreado pelo Git.")

                    # Validar arquivos que NÃO DEVEM ser rastreados
                    must_not_track = [
                        ".env",
                        "data/raw/dummy.html",
                        "data/chromadb_local/test.sqlite3",
                        "venv/bin_file",
                    ]
                    for mnf in must_not_track:
                        if mnf in staged_files:
                            errors.append(f"Regra do Git falhou: '{mnf}' FOI indevidamente rastreado pelo Git.")
            except Exception as e:
                log_warn(f"Erro no teste temporário de git: {e}")

    if not gitattributes_path.is_file():
        errors.append(".gitattributes não existe na raiz do projeto.")
    else:
        ga_content = gitattributes_path.read_text(encoding="utf-8", errors="replace").strip()
        if "* text=auto eol=lf" not in ga_content:
            errors.append(".gitattributes não contém a diretiva canônica '* text=auto eol=lf'.")

    return errors


def verify_requirements(root: Path) -> list[str]:
    errors = []
    req_path = root / "requirements.txt"
    if not req_path.is_file():
        errors.append("requirements.txt não existe na raiz do projeto.")
        return errors

    content = req_path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

    expected_12 = {
        "fastapi": set(),
        "uvicorn": {"standard"},
        "pydantic": set(),
        "pymongo": set(),
        "chromadb": set(),
        "rank_bm25": set(),
        "sentence-transformers": set(),
        "nltk": set(),
        "python-dotenv": set(),
        "beautifulsoup4": set(),
        "lxml": set(),
        "requests": set(),
    }

    try:
        from packaging.requirements import Requirement
    except ImportError:
        errors.append("Biblioteca 'packaging' necessária para validação formal de requirements.txt.")
        return errors

    parsed_deps: dict[str, set[str]] = {}
    for line in lines:
        try:
            req = Requirement(line)
            normalized_name = req.name.lower().replace("_", "-")
            if str(req.specifier) != "":
                errors.append(f"Dependência '{line}' possui versão fixada ('{req.specifier}'). Requisito R1 exige 'sem pin'.")
            parsed_deps[req.name] = req.extras
        except Exception as e:
            errors.append(f"Falha ao interpretar dependência '{line}': {e}")

    # Verificar ausências
    for exp_name, exp_extras in expected_12.items():
        # Busca normalizada
        found = False
        for actual_name, actual_extras in parsed_deps.items():
            if actual_name.lower().replace("_", "-") == exp_name.lower().replace("_", "-"):
                found = True
                if actual_extras != exp_extras:
                    errors.append(
                        f"Dependência '{exp_name}' possui extras incorretos: esperado {exp_extras}, obtido {actual_extras}"
                    )
                break
        if not found:
            errors.append(f"Dependência mandatória ausente em requirements.txt: '{exp_name}'")

    # Verificar itens extras não autorizados
    for actual_name in parsed_deps:
        matched = any(actual_name.lower().replace("_", "-") == exp.lower().replace("_", "-") for exp in expected_12)
        if not matched:
            errors.append(f"Dependência não prevista encontrada em requirements.txt: '{actual_name}'")

    if len(lines) != 12:
        errors.append(f"requirements.txt deve conter exatamente 12 dependências, encontrou {len(lines)}.")

    return errors


def verify_env_example(root: Path) -> list[str]:
    errors = []
    env_path = root / ".env.example"
    if not env_path.is_file():
        errors.append(".env.example não existe na raiz do projeto.")
        return errors

    content = env_path.read_text(encoding="utf-8", errors="replace")
    env_vars: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            errors.append(f"Linha inválida em .env.example (sem delimitador '='): '{line}'")
            continue
        k, v = line.split("=", 1)
        env_vars[k.strip()] = v.strip()

    expected_vars = {
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DB_NAME": "rag_juridico",
        "CHROMA_DB_PATH": "./data/chromadb_local",
    }

    for k, v in expected_vars.items():
        if k not in env_vars:
            errors.append(f"Variável mandatória ausente em .env.example: '{k}'")
        elif env_vars[k] != v:
            errors.append(f"Valor incorreto para '{k}' em .env.example: esperado '{v}', obtido '{env_vars[k]}'")

    return errors


def run_all(root_dir: str | Path | None = None) -> int:
    if root_dir is None:
        root = Path(__file__).resolve().parent.parent.parent.parent
    else:
        root = Path(root_dir).resolve()

    print(f"=== INICIANDO VALIDAÇÃO DO MILESTONE 1 EM: {root} ===")

    all_errors: dict[str, list[str]] = {
        "Docker Compose": verify_docker_compose(root),
        "Estrutura e Pacotes": verify_structure(root),
        "Git Governance (.gitignore e .gitattributes)": verify_git_rules(root),
        "Dependências (requirements.txt)": verify_requirements(root),
        "Ambiente (.env.example)": verify_env_example(root),
    }

    total_failures = 0
    print("\n=== RESULTADO POR CATEGORIA ===")
    for category, errs in all_errors.items():
        if not errs:
            log_pass(f"{category}: CONFORME")
        else:
            total_failures += len(errs)
            log_fail(f"{category}: {len(errs)} não conformidade(s) detectada(s)")
            for e in errs:
                print(f"   -> {e}")

    print("\n" + "=" * 50)
    if total_failures == 0:
        log_pass("MILESTONE 1: 100% DAS ESPECIFICAÇÕES ATENDIDAS!")
        return 0
    else:
        log_fail(f"MILESTONE 1: {total_failures} NÃO CONFORMIDADES IDENTIFICADAS.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all())
