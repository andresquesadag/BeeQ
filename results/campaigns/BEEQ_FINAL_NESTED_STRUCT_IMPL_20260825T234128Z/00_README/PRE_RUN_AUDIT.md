# BeeQ final nested structure-aware implementation: pre-run audit

Campaign directory: `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260825T234128Z`

Audit time (UTC): `2026-08-25T23:41:28Z`

Repository commit at audit: `46cf3a788a655fc2e1cda2ed3941e8b890accb00`

Repository state at audit: clean (`git status --short` returned no entries and
`git diff --check` passed).

## Audit boundary

This is a pre-run audit only. No model was trained and no campaign result was
copied. The historical holdout and CR8 files were hashed as opaque byte streams;
their CSV contents and labels were not opened. Only the official development
file was parsed for schema, fold, cluster, descriptor, and SMILES checks.

## Official input hashes

All required files exist under `.donotmerge_aux/Luis/01_DATA` and all SHA-256
digests match the frozen values supplied by the team.

| File | Expected and observed SHA-256 | Status |
| --- | --- | --- |
| `master_RDKitFixed.csv` | `a0a6177b3319dba8f210d2358bdd63edbb1c6db3d9b657daa992459b11f2c38e` | PASS |
| `train_RDKitFixed.csv` | `06a0817c082d7715211ca62aae367079f192e1a6c6663c2005c8c8eb5c758984` | PASS |
| `test_RDKitFixed.csv` | `3f964207e5d732315501d11be2d50c4f520e51a8c7f17b70fe8594390988c8f5` | PASS |
| `ExternalFinal_RDKitFixed.csv` | `70a01eedd970991e072eb9db8e2acdbe854dc8d4623b42bb2263318486cd41fb` | PASS |

The master file was not parsed during this audit because it contains the
historical holdout. Its byte-level hash is sufficient before the development
freeze.

## Development data audit

The official `train_RDKitFixed.csv` passed the pre-run checks:

- 712 rows: 490 negative and 222 positive;
- required identity, label, split, cluster, and X10 columns present;
- X10 appears in the required frozen order and all values are finite;
- no duplicated IDs or SMILES;
- all SMILES parse with RDKit;
- `STRICT_CV_FOLD` contains exactly 1, 2, 3, 4, and 5;
- no `BUTINA_CLUSTER_ID` is assigned to more than one outer fold.

| Outer fold | Train N | Validation N | Train 0/1 | Validation 0/1 | Train clusters | Validation clusters | Cluster intersection |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 575 | 137 | 393 / 182 | 97 / 40 | 299 | 75 | 0 |
| 2 | 607 | 105 | 422 / 185 | 68 / 37 | 304 | 70 | 0 |
| 3 | 565 | 147 | 380 / 185 | 110 / 37 | 295 | 79 | 0 |
| 4 | 531 | 181 | 368 / 163 | 122 / 59 | 300 | 74 | 0 |
| 5 | 570 | 142 | 397 / 173 | 93 / 49 | 298 | 76 | 0 |

The campaign will regenerate this table as
`02_DATA_AUDIT/SPLIT_INTEGRITY_AUDIT.csv` and abort if any value violates the
frozen contract.

## Frozen X10

The campaign will import `X10_FEATURES` from `src/config.py` without changing
its values or order:

1. `MolLogP`
2. `MolWt`
3. `TPSA_SP`
4. `NumHDonors`
5. `NumRotatableBonds`
6. `NumAromaticRings`
7. `nHalogen`
8. `n_OP`
9. `LiPHEX_prediction`
10. `sasa002_frac_polar_hetero_only`

No ablations or feature selection will be enabled in the final campaign.

## Existing implementations to reuse

### Classical models

Source: `src/classical_models.py`.

- Logistic regression: `StandardScaler` followed by class-weighted
  `LogisticRegression`, `liblinear`, `max_iter=5000`.
- Random Forest: 300 trees, `class_weight=balanced_subsample`,
  `max_features=sqrt`, one estimator job, deterministic seed. It has no scaler.
- MLP: `StandardScaler` followed by `MLPClassifier`, `max_iter=2000`,
  `early_stopping=True`, deterministic seed.
- The standalone pipeline also has an RBF-SVC, but the principal matched-kernel
  comparison will reuse the precomputed RBF implementation from
  `src/quantum_experiment.py` so RBF and quantum kernels share the same folds,
  scaling, SVC machinery, and score type.
- XGBoost exists. It will not be part of the six-model primary analysis. It may
  be run later as a clearly separated secondary/SI analysis without affecting
  any freeze or selection.

Classical implementation SHA-256:
`02c9a111c7e0891f69d081a988a1b340bc208100098576a82d125aa1a002f64a`.

### Matched RBF kernel

Sources: `src/quantum_experiment.py` and `src/kernels.py`.

The matched control is an exact precomputed RBF Gram matrix
`exp(-gamma * squared_euclidean_distance)` followed by a class-weighted
precomputed-kernel SVC. `StandardScaler` is fitted independently on the
training rows of every inner or outer split.

### Product-state quantum fidelity kernel

Sources: `src/quantum_feature_maps.py`, `src/quantum_experiment.py`, and
`src/kernels.py`.

The existing implementation is retained exactly. For X10 it uses 10 qubits and
one descriptor per qubit. Each standardized and scaled descriptor `x_j` is
encoded as `RY(x_j)|0>`, represented directly by the local amplitudes
`[cos(x_j/2), sin(x_j/2)]`. The complete state is the tensor product of the ten
local states, with statevector dimension 1024. There is no entanglement,
hardware, noise, or shots. The Gram matrix is the squared state fidelity
`|<psi(x)|psi(y)>|^2`.

### IQP-ZZ quantum fidelity kernel

Sources: `src/quantum_feature_maps.py`, `src/quantum_experiment.py`, and
`src/kernels.py`.

The existing `iqp_zz_linear_statevectors` implementation is retained exactly;
it will not be replaced by another ZZ map. For X10 it uses 10 qubits and a
1024-dimensional exact NumPy statevector. It starts in a uniform superposition
and applies phases corresponding to linear Z terms and nearest-neighbor ZZ
terms. For computational-basis signs `z_j in {+1,-1}`, its implemented phase is

`sum_j x_j z_j + interaction_strength * sum_j x_j x_(j+1) z_j z_(j+1)`.

The state amplitude is `exp(i * phase) / sqrt(2^10)`. The coupling topology is
linear nearest-neighbor, the current interaction strength is fixed at 1.0, and
the kernel is squared state fidelity. There is no hardware, noise, or shots.
The implementation does not use Qiskit at runtime and the repository contains
no separate Qiskit/PennyLane reference circuit to compare against.

Quantum implementation SHA-256 values:

- `src/quantum_experiment.py`: `175482a801fee4313e6c5d3914aebcb1af107962ffc6892873634c97f73b7687`
- `src/quantum_feature_maps.py`: `dce90964bec0a0d899ff934e8e7821cf35bc17a89caad959a3a2938ad763e2d4`
- `src/kernels.py`: `160caf060eff4929552454ed43313ad47773699a66a27dc833b69e11ded56225`

The existing kernel and metric unit tests passed: 6 tests passed. These are
small-sample unit tests, not the requested campaign-wide quantum QC artifact.

## Recovered hyperparameter spaces

The spaces are explicit in the existing code and `configs/quantum.json`.
Nothing needs to be invented or expanded.

| Model | Frozen search space |
| --- | --- |
| Logistic regression | `C = [0.01, 0.1, 1, 10, 100]` |
| Random Forest | `max_depth = [None, 6]`; `min_samples_leaf = [1, 3]` |
| MLP | hidden layers `[(32,), (32,16)]`; `alpha = [0.0001, 0.001, 0.01]`; learning rate `[0.0003, 0.001]` |
| Matched RBF | `C = [0.1, 1, 10, 100]`; `gamma = [0.01, 0.03, 0.1, 0.3]` |
| Product QK | `C = [0.1, 1, 10, 100]`; feature scale `[0.125, 0.25, 0.5, 1.0]` |
| IQP-ZZ QK | `C = [0.1, 1, 10, 100]`; feature scale `[0.125, 0.25, 0.5, 1.0]`; interaction strength fixed at `1.0` |

Fixed estimator settings will also be serialized in
`01_CONFIG/HYPERPARAMETER_SPACES.json` before fitting. The quantum config file
hash is `f88e97fc78d581099340eefa6492a0e496e93bdc35583831d8f5a46ac142a369`.

## Environment observed during audit

| Component | Version/status |
| --- | --- |
| Python | 3.12.8 |
| NumPy | 2.5.1 |
| pandas | 2.3.3 |
| scikit-learn | 1.9.0 |
| XGBoost | 3.4.1 |
| RDKit | 2026.03.5 |
| Qiskit | 2.5.2 |
| Matplotlib | 3.11.1 |
| PennyLane | not installed; not required by the existing kernels |
| Optuna | not installed; not required by the frozen grid search |

## Required adaptations; existing algorithms remain unchanged

The current repository already performs structure-aware nested AUROC model
selection with train-only preprocessing. It does not yet implement all final
protocol requirements. The final campaign code must add the following without
changing the six model or kernel definitions:

1. Generate pooled inner OOF scores after HPO and select an MCC-maximizing
   threshold, with balanced accuracy as deterministic tie-breaker, separately
   for each model and outer fold.
2. Apply that frozen inner-derived threshold to outer validation and save score,
   threshold, margin, prediction, confusion counts, sensitivity, and
   specificity.
3. Separate final development-only selection, artifact hashing, and freeze from
   later holdout/CR8 loading. The current campaign evaluates the holdout in the
   same run function and therefore needs a stricter phase boundary.
4. Tighten and record quantum QC. The current assertion uses `atol=1e-7`; the
   final artifact must record symmetry error, diagonal error, and raw minimum
   eigenvalue and enforce the requested `1e-10`, `1e-10`, and `-1e-8` limits.
5. Implement development-only dual applicability domains. The existing external
   runtime uses standardized one-nearest-neighbor distance over 893 rows, so it
   cannot be reused as-is for the required development-only mean 5-NN rule.
   Structural Morgan AD and top-10 Tanimoto neighbor reporting are new.
6. Replace the existing molecule-stratified paired bootstrap with paired
   `BUTINA_CLUSTER_ID` resampling for the primary statistical comparisons.
7. Add fixed-configuration Y-randomization for all six models. No existing
   Y-randomization implementation was found.
8. Add the required figures, final manifest, automatic scientific summary, and
   stop-condition checks.

## Final implementation and execution plan

No modeling begins until the configuration artifacts below are written and
hashed.

### Phase A: immutable configuration and audits

1. Add a dedicated final-campaign module that writes only into this new
   directory and refuses to overwrite any artifact.
2. Serialize campaign settings, exact model definitions, quantum maps,
   hyperparameter spaces, seed `20260824`, dependency versions, source hashes,
   and code hashes under `01_CONFIG/`.
3. Parse only development, regenerate input/count/fold audits, validate X10,
   SMILES, folds, groups, and inner-split cluster isolation, and abort on any
   mismatch.

### Phase B: primary nested outer evaluation

4. For each frozen outer fold and each of the six primary models, create the
   same deterministic four `StratifiedGroupKFold` inner splits using
   `random_state = 20260824 + outer_fold`.
5. Select hyperparameters by mean inner AUROC only. All preprocessing is fitted
   on the corresponding inner-training rows.
6. With the selected configuration, produce inner OOF scores, select the
   MCC/BA threshold from those scores, refit on the complete outer-training
   partition, and evaluate outer validation once.
7. Enforce exactly 712 unique outer OOF predictions per model and write the
   fold metrics, summary, predictions, selected parameters, and quantum QC.

### Phase C: development-only final freeze

8. Select one configuration per model using the five frozen development folds,
   then generate development OOF scores for the selected configuration and
   derive the final MCC/BA threshold exclusively from those scores.
9. Fit each final model on all 712 development rows. Serialize selections,
   scalers/model state as needed, thresholds, QC, and SHA-256 hashes. Create a
   machine-readable freeze marker containing the complete artifact manifest.
10. Prevent downstream evaluation unless the freeze marker and every upstream
    hash verify exactly.

### Phase D: post-freeze evaluation and interpretation

11. Only after the freeze, parse and validate the historical holdout, evaluate
    it without changes, and label it explicitly as historical and previously
    inspected.
12. Then parse CR8, evaluate the independent external challenge without
    changes, and retain all eight molecule-level results regardless of error or
    applicability status.
13. Compute development-only Morgan P05 and standardized-X10 mean-5NN P95 AD
    thresholds, apply them to CR8, and generate the dual AD and top-10 neighbor
    artifacts. Expected historical values are sanity checks, never targets.

### Phase E: statistics, sanity checks, figures, and manifest

14. Run 2,000 paired cluster-bootstrap replicates for the five required model
    comparisons using the nested outer OOF predictions.
15. Run 200 explicitly labeled fixed-configuration Y-randomization replicates
    for all six models. X10, clusters, outer folds, and frozen configurations
    remain fixed; only development labels are permuted. Kernel matrices can be
    cached because their geometry does not depend on labels.
16. Generate the seven requested publication figures in PNG at 300 dpi plus SVG
    where supported, then write the automatic final summary and the complete
    SHA-256 artifact manifest.
17. Run focused tests, the complete test suite, `git diff --check`, manifest
    verification, and cross-file row/hash consistency checks before declaring
    the campaign complete.

## Stop-condition disposition

No pre-run stop condition was triggered:

- all four input hashes match;
- X10 is complete, finite, and ordered correctly in development;
- development SMILES are valid;
- outer folds are exactly 1 through 5;
- no cluster crosses an outer fold;
- existing HPO spaces are unambiguous;
- existing Product and IQP-ZZ implementations are identified and tested.

The historical holdout and CR8 remain unopened pending the development-only
freeze. Full-size kernel QC and every downstream result remain deliberately
unexecuted at this stage.
