"""
Módulo de Busca Clássica com TF-IDF e Rede Neural MLP - JudAI
============================================================
Implementa o classificador neural clássico (TF-IDF + PyTorch MLP) para recuperação
e ranqueamento de artigos da legislação civil brasileira (Código Civil / cc2002).

Arquitetura:
- Vetorizador TF-IDF esparso com vocabulário de até 5.000 termos relevantes.
- Rede Neural MLP: Linear(vocab_size, 512) -> ReLU -> Dropout(0.3) -> Linear(512, num_classes).
- Treinamento combinado: artigos vigentes + 4 variações sintéticas por artigo + pares_bert_inicial.jsonl.
- Validação out-of-sample: avaliacao_inicial.jsonl.
- Persistência em disco: data/models/tfidf_mlp/ (modelo_classico.pt, vectorizer.pkl, label_encoder.pkl, metadata.json, artigos_dict.pkl).
"""
from __future__ import annotations

import copy
import json
import logging
import os
import pickle
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

# Localiza e adiciona a raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.mongo_connection import MongoConnection

logger = logging.getLogger("judai.models.tfidf_mlp")


# ---------------------------------------------------------------------------
# Funções de Pré-processamento e Geração Sintética
# ---------------------------------------------------------------------------

STOP_WORDS = {
    'o', 'a', 'os', 'as', 'de', 'do', 'da', 'em', 'no', 'na', 'para', 'com',
    'por', 'que', 'se', 'é', 'não', 'dos', 'das', 'aos', 'ou', 'como', 'sobre'
}


def limpar_texto(texto: Any) -> str:
    """Normaliza texto removendo pontuação, excesso de espaços e convertendo para minúsculas."""
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def extrair_palavras_chave(texto_limpo: str) -> str:
    """Extrai até 6 palavras-chave relevantes que não pertençam à lista de stopwords."""
    palavras = texto_limpo.split()
    keywords = [p for p in palavras if p not in STOP_WORDS and len(p) > 3]
    return " ".join(keywords[:6])


def gerar_perguntas_sinteticas(texto_limpo: str) -> list[str]:
    """Gera 4 variações textuais para treinamento a partir do texto limpo do dispositivo."""
    keywords = extrair_palavras_chave(texto_limpo)
    if not keywords:
        return [texto_limpo]
    return [
        texto_limpo,
        f"o que a legislação diz sobre {keywords}",
        f"qual é a regra jurídica aplicável a {keywords}",
        f"como o código civil trata o tema de {keywords}"
    ]


# ---------------------------------------------------------------------------
# Arquitetura PyTorch: ModeloClassicoTFIDF
# ---------------------------------------------------------------------------

class ModeloClassicoTFIDF(nn.Module):
    """
    Rede Neural Densa Feedforward (MLP) para classificação de texto vetorizado por TF-IDF.
    Espelha estritamente a arquitetura validada no notebook TFIDF_MLP.ipynb:
    Linear(tamanho_vocabulario, 512) -> ReLU -> Dropout(0.3) -> Linear(512, num_classes)
    """

    def __init__(self, tamanho_vocabulario: int, num_classes: int) -> None:
        super(ModeloClassicoTFIDF, self).__init__()
        self.tamanho_vocabulario = tamanho_vocabulario
        self.num_classes = num_classes
        self.fc1 = nn.Linear(tamanho_vocabulario, 512)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(512, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.fc1(x)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        return out


# ---------------------------------------------------------------------------
# Classe Gerenciadora: TfidfMLPSearch
# ---------------------------------------------------------------------------

class TfidfMLPSearch:
    """
    Gerenciador completo de treinamento, persistência e busca para o modelo TF-IDF + MLP.
    Permite inferência com latência mínima (< 5ms) reutilizando artefatos persistidos em disco.
    """

    DEFAULT_SAVE_DIR: Path = PROJECT_ROOT / "data" / "models" / "tfidf_mlp"
    DEFAULT_DATASET_DIR: Path = PROJECT_ROOT / "data" / "dataset"

    def __init__(
        self,
        model_dir: Optional[Path | str] = None,
        auto_load: bool = True,
        device: Optional[str] = None
    ) -> None:
        self.model_dir: Path = Path(model_dir or self.DEFAULT_SAVE_DIR)
        if device:
            self.device: torch.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model: Optional[ModeloClassicoTFIDF] = None
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.artigos_dict: dict[str, dict[str, str]] = {}
        self.metadata: dict[str, Any] = {}
        self.is_loaded: bool = False

        if auto_load and (self.model_dir / "modelo_classico.pt").exists():
            self.load(self.model_dir)

    def fit(
        self,
        db: Optional[Any] = None,
        dataset_dir: Optional[Path | str] = None,
        save_dir: Optional[Path | str] = None,
        epochs: int = 20,
        lr: float = 0.001,
        batch_size: int = 32,
        max_features: int = 5000,
        seed: int = 42
    ) -> dict[str, Any]:
        """
        Executa o pipeline completo de treinamento do classificador TF-IDF + MLP.
        """
        torch.manual_seed(seed)
        np.random.seed(seed)

        save_path = Path(save_dir or self.model_dir)
        data_path = Path(dataset_dir or self.DEFAULT_DATASET_DIR)

        # 1. Obtenção dos artigos do MongoDB
        if db is None:
            db = MongoConnection().get_db()

        cursor = db["artigos"].find({"lei_id": "cc2002", "vigente": True}).sort("ordem", 1)
        self.artigos_dict = {}
        dados_sinteticos: list[dict[str, str]] = []

        for doc in cursor:
            id_artigo = str(doc["_id"])
            citacao = doc.get("citacao") or f"Código Civil, art. {doc.get('numero', '')}"
            texto_artigo = doc.get("texto_vigente") or doc.get("texto") or ""

            self.artigos_dict[id_artigo] = {
                "citacao": citacao,
                "texto": texto_artigo
            }

            texto_limpo = limpar_texto(doc.get("texto", "") or texto_artigo)
            if texto_limpo:
                for var in gerar_perguntas_sinteticas(texto_limpo):
                    dados_sinteticos.append({"texto": var, "label": id_artigo, "origem": "sintetico"})

        df_sintetico = pd.DataFrame(dados_sinteticos)
        if df_sintetico.empty:
            raise RuntimeError("Nenhum dado sintético pôde ser gerado a partir do MongoDB.")

        # 2. Carregamento dos dados JSONL
        def _carregar_jsonl(filename: str) -> pd.DataFrame:
            path = data_path / filename
            rows = []
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str:
                            obj = json.loads(line_str)
                            rows.append({
                                "texto": limpar_texto(obj["pergunta"]),
                                "label": obj["artigo_id"],
                                "origem": "real"
                            })
            return pd.DataFrame(rows)

        df_pares_bert = _carregar_jsonl("pares_bert_inicial.jsonl")
        df_avaliacao = _carregar_jsonl("avaliacao_inicial.jsonl")

        # 3. Composição dos conjuntos de treino e validação
        if not df_pares_bert.empty:
            df_treino = pd.concat([df_sintetico, df_pares_bert], ignore_index=True)
        else:
            df_treino = df_sintetico.copy()

        df_validacao = df_avaliacao.copy() if not df_avaliacao.empty else df_treino.sample(min(len(df_treino), 50), random_state=seed)

        # 4. Mapeamento de classes e rótulos
        df_completo = pd.concat([df_treino, df_validacao], ignore_index=True)
        todas_as_classes = sorted(list(set(df_completo['label']).union(set(self.artigos_dict.keys()))))
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(todas_as_classes)
        num_classes = len(self.label_encoder.classes_)

        df_treino['label_encoded'] = self.label_encoder.transform(df_treino['label'])
        df_validacao['label_encoded'] = self.label_encoder.transform(df_validacao['label'])

        # 5. Vetorização TF-IDF
        self.vectorizer = TfidfVectorizer(max_features=max_features)
        X_treino_tfidf = self.vectorizer.fit_transform(df_treino['texto'])
        X_valid_tfidf = self.vectorizer.transform(df_validacao['texto'])

        tamanho_vocabulario = X_treino_tfidf.shape[1]

        # 6. Conversão para Tensores e DataLoaders
        X_treino_tensor = torch.tensor(X_treino_tfidf.toarray(), dtype=torch.float32)
        Y_treino_tensor = torch.tensor(df_treino['label_encoded'].values, dtype=torch.long)
        X_valid_tensor = torch.tensor(X_valid_tfidf.toarray(), dtype=torch.float32)
        Y_valid_tensor = torch.tensor(df_validacao['label_encoded'].values, dtype=torch.long)

        train_loader = DataLoader(
            TensorDataset(X_treino_tensor, Y_treino_tensor),
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=False,
        )
        val_loader = DataLoader(
            TensorDataset(X_valid_tensor, Y_valid_tensor),
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=False,
        )

        # 7. Inicialização do Modelo e Treinamento
        self.model = ModeloClassicoTFIDF(tamanho_vocabulario, num_classes).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        min_val_loss = float("inf")
        best_epoch = 0
        best_val_acc = 0.0
        best_state_dict = copy.deepcopy(self.model.state_dict())

        for epoch in range(epochs):
            self.model.train()
            total_train_loss = 0.0
            for x_b, y_b in train_loader:
                x_b, y_b = x_b.to(self.device), y_b.to(self.device)
                optimizer.zero_grad()
                outputs = self.model(x_b)
                loss = criterion(outputs, y_b)
                loss.backward()
                optimizer.step()
                total_train_loss += loss.item()

            # Validação
            self.model.eval()
            total_val_loss = 0.0
            total_acc = 0
            with torch.no_grad():
                for x_v, y_v in val_loader:
                    x_v, y_v = x_v.to(self.device), y_v.to(self.device)
                    outputs = self.model(x_v)
                    loss = criterion(outputs, y_v)
                    preds = outputs.argmax(dim=1)
                    total_acc += (preds == y_v).sum().item()
                    total_val_loss += loss.item()

            val_loss = total_val_loss / max(1, len(val_loader))
            val_acc = total_acc / max(1, len(df_validacao))

            if val_loss < min_val_loss or epoch == 0:
                min_val_loss = val_loss
                best_epoch = epoch + 1
                best_val_acc = val_acc
                best_state_dict = copy.deepcopy(self.model.state_dict())

        # Carrega o melhor estado
        self.model.load_state_dict(best_state_dict)
        self.model.eval()

        self.metadata = {
            "model_name": "TFIDF_MLP",
            "tamanho_vocabulario": int(tamanho_vocabulario),
            "num_classes": int(num_classes),
            "best_epoch": int(best_epoch),
            "val_loss": round(float(min_val_loss), 4),
            "val_acc": round(float(best_val_acc), 4),
            "epochs": epochs,
            "lr": lr,
            "batch_size": batch_size,
            "device": str(self.device),
            "artigos_indexados": len(self.artigos_dict),
            "saved_at": datetime.now(timezone.utc).isoformat()
        }

        # 8. Persistência
        self.save(save_path)
        self.is_loaded = True

        return self.metadata

    def save(self, save_dir: Optional[Path | str] = None) -> None:
        """Salva todos os artefatos do modelo em disco para inferência futura de custo zero."""
        target_dir = Path(save_dir or self.model_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        if self.model is None or self.vectorizer is None or self.label_encoder is None:
            raise RuntimeError("Não é possível salvar: modelo, vetorizador ou codificador não inicializados.")

        # 1. Pesos PyTorch
        torch.save(self.model.state_dict(), target_dir / "modelo_classico.pt")

        # 2. Vetorizador TF-IDF
        with open(target_dir / "vectorizer.pkl", "wb") as f:
            pickle.dump(self.vectorizer, f)

        # 3. LabelEncoder
        with open(target_dir / "label_encoder.pkl", "wb") as f:
            pickle.dump(self.label_encoder, f)

        # 4. Metadados JSON
        with open(target_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

        # 5. Dicionário de Artigos para Lookup em Tempo Real
        with open(target_dir / "artigos_dict.pkl", "wb") as f:
            pickle.dump(self.artigos_dict, f)

    def load(self, save_dir: Optional[Path | str] = None) -> bool:
        """Carrega os artefatos salvos em disco garantindo inferência instantânea."""
        target_dir = Path(save_dir or self.model_dir)

        caminho_modelo = target_dir / "modelo_classico.pt"
        caminho_vec = target_dir / "vectorizer.pkl"
        caminho_le = target_dir / "label_encoder.pkl"
        caminho_meta = target_dir / "metadata.json"

        if not (caminho_modelo.exists() and caminho_vec.exists() and caminho_le.exists() and caminho_meta.exists()):
            return False

        # Metadados
        with open(caminho_meta, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        vocab_size = self.metadata["tamanho_vocabulario"]
        num_classes = self.metadata["num_classes"]

        # Vetorizador
        with open(caminho_vec, "rb") as f:
            self.vectorizer = pickle.load(f)

        # LabelEncoder
        with open(caminho_le, "rb") as f:
            self.label_encoder = pickle.load(f)

        # Modelo PyTorch
        self.model = ModeloClassicoTFIDF(vocab_size, num_classes).to(self.device)
        state_dict = torch.load(caminho_modelo, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()

        # Dicionário de lookup
        caminho_dict = target_dir / "artigos_dict.pkl"
        if caminho_dict.exists():
            with open(caminho_dict, "rb") as f:
                self.artigos_dict = pickle.load(f)
        else:
            try:
                db = MongoConnection().get_db()
                cursor = db["artigos"].find({"lei_id": "cc2002", "vigente": True})
                self.artigos_dict = {
                    str(d["_id"]): {
                        "citacao": d.get("citacao") or f"Código Civil, art. {d.get('numero', '')}",
                        "texto": d.get("texto_vigente") or d.get("texto") or ""
                    }
                    for d in cursor
                }
            except Exception:
                self.artigos_dict = {}

        self.is_loaded = True
        return True

    def search(self, query: str, top_k: int = 3) -> dict[str, Any]:
        """
        Executa a busca jurídica e retorna a estrutura padronizada com top-K previsões.
        """
        start_time = time.perf_counter()

        if not self.is_loaded:
            loaded = self.load()
            if not loaded:
                raise RuntimeError("Modelo TFIDF_MLP não foi treinado nem carregado do disco.")

        query_limpa = limpar_texto(query)
        if not query_limpa:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "model": "tfidf_mlp",
                "query": query,
                "results": [],
                "execution_time_ms": execution_time_ms
            }

        # Vetorização e inferência neural
        vetor = self.vectorizer.transform([query_limpa])
        tensor = torch.tensor(vetor.toarray(), dtype=torch.float32).to(self.device)

        with torch.inference_mode():
            outputs = self.model(tensor)
            probabilidades = F.softmax(outputs, dim=1)
            k = min(top_k, self.metadata.get("num_classes", outputs.shape[1]))
            scores, indices = torch.topk(probabilidades, k)

        results: list[dict[str, Any]] = []
        for i in range(k):
            idx_classe = indices[0][i].item()
            score = round(float(scores[0][i].item()), 4)
            id_artigo = self.label_encoder.inverse_transform([idx_classe])[0]

            artigo_info = self.artigos_dict.get(id_artigo, {})
            citacao = artigo_info.get("citacao", f"Código Civil, {id_artigo}")
            texto = artigo_info.get("texto", "")

            results.append({
                "artigo_id": id_artigo,
                "citacao": citacao,
                "texto": texto,
                "score": score
            })

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "model": "tfidf_mlp",
            "query": query,
            "results": results,
            "execution_time_ms": execution_time_ms
        }

    def evaluate(self, dataset_dir: Optional[Path | str] = None) -> dict[str, float]:
        """
        Avalia o modelo contra a base out-of-sample (avaliacao_inicial.jsonl)
        calculando Top-1 e Top-3 accuracy.
        """
        data_path = Path(dataset_dir or self.DEFAULT_DATASET_DIR)
        path = data_path / "avaliacao_inicial.jsonl"
        if not path.exists():
            return {"top1_acc": 0.0, "top3_acc": 0.0}

        exemplos: list[tuple[str, str]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    exemplos.append((item["pergunta"], item["artigo_id"]))

        if not exemplos:
            return {"top1_acc": 0.0, "top3_acc": 0.0}

        top1_hits = 0
        top3_hits = 0
        for pergunta, esperado in exemplos:
            resp = self.search(pergunta, top_k=3)
            recuperados = [r["artigo_id"] for r in resp.get("results", [])]
            if recuperados and recuperados[0] == esperado:
                top1_hits += 1
            if esperado in recuperados:
                top3_hits += 1

        total = len(exemplos)
        return {
            "top1_acc": round(top1_hits / total, 4),
            "top3_acc": round(top3_hits / total, 4),
            "total_samples": total
        }
