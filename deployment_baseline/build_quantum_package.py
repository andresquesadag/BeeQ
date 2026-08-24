"""Build the approved full-reference BeeQ IQP-ZZ deployment package."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, X10_FEATURES
from src.data import load_bundle, sha256_file, sha256_json
from src.deployment_models import ExactIQPZZKernelSVC


MODEL_NAME = "quantum_iqp_zz_linear"
MODEL_VERSION = "beeq-x10-quantum_iqp_zz_linear-full-reference-v1"
QUANTUM_RUN = PROJECT_ROOT / "results" / "runs" / "20260818T070420Z_quantum_bfff644b61"
RESULTS_DIR = PROJECT_ROOT / "results" / "final" / "20260818T070959Z_f1f76c91f3"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _selected_parameters() -> tuple[dict[str, float], dict[str, Any]]:
    source = QUANTUM_RUN / "historical_holdout_best_params.json"
    rows = json.loads(source.read_text(encoding="utf-8"))
    matches = [
        row
        for row in rows
        if row["representation"] == "x10" and row["model"] == MODEL_NAME
    ]
    if len(matches) != 1:
        raise RuntimeError("could not resolve one frozen X10 IQP-ZZ parameter record")
    return matches[0]["best_params"], matches[0]


def build(output_root: Path, data_dir: Path | None = None) -> Path:
    bundle = load_bundle(data_dir)
    if bundle.master is None or len(bundle.master) != 893:
        raise RuntimeError("the deployment fit requires the validated 893-row master corpus")
    params, selection = _selected_parameters()
    expected = {"C": 1.0, "feature_scale": 0.125, "interaction_strength": 1.0}
    if params != expected:
        raise RuntimeError(f"frozen IQP-ZZ parameters changed: {params!r}")

    model = ExactIQPZZKernelSVC(
        c=float(params["C"]),
        feature_scale=float(params["feature_scale"]),
        interaction_strength=float(params["interaction_strength"]),
        class_weight="balanced",
        random_state=42,
    )
    features = bundle.master.loc[:, X10_FEATURES].to_numpy(dtype=float)
    labels = bundle.master["LABEL"].to_numpy(dtype=int)
    model.fit(features, labels)

    package_dir = output_root.resolve() / MODEL_NAME
    package_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = package_dir / "model.pkl"
    with artifact_path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)

    parameter_source = QUANTUM_RUN / "historical_holdout_best_params.json"
    manifest = {
        "applicability_policy": {
            "method": "standardized-X10 nearest-reference distance",
            "status": "implemented_by_external_validation_runtime_v1",
        },
        "approval_status": "approved_for_external_validation",
        "artifact": artifact_path.name,
        "artifact_sha256": _file_hash(artifact_path),
        "baseline_provenance": {
            "quantum_run_dir": str(QUANTUM_RUN.relative_to(PROJECT_ROOT)),
            "quantum_run_manifest_sha256": sha256_file(QUANTUM_RUN / "manifest.json"),
            "selection_record_sha256": sha256_file(parameter_source),
            "selection_used_development_labels_only": True,
            "historical_holdout_labels_used_for_parameter_selection": False,
            "results_dir": str(RESULTS_DIR.relative_to(PROJECT_ROOT)),
            "results_manifest_sha256": sha256_file(RESULTS_DIR / "manifest.json"),
            "export_is_not_an_original_evaluation_fit": True,
            "metrics_are_read_only_context": True,
        },
        "endpoint": bundle.audit["endpoint"],
        "feature_order": list(X10_FEATURES),
        "feature_schema_sha256": sha256_json(list(X10_FEATURES)),
        "fit_corpus": "893 curated reference molecules: development plus historical holdout",
        "fit_rows": 893,
        "fit_scope": "full_curated_reference_corpus",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "package_schema_version": 1,
        "preprocessing": {
            "backend": "exact_numpy_statevector",
            "class_weight": "balanced",
            "kernel": "IQP-ZZ nearest-neighbor linear coupling fidelity kernel",
            "pipeline": "src.deployment_models.ExactIQPZZKernelSVC",
            "random_seed": 42,
            "settings": params,
            "selection_cv_auroc": selection["best_cv_auroc"],
        },
        "source_data": {
            "feature_schema_sha256": bundle.audit["feature_schema_sha256"],
            "master_csv_sha256": bundle.audit["source_files"]["master.csv"],
            "split_sha256": bundle.audit["split_sha256"],
        },
        "threshold_policy": {
            "development_oof_sensitivity": {
                "criterion": "maximum Youden J on pooled structure-aware development OOF scores",
                "oof_predictions_sha256": sha256_file(QUANTUM_RUN / "oof_predictions.csv"),
                "threshold": -0.2578196419168673,
                "uses_external_labels": False,
            },
            "endpoint_threshold": "acute LD50 <= 11 microgram/bee",
            "primary_decision_policy": "serialized estimator class prediction (decision function >= 0)",
            "primary_threshold": 0.0,
            "score_type": "SVC decision function",
            "status": "frozen_for_external_validation_v1",
        },
    }
    (package_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return package_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "deployment_baseline" / "model_packages",
    )
    args = parser.parse_args()
    print(build(args.output_root, args.data_dir))


if __name__ == "__main__":
    main()
