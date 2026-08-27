# Final campaign reexecution equivalence

## Compared campaigns

- Baseline: `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260825T234128Z`
- Clean-path validation: `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z`

The validation campaign was executed from the versioned inputs in
`data/official/` after the repository cleanup. It completed all phases: nested
CV, development-only selection and freeze, historical holdout, CR8, paired
cluster bootstrap, 200 Y-randomizations, quantum QC, figures, and manifest.

## Result

Twenty-one deterministic result files were compared. Twenty files are
byte-for-byte identical, covering:

- input and split audits;
- nested fold metrics, OOF predictions, summaries, and selected parameters;
- final thresholds;
- holdout metrics and predictions;
- CR8 metrics, predictions, applicability-domain results, and neighbors;
- paired bootstrap and all Y-randomization outputs; and
- quantum-kernel and reference-implementation QC.

`FINAL_MODEL_SELECTIONS.json` is semantically identical except for the six
`artifact_sha256` values. Those hashes changed intentionally because the frozen
bundles now use importable classes from `src.model_artifacts` instead of classes
serialized as `__main__`. All six new artifacts were successfully loaded in a
separate Python process; their selected parameters, thresholds, and reported
metrics are unchanged.

Conclusion: relocating the canonical inputs did not alter any numerical result,
and the reexecution fixes model-artifact portability without changing model
behavior.
