# BeeQ 70/20/10 campaign summary

Campaign: `20260825T034056Z_cd0dba4468`  
Status: complete  
Seed: 42  
Representation: corrected X10 descriptors.

## Split construction

The split was generated exclusively from the corrected 893-row master. The
old 73-row `Externalset.csv` was used only as a reservation list; none of its
stored descriptor values were copied into model inputs.

| Partition | Rows | Fraction | Negative | Positive |
| --- | ---: | ---: | ---: | ---: |
| Train/development | 625 | 69.99% | 435 | 190 |
| Historical holdout | 179 | 20.04% | 125 | 54 |
| External | 89 | 9.97% | 62 | 27 |

Of the 73 reference molecules, 71 could be linked to corrected master rows by
canonical SMILES or CAS. `lambda-Cyhalothrin` and `Tefluthrin` were not present
in the master and were not fabricated. Eighteen additional master rows were
sampled reproducibly by label to complete the 89-row external partition.

Two reference labels disagreed with the master (`Flutriafol` and
`Mesotrione`); the corrected master labels were authoritative.

## Leakage audit

- External/internal ID overlap: 0.
- External/internal exact SMILES overlap: 0.
- External/internal RDKit-canonical SMILES overlap: 0.
- Train/holdout Butina-cluster overlap: 0.
- External/internal Butina-cluster overlap: 40 clusters.

The last item is an explicit limitation. Forcing all 71 available reference
molecules outside while preserving a 10% external size cannot also provide
complete cluster isolation. Moving every related cluster outside would require
234 of 893 molecules (26.2%), no longer a 70/20/10 design.

## Classical development OOF

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| Random Forest | 0.7694 | 0.6912 | 0.7007 | 0.4938 |
| Logistic regression | 0.7681 | 0.6633 | 0.7143 | 0.4339 |
| XGBoost | 0.7575 | 0.6846 | 0.7004 | 0.4988 |
| RBF-SVC | 0.7374 | 0.6504 | 0.6970 | 0.4044 |
| MLP | 0.6039 | 0.5138 | 0.6191 | 0.3392 |

Random Forest led OOF AUROC, while XGBoost had the highest OOF MCC.

## Quantum development OOF

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| Product-state quantum kernel | 0.7399 | 0.6492 | 0.6990 | 0.4121 |
| Matched RBF kernel | 0.7373 | 0.6504 | 0.6970 | 0.4044 |
| IQP-ZZ quantum kernel | 0.7283 | 0.6351 | 0.6850 | 0.3839 |

The quantum results are close to the matched RBF control and do not establish
a quantum advantage.

## Holdout evaluation with development-selected parameters

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| Random Forest | 0.7645 | 0.6717 | 0.7510 | 0.5532 |
| XGBoost | 0.7557 | 0.6399 | 0.7085 | 0.4446 |
| Product-state quantum kernel | 0.7113 | 0.6027 | 0.6725 | 0.3469 |
| MLP | 0.7093 | 0.5922 | 0.6797 | 0.4541 |
| IQP-ZZ quantum kernel | 0.7062 | 0.6149 | 0.6740 | 0.3655 |
| Matched RBF kernel | 0.6890 | 0.6139 | 0.6607 | 0.3377 |
| RBF-SVC | 0.6889 | 0.6138 | 0.6607 | 0.3377 |
| Logistic regression | 0.6879 | 0.5777 | 0.6685 | 0.3370 |

Random Forest led both holdout AUROC and MCC.

## External evaluation with development-selected parameters

| Model | AUROC | AUPRC | Balanced accuracy | MCC | Positive predictions |
| --- | ---: | ---: | ---: | ---: | ---: |
| MLP | 0.6947 | 0.6113 | 0.6135 | 0.3461 | 9 |
| XGBoost | 0.6858 | 0.6083 | 0.6368 | 0.3275 | 16 |
| Random Forest | 0.6846 | 0.6413 | 0.6852 | 0.5391 | 10 |
| IQP-ZZ quantum kernel | 0.6792 | 0.6125 | 0.6682 | 0.3584 | 22 |
| Product-state quantum kernel | 0.6762 | 0.6059 | 0.6682 | 0.3584 | 22 |
| Matched RBF kernel | 0.6559 | 0.5780 | 0.6496 | 0.3240 | 21 |
| RBF-SVC | 0.6559 | 0.5780 | 0.6496 | 0.3240 | 21 |
| Logistic regression | 0.6308 | 0.5720 | 0.6705 | 0.3489 | 25 |

The MLP had the highest external AUROC, but Random Forest had the strongest
external AUPRC, balanced accuracy, and MCC. The external partition was not
used for hyperparameter selection.

## Selected full-development hyperparameters

- Logistic regression: `C=100`.
- RBF-SVC: `C=100`, `gamma=0.01`.
- Random Forest: no maximum depth, `min_samples_leaf=1`.
- XGBoost: 200 trees, depth 3, learning rate 0.1, subsample 0.8,
  column sample 0.8.
- MLP: hidden layers `(32, 16)`, alpha 0.0001, learning rate 0.001.
- Matched RBF kernel: `C=100`, `gamma=0.01`.
- Product-state kernel: `C=100`, feature scale 0.125.
- IQP-ZZ kernel: `C=10`, feature scale 0.125, interaction strength 1.0.

## Traceability

- `audit/` contains the split manifest, old-reference matching audit, and an
  immutable copy of the old reference list.
- `classical/` contains nested-CV HPO, OOF and holdout artifacts.
- `quantum/` contains exact-kernel HPO, diagnostics and holdout artifacts.
- `external/` contains selected-model metrics, predictions and overlap audit.
- `data_snapshot/` contains the exact local inputs and is ignored by Git.
- `logs/` contains captured output for every phase.
- The root `manifest.json` hashes every campaign artifact.
