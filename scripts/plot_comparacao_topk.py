#!/usr/bin/env python3
"""
Script de Comparação Quantitativa (Top-K) para Artigo Científico.

Gera gráfico de barras agrupadas comparando a recuperação Top-1, Top-3 e Top-5
entre o Modelo Clássico (TF-IDF + MLP) e o Modelo Moderno SOTA (BERTimbau).
"""
from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO DE ENTRADA DE VARIÁVEIS (Insira ou atualize seus números reais aqui)
# ==============================================================================
# Métricas do Modelo Clássico (TF-IDF + MLP)
top1_tfidf: float = 52.4
top3_tfidf: float = 74.1
top5_tfidf: float = 81.8

# Métricas do Modelo SOTA (BERTimbau / Transformer)
top1_bert: float = 78.6
top3_bert: float = 89.2
top5_bert: float = 93.5


def gerar_grafico_topk(
    top1_cla: float = top1_tfidf,
    top3_cla: float = top3_tfidf,
    top5_cla: float = top5_tfidf,
    top1_mod: float = top1_bert,
    top3_mod: float = top3_bert,
    top5_mod: float = top5_bert,
    salvar_caminho: Path | str | None = None
) -> Path:
    """Gera e salva o gráfico comparativo Top-K com tipografia e estética científica."""
    sns.set_theme(style="ticks", palette="muted")
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "figure.titlesize": 14
    })

    metricas = ["Top-1", "Top-3", "Top-5"]
    valores_tfidf = [top1_cla, top3_cla, top5_cla]
    valores_bert = [top1_mod, top3_mod, top5_mod]

    x = np.arange(len(metricas))
    largura = 0.32

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    cor_tfidf = "#4A7BB0"
    cor_bert = "#D95F02"

    barras1 = ax.bar(
        x - largura/2, valores_tfidf, largura,
        label="TF-IDF + MLP (Clássico)",
        color=cor_tfidf, edgecolor="black", linewidth=0.8, alpha=0.9
    )
    barras2 = ax.bar(
        x + largura/2, valores_bert, largura,
        label="BERTimbau (Transformer SOTA)",
        color=cor_bert, edgecolor="black", linewidth=0.8, alpha=0.9
    )

    # Anotação com o valor no topo de cada barra
    for barra in barras1:
        altura = barra.get_height()
        ax.annotate(
            f"{altura:.1f}%",
            xy=(barra.get_x() + barra.get_width() / 2, altura),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center", va="bottom",
            fontweight="bold", fontsize=10
        )

    for barra in barras2:
        altura = barra.get_height()
        ax.annotate(
            f"{altura:.1f}%",
            xy=(barra.get_x() + barra.get_width() / 2, altura),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center", va="bottom",
            fontweight="bold", fontsize=10
        )

    ax.set_ylabel("Acurácia de Recuperação (%)")
    ax.set_title("Comparação de Desempenho Top-K: Classificação no Código Civil (2.063 Classes)", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(metricas)
    ax.set_ylim(0, 105)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=True, loc="upper left")

    sns.despine(top=True, right=True)
    plt.tight_layout()

    if salvar_caminho is None:
        salvar_caminho = Path(__file__).resolve().parent.parent / "data" / "resultados" / "grafico_topk_comparativo.png"
    salvar_caminho = Path(salvar_caminho)
    salvar_caminho.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(salvar_caminho, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Gráfico Top-K salvo com sucesso em: {salvar_caminho}")
    return salvar_caminho


if __name__ == "__main__":
    gerar_grafico_topk()
