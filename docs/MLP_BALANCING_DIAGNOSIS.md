# MLP balancing: pre-implementation diagnosis

This diagnosis precedes the new sensitivity implementation. The reference is
`results/campaigns/BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z`, the portable
reexecution of the final 20260825 campaign, not the older 70/20/10 experiments.

## Confirmed facts and limits of attribution

- Commit `5a410041c9807aa499e8cf3f64bd855f21d51558` introduced `MLPClassifier`
  into `src/classical_models.py:model_specs`. It specified `max_iter=2000`,
  `early_stopping=True`, and a seeded 12-candidate grid, without weighting.
  Its commit message and diff contain no rationale for that omission.
- `src/final_nested_campaign.py:select_classical`, `classical_inner_oof`,
  `run_nested`, and `final_selection` call `fit(X, y)` without sample weights.
  No sampling, SMOTE, duplication, or other balancing is applied to this MLP.
- The introducing commit's requirements and the final campaign's recorded
  environment specify scikit-learn **1.9.0**, Python **3.12.8**, NumPy **2.5.1**,
  and pandas **2.3.3**. The local `.venv` has those exact versions and its MLP
  fit signature is `(self, X, y, sample_weight=None)`. Thus an inability to
  weight training is **not** supported as the cause in this environment.
- LR uses `class_weight='balanced'`; RF uses `balanced_subsample`; RBF,
  Product QK, and IQP-ZZ QK use precomputed SVC with `class_weight='balanced'`.
  RF weights are computed within bootstrap samples, so the mechanisms are not
  identical across families.
- Local, unversioned `.donotmerge_aux/Bee_project_weightclass.ipynb`, cell 12,
  chooses balancing only by checking for a constructor `class_weight` argument.
  This could explain confusing absent `class_weight` with absent sample-weight
  support. It is **a hypothesis**, not evidence that this notebook caused the
  final implementation. Its SHA-256 and excerpt will be recorded in the run.
- No inspected commit, configuration, or log establishes a deliberate scientific
  reason. The confirmed implementation omission and the undocumented motivation
  must be distinguished; author intent remains undetermined.

## Verified protocol

`src.final_nested_campaign` is the relevant entry point. It freezes five outer
`STRICT_CV_FOLD` partitions and generates four inner StratifiedGroupKFold splits
with seed `20260824 + outer_fold`. Estimators use seed `20260824`. HPO maximizes
unweighted mean inner AUROC, with ParameterGrid ordering breaking exact ties.
The scaler is fitted in each CV training partition. The 12 MLP candidates vary
hidden layers `(32,)`/`(32,16)`, alpha `0.0001/0.001/0.01`, and initial learning
rate `0.0003/0.001`; Adam/ReLU and all remaining defaults come from 1.9.0.

Thresholds use pooled inner OOF scores, maximizing MCC, then balanced accuracy,
then smallest absolute threshold, then smallest threshold. The final Development
selection uses the five frozen outer folds as its selection CV, then an OOF
threshold and a fit on all Development. These selection OOF metrics are not an
unbiased additional performance estimate.

Development has 712 molecules (490 negative, 222 toxic), holdout 181 (132/49),
CR8 8 (6/2). Outer validation counts (negative/toxic) are 97/40, 68/37, 110/37,
122/59, 93/49. The audited outer and generated inner CV partitions are cluster
disjoint; Development/holdout have no shared ID, SMILES, or Butina cluster.
The new runner must use explicit `data/official` paths: an ambient BEEQ_DATA_DIR
can select auxiliary files with equivalent rows but different byte hashes.

## Directly related limitations

Native MLP early stopping reserves 10% of the CV training partition by a
stratified molecule split, not a grouped split. Its scaler was fitted before
this reservation. This does not expose CV validation or holdout to training,
but the stopping subset is not cluster independent and contributes to scaler
statistics. Preserve this in both variants and report it rather than changing
the historical experiment. Native sample weights also weight the stopping
accuracy and change the batch-weight normalization of L2. Consequently this
comparison estimates native weighted training, including its stopping effect,
not an isolated gradient-loss effect with an invariant stopping trajectory.
Weights will be derived only from the labels supplied to each CV training fit;
the native stopping reservation is part of that fit partition. No inner/outer
evaluation, holdout, or CR8 labels enter the class-count calculation.

The original runner globally suppresses ConvergenceWarning, so absence of saved
warnings does not prove convergence. New runs must capture warnings, iteration
counts, loss and stopping histories without modifying training settings.

## Original numerical evidence

Recorded outer AUROC is **0.6770992931740407 +/- 0.12448326823504426** (sample
SD); pooled nested OOF AUROC is **0.667687074829932**, a different quantity.
Historical holdout AUROC is **0.462430426716141**. These agree with the user's
approximate PDF values. The exact reviewed PDF and current manuscript source
are absent from this checkout; historical drafts remain in Git, including
`02ff85e:.tmp_paper/main.tex`. That draft's `tab:model_performance` incorrectly
labels a mixed table as pooled OOF while AUROC/AUPRC are outer-fold mean/SD;
an editorial replacement must distinguish these quantities and correct the
MLP AUROC SD rounding to 0.124 at three decimals.

## Library evidence

- Official API: https://scikit-learn.org/1.9/modules/generated/sklearn.neural_network.MLPClassifier.html
  (`sample_weight` added in 1.7).
- Exact-version source: https://github.com/scikit-learn/scikit-learn/blob/1.9.0/sklearn/neural_network/_multilayer_perceptron.py
- Installed implementation: `.venv/Lib/site-packages/sklearn/neural_network/_multilayer_perceptron.py`,
  `_backprop`, `_fit_stochastic`, `_update_no_improvement_count`, `_score`.

The recorded installed source hash is the execution authority; online 1.9
documentation currently describes the patch release 1.9.1, not a runtime upgrade.
