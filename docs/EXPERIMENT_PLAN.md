# BeeQ experiment plan

## Scope

The initial paper tests whether a compact ten-descriptor representation can
screen acute honey-bee toxicity and whether explicit structural information
and a simulated quantum kernel change the learned geometry. Costa Rican
external validation is deferred until a separate regional dataset exists.

## Phase 1 - Foundation

Deliverables:

- validated data contract and immutable feature order;
- SHA-256 hashes for source files and canonical split assignments;
- non-sensitive dataset manifest;
- deterministic configuration files and tests;
- thin notebook and IEEE paper templates.

Acceptance criteria:

- 712 development and 181 historical-holdout rows;
- unique IDs and SMILES;
- finite X10 values;
- labels restricted to 0/1;
- five development folds;
- no Butina-cluster overlap between development and holdout;
- no cluster divided across development folds.

## Phase 2 - Classical baseline and ablations

Models:

- class-weighted logistic regression;
- class-weighted RBF-SVC;
- class-weighted random forest as a nonlinear non-kernel reference.

Representations:

- X10;
- X10 without `n_OP`;
- X10 without `MolLogP`;
- X10 without `LiPHEX_prediction`;
- X10 without both partition descriptors.

Protocol:

1. Treat each frozen `STRICT_CV_FOLD` as one outer validation fold.
2. Fit scaling and select hyperparameters only within outer-training rows.
3. Use stratified group-aware inner CV, grouped by `BUTINA_CLUSTER_ID`.
4. Produce exactly one out-of-fold score per development molecule.
5. Report pooled OOF AUROC, AUPRC, MCC and balanced accuracy, plus fold
   dispersion and model-selection parameters.
6. Keep the historical holdout opt-in and label it as previously inspected.

The primary comparison for each hypothesis is paired by molecule and outer
fold. A result is not selected because it performs better on the historical
holdout.

## Phase 3 - Matched simulated quantum kernels

Candidate maps:

- an angle-encoded product-state control;
- an IQP-style map with nearest-neighbor ZZ interactions.

Required controls:

- same X coordinates, molecule IDs and folds as the RBF experiment;
- train-only preprocessing at every evaluation level;
- comparable search budget for SVC `C` and kernel scale;
- exact statevector kernel first; shot noise is a later sensitivity study;
- PSD, symmetry and unit-diagonal tests before model fitting.

Beyond predictive metrics, compare centered kernel alignment, effective rank,
eigenvalue concentration and molecule-level prediction disagreement.

## Phase 4 - Results and uncertainty

Produce:

- fold and pooled metric tables;
- OOF and historical predictions with molecule IDs;
- paired bootstrap confidence intervals for metric differences;
- ROC and precision-recall curves from OOF scores;
- ablation plot for `n_OP`, `MolLogP` and `LiPHEX_prediction`;
- RBF/quantum kernel alignment and spectra;
- errors stratified by train similarity and structural group.

Every table and figure must be generated from a versioned run directory.

## Phase 5 - IEEE/BIP manuscript

Target a double-blind 6-8 page IEEE conference paper:

1. Introduction and contributions.
2. Related work and ApisTox context.
3. Curated domain, X10 representation and hypotheses.
4. Structure-aware classical and quantum methods.
5. Results, ablations and kernel analysis.
6. Limitations, reproducibility and conclusion.

Claims must distinguish development OOF evidence, historical-holdout evidence
and any future external validation.

## Traceability contract

Each run manifest records:

- source-file and canonical split SHA-256 hashes;
- feature names and order;
- complete experiment configuration and its hash;
- Git commit and dirty-state flag;
- Python and package versions;
- random seeds and CV assignments;
- hashes of generated CSV/JSON outputs;
- evaluation status: `development_oof` or `historical_holdout`.

Hashes make adaptive experimentation auditable; they do not turn a repeatedly
inspected holdout back into an unseen confirmatory test.
