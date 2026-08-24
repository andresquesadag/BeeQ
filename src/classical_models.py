"""Nested structure-aware classical baselines and controlled X10 ablations."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .config import FEATURE_SETS, OUTER_FOLDS
from .evaluation import METRIC_COLUMNS, binary_metrics, continuous_scores


@dataclass(frozen=True)
class ModelSpec:
    estimator: Pipeline
    param_grid: dict[str, list[Any]]


@dataclass(frozen=True)
class ExperimentTables:
    fold_metrics: pd.DataFrame
    predictions: pd.DataFrame
    summary: pd.DataFrame
    best_params: list[dict[str, Any]]


def model_specs(seed: int, quick: bool = False) -> dict[str, ModelSpec]:
    """Return auditable model definitions and matched hyperparameter grids."""

    logistic_c = [0.1, 1.0, 10.0] if quick else [0.01, 0.1, 1.0, 10.0, 100.0]
    svc_c = [0.1, 1.0, 10.0] if quick else [0.1, 1.0, 10.0, 100.0]
    svc_gamma: list[Any] = [0.03, 0.1, "scale"] if quick else [0.01, 0.03, 0.1, 0.3, "scale"]
    forest_depth = [None, 6] if not quick else [None]
    forest_leaf = [1, 3] if not quick else [1]

    specs = {
        "logistic": ModelSpec(
            estimator=Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=5000,
                            random_state=seed,
                            solver="liblinear",
                        ),
                    ),
                ]
            ),
            param_grid={"model__C": logistic_c},
        ),
        "rbf_svc": ModelSpec(
            estimator=Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        SVC(
                            kernel="rbf",
                            class_weight="balanced",
                            random_state=seed,
                        ),
                    ),
                ]
            ),
            param_grid={"model__C": svc_c, "model__gamma": svc_gamma},
        ),
        "random_forest": ModelSpec(
            estimator=Pipeline(
                [
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=300,
                            class_weight="balanced_subsample",
                            max_features="sqrt",
                            n_jobs=1,
                            random_state=seed,
                        ),
                    )
                ]
            ),
            param_grid={
                "model__max_depth": forest_depth,
                "model__min_samples_leaf": forest_leaf,
            },
        ),
        "mlp": ModelSpec(
            estimator=Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        MLPClassifier(
                            max_iter=2000,
                            early_stopping=True,
                            random_state=seed,
                        ),
                    ),
                ]
            ),
            param_grid={
                "model__hidden_layer_sizes": [(32,), (32, 16)] if not quick else [(32,)],
                "model__alpha": [0.0001, 0.001, 0.01] if not quick else [0.001],
                "model__learning_rate_init": [0.0003, 0.001] if not quick else [0.001],
            },
        ),
    }
    try:
        from xgboost import XGBClassifier

        specs["xgboost"] = ModelSpec(
            estimator=Pipeline(
                [
                    (
                        "model",
                        XGBClassifier(
                            objective="binary:logistic",
                            eval_metric="logloss",
                            n_jobs=1,
                            random_state=seed,
                        ),
                    )
                ]
            ),
            param_grid={
                "model__n_estimators": [100, 200] if not quick else [100],
                "model__max_depth": [2, 3] if not quick else [2],
                "model__learning_rate": [0.03, 0.1] if not quick else [0.1],
                "model__subsample": [0.8],
                "model__colsample_bytree": [0.8, 1.0] if not quick else [1.0],
            },
        )
    except ImportError:
        pass
    return specs


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


def _grid_search(
    spec: ModelSpec,
    features: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    inner_splits: int,
    seed: int,
    n_jobs: int,
) -> GridSearchCV:
    cv = _inner_splits(features, labels, groups, inner_splits, seed)
    search = GridSearchCV(
        estimator=spec.estimator,
        param_grid=spec.param_grid,
        scoring="roc_auc",
        cv=cv,
        n_jobs=n_jobs,
        refit=True,
        error_score="raise",
        return_train_score=False,
    )
    search.fit(features, labels)
    return search


def _jsonable_params(params: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(params, default=str))


def _summarize(
    fold_metrics: pd.DataFrame, predictions: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["representation", "model"]
    for (representation, model), group in predictions.groupby(keys, sort=False):
        metrics = binary_metrics(group["y_true"], group["y_pred"], group["y_score"])
        fold_group = fold_metrics[
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
            row[f"fold_mean_{metric}"] = float(fold_group[metric].mean())
            row[f"fold_std_{metric}"] = float(fold_group[metric].std(ddof=1))
        rows.append(row)
    summary = pd.DataFrame(rows)
    return summary.sort_values(
        ["auroc", "mcc"], ascending=[False, False], kind="stable"
    ).reset_index(drop=True)


def run_development_oof(
    train: pd.DataFrame,
    models: Iterable[str],
    representations: Iterable[str],
    *,
    seed: int,
    inner_splits: int,
    n_jobs: int,
    quick: bool = False,
) -> ExperimentTables:
    """Run nested model selection with frozen structure-aware outer folds."""

    available_models = model_specs(seed, quick)
    model_names = list(models)
    representation_names = list(representations)
    unknown_models = sorted(set(model_names) - set(available_models))
    unknown_representations = sorted(set(representation_names) - set(FEATURE_SETS))
    if unknown_models:
        raise ValueError(f"Unknown models: {unknown_models}")
    if unknown_representations:
        raise ValueError(f"Unknown representations: {unknown_representations}")

    folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    labels_all = train["LABEL"].astype(int).to_numpy()
    fold_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []

    for representation in representation_names:
        feature_names = FEATURE_SETS[representation]
        features_all = train.loc[:, feature_names].to_numpy(dtype=float)
        for model_name in model_names:
            spec = available_models[model_name]
            for outer_fold in OUTER_FOLDS:
                started = time.perf_counter()
                train_mask = folds != outer_fold
                validation_mask = folds == outer_fold

                x_train = features_all[train_mask]
                y_train = labels_all[train_mask]
                groups_train = train.loc[train_mask, "BUTINA_CLUSTER_ID"].to_numpy()
                x_validation = features_all[validation_mask]
                y_validation = labels_all[validation_mask]

                search = _grid_search(
                    spec,
                    x_train,
                    y_train,
                    groups_train,
                    inner_splits,
                    seed + outer_fold,
                    n_jobs,
                )
                prediction = search.predict(x_validation).astype(int)
                score = continuous_scores(search, x_validation)
                metrics = binary_metrics(y_validation, prediction, score)
                elapsed = time.perf_counter() - started

                fold_rows.append(
                    {
                        "evaluation_status": "development_oof",
                        "representation": representation,
                        "n_features": len(feature_names),
                        "model": model_name,
                        "outer_fold": outer_fold,
                        "n_train": int(train_mask.sum()),
                        "n_validation": int(validation_mask.sum()),
                        "positive_prevalence": float(y_validation.mean()),
                        "best_inner_auroc": float(search.best_score_),
                        "elapsed_seconds": float(elapsed),
                        **metrics,
                    }
                )
                parameter_rows.append(
                    {
                        "evaluation_status": "development_oof",
                        "representation": representation,
                        "model": model_name,
                        "outer_fold": outer_fold,
                        "best_inner_auroc": float(search.best_score_),
                        "best_params": _jsonable_params(search.best_params_),
                    }
                )

                validation_rows = train.loc[
                    validation_mask,
                    ["ID", "BUTINA_CLUSTER_ID", "STRICT_CV_FOLD", "LABEL"],
                ]
                for row, predicted, scored in zip(
                    validation_rows.itertuples(index=False), prediction, score
                ):
                    prediction_rows.append(
                        {
                            "evaluation_status": "development_oof",
                            "representation": representation,
                            "n_features": len(feature_names),
                            "model": model_name,
                            "ID": int(row.ID),
                            "BUTINA_CLUSTER_ID": int(row.BUTINA_CLUSTER_ID),
                            "outer_fold": int(row.STRICT_CV_FOLD),
                            "y_true": int(row.LABEL),
                            "y_pred": int(predicted),
                            "y_score": float(scored),
                        }
                    )

    fold_frame = pd.DataFrame(fold_rows)
    prediction_frame = pd.DataFrame(prediction_rows)
    expected_predictions = len(train) * len(model_names) * len(representation_names)
    if len(prediction_frame) != expected_predictions:
        raise RuntimeError(
            f"Expected {expected_predictions} OOF predictions; got {len(prediction_frame)}"
        )
    duplicate_key = ["representation", "model", "ID"]
    if prediction_frame.duplicated(duplicate_key).any():
        raise RuntimeError("Each model/representation must score every ID exactly once")

    return ExperimentTables(
        fold_metrics=fold_frame,
        predictions=prediction_frame,
        summary=_summarize(fold_frame, prediction_frame),
        best_params=parameter_rows,
    )


def run_historical_holdout(
    train: pd.DataFrame,
    test: pd.DataFrame,
    models: Iterable[str],
    representations: Iterable[str],
    *,
    seed: int,
    n_jobs: int,
    quick: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    """Fit on all development rows and evaluate the previously inspected holdout."""

    available_models = model_specs(seed, quick)
    frozen_folds = train["STRICT_CV_FOLD"].astype(int).to_numpy()
    frozen_cv = [
        (np.flatnonzero(frozen_folds != fold), np.flatnonzero(frozen_folds == fold))
        for fold in OUTER_FOLDS
    ]
    labels = train["LABEL"].astype(int).to_numpy()
    test_labels = test["LABEL"].astype(int).to_numpy()
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []

    for representation in representations:
        feature_names = FEATURE_SETS[representation]
        x_train = train.loc[:, feature_names].to_numpy(dtype=float)
        x_test = test.loc[:, feature_names].to_numpy(dtype=float)
        for model_name in models:
            spec = available_models[model_name]
            started = time.perf_counter()
            search = GridSearchCV(
                estimator=spec.estimator,
                param_grid=spec.param_grid,
                scoring="roc_auc",
                cv=frozen_cv,
                n_jobs=n_jobs,
                refit=True,
                error_score="raise",
            )
            search.fit(x_train, labels)
            prediction = search.predict(x_test).astype(int)
            score = continuous_scores(search, x_test)
            metrics = binary_metrics(test_labels, prediction, score)
            metric_rows.append(
                {
                    "evaluation_status": "historical_holdout",
                    "representation": representation,
                    "n_features": len(feature_names),
                    "model": model_name,
                    "n_molecules": len(test),
                    "positive_prevalence": float(test_labels.mean()),
                    "selection_cv_auroc": float(search.best_score_),
                    "elapsed_seconds": float(time.perf_counter() - started),
                    **metrics,
                }
            )
            parameter_rows.append(
                {
                    "evaluation_status": "historical_holdout",
                    "representation": representation,
                    "model": model_name,
                    "best_cv_auroc": float(search.best_score_),
                    "best_params": _jsonable_params(search.best_params_),
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
                        "model": model_name,
                        "ID": int(row.ID),
                        "BUTINA_CLUSTER_ID": int(row.BUTINA_CLUSTER_ID),
                        "y_true": int(row.LABEL),
                        "y_pred": int(predicted),
                        "y_score": float(scored),
                    }
                )

    return (
        pd.DataFrame(metric_rows).sort_values("auroc", ascending=False),
        pd.DataFrame(prediction_rows),
        parameter_rows,
    )
