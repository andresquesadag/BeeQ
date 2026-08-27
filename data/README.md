# Versioned BeeQ data

This directory makes the retained campaigns independent of the former local
the original local handoff.

## `official/`

| File | Role |
| --- | --- |
| `master_RDKitFixed.csv` | Corrected 893-row master |
| `train_RDKitFixed.csv` | Frozen 712-row development partition |
| `test_RDKitFixed.csv` | 181-row historical, previously inspected holdout |
| `ExternalFinal_RDKitFixed.csv` | Eight-molecule CR8 challenge |

## `reference/`

`Externalset.csv` is the 73-row reservation list used only to reconstruct the
recorded 70/20/10 split. Matched rows take corrected values from the official
master; stored reference descriptors are not used as model inputs.

## `generated/`

Ignored deterministic output from `python -m src.split_70_20_10`.

## Frozen X10 order

`MolLogP`, `MolWt`, `TPSA_SP`, `NumHDonors`, `NumRotatableBonds`,
`NumAromaticRings`, `nHalogen`, `n_OP`, `LiPHEX_prediction`, and
`sasa002_frac_polar_hetero_only`.

Every committed input is listed in `SHA256SUMS.csv`. Do not replace a CSV in
place; add a new version and record its provenance instead.
