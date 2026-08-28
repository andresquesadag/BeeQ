# BeeQ

Auditable classical and exact-statevector quantum-kernel experiments for acute
honey-bee toxicity screening with the frozen X10 molecular representation.

This branch is intentionally narrow. It contains the official corrected data,
the code required to reproduce the recorded campaigns, tests, and immutable
campaign artifacts. Paper drafts, notebooks, deployment prototypes, and loose
exploratory runs are maintained elsewhere.

## Endpoint and representation

- `LABEL = 1`: acute LD50 <= 11 microgram a.i./bee.
- `LABEL = 0`: acute LD50 > 11 microgram a.i./bee.
- Features: the ten ordered descriptors declared in `src/config.py`.
- Structure control: frozen `STRICT_CV_FOLD` values grouped by
  `BUTINA_CLUSTER_ID`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `data/official/` | Four corrected, frozen CSV inputs used by the final campaign |
| `data/reference/` | Legacy external reservation list required for the 70/20/10 split |
| `configs/` | Classical and quantum settings used by the corrected campaign runner |
| `src/` | Data validation, split generation, model implementations, kernels, and campaign runners |
| `tests/` | Data, split, metric, kernel, campaign, and artifact invariants |
| `results/campaigns/` | All completed campaign bundles and their SHA-256 manifests |
| `docs/` | Protocol, audit boundaries, and reproducibility notes |

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

## Reproduce the corrected 70/20/10 campaign

```powershell
.\.venv\Scripts\python.exe -m src.split_70_20_10
.\.venv\Scripts\python.exe -m src.campaign `
  --source-data data/generated/master_70_20_10_seed42
```

The generated split is ignored because it is deterministic. Its source data,
split implementation, recorded audit, and completed campaign are versioned.

## Run a new final nested campaign

```powershell
.\.venv\Scripts\python.exe -m src.final_nested_campaign
```

The runner verifies official hashes, audits folds and clusters, performs nested
selection on development only, creates a verifiable freeze, and only then
evaluates the historical holdout and CR8. It also writes applicability-domain,
cluster-bootstrap, Y-randomization, figures, and SHA-256 artifacts.

Each invocation creates a new timestamped directory under
`results/campaigns/`; completed campaigns are never overwritten.

## Source-of-truth rules

- Official CSVs and `data/SHA256SUMS.csv` define input identity.
- Code and frozen settings define execution.
- Completed campaign directories are immutable.
- The historical holdout is not pristine or unseen.
- CR8 is an eight-molecule challenge, not a large validation cohort.
- Exact simulated kernels do not establish hardware quantum advantage.

See [docs/AUDITABILITY.md](docs/AUDITABILITY.md) for retained dependencies and
known historical limitations.

## Licensing

Code is MIT licensed. Dataset and descriptor redistribution rights are separate;
review `data/LICENSE` before making a public mirror or release.
