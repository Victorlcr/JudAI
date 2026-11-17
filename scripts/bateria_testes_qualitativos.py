#!/usr/bin/env python3
"""
Bateria de Testes Qualitativos: Avaliação Semântica Comparativa no Código Civil Brasileiro.

Compara o Modelo Clássico (TF-IDF + MLP) e o Modelo Moderno SOTA (BERTimbau + ChromaDB + mT0)
em categorias desafiadoras de Processamento de Linguagem Natural Jurídica.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para importações dos módulos src
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ==============================================================================
# 1. DICIONÁRIO DE CONSULTAS QUALITATIVAS (DESAFIOS SEMÂNTICOS)
# ==============================================================================
consultas_qualitativas: dict[str, str] = {
    # 1. Busca Literal: terminologia estrita e sintaxe idêntica à letra da lei (Art. 5º)
    "Busca Literal": (
        "A menoridade cessa aos dezoito anos completos, quando a pessoa fica "
        "habilitada à prática de todos os atos da vida civil."
    ),

    # 2. Sinônimos e Coloquialismo: linguagem do cidadão leigo sem termos jurídicos formais (Art. 1.283 / 1.297)
    "Sinônimos e Coloquialismo": (
        "O galho da árvore do meu vizinho está caindo no meu quintal e rachando a cerca. "
        "Posso cortar por conta própria sem pedir autorização para ele?"
    ),

    # 3. Polissemia: vocábulos com múltiplos sentidos técnicos e comuns ('prescrição' jurídica vs médica; 'alimentos')
    "Polissemia": (
        "Qual o prazo de prescrição para cobrar a prestação de alimentos vencida?"
    ),

    # 4. Inversão Sintática: ordem indireta proposital para testar robustez da ordem dos tokens (Art. 1.517 / 1.520)
    "Inversão Sintática": (
        "Com dezesseis anos completos, para que se realize validamente o casamento, "
        "de ambos os genitores a expressa autorização se faz imperiosa?"
    ),

    # 5. Caso Prático: situação fática em forma de narrativa sem citar o instituto jurídico (Art. 1.238 - Usucapião)
    "Caso Prático": (
        "João ocupa um terreno baldio urbano desde 2008 de forma contínua e sem qualquer oposição "
        "do proprietário registrado. Ele construiu ali sua casa e plantou hortaliças sem pagar aluguel. "
        "Ele já pode requerer a propriedade definitiva do imóvel?"
    ),

    # 6. Caso Prático de Responsabilidade Civil: verificação de nexo causal e dano (Art. 186 c/c 927)
    "Caso Prático de Responsabilidade Civil": (
        "Um motorista avançou o sinal vermelho e colidiu com a traseira do veículo de uma entregadora, "
        "causando perda total da moto e três meses de incapacidade para o trabalho. "
        "Quais as obrigações de reparação cabíveis?"
    )
}


def executar_bateria() -> list[dict]:
    """Executa a bateria de testes em ambos os modelos locais e retorna os resultados estruturados."""
    print("=" * 80)
    print("INICIANDO EXECUÇÃO DA BATERIA DE TESTES QUALITATIVOS (JUDAI)")
    print("=" * 80)

    # Inicialização dos modelos locais
    print("\n[1/2] Carregando Modelo Clássico (TF-IDF + MLP)...")
    from src.models.tfidf_mlp_search import TfidfMLPSearch
    modelo_classico = TfidfMLPSearch()
    modelo_classico.load()
    print("  -> Modelo Clássico carregado com sucesso.")

    print("\n[2/2] Carregando Modelo Moderno SOTA (BERTimbau + mT0)...")
    from src.models.bert_search import BERTSearch
    modelo_moderno = BERTSearch(limiar=0.50, lazy_load=False)
    print("  -> Modelo Moderno carregado com sucesso.")

    resultados = []

    print("\n" + "=" * 80)
    print("EXECUÇÃO DAS CONSULTAS QUALITATIVAS")
    print("=" * 80)

    for i, (categoria, query) in enumerate(consultas_qualitativas.items(), start=1):
        print(f"\n--- [Caso {i}/{len(consultas_qualitativas)}] Categoria: {categoria} ---")
        print(f"Query: \"{query}\"")

        # 1. Inferência Modelo Clássico
        t_inicio = time.perf_counter()
        res_classico = modelo_classico.search(query, top_k=3)
        t_classico = (time.perf_counter() - t_inicio) * 1000

        top1_cla = res_classico["results"][0] if res_classico.get("results") else {}
        print(f"\n  [Modelo Clássico | TF-IDF + MLP] ({t_classico:.1f}ms):")
        print(f"    - Artigo Top-1: {top1_cla.get('artigo_id', 'N/A')} ({top1_cla.get('citacao', 'N/A')})")
        print(f"    - Score/Probabilidade: {top1_cla.get('score', 0.0):.4f}")
        trecho_cla = (top1_cla.get("texto", "")[:130] + "...").replace("\n", " ")
        print(f"    - Trecho: {trecho_cla}")

        # 2. Inferência Modelo Moderno SOTA
        t_inicio = time.perf_counter()
        res_moderno = modelo_moderno.search(query, top_k=3)
        t_moderno = (time.perf_counter() - t_inicio) * 1000

        top1_mod = res_moderno["results"][0] if res_moderno.get("results") else {}
        print(f"\n  [Modelo Moderno | BERTimbau + mT0] ({t_moderno:.1f}ms):")
        print(f"    - Artigo Top-1: {top1_mod.get('artigo_id', 'N/A')} ({top1_mod.get('citacao', 'N/A')})")
        print(f"    - Similaridade Cosseno: {top1_mod.get('similarity_score', 0.0):.4f}")
        print(f"    - Abstenção: {res_moderno.get('abstencao', False)}")
        print(f"    - Resposta mT0: \"{res_moderno.get('resposta_gerada', '')}\"")

        resultados.append({
            "categoria": categoria,
            "query": query,
            "classico": {
                "top1_artigo_id": top1_cla.get("artigo_id"),
                "top1_citacao": top1_cla.get("citacao"),
                "score": top1_cla.get("score"),
                "latencia_ms": round(t_classico, 2),
                "top3": [r.get("artigo_id") for r in res_classico.get("results", [])]
            },
            "moderno": {
                "top1_artigo_id": top1_mod.get("artigo_id"),
                "top1_citacao": top1_mod.get("citacao"),
                "similarity_score": top1_mod.get("similarity_score"),
                "abstencao": res_moderno.get("abstencao", False),
                "resposta_gerada": res_moderno.get("resposta_gerada"),
                "latencia_ms": round(t_moderno, 2),
                "top3": [r.get("artigo_id") for r in res_moderno.get("results", [])]
            }
        })

    # Persistência do relatório qualitativo
    saida_dir = PROJECT_ROOT / "data" / "resultados"
    saida_dir.mkdir(parents=True, exist_ok=True)
    arquivo_saida = saida_dir / "resultado_bateria_qualitativa.json"
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"BATERIA CONCLUÍDA! Resultados salvos em: {arquivo_saida}")
    print("=" * 80)
    return resultados


if __name__ == "__main__":
    executar_bateria()
