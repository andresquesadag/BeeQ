"""Compatibility entry point for the exact NumPy quantum feature maps."""

from __future__ import annotations

import numpy as np

from .kernels import assert_valid_gram, fidelity_kernel
from .quantum_feature_maps import FEATURE_MAPS


def main() -> None:
    sample = np.array(
        [[0.0, 0.2, -0.4], [0.1, -0.3, 0.7], [0.9, 0.2, -0.1]],
        dtype=float,
    )
    for name, feature_map in FEATURE_MAPS.items():
        states = feature_map(sample)
        kernel = fidelity_kernel(states)
        assert_valid_gram(kernel)
        print(f"{name}: states={states.shape}, kernel={kernel.shape}, valid=True")


if __name__ == "__main__":
    main()
