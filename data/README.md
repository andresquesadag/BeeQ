# Data contract

BeeQ consumes a curated X10 handoff without committing molecule-level source
data. The default local source is `.donotmerge_aux/data/`.

## Required files

- `train.csv`: development molecules with frozen `STRICT_CV_FOLD` values 1-5.
- `test.csv`: structure-disjoint historical holdout.
- `master.csv`: exact union of development and holdout rows.

## Identity, target and split columns

`ID`, `name`, `CID`, `CAS`, `SMILES`, `LABEL`, `SET`,
`BUTINA_CLUSTER_ID`, `STRICT_CV_FOLD`.

`STRICT_CV_FOLD` must be defined for development rows and empty for holdout
rows. Molecule IDs, SMILES and Butina clusters must not overlap between
development and holdout.

## X10 feature schema

1. `MolLogP`
2. `MolWt`
3. `TPSA_SP`
4. `NumHDonors`
5. `NumRotatableBonds`
6. `NumAromaticRings`
7. `nHalogen`
8. `n_OP`
9. `LiPHEX_prediction`
10. `sasa002_frac_polar_hetero_only`

All feature values must be finite. The feature order is part of the
experimental contract and is included in every run hash.

## Generated artifacts

`data/processed/dataset_manifest.json` contains only schema, counts and
cryptographic hashes. It is safe to version provided the handoff terms permit
publishing aggregate counts.
