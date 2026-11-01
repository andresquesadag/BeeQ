import numpy as np
import pytest
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV

from src.classical_models import model_specs
from src.config import X10_FEATURES
from src.final_nested_campaign import SEED
from src.mlp_sensitivity import balanced_weights, checked_fit, search, assert_partition


def toy_frame():
    import pandas as pd
    rng = np.random.default_rng(100)
    x = rng.normal(size=(80, 10))
    frame = pd.DataFrame(x, columns=X10_FEATURES)
    frame["ID"] = np.arange(80)
    frame["BUTINA_CLUSTER_ID"] = np.arange(80)
    frame["LABEL"] = np.tile([0, 0, 0, 1], 20)
    return frame


def test_local_weight_formula_and_total_class_mass():
    y = np.array([0, 0, 0, 1])
    np.testing.assert_allclose(balanced_weights(y), [2/3, 2/3, 2/3, 2])
    # Changing the external population cannot enter this function.
    assert balanced_weights(np.array([0, 1, 1]))[0] == 1.5
    for invalid in ([0, 0], [0, 2], [], [[0, 1]]):
        with pytest.raises(ValueError):
            balanced_weights(np.asarray(invalid))


def test_weights_only_reach_mlp_and_native_split_is_preserved():
    frame = toy_frame()
    params = {"model__hidden_layer_sizes": (32,), "model__alpha": .001}
    audit = []
    original = checked_fit(frame, params, False, audit, "unit", "original", "1")
    balanced = checked_fit(frame, params, True, audit, "unit", "balanced", "1")
    np.testing.assert_array_equal(original.named_steps["scale"].mean_, balanced.named_steps["scale"].mean_)
    assert audit[0]["stopping_ids"] == audit[1]["stopping_ids"]
    assert audit[0]["gradient_ids"] == audit[1]["gradient_ids"]
    assert audit[1]["weight_sum"] == pytest.approx(len(frame))
    assert audit[0]["stopping_accuracy_weighted"] is False
    assert audit[1]["stopping_accuracy_weighted"] is True
    repeated = checked_fit(frame, params, True, [], "unit", "balanced", "1")
    x = frame[list(X10_FEATURES)].to_numpy()
    np.testing.assert_array_equal(balanced.predict_proba(x), repeated.predict_proba(x))


def test_manual_search_matches_original_grid_search_order_and_scores():
    frame = toy_frame()
    # Both classes in each split.
    splits = [(np.arange(40), np.arange(40, 80)), (np.arange(40, 80), np.arange(40))]
    spec = model_specs(SEED)["mlp"]
    original = GridSearchCV(clone(spec.estimator), spec.param_grid, scoring="roc_auc", cv=splits, refit=False, error_score="raise")
    original.fit(frame[list(X10_FEATURES)].to_numpy(), frame.LABEL.to_numpy())
    params, mean, sd = search(frame, splits, False, [], [], "unit", "toy")
    assert params == original.best_params_
    assert mean == pytest.approx(original.best_score_, abs=1e-14)
    assert sd == pytest.approx(original.cv_results_["std_test_score"][original.best_index_], abs=1e-14)


def test_group_leakage_is_rejected():
    frame = toy_frame()
    a, b = frame.iloc[:40].copy(), frame.iloc[40:].copy()
    assert_partition(a, b)
    b.iloc[0, b.columns.get_loc("BUTINA_CLUSTER_ID")] = a.BUTINA_CLUSTER_ID.iloc[0]
    with pytest.raises(RuntimeError, match="leakage"):
        assert_partition(a, b)
