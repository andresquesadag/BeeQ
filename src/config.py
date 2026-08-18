"""Project-wide constants and immutable feature declarations."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / ".donotmerge_aux" / "data"
DATA_DIR_ENV = "BEEQ_DATA_DIR"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results" / "runs"

SEED = 42
OUTER_FOLDS = (1, 2, 3, 4, 5)

X10_FEATURES = (
    "MolLogP",
    "MolWt",
    "TPSA_SP",
    "NumHDonors",
    "NumRotatableBonds",
    "NumAromaticRings",
    "nHalogen",
    "n_OP",
    "LiPHEX_prediction",
    "sasa002_frac_polar_hetero_only",
)

FEATURE_SETS = {
    "x10": X10_FEATURES,
    "without_n_op": tuple(f for f in X10_FEATURES if f != "n_OP"),
    "without_mollogp": tuple(f for f in X10_FEATURES if f != "MolLogP"),
    "without_liphex": tuple(
        f for f in X10_FEATURES if f != "LiPHEX_prediction"
    ),
    "without_partition_pair": tuple(
        f for f in X10_FEATURES if f not in {"MolLogP", "LiPHEX_prediction"}
    ),
}

IDENTITY_COLUMNS = ("ID", "name", "CID", "CAS", "SMILES")
SPLIT_COLUMNS = ("LABEL", "SET", "BUTINA_CLUSTER_ID", "STRICT_CV_FOLD")
REQUIRED_COLUMNS = IDENTITY_COLUMNS + SPLIT_COLUMNS + X10_FEATURES


def resolve_data_dir(value: str | Path | None = None) -> Path:
    """Resolve an explicit path, environment override, or local handoff default."""

    if value is not None:
        return Path(value).expanduser().resolve()
    if env_value := os.environ.get(DATA_DIR_ENV):
        return Path(env_value).expanduser().resolve()
    return DEFAULT_DATA_DIR.resolve()
