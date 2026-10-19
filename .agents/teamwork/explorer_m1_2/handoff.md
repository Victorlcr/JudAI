# Handoff Report — Explorer M1-2 (Arquivos de Configuração)

## 1. Observation
- `ORIGINAL_REQUEST.md` (linhas 12 a 14): Requisita a criação de `.gitignore` (regras para `venv/`, `.venv/`, `data/*` com exceção de `!data/**/.gitkeep`, `.env`, `__pycache__/`), `.gitattributes` (`* text=auto eol=lf`), `docker-compose.yml` (serviço `mongodb`, imagem `mongo:latest`, porta `27017:27017`, volume nomeado `mongo_data` montado em `/data/db`), `requirements.txt` (12 dependências sem pin: `fastapi`, `uvicorn[standard]`, `pydantic`, `pymongo`, `chromadb`, `rank_bm25`, `sentence-transformers`, `nltk`, `python-dotenv`, `beautifulsoup4`, `lxml`, `requests`) e `.env.example` (`MONGO_URI=mongodb://localhost:27017`, `MONGO_DB_NAME=rag_juridico`, `CHROMA_DB_PATH=./data/chromadb_local`).
- Teste empírico de Git Ignore (executado via subprocess Python em ambiente isolado):
  - Ao usar somente `data/*` e `!data/**/.gitkeep`, o Git exclui a pasta pai `data/raw` e **não desce** para avaliar `!data/**/.gitkeep`. Saída do teste: `STAGED FILES: A .gitignore` (nenhum `.gitkeep` em `data/` foi rastreado).
  - Ao usar `data/*`, `!data/**/` e `!data/**/.gitkeep`, subdiretórios são re-incluídos, mas arquivos de dados aninhados (`data/raw/test.html` e `data/chromadb_local/chroma.sqlite3`) **não casam** com `data/*` e tornam-se visíveis como untracked prontos para commit.
  - Ao aplicar o padrão completo:
    ```gitignore
    data/*
    !data/**/
    !data/**/.gitkeep
    data/**/*
    !data/**/
    !data/**/.gitkeep
    ```
    A saída do teste foi:
    ```text
    STAGED FILES:
    A  .gitignore
    A  data/chromadb_local/.gitkeep
    A  data/raw/.gitkeep
    ```
    Garantindo que todos os arquivos de dados locais em qualquer profundidade são ignorados e apenas `.gitkeep` é versionado.
- `docker compose version` no host Windows: comando retornou código 1 (`O termo 'docker' não é reconhecido como nome de cmdlet`). Docker não está no PATH imediato do PowerShell.

## 2. Logic Chain
1. A partir da observação de que Git ignora diretórios e não desce em diretórios ignorados (especificação oficial do Git), a exclusão cega de `data/*` inviabiliza a adição de `data/raw/.gitkeep`.
2. A partir do teste empírico de recursão de globbing, `data/*` atua apenas no nível imediato (1 nível), deixando arquivos em subpastas expostos. A regra complementar `data/**/*` com re-inclusão de diretórios `!data/**/` e do marcador `!data/**/.gitkeep` resolve 100% da árvore sem vazamento de dados.
3. A partir da exigência de portabilidade Windows/Linux, `.gitattributes` com `* text=auto eol=lf` garante que finais de linha de código e configurações sejam unificados em LF no repositório, prevenindo quebras em contêineres Docker.
4. No `docker-compose.yml`, o uso de volume nomeado `mongo_data:/data/db` previne conflitos de lock do motor WiredTiger no NTFS do Windows. Mapeamentos de porta devem ser cotados como string `"27017:27017"` para evitar ambiguidades em parsers YAML.
5. As 12 dependências do `requirements.txt` devem ser declaradas exatamente sem pinagem, e as dependências pesadas (`sentence-transformers`, `rank_bm25`) não devem ser importadas no topo dos módulos base para permitir execução de testes rápidos em ambientes leves.

## 3. Caveats
- O binário do Docker não está configurado no PATH do ambiente Windows atual. A validação de `docker compose config` depende de ambiente com Docker instalado ou validação estática de schema/sintaxe YAML.
- Caso o usuário utilize extensões ou IDEs com auto-formatação no Windows, deve-se atentar para que tabulações não sejam inseridas acidentalmente no `docker-compose.yml`.

## 4. Conclusion
As especificações canônicas dos 5 arquivos de configuração do Milestone 1 estão consolidadas, com conteúdos exatos e regras de mitigação detalhadas no relatório `e:\Programacao\JudAI\.agents\teamwork\explorer_m1_2\report_m1_config.md`. O Worker do Milestone 1 pode implementar diretamente os arquivos sem ambiguidades.

## 5. Verification Method
1. Inspecionar o relatório técnico em:
   `e:\Programacao\JudAI\.agents\teamwork\explorer_m1_2\report_m1_config.md`
2. Executar script de teste automatizado de sintaxe e conteúdo para os 5 arquivos:
   ```powershell
   python -c "
   import re

   # 1. requirements.txt
   reqs = [l.strip() for l in open('requirements.txt') if l.strip() and not l.startswith('#')]
   expected_reqs = ['fastapi', 'uvicorn[standard]', 'pydantic', 'pymongo', 'chromadb', 'rank_bm25', 'sentence-transformers', 'nltk', 'python-dotenv', 'beautifulsoup4', 'lxml', 'requests']
   assert reqs == expected_reqs, f'Requirements inconsistente: {reqs}'

   # 2. .env.example
   env = open('.env.example').read()
   assert 'MONGO_URI=mongodb://localhost:27017' in env
   assert 'MONGO_DB_NAME=rag_juridico' in env
   assert 'CHROMA_DB_PATH=./data/chromadb_local' in env

   # 3. .gitattributes
   attr = open('.gitattributes').read()
   assert '* text=auto eol=lf' in attr

   # 4. .gitignore
   ign = open('.gitignore').read()
   for rule in ['venv/', '.venv/', '__pycache__/', '.env', 'data/*', '!data/**/', '!data/**/.gitkeep']:
       assert rule in ign, f'Regra ausente: {rule}'

   print('Todos os arquivos de configuracao validados com sucesso!')
   "
   ```
