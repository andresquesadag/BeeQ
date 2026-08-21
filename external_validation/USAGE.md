# Future external-validation tool: usage guide

## Purpose and current status

This folder is a future workflow scaffold for assessing the BeeQ acute honey-bee toxicity baseline on one approved external CSV per future run, such as a later Costa Rican laboratory collection. It is documentation and input structure, not a deployed prediction service and not a completed validation analysis.

The current committed baseline result bundle is the read-only reference at `results/final/20260818T070959Z_f1f76c91f3/`; its `all_metrics.csv` is available for provenance and context. It is a saved research-result bundle, not a serialized scoring model, and cannot be invoked as the future predictor.

There is currently no compatible serialized predictor, no complete public descriptor-generation path for every required X10 feature, and no external laboratory dataset in this folder. The notebook contains safe scoring placeholders that stop clearly where those dependencies are missing. Placeholder cells must not be treated as operational scoring, predictions, validation results, or evidence of model performance.

## Prerequisite files and software

Before a real run is considered, the team must have all of the following:

- An approved, access-controlled external CSV and written permission to process it.
- A versioned model package that explicitly identifies its training data, endpoint, preprocessing, feature order, threshold/calibration policy, and approval status.
- An approved implementation for every required X10 descriptor, including the in-house descriptors that are not publicly recomputable from the current repository.
- A compatible Python/Jupyter environment and any reviewed dependencies required by the model and descriptor package.
- A documented applicability/domain policy and a review owner for exceptions.
- An agreed observed-label definition and laboratory provenance if evaluation, rather than prediction-only scoring, is intended.

Do not install or select dependencies, models, descriptor implementations, or thresholds ad hoc during a validation run. Record approved versions before processing private data.

## Folder layout

| Path | Purpose | Current state |
|---|---|---|
| `README.md` | Scope, limitations, privacy, and run gate | Available |
| `USAGE.md` | This team-facing guide | Available |
| `input_template.csv` | Header/example schema only; one row is explicitly fictional | Available |
| `external_validation_template.ipynb` | Non-executed workflow guide with stopping placeholders | Available |
| `output/` | Private root for separate external-validation runs | Empty except for placeholders; generated runs ignored |
| `output/README.md` | Output privacy and review rules | Available |
| `output/.gitignore` | Keeps generated run folders private while retaining documentation/placeholders | Available |

The repository must not become the storage location for real external records, molecule-level predictions, laboratory identifiers, or confidential derived tables. Use one input CSV per run and a new unique output subfolder for every run.

### Run path design

The future notebook should define these project-root-relative paths without mixing baseline and external outputs:

- `baseline_results_dir = results/final/20260818T070959Z_f1f76c91f3/` for read-only provenance/reference checks.
- `output_root = external_validation/output/` for private external-validation outputs.
- `run_output_dir = external_validation/output/<unique-run-id>/` for one run tied to one input CSV.

The baseline directory must never be written to, and `all_metrics.csv` must not be interpreted as a model file. A unique run folder prevents a future external result from overwriting either the baseline bundle or another external run.

## Preparing a full-list input CSV

Prepare one row for every external compound in the approved evaluation list. Keep the list complete for the declared scope; do not silently remove difficult compounds, duplicates, missing labels, or out-of-domain structures. Handle exclusions through a documented review record and retain the original approved input privately.

Use the exact header order shown below. Save the file as UTF-8 CSV and preserve the original file privately so its hash and row count can be recorded. The example in `input_template.csv` is fictional and must be replaced; it is not a real compound.

Observed fields may be empty for a prediction-only input. A comparison with laboratory observations requires a reviewed label definition, valid units, and documented provenance.

## Input fields

| Field | Required for prediction? | Required for evaluation? | Meaning and validation guidance |
|---|---|---|---|
| `sample_id` | Yes | Yes | Stable unique identifier assigned by the data owner. Do not use a personally identifying or confidential identifier unless approved. |
| `compound_name` | Recommended | Recommended | Human-readable name or approved local alias. Avoid embedding confidential information. |
| `smiles` | Yes | Yes | Structure string used to validate and derive descriptors. It must be parseable by the approved descriptor implementation; do not assume the fictional example is scientific input. |
| `observed_label` | No for prediction-only | Yes | Approved binary outcome. In the BeeQ reference convention, 1 means strongest available acute LD50 <= 11 microgram/bee and 0 means above that threshold. Confirm the external study uses the same endpoint before comparison. |
| `observed_ld50_ug_per_bee` | No | Recommended when available | Observed acute LD50 in microgram/bee, with units and censoring/limit-of-detection rules documented. It is not a model output. |
| `data_source` | Yes | Yes | Dataset, laboratory, study, or approved provenance reference. Use a non-sensitive reference that the review team can resolve privately. |
| `notes` | No | No | Non-sensitive context, exclusions, censoring notes, or review references. Do not place raw confidential material here. |

Do not add pesticide-use metadata or other shortcut variables to the model feature matrix unless a separately approved model explicitly requires them. The current BeeQ X10 contract contains ten molecular descriptors, not these input metadata fields.

## Future notebook workflow

The intended sequence in `external_validation_template.ipynb` is:

1. **Select one approved private input.** Point the future workflow to one access-controlled full-list CSV and record its source, approval, file hash, and row count outside the repository. Do not combine multiple future input files implicitly.
2. **Validate the file.** Check required headers, unique and non-empty `sample_id` values, structure presence, allowed label values, numeric LD50 units where supplied, missingness, and source provenance.
3. **Validate structures.** Parse `smiles` with the approved implementation and record parse failures or normalization decisions without silently discarding rows.
4. **Prepare X10.** Generate the exact ordered X10 descriptors with approved versions and units. Confirm finite values, feature order, descriptor hash, and compatibility with the model package.
5. **Read baseline provenance.** Check `baseline_results_dir` and, if approved, read saved metadata/results such as `all_metrics.csv` for reference only. Do not load it as a predictor or write into it.
6. **Load the future model package.** Confirm a compatible serialized model package, model version, endpoint, preprocessing, threshold/calibration policy, and approval status before generating any score. Actual prediction cannot run without this package and complete descriptor computation.
7. **Generate predictions and applicability flags.** Produce predictions only for accepted rows, retain row-level status for rejected/flagged rows, and attach model, input, descriptor, and policy provenance under a new unique `run_output_dir`.
8. **Compare with observations when approved.** Join predictions to reviewed labels by stable sample ID, report eligible counts and exclusions, and calculate only metrics approved for the study. Save optional comparison metrics separately from the baseline results. Do not treat a prediction-only input as validation evidence.
9. **Review and export privately.** Store molecule-level outputs and audit records in the unique run folder or another access-controlled location. Share only reviewed aggregates, if permitted.

The current notebook intentionally raises clear placeholder exceptions at input selection, schema validation, descriptor generation, model loading, prediction/applicability, and observed-label comparison. Those stops are expected until the required approved components exist. In particular, no prediction can run until a compatible serialized model package and complete descriptor computation are approved.

## Input validation and exception handling

Treat any of the following as a blocking data-quality or review exception: missing required columns; duplicate or blank sample IDs; missing/unparseable structures; invalid binary labels; inconsistent LD50 units; undocumented censoring; non-finite descriptors; feature-order or model-version mismatch; missing provenance; unauthorized data location; or an applicability policy that has not been approved.

Do not repair records silently, substitute descriptors, impute labels without approval, infer labels from names, or continue after a model/schema mismatch. Produce a private exception log containing the sample ID or approved internal reference, failure category, action owner, and disposition. Keep raw error details out of shared or tracked files.

## Expected private outputs

A future reviewed run may produce, outside public version control, in a new unique subfolder under `external_validation/output/`:

- An input snapshot or approved private reference plus a manifest with approval reference, row count, file hash, and data version.
- A validation report listing accepted, rejected, and missing rows.
- An applicability report listing domain-distance/applicability flags and the policy used to assign them.
- Descriptor-generation provenance and feature/schema hashes.
- A model/version manifest with preprocessing and threshold policy.
- Per-molecule predictions, kept private.
- An optional observed-label comparison metrics report with eligible counts, label prevalence, exclusions, uncertainty, and approved metrics.
- Run metadata linking back to the read-only baseline bundle, plus a concise review record stating who approved the run, when it ran, and what may be shared.

Run metadata should link back to `baseline_results_dir` and the exact baseline bundle/version used as reference, without modifying or replacing that bundle.

The `output/` directory is reserved for this purpose but currently contains no results. Its `.gitignore` keeps generated run outputs private while retaining `.gitkeep` and `README.md`. Do not commit real outputs there unless the project’s privacy and review policy explicitly changes.

## Observed laboratory labels and comparison

Observed labels enable an external performance comparison only when the laboratory endpoint is independently documented and compatible with the model target. The BeeQ reference target is binary acute toxicity based on the strongest available acute LD50 threshold of 11 microgram/bee. Confirm species, exposure route, endpoint definition, units, censoring, aggregation, and label timing before joining observations to predictions.

Keep prediction-only scoring separate from labeled evaluation. For a labeled comparison, use stable approved sample IDs, preserve unmatched and excluded rows in the private audit, and distinguish ranking metrics from threshold metrics. Do not describe an inspected historical holdout from the original project as a new external validation set.

## Privacy, versioning, and audit guidance

- Keep real CSVs, raw structures, laboratory identifiers, predictions, and derived molecule-level tables in approved access-controlled storage.
- Record hashes and versions for the input, descriptor package, model package, preprocessing, policy documents, and read-only baseline reference without publishing sensitive values.
- Preserve the original approved input and an immutable run record; do not overwrite a prior evaluation.
- Keep a private change log for exclusions, repairs, normalization, label adjudication, and applicability decisions.
- Share only reviewed aggregates and respect the source dataset, laboratory, institutional, and in-house descriptor terms.
- Treat this scaffold and the current BeeQ historical holdout as documentation aids, not as proof that a future external run is valid.

## Readiness checklist

Do not run real scoring until every item is confirmed:

- [ ] External data-use and privacy approvals are documented.
- [ ] Exactly one full-list CSV is selected for the run, stored privately, and recorded with source, version, hash, and row count.
- [ ] Required fields, IDs, structures, units, labels, missingness, and provenance have been reviewed.
- [ ] The exact X10 descriptor implementation and feature order are approved and available.
- [ ] A compatible serialized model package, preprocessing, endpoint, threshold/calibration policy, and versions are approved.
- [ ] Complete descriptor computation, including required in-house descriptors, is approved and available.
- [ ] The read-only baseline path is verified and the new unique output folder is selected; neither overlaps the other.
- [ ] Applicability/domain thresholds and exception handling are approved.
- [ ] A comparison plan defines eligible labels, metrics, uncertainty, and exclusions.
- [ ] Output access, retention, sharing, and scientific review owners are assigned.
- [ ] The fictional example row has not been mistaken for scientific data.

Until this checklist is complete, the notebook remains a non-operational template and no score or validation claim should be produced.
