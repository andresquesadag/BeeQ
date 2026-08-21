"""Safe loading and run-boundary helpers for future external validation.

The runtime only accepts an explicitly versioned package whose manifest matches
the BeeQ X10 contract. It never treats saved result tables as predictors and it
does not compute descriptors from SMILES.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import PROJECT_ROOT, X10_FEATURES


BASELINE_RESULTS_DIR = PROJECT_ROOT / "results" / "final" / "20260818T070959Z_f1f76c91f3"
OUTPUT_ROOT = PROJECT_ROOT / "external_validation" / "output"
DEPLOYMENT_PACKAGE_ROOT = PROJECT_ROOT / "deployment_baseline" / "model_packages"
EXPECTED_ENDPOINT = {
    "positive": "acute LD50 <= 11 microgram/bee",
    "negative": "acute LD50 > 11 microgram/bee",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _schema_hash(features: tuple[str, ...] | list[str]) -> str:
    payload = json.dumps(list(features), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LoadedModelPackage:
    """A validated, trusted serialized model and its immutable manifest."""

    model: Any
    manifest: dict[str, Any]
    package_dir: Path


def load_baseline_provenance(
    baseline_dir: str | Path = BASELINE_RESULTS_DIR,
) -> dict[str, Any]:
    """Read aggregate baseline provenance without treating it as a model."""

    directory = Path(baseline_dir).resolve()
    if directory == PROJECT_ROOT or not directory.is_dir():
        raise ValueError("baseline_results_dir must be an existing result directory")
    manifest_path = directory / "manifest.json"
    metrics_path = directory / "all_metrics.csv"
    if not manifest_path.is_file() or not metrics_path.is_file():
        raise ValueError("baseline reference must contain manifest.json and all_metrics.csv")
    return {
        "baseline_results_dir": str(directory),
        "manifest_sha256": _sha256(manifest_path),
        "metrics_sha256": _sha256(metrics_path),
        "read_only": True,
    }


def load_model_package(package_dir: str | Path) -> LoadedModelPackage:
    """Validate and load one explicitly versioned model package.

    The package must contain ``manifest.json`` and the artifact named by its
    manifest. The artifact is loaded only after its SHA-256 and compatibility
    contract have been checked. No default or implicit model is selected.
    """

    directory = Path(package_dir).resolve()
    manifest_path = directory / "manifest.json"
    if not directory.is_dir() or not manifest_path.is_file():
        raise ValueError("model package must be a directory containing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "package_schema_version",
        "model_version",
        "model_name",
        "artifact",
        "artifact_sha256",
        "feature_order",
        "feature_schema_sha256",
        "preprocessing",
        "threshold_policy",
        "endpoint",
        "baseline_provenance",
        "approval_status",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"model package manifest missing fields: {missing}")
    if manifest["package_schema_version"] != 1:
        raise ValueError("unsupported model package schema version")
    if manifest["approval_status"] != "approved_for_external_validation":
        raise ValueError("model package is not approved for external validation")
    if tuple(manifest["feature_order"]) != X10_FEATURES:
        raise ValueError("model package feature order does not match BeeQ X10")
    if manifest["feature_schema_sha256"] != _schema_hash(X10_FEATURES):
        raise ValueError("model package feature schema hash does not match BeeQ X10")
    if any(manifest["endpoint"].get(key) != value for key, value in EXPECTED_ENDPOINT.items()):
        raise ValueError("model package endpoint is incompatible with BeeQ")
    if not manifest["baseline_provenance"].get("results_dir"):
        raise ValueError("model package must identify its baseline results provenance")
    artifact = directory / manifest["artifact"]
    if not artifact.is_file() or _sha256(artifact) != manifest["artifact_sha256"]:
        raise ValueError("model package artifact is missing or has an invalid hash")
    with artifact.open("rb") as stream:
        model = pickle.load(stream)
    if not hasattr(model, "predict"):
        raise ValueError("model artifact does not implement predict")
    return LoadedModelPackage(model=model, manifest=manifest, package_dir=directory)


def load_approved_model_packages(
    package_root: str | Path = DEPLOYMENT_PACKAGE_ROOT,
) -> dict[str, LoadedModelPackage]:
    """Load the authoritative approved RF/RBF deployment pair only."""

    root = Path(package_root).resolve()
    if root != DEPLOYMENT_PACKAGE_ROOT.resolve():
        raise ValueError("approved packages must be loaded from deployment_baseline/model_packages")
    packages = {
        "random_forest": load_model_package(root / "random_forest"),
        "rbf_svc": load_model_package(root / "rbf_svc"),
    }
    for expected_name, package in packages.items():
        if package.manifest["model_name"] != expected_name:
            raise ValueError("deployment package model name does not match its approved slot")
    return packages


def validate_external_frame(frame: pd.DataFrame) -> None:
    """Validate public input columns without logging row values or structures."""

    required = {"sample_id", "smiles", "data_source"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"external input missing required columns: {missing}")
    if frame.empty:
        raise ValueError("external input is empty")
    if frame["sample_id"].isna().any() or frame["sample_id"].duplicated().any():
        raise ValueError("sample_id values must be unique and non-null")
    if frame["smiles"].isna().any() or frame["smiles"].eq("").any():
        raise ValueError("smiles values must be non-null and non-empty")
    if "observed_label" in frame.columns:
        labels = pd.to_numeric(frame["observed_label"], errors="coerce").dropna()
        if not labels.isin([0, 1]).all():
            raise ValueError("observed_label values must be binary 0/1 when supplied")


def score_x10_features(
    package: LoadedModelPackage,
    features: pd.DataFrame,
) -> np.ndarray:
    """Score already-approved X10 features; descriptor generation is out of scope."""

    if tuple(features.columns) != X10_FEATURES:
        raise ValueError("feature matrix must use the exact ordered BeeQ X10 columns")
    values = features.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("feature matrix contains missing or non-finite values")
    return np.asarray(package.model.predict(features), dtype=int)


def _continuous_score(model: Any, features: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        probabilities = np.asarray(model.predict_proba(features), dtype=float)
        return probabilities[:, 1]
    if hasattr(model, "decision_function"):
        return np.asarray(model.decision_function(features), dtype=float)
    raise ValueError("model artifact must implement predict_proba or decision_function")


def score_side_by_side(
    packages: dict[str, LoadedModelPackage],
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Return predictions, ranking scores, and disagreement for compatible packages."""

    if set(packages) != {"random_forest", "rbf_svc"}:
        raise ValueError("exactly the approved random_forest and rbf_svc packages are required")
    if tuple(features.columns) != X10_FEATURES:
        raise ValueError("feature matrix must use the exact ordered BeeQ X10 columns")
    values = features.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("feature matrix contains missing or non-finite values")
    result = pd.DataFrame(index=features.index)
    for name in ("random_forest", "rbf_svc"):
        model = packages[name].model
        result[f"{name}_prediction"] = np.asarray(model.predict(features), dtype=int)
        result[f"{name}_score"] = _continuous_score(model, features)
    result["model_disagreement"] = (
        result["random_forest_prediction"] != result["rbf_svc_prediction"]
    )
    return result.reset_index(drop=True)


def create_private_run_dir(output_root: str | Path = OUTPUT_ROOT) -> Path:
    """Create a unique run directory and refuse to overlap the baseline bundle."""

    root = Path(output_root).resolve()
    baseline = BASELINE_RESULTS_DIR.resolve()
    if root == baseline or baseline.is_relative_to(root):
        raise ValueError("external output root must not contain the baseline results directory")
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        candidate = root / f"run-{secrets.token_hex(8)}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError("could not allocate a unique private external-validation run directory")
