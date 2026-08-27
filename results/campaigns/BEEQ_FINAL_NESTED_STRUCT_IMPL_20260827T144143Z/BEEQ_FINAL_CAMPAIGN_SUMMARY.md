# BeeQ final nested structure-aware campaign summary

Campaign: `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z`  
Status: complete  
Seed: `20260824`

## 1. Dataset and hashes

All four official SHA-256 hashes matched before modeling. Development contained
712 molecules (490 non-toxic, 222 toxic); the historical holdout contained 181
(132/49), and CR8 contained eight (6/2). Holdout and CR8 contents were first
opened only after the development freeze manifest had been written and verified.

## 2. Frozen X10

The exact ordered features were: `MolLogP`, `MolWt`, `TPSA_SP`, `NumHDonors`, `NumRotatableBonds`, `NumAromaticRings`, `nHalogen`, `n_OP`, `LiPHEX_prediction`, `sasa002_frac_polar_hetero_only`.
No feature was added, removed, recalculated, or selected.

## 3. Nested CV protocol and split integrity

Five frozen `STRICT_CV_FOLD` outer folds were used. Within every outer-training
partition, four deterministic `StratifiedGroupKFold` splits grouped by
`BUTINA_CLUSTER_ID` selected hyperparameters by mean AUROC. All outer and inner
cluster intersections were zero. Scalers were fitted only on the corresponding
training rows. Thresholds were selected from inner OOF scores by maximum MCC,
then balanced accuracy, and applied unchanged to outer validation.

## 4. Model and quantum definitions

The primary models were Logistic Regression, Random Forest, MLP, matched RBF,
Product-state fidelity kernel, and IQP-ZZ fidelity kernel. Existing BeeQ
implementations were retained. Both quantum kernels used 10-qubit,
1024-dimensional exact noiseless NumPy statevectors with no shots. IQP-ZZ used
the existing linear nearest-neighbor coupling, not a substituted feature map.

## 5. Primary nested outer results

| MODEL | OUTER_AUROC_MEAN | OUTER_AUROC_SD | OUTER_AUPRC_MEAN | OUTER_AUPRC_SD | POOLED_OOF_BALANCED_ACCURACY | POOLED_OOF_MCC |
| --- | --- | --- | --- | --- | --- | --- |
| random_forest | 0.7480 | 0.0574 | 0.6573 | 0.0966 | 0.6798 | 0.4680 |
| logistic | 0.7328 | 0.1039 | 0.6596 | 0.1241 | 0.6784 | 0.4461 |
| quantum_angle_product | 0.7216 | 0.1075 | 0.6279 | 0.1263 | 0.6576 | 0.3966 |
| quantum_iqp_zz_linear | 0.7130 | 0.1056 | 0.6455 | 0.1122 | 0.6549 | 0.4000 |
| rbf_matched | 0.7106 | 0.1084 | 0.6404 | 0.1067 | 0.6633 | 0.4055 |
| mlp | 0.6771 | 0.1245 | 0.5961 | 0.1383 | 0.6536 | 0.4283 |

These outer results are the primary performance estimates. Inner AUROC values
are selection diagnostics only.

## 6. Final development-only selections

| MODEL | CV_AUROC_MEAN | CV_AUROC_SD | THRESHOLD | PARAMS |
| --- | --- | --- | --- | --- |
| logistic | 0.7328 | 0.0930 | 0.6605 | {"model__C": 100.0} |
| random_forest | 0.7501 | 0.0505 | 0.6826 | {"model__max_depth": null, "model__min_samples_leaf": 3} |
| mlp | 0.6863 | 0.1104 | 0.5246 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.0003} |
| rbf_matched | 0.7350 | 0.1112 | 0.9157 | {"C": 1.0, "gamma": 0.03} |
| quantum_angle_product | 0.7343 | 0.1158 | 0.6462 | {"C": 1.0, "feature_scale": 0.25} |
| quantum_iqp_zz_linear | 0.7346 | 0.1195 | 0.3835 | {"C": 1.0, "feature_scale": 0.125, "interaction_strength": 1.0} |

These selections are not independent performance estimates. They were frozen
and hashed before downstream evaluation.

## 7. Historical holdout

| MODEL | AUROC | AUPRC | BALANCED_ACCURACY | MCC | SENSITIVITY | SPECIFICITY | TP | TN | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 0.6848 | 0.4907 | 0.5551 | 0.1777 | 0.1633 | 0.9470 | 8.0000 | 125.0000 | 7.0000 | 41.0000 |
| random_forest | 0.6926 | 0.5034 | 0.6175 | 0.3579 | 0.2653 | 0.9697 | 13.0000 | 128.0000 | 4.0000 | 36.0000 |
| mlp | 0.4624 | 0.3024 | 0.5257 | 0.1110 | 0.0816 | 0.9697 | 4.0000 | 128.0000 | 4.0000 | 45.0000 |
| rbf_matched | 0.7058 | 0.4992 | 0.5434 | 0.2002 | 0.1020 | 0.9848 | 5.0000 | 130.0000 | 2.0000 | 44.0000 |
| quantum_angle_product | 0.6974 | 0.4596 | 0.5332 | 0.1650 | 0.0816 | 0.9848 | 4.0000 | 130.0000 | 2.0000 | 45.0000 |
| quantum_iqp_zz_linear | 0.6962 | 0.4633 | 0.5295 | 0.1357 | 0.0816 | 0.9773 | 4.0000 | 129.0000 | 3.0000 | 45.0000 |

## 8. CR8 independent external challenge

| MODEL | AUROC | AUPRC | BALANCED_ACCURACY | MCC | SENSITIVITY | SPECIFICITY | TP | TN | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 0.7500 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 6.0000 | 0.0000 | 2.0000 |
| random_forest | 0.7500 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 6.0000 | 0.0000 | 2.0000 |
| mlp | 0.8333 | 0.5833 | 0.4167 | -0.2182 | 0.0000 | 0.8333 | 0.0000 | 5.0000 | 1.0000 | 2.0000 |
| rbf_matched | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 6.0000 | 0.0000 | 2.0000 |
| quantum_angle_product | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 6.0000 | 0.0000 | 2.0000 |
| quantum_iqp_zz_linear | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 6.0000 | 0.0000 | 2.0000 |

CR8 was never used for model, parameter, threshold, feature, or architecture
selection.

## 9. Dual applicability domain and Tanimoto analysis

Development-only thresholds were Morgan P05 LOO Smax =
`0.223134` and standardized-X10 P95 LOO mean
5-NN distance = `2.198975`.

| name | LABEL | Smax_Morgan | d5NN_X10 | DUAL_AD |
| --- | --- | --- | --- | --- |
| Isotianil | 0.0000 | 0.2642 | 1.4041 | IN/IN |
| Fluoxapiprolin | 0.0000 | 0.5408 | 2.4376 | IN/OUT |
| Ethiprole | 1.0000 | 0.7400 | 1.7519 | IN/IN |
| Cyclobutrifluram | 0.0000 | 0.2647 | 1.0123 | IN/IN |
| Isoprothiolane | 0.0000 | 0.2973 | 1.3682 | IN/IN |
| Isocycloseram | 1.0000 | 0.2326 | 1.5794 | IN/IN |
| Spiropidion | 0.0000 | 0.3662 | 1.1636 | IN/IN |
| Florylpicoxamid | 0.0000 | 0.3085 | 1.6809 | IN/IN |

Top-10 Morgan neighbors and local toxic fractions are stored molecule by
molecule. Ethiprole and Isocycloseram were interpreted after freeze and did not
trigger retuning.

## 10. Paired cluster bootstrap

| LEFT_MODEL | RIGHT_MODEL | METRIC | OBSERVED_DELTA | BOOTSTRAP_MEDIAN | CI_LOW_95 | CI_HIGH_95 | P_DELTA_GT_0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| random_forest | logistic | AUROC | 0.0313 | 0.0311 | -0.0210 | 0.0932 | 0.8675 |
| random_forest | logistic | AUPRC | 0.0295 | 0.0280 | -0.0235 | 0.0812 | 0.8520 |
| random_forest | mlp | AUROC | 0.0889 | 0.0879 | 0.0217 | 0.1616 | 0.9955 |
| random_forest | mlp | AUPRC | 0.0986 | 0.0958 | 0.0366 | 0.1522 | 0.9990 |
| quantum_angle_product | rbf_matched | AUROC | 0.0017 | 0.0013 | -0.0197 | 0.0242 | 0.5410 |
| quantum_angle_product | rbf_matched | AUPRC | -0.0281 | -0.0257 | -0.0536 | 0.0008 | 0.0330 |
| quantum_iqp_zz_linear | rbf_matched | AUROC | -0.0014 | -0.0011 | -0.0237 | 0.0255 | 0.4690 |
| quantum_iqp_zz_linear | rbf_matched | AUPRC | -0.0109 | -0.0088 | -0.0380 | 0.0210 | 0.2745 |
| quantum_angle_product | quantum_iqp_zz_linear | AUROC | 0.0032 | 0.0018 | -0.0209 | 0.0279 | 0.5655 |
| quantum_angle_product | quantum_iqp_zz_linear | AUPRC | -0.0172 | -0.0165 | -0.0591 | 0.0206 | 0.2080 |

Intervals are descriptive paired cluster-bootstrap results; no automatic
significance claim is made.

## 11. Y-randomization

| MODEL | REAL_NESTED_OOF_AUROC | MEAN_RANDOMIZED_AUROC | SD_RANDOMIZED_AUROC | P95_RANDOMIZED_AUROC | EMPIRICAL_FRACTION_RANDOMIZED_GE_REAL |
| --- | --- | --- | --- | --- | --- |
| logistic | 0.7252 | 0.4996 | 0.0310 | 0.5516 | 0.0000 |
| random_forest | 0.7565 | 0.4958 | 0.0301 | 0.5430 | 0.0000 |
| mlp | 0.6677 | 0.5013 | 0.0256 | 0.5419 | 0.0000 |
| rbf_matched | 0.7154 | 0.4978 | 0.0304 | 0.5471 | 0.0000 |
| quantum_angle_product | 0.7171 | 0.4980 | 0.0304 | 0.5514 | 0.0000 |
| quantum_iqp_zz_linear | 0.7140 | 0.4979 | 0.0303 | 0.5493 | 0.0000 |

This was explicitly a fixed-configuration Y-randomization with 200 label
permutations on development only.

## 12. Quantum kernel QC

Every recorded selected quantum training matrix met symmetry error `< 1e-10`,
diagonal error `< 1e-10`, and minimum eigenvalue `>= -1e-8`. The repository had
no independent Qiskit/PennyLane reference circuit; the exact NumPy maps are the
canonical prior implementations.

## 13. Limitations

- The 181-molecule test is a historical, previously inspected holdout and is not a pristine confirmatory test.
- CR8 is an independent challenge panel but contains only eight molecules (two positives), so its metrics are highly unstable.
- Y-randomization uses frozen configurations rather than repeating full nested HPO for every permutation.
- The quantum experiments are exact noiseless simulations; they do not demonstrate hardware performance or quantum advantage.
- Thresholds maximize development MCC and therefore require independent prospective validation before operational use.

## 14. Artifacts and reproducibility

Configuration, input audits, fold-level selections, molecule-level predictions,
statistics, QC, figures, environment versions, and final SHA-256 hashes are
contained in the numbered campaign directories. `10_MANIFEST` is the integrity
entry point.
