"""Serializable estimators used by the BeeQ deployment packages."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.utils.validation import check_is_fitted

from .kernels import assert_valid_gram, fidelity_kernel
from .quantum_feature_maps import iqp_zz_linear_statevectors


class ExactIQPZZKernelSVC(ClassifierMixin, BaseEstimator):
    """Exact-statevector IQP-ZZ fidelity-kernel classifier.

    The estimator stores the fitted scaler, reference statevectors, and the
    precomputed-kernel SVC so that a package can score new X10 rows without
    retraining or access to the original CSV.
    """

    def __init__(
        self,
        *,
        c: float = 1.0,
        feature_scale: float = 0.125,
        interaction_strength: float = 1.0,
        class_weight: str | dict[int, float] | None = "balanced",
        random_state: int = 42,
    ) -> None:
        self.c = c
        self.feature_scale = feature_scale
        self.interaction_strength = interaction_strength
        self.class_weight = class_weight
        self.random_state = random_state

    @staticmethod
    def _values(features: Any) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        if values.ndim != 2 or values.shape[1] < 1:
            raise ValueError("features must be a non-empty two-dimensional matrix")
        if not np.isfinite(values).all():
            raise ValueError("features must contain only finite values")
        return values

    def fit(self, features: Any, labels: Any) -> "ExactIQPZZKernelSVC":
        values = self._values(features)
        target = np.asarray(labels, dtype=int).reshape(-1)
        if len(values) != len(target):
            raise ValueError("features and labels must contain the same number of rows")
        if set(np.unique(target)) != {0, 1}:
            raise ValueError("training labels must contain both binary classes")
        if self.c <= 0 or self.feature_scale <= 0 or self.interaction_strength < 0:
            raise ValueError("invalid IQP-ZZ deployment hyperparameters")

        self.n_features_in_ = values.shape[1]
        self.training_rows_ = len(values)
        self.scaler_ = StandardScaler().fit(values)
        scaled = self.scaler_.transform(values)
        self.reference_states_ = iqp_zz_linear_statevectors(
            self.feature_scale * scaled,
            interaction_strength=self.interaction_strength,
        )
        train_kernel = fidelity_kernel(self.reference_states_)
        assert_valid_gram(train_kernel, atol=1e-7)
        self.classifier_ = SVC(
            C=self.c,
            kernel="precomputed",
            class_weight=self.class_weight,
            random_state=self.random_state,
        )
        self.classifier_.fit(train_kernel, target)
        self.classes_ = self.classifier_.classes_
        return self

    def _cross_kernel(self, features: Any) -> np.ndarray:
        check_is_fitted(self, ("scaler_", "reference_states_", "classifier_"))
        values = self._values(features)
        if values.shape[1] != self.n_features_in_:
            raise ValueError(
                f"expected {self.n_features_in_} features; received {values.shape[1]}"
            )
        scaled = self.scaler_.transform(values)
        states = iqp_zz_linear_statevectors(
            self.feature_scale * scaled,
            interaction_strength=self.interaction_strength,
        )
        return fidelity_kernel(states, self.reference_states_)

    def predict(self, features: Any) -> np.ndarray:
        return self.classifier_.predict(self._cross_kernel(features)).astype(int)

    def decision_function(self, features: Any) -> np.ndarray:
        return np.asarray(
            self.classifier_.decision_function(self._cross_kernel(features)),
            dtype=float,
        ).reshape(-1)
