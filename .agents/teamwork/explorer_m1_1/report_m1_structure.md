# Relatório Técnico - Milestone 1: Estrutura de Diretórios e Pacotes (JudAI)

**Autor**: Explorer 1 (Milestone 1)  
**Data**: 2026-10-18  
**Status**: Concluído / Pronto para Execução  
**Público-alvo**: Orchestrator, Executor M1  

---

## 1. Resumo Executivo

Este documento estabelece a análise técnica, requisitos detalhados e o plano de implementação para a criação da árvore de diretórios e pacotes Python do projeto **JudAI**, em estrita conformidade com a requisição original (`ORIGINAL_REQUEST.md §R1`) e o plano mestre do projeto (`PROJECT.md`).

A estrutura foi projetada para garantir compatibilidade multiplataforma transparente (Windows e Linux/macOS), suporte a empacotamento modular em Python 3.11+, preservação da árvore em repositórios Git clonados e isolamento rigoroso entre módulos da aplicação.

---

## 2. Árvore Alvo e Especificação dos Arquivos

A árvore exata a ser criada no Milestone 1 consiste em:

```text
e:\Programacao\JudAI\
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── chromadb_local/
│       └── .gitkeep
├── notebooks/
│   └── .gitkeep
└── src/
    ├── __init__.py
    ├── scraper/
    │   └── __init__.py
    ├── database/
    │   └── __init__.py
    ├── models/
    │   └── __init__.py
    └── api/
        └── __init__.py
```

### Tabela Descritiva dos Componentes

| Caminho Relativo | Tipo | Finalidade Primária | Conteúdo / Tamanho |
|---|---|---|---|
| `data/raw/` | Diretório | Armazenamento de dados brutos coletados (HTMLs, textos, PDFs de leis) | N/A |
| `data/raw/.gitkeep` | Arquivo | Marcador para tracking da pasta vazia no Git | 0 bytes ou `\n` (LF) |
| `data/chromadb_local/` | Diretório | Armazenamento persistente local do ChromaDB (SQLite + vetores HNSW) | N/A |
| `data/chromadb_local/.gitkeep` | Arquivo | Marcador para tracking da pasta vazia no Git | 0 bytes ou `\n` (LF) |
| `notebooks/` | Diretório | Diretório para Jupyter Notebooks de experimentação e prototipação | N/A |
| `notebooks/.gitkeep` | Arquivo | Marcador para tracking da pasta vazia no Git | 0 bytes ou `\n` (LF) |
| `src/` | Diretório / Pacote | Raiz de código-fonte de produção do JudAI | N/A |
| `src/__init__.py` | Arquivo Python | Transforma `src` em pacote de primeiro nível e define metadados base | Docstring + `__version__ = "0.1.0"` |
| `src/scraper/` | Subpacote | Módulo de scraping, parsing e ingestão (ingestao_lei, carregar_mongo) | N/A |
| `src/scraper/__init__.py` | Arquivo Python | Transforma `src.scraper` em subpacote Python | Docstring descritiva |
| `src/database/` | Subpacote | Módulo de persistência e conexões Singleton (MongoDB e ChromaDB) | N/A |
| `src/database/__init__.py` | Arquivo Python | Transforma `src.database` em subpacote Python | Docstring descritiva |
| `src/models/` | Subpacote | Módulo de modelos e ranking (placeholders BM25 e BERT) | N/A |
| `src/models/__init__.py` | Arquivo Python | Transforma `src.models` em subpacote Python | Docstring descritiva |
| `src/api/` | Subpacote | Módulo da aplicação FastAPI e contratos Pydantic | N/A |
| `src/api/__init__.py` | Arquivo Python | Transforma `src.api` em subpacote Python | Docstring descritiva |

---

## 3. Análise Detalhada dos Arquivos `.gitkeep`

### 3.1 Mecanismo e Necessidade
O Git não armazena nós de diretórios de forma isolada no seu índice (DAG de commits baseia-se em árvores de *blobs* de arquivos). Se um diretório estiver vazio, ele não existirá após um `git clone`. Os arquivos `.gitkeep` funcionam como âncoras para que colaboradores recebam a estrutura pronta imediatamente ao clonar.

### 3.2 Conteúdo e Codificação
- **Conteúdo**: Arquivo vazio (0 bytes) ou contendo apenas uma quebra de linha `\n` (1 byte). Recomendamos 0 bytes para evitar qualquer interpretação de conteúdo.
- **Codificação**: UTF-8 (sem BOM) ou ASCII puro.
- **Permissões de Arquivo**: Permissões normais de leitura/escrita (`0644` no Linux/macOS, ACL padrão herdada no Windows).

---

## 4. Análise Detalhada dos Arquivos `__init__.py`

### 4.1 Requisitos de Inicialização de Pacotes
Embora o Python 3.3+ suporte *namespace packages* implícitos (PEP 420), pacotes regulares com `__init__.py` explícito são a convenção mandatória da indústria para:
1. Eliminar ambiguidade em ferramentas de análise estática e IDEs (`mypy`, `flake8`, `pylint`).
2. Garantir comportamento determinístico na execução de testes com `pytest`.
3. Permitir a execução modular correta via `python -m src.scraper.carregar_mongo` e `uvicorn src.api.main:app`.
4. Documentação de pacotes (prevenindo o aviso PEP 257 / flake8-docstrings D104 "Missing docstring in public package").

### 4.2 Restrição Crítica para o Milestone 1: Zero Imports Prematuros
Nos subpacotes `src.scraper`, `src.database`, `src.models` e `src.api`, os módulos correspondentes (`ingestao_lei.py`, `mongo_connection.py`, `bm25_search.py`, `main.py`, etc.) **ainda não existem no Milestone 1**.
Por conseguinte, nenhum `__init__.py` criado em M1 pode tentar importar módulos ou classes ainda não criados, sob pena de quebrar a importabilidade de `src` (`ModuleNotFoundError`).
Os arquivos devem conter **apenas docstrings informativas** e metadados seguros.

### 4.3 Conteúdo Recomendado para Cada `__init__.py`

#### `src/__init__.py`
```python
"""JudAI - Plataforma de RAG Híbrido Jurídico.

Infraestrutura base para recuperação e processamento de dispositivos legais.
"""

__version__ = "0.1.0"
```

#### `src/scraper/__init__.py`
```python
"""Módulo de coleta, raspagem e ingestão de normas jurídicas do JudAI."""
```

#### `src/database/__init__.py`
```python
"""Módulo de persistência e gerenciamento de conexões (MongoDB e ChromaDB) do JudAI."""
```

#### `src/models/__init__.py`
```python
"""Módulo de modelos de busca lexical e semântica do JudAI."""
```

#### `src/api/__init__.py`
```python
"""Módulo de API REST (FastAPI) e rotas de consulta do JudAI."""
```

---

## 5. Descoberta Crítica de Interação com Git (`.gitignore`)

Durante a exploração empírica em ambiente de teste isolado com o Git 2.45.0, foi validada uma particularidade vital da especificação do Git:
> *Se um diretório pai é ignorado (ex: `data/*`), o Git interrompe a navegação nesse nó para otimização de performance. Qualquer regra subsequente de inclusão como `!data/**/.gitkeep` NÃO terá efeito se o diretório `data/raw` for descartado prematuramente.*

### Validação Empírica
1. Com a regra simples:
   ```gitignore
   data/*
   !data/**/.gitkeep
   ```
   O Git ignora `data/raw` como diretório e **NÃO** rastreia `data/raw/.gitkeep`.
2. Para que o Git rastreie os `.gitkeep` e ignore rigorosamente todos os demais arquivos de dados gerados (bancos SQLite do ChromaDB, arquivos temporários HTML, etc.), a regra correta e testada para o `.gitignore` é:
   ```gitignore
   # Ignorar dados locais, mantendo pastas versionadas via .gitkeep
   data/*
   !data/**/
   data/*/**
   !data/**/.gitkeep
   ```
   *Esta recomendação foi testada e aprovada com sucesso na suíte de testes exploratórios.*

---

## 6. Estratégia de Implementação para o Executor

O Executor do Milestone 1 deve executar as etapas com total idempotência.

### Passo 1: Criação dos Diretórios
Criar todos os diretórios necessários garantindo que não falhem se já existirem:
- `data/raw`
- `data/chromadb_local`
- `notebooks`
- `src`
- `src/scraper`
- `src/database`
- `src/models`
- `src/api`

### Passo 2: Criação dos Arquivos `.gitkeep`
Gerar os 3 arquivos `.gitkeep` vazios em:
- `data/raw/.gitkeep`
- `data/chromadb_local/.gitkeep`
- `notebooks/.gitkeep`

### Passo 3: Criação dos Arquivos `__init__.py`
Gerar os 5 arquivos `__init__.py` com codificação UTF-8 (sem BOM) e quebras de linha LF (`\n`):
- `src/__init__.py`
- `src/scraper/__init__.py`
- `src/database/__init__.py`
- `src/models/__init__.py`
- `src/api/__init__.py`

---

## 7. Comandos de Verificação e Critérios de Aceite

O Executor e o Verificador podem confirmar a integridade da estrutura por meio dos seguintes testes automatizados:

### Teste de Verificação 1: Existência Física de Diretórios e Arquivos
Comando PowerShell:
```powershell
$paths = @(
    "data/raw/.gitkeep",
    "data/chromadb_local/.gitkeep",
    "notebooks/.gitkeep",
    "src/__init__.py",
    "src/scraper/__init__.py",
    "src/database/__init__.py",
    "src/models/__init__.py",
    "src/api/__init__.py"
)
foreach ($p in $paths) {
    if (-not (Test-Path $p)) { throw "Arquivo ausente: $p" }
}
Write-Output "Todos os 8 arquivos estruturais existem com sucesso."
```

### Teste de Verificação 2: Validação de Importação de Todos os Pacotes Python
Comando Python:
```bash
python -c "import src; import src.scraper; import src.database; import src.models; import src.api; print('Sucesso: Todos os 5 pacotes sao importaveis sem erro.')"
```

### Teste de Verificação 3: Inspeção de Metadados e Docstrings
Comando Python:
```bash
python -c "import src, src.scraper, src.database, src.models, src.api; assert src.__version__ == '0.1.0'; assert all(m.__doc__ for m in [src, src.scraper, src.database, src.models, src.api]); print('Sucesso: Docstrings e versoes validadas.')"
```

---

## 8. Conclusão

A arquitetura de diretórios e pacotes do Milestone 1 está completamente delineada, testada empiricamente quanto ao comportamento do Git e empacotamento Python, com diretrizes claras e livres de efeitos colaterais para o Executor.
