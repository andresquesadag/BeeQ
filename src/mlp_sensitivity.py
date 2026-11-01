"""Retrospective, immutable MLP class-weight sensitivity on frozen BeeQ X10.

Original shared runners and campaigns are deliberately not changed. Each fit
receives only its CV training rows; balanced weights are calculated there.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import pickle
import platform
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import ParameterGrid
from sklearn.neural_network import MLPClassifier
from sklearn.neural_network import _multilayer_perceptron as mlp_module

from .classical_models import model_specs
from .config import OUTER_FOLDS, X10_FEATURES
from .data import load_bundle
from .evaluation import continuous_scores
from .final_nested_campaign import (
    BOOTSTRAP_REPLICATES, EXPECTED_HASHES, SEED, classification_metrics,
    frozen_outer_splits, inner_splits, prediction_rows, select_threshold,
    sha256_file, validate_development, validate_postfreeze_frame, write_json,
)
from .model_artifacts import FrozenClassical

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "results/campaigns/BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z"
VARIANTS = ("MLP_original", "MLP_balanced_fixed", "MLP_balanced_search")
TOLERANCE = 1e-10


def balanced_weights(labels: np.ndarray) -> np.ndarray:
    """N/(2*n_c) using only labels supplied to this particular training fit."""
    y = np.asarray(labels)
    if y.ndim != 1 or set(np.unique(y)) != {0, 1}:
        raise ValueError("A training partition must contain both binary classes")
    counts = np.bincount(y.astype(int), minlength=2)
    weights = len(y) / (2.0 * counts[y.astype(int)])
    if not np.isfinite(weights).all() or (weights <= 0).any():
        raise RuntimeError("Invalid training weights")
    np.testing.assert_allclose(weights.sum(), len(y), rtol=0, atol=1e-10)
    for c in (0, 1):
        np.testing.assert_allclose(weights[y == c].sum(), len(y) / 2, atol=1e-10)
    return weights


def assert_partition(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    for column in ("ID", "BUTINA_CLUSTER_ID"):
        if set(train[column]) & set(validation[column]):
            raise RuntimeError(f"CV leakage in {column}")
    if set(train.LABEL.unique()) != {0, 1} or set(validation.LABEL.unique()) != {0, 1}:
        raise RuntimeError("CV train and validation must contain both classes")


def checked_fit(frame: pd.DataFrame, params: dict, balanced: bool,
                audit: list[dict], stage: str, variant: str, fold: str):
    """Fit the original pipeline, optionally passing weights to its MLP only.

    The train_test_split hook observes native stopping indices without changing
    arrays, random state, optimizer, stopping metric or implementation.
    """
    x = frame.loc[:, X10_FEATURES].to_numpy(float)
    y = frame.LABEL.to_numpy(int)
    weights = balanced_weights(y) if balanced else None
    estimator = clone(model_specs(SEED)["mlp"].estimator).set_params(**params)
    native_split = mlp_module.train_test_split
    stopping = {}

    def observe_split(*arrays, **kwargs):
        duplicate_kwargs = dict(kwargs)
        duplicate_kwargs["random_state"] = copy.deepcopy(kwargs["random_state"])
        a, b = native_split(np.arange(len(frame)), **duplicate_kwargs)
        result = native_split(*arrays, **kwargs)
        np.testing.assert_array_equal(result[0], arrays[0][a])
        np.testing.assert_array_equal(result[1], arrays[0][b])
        if balanced:
            np.testing.assert_array_equal(result[4], weights[a])
            np.testing.assert_array_equal(result[5], weights[b])
        stopping.update({
            "gradient_ids": frame.iloc[a].ID.astype(int).tolist(),
            "stopping_ids": frame.iloc[b].ID.astype(int).tolist(),
            "gradient_negative": int((y[a] == 0).sum()),
            "gradient_positive": int((y[a] == 1).sum()),
            "stopping_negative": int((y[b] == 0).sum()),
            "stopping_positive": int((y[b] == 1).sum()),
            "stopping_cluster_overlap": len(set(frame.iloc[a].BUTINA_CLUSTER_ID)
                                             & set(frame.iloc[b].BUTINA_CLUSTER_ID)),
            "stopping_accuracy_weighted": balanced,
        })
        return result

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")  # overrides historical suppression
        with patch.object(mlp_module, "train_test_split", observe_split):
            fit_kwargs = {"model__sample_weight": weights} if balanced else {}
            estimator.fit(x, y, **fit_kwargs)
    scaler = estimator.named_steps["scale"]
    np.testing.assert_allclose(scaler.mean_, x.mean(axis=0), rtol=0, atol=1e-12)
    np.testing.assert_allclose(scaler.var_, x.var(axis=0), rtol=0, atol=1e-10)
    if int(scaler.n_samples_seen_) != len(frame):
        raise RuntimeError("Scaler not fitted locally or received weights")
    model = estimator.named_steps["model"]
    audit.append({
        "stage": stage, "variant": variant, "fold": fold,
        "params": json.dumps(params, sort_keys=True), "seed": SEED,
        "fit_ids": frame.ID.astype(int).tolist(), "n_fit": len(frame),
        "negative": int((y == 0).sum()), "positive": int((y == 1).sum()),
        "weight_0": float(weights[y == 0][0]) if balanced else 1.0,
        "weight_1": float(weights[y == 1][0]) if balanced else 1.0,
        "weight_sum": float(weights.sum()) if balanced else len(frame),
        "scaler_mean": scaler.mean_.tolist(), "scaler_var": scaler.var_.tolist(),
        "scaler_n": int(scaler.n_samples_seen_), "resampling": False,
        "n_iter": int(model.n_iter_), "max_iter": model.max_iter,
        "stopped_before_max_iter": model.n_iter_ < model.max_iter,
        "loss": float(model.loss_), "loss_curve": model.loss_curve_,
        "validation_scores": model.validation_scores_,
        "best_validation_score": model.best_validation_score_,
        "warnings": [{"category": w.category.__name__, "message": str(w.message)}
                     for w in caught], **stopping,
    })
    if not np.isfinite(model.loss_curve_).all():
        raise RuntimeError("Nonfinite training loss")
    return estimator


def score_fit(frame, validation, params, balanced, audit, stage, variant, fold):
    assert_partition(frame, validation)
    estimator = checked_fit(frame, params, balanced, audit, stage, variant, fold)
    scores = continuous_scores(estimator, validation.loc[:, X10_FEATURES].to_numpy(float))
    if len(scores) != len(validation) or not np.isfinite(scores).all():
        raise RuntimeError("Invalid evaluation predictions")
    return scores, estimator


def search(frame, splits, balanced, audit, hpo, variant, scope):
    candidates = list(ParameterGrid(model_specs(SEED)["mlp"].param_grid))
    means, stds = [], []
    for c, params in enumerate(candidates):
        values = []
        for f, (tr, va) in enumerate(splits, 1):
            scores, _ = score_fit(frame.iloc[tr], frame.iloc[va], params, balanced,
                                  audit, "hpo", variant, f"{scope}.{c}.{f}")
            values.append(roc_auc_score(frame.iloc[va].LABEL, scores))
        means.append(float(np.mean(values)))
        stds.append(float(np.std(values, ddof=0)))  # GridSearchCV semantics
        hpo.append({"VARIANT": variant, "SCOPE": scope, "CANDIDATE": c,
                    "PARAMS": json.dumps(params, sort_keys=True),
                    "MEAN_AUROC": means[-1], "SD_AUROC": stds[-1],
                    **{f"FOLD_{i}": v for i, v in enumerate(values, 1)}})
    selected = int(np.argmax(means))  # first ParameterGrid candidate on exact ties
    return candidates[selected], means[selected], stds[selected]


def threshold_oof(frame, splits, params, balanced, audit, variant, scope, rows):
    scores = np.full(len(frame), np.nan)
    coverage = np.zeros(len(frame), int)
    for f, (tr, va) in enumerate(splits, 1):
        score, _ = score_fit(frame.iloc[tr], frame.iloc[va], params, balanced,
                            audit, "threshold_oof", variant, f"{scope}.{f}")
        scores[va] = score
        coverage[va] += 1
    if not np.isfinite(scores).all() or not (coverage == 1).all():
        raise RuntimeError("OOF coverage must be exactly once")
    threshold, metrics = select_threshold(frame.LABEL.to_numpy(int), scores)
    for row in prediction_rows(frame, variant, scope, scores, threshold):
        rows.append({"SCOPE": scope, **row})
    return threshold, metrics


def compare_predictions(new, reference, name):
    a = new.sort_values("ID").reset_index(drop=True)
    b = reference.sort_values("ID").reset_index(drop=True)
    if len(a) != len(b):
        raise RuntimeError(f"{name}: prediction count differs")
    for col in ("ID", "LABEL", "PRED"):
        np.testing.assert_array_equal(a[col], b[col], err_msg=f"{name}/{col}")
    for col in ("SCORE", "THRESHOLD", "MARGIN"):
        np.testing.assert_allclose(a[col], b[col], rtol=0, atol=TOLERANCE,
                                   err_msg=f"{name}/{col}")
    return {"check": name, "n": len(a), "max_abs_score_difference":
            float(np.max(np.abs(a.SCORE - b.SCORE))), "tolerance": TOLERANCE,
            "pass": True}


def verify_reference(reference, output):
    checks = []
    manifest = pd.read_csv(reference / "10_MANIFEST/ARTIFACT_MANIFEST_SHA256.csv")
    for row in manifest.itertuples(index=False):
        path = reference / row.relative_path
        passed = path.is_file() and path.stat().st_size == row.bytes and sha256_file(path) == row.sha256
        checks.append({"file": row.relative_path, "pass": passed})
        if not passed:
            raise RuntimeError(f"Invalid reference artifact: {path}")
    provenance = json.loads((reference / "10_MANIFEST/SOURCE_CODE_PROVENANCE.json").read_text())
    for name, expected in provenance["files"].items():
        raw = (ROOT / name).read_bytes()
        observed = hashlib.sha256(raw).hexdigest()
        normalized = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        passed = observed == expected or normalized == expected
        checks.append({"file": name, "pass": passed, "raw_sha256": observed,
                       "lf_sha256": normalized, "reference_sha256": expected,
                       "line_ending_normalization_required": observed != expected})
        if not passed:
            raise RuntimeError(f"Historical implementation has changed: {name}")
    pd.DataFrame(checks).to_csv(output / "REFERENCE_INTEGRITY.csv", index=False)


def record_splits(train, output):
    rows, members = [], []
    def add(scope, fold, a, b):
        tr, va = train.iloc[a], train.iloc[b]
        assert_partition(tr, va)
        rows.append({"SCOPE": scope, "FOLD": fold, "N_TRAIN": len(tr), "N_VALIDATION": len(va),
                     "TRAIN_NEGATIVE": int((tr.LABEL == 0).sum()),
                     "TRAIN_POSITIVE": int(tr.LABEL.sum()),
                     "VALIDATION_NEGATIVE": int((va.LABEL == 0).sum()),
                     "VALIDATION_POSITIVE": int(va.LABEL.sum()), "CLUSTER_OVERLAP": 0})
        for role, idx in (("train", a), ("validation", b)):
            for row in train.iloc[idx].itertuples(index=False):
                members.append({"SCOPE": scope, "FOLD": fold, "ROLE": role,
                                "ID": int(row.ID), "LABEL": int(row.LABEL),
                                "BUTINA_CLUSTER_ID": int(row.BUTINA_CLUSTER_ID)})
    for f, (a, b) in zip(OUTER_FOLDS, frozen_outer_splits(train)):
        add("outer", f, a, b)
        for i, (c, d) in enumerate(inner_splits(train, a, f), 1):
            add(f"inner_outer_{f}", i, a[c], a[d])
        add("final_selection", f, a, b)
    pd.DataFrame(rows).to_csv(output / "SPLIT_COUNTS.csv", index=False)
    pd.DataFrame(members).to_csv(output / "SPLIT_MEMBERSHIP.csv", index=False)


def metric_row(variant, evaluation, frame, scores, threshold, **extra):
    return {"MODEL": variant, "EVALUATION": evaluation, "N": len(frame),
            "NEGATIVE": int((frame.LABEL == 0).sum()), "POSITIVE": int(frame.LABEL.sum()),
            "THRESHOLD": threshold,
            **{k.upper(): v for k, v in classification_metrics(frame.LABEL.to_numpy(int), scores, threshold).items()},
            **extra}


def summarize(folds, predictions):
    rows = []
    for variant, group in predictions.groupby("MODEL", sort=False):
        m = folds[folds.MODEL == variant]
        truth, pred = group.LABEL.to_numpy(int), group.PRED.to_numpy(int)
        tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
        rows.append({"MODEL": variant, "N": len(group), "NEGATIVE": int((truth == 0).sum()),
                     "POSITIVE": int(truth.sum()),
                     **{f"{k}_{s}": float(getattr(m[k], s)() if s == "mean" else m[k].std(ddof=1))
                        for k in ("AUROC", "AUPRC", "BALANCED_ACCURACY", "MCC", "SENSITIVITY", "SPECIFICITY")
                        for s in ("mean", "sd")},
                     "POOLED_AUROC": roc_auc_score(truth, group.SCORE),
                     "POOLED_AUPRC": average_precision_score(truth, group.SCORE),
                     "POOLED_BA": (tp / (tp + fn) + tn / (tn + fp)) / 2,
                     "POOLED_MCC": float(sklearn.metrics.matthews_corrcoef(truth, pred)),
                     "POOLED_SENSITIVITY": tp / (tp + fn), "POOLED_SPECIFICITY": tn / (tn + fp),
                     "TP": tp, "FN": fn, "TN": tn, "FP": fp})
    return pd.DataFrame(rows)


def paired_statistics(folds, oof, reference, output):
    delta_rows = []
    original = folds[folds.MODEL == VARIANTS[0]].set_index("OUTER_FOLD")
    metrics = ("AUROC", "AUPRC", "BALANCED_ACCURACY", "MCC", "SENSITIVITY", "SPECIFICITY", "TP", "FN", "TN", "FP")
    for variant in VARIANTS[1:]:
        subset = folds[folds.MODEL == variant].set_index("OUTER_FOLD")
        for f in OUTER_FOLDS:
            delta_rows.append({"MODEL": variant, "OUTER_FOLD": f,
                               **{k: subset.loc[f, k] - original.loc[f, k] for k in metrics}})
    deltas = pd.DataFrame(delta_rows)
    deltas.to_csv(output / "PAIRED_FOLD_DELTAS.csv", index=False)
    deltas.groupby("MODEL")[list(metrics)].agg(["mean", "std"]).to_csv(output / "PAIRED_FOLD_DELTA_SUMMARY.csv")
    old = pd.read_csv(reference / "03_NESTED_CV/NESTED_OUTER_OOF_PREDICTIONS.csv")
    all_oof = pd.concat([oof, old[old.MODEL == "random_forest"]], ignore_index=True)
    wide = all_oof.pivot(index=["ID", "BUTINA_CLUSTER_ID", "LABEL"], columns="MODEL", values="SCORE").reset_index()
    if wide.isna().any().any():
        raise RuntimeError("Paired bootstrap molecule mismatch")
    clusters = sorted(wide.BUTINA_CLUSTER_ID.unique())
    indices = {c: np.flatnonzero(wide.BUTINA_CLUSTER_ID.to_numpy() == c) for c in clusters}
    pairs = [(v, VARIANTS[0]) for v in VARIANTS[1:]] + [("random_forest", VARIANTS[2])]
    functions = {"AUROC": roc_auc_score, "AUPRC": average_precision_score}
    draws = {(a, b, m): [] for a, b in pairs for m in functions}
    rng = np.random.default_rng(SEED)
    y = wide.LABEL.to_numpy(int)
    for _ in range(BOOTSTRAP_REPLICATES):
        idx = np.concatenate([indices[c] for c in rng.choice(clusters, len(clusters), replace=True)])
        if len(np.unique(y[idx])) < 2:
            continue
        for (a, b, m), values in draws.items():
            function = functions[m]
            values.append(function(y[idx], wide[a].to_numpy()[idx]) - function(y[idx], wide[b].to_numpy()[idx]))
    rows = []
    for (a, b, m), values in draws.items():
        function = functions[m]
        rows.append({"LEFT_MODEL": a, "RIGHT_MODEL": b, "METRIC": m,
                     "OBSERVED_DELTA": function(y, wide[a]) - function(y, wide[b]),
                     "CI_LOW_95": np.quantile(values, .025), "CI_HIGH_95": np.quantile(values, .975),
                     "BOOTSTRAP_MEDIAN": np.median(values), "P_DELTA_GT_0": np.mean(np.asarray(values) > 0),
                     "REPLICATES": len(values), "RESAMPLING_UNIT": "BUTINA_CLUSTER_ID"})
    pd.DataFrame(rows).to_csv(output / "PAIRED_CLUSTER_BOOTSTRAP.csv", index=False)


def verify_saved_metrics(reference, output):
    """Check all six saved models' predictions against their metrics, no refits."""
    rows = []
    for directory, prefix in (("03_NESTED_CV", "NESTED_OUTER_OOF"), ("05_HOLDOUT", "HOLDOUT"), ("06_EXTERNAL_CR8", "CR8")):
        pred = pd.read_csv(reference / directory / f"{prefix}_PREDICTIONS.csv")
        metrics_name = "NESTED_FOLD_METRICS.csv" if directory == "03_NESTED_CV" else f"{prefix}_METRICS.csv"
        saved = pd.read_csv(reference / directory / metrics_name)
        for row in saved.to_dict("records"):
            group = pred[pred.MODEL == row["MODEL"]]
            if "OUTER_FOLD" in row:
                group = group[group.OUTER_FOLD == row["OUTER_FOLD"]]
            if group.THRESHOLD.nunique() != 1:
                raise RuntimeError("Reference threshold inconsistency")
            observed = classification_metrics(group.LABEL.to_numpy(int), group.SCORE.to_numpy(float), float(group.THRESHOLD.iloc[0]))
            np.testing.assert_array_equal(group.PRED, (group.SCORE >= group.THRESHOLD).astype(int))
            for name, value in observed.items():
                np.testing.assert_allclose(value, row[name.upper()], atol=TOLERANCE, rtol=0)
            rows.append({"partition": directory, "model": row["MODEL"],
                         "fold": row.get("OUTER_FOLD", "final"), "pass": True})
    pd.DataFrame(rows).to_csv(output / "REFERENCE_METRIC_RECOMPUTATION.csv", index=False)


def run(output: Path, reference: Path, smoke=False, compare_to: Path | None = None):
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "STATUS.json", {"status": "running", "smoke": smoke})
    verify_reference(reference, output)
    verify_saved_metrics(reference, output)
    for name, expected in EXPECTED_HASHES.items():
        if sha256_file(ROOT / "data/official" / name) != expected:
            raise RuntimeError(f"Official input hash mismatch: {name}")
    if sklearn.__version__ != "1.9.0" or "sample_weight" not in inspect.signature(MLPClassifier.fit).parameters:
        raise RuntimeError("Use the historical scikit-learn 1.9.0 environment")
    if np.__version__ != "2.5.1" or pd.__version__ != "2.3.3" or platform.python_version() != "3.12.8":
        raise RuntimeError("Use the exact historical Python/NumPy/pandas environment")
    train = validate_development(ROOT / "data/official/train_RDKitFixed.csv", output)
    record_splits(train, output)
    implementation_path = Path(inspect.getfile(MLPClassifier))
    write_json(output / "CONFIG.json", {
        "seed": SEED, "inner_seeds": [SEED + f for f in OUTER_FOLDS], "outer_folds": list(OUTER_FOLDS),
        "inner_folds": 4, "feature_order": X10_FEATURES,
        "grid": model_specs(SEED)["mlp"].param_grid, "candidates": 12,
        "estimator_parameters": model_specs(SEED)["mlp"].estimator.get_params()["model"].get_params(),
        "weight_formula": "N_fit / (2 * n_class_fit)", "weight_scope": "CV training fit before native early-stopping reservation",
        "evaluation_sample_weights": False, "resampling": False,
        "A": "original-selected hyperparameters fixed separately per outer fold and final fit",
        "B": "12 candidates, four inner cluster folds; final selection on five frozen Development folds",
        "threshold": "max MCC, then BA, then abs(threshold), then threshold on local OOF",
        "retrospective": True, "original_reproduction_tolerance": TOLERANCE,
        "reference": reference.relative_to(ROOT).as_posix(), "smoke": smoke,
    })
    sources = [ROOT / p for p in ("src/mlp_sensitivity.py", "src/classical_models.py", "src/config.py", "src/evaluation.py", "src/final_nested_campaign.py", "src/model_artifacts.py", "docs/MLP_BALANCING_DIAGNOSIS.md")]
    write_json(output / "PROVENANCE.json", {
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
        "sklearn": sklearn.__version__, "scipy": __import__("scipy").__version__,
        "matplotlib": matplotlib.__version__, "platform": platform.platform(),
        "argv": sys.argv, "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], text=True).splitlines(),
        "input_hashes": {name: sha256_file(ROOT / "data/official" / name) for name in EXPECTED_HASHES},
        "source_hashes": {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in sources},
        "installed_mlp_source_sha256": sha256_file(implementation_path),
        "installed_mlp_source_path": str(implementation_path),
    })
    auxiliary = ROOT / ".donotmerge_aux/Bee_project_weightclass.ipynb"
    if auxiliary.exists():
        notebook = json.loads(auxiliary.read_text(encoding="utf-8"))
        write_json(output / "AUXILIARY_EVIDENCE.json", {"file": str(auxiliary.relative_to(ROOT)),
            "tracked": False, "sha256": sha256_file(auxiliary), "causal_link_established": False,
            "excerpts": [{"cell": i, "source": "".join(c.get("source", []))} for i, c in enumerate(notebook["cells"])
                         if c["cell_type"] == "code" and "supports_cw" in "".join(c.get("source", []))]})
    audit, hpo, fold_rows, pred_rows, threshold_rows, selected, checks = [], [], [], [], [], [], []
    params_by_fold = {}
    final_bundles, selections = {}, []
    old_params = pd.read_csv(reference / "03_NESTED_CV/SELECTED_PARAMS_PER_OUTER_FOLD.csv")
    old_oof = pd.read_csv(reference / "03_NESTED_CV/NESTED_OUTER_OOF_PREDICTIONS.csv")
    old_selection = next(s for s in json.loads((reference / "04_FINAL_SELECTION/FINAL_MODEL_SELECTIONS.json").read_text())["models"] if s["model"] == "mlp")
    for variant in VARIANTS:
        balanced = variant != VARIANTS[0]
        print(f"Starting {variant}", flush=True)
        for outer_fold, (tr, va) in zip(OUTER_FOLDS, frozen_outer_splits(train)):
            if smoke and outer_fold != 1:
                continue
            frame, validation = train.iloc[tr], train.iloc[va]
            splits = inner_splits(train, tr, outer_fold)
            if smoke:
                params = json.loads(old_params[(old_params.MODEL == "mlp") & (old_params.OUTER_FOLD == outer_fold)].BEST_PARAMS.iloc[0])
                mean = std = None
            elif variant == VARIANTS[1]:
                params = params_by_fold[outer_fold]
                mean = std = None  # fixed, not optimized for balanced AUROC
            else:
                params, mean, std = search(frame, splits, balanced, audit, hpo, variant, f"outer_{outer_fold}")
            if variant == VARIANTS[0]:
                params_by_fold[outer_fold] = params
            threshold, inner_metrics = threshold_oof(frame, splits, params, balanced, audit, variant, f"outer_{outer_fold}", threshold_rows)
            scores, _ = score_fit(frame, validation, params, balanced, audit, "outer_fit", variant, str(outer_fold))
            fold_rows.append(metric_row(variant, "nested_outer", validation, scores, threshold,
                            OUTER_FOLD=outer_fold, N_TRAIN=len(frame), INNER_AUROC_MEAN=mean, INNER_AUROC_SD=std))
            selected.append({"MODEL": variant, "OUTER_FOLD": outer_fold, "BEST_PARAMS": json.dumps(params, sort_keys=True),
                             "THRESHOLD": threshold, "INNER_THRESHOLD_MCC": inner_metrics["mcc"], "INNER_THRESHOLD_BA": inner_metrics["balanced_accuracy"]})
            pred_rows.extend(prediction_rows(validation, variant, outer_fold, scores, threshold))
            if variant == VARIANTS[0]:
                new = pd.DataFrame(pred_rows)
                checks.append(compare_predictions(new[(new.MODEL == variant) & (new.OUTER_FOLD == outer_fold)],
                              old_oof[(old_oof.MODEL == "mlp") & (old_oof.OUTER_FOLD == outer_fold)], f"outer_{outer_fold}"))
                expected = json.loads(old_params[(old_params.MODEL == "mlp") & (old_params.OUTER_FOLD == outer_fold)].BEST_PARAMS.iloc[0])
                if json.dumps(params, sort_keys=True) != json.dumps(expected, sort_keys=True):
                    raise RuntimeError("Original HPO parameters not reproduced")
            print(f"{variant}: outer fold {outer_fold}, AUROC={fold_rows[-1]['AUROC']:.6f}, threshold={threshold:.6f}", flush=True)
        if not smoke:
            splits = frozen_outer_splits(train)
            if variant == VARIANTS[1]:
                params = selections[0]["params"]
                mean = std = None
            else:
                params, mean, std = search(train, splits, balanced, audit, hpo, variant, "final")
            threshold, inner_metrics = threshold_oof(train, splits, params, balanced, audit, variant, "final", threshold_rows)
            estimator = checked_fit(train, params, balanced, audit, "final_fit", variant, "all")
            bundle = FrozenClassical(estimator, threshold)
            final_bundles[variant] = bundle
            artifact = output / f"{variant}.pkl"
            artifact.write_bytes(pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL))
            selections.append({"variant": variant, "params": params, "threshold": threshold,
                               "selection_mean_auroc": mean, "selection_sd_auroc": std,
                               "threshold_oof_metrics": inner_metrics, "artifact": artifact.name,
                               "artifact_sha256": sha256_file(artifact)})
            if variant == VARIANTS[0]:
                if json.dumps(params, sort_keys=True) != json.dumps(old_selection["best_params"], sort_keys=True):
                    raise RuntimeError("Original final selection not reproduced")
                np.testing.assert_allclose(threshold, old_selection["final_threshold"], atol=TOLERANCE, rtol=0)
        pd.DataFrame(fold_rows).to_csv(output / "NESTED_FOLD_METRICS.csv", index=False)
        pd.DataFrame(pred_rows).to_csv(output / "NESTED_OOF_PREDICTIONS.csv", index=False)
        pd.DataFrame(selected).to_csv(output / "SELECTED_PARAMS.csv", index=False)
        pd.DataFrame(threshold_rows).to_csv(output / "THRESHOLD_OOF_PREDICTIONS.csv", index=False)
        pd.DataFrame(hpo).to_csv(output / "HPO_CANDIDATES.csv", index=False)
        write_json(output / "FIT_AUDIT.json", audit)
        write_json(output / "FINAL_SELECTIONS.json", selections)
        write_json(output / "ORIGINAL_REPRODUCTION.json", checks)
    folds, oof = pd.DataFrame(fold_rows), pd.DataFrame(pred_rows)
    if not smoke:
        for v in VARIANTS:
            p = oof[oof.MODEL == v]
            if len(p) != len(train) or p.ID.duplicated().any() or set(p.ID) != set(train.ID):
                raise RuntimeError("Outer OOF coverage failure")
        summarize(folds, oof).to_csv(output / "NESTED_SUMMARY.csv", index=False)
    freeze_files = {p.name: sha256_file(p) for p in output.iterdir() if p.is_file() and p.name != "STATUS.json"}
    write_json(output / "DEVELOPMENT_FREEZE.json", {"status": "frozen", "utc": datetime.now(timezone.utc).isoformat(),
               "retrospective": True, "external_input_csv_contents_read_by_runner_before_freeze": False,
               "historical_reference_predictions_verified_before_freeze": True, "hashes": freeze_files})
    for name, expected in freeze_files.items():
        if sha256_file(output / name) != expected:
            raise RuntimeError(f"Freeze mismatch: {name}")
    external_metrics, external_predictions = [], []
    if not smoke:
        for evaluation, name, n, labels in (("historical_holdout", "test_RDKitFixed.csv", 181, {0: 132, 1: 49}),
                                            ("CR8", "ExternalFinal_RDKitFixed.csv", 8, {0: 6, 1: 2})):
            frame = pd.read_csv(ROOT / "data/official" / name)
            validate_postfreeze_frame(frame, expected_rows=n, expected_labels=labels, source=evaluation)
            for variant, bundle in final_bundles.items():
                restored = pickle.loads((output / f"{variant}.pkl").read_bytes())
                x = frame.loc[:, X10_FEATURES].to_numpy(float)
                scores = continuous_scores(restored.estimator, x)
                np.testing.assert_array_equal(scores, continuous_scores(bundle.estimator, x))
                external_metrics.append(metric_row(variant, evaluation, frame, scores, restored.threshold))
                rows = prediction_rows(frame, variant, evaluation, scores, restored.threshold)
                external_predictions.extend({"EVALUATION": evaluation, **r} for r in rows)
                if variant == VARIANTS[0]:
                    directory, prefix = ("05_HOLDOUT", "HOLDOUT") if evaluation == "historical_holdout" else ("06_EXTERNAL_CR8", "CR8")
                    old = pd.read_csv(reference / directory / f"{prefix}_PREDICTIONS.csv")
                    checks.append(compare_predictions(pd.DataFrame(rows), old[old.MODEL == "mlp"], evaluation))
        pd.DataFrame(external_metrics).to_csv(output / "EXTERNAL_METRICS.csv", index=False)
        pd.DataFrame(external_predictions).to_csv(output / "EXTERNAL_PREDICTIONS.csv", index=False)
        # freeze artifacts stay unchanged; post-freeze checks have their own file.
        write_json(output / "POSTFREEZE_ORIGINAL_REPRODUCTION.json", checks)
        paired_statistics(folds, oof, reference, output)
        figure(folds, pd.DataFrame(external_metrics), output)
    audit_frame = pd.DataFrame([{k: a[k] for k in ("stage", "variant", "fold", "n_fit", "negative", "positive", "weight_0", "weight_1", "weight_sum", "n_iter", "max_iter", "stopped_before_max_iter", "loss", "best_validation_score", "stopping_cluster_overlap", "stopping_accuracy_weighted")}
                               | {"warning_count": len(a["warnings"])} for a in audit])
    audit_frame.to_csv(output / "FIT_AUDIT_SUMMARY.csv", index=False)
    if compare_to:
        comparisons = []
        for p in sorted(output.glob("*.csv")):
            other = compare_to / p.name
            if not other.is_file():
                raise RuntimeError(f"Repeat output missing {other}")
            a, b = pd.read_csv(p), pd.read_csv(other)
            pd.testing.assert_frame_equal(a, b, check_exact=True)
            comparisons.append({"file": p.name, "exact_csv_match": True})
        write_json(output / "REPEAT_COMPARISON.json", comparisons)
    for name, expected in freeze_files.items():
        if sha256_file(output / name) != expected:
            raise RuntimeError(f"Post-evaluation mutation of Development artifact: {name}")
    write_json(output / "STATUS.json", {"status": "smoke_complete" if smoke else "complete", "smoke": smoke,
               "fits": len(audit), "warnings": int(audit_frame.warning_count.sum()), "retrospective": True})
    manifest(output)
    print(f"Completed {output}", flush=True)


def figure(folds, external, output):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
    colors = ("#364152", "#E5A12A", "#287F8E")
    for i, (variant, color) in enumerate(zip(VARIANTS, colors)):
        f = folds[folds.MODEL == variant]
        axes[0].plot(f.OUTER_FOLD, f.AUROC, marker="o", color=color, label=variant.replace("MLP_", ""))
        e = external[(external.MODEL == variant) & (external.EVALUATION == "historical_holdout")].iloc[0]
        axes[1].bar(i, e.AUROC, color=color)
        axes[2].bar(i - .15, e.SENSITIVITY, width=.3, color=color)
        axes[2].bar(i + .15, e.SPECIFICITY, width=.3, color=color, alpha=.4)
    axes[0].set(title="Nested Development: paired folds", xlabel="Outer fold", ylabel="AUROC", ylim=(0, 1))
    axes[0].legend(fontsize=8)
    axes[1].set(title="Historical holdout: discrimination", ylabel="AUROC", ylim=(0, 1))
    axes[2].set(title="Holdout: frozen-threshold decisions", ylabel="Sensitivity (solid) / specificity (faded)", ylim=(0, 1))
    for a in axes[1:]:
        a.set_xticks(range(3), ["Original", "Balanced A", "Balanced B"])
    fig.savefig(output / "MLP_SENSITIVITY.png", dpi=180)
    plt.close(fig)


def manifest(output):
    pd.DataFrame([{"relative_path": p.relative_to(output).as_posix(), "bytes": p.stat().st_size,
                   "sha256": sha256_file(p)} for p in sorted(output.rglob("*")) if p.is_file() and p.name != "MANIFEST_SHA256.csv"]).to_csv(output / "MANIFEST_SHA256.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--compare-to", type=Path)
    args = parser.parse_args()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir or ROOT / "results/mlp_sensitivity" / (timestamp + ("_smoke" if args.smoke else ""))
    try:
        run(output.resolve(), args.reference.resolve(), args.smoke, args.compare_to)
    except Exception as error:
        if output.exists() and not (output / "MANIFEST_SHA256.csv").exists():
            write_json(output / "STATUS.json", {"status": "failed", "error": repr(error)})
        raise


if __name__ == "__main__":
    main()
