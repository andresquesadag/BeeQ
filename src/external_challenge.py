"""Score holdout and external data with development-selected parameters."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .classical_models import model_specs
from .config import X10_FEATURES
from .evaluation import binary_metrics, continuous_scores
from .quantum_experiment import _kernel_matrices


def _load_params(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_set(frame: pd.DataFrame) -> set[str]:
    result: set[str] = set()
    for smiles in frame["SMILES"].astype(str):
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise ValueError(f"Invalid SMILES: {smiles}")
        result.add(Chem.MolToSmiles(molecule))
    return result


def _overlap_report(internal: pd.DataFrame, external: pd.DataFrame) -> dict[str, object]:
    exact = set(internal["SMILES"].astype(str)) & set(external["SMILES"].astype(str))
    canonical = _canonical_set(internal) & _canonical_set(external)
    ids = set(internal["ID"]) & set(external["ID"])
    clusters = set(internal["BUTINA_CLUSTER_ID"]) & set(external["BUTINA_CLUSTER_ID"])
    return {
        "internal_rows": int(len(internal)),
        "external_rows": int(len(external)),
        "internal_unique_smiles": int(internal["SMILES"].nunique()),
        "external_unique_smiles": int(external["SMILES"].nunique()),
        "id_overlap": int(len(ids)),
        "exact_smiles_overlap": int(len(exact)),
        "canonical_smiles_overlap": int(len(canonical)),
        "butina_cluster_overlap": int(len(clusters)),
        "canonicalization": "RDKit",
    }


def _rows(
    evaluation: str,
    model: str,
    frame: pd.DataFrame,
    predicted: np.ndarray,
    score: np.ndarray,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    labels = frame["LABEL"].to_numpy(dtype=int)
    metric = {
        "evaluation": evaluation,
        "model": model,
        "n_molecules": int(len(frame)),
        "positive_prevalence": float(labels.mean()),
        **binary_metrics(labels, predicted, score),
        "positive_predictions": int(predicted.sum()),
    }
    predictions = [
        {
            "evaluation": evaluation,
            "model": model,
            "ID": int(row.ID),
            "y_true": int(row.LABEL),
            "y_pred": int(label),
            "y_score": float(value),
        }
        for row, label, value in zip(
            frame[["ID", "LABEL"]].itertuples(index=False), predicted, score
        )
    ]
    return metric, predictions


def _classical_scores(
    train: pd.DataFrame,
    evaluations: dict[str, pd.DataFrame],
    parameter_rows: list[dict[str, object]],
    seed: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    specs = model_specs(seed)
    x_train = train.loc[:, X10_FEATURES].to_numpy(dtype=float)
    y_train = train["LABEL"].to_numpy(dtype=int)
    metrics: list[dict[str, object]] = []
    predictions: list[dict[str, object]] = []
    for selection in parameter_rows:
        if selection["representation"] != "x10":
            continue
        name = str(selection["model"])
        estimator = specs[name].estimator
        estimator.set_params(**dict(selection["best_params"]))
        estimator.fit(x_train, y_train)
        for evaluation, frame in evaluations.items():
            features = frame.loc[:, X10_FEATURES].to_numpy(dtype=float)
            score = continuous_scores(estimator, features)
            predicted = estimator.predict(features).astype(int)
            metric, rows = _rows(evaluation, name, frame, predicted, score)
            metrics.append(metric)
            predictions.extend(rows)
    return metrics, predictions


def _quantum_scores(
    train: pd.DataFrame,
    evaluations: dict[str, pd.DataFrame],
    parameter_rows: list[dict[str, object]],
    seed: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    raw_train = train.loc[:, X10_FEATURES].to_numpy(dtype=float)
    labels = train["LABEL"].to_numpy(dtype=int)
    scaler = StandardScaler().fit(raw_train)
    scaled_train = scaler.transform(raw_train)
    metrics: list[dict[str, object]] = []
    predictions: list[dict[str, object]] = []
    for selection in parameter_rows:
        if selection["representation"] != "x10":
            continue
        name = str(selection["model"])
        params = dict(selection["best_params"])
        c_value = float(params.pop("C"))
        train_kernel, _ = _kernel_matrices(name, params, scaled_train)
        classifier = SVC(
            C=c_value,
            kernel="precomputed",
            class_weight="balanced",
            random_state=seed,
        ).fit(train_kernel, labels)
        for evaluation, frame in evaluations.items():
            scaled = scaler.transform(frame.loc[:, X10_FEATURES].to_numpy(dtype=float))
            _, cross_kernel = _kernel_matrices(name, params, scaled_train, scaled)
            assert cross_kernel is not None
            score = classifier.decision_function(cross_kernel).reshape(-1)
            predicted = classifier.predict(cross_kernel).astype(int)
            metric, rows = _rows(evaluation, name, frame, predicted, score)
            metrics.append(metric)
            predictions.extend(rows)
    return metrics, predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--classical-run", type=Path, required=True)
    parser.add_argument("--quantum-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(args.data_dir / "train_RDKitFixed.csv")
    holdout = pd.read_csv(args.data_dir / "test_RDKitFixed.csv")
    external = pd.read_csv(args.data_dir / "ExternalFinal_RDKitFixed.csv")
    internal = pd.read_csv(args.data_dir / "master_RDKitFixed.csv")
    evaluations = {"holdout": holdout, "external": external}

    classical_metrics, classical_predictions = _classical_scores(
        train,
        evaluations,
        _load_params(args.classical_run / "historical_holdout_best_params.json"),
        args.seed,
    )
    quantum_metrics, quantum_predictions = _quantum_scores(
        train,
        evaluations,
        _load_params(args.quantum_run / "historical_holdout_best_params.json"),
        args.seed,
    )
    pd.DataFrame(classical_metrics + quantum_metrics).to_csv(
        args.output / "metrics.csv", index=False
    )
    pd.DataFrame(classical_predictions + quantum_predictions).to_csv(
        args.output / "predictions.csv", index=False
    )
    report = _overlap_report(internal, external)
    (args.output / "smiles_overlap.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    availability = {
        name: bool(importlib.util.find_spec(name))
        for name in ["rdkit", "xgboost", "qiskit"]
    }
    (args.output / "availability.json").write_text(
        json.dumps(availability, indent=2) + "\n", encoding="utf-8"
    )
    print(pd.DataFrame(classical_metrics + quantum_metrics).to_string(index=False))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
