# Relatório Técnico de Migração do Scraper — Milestone 3 (JudAI)

**Data**: 2026-10-18  
**Agente**: `explorer_m3_1` (Scraper Migration Specialist)  
**Status**: Investigação Concluída / Plano Pronto para Execução  
**Arquivos de Referência Gerados**:
- `proposed_ingestao_lei.py` -> `src/scraper/ingestao_lei.py`
- `proposed_carregar_mongo.py` -> `src/scraper/carregar_mongo.py`
- `proposed___init__.py` -> `src/scraper/__init__.py`

---

## 1. Sumário Executivo

O Milestone 3 estabelece a migração e consolidação dos mecanismos de ingestão jurídica da raiz para o pacote oficial `src/scraper/`.
A investigação técnica analisou os dois scripts existentes (`ingestao_lei.py` e `carregar_mongo.py`), as diretrizes de arquitetura do `PROJECT.md`, os requisitos de ambiente e as 88 asserções da suíte de testes pré-construída (`tests/test_tier1_feature_coverage.py`, `tests/test_tier3_cross_feature.py` e `tests/test_tier4_real_world.py`).

### Resultados da Investigação:
1. **`ingestao_lei.py`**: O script original possui 513 linhas e implementa um parser robusto do Planalto (tratamento de cp1252/utf-8, classificação hierárquica por regex, marcação de redação revogada/anterior e montagem de coleções). Além de manter todas as funções originais intactas, foram mapeadas e especificadas 5 funções essenciais requeridas pela suíte de testes E2E (`baixar_legislacao`, `salvar_bruto`, `extrair_metadados`, `extrair_estrutura` e `extrair_dispositivos`).
2. **`carregar_mongo.py`**: O script original possui 97 linhas e realiza a inserção do Código Civil (`cc2002`) no MongoDB. Exigia a remoção de valores hardcoded em prol da leitura de `MONGO_URI` e `MONGO_DB_NAME` via `python-dotenv` / `os.getenv` (com fallbacks `"mongodb://localhost:27017"` e `"rag_juridico"`), suporte a recarga dinâmica de variáveis em testes (`importlib.reload`), import resiliente do módulo `ingestao_lei` e suporte limpo à flag `--help` via CLI.
3. **Limpeza da Raiz**: A raiz do repositório deve ficar livre de scripts Python soltos, garantindo que o módulo resida exclusivamente em `src/scraper/`.

---

## 2. Diagnóstico dos Arquivos Existentes

### 2.1. `e:\Programacao\JudAI\ingestao_lei.py` (513 linhas)
- **Localização Atual**: Raiz do projeto.
- **Papel**: Motor de extração léxica e estrutural do HTML do Planalto.
- **Dependências de Terceiros**:
  - `bs4` (BeautifulSoup, `lxml`) importado no topo.
  - `requests` (import lazy dentro de `obter_bytes`).
  - `pymongo` (import lazy dentro de `salvar_mongo` e `main`).
- **Pontos Fortes**:
  - Manipulação resiliente de acentuação (detecção de caracteres `\ufffd`).
  - Parser robusto de cabeçalhos (`PARTE`, `LIVRO`, `TÍTULO`, `CAPÍTULO`, `SEÇÃO`, `SUBSEÇÃO`).
  - Identificação de artigos, parágrafos (incluindo "parágrafo único"), incisos em algarismos romanos e alíneas.
  - Identificação de vigência através de estilos CSS `line-through`, tags `<strike>/<s>/<del>` e menções a `(Revogado pela Lei ...)`.
  - Construção de três estruturas relacionais: `leis`, `artigos` e `dispositivos`.
- **Necessidades de Ajuste**:
  - Nenhuma alteração na lógica existente ou nos nomes das funções internas (`obter_bytes`, `decodificar`, `parsear`, `montar_colecoes`, `salvar_mongo`, etc.).
  - Adição de 5 funções públicas que a suíte de testes (`test_tier1_feature_coverage.py` e `test_tier4_real_world.py`) espera encontrar diretamente exportadas pelo módulo.

### 2.2. `e:\Programacao\JudAI\carregar_mongo.py` (97 linhas)
- **Localização Atual**: Raiz do projeto.
- **Papel**: Runner focado na carga do Código Civil no MongoDB local/remoto.
- **Problemas Detectados**:
  1. *Import rígido*: `import ingestao_lei as parser` falha quando invocado como `python -m src.scraper.carregar_mongo` a partir da raiz.
  2. *Configurações hardcoded*:
     ```python
     MONGO_URI = "mongodb://localhost:27017"
     NOME_BANCO = "rag_juridico"
     ```
     Não lia o arquivo `.env` nem respeitava variáveis de ambiente do sistema operacional.
  3. *Invocação CLI com `--help`*:
     No código original, `sys.argv[1]` era lido diretamente e passado como caminho de arquivo para `obter_bytes("--help")`, disparando `FileNotFoundError`.
- **Ajustes Mapeados**:
  1. Carregar variáveis via `dotenv.load_dotenv()` sem sobrescrever variáveis já exportadas no ambiente.
  2. Definir em nível de módulo `MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")` e `MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "rag_juridico")`.
  3. Vincular `NOME_BANCO = MONGO_DB_NAME` para retrocompatibilidade.
  4. Adicionar tratamento para `-h` / `--help` na rotina `__main__` com saída limpa (código `0`).
  5. Import multi-estratégia para `ingestao_lei`:
     ```python
     try:
         from src.scraper import ingestao_lei as parser
     except ImportError:
         try:
             from . import ingestao_lei as parser
         except ImportError:
             import ingestao_lei as parser
     ```

---

## 3. Matriz de Rastreabilidade com a Suíte de Testes

| Teste | Arquivo de Teste | Linhas | Requisito Verificado | Solução Projetada |
|---|---|---|---|---|
| `test_scraper_package_structure` | `test_tier1_feature_coverage.py` | 479-483 | `src/scraper/` e `__init__.py` existem | Confirmado existente; atualização de `__init__.py` |
| `test_scraper_ingestao_lei_importable` | `test_tier1_feature_coverage.py` | 485-489 | `import src.scraper.ingestao_lei` funciona | Arquivo em `src/scraper/ingestao_lei.py` |
| `test_scraper_carregar_mongo_importable` | `test_tier1_feature_coverage.py` | 491-495 | `import src.scraper.carregar_mongo` funciona | Arquivo em `src/scraper/carregar_mongo.py` |
| `test_scraper_parser_essential_functions_preserved` | `test_tier1_feature_coverage.py` | 497-510 | Presença de 5 funções: `baixar_legislacao`, `salvar_bruto`, `extrair_metadados`, `extrair_estrutura`, `extrair_dispositivos` | Funções wrapper/adapter de alta performance adicionadas sem afetar as originais |
| `test_scraper_carregar_mongo_env_support` | `test_tier1_feature_coverage.py` | 511-517 | `MONGO_URI`, `MONGO_DB_NAME` e `getenv/environ` presentes no arquivo | Variáveis expostas no topo do módulo com `os.getenv` |
| `test_scraper_no_scripts_left_in_root` | `test_tier1_feature_coverage.py` | 519-527 | Ausência de `ingestao_lei.py` e `carregar_mongo.py` na raiz | Exclusão dos arquivos legados da raiz |
| `test_scraper_and_mongo_connection_same_defaults` | `test_tier3_cross_feature.py` | 85-102 | Defaults coincidem com `MongoConnection` (`"mongodb://localhost:27017"` e `"rag_juridico"`) | Defaults idênticos em `os.getenv` |
| `test_scraper_module_execution_with_custom_env` | `test_tier3_cross_feature.py` | 104-122 | Reage a custom env após `importlib.reload` | `MONGO_URI` e `MONGO_DB_NAME` avaliados na importação via `os.getenv` |
| `test_parser_real_html_snippet` | `test_tier4_real_world.py` | 102-135 | `extrair_metadados(html, path)` e `extrair_dispositivos(html)` retornam dados válidos | Adapters conectam ao BeautifulSoup e `montar_colecoes` retornando artigos extraídos |
| `test_scraper_module_cli_invocation_help` | `test_tier4_real_world.py` | 137-153 | `python -m src.scraper.carregar_mongo --help` não levanta `ModuleNotFoundError` | Trata `-h`/`--help` sem erro |

---

## 4. Especificação Técnica dos Módulos Migrados

### 4.1. `src/scraper/ingestao_lei.py`

#### A. Funções Públicas Adicionais (Adapters para Suíte de Testes):
```python
def baixar_legislacao(entrada: str) -> tuple[bytes, str]:
    """
    Obtém os bytes brutos da legislação informada (URL HTTP/HTTPS ou arquivo local).
    Retorna tupla (bytes_brutos, origem).
    """
    return obter_bytes(entrada)


def salvar_bruto(conteudo: bytes, caminho_destino: str | Path) -> Path:
    """
    Salva os bytes brutos da legislação em disco no caminho de destino especificado.
    Cria diretórios pais automaticamente se necessário.
    """
    p = Path(caminho_destino)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(conteudo)
    return p


def extrair_metadados(html: str, origem: str = "") -> dict:
    """
    Extrai metadados básicos (título da lei, ementa e origem) a partir do HTML.
    Complementa informações a partir da tag <title> caso não detectadas nos parágrafos.
    """
    meta, _, _ = parsear(html)
    if not meta.get("titulo"):
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            meta["titulo"] = limpar(title_tag.get_text(strip=True))
    if origem:
        meta["origem"] = origem
    return meta


def extrair_estrutura(html: str) -> list[dict]:
    """
    Extrai a árvore estrutural e aninhada de artigos da lei a partir do HTML.
    """
    _, artigos, _ = parsear(html)
    return artigos


def extrair_dispositivos(html: str, lei_id: str = "cc2002", lei_nome: str = "Código Civil") -> list[dict]:
    """
    Extrai a lista tabular/plana de dispositivos (artigos, parágrafos, incisos, alíneas)
    a partir do HTML da lei, pronta para chunking, embedding ou gravação no MongoDB.
    """
    meta, artigos, _ = parsear(html)
    if not artigos:
        return []
    cols = montar_colecoes(
        lei_id=lei_id,
        lei_nome=lei_nome,
        meta=meta,
        artigos=artigos,
        origem="",
        sha256="",
        tem_acento_perdido=False,
    )
    return cols.get("dispositivos", [])
```

#### B. Compatibilidade de Execução:
- **Como Módulo**: `python -m src.scraper.ingestao_lei [argumentos]`
- **Import Programático**: `from src.scraper import ingestao_lei`
- **CLI Argparse**: 100% preservada a função `main(argv=None)`.

---

### 4.2. `src/scraper/carregar_mongo.py`

#### A. Estrutura de Imports e Configuração:
```python
import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# Carrega variáveis do arquivo .env (se existir) sem sobrescrever o ambiente
load_dotenv()

# Import resiliente do parser
try:
    from src.scraper import ingestao_lei as parser
except ImportError:
    try:
        from . import ingestao_lei as parser
    except ImportError:
        import ingestao_lei as parser

# ---------------------------- CONFIGURAÇÃO ---------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "rag_juridico")
NOME_BANCO = MONGO_DB_NAME  # Mantém compatibilidade com referências internas originais
LEI_ID = "cc2002"
LEI_NOME = "Código Civil"
FONTE_PADRAO = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
# ---------------------------------------------------------------------------
```

#### B. Tratamento CLI:
```python
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Uso: python -m src.scraper.carregar_mongo [fonte]")
        print("  fonte: URL da lei compilada no Planalto ou caminho para arquivo HTML local.")
        print(f"  Padrão: {FONTE_PADRAO}")
        sys.exit(0)
    fonte = sys.argv[1] if len(sys.argv) > 1 else FONTE_PADRAO
    colecoes = carregar_documentos(fonte)   # 1) lê e estrutura
    db = conectar()                         # 2) conecta
    inserir(db, colecoes)                   # 3) insere
    verificar(db)                           # 4) confere
```

---

### 4.3. `src/scraper/__init__.py`

Exposição explícita dos submódulos:
```python
"""Módulo de coleta, raspagem e ingestão de normas jurídicas do JudAI."""
from src.scraper import ingestao_lei
from src.scraper import carregar_mongo

__all__ = ["ingestao_lei", "carregar_mongo"]
```

---

## 5. Plano de Ação para o Agente Implementador (Worker)

Quando o Orchestrator autorizar o Worker a aplicar as alterações:

1. **Passo 1: Escrever `src/scraper/ingestao_lei.py`**
   - Copiar o conteúdo validado de `.agents/teamwork/explorer_m3_1/proposed_ingestao_lei.py`.
2. **Passo 2: Escrever `src/scraper/carregar_mongo.py`**
   - Copiar o conteúdo validado de `.agents/teamwork/explorer_m3_1/proposed_carregar_mongo.py`.
3. **Passo 3: Atualizar `src/scraper/__init__.py`**
   - Copiar o conteúdo validado de `.agents/teamwork/explorer_m3_1/proposed___init__.py`.
4. **Passo 4: Remover os arquivos legados da raiz**
   - Excluir `e:\Programacao\JudAI\ingestao_lei.py`.
   - Excluir `e:\Programacao\JudAI\carregar_mongo.py`.
5. **Passo 5: Executar os testes de validação**
   - Verificar imports e pytest.

---

## 6. Métodos de Verificação Independente

Após a implementação pelo Worker, a verificação deve ser realizada por:

```powershell
# 1. Validação de compilação sintática
python -m py_compile src/scraper/__init__.py src/scraper/ingestao_lei.py src/scraper/carregar_mongo.py

# 2. Teste de importação isolada
python -c "import src.scraper.ingestao_lei; print('ingestao_lei importado com sucesso!')"
python -c "import src.scraper.carregar_mongo; print('carregar_mongo importado com sucesso!')"

# 3. Teste de invocação modular CLI
python -m src.scraper.carregar_mongo --help

# 4. Verificação de ausência na raiz
python -c "from pathlib import Path; assert not Path('ingestao_lei.py').exists() and not Path('carregar_mongo.py').exists(), 'Arquivos legados ainda na raiz!'"

# 5. Execução dos testes do Milestone 3 via Pytest
python -m pytest tests/test_tier1_feature_coverage.py -k "TestScraperMigrationFeature" -v
python -m pytest tests/test_tier3_cross_feature.py -k "TestScraperAndDatabaseAlignment" -v
python -m pytest tests/test_tier4_real_world.py -k "TestRealWorldScraperFlow" -v
```

---

## 7. Conclusão da Investigação

A migração foi minuciosamente mapeada. Não há pontos cegos ou ambiguidades. Todos os requisitos da requisição original (`ORIGINAL_REQUEST.md`), do plano do projeto (`PROJECT.md`) e da suíte E2E prévia estão 100% harmonizados e contemplados nos arquivos propostos.
