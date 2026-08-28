# Auditability boundary

## Retained evidence

This branch retains every completed campaign, the official inputs required by
the latest protocols, the reservation list needed to rebuild the 70/20/10
split, executable source, dependency pins, and focused tests.

The three historical campaign directories remain byte-for-byte unchanged.
Their manifests therefore remain authoritative, including historical paths and
dirty-worktree status. A fourth campaign reexecutes the final protocol from the
new canonical paths and records portable model artifacts.

## Runtime dependency graph

The corrected campaign uses `src.split_70_20_10`, `src.campaign`,
`src.experiment`, `src.classical_models`, `src.quantum_experiment`,
`src.quantum_feature_maps`, `src.kernels`, `src.external_challenge`, and shared
`config`, `data`, `evaluation`, and `provenance` modules. It reads
`configs/classical.json` and `configs/quantum.json`.

The final nested campaign uses the same core implementations plus
`src.final_nested_campaign` and portable bundles from `src.model_artifacts`.

## Removed scope

- Paper LaTeX, generated paper tables/figures, mock PDF, and notebook.
- Deployment-package and private external-validation prototypes.
- Loose exploratory runs and paper-oriented integrated analysis.
- Source modules and tests used only by those removed workflows.

Git history remains the recovery mechanism for removed tracked files.

## Historical limitations preserved

- The final campaign was executed from a dirty worktree; its hashes remain.
- Its historical `.pkl` files were serialized under `__main__` and are not
  normally portable across processes. Recorded metrics used frozen in-memory
  objects and are unaffected. Future runs use `src.model_artifacts`.
- `src/evaluation.py` was used but omitted from that campaign's source-
  provenance JSON. The immutable campaign is not rewritten.
- Some configuration JSONs in the final campaign were provenance outputs, not
  files read back by the runner. Selected values were independently verified
  against the declared spaces.

## Merge validation

Run the complete test suite, regenerate the 70/20/10 split, execute the final
nested protocol, compare deterministic outputs to the recorded campaign,
verify every manifest/hash, and run `git diff --check`.
