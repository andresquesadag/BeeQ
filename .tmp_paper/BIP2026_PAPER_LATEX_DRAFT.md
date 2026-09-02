# BIP 2026 — borrador integral de `main.tex`

Este archivo no modifica `main.tex`. Contiene una versión autocontenida para copiar cuando se decida sustituir el borrador actual.

## Decisiones congeladas para este borrador

- Campaña primaria: `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z`.
- Semilla: `20260824`.
- Dominio modelado: 893 compuestos; desarrollo de 712 y holdout histórico de 181.
- Selección de modelos: únicamente los 712 compuestos de desarrollo, con validación anidada y agrupada por clúster químico.
- Extensión exploratoria: únicamente Exercise A (`BEEQ_EXERCISE_A_10Q_VS_20Q_20260829T021247Z`).
- Exercise B queda fuera del manuscrito.
- Interpretación autorizada: Exercise A muestra sensibilidad del kernel a la codificación y a la topología de 20 qubits; no demuestra ventaja cuántica ni una mejora robusta causada solamente por aumentar el número de qubits.
- El texto evita identificar autores o repositorios para respetar la revisión doble ciego de BIP 2026.

## Pendientes antes de enviar

1. Completar la procedencia de los datos: flujo desde 1,035 registros hasta los 893 compuestos congelados, reglas de exclusión, conteos por etapa y generación de los dos descriptores internos.
2. Resolver y documentar los tres grupos con CID repetido antes de afirmar unicidad por sustancia.
3. Crear un paquete suplementario anónimo y sustituir `ANONYMOUS_ARTIFACT_URL`.
4. Copiar las figuras elegidas a `.tmp_paper/fig/` con estos nombres:

   - `primary_nested_auroc.png` desde `results/campaigns/BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z/09_FIGURES/FIG01_NESTED_AUROC.png`.
   - `primary_cr8_ad.png` desde `results/campaigns/BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z/09_FIGURES/FIG04_DUAL_AD_CR8.png`.
   - `exercise_a_pooled_mcc.png` desde `results/campaigns/BEEQ_EXERCISE_A_10Q_VS_20Q_20260829T021247Z/06_FIGURES/FIG01_POOLED_MCC.png`.

5. Revisar la paginación con el template oficial. Si excede ocho páginas, la primera figura a mover al suplemento es la de dominio de aplicabilidad; la segunda es la de Exercise A, conservando sus resultados como tabla.
6. Para la versión camera-ready, restaurar autores, afiliaciones, agradecimientos y URL pública.

## Código LaTeX completo

```latex
\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts

\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{cite}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{url}

\graphicspath{{fig/}}

\newcommand{\bee}{\textit{Apis mellifera}}
\newcommand{\xset}{\ensuremath{\mathbf{x}_{10}}}
\newcommand{\todo}[1]{\textbf{[TODO: #1]}}

\begin{document}

\title{BeeQ: Structure-Aware Honey-Bee Toxicity Prediction with Exact Quantum Fidelity Kernels and 20-Qubit Encoding Variants}

% BIP 2026 uses double-blind review. Restore author names and affiliations only
% for the camera-ready version.
\author{\IEEEauthorblockN{Anonymous Author(s)}}

\maketitle

\begin{abstract}
Reliable estimation of acute chemical toxicity to honey bees is important for ecological risk assessment, yet available molecular datasets are small, imbalanced, and structurally redundant. We present BeeQ, a reproducible comparison of classical models and exactly simulated quantum fidelity kernels for binary acute-toxicity prediction. The frozen modeling domain contains 893 curated compounds represented by ten compact physicochemical descriptors. Model selection uses only a 712-compound development set through five outer and four inner structure-grouped folds; a historical 181-compound holdout and an eight-compound Costa Rican active-ingredient panel are used only after configuration freeze. Random forest produced the highest mean outer-fold AUROC, $0.748\pm0.057$, whereas product and IQP--ZZ quantum kernels reached $0.722\pm0.108$ and $0.713\pm0.106$, respectively. Their paired AUROC differences from a capacity-matched classical RBF kernel were small and bootstrap intervals crossed zero. A development-only 20-qubit diagnostic then compared an exact 10-qubit IQP--ZZ baseline with an idle-qubit control and two active 20-qubit encodings. Duplicate and complementary encodings increased pooled out-of-fold MCC by 0.031 and 0.026, respectively, but cluster-bootstrap intervals included or touched zero and the external panel did not confirm a sensitivity gain. These results show that quantum-kernel behavior can be modified through encoding and interaction topology, while providing no evidence of quantum advantage. The study emphasizes structure-aware validation, negative controls, external applicability analysis, and calibrated claims for small-data quantum molecular learning.
\end{abstract}

\begin{IEEEkeywords}
applicability domain, honey-bee toxicity, quantum kernel methods, QSAR, structure-aware validation
\end{IEEEkeywords}

\section{Introduction}

Honey bees support pollination in natural and agricultural ecosystems, making chemical risk to \bee{} an environmental and food-system concern \cite{abejas}. Costa Rica has additionally recognized apiculture as an activity of public environmental, social, and economic importance \cite{cr_ley9929_2021}. Acute-toxicity testing, however, cannot practically cover every existing or proposed chemical. In silico models can prioritize experiments and support weight-of-evidence assessment, provided that validation reflects the intended chemical generalization problem.

Honey-bee toxicity modeling is a difficult small-data setting. Public datasets combine heterogeneous sources and often contain class imbalance, local structural redundancy, and incomplete coverage of emerging active ingredients. Random row-wise splits may place close analogues on both sides of a split and consequently overstate generalization. Structure-aware partitioning, applicability-domain analysis, and an untouched external challenge are therefore at least as important as the choice of classifier.

Quantum kernel methods offer a controlled way to study nonlinear molecular similarity. A classical descriptor vector is mapped to a quantum state and pairwise similarity is defined by state fidelity \cite{schuld2019hilbertspaces,havlicek2019quantumfeatures}. This construction does not by itself imply a performance advantage. A meaningful comparison requires identical inputs and partitions, leakage-free tuning, a classical kernel of comparable role, numerical quality control, and negative controls that can expose label artifacts or purely nominal changes in circuit size.

This work asks three questions. First, how do compact classical baselines and exactly simulated quantum fidelity kernels compare under structure-grouped nested validation? Second, do the selected models generalize to a historical holdout and to a small Costa Rican active-ingredient panel? Third, can a controlled 20-qubit extension modify the behavior of a frozen 10-qubit IQP--ZZ kernel without interpreting a larger register as evidence of quantum advantage?

The principal contributions are:

\begin{itemize}
    \item a deterministic, cluster-grouped nested evaluation of three classical models, a matched RBF kernel, and two quantum fidelity kernels on the same ten-dimensional representation;
    \item paired cluster-bootstrap comparisons, label randomization, Gram-matrix quality checks, and dual applicability-domain diagnostics;
    \item post-freeze evaluation on a historical holdout and a small external panel; and
    \item an exact, development-only 10-to-20-qubit diagnostic containing an identity-preserving idle control and two active encoding variants.
\end{itemize}

\section{Related Work}

\subsection{Machine learning for honey-bee toxicity}

Honey-bee QSAR studies have explored curated physicochemical descriptors, fingerprints, graph kernels, and neural molecular representations. Carnesecchi \textit{et al.} combined acute contact-toxicity QSAR with mode-of-action profiling and emphasized curation and validation \cite{carnesecchi2020integrating}. Xu \textit{et al.} evaluated machine-learning models for acute contact toxicity \cite{xu2021insilico}, while BeeToxAI translated descriptor-based models into an accessible prediction tool \cite{moreirafilho2021beetoxai}. Structure-centered alternatives include graph-attention networks \cite{wang2020graphattention} and random-walk graph kernels with support-vector machines \cite{yang2022randomwalk}.

Recent work has benefited from broader public benchmarks. ApisTox consolidated small-molecule honey-bee toxicity records for classification \cite{adamczyk2025apistox}. Subsequent studies compared conventional learners \cite{adamczyk2026evaluating}, examined modern QSAR workflows \cite{sharifi2024insilico}, and applied graph neural networks \cite{damiao2025newgeneration}. These advances reinforce the importance of usable molecular representations, but reported performance remains sensitive to curation, splitting strategy, endpoint definition, and domain coverage.

\subsection{Quantum kernels in molecular prediction}

Quantum feature maps embed classical variables in a Hilbert space and permit kernel construction from state overlaps \cite{schuld2019hilbertspaces,havlicek2019quantumfeatures}. Toxicity and ADME--Tox studies have reported proof-of-concept quantum machine-learning workflows \cite{suzuki2020toxicityqml,bhatia2023admetox}. Comparative evidence across molecular tasks, however, does not establish a general quantum advantage and instead motivates matched classical controls and careful evaluation \cite{harjanto2026comparative}.

In small datasets, apparently favorable quantum results can arise from feature preprocessing, hyperparameter asymmetry, split leakage, or an unsuitable classical baseline. BeeQ therefore compares every kernel on identical standardized inputs and grouped folds, includes a capacity-matched RBF SVC, and treats exact simulation as a methodological experiment rather than as a claim of hardware acceleration.

\subsection{Validation gap}

OECD guidance frames QSAR credibility around a defined endpoint, an unambiguous algorithm, a defined applicability domain, appropriate measures of fit and predictivity, and mechanistic interpretation when possible \cite{oecd2014qsarvalidation,oecd2023qaf}. Many molecular-learning comparisons report only random-split averages. Fewer combine structure-disjoint nested selection, paired uncertainty, randomization controls, an untouched external challenge, and explicit analysis of representation changes. This combination is the gap addressed here.

\section{Materials and Methods}

\subsection{Data, endpoint, and frozen molecular representation}

The experiments use a frozen curated subset derived from ApisTox \cite{adamczyk2025apistox}. The binary endpoint indicates whether a compound belongs to the acute-toxic class under the project's frozen endpoint definition. The complete modeling domain contains 893 compounds: 712 in the development partition and 181 in a historical holdout. The development set contains 222 positive and 490 negative labels; the historical holdout contains 49 positives and 132 negatives. An external challenge contains eight Costa Rican active ingredients, of which two are positive under the same endpoint definition.

\todo{Replace this paragraph with the auditable curation flow from 1,035 source records to 893 modeled compounds, including every exclusion rule and count. Document how conflicting measurements were resolved, how salts/mixtures/metals and missing structures were handled, and how the two internal descriptors were generated.}

Each compound is represented by the same frozen ten-feature vector \xset. The representation was intentionally kept compact so that the primary quantum feature maps require ten qubits and can be compared on exactly the same information supplied to classical models. Table~\ref{tab:x10} lists the variables.

\begin{table*}[t]
\caption{Frozen ten-dimensional molecular representation.}
\label{tab:x10}
\centering
\footnotesize
\begin{tabularx}{\textwidth}{@{}lllX@{}}
\toprule
Feature & Family & Source & Meaning \\
\midrule
\texttt{MolLogP} & Physicochemical & RDKit & Crippen octanol--water partition coefficient \\
\texttt{MolWt} & Physicochemical & RDKit & Molecular weight \\
\texttt{TPSA\_SP} & Physicochemical & RDKit & Topological polar surface area \\
\texttt{NumHDonors} & Constitutional & RDKit & Hydrogen-bond donor count \\
\texttt{NumRotatableBonds} & Constitutional & RDKit & Rotatable-bond count \\
\texttt{NumAromaticRings} & Structural & RDKit & Aromatic-ring count \\
\texttt{nHalogen} & Structural & RDKit/SMARTS & Halogen-atom count \\
\texttt{n\_OP} & Structural & RDKit/SMARTS & Organophosphorus motif count \\
\texttt{LiPHEX\_prediction} & Internal & Frozen input & Lipophilicity-related model output \\
\texttt{sasa002\_frac\_polar\_hetero\_only} & Internal & Frozen input & Polar-hetero solvent-accessible surface fraction \\
\bottomrule
\end{tabularx}
\end{table*}

RDKit was used for cheminformatics operations \cite{rdkit}. Morgan fingerprints with radius 2, 1,024 bits, and chirality enabled were used only for structural grouping and applicability analysis, not as model inputs \cite{rogers2010ecfp}. Butina clustering used a Tanimoto-distance cutoff of 0.60 \cite{butina1999clustering}. Development and holdout partitions have no shared Butina cluster. The development partition contains 374 clusters and the historical holdout 88 clusters.

\subsection{Structure-aware nested selection}

The primary campaign was deterministic with seed 20260824. Five frozen outer folds estimate development performance. Within each outer-training partition, four deterministic stratified group folds tune the model while keeping complete Butina clusters together. Every split was checked for zero train--validation cluster intersection. Where scaling was required, standardization parameters were fitted only on each training partition and then applied to the corresponding validation partition.

Hyperparameters were selected by mean inner-fold AUROC. For each selected outer model, the decision threshold was obtained solely from inner out-of-fold scores by maximizing Matthews correlation coefficient (MCC), with balanced accuracy as the deterministic tie-breaker. The threshold was then applied without adjustment to the outer validation fold. This design separates hyperparameter and threshold selection from outer performance estimation.

After all development choices were frozen, the same selected configurations were refitted on the full development set and evaluated on the historical holdout. This holdout had been inspected in earlier project iterations and is consequently reported as a historical, non-pristine validation set rather than as a definitive external test. The eight-compound challenge panel was never used for model selection or threshold tuning.

\subsection{Classical and quantum models}

Classical baselines were logistic regression, random forest, and a feed-forward multilayer perceptron. Logistic regression used balanced class weights, the liblinear solver, and $C\in\{0.01,0.1,1,10,100\}$. Random forest used 300 trees, balanced-subsample weights, square-root feature sampling, maximum depth in $\{\text{unbounded},6\}$, and minimum leaf size in $\{1,3\}$. The multilayer perceptron used early stopping, one or two hidden layers of sizes $(32)$ or $(32,16)$, $L_2$ penalty in $\{10^{-4},10^{-3},10^{-2}\}$, and initial learning rate in $\{3\times10^{-4},10^{-3}\}$.

Kernel classifiers used a class-weighted support-vector machine \cite{cortes1995svm} with precomputed Gram matrices and $C\in\{0.1,1,10,100\}$. The classical kernel control was

\begin{equation}
K_{\mathrm{RBF}}(\mathbf{x},\mathbf{x}')=
\exp\!\left[-\gamma\lVert\mathbf{x}-\mathbf{x}'\rVert_2^2\right].
\label{eq:rbf}
\end{equation}

with $\gamma\in\{0.01,0.03,0.1,0.3\}$.

For a parameterized feature map $U_{\phi}$, quantum similarity was the exact fidelity kernel

\begin{equation}
K_Q(\mathbf{x},\mathbf{x}')=
\left|\langle 0|U_{\phi}^{\dagger}(\mathbf{x})
U_{\phi}(\mathbf{x}')|0\rangle\right|^2.
\label{eq:qkernel}
\end{equation}

Two ten-qubit maps were studied. With feature scale $s$, the product map is

\begin{equation}
|\psi_{\mathrm{prod}}(\mathbf{x})\rangle=
\bigotimes_{j=1}^{10}R_Y(sx_j)|0\rangle,
\qquad s\in\{0.125,0.25,0.5,1\}.
\label{eq:product-map}
\end{equation}

It encodes each standardized feature independently and isolates separable nonlinear similarity. The IQP--ZZ map starts in a uniform superposition and applies diagonal phases

\begin{equation}
\phi(\mathbf{x},\mathbf{z})=
\sum_{j=1}^{10}sx_jz_j+
\sum_{j=1}^{9}(sx_j)(sx_{j+1})z_jz_{j+1},
\label{eq:iqp-phase}
\end{equation}

where $z_j\in\{-1,+1\}$ labels computational-basis eigenvalues. The interaction strength was fixed at one and the scale $s$ used the same four-value grid as the product map. Both kernels were evaluated from exact noiseless statevectors of dimension $2^{10}=1{,}024$. No shot sampling, device noise, error mitigation, or quantum hardware was used.

Quantum Gram matrices were required to be numerically symmetric, have a unit diagonal within tolerance, and have minimum eigenvalue no smaller than $-10^{-8}$. Maximum symmetry and diagonal errors were below $10^{-10}$ in the frozen campaign.

\subsection{Uncertainty, randomization, and applicability domain}

Primary development summaries report the mean and sample standard deviation of outer-fold AUROC and AUPRC. Threshold-dependent metrics are pooled over the 712 outer out-of-fold predictions. Pairwise model differences were evaluated with 2,000 paired bootstrap resamples at the Butina-cluster level. The resulting 95\% percentile intervals preserve the dependency among analogues and the pairing of predictions across models.

A fixed-configuration label-randomization control used 200 permutations per model. Labels were permuted within the development workflow while model configurations remained fixed; the comparison asks whether the observed score is distinguishable from label-free structure under the same evaluation machinery.

Two complementary applicability-domain (AD) measures were frozen from development data. A structure AD uses each compound's maximum Morgan-fingerprint Tanimoto similarity to development compounds, with threshold equal to the fifth percentile of leave-one-out development maxima ($0.223134$). A descriptor AD uses the mean standardized Euclidean distance to the five nearest development neighbors, with threshold equal to the 95th percentile of leave-one-out development distances ($2.198975$). The two indicators are reported separately because structural novelty and displacement in the compact descriptor space are not equivalent.

\subsection{Exercise A: controlled 10-to-20-qubit extension}

Exercise A was performed only after the primary campaign had been frozen. It reuses the 712-compound development partition, the same outer and inner grouped folds, train-only scaling, model class, tuning objective, and threshold rule. The historical holdout and external panel were not used during selection. Before testing new encodings, the ten-qubit IQP--ZZ baseline was reproduced exactly: all 712 out-of-fold predictions, selected parameters, predicted classes, and thresholds matched the primary artifact up to floating-point precision (maximum score difference $4.44\times10^{-16}$).

Table~\ref{tab:architectures} defines the four diagnostic architectures. The idle-qubit control tensors the frozen ten-qubit state with ten unused $|0\rangle$ qubits; its kernel must be identical to the baseline. The duplicate encoding maps feature $z_j$ to $(z_j,z_j)$. The complementary encoding maps it to $(z_j,\operatorname{sgn}(z_j)\sqrt{|z_j|})$. Encoded pairs are interleaved, and the two active 20-qubit maps use 10 intra-variable plus 9 inter-variable nearest-neighbor edges.

\begin{table}[t]
\caption{Exercise A quantum-kernel diagnostics.}
\label{tab:architectures}
\centering
\footnotesize
\begin{tabularx}{\columnwidth}{@{}l c X@{}}
\toprule
Variant & Active qubits & Encoding/topology \\
\midrule
10q baseline & 10 & IQP--ZZ linear \\
20q idle & 10 of 20 & Baseline $\otimes |0\rangle^{\otimes 10}$ \\
20q duplicate & 20 & $(z_j,z_j)$; 19-edge chain \\
20q complementary & 20 & $(z_j,\mathrm{sgn}(z_j)\sqrt{|z_j|})$; chain \\
\bottomrule
\end{tabularx}
\end{table}

A dense 20-qubit statevector contains $1{,}048{,}576$ amplitudes and occupies approximately 16 MiB in complex double precision; materializing all states for the largest outer-training set would require approximately 9.48 GiB before Gram-matrix work. The active 20-qubit kernels were therefore evaluated with an exact transfer-matrix contraction of the linear Ising/IQP overlap. This is an algebraically exact classical computation for the specified topology, not a sampling or low-rank approximation.

The idle control tests implementation invariance. The duplicate and complementary variants test whether changing the active encoding and interaction graph changes predictive similarity. Because these interventions alter more than register width, their comparison can establish architecture sensitivity but cannot attribute any change solely to the number of qubits.

\section{Results and Discussion}

\subsection{Primary structure-aware development performance}

Table~\ref{tab:primary} summarizes the frozen nested campaign. Random forest achieved the highest mean outer AUROC, $0.748\pm0.057$, followed by logistic regression. Product and IQP--ZZ kernels were competitive with the matched RBF control but did not exceed it by a robust margin. The multilayer perceptron had the lowest mean AUROC and the greatest fold dispersion.

\begin{table*}[t]
\caption{Primary grouped nested-validation results. AUROC and AUPRC are outer-fold mean $\pm$ sample standard deviation; balanced accuracy and MCC are pooled over outer out-of-fold predictions.}
\label{tab:primary}
\centering
\footnotesize
\begin{tabular}{@{}lcccc@{}}
\toprule
Model & AUROC & AUPRC & Balanced accuracy & MCC \\
\midrule
Random forest & $0.7480\pm0.0574$ & $0.6573\pm0.0966$ & 0.6798 & 0.4680 \\
Logistic regression & $0.7328\pm0.1039$ & $0.6596\pm0.1241$ & 0.6784 & 0.4461 \\
Product quantum kernel & $0.7216\pm0.1075$ & $0.6279\pm0.1263$ & 0.6576 & 0.3966 \\
IQP--ZZ quantum kernel & $0.7130\pm0.1056$ & $0.6455\pm0.1122$ & 0.6549 & 0.4000 \\
RBF kernel & $0.7106\pm0.1084$ & $0.6404\pm0.1067$ & 0.6633 & 0.4055 \\
Multilayer perceptron & $0.6771\pm0.1245$ & $0.5961\pm0.1383$ & 0.6536 & 0.4283 \\
\bottomrule
\end{tabular}
\end{table*}

\begin{figure}[t]
    \centering
    \includegraphics[width=\columnwidth]{primary_nested_auroc.png}
    \caption{Outer-fold AUROC distributions for the frozen primary campaign. Every model uses the same structure-grouped folds.}
    \label{fig:primary-auroc}
\end{figure}

The paired cluster bootstrap clarifies the small kernel differences. Product minus RBF AUROC was $0.0017$ with 95\% CI $[-0.0197,0.0242]$; IQP--ZZ minus RBF was $-0.0014$ with CI $[-0.0237,0.0255]$. Product minus IQP--ZZ was $0.0032$ with CI $[-0.0209,0.0279]$. Thus, the experiment does not resolve a meaningful ranking among these three kernels. Random forest exceeded the multilayer perceptron by $0.0889$ AUROC with CI $[0.0217,0.1616]$, whereas its difference from logistic regression, $0.0313$, remained uncertain with CI $[-0.0210,0.0932]$.

In the 200-run fixed-configuration randomization test, observed pooled AUROCs ranged from 0.668 to 0.757, while permuted-label means were approximately 0.496--0.501. No randomized run equaled or exceeded its corresponding observed score. This supports the presence of learnable signal under the frozen workflow, although it does not distinguish causal toxicological mechanisms from correlational molecular structure.

\subsection{Historical holdout and external challenge}

Table~\ref{tab:holdout} reports the post-freeze historical holdout. AUROC remained near 0.69--0.71 for most non-neural models, but thresholded sensitivity was low. The RBF kernel attained the highest AUROC, 0.706, while random forest produced the highest holdout MCC, 0.358. Because the holdout was inspected during earlier project development, these values are corroborative rather than a pristine prospective estimate.

\begin{table*}[t]
\caption{Historical holdout results after development freeze.}
\label{tab:holdout}
\centering
\footnotesize
\begin{tabular}{@{}lcccccc@{}}
\toprule
Model & AUROC & AUPRC & Balanced accuracy & MCC & Sensitivity & Specificity \\
\midrule
Logistic regression & 0.6848 & 0.4907 & 0.5551 & 0.1777 & 0.1633 & 0.9470 \\
Random forest & 0.6926 & 0.5034 & 0.6175 & 0.3579 & 0.2653 & 0.9697 \\
Multilayer perceptron & 0.4624 & 0.3024 & 0.5257 & 0.1110 & 0.0816 & 0.9697 \\
RBF kernel & 0.7058 & 0.4992 & 0.5434 & 0.2002 & 0.1020 & 0.9848 \\
Product quantum kernel & 0.6974 & 0.4596 & 0.5332 & 0.1650 & 0.0816 & 0.9848 \\
IQP--ZZ quantum kernel & 0.6962 & 0.4633 & 0.5295 & 0.1357 & 0.0816 & 0.9773 \\
\bottomrule
\end{tabular}
\end{table*}

On the eight-compound external panel, logistic regression and random forest each achieved AUROC 0.75, and the multilayer perceptron reached 0.833; the three kernel SVCs yielded AUROC 0.50. These rankings are descriptive because the panel contains only two positives and six negatives. More importantly, every frozen threshold missed both positives; most models predicted all eight compounds as negative, while the multilayer perceptron added one false positive. The external challenge therefore exposes a sensitivity failure that rank metrics alone conceal.

Seven of eight external compounds were inside both frozen ADs. Fluoxapiprolin was inside the fingerprint AD but outside the descriptor AD. The two positive compounds, Ethiprole and Isocycloseram, were inside both domains, yet remained below all principal decision thresholds. The false negatives therefore cannot be explained solely by gross extrapolation under the two selected AD measures. They instead point to endpoint sparsity, representation limitations, calibration shift, or missing mechanistic information.

\begin{figure}[t]
    \centering
    \includegraphics[width=\columnwidth]{primary_cr8_ad.png}
    \caption{Dual applicability-domain assessment of the eight-compound external challenge. Structural similarity and compact-descriptor distance are reported independently.}
    \label{fig:cr8-ad}
\end{figure}

\subsection{Exercise A: what changed at 20 qubits?}

Table~\ref{tab:exercise-a} reports pooled development out-of-fold performance. The 20-qubit idle control was numerically identical to the 10-qubit baseline, confirming that unused qubits do not change the kernel or classifier. The duplicate and complementary active encodings increased pooled MCC from 0.4000 to 0.4314 and 0.4255, respectively. Their AUROC and AUPRC point estimates also increased modestly.

\begin{table*}[t]
\caption{Exercise A pooled out-of-fold results on the 712-compound development set.}
\label{tab:exercise-a}
\centering
\footnotesize
\begin{tabular}{@{}lccccc@{}}
\toprule
Architecture & AUROC & AUPRC & Balanced accuracy & MCC & Sensitivity / Specificity \\
\midrule
10q IQP--ZZ baseline & 0.7140 & 0.6151 & 0.6549 & 0.4000 & 0.3649 / 0.9449 \\
20q idle control & 0.7140 & 0.6151 & 0.6549 & 0.4000 & 0.3649 / 0.9449 \\
20q duplicate & 0.7271 & 0.6321 & 0.6583 & 0.4314 & 0.3514 / 0.9653 \\
20q complementary & 0.7288 & 0.6379 & 0.6696 & 0.4255 & 0.3964 / 0.9429 \\
\bottomrule
\end{tabular}
\end{table*}

\begin{figure}[t]
    \centering
    \includegraphics[width=\columnwidth]{exercise_a_pooled_mcc.png}
    \caption{Pooled MCC for the frozen 10-qubit baseline and the three Exercise A controls. The idle control overlaps the baseline exactly.}
    \label{fig:exercise-a-mcc}
\end{figure}

The paired cluster bootstrap tempers this apparent improvement. Duplicate minus baseline MCC was $0.0314$ with 95\% CI $[-0.0120,0.0696]$. Complementary minus baseline was $0.0255$ with CI $[0.0000,0.0606]$, touching zero at the reported precision. Complementary minus duplicate was $-0.0058$ with CI $[-0.0511,0.0478]$. Each active variant exceeded the baseline in three of five outer folds. These outcomes are consistent with a small architecture-dependent change, but not with a stable ordering.

The later external-panel extension did not validate a thresholded improvement. Baseline, idle, and duplicate variants produced AUROC 0.50 and AUPRC 0.393; the complementary variant produced AUROC 0.583 and AUPRC 0.643. All four nevertheless predicted zero of two positives at their frozen thresholds, giving sensitivity 0 and MCC 0. With only eight compounds, the rank-metric differences are too unstable for confirmatory inference.

Exercise A therefore supports a narrow conclusion: modifying the active feature encoding and ZZ interaction topology can modify the exact quantum Gram matrix and produce small development-set metric changes. It does not show that adding qubits alone is beneficial. The identity of the idle control demonstrates the opposite for unused qubits, while duplicate and complementary variants jointly change representation, active circuit width, and topology. Nor do these exactly simulated experiments establish runtime or predictive quantum advantage over classical computation.

\section{Limitations}

The study has five principal limitations. First, the dataset is small and imbalanced, and the complete upstream curation path from source records to the frozen 893-compound domain must be documented before submission. Second, the historical holdout is not pristine because it was examined in earlier project iterations. Third, the eight-compound challenge contains only two positives and supports case-level diagnosis, not a stable generalization estimate. Fourth, the compact ten-descriptor representation favors interpretability and exact simulation but may omit substructural or mechanistic information needed for difficult toxicants. Fifth, all quantum kernels were evaluated exactly and noiselessly on classical hardware. The work therefore addresses predictive geometry and experimental controls, not quantum hardware feasibility, noise robustness, scaling, or computational advantage.

Additional limitations apply to Exercise A. The active 20-qubit variants change encoding and interaction structure simultaneously; they are not a controlled estimate of a ``qubit-count effect.'' The exact transfer-matrix method also benefits from the chosen linear topology and does not imply efficient contraction for arbitrary deep or densely connected feature maps. Future studies should pre-register a larger external panel, isolate encoding and graph ablations, assess calibration and cost-sensitive thresholds, and compare against richer fingerprint and graph baselines under the same grouped protocol.

\section{Conclusion}

BeeQ provides a structure-aware evaluation of classical and exact quantum fidelity kernels for acute honey-bee toxicity prediction. On the frozen development campaign, random forest gave the highest mean nested AUROC, while product and IQP--ZZ quantum kernels were statistically indistinguishable from a matched RBF control. Randomization tests supported genuine predictive signal, but the historical holdout and the eight-compound challenge exposed weak sensitivity at frozen thresholds.

The 20-qubit Exercise A extension adds a useful diagnostic rather than a claim of advantage. Idle qubits left the kernel exactly unchanged; two active encodings produced modest development-set gains whose uncertainty intervals included or touched zero and whose sensitivity did not transfer to the small external panel. The defensible result is therefore that quantum-kernel behavior is tunable through encoding and topology. Establishing practical value will require stronger data provenance, larger prospective validation, more expressive classical controls, and hardware-aware experiments.

% Omit identifying acknowledgments during double-blind review.
% \section*{Acknowledgment}
% Restore funding, institutional, and contributor acknowledgments for camera ready.

\section*{Data and Code Availability}
\todo{Create the anonymized review artifact and replace ANONYMOUS\_ARTIFACT\_URL before submission.} The artifact will contain frozen configurations, hashes, source code, aggregate results, and permitted molecule-level evaluation files. Redistribution of underlying toxicity records and internal descriptors remains subject to their original terms; the artifact will therefore distinguish executable code from data that cannot be relicensed. The public repository URL and full provenance statement will be restored in the camera-ready version.

\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
```

## Nota de interpretación para conservar al editar

La frase central de Exercise A debe mantenerse cerca de esta forma: *the kernel is tunable through encoding and topology, but the experiment does not isolate a qubit-count effect and does not establish quantum advantage*. El control idle 20q es esencial porque demuestra que ampliar el registro sin activar esos qubits no cambia nada. Los otros dos casos sí cambian el kernel, pero también cambian simultáneamente la codificación y el grafo de interacciones.
