# BeeQ

Reproducible classical and simulated-quantum kernel experiments for acute
honey-bee toxicity screening with a compact molecular representation.

The working endpoint is binary acute toxicity for *Apis mellifera*:

- `LABEL = 1`: strongest available acute LD50 <= 11 microgram/bee.
- `LABEL = 0`: strongest available acute LD50 > 11 microgram/bee.

The initial study evaluates ten molecular descriptors (X10), controlled
ablations, structure-aware generalization, and matched RBF/quantum kernels.
Regional validation is intentionally outside the initial experimental scope.

## Research questions

1. Does X10 contain signal that distinguishes toxic from non-toxic molecules?
2. Does the explicit organophosphorus motif count (`n_OP`) add predictive signal?
3. Do `MolLogP` and `LiPHEX_prediction` provide complementary information?
4. Do matched RBF and quantum fidelity kernels induce different geometries and predictions?
5. Does predictive signal persist for structure-disjoint molecules?

## Five-phase workflow

1. **Foundation:** repository structure, dataset contract, hashes, manifests,
   frozen folds, tests, and paper templates.
2. **Classical baseline:** nested group-aware model selection inside the five
   frozen development folds, X10 ablations, and pooled out-of-fold metrics.
3. **Quantum comparison:** simulated fidelity kernels on exactly the same
   coordinates, molecules, folds, and model-selection budget.
4. **Results:** paired metrics, kernel diagnostics, figures, prediction-level
   disagreement, uncertainty, and an auditable result bundle.
5. **Paper:** 6-8 page double-blind IEEE manuscript for BIP 2026.

See [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) for acceptance
criteria and the boundary between development and historical evaluation.

## Setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Data handoff

The source CSV files are local handoff material and are never committed. By
default the commands expect:

```text
.donotmerge_aux/data/train.csv
.donotmerge_aux/data/test.csv
.donotmerge_aux/data/master.csv
```

Another directory can be supplied with `--data-dir` or the `BEEQ_DATA_DIR`
environment variable. The expected schema is documented in
[`data/README.md`](data/README.md).

## Run phase 1

Audit the handoff and create a non-sensitive, hash-addressed manifest:

```bash
python -m src.data --write-manifest data/processed/dataset_manifest.json
python -m unittest discover -s tests -v
```

## Run phase 2

The default experiment evaluates logistic regression, RBF-SVC and random
forest over the declared representations. Preprocessing and hyperparameter
selection are fitted without access to each outer fold.

```bash
python -m src.experiment --config configs/classical.json
```

For a faster smoke run:

```bash
python -m src.experiment --config configs/classical.json \
  --models logistic rbf_svc --representations x10 without_n_op
```

Every run writes a new directory under `results/runs/` containing its config,
input/split hashes, Git state, fold metrics, OOF predictions and output hashes.
Historical holdout evaluation is opt-in:

```bash
python -m src.experiment --config configs/classical.json --evaluate-holdout
```

It is always labeled `historical_holdout`, never `unseen_test`.

## Generate figures

```bash
python -m src.plots --run-dir results/runs/<run_id>
```

## Layout

| Path | Purpose |
| --- | --- |
| `configs/` | Versioned experiment declarations |
| `data/` | Dataset contract and generated non-sensitive manifests |
| `docs/` | Experimental protocol and decisions |
| `notebooks/` | Thin, executable views over the source modules |
| `src/` | Validated data, experiments, metrics, kernels, and plots |
| `tests/` | Data-contract, metric, and kernel invariants |
| `results/runs/` | Versioned run bundles used by the paper |
| `paper/` | IEEE LaTeX source and generated figures |

## Provenance and licenses

Code is MIT licensed. Dataset redistribution is not implied; consult
[`data/LICENSE`](data/LICENSE) and the source dataset terms before publishing
or redistributing data-derived artifacts.
