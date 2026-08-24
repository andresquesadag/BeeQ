# External validation

This folder contains the guarded runtime for the three BeeQ deployment baselines—random forest, classical RBF-SVC, and exact-statevector IQP-ZZ—plus the workflow for one independently documented external CSV per run. The authoritative packages live in `deployment_baseline/model_packages/`. External observations and generated molecule-level results remain private and outside version control.

The current committed baseline bundle is a read-only reference for provenance and context at `results/final/20260818T070959Z_f1f76c91f3/`, including `all_metrics.csv`. Its saved metrics remain historical context, not the fitted objects used for export. The three exported final packages were refit on the full 893-molecule curated reference corpus (development plus historical holdout) and must not be represented as the same fitted objects that generated the development/holdout metrics.

`runtime.py` provides guarded package interfaces and `run.py` executes the complete private validation. The workflow validates the input and exact X10 matrix, verifies every model artifact against a deterministic refit, computes applicability, returns three-model predictions/disagreement, evaluates observed labels with 2,000 bootstrap replicates, and hashes every output. It does not compute descriptors from SMILES.

## Run the tool

From the project root, run:

```powershell
python -m external_validation.run --input <private-external.csv> --data-dir <private-reference-data-dir>
```

Each invocation creates a unique ignored folder under `external_validation/output/`. The input may use the public template names or the native BeeQ handoff names (`ID`, `SMILES`, `LABEL`, and all X10 columns).

## Practical run flow

The intended future flow is:

1. Obtain one approved, independently documented CSV handoff for the run.
2. Confirm data-use, privacy, and redistribution permissions before copying or processing it.
3. Validate the input schema, identifiers, labels, units, missingness, and structure fields.
4. Recompute the exact X10 descriptor definitions required by the packaged model, including any approved in-house descriptors.
5. Load all three explicitly versioned packages from `deployment_baseline/model_packages/` and verify their manifests, hashes, and deterministic refits.
6. Generate random-forest, RBF-SVC, and IQP-ZZ predictions, scores, model-disagreement flags, applicability/domain flags, and provenance.
7. Compare predictions with observed laboratory labels only after endpoint, units, label provenance, and approved metrics are reviewed.
8. Write validation reports and approved private outputs to a unique subfolder under `external_validation/output/`; never overwrite the baseline bundle or a prior run.

The supplied `input_template.csv` contains headers and one clearly fictional example row for testing an upload flow. It is not a real compound or observation and must not be used as scientific evidence.

## Input and privacy

Do not commit real molecule records, SMILES, laboratory results, personal information, confidential sample identifiers, or proprietary descriptors. Keep the one-run input CSV and generated outputs in a private, access-controlled location. Before sharing any aggregate result, obtain the required laboratory, institutional, and source-data approvals.

The proposed project-root-relative paths are:

- `baseline_results_dir = results/final/20260818T070959Z_f1f76c91f3/` — read-only provenance/reference bundle only.
- `output_root = external_validation/output/` — private external-validation output root.
- `run_output_dir = external_validation/output/<unique-run-id>/` — one unique subfolder per future input/run.

The expected label convention follows the current BeeQ reference documentation: `observed_label=1` means strongest available acute LD50 <= 11 microgram/bee, and `observed_label=0` means above that threshold. `observed_label` and `observed_ld50_ug_per_bee` may be empty for prediction-only submissions, but evaluation requires an approved observed label definition and provenance.

## Current limitations

- No private external laboratory dataset is committed.
- The deployment packages are new 893-row fits, not the original evaluation objects; historical metrics are read-only context.
- The current repository does not provide a complete public package that recomputes every X10 descriptor, including the in-house descriptors.
- The historical BeeQ holdout was previously inspected and is not a substitute for a new independent validation set.
- External validation must preserve the model’s exact feature order, units, preprocessing, endpoint definition, and versioned provenance.
- Applicability flags are required because performance declines for compounds distant from the reference descriptor space.

## Run status and expected outputs

The runtime is operational for an approved CSV that already contains the exact X10 matrix and labels. Descriptor-contract mismatches, structural overlap, and rows outside the applicability boundary are retained as explicit warnings rather than silently discarded.

The private output set for each unique run is: an input manifest and hash; validation and deployment-verification reports; per-model predictions and continuous scores; disagreement and applicability fields; bootstrap metrics and paired comparisons; threshold sensitivity; two aggregate paper figures; one generated LaTeX table; and run metadata linking back to the read-only baseline bundle. Generated outputs are ignored by `output/.gitignore`; the baseline results remain separate and are never overwritten.

## Files

- `input_template.csv`: safe schema example only.
- `external_validation_template.ipynb`: non-executed workflow guide with placeholder cells.
- `output/README.md`: privacy and review rules for future exports.
- `output/`: reserved for reviewed private results; the directory is kept with `.gitkeep` only.
- `runtime.py`: guarded package/provenance/input/run-boundary interfaces; no model artifact is included.
- `model_package.schema.json`: manifest contract for a future approved package.
- `../deployment_baseline/model_packages/random_forest/`: approved full-reference random-forest package.
- `../deployment_baseline/model_packages/rbf_svc/`: approved full-reference classical RBF-SVC package.
- `../deployment_baseline/model_packages/quantum_iqp_zz_linear/`: approved full-reference exact IQP-ZZ package.

The package artifacts are deployment-oriented refits, not a rerun of the research comparison. Their primary decision thresholds are the frozen estimator defaults; development-OOF Youden thresholds are reported only as sensitivity analyses and never fitted to external labels. Applicability uses the 95th percentile of leave-one-out nearest-neighbor distance in standardized reference X10 space.
