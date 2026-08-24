# BeeQ corrected campaign summary

Campaign: `20260824T183229Z_418787d0cc`  
Status: complete  
Protocol: corrected X10, nested structure-aware model selection, historical
holdout, exact-statevector quantum comparison, and external challenge audit.

## Executive summary

The campaign evaluated five classical models, two exact quantum fidelity
kernels, and one matched classical kernel using the ten corrected BeeQ
descriptors. Random Forest led development OOF ranking performance. XGBoost
had the strongest classical OOF MCC. IQP-ZZ led the two quantum kernels in
development OOF. The MLP had the highest classical holdout AUROC but weak MCC,
so this isolated result is not evidence that it is the best generalizing
model. No exact or RDKit-canonical SMILES overlap was found between the
893-molecule internal corpus and the eight-molecule external panel.

The external panel is an exploratory challenge because it contains only eight
independent molecules: six negative and two positive. Its metrics must not be
used for model or threshold selection or as definitive generalization evidence.

## Data and protocol

| Partition | Rows | Positive | Negative | Role |
| --- | ---: | ---: | ---: | --- |
| Development | 712 | 222 | 490 | Nested structure-aware HPO and OOF |
| Historical holdout | 181 | 49 | 132 | Previously inspected holdout |
| Internal master | 893 | 271 | 622 | Curated reference corpus |
| External challenge | 8 | 2 | 6 | Exploratory external evaluation |

- Representation: corrected X10 descriptors.
- Outer folds: five frozen structure-aware folds.
- Inner folds: four folds for hyperparameter selection.
- Primary HPO metric: AUROC.
- Seed: 42.
- External overlap: zero exact SMILES and zero RDKit-canonical SMILES.

## Classical development OOF

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| Random Forest | 0.7567 | 0.6711 | 0.6793 | 0.4125 |
| XGBoost | 0.7324 | 0.6429 | 0.6788 | 0.4383 |
| Logistic regression | 0.7223 | 0.6436 | 0.6898 | 0.4003 |
| RBF-SVC | 0.7157 | 0.6237 | 0.6725 | 0.4188 |
| MLP | 0.6518 | 0.5742 | 0.6621 | 0.4052 |

Random Forest had the highest OOF AUROC. XGBoost had the highest OOF MCC.

## Classical historical holdout

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| MLP | 0.7327 | 0.5412 | 0.5601 | 0.2336 |
| RBF-SVC | 0.7058 | 0.4992 | 0.6102 | 0.2634 |
| XGBoost | 0.6875 | 0.5236 | 0.6050 | 0.2751 |
| Logistic regression | 0.6848 | 0.4907 | 0.6895 | 0.3869 |
| Random Forest | 0.6790 | 0.5112 | 0.6446 | 0.3369 |

The MLP holdout AUROC should be interpreted alongside its low balanced
accuracy and MCC. Logistic regression had the strongest holdout MCC.

## Quantum and matched-kernel development OOF

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| IQP-ZZ fidelity kernel | 0.7211 | 0.6329 | 0.6737 | 0.4192 |
| Product-state fidelity kernel | 0.7186 | 0.6169 | 0.6742 | 0.4128 |
| Matched RBF kernel | 0.7157 | 0.6237 | 0.6725 | 0.4188 |

The quantum kernels were close to the matched RBF control. These results do
not establish a quantum advantage.

## Quantum and matched-kernel historical holdout

| Model | AUROC | AUPRC | Balanced accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| Matched RBF kernel | 0.7058 | 0.4992 | 0.6102 | 0.2634 |
| Product-state fidelity kernel | 0.6974 | 0.4596 | 0.5642 | 0.1819 |
| IQP-ZZ fidelity kernel | 0.6962 | 0.4633 | 0.5642 | 0.1819 |

## External eight-molecule challenge

| Model | AUROC | AUPRC | Balanced accuracy | MCC | Predicted positive |
| --- | ---: | ---: | ---: | ---: | ---: |
| Logistic regression | 0.7500 | 0.5000 | 0.6667 | 0.3333 | 6 |
| RBF-SVC | 0.7500 | 0.5000 | 0.6667 | 0.3333 | 2 |
| Random Forest | 0.6667 | 0.4500 | 0.6667 | 0.3333 | 2 |
| XGBoost | 0.5833 | 0.4167 | 0.5833 | 0.1491 | 3 |
| IQP-ZZ | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 0 |
| Exploratory MLP | 0.3333 | 0.2667 | 0.5000 | 0.0000 | 0 |

These values are unstable because only two external positives are present.

## Selected full-development hyperparameters

- Logistic regression: `C=100`.
- RBF-SVC: `C=1`, `gamma=0.03`.
- Random Forest: no maximum depth, `min_samples_leaf=3`.
- XGBoost: 200 trees, depth 3, learning rate 0.03, subsample 0.8,
  column sample 0.8.
- MLP: hidden layers `(32, 16)`, alpha 0.01, learning rate 0.001.
- Matched RBF kernel: `C=1`, `gamma=0.03`.
- Product-state kernel: `C=1`, feature scale 0.25.
- IQP-ZZ kernel: `C=1`, feature scale 0.125, interaction strength 1.0.

## Folder contents

- `classical/`: classical run configuration, fold metrics, OOF predictions,
  summaries, selected parameters, holdout predictions, and nested manifest.
- `quantum/`: quantum and matched-kernel metrics, predictions, diagnostics,
  selected parameters, holdout results, and nested manifest.
- `external/`: external metrics, OOF diagnostic predictions, dependency
  availability, and exact/canonical SMILES overlap audit.
- `logs/`: captured output from all three campaign phases.
- `data_snapshot/`: local corrected inputs. This directory is ignored by Git;
  source and snapshot hashes are retained in the manifests.
- Root JSON files: frozen campaign configuration, environment, Git state, and
  the top-level integrity manifest.

## Integrity and limitations

- The campaign completed successfully.
- All 32 original campaign artifacts passed SHA-256 verification before this
  summary was added.
- The summary is included in the top-level manifest after generation.
- Historical results remain provenance only and must not be mixed with this
  corrected campaign.
- The holdout was previously inspected and is not a pristine unseen test.
- The external sample is too small for definitive claims.
- Bootstrap confidence intervals and paired uncertainty estimates are still
  required before selecting the final paper headline model.
