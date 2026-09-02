# BeeQ Exercise B — pairwise ZZ y construcción de caminos

## Alcance

Se ejecutó exclusivamente el Ejercicio B como campaña separada. Los 45 pares no dirigidos se cribaron dentro del entrenamiento de cada outer fold. Los labels de outer-validation no se usaron para seleccionar aristas, caminos, escalas, C ni thresholds. La simulación fue exacta, sin shots, ruido ni hardware cuántico. No se consultaron los papers excluidos ni el historical holdout.

## Pares principales

### Mayor MCC pairwise inner-OOF

- MolLogP__n_OP: 0.5214
- MolWt__n_OP: 0.5071
- nHalogen__n_OP: 0.4985
- NumHDonors__n_OP: 0.4922
- n_OP__sasa002_frac_polar_hetero_only: 0.4885

### Mayor delta atribuible a ZZ

- MolLogP__n_OP: +0.0479
- MolLogP__MolWt: +0.0213
- NumAromaticRings__LiPHEX_prediction: +0.0190
- LiPHEX_prediction__sasa002_frac_polar_hetero_only: +0.0189
- NumAromaticRings__sasa002_frac_polar_hetero_only: +0.0180

### Mayor estabilidad

- MolLogP__n_OP: stable score +0.0062; 8/20 deltas positivos
- MolLogP__NumRotatableBonds: stable score -0.0110; 13/20 deltas positivos
- LiPHEX_prediction__sasa002_frac_polar_hetero_only: stable score -0.0138; 13/20 deltas positivos
- NumRotatableBonds__LiPHEX_prediction: stable score -0.0214; 9/20 deltas positivos
- MolLogP__LiPHEX_prediction: stable score -0.0136; 10/20 deltas positivos

Pares que sobrevivieron Holm a 0.05: **0/45**. El ranking pairwise sigue siendo exploratorio y sujeto a winner's curse.

## Caminos por outer fold

| Fold | Tipo | Orden | Puntaje |
|---:|---|---|---:|
| 1 | current_order | MolLogP → MolWt → TPSA_SP → NumHDonors → NumRotatableBonds → NumAromaticRings → nHalogen → n_OP → LiPHEX_prediction → sasa002_frac_polar_hetero_only | -0.0513 |
| 1 | max_synergy_path | MolLogP → n_OP → LiPHEX_prediction → NumRotatableBonds → sasa002_frac_polar_hetero_only → nHalogen → TPSA_SP → MolWt → NumHDonors → NumAromaticRings | 0.2159 |
| 1 | stable_synergy_path | NumAromaticRings → NumHDonors → MolWt → LiPHEX_prediction → n_OP → MolLogP → TPSA_SP → NumRotatableBonds → sasa002_frac_polar_hetero_only → nHalogen | 0.0349 |
| 2 | current_order | MolLogP → MolWt → TPSA_SP → NumHDonors → NumRotatableBonds → NumAromaticRings → nHalogen → n_OP → LiPHEX_prediction → sasa002_frac_polar_hetero_only | -0.0806 |
| 2 | max_synergy_path | NumHDonors → nHalogen → MolWt → n_OP → MolLogP → NumRotatableBonds → LiPHEX_prediction → NumAromaticRings → sasa002_frac_polar_hetero_only → TPSA_SP | 0.3584 |
| 2 | stable_synergy_path | NumAromaticRings → NumRotatableBonds → LiPHEX_prediction → nHalogen → NumHDonors → MolWt → MolLogP → n_OP → sasa002_frac_polar_hetero_only → TPSA_SP | 0.0332 |
| 3 | current_order | MolLogP → MolWt → TPSA_SP → NumHDonors → NumRotatableBonds → NumAromaticRings → nHalogen → n_OP → LiPHEX_prediction → sasa002_frac_polar_hetero_only | 0.1435 |
| 3 | max_synergy_path | TPSA_SP → MolWt → MolLogP → NumHDonors → n_OP → NumRotatableBonds → NumAromaticRings → LiPHEX_prediction → sasa002_frac_polar_hetero_only → nHalogen | 0.3646 |
| 3 | stable_synergy_path | LiPHEX_prediction → MolLogP → TPSA_SP → NumRotatableBonds → n_OP → NumHDonors → NumAromaticRings → MolWt → nHalogen → sasa002_frac_polar_hetero_only | 0.0295 |
| 4 | current_order | MolLogP → MolWt → TPSA_SP → NumHDonors → NumRotatableBonds → NumAromaticRings → nHalogen → n_OP → LiPHEX_prediction → sasa002_frac_polar_hetero_only | 0.0449 |
| 4 | max_synergy_path | NumAromaticRings → MolWt → NumHDonors → nHalogen → n_OP → TPSA_SP → NumRotatableBonds → MolLogP → LiPHEX_prediction → sasa002_frac_polar_hetero_only | 0.1505 |
| 4 | stable_synergy_path | NumRotatableBonds → NumAromaticRings → NumHDonors → MolLogP → LiPHEX_prediction → sasa002_frac_polar_hetero_only → MolWt → n_OP → nHalogen → TPSA_SP | 0.0210 |
| 5 | current_order | MolLogP → MolWt → TPSA_SP → NumHDonors → NumRotatableBonds → NumAromaticRings → nHalogen → n_OP → LiPHEX_prediction → sasa002_frac_polar_hetero_only | 0.0592 |
| 5 | max_synergy_path | LiPHEX_prediction → NumRotatableBonds → TPSA_SP → NumAromaticRings → nHalogen → MolLogP → n_OP → NumHDonors → sasa002_frac_polar_hetero_only → MolWt | 0.3490 |
| 5 | stable_synergy_path | LiPHEX_prediction → sasa002_frac_polar_hetero_only → MolWt → n_OP → MolLogP → NumHDonors → NumRotatableBonds → nHalogen → NumAromaticRings → TPSA_SP | 0.0277 |

Número de órdenes distintos por tipo: {"current_order": 1, "max_synergy_path": 5, "stable_synergy_path": 5}.

## Circuitos completos pooled OOF

| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. |
|---|---:|---:|---:|---:|---:|---:|
| current_order_10q | 0.4000 | 0.7140 | 0.6151 | 0.6549 | 0.3649 | 0.9449 |
| max_synergy_path_10q | 0.3884 | 0.7183 | 0.6206 | 0.6543 | 0.3739 | 0.9347 |
| stable_synergy_path_10q | 0.4256 | 0.7158 | 0.6115 | 0.6622 | 0.3694 | 0.9551 |
| current_order_20q_duplicate | 0.4314 | 0.7271 | 0.6321 | 0.6583 | 0.3514 | 0.9653 |
| current_order_20q_complementary | 0.4255 | 0.7288 | 0.6379 | 0.6696 | 0.3964 | 0.9429 |
| max_synergy_path_20q_duplicate | 0.3360 | 0.6922 | 0.5953 | 0.6349 | 0.3514 | 0.9184 |
| max_synergy_path_20q_complementary | 0.4295 | 0.7283 | 0.6366 | 0.6694 | 0.3919 | 0.9469 |
| stable_synergy_path_20q_duplicate | 0.4263 | 0.7296 | 0.6356 | 0.6585 | 0.3559 | 0.9612 |
| stable_synergy_path_20q_complementary | 0.4217 | 0.7287 | 0.6371 | 0.6698 | 0.4009 | 0.9388 |

## Deltas primarios MCC

- max_synergy_path_10q − current_order_10q: -0.0116, IC95% [-0.0297, 0.0053], P(delta>0)=0.095.
- stable_synergy_path_10q − current_order_10q: +0.0256, IC95% [0.0077, 0.0484], P(delta>0)=0.997.
- max_synergy_path_20q_duplicate − current_order_20q_duplicate: -0.0954, IC95% [-0.1682, -0.0262], P(delta>0)=0.001.
- max_synergy_path_20q_complementary − current_order_20q_complementary: +0.0040, IC95% [-0.0014, 0.0135], P(delta>0)=0.726.
- stable_synergy_path_20q_duplicate − current_order_20q_duplicate: -0.0050, IC95% [-0.0242, 0.0161], P(delta>0)=0.286.
- stable_synergy_path_20q_complementary − current_order_20q_complementary: -0.0038, IC95% [-0.0187, 0.0091], P(delta>0)=0.280.

Random Forest congelado conserva MCC 0.4680; mejor arquitectura seleccionada de B: 0.4295. Random Forest continúa por encima.

## Y-randomization

Se ejecutaron 5 permutaciones completas del cribado y reconstrucción de camino. La distribución nula del mejor MCC pairwise y del mejor puntaje de camino está en `09_Y_RANDOMIZATION/Y_RANDOMIZATION_RESULTS.csv`. El número final fue fijado tras benchmark y está documentado en configuración/provenance.

La ampliación posterior está parametrizada mediante `--y-replicates`. La guía
`09_Y_RANDOMIZATION/RESUME_TO_200.md` contiene el comando exacto para reanudar
esta misma campaña con un objetivo total de 200; los cinco checkpoints existentes
se reutilizan y solo se calculan las 195 repeticiones faltantes.

## Evaluación externa CR8 al final

CR8 contiene 8 moléculas (6 negativas, 2 positivas). Todos los caminos finales, escalas, C y thresholds se congelaron usando solo desarrollo antes de evaluar CR8; CR8 no participó en selección.

| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. |
|---|---:|---:|---:|---:|---:|---:|
| current_order_10q | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 |
| max_synergy_path_10q | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 |
| stable_synergy_path_10q | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 |
| current_order_20q_duplicate | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 |
| current_order_20q_complementary | 0.0000 | 0.5833 | 0.6429 | 0.5000 | 0.0000 | 1.0000 |
| max_synergy_path_20q_duplicate | 0.3333 | 0.5000 | 0.3929 | 0.6667 | 0.5000 | 0.8333 |
| max_synergy_path_20q_complementary | 0.0000 | 0.5833 | 0.6429 | 0.5000 | 0.0000 | 1.0000 |
| stable_synergy_path_20q_duplicate | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 |
| stable_synergy_path_20q_complementary | 0.0000 | 0.5833 | 0.6429 | 0.5000 | 0.0000 | 1.0000 |

## Interpretación

Los resultados outer de circuitos completos evalúan confirmatoriamente el algoritmo de selección predefinido; los rankings y outer pairwise individuales son exploratorios. Cambios fuertes de aristas/caminos entre folds indican inestabilidad de selección y posible winner's curse. Ningún resultado demuestra ventaja cuántica. CR8 es demasiado pequeño para conclusiones firmes y no autoriza ajustes post hoc.

Los CSV son la fuente canónica; `PAIRWISE_SUMMARY.xlsx` es un resumen navegable. Los checkpoints atómicos por outer fold y permutación permiten reanudar la campaña.

## Verificación final

Las 11 pruebas específicas de A, CR8 y B pasan. La suite completa reporta 24
passes y 2 fallos históricos de hashes físicos; ambos se explican enteramente por
CRLF frente a LF canónico. No se alteraron expectativas, datasets ni artefactos
retenidos. El detalle está en `00_AUDIT/FINAL_TEST_RESULTS.md`.
