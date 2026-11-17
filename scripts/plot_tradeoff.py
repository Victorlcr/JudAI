#!/usr/bin/env python3
"""
Script de Gráfico de Trade-off (Custo Computacional vs. Benefício de Acurácia).

Gera gráfico de dispersão com bolhas proporcionais ao número de parâmetros
dos modelos (TF-IDF + MLP, BERTimbau e mT0 Base), utilizando os dados reais
de tempo de treino, parâmetros e acurácia Top-3 do projeto JudAI.
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# DADOS REAIS EXPERIMENTAIS DO TRADE-OFF (Ambiente de Treinamento JudAI)
# ==============================================================================
# - TF-IDF + MLP: 20 épocas em CPU local | 3.6M parâmetros
# - BERTimbau Base: 8 épocas Fine-Tuning em GPU (Colab T4) | 110M parâmetros
# - mT0 Base: 5 épocas Fine-Tuning Seq2Seq em GPU (Colab T4) | 580M parâmetros

dados_modelos: list[dict] = [
    {
        "nome": "TF-IDF + MLP (Clássico)",
        "tempo_min": 4.0,           # Eixo X (Minutos de treinamento)
        "top3_acc": 100.0,          # Eixo Y (Acurácia Top-3 %)
        "parametros_m": 3.6,        # Tamanho da bolha (milhões de parâmetros)
        "cor": "#2b5c8f"
    },
    {
        "nome": "BERTimbau Ajustado (Busca)",
        "tempo_min": 6.0,           # Eixo X
        "top3_acc": 75.0,           # Eixo Y
        "parametros_m": 110.0,      # Tamanho da bolha (milhões de parâmetros)
        "cor": "#d95f02"
    },
    {
        "nome": "mT0-Jurídico (RAG Completo)",
        "tempo_min": 21.0,          # Eixo X
        "top3_acc": 76.0,           # Eixo Y
        "parametros_m": 580.0,      # Tamanho da bolha (milhões de parâmetros)
        "cor": "#7570b3"
    }
]


def carregar_dados_tradeoff_reais() -> list[dict]:
    """Carrega os dados reais do arquivo JSON gerado pelos experimentos se disponível."""
    caminho_json = PROJECT_ROOT / "data" / "resultados" / "metricas_consolidadas_reais.json"
    if caminho_json.exists():
        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                dados = json.load(f)
            lista = dados.get("tradeoff_custo_beneficio", [])
            if lista:
                cores = ["#2b5c8f", "#d95f02", "#7570b3"]
                return [
                    {
                        "nome": item["modelo"],
                        "tempo_min": item["tempo_treino_min"],
                        "top3_acc": item["top3_acc"],
                        "parametros_m": item["parametros_milhoes"],
                        "cor": cores[i % len(cores)]
                    }
                    for i, item in enumerate(lista)
                ]
        except Exception:
            pass
    return dados_modelos


def gerar_grafico_tradeoff(
    modelos: list[dict] | None = None,
    salvar_caminho: Path | str | None = None
) -> Path:
    """Gera e salva o gráfico de dispersão/trade-off com formatação científica."""
    if modelos is None:
        modelos = carregar_dados_tradeoff_reais()

    sns.set_theme(style="whitegrid", font="serif")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10
    })

    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)

    tempos = [m["tempo_min"] for m in modelos]
    acuracias = [m["top3_acc"] for m in modelos]
    params = [m["parametros_m"] for m in modelos]
    nomes = [m["nome"] for m in modelos]
    cores = [m["cor"] for m in modelos]

    # Escala proporcional para visualização clara das bolhas
    tamanhos_bolha = [np.sqrt(p) * 45 for p in params]

    # Plot dos pontos de dispersão
    scatter = ax.scatter(
        tempos, acuracias,
        s=tamanhos_bolha,
        c=cores,
        alpha=0.85,
        edgecolors="black",
        linewidths=1.2,
        zorder=3
    )

    # Anotações dos nomes e detalhes
    posicoes_rotulo = [
        (10, 10),    # TF-IDF + MLP
        (15, -15),   # BERTimbau
        (-25, 18)    # mT0 Base
    ]

    for i, nome in enumerate(nomes):
        dx, dy = posicoes_rotulo[i] if i < len(posicoes_rotulo) else (10, 10)
        ax.annotate(
            f"{nome}\n({params[i]}M params | {acuracias[i]:.1f}%)",
            xy=(tempos[i], acuracias[i]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontweight="bold",
            fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="gray", lw=0.8),
            zorder=4
        )

    # Linha de tendência suave
    ax.plot(tempos, acuracias, linestyle=":", color="gray", alpha=0.6, zorder=2)

    ax.set_xlabel("Tempo de Treinamento (Minutos)", fontweight="bold")
    ax.set_ylabel("Acurácia Top-3 (%)", fontweight="bold")
    ax.set_title(
        "Trade-off: Custo Computacional vs. Acurácia Top-3\n"
        "(Área das bolhas proporcional ao volume de parâmetros)",
        pad=16
    )

    ax.set_xlim(1, 26)
    ax.set_ylim(60, 108)

    # Legenda explicativa para as bolhas
    legend_elements = [
        plt.scatter([], [], s=np.sqrt(3.6)*45, c="#2b5c8f", edgecolors="black", alpha=0.8, label="TF-IDF + MLP (3.6M)"),
        plt.scatter([], [], s=np.sqrt(110)*45, c="#d95f02", edgecolors="black", alpha=0.8, label="BERT-Jurídico (110M)"),
        plt.scatter([], [], s=np.sqrt(580)*45, c="#7570b3", edgecolors="black", alpha=0.8, label="mT0-Jurídico (580M)")
    ]
    ax.legend(handles=legend_elements, loc="lower right", title="Arquiteturas", frameon=True, framealpha=0.95)

    plt.tight_layout()

    if salvar_caminho is None:
        salvar_caminho = PROJECT_ROOT / "data" / "resultados" / "grafico_tradeoff_custo_beneficio.png"
    else:
        salvar_caminho = Path(salvar_caminho)

    salvar_caminho.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(salvar_caminho, bbox_inches="tight")
    plt.close()

    print(f"[OK] Gráfico de Trade-off gerado com dados reais em: {salvar_caminho}")
    return salvar_caminho


if __name__ == "__main__":
    gerar_grafico_tradeoff()
