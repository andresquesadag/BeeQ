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

## Run phase 3

The quantum phase uses exact NumPy statevectors, so Qiskit and hardware
credentials are not required. It executes product-state and IQP-ZZ fidelity
kernels plus a matched RBF control.

```bash
python -m src.quantum_experiment --config configs/quantum.json
```

## Run phase 4

Combine one complete classical run and one complete quantum run:

```bash
python -m src.analysis --config configs/analysis.json \
  --classical-run results/runs/<classical_run_id> \
  --quantum-run results/runs/<quantum_run_id>
```

This creates bootstrap intervals, paired comparisons, kernel diagnostics,
generalization strata, figures and LaTeX tables under `results/final/`.
`results/final/latest.json` records the exact bundle displayed by the notebook.

## Run phase 5

The executed master notebook contains all five phases and loads frozen results
when expensive cells are disabled:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/classic.ipynb
```

Compile the six-page double-blind manuscript from `paper/`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The reviewed submission artifact is `output/pdf/BeeQ_BIP2026.pdf`.

## External validation

The deployment phase contains full-reference Random Forest, RBF-SVC, and exact
IQP-ZZ packages. Run one approved private X10 handoff with:

```bash
python -m external_validation.run --input <external.csv> --data-dir <reference-data-dir>
```

The command verifies all three artifacts by deterministic refit, audits the
external descriptor contract and structural overlap, computes applicability,
and writes private predictions, 2,000-replicate bootstrap metrics, paired
AUROC comparisons, threshold sensitivity, and hashes to a unique ignored run
folder under `external_validation/output/`.

## Corrected complete campaign

The corrected Luis handoff can be evaluated end to end with one command:

```bash
python -m src.campaign
```

Run it from the repository root with the project virtual environment active.
On Windows, the fully explicit command is:

```powershell
.\.venv\Scripts\python.exe -m src.campaign
```

Each invocation creates a unique `results/campaigns/<timestamp>_<config-hash>/`
directory. It snapshots and hashes the corrected train, holdout, master, and
external tables; runs nested structure-aware HPO for logistic regression,
RBF-SVC, Random Forest, XGBoost, and the exploratory MLP; runs matched RBF,
product-state, and IQP-ZZ exact-statevector kernels; evaluates the historical
holdout and the eight-molecule external challenge; records exact and RDKit-
canonical SMILES overlap; and writes one top-level manifest containing hashes
for every output. Existing runs are never overwritten.

The external panel contains only eight independent molecules and is therefore
reported as an exploratory challenge, not as definitive evidence of model
generalization.

### Reproducible 70/20/10 variant

Create a second split from the corrected 893-row master while using the old
73-row external file only as a reservation list:

```powershell
.\.venv\Scripts\python.exe -m src.split_70_20_10
.\.venv\Scripts\python.exe -m src.campaign `
  --source-data .donotmerge_aux/generated/master_70_20_10_seed42
```

This produces 625 development rows, 179 holdout rows, and 89 external rows.
Seventy-one reference molecules are recovered from the corrected master; two
reference compounds absent from the master are documented but not fabricated.
The external descriptors and labels always come from the corrected master.

The campaign directory is the source of truth for corrected results. Older
`results/runs/` and `results/final/` bundles are retained only as historical
provenance and must not be mixed with corrected campaign metrics. Raw dataset
snapshots are ignored by Git; their hashes remain recorded in the campaign
configuration and manifest.

## Layout

| Path | Purpose |
| --- | --- |
| `configs/` | Versioned experiment declarations |
| `data/` | Dataset contract and generated non-sensitive manifests |
| `docs/` | Experimental protocol and decisions |
| `notebooks/` | Executed five-phase master notebook |
| `src/` | Validated data, experiments, metrics, kernels, and plots |
| `tests/` | Data-contract, metric, and kernel invariants |
| `results/runs/` | Versioned run bundles used by the paper |
| `results/campaigns/` | One-command corrected classical/quantum campaigns |
| `deployment_baseline/` | Versioned full-reference deployment models |
| `external_validation/` | Private three-model external-validation workflow |
| `paper/` | IEEE LaTeX source, generated tables, and figures |
| `output/pdf/` | Reviewed conference-paper PDF |

## Provenance and licenses

Code is MIT licensed. Dataset redistribution is not implied; consult
[`data/LICENSE`](data/LICENSE) and the source dataset terms before publishing
or redistributing data-derived artifacts.
