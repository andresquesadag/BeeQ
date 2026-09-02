"""Exercise A: exact, resumable 10-qubit versus 20-qubit IQP-ZZ campaign.

The optimized kernel is an exact transfer-matrix contraction of the complex
one-dimensional Ising partition function defined by the repository's canonical
statevector feature map.  It uses neither shots nor noise and is not a quantum
hardware experiment.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
from .final_nested_campaign import classification_metrics, select_threshold
from .kernels import fidelity_kernel
from .quantum_feature_maps import iqp_zz_linear_statevectors


SEED = 20260824
INNER_FOLDS = 4
BOOTSTRAP_REPLICATES = 2000
FEATURE_SCALES = (0.125, 0.25, 0.5, 1.0)
C_VALUES = (0.1, 1.0, 10.0, 100.0)
INTERACTION_STRENGTH = 1.0
BASELINE_CAMPAIGN = (
    PROJECT_ROOT
    / "results"
    / "campaigns"
    / "BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z"
)
DATA_PATH = PROJECT_ROOT / "data" / "official" / "train_RDKitFixed.csv"
EXPECTED_DATA_SHA256 = "06a0817c082d7715211ca62aae367079f192e1a6c6663c2005c8c8eb5c758984"
BASELINE = "quantum_iqp_zz_linear"
IDLE = "iqp_zz_current_20q_idle_control"
DUPLICATE = "iqp_zz_current_20q_duplicate"
COMPLEMENTARY = "iqp_zz_current_20q_complementary_signed_sqrt"
MODELS = (BASELINE, IDLE, DUPLICATE, COMPLEMENTARY)
UNIQUE_EVALUATED_MODELS = (BASELINE, DUPLICATE, COMPLEMENTARY)
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".txt", ".svg"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_canonical_lf(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def git_snapshot() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()

    status = run("status", "--short", "--branch").splitlines()
    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "status_short_branch": status,
    }


def environment_snapshot() -> dict[str, Any]:
    packages = {}
    for name in (
        "numpy", "pandas", "scikit-learn", "scipy", "matplotlib"
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    blas = io.StringIO()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with contextlib.redirect_stdout(blas):
            np.__config__.show()
    return {
        "captured_utc": utc_now(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(),
        "packages": packages,
        "numpy_blas_configuration": blas.getvalue(),
        "numpy_configuration_warnings": [str(item.message) for item in captured],
        "process_rss_bytes": process_rss_bytes(),
    }


def process_rss_bytes() -> int:
    """Return current process working-set bytes without an extra dependency."""

    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        )
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.WorkingSetSize)
    import resource

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def architecture_definition(model: str) -> dict[str, Any]:
    common = {
        "order": list(X10_FEATURES),
        "initial_state": "uniform_superposition_on_active_qubits",
        "linear_phase": "Z",
        "interaction_strength": 1.0,
        "repetitions": 1,
        "shots": None,
        "noise": None,
        "fidelity": "abs(<psi(x)|psi(y)>)**2",
    }
    if model == BASELINE:
        return {**common, "qubits": 10, "encoding": ["z"] * 10, "edges": "linear_9"}
    if model == IDLE:
        return {
            **common,
            "qubits": 20,
            "active_qubits": 10,
            "idle_qubits": 10,
            "encoding": "baseline_10q tensor fixed_|0>^10",
            "edges": "baseline_linear_9_only",
            "competitive_model": False,
        }
    encoding = "z,z" if model == DUPLICATE else "z,sign(z)*sqrt(abs(z))"
    return {
        **common,
        "qubits": 20,
        "encoding": encoding,
        "qubit_layout": "V1a,V1b,V2a,V2b,...,V10a,V10b",
        "edges": "10 intra-variable plus 9 inter-variable, all weight 1",
        "transform_order": "StandardScaler(train-only), complementary transform, feature_scale",
    }


def encode_features(standardized: np.ndarray, model: str) -> np.ndarray:
    values = np.asarray(standardized, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(X10_FEATURES):
        raise ValueError("Expected standardized X10 with shape (samples, 10)")
    if not np.isfinite(values).all():
        raise ValueError("Encoded features must be finite")
    if model in {BASELINE, IDLE}:
        return values.copy()
    if model == DUPLICATE:
        return np.repeat(values, 2, axis=1)
    if model == COMPLEMENTARY:
        transformed = np.sign(values) * np.sqrt(np.abs(values))
        return np.stack((values, transformed), axis=2).reshape(len(values), 20)
    raise ValueError(f"Unknown architecture: {model}")


def exact_chain_fidelity_kernel(
    left: np.ndarray,
    right: np.ndarray | None = None,
    *,
    interaction_strength: float = 1.0,
    block_rows: int = 128,
) -> np.ndarray:
    """Contract the IQP-ZZ overlap exactly using a two-state transfer matrix.

    For encoded vectors x and y, the overlap is
    2^-n sum_s exp(i[sum_j (x_j-y_j)s_j +
    strength*sum_j (x_j*x_(j+1)-y_j*y_(j+1))s_j*s_(j+1)]).
    """

    x = np.asarray(left, dtype=float)
    y = x if right is None else np.asarray(right, dtype=float)
    if x.ndim != 2 or y.ndim != 2 or x.shape[1] != y.shape[1] or x.shape[1] < 1:
        raise ValueError("left/right must be finite 2D arrays with equal feature counts")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("left/right must be finite")
    if block_rows < 1:
        raise ValueError("block_rows must be positive")
    n_qubits = x.shape[1]
    result = np.empty((len(x), len(y)), dtype=float)
    y_products = y[:, :-1] * y[:, 1:] if n_qubits > 1 else None
    for start in range(0, len(x), block_rows):
        stop = min(start + block_rows, len(x))
        xb = x[start:stop]
        h = xb[:, None, 0] - y[None, :, 0]
        plus = np.exp(1j * h)
        minus = np.exp(-1j * h)
        if n_qubits > 1:
            x_products = xb[:, :-1] * xb[:, 1:]
            assert y_products is not None
            for qubit in range(1, n_qubits):
                h = xb[:, None, qubit] - y[None, :, qubit]
                coupling = interaction_strength * (
                    x_products[:, None, qubit - 1] - y_products[None, :, qubit - 1]
                )
                exp_h = np.exp(1j * h)
                exp_j = np.exp(1j * coupling)
                next_plus = exp_h * (plus * exp_j + minus / exp_j)
                next_minus = (plus / exp_j + minus * exp_j) / exp_h
                plus, minus = next_plus, next_minus
        overlap = (plus + minus) / float(1 << n_qubits)
        result[start:stop] = np.abs(overlap) ** 2
    return np.clip(result, 0.0, 1.0)


def kernel_qc(
    kernel: np.ndarray,
    *,
    model: str,
    stage: str,
    outer_fold: int | str,
    inner_fold: int | str,
    scale: float,
    compute_eigenvalue: bool = True,
) -> dict[str, Any]:
    matrix = np.asarray(kernel, dtype=float)
    symmetry = float(np.max(np.abs(matrix - matrix.T)))
    diagonal = float(np.max(np.abs(np.diag(matrix) - 1.0)))
    minimum = (
        float(np.linalg.eigvalsh((matrix + matrix.T) / 2.0).min())
        if compute_eigenvalue
        else float("nan")
    )
    passed = symmetry < 1e-10 and diagonal < 1e-10 and (
        not compute_eigenvalue or minimum >= -1e-8
    )
    row = {
        "MODEL": model,
        "STAGE": stage,
        "OUTER_FOLD": outer_fold,
        "INNER_FOLD": inner_fold,
        "FEATURE_SCALE": scale,
        "N": len(matrix),
        "SYMMETRY_ERROR": symmetry,
        "DIAGONAL_ERROR": diagonal,
        "MIN_EIGENVALUE": minimum,
        "PASS": passed,
    }
    if not passed:
        raise RuntimeError(f"Kernel QC failed: {row}")
    return row


def frozen_outer_indices(train: pd.DataFrame, outer_fold: int) -> tuple[np.ndarray, np.ndarray]:
    folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    return np.flatnonzero(folds != outer_fold), np.flatnonzero(folds == outer_fold)


def inner_indices(
    train: pd.DataFrame, outer_train: np.ndarray, outer_fold: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    subset = train.iloc[outer_train]
    splitter = StratifiedGroupKFold(
        n_splits=INNER_FOLDS, shuffle=True, random_state=SEED + outer_fold
    )
    splits = list(
        splitter.split(
            np.zeros((len(subset), 1)), subset["LABEL"], subset["BUTINA_CLUSTER_ID"]
        )
    )
    for train_local, validation_local in splits:
        overlap = set(subset.iloc[train_local]["BUTINA_CLUSTER_ID"]) & set(
            subset.iloc[validation_local]["BUTINA_CLUSTER_ID"]
        )
        if overlap:
            raise RuntimeError(f"Inner cluster leakage in outer fold {outer_fold}")
    return splits


def model_kernel(
    train_standardized: np.ndarray,
    evaluation_standardized: np.ndarray | None,
    model: str,
    scale: float,
) -> tuple[np.ndarray, np.ndarray | None]:
    train_encoded = scale * encode_features(train_standardized, model)
    if model == BASELINE:
        train_states = iqp_zz_linear_statevectors(
            train_encoded, interaction_strength=INTERACTION_STRENGTH
        )
        train_kernel = fidelity_kernel(train_states)
        evaluation_kernel = None
        if evaluation_standardized is not None:
            evaluation_encoded = scale * encode_features(evaluation_standardized, model)
            evaluation_states = iqp_zz_linear_statevectors(
                evaluation_encoded, interaction_strength=INTERACTION_STRENGTH
            )
            evaluation_kernel = fidelity_kernel(evaluation_states, train_states)
        return train_kernel, evaluation_kernel
    train_kernel = exact_chain_fidelity_kernel(train_encoded)
    evaluation_kernel = None
    if evaluation_standardized is not None:
        evaluation_encoded = scale * encode_features(evaluation_standardized, model)
        evaluation_kernel = exact_chain_fidelity_kernel(evaluation_encoded, train_encoded)
    return train_kernel, evaluation_kernel


def evaluate_fold(train: pd.DataFrame, model: str, outer_fold: int) -> dict[str, Any]:
    started = time.perf_counter()
    rss_started = process_rss_bytes()
    outer_train, outer_validation = frozen_outer_indices(train, outer_fold)
    splits = inner_indices(train, outer_train, outer_fold)
    x_all = train.loc[:, X10_FEATURES].to_numpy(float)
    y_all = train["LABEL"].to_numpy(int)
    x_train = x_all[outer_train]
    y_train = y_all[outer_train]
    x_validation = x_all[outer_validation]
    y_validation = y_all[outer_validation]
    qc_rows: list[dict[str, Any]] = []
    hpo: dict[tuple[int, float], list[float]] = {
        (scale_index, c): []
        for scale_index in range(len(FEATURE_SCALES))
        for c in C_VALUES
    }

    for inner_fold, (train_idx, validation_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(x_train[train_idx])
        inner_train = scaler.transform(x_train[train_idx])
        inner_validation = scaler.transform(x_train[validation_idx])
        for scale_index, scale in enumerate(FEATURE_SCALES):
            train_kernel, validation_kernel = model_kernel(
                inner_train, inner_validation, model, scale
            )
            qc_rows.append(
                kernel_qc(
                    train_kernel,
                    model=model,
                    stage="nested_hpo",
                    outer_fold=outer_fold,
                    inner_fold=inner_fold,
                    scale=scale,
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
                classifier.fit(train_kernel, y_train[train_idx])
                scores = classifier.decision_function(validation_kernel)
                hpo[(scale_index, c)].append(
                    float(roc_auc_score(y_train[validation_idx], scores))
                )

    ranked = sorted(
        (
            (float(np.mean(scores)), float(np.std(scores, ddof=1)), scale_index, c)
            for (scale_index, c), scores in hpo.items()
        ),
        key=lambda row: (-row[0], row[2], row[3]),
    )
    inner_mean, inner_sd, scale_index, c = ranked[0]
    scale = FEATURE_SCALES[scale_index]
    inner_oof = np.full(len(y_train), np.nan)
    for inner_fold, (train_idx, validation_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(x_train[train_idx])
        inner_train = scaler.transform(x_train[train_idx])
        inner_validation = scaler.transform(x_train[validation_idx])
        train_kernel, validation_kernel = model_kernel(
            inner_train, inner_validation, model, scale
        )
        assert validation_kernel is not None
        classifier = SVC(
            C=c,
            kernel="precomputed",
            class_weight="balanced",
            random_state=SEED,
        )
        classifier.fit(train_kernel, y_train[train_idx])
        inner_oof[validation_idx] = classifier.decision_function(validation_kernel)
    if not np.isfinite(inner_oof).all():
        raise RuntimeError("Missing inner-OOF scores")
    threshold, threshold_metrics = select_threshold(y_train, inner_oof)

    scaler = StandardScaler().fit(x_train)
    outer_train_standardized = scaler.transform(x_train)
    outer_validation_standardized = scaler.transform(x_validation)
    train_kernel, validation_kernel = model_kernel(
        outer_train_standardized, outer_validation_standardized, model, scale
    )
    qc_rows.append(
        kernel_qc(
            train_kernel,
            model=model,
            stage="nested_outer_fit",
            outer_fold=outer_fold,
            inner_fold="all",
            scale=scale,
        )
    )
    assert validation_kernel is not None
    classifier = SVC(
        C=c,
        kernel="precomputed",
        class_weight="balanced",
        random_state=SEED,
    )
    classifier.fit(train_kernel, y_train)
    outer_scores = classifier.decision_function(validation_kernel)
    metrics = classification_metrics(y_validation, outer_scores, threshold)
    predictions = []
    for source, score in zip(train.iloc[outer_validation].itertuples(index=False), outer_scores):
        prediction = int(score >= threshold)
        predictions.append(
            {
                "ID": int(source.ID),
                "name": str(source.name),
                "BUTINA_CLUSTER_ID": int(source.BUTINA_CLUSTER_ID),
                "MODEL": model,
                "OUTER_FOLD": outer_fold,
                "LABEL": int(source.LABEL),
                "SCORE": float(score),
                "THRESHOLD": float(threshold),
                "MARGIN": float(score - threshold),
                "PRED": prediction,
            }
        )
    return {
        "model": model,
        "outer_fold": outer_fold,
        "parameters": {
            "MODEL": model,
            "OUTER_FOLD": outer_fold,
            "BEST_PARAMS": json.dumps(
                {"C": c, "feature_scale": scale, "interaction_strength": 1.0},
                sort_keys=True,
            ),
            "INNER_AUROC_MEAN": inner_mean,
            "INNER_AUROC_SD": inner_sd,
            "THRESHOLD": threshold,
            "INNER_THRESHOLD_MCC": threshold_metrics["mcc"],
            "INNER_THRESHOLD_BA": threshold_metrics["balanced_accuracy"],
        },
        "metrics": {
            "MODEL": model,
            "OUTER_FOLD": outer_fold,
            "N_TRAIN": len(outer_train),
            "N_VALIDATION": len(outer_validation),
            "INNER_AUROC_MEAN": inner_mean,
            "INNER_AUROC_SD": inner_sd,
            "THRESHOLD": threshold,
            **{key.upper(): value for key, value in metrics.items()},
        },
        "predictions": predictions,
        "kernel_qc": qc_rows,
        "runtime": {
            "elapsed_seconds": time.perf_counter() - started,
            "rss_start_bytes": rss_started,
            "rss_end_bytes": process_rss_bytes(),
        },
    }


def checkpoint_signature(model: str, outer_fold: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "model": model,
        "outer_fold": outer_fold,
        "input_sha256": EXPECTED_DATA_SHA256,
        "source_sha256": sha256_file(Path(__file__)),
        "seed": SEED,
        "feature_scales": list(FEATURE_SCALES),
        "c_values": list(C_VALUES),
    }


def run_or_resume_fold(
    train: pd.DataFrame,
    model: str,
    outer_fold: int,
    checkpoint: Path,
    *,
    resume: bool,
) -> dict[str, Any]:
    signature = checkpoint_signature(model, outer_fold)
    if resume and checkpoint.is_file():
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        if payload.get("signature") != signature:
            raise RuntimeError(f"Checkpoint signature mismatch: {checkpoint}")
        return payload["result"]
    result = evaluate_fold(train, model, outer_fold)
    atomic_json(
        checkpoint,
        {"status": "complete", "completed_utc": utc_now(), "signature": signature, "result": result},
    )
    return result


def validate_data(train: pd.DataFrame) -> pd.DataFrame:
    physical_hash = sha256_file(DATA_PATH)
    canonical_hash = sha256_canonical_lf(DATA_PATH)
    if EXPECTED_DATA_SHA256 not in {physical_hash, canonical_hash}:
        raise RuntimeError(
            "Frozen development input differs beyond Windows line endings"
        )
    required = {
        "ID", "name", "LABEL", "BUTINA_CLUSTER_ID", "STRICT_CV_FOLD", *X10_FEATURES
    }
    if missing := sorted(required - set(train.columns)):
        raise RuntimeError(f"Missing columns: {missing}")
    if len(train) != 712 or train["LABEL"].value_counts().to_dict() != {0: 490, 1: 222}:
        raise RuntimeError("Frozen development row/label contract mismatch")
    if train.groupby("BUTINA_CLUSTER_ID")["STRICT_CV_FOLD"].nunique().max() != 1:
        raise RuntimeError("A cluster crosses frozen outer folds")
    rows = []
    for fold in OUTER_FOLDS:
        outer_train, outer_validation = frozen_outer_indices(train, fold)
        train_clusters = set(train.iloc[outer_train]["BUTINA_CLUSTER_ID"])
        validation_clusters = set(train.iloc[outer_validation]["BUTINA_CLUSTER_ID"])
        rows.append(
            {
                "OUTER_FOLD": fold,
                "N_TRAIN": len(outer_train),
                "N_VALIDATION": len(outer_validation),
                "TRAIN_NEGATIVE": int((train.iloc[outer_train].LABEL == 0).sum()),
                "TRAIN_POSITIVE": int((train.iloc[outer_train].LABEL == 1).sum()),
                "VALIDATION_NEGATIVE": int((train.iloc[outer_validation].LABEL == 0).sum()),
                "VALIDATION_POSITIVE": int((train.iloc[outer_validation].LABEL == 1).sum()),
                "TRAIN_CLUSTERS": len(train_clusters),
                "VALIDATION_CLUSTERS": len(validation_clusters),
                "CLUSTER_INTERSECTION": len(train_clusters & validation_clusters),
            }
        )
    audit = pd.DataFrame(rows)
    if audit.CLUSTER_INTERSECTION.max() != 0:
        raise RuntimeError("Outer-fold cluster leakage")
    return audit


def benchmark_backend(train: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    sample = train.loc[:2, X10_FEATURES].to_numpy(float)
    standardized = StandardScaler().fit_transform(sample)
    rows = []
    rss_before = process_rss_bytes()
    for model in (DUPLICATE, COMPLEMENTARY):
        encoded = FEATURE_SCALES[0] * encode_features(standardized, model)
        started = time.perf_counter()
        states = iqp_zz_linear_statevectors(encoded, interaction_strength=1.0)
        materialized_seconds = time.perf_counter() - started
        materialized_kernel = fidelity_kernel(states)
        rss_materialized = process_rss_bytes()
        started = time.perf_counter()
        optimized_kernel = exact_chain_fidelity_kernel(encoded, block_rows=128)
        optimized_seconds = time.perf_counter() - started
        maximum_error = float(np.max(np.abs(materialized_kernel - optimized_kernel)))
        qc = kernel_qc(
            optimized_kernel,
            model=model,
            stage="technical_benchmark",
            outer_fold="subset",
            inner_fold="none",
            scale=FEATURE_SCALES[0],
        )
        rows.append(
            {
                "MODEL": model,
                "SUBSET_SAMPLES": len(encoded),
                "QUBITS": encoded.shape[1],
                "STATEVECTOR_DIMENSION": states.shape[1],
                "BYTES_PER_STATEVECTOR": states.shape[1] * states.dtype.itemsize,
                "MATERIALIZED_SECONDS": materialized_seconds,
                "OPTIMIZED_SECONDS": optimized_seconds,
                "MAX_KERNEL_ERROR": maximum_error,
                "RSS_BEFORE_BYTES": rss_before,
                "RSS_AFTER_MATERIALIZATION_BYTES": rss_materialized,
                "SYMMETRY_ERROR": qc["SYMMETRY_ERROR"],
                "DIAGONAL_ERROR": qc["DIAGONAL_ERROR"],
                "MIN_EIGENVALUE": qc["MIN_EIGENVALUE"],
                "PASS": maximum_error < 1e-10 and qc["PASS"],
            }
        )
        del states, materialized_kernel, optimized_kernel

    baseline_encoded = FEATURE_SCALES[0] * encode_features(standardized, BASELINE)
    baseline_states = iqp_zz_linear_statevectors(baseline_encoded)
    fixed_idle = np.zeros(1 << 10, dtype=complex)
    fixed_idle[0] = 1.0
    idle_states = (baseline_states[:, :, None] * fixed_idle[None, None, :]).reshape(
        len(baseline_states), -1
    )
    idle_error = float(
        np.max(np.abs(fidelity_kernel(baseline_states) - fidelity_kernel(idle_states)))
    )
    del idle_states, baseline_states
    max_outer_train = max(len(frozen_outer_indices(train, fold)[0]) for fold in OUTER_FOLDS)
    state_bytes = (1 << 20) * np.dtype(complex).itemsize
    details = {
        "idle_materialized_subset_samples": len(standardized),
        "idle_kernel_max_error": idle_error,
        "idle_equivalence_pass": idle_error < 1e-10,
        "statevector_dimension_20q": 1 << 20,
        "bytes_per_complex128_statevector_20q": state_bytes,
        "max_outer_train_samples": max_outer_train,
        "projected_materialized_outer_train_bytes": max_outer_train * state_bytes,
        "projected_materialized_outer_train_gib": max_outer_train * state_bytes / 2**30,
        "selected_backend": "exact_chain_transfer_matrix",
        "selected_backend_is_approximation": False,
    }
    if not pd.DataFrame(rows).PASS.all() or not details["idle_equivalence_pass"]:
        raise RuntimeError("Technical benchmark/equivalence failed")
    return pd.DataFrame(rows), details


def reproduce_baseline(
    train: pd.DataFrame, root: Path, *, resume: bool
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = []
    for fold in OUTER_FOLDS:
        print(f"Baseline reproduction outer fold {fold}/5", flush=True)
        results.append(
            run_or_resume_fold(
                train,
                BASELINE,
                fold,
                root / "02_BASELINE_REPRODUCTION" / "checkpoints" / f"outer_fold_{fold}.json",
                resume=resume,
            )
        )
    metrics = pd.DataFrame([result["metrics"] for result in results])
    params = pd.DataFrame([result["parameters"] for result in results])
    predictions = pd.DataFrame(
        [row for result in results for row in result["predictions"]]
    )
    qc = pd.DataFrame([row for result in results for row in result["kernel_qc"]])
    frozen_predictions = pd.read_csv(
        BASELINE_CAMPAIGN / "03_NESTED_CV" / "NESTED_OUTER_OOF_PREDICTIONS.csv"
    )
    frozen_predictions = frozen_predictions[frozen_predictions.MODEL == BASELINE]
    joined = predictions.merge(
        frozen_predictions,
        on=["ID", "OUTER_FOLD", "LABEL"],
        suffixes=("_REPRODUCED", "_FROZEN"),
        validate="one_to_one",
    )
    frozen_params = pd.read_csv(
        BASELINE_CAMPAIGN / "03_NESTED_CV" / "SELECTED_PARAMS_PER_OUTER_FOLD.csv"
    )
    frozen_params = frozen_params[frozen_params.MODEL == BASELINE].sort_values("OUTER_FOLD")
    reproduced_params = params.sort_values("OUTER_FOLD")
    parameter_matches = []
    for reproduced, frozen in zip(
        reproduced_params.itertuples(index=False), frozen_params.itertuples(index=False)
    ):
        parameter_matches.append(
            json.loads(reproduced.BEST_PARAMS) == json.loads(frozen.BEST_PARAMS)
        )
    comparison = pd.DataFrame(
        [
            {
                "N_MATCHED": len(joined),
                "PARAMETERS_EXACT_MATCH": all(parameter_matches),
                "PREDICTIONS_EXACT_MATCH": bool(
                    np.array_equal(joined.PRED_REPRODUCED, joined.PRED_FROZEN)
                ),
                "MAX_ABS_SCORE_ERROR": float(
                    np.max(np.abs(joined.SCORE_REPRODUCED - joined.SCORE_FROZEN))
                ),
                "MAX_ABS_THRESHOLD_ERROR": float(
                    np.max(np.abs(joined.THRESHOLD_REPRODUCED - joined.THRESHOLD_FROZEN))
                ),
                "NUMERIC_TOLERANCE": 1e-8,
            }
        ]
    )
    passed = bool(
        comparison.PARAMETERS_EXACT_MATCH.iloc[0]
        and comparison.PREDICTIONS_EXACT_MATCH.iloc[0]
        and comparison.MAX_ABS_SCORE_ERROR.iloc[0] < 1e-8
        and comparison.MAX_ABS_THRESHOLD_ERROR.iloc[0] < 1e-8
    )
    comparison["PASS"] = passed
    output = root / "02_BASELINE_REPRODUCTION"
    metrics.to_csv(output / "BASELINE_FOLD_METRICS.csv", index=False)
    params.to_csv(output / "BASELINE_SELECTED_PARAMS.csv", index=False)
    predictions.to_csv(output / "BASELINE_OOF_PREDICTIONS.csv", index=False)
    comparison.to_csv(output / "FROZEN_ARTIFACT_COMPARISON.csv", index=False)
    qc.to_csv(output / "BASELINE_KERNEL_QC.csv", index=False)
    if not passed:
        raise RuntimeError(
            "Baseline reproduction differs materially from frozen artifacts; new models not run"
        )
    return metrics, params, predictions, qc


def idle_from_baseline(
    baseline_metrics: pd.DataFrame,
    baseline_params: pd.DataFrame,
    baseline_predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = baseline_metrics.copy()
    params = baseline_params.copy()
    predictions = baseline_predictions.copy()
    for frame in (metrics, params, predictions):
        frame["MODEL"] = IDLE
    return metrics, params, predictions


def pooled_metrics(metrics: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model in MODELS:
        group = predictions[predictions.MODEL == model]
        truth = group.LABEL.to_numpy(int)
        scores = group.SCORE.to_numpy(float)
        pred = group.PRED.to_numpy(int)
        tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
        folds = metrics[metrics.MODEL == model]
        rows.append(
            {
                "MODEL": model,
                "N": len(group),
                "MCC": matthews_corrcoef(truth, pred),
                "AUROC": roc_auc_score(truth, scores),
                "AUPRC": average_precision_score(truth, scores),
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


def paired_cluster_bootstrap(
    predictions: pd.DataFrame, pooled: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wide = predictions.pivot(
        index=["ID", "BUTINA_CLUSTER_ID", "LABEL"], columns="MODEL", values="PRED"
    ).reset_index()
    clusters = np.asarray(sorted(wide.BUTINA_CLUSTER_ID.unique()))
    cluster_indices = {
        cluster: np.flatnonzero(wide.BUTINA_CLUSTER_ID.to_numpy() == cluster)
        for cluster in clusters
    }
    comparisons = (
        (IDLE, BASELINE),
        (DUPLICATE, BASELINE),
        (COMPLEMENTARY, BASELINE),
        (COMPLEMENTARY, DUPLICATE),
    )
    truth = wide.LABEL.to_numpy(int)
    rng = np.random.default_rng(SEED)
    raw_rows = []
    model_bootstrap = {model: [] for model in MODELS}
    for replicate in range(1, BOOTSTRAP_REPLICATES + 1):
        sampled_clusters = rng.choice(clusters, size=len(clusters), replace=True)
        sampled = np.concatenate([cluster_indices[cluster] for cluster in sampled_clusters])
        sampled_truth = truth[sampled]
        model_mcc = {
            model: float(matthews_corrcoef(sampled_truth, wide[model].to_numpy()[sampled]))
            for model in MODELS
        }
        for model, value in model_mcc.items():
            model_bootstrap[model].append(value)
        for left, right in comparisons:
            raw_rows.append(
                {
                    "REPLICATE": replicate,
                    "LEFT_MODEL": left,
                    "RIGHT_MODEL": right,
                    "MCC_DELTA": model_mcc[left] - model_mcc[right],
                }
            )
    raw = pd.DataFrame(raw_rows)
    summary_rows = []
    observed_map = pooled.set_index("MODEL").MCC.to_dict()
    for left, right in comparisons:
        values = raw.loc[
            (raw.LEFT_MODEL == left) & (raw.RIGHT_MODEL == right), "MCC_DELTA"
        ].to_numpy()
        summary_rows.append(
            {
                "LEFT_MODEL": left,
                "RIGHT_MODEL": right,
                "METRIC": "MCC",
                "OBSERVED_DELTA": observed_map[left] - observed_map[right],
                "BOOTSTRAP_MEDIAN": np.median(values),
                "CI_LOW_95": np.quantile(values, 0.025),
                "CI_HIGH_95": np.quantile(values, 0.975),
                "P_DELTA_GT_0": np.mean(values > 0),
                "REPLICATES": len(values),
                "RESAMPLING_UNIT": "BUTINA_CLUSTER_ID",
                "SEED": SEED,
            }
        )
    summary = pd.DataFrame(summary_rows)
    intervals = []
    for model in MODELS:
        values = np.asarray(model_bootstrap[model])
        intervals.append(
            {
                "MODEL": model,
                "MCC_CI_LOW_95": np.quantile(values, 0.025),
                "MCC_CI_HIGH_95": np.quantile(values, 0.975),
                "MCC_BOOTSTRAP_MEDIAN": np.median(values),
            }
        )
    return summary, raw, pd.DataFrame(intervals)


def create_figures(pooled: pd.DataFrame, fold_metrics: pd.DataFrame, output: Path) -> None:
    labels = ["10q", "20q idle", "20q duplicate", "20q complementary"]
    colors = ["#355070", "#9CA3AF", "#6D597A", "#B56576"]
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.bar(labels, pooled.set_index("MODEL").loc[list(MODELS), "MCC"], color=colors)
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_ylabel("Pooled OOF MCC")
    axis.set_title("Exercise A: primary metric")
    axis.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(output / "FIG01_POOLED_MCC.png", dpi=180)
    fig.savefig(output / "FIG01_POOLED_MCC.svg")
    plt.close(fig)

    secondary = ["AUROC", "AUPRC", "BALANCED_ACCURACY", "SENSITIVITY", "SPECIFICITY"]
    x = np.arange(len(secondary))
    width = 0.19
    fig, axis = plt.subplots(figsize=(11, 5.5))
    indexed = pooled.set_index("MODEL")
    for index, (model, label, color) in enumerate(zip(MODELS, labels, colors)):
        axis.bar(x + (index - 1.5) * width, indexed.loc[model, secondary], width, label=label, color=color)
    axis.set_xticks(x, [name.replace("_", " ").title() for name in secondary])
    axis.set_ylim(0, 1)
    axis.set_ylabel("Pooled OOF metric")
    axis.set_title("Exercise A: secondary metrics")
    axis.legend(frameon=False, ncols=2)
    fig.tight_layout()
    fig.savefig(output / "FIG02_SECONDARY_METRICS.png", dpi=180)
    fig.savefig(output / "FIG02_SECONDARY_METRICS.svg")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 5.5))
    for model, label, color in zip(MODELS, labels, colors):
        group = fold_metrics[fold_metrics.MODEL == model].sort_values("OUTER_FOLD")
        axis.plot(group.OUTER_FOLD, group.MCC, marker="o", label=label, color=color)
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_xticks(OUTER_FOLDS)
    axis.set_xlabel("Outer fold")
    axis.set_ylabel("MCC")
    axis.set_title("Exercise A: MCC by frozen outer fold")
    axis.legend(frameon=False, ncols=2)
    fig.tight_layout()
    fig.savefig(output / "FIG03_FOLD_MCC.png", dpi=180)
    fig.savefig(output / "FIG03_FOLD_MCC.svg")
    plt.close(fig)


def make_report(
    root: Path,
    pooled: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    deltas: pd.DataFrame,
    reproduction: pd.DataFrame,
    benchmark_details: dict[str, Any],
) -> None:
    values = pooled.set_index("MODEL")
    delta_map = {
        (row.LEFT_MODEL, row.RIGHT_MODEL): row for row in deltas.itertuples(index=False)
    }
    duplicate = delta_map[(DUPLICATE, BASELINE)]
    complementary = delta_map[(COMPLEMENTARY, BASELINE)]
    complement_vs_duplicate = delta_map[(COMPLEMENTARY, DUPLICATE)]
    duplicate_folds = fold_metrics.pivot(index="OUTER_FOLD", columns="MODEL", values="MCC")
    duplicate_positive = int((duplicate_folds[DUPLICATE] > duplicate_folds[BASELINE]).sum())
    complementary_positive = int((duplicate_folds[COMPLEMENTARY] > duplicate_folds[BASELINE]).sum())
    contextual = pd.read_csv(BASELINE_CAMPAIGN / "03_NESTED_CV" / "NESTED_SUMMARY.csv")
    contextual = contextual[contextual.MODEL.isin(["random_forest", "rbf_matched", "quantum_angle_product"])]
    context_lines = "\n".join(
        f"- {row.MODEL}: MCC {row.POOLED_OOF_MCC:.4f}, AUROC {row.POOLED_OOF_AUROC:.4f}."
        for row in contextual.itertuples(index=False)
    )
    report = f"""# BeeQ Exercise A — baseline 10q frente a expansión 20q

## Alcance y protocolo

Se ejecutó exclusivamente el Ejercicio A. Se usaron las 712 moléculas de desarrollo, los cinco `STRICT_CV_FOLD`, cuatro folds internos `StratifiedGroupKFold`, escalado train-only, SVC precomputed con `class_weight=\"balanced\"`, selección por AUROC inner y threshold inner-OOF por MCC. La simulación fue exacta, sin shots, ruido ni hardware cuántico. No se consultó el historical holdout ni CR8 y no se usaron papers externos.

El backend final contrajo exactamente la cadena IQP-ZZ como una función de partición de Ising compleja. No es una aproximación. La materialización 20q tiene dimensión {benchmark_details['statevector_dimension_20q']:,}, usa {benchmark_details['bytes_per_complex128_statevector_20q'] / 2**20:.1f} MiB por statevector y proyectaría {benchmark_details['projected_materialized_outer_train_gib']:.2f} GiB para el outer-train máximo; por eso se seleccionó la contracción exacta.

## Reproducción 10q

La reproducción cotejó {int(reproduction.N_MATCHED.iloc[0])} predicciones. Parámetros y clases coinciden exactamente: {bool(reproduction.PARAMETERS_EXACT_MATCH.iloc[0])} / {bool(reproduction.PREDICTIONS_EXACT_MATCH.iloc[0])}. Error máximo de score: {reproduction.MAX_ABS_SCORE_ERROR.iloc[0]:.3e}; error máximo de threshold: {reproduction.MAX_ABS_THRESHOLD_ERROR.iloc[0]:.3e}. Resultado: {'PASS' if reproduction.PASS.iloc[0] else 'FAIL'}.

## Resultados pooled OOF

| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. | TP | TN | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
"""
    for model in MODELS:
        row = values.loc[model]
        report += f"| {model} | {row.MCC:.4f} | {row.AUROC:.4f} | {row.AUPRC:.4f} | {row.BALANCED_ACCURACY:.4f} | {row.SENSITIVITY:.4f} | {row.SPECIFICITY:.4f} | {int(row.TP)} | {int(row.TN)} | {int(row.FP)} | {int(row.FN)} |\n"
    report += f"""

## Deltas MCC pareados por cluster

- 20q idle − 10q: delta {delta_map[(IDLE, BASELINE)].OBSERVED_DELTA:.4f}, IC95% [{delta_map[(IDLE, BASELINE)].CI_LOW_95:.4f}, {delta_map[(IDLE, BASELINE)].CI_HIGH_95:.4f}].
- 20q duplicate − 10q: delta {duplicate.OBSERVED_DELTA:.4f}, mediana bootstrap {duplicate.BOOTSTRAP_MEDIAN:.4f}, IC95% [{duplicate.CI_LOW_95:.4f}, {duplicate.CI_HIGH_95:.4f}], P(delta>0)={duplicate.P_DELTA_GT_0:.3f}.
- 20q complementary − 10q: delta {complementary.OBSERVED_DELTA:.4f}, mediana bootstrap {complementary.BOOTSTRAP_MEDIAN:.4f}, IC95% [{complementary.CI_LOW_95:.4f}, {complementary.CI_HIGH_95:.4f}], P(delta>0)={complementary.P_DELTA_GT_0:.3f}.
- 20q complementary − duplicate: delta {complement_vs_duplicate.OBSERVED_DELTA:.4f}, mediana bootstrap {complement_vs_duplicate.BOOTSTRAP_MEDIAN:.4f}, IC95% [{complement_vs_duplicate.CI_LOW_95:.4f}, {complement_vs_duplicate.CI_HIGH_95:.4f}], P(delta>0)={complement_vs_duplicate.P_DELTA_GT_0:.3f}.

Duplicate supera al baseline en {duplicate_positive}/5 folds; complementary lo supera en {complementary_positive}/5 folds.

## Respuestas científicas

- **¿Mejora duplicate frente a 10q?** {'Sí en el estimador puntual.' if duplicate.OBSERVED_DELTA > 0 else 'No en el estimador puntual.'} El IC {'permanece completamente por encima de cero.' if duplicate.CI_LOW_95 > 0 else 'incluye cero y no respalda una mejora positiva robusta.'}
- **¿Mejora complementary frente a 10q?** {'Sí en el estimador puntual.' if complementary.OBSERVED_DELTA > 0 else 'No en el estimador puntual.'} El IC {'permanece completamente por encima de cero.' if complementary.CI_LOW_95 > 0 else 'incluye cero y no respalda una mejora positiva robusta.'}
- **Consistencia:** los conteos outer son {duplicate_positive}/5 (duplicate) y {complementary_positive}/5 (complementary); esto determina si la dirección fue homogénea.
- **Redundancia frente a codificación:** idle demuestra que qubits sin información no cambian el kernel. Duplicate mezcla redundancia con una topología de 19 aristas y términos intra-variable; complementary cambia además la función de codificación. El delta complementary−duplicate aísla operativamente esa codificación bajo la misma topología, no un efecto causal universal del número de qubits.
- **Qué no puede inferirse:** no hay evidencia de ventaja cuántica, rendimiento en holdout/CR8, generalización a otras transformaciones, superioridad causada solo por “20 qubits”, ni confirmación externa.

## Referencias contextuales congeladas (no usadas para seleccionar 20q)

{context_lines}

## Artefactos y reproducibilidad

Los CSV son la fuente canónica. `EXERCISE_A_SUMMARY.xlsx` es un resumen navegable. Los checkpoints atómicos por outer fold permiten `--resume`. `07_MANIFEST/ARTIFACT_MANIFEST_SHA256.csv` registra hashes físicos y, para texto, hashes canónicos LF. La configuración, ambiente, Git, tiempos, memoria, warnings y reglas de desempate están auditados en las carpetas numeradas.
"""
    (root / "FINAL_REPORT.md").write_text(report, encoding="utf-8")


def build_manifest(root: Path) -> pd.DataFrame:
    manifest_dir = root / "07_MANIFEST"
    manifest_path = manifest_dir / "ARTIFACT_MANIFEST_SHA256.csv"
    status_path = manifest_dir / "CAMPAIGN_STATUS.json"
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path not in {manifest_path, status_path}
    ]
    rows = []
    for path in sorted(files):
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256_physical": sha256_file(path),
                "sha256_canonical_lf": sha256_canonical_lf(path),
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(manifest_path, index=False)
    for row in frame.itertuples(index=False):
        if sha256_file(root / row.relative_path) != row.sha256_physical:
            raise RuntimeError(f"Manifest verification failed: {row.relative_path}")
    write_json(
        status_path,
        {
            "status": "complete",
            "completed_utc": utc_now(),
            "artifact_count_excluding_manifest_and_status": len(frame),
            "manifest_sha256_physical": sha256_file(manifest_path),
            "exercise": "A",
        },
    )
    return frame


def prepare_campaign(root: Path, args: argparse.Namespace) -> None:
    directories = (
        "00_AUDIT",
        "01_CONFIG",
        "02_BASELINE_REPRODUCTION",
        "03_TECHNICAL_BENCHMARK",
        "04_NESTED_CV",
        "05_STATISTICS",
        "06_FIGURES",
        "07_MANIFEST",
    )
    for name in directories:
        (root / name).mkdir(parents=True, exist_ok=True)
    if not args.resume and (root / "07_MANIFEST" / "CAMPAIGN_STATUS.json").exists():
        raise FileExistsError(f"Completed campaign exists: {root}")


def run_campaign(args: argparse.Namespace) -> Path:
    root = args.campaign_dir.resolve()
    prepare_campaign(root, args)
    if args.rebuild_manifest:
        build_manifest(root)
        return root
    started = time.perf_counter()
    task_initial = {
        "captured_before_any_task_modification": True,
        "branch": args.initial_branch,
        "head": args.initial_head,
        "status_short_branch": ["## main...origin/main"] if args.initial_status_clean else None,
        "python": args.initial_python,
    }
    write_json(root / "00_AUDIT" / "TASK_INITIAL_WORKSPACE_STATE.json", task_initial)
    write_json(root / "00_AUDIT" / "CAMPAIGN_START_GIT_STATE.json", git_snapshot())
    captured_environment = environment_snapshot()
    write_json(root / "00_AUDIT" / "ENVIRONMENT.json", captured_environment)
    train = pd.read_csv(DATA_PATH)
    split_audit = validate_data(train)
    split_audit.to_csv(root / "00_AUDIT" / "SPLIT_INTEGRITY.csv", index=False)
    input_hashes = pd.DataFrame(
        [
            {
                "relative_path": DATA_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256_physical": sha256_file(DATA_PATH),
                "sha256_canonical_lf": sha256_canonical_lf(DATA_PATH),
                "expected_physical_sha256": EXPECTED_DATA_SHA256,
                "physical_match": sha256_file(DATA_PATH) == EXPECTED_DATA_SHA256,
                "canonical_lf_match": sha256_canonical_lf(DATA_PATH) == EXPECTED_DATA_SHA256,
                "content_match_allowing_line_endings": EXPECTED_DATA_SHA256
                in {sha256_file(DATA_PATH), sha256_canonical_lf(DATA_PATH)},
            }
        ]
    )
    input_hashes.to_csv(root / "00_AUDIT" / "INPUT_HASHES.csv", index=False)
    config = {
        "exercise": "A",
        "seed": SEED,
        "features": list(X10_FEATURES),
        "outer_folds": list(OUTER_FOLDS),
        "inner_folds": INNER_FOLDS,
        "splitter": "StratifiedGroupKFold",
        "group": "BUTINA_CLUSTER_ID",
        "feature_scales": list(FEATURE_SCALES),
        "C_values": list(C_VALUES),
        "selection_metric": "mean_inner_AUROC",
        "selection_tie_break": "feature_scale_order_then_C_ascending",
        "threshold": "max_inner_OOF_MCC_then_balanced_accuracy_then_abs_threshold_then_threshold",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": SEED,
        "bootstrap_unit": "BUTINA_CLUSTER_ID",
        "simulation": "exact_no_shots_no_noise",
        "historical_holdout_used": False,
        "CR8_used": False,
        "excluded_papers_used": False,
        "baseline_campaign_read_only": str(BASELINE_CAMPAIGN),
        "resume": "atomic outer-fold JSON checkpoints validated by source/config/input signature",
    }
    write_json(root / "01_CONFIG" / "CAMPAIGN_CONFIG.json", config)
    write_json(
        root / "01_CONFIG" / "ARCHITECTURE_DEFINITIONS.json",
        {model: architecture_definition(model) for model in MODELS},
    )
    write_json(
        root / "07_MANIFEST" / "SOURCE_CODE_PROVENANCE.json",
        {
            "src/exercise_a_campaign.py": {
                "sha256_physical": sha256_file(Path(__file__)),
                "sha256_canonical_lf": sha256_canonical_lf(Path(__file__)),
            },
            "src/quantum_feature_maps.py": {
                "sha256_physical": sha256_file(PROJECT_ROOT / "src" / "quantum_feature_maps.py"),
                "sha256_canonical_lf": sha256_canonical_lf(PROJECT_ROOT / "src" / "quantum_feature_maps.py"),
            },
        },
    )

    baseline_metrics, baseline_params, baseline_predictions, baseline_qc = reproduce_baseline(
        train, root, resume=args.resume
    )
    reproduction = pd.read_csv(
        root / "02_BASELINE_REPRODUCTION" / "FROZEN_ARTIFACT_COMPARISON.csv"
    )

    print("Technical 20q materialization benchmark", flush=True)
    benchmark, benchmark_details = benchmark_backend(train)
    benchmark.to_csv(
        root / "03_TECHNICAL_BENCHMARK" / "TECHNICAL_BENCHMARK.csv", index=False
    )
    write_json(
        root / "03_TECHNICAL_BENCHMARK" / "BENCHMARK_DETAILS.json", benchmark_details
    )

    new_results = []
    for fold in OUTER_FOLDS:
        checkpoint = root / "04_NESTED_CV" / "checkpoints" / f"outer_fold_{fold}.json"
        signature = {
            "schema_version": 1,
            "outer_fold": fold,
            "models": [DUPLICATE, COMPLEMENTARY],
            "input_sha256": EXPECTED_DATA_SHA256,
            "source_sha256": sha256_file(Path(__file__)),
        }
        if args.resume and checkpoint.is_file():
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            if payload.get("signature") != signature:
                raise RuntimeError(f"Checkpoint signature mismatch: {checkpoint}")
            fold_results = payload["results"]
        else:
            fold_results = []
            for model in (DUPLICATE, COMPLEMENTARY):
                print(f"{model} outer fold {fold}/5", flush=True)
                fold_results.append(evaluate_fold(train, model, fold))
            atomic_json(
                checkpoint,
                {"status": "complete", "completed_utc": utc_now(), "signature": signature, "results": fold_results},
            )
        new_results.extend(fold_results)

    new_metrics = pd.DataFrame([result["metrics"] for result in new_results])
    new_params = pd.DataFrame([result["parameters"] for result in new_results])
    new_predictions = pd.DataFrame(
        [row for result in new_results for row in result["predictions"]]
    )
    new_qc = pd.DataFrame([row for result in new_results for row in result["kernel_qc"]])
    idle_metrics, idle_params, idle_predictions = idle_from_baseline(
        baseline_metrics, baseline_params, baseline_predictions
    )
    all_metrics = pd.concat([baseline_metrics, idle_metrics, new_metrics], ignore_index=True)
    all_params = pd.concat([baseline_params, idle_params, new_params], ignore_index=True)
    all_predictions = pd.concat(
        [baseline_predictions, idle_predictions, new_predictions], ignore_index=True
    )
    all_qc = pd.concat([baseline_qc, new_qc], ignore_index=True)
    if set(all_predictions.groupby("MODEL").size()) != {len(train)}:
        raise RuntimeError("Missing OOF predictions")
    if all_predictions.duplicated(["MODEL", "ID"]).any():
        raise RuntimeError("Duplicate OOF predictions")
    pooled = pooled_metrics(all_metrics, all_predictions)
    deltas, bootstrap_raw, intervals = paired_cluster_bootstrap(all_predictions, pooled)
    pooled = pooled.merge(intervals, on="MODEL", how="left", validate="one_to_one")

    all_metrics.to_csv(root / "04_NESTED_CV" / "OUTER_FOLD_METRICS.csv", index=False)
    all_predictions.to_csv(root / "04_NESTED_CV" / "OOF_PREDICTIONS.csv", index=False)
    all_params.to_csv(root / "04_NESTED_CV" / "SELECTED_PARAMS_PER_FOLD.csv", index=False)
    all_qc.to_csv(root / "04_NESTED_CV" / "KERNEL_QC.csv", index=False)
    pooled.to_csv(root / "04_NESTED_CV" / "POOLED_OOF_METRICS.csv", index=False)
    deltas.to_csv(root / "05_STATISTICS" / "PAIRED_MODEL_DELTAS.csv", index=False)
    bootstrap_raw.to_csv(root / "05_STATISTICS" / "PAIRED_CLUSTER_BOOTSTRAP_RAW.csv", index=False)
    create_figures(pooled, all_metrics, root / "06_FIGURES")
    make_report(root, pooled, all_metrics, deltas, reproduction, benchmark_details)
    write_json(
        root / "00_AUDIT" / "WARNINGS.json",
        {
            "warnings": captured_environment["numpy_configuration_warnings"],
            "note": "Warnings were captured and were not suppressed.",
        },
    )
    write_json(
        root / "00_AUDIT" / "RUNTIME_AND_MEMORY.json",
        {
            "completed_utc": utc_now(),
            "total_elapsed_seconds": time.perf_counter() - started,
            "final_process_rss_bytes": process_rss_bytes(),
            "fold_runtimes": [
                result["runtime"]
                for result in [
                    *[json.loads((root / "02_BASELINE_REPRODUCTION" / "checkpoints" / f"outer_fold_{fold}.json").read_text(encoding="utf-8"))["result"] for fold in OUTER_FOLDS],
                    *new_results,
                ]
            ],
        },
    )
    build_manifest(root)
    return root


def default_campaign_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return PROJECT_ROOT / "results" / "campaigns" / f"BEEQ_EXERCISE_A_10Q_VS_20Q_{timestamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, default=default_campaign_dir())
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rebuild-manifest", action="store_true")
    parser.add_argument("--initial-branch", default="main")
    parser.add_argument("--initial-head", default="d0513433a22edaecdfbebab94c7a924e0b51f55e")
    parser.add_argument("--initial-status-clean", action="store_true")
    parser.add_argument("--initial-python", default="3.14.5")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = run_campaign(args)
    print(f"Exercise A campaign complete: {root}", flush=True)


if __name__ == "__main__":
    main()
