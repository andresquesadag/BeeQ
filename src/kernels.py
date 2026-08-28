"""Classical/fidelity kernel construction and geometry diagnostics."""

from __future__ import annotations

import numpy as np


def rbf_kernel(
    x: np.ndarray, y: np.ndarray | None = None, *, gamma: float
) -> np.ndarray:
    """Compute an RBF Gram or cross-kernel matrix."""

    left = np.asarray(x, dtype=float)
    right = left if y is None else np.asarray(y, dtype=float)
    if left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[1]:
        raise ValueError("x and y must be 2D arrays with the same feature count")
    if gamma <= 0:
        raise ValueError("gamma must be positive")
    distances = (
        np.sum(left**2, axis=1)[:, None]
        + np.sum(right**2, axis=1)[None, :]
        - 2.0 * left @ right.T
    )
    np.maximum(distances, 0.0, out=distances)
    return np.exp(-gamma * distances)


def _normalized_states(states: np.ndarray) -> np.ndarray:
    array = np.asarray(states, dtype=complex)
    if array.ndim != 2:
        raise ValueError("Statevectors must be a 2D array")
    norms = np.linalg.norm(array, axis=1)
    if np.any(norms <= 0) or not np.isfinite(norms).all():
        raise ValueError("Each statevector must have a finite, nonzero norm")
    return array / norms[:, None]


def fidelity_kernel(
    states: np.ndarray, other_states: np.ndarray | None = None
) -> np.ndarray:
    """Compute |<psi(x)|psi(y)>|^2 from exact statevectors."""

    left = _normalized_states(states)
    right = left if other_states is None else _normalized_states(other_states)
    if left.shape[1] != right.shape[1]:
        raise ValueError("Statevector dimensions must match")
    overlaps = left @ right.conj().T
    kernel = np.abs(overlaps) ** 2
    return np.clip(kernel.real, 0.0, 1.0)


def center_kernel(kernel: np.ndarray) -> np.ndarray:
    matrix = np.asarray(kernel, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Kernel centering requires a square matrix")
    row_mean = matrix.mean(axis=1, keepdims=True)
    column_mean = matrix.mean(axis=0, keepdims=True)
    return matrix - row_mean - column_mean + matrix.mean()


def centered_kernel_alignment(left: np.ndarray, right: np.ndarray) -> float:
    """Return normalized Frobenius alignment between centered kernels."""

    left_centered = center_kernel(left)
    right_centered = center_kernel(right)
    numerator = float(np.sum(left_centered * right_centered))
    denominator = float(
        np.linalg.norm(left_centered, "fro") * np.linalg.norm(right_centered, "fro")
    )
    if denominator == 0:
        raise ValueError("Centered kernel alignment is undefined for zero norm")
    return numerator / denominator


def effective_rank(kernel: np.ndarray, tolerance: float = 1e-12) -> float:
    """Entropy-based effective rank for a symmetric PSD kernel."""

    matrix = np.asarray(kernel, dtype=float)
    eigenvalues = np.linalg.eigvalsh((matrix + matrix.T) / 2.0)
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    total = eigenvalues.sum()
    if total <= tolerance:
        return 0.0
    probabilities = eigenvalues[eigenvalues > tolerance] / total
    return float(np.exp(-np.sum(probabilities * np.log(probabilities))))


def assert_valid_gram(
    kernel: np.ndarray, *, atol: float = 1e-8, require_unit_diagonal: bool = True
) -> None:
    """Raise if a self-kernel is not finite, symmetric, and PSD."""

    matrix = np.asarray(kernel, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise AssertionError("Gram matrix must be square")
    if not np.isfinite(matrix).all():
        raise AssertionError("Gram matrix must be finite")
    if not np.allclose(matrix, matrix.T, atol=atol):
        raise AssertionError("Gram matrix must be symmetric")
    if require_unit_diagonal and not np.allclose(
        np.diag(matrix), 1.0, atol=atol
    ):
        raise AssertionError("Gram matrix must have a unit diagonal")
    if np.linalg.eigvalsh((matrix + matrix.T) / 2.0).min() < -atol:
        raise AssertionError("Gram matrix must be positive semidefinite")
