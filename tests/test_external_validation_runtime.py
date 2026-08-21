import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from external_validation.runtime import (
    create_private_run_dir,
    load_model_package,
    validate_external_frame,
)


class ExternalValidationRuntimeTests(unittest.TestCase):
    def test_missing_package_is_blocked_before_model_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                load_model_package(directory)

    def test_input_validation_does_not_require_or_print_raw_records(self):
        frame = pd.DataFrame(
            {
                "sample_id": ["fixture-1"],
                "smiles": ["fixture-smiles"],
                "data_source": ["fixture-source"],
            }
        )
        validate_external_frame(frame)

    def test_run_directory_is_unique_and_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            first = create_private_run_dir(directory)
            second = create_private_run_dir(directory)
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())


if __name__ == "__main__":
    unittest.main()
