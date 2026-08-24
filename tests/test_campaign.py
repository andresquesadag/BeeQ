"""Campaign-level model availability and configuration invariants."""

from src.classical_models import model_specs


def test_complete_classical_model_set_is_available() -> None:
    assert set(model_specs(seed=42)) == {
        "logistic",
        "rbf_svc",
        "random_forest",
        "xgboost",
        "mlp",
    }
