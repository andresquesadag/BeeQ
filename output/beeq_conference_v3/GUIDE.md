# BeeQ presentation guide (English)

English version of the BeeQ conference talk. The Spanish version lives in
`output/beeq_conference_v2/`. Both are generated from the same build scripts and
therefore carry exactly the same verified numbers.

This is a draft for the author's review: it is not published or sent to anyone.

## How to open it

Double-click `index.html` in any modern browser. The file is self-contained: it
loads no external fonts, scripts or images, so it works offline and from a USB
stick.

| Key | Action |
|---|---|
| `→` `space` `PgDn` | Next |
| `←` `PgUp` | Previous |
| `Home` / `End` | First / last |
| `N` | Presenter notes (with target and cumulative time) |
| `F` | Fullscreen |
| `P` | Print or save as PDF |
| `T` | Rehearsal timer (against the planned 13:10) |

The bottom bar has the same controls. The address carries the slide number
(`index.html#10`), so you can link to one slide or reload without losing your
place.

**To project:** press `F`. The slide scales by itself keeping 16:9; it is designed
at 1600 × 900 and adapts to any resolution.

## Files

| File | What it is |
|---|---|
| `index.html` | The deck. Self-contained, ~178 KB, 16 slides |
| `BeeQ_presentation.pdf` | PDF export, 16 pages in 16:9 |
| `PRESENTER_NOTES.md` | Script with timings, transitions and likely questions |
| `VERIFICATION.md` | Source, traceability and discrepancy record |
| `GUIDE.md` | This document |

The build scripts are shared with the Spanish deck and live in
`output/beeq_conference_v2/build/`.

## Structure: five blocks

Sixteen slides. The top bar shows which block you are in, each segment sized in
proportion to its number of slides. Slide 2 is an agenda announcing the blocks.
The footer always reads "BeeQ · IEEE BIP 2026" plus the slide number.

| # | Slide | Block |
|---|---|---|
| 1 | Title · the paper's original title | — |
| 2 | Agenda | — |
| 3 | The problem: exposure, measurement, prioritisation | **A · Context** |
| 4 | Research question and matched pipeline | **A · Context** |
| 5 | BeeQ893 and the endpoint | **B · Methodology** |
| 6 | Cluster partitions and freezing | **B · Methodology** |
| 7 | From molecule to X10 and the qubit angle | **B · Methodology** |
| 8 | What a kernel is | **C · Implementation** |
| 9 | Quantum encoding, fidelity and scope | **C · Implementation** |
| 10 | Performance across model families | **D · Results** |
| 11 | Ranking versus detection: the holdout | **D · Results** |
| 12 | CR8 and the applicability domain | **D · Results** |
| 13 | Ethiprole and its toxic neighbour | **D · Results** |
| 14 | Conclusions and limits, in two columns | **E · Conclusions** |
| 15 | Future work | **E · Conclusions** |
| 16 | Data, code and closing | **E · Conclusions** |

### Why the block split falls there

"Methodology" groups the data and how we prepared it: the dataset, the partitions
and the representation. "Implementation" groups what was actually built and run:
the kernel and the quantum encoding with its simulation scope. If you prefer the
quantum encoding to count as methodology, change `data-block="C"` to `"B"` on
slide 9 of `build/template_en.html`.

## Design decisions

**One slide, one idea.** Every headline is a claim, not a label. If the audience
reads only the headlines, they follow the argument.

**Varied compositions.** Typographic agenda (2), three-column grid (3),
full-width diagram (4), dominant chart with side commentary (5, 10, 11), two
stacked charts (6), data cards (7), balanced two columns (8, 12, 14, 15) and a
centred symmetric composition (13).

**Colour carries meaning, consistently.** Teal for the classical kernel (RBF),
indigo for Product QK, violet for IQP-ZZ, slate for the non-kernel models, red for
toxic/error/limit and amber for emphasis. The same colours identify the same
models in every chart, so legends need not be re-read.

**Typography.** Serif for headlines — it sets the academic register and separates
them from the data — and sans with tabular figures for everything numeric. System
fonts only: nothing to download, nothing to fail on the room's laptop.

**Sizes made for projection.** Headlines run 42–78 px on a 1600 × 900 canvas; text
the audience must read never drops below ~25 px, and chart labels were sized
accounting for the scale factor at which each chart is inlined into its column.

**Graphical honesty.** Three rules applied without exception:
1. Every data chart carries the exact table it comes from.
2. Every conceptual schematic is marked as such with a dashed rule, so it is never
   mistaken for a measurement.
3. Wherever means are shown, the individual folds and the dispersion are shown
   too, and the caption states that the bar is a standard deviation and not a
   confidence interval.

**Charts come from the data, not from the paper's figures.** Each one is generated
from the Supporting Information tables by a script. The two chemical structures
were drawn with RDKit from the frozen SMILES.

**Deliberately left out.** No animations or transitions: in a 15-minute talk they
cost time and break when projected. No decorative icons. The only illustration is
the bee on slide 3.

## Exporting to PDF

A PDF is already generated: `BeeQ_presentation.pdf`, 16 pages, one per slide, in
16:9 with background colours.

To regenerate it from the browser: press `P`, choose "Save as PDF", no margins and
**with** background graphics enabled (otherwise the four dark slides come out
blank). The PDF contains the slides, not the notes: the script is in
`PRESENTER_NOTES.md`.

## Regenerating the deck

The verified data lives in the scripts, not hand-typed into the HTML, so any
correction propagates to the charts reproducibly. Run from the repository root:

```bash
python output/beeq_conference_v2/build/render_molecules.py
```

```bash
python output/beeq_conference_v2/build/make_charts.py --lang=en
```

```bash
python output/beeq_conference_v2/build/assemble.py --lang=en
```

- `render_molecules.py` draws Ethiprole and fipronil with RDKit from the SMILES in
  `data/official/`. It needs the project interpreter (`.venv/Scripts/python.exe`).
  The drawings carry no text, so both languages share them.
- `make_charts.py --lang=en` writes the translated charts into `generated_en/`.
  The `TR` translation table at the top of the file is the single place to change
  a chart label; it also switches the decimal mark from comma to point.
- `assemble.py --lang=en` inlines everything into this folder's `index.html`.

To change wording or layout, edit `build/template_en.html` and re-run
`assemble.py --lang=en`. The Spanish and English templates are edited separately:
they share CSS and JavaScript, but their prose is independent, so a change to one
does not propagate to the other.

## Open items for the author

1. **Table II.** It could not be supported from the retained artefacts and so does
   not appear. If the campaign that produced it is located, a slide can be added
   to block B. Detail in `VERIFICATION.md`, discrepancy D-3.
2. **Manuscript consistency.** The deck uses the balanced MLP variant B
   throughout; the manuscript still mixes the two variants within one paragraph.
   The proposed corrections are already drafted in
   `docs/mlp_sensitivity/audit_20261105/CORRECTIONS_EN.md`.
3. **Authors and affiliations** on the title slide: please confirm them and fix the
   final ordering.
4. **Block split** between Methodology and Implementation: see the note above if
   you prefer the quantum encoding in block B.
5. **Keeping the two decks in step.** A wording change made in one template must be
   repeated in the other. The charts stay in step automatically.
