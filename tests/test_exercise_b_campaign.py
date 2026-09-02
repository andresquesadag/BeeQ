import itertools

import numpy as np

from src.exercise_a_campaign import exact_chain_fidelity_kernel
from src.exercise_b_campaign import (
    all_pairs,
    canonical_path,
    held_karp_paths,
    path_statistics,
    validate_pair_enumeration,
)


def test_exactly_45_unordered_pairs_and_nine_occurrences() -> None:
    pairs = all_pairs()
    assert len(pairs) == len(set(pairs)) == 45
    counts = {index: 0 for index in range(10)}
    for left, right in pairs:
        assert left < right
        counts[left] += 1
        counts[right] += 1
    assert set(counts.values()) == {9}
    assert len(validate_pair_enumeration()) == 45


def test_pair_reversal_kernel_symmetry() -> None:
    rng = np.random.default_rng(20260824)
    pair = rng.normal(size=(8, 2))
    forward = exact_chain_fidelity_kernel(pair)
    reverse = exact_chain_fidelity_kernel(pair[:, ::-1])
    assert np.max(np.abs(forward - reverse)) < 1e-12


def test_canonical_path_equals_reverse() -> None:
    path = (3, 1, 8, 0, 2)
    assert canonical_path(path) == canonical_path(path[::-1])


def test_held_karp_matches_bruteforce_small_graph() -> None:
    weights = np.array(
        [
            [0.0, 8.0, 2.0, 1.0],
            [8.0, 0.0, 7.0, 2.0],
            [2.0, 7.0, 0.0, 6.0],
            [1.0, 2.0, 6.0, 0.0],
        ]
    )
    observed = held_karp_paths(weights, top_k=1)[0]
    brute = max(
        itertools.permutations(range(4)),
        key=lambda path: path_statistics(path, weights)[0],
    )
    assert path_statistics(observed, weights)[0] == path_statistics(brute, weights)[0]


def test_held_karp_is_deterministic() -> None:
    rng = np.random.default_rng(4)
    raw = rng.normal(size=(6, 6))
    weights = (raw + raw.T) / 2
    np.fill_diagonal(weights, 0)
    assert held_karp_paths(weights, top_k=2) == held_karp_paths(weights, top_k=2)
