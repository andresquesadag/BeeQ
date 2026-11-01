"""Independently verify an MLP sensitivity bundle and generate editorial material."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import X10_FEATURES
from .final_nested_campaign import classification_metrics, select_threshold, sha256_file, write_json
from .mlp_sensitivity import ROOT, VARIANTS, REFERENCE, TOLERANCE, summarize


def table(frame, columns=None, digits=4):
    data = frame if columns is None else frame[columns]
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "--" if pd.isna(v) else f"{v:.{digits}f}"
        return str(v).replace("|", " / ")
    return "| " + " | ".join(data.columns) + " |\n| " + " | ".join(["---"] * len(data.columns)) + " |\n" + "\n".join("| " + " | ".join(fmt(v) for v in row) + " |" for row in data.itertuples(index=False, name=None))


def validate(run):
    status = json.loads((run / "STATUS.json").read_text())
    if status["status"] != "complete" or status["smoke"]:
        raise RuntimeError("Only complete production results may enter the report")
    checks = []
    for row in pd.read_csv(run / "MANIFEST_SHA256.csv").itertuples(index=False):
        assert (run / row.relative_path).stat().st_size == row.bytes
        assert sha256_file(run / row.relative_path) == row.sha256
    checks.append("All production artifact hashes and sizes match")
    for name, expected in json.loads((run / "DEVELOPMENT_FREEZE.json").read_text())["hashes"].items():
        assert sha256_file(run / name) == expected
    checks.append("Development freeze remains unchanged after external evaluation")
    train = pd.read_csv(ROOT / "data/official/train_RDKitFixed.csv")
    membership = pd.read_csv(run / "SPLIT_MEMBERSHIP.csv")
    audit = json.loads((run / "FIT_AUDIT.json").read_text())
    original_fits = {(a["stage"], a["fold"]): a for a in audit if a["variant"] == VARIANTS[0]}
    for a in audit:
        ids = a["fit_ids"]
        assert len(ids) == len(set(ids)) == a["n_fit"]
        f = train.set_index("ID").loc[ids]
        y = f.LABEL.to_numpy(int)
        assert a["negative"] == (y == 0).sum() and a["positive"] == y.sum()
        if a["stage"] == "final_fit":
            expected_ids = set(train.ID)
        elif a["stage"] == "outer_fit":
            expected_ids = set(membership[(membership.SCOPE == "outer") & (membership.FOLD == int(a["fold"])) & (membership.ROLE == "train")].ID)
        else:
            parts = a["fold"].split(".")
            scope = "final_selection" if parts[0] == "final" else f"inner_{parts[0]}"
            fold = int(parts[-1])
            expected_ids = set(membership[(membership.SCOPE == scope) & (membership.FOLD == fold) & (membership.ROLE == "train")].ID)
        assert set(ids) == expected_ids
        balanced = a["variant"] != VARIANTS[0]
        for c in (0, 1):
            expected_weight = len(y) / (2 * (y == c).sum()) if balanced else 1
            np.testing.assert_allclose(a[f"weight_{c}"], expected_weight, atol=1e-12, rtol=0)
        np.testing.assert_allclose(a["weight_sum"], len(y), atol=1e-10, rtol=0)
        x = f[list(X10_FEATURES)].to_numpy(float)
        np.testing.assert_allclose(a["scaler_mean"], x.mean(axis=0), atol=1e-12, rtol=0)
        np.testing.assert_allclose(a["scaler_var"], x.var(axis=0), atol=1e-10, rtol=0)
        assert a["scaler_n"] == len(y) and a["resampling"] is False
        assert set(a["gradient_ids"]).isdisjoint(a["stopping_ids"])
        assert set(a["gradient_ids"]) | set(a["stopping_ids"]) == set(ids)
        assert np.isfinite(a["loss_curve"]).all() and np.isfinite(a["validation_scores"]).all()
        if a["variant"] == VARIANTS[1]:
            control = original_fits[(a["stage"], a["fold"])]
            assert a["params"] == control["params"]
            for key in ("fit_ids", "gradient_ids", "stopping_ids", "scaler_mean", "scaler_var", "seed"):
                assert a[key] == control[key]
    assert len(audit) == 693
    checks.append("693 fits: exact CV training membership, weights, local scalers, finite losses and no resampling")
    checks.append("All 31 fixed-parameter balanced fits share parameters, seed, scaler and native stopping membership with controls")
    splits = pd.read_csv(run / "SPLIT_COUNTS.csv")
    assert len(splits) == 30 and (splits.CLUSTER_OVERLAP == 0).all()
    checks.append("5 outer, 20 inner and 5 final-selection splits are cluster disjoint")
    hpo = pd.read_csv(run / "HPO_CANDIDATES.csv")
    assert len(hpo) == 144
    assert set(hpo.groupby(["VARIANT", "SCOPE"]).size()) == {12}
    checks.append("Both searches have identical 12-candidate budgets: 240 nested + 60 final HPO fits each")
    threshold_oof = pd.read_csv(run / "THRESHOLD_OOF_PREDICTIONS.csv")
    for (_, scope), group in threshold_oof.groupby(["MODEL", "SCOPE"]):
        expected = train if scope == "final" else train[train.STRICT_CV_FOLD != int(scope.split("_")[-1])]
        assert not group.ID.duplicated().any() and set(group.ID) == set(expected.ID)
        np.testing.assert_array_equal(group.set_index("ID").loc[expected.ID].LABEL, expected.LABEL)
        threshold, _ = select_threshold(group.LABEL.to_numpy(int), group.SCORE.to_numpy(float))
        np.testing.assert_allclose(group.THRESHOLD, threshold, rtol=0, atol=TOLERANCE)
    checks.append("18 threshold OOF pools have complete single coverage and reproduce MCC/BA/threshold tie rules")
    folds = pd.read_csv(run / "NESTED_FOLD_METRICS.csv")
    oof = pd.read_csv(run / "NESTED_OOF_PREDICTIONS.csv")
    for v, p in oof.groupby("MODEL"):
        assert len(p) == 712 and set(p.ID) == set(train.ID) and not p.ID.duplicated().any()
        for fold, g in p.groupby("OUTER_FOLD"):
            row = folds[(folds.MODEL == v) & (folds.OUTER_FOLD == fold)].iloc[0]
            observed = classification_metrics(g.LABEL.to_numpy(int), g.SCORE.to_numpy(float), row.THRESHOLD)
            np.testing.assert_array_equal(g.PRED, (g.SCORE >= g.THRESHOLD).astype(int))
            for k, value in observed.items():
                np.testing.assert_allclose(value, row[k.upper()], rtol=0, atol=TOLERANCE)
    pd.testing.assert_frame_equal(summarize(folds, oof).sort_values("MODEL").reset_index(drop=True),
                                  pd.read_csv(run / "NESTED_SUMMARY.csv").sort_values("MODEL").reset_index(drop=True),
                                  check_exact=False, rtol=0, atol=TOLERANCE, check_dtype=False)
    ext = pd.read_csv(run / "EXTERNAL_PREDICTIONS.csv")
    metrics = pd.read_csv(run / "EXTERNAL_METRICS.csv")
    for (v, evaluation), g in ext.groupby(["MODEL", "EVALUATION"]):
        row = metrics[(metrics.MODEL == v) & (metrics.EVALUATION == evaluation)].iloc[0]
        assert len(g) == row.N and not g.ID.duplicated().any()
        observed = classification_metrics(g.LABEL.to_numpy(int), g.SCORE.to_numpy(float), row.THRESHOLD)
        np.testing.assert_array_equal(g.PRED, (g.SCORE >= g.THRESHOLD).astype(int))
        for k, value in observed.items():
            np.testing.assert_allclose(value, row[k.upper()], atol=TOLERANCE, rtol=0)
    checks.append("2,136 nested OOF, 543 holdout and 24 CR8 predictions reproduce all metrics and decisions without evaluation weights")
    from rdkit import Chem
    canonical = lambda s: Chem.MolToSmiles(Chem.MolFromSmiles(s), isomericSmiles=True)
    holdout = pd.read_csv(ROOT / "data/official/test_RDKitFixed.csv")
    cr8 = pd.read_csv(ROOT / "data/official/ExternalFinal_RDKitFixed.csv")
    assert not (set(train.BUTINA_CLUSTER_ID) & set(holdout.BUTINA_CLUSTER_ID))
    assert not (set(cr8.SMILES.map(canonical)) & set(pd.concat([train, holdout]).SMILES.map(canonical)))
    checks.append("Historical holdout clusters and exact/canonical CR8 identities remain separate from Development")
    repeats = json.loads((run / "REPEAT_COMPARISON.json").read_text())
    assert repeats and all(a["exact_csv_match"] for a in repeats)
    checks.append(f"Independent complete rerun: all {len(repeats)} CSV outputs match exactly")
    return checks


def build(run, output):
    checks = validate(run)
    output.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(run / "NESTED_SUMMARY.csv")
    folds = pd.read_csv(run / "NESTED_FOLD_METRICS.csv")
    external = pd.read_csv(run / "EXTERNAL_METRICS.csv")
    predictions = pd.read_csv(run / "EXTERNAL_PREDICTIONS.csv")
    params = pd.read_csv(run / "SELECTED_PARAMS.csv")
    bootstrap = pd.read_csv(run / "PAIRED_CLUSTER_BOOTSTRAP.csv")
    deltas = pd.read_csv(run / "PAIRED_FOLD_DELTAS.csv")
    audit = pd.read_csv(run / "FIT_AUDIT_SUMMARY.csv")
    selections = json.loads((run / "FINAL_SELECTIONS.json").read_text())
    comparisons = json.loads((run / "POSTFREEZE_ORIGINAL_REPRODUCTION.json").read_text())
    write_json(output / "VALIDATION.json", {"status": "passed", "checks": checks, "run": str(run),
               "training_warning_count": int(audit.warning_count.sum()), "test_suite": "19 passed",
               "manuscript_integration": "reviewed source unavailable; replacement blocks supplied"})
    # Export concise tables with explicit aggregation semantics.
    development = pd.DataFrame([{
        "Variant": r.MODEL, "AUROC mean +/- SD": f"{r.AUROC_mean:.4f} +/- {r.AUROC_sd:.4f}",
        "AUPRC mean +/- SD": f"{r.AUPRC_mean:.4f} +/- {r.AUPRC_sd:.4f}",
        "Pooled BA": r.POOLED_BA, "Pooled MCC": r.POOLED_MCC,
        "Sensitivity": r.POOLED_SENSITIVITY, "Specificity": r.POOLED_SPECIFICITY,
        "TP": r.TP, "FN": r.FN, "TN": r.TN, "FP": r.FP,
    } for r in summary.itertuples(index=False)])
    development.to_csv(output / "DEVELOPMENT_TABLE.csv", index=False)
    cr = predictions[predictions.EVALUATION == "CR8"].pivot(index=["ID", "name", "LABEL"], columns="MODEL", values=["SCORE", "PRED"])
    cr.columns = [f"{m}_{v}" for m, v in cr.columns]
    cr = cr.reset_index()
    cr.to_csv(output / "CR8_COMPOUND_TABLE.csv", index=False)
    hold = external[external.EVALUATION == "historical_holdout"]
    baseline = summary[summary.MODEL == VARIANTS[0]].iloc[0]
    fixed = summary[summary.MODEL == VARIANTS[1]].iloc[0]
    tuned = summary[summary.MODEL == VARIANTS[2]].iloc[0]
    methods = """The original MLP baseline used StandardScaler followed by scikit-learn 1.9.0 MLPClassifier, with ReLU activation, Adam, max_iter=2000, early_stopping=True, validation_fraction=0.1, and random_state=20260824. It was trained without class balancing. The implementation omitted sample weights when the MLP was introduced; no contemporaneous rationale establishes why. The recorded library supported sample_weight, so a library restriction cannot be cited as the explanation. LR, RF and the three SVC-based baselines retained their original weighting mechanisms. This initial asymmetry remains a limitation of the original comparison.

We conducted an additional retrospective sensitivity analysis using the same X10 features, molecules and frozen partitions. For every training fit, class weights were calculated as w_c=N_fit/(2 n_c,fit) from that fit's labels and passed only to the MLP as sample weights. The scaler and all evaluation metrics remained unweighted; no resampling was used. Analysis A fixed each outer fold's hyperparameters and the final configuration to those selected by the original unweighted MLP. Analysis B repeated the full 12-candidate search over hidden_layer_sizes={(32,), (32,16)}, alpha={0.0001,0.001,0.01}, and learning_rate_init={0.0003,0.001}, using five frozen outer folds and four inner cluster-disjoint StratifiedGroupKFold partitions with seeds 20260824+outer_fold. Mean unweighted inner AUROC selected the first highest-scoring ParameterGrid candidate.

For each variant and outer training partition, thresholds were estimated separately from complete inner OOF predictions by maximizing MCC, then balanced accuracy, then minimizing the absolute threshold and finally the threshold itself. Final configuration selection used the five frozen Development folds; its OOF predictions determined a final threshold under the same rule, followed by training on all Development. Selection OOF metrics are not an additional unbiased estimate of generalization. All configurations, thresholds and model artifacts were frozen before the new input CSV evaluations of the historical holdout and CR8. These datasets and historical predictions had already been observed, so the extension is retrospective, not a new blind evaluation.

Native early stopping was preserved in both variants. Its stratified 10% molecule reservation is not cluster disjoint, and StandardScaler is fitted before that reservation. Weights are derived from the enclosing CV training fit, including this native stopping reservation; no CV evaluation, holdout or CR8 labels contribute to the class counts. The native implementation carries these weights into stopping accuracy and normalizes both the loss gradient and L2 penalty by each minibatch's weight sum. Therefore Analysis A measures the effect of native weighted training, including its stopping behavior, rather than a pure loss-gradient effect with an invariant stopping trajectory. Architecture, optimizer, alpha, batch size, tolerance and stopping settings were not changed.

Differences were paired on the same outer folds. For comparison with the original project statistics, we also used 2,000 paired Butina-cluster bootstrap resamples of fixed pooled OOF scores (seed 20260824). These descriptive intervals condition on the fitted predictions, do not repeat training or selection, and do not constitute multiplicity-adjusted hypothesis tests. Cross-fold score calibration and overlapping training sets limit interpretation of pooled statistics and five-fold consistency."""
    results = f"""The original MLP was reproduced before interpreting balancing: all five nested OOF folds, selected configurations, thresholds, historical-holdout predictions and CR8 predictions agreed with the recorded campaign (maximum absolute score difference {max(c['max_abs_score_difference'] for c in comparisons):.2e}; tolerance 1e-10). Its Development outer-fold AUROC was {baseline.AUROC_mean:.3f} +/- {baseline.AUROC_sd:.3f} and AUPRC {baseline.AUPRC_mean:.3f} +/- {baseline.AUPRC_sd:.3f}; historical-holdout AUROC was 0.462. Thus the reviewed approximate values refer to the outer-fold mean and holdout, respectively; pooled nested OOF AUROC was 0.668.

With original hyperparameters fixed (Analysis A), outer-fold AUROC became {fixed.AUROC_mean:.3f} +/- {fixed.AUROC_sd:.3f} and AUPRC {fixed.AUPRC_mean:.3f} +/- {fixed.AUPRC_sd:.3f}. With full retuning (Analysis B), AUROC was {tuned.AUROC_mean:.3f} +/- {tuned.AUROC_sd:.3f} and AUPRC {tuned.AUPRC_mean:.3f} +/- {tuned.AUPRC_sd:.3f}. Paired mean AUROC changes were +0.0113 and +0.0021, respectively. At the fold-specific MCC thresholds, pooled toxic recall changed from 75/222 to 79/222 and 75/222, while false positives increased from 15/490 to 39/490 and 36/490. Recall improved in four folds but fell from 12/37 to 1/37 in the third fold in both balanced variants. Consequently sensitivity did not improve consistently. Pooled MCC decreased from 0.428 to 0.344 and 0.338.

The descriptive pooled AUROC bootstrap intervals included zero for both balanced-minus-original comparisons (A: -0.0242 to 0.0356; B: -0.0369 to 0.0258). For retuned pooled AUPRC the difference was -0.0474, with a descriptive interval of -0.0989 to -0.0009. This negative pooled result differs from the small outer-fold mean change and must not be described as a global discrimination improvement. No causal explanation of the MLP's overall inferiority is established by these results.

On the historical holdout, AUROC/AUPRC changed from 0.462/0.302 to 0.481/0.332 in A and 0.482/0.329 in B. Using separately frozen thresholds (original 0.524583, A 0.536224, B 0.528334), toxic recovery increased from 4/49 to 11/49 and 13/49, while specificity fell from 128/132 (0.970) to 116/132 (0.879) and 110/132 (0.833). False positives rose from 4 to 16 and 22. Discrimination therefore remained weak, whereas the major practical change was increased positive decisions with a specificity cost.

In CR8, both balanced variants detected Isocycloseram, which the original missed; all variants missed Ethiprole. Fluoxapiprolin became an additional false positive, while Florylpicoxamid remained a false positive. AUROC/AUPRC decreased from 0.833/0.583 to 0.667/0.450 in A and 0.583/0.367 in B. Recovering one of two toxic compounds cannot establish population sensitivity or robust regional generalization.

All 693 fits stopped before 2,000 iterations (12-77 iterations) without recorded training warnings. This verifies finite training and the configured stopping behavior, not optimization to a global or stationary solution. Native stopping reservations shared 14-32 clusters with their gradient-training subsets. An independent complete rerun reproduced all tabular outputs exactly. The balanced retuned MLP remains numerically below every other BeeQ model in mean outer AUROC; RF remains highest at 0.748. The quantum-versus-matched-RBF results are unaffected. The findings therefore preserve BeeQ's central comparative conclusions while qualifying the original MLP limitation: balancing improves retrospective toxic recovery at the price of more false positives and does not resolve its weak discrimination."""
    reviewer = """We thank the reviewer for identifying the unbalanced MLP baseline. We verified that the original implementation omitted sample weights; its recorded scikit-learn version supported weighting, and no documented rationale establishes why weights were omitted. We retained the original results and added two retrospective analyses: a paired comparison with the original hyperparameters fixed, and a fully retuned balanced MLP under the same 5-outer/4-inner cluster protocol and 12-candidate search. The original predictions were reproduced, and an independent complete rerun matched all tabular outputs. Development mean AUROC changed from 0.677 to 0.688 (fixed) and 0.679 (retuned), without consistent sensitivity improvement. On the historical holdout, toxic recovery increased from 4/49 to 11/49 and 13/49, but false positives increased from 4 to 16 and 22; AUROC remained 0.481-0.482. In CR8, one previously missed toxic compound was recovered, with an additional false positive and lower discrimination. We have supplied revised Methods and Results text and a supplementary analysis reporting weights, thresholds, selected parameters, convergence, paired differences and compound-level predictions. The original limitation and the retrospective nature of the external evaluations remain explicit; our central comparative conclusions are unchanged."""
    patch_text = f"""# Manuscript replacement and insertion blocks (English)

The exact reviewed PDF and current main manuscript source are absent from this
checkout. `README.md` and `docs/AUDITABILITY.md` explicitly record removal of
paper sources. Historical `02ff85e:.tmp_paper/main.tex` is an incomplete draft,
not an authoritative copy of the reviewed manuscript. Do not replace the active
paper with that draft. The anchors below are verified in that Git source and
identify the corresponding reviewed-paper sections for editorial integration.

## Methods: Section III-D, Classical and Quantum Models

Insert after `\\label{{sec:models}}`, immediately following the classical-model
paragraph. Retain the original LR/RF/SVC descriptions and their weighting.

{methods}

## Results: Section IV-A, Chemical Space and Classical Baselines

Insert after `\\label{{sec:results-classical}}` and the original baseline table.
Add supplementary Tables S1-S7 and the additional sensitivity figure; retain
the original MLP row and label both new rows as additional analyses A/B.

{results}

## Directly affected table/figure corrections

- `\\label{{tab:model_performance}}`: replace the caption with:
  "Original Development comparison. AUROC and AUPRC are the mean +/- sample SD
  over five outer folds; balanced accuracy and MCC use pooled nested OOF
  decisions at fold-specific, inner-OOF-selected thresholds. Additional balanced
  MLP sensitivity results are reported separately in Supplementary Table S1."
- Correct the original MLP AUROC SD from `0.125` to `0.124` at three decimals.
- Preserve the historical MLP label and add clearly separate sensitivity rows
  only if expanding the main table. Use `DEVELOPMENT_TABLE.csv`, rather than
  mixing final-selection CV results with nested performance.
- Section IV-D (`\\label{{sec:results-ad}}`): incorporate the holdout and CR8
  paragraphs above and refer to S2/S5. Preserve CR8's two-positive limitation.
- Supplement: use the new self-contained `MLP_BALANCING_SUPPLEMENT.tex` and
  the additional `MLP_SENSITIVITY.png` from the run. Its figure caption is:
  "Retrospective MLP class-weight sensitivity using frozen X10 partitions.
  Left: paired outer-fold AUROC. Middle: historical-holdout AUROC. Right:
  sensitivity (solid) and specificity (faded) at separately frozen thresholds.
  A fixes original hyperparameters; B repeats the original search."
- Any blanket statement that all original models were balanced must explicitly
  exempt the original MLP. Keep its original unbalanced result traceable.

## Response to reviewer

{reviewer}
"""
    (output / "MANUSCRIPT_REPLACEMENTS_EN.md").write_text(patch_text, encoding="utf-8")
    (output / "REVIEWER_RESPONSE_EN.md").write_text(reviewer + "\n", encoding="utf-8")
    convergence = audit.groupby("variant").agg(FITS=("n_iter", "size"), MIN_ITER=("n_iter", "min"), MAX_ITER=("n_iter", "max"), WARNINGS=("warning_count", "sum"), STOPPING_CLUSTER_OVERLAP_MIN=("stopping_cluster_overlap", "min"), STOPPING_CLUSTER_OVERLAP_MAX=("stopping_cluster_overlap", "max")).reset_index()
    report = f"""# BeeQ: diagnóstico, validación y sensibilidad del MLP balanceado

Fecha de trabajo: 8 de octubre de 2026 (America/Costa_Rica). Los nombres de
artefactos usan UTC. Ejecución definitiva: `{run.relative_to(ROOT).as_posix()}`.

## 1. Diagnóstico y evidencia

La implementación original omitió pesos; no se pudo establecer la intención de
los autores. El commit `5a410041c9807aa499e8cf3f64bd855f21d51558` introdujo
`MLPClassifier` con early stopping y sin ponderación. Su mensaje y diff no
explican la decisión. Los requisitos de ese commit y `01_CONFIG/ENVIRONMENT.json`
de la campaña final registran scikit-learn 1.9.0, que admite `fit(sample_weight)`.
No corresponde atribuir la ausencia a una restricción de esa versión.

Un notebook auxiliar no versionado prueba balanceo solamente si el constructor
expone `class_weight`. Confundir esa API con `sample_weight` es una hipótesis
plausible; no hay vínculo causal demostrado con el runner final. Se conserva su
hash y extracto en `AUXILIARY_EVIDENCE.json`. Véase
`docs/MLP_BALANCING_DIAGNOSIS.md` para el diagnóstico emitido antes de implementar.

LR usa `balanced`, RF `balanced_subsample` y los tres SVC (RBF, Product e IQP-ZZ)
usan `balanced`. El MLP no recibía pesos ni remuestreo. La procedencia de los
otros cinco modelos fue verificada: 51 artefactos de referencia y ocho fuentes
coinciden con sus hashes (normalizando únicamente CRLF/LF en fuentes), y 42
tablas por modelo/partición/fold concuerdan con sus predicciones. No se repitieron
esos modelos porque ninguna corrección modificó su entrenamiento.

Development: 712 moléculas, 490 negativas/222 tóxicas; holdout: 181, 132/49;
CR8: 8, 6/2. La AUROC original es 0.677099 +/- 0.124483 en los cinco folds;
0.667687 corresponde a OOF agrupado. El holdout confirma 0.462430. Las cifras
aproximadas aportadas por el usuario concuerdan con los resultados originales;
el PDF revisado no está disponible para comprobar todas sus referencias.

La reserva nativa de early stopping divide moléculas sin agrupar por cluster;
el escalador ya se ajustó cuando se crea esa reserva. Conservamos esta limitación
en ambas variantes. El runner histórico suprimía ConvergenceWarning, de modo que
sus registros no bastaban para evaluar convergencia.

## 2. Cambios, justificación y control experimental

- `src/mlp_sensitivity.py`: runner aditivo e inmutable, tres variantes claramente
  nombradas; usa las funciones y espacios originales sin modificar el pipeline
  compartido. `balanced_weights` calcula N/(2*n_c) exclusivamente con las
  etiquetas recibidas por el ajuste de entrenamiento. `checked_fit` pasa los
  pesos solamente a `model__sample_weight`, conserva el escalador sin pesos,
  registra la reserva nativa y captura todas las advertencias.
- `tests/test_mlp_sensitivity.py`: fórmula y masas de clase, separación de grupos,
  equivalencia de la búsqueda manual con GridSearchCV, aislamiento del escalador
  y repetición determinista de entrenamiento ponderado.
- `src/mlp_sensitivity_report.py`: auditoría independiente de artefactos, pesos,
  pertenencia a particiones, métricas y umbrales; genera este informe y material
  editorial a partir de resultados validados.
- `.gitattributes`: conserva los finales de línea históricos de cinco CSV de
  entrada y cinco artefactos anteriores. Git con core.autocrlf=true había cambiado
  sus bytes. Se restauró LF únicamente tras demostrar que el hash resultante
  coincidía exactamente con el manifiesto; no se cambió ninguna molécula, etiqueta,
  descriptor, partición ni cifra. Los artefactos históricos recuperaron su
  identidad original; sus manifiestos y modelos no se reescribieron.

**A, efecto directo:** los mismos hiperparámetros originales seleccionados para
cada fold y para el ajuste final, con las mismas particiones, semillas y escalado.
La diferencia deliberada es pasar los pesos al entrenamiento nativo. Los umbrales
se estiman de nuevo por variante, tal como exige el protocolo. **B, protocolo
completo:** 12 candidatos y el mismo presupuesto: 240 ajustes HPO anidados y 60
en selección final, para original y balanceado. A tiene 31 ajustes; cada búsqueda
completa, 331 incluyendo los ajustes posteriores a HPO.

La versión instalada admite ponderación desde la API oficial. El entrenamiento
pondera la entropía cruzada y sus gradientes; L2 se normaliza por la suma de pesos
del minibatch, no por su número de muestras. Los pesos suman N antes de la reserva
nativa; no necesariamente suman el tamaño de cada minibatch o subconjunto de
gradiente. Early stopping usa accuracy ponderada en su reserva con los mismos
pesos derivados del ajuste local. Por ello A controla la configuración pero no
aísla exclusivamente la pérdida de su interacción nativa con parada y L2. No se
modificaron librería, ReLU/Adam, arquitectura, optimizador, tolerancia, 10% de
reserva, batch_size='auto', max_iter=2000 ni paciencia de 10 iteraciones.

Las etiquetas de la reserva nativa forman parte del ajuste CV que define los
pesos; no entran etiquetas de la validación interna/externa, holdout o CR8. Esta
distinción es explícita y no equivale a una reserva de parada independiente.

## 3. Validación y estado final

{chr(10).join('- ' + c + '.' for c in checks)}

La tolerancia 1e-10 se fijó antes de interpretar el balanceo: en el mismo entorno
y con las mismas semillas se espera coincidencia numérica; permite únicamente
redondeo de coma flotante, no discrepancias de selección o decisiones. La mayor
diferencia original de score fue {max(c['max_abs_score_difference'] for c in comparisons):.3e}.
Parámetros y decisiones históricas coinciden; los umbrales difieren únicamente
por redondeo numérico. La suite completa termina con **19 tests aprobados**.

{table(convergence)}

Ningún ajuste alcanzó max_iter y no se registraron advertencias de entrenamiento.
Esto demuestra parada finita bajo la política configurada, no convergencia a un
óptimo global ni resolución del problema de la reserva por moléculas.

Las primeras pruebas pequeñas fallaron por verificación demasiado estricta de
finales de línea de fuentes, una columna de OOF mal nombrada en el nuevo auditor,
y los hashes de CSV convertidos por Git. Sus STATUS.json se conservaron. La
prueba `smoke_20261009_v4` completó las tres ramas con parámetros fijos del primer
fold. La primera ejecución completa guardó NaN para estadísticas de selección no
aplicables a A; se corrigió a null y se ejecutó un segundo análisis completo,
`full_20261009_v2`, con igualdad exacta de todos los CSV frente al anterior. Las
ejecuciones fallidas y la primera ejecución no son la entrega definitiva.

## 4. Resultados de Development

AUROC/AUPRC son media +/- desviación estándar muestral entre folds. BA, MCC,
sensibilidad, especificidad y confusión en esta tabla son OOF agrupados con los
umbrales estimados localmente; las medias/SD de las seis métricas se conservan
por separado en `NESTED_SUMMARY.csv`.

{table(development)}

Métricas y umbrales por fold:

{table(folds, ['MODEL','OUTER_FOLD','NEGATIVE','POSITIVE','AUROC','AUPRC','BALANCED_ACCURACY','MCC','SENSITIVITY','SPECIFICITY','TP','FN','TN','FP','THRESHOLD'])}

Hiperparámetros seleccionados:

{table(params, ['MODEL','OUTER_FOLD','BEST_PARAMS','THRESHOLD'])}

Diferencias emparejadas balanceado menos original:

{table(deltas)}

{table(deltas.groupby('MODEL')[['AUROC','AUPRC','SENSITIVITY','SPECIFICITY']].mean().reset_index())}

## 5. Holdout histórico y CR8 después de congelar Development

{table(external, ['MODEL','EVALUATION','N','NEGATIVE','POSITIVE','AUROC','AUPRC','BALANCED_ACCURACY','MCC','SENSITIVITY','SPECIFICITY','TP','FN','TN','FP','THRESHOLD'])}

Configuraciones finales: original y A usan (32,16), alpha=0.01, learning_rate_init
=0.0003. B usa (32,16), alpha=0.001, learning_rate_init=0.001. Se seleccionan con
los cinco folds de Development; sus umbrales son 0.5245830869, 0.5362241016 y
0.5283342876. Son específicos de cada distribución de scores y no se optimizaron
con datos externos. Los resultados de la selección final tienen sesgo de selección
y no reemplazan la validación anidada.

Predicciones CR8 (1=tóxico):

{table(cr)}

Isocycloseram pasa de falso negativo a verdadero positivo en ambas variantes.
Ethiprole continúa como falso negativo. Fluoxapiprolin se añade como falso
positivo y Florylpicoxamid sigue siendo falso positivo. Los otros cuatro
compuestos conservan la decisión negativa. Los IDs de CR8 son locales a ese
panel, no identificadores globales de las moléculas del corpus interno.

## 6. Estadística e impacto científico

{table(bootstrap)}

Los intervalos son descriptivos sobre predicciones OOF agrupadas, con remuestreo
pareado de 374 clusters de Butina y 2.000 réplicas. No reentrenan modelos ni
incorporan incertidumbre de HPO; P_DELTA_GT_0 es una proporción bootstrap, no un
p-valor. Los cinco folds comparten entrenamiento y tampoco constituyen cinco
experimentos independientes. Scores de modelos distintos por fold pueden estar
calibrados de forma diferente; una media por fold y una AUROC/AUPRC agrupada
responden preguntas distintas.

1. **¿Por qué no estaba balanceado?** Se confirma la omisión de pesos en fit;
   el motivo autoral no está documentado. Restricción de la librería descartada
   para el entorno registrado; confusión entre APIs es una hipótesis limitada.
2. **¿Explica el desempeño inferior?** Explica parte de la baja recuperación
   retrospectiva de tóxicos al umbral en holdout, pero no resuelve la discriminación
   ni demuestra la causa del desempeño inferior frente a otras familias.
3. **¿Mejora sensibilidad consistentemente?** No: mejora en cuatro folds, pero
   en el tercero cae de 12/37 a 1/37. A recupera 4 tóxicos adicionales en OOF
   agrupado; B recupera el mismo total que el original. Holdout mejora en ambas.
4. **¿Discriminación o decisiones?** Principalmente decisiones. AUROC media
   cambia +0.0113 en A y +0.0021 en B. AUPRC agrupada empeora; holdout permanece
   por debajo de AUROC 0.5 pese a una pequeña mejora. CR8 empeora en AUROC/AUPRC.
5. **¿Especificidad y FP?** OOF: FP 15 -> 39/36; holdout: 4 -> 16/22. Mayor
   recuperación tiene un costo considerable en especificidad.
6. **¿Conclusiones centrales?** RF conserva la mayor AUROC media (0.748) y B
   queda por debajo de las otras cinco familias. La comparación Product/IQP-ZZ
   frente a RBF no cambia; no surge evidencia nueva de ventaja cuántica.
7. **¿Incertidumbres?** Intención autoral, variación entre semillas no estudiadas,
   parada temprana basada en moléculas y accuracy, calibración entre folds,
   incertidumbre de selección no capturada por bootstrap, holdout previamente
   observado y solo dos positivos en CR8. No debe generalizarse sensibilidad
   regional ni atribuir toda diferencia al gradiente de pérdida por separado.

## 7. Actualización editorial

Se entregan `MANUSCRIPT_REPLACEMENTS_EN.md`, `REVIEWER_RESPONSE_EN.md`, tablas
CSV y `MLP_BALANCING_SUPPLEMENT.tex`. El manuscrito activo revisado no está en el
checkout; no se reconstruyó sobre un borrador histórico incompleto. Las ubicaciones
se verificaron en `02ff85e:.tmp_paper/main.tex`: III-D/sec:models,
IV-A/sec:results-classical, IV-D/sec:results-ad y tab:model_performance. Ese borrador
denomina pooled OOF una tabla mixta de media/SD y métricas agrupadas, y redondea
0.124483 a 0.125. Los bloques corrigen ambas inconsistencias directamente
afectadas. Se conserva la fila original y se añaden A/B como análisis posteriores.

La figura adicional `{run.relative_to(ROOT).as_posix()}/MLP_SENSITIVITY.png`
compara folds, discriminación y decisiones del holdout. Las figuras y tablas
históricas permanecen trazables. `EDITORIAL_QA.json` registra por separado el
resultado de compilación y la comprobación editorial; integración y compilación
del manuscrito revisado completo quedan pendientes de sus fuentes actuales.

## 8. Respuesta al revisor (English)

{reviewer}

## 9. Reproducibilidad

```powershell
# Desde C:\\Github_Repos\\BeeQ; usar .venv, no el Python global 3.14.5.
.\\.venv\\Scripts\\python.exe -m pytest -q
.\\.venv\\Scripts\\python.exe -m src.mlp_sensitivity --smoke --output-dir results/mlp_sensitivity/NEW_SMOKE
.\\.venv\\Scripts\\python.exe -m src.mlp_sensitivity --output-dir results/mlp_sensitivity/NEW_FULL --compare-to {run.relative_to(ROOT).as_posix()}
.\\.venv\\Scripts\\python.exe -m src.mlp_sensitivity_report --run results/mlp_sensitivity/NEW_FULL --output-dir docs/mlp_sensitivity
git diff --check
```

Las rutas de salida de ejecuciones deben ser nuevas. `PROVENANCE.json` registra
versiones, plataforma, comando, commit/dirty status, hashes de inputs y fuentes,
y hash del código instalado del MLP. Python 3.12.8, sklearn 1.9.0, NumPy 2.5.1,
pandas 2.3.3; semillas de modelo 20260824, internas 20260825-20260829,
bootstrap 20260824. `CONFIG.json`, `SPLIT_MEMBERSHIP.csv`, `HPO_CANDIDATES.csv`,
`THRESHOLD_OOF_PREDICTIONS.csv`, `FIT_AUDIT.json`, los tres .pkl portables,
`DEVELOPMENT_FREEZE.json` y `MANIFEST_SHA256.csv` contienen la evidencia completa.
Los pesos finales son 712/(2*490)=0.7265306122 y
712/(2*222)=1.6036036036; cada partición tiene sus propios pesos.

Los modelos finales solo reciben X10 después del freeze. La verificación inicial
leyó predicciones históricas para comprobar procedencia, lo que se registra de
forma explícita. Ni el freeze nuevo ni la ausencia de lectura temprana de los
CSV externos convierten esta extensión en una evaluación ciega.

## 10. Pendientes y problemas fuera de alcance

No quedan ajustes, predicciones o comprobaciones numéricas del análisis A/B
pendientes. Falta integrar los bloques en la fuente exacta del manuscrito revisado
y compilar ese proyecto completo; el suplemento independiente sí dispone de
fuente y se valida por separado. La causa autoral sigue sin poder determinarse.
No se realizaron nuevos análisis de semillas, arquitecturas ni cambios de parada.
Las inconsistencias de representación y otros placeholders del borrador histórico
no se corrigieron porque ese borrador no es la fuente revisada y exceden el alcance.
"""
    (output / "REPORT_ES.md").write_text(report, encoding="utf-8")
    supplement(output, methods, results, development, folds, external, params, cr, bootstrap, convergence, run)
    print(f"Verified results and wrote report/editorial artifacts to {output}")


def tex_escape(text):
    mapping = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#", "{": r"\{", "}": r"\}"}
    return "".join(mapping.get(c, c) for c in str(text))


def tex_table(frame, columns, caption, label, fmt=None):
    data = frame[columns]
    alignment = "l" + "r" * (len(columns) - 1)
    header = " & ".join(tex_escape(c) for c in columns) + " \\\\\n"
    rows = []
    for row in data.itertuples(index=False, name=None):
        values = []
        for c, v in zip(columns, row):
            if isinstance(v, (float, np.floating)):
                values.append(f"{v:.{(fmt or {}).get(c, 3)}f}")
            else:
                values.append(tex_escape(v).replace("+/-", "$\\pm$"))
        rows.append(" & ".join(values) + " \\\\")
    numbers = {"tab:s1": "S1a", "tab:s1b": "S1b", "tab:s2historical_holdout": "S2a",
               "tab:s2bhistorical_holdout": "S2b", "tab:s2CR8": "S2c", "tab:s2bCR8": "S2d",
               "tab:s4": "S4", "tab:s5": "S5a", "tab:s5b": "S5b", "tab:s6": "S6", "tab:s7": "S7"}
    for i, variant in enumerate(VARIANTS):
        numbers["tab:s3" + variant] = "S3" + chr(ord("a") + i * 2)
        numbers["tab:s3b" + variant] = "S3" + chr(ord("b") + i * 2)
    number = numbers[label]
    # Every panel is small: keep its caption/header/data together on one page.
    return f"\\renewcommand{{\\thetable}}{{{number}}}\n\\begin{{center}}\n\\begin{{minipage}}{{\\textwidth}}\\centering\\small\n\\refstepcounter{{table}}\\label{{{label}}}\nTable {number}: {caption}\\par\\smallskip\n\\begin{{tabular}}{{{alignment}}}\n\\toprule\n{header}\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{minipage}\n\\end{center}\n"


def supplement(output, methods, results, development, folds, external, params, cr, bootstrap, convergence, run):
    short = {VARIANTS[0]: "Original", VARIANTS[1]: "Balanced A", VARIANTS[2]: "Balanced B"}
    dev = development.copy()
    dev["Variant"] = dev.Variant.map(short)
    dev = dev.rename(columns={"AUROC mean +/- SD": "AUROC mean/SD", "AUPRC mean +/- SD": "AUPRC mean/SD", "Sensitivity": "Sens.", "Specificity": "Spec."})
    parts = [r"\documentclass[10pt]{article}", r"\usepackage[a4paper,margin=18mm]{geometry}",
             r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}",
             r"\usepackage{lmodern}",
             r"\usepackage{amsmath,booktabs,longtable,array,hyperref}",
             r"\hypersetup{colorlinks=true,urlcolor=blue,pdftitle={BeeQ: retrospective MLP class-weight sensitivity}}",
             r"\setlength{\LTcapwidth}{\textwidth}",
             r"\newcommand{\sectionspace}{\par\begingroup\dimen0=\pagegoal\advance\dimen0 by-\pagetotal\ifdim\dimen0<180pt\newpage\fi\endgroup}",
             r"\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}",
             r"\renewcommand{\thetable}{S\arabic{table}}",
             r"\begin{document}", r"\title{BeeQ: retrospective MLP class-weight sensitivity}",
             r"\author{Reproducibility and editorial supplement}\date{8 October 2026}\maketitle",
             r"\textbf{Status.} Additional analyses A/B retain the original unweighted baseline; external evaluations are retrospective. The reviewed main manuscript source is unavailable in this checkout.",
             r"\section{Methods}", tex_escape(methods).replace("+/-", r"$\pm$"),
             r"\[w_c=\frac{N_{\mathrm{fit}}}{2n_{c,\mathrm{fit}}},\qquad w_i=w_{y_i},\quad c\in\{0,1\}.\]",
             r"\section{Results}", tex_escape(results).replace("+/-", r"$\pm$"),
             r"\section{Development summary}"]
    parts.append(tex_table(dev, ["Variant", "AUROC mean/SD", "AUPRC mean/SD", "Pooled BA", "Pooled MCC"],
                           "AUROC/AUPRC: outer-fold mean and sample SD. BA/MCC: pooled nested OOF decisions. A fixes original hyperparameters; B repeats the search.", "tab:s1"))
    parts.append(tex_table(dev, ["Variant", "Sens.", "Spec.", "TP", "FN", "TN", "FP"],
                           "Pooled nested Development decisions (490 negative, 222 toxic).", "tab:s1b"))
    parts.append(r"\section{External evaluation and frozen thresholds}")
    e = external.copy()
    e["Variant"] = e.MODEL.map(short)
    for partition in ("historical_holdout", "CR8"):
        g = e[e.EVALUATION == partition]
        parts.append(tex_table(g, ["Variant", "AUROC", "AUPRC", "BALANCED_ACCURACY", "MCC", "THRESHOLD"],
                               tex_escape(partition) + ": discrimination and frozen-threshold metrics.", "tab:s2" + partition,
                               {"THRESHOLD": 6}))
        parts.append(tex_table(g, ["Variant", "SENSITIVITY", "SPECIFICITY", "TP", "FN", "TN", "FP"],
                               tex_escape(partition) + ": toxic recovery and specificity.", "tab:s2b" + partition))
    parts.append(r"\section{Outer folds and selected hyperparameters}")
    for variant in VARIANTS:
        f = folds[folds.MODEL == variant].rename(columns={"OUTER_FOLD": "Fold", "BALANCED_ACCURACY": "BA", "SENSITIVITY": "Sens.", "SPECIFICITY": "Spec."})
        parts.append(tex_table(f, ["Fold", "AUROC", "AUPRC", "BA", "MCC", "Sens.", "Spec.", "THRESHOLD"], short[variant] + ": outer-fold metrics.", "tab:s3" + variant, {"THRESHOLD": 6}))
        parts.append(tex_table(f, ["Fold", "NEGATIVE", "POSITIVE", "TP", "FN", "TN", "FP"], short[variant] + ": outer-fold class counts and decisions.", "tab:s3b" + variant))
    p = params.copy()
    parsed = p.BEST_PARAMS.map(json.loads)
    p["Variant"] = p.MODEL.map(short)
    p["Fold"] = p.OUTER_FOLD
    p["Layers"] = parsed.map(lambda x: str(x["model__hidden_layer_sizes"]))
    p["Alpha"] = parsed.map(lambda x: x["model__alpha"])
    p["Rate"] = parsed.map(lambda x: x["model__learning_rate_init"])
    parts.append(tex_table(p, ["Variant", "Fold", "Layers", "Alpha", "Rate", "THRESHOLD"], "Selected outer-fold configurations and thresholds.", "tab:s4", {"Alpha": 4, "Rate": 4, "THRESHOLD": 6}))
    parts.append(r"Original and A final configuration: layers (32,16), $\alpha=0.01$, initial learning rate 0.0003. B final configuration: layers (32,16), $\alpha=0.001$, initial learning rate 0.001. Final selection uses the five frozen Development folds, not external labels.")
    parts.append(r"\section{CR8 compound predictions}")
    c = cr.rename(columns={"name": "Compound", "LABEL": "Truth"}).copy()
    for variant in VARIANTS:
        c[short[variant] + " score"] = c["SCORE_" + variant]
        c[short[variant] + " pred"] = c["PRED_" + variant].astype(int)
    parts.append(tex_table(c, ["Compound", "Truth", "Original score", "Balanced A score", "Balanced B score"], "CR8 scores (positive class = toxic).", "tab:s5"))
    parts.append(tex_table(c, ["Compound", "Truth", "Original pred", "Balanced A pred", "Balanced B pred"], "CR8 decisions at separately frozen thresholds; only two compounds are toxic.", "tab:s5b"))
    parts.append(r"\section{Paired cluster bootstrap}")
    b = bootstrap.copy()
    b["Comparison"] = b.LEFT_MODEL.map(lambda x: short.get(x, "RF")) + " - " + b.RIGHT_MODEL.map(short)
    b = b.rename(columns={"OBSERVED_DELTA": "Delta", "CI_LOW_95": "CI low", "CI_HIGH_95": "CI high"})
    parts.append(tex_table(b, ["Comparison", "METRIC", "Delta", "CI low", "CI high", "P_DELTA_GT_0"], "2,000 paired cluster resamples of pooled OOF predictions. Intervals are descriptive; the last column is not a p-value.", "tab:s6"))
    parts.append(r"\section{Training audit and reproducibility}")
    a = convergence.rename(columns={"variant": "Variant", "MIN_ITER": "Min iter", "MAX_ITER": "Max iter"}).copy()
    a["Variant"] = a.Variant.map(short)
    parts.append(tex_table(a, ["Variant", "FITS", "Min iter", "Max iter", "WARNINGS"], r"All fits stopped before max\_iter=2000; no recorded training warnings. This is not proof of global optimization.", "tab:s7"))
    parts.append(r"Python 3.12.8; scikit-learn 1.9.0; NumPy 2.5.1; pandas 2.3.3. Model seed 20260824; inner seeds 20260825--20260829; bootstrap seed 20260824. Full-Development class weights: 0.7265306122 (negative), 1.6036036036 (toxic). All five outer and twenty inner CV splits are cluster disjoint. Native early-stopping reservations are not: 14--32 clusters overlap their gradient subsets. No resampling or evaluation weighting was used. All CSV outputs match an independent complete rerun exactly.")
    parts.append(r"\textbf{Repeat from the repository root with its historical environment:}")
    parts.append("\\begin{verbatim}\n.\\.venv\\Scripts\\python.exe -m src.mlp_sensitivity\n# Add --output-dir NEW_PATH; existing bundles are never overwritten.\n.\\.venv\\Scripts\\python.exe -m src.mlp_sensitivity_report\n# Add --run NEW_PATH --output-dir docs/mlp_sensitivity\n\\end{verbatim}")
    parts.append("\\textbf{Authoritative bundle:} \\path{" + run.relative_to(ROOT).as_posix() + "}.")
    parts.append(r"The bundle contains input/source hashes, exact split memberships, candidate-level AUROCs, selected parameters, threshold OOF predictions, full fit/stopping histories, model artifacts, post-freeze external predictions and metrics, paired statistics, a sensitivity figure and integrity manifests. The separate manuscript replacement file maps this additional analysis to Methods III-D, Results IV-A/IV-D and the original baseline table without deleting the initial limitation.")
    parts.append(r"\textbf{Library references:} \href{https://scikit-learn.org/1.9/modules/generated/sklearn.neural_network.MLPClassifier.html}{Official MLPClassifier API documentation} and the locally hashed 1.9.0 implementation. No runtime dependency was upgraded.")
    parts.append(r"\end{document}")
    content = "\n\n".join(parts).replace(r"\section{", r"\sectionspace\section{")
    (output / "MLP_BALANCING_SUPPLEMENT.tex").write_text(content + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/mlp_sensitivity")
    args = parser.parse_args()
    build(args.run.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()
