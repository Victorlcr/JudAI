# Handoff Report — spec_miner_survey_3

**Data**: 2026-10-18  
**Agente**: `spec_miner_survey_3` (Specification Miner - Survey API, Database & ML Specs)  
**Destinatário**: Orchestrator (`842a2a88-b148-48d8-9385-f2322710bb06`)  
**Status**: Concluído (Hard Handoff)  

---

## 1. Observation

- **Requisitos Formais em `ORIGINAL_REQUEST.md`**:
  - Linha 13: `src/database/{__init__,mongo_connection,chroma_connection}.py`, `src/models/{__init__,bm25_search,bert_search}.py`, `src/api/{__init__,main}.py`. `.env.example`: `MONGO_URI=mongodb://localhost:27017`, `MONGO_DB_NAME=rag_juridico`, `CHROMA_DB_PATH=./data/chromadb_local`.
  - Linha 16: `src/api/main.py`: FastAPI, Pydantic `QueryRequest(query: str)`, `GET /health` retorna status da API, `POST /search/bm25` e `POST /search/bert` com retorno mockado (ex.: `{model, query, results: [], detail: "not implemented"}`).
  - Linha 17: `mongo_connection.py` e `chroma_connection.py`: classes Singleton (`pymongo.MongoClient`; `chromadb.PersistentClient`) usando variáveis de ambiente via `python-dotenv`; criar a pasta do Chroma se não existir; sem lógica de inserção/busca.
  - Linha 18: `bm25_search.py` e `bert_search.py`: apenas placeholders com docstring.
  - Linha 26: `uvicorn src.api.main:app` sobe e `/health`, `/search/bm25`, `/search/bert` respondem 200 (POST com `{"query":"x"}`).
  - Linha 27: "Duas instanciações de cada classe de conexão retornam o mesmo objeto."
  - Linha 29: "Nenhum código de ML além de placeholders".
- **Comportamento Observado em Testes de Padrões e Provas**:
  - Teste do Singleton Ingênuo no Python (`python -c "... class SingletonNaive ..."`):
    `s1 is s2` avalia para `True`, porém o método `__init__` é executado novamente a cada chamada (`Init called with val: second`), sobrescrevendo atributos se não houver guarda de inicialização.
  - Teste do Singleton Guardado (`python -c "... class SingletonGuarded ..."`):
    Com a verificação de `if getattr(self, "_initialized", False): return` associada a um `threading.Lock()`, a reinicialização é impedida (`Guarded init called with val: first`), garantindo estabilidade e reuso do cliente.
  - Teste de Fallback com Variáveis Vazias (`python -c "... os.environ['TEST_EMPTY'] = '' ..."`):
    `os.getenv('TEST_EMPTY', 'default')` retorna `""` quando a variável está presente mas vazia. O padrão seguro `os.getenv('VAR') or 'default'` garante fallback efetivo para os valores padrão.
  - Teste de Validação Pydantic com `QueryRequest(query: str)`:
    Inputs válidos como `{"query": "direito civil"}` ou `{"query": "x"}` serializam com sucesso. Inputs sem o campo `query` geram `ValidationError: Field required` (HTTP 422 no FastAPI). Inputs como inteiros geram `Input should be a valid string`.
  - Inspeção de Scripts Existentes:
    `carregar_mongo.py` (linhas 26-27) define hardcoded `MONGO_URI = "mongodb://localhost:27017"` e `NOME_BANCO = "rag_juridico"`, confirmando a compatibilidade dos nomes de configuração e defaults especificados.
- **Artefato Criado**:
  - `e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\spec_api_database.md` com 370 linhas contendo a especificação completa, contratos de interface tipados, tabela de funcionalidades mapeadas, casos de borda e matriz de testes unitários/E2E.

---

## 2. Logic Chain

1. **Observação**: `ORIGINAL_REQUEST.md` exige que `mongo_connection.py` e `chroma_connection.py` sejam Singletons onde "duas instanciações de cada classe de conexão retornam o mesmo objeto" e reutilizem o `MongoClient` e `PersistentClient`.
2. **Observação**: No modelo de objetos do Python, sobrescrever `__new__` para retornar uma instância em cache faz com que o interpretador invoque `__init__` na mesma instância toda vez que a classe é chamada.
3. **Dedução**: Se a instanciação do `MongoClient` ou `PersistentClient` estiver dentro do `__init__` sem proteção, cada chamada `MongoConnection()` reinicializará o cliente de rede. Logo, a especificação técnica obriga o uso de `self._initialized` e `threading.Lock()` para tornar o Singleton thread-safe e verdadeiramente idempotente.
4. **Observação**: `ORIGINAL_REQUEST.md` estipula que a pasta do ChromaDB deve ser criada se não existir e deve ser compatível com Windows e Linux.
5. **Dedução**: O uso de `pathlib.Path(path).resolve()` e `mkdir(parents=True, exist_ok=True)` elimina discrepâncias de caminhos relativos ou barras (`\` vs `/`), garantindo portabilidade entre SOs sem separadores hardcoded.
6. **Observação**: `ORIGINAL_REQUEST.md` proíbe terminantemente qualquer lógica de ML além de placeholders com docstring e exige que a API responda mocks estáticos com status 200.
7. **Dedução**: Nenhuma dependência pesada de ML (`torch`, `sentence-transformers`, `transformers`) pode ser importada no escopo global de `bm25_search.py` ou `bert_search.py`, sob pena de atrasar ou inviabilizar a subida da API em ambientes com recursos restritos ou sem modelo baixado. Os endpoints de `/search/bm25` e `/search/bert` devem retornar estruturas mockadas fixas contendo `{"model": ..., "query": request.query, "results": [], "detail": "not implemented"}`.

---

## 3. Caveats

- **Ambiente Global**: As bibliotecas `fastapi`, `chromadb` e `pymongo` devem ser instaladas no ambiente virtual (`venv`) do projeto conforme `requirements.txt`. A especificação técnica foi validada teoricamente e experimentalmente com Python 3.11 e Pydantic v2 instalados no host.
- **Ping no Banco**: PyMongo realiza conexão lazy por padrão; portanto, `MongoConnection()` pode ser instanciada sem erro mesmo com o container do MongoDB ainda iniciando, a menos que uma query ou `admin.command("ping")` seja executada. A especificação orienta a não executar ping no `__init__`, preservando a rapidez de inicialização do esqueleto.

---

## 4. Conclusion

As especificações técnicas, contratos de interface, schemas Pydantic, comportamentos Singleton com proteção de reinicialização e matriz de validação de testes estão 100% formalizados e documentados no arquivo:
`e:\Programacao\JudAI\.agents\teamwork\spec_miner_survey_3\spec_api_database.md`.
O projeto está completamente apto a avançar para a fase de decomposição no `PROJECT.md` e implementação dos marcos M2 (Conexões Singleton), M3 (Placeholders de ML) e M4 (Boilerplate FastAPI).

---

## 5. Verification Method

Para verificar de forma independente as conclusões e contratos especificados neste relatório:
1. Inspecionar o documento de especificação:
   `view_file(AbsolutePath="e:\\Programacao\\JudAI\\.agents\\teamwork\\spec_miner_survey_3\\spec_api_database.md")`
2. Verificar a consistência com `ORIGINAL_REQUEST.md`:
   `view_file(AbsolutePath="e:\\Programacao\\JudAI\\.agents\\teamwork\\ORIGINAL_REQUEST.md")`
3. Validar a execução dos testes de Singleton e Pydantic demonstrados na seção Observation:
   `python -c "from pydantic import BaseModel; class Q(BaseModel): query: str; print(Q(query='ok').model_dump())"`
