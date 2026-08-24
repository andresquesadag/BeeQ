"""Reproducible comparison on Luis's corrected BeeQ datasets.

Runs available scikit-learn baselines plus the exploratory MLP, audits exact
SMILES overlap, and writes OOF, holdout, external, and availability reports.
Optional RDKit/XGBoost/quantum components are reported as unavailable rather
than silently omitted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, matthews_corrcoef, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from src.deployment_models import ExactIQPZZKernelSVC

FEATURES = ["MolLogP", "MolWt", "TPSA_SP", "NumHDonors", "NumRotatableBonds", "NumAromaticRings", "nHalogen", "n_OP", "LiPHEX_prediction", "sasa002_frac_polar_hetero_only"]


def models(seed: int) -> dict[str, object]:
    result = {
        "logistic": Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000, random_state=seed))]),
        "rbf_svc": Pipeline([("scale", StandardScaler()), ("model", SVC(C=1.0, gamma="scale", class_weight="balanced", probability=True, random_state=seed))]),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, max_features=0.7, class_weight="balanced_subsample", random_state=seed, n_jobs=1),
        "mlp_exploratory": Pipeline([("scale", StandardScaler()), ("model", MLPClassifier(hidden_layer_sizes=(32, 16), alpha=1e-3, learning_rate_init=1e-3, max_iter=2000, early_stopping=True, random_state=seed))]),
    }
    try:
        from xgboost import XGBClassifier
        result["xgboost"] = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=1.0, objective="binary:logistic", eval_metric="logloss", n_jobs=1, random_state=seed)
    except ImportError:
        pass
    result["quantum_iqp_zz"] = ExactIQPZZKernelSVC(c=1.0, feature_scale=0.125, interaction_strength=1.0, random_state=seed)
    return result


def scores(estimator, x):
    return estimator.predict_proba(x)[:, 1] if hasattr(estimator, "predict_proba") else estimator.decision_function(x)


def metrics(y, score):
    pred = (score >= 0.5).astype(int)
    return {"auroc": roc_auc_score(y, score), "auprc": average_precision_score(y, score), "balanced_accuracy": balanced_accuracy_score(y, pred), "mcc": matthews_corrcoef(y, pred), "positive_predictions": int(pred.sum())}


def overlap_report(internal, external):
    a = set(internal.SMILES.astype(str)); b = set(external.SMILES.astype(str))
    result = {"internal_rows": len(internal), "external_rows": len(external), "internal_unique_smiles": internal.SMILES.nunique(), "external_unique_smiles": external.SMILES.nunique(), "exact_smiles_overlap": len(a & b), "overlap_smiles": sorted(a & b)}
    try:
        from rdkit import Chem
        ca = {Chem.MolToSmiles(m) for s in internal.SMILES for m in [Chem.MolFromSmiles(str(s))] if m is not None}
        cb = {Chem.MolToSmiles(m) for s in external.SMILES for m in [Chem.MolFromSmiles(str(s))] if m is not None}
        result["canonical_smiles_overlap"] = len(ca & cb)
        result["canonicalization"] = "RDKit"
    except Exception as exc:
        result["canonical_smiles_overlap"] = None
        result["canonicalization"] = f"unavailable: {type(exc).__name__}"
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path(".donotmerge_aux/Luis/01_DATA"))
    p.add_argument("--output", type=Path, default=Path("results/external_challenge"))
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(args.data_dir / "train_RDKitFixed.csv"); test = pd.read_csv(args.data_dir / "test_RDKitFixed.csv"); ext = pd.read_csv(args.data_dir / "ExternalFinal_RDKitFixed.csv"); master = pd.read_csv(args.data_dir / "master_RDKitFixed.csv")
    x, y = train[FEATURES], train.LABEL.astype(int); xt, yt = test[FEATURES], test.LABEL.astype(int); xe, ye = ext[FEATURES], ext.LABEL.astype(int)
    all_metrics = []; oof_rows = []
    for name, estimator in models(args.seed).items():
        splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=args.seed)
        oof = np.zeros(len(train))
        for fold, (tr, va) in enumerate(splitter.split(x, y, train.BUTINA_CLUSTER_ID), 1):
            estimator.fit(x.iloc[tr], y.iloc[tr]); oof[va] = scores(estimator, x.iloc[va])
        all_metrics.append({"evaluation": "structure_oof", "model": name, **metrics(y.to_numpy(), oof)})
        estimator.fit(x, y)
        all_metrics.append({"evaluation": "holdout", "model": name, **metrics(yt.to_numpy(), scores(estimator, xt))})
        all_metrics.append({"evaluation": "external8", "model": name, **metrics(ye.to_numpy(), scores(estimator, xe))})
        oof_rows.extend({"model": name, "ID": int(i), "y_true": int(y.iloc[i]), "y_score": float(oof[i])} for i in range(len(train)))
    pd.DataFrame(all_metrics).to_csv(args.output / "metrics.csv", index=False)
    pd.DataFrame(oof_rows).to_csv(args.output / "oof_predictions.csv", index=False)
    (args.output / "smiles_overlap.json").write_text(json.dumps(overlap_report(master, ext), indent=2), encoding="utf-8")
    availability = {name: bool(__import__("importlib.util").util.find_spec(name)) for name in ["rdkit", "xgboost", "qiskit"]}
    (args.output / "availability.json").write_text(json.dumps(availability, indent=2), encoding="utf-8")
    print(pd.DataFrame(all_metrics).to_string(index=False)); print(json.dumps(overlap_report(master, ext), indent=2)); print(json.dumps(availability, indent=2))


if __name__ == "__main__": main()
