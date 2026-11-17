#!/usr/bin/env python3
"""
Script de Gráfico de Trade-off (Custo Computacional vs. Benefício de Acurácia).

Gera gráfico de dispersão com bolhas proporcionais ao número de parâmetros
dos modelos (TF-IDF + MLP, BERTimbau e mT0 Base).
"""
from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==============================================================================
# DADOS EXPERIMENTAIS DO TRADE-OFF (Ajuste conforme seus benchmarks)
# ==============================================================================
dados_modelos: list[dict] = [
    {
        "nome": "TF-IDF + MLP",
        "tempo_min": 4.0,           # Eixo X (Minutos de treinamento)
        "top3_acc": 74.1,           # Eixo Y (Acurácia Top-3 %)
        "parametros_m": 14.3,       # Tamanho da bolha (milhões de parâmetros)
        "cor": "#2b5c8f"
    },
    {
        "nome": "BERTimbau Base",
        "tempo_min": 6.0,           # Eixo X
        "top3_acc": 89.2,           # Eixo Y
        "parametros_m": 110.0,      # Tamanho da bolha (milhões de parâmetros)
        "cor": "#d95f02"
    },
    {
        "nome": "mT0 Base (RAG/Seq2Seq)",
        "tempo_min": 21.0,          # Eixo X
        "top3_acc": 93.8,           # Eixo Y
        "parametros_m": 580.0,      # Tamanho da bolha (milhões de parâmetros)
        "cor": "#7570b3"
    }
]


def gerar_grafico_tradeoff(
    modelos: list[dict] | None = None,
    salvar_caminho: Path | str | None = None
) -> Path:
    """Gera e salva o gráfico de dispersão/trade-off com formatação científica."""
    if modelos is None:
        modelos = dados_modelos

    sns.set_theme(style="whitegrid", font="serif")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10
    })

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    tempos = [m["tempo_min"] for m in modelos]
    acuracias = [m["top3_acc"] for m in modelos]
    cores = [m["cor"] for m in modelos]
    pesos = [m["parametros_m"] for m in modelos]

    # Fator de escala para área da bolha ser proporcional ao número de parâmetros
    tamanhos_bolha = [np.sqrt(p) * 65 for p in pesos]

    ax.scatter(
        tempos,
        acuracias,
        s=tamanhos_bolha,
        c=cores,
        alpha=0.75,
        edgecolors="black",
        linewidths=1.2,
        zorder=3
    )

    # Rótulos textuais de cada modelo no gráfico
    deslocamentos = [(0.5, -1.8), (0.5, 0.9), (-3.8, 1.2)]
    for i, m in enumerate(modelos):
        dx, dy = deslocamentos[i] if i < len(deslocamentos) else (0.5, 0.5)
        ax.annotate(
            f"{m['nome']}\n({m['top3_acc']:.1f}% | {m['tempo_min']} min)",
            xy=(m["tempo_min"], m["top3_acc"]),
            xytext=(m["tempo_min"] + dx, m["top3_acc"] + dy),
            fontsize=10,
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="gray", lw=0.8)
        )

    ax.set_xlabel("Tempo de Treinamento (Minutos)")
    ax.set_ylabel("Acurácia Top-3 (%)")
    ax.set_title("Análise de Trade-off: Custo de Treinamento vs. Acurácia Top-3", pad=15)

    ax.set_xlim(0, 26)
    ax.set_ylim(65, 100)

    # Legenda explicativa da escala das bolhas
    legenda_tamanhos = [15, 110, 580]
    for p in legenda_tamanhos:
        ax.scatter([], [], s=np.sqrt(p) * 65, c="gray", alpha=0.4, edgecolors="black", label=f"~{p}M parâmetros")

    ax.legend(title="Escala de Parâmetros", frameon=True, loc="lower right", scatterpoints=1)

    sns.despine(top=True, right=True)
    plt.tight_layout()

    if salvar_caminho is None:
        salvar_caminho = Path(__file__).resolve().parent.parent / "data" / "resultados" / "grafico_tradeoff_custo_beneficio.png"
    salvar_caminho = Path(salvar_caminho)
    salvar_caminho.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(salvar_caminho, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Gráfico de Trade-off salvo com sucesso em: {salvar_caminho}")
    return salvar_caminho


if __name__ == "__main__":
    gerar_grafico_tradeoff()
