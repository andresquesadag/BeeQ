import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import numpy as np

from external_validation.runtime import (
    APPROVED_MODEL_ORDER,
    LoadedModelPackage,
    create_private_run_dir,
    load_model_package,
    score_side_by_side,
    validate_external_frame,
)
from src.config import X10_FEATURES
from src.deployment_models import ExactIQPZZKernelSVC


class ExternalValidationRuntimeTests(unittest.TestCase):
    def test_missing_package_is_blocked_before_model_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                load_model_package(directory)

    def test_input_validation_does_not_require_or_print_raw_records(self):
        frame = pd.DataFrame(
            {
                "sample_id": ["fixture-1"],
                "smiles": ["fixture-smiles"],
                "data_source": ["fixture-source"],
            }
        )
        validate_external_frame(frame)

    def test_run_directory_is_unique_and_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            first = create_private_run_dir(directory)
            second = create_private_run_dir(directory)
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_exact_iqp_zz_estimator_scores_unseen_rows(self):
        rng = np.random.default_rng(42)
        features = rng.normal(size=(12, len(X10_FEATURES)))
        labels = np.array([0, 1] * 6)
        model = ExactIQPZZKernelSVC().fit(features, labels)
        prediction = model.predict(features[:3])
        score = model.decision_function(features[:3])
        self.assertEqual(prediction.shape, (3,))
        self.assertEqual(score.shape, (3,))
        self.assertTrue(np.isfinite(score).all())

    def test_approved_quantum_package_is_loadable(self):
        root = Path(__file__).resolve().parents[1]
        package = load_model_package(
            root
            / "deployment_baseline"
            / "model_packages"
            / "quantum_iqp_zz_linear"
        )
        self.assertEqual(package.manifest["fit_rows"], 893)
        self.assertIsInstance(package.model, ExactIQPZZKernelSVC)

    def test_three_model_scoring_contract(self):
        class DummyModel:
            def __init__(self, prediction, score):
                self.prediction = prediction
                self.score = score

            def predict(self, features):
                return np.full(len(features), self.prediction)

            def decision_function(self, features):
                return np.full(len(features), self.score, dtype=float)

        packages = {
            name: LoadedModelPackage(
                model=DummyModel(index % 2, float(index)),
                manifest={},
                package_dir=Path("."),
            )
            for index, name in enumerate(APPROVED_MODEL_ORDER)
        }
        features = pd.DataFrame(
            np.zeros((2, len(X10_FEATURES))), columns=X10_FEATURES
        )
        scored = score_side_by_side(packages, features)
        self.assertEqual(len(scored), 2)
        self.assertTrue(scored["any_model_disagreement"].all())
        self.assertTrue((scored["positive_votes"] == 1).all())


if __name__ == "__main__":
    unittest.main()
