"""Load, validate, audit, and hash the curated BeeQ X10 handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import (
    OUTER_FOLDS,
    REQUIRED_COLUMNS,
    X10_FEATURES,
    resolve_data_dir,
)


@dataclass(frozen=True)
class DatasetBundle:
    """Validated development, historical holdout, and optional master tables."""

    data_dir: Path
    train: pd.DataFrame
    test: pd.DataFrame
    master: pd.DataFrame | None
    audit: dict[str, Any]


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a file without loading it all into memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    """Hash a JSON-serializable object using a canonical encoding."""

    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required data file not found: {path}. "
            "Supply --data-dir or set BEEQ_DATA_DIR."
        )
    return pd.read_csv(path)


def _validate_columns(frame: pd.DataFrame, source: str) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def _validate_common(frame: pd.DataFrame, source: str) -> None:
    _validate_columns(frame, source)

    if frame.empty:
        raise ValueError(f"{source} is empty")
    if frame["ID"].isna().any() or frame["ID"].duplicated().any():
        raise ValueError(f"{source} must contain unique, non-null IDs")
    if frame["SMILES"].isna().any() or frame["SMILES"].duplicated().any():
        raise ValueError(f"{source} must contain unique, non-null SMILES")

    labels = set(frame["LABEL"].dropna().astype(int).unique())
    if not labels <= {0, 1} or not labels:
        raise ValueError(f"{source} LABEL values must be binary 0/1; found {labels}")

    numeric = frame.loc[:, X10_FEATURES].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    if numeric.isna().any().any() or not np.isfinite(values).all():
        bad = numeric.columns[numeric.isna().any()].tolist()
        raise ValueError(f"{source} has missing/non-numeric X10 values: {bad}")


def _validate_train(frame: pd.DataFrame) -> None:
    _validate_common(frame, "train.csv")
    if set(frame["SET"].unique()) != {"DEVELOPMENT"}:
        raise ValueError("train.csv SET must contain only DEVELOPMENT")
    if frame["STRICT_CV_FOLD"].isna().any():
        raise ValueError("train.csv requires STRICT_CV_FOLD for every row")

    folds = set(frame["STRICT_CV_FOLD"].astype(int).unique())
    if folds != set(OUTER_FOLDS):
        raise ValueError(f"Expected folds {OUTER_FOLDS}; found {sorted(folds)}")

    cluster_fold_counts = frame.groupby("BUTINA_CLUSTER_ID")[
        "STRICT_CV_FOLD"
    ].nunique()
    split_clusters = cluster_fold_counts[cluster_fold_counts > 1].index.tolist()
    if split_clusters:
        raise ValueError(
            "Butina clusters cannot be split across development folds; "
            f"found {split_clusters[:10]}"
        )


def _validate_test(frame: pd.DataFrame) -> None:
    _validate_common(frame, "test.csv")
    if set(frame["SET"].unique()) != {"TEST"}:
        raise ValueError("test.csv SET must contain only TEST")
    if frame["STRICT_CV_FOLD"].notna().any():
        raise ValueError("test.csv STRICT_CV_FOLD must be empty")


def _canonical_split_hash(train: pd.DataFrame, test: pd.DataFrame) -> str:
    columns = ["ID", "LABEL", "SET", "BUTINA_CLUSTER_ID", "STRICT_CV_FOLD"]
    combined = pd.concat([train[columns], test[columns]], ignore_index=True)
    combined = combined.sort_values("ID", kind="stable")
    records: list[dict[str, Any]] = []
    for row in combined.itertuples(index=False):
        fold = None if pd.isna(row.STRICT_CV_FOLD) else int(row.STRICT_CV_FOLD)
        records.append(
            {
                "ID": int(row.ID),
                "LABEL": int(row.LABEL),
                "SET": str(row.SET),
                "BUTINA_CLUSTER_ID": int(row.BUTINA_CLUSTER_ID),
                "STRICT_CV_FOLD": fold,
            }
        )
    return sha256_json(records)


def _frame_summary(frame: pd.DataFrame) -> dict[str, Any]:
    labels = frame["LABEL"].value_counts().sort_index()
    return {
        "rows": int(len(frame)),
        "label_counts": {str(int(k)): int(v) for k, v in labels.items()},
        "positive_prevalence": float(frame["LABEL"].mean()),
        "unique_ids": int(frame["ID"].nunique()),
        "unique_smiles": int(frame["SMILES"].nunique()),
        "clusters": int(frame["BUTINA_CLUSTER_ID"].nunique()),
    }


def load_bundle(data_dir: str | Path | None = None) -> DatasetBundle:
    """Load and validate all available handoff tables."""

    resolved = resolve_data_dir(data_dir)
    train_path = resolved / "train.csv"
    test_path = resolved / "test.csv"
    master_path = resolved / "master.csv"

    train = _read_csv(train_path)
    test = _read_csv(test_path)
    master = _read_csv(master_path) if master_path.is_file() else None

    _validate_train(train)
    _validate_test(test)
    if master is not None:
        _validate_common(master, "master.csv")

    id_overlap = set(train["ID"]) & set(test["ID"])
    smiles_overlap = set(train["SMILES"]) & set(test["SMILES"])
    cluster_overlap = set(train["BUTINA_CLUSTER_ID"]) & set(
        test["BUTINA_CLUSTER_ID"]
    )
    if id_overlap or smiles_overlap or cluster_overlap:
        raise ValueError(
            "Development/test overlap detected: "
            f"IDs={len(id_overlap)}, SMILES={len(smiles_overlap)}, "
            f"clusters={len(cluster_overlap)}"
        )

    if master is not None:
        expected_ids = set(train["ID"]) | set(test["ID"])
        if set(master["ID"]) != expected_ids or len(master) != len(expected_ids):
            raise ValueError("master.csv must be the exact union of train.csv and test.csv")

    fold_counts = (
        train["STRICT_CV_FOLD"].astype(int).value_counts().sort_index()
    )
    audit = {
        "schema_version": 1,
        "endpoint": {
            "column": "LABEL",
            "positive": "acute LD50 <= 11 microgram/bee",
            "negative": "acute LD50 > 11 microgram/bee",
        },
        "feature_order": list(X10_FEATURES),
        "feature_schema_sha256": sha256_json(list(X10_FEATURES)),
        "split_sha256": _canonical_split_hash(train, test),
        "source_files": {
            "train.csv": sha256_file(train_path),
            "test.csv": sha256_file(test_path),
            **(
                {"master.csv": sha256_file(master_path)}
                if master_path.is_file()
                else {}
            ),
        },
        "development": {
            **_frame_summary(train),
            "fold_counts": {str(int(k)): int(v) for k, v in fold_counts.items()},
        },
        "historical_holdout": _frame_summary(test),
        "overlap": {"ids": 0, "smiles": 0, "butina_clusters": 0},
    }
    if master is not None:
        audit["master"] = _frame_summary(master)

    return DatasetBundle(resolved, train, test, master, audit)


def write_json(path: str | Path, payload: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--write-manifest", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    bundle = load_bundle(args.data_dir)
    print(json.dumps(bundle.audit, indent=2, sort_keys=True, ensure_ascii=False))
    if args.write_manifest:
        output = write_json(args.write_manifest, bundle.audit)
        print(f"Wrote dataset manifest: {output.resolve()}")


if __name__ == "__main__":
    main()
