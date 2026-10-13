from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

from .classical_models import ModelSpec, model_specs
from .config import OUTER_FOLDS, X10_FEATURES
from .evaluation import continuous_scores
from .final_nested_campaign import (
    EXPECTED_HASHES,
    SEED,
    classical_inner_oof,
    classification_metrics,
    frozen_outer_splits,
    inner_splits,
    prediction_rows,
    select_classical,
    select_threshold,
    sha256_file,
    validate_development,
    validate_postfreeze_frame,
)

LABELS = {"X10": "X10_RF", "ECFP": "ECFP_RF", "MACCS": "MACCS_RF", "RDKit2D": "RDKit2D_RF",
          "Mordred": "Mordred_RF", "AtomCounts": "AtomCounts_RF", "WL-OA": "WL-OA_SVM"}


# ----------------------------------------------------------------- clasificador RF
def rf_spec(kind: str) -> ModelSpec:
    """'beeq' = RF de BeeQ (misma fila que RF-X10 de la Tabla I).
    'alt' = RF alternativo de sensibilidad (100 arboles, entropy, balanced, min_samples_split 2..10)."""
    if kind == "beeq":
        return model_specs(SEED, quick=False)["random_forest"]
    rf = RandomForestClassifier(n_estimators=100, criterion="entropy",
                                class_weight="balanced", random_state=SEED)
    return ModelSpec(estimator=Pipeline([("model", rf)]),
                     param_grid={"model__min_samples_split": list(range(2, 11))})


# ----------------------------------------------------------------- caracteristicas
def load_export(features_dir: Path, frame: pd.DataFrame) -> dict:
    """Carga las caracteristicas exportadas (manifest.json + .npy) y comprueba que corresponde a ESTAS
    moleculas, en este orden (Development primero, holdout despues), y que los archivos no cambiaron."""
    man = json.loads((features_dir / "manifest.json").read_text())
    if man["ids"] != frame["ID"].astype(int).tolist():
        raise RuntimeError("Las caracteristicas exportadas no corresponden a las moleculas/orden de BeeQ")
    for f, h in man["file_sha256"].items():
        if sha256_file(features_dir / f) != h:
            raise RuntimeError(f"Archivo modificado desde la exportacion: {f}")
    return man


# ----------------------------------------------------------------- representaciones
class VectorRep:
    """Matriz de caracteristicas + RF. Cada config de la huella es un candidato mas de la rejilla."""

    def __init__(self, rep: str, frame: pd.DataFrame, spec: ModelSpec, export: dict | None, features_dir: Path | None):
        if rep == "X10":
            self.configs, self.mats = [{}], [frame.loc[:, X10_FEATURES].to_numpy(float)]
        else:
            info = export["reps"][rep]
            self.configs = info["configs"]
            self.mats = [np.load(features_dir / f) for f in info["files"]]
            assert all(m.shape[0] == len(frame) for m in self.mats)
        self.spec = spec

    def select(self, tr, splits, y):
        best = None
        for i, x in enumerate(self.mats):
            params, mean, sd = select_classical(self.spec, x[tr], y[tr], splits)
            if best is None or mean > best[0]:          # empates: primera configuracion
                best = (mean, sd, {"cfg_index": i, "feature_config": self.configs[i], "rf": params})
        return best[2], best[0], best[1]

    def _est(self, state):
        return clone(self.spec.estimator).set_params(**state["rf"])

    def inner_oof(self, state, tr, splits, y):
        return classical_inner_oof(self.spec, state["rf"], self.mats[state["cfg_index"]][tr], y[tr], splits)

    def fit_score(self, state, tr, te, y):
        x = self.mats[state["cfg_index"]]
        est = self._est(state).fit(x[tr], y[tr])
        return continuous_scores(est, x[te])


class KernelRep:
    """Kernel WL-OA exportado + SVC precomputado (convenciones de BeeQ)."""

    def __init__(self, export: dict, features_dir: Path, n_total: int):
        info = export["reps"]["WL-OA"]
        self.grams = {n: np.load(features_dir / f) for n, f in zip(info["n_iter"], info["files"])}
        self.svm_c = info["svm_C"]
        assert all(k.shape == (n_total, n_total) for k in self.grams.values())

    @staticmethod
    def _svc(c):
        return SVC(C=float(c), kernel="precomputed", class_weight="balanced", random_state=SEED)

    def select(self, tr, splits, y):
        best = None
        for n, k in self.grams.items():
            gs = GridSearchCV(self._svc(1.0), {"C": self.svm_c}, scoring="roc_auc", cv=splits,
                              n_jobs=1, refit=False, error_score="raise")
            gs.fit(k[np.ix_(tr, tr)], y[tr])
            i = int(gs.best_index_)
            mean, sd = float(gs.best_score_), float(gs.cv_results_["std_test_score"][i])
            if best is None or mean > best[0]:
                best = (mean, sd, {"n_iter": n, "C": float(gs.best_params_["C"])})
        return best[2], best[0], best[1]

    def inner_oof(self, state, tr, splits, y):
        k = self.grams[state["n_iter"]][np.ix_(tr, tr)]
        scores = np.full(len(tr), np.nan)
        for a, b in splits:
            scores[b] = self._svc(state["C"]).fit(k[np.ix_(a, a)], y[tr][a]).decision_function(k[np.ix_(b, a)])
        return scores

    def fit_score(self, state, tr, te, y):
        k = self.grams[state["n_iter"]]
        return self._svc(state["C"]).fit(k[np.ix_(tr, tr)], y[tr]).decision_function(k[np.ix_(te, tr)])


# ----------------------------------------------------------------- protocolo
def run_nested(rep, label, train, y):
    metrics, oof, params = [], [], []
    for fold, (tr, va) in zip(OUTER_FOLDS, frozen_outer_splits(train)):
        splits = inner_splits(train, tr, fold)
        state, mean, sd = rep.select(tr, splits, y)
        thr, thr_m = select_threshold(y[tr], rep.inner_oof(state, tr, splits, y))
        scores = rep.fit_score(state, tr, va, y)
        m = classification_metrics(y[va], scores, thr)
        metrics.append({"MODEL": label, "OUTER_FOLD": fold, "N_TRAIN": len(tr), "N_VALIDATION": len(va),
                        "INNER_AUROC_MEAN": mean, "INNER_AUROC_SD": sd, "THRESHOLD": thr,
                        **{k.upper(): v for k, v in m.items()}})
        params.append({"MODEL": label, "OUTER_FOLD": fold, "BEST_PARAMS": json.dumps(state, default=str, sort_keys=True),
                       "INNER_AUROC_MEAN": mean, "THRESHOLD": thr, "INNER_THRESHOLD_MCC": thr_m["mcc"]})
        oof.extend(prediction_rows(train.iloc[va], label, fold, scores, thr))
        print(f"  [{label}] fold {fold}: AUROC={m['auroc']:.3f} inner={mean:.3f} thr={thr:.3f}", flush=True)
    return pd.DataFrame(metrics), pd.DataFrame(oof), pd.DataFrame(params)


def run_final(rep, label, train, test, y_all, n_dev):
    """Equivale a final_selection + score_frozen de BeeQ: seleccion sobre los 5 folds congelados."""
    dev = np.arange(n_dev)
    hold = np.arange(n_dev, n_dev + len(test))
    splits = frozen_outer_splits(train)
    state, mean, sd = rep.select(dev, splits, y_all)
    thr, _ = select_threshold(y_all[dev], rep.inner_oof(state, dev, splits, y_all))
    scores = rep.fit_score(state, dev, hold, y_all)                     # holdout: una sola evaluacion
    m = classification_metrics(y_all[hold], scores, thr)
    row = {"EVALUATION": "historical_holdout", "MODEL": label, "N": len(test),
           **{k.upper(): v for k, v in m.items()}, "THRESHOLD": thr, "DEV_CV_AUROC": mean,
           "BEST_PARAMS": json.dumps(state, default=str, sort_keys=True)}
    return pd.DataFrame([row]), pd.DataFrame(prediction_rows(test, label, "historical_holdout", scores, thr))


def load_data(data_dir: Path, out: Path, skip_checks: bool):
    train_p, test_p = data_dir / "train_RDKitFixed.csv", data_dir / "test_RDKitFixed.csv"
    if skip_checks:
        train, test = pd.read_csv(train_p), pd.read_csv(test_p)
    else:
        for p in (train_p, test_p):
            if sha256_file(p) != EXPECTED_HASHES[p.name]:
                raise RuntimeError(f"Hash distinto del contrato congelado: {p.name}")
        (out / "audit").mkdir(parents=True, exist_ok=True)
        train = validate_development(train_p, out / "audit")
        test = pd.read_csv(test_p)
        validate_postfreeze_frame(test, expected_rows=181, expected_labels={0: 132, 1: 49}, source="holdout")
    assert not set(train.BUTINA_CLUSTER_ID) & set(test.BUTINA_CLUSTER_ID), "Clusters compartidos Dev/holdout"
    return train.reset_index(drop=True), test.reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=Path("data/official"))
    ap.add_argument("--out", type=Path, default=Path("results/baselines"))
    ap.add_argument("--reps", nargs="+", required=True, choices=list(LABELS))
    ap.add_argument("--rf", choices=["beeq", "alt"], default="beeq")
    ap.add_argument("--features-dir", type=Path, default=None,
                    help="carpeta con las caracteristicas exportadas (obligatoria salvo para X10)")
    ap.add_argument("--holdout", action="store_true", help="evalua el holdout UNA vez (tras fijar la lista)")
    ap.add_argument("--skip-contract-checks", action="store_true", help="SOLO para pruebas con datos sinteticos")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    train, test = load_data(a.data_dir, a.out, a.skip_contract_checks)
    frame = pd.concat([train, test], ignore_index=True)       # primero Development, luego holdout
    y_all = frame["LABEL"].to_numpy(int)
    y = y_all[: len(train)]
    spec = rf_spec(a.rf)
    json.dump({"seed": SEED, "rf": a.rf, "reps": a.reps, "sklearn": sklearn.__version__,
               "data_sha256": {p: sha256_file(a.data_dir / p) for p in ("train_RDKitFixed.csv", "test_RDKitFixed.csv")}},
              open(a.out / "run_config.json", "w"), indent=2)

    export = load_export(a.features_dir, frame) if a.features_dir else None
    for name in a.reps:
        suffix = "" if (a.rf == "beeq" or name == "WL-OA") else "_rfAlt"
        label = LABELS[name] + suffix
        t0 = time.perf_counter()
        print(f"== {label}", flush=True)
        if name != "X10" and export is None:
            raise SystemExit(f"{name} requiere --features-dir (carpeta con las caracteristicas exportadas)")
        rep = (KernelRep(export, a.features_dir, len(frame)) if name == "WL-OA"
               else VectorRep(name, frame, spec, export, a.features_dir))
        m, o, p = run_nested(rep, label, train, y)
        m.to_csv(a.out / f"{label}_NESTED_FOLD_METRICS.csv", index=False)
        o.to_csv(a.out / f"{label}_NESTED_OOF_PREDICTIONS.csv", index=False)
        p.to_csv(a.out / f"{label}_SELECTED_PARAMS.csv", index=False)
        if a.holdout:
            hm, hp = run_final(rep, label, train, test, y_all, len(train))
            hm.to_csv(a.out / f"{label}_HOLDOUT_METRICS.csv", index=False)
            hp.to_csv(a.out / f"{label}_HOLDOUT_PREDICTIONS.csv", index=False)
        print(f"   {label}: AUROC externo medio={m.AUROC.mean():.3f} (SD {m.AUROC.std(ddof=1):.3f}), "
              f"{time.perf_counter() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()