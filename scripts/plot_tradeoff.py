#!/usr/bin/env python3
"""
Script de Gráfico de Trade-off (Custo Computacional vs. Benefício de Acurácia Top-3).

Utiliza os resultados reais obtidos sobre os 4 arquivos de avaliação em
Desktop/test (test_formal, test_informal, val_formal, val_informal):
  - Eixo X: Tempo de Treinamento em Minutos (TF-IDF = 4 min; BERT = 6 min; mT0 = 21 min)
  - Eixo Y: Acurácia Top-3 (%) real medida nos datasets
  - Tamanho da bolha: Volume de parâmetros (3.6M, 110M, 580M)
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# DADOS REAIS MEDIDOS EM C:\Users\victo\Desktop\test (4 arquivos: formal + informal)
# ==============================================================================
# 1) Escopo justo do Código Civil (cc2002: 190 perguntas = 95 formais + 95 informais)
dados_cc2002: list[dict] = [
    {
        "nome": "TF-IDF + MLP (Clássico)",
        "tempo_min": 4.0,
        "top3_acc": 45.26,     # 86 / 190 acertos Top-3 no cc2002 (formal + informal)
        "parametros_m": 3.6,
        "cor": "#2b5c8f",
    },
    {
        "nome": "BERT-Jurídico (Busca)",
        "tempo_min": 6.0,
        "top3_acc": 74.21,     # 141 / 190 acertos Top-3 no cc2002 (formal + informal)
        "parametros_m": 110.0,
        "cor": "#d95f02",
    },
    {
        "nome": "mT0-Jurídico (RAG Completo)",
        "tempo_min": 21.0,
        "top3_acc": 74.21,     # Pipeline RAG baseado no Top-3 recuperado pelo BERT-Jurídico
        "parametros_m": 580.0,
        "cor": "#7570b3",
    },
]

# 2) Base completa das 19 leis (1.198 perguntas = 599 formais + 599 informais)
dados_19leis: list[dict] = [
    {
        "nome": "TF-IDF + MLP (Clássico)",
        "tempo_min": 4.0,
        "top3_acc": 7.26,      # 87 / 1.198 acertos Top-3 nas 19 leis
        "parametros_m": 3.6,
        "cor": "#2b5c8f",
    },
    {
        "nome": "BERT-Jurídico (Busca)",
        "tempo_min": 6.0,
        "top3_acc": 74.12,     # 888 / 1.198 acertos Top-3 nas 19 leis
        "parametros_m": 110.0,
        "cor": "#d95f02",
    },
    {
        "nome": "mT0-Jurídico (RAG Completo)",
        "tempo_min": 21.0,
        "top3_acc": 74.12,     # Pipeline RAG baseado no Top-3 recuperado pelo BERT-Jurídico
        "parametros_m": 580.0,
        "cor": "#7570b3",
    },
]


def gerar_grafico_tradeoff(
    modelos: list[dict],
    titulo: str,
    salvar_caminho: Path | str,
    ylim: tuple[float, float] = (0, 100),
) -> Path:
    """Gera e salva o gráfico de dispersão/trade-off com formatação científica."""
    sns.set_theme(style="whitegrid", font="serif")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
    })

    fig, ax = plt.subplots(figsize=(9.5, 6), dpi=300)

    tempos = [m["tempo_min"] for m in modelos]
    acuracias = [m["top3_acc"] for m in modelos]
    params = [m["parametros_m"] for m in modelos]
    nomes = [m["nome"] for m in modelos]
    cores = [m["cor"] for m in modelos]

    # Escala proporcional para visualização clara das bolhas
    tamanhos_bolha = [np.sqrt(p) * 45 for p in params]

    # Plot dos pontos de dispersão
    ax.scatter(
        tempos,
        acuracias,
        s=tamanhos_bolha,
        c=cores,
        alpha=0.85,
        edgecolors="black",
        linewidths=1.2,
        zorder=3,
    )

    # Anotações sem sobreposição
    posicoes_rotulo = [
        (16, 12),     # TF-IDF + MLP
        (18, 16),     # BERT-Jurídico
        (-135, -52),  # mT0-Jurídico
    ]

    for i, nome in enumerate(nomes):
        dx, dy = posicoes_rotulo[i] if i < len(posicoes_rotulo) else (10, 10)
        ax.annotate(
            f"{nome}\n({params[i]}M params | Top-3: {acuracias[i]:.1f}%)",
            xy=(tempos[i], acuracias[i]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontweight="bold",
            fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="gray", alpha=0.92),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="gray", lw=0.8),
            zorder=4,
        )

    # Linha de ligação suave entre os pontos
    ax.plot(tempos, acuracias, linestyle=":", color="gray", alpha=0.65, zorder=2)

    ax.set_xlabel("Tempo de Treinamento (Minutos)", fontweight="bold")
    ax.set_ylabel("Acurácia Top-3 (%)", fontweight="bold")
    ax.set_title(titulo, pad=16)

    ax.set_xlim(1, 26)
    ax.set_ylim(*ylim)

    legend_elements = [
        plt.scatter([], [], s=50, c="#2b5c8f", edgecolors="black", alpha=0.85, label="TF-IDF + MLP (3.6M params)"),
        plt.scatter([], [], s=140, c="#d95f02", edgecolors="black", alpha=0.85, label="BERT-Jurídico (110M params)"),
        plt.scatter([], [], s=280, c="#7570b3", edgecolors="black", alpha=0.85, label="mT0-Jurídico (580M params)"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="lower right",
        title="Arquiteturas (Tamanho = Parâmetros)",
        frameon=True,
        framealpha=0.95,
        labelspacing=1.2,
        borderpad=0.9,
        handletextpad=1.0,
    )

    plt.tight_layout()

    salvar_caminho = Path(salvar_caminho)
    salvar_caminho.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(salvar_caminho, bbox_inches="tight")
    plt.close()

    print(f"[OK] Gráfico de Trade-off salvo em: {salvar_caminho}")
    return salvar_caminho


if __name__ == "__main__":
    # 1. Gráfico principal (escopo justo do Código Civil: 190 perguntas formal + informal)
    gerar_grafico_tradeoff(
        modelos=dados_cc2002,
        titulo=(
            "Trade-off: Custo Computacional vs. Acurácia Top-3 (Código Civil — Desktop/test)\n"
            "190 perguntas (95 formais + 95 informais) | Bolhas proporcionais aos parâmetros"
        ),
        salvar_caminho=PROJECT_ROOT / "data" / "resultados" / "grafico_tradeoff_custo_beneficio.png",
        ylim=(30, 95),
    )

    # 2. Gráfico complementar (todas as 19 leis do Desktop/test: 1.198 perguntas)
    gerar_grafico_tradeoff(
        modelos=dados_19leis,
        titulo=(
            "Trade-off: Custo Computacional vs. Acurácia Top-3 (Base Completa 19 Leis — Desktop/test)\n"
            "1.198 perguntas (599 formais + 599 informais) | Bolhas proporcionais aos parâmetros"
        ),
        salvar_caminho=PROJECT_ROOT / "data" / "resultados" / "grafico_tradeoff_completo_19leis.png",
        ylim=(0, 95),
    )
