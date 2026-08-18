"""Exact NumPy statevector feature maps for the phase-3 simulator baseline."""

from __future__ import annotations

import numpy as np


def _angles(features: np.ndarray) -> np.ndarray:
    values = np.asarray(features, dtype=float)
    if values.ndim != 2 or values.shape[1] < 1:
        raise ValueError("features must have shape (samples, qubits)")
    if not np.isfinite(values).all():
        raise ValueError("features must be finite")
    return values


def angle_product_statevectors(features: np.ndarray) -> np.ndarray:
    """Encode one descriptor per qubit with independent RY rotations."""

    values = _angles(features)
    states = np.ones((len(values), 1), dtype=complex)
    for column in range(values.shape[1]):
        half_angle = values[:, column] / 2.0
        local = np.column_stack([np.cos(half_angle), np.sin(half_angle)])
        states = (states[:, :, None] * local[:, None, :]).reshape(len(values), -1)
    return states


def iqp_zz_linear_statevectors(
    features: np.ndarray, *, interaction_strength: float = 1.0
) -> np.ndarray:
    """Encode descriptors in an IQP-style phase map with linear ZZ coupling.

    The exact simulator starts in a uniform superposition and applies diagonal
    Z and nearest-neighbor ZZ phases. It is deterministic and requires no
    Qiskit backend or hardware credentials.
    """

    values = _angles(features)
    if interaction_strength < 0:
        raise ValueError("interaction_strength must be non-negative")
    n_qubits = values.shape[1]
    dimension = 1 << n_qubits
    basis = np.arange(dimension, dtype=np.uint64)[:, None]
    positions = np.arange(n_qubits, dtype=np.uint64)[None, :]
    bits = ((basis >> positions) & 1).astype(float)
    signs = 1.0 - 2.0 * bits

    phases = values @ signs.T
    if n_qubits > 1 and interaction_strength:
        interactions = values[:, :-1] * values[:, 1:]
        zz_signs = signs[:, :-1] * signs[:, 1:]
        phases += interaction_strength * interactions @ zz_signs.T
    return np.exp(1j * phases) / np.sqrt(dimension)


FEATURE_MAPS = {
    "angle_product": angle_product_statevectors,
    "iqp_zz_linear": iqp_zz_linear_statevectors,
}
