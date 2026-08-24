"""Run the private BeeQ external validation on one complete X10 CSV."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score, pairwise_distances, roc_auc_score
from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.preprocessing import StandardScaler

from external_validation.runtime import (
    APPROVED_MODEL_ORDER,
    create_private_run_dir,
    load_approved_model_packages,
    load_baseline_provenance,
    score_side_by_side,
    validate_external_frame,
)
from src.classical_models import model_specs
from src.config import DEFAULT_DATA_DIR, X10_FEATURES
from src.data import load_bundle, sha256_file, sha256_json
from src.deployment_models import ExactIQPZZKernelSVC
from src.evaluation import METRIC_COLUMNS, binary_metrics, continuous_scores


BOOTSTRAP_REPLICATES = 2000
APPLICABILITY_QUANTILE = 0.95


def _write_json(path: Path, payload: Any) -> Path:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def _normalise_input(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Map the native BeeQ handoff columns to the public validation contract."""

    aliases = {
        "sample_id": "sample_id" if "sample_id" in frame else "ID",
        "smiles": "smiles" if "smiles" in frame else "SMILES",
        "observed_label": (
            "observed_label" if "observed_label" in frame else "LABEL"
        ),
    }
    missing = [source for source in aliases.values() if source not in frame]
    if missing:
        raise ValueError(f"external input is missing identity/label columns: {missing}")
    normalised = pd.DataFrame(
        {
            "sample_id": frame[aliases["sample_id"]].astype(str),
            "smiles": frame[aliases["smiles"]].astype(str),
            "observed_label": pd.to_numeric(
                frame[aliases["observed_label"]], errors="raise"
            ).astype(int),
            "data_source": (
                frame["data_source"].astype(str)
                if "data_source" in frame
                else pd.Series(source_name, index=frame.index, dtype=str)
            ),
        }
    )
    validate_external_frame(normalised)
    if normalised["data_source"].isna().any() or normalised["data_source"].eq("").any():
        raise ValueError("data_source values must be non-null and non-empty")
    if not normalised["observed_label"].isin([0, 1]).all():
        raise ValueError("all observed labels must be binary 0/1")
    if normalised["observed_label"].nunique() != 2:
        raise ValueError("external evaluation requires both endpoint classes")
    return normalised


def _feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(X10_FEATURES) - set(frame.columns))
    if missing:
        raise ValueError(f"external input is missing X10 descriptors: {missing}")
    features = frame.loc[:, X10_FEATURES].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("external X10 descriptors contain missing or non-finite values")
    return features


def _descriptor_audit(
    external: pd.DataFrame,
    reference: pd.DataFrame,
) -> tuple[dict[str, Any], pd.Series]:
    reference_smiles = set(reference["SMILES"].astype(str))
    overlap = external["SMILES"].astype(str).isin(reference_smiles)
    joined = external.merge(
        reference[["SMILES", "LABEL", *X10_FEATURES]],
        on="SMILES",
        how="inner",
        suffixes=("_external", "_reference"),
        validate="many_to_one",
    )
    consistency: dict[str, Any] = {}
    for feature in X10_FEATURES:
        left = joined[f"{feature}_external"].to_numpy(dtype=float)
        right = joined[f"{feature}_reference"].to_numpy(dtype=float)
        equal = np.isclose(left, right, rtol=1e-9, atol=1e-9)
        consistency[feature] = {
            "matching_shared_structures": int(equal.sum()),
            "mismatching_shared_structures": int((~equal).sum()),
            "maximum_absolute_difference": float(np.max(np.abs(left - right)))
            if len(joined)
            else 0.0,
        }

    ranges: dict[str, Any] = {}
    for feature in X10_FEATURES:
        low = float(reference[feature].min())
        high = float(reference[feature].max())
        values = external[feature].to_numpy(dtype=float)
        ranges[feature] = {
            "reference_min": low,
            "reference_max": high,
            "external_min": float(values.min()),
            "external_max": float(values.max()),
            "external_rows_outside_reference_range": int(
                ((values < low) | (values > high)).sum()
            ),
        }

    label_matches = (
        joined["LABEL_external"].astype(int)
        == joined["LABEL_reference"].astype(int)
    )
    report = {
        "exact_smiles_shared_with_reference": int(overlap.sum()),
        "exact_smiles_not_in_reference": int((~overlap).sum()),
        "shared_structure_label_matches": int(label_matches.sum()),
        "shared_structure_label_mismatches": int((~label_matches).sum()),
        "descriptor_consistency_on_shared_structures": consistency,
        "feature_range_checks": ranges,
    }
    return report, overlap


def _applicability(
    external_features: pd.DataFrame,
    reference_features: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    scaler = StandardScaler().fit(reference_features.to_numpy(dtype=float))
    reference_scaled = scaler.transform(reference_features.to_numpy(dtype=float))
    external_scaled = scaler.transform(external_features.to_numpy(dtype=float))
    reference_distances = pairwise_distances(reference_scaled)
    np.fill_diagonal(reference_distances, np.inf)
    reference_nearest = reference_distances.min(axis=1)
    threshold = float(np.quantile(reference_nearest, APPLICABILITY_QUANTILE))
    cross_distances = pairwise_distances(external_scaled, reference_scaled)
    nearest_index = cross_distances.argmin(axis=1)
    nearest_distance = cross_distances[np.arange(len(external_scaled)), nearest_index]
    frame = pd.DataFrame(
        {
            "descriptor_distance_to_reference": nearest_distance,
            "nearest_reference_row": nearest_index,
            "within_applicability_domain": nearest_distance <= threshold,
        }
    )
    report = {
        "method": "Euclidean nearest-neighbor distance after StandardScaler fit on all 893 reference X10 rows",
        "reference_leave_one_out_quantile": APPLICABILITY_QUANTILE,
        "distance_threshold": threshold,
        "within_domain_rows": int(frame["within_applicability_domain"].sum()),
        "outside_domain_rows": int((~frame["within_applicability_domain"]).sum()),
    }
    return frame, report


def _bootstrap_intervals(
    truth: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
    *,
    seed: int,
) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    negative = np.flatnonzero(truth == 0)
    positive = np.flatnonzero(truth == 1)
    sampled_negative = rng.choice(
        negative, size=(BOOTSTRAP_REPLICATES, len(negative)), replace=True
    )
    sampled_positive = rng.choice(
        positive, size=(BOOTSTRAP_REPLICATES, len(positive)), replace=True
    )
    indices = np.concatenate([sampled_negative, sampled_positive], axis=1)
    sampled_predictions = predictions[indices]
    sampled_scores = scores[indices]
    n_negative = len(negative)
    n_positive = len(positive)

    false_positive = sampled_predictions[:, :n_negative].sum(axis=1)
    true_negative = n_negative - false_positive
    true_positive = sampled_predictions[:, n_negative:].sum(axis=1)
    false_negative = n_positive - true_positive
    precision_denominator = true_positive + false_positive
    precision = np.divide(
        true_positive,
        precision_denominator,
        out=np.zeros(BOOTSTRAP_REPLICATES, dtype=float),
        where=precision_denominator != 0,
    )
    recall = true_positive / n_positive
    f1_denominator = precision + recall
    f1 = np.divide(
        2.0 * precision * recall,
        f1_denominator,
        out=np.zeros(BOOTSTRAP_REPLICATES, dtype=float),
        where=f1_denominator != 0,
    )
    mcc_denominator = np.sqrt(
        (true_positive + false_positive)
        * (true_positive + false_negative)
        * (true_negative + false_positive)
        * (true_negative + false_negative)
    )
    mcc = np.divide(
        true_positive * true_negative - false_positive * false_negative,
        mcc_denominator,
        out=np.zeros(BOOTSTRAP_REPLICATES, dtype=float),
        where=mcc_denominator != 0,
    )
    negative_scores = sampled_scores[:, :n_negative]
    positive_scores = sampled_scores[:, n_negative:]
    auc = (
        (positive_scores[:, :, None] > negative_scores[:, None, :]).mean(axis=(1, 2))
        + 0.5
        * (positive_scores[:, :, None] == negative_scores[:, None, :]).mean(axis=(1, 2))
    )
    bootstrap_truth = np.concatenate(
        [np.zeros(n_negative, dtype=int), np.ones(n_positive, dtype=int)]
    )
    auprc = np.fromiter(
        (
            average_precision_score(bootstrap_truth, sampled_scores[row])
            for row in range(BOOTSTRAP_REPLICATES)
        ),
        dtype=float,
        count=BOOTSTRAP_REPLICATES,
    )
    values = {
        "auroc": auc,
        "auprc": auprc,
        "balanced_accuracy": 0.5
        * (true_positive / n_positive + true_negative / n_negative),
        "mcc": mcc,
        "accuracy": (true_positive + true_negative) / (n_positive + n_negative),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }
    return {
        metric: (
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        )
        for metric, samples in values.items()
    }


def _metric_tables(
    predictions: pd.DataFrame,
    labels: np.ndarray,
    overlap: np.ndarray,
    within_domain: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    subsets = {
        "all_external": np.ones(len(labels), dtype=bool),
        "shared_structure": overlap,
        "novel_structure": ~overlap,
        "outside_applicability_domain": ~within_domain,
    }
    rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    for subset_index, (subset_name, mask) in enumerate(subsets.items()):
        truth = labels[mask]
        if len(truth) == 0 or set(np.unique(truth)) != {0, 1}:
            continue
        for model_index, model_name in enumerate(APPROVED_MODEL_ORDER):
            predicted = predictions.loc[mask, f"{model_name}_prediction"].to_numpy(int)
            scores = predictions.loc[mask, f"{model_name}_score"].to_numpy(float)
            metrics = binary_metrics(truth, predicted, scores)
            intervals = _bootstrap_intervals(
                truth,
                predicted,
                scores,
                seed=42 + 100 * subset_index + model_index,
            )
            row: dict[str, Any] = {
                "subset": subset_name,
                "model": model_name,
                "n_molecules": int(len(truth)),
                "n_positive": int(truth.sum()),
                "positive_prevalence": float(truth.mean()),
                **metrics,
            }
            for metric, (low, high) in intervals.items():
                row[f"{metric}_ci_low"] = low
                row[f"{metric}_ci_high"] = high
            rows.append(row)

        rng = np.random.default_rng(1042 + subset_index)
        negative = np.flatnonzero(truth == 0)
        positive = np.flatnonzero(truth == 1)
        sampled_negative = rng.choice(
            negative, size=(BOOTSTRAP_REPLICATES, len(negative)), replace=True
        )
        sampled_positive = rng.choice(
            positive, size=(BOOTSTRAP_REPLICATES, len(positive)), replace=True
        )
        sampled_indices = np.concatenate(
            [sampled_negative, sampled_positive], axis=1
        )
        auc_samples: dict[str, np.ndarray] = {}
        for model_name in APPROVED_MODEL_ORDER:
            model_scores = predictions.loc[
                mask, f"{model_name}_score"
            ].to_numpy(float)[sampled_indices]
            negative_scores = model_scores[:, : len(negative)]
            positive_scores = model_scores[:, len(negative) :]
            auc_samples[model_name] = (
                (
                    positive_scores[:, :, None]
                    > negative_scores[:, None, :]
                ).mean(axis=(1, 2))
                + 0.5
                * (
                    positive_scores[:, :, None]
                    == negative_scores[:, None, :]
                ).mean(axis=(1, 2))
            )
        for left, right in combinations(APPROVED_MODEL_ORDER, 2):
            left_scores = predictions.loc[mask, f"{left}_score"].to_numpy(float)
            right_scores = predictions.loc[mask, f"{right}_score"].to_numpy(float)
            observed = float(
                roc_auc_score(truth, left_scores)
                - roc_auc_score(truth, right_scores)
            )
            differences = auc_samples[left] - auc_samples[right]
            paired_rows.append(
                {
                    "subset": subset_name,
                    "left_model": left,
                    "right_model": right,
                    "metric": "auroc_difference",
                    "estimate": observed,
                    "ci_low": float(np.quantile(differences, 0.025)),
                    "ci_high": float(np.quantile(differences, 0.975)),
                    "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(paired_rows)


def _threshold_sensitivity(
    scored: pd.DataFrame,
    labels: np.ndarray,
    overlap: np.ndarray,
    within_domain: np.ndarray,
    packages: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    enriched = scored.copy()
    subsets = {
        "all_external": np.ones(len(labels), dtype=bool),
        "shared_structure": overlap,
        "novel_structure": ~overlap,
        "outside_applicability_domain": ~within_domain,
    }
    rows: list[dict[str, Any]] = []
    for model_name in APPROVED_MODEL_ORDER:
        policy = packages[model_name].manifest["threshold_policy"]
        score_type = policy["score_type"]
        primary_threshold = float(policy["primary_threshold"])
        sensitivity = policy["development_oof_sensitivity"]
        sensitivity_threshold = float(sensitivity["threshold"])
        scores = scored[f"{model_name}_score"].to_numpy(dtype=float)
        primary_prediction = scored[f"{model_name}_prediction"].to_numpy(dtype=int)
        thresholded_primary = (scores >= primary_threshold).astype(int)
        if not np.array_equal(primary_prediction, thresholded_primary):
            raise RuntimeError(
                f"{model_name} serialized predictions do not match its frozen threshold"
            )
        sensitivity_prediction = (scores >= sensitivity_threshold).astype(int)
        enriched[f"{model_name}_oof_youden_prediction"] = sensitivity_prediction
        for subset_name, mask in subsets.items():
            truth = labels[mask]
            if len(truth) == 0 or set(np.unique(truth)) != {0, 1}:
                continue
            for policy_name, threshold, prediction in (
                (
                    "primary_serialized_estimator",
                    primary_threshold,
                    primary_prediction,
                ),
                (
                    "development_oof_youden_sensitivity",
                    sensitivity_threshold,
                    sensitivity_prediction,
                ),
            ):
                metrics = binary_metrics(truth, prediction[mask], scores[mask])
                rows.append(
                    {
                        "subset": subset_name,
                        "model": model_name,
                        "decision_policy": policy_name,
                        "score_type": score_type,
                        "score_threshold": threshold,
                        "n_molecules": int(len(truth)),
                        "n_positive": int(truth.sum()),
                        "predicted_positive": int(prediction[mask].sum()),
                        **{
                            metric: metrics[metric]
                            for metric in (
                                "balanced_accuracy",
                                "mcc",
                                "accuracy",
                                "precision",
                                "recall",
                                "f1",
                            )
                        },
                    }
                )
    return enriched, pd.DataFrame(rows)


def _paper_artifacts(
    run_dir: Path,
    scored: pd.DataFrame,
    labels: np.ndarray,
    metrics: pd.DataFrame,
) -> list[Path]:
    display_names = {
        "random_forest": "Random forest",
        "rbf_svc": "RBF-SVC",
        "quantum_iqp_zz_linear": "Quantum IQP-ZZ",
    }
    colors = {
        "random_forest": "#2b6cb0",
        "rbf_svc": "#d97706",
        "quantum_iqp_zz_linear": "#6b46c1",
    }
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    for model_name in APPROVED_MODEL_ORDER:
        scores = scored[f"{model_name}_score"].to_numpy(dtype=float)
        fpr, tpr, _ = roc_curve(labels, scores)
        precision, recall, _ = precision_recall_curve(labels, scores)
        model_metrics = metrics[
            (metrics["subset"] == "all_external")
            & (metrics["model"] == model_name)
        ].iloc[0]
        axes[0].plot(
            fpr,
            tpr,
            color=colors[model_name],
            linewidth=2,
            label=f"{display_names[model_name]} ({model_metrics['auroc']:.3f})",
        )
        axes[1].plot(
            recall,
            precision,
            color=colors[model_name],
            linewidth=2,
            label=f"{display_names[model_name]} ({model_metrics['auprc']:.3f})",
        )
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="0.5", linewidth=1)
    axes[1].axhline(labels.mean(), linestyle="--", color="0.5", linewidth=1)
    axes[0].set(xlabel="False-positive rate", ylabel="True-positive rate", title="ROC")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall")
    for axis in axes:
        axis.set_xlim(0, 1)
        axis.set_ylim(0, 1.02)
        axis.grid(alpha=0.2)
        axis.legend(frameon=False, fontsize=8)
    figure.suptitle("BeeQ external validation (N=73)")
    figure.tight_layout()
    curves_path = run_dir / "external_roc_pr_curves.png"
    figure.savefig(curves_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    all_metrics = metrics[metrics["subset"] == "all_external"].set_index("model")
    figure, axis = plt.subplots(figsize=(7.4, 4.2))
    positions = np.arange(len(APPROVED_MODEL_ORDER))
    estimates = np.array([all_metrics.loc[name, "auroc"] for name in APPROVED_MODEL_ORDER])
    lower = np.array([all_metrics.loc[name, "auroc_ci_low"] for name in APPROVED_MODEL_ORDER])
    upper = np.array([all_metrics.loc[name, "auroc_ci_high"] for name in APPROVED_MODEL_ORDER])
    axis.errorbar(
        positions,
        estimates,
        yerr=np.vstack([estimates - lower, upper - estimates]),
        fmt="o",
        markersize=8,
        capsize=5,
        color="#1f2937",
        ecolor="#4b5563",
    )
    axis.axhline(0.5, linestyle="--", color="0.5", linewidth=1)
    axis.set_xticks(positions, [display_names[name] for name in APPROVED_MODEL_ORDER])
    axis.set_ylabel("AUROC (95% stratified bootstrap interval)")
    axis.set_ylim(0.35, 1.02)
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    overview_path = run_dir / "external_auroc_overview.png"
    figure.savefig(overview_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    table_lines = [
        r"\begin{table}[t]",
        r"\caption{External X10 validation on 73 observations.}",
        r"\label{tab:external-validation}",
        r"\centering",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Model & AUROC (95\% CI) & AUPRC & Bal. acc. & MCC \\",
        r"\midrule",
    ]
    for name in APPROVED_MODEL_ORDER:
        row = all_metrics.loc[name]
        table_lines.append(
            f"{display_names[name]} & {row['auroc']:.3f} "
            f"({row['auroc_ci_low']:.3f}--{row['auroc_ci_high']:.3f}) & "
            f"{row['auprc']:.3f} & {row['balanced_accuracy']:.3f} & "
            f"{row['mcc']:.3f} " + r"\\"
        )
    table_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    table_path = run_dir / "external_results_table.tex"
    table_path.write_text("\n".join(table_lines) + "\n", encoding="utf-8")
    return [curves_path, overview_path, table_path]


def _verify_deployment(
    packages: dict[str, Any],
    master: pd.DataFrame,
    expected_master_hash: str,
) -> dict[str, Any]:
    features = master.loc[:, X10_FEATURES].to_numpy(dtype=float)
    labels = master["LABEL"].to_numpy(dtype=int)
    report: dict[str, Any] = {}
    classical = model_specs(seed=42)
    for name in APPROVED_MODEL_ORDER:
        package = packages[name]
        manifest = package.manifest
        model = package.model
        checks = {
            "artifact_hash_valid": True,
            "feature_schema_valid": True,
            "fit_rows_manifest": manifest.get("fit_rows"),
            "fit_rows_valid": manifest.get("fit_rows") == len(master),
            "source_master_hash_valid": (
                manifest.get("source_data", {}).get("master_csv_sha256")
                == expected_master_hash
            ),
            "classes_valid": np.array_equal(np.asarray(model.classes_), [0, 1]),
            "n_features_valid": int(model.n_features_in_) == len(X10_FEATURES),
        }
        if name in classical:
            fresh = classical[name].estimator
            fresh.set_params(**manifest["preprocessing"]["settings"])
            fresh.fit(features, labels)
            checks["deterministic_refit_prediction_match"] = bool(
                np.array_equal(model.predict(features), fresh.predict(features))
            )
            checks["deterministic_refit_score_max_abs_difference"] = float(
                np.max(
                    np.abs(
                        continuous_scores(model, features)
                        - continuous_scores(fresh, features)
                    )
                )
            )
        else:
            if not isinstance(model, ExactIQPZZKernelSVC):
                raise TypeError("quantum deployment artifact has an unexpected estimator type")
            settings = manifest["preprocessing"]["settings"]
            fresh = ExactIQPZZKernelSVC(
                c=float(settings["C"]),
                feature_scale=float(settings["feature_scale"]),
                interaction_strength=float(settings["interaction_strength"]),
                class_weight="balanced",
                random_state=42,
            ).fit(features, labels)
            checks["deterministic_refit_reference_states_max_abs_difference"] = float(
                np.max(np.abs(model.reference_states_ - fresh.reference_states_))
            )
            checks["deterministic_refit_dual_coefficients_max_abs_difference"] = float(
                np.max(
                    np.abs(
                        model.classifier_.dual_coef_ - fresh.classifier_.dual_coef_
                    )
                )
            )
            checks["deterministic_refit_support_indices_match"] = bool(
                np.array_equal(
                    model.classifier_.support_, fresh.classifier_.support_
                )
            )
        checks["all_checks_passed"] = all(
            value is True or (isinstance(value, float) and value == 0.0)
            for key, value in checks.items()
            if key.endswith("valid")
            or "match" in key
            or "difference" in key
        )
        report[name] = checks
    report["all_packages_verified"] = all(
        entry["all_checks_passed"] for entry in report.values() if isinstance(entry, dict)
    )
    return report


def run(input_path: Path, data_dir: Path, output_root: Path | None = None) -> Path:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    raw = pd.read_csv(input_path)
    normalised = _normalise_input(raw, input_path.name)
    features = _feature_matrix(raw)
    bundle = load_bundle(data_dir)
    if bundle.master is None:
        raise RuntimeError("external validation requires the validated master corpus")

    descriptor_report, overlap = _descriptor_audit(raw, bundle.master)
    applicability, applicability_report = _applicability(
        features, bundle.master.loc[:, X10_FEATURES]
    )
    packages = load_approved_model_packages()
    deployment_report = _verify_deployment(
        packages,
        bundle.master,
        bundle.audit["source_files"]["master.csv"],
    )
    scored = score_side_by_side(packages, features)
    labels = normalised["observed_label"].to_numpy(dtype=int)
    scored, threshold_metrics = _threshold_sensitivity(
        scored,
        labels,
        overlap.to_numpy(dtype=bool),
        applicability["within_applicability_domain"].to_numpy(dtype=bool),
        packages,
    )

    predictions = pd.DataFrame(
        {
            "sample_id": normalised["sample_id"],
            "compound_name": raw["name"] if "name" in raw else "",
            "observed_label": normalised["observed_label"],
            "data_source": normalised["data_source"],
            "shared_structure_with_reference": overlap,
        }
    )
    predictions = pd.concat([predictions, applicability, scored], axis=1)
    metrics, paired = _metric_tables(
        scored,
        labels,
        overlap.to_numpy(dtype=bool),
        applicability["within_applicability_domain"].to_numpy(dtype=bool),
    )

    warnings: list[str] = []
    if "data_source" not in raw:
        warnings.append(
            "The input has no data_source column; the private file name was used as provenance."
        )
    if descriptor_report["exact_smiles_shared_with_reference"]:
        warnings.append(
            "Some external observations share exact SMILES with the reference corpus; "
            "results are stratified by shared versus novel structure."
        )
    mismatched = [
        name
        for name, item in descriptor_report[
            "descriptor_consistency_on_shared_structures"
        ].items()
        if item["mismatching_shared_structures"]
    ]
    if mismatched:
        warnings.append(
            "Descriptor values differ on shared structures for: " + ", ".join(mismatched)
        )
    if applicability_report["outside_domain_rows"]:
        warnings.append(
            "Some rows are outside the frozen standardized-X10 applicability boundary."
        )

    output_parent = output_root.resolve() if output_root else None
    run_dir = create_private_run_dir(output_parent) if output_parent else create_private_run_dir()
    output_paths = [
        _write_json(
            run_dir / "input_manifest.json",
            {
                "input_file": input_path.name,
                "input_sha256": sha256_file(input_path),
                "rows": len(raw),
                "columns": list(raw.columns),
                "feature_order": list(X10_FEATURES),
                "feature_schema_sha256": sha256_json(list(X10_FEATURES)),
                "observed_label_counts": {
                    str(key): int(value)
                    for key, value in normalised["observed_label"].value_counts().sort_index().items()
                },
            },
        ),
        _write_json(run_dir / "deployment_verification.json", deployment_report),
        _write_json(
            run_dir / "validation_report.json",
            {
                "status": "completed_with_warnings" if warnings else "completed",
                "rows": len(raw),
                "unique_sample_ids": int(normalised["sample_id"].nunique()),
                "unique_smiles": int(normalised["smiles"].nunique()),
                "missing_values": int(raw.isna().sum().sum()),
                "descriptor_audit": descriptor_report,
                "applicability": applicability_report,
                "warnings": warnings,
                "smiles_validation": (
                    "non-empty and unique string validation; no RDKit parsing was required "
                    "because the approved X10 matrix was supplied"
                ),
            },
        ),
    ]
    predictions_path = run_dir / "predictions.csv"
    metrics_path = run_dir / "metrics.csv"
    paired_path = run_dir / "paired_bootstrap.csv"
    threshold_path = run_dir / "threshold_sensitivity.csv"
    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    paired.to_csv(paired_path, index=False)
    threshold_metrics.to_csv(threshold_path, index=False)
    output_paths.extend(
        [predictions_path, metrics_path, paired_path, threshold_path]
    )
    output_paths.extend(_paper_artifacts(run_dir, scored, labels, metrics))
    baseline = load_baseline_provenance()
    run_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_with_warnings" if warnings else "completed",
        "input_sha256": sha256_file(input_path),
        "reference_split_sha256": bundle.audit["split_sha256"],
        "baseline_provenance": baseline,
        "models": {
            name: {
                "version": package.manifest["model_version"],
                "artifact_sha256": package.manifest["artifact_sha256"],
                "manifest_sha256": sha256_file(package.package_dir / "manifest.json"),
                "threshold_policy": package.manifest["threshold_policy"],
            }
            for name, package in packages.items()
        },
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "outputs": {
            path.name: sha256_file(path) for path in output_paths
        },
    }
    _write_json(run_dir / "manifest.json", run_manifest)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    print(run(args.input, args.data_dir, args.output_root))


if __name__ == "__main__":
    main()
