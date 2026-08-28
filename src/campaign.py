"""Run the complete corrected BeeQ comparison with one auditable command."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import PROJECT_ROOT
from .data import sha256_file, sha256_json, write_json
from .provenance import environment, git_state


CORRECTED_NAMES = {
    "train_RDKitFixed.csv": "train.csv",
    "test_RDKitFixed.csv": "test.csv",
    "master_RDKitFixed.csv": "master.csv",
    "ExternalFinal_RDKitFixed.csv": "external.csv",
}


def _run(command: list[str], log_path: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"Command failed; see {log_path}")


def _only_run(directory: Path) -> Path:
    runs = [path for path in directory.iterdir() if path.is_dir()]
    if len(runs) != 1:
        raise RuntimeError(f"Expected exactly one run under {directory}; found {runs}")
    return runs[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-data",
        type=Path,
        default=PROJECT_ROOT / "data" / "official",
    )
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "results" / "campaigns"
    )
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    source = args.source_data.resolve()
    source_paths = {name: source / name for name in CORRECTED_NAMES}
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing corrected inputs: {missing}")

    code_paths = [
        PROJECT_ROOT / "src" / "campaign.py",
        PROJECT_ROOT / "src" / "classical_models.py",
        PROJECT_ROOT / "src" / "quantum_experiment.py",
        PROJECT_ROOT / "src" / "external_challenge.py",
        PROJECT_ROOT / "src" / "split_70_20_10.py",
        PROJECT_ROOT / "configs" / "quantum.json",
    ]
    supplemental_names = [
        "split_manifest.json",
        "external_reference_match_audit.csv",
        "Externalset_reference_only.csv",
    ]
    supplemental_paths = {
        name: source / name
        for name in supplemental_names
        if (source / name).is_file()
    }
    config = {
        "schema_version": 1,
        "protocol": "beeq_corrected_complete_nested_v1",
        "seed": 42,
        "outer_folds": 5,
        "inner_folds": 4,
        "selection_metric": "roc_auc",
        "classical_models": ["logistic", "rbf_svc", "random_forest", "xgboost", "mlp"],
        "quantum_models": ["quantum_angle_product", "quantum_iqp_zz_linear"],
        "matched_kernel_control": "rbf_matched",
        "representation": "x10",
        "quick": bool(args.quick),
        "source_hashes": {name: sha256_file(path) for name, path in source_paths.items()},
        "supplemental_source_hashes": {
            name: sha256_file(path) for name, path in supplemental_paths.items()
        },
        "code_hashes": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): sha256_file(path)
            for path in code_paths
        },
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_{sha256_json(config)[:10]}"
    root = args.output_root.resolve() / run_id
    root.mkdir(parents=True, exist_ok=False)
    for name in ["data_snapshot", "classical", "quantum", "external", "audit", "logs"]:
        (root / name).mkdir()

    snapshot = root / "data_snapshot"
    for source_name, target_name in CORRECTED_NAMES.items():
        shutil.copy2(source_paths[source_name], snapshot / target_name)
    for name, path in supplemental_paths.items():
        shutil.copy2(path, root / "audit" / name)
    write_json(root / "run_config.json", config)
    write_json(root / "environment.json", environment())
    write_json(root / "git_state.json", git_state())

    python = sys.executable
    classical = [
        python, "-m", "src.experiment", "--data-dir", str(snapshot),
        "--output-root", str(root / "classical"), "--models",
        *config["classical_models"], "--representations", "x10",
        "--inner-splits", "4", "--n-jobs", "1", "--evaluate-holdout",
    ]
    if args.quick:
        classical.append("--quick")
    _run(classical, root / "logs" / "classical.log")
    classical_run = _only_run(root / "classical")

    _run(
        [
            python, "-m", "src.quantum_experiment", "--data-dir", str(snapshot),
            "--output-root", str(root / "quantum"), "--representations", "x10",
            "--kernels", "rbf_matched", "quantum_angle_product",
            "quantum_iqp_zz_linear",
        ],
        root / "logs" / "quantum.log",
    )
    quantum_run = _only_run(root / "quantum")

    _run(
        [
            python, "-m", "src.external_challenge", "--data-dir", str(source),
            "--classical-run", str(classical_run),
            "--quantum-run", str(quantum_run),
            "--output", str(root / "external"),
        ],
        root / "logs" / "external.log",
    )

    files = [path for path in root.rglob("*") if path.is_file() and path.name != "manifest.json"]
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "config_sha256": sha256_json(config),
        "outputs": {
            str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
            for path in sorted(files)
        },
    }
    write_json(root / "manifest.json", manifest)
    print(root)


if __name__ == "__main__":
    main()
