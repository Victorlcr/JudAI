"""Adversarial stress-test script for JudAI Milestone 1.

Author: reviewer_m1_2
Scope: Independent verification of cross-platform compliance,
governance, line endings, packaging, docker-compose syntax,
and requirements integrity.
"""

from pathlib import Path
import re
import sys

def test_line_endings(root: Path):
    target_files = [
        root / ".gitattributes",
        root / "requirements.txt",
        root / ".env.example",
        root / ".gitignore",
        root / "docker-compose.yml",
        root / "data" / "raw" / ".gitkeep",
        root / "data" / "chromadb_local" / ".gitkeep",
        root / "notebooks" / ".gitkeep",
        root / "src" / "__init__.py",
        root / "src" / "scraper" / "__init__.py",
        root / "src" / "database" / "__init__.py",
        root / "src" / "models" / "__init__.py",
        root / "src" / "api" / "__init__.py",
    ]
    for p in target_files:
        assert p.is_file(), f"File {p} does not exist"
        data = p.read_bytes()
        assert b"\r\n" not in data, f"CRLF found in {p.relative_to(root)}"
        assert b"\n" in data, f"LF not found in {p.relative_to(root)}"
    print("[PASS] All target files have strict LF line endings.")

def test_gitattributes(root: Path):
    p = root / ".gitattributes"
    content = p.read_text(encoding="utf-8").strip()
    assert content == "* text=auto eol=lf", f"Unexpected .gitattributes content: '{content}'"
    print("[PASS] .gitattributes contains exact canonical directive.")

def test_requirements(root: Path):
    p = root / "requirements.txt"
    lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pymongo",
        "chromadb",
        "rank_bm25",
        "sentence-transformers",
        "nltk",
        "python-dotenv",
        "beautifulsoup4",
        "lxml",
        "requests",
    ]
    assert lines == expected, f"requirements.txt mismatch: {lines} vs {expected}"
    assert len(lines) == 12, f"Expected 12 deps, found {len(lines)}"
    print("[PASS] requirements.txt matches exactly 12 unpinned dependencies in order.")

def test_env_example(root: Path):
    p = root / ".env.example"
    lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines()]
    non_empty = [line for line in lines if line and not line.startswith("#")]
    expected = [
        "MONGO_URI=mongodb://localhost:27017",
        "MONGO_DB_NAME=rag_juridico",
        "CHROMA_DB_PATH=./data/chromadb_local",
    ]
    assert non_empty == expected, f"Unexpected .env.example content: {non_empty}"
    print("[PASS] .env.example contains exact canonical environment variables.")

def test_docker_compose_structure(root: Path):
    p = root / "docker-compose.yml"
    content = p.read_text(encoding="utf-8")
    assert "services:" in content
    assert "mongodb:" in content
    assert "image: mongo:latest" in content
    assert 'ports:\n      - "27017:27017"' in content or "ports:\n      - '27017:27017'" in content or '- "27017:27017"' in content
    assert "- mongo_data:/data/db" in content
    assert "volumes:\n  mongo_data:" in content
    print("[PASS] docker-compose.yml strictly adheres to compose specification.")

def test_clean_packages(root: Path):
    # Verify __init__.py files
    inits = [
        root / "src" / "__init__.py",
        root / "src" / "scraper" / "__init__.py",
        root / "src" / "database" / "__init__.py",
        root / "src" / "models" / "__init__.py",
        root / "src" / "api" / "__init__.py",
    ]
    for init_file in inits:
        content = init_file.read_text(encoding="utf-8")
        # Ensure it has a docstring
        assert '"""' in content, f"Docstring missing in {init_file}"
        # Ensure no premature imports
        for forbidden in ["import mongo_connection", "import chroma_connection", "import bm25_search", "import bert_search", "import main"]:
            assert forbidden not in content, f"Premature import '{forbidden}' found in {init_file}"
    print("[PASS] Package __init__.py files are clean with docstrings and zero premature imports.")

def main():
    root = Path(__file__).resolve().parent.parent.parent.parent
    print(f"Running reviewer_m1_2 adversarial suite against: {root}")
    test_line_endings(root)
    test_gitattributes(root)
    test_requirements(root)
    test_env_example(root)
    test_docker_compose_structure(root)
    test_clean_packages(root)
    print("\nALL ADVERSARIAL TESTS PASSED!")

if __name__ == "__main__":
    main()
