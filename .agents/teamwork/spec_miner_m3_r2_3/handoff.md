# Relatório de Handoff: Especificação de Testes para Rodada 2 do Milestone 3

**Agente**: `spec_miner_m3_r2_3` (Specification Miner)  
**Parent / Orquestrador**: `842a2a88-b148-48d8-9385-f2322710bb06`  
**Data**: 2026-10-18T23:50:00Z  
**Diretório de Trabalho**: `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3`  
**Status**: Concluído (Read-Only)  

---

## 1. Observation

1. **Expressão Regular `RE_PAR` em `src/scraper/ingestao_lei.py`**:
   - Linha 75: `ORD = r"(?:\s*[º°ª]+|\s+o(?=\s|$))?"` — O escape `\ufffd` foi suprimido.
   - Linha 79: `RE_PAR = re.compile(rf"^(?:§|)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)` — A remoção acidental de `\ufffd` resultou no ramo vazio `(?:§|)`.
   - Comparado ao código original histórico (`ingestao_lei.py:75` e `79`), onde constava `[º°ª\ufffd]+` e `(?:§|\ufffd)`.
2. **Comportamento Observado da Regex Atual**:
   - `RE_PAR.match("1. Princípio fundamental")` avalia `^(?:§|)` casando a alternativa vazia no início da linha, casando o numeral `'1'` em `{NUM}` e retornando um objeto `Match`. No método `parsear()` (linhas 257-266), isso gera erroneamente um nó de tipo `paragrafo` com rótulo `"§ 1º"`.
   - `RE_PAR.match("\ufffd 1º Texto")` falha porque, após o casamento vazio em `^`, o caractere corrente é `\ufffd`, impedindo o casamento do numeral em `\s*({NUM})`.
3. **Persistência de Arquivos Legados na Raiz**:
   - Os arquivos `e:\Programacao\JudAI\ingestao_lei.py` (513 linhas) e `e:\Programacao\JudAI\carregar_mongo.py` (97 linhas) continuam existindo fisicamente na raiz do projeto.
   - O teste unitário em `tests/test_tier1_feature_coverage.py:519` (`test_scraper_no_scripts_left_in_root`) possui bloco condicional com instrução vazia `pass`, não validando ativamente a remoção dos arquivos legados.
4. **Artefatos Produzidos**:
   - Especificação técnica e formal detalhada em `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\spec_m3_r2_validation.md`.
   - Script de validação executável em `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\verify_m3_r2.py`.

---

## 2. Logic Chain

1. O requisito mandatório `ORIGINAL_REQUEST.md §R2` determinou o deslocamento dos scripts de raspagem da raiz para `src/scraper/`. A permanência dos arquivos na raiz viola a regra de escopo limpo e causa risco de divergência de versões.
2. Na migração de `ingestao_lei.py`, a sanitização de caracteres corrompidos removeu o símbolo `\ufffd` de dentro da alternância `(?:§|\ufffd)` em vez de manter a sequência de escape `\ufffd`.
3. Em sintaxe de expressões regulares, a sequência `(?:§|)` introduz uma alternativa nula à direita da barra vertical.
4. Toda string que não se inicia por `§` tem casamento imediato e com custo zero na alternativa nula, ancorada em `^`.
5. Qualquer linha que inicie com numerais (listas numéricas, valores, prazos, anos) tem seu numeral consumido pelo grupo `{NUM}`, convertendo uma enumeração explicativa de caput em um dispositivo formal de parágrafo.
6. A restauração exata para:
   - `ORD = r"(?:\s*[º°ª\ufffd]+|\s+o(?=\s|$))?"`
   - `RE_PAR = re.compile(rf"^(?:§|\ufffd)\s*({NUM}){ORD}{SUF}\s*[.\-–—]*\s*(.*)$", re.S)`
   elimina o ramo vazio, bloqueia categoricamente qualquer linha numérica sem `§` ou `\ufffd`, e restaura o parsing resiliente de textos de lei corrompidos com mojibake do Planalto.
7. A exclusão de `ingestao_lei.py` e `carregar_mongo.py` da raiz, combinada com a adição de asserções estritas `assert not (ROOT_DIR / "ingestao_lei.py").exists()` no teste `test_scraper_no_scripts_left_in_root`, fecha o gap de qualidade do Milestone 3.

---

## 3. Caveats

- Como `spec_miner_m3_r2_3` é um agente estritamente **read-only**, nenhuma alteração foi realizada nos arquivos do projeto (`src/scraper/ingestao_lei.py`, scripts da raiz ou arquivos sob `tests/`).
- As correções de código devem ser executadas pelo agente Worker da Rodada 2 (`worker_m3_r2`).
- As ferramentas de execução terminal (`run_command`) foram evitadas nesta sessão em respeito ao timeout de permissão verificado pelo revisor anterior; toda a modelagem e inspeção foi realizada com ferramentas determinísticas do sistema de arquivos.

---

## 4. Conclusion

A especificação para a Rodada 2 do Milestone 3 está 100% concluída:
1. Casos de teste negativos para numerais sem `§` detalhados e mapeados para rejeição imediata (`match is None`).
2. Casos de teste positivos para `\ufffd` detalhados com validação de grupos de captura e preservação de ordinalidade.
3. Casos de regressão para parágrafos padrão `§` mapeados.
4. Cenário de integração HTML formulado para garantir contagem exata de dispositivos sem nós espúrios.
5. Requisitos de remoção física e asserção em teste unitário para os scripts da raiz definidos com precisão.
6. O script `verify_m3_r2.py` está pronto para ser executado pelo Worker para validar sua implementação.

---

## 5. Verification Method

Para verificar independentemente esta especificação e validar as correções do Worker:

1. **Inspecionar a Especificação Formal**:
   - Ler o arquivo `e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\spec_m3_r2_validation.md`.
2. **Executar o Verificador Rápido da Rodada 2**:
   ```powershell
   python e:\Programacao\JudAI\.agents\teamwork\spec_miner_m3_r2_3\verify_m3_r2.py --verbose
   ```
3. **Verificar os Testes Pytest do Projeto**:
   ```powershell
   python -m pytest tests/test_tier1_feature_coverage.py -k "test_scraper_no_scripts_left_in_root"
   ```
