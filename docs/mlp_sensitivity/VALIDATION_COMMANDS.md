# Executed commands and outcomes

All Python training commands used the repository `.venv` (Python 3.12.8),
not the global Python 3.14.5. Commands were run from `C:\Github_Repos\BeeQ`.

| Command | Outcome |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_mlp_sensitivity.py` | 4 passed; two feature-name warnings in the initial test invocation were removed by passing the same NumPy input format as production. |
| `python -m src.mlp_sensitivity --smoke --output-dir results/mlp_sensitivity/smoke_20261009` (with `.venv` Python throughout) | Failed source-byte verification due to CRLF checkout; preserved failure status. |
| Same smoke command with `smoke_20261009_v2` | Failed new audit's use of FOLD rather than the original OUTER_FOLD column; corrected before production. |
| Same smoke command with `smoke_20261009_v3` | Failed canonical input hashes due to CRLF checkout; LF bytes verified against and restored to the original SHA-256 values. |
| Same smoke command with `smoke_20261009_v4` | Complete; original fold 1 matched and both weighted fit branches executed. This pilot did not conduct HPO and is not scientific evidence for Analysis B. |
| `.\.venv\Scripts\python.exe -m src.mlp_sensitivity --output-dir results/mlp_sensitivity/full_20261009` | Complete: 693 fits, no training warnings, original reproduced before interpreting balancing, all variants frozen before new external input CSV evaluation. Non-applicable fixed-analysis selection statistics initially serialized as NaN. |
| `.\.venv\Scripts\python.exe -m src.mlp_sensitivity --output-dir results/mlp_sensitivity/full_20261009_v2 --compare-to results/mlp_sensitivity/full_20261009` | Definitive complete run: 693 fits, no training warnings, standard JSON null for non-applicable statistics. All 18 CSV outputs match the first complete run exactly. |
| `.\.venv\Scripts\python.exe -m src.mlp_sensitivity_report --run results/mlp_sensitivity/full_20261009_v2 --output-dir docs/mlp_sensitivity` | Passed independent checks of hashes, split/fit membership, weights, scalers, fixed-control equivalence, OOF coverage, threshold rules, metrics and repeated outputs. Repeated after editorial layout changes. |
| `.\.venv\Scripts\python.exe -m pytest -q` | Final suite: 19 passed, no warnings. Earlier manifest failures were confined to checkout line endings, subsequently restored to recorded byte identity and pinned by `.gitattributes`. |
| `.\.venv\Scripts\python.exe -m py_compile src/mlp_sensitivity.py src/mlp_sensitivity_report.py` | Passed. |
| `git diff --check` | Passed. Git notes that README line endings may be converted on checkout; no whitespace errors. |
| Native `compile_latex_document` on the saved supplement | Environment failure: `Unable to find standard directories for platform`; source kept open. |
| Existing `pdflatex` via structured subprocess arguments, two passes after the final source change | Success: five-page PDF, no overfull/underfull, undefined-reference or rerun diagnostics. Exact final transcript is `COMPILE_LOG.txt`. |
| `pdftoppm -r 120 -png output/pdf/MLP_BALANCING_SUPPLEMENT.pdf tmp/pdfs/mlp_sensitivity/page` | Rendered all five final pages; each inspected visually. All tables fit, complete panels stay together, headings and references are coherent. |
| Bundled Python with pdfplumber | Confirmed 17 table panels, eight compound names, primary Development metrics and three frozen thresholds in the final PDF text. |

## Recompile the supplied source

The native editor is the default source editor. Its compiler was unavailable in
this session. The existing TinyTeX fallback can be repeated with:

```powershell
New-Item -ItemType Directory -Force output/pdf | Out-Null
pdflatex "-interaction=nonstopmode" "-halt-on-error" "-output-directory=output/pdf" "docs/mlp_sensitivity/MLP_BALANCING_SUPPLEMENT.tex"
pdflatex "-interaction=nonstopmode" "-halt-on-error" "-output-directory=output/pdf" "docs/mlp_sensitivity/MLP_BALANCING_SUPPLEMENT.tex"
```

The actual invocation used Python `subprocess.run` with the same arguments and
absolute paths, avoiding PowerShell argument splitting. No TeX dependency was
installed. The main reviewed manuscript cannot be compiled without its current
source; this is separate from the successfully compiled new supplement.
