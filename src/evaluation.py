"""Shared binary-classification metrics and score extraction."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


METRIC_COLUMNS = (
    "auroc",
    "auprc",
    "balanced_accuracy",
    "mcc",
    "accuracy",
    "precision",
    "recall",
    "f1",
)


def continuous_scores(estimator: Any, features: Any) -> np.ndarray:
    """Return positive-class scores suitable for AUROC/AUPRC."""

    if hasattr(estimator, "predict_proba"):
        probabilities = np.asarray(estimator.predict_proba(features))
        return probabilities[:, 1]
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(features)).reshape(-1)
    raise TypeError("Estimator must expose predict_proba or decision_function")


def binary_metrics(
    y_true: Any, y_pred: Any, y_score: Any
) -> dict[str, float]:
    """Calculate ranking and threshold metrics for the toxic class."""

    truth = np.asarray(y_true, dtype=int)
    predicted = np.asarray(y_pred, dtype=int)
    scores = np.asarray(y_score, dtype=float)
    if not (len(truth) == len(predicted) == len(scores)):
        raise ValueError("y_true, y_pred and y_score must have equal length")
    if set(np.unique(truth)) != {0, 1}:
        raise ValueError("Both binary classes must be present in y_true")
    if not np.isfinite(scores).all():
        raise ValueError("y_score must contain only finite values")

    return {
        "auroc": float(roc_auc_score(truth, scores)),
        "auprc": float(average_precision_score(truth, scores)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
        "mcc": float(matthews_corrcoef(truth, predicted)),
        "accuracy": float(accuracy_score(truth, predicted)),
        "precision": float(precision_score(truth, predicted, zero_division=0)),
        "recall": float(recall_score(truth, predicted, zero_division=0)),
        "f1": float(f1_score(truth, predicted, zero_division=0)),
    }
