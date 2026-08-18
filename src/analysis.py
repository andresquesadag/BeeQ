"""Combine completed runs into final statistics, figures, and paper tables."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import StandardScaler

from .config import PROJECT_ROOT, X10_FEATURES
from .data import load_bundle, sha256_file, sha256_json, write_json
from .provenance import environment, git_state


MODEL_LABELS = {
    "logistic": "Logistic regression",
    "random_forest": "Random forest",
    "rbf_svc": "RBF-SVC",
    "rbf_matched": "RBF kernel (matched)",
    "quantum_angle_product": "Quantum product map",
    "quantum_iqp_zz_linear": "Quantum IQP-ZZ map",
}

REPRESENTATION_LABELS = {
    "x10": "X10",
    "without_n_op": "X10 - n_OP",
    "without_mollogp": "X10 - MolLogP",
    "without_liphex": "X10 - LiPHEX",
    "without_partition_pair": "X10 - both partition descriptors",
}

COLORS = {
    "logistic": "#4C78A8",
    "random_forest": "#59A14F",
    "rbf_svc": "#E15759",
    "rbf_matched": "#E15759",
    "quantum_angle_product": "#B279A2",
    "quantum_iqp_zz_linear": "#F28E2B",
}


def _stratified_bootstrap_indices(
    labels: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    negative = np.flatnonzero(labels == 0)
    positive = np.flatnonzero(labels == 1)
    return np.concatenate(
        [
            rng.choice(negative, size=len(negative), replace=True),
            rng.choice(positive, size=len(positive), replace=True),
        ]
    )


def _metric_function(name: str) -> Callable[[np.ndarray, np.ndarray], float]:
    if name == "auroc":
        return lambda labels, scores: float(roc_auc_score(labels, scores))
    if name == "auprc":
        return lambda labels, scores: float(average_precision_score(labels, scores))
    raise ValueError(f"Unsupported bootstrap metric: {name}")


def bootstrap_metric(
    labels: np.ndarray,
    scores: np.ndarray,
    *,
    metric: str,
    replicates: int,
    confidence_level: float,
    seed: int,
) -> tuple[float, float]:
    function = _metric_function(metric)
    rng = np.random.default_rng(seed)
    estimates = np.empty(replicates, dtype=float)
    for index in range(replicates):
        sampled = _stratified_bootstrap_indices(labels, rng)
        estimates[index] = function(labels[sampled], scores[sampled])
    alpha = (1.0 - confidence_level) / 2.0
    low, high = np.quantile(estimates, [alpha, 1.0 - alpha])
    return float(low), float(high)


def paired_bootstrap_delta(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    metric: str,
    replicates: int,
    confidence_level: float,
    seed: int,
) -> dict[str, float]:
    merged = left[["ID", "y_true", "y_score"]].merge(
        right[["ID", "y_true", "y_score"]],
        on="ID",
        suffixes=("_left", "_right"),
        validate="one_to_one",
    )
    if not np.array_equal(merged["y_true_left"], merged["y_true_right"]):
        raise ValueError("Paired predictions disagree on labels")
    labels = merged["y_true_left"].to_numpy(dtype=int)
    left_scores = merged["y_score_left"].to_numpy(dtype=float)
    right_scores = merged["y_score_right"].to_numpy(dtype=float)
    function = _metric_function(metric)
    observed = function(labels, left_scores) - function(labels, right_scores)
    rng = np.random.default_rng(seed)
    deltas = np.empty(replicates, dtype=float)
    for index in range(replicates):
        sampled = _stratified_bootstrap_indices(labels, rng)
        deltas[index] = function(labels[sampled], left_scores[sampled]) - function(
            labels[sampled], right_scores[sampled]
        )
    alpha = (1.0 - confidence_level) / 2.0
    low, high = np.quantile(deltas, [alpha, 1.0 - alpha])
    return {
        "delta": float(observed),
        "ci_low": float(low),
        "ci_high": float(high),
        "bootstrap_probability_delta_gt_zero": float(np.mean(deltas > 0)),
        "n_molecules": int(len(merged)),
    }


def _load_run(run_dir: Path, source: str) -> dict[str, Any]:
    required = ["manifest.json", "summary.csv", "oof_predictions.csv"]
    missing = [name for name in required if not (run_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"{run_dir} is missing {missing}")
    result: dict[str, Any] = {
        "source": source,
        "run_dir": run_dir,
        "manifest": json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")),
        "development_metrics": pd.read_csv(run_dir / "summary.csv"),
        "development_predictions": pd.read_csv(run_dir / "oof_predictions.csv"),
        "holdout_metrics": pd.read_csv(run_dir / "historical_holdout_metrics.csv"),
        "holdout_predictions": pd.read_csv(
            run_dir / "historical_holdout_predictions.csv"
        ),
    }
    diagnostics = run_dir / "kernel_diagnostics.csv"
    historical_diagnostics = run_dir / "historical_kernel_diagnostics.csv"
    result["diagnostics"] = (
        pd.read_csv(diagnostics) if diagnostics.is_file() else pd.DataFrame()
    )
    result["historical_diagnostics"] = (
        pd.read_csv(historical_diagnostics)
        if historical_diagnostics.is_file()
        else pd.DataFrame()
    )
    return result


def _all_metrics(
    runs: list[dict[str, Any]], config: dict[str, Any]
) -> pd.DataFrame:
    rows = []
    seed = int(config["seed"])
    for source_index, run in enumerate(runs):
        for status, metrics, predictions in [
            (
                "development_oof",
                run["development_metrics"],
                run["development_predictions"],
            ),
            (
                "historical_holdout",
                run["holdout_metrics"],
                run["holdout_predictions"],
            ),
        ]:
            for _, metric_row in metrics.iterrows():
                model = metric_row["model"]
                representation = metric_row["representation"]
                group = predictions[
                    (predictions["model"] == model)
                    & (predictions["representation"] == representation)
                ]
                auroc_low, auroc_high = bootstrap_metric(
                    group["y_true"].to_numpy(dtype=int),
                    group["y_score"].to_numpy(dtype=float),
                    metric="auroc",
                    replicates=int(config["bootstrap_replicates"]),
                    confidence_level=float(config["confidence_level"]),
                    seed=seed + source_index * 1000 + len(rows),
                )
                auprc_low, auprc_high = bootstrap_metric(
                    group["y_true"].to_numpy(dtype=int),
                    group["y_score"].to_numpy(dtype=float),
                    metric="auprc",
                    replicates=int(config["bootstrap_replicates"]),
                    confidence_level=float(config["confidence_level"]),
                    seed=seed + 50000 + source_index * 1000 + len(rows),
                )
                row = metric_row.to_dict()
                row.update(
                    {
                        "source_run": run["source"],
                        "evaluation_status": status,
                        "model_label": MODEL_LABELS.get(model, model),
                        "representation_label": REPRESENTATION_LABELS.get(
                            representation, representation
                        ),
                        "auroc_ci_low": auroc_low,
                        "auroc_ci_high": auroc_high,
                        "auprc_ci_low": auprc_low,
                        "auprc_ci_high": auprc_high,
                    }
                )
                rows.append(row)
    return pd.DataFrame(rows)


def _comparison_rows(
    runs: list[dict[str, Any]], config: dict[str, Any]
) -> pd.DataFrame:
    comparisons: list[dict[str, Any]] = []
    counter = 0

    def compare(
        run: dict[str, Any],
        status: str,
        predictions: pd.DataFrame,
        left_model: str,
        left_representation: str,
        right_model: str,
        right_representation: str,
        family: str,
        label: str,
    ) -> None:
        nonlocal counter
        left = predictions[
            (predictions["model"] == left_model)
            & (predictions["representation"] == left_representation)
        ]
        right = predictions[
            (predictions["model"] == right_model)
            & (predictions["representation"] == right_representation)
        ]
        if left.empty or right.empty:
            return
        for metric in ["auroc", "auprc"]:
            result = paired_bootstrap_delta(
                left,
                right,
                metric=metric,
                replicates=int(config["bootstrap_replicates"]),
                confidence_level=float(config["confidence_level"]),
                seed=int(config["seed"]) + counter * 97,
            )
            comparisons.append(
                {
                    "family": family,
                    "comparison": label,
                    "source_run": run["source"],
                    "evaluation_status": status,
                    "metric": metric,
                    "left_model": left_model,
                    "left_representation": left_representation,
                    "right_model": right_model,
                    "right_representation": right_representation,
                    **result,
                }
            )
            counter += 1

    for run in runs:
        for status, predictions in [
            ("development_oof", run["development_predictions"]),
            ("historical_holdout", run["holdout_predictions"]),
        ]:
            models = predictions["model"].unique().tolist()
            representations = set(predictions["representation"])
            if run["source"] == "classical":
                for model in models:
                    for ablation in [
                        "without_n_op",
                        "without_mollogp",
                        "without_liphex",
                        "without_partition_pair",
                    ]:
                        if ablation in representations:
                            compare(
                                run,
                                status,
                                predictions,
                                model,
                                "x10",
                                model,
                                ablation,
                                "descriptor_ablation",
                                f"X10 vs {REPRESENTATION_LABELS[ablation]} ({MODEL_LABELS[model]})",
                            )
            else:
                for model in models:
                    compare(
                        run,
                        status,
                        predictions,
                        model,
                        "x10",
                        model,
                        "without_n_op",
                        "structural_ablation",
                        f"X10 vs X10 - n_OP ({MODEL_LABELS[model]})",
                    )
                for quantum_model in [
                    "quantum_angle_product",
                    "quantum_iqp_zz_linear",
                ]:
                    compare(
                        run,
                        status,
                        predictions,
                        quantum_model,
                        "x10",
                        "rbf_matched",
                        "x10",
                        "quantum_vs_classical",
                        f"{MODEL_LABELS[quantum_model]} vs matched RBF",
                    )
    return pd.DataFrame(comparisons)


def _disagreement(runs: list[dict[str, Any]]) -> pd.DataFrame:
    quantum = next(run for run in runs if run["source"] == "quantum")
    rows = []
    for status, predictions in [
        ("development_oof", quantum["development_predictions"]),
        ("historical_holdout", quantum["holdout_predictions"]),
    ]:
        reference = predictions[
            (predictions["representation"] == "x10")
            & (predictions["model"] == "rbf_matched")
        ][["ID", "y_pred", "y_score"]]
        for model in ["quantum_angle_product", "quantum_iqp_zz_linear"]:
            candidate = predictions[
                (predictions["representation"] == "x10")
                & (predictions["model"] == model)
            ][["ID", "y_pred", "y_score"]]
            merged = reference.merge(
                candidate, on="ID", suffixes=("_rbf", "_quantum"), validate="one_to_one"
            )
            correlation = spearmanr(
                merged["y_score_rbf"], merged["y_score_quantum"]
            ).statistic
            rows.append(
                {
                    "evaluation_status": status,
                    "model": model,
                    "n_molecules": len(merged),
                    "prediction_disagreement_rate": float(
                        (merged["y_pred_rbf"] != merged["y_pred_quantum"]).mean()
                    ),
                    "score_spearman_with_rbf": float(correlation),
                }
            )
    return pd.DataFrame(rows)


def _diagnostic_summary(quantum_run: dict[str, Any]) -> pd.DataFrame:
    development = quantum_run["diagnostics"].copy()
    grouped = (
        development.groupby(["representation", "model"], as_index=False)
        .agg(
            effective_rank_mean=("effective_rank", "mean"),
            effective_rank_std=("effective_rank", "std"),
            target_alignment_mean=("target_alignment", "mean"),
            target_alignment_std=("target_alignment", "std"),
            alignment_with_rbf_mean=("alignment_with_rbf", "mean"),
            alignment_with_rbf_std=("alignment_with_rbf", "std"),
        )
    )
    grouped.insert(0, "evaluation_status", "development_outer_train")
    historical = quantum_run["historical_diagnostics"].copy()
    historical = historical.rename(
        columns={
            "effective_rank": "effective_rank_mean",
            "target_alignment": "target_alignment_mean",
            "alignment_with_rbf": "alignment_with_rbf_mean",
        }
    )
    for column in [
        "effective_rank_std",
        "target_alignment_std",
        "alignment_with_rbf_std",
    ]:
        historical[column] = np.nan
    return pd.concat(
        [
            grouped,
            historical[
                [
                    "evaluation_status",
                    "representation",
                    "model",
                    "effective_rank_mean",
                    "effective_rank_std",
                    "target_alignment_mean",
                    "target_alignment_std",
                    "alignment_with_rbf_mean",
                    "alignment_with_rbf_std",
                ]
            ],
        ],
        ignore_index=True,
    )


def _error_strata(
    bundle: Any, runs: list[dict[str, Any]]
) -> pd.DataFrame:
    scaler = StandardScaler().fit(bundle.train.loc[:, X10_FEATURES].to_numpy(float))
    train_scaled = scaler.transform(bundle.train.loc[:, X10_FEATURES].to_numpy(float))
    test_scaled = scaler.transform(bundle.test.loc[:, X10_FEATURES].to_numpy(float))
    squared = (
        np.sum(test_scaled**2, axis=1)[:, None]
        + np.sum(train_scaled**2, axis=1)[None, :]
        - 2.0 * test_scaled @ train_scaled.T
    )
    nearest_distance = np.sqrt(np.clip(squared.min(axis=1), 0.0, None))
    metadata = bundle.test[["ID", "LABEL", "n_OP"]].copy()
    metadata["descriptor_distance_to_train"] = nearest_distance
    metadata["distance_tertile"] = pd.qcut(
        metadata["descriptor_distance_to_train"],
        q=3,
        labels=["near", "middle", "far"],
    ).astype(str)
    metadata["n_op_group"] = np.where(metadata["n_OP"] > 0, "n_OP > 0", "n_OP = 0")

    selected = []
    for run in runs:
        predictions = run["holdout_predictions"]
        models = (
            ["logistic", "random_forest"]
            if run["source"] == "classical"
            else ["rbf_matched", "quantum_angle_product", "quantum_iqp_zz_linear"]
        )
        for model in models:
            group = predictions[
                (predictions["representation"] == "x10")
                & (predictions["model"] == model)
            ].copy()
            group["source_run"] = run["source"]
            selected.append(group)
    predictions = pd.concat(selected, ignore_index=True).merge(
        metadata, on="ID", suffixes=("", "_metadata"), validate="many_to_one"
    )
    predictions["error"] = (predictions["y_pred"] != predictions["y_true"]).astype(int)

    rows = []
    for dimension in ["distance_tertile", "n_op_group"]:
        for (source, model, stratum), group in predictions.groupby(
            ["source_run", "model", dimension], observed=True
        ):
            auroc = (
                float(roc_auc_score(group["y_true"], group["y_score"]))
                if group["y_true"].nunique() == 2
                else np.nan
            )
            rows.append(
                {
                    "source_run": source,
                    "model": model,
                    "dimension": dimension,
                    "stratum": stratum,
                    "n_molecules": len(group),
                    "positive_prevalence": float(group["y_true"].mean()),
                    "error_rate": float(group["error"].mean()),
                    "auroc": auroc,
                }
            )
    return pd.DataFrame(rows)


def _plot_overview(metrics: pd.DataFrame, output: Path) -> None:
    selected = metrics[
        (metrics["representation"] == "x10")
        & (metrics["model"].isin(
            [
                "logistic",
                "random_forest",
                "rbf_matched",
                "quantum_angle_product",
                "quantum_iqp_zz_linear",
            ]
        ))
    ].copy()
    models = selected["model"].drop_duplicates().tolist()
    x = np.arange(len(models))
    width = 0.36
    fig, axis = plt.subplots(figsize=(9.2, 4.8))
    for offset, (status, label) in enumerate(
        [("development_oof", "Development OOF"), ("historical_holdout", "Historical holdout")]
    ):
        values = []
        lower = []
        upper = []
        for model in models:
            row = selected[
                (selected["model"] == model)
                & (selected["evaluation_status"] == status)
            ].iloc[0]
            values.append(row["auroc"])
            lower.append(row["auroc"] - row["auroc_ci_low"])
            upper.append(row["auroc_ci_high"] - row["auroc"])
        positions = x + (offset - 0.5) * width
        axis.bar(
            positions,
            values,
            width,
            label=label,
            color="#D9A62E" if offset == 0 else "#4C78A8",
            edgecolor="#333333",
            yerr=np.array([lower, upper]),
            capsize=3,
        )
    axis.axhline(0.5, color="#777777", linestyle="--", linewidth=1)
    axis.set_xticks(x, [MODEL_LABELS[model] for model in models], rotation=18, ha="right")
    axis.set_ylabel("AUROC (95% stratified bootstrap CI)")
    axis.set_ylim(0.45, 0.85)
    axis.legend(frameon=False, ncol=2)
    axis.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _plot_ablation(comparisons: pd.DataFrame, output: Path) -> None:
    selected = comparisons[
        (comparisons["family"] == "descriptor_ablation")
        & (comparisons["evaluation_status"] == "development_oof")
        & (comparisons["metric"] == "auroc")
    ].copy()
    labels = []
    for row in selected.itertuples(index=False):
        ablation = REPRESENTATION_LABELS[row.right_representation].replace("X10 - ", "")
        labels.append(f"{MODEL_LABELS[row.left_model]}: remove {ablation}")
    selected["label"] = labels
    selected = selected.sort_values("delta")
    xerr = np.vstack(
        [selected["delta"] - selected["ci_low"], selected["ci_high"] - selected["delta"]]
    )
    fig, axis = plt.subplots(figsize=(9.2, 6.3))
    axis.errorbar(
        selected["delta"],
        np.arange(len(selected)),
        xerr=xerr,
        fmt="o",
        color="#463A18",
        ecolor="#D9A62E",
        capsize=3,
    )
    axis.axvline(0.0, color="#777777", linestyle="--", linewidth=1)
    axis.set_yticks(np.arange(len(selected)), selected["label"])
    axis.set_xlabel("AUROC difference: X10 - ablated representation")
    axis.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _plot_curves(runs: list[dict[str, Any]], output: Path) -> None:
    selected_frames = []
    for run in runs:
        models = (
            ["logistic", "random_forest"]
            if run["source"] == "classical"
            else ["rbf_matched", "quantum_iqp_zz_linear"]
        )
        for status, frame in [
            ("Development OOF", run["development_predictions"]),
            ("Historical holdout", run["holdout_predictions"]),
        ]:
            group = frame[
                (frame["representation"] == "x10") & (frame["model"].isin(models))
            ].copy()
            group["panel_status"] = status
            selected_frames.append(group)
    predictions = pd.concat(selected_frames, ignore_index=True)
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 8.0))
    for row_index, status in enumerate(["Development OOF", "Historical holdout"]):
        panel = predictions[predictions["panel_status"] == status]
        for model, group in panel.groupby("model", sort=False):
            fpr, tpr, _ = roc_curve(group["y_true"], group["y_score"])
            precision, recall, _ = precision_recall_curve(group["y_true"], group["y_score"])
            axes[row_index, 0].plot(
                fpr,
                tpr,
                label=f"{MODEL_LABELS[model]} ({roc_auc_score(group['y_true'], group['y_score']):.3f})",
                color=COLORS[model],
                linewidth=1.8,
            )
            axes[row_index, 1].plot(
                recall,
                precision,
                label=f"{MODEL_LABELS[model]} ({average_precision_score(group['y_true'], group['y_score']):.3f})",
                color=COLORS[model],
                linewidth=1.8,
            )
        axes[row_index, 0].plot([0, 1], [0, 1], "--", color="#999999", linewidth=1)
        prevalence = panel.drop_duplicates("ID")["y_true"].mean()
        axes[row_index, 1].axhline(prevalence, linestyle="--", color="#999999", linewidth=1)
        axes[row_index, 0].set_title(f"{status}: ROC")
        axes[row_index, 1].set_title(f"{status}: precision-recall")
        axes[row_index, 0].set_xlabel("False positive rate")
        axes[row_index, 0].set_ylabel("True positive rate")
        axes[row_index, 1].set_xlabel("Recall")
        axes[row_index, 1].set_ylabel("Precision")
        for axis in axes[row_index]:
            axis.set_xlim(0, 1)
            axis.set_ylim(0, 1)
            axis.grid(alpha=0.18)
            axis.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _plot_kernel_geometry(diagnostics: pd.DataFrame, output: Path) -> None:
    selected = diagnostics[
        (diagnostics["representation"] == "x10")
        & (diagnostics["evaluation_status"] == "development_outer_train")
    ].copy()
    models = selected["model"].tolist()
    labels = [MODEL_LABELS[model] for model in models]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    axes[0].bar(
        labels,
        selected["effective_rank_mean"],
        yerr=selected["effective_rank_std"],
        color=[COLORS[model] for model in models],
        edgecolor="#333333",
        capsize=3,
    )
    axes[0].set_ylabel("Effective rank")
    axes[0].set_title("Kernel spectral complexity")
    axes[1].bar(
        labels,
        selected["alignment_with_rbf_mean"],
        yerr=selected["alignment_with_rbf_std"],
        color=[COLORS[model] for model in models],
        edgecolor="#333333",
        capsize=3,
    )
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel("Centered alignment with RBF")
    axes[1].set_title("Kernel geometry similarity")
    for axis in axes:
        axis.tick_params(axis="x", rotation=18)
        axis.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _plot_error_strata(strata: pd.DataFrame, output: Path) -> None:
    selected = strata[strata["dimension"] == "distance_tertile"].copy()
    order = ["near", "middle", "far"]
    models = selected["model"].drop_duplicates().tolist()
    x = np.arange(len(order))
    width = 0.15
    fig, axis = plt.subplots(figsize=(8.8, 4.5))
    for index, model in enumerate(models):
        group = selected[selected["model"] == model].set_index("stratum").reindex(order)
        positions = x + (index - (len(models) - 1) / 2) * width
        axis.bar(
            positions,
            group["error_rate"],
            width,
            label=MODEL_LABELS[model],
            color=COLORS[model],
            edgecolor="#333333",
        )
    axis.set_xticks(x, ["Near", "Middle", "Far"])
    axis.set_xlabel("Nearest standardized X10 distance to development")
    axis.set_ylabel("Historical holdout error rate")
    axis.set_ylim(0, 0.65)
    axis.legend(frameon=False, fontsize=8, ncol=2)
    axis.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _plot_correlations(bundle: Any, output: Path) -> None:
    correlation = bundle.train.loc[:, X10_FEATURES].corr(method="spearman")
    fig, axis = plt.subplots(figsize=(7.6, 6.8))
    image = axis.imshow(correlation, vmin=-1, vmax=1, cmap="RdBu_r")
    labels = [
        "MolLogP",
        "MolWt",
        "TPSA",
        "H donors",
        "Rotatable",
        "Aromatic",
        "Halogen",
        "n_OP",
        "LiPHEX",
        "Polar SASA",
    ]
    axis.set_xticks(np.arange(len(labels)), labels, rotation=50, ha="right")
    axis.set_yticks(np.arange(len(labels)), labels)
    fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04, label="Spearman correlation")
    axis.set_title("Development X10 descriptor correlations")
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _paper_tables(
    bundle: Any,
    metrics: pd.DataFrame,
    comparisons: pd.DataFrame,
    diagnostics: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    dataset_text = rf"""\begin{{table}}[t]
\caption{{Curated molecular domain and fixed evaluation protocol.}}
\label{{tab:data}}
\centering
\begin{{tabular}}{{lr}}
\toprule
Property & Value \\
\midrule
All curated molecules & {len(bundle.train) + len(bundle.test)} \\
Development molecules & {len(bundle.train)} \\
Historical holdout molecules & {len(bundle.test)} \\
Development toxic / non-toxic & {int(bundle.train['LABEL'].sum())} / {int((1-bundle.train['LABEL']).sum())} \\
Holdout toxic / non-toxic & {int(bundle.test['LABEL'].sum())} / {int((1-bundle.test['LABEL']).sum())} \\
Development / holdout clusters & {bundle.train['BUTINA_CLUSTER_ID'].nunique()} / {bundle.test['BUTINA_CLUSTER_ID'].nunique()} \\
Frozen development folds & 5 \\
Molecular descriptors & 10 \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    path = output_dir / "dataset_table.tex"
    path.write_text(dataset_text, encoding="utf-8")
    outputs.append(path)

    selected = metrics[
        (metrics["representation"] == "x10")
        & (metrics["model"].isin(
            [
                "logistic",
                "random_forest",
                "rbf_matched",
                "quantum_angle_product",
                "quantum_iqp_zz_linear",
            ]
        ))
    ]
    lines = [
        r"\begin{table*}[t]",
        r"\caption{X10 predictive performance. Parentheses show 95\% stratified bootstrap intervals for AUROC.}",
        r"\label{tab:main-results}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{llcccc}",
        r"\toprule",
        r"Evaluation & Model & AUROC (95\% CI) & AUPRC & Balanced Acc. & MCC \\",
        r"\midrule",
    ]
    for status, status_label in [
        ("development_oof", "Development OOF"),
        ("historical_holdout", "Historical holdout"),
    ]:
        panel = selected[selected["evaluation_status"] == status]
        for _, row in panel.iterrows():
            lines.append(
                f"{status_label} & {MODEL_LABELS[row['model']]} & "
                f"{row['auroc']:.3f} ({row['auroc_ci_low']:.3f}--{row['auroc_ci_high']:.3f}) & "
                f"{row['auprc']:.3f} & {row['balanced_accuracy']:.3f} & {row['mcc']:.3f} \\\\"
            )
        if status == "development_oof":
            lines.append(r"\midrule")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""])
    path = output_dir / "main_results_table.tex"
    path.write_text("\n".join(lines), encoding="utf-8")
    outputs.append(path)

    ablation = comparisons[
        (comparisons["family"] == "descriptor_ablation")
        & (comparisons["evaluation_status"] == "development_oof")
        & (comparisons["metric"] == "auroc")
        & (comparisons["left_model"].isin(["logistic", "rbf_svc", "random_forest"]))
    ]
    lines = [
        r"\begin{table}[t]",
        r"\caption{Development AUROC change $\Delta=$ X10 minus ablated representation.}",
        r"\label{tab:ablation}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Removed & LR & RBF & RF \\",
        r"\midrule",
    ]
    for representation, label in [
        ("without_n_op", r"$n_{OP}$"),
        ("without_mollogp", "MolLogP"),
        ("without_liphex", "LiPHEX"),
        ("without_partition_pair", "Both partition"),
    ]:
        values = []
        for model in ["logistic", "rbf_svc", "random_forest"]:
            row = ablation[
                (ablation["right_representation"] == representation)
                & (ablation["left_model"] == model)
            ].iloc[0]
            values.append(f"{row['delta']:+.3f}")
        lines.append(f"{label} & {values[0]} & {values[1]} & {values[2]} \\\\ ")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path = output_dir / "ablation_table.tex"
    path.write_text("\n".join(lines), encoding="utf-8")
    outputs.append(path)

    geometry = diagnostics[
        (diagnostics["representation"] == "x10")
        & (diagnostics["evaluation_status"] == "development_outer_train")
    ]
    lines = [
        r"\begin{table}[t]",
        r"\caption{X10 kernel geometry across outer-training folds (mean $\pm$ SD).}",
        r"\label{tab:geometry}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Kernel & Eff. rank & Target align. & RBF align. \\",
        r"\midrule",
    ]
    for _, row in geometry.iterrows():
        short_label = {
            "quantum_angle_product": "Product",
            "quantum_iqp_zz_linear": "IQP-ZZ",
            "rbf_matched": "RBF",
        }[row["model"]]
        lines.append(
            f"{short_label} & "
            f"{row['effective_rank_mean']:.2f}$\\pm${row['effective_rank_std']:.2f} & "
            f"{row['target_alignment_mean']:.3f}$\\pm${row['target_alignment_std']:.3f} & "
            f"{row['alignment_with_rbf_mean']:.3f}$\\pm${row['alignment_with_rbf_std']:.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path = output_dir / "kernel_geometry_table.tex"
    path.write_text("\n".join(lines), encoding="utf-8")
    outputs.append(path)
    return outputs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classical-run", type=Path, required=True)
    parser.add_argument("--quantum-run", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "configs" / "analysis.json"
    )
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "results" / "final"
    )
    parser.add_argument("--data-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source_git_state = git_state()
    source_environment = environment()
    bundle = load_bundle(args.data_dir)
    classical = _load_run(args.classical_run.resolve(), "classical")
    quantum = _load_run(args.quantum_run.resolve(), "quantum")
    runs = [classical, quantum]
    split_hashes = {run["manifest"]["dataset"]["split_sha256"] for run in runs}
    if split_hashes != {bundle.audit["split_sha256"]}:
        raise ValueError("Input runs do not share the current canonical split hash")

    analysis_config = {
        **config,
        "protocol": "final_analysis_v1",
        "classical_run": classical["run_dir"].name,
        "quantum_run": quantum["run_dir"].name,
        "split_sha256": bundle.audit["split_sha256"],
    }
    fingerprint = sha256_json(analysis_config)[:10]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_root.resolve() / f"{timestamp}_{fingerprint}"
    output_dir.mkdir(parents=True, exist_ok=False)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir()

    metrics = _all_metrics(runs, config)
    comparisons = _comparison_rows(runs, config)
    disagreement = _disagreement(runs)
    diagnostics = _diagnostic_summary(quantum)
    strata = _error_strata(bundle, runs)
    correlation = float(
        bundle.train[["MolLogP", "LiPHEX_prediction"]]
        .corr(method="spearman")
        .iloc[0, 1]
    )

    outputs: list[Path] = []
    for name, frame in [
        ("all_metrics.csv", metrics),
        ("paired_bootstrap.csv", comparisons),
        ("prediction_disagreement.csv", disagreement),
        ("kernel_diagnostics_summary.csv", diagnostics),
        ("holdout_error_strata.csv", strata),
    ]:
        path = output_dir / name
        frame.to_csv(path, index=False)
        outputs.append(path)

    dataset_summary = {
        "development_rows": len(bundle.train),
        "historical_holdout_rows": len(bundle.test),
        "development_positive_prevalence": float(bundle.train["LABEL"].mean()),
        "historical_holdout_positive_prevalence": float(bundle.test["LABEL"].mean()),
        "development_clusters": int(bundle.train["BUTINA_CLUSTER_ID"].nunique()),
        "historical_holdout_clusters": int(bundle.test["BUTINA_CLUSTER_ID"].nunique()),
        "mollogp_liphex_spearman": correlation,
        "split_sha256": bundle.audit["split_sha256"],
    }
    outputs.append(write_json(output_dir / "dataset_summary.json", dataset_summary))
    outputs.append(write_json(output_dir / "analysis_config.json", analysis_config))

    figure_paths = [
        figure_dir / "x10_model_overview.png",
        figure_dir / "descriptor_ablation.png",
        figure_dir / "roc_pr_curves.png",
        figure_dir / "kernel_geometry.png",
        figure_dir / "holdout_distance_errors.png",
        figure_dir / "descriptor_correlations.png",
    ]
    _plot_overview(metrics, figure_paths[0])
    _plot_ablation(comparisons, figure_paths[1])
    _plot_curves(runs, figure_paths[2])
    _plot_kernel_geometry(diagnostics, figure_paths[3])
    _plot_error_strata(strata, figure_paths[4])
    _plot_correlations(bundle, figure_paths[5])
    outputs.extend(figure_paths)

    paper_figure_dir = PROJECT_ROOT / "paper" / "fig"
    paper_figure_dir.mkdir(parents=True, exist_ok=True)
    for figure in figure_paths:
        destination = paper_figure_dir / figure.name
        shutil.copy2(figure, destination)
        outputs.append(destination)
    table_paths = _paper_tables(
        bundle, metrics, comparisons, diagnostics, PROJECT_ROOT / "paper" / "generated"
    )
    outputs.extend(table_paths)

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_config_sha256": sha256_json(analysis_config),
        "dataset": bundle.audit,
        "input_runs": {
            "classical": {
                "directory": classical["run_dir"].name,
                "manifest_sha256": sha256_file(classical["run_dir"] / "manifest.json"),
            },
            "quantum": {
                "directory": quantum["run_dir"].name,
                "manifest_sha256": sha256_file(quantum["run_dir"] / "manifest.json"),
            },
        },
        "git": source_git_state,
        "environment": source_environment,
        "outputs": {str(path.relative_to(PROJECT_ROOT)): sha256_file(path) for path in outputs},
    }
    manifest_path = write_json(output_dir / "manifest.json", manifest)
    latest = {
        "analysis_directory": str(output_dir.relative_to(PROJECT_ROOT)),
        "classical_run": str(classical["run_dir"].relative_to(PROJECT_ROOT)),
        "quantum_run": str(quantum["run_dir"].relative_to(PROJECT_ROOT)),
        "manifest_sha256": sha256_file(manifest_path),
    }
    write_json(args.output_root.resolve() / "latest.json", latest)
    print(f"MolLogP/LiPHEX Spearman: {correlation:.6f}")
    print(f"Final analysis directory: {output_dir}")


if __name__ == "__main__":
    main()
