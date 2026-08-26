"""Execute the frozen BeeQ final nested structure-aware validation campaign.

This runner deliberately separates development-only model selection and artifact
freezing from historical-holdout and CR8 evaluation.  It reuses the model and
kernel implementations already present in :mod:`src.classical_models`,
:mod:`src.quantum_experiment`, and :mod:`src.quantum_feature_maps`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import pickle
import platform
import subprocess
import sys
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from rdkit import Chem, DataStructs
from rdkit.Chem import Draw, rdFingerprintGenerator
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    pairwise_distances,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .classical_models import model_specs
from .config import OUTER_FOLDS, X10_FEATURES
from .evaluation import continuous_scores
from .quantum_experiment import _kernel_candidates, _kernel_matrices


warnings.filterwarnings("ignore", category=ConvergenceWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / ".donotmerge_aux" / "Luis" / "01_DATA"
DEFAULT_CAMPAIGN_DIR = (
    PROJECT_ROOT
    / "results"
    / "campaigns"
    / "BEEQ_FINAL_NESTED_STRUCT_IMPL_20260825T234128Z"
)
SEED = 20260824
INNER_FOLDS = 4
BOOTSTRAP_REPLICATES = 2000
Y_RANDOMIZATION_REPLICATES = 200
PRIMARY_MODELS = (
    "logistic",
    "random_forest",
    "mlp",
    "rbf_matched",
    "quantum_angle_product",
    "quantum_iqp_zz_linear",
)
CLASSICAL_MODELS = PRIMARY_MODELS[:3]
KERNEL_MODELS = PRIMARY_MODELS[3:]
QUANTUM_MODELS = PRIMARY_MODELS[4:]

EXPECTED_HASHES = {
    "master_RDKitFixed.csv": "a0a6177b3319dba8f210d2358bdd63edbb1c6db3d9b657daa992459b11f2c38e",
    "train_RDKitFixed.csv": "06a0817c082d7715211ca62aae367079f192e1a6c6663c2005c8c8eb5c758984",
    "test_RDKitFixed.csv": "3f964207e5d732315501d11be2d50c4f520e51a8c7f17b70fe8594390988c8f5",
    "ExternalFinal_RDKitFixed.csv": "70a01eedd970991e072eb9db8e2acdbe854dc8d4623b42bb2263318486cd41fb",
}

HYPERPARAMETER_SPACES: dict[str, dict[str, list[Any]]] = {
    "logistic": {"model__C": [0.01, 0.1, 1.0, 10.0, 100.0]},
    "random_forest": {
        "model__max_depth": [None, 6],
        "model__min_samples_leaf": [1, 3],
    },
    "mlp": {
        "model__hidden_layer_sizes": [(32,), (32, 16)],
        "model__alpha": [0.0001, 0.001, 0.01],
        "model__learning_rate_init": [0.0003, 0.001],
    },
    "rbf_matched": {
        "C": [0.1, 1.0, 10.0, 100.0],
        "gamma": [0.01, 0.03, 0.1, 0.3],
    },
    "quantum_angle_product": {
        "C": [0.1, 1.0, 10.0, 100.0],
        "feature_scale": [0.125, 0.25, 0.5, 1.0],
    },
    "quantum_iqp_zz_linear": {
        "C": [0.1, 1.0, 10.0, 100.0],
        "feature_scale": [0.125, 0.25, 0.5, 1.0],
        "interaction_strength": [1.0],
    },
}

QUANTUM_CONFIG = {
    "seed": SEED,
    "inner_splits": INNER_FOLDS,
    "backend": "exact_numpy_statevector",
    "shots": None,
    "c_values": [0.1, 1.0, 10.0, 100.0],
    "rbf_gamma": [0.01, 0.03, 0.1, 0.3],
    "feature_scales": [0.125, 0.25, 0.5, 1.0],
    "interaction_strength": 1.0,
    "selection_metric": "roc_auc",
}


@dataclass
class FrozenClassical:
    estimator: Any
    threshold: float


@dataclass
class FrozenKernel:
    scaler: StandardScaler
    classifier: SVC
    train_scaled: np.ndarray
    params: dict[str, float]
    threshold: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--short"], cwd=PROJECT_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()
    return {"commit": commit, "dirty": bool(status), "status": status}


def environment() -> dict[str, str]:
    result = {"python": platform.python_version(), "platform": platform.platform()}
    for name in ("numpy", "pandas", "sklearn", "xgboost", "rdkit", "qiskit", "matplotlib", "pennylane", "optuna"):
        try:
            module = importlib.import_module(name)
            result[name] = str(getattr(module, "__version__", "installed-version-unreported"))
        except ImportError:
            result[name] = "not installed"
    return result


def prepare_directories(root: Path, *, allow_completed: bool = False) -> dict[str, Path]:
    names = {
        "readme": "00_README",
        "config": "01_CONFIG",
        "audit": "02_DATA_AUDIT",
        "nested": "03_NESTED_CV",
        "final": "04_FINAL_SELECTION",
        "holdout": "05_HOLDOUT",
        "external": "06_EXTERNAL_CR8",
        "statistics": "07_STATISTICS",
        "qc": "08_QUANTUM_QC",
        "figures": "09_FIGURES",
        "manifest": "10_MANIFEST",
    }
    if not (root / "00_README" / "PRE_RUN_AUDIT.md").is_file():
        raise FileNotFoundError("The approved PRE_RUN_AUDIT.md is missing")
    if not allow_completed and (root / "10_MANIFEST" / "ARTIFACT_MANIFEST_SHA256.csv").exists():
        raise FileExistsError("A completed campaign manifest already exists")
    paths = {key: root / value for key, value in names.items()}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def verify_input_hashes(data_dir: Path, output: Path) -> pd.DataFrame:
    rows = []
    for name, expected in EXPECTED_HASHES.items():
        path = data_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256_file(path)
        rows.append({"file": name, "expected_sha256": expected, "observed_sha256": observed, "match": observed == expected})
        if observed != expected:
            raise RuntimeError(f"Input hash mismatch: {name}")
    frame = pd.DataFrame(rows)
    frame.to_csv(output, index=False)
    return frame


def validate_development(path: Path, audit_dir: Path) -> pd.DataFrame:
    train = pd.read_csv(path)
    required = ["ID", "name", "SMILES", "LABEL", "BUTINA_CLUSTER_ID", "STRICT_CV_FOLD", *X10_FEATURES]
    missing = sorted(set(required) - set(train.columns))
    if missing:
        raise RuntimeError(f"Missing development columns: {missing}")
    if len(train) != 712 or train["LABEL"].value_counts().to_dict() != {0: 490, 1: 222}:
        raise RuntimeError("Development row or label counts differ from the frozen contract")
    values = train.loc[:, X10_FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(values).all():
        raise RuntimeError("Development X10 contains missing or non-finite values")
    if train["ID"].duplicated().any() or train["SMILES"].duplicated().any():
        raise RuntimeError("Duplicate development ID or SMILES")
    invalid = train.loc[train["SMILES"].map(lambda s: Chem.MolFromSmiles(str(s)) is None), "ID"].tolist()
    if invalid:
        raise RuntimeError(f"Invalid development SMILES: {invalid[:10]}")
    folds = train["STRICT_CV_FOLD"].astype(int)
    if set(folds) != set(OUTER_FOLDS):
        raise RuntimeError(f"Unexpected outer folds: {sorted(set(folds))}")
    if (train.groupby("BUTINA_CLUSTER_ID")["STRICT_CV_FOLD"].nunique() > 1).any():
        raise RuntimeError("A Butina cluster crosses frozen outer folds")
    rows = []
    for fold in OUTER_FOLDS:
        outer_train = train[folds != fold]
        validation = train[folds == fold]
        overlap = set(outer_train["BUTINA_CLUSTER_ID"]) & set(validation["BUTINA_CLUSTER_ID"])
        row = {
            "outer_fold": fold,
            "n_train": len(outer_train), "n_validation": len(validation),
            "train_negative": int((outer_train["LABEL"] == 0).sum()),
            "train_positive": int((outer_train["LABEL"] == 1).sum()),
            "validation_negative": int((validation["LABEL"] == 0).sum()),
            "validation_positive": int((validation["LABEL"] == 1).sum()),
            "train_clusters": outer_train["BUTINA_CLUSTER_ID"].nunique(),
            "validation_clusters": validation["BUTINA_CLUSTER_ID"].nunique(),
            "cluster_intersection": len(overlap),
        }
        if overlap:
            raise RuntimeError(f"Outer fold {fold} has cluster leakage")
        rows.append(row)
    pd.DataFrame(rows).to_csv(audit_dir / "SPLIT_INTEGRITY_AUDIT.csv", index=False)
    pd.DataFrame([
        {"partition": "development", "rows": len(train), "negative": int((train.LABEL == 0).sum()), "positive": int((train.LABEL == 1).sum())},
        {"partition": "historical_holdout", "rows": 181, "negative": 132, "positive": 49},
        {"partition": "external_CR8", "rows": 8, "negative": 6, "positive": 2},
    ]).to_csv(audit_dir / "DATASET_COUNTS.csv", index=False)
    return train


def frozen_outer_splits(train: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    return [(np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)) for fold in OUTER_FOLDS]


def inner_splits(train: pd.DataFrame, indices: np.ndarray, outer_fold: int) -> list[tuple[np.ndarray, np.ndarray]]:
    subset = train.iloc[indices]
    splitter = StratifiedGroupKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=SEED + outer_fold)
    local = list(splitter.split(np.zeros((len(subset), 1)), subset["LABEL"], subset["BUTINA_CLUSTER_ID"]))
    for train_local, validation_local in local:
        overlap = set(subset.iloc[train_local]["BUTINA_CLUSTER_ID"]) & set(subset.iloc[validation_local]["BUTINA_CLUSTER_ID"])
        if overlap:
            raise RuntimeError(f"Inner cluster leakage in outer fold {outer_fold}")
    return local


def classification_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float | int]:
    truth = np.asarray(y_true, dtype=int)
    score = np.asarray(scores, dtype=float)
    pred = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
    return {
        "auroc": float(roc_auc_score(truth, score)),
        "auprc": float(average_precision_score(truth, score)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
        "mcc": float(matthews_corrcoef(truth, pred)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else float("nan"),
        "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
    }


def select_threshold(y_true: np.ndarray, scores: np.ndarray) -> tuple[float, dict[str, float | int]]:
    score = np.asarray(scores, dtype=float)
    candidates = np.r_[np.unique(score), np.nextafter(score.max(), np.inf)]
    ranked = []
    for threshold in candidates:
        metrics = classification_metrics(y_true, score, float(threshold))
        ranked.append((-float(metrics["mcc"]), -float(metrics["balanced_accuracy"]), abs(float(threshold)), float(threshold), metrics))
    _, _, _, threshold, metrics = min(ranked, key=lambda row: row[:4])
    return threshold, metrics


def prediction_rows(frame: pd.DataFrame, model: str, fold: int | str, scores: np.ndarray, threshold: float) -> list[dict[str, Any]]:
    pred = (scores >= threshold).astype(int)
    rows = []
    for source, score, label in zip(frame.itertuples(index=False), scores, pred):
        rows.append({
            "ID": int(source.ID), "name": str(source.name),
            "BUTINA_CLUSTER_ID": (
                int(source.BUTINA_CLUSTER_ID)
                if hasattr(source, "BUTINA_CLUSTER_ID") and pd.notna(source.BUTINA_CLUSTER_ID)
                else None
            ),
            "MODEL": model, "OUTER_FOLD": fold, "LABEL": int(source.LABEL),
            "SCORE": float(score), "THRESHOLD": float(threshold),
            "MARGIN": float(score - threshold), "PRED": int(label),
        })
    return rows


def qc_kernel(kernel: np.ndarray, *, model: str, stage: str, fold: Any, params: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    if model not in QUANTUM_MODELS:
        return
    matrix = np.asarray(kernel, dtype=float)
    symmetry = float(np.max(np.abs(matrix - matrix.T)))
    diagonal = float(np.max(np.abs(np.diag(matrix) - 1.0)))
    min_eigenvalue = float(np.linalg.eigvalsh((matrix + matrix.T) / 2.0).min())
    passed = symmetry < 1e-10 and diagonal < 1e-10 and min_eigenvalue >= -1e-8
    rows.append({
        "MODEL": model, "STAGE": stage, "FOLD": fold,
        "N": len(matrix), "PARAMS": json.dumps(jsonable(params), sort_keys=True),
        "SYMMETRY_ERROR": symmetry, "DIAGONAL_ERROR": diagonal,
        "MIN_EIGENVALUE": min_eigenvalue, "PASS": passed,
    })
    if not passed:
        raise RuntimeError(f"Quantum kernel QC failed: {model}, {stage}, fold={fold}")


def classical_inner_oof(spec: Any, params: dict[str, Any], x: np.ndarray, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    scores = np.full(len(y), np.nan)
    for train_idx, val_idx in splits:
        estimator = clone(spec.estimator).set_params(**params)
        estimator.fit(x[train_idx], y[train_idx])
        scores[val_idx] = continuous_scores(estimator, x[val_idx])
    if not np.isfinite(scores).all():
        raise RuntimeError("Missing classical inner OOF scores")
    return scores


def select_classical(spec: Any, x: np.ndarray, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]]) -> tuple[dict[str, Any], float, float]:
    search = GridSearchCV(clone(spec.estimator), spec.param_grid, scoring="roc_auc", cv=splits, n_jobs=1, refit=False, error_score="raise")
    search.fit(x, y)
    index = int(search.best_index_)
    return dict(search.best_params_), float(search.best_score_), float(search.cv_results_["std_test_score"][index])


def kernel_inner_oof(model: str, params: dict[str, float], x: np.ndarray, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]], qc_rows: list[dict[str, Any]], stage: str, fold: Any) -> np.ndarray:
    scores = np.full(len(y), np.nan)
    kernel_params = {k: v for k, v in params.items() if k != "C"}
    for inner_fold, (train_idx, val_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(x[train_idx])
        train_scaled = scaler.transform(x[train_idx])
        validation_scaled = scaler.transform(x[val_idx])
        train_kernel, validation_kernel = _kernel_matrices(model, kernel_params, train_scaled, validation_scaled)
        qc_kernel(train_kernel, model=model, stage=stage, fold=f"{fold}.{inner_fold}", params=params, rows=qc_rows)
        classifier = SVC(C=float(params["C"]), kernel="precomputed", class_weight="balanced", random_state=SEED)
        classifier.fit(train_kernel, y[train_idx])
        scores[val_idx] = classifier.decision_function(validation_kernel)
    if not np.isfinite(scores).all():
        raise RuntimeError("Missing kernel inner OOF scores")
    return scores


def select_kernel(model: str, x: np.ndarray, y: np.ndarray, splits: list[tuple[np.ndarray, np.ndarray]], qc_rows: list[dict[str, Any]], stage: str, fold: Any) -> tuple[dict[str, float], float, float]:
    candidates = _kernel_candidates(model, QUANTUM_CONFIG)
    c_values = QUANTUM_CONFIG["c_values"]
    scores: dict[tuple[int, float], list[float]] = {(i, float(c)): [] for i in range(len(candidates)) for c in c_values}
    for inner_fold, (train_idx, val_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(x[train_idx])
        train_scaled = scaler.transform(x[train_idx])
        validation_scaled = scaler.transform(x[val_idx])
        for candidate_index, kernel_params in enumerate(candidates):
            train_kernel, validation_kernel = _kernel_matrices(model, kernel_params, train_scaled, validation_scaled)
            qc_kernel(train_kernel, model=model, stage=f"{stage}_hpo", fold=f"{fold}.{inner_fold}", params=kernel_params, rows=qc_rows)
            for c in c_values:
                classifier = SVC(C=float(c), kernel="precomputed", class_weight="balanced", random_state=SEED)
                classifier.fit(train_kernel, y[train_idx])
                score = classifier.decision_function(validation_kernel)
                scores[(candidate_index, float(c))].append(float(roc_auc_score(y[val_idx], score)))
    ranked = sorted(
        ((float(np.mean(values)), float(np.std(values, ddof=1)), candidate_index, c) for (candidate_index, c), values in scores.items()),
        key=lambda item: (-item[0], item[2], item[3]),
    )
    mean_score, std_score, candidate_index, c = ranked[0]
    return {"C": c, **candidates[candidate_index]}, mean_score, std_score


def run_nested(train: pd.DataFrame, nested_dir: Path, qc_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x_all = train.loc[:, X10_FEATURES].to_numpy(float)
    y_all = train["LABEL"].to_numpy(int)
    specs = model_specs(SEED, quick=False)
    metric_rows: list[dict[str, Any]] = []
    oof_rows: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []
    qc_rows: list[dict[str, Any]] = []

    for outer_fold, (outer_train, outer_validation) in zip(OUTER_FOLDS, frozen_outer_splits(train)):
        splits = inner_splits(train, outer_train, outer_fold)
        x_train, y_train = x_all[outer_train], y_all[outer_train]
        x_validation, y_validation = x_all[outer_validation], y_all[outer_validation]

        for model in CLASSICAL_MODELS:
            spec = specs[model]
            params, inner_mean, inner_std = select_classical(spec, x_train, y_train, splits)
            inner_scores = classical_inner_oof(spec, params, x_train, y_train, splits)
            threshold, threshold_metrics = select_threshold(y_train, inner_scores)
            estimator = clone(spec.estimator).set_params(**params)
            estimator.fit(x_train, y_train)
            scores = continuous_scores(estimator, x_validation)
            metrics = classification_metrics(y_validation, scores, threshold)
            metric_rows.append({"MODEL": model, "OUTER_FOLD": outer_fold, "N_TRAIN": len(outer_train), "N_VALIDATION": len(outer_validation), "INNER_AUROC_MEAN": inner_mean, "INNER_AUROC_SD": inner_std, "THRESHOLD": threshold, **{k.upper(): v for k, v in metrics.items()}})
            parameter_rows.append({"MODEL": model, "OUTER_FOLD": outer_fold, "BEST_PARAMS": json.dumps(jsonable(params), sort_keys=True), "INNER_AUROC_MEAN": inner_mean, "INNER_AUROC_SD": inner_std, "THRESHOLD": threshold, "INNER_THRESHOLD_MCC": threshold_metrics["mcc"], "INNER_THRESHOLD_BA": threshold_metrics["balanced_accuracy"]})
            oof_rows.extend(prediction_rows(train.iloc[outer_validation], model, outer_fold, scores, threshold))

        for model in KERNEL_MODELS:
            params, inner_mean, inner_std = select_kernel(model, x_train, y_train, splits, qc_rows, "nested", outer_fold)
            inner_scores = kernel_inner_oof(model, params, x_train, y_train, splits, qc_rows, "nested_threshold", outer_fold)
            threshold, threshold_metrics = select_threshold(y_train, inner_scores)
            scaler = StandardScaler().fit(x_train)
            train_scaled = scaler.transform(x_train)
            validation_scaled = scaler.transform(x_validation)
            kernel_params = {k: v for k, v in params.items() if k != "C"}
            train_kernel, validation_kernel = _kernel_matrices(model, kernel_params, train_scaled, validation_scaled)
            qc_kernel(train_kernel, model=model, stage="nested_outer_fit", fold=outer_fold, params=params, rows=qc_rows)
            classifier = SVC(C=float(params["C"]), kernel="precomputed", class_weight="balanced", random_state=SEED)
            classifier.fit(train_kernel, y_train)
            scores = classifier.decision_function(validation_kernel)
            metrics = classification_metrics(y_validation, scores, threshold)
            metric_rows.append({"MODEL": model, "OUTER_FOLD": outer_fold, "N_TRAIN": len(outer_train), "N_VALIDATION": len(outer_validation), "INNER_AUROC_MEAN": inner_mean, "INNER_AUROC_SD": inner_std, "THRESHOLD": threshold, **{k.upper(): v for k, v in metrics.items()}})
            parameter_rows.append({"MODEL": model, "OUTER_FOLD": outer_fold, "BEST_PARAMS": json.dumps(jsonable(params), sort_keys=True), "INNER_AUROC_MEAN": inner_mean, "INNER_AUROC_SD": inner_std, "THRESHOLD": threshold, "INNER_THRESHOLD_MCC": threshold_metrics["mcc"], "INNER_THRESHOLD_BA": threshold_metrics["balanced_accuracy"]})
            oof_rows.extend(prediction_rows(train.iloc[outer_validation], model, outer_fold, scores, threshold))

    metrics_frame = pd.DataFrame(metric_rows)
    oof_frame = pd.DataFrame(oof_rows)
    params_frame = pd.DataFrame(parameter_rows)
    qc_frame = pd.DataFrame(qc_rows)
    expected = len(train) * len(PRIMARY_MODELS)
    if len(oof_frame) != expected:
        raise RuntimeError(f"Expected {expected} nested OOF predictions; found {len(oof_frame)}")
    if oof_frame.duplicated(["MODEL", "ID"]).any():
        raise RuntimeError("Duplicate nested OOF model/ID predictions")
    if set(oof_frame.groupby("MODEL").size()) != {len(train)}:
        raise RuntimeError("Missing nested OOF predictions")

    summaries = []
    for model in PRIMARY_MODELS:
        model_metrics = metrics_frame[metrics_frame.MODEL == model]
        model_oof = oof_frame[oof_frame.MODEL == model]
        pooled = classification_metrics(model_oof.LABEL.to_numpy(int), model_oof.SCORE.to_numpy(float), 0.0)
        pooled_pred = model_oof.PRED.to_numpy(int)
        truth = model_oof.LABEL.to_numpy(int)
        tn, fp, fn, tp = confusion_matrix(truth, pooled_pred, labels=[0, 1]).ravel()
        summaries.append({
            "MODEL": model,
            "OUTER_AUROC_MEAN": model_metrics.AUROC.mean(), "OUTER_AUROC_SD": model_metrics.AUROC.std(ddof=1),
            "OUTER_AUPRC_MEAN": model_metrics.AUPRC.mean(), "OUTER_AUPRC_SD": model_metrics.AUPRC.std(ddof=1),
            "POOLED_OOF_AUROC": pooled["auroc"], "POOLED_OOF_AUPRC": pooled["auprc"],
            "POOLED_OOF_BALANCED_ACCURACY": balanced_accuracy_score(truth, pooled_pred),
            "POOLED_OOF_MCC": matthews_corrcoef(truth, pooled_pred),
            "POOLED_OOF_SENSITIVITY": tp / (tp + fn), "POOLED_OOF_SPECIFICITY": tn / (tn + fp),
            "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        })
    summary_frame = pd.DataFrame(summaries).sort_values("OUTER_AUROC_MEAN", ascending=False)
    metrics_frame.to_csv(nested_dir / "NESTED_FOLD_METRICS.csv", index=False)
    summary_frame.to_csv(nested_dir / "NESTED_SUMMARY.csv", index=False)
    oof_frame.to_csv(nested_dir / "NESTED_OUTER_OOF_PREDICTIONS.csv", index=False)
    params_frame.to_csv(nested_dir / "SELECTED_PARAMS_PER_OUTER_FOLD.csv", index=False)
    qc_frame.to_csv(qc_dir / "QUANTUM_KERNEL_QC.csv", index=False)
    return metrics_frame, summary_frame, oof_frame, qc_frame


def append_qc(path: Path, rows: list[dict[str, Any]]) -> None:
    existing = pd.read_csv(path)
    pd.concat([existing, pd.DataFrame(rows)], ignore_index=True).to_csv(path, index=False)


def final_selection(train: pd.DataFrame, final_dir: Path, qc_dir: Path) -> tuple[dict[str, FrozenClassical | FrozenKernel], list[dict[str, Any]]]:
    x = train.loc[:, X10_FEATURES].to_numpy(float)
    y = train["LABEL"].to_numpy(int)
    splits = frozen_outer_splits(train)
    specs = model_specs(SEED, quick=False)
    frozen: dict[str, FrozenClassical | FrozenKernel] = {}
    selections: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    qc_rows: list[dict[str, Any]] = []
    artifact_dir = final_dir / "model_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    for model in CLASSICAL_MODELS:
        spec = specs[model]
        params, mean_auc, std_auc = select_classical(spec, x, y, splits)
        oof_scores = classical_inner_oof(spec, params, x, y, splits)
        threshold, threshold_metrics = select_threshold(y, oof_scores)
        estimator = clone(spec.estimator).set_params(**params).fit(x, y)
        bundle = FrozenClassical(estimator=estimator, threshold=threshold)
        frozen[model] = bundle
        artifact = artifact_dir / f"{model}.pkl"
        with artifact.open("wb") as stream:
            pickle.dump(bundle, stream, protocol=pickle.HIGHEST_PROTOCOL)
        selections.append({"model": model, "best_params": jsonable(params), "development_cv_mean_auroc": mean_auc, "development_cv_sd_auroc": std_auc, "final_threshold": threshold, "threshold_inner_oof_mcc": threshold_metrics["mcc"], "threshold_inner_oof_balanced_accuracy": threshold_metrics["balanced_accuracy"], "artifact": artifact.relative_to(final_dir).as_posix(), "artifact_sha256": sha256_file(artifact)})
        thresholds.append({"MODEL": model, "THRESHOLD": threshold, "CRITERION": "max_MCC_then_BA_on_development_OOF"})

    for model in KERNEL_MODELS:
        params, mean_auc, std_auc = select_kernel(model, x, y, splits, qc_rows, "final_selection", "all")
        oof_scores = kernel_inner_oof(model, params, x, y, splits, qc_rows, "final_threshold", "all")
        threshold, threshold_metrics = select_threshold(y, oof_scores)
        scaler = StandardScaler().fit(x)
        train_scaled = scaler.transform(x)
        kernel_params = {k: v for k, v in params.items() if k != "C"}
        train_kernel, _ = _kernel_matrices(model, kernel_params, train_scaled)
        qc_kernel(train_kernel, model=model, stage="final_full_development_fit", fold="all", params=params, rows=qc_rows)
        classifier = SVC(C=float(params["C"]), kernel="precomputed", class_weight="balanced", random_state=SEED).fit(train_kernel, y)
        bundle = FrozenKernel(scaler=scaler, classifier=classifier, train_scaled=train_scaled, params=params, threshold=threshold)
        frozen[model] = bundle
        artifact = artifact_dir / f"{model}.pkl"
        with artifact.open("wb") as stream:
            pickle.dump(bundle, stream, protocol=pickle.HIGHEST_PROTOCOL)
        selections.append({"model": model, "best_params": jsonable(params), "development_cv_mean_auroc": mean_auc, "development_cv_sd_auroc": std_auc, "final_threshold": threshold, "threshold_inner_oof_mcc": threshold_metrics["mcc"], "threshold_inner_oof_balanced_accuracy": threshold_metrics["balanced_accuracy"], "artifact": artifact.relative_to(final_dir).as_posix(), "artifact_sha256": sha256_file(artifact)})
        thresholds.append({"MODEL": model, "THRESHOLD": threshold, "CRITERION": "max_MCC_then_BA_on_development_OOF"})

    append_qc(qc_dir / "QUANTUM_KERNEL_QC.csv", qc_rows)
    write_json(final_dir / "FINAL_MODEL_SELECTIONS.json", {"selection_scope": "development_only", "performance_status": "not_unbiased_performance_estimate", "seed": SEED, "models": selections})
    pd.DataFrame(thresholds).to_csv(final_dir / "FINAL_THRESHOLDS.csv", index=False)
    return frozen, selections


def create_freeze(root: Path, paths: dict[str, Path]) -> dict[str, str]:
    files = []
    for key in ("config", "audit", "nested", "final", "qc"):
        files.extend(path for path in paths[key].rglob("*") if path.is_file())
    hashes = {path.relative_to(root).as_posix(): sha256_file(path) for path in sorted(files)}
    payload = {
        "status": "development_frozen",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_or_cr8_content_read_before_freeze": False,
        "artifact_hashes": hashes,
    }
    freeze_path = paths["final"] / "DEVELOPMENT_FREEZE_MANIFEST.json"
    write_json(freeze_path, payload)
    for relative, expected in hashes.items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"Freeze verification failed: {relative}")
    return hashes


def validate_postfreeze_frame(frame: pd.DataFrame, *, expected_rows: int, expected_labels: dict[int, int], source: str) -> None:
    required = {"ID", "name", "SMILES", "LABEL", *X10_FEATURES}
    missing = sorted(required - set(frame.columns))
    if missing or len(frame) != expected_rows:
        raise RuntimeError(f"{source} schema/count mismatch: missing={missing}, rows={len(frame)}")
    labels = {int(k): int(v) for k, v in frame.LABEL.value_counts().to_dict().items()}
    if labels != expected_labels:
        raise RuntimeError(f"{source} label count mismatch: {labels}")
    values = frame.loc[:, X10_FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(values).all():
        raise RuntimeError(f"{source} has invalid X10")


def score_frozen(frozen: dict[str, FrozenClassical | FrozenKernel], frame: pd.DataFrame, evaluation: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = frame.loc[:, X10_FEATURES].to_numpy(float)
    predictions = []
    metrics = []
    for model in PRIMARY_MODELS:
        bundle = frozen[model]
        if isinstance(bundle, FrozenClassical):
            scores = continuous_scores(bundle.estimator, x)
            threshold = bundle.threshold
        else:
            scaled = bundle.scaler.transform(x)
            kernel_params = {k: v for k, v in bundle.params.items() if k != "C"}
            _, cross_kernel = _kernel_matrices(model, kernel_params, bundle.train_scaled, scaled)
            scores = bundle.classifier.decision_function(cross_kernel)
            threshold = bundle.threshold
        predictions.extend(prediction_rows(frame, model, evaluation, scores, threshold))
        metrics.append({"EVALUATION": evaluation, "MODEL": model, "N": len(frame), **{k.upper(): v for k, v in classification_metrics(frame.LABEL.to_numpy(int), scores, threshold).items()}})
    return pd.DataFrame(predictions), pd.DataFrame(metrics)


def applicability_and_neighbors(train: pd.DataFrame, external: pd.DataFrame, external_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=1024, includeChirality=True)
    train_molecules = [Chem.MolFromSmiles(str(value)) for value in train.SMILES]
    external_molecules = [Chem.MolFromSmiles(str(value)) for value in external.SMILES]
    if any(mol is None for mol in train_molecules + external_molecules):
        raise RuntimeError("Invalid SMILES in applicability-domain inputs")
    train_fingerprints = [generator.GetFingerprint(mol) for mol in train_molecules]
    external_fingerprints = [generator.GetFingerprint(mol) for mol in external_molecules]

    loo_smax = np.empty(len(train))
    for index, fingerprint in enumerate(train_fingerprints):
        similarities = np.asarray(DataStructs.BulkTanimotoSimilarity(fingerprint, train_fingerprints), dtype=float)
        similarities[index] = -np.inf
        loo_smax[index] = similarities.max()
    structural_threshold = float(np.quantile(loo_smax, 0.05))

    scaler = StandardScaler().fit(train.loc[:, X10_FEATURES].to_numpy(float))
    train_scaled = scaler.transform(train.loc[:, X10_FEATURES].to_numpy(float))
    external_scaled = scaler.transform(external.loc[:, X10_FEATURES].to_numpy(float))
    train_distances = pairwise_distances(train_scaled)
    np.fill_diagonal(train_distances, np.inf)
    loo_d5 = np.sort(train_distances, axis=1)[:, :5].mean(axis=1)
    descriptor_threshold = float(np.quantile(loo_d5, 0.95))
    cross_distances = pairwise_distances(external_scaled, train_scaled)

    ad_rows = []
    neighbor_rows = []
    for external_index, (row, fingerprint) in enumerate(zip(external.itertuples(index=False), external_fingerprints)):
        similarities = np.asarray(DataStructs.BulkTanimotoSimilarity(fingerprint, train_fingerprints), dtype=float)
        order = np.argsort(-similarities, kind="stable")[:10]
        smax = float(similarities[order[0]])
        d5 = float(np.sort(cross_distances[external_index])[:5].mean())
        structural_in = smax >= structural_threshold
        descriptor_in = d5 <= descriptor_threshold
        ad_rows.append({
            "ID": int(row.ID), "name": str(row.name), "LABEL": int(row.LABEL),
            "Smax_Morgan": smax, "structural_P05_threshold": structural_threshold,
            "structural_AD": "IN" if structural_in else "OUT",
            "d5NN_X10": d5, "descriptor_P95_threshold": descriptor_threshold,
            "descriptor_AD": "IN" if descriptor_in else "OUT",
            "DUAL_AD": f"{'IN' if structural_in else 'OUT'}/{'IN' if descriptor_in else 'OUT'}",
        })
        for rank, train_index in enumerate(order, start=1):
            neighbor = train.iloc[int(train_index)]
            neighbor_rows.append({
                "CR8_ID": int(row.ID), "CR8_name": str(row.name), "CR8_LABEL": int(row.LABEL),
                "Smax": smax, "RANK": rank, "NEIGHBOR_ID": int(neighbor.ID),
                "NEIGHBOR_name": str(neighbor["name"]), "NEIGHBOR_SMILES": str(neighbor.SMILES),
                "TANIMOTO": float(similarities[train_index]), "NEIGHBOR_LABEL": int(neighbor.LABEL),
                "TOP5_LOCAL_TOXIC_FRACTION": float(train.iloc[order[:5]].LABEL.mean()),
                "TOP10_LOCAL_TOXIC_FRACTION": float(train.iloc[order].LABEL.mean()),
            })
    ad = pd.DataFrame(ad_rows)
    neighbors = pd.DataFrame(neighbor_rows)
    ad.to_csv(external_dir / "CR8_DUAL_AD.csv", index=False)
    neighbors.to_csv(external_dir / "CR8_TOP10_TANIMOTO_NEIGHBORS.csv", index=False)
    thresholds = {"structural_P05_LOO_Smax": structural_threshold, "descriptor_P95_LOO_mean_5NN": descriptor_threshold}
    write_json(external_dir / "AD_THRESHOLDS.json", thresholds)
    return ad, neighbors, thresholds


def paired_cluster_bootstrap(oof: pd.DataFrame, output: Path) -> pd.DataFrame:
    wide_score = oof.pivot(index=["ID", "BUTINA_CLUSTER_ID", "LABEL"], columns="MODEL", values="SCORE").reset_index()
    clusters = sorted(wide_score.BUTINA_CLUSTER_ID.unique())
    cluster_indices = {cluster: np.flatnonzero(wide_score.BUTINA_CLUSTER_ID.to_numpy() == cluster) for cluster in clusters}
    comparisons = [
        ("random_forest", "logistic"),
        ("random_forest", "mlp"),
        ("quantum_angle_product", "rbf_matched"),
        ("quantum_iqp_zz_linear", "rbf_matched"),
        ("quantum_angle_product", "quantum_iqp_zz_linear"),
    ]
    metrics = {"AUROC": roc_auc_score, "AUPRC": average_precision_score}
    truth = wide_score.LABEL.to_numpy(int)
    observed: dict[tuple[str, str, str], float] = {}
    deltas: dict[tuple[str, str, str], list[float]] = {}
    for left, right in comparisons:
        for metric, function in metrics.items():
            key = (left, right, metric)
            observed[key] = float(function(truth, wide_score[left]) - function(truth, wide_score[right]))
            deltas[key] = []
    rng = np.random.default_rng(SEED)
    cluster_array = np.asarray(clusters)
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled_clusters = rng.choice(cluster_array, size=len(cluster_array), replace=True)
        sampled = np.concatenate([cluster_indices[cluster] for cluster in sampled_clusters])
        labels = truth[sampled]
        if len(np.unique(labels)) < 2:
            continue
        for left, right in comparisons:
            for metric, function in metrics.items():
                deltas[(left, right, metric)].append(float(function(labels, wide_score[left].to_numpy()[sampled]) - function(labels, wide_score[right].to_numpy()[sampled])))
    rows = []
    for key, values in deltas.items():
        left, right, metric = key
        array = np.asarray(values)
        rows.append({
            "LEFT_MODEL": left, "RIGHT_MODEL": right, "METRIC": metric,
            "OBSERVED_DELTA": observed[key], "BOOTSTRAP_MEDIAN": float(np.median(array)),
            "CI_LOW_95": float(np.quantile(array, 0.025)), "CI_HIGH_95": float(np.quantile(array, 0.975)),
            "P_DELTA_GT_0": float(np.mean(array > 0)), "REPLICATES": len(array),
            "RESAMPLING_UNIT": "BUTINA_CLUSTER_ID",
        })
    frame = pd.DataFrame(rows)
    frame.to_csv(output, index=False)
    return frame


def y_randomization(train: pd.DataFrame, selections: list[dict[str, Any]], oof: pd.DataFrame, output: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = train.loc[:, X10_FEATURES].to_numpy(float)
    original_y = train.LABEL.to_numpy(int)
    outer = frozen_outer_splits(train)
    specs = model_specs(SEED, quick=False)
    selection_map = {row["model"]: row for row in selections}

    kernel_cache: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    for model in KERNEL_MODELS:
        params = selection_map[model]["best_params"]
        kernel_params = {k: v for k, v in params.items() if k != "C"}
        for fold_index, (train_idx, val_idx) in enumerate(outer, start=1):
            scaler = StandardScaler().fit(x[train_idx])
            train_scaled = scaler.transform(x[train_idx])
            val_scaled = scaler.transform(x[val_idx])
            kernel_cache[(model, fold_index)] = _kernel_matrices(model, kernel_params, train_scaled, val_scaled)

    rng = np.random.default_rng(SEED)
    raw_rows = []
    for permutation in range(1, Y_RANDOMIZATION_REPLICATES + 1):
        permuted = rng.permutation(original_y)
        for model in PRIMARY_MODELS:
            scores = np.full(len(train), np.nan)
            params = selection_map[model]["best_params"]
            for fold_index, (train_idx, val_idx) in enumerate(outer, start=1):
                if model in CLASSICAL_MODELS:
                    estimator = clone(specs[model].estimator).set_params(**params)
                    estimator.fit(x[train_idx], permuted[train_idx])
                    scores[val_idx] = continuous_scores(estimator, x[val_idx])
                else:
                    train_kernel, val_kernel = kernel_cache[(model, fold_index)]
                    classifier = SVC(C=float(params["C"]), kernel="precomputed", class_weight="balanced", random_state=SEED)
                    classifier.fit(train_kernel, permuted[train_idx])
                    scores[val_idx] = classifier.decision_function(val_kernel)
            raw_rows.append({"MODEL": model, "PERMUTATION": permutation, "RANDOMIZED_AUROC": float(roc_auc_score(permuted, scores)), "MODE": "fixed_configuration"})
        if permutation % 20 == 0:
            print(f"Y-randomization: {permutation}/{Y_RANDOMIZATION_REPLICATES}", flush=True)
    raw = pd.DataFrame(raw_rows)
    real = oof.groupby("MODEL").apply(lambda group: roc_auc_score(group.LABEL, group.SCORE), include_groups=False).to_dict()
    summary_rows = []
    for model in PRIMARY_MODELS:
        values = raw.loc[raw.MODEL == model, "RANDOMIZED_AUROC"].to_numpy()
        summary_rows.append({
            "MODEL": model, "REAL_NESTED_OOF_AUROC": float(real[model]),
            "MEAN_RANDOMIZED_AUROC": float(values.mean()), "SD_RANDOMIZED_AUROC": float(values.std(ddof=1)),
            "P95_RANDOMIZED_AUROC": float(np.quantile(values, 0.95)),
            "EMPIRICAL_FRACTION_RANDOMIZED_GE_REAL": float(np.mean(values >= real[model])),
            "PERMUTATIONS": len(values), "MODE": "fixed_configuration_Y_randomization",
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output, index=False)
    raw.to_csv(output.with_name("Y_RANDOMIZATION_RAW.csv"), index=False)
    return summary, raw


MODEL_LABELS = {
    "logistic": "Logistic regression", "random_forest": "Random Forest", "mlp": "MLP",
    "rbf_matched": "Matched RBF", "quantum_angle_product": "Product QK",
    "quantum_iqp_zz_linear": "IQP-ZZ QK",
}


def save_figure(fig: plt.Figure, base: Path) -> None:
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def generate_figures(metrics: pd.DataFrame, oof: pd.DataFrame, y_raw: pd.DataFrame, ad: pd.DataFrame, cr8_predictions: pd.DataFrame, neighbors: pd.DataFrame, external: pd.DataFrame, train: pd.DataFrame, figures_dir: Path) -> None:
    colors = {model: color for model, color in zip(PRIMARY_MODELS, ["#4C78A8", "#59A14F", "#9C755F", "#E15759", "#B279A2", "#F28E2B"])}
    for metric, filename, xlabel in (("AUROC", "FIG01_NESTED_AUROC", "Outer-fold AUROC"), ("AUPRC", "FIG02_NESTED_AUPRC", "Outer-fold AUPRC")):
        fig, axis = plt.subplots(figsize=(7.2, 4.2))
        for index, model in enumerate(PRIMARY_MODELS):
            values = metrics.loc[metrics.MODEL == model, metric].to_numpy(float)
            axis.scatter(values, np.full(len(values), index), color=colors[model], alpha=0.75, s=28)
            axis.errorbar(values.mean(), index, xerr=values.std(ddof=1), fmt="o", color="black", capsize=3)
        axis.set_yticks(range(len(PRIMARY_MODELS)), [MODEL_LABELS[m] for m in PRIMARY_MODELS])
        axis.set_xlabel(xlabel); axis.grid(axis="x", alpha=0.25); axis.invert_yaxis()
        save_figure(fig, figures_dir / filename)

    fig, axis = plt.subplots(figsize=(8.0, 4.5))
    arrays = [y_raw.loc[y_raw.MODEL == model, "RANDOMIZED_AUROC"] for model in PRIMARY_MODELS]
    axis.violinplot(arrays, positions=np.arange(len(PRIMARY_MODELS)), showmeans=True, widths=0.8)
    for index, model in enumerate(PRIMARY_MODELS):
        group = oof[oof.MODEL == model]
        axis.scatter(index, roc_auc_score(group.LABEL, group.SCORE), color=colors[model], edgecolor="black", zorder=3)
    axis.axhline(0.5, color="gray", linestyle="--", linewidth=1)
    axis.set_xticks(range(len(PRIMARY_MODELS)), [MODEL_LABELS[m] for m in PRIMARY_MODELS], rotation=25, ha="right")
    axis.set_ylabel("AUROC"); axis.set_title("Fixed-configuration Y-randomization")
    save_figure(fig, figures_dir / "FIG03_Y_RANDOMIZATION")

    fig, axis = plt.subplots(figsize=(6.5, 4.8))
    axis.scatter(ad.Smax_Morgan, ad.d5NN_X10, color="#4C78A8")
    axis.axvline(ad.structural_P05_threshold.iloc[0], color="gray", linestyle="--")
    axis.axhline(ad.descriptor_P95_threshold.iloc[0], color="gray", linestyle="--")
    for row in ad.itertuples(index=False):
        if str(row.name).lower() in {"ethiprole", "isocycloseram"}:
            axis.annotate(row.name, (row.Smax_Morgan, row.d5NN_X10), xytext=(5, 5), textcoords="offset points")
    axis.set_xlabel("Maximum Morgan Tanimoto to development")
    axis.set_ylabel("Mean standardized-X10 distance to 5 neighbors")
    save_figure(fig, figures_dir / "FIG04_DUAL_AD_CR8")

    margin = cr8_predictions.pivot(index="name", columns="MODEL", values="MARGIN").reindex(columns=PRIMARY_MODELS)
    fig, axis = plt.subplots(figsize=(8.5, 5.0))
    maximum = max(abs(margin.to_numpy()).max(), 1e-12)
    image = axis.imshow(margin, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-maximum, vcenter=0, vmax=maximum), aspect="auto")
    axis.set_yticks(range(len(margin)), margin.index)
    axis.set_xticks(range(len(PRIMARY_MODELS)), [MODEL_LABELS[m] for m in PRIMARY_MODELS], rotation=30, ha="right")
    fig.colorbar(image, ax=axis, label="Score − frozen threshold")
    save_figure(fig, figures_dir / "FIG05_CR8_SCORE_MARGIN")

    external_lookup = external.set_index("name")
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=1024, includeChirality=True)
    train_molecules = [Chem.MolFromSmiles(str(value)) for value in train.SMILES]
    train_fingerprints = [generator.GetFingerprint(molecule) for molecule in train_molecules]
    for target, filename in (("Ethiprole", "FIG06_ETHIPROLE_NEIGHBORS"), ("Isocycloseram", "FIG07_ISOCYCLOSERAM_NEIGHBORS")):
        matches = [name for name in external_lookup.index if str(name).lower() == target.lower()]
        if not matches:
            continue
        actual = matches[0]
        target_molecule = Chem.MolFromSmiles(str(external_lookup.loc[actual, "SMILES"]))
        target_fingerprint = generator.GetFingerprint(target_molecule)
        similarities = np.asarray(DataStructs.BulkTanimotoSimilarity(target_fingerprint, train_fingerprints), dtype=float)
        toxic_indices = np.flatnonzero(train.LABEL.to_numpy(int) == 1)
        nontoxic_indices = np.flatnonzero(train.LABEL.to_numpy(int) == 0)
        toxic_index = int(toxic_indices[np.argmax(similarities[toxic_indices])])
        nontoxic_index = int(nontoxic_indices[np.argmax(similarities[nontoxic_indices])])
        toxic = train.iloc[toxic_index]
        nontoxic = train.iloc[nontoxic_index]
        molecules = [target_molecule, train_molecules[toxic_index], train_molecules[nontoxic_index]]
        legends = [
            f"Target: {actual}\nlabel={int(external_lookup.loc[actual, 'LABEL'])}",
            f"Closest toxic\nID={int(toxic.ID)} | T={similarities[toxic_index]:.3f}",
            f"Closest non-toxic\nID={int(nontoxic.ID)} | T={similarities[nontoxic_index]:.3f}",
        ]
        image = Draw.MolsToGridImage(molecules, molsPerRow=3, subImgSize=(500, 400), legends=legends, useSVG=False)
        image.save(figures_dir / f"{filename}.png", dpi=(300, 300))
        svg = Draw.MolsToGridImage(molecules, molsPerRow=3, subImgSize=(500, 400), legends=legends, useSVG=True)
        (figures_dir / f"{filename}.svg").write_text(str(svg), encoding="utf-8")


def write_initial_config(paths: dict[str, Path], input_hashes: pd.DataFrame) -> None:
    config = {
        "campaign": "BEEQ_FINAL_NESTED_STRUCT_IMPL",
        "seed": SEED, "outer_folds": list(OUTER_FOLDS), "inner_folds": INNER_FOLDS,
        "selection_metric": "mean_inner_AUROC",
        "threshold_policy": "max_MCC_then_balanced_accuracy_on_inner_OOF",
        "features": list(X10_FEATURES), "primary_models": list(PRIMARY_MODELS),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "y_randomization_replicates": Y_RANDOMIZATION_REPLICATES,
        "y_randomization_mode": "fixed_configuration",
        "input_hashes": dict(zip(input_hashes.file, input_hashes.observed_sha256)),
    }
    write_json(paths["config"] / "CAMPAIGN_CONFIG.json", config)
    write_json(paths["config"] / "HYPERPARAMETER_SPACES.json", HYPERPARAMETER_SPACES)
    write_json(paths["config"] / "MODEL_DEFINITIONS.json", {
        "logistic": {"implementation": "src.classical_models.model_specs", "scaler": "StandardScaler", "class_weight": "balanced", "solver": "liblinear", "max_iter": 5000},
        "random_forest": {"implementation": "src.classical_models.model_specs", "n_estimators": 300, "class_weight": "balanced_subsample", "max_features": "sqrt", "scaler": None},
        "mlp": {"implementation": "src.classical_models.model_specs", "scaler": "StandardScaler", "max_iter": 2000, "early_stopping": True},
        "rbf_matched": {"implementation": "src.kernels.rbf_kernel", "classifier": "class-weighted precomputed SVC"},
        "quantum_angle_product": {"implementation": "src.quantum_feature_maps.angle_product_statevectors", "classifier": "class-weighted precomputed SVC"},
        "quantum_iqp_zz_linear": {"implementation": "src.quantum_feature_maps.iqp_zz_linear_statevectors", "classifier": "class-weighted precomputed SVC"},
    })
    write_json(paths["config"] / "QUANTUM_FEATURE_MAPS.json", {
        "backend": "exact_numpy_statevector", "qubits": 10, "statevector_dimension": 1024, "shots": None, "noise": None,
        "fidelity_kernel": "abs(<psi(x)|psi(y)>)**2",
        "product": {"encoding": "one RY angle per standardized/scaled X10 descriptor", "entanglement": "none", "reps": 1},
        "iqp_zz_linear": {"encoding": "uniform superposition with diagonal linear-Z and x_j*x_(j+1) nearest-neighbor ZZ phases", "entanglement": "linear nearest-neighbor", "reps": 1, "interaction_strength": 1.0},
        "reference_circuit": "not available in repository; exact NumPy implementation is canonical",
    })
    write_json(paths["config"] / "ENVIRONMENT.json", {"captured_utc": datetime.now(timezone.utc).isoformat(), "git": git_state(), "dependencies": environment()})
    pd.DataFrame([{"MODEL": model, "STATUS": "not_available", "REASON": "No independent Qiskit/PennyLane reference implementation exists in the repository; canonical exact NumPy implementation retained."} for model in QUANTUM_MODELS]).to_csv(paths["qc"] / "REFERENCE_IMPLEMENTATION_CHECK.csv", index=False)


def markdown_table(frame: pd.DataFrame, columns: Iterable[str] | None = None, digits: int = 4) -> str:
    selected = frame.loc[:, list(columns)] if columns is not None else frame
    formatted = selected.copy()
    for column in formatted.select_dtypes(include=[np.number]).columns:
        formatted[column] = formatted[column].map(lambda value: f"{value:.{digits}f}" if pd.notna(value) else "NA")
    header = "| " + " | ".join(formatted.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(formatted.columns)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in formatted.itertuples(index=False, name=None)]
    return "\n".join([header, separator, *rows])


def write_summary(root: Path, paths: dict[str, Path], nested_summary: pd.DataFrame, selections: list[dict[str, Any]], holdout_metrics: pd.DataFrame, cr8_metrics: pd.DataFrame, ad: pd.DataFrame, thresholds: dict[str, float], bootstrap: pd.DataFrame, y_summary: pd.DataFrame) -> None:
    selection_frame = pd.DataFrame([{"MODEL": row["model"], "CV_AUROC_MEAN": row["development_cv_mean_auroc"], "CV_AUROC_SD": row["development_cv_sd_auroc"], "THRESHOLD": row["final_threshold"], "PARAMS": json.dumps(row["best_params"], sort_keys=True)} for row in selections])
    limitations = [
        "The 181-molecule test is a historical, previously inspected holdout and is not a pristine confirmatory test.",
        "CR8 is an independent challenge panel but contains only eight molecules (two positives), so its metrics are highly unstable.",
        "Y-randomization uses frozen configurations rather than repeating full nested HPO for every permutation.",
        "The quantum experiments are exact noiseless simulations; they do not demonstrate hardware performance or quantum advantage.",
        "Thresholds maximize development MCC and therefore require independent prospective validation before operational use.",
    ]
    text = f"""# BeeQ final nested structure-aware campaign summary

Campaign: `{root.name}`  
Status: complete  
Seed: `{SEED}`

## 1. Dataset and hashes

All four official SHA-256 hashes matched before modeling. Development contained
712 molecules (490 non-toxic, 222 toxic); the historical holdout contained 181
(132/49), and CR8 contained eight (6/2). Holdout and CR8 contents were first
opened only after the development freeze manifest had been written and verified.

## 2. Frozen X10

The exact ordered features were: {", ".join(f"`{value}`" for value in X10_FEATURES)}.
No feature was added, removed, recalculated, or selected.

## 3. Nested CV protocol and split integrity

Five frozen `STRICT_CV_FOLD` outer folds were used. Within every outer-training
partition, four deterministic `StratifiedGroupKFold` splits grouped by
`BUTINA_CLUSTER_ID` selected hyperparameters by mean AUROC. All outer and inner
cluster intersections were zero. Scalers were fitted only on the corresponding
training rows. Thresholds were selected from inner OOF scores by maximum MCC,
then balanced accuracy, and applied unchanged to outer validation.

## 4. Model and quantum definitions

The primary models were Logistic Regression, Random Forest, MLP, matched RBF,
Product-state fidelity kernel, and IQP-ZZ fidelity kernel. Existing BeeQ
implementations were retained. Both quantum kernels used 10-qubit,
1024-dimensional exact noiseless NumPy statevectors with no shots. IQP-ZZ used
the existing linear nearest-neighbor coupling, not a substituted feature map.

## 5. Primary nested outer results

{markdown_table(nested_summary, ['MODEL','OUTER_AUROC_MEAN','OUTER_AUROC_SD','OUTER_AUPRC_MEAN','OUTER_AUPRC_SD','POOLED_OOF_BALANCED_ACCURACY','POOLED_OOF_MCC'])}

These outer results are the primary performance estimates. Inner AUROC values
are selection diagnostics only.

## 6. Final development-only selections

{markdown_table(selection_frame, ['MODEL','CV_AUROC_MEAN','CV_AUROC_SD','THRESHOLD','PARAMS'])}

These selections are not independent performance estimates. They were frozen
and hashed before downstream evaluation.

## 7. Historical holdout

{markdown_table(holdout_metrics, ['MODEL','AUROC','AUPRC','BALANCED_ACCURACY','MCC','SENSITIVITY','SPECIFICITY','TP','TN','FP','FN'])}

## 8. CR8 independent external challenge

{markdown_table(cr8_metrics, ['MODEL','AUROC','AUPRC','BALANCED_ACCURACY','MCC','SENSITIVITY','SPECIFICITY','TP','TN','FP','FN'])}

CR8 was never used for model, parameter, threshold, feature, or architecture
selection.

## 9. Dual applicability domain and Tanimoto analysis

Development-only thresholds were Morgan P05 LOO Smax =
`{thresholds['structural_P05_LOO_Smax']:.6f}` and standardized-X10 P95 LOO mean
5-NN distance = `{thresholds['descriptor_P95_LOO_mean_5NN']:.6f}`.

{markdown_table(ad, ['name','LABEL','Smax_Morgan','d5NN_X10','DUAL_AD'])}

Top-10 Morgan neighbors and local toxic fractions are stored molecule by
molecule. Ethiprole and Isocycloseram were interpreted after freeze and did not
trigger retuning.

## 10. Paired cluster bootstrap

{markdown_table(bootstrap, ['LEFT_MODEL','RIGHT_MODEL','METRIC','OBSERVED_DELTA','BOOTSTRAP_MEDIAN','CI_LOW_95','CI_HIGH_95','P_DELTA_GT_0'])}

Intervals are descriptive paired cluster-bootstrap results; no automatic
significance claim is made.

## 11. Y-randomization

{markdown_table(y_summary, ['MODEL','REAL_NESTED_OOF_AUROC','MEAN_RANDOMIZED_AUROC','SD_RANDOMIZED_AUROC','P95_RANDOMIZED_AUROC','EMPIRICAL_FRACTION_RANDOMIZED_GE_REAL'])}

This was explicitly a fixed-configuration Y-randomization with 200 label
permutations on development only.

## 12. Quantum kernel QC

Every recorded selected quantum training matrix met symmetry error `< 1e-10`,
diagonal error `< 1e-10`, and minimum eigenvalue `>= -1e-8`. The repository had
no independent Qiskit/PennyLane reference circuit; the exact NumPy maps are the
canonical prior implementations.

## 13. Limitations

{''.join(f'- {item}\n' for item in limitations)}
## 14. Artifacts and reproducibility

Configuration, input audits, fold-level selections, molecule-level predictions,
statistics, QC, figures, environment versions, and final SHA-256 hashes are
contained in the numbered campaign directories. `10_MANIFEST` is the integrity
entry point.
"""
    (root / "BEEQ_FINAL_CAMPAIGN_SUMMARY.md").write_text(text, encoding="utf-8")
    (paths["readme"] / "README.md").write_text(
        "# BeeQ final campaign\n\nSee `../BEEQ_FINAL_CAMPAIGN_SUMMARY.md` for the scientific summary and `../10_MANIFEST/ARTIFACT_MANIFEST_SHA256.csv` for artifact integrity.\n",
        encoding="utf-8",
    )


def final_manifest(root: Path, manifest_dir: Path) -> pd.DataFrame:
    manifest_path = manifest_dir / "ARTIFACT_MANIFEST_SHA256.csv"
    status_path = manifest_dir / "CAMPAIGN_STATUS.json"
    files = [path for path in root.rglob("*") if path.is_file() and path not in {manifest_path, status_path}]
    frame = pd.DataFrame([{"relative_path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in sorted(files)])
    frame.to_csv(manifest_path, index=False)
    for row in frame.itertuples(index=False):
        if sha256_file(root / row.relative_path) != row.sha256:
            raise RuntimeError(f"Final manifest verification failed: {row.relative_path}")
    write_json(status_path, {"status": "complete", "completed_utc": datetime.now(timezone.utc).isoformat(), "artifact_count_excluding_manifest_and_status": len(frame), "manifest_sha256": sha256_file(manifest_path)})
    return frame


def verify_existing_freeze(root: Path, final_dir: Path) -> None:
    freeze_path = final_dir / "DEVELOPMENT_FREEZE_MANIFEST.json"
    if not freeze_path.is_file():
        raise FileNotFoundError("Cannot finalize without a development freeze manifest")
    payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    if payload.get("status") != "development_frozen":
        raise RuntimeError("Development freeze status is invalid")
    for relative, expected in payload["artifact_hashes"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"Frozen artifact changed before finalization: {relative}")


def resume_finalization(root: Path, data_dir: Path, paths: dict[str, Path]) -> None:
    verify_existing_freeze(root, paths["final"])
    train = pd.read_csv(data_dir / "train_RDKitFixed.csv")
    external = pd.read_csv(data_dir / "ExternalFinal_RDKitFixed.csv")
    nested_metrics = pd.read_csv(paths["nested"] / "NESTED_FOLD_METRICS.csv")
    nested_summary = pd.read_csv(paths["nested"] / "NESTED_SUMMARY.csv")
    oof = pd.read_csv(paths["nested"] / "NESTED_OUTER_OOF_PREDICTIONS.csv")
    selections = json.loads((paths["final"] / "FINAL_MODEL_SELECTIONS.json").read_text(encoding="utf-8"))["models"]
    holdout_metrics = pd.read_csv(paths["holdout"] / "HOLDOUT_METRICS.csv")
    cr8_metrics = pd.read_csv(paths["external"] / "CR8_METRICS.csv")
    cr8_predictions = pd.read_csv(paths["external"] / "CR8_PREDICTIONS.csv")
    ad = pd.read_csv(paths["external"] / "CR8_DUAL_AD.csv")
    neighbors = pd.read_csv(paths["external"] / "CR8_TOP10_TANIMOTO_NEIGHBORS.csv")
    thresholds = json.loads((paths["external"] / "AD_THRESHOLDS.json").read_text(encoding="utf-8"))
    bootstrap = pd.read_csv(paths["statistics"] / "PAIRED_CLUSTER_BOOTSTRAP.csv")
    y_summary = pd.read_csv(paths["statistics"] / "Y_RANDOMIZATION_RESULTS.csv")
    y_raw = pd.read_csv(paths["statistics"] / "Y_RANDOMIZATION_RAW.csv")
    generate_figures(nested_metrics, oof, y_raw, ad, cr8_predictions, neighbors, external, train, paths["figures"])
    write_summary(root, paths, nested_summary, selections, holdout_metrics, cr8_metrics, ad, thresholds, bootstrap, y_summary)
    manifest = final_manifest(root, paths["manifest"])
    print(f"Campaign complete after verified finalization resume: {root}", flush=True)
    print(f"Artifacts hashed: {len(manifest)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--campaign-dir", type=Path, default=DEFAULT_CAMPAIGN_DIR)
    parser.add_argument("--resume-finalization", action="store_true")
    parser.add_argument("--rebuild-manifest-only", action="store_true")
    args = parser.parse_args()
    root = args.campaign_dir.resolve()
    data_dir = args.data_dir.resolve()
    paths = prepare_directories(
        root,
        allow_completed=args.rebuild_manifest_only or args.resume_finalization,
    )
    if args.rebuild_manifest_only:
        verify_existing_freeze(root, paths["final"])
        manifest = final_manifest(root, paths["manifest"])
        print(f"Manifest rebuilt and verified: {len(manifest)} artifacts", flush=True)
        return
    if args.resume_finalization:
        resume_finalization(root, data_dir, paths)
        return

    print("Phase A: opaque hash verification and development audit", flush=True)
    input_hashes = verify_input_hashes(data_dir, paths["audit"] / "INPUT_HASHES.csv")
    write_initial_config(paths, input_hashes)
    train = validate_development(data_dir / "train_RDKitFixed.csv", paths["audit"])

    print("Phase B: primary nested outer evaluation", flush=True)
    nested_metrics, nested_summary, oof, _ = run_nested(train, paths["nested"], paths["qc"])

    print("Phase C: development-only final selection and freeze", flush=True)
    frozen, selections = final_selection(train, paths["final"], paths["qc"])
    create_freeze(root, paths)

    print("Phase D: post-freeze historical holdout evaluation", flush=True)
    if sha256_file(data_dir / "test_RDKitFixed.csv") != EXPECTED_HASHES["test_RDKitFixed.csv"]:
        raise RuntimeError("Post-freeze holdout hash mismatch")
    holdout = pd.read_csv(data_dir / "test_RDKitFixed.csv")
    validate_postfreeze_frame(holdout, expected_rows=181, expected_labels={0: 132, 1: 49}, source="historical holdout")
    holdout_predictions, holdout_metrics = score_frozen(frozen, holdout, "historical_holdout")
    holdout_predictions.to_csv(paths["holdout"] / "HOLDOUT_PREDICTIONS.csv", index=False)
    holdout_metrics.to_csv(paths["holdout"] / "HOLDOUT_METRICS.csv", index=False)

    print("Phase D: post-freeze CR8 evaluation and applicability domain", flush=True)
    if sha256_file(data_dir / "ExternalFinal_RDKitFixed.csv") != EXPECTED_HASHES["ExternalFinal_RDKitFixed.csv"]:
        raise RuntimeError("Post-freeze CR8 hash mismatch")
    external = pd.read_csv(data_dir / "ExternalFinal_RDKitFixed.csv")
    validate_postfreeze_frame(external, expected_rows=8, expected_labels={0: 6, 1: 2}, source="CR8")
    cr8_predictions, cr8_metrics = score_frozen(frozen, external, "CR8")
    cr8_predictions.to_csv(paths["external"] / "CR8_PREDICTIONS.csv", index=False)
    cr8_metrics.to_csv(paths["external"] / "CR8_METRICS.csv", index=False)
    ad, neighbors, thresholds = applicability_and_neighbors(train, external, paths["external"])

    print("Phase E: paired cluster bootstrap", flush=True)
    bootstrap = paired_cluster_bootstrap(oof, paths["statistics"] / "PAIRED_CLUSTER_BOOTSTRAP.csv")
    print("Phase E: fixed-configuration Y-randomization", flush=True)
    y_summary, y_raw = y_randomization(train, selections, oof, paths["statistics"] / "Y_RANDOMIZATION_RESULTS.csv")
    print("Phase E: figures, summary, and integrity manifest", flush=True)
    generate_figures(nested_metrics, oof, y_raw, ad, cr8_predictions, neighbors, external, train, paths["figures"])
    write_summary(root, paths, nested_summary, selections, holdout_metrics, cr8_metrics, ad, thresholds, bootstrap, y_summary)
    manifest = final_manifest(root, paths["manifest"])
    print(f"Campaign complete: {root}", flush=True)
    print(f"Artifacts hashed: {len(manifest)}", flush=True)


if __name__ == "__main__":
    main()
