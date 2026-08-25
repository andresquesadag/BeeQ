"""Campaign-level model availability and configuration invariants."""

from src.classical_models import model_specs
from src.split_70_20_10 import EXTERNAL_ROWS, HOLDOUT_ROWS, TRAIN_ROWS


def test_complete_classical_model_set_is_available() -> None:
    assert set(model_specs(seed=42)) == {
        "logistic",
        "rbf_svc",
        "random_forest",
        "xgboost",
        "mlp",
    }


def test_requested_split_counts_cover_corrected_master() -> None:
    assert (TRAIN_ROWS, HOLDOUT_ROWS, EXTERNAL_ROWS) == (625, 179, 89)
    assert TRAIN_ROWS + HOLDOUT_ROWS + EXTERNAL_ROWS == 893
