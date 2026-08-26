import numpy as np

from src.final_nested_campaign import classification_metrics, qc_kernel, select_threshold


def test_threshold_is_selected_from_scores_and_maximizes_mcc():
    labels = np.array([0, 0, 1, 1])
    scores = np.array([-0.4, -0.1, 0.2, 0.8])
    threshold, metrics = select_threshold(labels, scores)
    assert threshold == 0.2
    assert metrics["mcc"] == 1.0
    assert classification_metrics(labels, scores, threshold)["balanced_accuracy"] == 1.0


def test_quantum_qc_records_requested_values():
    rows = []
    qc_kernel(np.eye(3), model="quantum_angle_product", stage="unit", fold=1, params={"feature_scale": 1.0}, rows=rows)
    assert rows[0]["PASS"] is True
    assert rows[0]["SYMMETRY_ERROR"] == 0.0
    assert rows[0]["DIAGONAL_ERROR"] == 0.0
    assert rows[0]["MIN_EIGENVALUE"] == 1.0
