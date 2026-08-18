# Results

Each experiment creates an immutable-style directory under `results/runs/`.
The directory name combines an UTC timestamp with a short configuration hash.

Required classical run artifacts:

- `run_config.json`
- `manifest.json`
- `fold_metrics.csv`
- `oof_predictions.csv`
- `summary.csv`
- `best_params.json`

Quantum run directories additionally contain:

- `kernel_diagnostics.csv`
- matched RBF and exact-statevector predictions;
- per-fold kernel parameters and integrity hashes.

Historical holdout artifacts are generated only with `--evaluate-holdout` and
retain `evaluation_status=historical_holdout` in every table.

Figures generated from a run live inside its `figures/` subdirectory. Figures
selected for the manuscript may later be copied into `paper/fig/` together
with the originating run ID.

Integrated bundles live under `results/final/` and contain the combined metric
table, 2,000-replicate paired bootstrap comparisons, prediction disagreement,
kernel summaries, distance-stratified holdout errors, six figures, generated
LaTeX tables and a SHA-256 manifest. `results/final/latest.json` is the only
moving pointer; every referenced run directory remains explicit.
