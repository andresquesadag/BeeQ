import hashlib
import json
import unittest
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]


class DeliverableTests(unittest.TestCase):
    def test_master_notebook_is_executed_and_covers_five_phases(self):
        notebook = nbformat.read(ROOT / "notebooks" / "classic.ipynb", as_version=4)
        markdown = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "markdown"
        )
        for phase in range(1, 6):
            self.assertIn(f"## Fase {phase}", markdown)

        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        self.assertTrue(code_cells)
        self.assertTrue(all(cell.execution_count is not None for cell in code_cells))
        self.assertFalse(
            any(
                output.output_type == "error"
                for cell in code_cells
                for output in cell.outputs
            )
        )

        serialized_outputs = json.dumps(
            [output for cell in code_cells for output in cell.outputs],
            ensure_ascii=False,
        )
        self.assertIn("SMILES", serialized_outputs)
        self.assertIn("MolLogP", serialized_outputs)

    def test_latest_analysis_pointer_and_manifest(self):
        latest_path = ROOT / "results" / "final" / "latest.json"
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        analysis_dir = ROOT / latest["analysis_directory"]
        classical_dir = ROOT / latest["classical_run"]
        quantum_dir = ROOT / latest["quantum_run"]
        for directory in (analysis_dir, classical_dir, quantum_dir):
            self.assertTrue(directory.is_dir())
            self.assertTrue((directory / "manifest.json").is_file())

        manifest_bytes = (analysis_dir / "manifest.json").read_bytes()
        self.assertEqual(
            hashlib.sha256(manifest_bytes).hexdigest(), latest["manifest_sha256"]
        )
        for artifact in (
            "all_metrics.csv",
            "paired_bootstrap.csv",
            "prediction_disagreement.csv",
            "kernel_diagnostics_summary.csv",
            "holdout_error_strata.csv",
        ):
            self.assertTrue((analysis_dir / artifact).is_file())

        for run_dir in (classical_dir, quantum_dir):
            run_manifest = json.loads(
                (run_dir / "manifest.json").read_text(encoding="utf-8")
            )
            for relative_path, expected_hash in run_manifest["outputs"].items():
                self.assertEqual(
                    hashlib.sha256((run_dir / relative_path).read_bytes()).hexdigest(),
                    expected_hash,
                )

        analysis_manifest = json.loads(manifest_bytes)
        for relative_path, expected_hash in analysis_manifest["outputs"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest(),
                expected_hash,
            )

    def test_final_paper_matches_reviewed_manifest(self):
        paper = ROOT / "output" / "pdf" / "BeeQ_BIP2026.pdf"
        payload = paper.read_bytes()
        manifest = json.loads(
            (paper.parent / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertTrue(payload.startswith(b"%PDF-"))
        self.assertGreater(len(payload), 100_000)
        self.assertEqual(manifest["page_count"], 6)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(), manifest["paper_sha256"]
        )
        self.assertEqual(manifest["visual_review"], "passed_all_pages")


if __name__ == "__main__":
    unittest.main()
