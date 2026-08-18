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

Historical holdout artifacts are generated only with `--evaluate-holdout` and
retain `evaluation_status=historical_holdout` in every table.

Figures generated from a run live inside its `figures/` subdirectory. Figures
selected for the manuscript may later be copied into `paper/fig/` together
with the originating run ID.
