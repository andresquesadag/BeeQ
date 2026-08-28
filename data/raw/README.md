# ApisTox QML pre-screening handoff — X10

Generated: 2026-08-15T00:05:20

## 1. Purpose

This folder is the handoff package for the ML/QML team working on acute
honey-bee toxicity classification using the curated ApisTox domain.

This is a **pre-screening / development package**. It is not a claim of
state-of-the-art QSAR performance.

The molecular endpoint is binary acute toxicity for *Apis mellifera*:

- `LABEL = 1`: toxic, strongest available acute LD50 <= 11 microgram/bee.
- `LABEL = 0`: non-toxic, strongest available acute LD50 > 11 microgram/bee.

The model therefore predicts the binary class directly. It does **not**
predict a continuous LD50 and then threshold that prediction.

## 2. Files

### `master.csv`
All 893 curated molecules in one table.

### `train.csv`
712-molecule DEVELOPMENT set. This file contains the frozen
`STRICT_CV_FOLD` assignment for structure-aware model development.

### `test.csv`
181-molecule historical structure-aware holdout.

**Important:** this holdout has already been evaluated during pre-screening
(X10 and X9 experiments). It must therefore not be described as a pristine
unseen confirmatory test in the manuscript. It remains useful as a fixed
historical holdout / external-to-training benchmark.

## 3. Curated molecular domain

Curated organic/metal-free ApisTox working domain:

- Total N = 893
- DEVELOPMENT = 712
- TEST = 181
- DEVELOPMENT labels: 0 = 490, 1 = 222
- DEVELOPMENT positive prevalence = 0.311798
- TEST labels: 0 = 132, 1 = 49
- TEST positive prevalence = 0.270718

All exported rows have unique IDs and finite values for all X10 descriptors.

## 4. Structure-aware split

The working split was constructed from molecular structure using:

- Morgan/ECFP radius = 2
- fingerprint size = 1024 bits
- chirality enabled
- Butina clustering cutoff = 0.60
- group-aware stratification
- DEVELOPMENT / TEST cluster overlap = 0

Current exported cluster counts:

- DEVELOPMENT clusters = 374
- TEST clusters = 88

The DEVELOPMENT set also contains five frozen `STRICT_CV_FOLD` assignments.
These folds should be reused for classical and quantum model comparison rather
than regenerated to obtain a more favorable split.

The split should be described as a **structure-aware cluster-disjoint
holdout**, not as a mathematically strict OOD split.

## 5. X10 molecular representation

The exported molecular representation contains exactly ten descriptors:

1. `MolLogP`
   RDKit Crippen octanol/water lipophilicity estimate.

2. `MolWt`
   Molecular weight; global molecular-size dimension.

3. `TPSA_SP`
   RDKit topological polar surface area calculated with sulfur and phosphorus
   contributions enabled (`CalcTPSA(..., includeSandP=True)`).

4. `NumHDonors`
   Number of hydrogen-bond donors.

5. `NumRotatableBonds`
   Molecular flexibility / rotatable-bond count.

6. `NumAromaticRings`
   Aromatic-ring count.

7. `nHalogen`
   Total atom count for F + Cl + Br + I.

8. `n_OP`
   Count of organophosphorus-like centers using the frozen SMARTS:
   `[P;X4](=[O,S])([O,S][#6])([O,S][#6])`.
   This is a structural count, not a statement that every phosphorus-containing
   molecule is toxic.

9. `LiPHEX_prediction`
   Frozen in-house predicted hexadecane/water partition coefficient.
   It is an auxiliary partition descriptor, not a bee-toxicity model.

10. `sasa002_frac_polar_hetero_only`
    In-house 3D molecular-surface descriptor representing the fraction of
    solvent-accessible surface assigned to polar heteroatom surface.

The X10 representation intentionally mixes:
- conventional physicochemical properties,
- molecular architecture,
- a broad halogen composition variable,
- one explicit organophosphorus structural motif,
- one alternative partitioning descriptor,
- one 3D surface-polarity descriptor.

## 6. Variables intentionally not exported as model features

Pesticide-use metadata such as `insecticide`, `herbicide`, `fungicide`,
`other_agrochemical`, source and year are intentionally omitted from the
handoff feature matrix.

They may be used for stratified error analysis, but should not silently enter
the molecular prediction model because they can act as strong shortcut
variables.

## 7. Development history

The descriptor work proceeded as exploratory pre-screening.

### Initial in-house-only compact representations

An initial X5/X7 representation made mostly of LiPHEX plus selected in-house
3D physicochemical descriptors performed weakly under the frozen
structure-aware folds.

Representative results:
- RBF X5 pooled OOF AUROC ~ 0.522
- RBF X7 pooled OOF AUROC ~ 0.604

Changing RobustScaler to StandardScaler did not resolve the problem.
Logistic regression and CatBoost diagnostics indicated that scaling alone was
not the main bottleneck.

### FREE20 in-house screening

A wider pool of 20 in-house descriptors improved CatBoost development
performance:
- FREE20 CatBoost OOF AUROC = 0.6925
- FREE20 AUPRC = 0.5601
- FREE20 MCC = 0.2717

Adding LiPHEX to FREE20 produced essentially unchanged AUROC (~0.6917),
which was treated as inconclusive rather than proof that LiPHEX is useless.

### Hybrid X10

A literature-informed hybrid representation was then assembled from RDKit,
fragment/element counts, LiPHEX and one in-house surface descriptor.

Development-only HPO on X10:
- RBF best: C = 1.0, gamma = 0.03, mean CV AUROC = 0.72544
- CatBoost best: depth = 3, learning_rate = 0.03, l2_leaf_reg = 10,
  mean CV AUROC = 0.74181
- Logistic regression best C = 100

First historical holdout evaluation for X10:

| Model | AUROC | AUPRC | BA | MCC |
|---|---:|---:|---:|---:|
| Logistic regression | 0.6891 | 0.5156 | 0.6933 | 0.3975 |
| RBF-SVC | 0.6977 | 0.4975 | 0.5872 | 0.2246 |
| CatBoost | 0.7031 | 0.5348 | 0.6514 | 0.3112 |

The holdout therefore showed moderate ranking performance (~0.70 AUROC) but
only modest binary classification performance. Logistic regression produced
the highest observed MCC on the historical holdout.

## 8. X10 feature-ablation result

A DEVELOPMENT-only permutation + leave-one-feature-out analysis found that
removing `NumHDonors` improved OOF AUROC in all three diagnostic model
families:

- LR: +0.0142 AUROC
- RBF: +0.0125 AUROC
- CatBoost: +0.0074 AUROC

This generated an exploratory X9 representation.

However, X9 did **not** improve the historical holdout consistently:

| Model | X10 AUROC | X9 AUROC |
|---|---:|---:|
| Logistic regression | 0.6891 | 0.6877 |
| RBF-SVC | 0.6977 | 0.6981 |
| CatBoost | 0.7031 | 0.6869 |

Accordingly, this handoff deliberately exports the broader **X10** panel for
the ML team. `NumHDonors` should be treated as a pre-specified ablation
candidate rather than silently deleted.

## 9. Important representation observations

Development X10 showed one strong redundancy:

- Spearman(`TPSA_SP`, `sasa002_frac_polar_hetero_only`) = 0.834

Other useful observations:
- Spearman(`MolLogP`, `LiPHEX_prediction`) = 0.405
- `n_OP` is sparse (mode = 0; ~87.6% zeros in DEVELOPMENT)
- `nHalogen` is discrete and zero for ~54.5% of DEVELOPMENT
- all ten features are finite in the exported domain

Permutation/LOFO analyses strongly identified `n_OP` as important for the
current classification task. This suggests that explicit structural/mode-of-
action information carries signal not captured by global physicochemical
properties alone.

## 10. Recommended ML/QML use

For classical pre-screening:
- use the frozen five DEVELOPMENT folds;
- class weighting is appropriate for the moderate class imbalance;
- report at minimum AUROC, AUPRC, balanced accuracy and MCC;
- do not use pesticide-use metadata as hidden features.

For the classical-vs-quantum comparison:
- both kernels must receive the exact same molecular coordinates;
- preprocessing must be fitted only on training folds;
- hyperparameter-search budgets should be matched as closely as practical;
- the main purpose is paired kernel comparison, not claiming state-of-the-art
  bee-toxicity prediction.

X10 is suitable as a compact handoff representation. A smaller X9 can be
treated as a dimensionality/ablation experiment.

## 11. Test-set status

The 181-molecule holdout has been inspected during pre-screening.

Therefore:
- do not call it untouched/virgin after this point;
- do not repeatedly redesign features from its scores;
- retain the exact historical test results for auditability;
- any later confirmatory claim should rely on a clearly declared evaluation
  strategy rather than pretending this test was never opened.

## 12. Output SHA-256 hashes

- `master.csv`: `a73800d9123caf4e7dfc0a5833b2fb3c7d4514b3593e1b7d9974994ed54eab96`
- `train.csv`: `deb88b60578cb44f3e64912cbc30d0aaa1f518f5ed91c45af9bcedf1a2c1ad7c`
- `test.csv`: `0b6cabbb62e5b10751b080aac118d0c92b7d7177bd8e00c7c3986e1d061fcdb1`

Source X10 file hashes:
- `DEVELOPMENT_712_X10.csv`: `78b380198a35ba2acd704e73b7c7693fdcd9bac4948c3231be771ce9986c07e5`
- `LOCKED_TEST_181_X10.csv`: `a60a97855b90292c9bb9366a9f20ff69611b6bb3bcccfa09c55637eda30d516e`

## 13. Feature columns

```text
MolLogP
MolWt
TPSA_SP
NumHDonors
NumRotatableBonds
NumAromaticRings
nHalogen
n_OP
LiPHEX_prediction
sasa002_frac_polar_hetero_only
```

## 14. Target column

```text
LABEL
```

with:
- 1 = acute toxic class (LD50 <= 11 microgram/bee)
- 0 = acute non-toxic class (LD50 > 11 microgram/bee)

## 15. Split/fold columns

- `SET`
- `BUTINA_CLUSTER_ID`
- `STRICT_CV_FOLD` (defined only for DEVELOPMENT)
