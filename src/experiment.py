"""Run versioned BeeQ classical experiments from a declarative config."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classical_models import run_development_oof, run_historical_holdout
from .config import DEFAULT_RESULTS_DIR, FEATURE_SETS, PROJECT_ROOT
from .data import load_bundle, sha256_file, sha256_json, write_json


def _git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    commit = run("rev-parse", "HEAD") or None
    status = run("status", "--porcelain")
    return {"commit": commit, "dirty": bool(status), "status": status.splitlines()}


def _environment() -> dict[str, Any]:
    packages = {}
    for name in ["numpy", "pandas", "scikit-learn", "matplotlib", "qiskit", "rdkit"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def _load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"seed", "inner_splits", "models", "representations"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Config is missing fields: {missing}")
    return config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "configs" / "classical.json"
    )
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--representations", nargs="+", default=None)
    parser.add_argument("--inner-splits", type=int, default=None)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--evaluate-holdout", action="store_true", default=None)
    return parser.parse_args()


def _write_outputs(
    output_dir: Path,
    run_config: dict[str, Any],
    bundle_audit: dict[str, Any],
    development: Any,
    holdout: tuple[Any, Any, list[dict[str, Any]]] | None,
    source_git_state: dict[str, Any],
    source_environment: dict[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=False)
    run_config_path = write_json(output_dir / "run_config.json", run_config)
    fold_path = output_dir / "fold_metrics.csv"
    prediction_path = output_dir / "oof_predictions.csv"
    summary_path = output_dir / "summary.csv"
    params_path = write_json(output_dir / "best_params.json", development.best_params)
    development.fold_metrics.to_csv(fold_path, index=False)
    development.predictions.to_csv(prediction_path, index=False)
    development.summary.to_csv(summary_path, index=False)

    output_paths = [run_config_path, fold_path, prediction_path, summary_path, params_path]
    holdout_status = "not_evaluated"
    if holdout is not None:
        holdout_metrics, holdout_predictions, holdout_params = holdout
        holdout_metrics_path = output_dir / "historical_holdout_metrics.csv"
        holdout_predictions_path = output_dir / "historical_holdout_predictions.csv"
        holdout_params_path = write_json(
            output_dir / "historical_holdout_best_params.json", holdout_params
        )
        holdout_metrics.to_csv(holdout_metrics_path, index=False)
        holdout_predictions.to_csv(holdout_predictions_path, index=False)
        output_paths.extend(
            [holdout_metrics_path, holdout_predictions_path, holdout_params_path]
        )
        holdout_status = "historical_holdout_previously_inspected"

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation": {
            "development": "nested_structure_aware_oof",
            "holdout": holdout_status,
        },
        "run_config_sha256": sha256_json(run_config),
        "dataset": bundle_audit,
        "git": source_git_state,
        "environment": source_environment,
        "outputs": {
            path.name: sha256_file(path)
            for path in output_paths
        },
    }
    return write_json(output_dir / "manifest.json", manifest)


def main() -> None:
    args = _parse_args()
    config = _load_config(args.config.resolve())
    source_git_state = _git_state()
    source_environment = _environment()
    models = args.models or config["models"]
    representations = args.representations or config["representations"]
    inner_splits = args.inner_splits or int(config["inner_splits"])
    evaluate_holdout = (
        bool(config.get("evaluate_historical_holdout", False))
        if args.evaluate_holdout is None
        else args.evaluate_holdout
    )
    unknown_representations = sorted(set(representations) - set(FEATURE_SETS))
    if unknown_representations:
        raise ValueError(f"Unknown representations: {unknown_representations}")

    bundle = load_bundle(args.data_dir)
    run_config = {
        "protocol": "classical_nested_structure_aware_v1",
        "seed": int(config["seed"]),
        "inner_splits": inner_splits,
        "primary_metric": "roc_auc",
        "models": list(models),
        "representations": list(representations),
        "feature_sets": {name: list(FEATURE_SETS[name]) for name in representations},
        "n_jobs": args.n_jobs,
        "quick_grid": bool(args.quick),
        "evaluate_historical_holdout": evaluate_holdout,
        "split_sha256": bundle.audit["split_sha256"],
        "feature_schema_sha256": bundle.audit["feature_schema_sha256"],
    }

    development = run_development_oof(
        bundle.train,
        models,
        representations,
        seed=run_config["seed"],
        inner_splits=inner_splits,
        n_jobs=args.n_jobs,
        quick=args.quick,
    )
    holdout = None
    if evaluate_holdout:
        holdout = run_historical_holdout(
            bundle.train,
            bundle.test,
            models,
            representations,
            seed=run_config["seed"],
            n_jobs=args.n_jobs,
            quick=args.quick,
        )

    fingerprint = sha256_json(run_config)[:10]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_root.resolve() / f"{timestamp}_{fingerprint}"
    _write_outputs(
        output_dir,
        run_config,
        bundle.audit,
        development,
        holdout,
        source_git_state,
        source_environment,
    )

    display_columns = [
        "representation",
        "model",
        "auroc",
        "auprc",
        "balanced_accuracy",
        "mcc",
    ]
    print(development.summary[display_columns].to_string(index=False))
    print(f"Run directory: {output_dir}")


if __name__ == "__main__":
    main()
