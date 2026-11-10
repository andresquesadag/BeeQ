# Presenter notes · BeeQ · IEEE BIP 2026

Version 4, in English. Planned running time **13:40** in a 15-minute slot. The two
supplementary slides at the end do not count towards it. The same notes live in
the deck: press **N**.

## Reveals

Four slides build up in steps. The right arrow advances the step first and the
slide second; the left arrow undoes the step.

| Slide | What is on screen first | What appears on the click |
|---|---|---|
| 4 · Context | the three steps | the bee strip and "BeeQ sits at the third step" |
| 6 · BeeQ893 | the claims: 1,035 → 893, binary endpoint | the partition chart, to talk through clusters |
| 8 · X10 | the molecule | the ten descriptor cards, all at once |
| 11 · Performance | the headline | the chart, with the claim and the AUROC gloss below it |

**The PDF has one page per step**, so a slide with one reveal prints as two
pages. That is why the 19 slides come out as 23 pages.

The block you are in is shown by the stepper at the top right of every content
slide, not by a hairline at the top edge.

## Budget by block

| Block | Slides | Time | Cumulative |
|---|---|---|---|
| Title, agenda and team | 1–3 | 1:15 | 1:15 |
| **A · Context** | 4–5 | 1:40 | 2:55 |
| **B · Methodology** | 6–8 | 2:50 | 5:45 |
| **C · Implementation** | 9–10 | 1:55 | 7:40 |
| **D · Results** | 11–14 | 3:50 | 11:30 |
| **E · Conclusions** | 15–17 | 2:10 | 13:40 |
| Supplementary | S1–S2 | — | — |

**If you are running late**, compress slide 9, then 14, then 2. **Do not**
compress 12 or 15.

---

## 1 · Title — 0:20 · cum. 0:20
Good morning. This talk is about a controlled experiment: we took a real problem
in computational toxicology and asked whether a quantum kernel compares molecules
differently from a classical kernel, when everything else is held fixed.

> **Transition:** "Here is the route."

## 2 · Agenda — 0:25 · cum. 0:45
Five blocks. Context and the question; methodology, which is the data and how we
prepared it; implementation, which is the kernel and the quantum encoding;
results; and conclusions with the future work. The bar at the top always shows
which block we are in.

> **Transition:** "Let us start with the why."

## 3 · The team — 0:30 · cum. 1:15
We met working together at Quantathon 2026 CR, on a quantum classification
problem for water potability. BeeQ came out of the same group a few weeks later:
chemistry from CBio3 at UCR, computing from UCR and TEC.

*Personalise this: say who proposed the question and in what setting. This is the
moment of the talk to speak in the first person.*

> **Transition:** "With the team introduced, on to the problem." 

## 4 · Context — 0:40 · cum. 1:55
Honey bees are important pollinators and are exposed to agricultural active
ingredients. The standard for acute toxicity is an in vivo assay giving the LD₅₀
per bee: reliable, but slow, expensive, and requiring animals.

The third step is what gives the project its purpose: the point is not to take
every molecule to the laboratory, but to have a prior comparison telling us which
ones are more likely to be toxic and deserve the assay. Prioritise, not replace.

> **Transition:** "Within that frame, our question is methodological."

## 5 · Research question — 1:00 · cum. 2:55
The question on screen is the paper's, verbatim. A quantum kernel encodes
descriptors into quantum states and uses the fidelity between those states as a
similarity measure. That changes how similar two molecules are considered to be,
but the classifier can stay classical.

Huang and colleagues showed that the geometric difference between classical and
quantum kernels is the key factor for their predictive behaviour to differ.
Fidelity kernels can also concentrate exponentially. So the question is empirical.

**The pipeline.** We start from ApisTox, go through curation and pre-processing,
partition by molecular clusters, and then two tracks open: the classical
reference models — logistic regression, Random Forest and MLP — and the three
kernels sharing one SVC. Everything converges on the same metrics.

What matters is that everything is fixed except the amber box. That is why any
difference can be attributed to the kernel. One caveat: "matched RBF" does not
mean matching the bandwidth.

> **Transition:** "Let us look at the starting data."

## 6 · BeeQ893 and the endpoint — 0:50 · cum. 3:45
We start from ApisTox, which integrates curated data from ECOTOX, PPDB and BPDB,
with 1,035 compounds. After an additional curation and structural standardisation
stage — excluding metal-containing structures, handling salts and charge states
with RDKit — 893 organic molecules remain: 622 non-toxic and 271 toxic.

Those 893 split into Development, 712 molecules, and a historical holdout of 181.
Separately there is CR8, an external panel of eight active ingredients approved in
Costa Rica.

The endpoint is binary: toxic if the LD₅₀ is at most 11 micrograms per bee. That
threshold comes from ApisTox and the EPA bee-risk guidance, was fixed before
modelling, and was not optimised.

*If asked:* for the 142 excluded molecules a per-operation removal ledger cannot
be reconstructed; and the label aggregates the most severe exposure route
available, so it is not one homogeneous protocol.

> **Transition:** "Now, how they are split for a fair evaluation."

## 7 · Partitions and freezing — 0:55 · cum. 4:40
The central risk in molecular evaluation is similarity leakage: if an evaluation
molecule has a near-identical relative in training, the model looks better than it
is. Recent ApisTox benchmarking insists on this point.

So we cluster first. Morgan fingerprints of radius 2 and 1,024 bits with
chirality, Tanimoto similarity, and Butina clustering at a 0.60 cutoff. That gives
462 clusters, 334 of them singletons and the largest with 40 molecules. Whole
clusters are assigned disjointly.

At the top you see the composition of the five frozen outer folds and the audit:
zero clusters shared across either side of any fold. Note the heterogeneity —
fold 4 validates 181 molecules with 59 toxic; fold 2 only 105 with 37. That will
explain much of the dispersion we are about to see.

Below, the selection and freezing flow. Within each outer fold's training
partition, four inner cluster-grouped splits choose hyperparameters by mean inner
AUROC and the threshold by maximum MCC. Then a single refit on all 712, and
everything is frozen. The manifest is written before the holdout and CR8 are
opened; both are evaluated once.

*Caveat:* the holdout is "historical" — it was inspected during earlier
exploratory stages. And cluster disjointness is not a formal out-of-distribution
guarantee.

> **Transition:** "And how do we describe each molecule?"

## 8 · From molecule to X10 — 1:05 · cum. 5:45
Every model receives the same ordered ten-dimensional vector, X10. Here we build
it with a concrete molecule, Ethiprole, from the external panel.

Three steps. First, ten physicochemical and structural descriptors are computed on
the structure: that is the large value on each card. Second, standardisation:
subtract the mean and divide by the standard deviation of the corresponding
training partition, never using evaluation data; that is z. Third, and this is
what connects to the quantum part: that standardised value is multiplied by the
encoding scale s, which is 0.25, giving the angle theta that rotates a qubit.

One descriptor, one qubit. The descriptor order determines which qubit receives
which; that is why each card carries its number in the corner. That decision comes
back in the future work.

Note that nHal gives the largest angle: Ethiprole has five halogens against a mean
of 1.25. LiPHEX gives the most negative one.

The useful analogy is a house fact sheet: floor area, rooms, year built. It lets
you compare houses, but nobody would say it reconstructs the house.

> **Transition:** "With the molecule now in numbers, on to the models."

## 9 · What a kernel is — 0:40 · cum. 6:25
For those who do not work with this: a kernel is a function that, given two
molecules, returns a number saying how similar they are. Do that for every pair
and you get a square table, the Gram matrix.

The classical reference is the RBF kernel, which decays exponentially with the
squared distance between standardised descriptors. Gamma says how fast it decays,
that is, how demanding the notion of "similar" is.

The key point: the classifier does not change. An SVC receives the pre-computed
table and learns the boundary. Changing the kernel changes the similarity
geometry, not the machine that decides. That is how we isolate the kernel's effect.

> **Transition:** "And here is where the quantum part comes in."

## 10 · Quantum encoding and fidelity — 1:15 · cum. 7:40
We take the standardised descriptor and turn it into an angle. On the Bloch
sphere, a qubit starting at the |0⟩ pole tilts by an angle theta equal to s times
z. With ten descriptors, ten qubits.

The Product map does exactly that: ten independent RY rotations, with no
entangling operation. The IQP-ZZ map starts from a uniform superposition with
Hadamards, applies a layer of RZ phases and then RZZ phases between neighbouring
qubits in a chain, with interaction strength fixed at one and a single repetition.
There is no final Hadamard layer.

Note that detail about the chain: only neighbouring qubits are coupled. We will
come back to it at the end.

The similarity between two molecules is the fidelity between their states: the
squared modulus of the inner product. It lies between zero and one, and equals one
when the states coincide.

**The scope, worth stating before any result:** everything was simulated with
exact statevectors in NumPy, 1,024 amplitudes per molecule, without shot sampling,
without a noise model and without hardware execution. Qiskit appears in the
environment but did not execute the reported campaign. This is not a hardware
benchmark.

> **Transition:** "Let us see what happened when we measured."

## 11 · Performance — 1:10 · cum. 8:50
First, what AUROC is, because everything else depends on it: the probability that
a randomly chosen toxic molecule scores higher than a randomly chosen non-toxic
one. It measures **ranking ability**, not percentage correct.

Random Forest reached the highest mean, 0.748 ± 0.057. Then logistic regression at
0.733. The three kernels landed very close together: Product 0.722, IQP-ZZ 0.713
and matched RBF 0.711. The balanced MLP, 0.679.

**What I want you to see is the dispersion, not the ordering.** Each open circle
is one fold. The kernels' standard deviations are around 0.106 to 0.108, while the
differences between their means are one or two thousandths. Fold 1 drags every
kernel below 0.57; fold 5 lifts them above 0.79. Remember the fold composition:
they are not interchangeable.

The crosses are the historical holdout, for reference.

Random Forest doing well is consistent with nonlinear relationships within X10;
logistic regression being competitive suggests a simple linear model captures much
of the signal.

*If asked about the paired comparison:* the per-fold differences between Product
and RBF, and between IQP-ZZ and RBF, average +0.011 and +0.002, do not keep a
consistent direction across folds, and change sign on the holdout. The
cluster-level paired bootstrap includes zero in all three contrasts.

> **Transition:** "But all of this is ranking ability. What about detection?"

## 12 · Ranking versus detection — 1:00 · cum. 9:50
**The distinction that matters most to a toxicologist.** A regulatory decision
needs a threshold and a binary answer. And there the picture changes completely.

On the holdout of 181 molecules — 49 toxic and 132 non-toxic — five of the six
models hold AUROC between 0.68 and 0.71, similar to Development. The matched RBF
even rises to 0.706.

**But at the frozen thresholds, sensitivity collapses:** between 0.082 and 0.265.
The best case is Random Forest, detecting 13 of 49 and letting 36 through. Product
and IQP-ZZ detect four each. Specificity is high, between 0.833 and 0.985.

Put differently: these models rank reasonably, but at the chosen operating point
they behave as very conservative filters that almost never raise an alarm. For
prioritisation that is a serious problem, because the false negative is the costly
error.

*On the MLP:* the one shown is the balanced, retuned variant. It detects 13 of 49
like Random Forest, but at the cost of 22 false positives and an AUROC of 0.482,
below chance.

> **Transition:** "And what if the molecule resembles what the model has already seen?"

## 13 · CR8 and the applicability domain — 0:55 · cum. 10:45
CR8 is an external panel of eight active ingredients approved in Costa Rica under
decree 43838, with no overlap against BeeQ893 or ApisTox, verified by canonical
SMILES and full InChIKey.

The domain is defined by two criteria derived from Development only. Horizontal
axis: structural support, maximum Morgan/Tanimoto similarity, cut at the 5th
percentile, 0.223. Vertical axis: descriptor-space support, mean distance to the
five nearest neighbours in standardised X10, cut at the 95th percentile, 2.199.
Neither was optimised on performance.

Seven of the eight fall inside both domains; the only one outside is
Fluoxapiprolin, on descriptor distance.

**And here is the point:** both toxic compounds, Ethiprole and Isocycloseram, are
inside both domains. Ethiprole was called non-toxic by all six models, and
Isocycloseram by five: the balanced MLP did detect it, but in exchange produced
two false positives, Fluoxapiprolin and Florylpicoxamid. Formal domain membership
quantifies proximity to Development; it does not guarantee a correct call.

*With eight compounds and two positives, changing one decision moves sensitivity
by half a point. These are compound-level observations, not population-level
conclusions. The two axes are weakly associated, Spearman −0.31.*

> **Transition:** "Let us look closely at the Ethiprole case."

## 14 · Ethiprole and its neighbour — 0:45 · cum. 11:30
To me this is the most instructive result. Ethiprole's nearest neighbour in
Development is fipronil, at Tanimoto similarity 0.740. They are clearly related
structures: the same pyrazole core with the dichloro, trifluoromethyl phenyl; what
changes is the sulfur substituent.

And fipronil is labelled **toxic** and was in training. The model had a very
similar toxic example and still called Ethiprole non-toxic. All six models failed.

Nor is it a borderline case: Ethiprole's experimental LD₅₀ is well below the
11 µg per bee threshold.

Isocycloseram is the complementary case: its maximum structural support is 0.233,
barely above the cutoff. There the problem does look like chemotype extrapolation.

The honest reading is that X10 may not capture some structure-activity
relationships relevant to this endpoint. That is a hypothesis for toxicodynamic
and biophysical studies, not a conclusion demonstrated here.

> **Transition:** "Let us close with what this does and does not show."

## 15 · Conclusions — 0:55 · cum. 12:25
Two findings under molecular-cluster-disjoint evaluation.

First: the quantum kernels evaluated did not deliver a consistent predictive
improvement over the matched RBF. They came very close, but without an advantage
that persisted across the five folds, and on the holdout the contrasts changed
sign.

Second: they did not induce a clearly distinct similarity geometry either. The
three kernels' Gram matrices are highly aligned: CKA of 0.982 and 0.985 against
the RBF, and 0.9995 between the two quantum kernels.

And a practical finding that goes beyond the quantum question: detection of toxic
compounds outside Development is weak.

**The right-hand column matters just as much.** This does not demonstrate quantum
advantage: it shows that these two fixed maps, with this representation and this
protocol, do not separate from the RBF. We did not evaluate noise or hardware. It
does not establish clinical or regulatory utility. And it does not generalise
beyond X10 and these maps.

> **Transition:** "Where do we go next?"

## 16 · Future work — 0:50 · cum. 13:15
Three concrete directions.

First: extend encoding-scale optimisation. Bandwidth turned out to be the decisive
factor, so it deserves to be treated as an object of study rather than a
by-product of the hyperparameter search.

Second: instead of fixed maps, train the embedding parameters through
kernel-target alignment.

Third, and this is where the figure comes in: rearrange and widen the qubits.
Recall that in the IQP-ZZ map the RZZ interactions only couple neighbouring qubits
in a chain. That means **which descriptor sits next to which** determines which
pairs of features can interact. Today the order is simply inherited from the table.

The figure shows how much signal each descriptor carries on its own in
Development. nOP is the most informative at 0.675; LiPHEX alone is close to
chance. One line of work is to use that structure to decide the qubit ordering,
duplicate qubits per descriptor to retain more context, or add descriptors. I
stress that this figure is descriptive: no descriptor was selected or removed
from it.

> **Transition:** "And with that I will close."

## 17 · Closing — 0:25 · cum. 13:40
The Supporting Information is archived on Zenodo, and the curated dataset, the
descriptors and the training workflow are in the GitHub repository. Thank you very
much.

---

---

## S1 · Supplementary · Kernel geometry

Back-up slide, after the closing. Use it if they ask about the geometry, or
whether the comparison against the RBF was fair.

Each panel puts one quantum kernel against the matched RBF for all 253,116 unique
Development pairs. The cloud sits on a single tight curve above the diagonal: the
kernels rank pair similarity almost identically, just on a compressed scale.
Centred alignment is 0.982 and 0.985; between the two quantum kernels, 0.9995.

The slope p near 0.55 is what the small-angle argument predicts. Product behaves
as an RBF with effective gamma 0.015625 against a tuned RBF at 0.03, which gives
0.52. The remaining gap is bandwidth, not quantum structure: a classical RBF at
that same gamma has effective rank 3.078 against Product's 3.086.

*The figure is recomputed from the frozen inputs and reproduces every value of SI
Table S22 to better than 5e-7.*

## S2 · Supplementary · The ten descriptors

Back-up slide. Use it if they ask what X10 contains or what a given descriptor
means.

The two that usually draw questions are nOP and fSASA. **nOP** is not the number
of phosphorus atoms: it counts matches to an organophosphorus-like SMARTS
pattern, and several matches can involve the same phosphorus. It carries the
strongest univariate signal, 0.675 AUROC on its own. **fSASA** is the fraction of
solvent-accessible surface belonging to polar heteroatoms; the upstream procedure
that generated it is not reproducible from the retained artefacts, and the
Supporting Information says so.

**LiPHEX** is an in-house partition descriptor, not a toxicity prediction.

---

## Likely questions and short answers


**Why did you not run on quantum hardware?**
The aim was to isolate the effect of the kernel's geometry. Introducing noise and
sampling error would have confounded that effect with the device's. Ten qubits
keep the circuit small enough to do it later; it is in the future work.

**Why only ten descriptors? That seems few.**
Because each descriptor occupies one qubit and the number of descriptors fixes the
circuit size. It is a declared design decision, not a claim that ten suffice. The
Ethiprole case in fact suggests X10 may not capture everything.

**Is this not a negative result?**
It is a bounded and, we think, informative one. In particular, controlling the
bandwidth — comparing Product against a classical RBF with the same effective
gamma of 0.015625 — the effective rank goes from 3.086 to 3.078: the apparent
difference was bandwidth, not quantum nature. That points future work at the
encoding scale and at trainable kernels.

**What about the MLP?**
There are two variants: the original unweighted one and the balanced, retuned one.
This talk uses the balanced variant consistently. The provenance is documented in
the verification record.

**What about the comparison with other representations?**
The paper reports a table with six alternative representations, but its provenance
could not be supported from the retained artefacts, so it is not presented here.
It is logged as pending.

**Is this usable for regulation?**
No. Sensitivity outside Development is between 0.082 and 0.265. As support for
exploratory prioritisation it is interesting; as a decision criterion, no.
