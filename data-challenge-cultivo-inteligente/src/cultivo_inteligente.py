"""Funções reutilizáveis do projeto de recomendação de cultivo.

O módulo concentra aquisição, validação, modelagem e inferência para que o
notebook final permaneça legível e reproduzível.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    top_k_accuracy_score,
)
from sklearn.model_selection import RandomizedSearchCV, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"
DATASET_ID = "randalakab/Crop-recommendation"
RANDOM_STATE = 42


def fix_seeds(seed: int = RANDOM_STATE) -> None:
    """Fixa as fontes de aleatoriedade usadas neste projeto."""

    random.seed(seed)
    np.random.seed(seed)


def load_crop_data(
    project_root: Path,
    dataset_id: str = DATASET_ID,
    timeout: int = 30,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Carrega o CSV publicado no Hugging Face, com contingência local."""

    project_root = Path(project_root).resolve()
    fallback = project_root / "data" / "crop_recommendation.csv"
    api_url = f"https://huggingface.co/api/datasets/{dataset_id}"

    try:
        with urlopen(api_url, timeout=timeout) as response:
            dataset_info = json.load(response)
        csv_files = [
            item["rfilename"]
            for item in dataset_info.get("siblings", [])
            if item.get("rfilename", "").lower().endswith(".csv")
        ]
        if not csv_files:
            raise RuntimeError("A API não informou arquivo CSV no dataset.")

        preferred = [name for name in csv_files if "crop_recommendation" in name.lower()]
        selected_file = (preferred or csv_files)[0]
        encoded_file = "/".join(quote(part) for part in selected_file.split("/"))
        source = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{encoded_file}"
        frame = pd.read_csv(source)
        source_type = "Hugging Face"
    except Exception as error:
        if not fallback.exists():
            raise RuntimeError(
                "Falha ao acessar o Hugging Face e não existe CSV local de contingência."
            ) from error
        selected_file = fallback.name
        source = str(fallback)
        source_type = "arquivo local de contingência"
        dataset_info = {}
        frame = pd.read_csv(fallback)

    provenance = {
        "dataset": dataset_id,
        "arquivo": selected_file,
        "fonte_utilizada": source,
        "tipo_fonte": source_type,
        "revisao_api": dataset_info.get("sha", "não informada"),
        "ultima_modificacao_api": dataset_info.get("lastModified", "não informada"),
    }
    return frame, provenance


def validate_crop_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Valida esquema, tipos e qualidade básica; devolve cópia normalizada."""

    expected = FEATURES + [TARGET]
    missing = [column for column in expected if column not in frame.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    clean = frame.loc[:, expected].copy()
    for column in FEATURES:
        clean[column] = pd.to_numeric(clean[column], errors="raise")
    clean[TARGET] = clean[TARGET].astype(str).str.strip()

    if clean[TARGET].eq("").any():
        raise ValueError("Foram encontrados rótulos vazios.")
    if clean.isna().any().any():
        raise ValueError("A base contém valores ausentes após a validação.")

    class_counts = clean[TARGET].value_counts()
    diagnostics = pd.DataFrame(
        {
            "verificacao": [
                "registros",
                "colunas",
                "valores ausentes",
                "linhas duplicadas",
                "culturas",
                "menor classe",
                "maior classe",
                "umidade acima de 100",
            ],
            "resultado": [
                len(clean),
                clean.shape[1],
                int(clean.isna().sum().sum()),
                int(clean.duplicated().sum()),
                int(clean[TARGET].nunique()),
                int(class_counts.min()),
                int(class_counts.max()),
                int(clean["humidity"].gt(100).sum()),
            ],
        }
    )
    return clean, diagnostics


def build_candidate_models(seed: int = RANDOM_STATE) -> dict[str, Any]:
    """Constrói alternativas comparáveis para a classificação multiclasse."""

    return {
        "Baseline": DummyClassifier(strategy="most_frequent"),
        "Regressão logística": Pipeline(
            [
                ("padronizacao", StandardScaler()),
                (
                    "modelo",
                    LogisticRegression(
                        max_iter=4000,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "Árvore de decisão": DecisionTreeClassifier(
            max_depth=10,
            min_samples_leaf=2,
            random_state=seed,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            random_state=seed,
            n_jobs=-1,
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=400,
            random_state=seed,
            n_jobs=-1,
        ),
    }


def compare_models(
    models: dict[str, Any],
    X: pd.DataFrame,
    y: pd.Series,
    cv: Any,
) -> pd.DataFrame:
    """Compara modelos somente no treino com as mesmas partições de CV."""

    scoring = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "precision_macro": "precision_macro",
        "recall_macro": "recall_macro",
        "f1_macro": "f1_macro",
        "f1_weighted": "f1_weighted",
    }
    rows: list[dict[str, Any]] = []
    for name, model in models.items():
        scores = cross_validate(
            model,
            X,
            y,
            cv=cv,
            scoring=scoring,
            n_jobs=1,
            return_train_score=True,
        )
        row: dict[str, Any] = {
            "modelo": name,
            "tempo_ajuste_medio_s": scores["fit_time"].mean(),
        }
        for metric in scoring:
            test_values = scores[f"test_{metric}"]
            train_values = scores[f"train_{metric}"]
            row[f"{metric}_media"] = test_values.mean()
            row[f"{metric}_dp"] = test_values.std()
            row[f"{metric}_treino"] = train_values.mean()
        row["gap_f1_macro"] = row["f1_macro_treino"] - row["f1_macro_media"]
        rows.append(row)

    return (
        pd.DataFrame(rows)
        .sort_values("f1_macro_media", ascending=False)
        .reset_index(drop=True)
    )


def build_tuning_search(
    family_name: str,
    estimator: Any,
    cv: Any,
    seed: int = RANDOM_STATE,
    n_iter: int = 18,
) -> RandomizedSearchCV:
    """Cria busca controlada para a melhor família de ensemble."""

    if family_name not in {"Random Forest", "Extra Trees"}:
        raise ValueError("A busca final está definida para Random Forest ou Extra Trees.")

    parameters = {
        "n_estimators": [300, 500, 700, 900],
        "max_depth": [None, 12, 20, 30],
        "min_samples_split": [2, 4, 8],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2", 0.75],
        "class_weight": [None, "balanced"],
    }
    return RandomizedSearchCV(
        estimator=estimator,
        param_distributions=parameters,
        n_iter=n_iter,
        scoring="f1_macro",
        n_jobs=1,
        cv=cv,
        random_state=seed,
        refit=True,
        return_train_score=True,
        verbose=0,
    )


def evaluate_classifier(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict[str, float], np.ndarray, np.ndarray]:
    """Calcula métricas finais no teste reservado uma única vez."""

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)
    labels = list(model.classes_)
    metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "balanced_accuracy": balanced_accuracy_score(y_test, predictions),
        "precision_macro": precision_score(y_test, predictions, average="macro", zero_division=0),
        "recall_macro": recall_score(y_test, predictions, average="macro", zero_division=0),
        "f1_macro": f1_score(y_test, predictions, average="macro", zero_division=0),
        "f1_weighted": f1_score(y_test, predictions, average="weighted", zero_division=0),
        "top3_accuracy": top_k_accuracy_score(
            y_test,
            probabilities,
            k=3,
            labels=labels,
        ),
        "log_loss": log_loss(y_test, probabilities, labels=labels),
        "errors": int(np.sum(predictions != y_test.to_numpy())),
        "test_observations": int(len(y_test)),
    }
    return metrics, predictions, probabilities


def confidence_diagnostics(
    y_true: pd.Series,
    predictions: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resume confiança máxima e acurácia por faixa de probabilidade."""

    detail = pd.DataFrame(
        {
            "real": y_true.to_numpy(),
            "predicted": predictions,
            "confidence": probabilities.max(axis=1),
        },
        index=y_true.index,
    )
    detail["correct"] = detail["real"].eq(detail["predicted"])
    bins = [0.0, 0.60, 0.70, 0.80, 0.90, 0.95, 1.000001]
    detail["confidence_band"] = pd.cut(
        detail["confidence"], bins=bins, include_lowest=True
    )
    summary = (
        detail.groupby("confidence_band", observed=True)
        .agg(
            observations=("correct", "size"),
            accuracy=("correct", "mean"),
            mean_confidence=("confidence", "mean"),
        )
        .reset_index()
    )
    return detail, summary


def feature_ranges(X_train: pd.DataFrame) -> pd.DataFrame:
    """Faixas observadas no treino usadas como salvaguarda de inferência."""

    ranges = X_train[FEATURES].agg(["min", "max", "mean", "std"]).T
    ranges.index.name = "feature"
    return ranges


def recommend_top_k(
    model: Any,
    observation: dict[str, float] | pd.DataFrame,
    ranges: pd.DataFrame,
    top_k: int = 3,
) -> tuple[pd.DataFrame, list[str]]:
    """Retorna culturas mais compatíveis e alertas para entradas fora da base."""

    if isinstance(observation, dict):
        frame = pd.DataFrame([observation])
    else:
        frame = observation.copy()

    missing = [column for column in FEATURES if column not in frame.columns]
    if missing:
        raise ValueError(f"Variáveis ausentes para inferência: {missing}")
    frame = frame.loc[:, FEATURES].apply(pd.to_numeric, errors="raise")
    if len(frame) != 1:
        raise ValueError("A demonstração operacional aceita uma observação por chamada.")

    warnings: list[str] = []
    for feature in FEATURES:
        value = float(frame.iloc[0][feature])
        lower = float(ranges.loc[feature, "min"])
        upper = float(ranges.loc[feature, "max"])
        if value < lower or value > upper:
            warnings.append(
                f"{feature}={value:.3f} fora da faixa observada [{lower:.3f}, {upper:.3f}]"
            )

    probabilities = model.predict_proba(frame)[0]
    order = np.argsort(probabilities)[::-1][:top_k]
    recommendations = pd.DataFrame(
        {
            "rank": np.arange(1, len(order) + 1),
            "crop": np.asarray(model.classes_)[order],
            "compatibility": probabilities[order],
        }
    )
    return recommendations, warnings
