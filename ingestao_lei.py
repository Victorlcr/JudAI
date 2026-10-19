"""
DEPRECATED: Este arquivo foi migrado para src/scraper/ingestao_lei.py.
A remoção física deste arquivo ocorrerá no Milestone 5 (Git Init).
"""
import sys
import warnings

warnings.warn(
    "ingestao_lei.py na raiz do projeto está obsoleto e foi migrado para src.scraper.ingestao_lei. "
    "Este shim será removido no Milestone 5.",
    DeprecationWarning,
    stacklevel=2,
)

import src.scraper.ingestao_lei as _target  # noqa: E402

# Re-exportação explícita para suporte a IDEs, linters e análise estática (AST)
from src.scraper.ingestao_lei import *  # noqa: E402, F401, F403

# Aliasing de módulo em sys.modules para prevenção estrita de split-brain
sys.modules[__name__] = _target
sys.modules.setdefault("ingestao_lei", _target)

if __name__ == "__main__":
    _target.main()
