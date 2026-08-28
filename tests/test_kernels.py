import unittest

import numpy as np

from src.kernels import (
    assert_valid_gram,
    centered_kernel_alignment,
    effective_rank,
    fidelity_kernel,
    rbf_kernel,
)
from src.quantum_feature_maps import (
    angle_product_statevectors,
    iqp_zz_linear_statevectors,
)


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.features = np.array(
            [[0.0, 0.2, -0.4], [0.1, -0.3, 0.7], [0.9, 0.2, -0.1]],
            dtype=float,
        )

    def test_rbf_is_valid(self):
        kernel = rbf_kernel(self.features, gamma=0.3)
        assert_valid_gram(kernel)

    def test_product_fidelity_is_valid(self):
        states = angle_product_statevectors(self.features)
        kernel = fidelity_kernel(states)
        assert_valid_gram(kernel)

    def test_iqp_fidelity_is_valid(self):
        states = iqp_zz_linear_statevectors(self.features)
        kernel = fidelity_kernel(states)
        assert_valid_gram(kernel)

    def test_kernel_diagnostics(self):
        kernel = rbf_kernel(self.features, gamma=0.3)
        self.assertAlmostEqual(centered_kernel_alignment(kernel, kernel), 1.0)
        self.assertGreaterEqual(effective_rank(kernel), 1.0)


if __name__ == "__main__":
    unittest.main()
