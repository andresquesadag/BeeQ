import unittest

from src.evaluation import binary_metrics


class EvaluationTests(unittest.TestCase):
    def test_perfect_classifier(self):
        metrics = binary_metrics(
            [0, 0, 1, 1],
            [0, 0, 1, 1],
            [0.01, 0.2, 0.8, 0.99],
        )
        self.assertEqual(metrics["auroc"], 1.0)
        self.assertEqual(metrics["mcc"], 1.0)
        self.assertEqual(metrics["balanced_accuracy"], 1.0)

    def test_rejects_single_class_truth(self):
        with self.assertRaises(ValueError):
            binary_metrics([0, 0], [0, 0], [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
