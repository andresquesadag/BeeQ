# Future external validation

This folder contains the guarded runtime path for the two approved BeeQ deployment baselines—random forest and classical RBF-SVC—plus a future workflow for one independently collected external CSV per run, such as a Costa Rican laboratory dataset. The authoritative packages live in `deployment_baseline/model_packages/`, a separate deployment phase. This folder contains no external observations, raw molecule rows, descriptor-generation implementation, or validation results. It is not a replacement for the existing research pipeline and does not claim that external validation has occurred.

The current committed baseline bundle is a read-only reference for provenance and context at `results/final/20260818T070959Z_f1f76c91f3/`, including `all_metrics.csv`. Its saved metrics remain historical context, not the fitted objects used for export. The two exported final packages were refit on the full 893-molecule curated reference corpus (development plus historical holdout) and must not be represented as the same fitted objects that generated the development/holdout metrics.

`runtime.py` provides guarded packaging interfaces: it accepts only the approved versioned packages from `deployment_baseline/model_packages/`, with a manifest, artifact hash, exact X10 schema, endpoint, preprocessing, threshold policy, approval status, and baseline provenance. It validates external input structure, scores only an already-approved X10 feature matrix, returns side-by-side predictions/disagreement for both models, and allocates unique output directories. It does not compute descriptors from SMILES.

## How to use the future tool

The intended future use is one approved external CSV per run. The workflow validates the CSV, prepares the exact approved X10 descriptors, loads both versioned packages from `deployment_baseline/model_packages/`, generates per-model predictions plus disagreement and applicability outputs, and optionally compares predictions with independently documented laboratory labels. The committed baseline results are read only for provenance and reference; they are not the future scoring model. Each run writes to a new private output subfolder. Real scoring remains gated until descriptor computation, threshold/calibration, applicability, privacy, and review approvals are complete.

## Practical run flow

The intended future flow is:

1. Obtain one approved, independently documented CSV handoff for the run.
2. Confirm data-use, privacy, and redistribution permissions before copying or processing it.
3. Validate the input schema, identifiers, labels, units, missingness, and structure fields.
4. Recompute the exact X10 descriptor definitions required by the packaged model, including any approved in-house descriptors.
5. Load both explicitly versioned packages from `deployment_baseline/model_packages/` and verify their manifests and hashes.
6. Generate random-forest and RBF-SVC predictions, scores, model-disagreement flags, applicability/domain flags, and provenance.
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

- No Costa Rican or other external laboratory dataset is included.
- The deployment packages are new 893-row fits, not the original evaluation objects; historical metrics are read-only context.
- The current repository does not provide a complete public package that recomputes every X10 descriptor, including the in-house descriptors.
- The historical BeeQ holdout was previously inspected and is not a substitute for a new independent validation set.
- External validation must preserve the model’s exact feature order, units, preprocessing, endpoint definition, and versioned provenance.
- Applicability flags are required because performance declines for compounds distant from the reference descriptor space.

## Run status and expected outputs

Do not run this as a validated analysis until approved inputs, complete descriptor generation, a compatible serialized model package, applicability thresholds, and review procedures exist. The notebook intentionally stops with clear placeholders where those dependencies are unavailable. It must not invent predictions, scores, confidence intervals, or trained-model results.

The proposed private output set for each unique run is: an input snapshot/reference and manifest hash; a validation report; per-model predictions and continuous scores; a model-disagreement report; an applicability report; descriptor/schema provenance; optional observed-label comparison metrics; and run metadata linking back to the read-only baseline bundle. Generated run outputs are ignored by `output/.gitignore`; the baseline results remain separate and are never overwritten.

## Files

- `input_template.csv`: safe schema example only.
- `external_validation_template.ipynb`: non-executed workflow guide with placeholder cells.
- `output/README.md`: privacy and review rules for future exports.
- `output/`: reserved for reviewed private results; the directory is kept with `.gitkeep` only.
- `runtime.py`: guarded package/provenance/input/run-boundary interfaces; no model artifact is included.
- `model_package.schema.json`: manifest contract for a future approved package.
- `../deployment_baseline/model_packages/random_forest/`: approved full-reference random-forest package.
- `../deployment_baseline/model_packages/rbf_svc/`: approved full-reference classical RBF-SVC package.

The package artifacts are deployment-oriented refits, not a rerun of the research comparison. The manifests identify the recorded selection recipe and preserve the original result-bundle hashes for audit context. The current thresholding and applicability/domain policies remain marked as not approved; scientific external validation therefore remains blocked until those policies, descriptor generation (including the in-house X10 descriptors), input approvals, and review procedures are complete.
