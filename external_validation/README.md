# Future external validation

This folder is a future-work scaffold for evaluating a packaged BeeQ baseline on one independently collected external CSV per future run, such as a Costa Rican laboratory dataset. It does not contain external observations, trained-model packaging, descriptor-generation code, or validation results. It is not a replacement for the existing research pipeline and does not claim that external validation has occurred.

The current committed baseline bundle is a read-only reference for provenance and context at `results/final/20260818T070959Z_f1f76c91f3/`, including `all_metrics.csv`. That bundle contains saved research results, not a serialized scoring model, and must not be treated as an executable predictor.

## Future tool overview

The intended future use is one approved external CSV containing a list of molecules per run. The workflow will validate the CSV schema and structures, prepare the exact approved X10 descriptors, load a compatible versioned model package, generate predictions with applicability/domain flags, and optionally compare predictions with independently documented laboratory labels. The committed baseline results are read only for provenance and reference; they are not the future scoring model. Each run will write to a new private output subfolder so external results remain separate from the baseline bundle and from prior runs. Scoring is not operational until approved descriptor computation, compatible model packaging, applicability rules, and review procedures exist.

## Scope

The intended future flow is:

1. Obtain one approved, independently documented CSV handoff for the run.
2. Confirm data-use, privacy, and redistribution permissions before copying or processing it.
3. Validate the input schema, identifiers, labels, units, missingness, and structure fields.
4. Recompute the exact X10 descriptor definitions required by the packaged model, including any approved in-house descriptors.
5. Load an explicitly versioned model package compatible with the descriptor schema.
6. Generate predictions together with applicability/domain flags and provenance.
7. Compare predictions with observed laboratory labels only after label definitions and provenance are reviewed.
8. Write new external-validation outputs to a unique private subfolder under `external_validation/output/`; never overwrite the baseline bundle or a prior external run.

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
- The current repository does not provide a public package that recomputes every X10 descriptor or loads a production-ready model.
- The historical BeeQ holdout was previously inspected and is not a substitute for a new independent validation set.
- External validation must preserve the model’s exact feature order, units, preprocessing, endpoint definition, and versioned provenance.
- Applicability flags are required because performance declines for compounds distant from the reference descriptor space.

## Run status

Do not run this as a validated analysis until approved inputs, complete descriptor generation, a compatible serialized model package, applicability thresholds, and review procedures exist. The notebook intentionally stops with clear placeholders where those dependencies are unavailable. It must not invent predictions, scores, confidence intervals, or trained-model results.

The proposed private output set for each unique run is: an input snapshot and manifest hash; a validation report; per-molecule predictions; an applicability report; optional observed-label comparison metrics; and run metadata linking back to the read-only baseline bundle. Generated run outputs are ignored by `output/.gitignore`; the baseline results remain separate and are never overwritten.

## Files

- `input_template.csv`: safe schema example only.
- `external_validation_template.ipynb`: non-executed workflow guide with placeholder cells.
- `output/README.md`: privacy and review rules for future exports.
- `output/`: reserved for reviewed private results; the directory is kept with `.gitkeep` only.
