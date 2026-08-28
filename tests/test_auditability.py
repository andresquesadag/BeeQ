import csv
import hashlib
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from src.model_artifacts import FrozenClassical, FrozenKernel


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_versioned_input_hashes():
    with (ROOT / "data" / "SHA256SUMS.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 5
    for row in rows:
        assert _sha256(ROOT / "data" / row["relative_path"]) == row["sha256"]


def test_retained_campaign_manifests():
    campaigns = ROOT / "results" / "campaigns"
    historical = [
        campaigns / "20260824T183229Z_418787d0cc",
        campaigns / "20260825T034056Z_cd0dba4468",
    ]
    for root in historical:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for relative, expected in manifest["outputs"].items():
            path = root / relative
            if relative.startswith("data_snapshot/"):
                continue
            assert path.is_file()
            assert _sha256(path) == expected

    finals = {
        campaigns / "BEEQ_FINAL_NESTED_STRUCT_IMPL_20260825T234128Z": 51,
        campaigns / "BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z": 51,
    }
    for final, expected_count in finals.items():
        with (final / "10_MANIFEST" / "ARTIFACT_MANIFEST_SHA256.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == expected_count
        for row in rows:
            path = final / row["relative_path"]
            assert path.stat().st_size == int(row["bytes"])
            assert _sha256(path) == row["sha256"]


def test_new_model_artifacts_are_cross_process_portable(tmp_path):
    x = np.array([[0.0], [1.0]])
    y = np.array([0, 1])
    classifier = SVC(kernel="linear").fit(x, y)
    scaler = StandardScaler().fit(x)
    artifacts = [
        FrozenClassical(estimator=classifier, threshold=0.0),
        FrozenKernel(
            scaler=scaler,
            classifier=classifier,
            train_scaled=scaler.transform(x),
            params={"C": 1.0},
            threshold=0.0,
        ),
    ]
    path = tmp_path / "artifacts.pkl"
    path.write_bytes(pickle.dumps(artifacts))
    restored = pickle.loads(path.read_bytes())
    assert [type(item).__module__ for item in restored] == [
        "src.model_artifacts",
        "src.model_artifacts",
    ]


def test_reexecuted_campaign_artifacts_are_portable():
    artifact_dir = (
        ROOT
        / "results"
        / "campaigns"
        / "BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z"
        / "04_FINAL_SELECTION"
        / "model_artifacts"
    )
    restored = [pickle.loads(path.read_bytes()) for path in artifact_dir.glob("*.pkl")]
    assert len(restored) == 6
    assert {type(item).__module__ for item in restored} == {"src.model_artifacts"}
