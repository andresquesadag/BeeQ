"""Generate traceable phase-4 figures from a completed run directory."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data import sha256_file, write_json


def plot_metric(summary: pd.DataFrame, metric: str, output: Path) -> Path:
    required = {"representation", "model", metric, f"fold_std_{metric}"}
    missing = sorted(required - set(summary.columns))
    if missing:
        raise ValueError(f"summary.csv lacks columns: {missing}")

    labels = summary["representation"] + " / " + summary["model"]
    values = summary[metric].to_numpy()
    errors = summary[f"fold_std_{metric}"].to_numpy()
    order = np.argsort(values)
    height = max(4.5, 0.35 * len(summary) + 1.5)
    fig, axis = plt.subplots(figsize=(9, height))
    axis.barh(
        np.arange(len(summary)),
        values[order],
        xerr=errors[order],
        color="#d6a62e",
        edgecolor="#463a18",
        alpha=0.9,
    )
    axis.set_yticks(np.arange(len(summary)), labels.iloc[order])
    axis.set_xlabel(f"Pooled OOF {metric.upper()} (error bars: fold SD)")
    axis.set_title("BeeQ classical structure-aware baseline")
    axis.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_dir = args.run_dir.resolve()
    summary = pd.read_csv(run_dir / "summary.csv")
    figure_dir = run_dir / "figures"
    outputs = []
    for metric in ["auroc", "mcc"]:
        output = plot_metric(summary, metric, figure_dir / f"classical_oof_{metric}.png")
        outputs.append(output)
        print(f"Wrote {output}")
    figure_manifest = {
        "source_summary_sha256": sha256_file(run_dir / "summary.csv"),
        "figures": {output.name: sha256_file(output) for output in outputs},
    }
    manifest_path = write_json(figure_dir / "figures_manifest.json", figure_manifest)
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
