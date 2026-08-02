# QB3P2

Quantum kernel methods for blood-brain barrier permeability prediction.
Code for the paper _Q-B3P2_ (in preparation).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduce everything

Run from the repository root, in this order:

```bash
python -m src.data          # data/raw/bbb.csv  ->  data/processed/descriptors.csv
python -m src.experiment    #                   ->  results/folds.csv, results/seeds.csv
python -m src.plots         #                   ->  paper/fig/ba_by_model.png
```

Each module also runs on its own as a check:

```bash
python -m src.feature_maps  # prints the four circuits
python -m src.kernels       # verifies the kernels are symmetric, unit-diagonal, PSD
pytest                      # the same checks as assertions
```

## Layout

| Path              | What it is                                               |
| ----------------- | -------------------------------------------------------- |
| `data/raw/`       | Input data, never edited                                 |
| `data/processed/` | Descriptors + fixed train/test split, generated          |
| `src/config.py`   | Seeds, qubit mapping, interaction graphs - all constants |
| `src/`            | The pipeline, one step per module                        |
| `results/`        | CSV outputs, committed so the paper's numbers are in git |
| `paper/`          | LaTeX source; `paper/fig/` is written by `src/plots.py`  |

## Notes

The fidelity kernel is computed from statevectors, not by executing circuits:
with 4 qubits each molecule is a 16-element vector and the whole Gram matrix is
one matrix product. Shot noise is added by binomial sampling of the exact
probabilities. No quantum hardware or simulator backend is required.

## License

Code: MIT (see `LICENSE`).
Data, derived tables and figures: CC BY 4.0 (see `data/LICENSE`).
