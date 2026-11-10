---
theme: default
title: "BeeQ | 8th IEEE International Conference on BioInspired Processing | BIP 2026"
titleTemplate: "%s"
info: "BeeQ, BIP 2026; UCR Guápiles, November 11, 2026; presented by Johnny Z. Agüero-Sandí"
author: "Luis A. Zumbado-Silva, Andrés Quesada-González, Johnny Z. Agüero-Sandí, Melissa Carvajal-Charpentier, Mauricio Gutiérrez-Arguedas, William J. Zamora-Ramírez"
aspectRatio: "16/9"
canvasWidth: 1280
colorSchema: light
presenter: true
transition: fade
layout: full
hideInToc: false
---
<div class="deck-slide cover-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>IEEE BIP 2026 · RESEARCH PRESENTATION</div>
<div class="cover-top"><div><div class="beeq-word">Bee<span>Q</span><i aria-label="pentagon" class="pent-point"></i></div><h1 class="paper-name">Evaluating Quantum Fidelity Kernels as a New Approach Methodology for Molecular Toxicity Prediction</h1></div><img alt="BeeQ bee mark" class="official-logo bee-cover" src="/art/beeq_bee.svg"/></div>
<div class="conference-full">8th IEEE International Conference on<br/><b>BioInspired Processing (BIP 2026)</b></div>
<div class="cover-venue"><span class="dot-amber"></span> November 11, 2026 <span class="cover-sep">·</span> University of Costa Rica, Guápiles</div>
<div class="author-line">Luis A. Zumbado-Silva · Andrés Quesada-González · <strong>Johnny Z. Agüero-Sandí</strong> · Melissa Carvajal-Charpentier · Mauricio Gutiérrez-Arguedas · William J. Zamora-Ramírez</div>
<div class="presenter-line">Presented by <strong>Johnny Z. Agüero-Sandí</strong></div>
</main>
<footer class="slide-footer"><span>BEEQ · CONFERENCE PRESENTATION</span><b>01 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>WHY THIS MATTERS</div>
<h1 class="slide-title">Why predict toxicity in honey bees?</h1>
<div class="intro-problem"><div class="intro-mark"><img alt="BeeQ bee icon" src="/art/beeq_bee.svg"/><strong><i>Apis mellifera</i></strong></div><div class="intro-points"><div><b>01</b><span>Some chemicals can be <strong>toxic to bees.</strong></span></div><div><b>02</b><span>Molecular models can help <strong>prioritize testing.</strong></span></div><div><b>03</b><span>A missed toxic compound <strong>matters.</strong></span></div></div></div>
<div class="small-audience"><b>Show of hands:</b> Would you trust a “non-toxic” prediction <em>without external validation?</em></div>
</main>
<footer class="slide-footer"><span>WHY BEEQ EXISTS</span><b>02 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>WHAT BEEQ DOES</div><h1 class="slide-title">What does BeeQ actually test?</h1>
<div class="three-questions"><div><span class="qhex">01</span><b>Prediction</b><small>Compare against strong classical baselines.</small></div><div><span class="qhex qpurple">02</span><b>Similarity</b><small>Check whether similarity really changes.</small></div><div><span class="qhex qcyan">03</span><b>Transfer</b><small>Test unfamiliar chemistry and toxic cases.</small></div></div>
<div class="statement-strip"><b>Contribution:</b> a structure-aware test of whether quantum kernels add value beyond classical molecular models.</div>
</main>
<footer class="slide-footer"><span>BEEQ · THREE RESEARCH QUESTIONS</span><b>03 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="kicker"><span class="kickerhex"></span>METHODS · OUR GUIDE</div><h1 class="slide-title">One experiment. Four steps.</h1><div class="v6-roadmap">
<div class="v6-phase"><span class="v6-phase-no">01</span><strong>Data</strong><small>893 molecules<br/>X10 descriptors</small></div><div class="v6-link">→</div>
<div class="v6-phase v6-purple"><span class="v6-phase-no">02</span><strong>Split</strong><small>462 structural<br/>clusters</small></div><div class="v6-link">→</div>
<div class="v6-phase v6-cyan"><span class="v6-phase-no">03</span><strong>Compare</strong><small>6 models<br/>nested CV</small></div><div class="v6-link">→</div>
<div class="v6-phase v6-orange"><span class="v6-phase-no">04</span><strong>Test</strong><small>181 holdout<br/>+ CR8 external</small></div>
</div><div class="v6-output"><span>Fixed input &amp; matched splits</span><span>→</span><strong>Only the similarity function changes between the three SVCs</strong></div>
</main><footer class="slide-footer"><span>FIGURE 1 · SIMPLIFIED GUIDE · ORIGINAL IN APPENDIX</span><b>04 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="method-locator" aria-label="Methodology stage"><span class="stage-chip active">1 DATA</span><span class="stage-chip ">2 SPLIT</span><span class="stage-chip ">3 MODELS</span><span class="stage-chip ">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>DATA &amp; STRUCTURAL SPLIT</div><h1 class="slide-title">One dataset. Two independent partitions.</h1><div class="v6-metrics"><div><b>893</b><span>compounds</span></div><div><b>271</b><span>toxic</span></div><div><b>622</b><span>non-toxic</span></div></div>
<div class="v6-endpoint"><b>Toxic when LD₅₀ ≤ 11 µg/bee</b><span>LD₅₀ = dose lethal to 50% of tested bees</span></div>
<div class="split-bar v6-split"><div class="split-segment dev"><b>712</b><span>Development · 374 clusters</span></div><div class="split-segment hold"><b>181</b><span>Holdout · 88 clusters</span></div></div>
<div class="v6-under"><span><b>462 Butina clusters</b> from Morgan fingerprints</span><span>No family crosses the split</span></div></main><footer class="slide-footer"><span>BEEQ893 · ENDPOINT AND PARTITION</span><b>05 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="method-locator" aria-label="Methodology stage"><span class="stage-chip ">1 DATA</span><span class="stage-chip active">2 SPLIT</span><span class="stage-chip ">3 MODELS</span><span class="stage-chip ">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>DATA SPLIT · NESTED CROSS-VALIDATION</div><h1 class="slide-title">Inner chooses. Outer evaluates.</h1><div class="v6-hero-art"><img src="/art/nested_cv_simple.svg" alt="Five outer group-disjoint folds. Each outer training portion contains a four-fold inner tuning loop, with a separate external holdout."/></div>
<div class="v6-rule"><span class="v6-dot teal"></span><strong>Clusters stay together.</strong><span class="v6-dot gold"></span><strong>One outer fold tests each turn.</strong></div></main><footer class="slide-footer"><span>5 OUTER + 4 INNER · THE HOLDOUT REMAINS SEPARATE</span><b>06 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="method-locator" aria-label="Methodology stage"><span class="stage-chip ">1 DATA</span><span class="stage-chip ">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip ">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>MODELS · FIXED X10 INPUT</div><h1 class="slide-title">Every molecule becomes ten descriptors.</h1><div class="v6-rep">
<div class="v6-molecule"><img src="/art/ethiprole_molecule.png" alt="Chemical structure of Ethiprole, a held-out external agrochemical"/><strong>Example: Ethiprole</strong><small>Chemical structure</small></div>
<div class="v6-rep-arrow">→</div>
<div class="v6-ten"><div class="v6-ten-title">X10 · same inputs for all models</div><div class="v6-descriptorgrid"><span>logP</span><span>MW</span><span>TPSA</span><span>HBD</span><span>RotB</span><span>ArR</span><span>nHal</span><span>nOP</span><span>LiPHEX</span><span>fSASA</span></div><div class="v6-descriptor-foot">Properties → standardize → compare</div></div>
</div><div class="v6-rule"><b>Morgan fingerprints</b> group structures; <b>X10 descriptors</b> feed the models.</div></main><footer class="slide-footer"><span>MOLECULAR REPRESENTATION · FULL DEFINITIONS IN APPENDIX</span><b>07 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="method-locator" aria-label="Methodology stage"><span class="stage-chip ">1 DATA</span><span class="stage-chip ">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip ">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>MODELS · 20-SECOND THEORY</div><h1 class="slide-title">A kernel is a similarity score.</h1><div class="v6-hero-art v6-kernel"><img src="/art/kernel_basics.svg" alt="Two molecular vectors passed through a similarity function to fill a pairwise similarity matrix"/></div>
<div class="v6-modelband"><span>Classical: <b>LR · RF · MLP</b></span><span>Matched SVCs: <b>RBF · Product QK · IQP–ZZ QK</b></span></div></main><footer class="slide-footer"><span>THE SAME X10 · THREE DIFFERENT SVC KERNELS</span><b>08 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="method-locator" aria-label="Methodology stage"><span class="stage-chip ">1 DATA</span><span class="stage-chip ">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip ">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>MODELS · SIMULATED CIRCUITS</div><h1 class="slide-title">Quantum kernels encode X10 in 10 qubits.</h1><div class="v6-circuit-art"><img src="/art/quantum_circuits_clean.svg" alt="Simplified Product quantum kernel circuit with independent RY rotations and IQP-ZZ circuit with H, RZ, and adjacent ZZ couplings"/></div>
<div class="v6-circuit-foot"><span><b>Similarity:</b> squared state overlap (fidelity)</span><span><b>Exact simulation</b> · no quantum hardware</span></div></main><footer class="slide-footer"><span>PRODUCT VS IQP–ZZ · SCHEMATIC, FULL SI FIGURE IN APPENDIX</span><b>09 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide figure2-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER FIGURE 2 · PERFORMANCE</div><h1 class="slide-title">Do quantum kernels improve ranking?</h1>
<div class="two-figures"><figure><figcaption><b>A</b> AUROC · discrimination</figcaption><img alt="Original paper Figure 2A: outer-fold AUROC, means, holdout markers" class="chart" src="/fig/fig2-A-auroc-tight.png"/></figure><figure><figcaption><b>B</b> AUPRC · toxic-class precision/recall</figcaption><img alt="Original paper Figure 2B: outer-fold AUPRC and holdout markers" class="chart" src="/fig/fig2-B-auprc-tight.png"/></figure></div>
<div class="lesson"><span class="lessonhex"></span><b>Answer:</b> No stable quantum improvement. Random Forest reaches mean AUROC <strong>0.748 ± 0.057</strong>.</div>
</main>
<footer class="slide-footer"><span>PAPER FIGURE 2 · AUROC AND AUPRC</span><b>10 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip">3 MODELS</span><span class="stage-chip active">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER RESULTS · HISTORICAL TRANSFER</div><h1 class="slide-title">The most costly errors were missed toxic compounds.</h1>
<div class="error-center"><div class="error-metric"><span>TOXIC-COMPOUND SENSITIVITY</span><strong>8–27<span>%</span></strong><small>Historical holdout · at Development-selected thresholds</small></div><div class="miss-box"><b>36–45</b><span>toxic compounds missed<br/>out of 49 truly toxic</span></div></div>
<div class="bottom-warning">High overall ranking performance does not guarantee toxic-compound detection.</div>
</main>
<footer class="slide-footer"><span>HISTORICAL HOLDOUT · SENSITIVITY</span><b>11 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER FIGURE 3A · PAIRED TEST</div><h1 class="slide-title">Does replacing RBF help on identical folds?</h1><div class="chart-frame"><img alt="fig/fig3-A-paired-tight.png" class="chart" src="/fig/fig3-A-paired-tight.png"/></div><div class="lesson"><span class="lessonhex"></span><b>Answer:</b> Average ΔAUROC is small: <b>+0.011</b> (Product) and <b>+0.002</b> (IQP–ZZ); signs vary.</div></main>
<footer class="slide-footer"><span>PAPER FIGURE 3A · SAME-FOLD DIFFERENCES</span><b>12 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER FIGURE 3B · SIMILARITY</div><h1 class="slide-title">Why are their predictions so alike?</h1>
<div class="wide-figure"><img alt="Paper Figure 3B kernel similarity comparisons" class="chart" src="/fig/fig3-B-geometry-tight.png"/></div>
<div class="cka-bar"><div><strong>0.982</strong><span>Product QK ↔ RBF</span></div><div><strong>0.985</strong><span>IQP–ZZ ↔ RBF</span></div><div><strong>0.9995</strong><span>Product ↔ IQP–ZZ</span></div></div>
<div class="bottom-reading">Centered kernel alignment (CKA): very similar geometry, not identical functions.</div>
</main>
<footer class="slide-footer"><span>PAPER FIGURE 3B · KERNEL GEOMETRY</span><b>13 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip">3 MODELS</span><span class="stage-chip active">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER FIGURE 4A · EXTERNAL CHALLENGE</div><h1 class="slide-title">Can eight local agrochemicals reveal a blind spot?</h1><div class="chart-frame"><img alt="fig/fig4-A-decisions-tight.png" class="chart" src="/fig/fig4-A-decisions-tight.png"/></div><div class="lesson"><span class="lessonhex"></span><b>Two toxic cases:</b> Ethiprole missed by all six models; Isocycloseram missed by five.</div></main>
<footer class="slide-footer"><span>PAPER FIGURE 4A · CR8 EXTERNAL DECISIONS</span><b>14 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip">3 MODELS</span><span class="stage-chip active">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER FIGURE 4B · APPLICABILITY DOMAIN</div><h1 class="slide-title">Does domain membership guarantee reliability?</h1><div class="chart-frame"><img alt="fig/fig4-B-domain-tight.png" class="chart" src="/fig/fig4-B-domain-tight.png"/></div><div class="lesson"><span class="lessonhex"></span><b>No.</b> 7/8 CR8 chemicals lie inside both domain checks; important mistakes remain.</div></main>
<footer class="slide-footer"><span>PAPER FIGURE 4B · APPLICABILITY DOMAIN</span><b>15 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip">3 MODELS</span><span class="stage-chip active">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>PAPER FIGURE 4C · NEIGHBORS</div><h1 class="slide-title">What do the chemical neighborhoods tell us?</h1><div class="chart-frame"><img alt="fig/fig4-C-neighbors-tight.png" class="chart" src="/fig/fig4-C-neighbors-tight.png"/></div><div class="lesson"><span class="lessonhex"></span><b>Different failure mechanisms:</b> Ethiprole has nearer toxic support; Isocycloseram has weaker structural support.</div></main>
<footer class="slide-footer"><span>PAPER FIGURE 4C · CHEMICAL NEIGHBORS</span><b>16 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="method-locator" aria-label="Methodology stage"><span class="stage-chip ">1 DATA</span><span class="stage-chip ">2 SPLIT</span><span class="stage-chip ">3 MODELS</span><span class="stage-chip active">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>RESULTS · A CONCRETE EXAMPLE</div><h1 class="slide-title">Similar chemistry did not prevent the error.</h1><div class="v6-pair">
<div class="v6-chemical"><div class="v6-mol-crop"><img src="/art/ethiprole_molecule.png" alt="Ethiprole chemical structure"/></div><strong>Ethiprole</strong><span>CR8 · toxic</span><b class="v6-wrong">Missed by all 6</b></div>
<div class="v6-sim"><b>0.740</b><span>Morgan/Tanimoto<br/>similarity</span><div class="v6-double-arrow">↔</div></div>
<div class="v6-chemical"><div class="v6-mol-crop"><img src="/art/fipronil_molecule.png" alt="Fipronil chemical structure"/></div><strong>Fipronil</strong><span>Development · toxic</span><b class="v6-known">Known in training</b></div></div>
<div class="v6-rule"><strong>Even a nearby toxic compound did not guarantee a correct toxic prediction.</strong></div></main><footer class="slide-footer"><span>SI TABLE · ETHIPROLE / FIPRONIL (ID 387)</span><b>17 / 20</b></footer></div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>WHAT WE CAN NOW CONCLUDE</div><h1 class="slide-title">What did BeeQ contribute?</h1>
<div class="takeaway-stack"><div><span class="mark-hex">1</span><b>Performance</b><strong>Quantum ≈ RBF</strong><p>No consistent gain on matched partitions.</p></div><div><span class="mark-hex purple">2</span><b>Geometry</b><strong>Nearly aligned</strong><p>CKA explains why rankings are similar.</p></div><div><span class="mark-hex cyan">3</span><b>Transfer</b><strong>Toxic cases missed</strong><p>Holdout and CR8 reveal practical gaps.</p></div></div>
<div class="statement-strip">BeeQ contributes a reproducible <b>test of the claim</b>, not just a model ranking.</div>
</main>
<footer class="slide-footer"><span>TAKEAWAYS · RESEARCH CONTRIBUTION</span><b>18 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide future-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>FUTURE WORK</div><h1 class="slide-title">Future work: what would change the result?</h1>
<div class="future-title">FUTURE <b>WORK</b><span class="future-hex">⬡</span></div>
<div class="future-grid"><div><span>01</span><b>Better representations</b><p>Improve descriptors while keeping qubit budgets realistic.</p></div><div><span>02</span><b>Safety-aware decisions</b><p>Optimize toxic-case recall and reliable uncertainty estimates.</p></div><div><span>03</span><b>Harder external tests</b><p>New chemistry, wider validation, and eventual device-aware checks.</p></div></div>
</main>
<footer class="slide-footer"><span>FUTURE WORK · NEXT EXPERIMENTS</span><b>19 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide end-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>THANK YOU</div><h1 class="slide-title">Questions?</h1>
<div class="thanks-body"><div class="thanks-logo">Bee<span>Q</span><i class="pent-point"></i></div><div class="thanks-invite">What would it take to <b>trust</b> a toxicity prediction?</div><div class="thanks-links"><b>Presented by Johnny Z. Agüero-Sandí</b><br/>github.com/andresquesadag/BeeQ<br/>Supporting Information · DOI: 10.5281/zenodo.23329579</div></div>
</main>
<footer class="slide-footer"><span>THANK YOU · QUESTIONS</span><b>20 / 20</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>TECHNICAL APPENDIX</div><h1 class="slide-title">Additional evidence &amp; diagnostics.</h1><div class="backup-index"><div>Original paper figures</div><div>Validation protocol</div><div>Kernel geometry</div><div>External cases</div><div>X10 tradeoffs</div></div><div class="statement-strip">These slides are for Q&amp;A—not part of the 15-minute main talk.</div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B01</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · PAPER FIGURE 2A</div><h1 class="slide-title">AUROC enlarged.</h1><div class="chart-frame"><img alt="fig/fig2-A-auroc-tight.png" class="chart" src="/fig/fig2-A-auroc-tight.png"/></div><div class="lesson"><span class="lessonhex"></span>AUROC reflects ranking across classification thresholds.</div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B02</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · PAPER FIGURE 2B</div><h1 class="slide-title">AUPRC enlarged.</h1><div class="chart-frame"><img alt="fig/fig2-B-auprc-tight.png" class="chart" src="/fig/fig2-B-auprc-tight.png"/></div><div class="lesson"><span class="lessonhex"></span>AUPRC focuses the precision-recall trade-off on the positive toxic class.</div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B03</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · PAPER FIGURE 1</div><h1 class="slide-title">Original full methods diagram.</h1><div class="chart-frame"><img alt="fig/modelling-methods.svg" class="chart" src="/fig/modelling-methods.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B04</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · KERNEL PAIRS</div><h1 class="slide-title">Paired differences by fold.</h1><div class="chart-frame"><img alt="fig/fig3-A-paired-tight.png" class="chart" src="/fig/fig3-A-paired-tight.png"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B05</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · KERNEL GEOMETRY</div><h1 class="slide-title">Expanded similarity mapping.</h1><div class="chart-frame"><img alt="fig/fig3-B-geometry-tight.png" class="chart" src="/fig/fig3-B-geometry-tight.png"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B06</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · MAIN FIGURE 4</div><h1 class="slide-title">Complete CR8 experiment figure.</h1><div class="chart-frame"><img alt="fig/external-final-freeze.svg" class="chart" src="/fig/external-final-freeze.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B07</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · SI VALIDATION</div><h1 class="slide-title">Nested selection and holdout workflow.</h1><div class="chart-frame"><img alt="si/nested_workflow.svg" class="chart" src="/si/nested_workflow.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B08</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · SI CIRCUITS</div><h1 class="slide-title">Product vs IQP–ZZ feature maps.</h1><div class="chart-frame"><img alt="si/feature_maps.svg" class="chart" src="/si/feature_maps.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B09</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · SI PARTITIONS</div><h1 class="slide-title">Cluster and fold composition.</h1><div class="chart-frame"><img alt="si/clusters_folds.svg" class="chart" src="/si/clusters_folds.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B10</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · SI CURVES</div><h1 class="slide-title">ROC and precision-recall curves.</h1><div class="chart-frame"><img alt="si/roc_pr.svg" class="chart" src="/si/roc_pr.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B11</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · SI ROBUSTNESS</div><h1 class="slide-title">Label-randomization control.</h1><div class="chart-frame"><img alt="si/yrandom.svg" class="chart" src="/si/yrandom.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B12</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · SI CR8</div><h1 class="slide-title">Detailed domain / decision checks.</h1><div class="chart-frame"><img alt="si/cr8_ad_decisions.svg" class="chart" src="/si/cr8_ad_decisions.svg"/></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B13</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · REPRESENTATIONS</div><h1 class="slide-title">Is X10 the best possible input?</h1><div class="backup-table"><div class="row table-head"><span>Representation</span><span>Classifier</span><span>Mean AUROC ± SD</span></div><div class="row"><span>WL-OA graph kernel</span><span>SVC</span><b>0.805 ± 0.073</b></div><div class="row"><span>ECFP</span><span>RF</span><b>0.787 ± 0.091</b></div><div class="row"><span>RDKit2D</span><span>RF</span><b>0.784 ± 0.064</b></div><div class="row"><span>X10 (BeeQ)</span><span>Fixed representation</span><b>Controlled</b></div></div><div class="lesson">X10 is a fixed scientific comparison contract—not an optimized QSAR representation.</div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B14</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">TECHNICAL APPENDIX</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · CLAIMS &amp; LIMITS</div><h1 class="slide-title">Which claim is supported?</h1><div class="backup-limits"><div><strong>SUPPORTED</strong><p>Matched kernel results and near-identical kernel geometry in this simulated fixed-X10 setting.</p></div><div><strong>NOT SUPPORTED</strong><p>Quantum hardware advantage; population-level CR8 sensitivity; direct regulatory safety claims.</p></div><div><strong>WHY</strong><p>External shifts, label imbalance and limited compound support still matter.</p></div></div></main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B15</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip active">2 SPLIT</span><span class="stage-chip">3 MODELS</span><span class="stage-chip">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>METHODOLOGICAL SAFEGUARD</div><h1 class="slide-title">We split by molecules’ structural families.</h1>
<div class="big-partition"><div class="partition-top"><div class="partition-a"><span>DEVELOPMENT</span><b>712</b><small>374 clusters</small></div><div class="partition-b"><span>HISTORICAL HOLDOUT</span><b>181</b><small>88 clusters</small></div></div><div class="partition-bottom">462 Butina clusters · no cluster shared across these partitions</div></div>
<div class="fold-panel"><div><b>5 outer folds</b><span>Estimate generalization</span></div><div class="fold-arrow">→</div><div><b>4 inner folds</b><span>Choose hyperparameters</span></div><div class="fold-arrow">→</div><div><b>Frozen holdout</b><span>Assess transfer</span></div></div>
<div class="statement-strip">The point: avoid evaluating near-relatives as if they were new chemistry.</div>
</main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B16</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div aria-label="Methodology stage" class="method-locator"><span class="stage-chip">1 DATA</span><span class="stage-chip">2 SPLIT</span><span class="stage-chip active">3 MODELS</span><span class="stage-chip">4 TEST</span></div><div class="kicker"><span class="kickerhex"></span>MATCHED EXPERIMENT</div><h1 class="slide-title">Same X10. Different similarity kernels.</h1>
<div class="input-label">10 descriptors → 10-qubit fixed quantum feature maps</div>
<div class="kernel-grid"><div class="kernel-classic"><span>CLASSICAL</span><b>RBF</b><p>Distance-based<br/>similarity</p></div><div class="kernel-quantum"><span>QUANTUM</span><b>Product QK</b><p>Independent<br/>rotations</p></div><div class="kernel-quantum"><span>QUANTUM</span><b>IQP–ZZ QK</b><p>Entangling<br/>interactions</p></div></div>
<div class="matched-band"><span>ALL THREE</span><strong>Same molecules · same folds · same SVC protocol</strong></div>
<div class="small-method-note">LR, Random Forest and MLP add reference baselines.</div>
</main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B17</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide">
<header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span aria-label="pentagon" class="brand-divider pent-divider"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026  ·  UCR GUÁPILES</div></header>
<main class="slide-main"><div class="kicker"><span class="kickerhex"></span>INTERPRETATION &amp; LIMITS</div><h1 class="slide-title">What this study does—and does not—establish.</h1>
<div class="limit-grid"><div><div class="limit-icon">✓</div><b>What we evaluated</b><p>Exact, simulated 10-qubit fidelity kernels using fixed X10 descriptors.</p></div><div><div class="limit-icon x">×</div><b>What we cannot claim</b><p>Quantum hardware advantage or validated pesticide-safety deployment.</p></div></div>
<div class="limit-foot">CR8 has only 8 compounds; the historical holdout was inspected in exploratory research phases.</div>
</main>
<footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B18</b></footer>
</div>


---
layout: full
transition: fade
---
<div class="deck-slide "><header class="slide-header"><div class="brand"><span class="hex-icon"></span><strong>BeeQ</strong><span class="brand-divider pent-divider" aria-label="pentagon"></span><span>QUANTUM KERNELS &amp; BEE TOXICITY</span></div><div class="header-event">BIP 2026 · UCR GUÁPILES</div></header><main class="slide-main"><div class="kicker"><span class="kickerhex"></span>BACKUP · X10 GLOSSARY</div><h1 class="slide-title">What do the ten descriptors mean?</h1><div class="v6-def-grid"><div class="v6-def"><span>01</span><b>logP</b><p>Estimated oil/water partitioning; lipophilicity</p></div><div class="v6-def"><span>02</span><b>MW</b><p>Molecular weight</p></div><div class="v6-def"><span>03</span><b>TPSA</b><p>Topological polar surface area</p></div><div class="v6-def"><span>04</span><b>HBD</b><p>Hydrogen-bond donor groups</p></div><div class="v6-def"><span>05</span><b>RotB</b><p>Rotatable bonds</p></div><div class="v6-def"><span>06</span><b>ArR</b><p>Aromatic ring count</p></div><div class="v6-def"><span>07</span><b>nHal</b><p>Number of halogen atoms (F, Cl, Br, I)</p></div><div class="v6-def"><span>08</span><b>nOP</b><p>Frozen organophosphorus-like pattern count</p></div><div class="v6-def"><span>09</span><b>LiPHEX</b><p>Predicted hexadecane/water partition descriptor</p></div><div class="v6-def"><span>10</span><b>fSASA</b><p>Fraction of exposed area on polar heteroatoms</p></div></div><div class="v6-def-source">Source: Supporting Information, frozen X10 descriptor order. All models receive these ten standardized features.</div></main><footer class="slide-footer"><span>BACKUP · REFERENCE MATERIAL</span><b>B19</b></footer></div>


