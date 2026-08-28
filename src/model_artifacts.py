"""Portable frozen model bundles produced by the final BeeQ campaign."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


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
