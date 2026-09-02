# BeeQ Exercise A — baseline 10q frente a expansión 20q

## Alcance y protocolo

Se ejecutó exclusivamente el Ejercicio A. Se usaron las 712 moléculas de desarrollo, los cinco `STRICT_CV_FOLD`, cuatro folds internos `StratifiedGroupKFold`, escalado train-only, SVC precomputed con `class_weight="balanced"`, selección por AUROC inner y threshold inner-OOF por MCC. La simulación fue exacta, sin shots, ruido ni hardware cuántico. No se consultó el historical holdout ni CR8 y no se usaron papers externos.

El backend final contrajo exactamente la cadena IQP-ZZ como una función de partición de Ising compleja. No es una aproximación. La materialización 20q tiene dimensión 1,048,576, usa 16.0 MiB por statevector y proyectaría 9.48 GiB para el outer-train máximo; por eso se seleccionó la contracción exacta.

## Reproducción 10q

La reproducción cotejó 712 predicciones. Parámetros y clases coinciden exactamente: True / True. Error máximo de score: 4.441e-16; error máximo de threshold: 6.939e-17. Resultado: PASS.

## Resultados pooled OOF

| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. | TP | TN | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quantum_iqp_zz_linear | 0.4000 | 0.7140 | 0.6151 | 0.6549 | 0.3649 | 0.9449 | 81 | 463 | 27 | 141 |
| iqp_zz_current_20q_idle_control | 0.4000 | 0.7140 | 0.6151 | 0.6549 | 0.3649 | 0.9449 | 81 | 463 | 27 | 141 |
| iqp_zz_current_20q_duplicate | 0.4314 | 0.7271 | 0.6321 | 0.6583 | 0.3514 | 0.9653 | 78 | 473 | 17 | 144 |
| iqp_zz_current_20q_complementary_signed_sqrt | 0.4255 | 0.7288 | 0.6379 | 0.6696 | 0.3964 | 0.9429 | 88 | 462 | 28 | 134 |


## Deltas MCC pareados por cluster

- 20q idle − 10q: delta 0.0000, IC95% [0.0000, 0.0000].
- 20q duplicate − 10q: delta 0.0314, mediana bootstrap 0.0318, IC95% [-0.0120, 0.0696], P(delta>0)=0.935.
- 20q complementary − 10q: delta 0.0255, mediana bootstrap 0.0243, IC95% [0.0000, 0.0606], P(delta>0)=0.974.
- 20q complementary − duplicate: delta -0.0058, mediana bootstrap -0.0068, IC95% [-0.0511, 0.0478], P(delta>0)=0.391.

Duplicate supera al baseline en 3/5 folds; complementary lo supera en 3/5 folds.

## Respuestas científicas

- **¿Mejora duplicate frente a 10q?** Sí en el estimador puntual. El IC incluye cero y no respalda una mejora positiva robusta.
- **¿Mejora complementary frente a 10q?** Sí en el estimador puntual. El IC incluye cero y no respalda una mejora positiva robusta.
- **Consistencia:** los conteos outer son 3/5 (duplicate) y 3/5 (complementary); esto determina si la dirección fue homogénea.
- **Redundancia frente a codificación:** idle demuestra que qubits sin información no cambian el kernel. Duplicate mezcla redundancia con una topología de 19 aristas y términos intra-variable; complementary cambia además la función de codificación. El delta complementary−duplicate aísla operativamente esa codificación bajo la misma topología, no un efecto causal universal del número de qubits.
- **Qué no puede inferirse:** no hay evidencia de ventaja cuántica, rendimiento en holdout/CR8, generalización a otras transformaciones, superioridad causada solo por “20 qubits”, ni confirmación externa.

## Referencias contextuales congeladas (no usadas para seleccionar 20q)

- random_forest: MCC 0.4680, AUROC 0.7565.
- quantum_angle_product: MCC 0.3966, AUROC 0.7171.
- rbf_matched: MCC 0.4055, AUROC 0.7154.

## Artefactos y reproducibilidad

Los CSV son la fuente canónica. `EXERCISE_A_SUMMARY.xlsx` es un resumen navegable. Los checkpoints atómicos por outer fold permiten `--resume`. `07_MANIFEST/ARTIFACT_MANIFEST_SHA256.csv` registra hashes físicos y, para texto, hashes canónicos LF. La configuración, ambiente, Git, tiempos, memoria, warnings y reglas de desempate están auditados en las carpetas numeradas.

## Implementación, ejecución y pruebas

Se añadió `src/exercise_a_campaign.py` con el backend exacto de contracción, nested CV, checkpoints atómicos, comparación congelada, QC, bootstrap, figuras, provenance y manifest; y `tests/test_exercise_a_campaign.py` con cinco pruebas nuevas. Se ejecutaron reproducción 10q, equivalencia idle, benchmark materializado 20q, nested CV de duplicate/complementary, 2,000 réplicas bootstrap y una reanudación real desde checkpoints. El Ejercicio B no se ejecutó.

- Pruebas específicas: 5 passed, 0 failed.
- Suite completa existente: 18 passed, 2 failed. Ambos fallos son de auditabilidad por hashes físicos CRLF en Windows (`test_versioned_input_hashes` y `test_retained_campaign_manifests`). Los cinco inputs y los tres artefactos históricos afectados coinciden exactamente con los hashes esperados al canonicalizar a LF. No se modificaron expectativas históricas.
- `git diff --check`: pass.
- Estado final previsto: campaña, `src/exercise_a_campaign.py` y `tests/test_exercise_a_campaign.py` sin seguimiento; no hubo commit, push, pull, reset, checkout ni cambio de rama.

<!-- CR8_EXTENSION_START -->
## Extensión posterior — evaluación externa CR8

Esta sección se añadió sin repetir la nested CV de A. Cada arquitectura se seleccionó nuevamente usando exclusivamente las 712 moléculas de desarrollo y los cinco folds congelados; scaler, escala, C y threshold se congelaron antes de evaluar una sola vez las 8 moléculas CR8 (6 negativas, 2 positivas). CR8 no intervino en selección.

| Modelo | MCC | AUROC | AUPRC | Bal. acc. | Sens. | Esp. | TP | TN | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quantum_iqp_zz_linear | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 | 0 | 6 | 0 | 2 |
| iqp_zz_current_20q_idle_control | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 | 0 | 6 | 0 | 2 |
| iqp_zz_current_20q_duplicate | 0.0000 | 0.5000 | 0.3929 | 0.5000 | 0.0000 | 1.0000 | 0 | 6 | 0 | 2 |
| iqp_zz_current_20q_complementary_signed_sqrt | 0.0000 | 0.5833 | 0.6429 | 0.5000 | 0.0000 | 1.0000 | 0 | 6 | 0 | 2 |

Con solo 8 observaciones y 2 positivos, estas métricas tienen resolución muy baja y deben interpretarse como validación externa descriptiva, no como evidencia confirmatoria ni como base para retuning.
<!-- CR8_EXTENSION_END -->

## Verificación final posterior a la extensión

Las 11 pruebas específicas de A, CR8 y B pasan. La suite completa reporta 24
passes y 2 fallos históricos de hashes físicos; ambos se explican enteramente por
CRLF frente a LF canónico. No se alteraron expectativas, datasets ni artefactos
retenidos. El detalle está en `00_AUDIT/FINAL_TEST_RESULTS.md`.
