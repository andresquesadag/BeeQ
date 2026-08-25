# Corrected BeeQ campaign

## Canonical command

Run the complete corrected campaign from the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.campaign
```

The optional `--source-data` and `--output-root` arguments change locations,
not the protocol. Do not use `--quick` for paper results.

## 70/20/10 split variant

Generate the deterministic split, then point the same campaign command at it:

```powershell
.\.venv\Scripts\python.exe -m src.split_70_20_10
.\.venv\Scripts\python.exe -m src.campaign `
  --source-data .donotmerge_aux/generated/master_70_20_10_seed42
```

The 893 corrected master rows are partitioned into 625 development rows
(69.99%), 179 holdout rows (20.04%), and 89 external rows (9.97%). The legacy
73-row external file is only a reservation reference. Seventy-one compounds
can be linked to the master by canonical SMILES or CAS, while two are absent.
Eighteen additional master rows are selected deterministically and stratified
by label to complete the external target.

Train and holdout are Butina-cluster disjoint. External and internal are ID,
exact-SMILES, and canonical-SMILES disjoint. They are not completely
Butina-cluster disjoint: enforcing all reference molecules and full cluster
isolation would require 234 external rows (26.2%), which conflicts with the
requested 10% external size.

## Fixed structure

Every invocation creates `results/campaigns/<timestamp>_<config-hash>/` with:

- `run_config.json`, `environment.json`, `git_state.json`, and `manifest.json`;
- `classical/`: nested structure-aware HPO, OOF, and historical holdout;
- `quantum/`: matched RBF and exact product/IQP-ZZ kernel comparisons;
- `external/`: eight-molecule challenge metrics and SMILES audit;
- `logs/`: captured command output;
- `data_snapshot/`: local corrected inputs, ignored by Git.

The top-level manifest hashes every generated artifact. Existing runs are
never overwritten. The timestamp is unique per execution; the configuration
hash allows equivalent protocols to be recognized.

The external challenge implementation lives in `src.external_challenge` and
is invoked by the campaign; it is not a separate exploratory workflow.

## Interpretation rules

- Model and hyperparameter selection use development data only.
- The historical holdout is labeled as previously inspected.
- External labels are not evidence for model or threshold selection.
- The eight-row external panel is exploratory due to its small sample size.
- Exact and RDKit-canonical SMILES overlap with the internal corpus must both
  be zero.
- Historical `results/runs/` and `results/final/` remain provenance only and
  are not combined with corrected campaign results.

## Validation

After a code change, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

For a completed campaign, verify that `manifest.json` has status `complete`
and that every recorded SHA-256 matches its file before using results.
