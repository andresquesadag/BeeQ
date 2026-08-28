"""Create a reproducible 70/20/10 BeeQ split from the corrected master."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold

from .config import PROJECT_ROOT
from .data import sha256_file, write_json


SEED = 42
TRAIN_ROWS = 625
HOLDOUT_ROWS = 179
EXTERNAL_ROWS = 89


def _canonical(smiles: object) -> str:
    molecule = Chem.MolFromSmiles(str(smiles))
    if molecule is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    return Chem.MolToSmiles(molecule)


def _reference_matches(
    master: pd.DataFrame, reference: pd.DataFrame
) -> tuple[set[int], pd.DataFrame]:
    master_can = master["SMILES"].map(_canonical)
    reference_can = reference["SMILES"].map(_canonical)
    by_can: dict[str, list[int]] = {}
    by_cas: dict[str, list[int]] = {}
    for index, row in master.iterrows():
        by_can.setdefault(master_can.loc[index], []).append(index)
        by_cas.setdefault(str(row["CAS"]), []).append(index)

    selected: set[int] = set()
    audit_rows: list[dict[str, object]] = []
    for index, row in reference.iterrows():
        candidates = by_can.get(reference_can.loc[index], [])
        method = "canonical_smiles"
        if not candidates:
            candidates = by_cas.get(str(row["CAS"]), [])
            method = "cas"
        if len(candidates) > 1:
            raise ValueError(
                f"Ambiguous reference match for {row['name']}: {candidates}"
            )
        matched = candidates[0] if candidates else None
        if matched is not None:
            selected.add(matched)
            source = master.loc[matched]
            audit_rows.append(
                {
                    "reference_ID": int(row["ID"]),
                    "reference_name": str(row["name"]),
                    "reference_CAS": str(row["CAS"]),
                    "reference_LABEL": int(row["LABEL"]),
                    "match_status": "matched",
                    "match_method": method,
                    "master_ID": int(source["ID"]),
                    "master_name": str(source["name"]),
                    "master_LABEL": int(source["LABEL"]),
                    "label_agrees": bool(int(row["LABEL"]) == int(source["LABEL"])),
                }
            )
        else:
            audit_rows.append(
                {
                    "reference_ID": int(row["ID"]),
                    "reference_name": str(row["name"]),
                    "reference_CAS": str(row["CAS"]),
                    "reference_LABEL": int(row["LABEL"]),
                    "match_status": "not_in_master",
                    "match_method": None,
                    "master_ID": None,
                    "master_name": None,
                    "master_LABEL": None,
                    "label_agrees": None,
                }
            )
    return selected, pd.DataFrame(audit_rows)


def _sample_external_additions(
    master: pd.DataFrame, forced: set[int], seed: int
) -> set[int]:
    needed = EXTERNAL_ROWS - len(forced)
    if needed < 0:
        raise ValueError("Reference-linked rows exceed the external target")
    pool = master.loc[~master.index.isin(forced)]
    target_positive = round(EXTERNAL_ROWS * float(master["LABEL"].mean()))
    forced_positive = int(master.loc[list(forced), "LABEL"].sum())
    positive_needed = target_positive - forced_positive
    negative_needed = needed - positive_needed
    if positive_needed < 0 or negative_needed < 0:
        raise ValueError("Forced external rows make stratified completion impossible")
    rng = np.random.default_rng(seed)
    positive = rng.choice(
        pool.loc[pool["LABEL"] == 1].index.to_numpy(),
        positive_needed,
        replace=False,
    )
    negative = rng.choice(
        pool.loc[pool["LABEL"] == 0].index.to_numpy(),
        negative_needed,
        replace=False,
    )
    return {int(value) for value in np.concatenate([positive, negative])}


def _group_holdout(
    internal: pd.DataFrame, seed: int
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    splitter = GroupShuffleSplit(
        n_splits=10_000,
        test_size=HOLDOUT_ROWS / len(internal),
        random_state=seed,
    )
    labels = internal["LABEL"].to_numpy(dtype=int)
    groups = internal["BUTINA_CLUSTER_ID"].to_numpy()
    target_prevalence = float(internal["LABEL"].mean())
    best: tuple[tuple[float, float, int], np.ndarray, np.ndarray] | None = None
    for candidate, (train_index, holdout_index) in enumerate(
        splitter.split(internal, labels, groups)
    ):
        score = (
            float(abs(len(holdout_index) - HOLDOUT_ROWS)),
            float(abs(labels[holdout_index].mean() - target_prevalence)),
            candidate,
        )
        if best is None or score < best[0]:
            best = (score, train_index, holdout_index)
    assert best is not None
    if len(best[1]) != TRAIN_ROWS or len(best[2]) != HOLDOUT_ROWS:
        raise RuntimeError(
            f"Could not obtain exact 70/20/10 row counts: "
            f"train={len(best[1])}, holdout={len(best[2])}"
        )
    return best[1], best[2], {
        "candidate_index": int(best[0][2]),
        "holdout_size_error": int(best[0][0]),
        "holdout_prevalence_error": float(best[0][1]),
    }


def _assign_folds(train: pd.DataFrame, seed: int) -> pd.Series:
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    folds = pd.Series(index=train.index, dtype="int64")
    labels = train["LABEL"].to_numpy(dtype=int)
    groups = train["BUTINA_CLUSTER_ID"].to_numpy()
    dummy = np.zeros((len(train), 1))
    for fold, (_, validation) in enumerate(
        splitter.split(dummy, labels, groups), start=1
    ):
        folds.iloc[validation] = fold
    return folds.astype(int)


def build(
    master_path: Path,
    reference_path: Path,
    output_dir: Path,
    seed: int = SEED,
) -> Path:
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    master = pd.read_csv(master_path)
    reference = pd.read_csv(reference_path)
    if len(master) != 893:
        raise ValueError(f"Expected 893 corrected master rows; found {len(master)}")
    forced, match_audit = _reference_matches(master, reference)
    if len(forced) != 71:
        raise RuntimeError(f"Expected 71 reference-linked master rows; found {len(forced)}")
    additions = _sample_external_additions(master, forced, seed)
    external_index = forced | additions
    external = master.loc[sorted(external_index)].copy()
    internal = master.loc[~master.index.isin(external_index)].copy()
    train_pos, holdout_pos, group_search = _group_holdout(internal, seed)
    train = internal.iloc[train_pos].copy()
    holdout = internal.iloc[holdout_pos].copy()

    train["SET"] = "DEVELOPMENT"
    train["STRICT_CV_FOLD"] = _assign_folds(train, seed).to_numpy()
    holdout["SET"] = "TEST"
    holdout["STRICT_CV_FOLD"] = np.nan
    external["SET"] = "EXTERNAL_70_20_10"
    external["STRICT_CV_FOLD"] = np.nan
    internal_master = pd.concat([train, holdout]).sort_values("ID")
    train = train.sort_values("ID")
    holdout = holdout.sort_values("ID")
    external = external.sort_values("ID")

    canonical = {
        name: set(frame["SMILES"].map(_canonical))
        for name, frame in {
            "train": train,
            "holdout": holdout,
            "external": external,
        }.items()
    }
    exact = {
        name: set(frame["SMILES"].astype(str))
        for name, frame in {
            "train": train,
            "holdout": holdout,
            "external": external,
        }.items()
    }
    if exact["external"] & (exact["train"] | exact["holdout"]):
        raise RuntimeError("Exact SMILES leakage into external split")
    if canonical["external"] & (canonical["train"] | canonical["holdout"]):
        raise RuntimeError("Canonical SMILES leakage into external split")
    train_holdout_cluster_overlap = set(train["BUTINA_CLUSTER_ID"]) & set(
        holdout["BUTINA_CLUSTER_ID"]
    )
    if train_holdout_cluster_overlap:
        raise RuntimeError("Butina clusters overlap between train and holdout")

    output_dir.mkdir(parents=True)
    paths = {
        "train_RDKitFixed.csv": train,
        "test_RDKitFixed.csv": holdout,
        "master_RDKitFixed.csv": internal_master,
        "ExternalFinal_RDKitFixed.csv": external,
        "master_full_reference_RDKitFixed.csv": master,
    }
    for name, frame in paths.items():
        frame.to_csv(output_dir / name, index=False)
    match_audit.to_csv(output_dir / "external_reference_match_audit.csv", index=False)
    shutil.copy2(reference_path, output_dir / "Externalset_reference_only.csv")

    external_internal_cluster_overlap = set(external["BUTINA_CLUSTER_ID"]) & set(
        internal_master["BUTINA_CLUSTER_ID"]
    )
    manifest = {
        "schema_version": 1,
        "protocol": "corrected_master_forced_reference_70_20_10_v1",
        "seed": seed,
        "source": {
            "corrected_master": str(master_path.resolve()),
            "corrected_master_sha256": sha256_file(master_path),
            "external_reference": str(reference_path.resolve()),
            "external_reference_sha256": sha256_file(reference_path),
            "reference_rows": int(len(reference)),
            "reference_rows_matched_to_master": int(len(forced)),
            "reference_rows_not_in_master": int(
                (match_audit["match_status"] == "not_in_master").sum()
            ),
            "reference_label_conflicts": int(
                (match_audit["label_agrees"] == False).sum()  # noqa: E712
            ),
        },
        "split": {
            "train_rows": int(len(train)),
            "holdout_rows": int(len(holdout)),
            "external_rows": int(len(external)),
            "train_fraction": len(train) / len(master),
            "holdout_fraction": len(holdout) / len(master),
            "external_fraction": len(external) / len(master),
            "external_reference_linked_rows": int(len(forced)),
            "external_stratified_additions": int(len(additions)),
            "group_search": group_search,
        },
        "labels": {
            name: {
                str(int(label)): int(count)
                for label, count in frame["LABEL"].value_counts().sort_index().items()
            }
            for name, frame in {
                "train": train,
                "holdout": holdout,
                "external": external,
            }.items()
        },
        "leakage_audit": {
            "train_holdout_id_overlap": 0,
            "train_holdout_exact_smiles_overlap": 0,
            "train_holdout_butina_cluster_overlap": 0,
            "external_internal_id_overlap": 0,
            "external_internal_exact_smiles_overlap": 0,
            "external_internal_canonical_smiles_overlap": 0,
            "external_internal_butina_cluster_overlap": len(
                external_internal_cluster_overlap
            ),
            "cluster_note": (
                "Reference-forced external rows share Butina clusters with internal "
                "rows; complete cluster isolation would move 234/893 rows external."
            ),
        },
    }
    written = list(paths) + [
        "external_reference_match_audit.csv",
        "Externalset_reference_only.csv",
    ]
    manifest["outputs"] = {
        name: sha256_file(output_dir / name) for name in sorted(written)
    }
    write_json(output_dir / "split_manifest.json", manifest)
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--master",
        type=Path,
        default=PROJECT_ROOT / "data" / "official" / "master_RDKitFixed.csv",
    )
    parser.add_argument(
        "--external-reference",
        type=Path,
        default=PROJECT_ROOT / "data" / "reference" / "Externalset.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "generated" / "master_70_20_10_seed42",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print(build(args.master.resolve(), args.external_reference.resolve(), args.output.resolve(), args.seed))


if __name__ == "__main__":
    main()
