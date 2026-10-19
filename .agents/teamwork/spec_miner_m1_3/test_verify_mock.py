import tempfile
import pathlib
from pathlib import Path
import verify_m1

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    
    # 1. docker-compose.yml
    compose_content = (
        "services:\n"
        "  mongodb:\n"
        "    image: mongo:latest\n"
        "    container_name: judai-mongodb\n"
        "    restart: unless-stopped\n"
        "    ports:\n"
        '      - "27017:27017"\n'
        "    volumes:\n"
        "      - mongo_data:/data/db\n"
        "\n"
        "volumes:\n"
        "  mongo_data:\n"
    )
    (root / "docker-compose.yml").write_text(compose_content, encoding="utf-8")

    # 2. structure
    (root / "data" / "raw").mkdir(parents=True)
    (root / "data" / "raw" / ".gitkeep").write_text("", encoding="utf-8")
    (root / "data" / "chromadb_local").mkdir(parents=True)
    (root / "data" / "chromadb_local" / ".gitkeep").write_text("", encoding="utf-8")
    (root / "notebooks").mkdir(parents=True)
    (root / "notebooks" / ".gitkeep").write_text("", encoding="utf-8")

    (root / "src" / "scraper").mkdir(parents=True)
    (root / "src" / "database").mkdir(parents=True)
    (root / "src" / "models").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)

    (root / "src" / "__init__.py").write_text('"""JudAI Package."""\n', encoding="utf-8")
    (root / "src" / "scraper" / "__init__.py").write_text('"""Scraper."""\n', encoding="utf-8")
    (root / "src" / "database" / "__init__.py").write_text('"""Database."""\n', encoding="utf-8")
    (root / "src" / "models" / "__init__.py").write_text('"""Models."""\n', encoding="utf-8")
    (root / "src" / "api" / "__init__.py").write_text('"""API."""\n', encoding="utf-8")

    # 3. git files
    gitignore_content = (
        "venv/\n"
        ".venv/\n"
        "env/\n"
        "__pycache__/\n"
        "*.py[cod]\n"
        ".env\n"
        "data/*\n"
        "!data/**/\n"
        "!data/**/.gitkeep\n"
        "data/**/*\n"
        "!data/**/\n"
        "!data/**/.gitkeep\n"
    )
    (root / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    (root / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8")

    # 4. requirements.txt
    req_content = (
        "fastapi\n"
        "uvicorn[standard]\n"
        "pydantic\n"
        "pymongo\n"
        "chromadb\n"
        "rank_bm25\n"
        "sentence-transformers\n"
        "nltk\n"
        "python-dotenv\n"
        "beautifulsoup4\n"
        "lxml\n"
        "requests\n"
    )
    (root / "requirements.txt").write_text(req_content, encoding="utf-8")

    # 5. .env.example
    env_content = (
        "MONGO_URI=mongodb://localhost:27017\n"
        "MONGO_DB_NAME=rag_juridico\n"
        "CHROMA_DB_PATH=./data/chromadb_local\n"
    )
    (root / ".env.example").write_text(env_content, encoding="utf-8")

    # Run verify_m1 against the mock root
    code = verify_m1.run_all(root)
    print(f"Mock validation result exit code: {code}")
    assert code == 0, f"Expected 0, got {code}"
    print("ALL MOCK VALIDATION CHECKS PASSED WITH ZERO ERRORS!")
