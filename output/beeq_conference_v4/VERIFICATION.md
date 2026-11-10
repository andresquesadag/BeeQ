# Source and verification record

Deck: `output/beeq_conference_v4/index.html` (17 slides plus two
supplementary, five blocks, English).
Last verified: 6 November 2026.

This record links every relevant figure and claim in the deck to its source, and
documents the discrepancies that could **not** be resolved from the available
files.

> **Shared provenance.** This deck is generated from the same build scripts as the
> Spanish deck in `output/beeq_conference_v2/`, so the two carry exactly the same
> verified numbers. Only the language and the decimal mark differ. The Spanish
> record is `output/beeq_conference_v2/VERIFICACION.md`.

> **The MLP.** By the author's decision, the whole talk uses the **balanced,
> retuned MLP (variant B)** consistently, on slides 10, 11 and 12. Consequences
> are in section D-1.

> **Figure captions.** On-screen captions are abbreviated to the exact table (for
> example "SI Table S18"). Full traceability for each figure stays in this
> document, which is the reference record. No figure changed.

> **What V4 adds to this record.**
> · Slide 13 now carries the **density of the 712 Development molecules** behind
>   the applicability domain. It comes from
>   `manuscript/final_revision/tables/development_ad.csv`, which gives Smax and
>   d5 per molecule and **reproduces exactly** the 650 dual-IN count of SI Table
>   S25. The window is 0.10–1.00 x 0.4–3.6 and leaves 6 of the 712 outside.
> · Supplementary S1 shows K_Q against K_RBF for all 253,116 unique Development
>   pairs. The three Gram matrices were **recomputed from the frozen inputs** by
>   `build/gram_geometry.py`, following SI Eqs. S8, S12 and S15 with the frozen
>   scales (Product s = 0.25, IQP-ZZ s = 0.125 with lambda = 1, matched RBF
>   gamma = 0.03). The reconstruction reproduces all nine quantities of SI Table
>   S22 to within 4.6e-7, and the log-log slopes to within 1e-6 of SI Table S23.
>   See discrepancy D-5 on the slope labels.
> · Slide 7 replaces the fold bar chart with a protocol diagram. The per-fold
>   counts are unchanged and remain in SI Table S9 and in this record.
> · Slide 3 is institutional: two photographs, no figures.
> · Supplementary S2 reproduces SI Table S3.
> No figure changed with respect to V3.

## 1. Source hierarchy adopted

| Priority | Source | Used for |
|---|---|---|
| 1 | Frozen campaign `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z` and the SI tables that read it | Metrics for LR, RF, RBF, Product QK and IQP-ZZ QK; geometry; applicability domain |
| 2 | `results/mlp_sensitivity/full_20261009_v2/` | **All** MLP figures (balanced variant B) |
| 3 | `docs/mlp_sensitivity/audit_20261105/` | Independent audit that re-scores the saved models and confirms 1 and 2 |
| 4 | `manuscript/final_revision/tables/development_ad.csv` | Development density behind slide 13 |
| 5 | Frozen CSVs in `data/official/` (SHA-256 verified in SI Table S32) | Per-molecule values: SMILES, X10, labels |
| 5 | Main paper | Narrative and definitions; not used as a numerical source where it contradicts 1–3 |

Abbreviations: `[TI]` paper Table I (= SI Table S15); `[Sn]` SI Table n; `[§]`
paper section; `[MLP-B]` `results/mlp_sensitivity/full_20261009_v2/`; `[AUD]`
`docs/mlp_sensitivity/audit_20261105/`.

## 2. Traceability by slide

### S3 · Context
No figures. The framing — key pollinator, in vivo assay as the standard, NAM as
support for prioritisation — comes from `[§ I]` and references [6] and [14] of the
paper. The slide states explicitly that BeeQ is exploratory and not a regulatory
decision criterion.

### S4 · Research question and pipeline
The headline is the paper's question verbatim (`[§ I]`, final paragraph of the
introduction). The pipeline reflects `[§ II.C–II.E]`: ApisTox → curation and
per-partition scaling → cluster-disjoint folds → two tracks (classical models
LR/RF/MLP, and the three kernels with a precomputed-kernel SVC) → common metrics.
Marked on screen as a conceptual schematic. The note that "matched RBF" does not
imply matching the bandwidth comes from `[§ II.D]`.

### S5 · Dataset and endpoint
| Figure | Value | Source |
|---|---|---|
| BeeQ893 | 893 = 622 non-toxic + 271 toxic | `[S1]`, `[§ II.A]` |
| Development | 712 = 490 / 222 · 374 clusters | `[S1]` |
| Historical holdout | 181 = 132 / 49 · 88 clusters | `[S1]` |
| CR8 | 8 = 6 / 2, no cluster IDs | `[S1]` |
| Starting point | 1,035 ApisTox compounds | `[S1 A]`, `[§ II.A]` |
| Endpoint | LD₅₀ ≤ 11 µg/bee ⇒ class 1; fixed before modelling | `[§ II.A]`, `[S1 B]` |

Limits stated in the notes rather than on screen: the 142 exclusions have no
reconstructable per-operation ledger `[S1 A]`; the label aggregates the most
severe exposure route `[§ II.A]`.

### S6 · Partitions and freezing
| Claim | Source |
|---|---|
| Morgan radius 2, 1,024 bits, with chirality; Tanimoto | `[§ II.C]`, `[S3 A]` |
| Butina at cutoff 0.60 on d = 1 − T | `[§ II.C]`, `[S3 A]` |
| 462 clusters, 334 singletons, largest 40 | `[§ II.C]`, `[S3 A]` |
| Composition of the five folds and zero shared clusters | `[S9]` |
| 4 inner StratifiedGroupKFold splits, selection by mean inner AUROC | `[§ II.C]`, `[S3 B]` |
| Threshold: max MCC, ties by BA, then \|t\|, then t | `[§ II.D]`, `[S3 B]` Eq. S5 |
| Single refit on 712; manifest written before opening the external sets | `[S3 B]` |
| Holdout "historical" because of earlier exploratory inspection | `[§ II.C]`, `[S1 B]` |

### S7 · Molecule → X10 → qubit angle
Ethiprole's raw values are taken verbatim from
`data/official/ExternalFinal_RDKitFixed.csv`. Standardisation was computed over the
712 rows of `data/official/train_RDKitFixed.csv` using the `StandardScaler`
convention (population standard deviation, Eq. S3). Reproducible script:
`build/encoding_values.py`.

| qb | Descriptor | Raw | z | θ = 0.25·z |
|---|---|---|---|---|
| 1 | logP | 3.7793 | +0.44 | +0.109 |
| 2 | MW | 397.209 | +0.77 | +0.193 |
| 3 | TPSA | 90.69 | +0.37 | +0.092 |
| 4 | HBD | 1 | +0.12 | +0.031 |
| 5 | RotB | 3 | −0.52 | −0.130 |
| 6 | ArR | 2 | +0.78 | +0.195 |
| 7 | nHal | 5 | +1.94 | +0.486 |
| 8 | nOP | 0 | −0.36 | −0.090 |
| 9 | LiPHEX | −1.9154 | −1.62 | −0.406 |
| 10 | fSASA | 0.1900 | +0.27 | +0.067 |

Cross-check: the computed means and deviations match `[S4]` (e.g. logP
2.9626 / 1.8734 computed against 2.963 / 1.875 published; the difference is
population versus sample SD). Descriptor order and qubit assignment: `[S3]`.
Encoding scale s = 0.25: frozen selection in `[S14]`.

### S8–S9 · Kernels and quantum encoding
| Claim | Source |
|---|---|
| K_RBF(z,z′) = exp(−γ‖z−z′‖²) | `[S4 A]` Eq. S8 |
| SVC with precomputed kernel, balanced weights | `[§ II.D]`, `[S4 A]` |
| Fidelity K_Q = \|⟨ψ(z)\|ψ(z′)⟩\|² | `[S4 B]` Eq. S10 |
| Product: ten RY(s·z), no entanglement | `[S4 C]` Eq. S11 |
| IQP-ZZ: H + RZ + nearest-neighbour RZZ chain, λ = 1, one repetition, no final Hadamard | `[S4 D]` Eqs. S15–S16 |
| Selected scales: Product s = 0.25; IQP-ZZ s = 0.125 | `[S14]` |
| Exact statevector in NumPy, 1,024 amplitudes, no shots, noise or hardware | `[S4 E]` |
| Qiskit present in the environment but did not execute the campaign | `[S4 E]` |

### S10 · Performance on Development
Per-fold AUROC from `[S17]`; means and SDs from `[TI]` = `[S15]`; holdout crosses
from `[S18]`. **The MLP row comes from `[MLP-B]`** (`NESTED_SUMMARY.csv`,
`EXTERNAL_METRICS.csv`), confirmed by `[AUD]`.

| Model | Mean ± SD | Holdout |
|---|---|---|
| Random Forest | 0.7480 ± 0.0574 | 0.6926 |
| Logistic Regression | 0.7328 ± 0.1039 | 0.6848 |
| Product QK | 0.7216 ± 0.1075 | 0.6974 |
| IQP-ZZ QK | 0.7130 ± 0.1056 | 0.6962 |
| Matched RBF | 0.7106 ± 0.1084 | 0.7058 |
| **Balanced MLP (B)** | **0.6792 ± 0.0997** | **0.4821** |

Per-fold AUROC of the balanced MLP: 0.535825 · 0.645469 · 0.780835 · 0.667547 ·
0.766513 (`[AUD]`, "Figure 2 and main table" block).

The bar shown is a **standard deviation across folds**, captioned on screen as
"not a confidence interval", per `[§ III.A]` and `[S6 A]`.

### S11 · Historical holdout
Figures from `[S18]` for the five frozen families and from `[MLP-B]` for the MLP.

| Model | AUROC | Sens. | TP | FN | FP | Spec. |
|---|---|---|---|---|---|---|
| Random Forest | 0.6926 | 0.2653 | 13 | 36 | 4 | 0.9697 |
| Logistic Regression | 0.6848 | 0.1633 | 8 | 41 | 7 | 0.9470 |
| Product QK | 0.6974 | 0.0816 | 4 | 45 | 2 | 0.9848 |
| IQP-ZZ QK | 0.6962 | 0.0816 | 4 | 45 | 3 | 0.9773 |
| Matched RBF | 0.7058 | 0.1020 | 5 | 44 | 2 | 0.9848 |
| **Balanced MLP (B)** | **0.4821** | **0.2653** | **13** | **36** | **22** | **0.8333** |

Resulting ranges, used in the notes: sensitivity **0.082–0.265**, specificity
**0.833–0.985**, 36 to 45 false negatives out of 49. With this alignment all three
ranges **match exactly** those published in the abstract and in `[§ III.B]`.

### S12 · CR8 and the applicability domain
| Claim | Source |
|---|---|
| Dual domain and coordinates of the eight compounds | `[S26]` |
| Cutoffs S = 0.223134 (P05) and d = 2.198975 (P95), from Development only | `[S9 A]`, `[§ II.E]` |
| 7 of 8 inside both domains; Fluoxapiprolin IN/OUT | `[S26]` |
| Decisions of LR, RF, RBF, Product, IQP-ZZ | `[S27]` |
| **MLP decisions (balanced column)** | **`docs/mlp_sensitivity/CR8_COMPOUND_TABLE.csv`, confirmed by `[AUD]`** |
| Spearman ρ = −0.31 between the two axes | `[§ III.E]` |
| No overlap with BeeQ893/ApisTox (canonical SMILES + InChIKey) | `[§ II.E]`, `[S1 B]` |

Matrix shown: every model predicts class 0 on all eight compounds **except** the
balanced MLP, which predicts class 1 for Isocycloseram (correct), Fluoxapiprolin
(false positive) and Florylpicoxamid (false positive). Balanced MLP CR8 counts:
TP 1, TN 4, FP 2, FN 1.

### S13 · Local chemical support
| Claim | Source |
|---|---|
| Ethiprole's nearest structural neighbour: ID 387, fipronil, T = 0.7400, class 1 | `[S29]`, `[S30]` |
| Isocycloseram's maximum structural support: 0.2326 | `[S26]`, `[S30]` |
| Both have LD₅₀ well below 11 µg/bee | `[§ III.E]` and refs. [26], [27] |
| Ethiprole misclassified by all six models | `[S27]` + `[MLP-B]` (both MLP variants fail it) |

Both structures were drawn with RDKit 2026.03.5 from the frozen SMILES
(`build/render_molecules.py`); neither was copied from a published figure.

### S14 · Conclusions
The CKA values quoted in the notes (0.982 and 0.985 against the RBF; 0.9995
between the two quantum kernels) come from `[S22]`. The 0.082–0.265 sensitivity
range comes from the S11 table above.

### S15 · Future work
The three directions correspond to `[§ IV]` ("extending encoding-scale
optimization, training embedding parameters through kernel-target alignment, and
evaluating projected kernels"). The third — rearranging and widening the qubits —
is an extension proposed by the author for this talk; it rests on a documented
fact, that the IQP-ZZ RZZ chain couples only neighbouring qubits `[S4 D]`, and on
the descriptor order fixing the qubit assignment `[S3]`. It is presented as a line
of work, not a result.

The chart is the orientation-free univariate AUROC from `[S5]`, captioned on screen
as descriptive and stated not to have been a selection criterion, as the table
itself indicates.

## 3. Discrepancies

### D-1 · The paper mixes two MLP variants · **resolved; the talk adopts variant B**

The frozen campaign records a single MLP, **without class weighting**. The
re-analysis `[MLP-B]` adds two balanced variants. The paper's figures come from
both sources at once:

| Passage in the paper | Published value | Corresponds to |
|---|---|---|
| Table I, MLP row | 0.679 ± 0.100 · AUPRC 0.594 ± 0.112 · BA 0.632 · MCC 0.338 | **balanced B** (0.6792 ± 0.0997 · 0.5942 ± 0.1119 · 0.6322 · 0.3376) |
| Abstract and § III.B: "AUROCs … 0.462 (MLP)" | 0.462 | **original unweighted** (0.4624) |
| § III.B: "its AUPRC decreased to 0.329" | 0.329 | **balanced B** (0.3290) |
| § III.B: "identified 13 of the 49 … and produced 22 false positives" | 13 / 22 | **balanced B** |
| § III.B: "specificity between 0.833 and 0.985" | 0.833 | **balanced B** (0.8333) |

**Decision taken.** The deck uses the **balanced variant B** on every slide,
labelled "Balanced MLP". Under that convention, four of the five passages are
reproduced exactly; the only one that is not — the abstract's holdout AUROC of
0.462 — belongs to the original MLP, which this deck does not show.

**Still open in the manuscript.** The text continues to combine both variants
within one paragraph. The corrections are already drafted in
`docs/mlp_sensitivity/audit_20261105/CORRECTIONS_EN.md`, which proposes exactly
this convention: label the MLP row of Table I and Figure 2 as the balanced,
retuned variant, keep the original as a separate baseline, and replace the
abstract's range with "0.482 … to 0.706".

#### Independent corroboration

The audit `[AUD]` re-scored the saved models without refitting any
(`model_fits_performed: 0`, maximum re-scoring error ~1e-16) and verified 6
external metric rows, 15 outer-fold rows and 32 manifest files. Its recomputed
values match **exactly** those used here:

| | Audit | Used in the deck |
|---|---|---|
| Balanced MLP B · Development | 0.679238 ± 0.099729 | identical |
| Balanced MLP B · holdout | AUROC 0.482066 · AP 0.329039 · TP 13 · FP 22 · FN 36 | identical |
| Balanced MLP B · CR8 | TP 1 · TN 4 · FP 2 · FN 1 | identical |
| Original MLP · holdout (not shown) | AUROC 0.462430 · TP 4 · FP 4 · FN 45 | cited in this record only |

### D-2 · CR8: Isocycloseram · **resolved**

| | Frozen campaign `[S27]`, `[S28]` | Balanced variant B (shown) |
|---|---|---|
| Ethiprole | class 0 in all six models | class 0 (false negative) |
| Isocycloseram | class 0 in all six models | **class 1 (correct)** |
| MLP false positives | Florylpicoxamid only | Fluoxapiprolin **and** Florylpicoxamid |
| MLP counts | TP 0, FP 1, FN 2 | TP 1, FP 2, FN 1 |

With variant B, the paper's claim — "five misclassified Isocycloseram; MLP
correctly identified Isocycloseram", with false positives for Fluoxapiprolin and
Florylpicoxamid — is reproduced exactly. Slide 12 shows that matrix and its
caption labels it "balanced MLP".

### D-3 · Table II (six alternative representations) · **not verifiable, excluded**

Paper Table II compares X10 against WL-OA (0.805 ± 0.073), ECFP (0.787 ± 0.091),
RDKit2D (0.784 ± 0.064), Mordred (0.755 ± 0.103), atom counts (0.748 ± 0.068) and
MACCS (0.732 ± 0.104), claiming recomputation on BeeQ893 under the same nested
protocol. It could not be supported:

1. The Supporting Information does **not** contain that comparison. `[S10 A]`
   documents a **different** exploratory screen (X5, X7, FREE20, X10 minus HBD,
   X10 versus X9) and warns that those values "belong to exploratory
   pre-screening … and are not substituted for the frozen nested results".
2. `[S11]` states expressly that "matched predictive descriptor ablations … were
   not available for this evaluation".
3. Repository search: the values 0.805 / 0.787 / 0.784 appear in no file under
   `results/`, `docs/` or `manuscript/`.
4. `manuscript/final_revision/audit/PUBLISHED_APISTOX_CONTEXT.csv` holds the
   **published** ApisTox benchmark figures (WL-OA SVM MaxMin 0.8395; ECFP RF
   0.7166 MaxMin / 0.7816 temporal …), which do **not** match Table II.

**Decision.** Table II is not presented. The justification for X10 rests on the
documented argument (one descriptor, one qubit) and, on slide 15, on univariate
associations labelled as descriptive.

### D-5 · The slope labels in paper Figure 3B look swapped · **flagged**

SI Table S23 gives, for the unweighted fit log K_Q = a + p log K_RBF over all
253,116 pairs, slope 0.586551 for Product and 0.559648 for IQP-ZZ, with
origin-constrained values 0.562509 and 0.551553. The independent reconstruction
in `build/gram_geometry.py` returns exactly those four numbers.

Rounded, that is **p = 0.56 for Product and p = 0.55 for IQP-ZZ**. Figure 3B of
the paper labels the Product panel "p ~ 0.55" and the IQP-ZZ panel "p ~ 0.56",
i.e. the other way round. Supplementary S1 of this deck shows the values that
follow from Table S23 and from the recomputation.

**Action for the authors.** Check the panel labels in Figure 3B against Table
S23 before the final version. Nothing else depends on this.

### D-4 · Minor: SI Table S2 column alignment in text extraction
Extracting text from the SI PDF misaligns the CAS column. The frozen CSV gives
Isocycloseram CAS 2061933-85-3 and Ethiprole 181587-01-9. The deck shows no CAS
numbers, so no claim is affected.

## 4. Claims deliberately not made

The deck does **not** claim, on screen or in the notes: quantum advantage;
performance on real quantum hardware or under noise; clinical or regulatory
utility; mathematical equivalence between the three kernels; generalisation beyond
X10, these fixed maps and this protocol; that applicability-domain membership
guarantees a correct classification; nor that the fold-wise deviations are
confidence intervals. Slide 14 devotes a whole column to "what this work does not
show".

## 5. Limits the Supporting Information itself declares, and which the deck respects

- The holdout is **historical**: inspected during earlier exploratory stages
  `[S1 B]`. Stated in the notes for S6 and S11.
- CR8 has **eight compounds and two positives**: changing one decision moves
  sensitivity by 0.5 `[S9 B]`. Stated in the notes for S12.
- Cluster disjointness is **not** a formal out-of-distribution guarantee
  `[S3 A]`. Stated in the notes for S6.
- A high CKA does **not** imply identical entries, spectra or decisions `[S8]`.
- The upstream fSASA generation procedure is not reproducible from the retained
  artefacts `[S2 A]`. Nothing to the contrary is claimed on S7.
- The MLP's native early stopping uses a random, **non** cluster-grouped
  reservation, in both variants `[S4 A]`, `[MLP-B]`. Not mentioned on screen.
- The external evaluations of the balanced variants are **retrospective**: a
  freeze within that re-analysis does not undo prior observation of the original
  external results (`[AUD]`, proposed Methods II-D).
- The full-pipeline notebook dated 2026-08-31 differs from the frozen 2026-08-27
  campaign in the fourth decimal of some quantum results `[S1 C]`. The deck uses
  the frozen campaign exclusively.

## 6. Checks that could not be performed

- The paper's Figures 1 to 4 were not verified visually: the text extracted from
  the PDF preserves the labels but does not allow plotted positions to be
  compared. Every chart in the deck was built from the **tables**.
- No model was re-run. Metrics were read from the retained artefacts, as the
  Supporting Information and the audit `[AUD]` also do.
- The exported PDF was verified structurally (16 pages, one per slide, 16:9,
  background colours present on the four dark slides), but not inspected page by
  page visually.
