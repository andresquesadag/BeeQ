import unittest

from src.config import DEFAULT_DATA_DIR, OUTER_FOLDS, X10_FEATURES
from src.data import load_bundle


class HandoffDataTests(unittest.TestCase):
    @unittest.skipUnless(DEFAULT_DATA_DIR.is_dir(), "local handoff is not available")
    def test_local_handoff_contract(self):
        bundle = load_bundle()
        self.assertEqual(len(bundle.train), 712)
        self.assertEqual(len(bundle.test), 181)
        self.assertEqual(tuple(bundle.audit["feature_order"]), X10_FEATURES)
        self.assertEqual(
            set(bundle.train["STRICT_CV_FOLD"].astype(int).unique()),
            set(OUTER_FOLDS),
        )
        self.assertEqual(bundle.audit["overlap"]["butina_clusters"], 0)


if __name__ == "__main__":
    unittest.main()
