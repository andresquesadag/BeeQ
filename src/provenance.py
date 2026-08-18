"""Shared run provenance helpers."""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .config import PROJECT_ROOT
from .data import sha256_file


def git_state() -> dict[str, Any]:
    """Capture the source commit and dirty state before a run creates outputs."""

    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    commit = run("rev-parse", "HEAD") or None
    status = run("status", "--porcelain")
    return {"commit": commit, "dirty": bool(status), "status": status.splitlines()}


def environment() -> dict[str, Any]:
    packages = {}
    for name in [
        "numpy",
        "pandas",
        "scikit-learn",
        "scipy",
        "matplotlib",
        "qiskit",
        "rdkit",
        "nbformat",
        "nbclient",
    ]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def file_hashes(paths: Iterable[Path]) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in paths}
