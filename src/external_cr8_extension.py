"""Post-freeze CR8 evaluation for Exercise A without rerunning nested CV."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .config import OUTER_FOLDS, PROJECT_ROOT, X10_FEATURES
from .exercise_a_campaign import (
    BASELINE,
    COMPLEMENTARY,
    C_VALUES,
    DUPLICATE,
    FEATURE_SCALES,
    IDLE,
    INTERACTION_STRENGTH,
    MODELS,
    SEED,
    architecture_definition,
    build_manifest,
    classification_metrics,
    kernel_qc,
    model_kernel,
    select_threshold,
    sha256_canonical_lf,
    sha256_file,
    utc_now,
    write_json,
)


DEFAULT_A_CAMPAIGN = (
    PROJECT_ROOT
    / "results"
    / "campaigns"
    / "BEEQ_EXERCISE_A_10Q_VS_20Q_20260829T021247Z"
)
DEVELOPMENT_PATH = PROJECT_ROOT / "data" / "official" / "train_RDKitFixed.csv"
CR8_PATH = PROJECT_ROOT / "data" / "official" / "ExternalFinal_RDKitFixed.csv"
EXPECTED_CR8_SHA256_LF = "70a01eedd970991e072eb9db8e2acdbe854dc8d4623b42bb2263318486cd41fb"
START_MARKER = "<!-- CR8_EXTENSION_START -->"
END_MARKER = "<!-- CR8_EXTENSION_END -->"


def atomic_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def frozen_five_splits(train: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    splits = []
    for fold in OUTER_FOLDS:
        train_idx = np.flatnonzero(folds != fold)
        validation_idx = np.flatnonzero(folds == fold)
        train_groups = set(train.iloc[train_idx].BUTINA_CLUSTER_ID)
        validation_groups = set(train.iloc[validation_idx].BUTINA_CLUSTER_ID)
        if train_groups & validation_groups:
            raise RuntimeError(f"Cluster leakage in frozen fold {fold}")
        splits.append((train_idx, validation_idx))
    return splits


def select_and_fit(
    train: pd.DataFrame,
    external: pd.DataFrame,
    model: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    x = train.loc[:, X10_FEATURES].to_numpy(float)
    y = train.LABEL.to_numpy(int)
    x_external = external.loc[:, X10_FEATURES].to_numpy(float)
    splits = frozen_five_splits(train)
    hpo = {
        (scale_index, c): []
        for scale_index in range(len(FEATURE_SCALES))
        for c in C_VALUES
    }
    qc_rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for fold, (train_idx, validation_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(x[train_idx])
        x_train = scaler.transform(x[train_idx])
        x_validation = scaler.transform(x[validation_idx])
        for scale_index, scale in enumerate(FEATURE_SCALES):
            train_kernel, validation_kernel = model_kernel(
                x_train, x_validation, model, scale
            )
            qc_rows.append(
                kernel_qc(
                    train_kernel,
                    model=model,
                    stage="cr8_final_selection_hpo",
                    outer_fold="all_development",
                    inner_fold=fold,
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
                classifier.fit(train_kernel, y[train_idx])
                score = classifier.decision_function(validation_kernel)
                hpo[(scale_index, c)].append(
                    float(roc_auc_score(y[validation_idx], score))
                )
    ranked = sorted(
        (
            (float(np.mean(scores)), float(np.std(scores, ddof=1)), scale_index, c)
            for (scale_index, c), scores in hpo.items()
        ),
        key=lambda row: (-row[0], row[2], row[3]),
    )
    mean_auroc, sd_auroc, scale_index, c = ranked[0]
    scale = FEATURE_SCALES[scale_index]
    oof = np.full(len(train), np.nan)
    for fold, (train_idx, validation_idx) in enumerate(splits, start=1):
        scaler = StandardScaler().fit(x[train_idx])
        train_kernel, validation_kernel = model_kernel(
            scaler.transform(x[train_idx]),
            scaler.transform(x[validation_idx]),
            model,
            scale,
        )
        assert validation_kernel is not None
        classifier = SVC(
            C=c,
            kernel="precomputed",
            class_weight="balanced",
            random_state=SEED,
        )
        classifier.fit(train_kernel, y[train_idx])
        oof[validation_idx] = classifier.decision_function(validation_kernel)
    threshold, threshold_metrics = select_threshold(y, oof)
    scaler = StandardScaler().fit(x)
    train_kernel, external_kernel = model_kernel(
        scaler.transform(x), scaler.transform(x_external), model, scale
    )
    qc_rows.append(
        kernel_qc(
            train_kernel,
            model=model,
            stage="cr8_full_development_fit",
            outer_fold="all_development",
            inner_fold="all",
            scale=scale,
        )
    )
    assert external_kernel is not None
    classifier = SVC(
        C=c,
        kernel="precomputed",
        class_weight="balanced",
        random_state=SEED,
    )
    classifier.fit(train_kernel, y)
    scores = classifier.decision_function(external_kernel)
    predictions = []
    for row, score in zip(external.itertuples(index=False), scores):
        predictions.append(
            {
                "ID": int(row.ID),
                "name": str(row.name),
                "MODEL": model,
                "LABEL": int(row.LABEL),
                "SCORE": float(score),
                "THRESHOLD": float(threshold),
                "MARGIN": float(score - threshold),
                "PRED": int(score >= threshold),
            }
        )
    selection = {
        "MODEL": model,
        "C": c,
        "FEATURE_SCALE": scale,
        "INTERACTION_STRENGTH": INTERACTION_STRENGTH,
        "MEAN_CV_AUROC": mean_auroc,
        "SD_CV_AUROC": sd_auroc,
        "THRESHOLD": threshold,
        "THRESHOLD_INNER_MCC": threshold_metrics["mcc"],
        "THRESHOLD_INNER_BALANCED_ACCURACY": threshold_metrics["balanced_accuracy"],
        "ELAPSED_SECONDS": time.perf_counter() - started,
    }
    return selection, predictions, qc_rows


def append_report(
    report_path: Path, metrics: pd.DataFrame, selections: pd.DataFrame
) -> None:
    existing = report_path.read_text(encoding="utf-8")
    if START_MARKER in existing:
        before = existing.split(START_MARKER, 1)[0].rstrip()
        after = existing.split(END_MARKER, 1)[1].lstrip() if END_MARKER in existing else ""
        existing = before + ("\n\n" + after if after else "")
    section = [
        START_MARKER,
        "## Extensión posterior — evaluación externa CR8",
        "",
        "Esta sección se añadió sin repetir la nested CV de A. Cada arquitectura se seleccionó nuevamente usando exclusivamente las 712 moléculas de desarrollo y los cinco folds congelados; scaler, escala, C y threshold se congelaron antes de evaluar una sola vez las 8 moléculas CR8 (6 negativas, 2 positivas). CR8 no intervino en selección.",
        "",
        "| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. | TP | TN | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics.itertuples(index=False):
        section.append(
            f"| {row.MODEL} | {row.MCC:.4f} | {row.AUROC:.4f} | {row.AUPRC:.4f} | "
            f"{row.BALANCED_ACCURACY:.4f} | {row.SENSITIVITY:.4f} | {row.SPECIFICITY:.4f} | "
            f"{int(row.TP)} | {int(row.TN)} | {int(row.FP)} | {int(row.FN)} |"
        )
    section.extend(
        [
            "",
            "Con solo 8 observaciones y 2 positivos, estas métricas tienen resolución muy baja y deben interpretarse como validación externa descriptiva, no como evidencia confirmatoria ni como base para retuning.",
            END_MARKER,
        ]
    )
    atomic_text(report_path, existing.rstrip() + "\n\n" + "\n".join(section) + "\n")


def run(campaign: Path) -> None:
    campaign = campaign.resolve()
    output = campaign / "08_EXTERNAL_CR8"
    output.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(DEVELOPMENT_PATH)
    external = pd.read_csv(CR8_PATH)
    if len(external) != 8 or external.LABEL.value_counts().to_dict() != {0: 6, 1: 2}:
        raise RuntimeError("CR8 row/label contract mismatch")
    physical = sha256_file(CR8_PATH)
    canonical = sha256_canonical_lf(CR8_PATH)
    if EXPECTED_CR8_SHA256_LF not in {physical, canonical}:
        raise RuntimeError("CR8 content hash mismatch beyond line endings")
    selections = []
    predictions = []
    qc_rows = []
    for model in (BASELINE, DUPLICATE, COMPLEMENTARY):
        print(f"Exercise A CR8 final selection: {model}", flush=True)
        selection, model_predictions, model_qc = select_and_fit(train, external, model)
        selections.append(selection)
        predictions.extend(model_predictions)
        qc_rows.extend(model_qc)
    baseline_selection = dict(selections[0])
    baseline_selection["MODEL"] = IDLE
    idle_predictions = [dict(row, MODEL=IDLE) for row in predictions if row["MODEL"] == BASELINE]
    selections.insert(1, baseline_selection)
    predictions.extend(idle_predictions)
    prediction_frame = pd.DataFrame(predictions)
    metric_rows = []
    for model in MODELS:
        group = prediction_frame[prediction_frame.MODEL == model]
        result = classification_metrics(
            group.LABEL.to_numpy(int), group.SCORE.to_numpy(float), float(group.THRESHOLD.iloc[0])
        )
        metric_rows.append({"MODEL": model, "N": len(group), **{key.upper(): value for key, value in result.items()}})
    metrics = pd.DataFrame(metric_rows)
    pd.DataFrame(selections).to_csv(output / "CR8_FINAL_SELECTION.csv", index=False)
    prediction_frame.to_csv(output / "CR8_PREDICTIONS.csv", index=False)
    metrics.to_csv(output / "CR8_METRICS.csv", index=False)
    pd.DataFrame(qc_rows).to_csv(output / "CR8_KERNEL_QC.csv", index=False)
    write_json(
        output / "CR8_PROVENANCE.json",
        {
            "completed_utc": utc_now(),
            "development_physical_sha256": sha256_file(DEVELOPMENT_PATH),
            "development_canonical_lf_sha256": sha256_canonical_lf(DEVELOPMENT_PATH),
            "CR8_physical_sha256": physical,
            "CR8_canonical_lf_sha256": canonical,
            "CR8_expected_lf_sha256": EXPECTED_CR8_SHA256_LF,
            "selection_data": "development_only",
            "external_used_for_selection": False,
            "architectures": {model: architecture_definition(model) for model in MODELS},
            "source_sha256": sha256_file(Path(__file__)),
        },
    )
    config_path = campaign / "01_CONFIG" / "CAMPAIGN_CONFIG.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["CR8_used"] = True
    config["CR8_role"] = "post-freeze_descriptive_external_evaluation"
    config["CR8_used_for_selection"] = False
    write_json(config_path, config)
    append_report(campaign / "FINAL_REPORT.md", metrics, pd.DataFrame(selections))
    build_manifest(campaign)
    print(f"Exercise A CR8 extension complete: {campaign}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, default=DEFAULT_A_CAMPAIGN)
    args = parser.parse_args()
    run(args.campaign_dir)


if __name__ == "__main__":
    main()
