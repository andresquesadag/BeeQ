# BeeQ deployment baseline

This is a separate deployment-oriented phase built from the approved BeeQ
baseline evidence. It does not rewrite or replace the original experiment,
historical result bundles, configs, paper, or private handoff.

## Scope

The three versioned packages in `model_packages/` are the approved random-forest,
classical RBF-SVC, and exact-statevector IQP-ZZ kernel models. They are new deployment fits on the full 893-row
curated BeeQ reference corpus (development plus historical holdout), using the
recorded X10 recipe and selected parameters. They are not the fitted objects
that generated the original development or historical-holdout metrics.

Each package manifest records the exact X10 order and schema hash, preprocessing,
model settings, endpoint, source-data and baseline-result provenance hashes,
fit scope, artifact hash, and threshold/applicability policy status. The
historical results remain read-only context.

## How a future user will use it

1. Obtain approval for one private external CSV and keep it outside the
   repository. One CSV maps to one run and one unique private output folder.
2. Validate the CSV fields, IDs, structures, labels, units, and provenance.
3. Use the separately approved descriptor implementation to derive the exact
   ordered X10 matrix, including the in-house descriptors. Confirm finite
   values and the feature-schema hash.
4. Have `external_validation/runtime.py` load all three packages from this folder,
   after package, threshold, applicability, and dependency approvals are
   recorded.
5. Write private validation metadata, per-model predictions, model-disagreement
   flags, applicability results, and provenance to a new run folder.
6. If reviewed laboratory labels are present, compare them separately using
   only approved metrics and preserve exclusions and uncertainty information.

## External-validation boundary

`external_validation/runtime.py` loads only these packages through the
authoritative `deployment_baseline/model_packages/` path. It can validate an
already-approved X10 feature matrix and return side-by-side predictions and
three-model disagreement. It does not compute descriptors from SMILES and no
external or Costa Rican data is included.

External scientific validation remains gated on approved descriptor generation
(including the in-house X10 descriptors), threshold/calibration policy,
applicability/domain policy, input permissions, and laboratory-label review.
Do not interpret the deployment fits as the original evaluated estimators or
claim historical metrics as a direct evaluation of these refit objects.
