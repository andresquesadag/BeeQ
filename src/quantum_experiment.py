"""Run matched exact-statevector quantum and RBF kernel experiments."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .config import DEFAULT_RESULTS_DIR, FEATURE_SETS, OUTER_FOLDS, PROJECT_ROOT
from .data import load_bundle, sha256_file, sha256_json, write_json
from .evaluation import METRIC_COLUMNS, binary_metrics
from .kernels import (
    assert_valid_gram,
    centered_kernel_alignment,
    effective_rank,
    fidelity_kernel,
    rbf_kernel,
)
from .provenance import environment, git_state
from .quantum_feature_maps import (
    angle_product_statevectors,
    iqp_zz_linear_statevectors,
)


KERNEL_NAMES = ("rbf_matched", "quantum_angle_product", "quantum_iqp_zz_linear")


@dataclass(frozen=True)
class SelectedKernel:
    kernel: str
    kernel_params: dict[str, float]
    c: float
    mean_inner_auroc: float
    fold_scores: tuple[float, ...]


def _kernel_candidates(kernel: str, config: dict[str, Any]) -> list[dict[str, float]]:
    if kernel == "rbf_matched":
        return [{"gamma": float(value)} for value in config["rbf_gamma"]]
    if kernel == "quantum_angle_product":
        return [
            {"feature_scale": float(value)} for value in config["feature_scales"]
        ]
    if kernel == "quantum_iqp_zz_linear":
        return [
            {
                "feature_scale": float(value),
                "interaction_strength": float(config["interaction_strength"]),
            }
            for value in config["feature_scales"]
        ]
    raise ValueError(f"Unknown kernel: {kernel}")


def _kernel_matrices(
    kernel: str,
    params: dict[str, float],
    train_features: np.ndarray,
    evaluation_features: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Build a training Gram matrix and optional evaluation-to-train matrix."""

    if kernel == "rbf_matched":
        gamma = params["gamma"]
        train_kernel = rbf_kernel(train_features, gamma=gamma)
        evaluation_kernel = (
            None
            if evaluation_features is None
            else rbf_kernel(evaluation_features, train_features, gamma=gamma)
        )
    elif kernel == "quantum_angle_product":
        scale = params["feature_scale"]
        train_states = angle_product_statevectors(scale * train_features)
        train_kernel = fidelity_kernel(train_states)
        evaluation_kernel = None
        if evaluation_features is not None:
            evaluation_states = angle_product_statevectors(scale * evaluation_features)
            evaluation_kernel = fidelity_kernel(evaluation_states, train_states)
    elif kernel == "quantum_iqp_zz_linear":
        scale = params["feature_scale"]
        interaction = params["interaction_strength"]
        train_states = iqp_zz_linear_statevectors(
            scale * train_features, interaction_strength=interaction
        )
        train_kernel = fidelity_kernel(train_states)
        evaluation_kernel = None
        if evaluation_features is not None:
            evaluation_states = iqp_zz_linear_statevectors(
                scale * evaluation_features, interaction_strength=interaction
            )
            evaluation_kernel = fidelity_kernel(evaluation_states, train_states)
    else:
        raise ValueError(f"Unknown kernel: {kernel}")

    assert_valid_gram(train_kernel, atol=1e-7)
    return train_kernel, evaluation_kernel


def _select_kernel(
    raw_features: np.ndarray,
    labels: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
    kernel: str,
    config: dict[str, Any],
) -> SelectedKernel:
    """Select kernel parameters and C with train-only preprocessing per split."""

    candidates = _kernel_candidates(kernel, config)
    c_values = [float(value) for value in config["c_values"]]
    scores: dict[tuple[int, float], list[float]] = {
        (candidate_index, c): []
        for candidate_index in range(len(candidates))
        for c in c_values
    }

    for train_indices, validation_indices in splits:
        scaler = StandardScaler().fit(raw_features[train_indices])
        train_scaled = scaler.transform(raw_features[train_indices])
        validation_scaled = scaler.transform(raw_features[validation_indices])
        y_train = labels[train_indices]
        y_validation = labels[validation_indices]

        for candidate_index, params in enumerate(candidates):
            train_kernel, validation_kernel = _kernel_matrices(
                kernel, params, train_scaled, validation_scaled
            )
            assert validation_kernel is not None
            for c in c_values:
                classifier = SVC(
                    C=c,
                    kernel="precomputed",
                    class_weight="balanced",
                    random_state=int(config["seed"]),
                )
                classifier.fit(train_kernel, y_train)
                validation_score = classifier.decision_function(validation_kernel)
                scores[(candidate_index, c)].append(
                    float(roc_auc_score(y_validation, validation_score))
                )

    ranked = sorted(
        (
            (float(np.mean(fold_scores)), candidate_index, c, tuple(fold_scores))
            for (candidate_index, c), fold_scores in scores.items()
        ),
        key=lambda item: (-item[0], item[1], item[2]),
    )
    mean_score, candidate_index, c, fold_scores = ranked[0]
    return SelectedKernel(
        kernel=kernel,
        kernel_params=candidates[candidate_index],
        c=c,
        mean_inner_auroc=mean_score,
        fold_scores=fold_scores,
    )


def _diagnostics(
    kernel: np.ndarray,
    labels: np.ndarray,
) -> dict[str, float]:
    symmetric = (kernel + kernel.T) / 2.0
    eigenvalues = np.clip(np.linalg.eigvalsh(symmetric), 0.0, None)[::-1]
    total = float(eigenvalues.sum())
    signed_labels = 2.0 * labels.astype(float) - 1.0
    target_kernel = np.outer(signed_labels, signed_labels)
    return {
        "effective_rank": effective_rank(kernel),
        "top1_eigenvalue_fraction": float(eigenvalues[:1].sum() / total),
        "top10_eigenvalue_fraction": float(eigenvalues[:10].sum() / total),
        "target_alignment": centered_kernel_alignment(kernel, target_kernel),
    }


def _summarize(
    fold_metrics: pd.DataFrame, predictions: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (representation, model), group in predictions.groupby(
        ["representation", "model"], sort=False
    ):
        metrics = binary_metrics(group["y_true"], group["y_pred"], group["y_score"])
        folds = fold_metrics[
            (fold_metrics["representation"] == representation)
            & (fold_metrics["model"] == model)
        ]
        row: dict[str, Any] = {
            "evaluation_status": "development_oof",
            "representation": representation,
            "n_features": int(group["n_features"].iloc[0]),
            "model": model,
            "n_molecules": int(len(group)),
            "positive_prevalence": float(group["y_true"].mean()),
            **metrics,
        }
        for metric in METRIC_COLUMNS:
            row[f"fold_mean_{metric}"] = float(folds[metric].mean())
            row[f"fold_std_{metric}"] = float(folds[metric].std(ddof=1))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["representation", "auroc"], ascending=[True, False], kind="stable"
    ).reset_index(drop=True)


def _inner_splits(
    features: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    n_splits: int,
    seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    splitter = StratifiedGroupKFold(
        n_splits=n_splits, shuffle=True, random_state=seed
    )
    return list(splitter.split(features, labels, groups))


def run_development(
    train: pd.DataFrame,
    representations: Iterable[str],
    kernels: Iterable[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    fold_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []
    outer_folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    labels_all = train["LABEL"].astype(int).to_numpy()

    for representation in representations:
        feature_names = FEATURE_SETS[representation]
        raw_all = train.loc[:, feature_names].to_numpy(dtype=float)
        for outer_fold in OUTER_FOLDS:
            outer_train = np.flatnonzero(outer_folds != outer_fold)
            outer_validation = np.flatnonzero(outer_folds == outer_fold)
            raw_train = raw_all[outer_train]
            labels_train = labels_all[outer_train]
            groups_train = train.iloc[outer_train]["BUTINA_CLUSTER_ID"].to_numpy()
            inner = _inner_splits(
                raw_train,
                labels_train,
                groups_train,
                int(config["inner_splits"]),
                int(config["seed"]) + outer_fold,
            )
            selected_kernels: dict[str, tuple[SelectedKernel, np.ndarray]] = {}

            for kernel_name in kernels:
                started = time.perf_counter()
                selected = _select_kernel(
                    raw_train, labels_train, inner, kernel_name, config
                )
                scaler = StandardScaler().fit(raw_train)
                train_scaled = scaler.transform(raw_train)
                validation_scaled = scaler.transform(raw_all[outer_validation])
                train_kernel, validation_kernel = _kernel_matrices(
                    kernel_name,
                    selected.kernel_params,
                    train_scaled,
                    validation_scaled,
                )
                assert validation_kernel is not None
                classifier = SVC(
                    C=selected.c,
                    kernel="precomputed",
                    class_weight="balanced",
                    random_state=int(config["seed"]),
                )
                classifier.fit(train_kernel, labels_train)
                prediction = classifier.predict(validation_kernel).astype(int)
                score = classifier.decision_function(validation_kernel)
                validation_labels = labels_all[outer_validation]
                metrics = binary_metrics(validation_labels, prediction, score)
                selected_kernels[kernel_name] = (selected, train_kernel)

                fold_rows.append(
                    {
                        "evaluation_status": "development_oof",
                        "representation": representation,
                        "n_features": len(feature_names),
                        "model": kernel_name,
                        "outer_fold": outer_fold,
                        "n_train": len(outer_train),
                        "n_validation": len(outer_validation),
                        "positive_prevalence": float(validation_labels.mean()),
                        "best_inner_auroc": selected.mean_inner_auroc,
                        "elapsed_seconds": float(time.perf_counter() - started),
                        **metrics,
                    }
                )
                parameter_rows.append(
                    {
                        "evaluation_status": "development_oof",
                        "representation": representation,
                        "model": kernel_name,
                        "outer_fold": outer_fold,
                        "best_inner_auroc": selected.mean_inner_auroc,
                        "inner_fold_auroc": list(selected.fold_scores),
                        "best_params": {
                            "C": selected.c,
                            **selected.kernel_params,
                        },
                    }
                )
                diagnostic_rows.append(
                    {
                        "evaluation_status": "development_outer_train",
                        "representation": representation,
                        "model": kernel_name,
                        "outer_fold": outer_fold,
                        **_diagnostics(train_kernel, labels_train),
                    }
                )

                validation_rows = train.iloc[outer_validation][
                    ["ID", "BUTINA_CLUSTER_ID", "STRICT_CV_FOLD", "LABEL"]
                ]
                for row, predicted, scored in zip(
                    validation_rows.itertuples(index=False), prediction, score
                ):
                    prediction_rows.append(
                        {
                            "evaluation_status": "development_oof",
                            "representation": representation,
                            "n_features": len(feature_names),
                            "model": kernel_name,
                            "ID": int(row.ID),
                            "BUTINA_CLUSTER_ID": int(row.BUTINA_CLUSTER_ID),
                            "outer_fold": int(row.STRICT_CV_FOLD),
                            "y_true": int(row.LABEL),
                            "y_pred": int(predicted),
                            "y_score": float(scored),
                        }
                    )

            reference = selected_kernels.get("rbf_matched")
            if reference is not None:
                reference_kernel = reference[1]
                for kernel_name, (_, kernel_matrix) in selected_kernels.items():
                    alignment = centered_kernel_alignment(reference_kernel, kernel_matrix)
                    for diagnostic in reversed(diagnostic_rows):
                        if (
                            diagnostic["representation"] == representation
                            and diagnostic["outer_fold"] == outer_fold
                            and diagnostic["model"] == kernel_name
                        ):
                            diagnostic["alignment_with_rbf"] = alignment
                            break

    fold_frame = pd.DataFrame(fold_rows)
    prediction_frame = pd.DataFrame(prediction_rows)
    expected = len(train) * len(list(representations)) * len(list(kernels))
    if len(prediction_frame) != expected:
        raise RuntimeError(f"Expected {expected} OOF predictions; got {len(prediction_frame)}")
    if prediction_frame.duplicated(["representation", "model", "ID"]).any():
        raise RuntimeError("Each quantum model must score each development ID once")
    summary = _summarize(fold_frame, prediction_frame)
    return (
        fold_frame,
        prediction_frame,
        summary,
        pd.DataFrame(diagnostic_rows),
        parameter_rows,
    )


def run_holdout(
    train: pd.DataFrame,
    test: pd.DataFrame,
    representations: Iterable[str],
    kernels: Iterable[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    labels = train["LABEL"].astype(int).to_numpy()
    test_labels = test["LABEL"].astype(int).to_numpy()
    frozen_folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    frozen_splits = [
        (np.flatnonzero(frozen_folds != fold), np.flatnonzero(frozen_folds == fold))
        for fold in OUTER_FOLDS
    ]
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []

    for representation in representations:
        feature_names = FEATURE_SETS[representation]
        raw_train = train.loc[:, feature_names].to_numpy(dtype=float)
        raw_test = test.loc[:, feature_names].to_numpy(dtype=float)
        selected_kernels: dict[str, np.ndarray] = {}
        for kernel_name in kernels:
            started = time.perf_counter()
            selected = _select_kernel(
                raw_train, labels, frozen_splits, kernel_name, config
            )
            scaler = StandardScaler().fit(raw_train)
            train_scaled = scaler.transform(raw_train)
            test_scaled = scaler.transform(raw_test)
            train_kernel, test_kernel = _kernel_matrices(
                kernel_name, selected.kernel_params, train_scaled, test_scaled
            )
            assert test_kernel is not None
            classifier = SVC(
                C=selected.c,
                kernel="precomputed",
                class_weight="balanced",
                random_state=int(config["seed"]),
            )
            classifier.fit(train_kernel, labels)
            prediction = classifier.predict(test_kernel).astype(int)
            score = classifier.decision_function(test_kernel)
            metrics = binary_metrics(test_labels, prediction, score)
            selected_kernels[kernel_name] = train_kernel
            metric_rows.append(
                {
                    "evaluation_status": "historical_holdout",
                    "representation": representation,
                    "n_features": len(feature_names),
                    "model": kernel_name,
                    "n_molecules": len(test),
                    "positive_prevalence": float(test_labels.mean()),
                    "selection_cv_auroc": selected.mean_inner_auroc,
                    "elapsed_seconds": float(time.perf_counter() - started),
                    **metrics,
                }
            )
            parameter_rows.append(
                {
                    "evaluation_status": "historical_holdout",
                    "representation": representation,
                    "model": kernel_name,
                    "best_cv_auroc": selected.mean_inner_auroc,
                    "cv_fold_auroc": list(selected.fold_scores),
                    "best_params": {"C": selected.c, **selected.kernel_params},
                }
            )
            diagnostic_rows.append(
                {
                    "evaluation_status": "historical_full_development_train",
                    "representation": representation,
                    "model": kernel_name,
                    "outer_fold": "all",
                    **_diagnostics(train_kernel, labels),
                }
            )
            for row, predicted, scored in zip(
                test[["ID", "BUTINA_CLUSTER_ID", "LABEL"]].itertuples(index=False),
                prediction,
                score,
            ):
                prediction_rows.append(
                    {
                        "evaluation_status": "historical_holdout",
                        "representation": representation,
                        "n_features": len(feature_names),
                        "model": kernel_name,
                        "ID": int(row.ID),
                        "BUTINA_CLUSTER_ID": int(row.BUTINA_CLUSTER_ID),
                        "y_true": int(row.LABEL),
                        "y_pred": int(predicted),
                        "y_score": float(scored),
                    }
                )

        if "rbf_matched" in selected_kernels:
            reference = selected_kernels["rbf_matched"]
            for diagnostic in diagnostic_rows:
                if (
                    diagnostic["representation"] == representation
                    and diagnostic["evaluation_status"]
                    == "historical_full_development_train"
                ):
                    diagnostic["alignment_with_rbf"] = centered_kernel_alignment(
                        reference, selected_kernels[diagnostic["model"]]
                    )

    return (
        pd.DataFrame(metric_rows).sort_values(
            ["representation", "auroc"], ascending=[True, False]
        ),
        pd.DataFrame(prediction_rows),
        pd.DataFrame(diagnostic_rows),
        parameter_rows,
    )


def _load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "seed",
        "inner_splits",
        "representations",
        "kernels",
        "c_values",
        "rbf_gamma",
        "feature_scales",
        "interaction_strength",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Quantum config is missing fields: {missing}")
    return config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "configs" / "quantum.json"
    )
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--representations", nargs="+", default=None)
    parser.add_argument("--kernels", nargs="+", default=None)
    parser.add_argument("--skip-holdout", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = _load_config(args.config.resolve())
    representations = args.representations or config["representations"]
    kernels = args.kernels or config["kernels"]
    unknown_representations = sorted(set(representations) - set(FEATURE_SETS))
    unknown_kernels = sorted(set(kernels) - set(KERNEL_NAMES))
    if unknown_representations or unknown_kernels:
        raise ValueError(
            f"Unknown representations={unknown_representations}, kernels={unknown_kernels}"
        )

    source_git_state = git_state()
    source_environment = environment()
    bundle = load_bundle(args.data_dir)
    run_config = {
        **config,
        "protocol": "matched_exact_statevector_nested_v1",
        "representations": list(representations),
        "kernels": list(kernels),
        "feature_sets": {name: list(FEATURE_SETS[name]) for name in representations},
        "evaluate_historical_holdout": not args.skip_holdout,
        "split_sha256": bundle.audit["split_sha256"],
        "feature_schema_sha256": bundle.audit["feature_schema_sha256"],
    }

    fold_metrics, predictions, summary, diagnostics, best_params = run_development(
        bundle.train, representations, kernels, run_config
    )
    holdout = None
    if not args.skip_holdout:
        holdout = run_holdout(
            bundle.train, bundle.test, representations, kernels, run_config
        )

    fingerprint = sha256_json(run_config)[:10]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_root.resolve() / f"{timestamp}_quantum_{fingerprint}"
    output_dir.mkdir(parents=True, exist_ok=False)

    paths: list[Path] = []
    paths.append(write_json(output_dir / "run_config.json", run_config))
    for name, frame in [
        ("fold_metrics.csv", fold_metrics),
        ("oof_predictions.csv", predictions),
        ("summary.csv", summary),
        ("kernel_diagnostics.csv", diagnostics),
    ]:
        path = output_dir / name
        frame.to_csv(path, index=False)
        paths.append(path)
    paths.append(write_json(output_dir / "best_params.json", best_params))

    holdout_status = "not_evaluated"
    if holdout is not None:
        holdout_metrics, holdout_predictions, holdout_diagnostics, holdout_params = holdout
        for name, frame in [
            ("historical_holdout_metrics.csv", holdout_metrics),
            ("historical_holdout_predictions.csv", holdout_predictions),
            ("historical_kernel_diagnostics.csv", holdout_diagnostics),
        ]:
            path = output_dir / name
            frame.to_csv(path, index=False)
            paths.append(path)
        paths.append(
            write_json(output_dir / "historical_holdout_best_params.json", holdout_params)
        )
        holdout_status = "historical_holdout_previously_inspected"

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation": {
            "development": "nested_structure_aware_oof",
            "holdout": holdout_status,
        },
        "run_config_sha256": sha256_json(run_config),
        "dataset": bundle.audit,
        "git": source_git_state,
        "environment": source_environment,
        "outputs": {path.name: sha256_file(path) for path in paths},
    }
    write_json(output_dir / "manifest.json", manifest)
    print(
        summary[
            [
                "representation",
                "model",
                "auroc",
                "auprc",
                "balanced_accuracy",
                "mcc",
            ]
        ].to_string(index=False)
    )
    if holdout is not None:
        print("\nHistorical holdout:")
        print(
            holdout[0][
                [
                    "representation",
                    "model",
                    "auroc",
                    "auprc",
                    "balanced_accuracy",
                    "mcc",
                ]
            ].to_string(index=False)
        )
    print(f"Run directory: {output_dir}")


if __name__ == "__main__":
    main()
