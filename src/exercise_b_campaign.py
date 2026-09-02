"""Exercise B: leakage-safe pairwise IQP-ZZ screening and path construction."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .config import OUTER_FOLDS, PROJECT_ROOT, X10_FEATURES
from .exercise_a_campaign import (
    BASELINE_CAMPAIGN,
    BOOTSTRAP_REPLICATES,
    C_VALUES,
    COMPLEMENTARY,
    DUPLICATE,
    FEATURE_SCALES,
    SEED,
    atomic_json,
    classification_metrics,
    encode_features,
    exact_chain_fidelity_kernel,
    process_rss_bytes,
    select_threshold,
    sha256_canonical_lf,
    sha256_file,
    utc_now,
    write_json,
)
from .kernels import rbf_kernel


INNER_FOLDS = 4
RBF_GAMMAS = (0.01, 0.03, 0.1, 0.3)
PAIR_ARMS = ("pair_phase_no_zz", "pair_iqp_zz", "pair_rbf_control")
CURRENT_ORDER = tuple(range(10))
EXPECTED_TRAIN_SHA256_LF = "06a0817c082d7715211ca62aae367079f192e1a6c6663c2005c8c8eb5c758984"
EXPECTED_CR8_SHA256_LF = "70a01eedd970991e072eb9db8e2acdbe854dc8d4623b42bb2263318486cd41fb"
TRAIN_PATH = PROJECT_ROOT / "data" / "official" / "train_RDKitFixed.csv"
CR8_PATH = PROJECT_ROOT / "data" / "official" / "ExternalFinal_RDKitFixed.csv"
FULL_10Q_MODELS = (
    "current_order_10q",
    "max_synergy_path_10q",
    "stable_synergy_path_10q",
)
FULL_20Q_MODELS = (
    "current_order_20q_duplicate",
    "current_order_20q_complementary",
    "max_synergy_path_20q_duplicate",
    "max_synergy_path_20q_complementary",
    "stable_synergy_path_20q_duplicate",
    "stable_synergy_path_20q_complementary",
)
FULL_MODELS = FULL_10Q_MODELS + FULL_20Q_MODELS
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".txt", ".svg", ".ndjson"}


def all_pairs() -> list[tuple[int, int]]:
    return list(itertools.combinations(range(len(X10_FEATURES)), 2))


def canonical_path(path: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    direct = tuple(path)
    reverse = direct[::-1]
    direct_names = tuple(X10_FEATURES[index] for index in direct)
    reverse_names = tuple(X10_FEATURES[index] for index in reverse)
    return direct if direct_names <= reverse_names else reverse


def path_edges(path: tuple[int, ...] | list[int]) -> list[tuple[int, int]]:
    return [tuple(sorted((left, right))) for left, right in zip(path[:-1], path[1:])]


def path_statistics(path: tuple[int, ...], weights: np.ndarray) -> tuple[float, float, float]:
    values = np.asarray([weights[left, right] for left, right in zip(path[:-1], path[1:])])
    return float(values.sum()), float(values.min()), float(values.std(ddof=0))


def _path_sort_key(path: tuple[int, ...], weights: np.ndarray) -> tuple[Any, ...]:
    total, minimum, deviation = path_statistics(path, weights)
    names = tuple(X10_FEATURES[index] for index in canonical_path(path))
    return (-total, -minimum, deviation, names)


def held_karp_paths(weights: np.ndarray, top_k: int = 2) -> list[tuple[int, ...]]:
    """Return deterministic top Hamiltonian paths without enumerating n! circuits."""

    matrix = np.asarray(weights, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("weights must be square")
    if not np.allclose(matrix, matrix.T, atol=1e-12):
        raise ValueError("weights must be symmetric")
    n = len(matrix)
    if n < 2:
        return [(0,)]
    dp: dict[tuple[int, int], list[tuple[int, ...]]] = {
        (1 << node, node): [(node,)] for node in range(n)
    }
    for size in range(2, n + 1):
        for subset in itertools.combinations(range(n), size):
            mask = sum(1 << node for node in subset)
            for end in subset:
                candidates: dict[tuple[int, ...], tuple[int, ...]] = {}
                previous_mask = mask ^ (1 << end)
                for previous in subset:
                    if previous == end:
                        continue
                    for path in dp.get((previous_mask, previous), []):
                        candidate = path + (end,)
                        candidates[canonical_path(candidate)] = candidate
                ranked = sorted(candidates.values(), key=lambda item: _path_sort_key(item, matrix))
                dp[(mask, end)] = ranked[:top_k]
    complete: dict[tuple[int, ...], tuple[int, ...]] = {}
    full_mask = (1 << n) - 1
    for end in range(n):
        for path in dp[(full_mask, end)]:
            complete[canonical_path(path)] = canonical_path(path)
    return sorted(complete.values(), key=lambda item: _path_sort_key(item, matrix))[:top_k]


def validate_pair_enumeration() -> pd.DataFrame:
    pairs = all_pairs()
    if len(pairs) != 45 or len(set(pairs)) != 45:
        raise RuntimeError("Expected exactly 45 unique unordered pairs")
    counts = {index: 0 for index in range(10)}
    for left, right in pairs:
        if not left < right:
            raise RuntimeError("Pairs must be canonical i<j")
        counts[left] += 1
        counts[right] += 1
    if set(counts.values()) != {9}:
        raise RuntimeError("Each X10 variable must occur in nine pairs")
    return pd.DataFrame(
        [
            {
                "PAIR_INDEX": index,
                "LEFT_INDEX": left,
                "RIGHT_INDEX": right,
                "LEFT_FEATURE": X10_FEATURES[left],
                "RIGHT_FEATURE": X10_FEATURES[right],
                "CANONICAL_PAIR": f"{X10_FEATURES[left]}__{X10_FEATURES[right]}",
            }
            for index, (left, right) in enumerate(pairs, start=1)
        ]
    )


def git_snapshot() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "status_short_branch": run("status", "--short", "--branch").splitlines(),
    }


def build_b_manifest(root: Path) -> pd.DataFrame:
    manifest_dir = root / "11_MANIFEST"
    manifest_path = manifest_dir / "ARTIFACT_MANIFEST_SHA256.csv"
    status_path = manifest_dir / "CAMPAIGN_STATUS.json"
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path not in {manifest_path, status_path}
    ]
    rows = []
    for path in sorted(files):
        canonical = sha256_canonical_lf(path) if path.suffix.lower() in TEXT_SUFFIXES else None
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256_physical": sha256_file(path),
                "sha256_canonical_lf": canonical,
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(manifest_path, index=False)
    for row in frame.itertuples(index=False):
        if sha256_file(root / row.relative_path) != row.sha256_physical:
            raise RuntimeError(f"Manifest verification failure: {row.relative_path}")
    write_json(
        status_path,
        {
            "status": "complete",
            "exercise": "B",
            "completed_utc": utc_now(),
            "artifact_count_excluding_manifest_and_status": len(frame),
            "manifest_sha256_physical": sha256_file(manifest_path),
        },
    )
    return frame


def frozen_outer_indices(train: pd.DataFrame, fold: int) -> tuple[np.ndarray, np.ndarray]:
    folds = train.STRICT_CV_FOLD.astype(int).to_numpy()
    return np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)


def inner_splits(
    labels: np.ndarray, groups: np.ndarray, outer_fold: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    splitter = StratifiedGroupKFold(
        n_splits=INNER_FOLDS, shuffle=True, random_state=SEED + outer_fold
    )
    splits = list(splitter.split(np.zeros((len(labels), 1)), labels, groups))
    for train_idx, validation_idx in splits:
        if set(groups[train_idx]) & set(groups[validation_idx]):
            raise RuntimeError(f"Inner cluster leakage in outer fold {outer_fold}")
    return splits


def frozen_five_splits(train: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    return [frozen_outer_indices(train, fold) for fold in OUTER_FOLDS]


def kernel_candidates(kind: str) -> list[dict[str, float]]:
    if kind == "rbf":
        return [{"gamma": gamma} for gamma in RBF_GAMMAS]
    return [{"feature_scale": scale} for scale in FEATURE_SCALES]


def build_kernel(
    train_scaled: np.ndarray,
    validation_scaled: np.ndarray | None,
    *,
    kind: str,
    params: dict[str, float],
    order: tuple[int, ...] | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    if kind == "rbf":
        gamma = params["gamma"]
        train_kernel = rbf_kernel(train_scaled, gamma=gamma)
        validation_kernel = (
            None
            if validation_scaled is None
            else rbf_kernel(validation_scaled, train_scaled, gamma=gamma)
        )
        return train_kernel, validation_kernel
    train_values = train_scaled
    validation_values = validation_scaled
    if order is not None:
        train_values = train_values[:, order]
        validation_values = None if validation_values is None else validation_values[:, order]
    scale = params["feature_scale"]
    interaction = 0.0 if kind in {"singleton", "pair_no_zz"} else 1.0
    if kind == "full20_duplicate":
        train_values = encode_features(train_values, DUPLICATE)
        validation_values = (
            None if validation_values is None else encode_features(validation_values, DUPLICATE)
        )
    elif kind == "full20_complementary":
        train_values = encode_features(train_values, COMPLEMENTARY)
        validation_values = (
            None
            if validation_values is None
            else encode_features(validation_values, COMPLEMENTARY)
        )
    train_encoded = scale * train_values
    train_kernel = exact_chain_fidelity_kernel(
        train_encoded, interaction_strength=interaction
    )
    validation_kernel = None
    if validation_values is not None:
        validation_kernel = exact_chain_fidelity_kernel(
            scale * validation_values,
            train_encoded,
            interaction_strength=interaction,
        )
    return train_kernel, validation_kernel


def qc_kernel(
    kernel: np.ndarray,
    *,
    model: str,
    stage: str,
    fold: Any,
    params: dict[str, Any],
    compute_eigenvalue: bool,
) -> dict[str, Any]:
    matrix = np.asarray(kernel, dtype=float)
    symmetry = float(np.max(np.abs(matrix - matrix.T)))
    diagonal = float(np.max(np.abs(np.diag(matrix) - 1.0)))
    minimum = (
        float(np.linalg.eigvalsh((matrix + matrix.T) / 2.0).min())
        if compute_eigenvalue
        else None
    )
    passed = symmetry < 1e-10 and diagonal < 1e-10 and (
        minimum is None or minimum >= -1e-8
    )
    if not passed:
        raise RuntimeError(f"Kernel QC failure: {model}, {stage}, {fold}")
    return {
        "MODEL": model,
        "STAGE": stage,
        "FOLD": fold,
        "PARAMS": json.dumps(params, sort_keys=True),
        "N": len(matrix),
        "SYMMETRY_ERROR": symmetry,
        "DIAGONAL_ERROR": diagonal,
        "MIN_EIGENVALUE": minimum,
        "PSD_VERIFICATION": "numeric" if minimum is not None else "fidelity_gram_by_construction",
        "PASS": passed,
    }


def metric_from_predictions(truth: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    return classification_metrics(truth, scores, threshold)


def select_kernel_cv(
    raw_features: np.ndarray,
    labels: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
    *,
    kind: str,
    model_name: str,
    fold_label: Any,
    order: tuple[int, ...] | None = None,
    qc_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidates = kernel_candidates(kind)
    hpo = {
        (candidate_index, c): []
        for candidate_index in range(len(candidates))
        for c in C_VALUES
    }
    for split_index, (train_idx, validation_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(raw_features[train_idx])
        train_scaled = scaler.transform(raw_features[train_idx])
        validation_scaled = scaler.transform(raw_features[validation_idx])
        for candidate_index, params in enumerate(candidates):
            train_kernel, validation_kernel = build_kernel(
                train_scaled,
                validation_scaled,
                kind=kind,
                params=params,
                order=order,
            )
            if qc_rows is not None and kind != "rbf" and candidate_index == 0:
                qc_rows.append(
                    qc_kernel(
                        train_kernel,
                        model=model_name,
                        stage="hpo_representative",
                        fold=f"{fold_label}.{split_index}",
                        params=params,
                        compute_eigenvalue=False,
                    )
                )
            assert validation_kernel is not None
            for c in C_VALUES:
                classifier = SVC(
                    C=c,
                    kernel="precomputed",
                    class_weight="balanced",
                    random_state=SEED,
                )
                classifier.fit(train_kernel, labels[train_idx])
                score = classifier.decision_function(validation_kernel)
                hpo[(candidate_index, c)].append(
                    float(roc_auc_score(labels[validation_idx], score))
                )
    ranked = sorted(
        (
            (float(np.mean(scores)), float(np.std(scores, ddof=1)), candidate_index, c)
            for (candidate_index, c), scores in hpo.items()
        ),
        key=lambda row: (-row[0], row[2], row[3]),
    )
    mean_auroc, sd_auroc, candidate_index, c = ranked[0]
    params = candidates[candidate_index]
    oof = np.full(len(labels), np.nan)
    for split_index, (train_idx, validation_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(raw_features[train_idx])
        train_kernel, validation_kernel = build_kernel(
            scaler.transform(raw_features[train_idx]),
            scaler.transform(raw_features[validation_idx]),
            kind=kind,
            params=params,
            order=order,
        )
        assert validation_kernel is not None
        classifier = SVC(
            C=c,
            kernel="precomputed",
            class_weight="balanced",
            random_state=SEED,
        )
        classifier.fit(train_kernel, labels[train_idx])
        oof[validation_idx] = classifier.decision_function(validation_kernel)
    if not np.isfinite(oof).all():
        raise RuntimeError(f"Missing inner OOF scores for {model_name}")
    threshold, threshold_metrics = select_threshold(labels, oof)
    fold_metrics = [
        metric_from_predictions(labels[validation_idx], oof[validation_idx], threshold)
        for _, validation_idx in splits
    ]
    return {
        "model": model_name,
        "kind": kind,
        "C": c,
        "kernel_params": params,
        "inner_auroc_mean": mean_auroc,
        "inner_auroc_sd": sd_auroc,
        "threshold": threshold,
        "threshold_metrics": threshold_metrics,
        "oof_scores": oof.tolist(),
        "fold_metrics": fold_metrics,
    }


def fit_outer(
    raw_train: np.ndarray,
    y_train: np.ndarray,
    raw_validation: np.ndarray,
    y_validation: np.ndarray,
    selection: dict[str, Any],
    *,
    order: tuple[int, ...] | None = None,
    qc_rows: list[dict[str, Any]] | None = None,
    qc_fold: Any = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    scaler = StandardScaler().fit(raw_train)
    train_kernel, validation_kernel = build_kernel(
        scaler.transform(raw_train),
        scaler.transform(raw_validation),
        kind=selection["kind"],
        params=selection["kernel_params"],
        order=order,
    )
    if qc_rows is not None and selection["kind"] != "rbf":
        qc_rows.append(
            qc_kernel(
                train_kernel,
                model=selection["model"],
                stage="outer_fit",
                fold=qc_fold,
                params={"C": selection["C"], **selection["kernel_params"]},
                compute_eigenvalue=selection["model"] in FULL_MODELS,
            )
        )
    assert validation_kernel is not None
    classifier = SVC(
        C=selection["C"],
        kernel="precomputed",
        class_weight="balanced",
        random_state=SEED,
    )
    classifier.fit(train_kernel, y_train)
    scores = classifier.decision_function(validation_kernel)
    return scores, metric_from_predictions(
        y_validation, scores, float(selection["threshold"])
    )


def prediction_rows(
    frame: pd.DataFrame,
    *,
    model: str,
    outer_fold: Any,
    scores: np.ndarray,
    threshold: float,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for source, score in zip(frame.itertuples(index=False), scores):
        row = {
            "ID": int(source.ID),
            "name": str(source.name),
            "BUTINA_CLUSTER_ID": (
                int(source.BUTINA_CLUSTER_ID) if pd.notna(source.BUTINA_CLUSTER_ID) else None
            ),
            "MODEL": model,
            "OUTER_FOLD": outer_fold,
            "LABEL": int(source.LABEL),
            "SCORE": float(score),
            "THRESHOLD": float(threshold),
            "MARGIN": float(score - threshold),
            "PRED": int(score >= threshold),
        }
        if extra:
            row.update(extra)
        rows.append(row)
    return rows


def screen_outer_fold(train: pd.DataFrame, outer_fold: int) -> dict[str, Any]:
    started = time.perf_counter()
    outer_train_idx, outer_validation_idx = frozen_outer_indices(train, outer_fold)
    train_frame = train.iloc[outer_train_idx]
    validation_frame = train.iloc[outer_validation_idx]
    x_all = train.loc[:, X10_FEATURES].to_numpy(float)
    y_all = train.LABEL.to_numpy(int)
    x_train = x_all[outer_train_idx]
    y_train = y_all[outer_train_idx]
    x_validation = x_all[outer_validation_idx]
    y_validation = y_all[outer_validation_idx]
    groups = train_frame.BUTINA_CLUSTER_ID.to_numpy()
    splits = inner_splits(y_train, groups, outer_fold)
    qc_rows: list[dict[str, Any]] = []
    singleton_rows = []
    singleton_mcc: dict[int, float] = {}
    singleton_selections: dict[int, dict[str, Any]] = {}
    for feature_index, feature_name in enumerate(X10_FEATURES):
        selection = select_kernel_cv(
            x_train[:, [feature_index]],
            y_train,
            splits,
            kind="singleton",
            model_name=f"singleton__{feature_name}",
            fold_label=outer_fold,
            qc_rows=qc_rows,
        )
        scores, outer_metrics = fit_outer(
            x_train[:, [feature_index]],
            y_train,
            x_validation[:, [feature_index]],
            y_validation,
            selection,
        )
        inner_metrics = selection["threshold_metrics"]
        singleton_mcc[feature_index] = float(inner_metrics["mcc"])
        singleton_selections[feature_index] = selection
        singleton_rows.append(
            {
                "OUTER_FOLD": outer_fold,
                "FEATURE_INDEX": feature_index,
                "FEATURE": feature_name,
                "INNER_MCC": inner_metrics["mcc"],
                "INNER_AUROC": inner_metrics["auroc"],
                "INNER_AUPRC": inner_metrics["auprc"],
                "INNER_BALANCED_ACCURACY": inner_metrics["balanced_accuracy"],
                "OUTER_MCC": outer_metrics["mcc"],
                "OUTER_AUROC": outer_metrics["auroc"],
                "OUTER_AUPRC": outer_metrics["auprc"],
                "C": selection["C"],
                "FEATURE_SCALE": selection["kernel_params"]["feature_scale"],
                "THRESHOLD": selection["threshold"],
                "SELECTION_SOURCE": "inner_OOF_outer_train_only",
            }
        )

    pair_inner_rows = []
    pair_outer_rows = []
    pair_prediction_rows = []
    edge_detail_rows = []
    for pair_number, (left, right) in enumerate(all_pairs(), start=1):
        if pair_number == 1 or pair_number % 5 == 0:
            print(f"Outer {outer_fold}: pair {pair_number}/45", flush=True)
        pair_name = f"{X10_FEATURES[left]}__{X10_FEATURES[right]}"
        raw_train_pair = x_train[:, [left, right]]
        raw_validation_pair = x_validation[:, [left, right]]
        selections: dict[str, dict[str, Any]] = {}
        arm_scores: dict[str, np.ndarray] = {}
        arm_outer_metrics: dict[str, dict[str, Any]] = {}
        for arm in PAIR_ARMS:
            kind = {
                "pair_phase_no_zz": "pair_no_zz",
                "pair_iqp_zz": "pair_zz",
                "pair_rbf_control": "rbf",
            }[arm]
            model_name = f"{arm}__{pair_name}"
            selection = select_kernel_cv(
                raw_train_pair,
                y_train,
                splits,
                kind=kind,
                model_name=model_name,
                fold_label=outer_fold,
                qc_rows=qc_rows if arm != "pair_rbf_control" else None,
            )
            outer_scores, outer_metrics = fit_outer(
                raw_train_pair,
                y_train,
                raw_validation_pair,
                y_validation,
                selection,
                qc_rows=qc_rows if arm == "pair_iqp_zz" and pair_number == 1 else None,
                qc_fold=outer_fold,
            )
            selections[arm] = selection
            arm_scores[arm] = outer_scores
            arm_outer_metrics[arm] = outer_metrics
            pair_outer_rows.append(
                {
                    "OUTER_FOLD": outer_fold,
                    "PAIR_INDEX": pair_number,
                    "PAIR": pair_name,
                    "LEFT_FEATURE": X10_FEATURES[left],
                    "RIGHT_FEATURE": X10_FEATURES[right],
                    "ARM": arm,
                    "C": selection["C"],
                    "KERNEL_PARAMS": json.dumps(selection["kernel_params"], sort_keys=True),
                    "THRESHOLD": selection["threshold"],
                    **{key.upper(): value for key, value in outer_metrics.items()},
                    "EXPLORATORY_OUTER_RESULT": True,
                    "USED_FOR_PATH_SELECTION": False,
                }
            )
            pair_prediction_rows.extend(
                prediction_rows(
                    validation_frame,
                    model=arm,
                    outer_fold=outer_fold,
                    scores=outer_scores,
                    threshold=selection["threshold"],
                    extra={
                        "PAIR_INDEX": pair_number,
                        "PAIR": pair_name,
                        "LEFT_FEATURE": X10_FEATURES[left],
                        "RIGHT_FEATURE": X10_FEATURES[right],
                    },
                )
            )
        zz = selections["pair_iqp_zz"]
        nozz = selections["pair_phase_no_zz"]
        zz_metrics = zz["threshold_metrics"]
        nozz_metrics = nozz["threshold_metrics"]
        fold_deltas = np.asarray(
            [
                zz_fold["mcc"] - nozz_fold["mcc"]
                for zz_fold, nozz_fold in zip(zz["fold_metrics"], nozz["fold_metrics"])
            ]
        )
        delta = float(zz_metrics["mcc"] - nozz_metrics["mcc"])
        stable_score = float(fold_deltas.mean() - 0.5 * fold_deltas.std(ddof=1))
        pair_inner_rows.append(
            {
                "OUTER_FOLD": outer_fold,
                "PAIR_INDEX": pair_number,
                "PAIR": pair_name,
                "LEFT_INDEX": left,
                "RIGHT_INDEX": right,
                "LEFT_FEATURE": X10_FEATURES[left],
                "RIGHT_FEATURE": X10_FEATURES[right],
                "PAIR_MCC_ZZ": zz_metrics["mcc"],
                "PAIR_MCC_NO_ZZ": nozz_metrics["mcc"],
                "DELTA_MCC_ZZ_VS_NO_ZZ": delta,
                "DELTA_MCC_ZZ_VS_BEST_SINGLETON": zz_metrics["mcc"]
                - max(singleton_mcc[left], singleton_mcc[right]),
                "PAIR_AUROC_ZZ": zz_metrics["auroc"],
                "PAIR_AUPRC_ZZ": zz_metrics["auprc"],
                "BALANCED_ACCURACY": zz_metrics["balanced_accuracy"],
                "SENSITIVITY": zz_metrics["sensitivity"],
                "SPECIFICITY": zz_metrics["specificity"],
                "INNER_FOLD_DELTA_MEAN": fold_deltas.mean(),
                "INNER_FOLD_DELTA_SD": fold_deltas.std(ddof=1),
                "INNER_FOLD_POSITIVE_DELTA_COUNT": int((fold_deltas > 0).sum()),
                "INNER_FOLD_DELTAS": json.dumps(fold_deltas.tolist()),
                "STABLE_EDGE_SCORE": stable_score,
                "ZZ_C": zz["C"],
                "ZZ_PARAMS": json.dumps(zz["kernel_params"], sort_keys=True),
                "ZZ_THRESHOLD": zz["threshold"],
                "NO_ZZ_C": nozz["C"],
                "NO_ZZ_PARAMS": json.dumps(nozz["kernel_params"], sort_keys=True),
                "NO_ZZ_THRESHOLD": nozz["threshold"],
                "EDGE_SCORE_SOURCE": "inner_OOF_outer_train_only",
                "OUTER_VALIDATION_LABELS_ACCESSED": False,
            }
        )
        edge_detail_rows.extend(
            [
                {
                    "OUTER_FOLD": outer_fold,
                    "PAIR": pair_name,
                    "SCORE_TYPE": "max_synergy",
                    "EDGE_SCORE": delta,
                },
                {
                    "OUTER_FOLD": outer_fold,
                    "PAIR": pair_name,
                    "SCORE_TYPE": "stable_synergy",
                    "EDGE_SCORE": stable_score,
                },
            ]
        )

    pair_inner = pd.DataFrame(pair_inner_rows)
    synergy = np.zeros((10, 10), dtype=float)
    stable = np.zeros((10, 10), dtype=float)
    predictive = np.zeros((10, 10), dtype=float)
    for row in pair_inner.itertuples(index=False):
        synergy[row.LEFT_INDEX, row.RIGHT_INDEX] = synergy[row.RIGHT_INDEX, row.LEFT_INDEX] = row.DELTA_MCC_ZZ_VS_NO_ZZ
        stable[row.LEFT_INDEX, row.RIGHT_INDEX] = stable[row.RIGHT_INDEX, row.LEFT_INDEX] = row.STABLE_EDGE_SCORE
        predictive[row.LEFT_INDEX, row.RIGHT_INDEX] = predictive[row.RIGHT_INDEX, row.LEFT_INDEX] = row.PAIR_MCC_ZZ
    max_paths = held_karp_paths(synergy, top_k=2)
    stable_paths = held_karp_paths(stable, top_k=2)
    max_path = max_paths[0]
    stable_path = stable_paths[0]
    stable_used_second = False
    if canonical_path(stable_path) == canonical_path(max_path):
        if len(stable_paths) < 2:
            raise RuntimeError("Stable path equals max path and no deterministic second path exists")
        stable_path = stable_paths[1]
        stable_used_second = True
    path_map = {
        "current_order": CURRENT_ORDER,
        "max_synergy_path": canonical_path(max_path),
        "stable_synergy_path": canonical_path(stable_path),
    }
    path_rows = []
    path_edge_rows = []
    matrix_hashes = {
        "max_synergy": hashlib.sha256(synergy.tobytes()).hexdigest(),
        "stable_synergy": hashlib.sha256(stable.tobytes()).hexdigest(),
    }
    for path_type, path in path_map.items():
        weight_matrix = stable if path_type == "stable_synergy_path" else synergy
        total, minimum, deviation = path_statistics(path, weight_matrix)
        path_rows.append(
            {
                "OUTER_FOLD": outer_fold,
                "PATH_TYPE": path_type,
                "ORDER_INDICES": json.dumps(path),
                "ORDER_FEATURES": json.dumps([X10_FEATURES[index] for index in path]),
                "CANONICAL_REVERSE": json.dumps([X10_FEATURES[index] for index in path[::-1]]),
                "TOTAL_SCORE": total,
                "MIN_EDGE_SCORE": minimum,
                "EDGE_SCORE_SD": deviation,
                "MATRIX_SHA256": matrix_hashes[
                    "stable_synergy" if path_type == "stable_synergy_path" else "max_synergy"
                ],
                "CONSTRUCTION_DATA": f"outer_{outer_fold}_train_inner_OOF_only",
                "STABLE_SECOND_BEST_USED": stable_used_second if path_type == "stable_synergy_path" else False,
            }
        )
        for position, (left, right) in enumerate(zip(path[:-1], path[1:]), start=1):
            path_edge_rows.append(
                {
                    "OUTER_FOLD": outer_fold,
                    "PATH_TYPE": path_type,
                    "EDGE_POSITION": position,
                    "LEFT_FEATURE": X10_FEATURES[left],
                    "RIGHT_FEATURE": X10_FEATURES[right],
                    "EDGE_SCORE": weight_matrix[left, right],
                }
            )

    full_metric_rows = []
    full_prediction_rows = []
    full_parameter_rows = []
    full_specs = [
        ("current_order_10q", "full10", path_map["current_order"]),
        ("max_synergy_path_10q", "full10", path_map["max_synergy_path"]),
        ("stable_synergy_path_10q", "full10", path_map["stable_synergy_path"]),
        ("current_order_20q_duplicate", "full20_duplicate", path_map["current_order"]),
        ("current_order_20q_complementary", "full20_complementary", path_map["current_order"]),
        ("max_synergy_path_20q_duplicate", "full20_duplicate", path_map["max_synergy_path"]),
        ("max_synergy_path_20q_complementary", "full20_complementary", path_map["max_synergy_path"]),
        ("stable_synergy_path_20q_duplicate", "full20_duplicate", path_map["stable_synergy_path"]),
        ("stable_synergy_path_20q_complementary", "full20_complementary", path_map["stable_synergy_path"]),
    ]
    for model_name, kind, order in full_specs:
        print(f"Outer {outer_fold}: full model {model_name}", flush=True)
        selection = select_kernel_cv(
            x_train,
            y_train,
            splits,
            kind=kind,
            model_name=model_name,
            fold_label=outer_fold,
            order=order,
            qc_rows=qc_rows,
        )
        scores, metrics = fit_outer(
            x_train,
            y_train,
            x_validation,
            y_validation,
            selection,
            order=order,
            qc_rows=qc_rows,
            qc_fold=outer_fold,
        )
        full_metric_rows.append(
            {
                "MODEL": model_name,
                "OUTER_FOLD": outer_fold,
                "N_TRAIN": len(x_train),
                "N_VALIDATION": len(x_validation),
                "ORDER_FEATURES": json.dumps([X10_FEATURES[index] for index in order]),
                "INNER_AUROC_MEAN": selection["inner_auroc_mean"],
                "INNER_AUROC_SD": selection["inner_auroc_sd"],
                "THRESHOLD": selection["threshold"],
                **{key.upper(): value for key, value in metrics.items()},
            }
        )
        full_parameter_rows.append(
            {
                "MODEL": model_name,
                "OUTER_FOLD": outer_fold,
                "ORDER_FEATURES": json.dumps([X10_FEATURES[index] for index in order]),
                "C": selection["C"],
                "KERNEL_PARAMS": json.dumps(selection["kernel_params"], sort_keys=True),
                "THRESHOLD": selection["threshold"],
                "INNER_THRESHOLD_MCC": selection["threshold_metrics"]["mcc"],
                "SELECTION_SOURCE": "inner_OOF_outer_train_only",
            }
        )
        full_prediction_rows.extend(
            prediction_rows(
                validation_frame,
                model=model_name,
                outer_fold=outer_fold,
                scores=scores,
                threshold=selection["threshold"],
            )
        )
    return {
        "outer_fold": outer_fold,
        "singleton_metrics": singleton_rows,
        "pair_inner_results": pair_inner_rows,
        "pair_outer_results": pair_outer_rows,
        "pair_oof_predictions": pair_prediction_rows,
        "constructed_paths": path_rows,
        "path_edge_details": path_edge_rows,
        "full_metrics": full_metric_rows,
        "full_predictions": full_prediction_rows,
        "full_parameters": full_parameter_rows,
        "kernel_qc": qc_rows,
        "matrices": {
            "predictive": predictive.tolist(),
            "synergy": synergy.tolist(),
            "stable": stable.tolist(),
        },
        "audit": {
            "outer_validation_used_for_pair_or_path_selection": False,
            "outer_validation_evaluated_once_per_frozen_model": True,
            "scaler_policy": "fit_each_inner_train_or_outer_train_only",
            "elapsed_seconds": time.perf_counter() - started,
            "rss_end_bytes": process_rss_bytes(),
        },
    }


def pooled_metrics(metrics: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, group in predictions.groupby("MODEL", sort=False):
        truth = group.LABEL.to_numpy(int)
        score = group.SCORE.to_numpy(float)
        pred = group.PRED.to_numpy(int)
        tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
        folds = metrics[metrics.MODEL == model]
        rows.append(
            {
                "MODEL": model,
                "N": len(group),
                "MCC": matthews_corrcoef(truth, pred),
                "AUROC": roc_auc_score(truth, score),
                "AUPRC": average_precision_score(truth, score),
                "BALANCED_ACCURACY": balanced_accuracy_score(truth, pred),
                "SENSITIVITY": tp / (tp + fn),
                "SPECIFICITY": tn / (tn + fp),
                "TP": tp,
                "TN": tn,
                "FP": fp,
                "FN": fn,
                "FOLD_MCC_MEAN": folds.MCC.mean(),
                "FOLD_MCC_SD": folds.MCC.std(ddof=1),
                "FOLD_AUROC_MEAN": folds.AUROC.mean(),
                "FOLD_AUROC_SD": folds.AUROC.std(ddof=1),
            }
        )
    return pd.DataFrame(rows)


def mcc_fast(y: np.ndarray, pred: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    pred = np.asarray(pred, dtype=int)
    tp = int(np.sum((y == 1) & (pred == 1)))
    tn = int(np.sum((y == 0) & (pred == 0)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return 0.0 if denominator == 0 else (tp * tn - fp * fn) / denominator


def holm_adjust(p_values: np.ndarray) -> np.ndarray:
    values = np.asarray(p_values, dtype=float)
    order = np.argsort(values, kind="stable")
    adjusted = np.empty(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (len(values) - rank) * values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def pairwise_bootstrap(
    pair_predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED + 45)
    summary_rows = []
    raw_rows = []
    for pair_index, group in pair_predictions.groupby("PAIR_INDEX", sort=True):
        wide = group.pivot(
            index=["ID", "BUTINA_CLUSTER_ID", "LABEL"], columns="MODEL", values="PRED"
        ).reset_index()
        clusters = np.asarray(sorted(wide.BUTINA_CLUSTER_ID.unique()))
        cluster_indices = {
            cluster: np.flatnonzero(wide.BUTINA_CLUSTER_ID.to_numpy() == cluster)
            for cluster in clusters
        }
        truth = wide.LABEL.to_numpy(int)
        zz = wide["pair_iqp_zz"].to_numpy(int)
        nozz = wide["pair_phase_no_zz"].to_numpy(int)
        observed = mcc_fast(truth, zz) - mcc_fast(truth, nozz)
        deltas = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
        for replicate in range(BOOTSTRAP_REPLICATES):
            sampled_clusters = rng.choice(clusters, size=len(clusters), replace=True)
            sampled = np.concatenate([cluster_indices[cluster] for cluster in sampled_clusters])
            deltas[replicate] = mcc_fast(truth[sampled], zz[sampled]) - mcc_fast(
                truth[sampled], nozz[sampled]
            )
            raw_rows.append(
                {
                    "PAIR_INDEX": int(pair_index),
                    "PAIR": group.PAIR.iloc[0],
                    "REPLICATE": replicate + 1,
                    "MCC_DELTA": deltas[replicate],
                }
            )
        p_two_sided = min(1.0, 2 * min(np.mean(deltas <= 0), np.mean(deltas >= 0)))
        summary_rows.append(
            {
                "PAIR_INDEX": int(pair_index),
                "PAIR": group.PAIR.iloc[0],
                "OBSERVED_DELTA": observed,
                "BOOTSTRAP_MEDIAN": np.median(deltas),
                "CI_LOW_95": np.quantile(deltas, 0.025),
                "CI_HIGH_95": np.quantile(deltas, 0.975),
                "P_DELTA_GT_0": np.mean(deltas > 0),
                "P_VALUE_TWO_SIDED": p_two_sided,
                "REPLICATES": BOOTSTRAP_REPLICATES,
                "RESAMPLING_UNIT": "BUTINA_CLUSTER_ID",
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary["HOLM_ADJUSTED_P"] = holm_adjust(summary.P_VALUE_TWO_SIDED.to_numpy())
    summary["HOLM_REJECT_0_05"] = summary.HOLM_ADJUSTED_P < 0.05
    return summary, pd.DataFrame(raw_rows)


def full_model_bootstrap(
    predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frozen = pd.read_csv(
        BASELINE_CAMPAIGN / "03_NESTED_CV" / "NESTED_OUTER_OOF_PREDICTIONS.csv"
    )
    frozen = frozen[frozen.MODEL.isin(["random_forest", "rbf_matched", "quantum_iqp_zz_linear"])]
    frozen = frozen.rename(columns={"MODEL": "FROZEN_MODEL"})
    frozen_rows = []
    for row in frozen.itertuples(index=False):
        frozen_rows.append(
            {
                "ID": row.ID,
                "BUTINA_CLUSTER_ID": row.BUTINA_CLUSTER_ID,
                "LABEL": row.LABEL,
                "MODEL": row.FROZEN_MODEL,
                "PRED": row.PRED,
            }
        )
    selected = predictions[["ID", "BUTINA_CLUSTER_ID", "LABEL", "MODEL", "PRED"]]
    combined = pd.concat([selected, pd.DataFrame(frozen_rows)], ignore_index=True)
    wide = combined.pivot(
        index=["ID", "BUTINA_CLUSTER_ID", "LABEL"], columns="MODEL", values="PRED"
    ).reset_index()
    comparisons = [
        ("max_synergy_path_10q", "current_order_10q"),
        ("stable_synergy_path_10q", "current_order_10q"),
        ("max_synergy_path_20q_duplicate", "current_order_20q_duplicate"),
        ("max_synergy_path_20q_complementary", "current_order_20q_complementary"),
        ("stable_synergy_path_20q_duplicate", "current_order_20q_duplicate"),
        ("stable_synergy_path_20q_complementary", "current_order_20q_complementary"),
    ]
    selected_models = [model for model in FULL_MODELS if not model.startswith("current_order")]
    comparisons.extend((model, "quantum_iqp_zz_linear") for model in selected_models)
    comparisons.extend((model, "rbf_matched") for model in selected_models)
    comparisons.extend((model, "random_forest") for model in selected_models)
    clusters = np.asarray(sorted(wide.BUTINA_CLUSTER_ID.unique()))
    cluster_indices = {
        cluster: np.flatnonzero(wide.BUTINA_CLUSTER_ID.to_numpy() == cluster)
        for cluster in clusters
    }
    truth = wide.LABEL.to_numpy(int)
    observed = {
        (left, right): mcc_fast(truth, wide[left].to_numpy(int))
        - mcc_fast(truth, wide[right].to_numpy(int))
        for left, right in comparisons
    }
    rng = np.random.default_rng(SEED)
    values = {(left, right): [] for left, right in comparisons}
    raw_rows = []
    for replicate in range(1, BOOTSTRAP_REPLICATES + 1):
        sampled_clusters = rng.choice(clusters, size=len(clusters), replace=True)
        sampled = np.concatenate([cluster_indices[cluster] for cluster in sampled_clusters])
        for left, right in comparisons:
            delta = mcc_fast(truth[sampled], wide[left].to_numpy(int)[sampled]) - mcc_fast(
                truth[sampled], wide[right].to_numpy(int)[sampled]
            )
            values[(left, right)].append(delta)
            raw_rows.append(
                {
                    "REPLICATE": replicate,
                    "LEFT_MODEL": left,
                    "RIGHT_MODEL": right,
                    "MCC_DELTA": delta,
                }
            )
    rows = []
    for left, right in comparisons:
        array = np.asarray(values[(left, right)])
        rows.append(
            {
                "LEFT_MODEL": left,
                "RIGHT_MODEL": right,
                "METRIC": "MCC",
                "OBSERVED_DELTA": observed[(left, right)],
                "BOOTSTRAP_MEDIAN": np.median(array),
                "CI_LOW_95": np.quantile(array, 0.025),
                "CI_HIGH_95": np.quantile(array, 0.975),
                "P_DELTA_GT_0": np.mean(array > 0),
                "REPLICATES": BOOTSTRAP_REPLICATES,
                "RESAMPLING_UNIT": "BUTINA_CLUSTER_ID",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(raw_rows)


def y_randomization_permutation(
    train: pd.DataFrame, permutation: int
) -> dict[str, Any]:
    rng = np.random.default_rng(SEED + 100000 + permutation)
    labels = rng.permutation(train.LABEL.to_numpy(int))
    features = train.loc[:, X10_FEATURES].to_numpy(float)
    splits = frozen_five_splits(train)
    synergy = np.zeros((10, 10), dtype=float)
    best_pair_mcc = -np.inf
    best_pair = None
    for left, right in all_pairs():
        raw = features[:, [left, right]]
        nozz = select_kernel_cv(
            raw,
            labels,
            splits,
            kind="pair_no_zz",
            model_name="y_random_pair_nozz",
            fold_label=f"perm_{permutation}",
        )
        zz = select_kernel_cv(
            raw,
            labels,
            splits,
            kind="pair_zz",
            model_name="y_random_pair_zz",
            fold_label=f"perm_{permutation}",
        )
        zz_mcc = float(zz["threshold_metrics"]["mcc"])
        delta = zz_mcc - float(nozz["threshold_metrics"]["mcc"])
        synergy[left, right] = synergy[right, left] = delta
        candidate_name = f"{X10_FEATURES[left]}__{X10_FEATURES[right]}"
        if zz_mcc > best_pair_mcc or (
            zz_mcc == best_pair_mcc and candidate_name < str(best_pair)
        ):
            best_pair_mcc = zz_mcc
            best_pair = candidate_name
    path = held_karp_paths(synergy, top_k=1)[0]
    total, minimum, deviation = path_statistics(path, synergy)
    return {
        "PERMUTATION": permutation,
        "BEST_PAIR_MCC": best_pair_mcc,
        "BEST_PAIR": best_pair,
        "BEST_PATH_SCORE": total,
        "BEST_PATH_MIN_EDGE": minimum,
        "BEST_PATH_EDGE_SD": deviation,
        "BEST_PATH": json.dumps([X10_FEATURES[index] for index in path]),
        "LABEL_SEED": SEED + 100000 + permutation,
        "MODE": "complete_pair_screen_and_path_rebuild",
    }


def matrix_frame(matrix: np.ndarray) -> pd.DataFrame:
    frame = pd.DataFrame(matrix, columns=X10_FEATURES, index=X10_FEATURES)
    frame.index.name = "FEATURE"
    return frame.reset_index()


def aggregate_edge_matrices(pair_inner: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    predictive = np.zeros((10, 10), dtype=float)
    synergy = np.zeros((10, 10), dtype=float)
    stable = np.zeros((10, 10), dtype=float)
    aggregate = pair_inner.groupby(["LEFT_INDEX", "RIGHT_INDEX"], as_index=False).agg(
        PAIR_MCC_ZZ=("PAIR_MCC_ZZ", "mean"),
        DELTA=("DELTA_MCC_ZZ_VS_NO_ZZ", "mean"),
        STABLE=("STABLE_EDGE_SCORE", "mean"),
    )
    for row in aggregate.itertuples(index=False):
        i, j = int(row.LEFT_INDEX), int(row.RIGHT_INDEX)
        predictive[i, j] = predictive[j, i] = row.PAIR_MCC_ZZ
        synergy[i, j] = synergy[j, i] = row.DELTA
        stable[i, j] = stable[j, i] = row.STABLE
    return predictive, synergy, stable


def external_cr8_evaluation(
    train: pd.DataFrame,
    external: pd.DataFrame,
    synergy: np.ndarray,
    stable: np.ndarray,
    output: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    max_paths = held_karp_paths(synergy, top_k=2)
    stable_paths = held_karp_paths(stable, top_k=2)
    max_path = max_paths[0]
    stable_path = stable_paths[0]
    if canonical_path(max_path) == canonical_path(stable_path):
        stable_path = stable_paths[1]
    orders = {
        "current_order": CURRENT_ORDER,
        "max_synergy_path": max_path,
        "stable_synergy_path": stable_path,
    }
    x = train.loc[:, X10_FEATURES].to_numpy(float)
    y = train.LABEL.to_numpy(int)
    x_external = external.loc[:, X10_FEATURES].to_numpy(float)
    y_external = external.LABEL.to_numpy(int)
    splits = frozen_five_splits(train)
    specs = [
        ("current_order_10q", "full10", orders["current_order"]),
        ("max_synergy_path_10q", "full10", orders["max_synergy_path"]),
        ("stable_synergy_path_10q", "full10", orders["stable_synergy_path"]),
        ("current_order_20q_duplicate", "full20_duplicate", orders["current_order"]),
        ("current_order_20q_complementary", "full20_complementary", orders["current_order"]),
        ("max_synergy_path_20q_duplicate", "full20_duplicate", orders["max_synergy_path"]),
        ("max_synergy_path_20q_complementary", "full20_complementary", orders["max_synergy_path"]),
        ("stable_synergy_path_20q_duplicate", "full20_duplicate", orders["stable_synergy_path"]),
        ("stable_synergy_path_20q_complementary", "full20_complementary", orders["stable_synergy_path"]),
    ]
    selection_rows = []
    prediction_output = []
    metric_rows = []
    qc_rows: list[dict[str, Any]] = []
    for model_name, kind, order in specs:
        print(f"CR8 final B model: {model_name}", flush=True)
        selection = select_kernel_cv(
            x,
            y,
            splits,
            kind=kind,
            model_name=model_name,
            fold_label="cr8_final",
            order=order,
            qc_rows=qc_rows,
        )
        scores, metrics = fit_outer(
            x,
            y,
            x_external,
            y_external,
            selection,
            order=order,
            qc_rows=qc_rows,
            qc_fold="cr8_final",
        )
        selection_rows.append(
            {
                "MODEL": model_name,
                "ORDER_FEATURES": json.dumps([X10_FEATURES[index] for index in order]),
                "C": selection["C"],
                "KERNEL_PARAMS": json.dumps(selection["kernel_params"], sort_keys=True),
                "THRESHOLD": selection["threshold"],
                "CV_AUROC_MEAN": selection["inner_auroc_mean"],
                "CV_AUROC_SD": selection["inner_auroc_sd"],
                "SELECTION_DATA": "development_only",
                "CR8_USED_FOR_SELECTION": False,
            }
        )
        metric_rows.append(
            {"MODEL": model_name, "N": len(external), **{key.upper(): value for key, value in metrics.items()}}
        )
        prediction_output.extend(
            prediction_rows(
                external,
                model=model_name,
                outer_fold="CR8",
                scores=scores,
                threshold=selection["threshold"],
            )
        )
    selection_frame = pd.DataFrame(selection_rows)
    prediction_frame = pd.DataFrame(prediction_output)
    metric_frame = pd.DataFrame(metric_rows)
    selection_frame.to_csv(output / "CR8_FINAL_SELECTION.csv", index=False)
    prediction_frame.to_csv(output / "CR8_PREDICTIONS.csv", index=False)
    metric_frame.to_csv(output / "CR8_METRICS.csv", index=False)
    pd.DataFrame(qc_rows).to_csv(output / "CR8_KERNEL_QC.csv", index=False)
    write_json(
        output / "CR8_PATHS.json",
        {
            name: [X10_FEATURES[index] for index in path]
            for name, path in orders.items()
        },
    )
    return selection_frame, prediction_frame, metric_frame


def heatmap(
    matrix: np.ndarray,
    title: str,
    output: Path,
    *,
    delta: bool,
) -> None:
    fig, axis = plt.subplots(figsize=(13, 11))
    maximum = float(np.max(np.abs(matrix))) if delta else float(np.max(matrix))
    minimum = -maximum if delta else float(np.min(matrix))
    image = axis.imshow(matrix, cmap="coolwarm" if delta else "viridis", vmin=minimum, vmax=maximum)
    axis.set_xticks(range(10), X10_FEATURES, rotation=45, ha="right")
    axis.set_yticks(range(10), X10_FEATURES)
    for i in range(10):
        for j in range(10):
            if i != j:
                axis.text(j, i, f"{matrix[i, j]:.3f}", ha="center", va="center", fontsize=7, color="black")
    axis.set_title(title)
    fig.colorbar(image, ax=axis, shrink=0.75)
    fig.tight_layout()
    fig.savefig(output.with_suffix(".png"), dpi=180)
    fig.savefig(output.with_suffix(".svg"))
    plt.close(fig)


def generate_figures(
    predictive: np.ndarray,
    synergy: np.ndarray,
    pooled: pd.DataFrame,
    y_results: pd.DataFrame,
    output: Path,
) -> None:
    heatmap(predictive, "Pair predictive MCC (inner-OOF mean)", output / "FIG01_PAIR_PREDICTIVE_MCC", delta=False)
    heatmap(synergy, "Pair ZZ synergy MCC delta (inner-OOF mean)", output / "FIG02_PAIR_ZZ_SYNERGY", delta=True)
    indexed = pooled.set_index("MODEL").loc[list(FULL_MODELS)]
    fig, axis = plt.subplots(figsize=(14, 6))
    axis.bar(range(len(indexed)), indexed.MCC, color=["#355070"] * 3 + ["#6D597A", "#B56576"] * 3)
    axis.set_xticks(range(len(indexed)), indexed.index, rotation=35, ha="right")
    axis.set_ylabel("Pooled OOF MCC")
    axis.set_title("Full selected circuits")
    fig.tight_layout()
    fig.savefig(output / "FIG03_FULL_MODEL_MCC.png", dpi=180)
    fig.savefig(output / "FIG03_FULL_MODEL_MCC.svg")
    plt.close(fig)
    if not y_results.empty:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        axes[0].hist(y_results.BEST_PAIR_MCC, bins=min(15, len(y_results)), color="#6D597A")
        axes[0].set_title("Y-randomization: best pair MCC")
        axes[1].hist(y_results.BEST_PATH_SCORE, bins=min(15, len(y_results)), color="#B56576")
        axes[1].set_title("Y-randomization: best path score")
        for axis in axes:
            axis.set_ylabel("Count")
        fig.tight_layout()
        fig.savefig(output / "FIG04_Y_RANDOMIZATION.png", dpi=180)
        fig.savefig(output / "FIG04_Y_RANDOMIZATION.svg")
        plt.close(fig)


def ranking_stability(pair_inner: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pair_index, group in pair_inner.groupby("PAIR_INDEX", sort=True):
        all_deltas = np.concatenate(
            [np.asarray(json.loads(value), dtype=float) for value in group.INNER_FOLD_DELTAS]
        )
        leave_out_means = []
        for fold_position in range(INNER_FOLDS):
            retained = []
            for value in group.INNER_FOLD_DELTAS:
                array = np.asarray(json.loads(value), dtype=float)
                retained.extend(np.delete(array, fold_position).tolist())
            leave_out_means.append(float(np.mean(retained)))
        rows.append(
            {
                "PAIR_INDEX": int(pair_index),
                "PAIR": group.PAIR.iloc[0],
                "MEAN_INNER_DELTA": all_deltas.mean(),
                "SD_INNER_DELTA": all_deltas.std(ddof=1),
                "POSITIVE_INNER_FOLD_COUNT": int((all_deltas > 0).sum()),
                "TOTAL_INNER_FOLDS": len(all_deltas),
                "STABLE_SCORE": all_deltas.mean() - 0.5 * all_deltas.std(ddof=1),
                "LEAVE_ONE_POSITION_MEANS": json.dumps(leave_out_means),
                "LEAVE_ONE_POSITION_RANGE": max(leave_out_means) - min(leave_out_means),
            }
        )
    frame = pd.DataFrame(rows)
    frame["RANK_BY_MEAN"] = frame.MEAN_INNER_DELTA.rank(method="min", ascending=False).astype(int)
    frame["RANK_BY_STABILITY"] = frame.STABLE_SCORE.rank(method="min", ascending=False).astype(int)
    return frame.sort_values(["RANK_BY_MEAN", "PAIR_INDEX"], kind="stable")


def write_report(
    root: Path,
    pair_inner: pd.DataFrame,
    pair_bootstrap: pd.DataFrame,
    paths: pd.DataFrame,
    pooled: pd.DataFrame,
    deltas: pd.DataFrame,
    external_metrics: pd.DataFrame,
    y_results: pd.DataFrame,
) -> None:
    top_predictive = (
        pair_inner.groupby("PAIR", as_index=False).PAIR_MCC_ZZ.mean().sort_values("PAIR_MCC_ZZ", ascending=False).head(5)
    )
    top_synergy = (
        pair_inner.groupby("PAIR", as_index=False).DELTA_MCC_ZZ_VS_NO_ZZ.mean().sort_values("DELTA_MCC_ZZ_VS_NO_ZZ", ascending=False).head(5)
    )
    stability = ranking_stability(pair_inner).head(5)
    survived = int(pair_bootstrap.HOLM_REJECT_0_05.sum())
    indexed = pooled.set_index("MODEL")
    frozen_summary = pd.read_csv(BASELINE_CAMPAIGN / "03_NESTED_CV" / "NESTED_SUMMARY.csv").set_index("MODEL")
    rf_mcc = float(frozen_summary.loc["random_forest", "POOLED_OOF_MCC"])
    path_consistency = paths.groupby("PATH_TYPE").ORDER_FEATURES.nunique().to_dict()
    lines = [
        "# BeeQ Exercise B — pairwise ZZ y construcción de caminos",
        "",
        "## Alcance",
        "",
        "Se ejecutó exclusivamente el Ejercicio B como campaña separada. Los 45 pares no dirigidos se cribaron dentro del entrenamiento de cada outer fold. Los labels de outer-validation no se usaron para seleccionar aristas, caminos, escalas, C ni thresholds. La simulación fue exacta, sin shots, ruido ni hardware cuántico. No se consultaron los papers excluidos ni el historical holdout.",
        "",
        "## Pares principales",
        "",
        "### Mayor MCC pairwise inner-OOF",
        "",
    ]
    lines.extend(f"- {row.PAIR}: {row.PAIR_MCC_ZZ:.4f}" for row in top_predictive.itertuples(index=False))
    lines.extend(["", "### Mayor delta atribuible a ZZ", ""])
    lines.extend(
        f"- {row.PAIR}: {row.DELTA_MCC_ZZ_VS_NO_ZZ:+.4f}"
        for row in top_synergy.itertuples(index=False)
    )
    lines.extend(["", "### Mayor estabilidad", ""])
    lines.extend(
        f"- {row.PAIR}: stable score {row.STABLE_SCORE:+.4f}; {int(row.POSITIVE_INNER_FOLD_COUNT)}/{int(row.TOTAL_INNER_FOLDS)} deltas positivos"
        for row in stability.itertuples(index=False)
    )
    lines.extend(
        [
            "",
            f"Pares que sobrevivieron Holm a 0.05: **{survived}/45**. El ranking pairwise sigue siendo exploratorio y sujeto a winner's curse.",
            "",
            "## Caminos por outer fold",
            "",
            "| Fold | Tipo | Orden | Puntaje |",
            "|---:|---|---|---:|",
        ]
    )
    for row in paths.itertuples(index=False):
        order = " → ".join(json.loads(row.ORDER_FEATURES))
        lines.append(f"| {row.OUTER_FOLD} | {row.PATH_TYPE} | {order} | {row.TOTAL_SCORE:.4f} |")
    lines.extend(["", "Número de órdenes distintos por tipo: " + json.dumps(path_consistency, sort_keys=True) + ".", ""])
    lines.extend(
        [
            "## Circuitos completos pooled OOF",
            "",
            "| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model in FULL_MODELS:
        row = indexed.loc[model]
        lines.append(
            f"| {model} | {row.MCC:.4f} | {row.AUROC:.4f} | {row.AUPRC:.4f} | {row.BALANCED_ACCURACY:.4f} | {row.SENSITIVITY:.4f} | {row.SPECIFICITY:.4f} |"
        )
    lines.extend(["", "## Deltas primarios MCC", ""])
    for row in deltas.itertuples(index=False):
        if row.RIGHT_MODEL.startswith("current_order"):
            lines.append(
                f"- {row.LEFT_MODEL} − {row.RIGHT_MODEL}: {row.OBSERVED_DELTA:+.4f}, IC95% [{row.CI_LOW_95:.4f}, {row.CI_HIGH_95:.4f}], P(delta>0)={row.P_DELTA_GT_0:.3f}."
            )
    best_selected_mcc = float(indexed.loc[[m for m in FULL_MODELS if not m.startswith("current_order")], "MCC"].max())
    lines.extend(
        [
            "",
            f"Random Forest congelado conserva MCC {rf_mcc:.4f}; mejor arquitectura seleccionada de B: {best_selected_mcc:.4f}. {'Random Forest continúa por encima.' if rf_mcc > best_selected_mcc else 'La mejor arquitectura seleccionada alcanza o supera el estimador puntual de Random Forest.'}",
            "",
            "## Y-randomization",
            "",
            f"Se ejecutaron {len(y_results)} permutaciones completas del cribado y reconstrucción de camino. La distribución nula del mejor MCC pairwise y del mejor puntaje de camino está en `09_Y_RANDOMIZATION/Y_RANDOMIZATION_RESULTS.csv`. El número final fue fijado tras benchmark y está documentado en configuración/provenance.",
            "",
            "## Evaluación externa CR8 al final",
            "",
            "CR8 contiene 8 moléculas (6 negativas, 2 positivas). Todos los caminos finales, escalas, C y thresholds se congelaron usando solo desarrollo antes de evaluar CR8; CR8 no participó en selección.",
            "",
            "| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in external_metrics.itertuples(index=False):
        lines.append(
            f"| {row.MODEL} | {row.MCC:.4f} | {row.AUROC:.4f} | {row.AUPRC:.4f} | {row.BALANCED_ACCURACY:.4f} | {row.SENSITIVITY:.4f} | {row.SPECIFICITY:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretación",
            "",
            "Los resultados outer de circuitos completos evalúan confirmatoriamente el algoritmo de selección predefinido; los rankings y outer pairwise individuales son exploratorios. Cambios fuertes de aristas/caminos entre folds indican inestabilidad de selección y posible winner's curse. Ningún resultado demuestra ventaja cuántica. CR8 es demasiado pequeño para conclusiones firmes y no autoriza ajustes post hoc.",
            "",
            "Los CSV son la fuente canónica; `PAIRWISE_SUMMARY.xlsx` es un resumen navegable. Los checkpoints atómicos por outer fold y permutación permiten reanudar la campaña.",
        ]
    )
    (root / "FINAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_directories(root: Path) -> dict[str, Path]:
    names = {
        "audit": "00_AUDIT",
        "config": "01_CONFIG",
        "singletons": "02_SINGLETONS",
        "pairs": "03_PAIRWISE_SCREEN",
        "matrices": "04_EDGE_MATRICES",
        "paths": "05_PATH_CONSTRUCTION",
        "full10": "06_FULL_10Q_VALIDATION",
        "full20": "07_FULL_20Q_VALIDATION",
        "statistics": "08_STATISTICS",
        "yrandom": "09_Y_RANDOMIZATION",
        "figures": "10_FIGURES",
        "manifest": "11_MANIFEST",
        "external": "12_EXTERNAL_CR8",
    }
    paths = {key: root / value for key, value in names.items()}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def default_campaign_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return PROJECT_ROOT / "results" / "campaigns" / f"BEEQ_EXERCISE_B_PAIRWISE_GRAPH_{stamp}"


def run_campaign(args: argparse.Namespace) -> Path:
    root = args.campaign_dir.resolve()
    paths = prepare_directories(root)
    if args.rebuild_manifest:
        build_b_manifest(root)
        return root
    train = pd.read_csv(TRAIN_PATH)
    external = pd.read_csv(CR8_PATH)
    if EXPECTED_TRAIN_SHA256_LF not in {sha256_file(TRAIN_PATH), sha256_canonical_lf(TRAIN_PATH)}:
        raise RuntimeError("Development hash mismatch")
    if EXPECTED_CR8_SHA256_LF not in {sha256_file(CR8_PATH), sha256_canonical_lf(CR8_PATH)}:
        raise RuntimeError("CR8 hash mismatch")
    if len(train) != 712 or train.LABEL.value_counts().to_dict() != {0: 490, 1: 222}:
        raise RuntimeError("Development contract mismatch")
    if len(external) != 8 or external.LABEL.value_counts().to_dict() != {0: 6, 1: 2}:
        raise RuntimeError("CR8 contract mismatch")
    pair_frame = validate_pair_enumeration()
    pair_frame.to_csv(paths["pairs"] / "ALL_45_PAIRS.csv", index=False)
    write_json(paths["audit"] / "GIT_STATE_AT_START.json", git_snapshot())
    write_json(
        paths["audit"] / "ENVIRONMENT.json",
        {
            "captured_utc": utc_now(),
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "rss_bytes": process_rss_bytes(),
        },
    )
    pd.DataFrame(
        [
            {
                "FILE": str(TRAIN_PATH.relative_to(PROJECT_ROOT)),
                "SHA256_PHYSICAL": sha256_file(TRAIN_PATH),
                "SHA256_CANONICAL_LF": sha256_canonical_lf(TRAIN_PATH),
                "EXPECTED_LF": EXPECTED_TRAIN_SHA256_LF,
            },
            {
                "FILE": str(CR8_PATH.relative_to(PROJECT_ROOT)),
                "SHA256_PHYSICAL": sha256_file(CR8_PATH),
                "SHA256_CANONICAL_LF": sha256_canonical_lf(CR8_PATH),
                "EXPECTED_LF": EXPECTED_CR8_SHA256_LF,
            },
        ]
    ).to_csv(paths["audit"] / "INPUT_HASHES.csv", index=False)
    config = {
        "exercise": "B",
        "seed": SEED,
        "features": list(X10_FEATURES),
        "pair_count": 45,
        "outer_folds": list(OUTER_FOLDS),
        "inner_folds": INNER_FOLDS,
        "C_values": list(C_VALUES),
        "feature_scales": list(FEATURE_SCALES),
        "rbf_gammas": list(RBF_GAMMAS),
        "selection_metric": "mean_inner_AUROC",
        "threshold_policy": "max_MCC_then_balanced_accuracy_then_abs_threshold_then_threshold",
        "stable_edge_score": "mean_inner_delta_mcc - 0.5*sd_inner_delta_mcc",
        "path_algorithm": "Held-Karp dynamic programming; path/reverse canonicalized",
        "path_tie_break": ["total_score", "minimum_edge", "edge_sd", "lexicographic_feature_names"],
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "y_randomization_replicates": args.y_replicates,
        "y_randomization_reduction_reason": args.y_reduction_reason,
        "simulation": "exact_no_shots_no_noise",
        "external_CR8_role": "post-freeze_only",
        "external_used_for_selection": False,
        "A_outer_results_used_for_selection": False,
        "historical_holdout_used": False,
        "excluded_papers_used": False,
    }
    write_json(paths["config"] / "CAMPAIGN_CONFIG.json", config)
    write_json(
        paths["manifest"] / "SOURCE_CODE_PROVENANCE.json",
        {
            "src/exercise_b_campaign.py": sha256_file(Path(__file__)),
            "src/exercise_a_campaign.py": sha256_file(PROJECT_ROOT / "src" / "exercise_a_campaign.py"),
            "dependency_note": "Only generic exact backend/metrics helpers from A code were reused; A outer results were not used for pair/path selection.",
        },
    )

    outer_results = []
    signature = {
        "source_sha256": sha256_file(Path(__file__)),
        "input_sha256_lf": EXPECTED_TRAIN_SHA256_LF,
        "seed": SEED,
    }
    for fold in OUTER_FOLDS:
        checkpoint = paths["pairs"] / "checkpoints" / f"outer_fold_{fold}.json"
        if args.resume and checkpoint.is_file():
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            if payload.get("signature") != {**signature, "outer_fold": fold}:
                raise RuntimeError(f"Checkpoint signature mismatch: {checkpoint}")
            result = payload["result"]
        else:
            print(f"Starting outer fold {fold}/5", flush=True)
            result = screen_outer_fold(train, fold)
            atomic_json(
                checkpoint,
                {
                    "status": "complete",
                    "completed_utc": utc_now(),
                    "signature": {**signature, "outer_fold": fold},
                    "result": result,
                },
            )
        outer_results.append(result)
    singleton = pd.DataFrame([row for result in outer_results for row in result["singleton_metrics"]])
    pair_inner = pd.DataFrame([row for result in outer_results for row in result["pair_inner_results"]])
    pair_outer = pd.DataFrame([row for result in outer_results for row in result["pair_outer_results"]])
    pair_predictions = pd.DataFrame([row for result in outer_results for row in result["pair_oof_predictions"]])
    paths_frame = pd.DataFrame([row for result in outer_results for row in result["constructed_paths"]])
    path_edges_frame = pd.DataFrame([row for result in outer_results for row in result["path_edge_details"]])
    full_metrics = pd.DataFrame([row for result in outer_results for row in result["full_metrics"]])
    full_predictions = pd.DataFrame([row for result in outer_results for row in result["full_predictions"]])
    full_params = pd.DataFrame([row for result in outer_results for row in result["full_parameters"]])
    qc = pd.DataFrame([row for result in outer_results for row in result["kernel_qc"]])
    singleton.to_csv(paths["singletons"] / "SINGLETON_METRICS.csv", index=False)
    pair_inner.to_csv(paths["pairs"] / "PAIRWISE_INNER_RESULTS.csv", index=False)
    pair_outer.to_csv(paths["pairs"] / "PAIRWISE_OUTER_RESULTS.csv", index=False)
    pair_predictions.to_csv(paths["pairs"] / "PAIRWISE_OOF_PREDICTIONS.csv", index=False)
    paths_frame.to_csv(paths["paths"] / "CONSTRUCTED_PATHS.csv", index=False)
    path_edges_frame.to_csv(paths["paths"] / "PATH_EDGE_DETAILS.csv", index=False)
    predictive, synergy, stable = aggregate_edge_matrices(pair_inner)
    matrix_frame(predictive).to_csv(paths["matrices"] / "PAIR_PREDICTIVE_MCC_MATRIX.csv", index=False)
    matrix_frame(synergy).to_csv(paths["matrices"] / "PAIR_ZZ_SYNERGY_MATRIX.csv", index=False)
    matrix_frame(stable).to_csv(paths["matrices"] / "PAIR_STABLE_SYNERGY_MATRIX.csv", index=False)
    rank_frame = ranking_stability(pair_inner)
    rank_frame.to_csv(paths["matrices"] / "PAIRWISE_RANKING_STABILITY.csv", index=False)
    metrics10 = full_metrics[full_metrics.MODEL.isin(FULL_10Q_MODELS)]
    metrics20 = full_metrics[full_metrics.MODEL.isin(FULL_20Q_MODELS)]
    predictions10 = full_predictions[full_predictions.MODEL.isin(FULL_10Q_MODELS)]
    predictions20 = full_predictions[full_predictions.MODEL.isin(FULL_20Q_MODELS)]
    metrics10.to_csv(paths["full10"] / "FULL_10Q_OUTER_METRICS.csv", index=False)
    predictions10.to_csv(paths["full10"] / "FULL_10Q_OOF_PREDICTIONS.csv", index=False)
    metrics20.to_csv(paths["full20"] / "FULL_20Q_OUTER_METRICS.csv", index=False)
    predictions20.to_csv(paths["full20"] / "FULL_20Q_OOF_PREDICTIONS.csv", index=False)
    full_params.to_csv(paths["statistics"] / "FULL_MODEL_SELECTED_PARAMS.csv", index=False)
    qc.to_csv(paths["statistics"] / "KERNEL_QC.csv", index=False)
    pooled = pooled_metrics(full_metrics, full_predictions)
    pooled.to_csv(paths["statistics"] / "FULL_MODEL_POOLED_METRICS.csv", index=False)
    pair_bootstrap, pair_bootstrap_raw = pairwise_bootstrap(pair_predictions)
    pair_bootstrap.to_csv(paths["statistics"] / "PAIRWISE_BOOTSTRAP.csv", index=False)
    pair_bootstrap[["PAIR_INDEX", "PAIR", "P_VALUE_TWO_SIDED", "HOLM_ADJUSTED_P", "HOLM_REJECT_0_05"]].to_csv(
        paths["statistics"] / "PAIRWISE_HOLM_CORRECTION.csv", index=False
    )
    pair_bootstrap_raw.to_csv(paths["statistics"] / "PAIRWISE_BOOTSTRAP_RAW.csv", index=False)
    deltas, deltas_raw = full_model_bootstrap(full_predictions)
    deltas.to_csv(paths["statistics"] / "PAIRED_MODEL_DELTAS.csv", index=False)
    deltas_raw.to_csv(paths["statistics"] / "PAIRED_MODEL_BOOTSTRAP_RAW.csv", index=False)

    y_rows = []
    for permutation in range(1, args.y_replicates + 1):
        checkpoint = paths["yrandom"] / "checkpoints" / f"permutation_{permutation:04d}.json"
        perm_signature = {**signature, "permutation": permutation}
        if args.resume and checkpoint.is_file():
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            if payload.get("signature") != perm_signature:
                raise RuntimeError(f"Y checkpoint signature mismatch: {checkpoint}")
            row = payload["result"]
        else:
            print(f"Y-randomization {permutation}/{args.y_replicates}", flush=True)
            permutation_started = time.perf_counter()
            row = y_randomization_permutation(train, permutation)
            row["ELAPSED_SECONDS"] = time.perf_counter() - permutation_started
            atomic_json(
                checkpoint,
                {"status": "complete", "signature": perm_signature, "result": row},
            )
        y_rows.append(row)
    y_results = pd.DataFrame(y_rows)
    y_results.to_csv(paths["yrandom"] / "Y_RANDOMIZATION_RESULTS.csv", index=False)
    write_json(
        paths["yrandom"] / "Y_RANDOMIZATION_BENCHMARK.json",
        {
            "replicates_executed": args.y_replicates,
            "median_seconds_per_replicate": float(y_results.ELAPSED_SECONDS.median()) if len(y_results) else None,
            "projected_seconds_for_200": float(y_results.ELAPSED_SECONDS.median() * 200) if len(y_results) else None,
            "reduction_reason": args.y_reduction_reason,
        },
    )
    cr8_selection, cr8_predictions, cr8_metrics = external_cr8_evaluation(
        train, external, synergy, stable, paths["external"]
    )
    generate_figures(predictive, synergy, pooled, y_results, paths["figures"])
    write_report(root, pair_inner, pair_bootstrap, paths_frame, pooled, deltas, cr8_metrics, y_results)
    write_json(
        paths["audit"] / "LEAKAGE_ASSERTIONS.json",
        {
            "all_outer_checkpoints_report_no_outer_validation_selection": all(
                not result["audit"]["outer_validation_used_for_pair_or_path_selection"]
                for result in outer_results
            ),
            "scaler_train_only": True,
            "CR8_used_for_selection": False,
            "A_outer_results_used_for_selection": False,
        },
    )
    build_b_manifest(root)
    return root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, default=default_campaign_dir())
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rebuild-manifest", action="store_true")
    parser.add_argument("--y-replicates", type=int, default=200)
    parser.add_argument("--y-reduction-reason", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = run_campaign(args)
    print(f"Exercise B campaign complete: {root}", flush=True)


if __name__ == "__main__":
    main()
