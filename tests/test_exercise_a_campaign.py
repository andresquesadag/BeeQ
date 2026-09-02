import json

import numpy as np

from src.exercise_a_campaign import (
    BASELINE,
    COMPLEMENTARY,
    DUPLICATE,
    atomic_json,
    encode_features,
    exact_chain_fidelity_kernel,
    kernel_qc,
)
from src.kernels import fidelity_kernel
from src.quantum_feature_maps import iqp_zz_linear_statevectors


def test_exact_chain_matches_materialized_statevector() -> None:
    rng = np.random.default_rng(20260824)
    x = rng.normal(size=(5, 6))
    y = rng.normal(size=(4, 6))
    expected_train = fidelity_kernel(iqp_zz_linear_statevectors(x))
    expected_cross = fidelity_kernel(
        iqp_zz_linear_statevectors(y), iqp_zz_linear_statevectors(x)
    )
    assert np.max(np.abs(exact_chain_fidelity_kernel(x) - expected_train)) < 1e-12
    assert np.max(np.abs(exact_chain_fidelity_kernel(y, x) - expected_cross)) < 1e-12


def test_twenty_qubit_encodings_are_interleaved() -> None:
    values = np.arange(1.0, 11.0)[None, :]
    duplicate = encode_features(values, DUPLICATE)
    complementary = encode_features(values, COMPLEMENTARY)
    assert duplicate.shape == complementary.shape == (1, 20)
    assert np.array_equal(duplicate[0, 0::2], values[0])
    assert np.array_equal(duplicate[0, 1::2], values[0])
    assert np.array_equal(complementary[0, 0::2], values[0])
    assert np.allclose(complementary[0, 1::2], np.sqrt(values[0]))


def test_idle_fixed_qubits_preserve_baseline_kernel() -> None:
    rng = np.random.default_rng(7)
    states = iqp_zz_linear_statevectors(rng.normal(size=(3, 10)))
    fixed = np.zeros(1 << 10, dtype=complex)
    fixed[0] = 1.0
    idle_states = (states[:, :, None] * fixed[None, None, :]).reshape(3, -1)
    assert np.max(np.abs(fidelity_kernel(states) - fidelity_kernel(idle_states))) < 1e-12


def test_kernel_qc_and_determinism() -> None:
    rng = np.random.default_rng(11)
    x = rng.normal(size=(12, 10))
    first = exact_chain_fidelity_kernel(x, block_rows=3)
    second = exact_chain_fidelity_kernel(x, block_rows=7)
    assert np.array_equal(first, second)
    row = kernel_qc(
        first,
        model=BASELINE,
        stage="test",
        outer_fold=0,
        inner_fold=0,
        scale=1.0,
    )
    assert row["PASS"]
    assert row["SYMMETRY_ERROR"] < 1e-10
    assert row["DIAGONAL_ERROR"] < 1e-10
    assert row["MIN_EIGENVALUE"] >= -1e-8


def test_atomic_checkpoint_replaces_complete_json(tmp_path) -> None:
    path = tmp_path / "outer_fold_1.json"
    atomic_json(path, {"status": "complete", "fold": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "fold": 1,
        "status": "complete",
    }
    assert list(tmp_path.glob("*.tmp")) == []
