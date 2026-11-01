# BeeQ: diagnóstico, validación y sensibilidad del MLP balanceado

Fecha de trabajo: 8 de octubre de 2026 (America/Costa_Rica). Los nombres de
artefactos usan UTC. Ejecución definitiva: `results/mlp_sensitivity/full_20261009_v2`.

## 1. Diagnóstico y evidencia

La implementación original omitió pesos; no se pudo establecer la intención de
los autores. El commit `5a410041c9807aa499e8cf3f64bd855f21d51558` introdujo
`MLPClassifier` con early stopping y sin ponderación. Su mensaje y diff no
explican la decisión. Los requisitos de ese commit y `01_CONFIG/ENVIRONMENT.json`
de la campaña final registran scikit-learn 1.9.0, que admite `fit(sample_weight)`.
No corresponde atribuir la ausencia a una restricción de esa versión.

Un notebook auxiliar no versionado prueba balanceo solamente si el constructor
expone `class_weight`. Confundir esa API con `sample_weight` es una hipótesis
plausible; no hay vínculo causal demostrado con el runner final. Se conserva su
hash y extracto en `AUXILIARY_EVIDENCE.json`. Véase
`docs/MLP_BALANCING_DIAGNOSIS.md` para el diagnóstico emitido antes de implementar.

LR usa `balanced`, RF `balanced_subsample` y los tres SVC (RBF, Product e IQP-ZZ)
usan `balanced`. El MLP no recibía pesos ni remuestreo. La procedencia de los
otros cinco modelos fue verificada: 51 artefactos de referencia y ocho fuentes
coinciden con sus hashes (normalizando únicamente CRLF/LF en fuentes), y 42
tablas por modelo/partición/fold concuerdan con sus predicciones. No se repitieron
esos modelos porque ninguna corrección modificó su entrenamiento.

Development: 712 moléculas, 490 negativas/222 tóxicas; holdout: 181, 132/49;
CR8: 8, 6/2. La AUROC original es 0.677099 +/- 0.124483 en los cinco folds;
0.667687 corresponde a OOF agrupado. El holdout confirma 0.462430. Las cifras
aproximadas aportadas por el usuario concuerdan con los resultados originales;
el PDF revisado no está disponible para comprobar todas sus referencias.

La reserva nativa de early stopping divide moléculas sin agrupar por cluster;
el escalador ya se ajustó cuando se crea esa reserva. Conservamos esta limitación
en ambas variantes. El runner histórico suprimía ConvergenceWarning, de modo que
sus registros no bastaban para evaluar convergencia.

## 2. Cambios, justificación y control experimental

- `src/mlp_sensitivity.py`: runner aditivo e inmutable, tres variantes claramente
  nombradas; usa las funciones y espacios originales sin modificar el pipeline
  compartido. `balanced_weights` calcula N/(2*n_c) exclusivamente con las
  etiquetas recibidas por el ajuste de entrenamiento. `checked_fit` pasa los
  pesos solamente a `model__sample_weight`, conserva el escalador sin pesos,
  registra la reserva nativa y captura todas las advertencias.
- `tests/test_mlp_sensitivity.py`: fórmula y masas de clase, separación de grupos,
  equivalencia de la búsqueda manual con GridSearchCV, aislamiento del escalador
  y repetición determinista de entrenamiento ponderado.
- `src/mlp_sensitivity_report.py`: auditoría independiente de artefactos, pesos,
  pertenencia a particiones, métricas y umbrales; genera este informe y material
  editorial a partir de resultados validados.
- `.gitattributes`: conserva los finales de línea históricos de cinco CSV de
  entrada y cinco artefactos anteriores. Git con core.autocrlf=true había cambiado
  sus bytes. Se restauró LF únicamente tras demostrar que el hash resultante
  coincidía exactamente con el manifiesto; no se cambió ninguna molécula, etiqueta,
  descriptor, partición ni cifra. Los artefactos históricos recuperaron su
  identidad original; sus manifiestos y modelos no se reescribieron.

**A, efecto directo:** los mismos hiperparámetros originales seleccionados para
cada fold y para el ajuste final, con las mismas particiones, semillas y escalado.
La diferencia deliberada es pasar los pesos al entrenamiento nativo. Los umbrales
se estiman de nuevo por variante, tal como exige el protocolo. **B, protocolo
completo:** 12 candidatos y el mismo presupuesto: 240 ajustes HPO anidados y 60
en selección final, para original y balanceado. A tiene 31 ajustes; cada búsqueda
completa, 331 incluyendo los ajustes posteriores a HPO.

La versión instalada admite ponderación desde la API oficial. El entrenamiento
pondera la entropía cruzada y sus gradientes; L2 se normaliza por la suma de pesos
del minibatch, no por su número de muestras. Los pesos suman N antes de la reserva
nativa; no necesariamente suman el tamaño de cada minibatch o subconjunto de
gradiente. Early stopping usa accuracy ponderada en su reserva con los mismos
pesos derivados del ajuste local. Por ello A controla la configuración pero no
aísla exclusivamente la pérdida de su interacción nativa con parada y L2. No se
modificaron librería, ReLU/Adam, arquitectura, optimizador, tolerancia, 10% de
reserva, batch_size='auto', max_iter=2000 ni paciencia de 10 iteraciones.

Las etiquetas de la reserva nativa forman parte del ajuste CV que define los
pesos; no entran etiquetas de la validación interna/externa, holdout o CR8. Esta
distinción es explícita y no equivale a una reserva de parada independiente.

## 3. Validación y estado final

- All production artifact hashes and sizes match.
- Development freeze remains unchanged after external evaluation.
- 693 fits: exact CV training membership, weights, local scalers, finite losses and no resampling.
- All 31 fixed-parameter balanced fits share parameters, seed, scaler and native stopping membership with controls.
- 5 outer, 20 inner and 5 final-selection splits are cluster disjoint.
- Both searches have identical 12-candidate budgets: 240 nested + 60 final HPO fits each.
- 18 threshold OOF pools have complete single coverage and reproduce MCC/BA/threshold tie rules.
- 2,136 nested OOF, 543 holdout and 24 CR8 predictions reproduce all metrics and decisions without evaluation weights.
- Historical holdout clusters and exact/canonical CR8 identities remain separate from Development.
- Independent complete rerun: all 18 CSV outputs match exactly.

La tolerancia 1e-10 se fijó antes de interpretar el balanceo: en el mismo entorno
y con las mismas semillas se espera coincidencia numérica; permite únicamente
redondeo de coma flotante, no discrepancias de selección o decisiones. La mayor
diferencia original de score fue 1.887e-15.
Parámetros y decisiones históricas coinciden; los umbrales difieren únicamente
por redondeo numérico. La suite completa termina con **19 tests aprobados**.

| variant | FITS | MIN_ITER | MAX_ITER | WARNINGS | STOPPING_CLUSTER_OVERLAP_MIN | STOPPING_CLUSTER_OVERLAP_MAX |
| --- | --- | --- | --- | --- | --- | --- |
| MLP_balanced_fixed | 31 | 14 | 52 | 0 | 15 | 32 |
| MLP_balanced_search | 331 | 12 | 77 | 0 | 14 | 32 |
| MLP_original | 331 | 12 | 62 | 0 | 14 | 32 |

Ningún ajuste alcanzó max_iter y no se registraron advertencias de entrenamiento.
Esto demuestra parada finita bajo la política configurada, no convergencia a un
óptimo global ni resolución del problema de la reserva por moléculas.

Las primeras pruebas pequeñas fallaron por verificación demasiado estricta de
finales de línea de fuentes, una columna de OOF mal nombrada en el nuevo auditor,
y los hashes de CSV convertidos por Git. Sus STATUS.json se conservaron. La
prueba `smoke_20261009_v4` completó las tres ramas con parámetros fijos del primer
fold. La primera ejecución completa guardó NaN para estadísticas de selección no
aplicables a A; se corrigió a null y se ejecutó un segundo análisis completo,
`full_20261009_v2`, con igualdad exacta de todos los CSV frente al anterior. Las
ejecuciones fallidas y la primera ejecución no son la entrega definitiva.

## 4. Resultados de Development

AUROC/AUPRC son media +/- desviación estándar muestral entre folds. BA, MCC,
sensibilidad, especificidad y confusión en esta tabla son OOF agrupados con los
umbrales estimados localmente; las medias/SD de las seis métricas se conservan
por separado en `NESTED_SUMMARY.csv`.

| Variant | AUROC mean +/- SD | AUPRC mean +/- SD | Pooled BA | Pooled MCC | Sensitivity | Specificity | TP | FN | TN | FP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLP_original | 0.6771 +/- 0.1245 | 0.5961 +/- 0.1383 | 0.6536 | 0.4283 | 0.3378 | 0.9694 | 75 | 147 | 475 | 15 |
| MLP_balanced_fixed | 0.6884 +/- 0.1005 | 0.6086 +/- 0.1186 | 0.6381 | 0.3442 | 0.3559 | 0.9204 | 79 | 143 | 451 | 39 |
| MLP_balanced_search | 0.6792 +/- 0.0997 | 0.5942 +/- 0.1119 | 0.6322 | 0.3376 | 0.3378 | 0.9265 | 75 | 147 | 454 | 36 |

Métricas y umbrales por fold:

| MODEL | OUTER_FOLD | NEGATIVE | POSITIVE | AUROC | AUPRC | BALANCED_ACCURACY | MCC | SENSITIVITY | SPECIFICITY | TP | FN | TN | FP | THRESHOLD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLP_original | 1 | 97 | 40 | 0.4889 | 0.4055 | 0.5845 | 0.2829 | 0.2000 | 0.9691 | 8 | 32 | 94 | 3 | 0.5240 |
| MLP_original | 2 | 68 | 37 | 0.6367 | 0.5206 | 0.6254 | 0.3252 | 0.3243 | 0.9265 | 12 | 25 | 63 | 5 | 0.5399 |
| MLP_original | 3 | 110 | 37 | 0.7921 | 0.6586 | 0.6576 | 0.4818 | 0.3243 | 0.9909 | 12 | 25 | 109 | 1 | 0.5206 |
| MLP_original | 4 | 122 | 59 | 0.6826 | 0.6281 | 0.6186 | 0.4164 | 0.2373 | 1.0000 | 14 | 45 | 122 | 0 | 0.5277 |
| MLP_original | 5 | 93 | 49 | 0.7852 | 0.7678 | 0.7637 | 0.5817 | 0.5918 | 0.9355 | 29 | 20 | 87 | 6 | 0.5134 |
| MLP_balanced_fixed | 1 | 97 | 40 | 0.5358 | 0.4504 | 0.5521 | 0.1131 | 0.3000 | 0.8041 | 12 | 28 | 78 | 19 | 0.5612 |
| MLP_balanced_fixed | 2 | 68 | 37 | 0.6455 | 0.5323 | 0.6389 | 0.3521 | 0.3514 | 0.9265 | 13 | 24 | 63 | 5 | 0.6362 |
| MLP_balanced_fixed | 3 | 110 | 37 | 0.7808 | 0.6308 | 0.5135 | 0.1427 | 0.0270 | 1.0000 | 1 | 36 | 110 | 0 | 0.6501 |
| MLP_balanced_fixed | 4 | 122 | 59 | 0.7134 | 0.6800 | 0.6619 | 0.4196 | 0.3729 | 0.9508 | 22 | 37 | 116 | 6 | 0.5556 |
| MLP_balanced_fixed | 5 | 93 | 49 | 0.7665 | 0.7493 | 0.7679 | 0.5663 | 0.6327 | 0.9032 | 31 | 18 | 84 | 9 | 0.5418 |
| MLP_balanced_search | 1 | 97 | 40 | 0.5358 | 0.4504 | 0.5521 | 0.1131 | 0.3000 | 0.8041 | 12 | 28 | 78 | 19 | 0.5612 |
| MLP_balanced_search | 2 | 68 | 37 | 0.6455 | 0.5323 | 0.6389 | 0.3521 | 0.3514 | 0.9265 | 13 | 24 | 63 | 5 | 0.6362 |
| MLP_balanced_search | 3 | 110 | 37 | 0.7808 | 0.6308 | 0.5135 | 0.1427 | 0.0270 | 1.0000 | 1 | 36 | 110 | 0 | 0.6503 |
| MLP_balanced_search | 4 | 122 | 59 | 0.6675 | 0.6080 | 0.6402 | 0.4105 | 0.3051 | 0.9754 | 18 | 41 | 119 | 3 | 0.5601 |
| MLP_balanced_search | 5 | 93 | 49 | 0.7665 | 0.7493 | 0.7679 | 0.5663 | 0.6327 | 0.9032 | 31 | 18 | 84 | 9 | 0.5418 |

Hiperparámetros seleccionados:

| MODEL | OUTER_FOLD | BEST_PARAMS | THRESHOLD |
| --- | --- | --- | --- |
| MLP_original | 1 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5240 |
| MLP_original | 2 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5399 |
| MLP_original | 3 | {"model__alpha": 0.001, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5206 |
| MLP_original | 4 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5277 |
| MLP_original | 5 | {"model__alpha": 0.0001, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5134 |
| MLP_balanced_fixed | 1 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5612 |
| MLP_balanced_fixed | 2 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.6362 |
| MLP_balanced_fixed | 3 | {"model__alpha": 0.001, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.6501 |
| MLP_balanced_fixed | 4 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5556 |
| MLP_balanced_fixed | 5 | {"model__alpha": 0.0001, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5418 |
| MLP_balanced_search | 1 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5612 |
| MLP_balanced_search | 2 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.6362 |
| MLP_balanced_search | 3 | {"model__alpha": 0.01, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.6503 |
| MLP_balanced_search | 4 | {"model__alpha": 0.0001, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.0003} | 0.5601 |
| MLP_balanced_search | 5 | {"model__alpha": 0.0001, "model__hidden_layer_sizes": [32, 16], "model__learning_rate_init": 0.001} | 0.5418 |

Diferencias emparejadas balanceado menos original:

| MODEL | OUTER_FOLD | AUROC | AUPRC | BALANCED_ACCURACY | MCC | SENSITIVITY | SPECIFICITY | TP | FN | TN | FP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLP_balanced_fixed | 1 | 0.0469 | 0.0449 | -0.0325 | -0.1697 | 0.1000 | -0.1649 | 4 | -4 | -16 | 16 |
| MLP_balanced_fixed | 2 | 0.0087 | 0.0117 | 0.0135 | 0.0269 | 0.0270 | 0.0000 | 1 | -1 | 0 | 0 |
| MLP_balanced_fixed | 3 | -0.0113 | -0.0278 | -0.1441 | -0.3391 | -0.2973 | 0.0091 | -11 | 11 | 1 | -1 |
| MLP_balanced_fixed | 4 | 0.0308 | 0.0518 | 0.0432 | 0.0032 | 0.1356 | -0.0492 | 8 | -8 | -6 | 6 |
| MLP_balanced_fixed | 5 | -0.0187 | -0.0185 | 0.0043 | -0.0153 | 0.0408 | -0.0323 | 2 | -2 | -3 | 3 |
| MLP_balanced_search | 1 | 0.0469 | 0.0449 | -0.0325 | -0.1697 | 0.1000 | -0.1649 | 4 | -4 | -16 | 16 |
| MLP_balanced_search | 2 | 0.0087 | 0.0117 | 0.0135 | 0.0269 | 0.0270 | 0.0000 | 1 | -1 | 0 | 0 |
| MLP_balanced_search | 3 | -0.0113 | -0.0278 | -0.1441 | -0.3391 | -0.2973 | 0.0091 | -11 | 11 | 1 | -1 |
| MLP_balanced_search | 4 | -0.0150 | -0.0202 | 0.0216 | -0.0058 | 0.0678 | -0.0246 | 4 | -4 | -3 | 3 |
| MLP_balanced_search | 5 | -0.0187 | -0.0185 | 0.0043 | -0.0153 | 0.0408 | -0.0323 | 2 | -2 | -3 | 3 |

| MODEL | AUROC | AUPRC | SENSITIVITY | SPECIFICITY |
| --- | --- | --- | --- | --- |
| MLP_balanced_fixed | 0.0113 | 0.0124 | 0.0012 | -0.0475 |
| MLP_balanced_search | 0.0021 | -0.0020 | -0.0123 | -0.0425 |

## 5. Holdout histórico y CR8 después de congelar Development

| MODEL | EVALUATION | N | NEGATIVE | POSITIVE | AUROC | AUPRC | BALANCED_ACCURACY | MCC | SENSITIVITY | SPECIFICITY | TP | FN | TN | FP | THRESHOLD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLP_original | historical_holdout | 181 | 132 | 49 | 0.4624 | 0.3024 | 0.5257 | 0.1110 | 0.0816 | 0.9697 | 4 | 45 | 128 | 4 | 0.5246 |
| MLP_balanced_fixed | historical_holdout | 181 | 132 | 49 | 0.4814 | 0.3321 | 0.5516 | 0.1288 | 0.2245 | 0.8788 | 11 | 38 | 116 | 16 | 0.5362 |
| MLP_balanced_search | historical_holdout | 181 | 132 | 49 | 0.4821 | 0.3290 | 0.5493 | 0.1110 | 0.2653 | 0.8333 | 13 | 36 | 110 | 22 | 0.5283 |
| MLP_original | CR8 | 8 | 6 | 2 | 0.8333 | 0.5833 | 0.4167 | -0.2182 | 0.0000 | 0.8333 | 0 | 2 | 5 | 1 | 0.5246 |
| MLP_balanced_fixed | CR8 | 8 | 6 | 2 | 0.6667 | 0.4500 | 0.5833 | 0.1491 | 0.5000 | 0.6667 | 1 | 1 | 4 | 2 | 0.5362 |
| MLP_balanced_search | CR8 | 8 | 6 | 2 | 0.5833 | 0.3667 | 0.5833 | 0.1491 | 0.5000 | 0.6667 | 1 | 1 | 4 | 2 | 0.5283 |

Configuraciones finales: original y A usan (32,16), alpha=0.01, learning_rate_init
=0.0003. B usa (32,16), alpha=0.001, learning_rate_init=0.001. Se seleccionan con
los cinco folds de Development; sus umbrales son 0.5245830869, 0.5362241016 y
0.5283342876. Son específicos de cada distribución de scores y no se optimizaron
con datos externos. Los resultados de la selección final tienen sesgo de selección
y no reemplazan la validación anidada.

Predicciones CR8 (1=tóxico):

| ID | name | LABEL | SCORE_MLP_balanced_fixed | SCORE_MLP_balanced_search | SCORE_MLP_original | PRED_MLP_balanced_fixed | PRED_MLP_balanced_search | PRED_MLP_original |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Isotianil | 0 | 0.4771 | 0.4802 | 0.4277 | 0.0000 | 0.0000 | 0.0000 |
| 2 | Fluoxapiprolin | 0 | 0.5734 | 0.5747 | 0.4872 | 1.0000 | 1.0000 | 0.0000 |
| 3 | Ethiprole | 1 | 0.5186 | 0.5204 | 0.4891 | 0.0000 | 0.0000 | 0.0000 |
| 4 | Cyclobutrifluram | 0 | 0.5200 | 0.5216 | 0.4708 | 0.0000 | 0.0000 | 0.0000 |
| 5 | Isoprothiolane | 0 | 0.4507 | 0.4536 | 0.3726 | 0.0000 | 0.0000 | 0.0000 |
| 6 | Isocycloseram | 1 | 0.5760 | 0.5730 | 0.5106 | 1.0000 | 1.0000 | 0.0000 |
| 7 | Spiropidion | 0 | 0.4658 | 0.4680 | 0.4151 | 0.0000 | 0.0000 | 0.0000 |
| 8 | Florylpicoxamid | 0 | 0.6453 | 0.6532 | 0.5353 | 1.0000 | 1.0000 | 1.0000 |

Isocycloseram pasa de falso negativo a verdadero positivo en ambas variantes.
Ethiprole continúa como falso negativo. Fluoxapiprolin se añade como falso
positivo y Florylpicoxamid sigue siendo falso positivo. Los otros cuatro
compuestos conservan la decisión negativa. Los IDs de CR8 son locales a ese
panel, no identificadores globales de las moléculas del corpus interno.

## 6. Estadística e impacto científico

| LEFT_MODEL | RIGHT_MODEL | METRIC | OBSERVED_DELTA | CI_LOW_95 | CI_HIGH_95 | BOOTSTRAP_MEDIAN | P_DELTA_GT_0 | REPLICATES | RESAMPLING_UNIT |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLP_balanced_fixed | MLP_original | AUROC | 0.0046 | -0.0242 | 0.0356 | 0.0047 | 0.6210 | 2000 | BUTINA_CLUSTER_ID |
| MLP_balanced_fixed | MLP_original | AUPRC | -0.0263 | -0.0735 | 0.0185 | -0.0256 | 0.1220 | 2000 | BUTINA_CLUSTER_ID |
| MLP_balanced_search | MLP_original | AUROC | -0.0063 | -0.0369 | 0.0258 | -0.0061 | 0.3510 | 2000 | BUTINA_CLUSTER_ID |
| MLP_balanced_search | MLP_original | AUPRC | -0.0474 | -0.0989 | -0.0009 | -0.0456 | 0.0220 | 2000 | BUTINA_CLUSTER_ID |
| random_forest | MLP_balanced_search | AUROC | 0.0952 | 0.0238 | 0.1714 | 0.0935 | 0.9965 | 2000 | BUTINA_CLUSTER_ID |
| random_forest | MLP_balanced_search | AUPRC | 0.1460 | 0.0733 | 0.2133 | 0.1413 | 1.0000 | 2000 | BUTINA_CLUSTER_ID |

Los intervalos son descriptivos sobre predicciones OOF agrupadas, con remuestreo
pareado de 374 clusters de Butina y 2.000 réplicas. No reentrenan modelos ni
incorporan incertidumbre de HPO; P_DELTA_GT_0 es una proporción bootstrap, no un
p-valor. Los cinco folds comparten entrenamiento y tampoco constituyen cinco
experimentos independientes. Scores de modelos distintos por fold pueden estar
calibrados de forma diferente; una media por fold y una AUROC/AUPRC agrupada
responden preguntas distintas.

1. **¿Por qué no estaba balanceado?** Se confirma la omisión de pesos en fit;
   el motivo autoral no está documentado. Restricción de la librería descartada
   para el entorno registrado; confusión entre APIs es una hipótesis limitada.
2. **¿Explica el desempeño inferior?** Explica parte de la baja recuperación
   retrospectiva de tóxicos al umbral en holdout, pero no resuelve la discriminación
   ni demuestra la causa del desempeño inferior frente a otras familias.
3. **¿Mejora sensibilidad consistentemente?** No: mejora en cuatro folds, pero
   en el tercero cae de 12/37 a 1/37. A recupera 4 tóxicos adicionales en OOF
   agrupado; B recupera el mismo total que el original. Holdout mejora en ambas.
4. **¿Discriminación o decisiones?** Principalmente decisiones. AUROC media
   cambia +0.0113 en A y +0.0021 en B. AUPRC agrupada empeora; holdout permanece
   por debajo de AUROC 0.5 pese a una pequeña mejora. CR8 empeora en AUROC/AUPRC.
5. **¿Especificidad y FP?** OOF: FP 15 -> 39/36; holdout: 4 -> 16/22. Mayor
   recuperación tiene un costo considerable en especificidad.
6. **¿Conclusiones centrales?** RF conserva la mayor AUROC media (0.748) y B
   queda por debajo de las otras cinco familias. La comparación Product/IQP-ZZ
   frente a RBF no cambia; no surge evidencia nueva de ventaja cuántica.
7. **¿Incertidumbres?** Intención autoral, variación entre semillas no estudiadas,
   parada temprana basada en moléculas y accuracy, calibración entre folds,
   incertidumbre de selección no capturada por bootstrap, holdout previamente
   observado y solo dos positivos en CR8. No debe generalizarse sensibilidad
   regional ni atribuir toda diferencia al gradiente de pérdida por separado.

## 7. Actualización editorial

Se entregan `MANUSCRIPT_REPLACEMENTS_EN.md`, `REVIEWER_RESPONSE_EN.md`, tablas
CSV y `MLP_BALANCING_SUPPLEMENT.tex`. El manuscrito activo revisado no está en el
checkout; no se reconstruyó sobre un borrador histórico incompleto. Las ubicaciones
se verificaron en `02ff85e:.tmp_paper/main.tex`: III-D/sec:models,
IV-A/sec:results-classical, IV-D/sec:results-ad y tab:model_performance. Ese borrador
denomina pooled OOF una tabla mixta de media/SD y métricas agrupadas, y redondea
0.124483 a 0.125. Los bloques corrigen ambas inconsistencias directamente
afectadas. Se conserva la fila original y se añaden A/B como análisis posteriores.

La figura adicional `results/mlp_sensitivity/full_20261009_v2/MLP_SENSITIVITY.png`
compara folds, discriminación y decisiones del holdout. Las figuras y tablas
históricas permanecen trazables. `EDITORIAL_QA.json` registra por separado el
resultado de compilación y la comprobación editorial; integración y compilación
del manuscrito revisado completo quedan pendientes de sus fuentes actuales.

## 8. Respuesta al revisor (English)

We thank the reviewer for identifying the unbalanced MLP baseline. We verified that the original implementation omitted sample weights; its recorded scikit-learn version supported weighting, and no documented rationale establishes why weights were omitted. We retained the original results and added two retrospective analyses: a paired comparison with the original hyperparameters fixed, and a fully retuned balanced MLP under the same 5-outer/4-inner cluster protocol and 12-candidate search. The original predictions were reproduced, and an independent complete rerun matched all tabular outputs. Development mean AUROC changed from 0.677 to 0.688 (fixed) and 0.679 (retuned), without consistent sensitivity improvement. On the historical holdout, toxic recovery increased from 4/49 to 11/49 and 13/49, but false positives increased from 4 to 16 and 22; AUROC remained 0.481-0.482. In CR8, one previously missed toxic compound was recovered, with an additional false positive and lower discrimination. We have supplied revised Methods and Results text and a supplementary analysis reporting weights, thresholds, selected parameters, convergence, paired differences and compound-level predictions. The original limitation and the retrospective nature of the external evaluations remain explicit; our central comparative conclusions are unchanged.

## 9. Reproducibilidad

```powershell
# Desde C:\Github_Repos\BeeQ; usar .venv, no el Python global 3.14.5.
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.mlp_sensitivity --smoke --output-dir results/mlp_sensitivity/NEW_SMOKE
.\.venv\Scripts\python.exe -m src.mlp_sensitivity --output-dir results/mlp_sensitivity/NEW_FULL --compare-to results/mlp_sensitivity/full_20261009_v2
.\.venv\Scripts\python.exe -m src.mlp_sensitivity_report --run results/mlp_sensitivity/NEW_FULL --output-dir docs/mlp_sensitivity
git diff --check
```

Las rutas de salida de ejecuciones deben ser nuevas. `PROVENANCE.json` registra
versiones, plataforma, comando, commit/dirty status, hashes de inputs y fuentes,
y hash del código instalado del MLP. Python 3.12.8, sklearn 1.9.0, NumPy 2.5.1,
pandas 2.3.3; semillas de modelo 20260824, internas 20260825-20260829,
bootstrap 20260824. `CONFIG.json`, `SPLIT_MEMBERSHIP.csv`, `HPO_CANDIDATES.csv`,
`THRESHOLD_OOF_PREDICTIONS.csv`, `FIT_AUDIT.json`, los tres .pkl portables,
`DEVELOPMENT_FREEZE.json` y `MANIFEST_SHA256.csv` contienen la evidencia completa.
Los pesos finales son 712/(2*490)=0.7265306122 y
712/(2*222)=1.6036036036; cada partición tiene sus propios pesos.

Los modelos finales solo reciben X10 después del freeze. La verificación inicial
leyó predicciones históricas para comprobar procedencia, lo que se registra de
forma explícita. Ni el freeze nuevo ni la ausencia de lectura temprana de los
CSV externos convierten esta extensión en una evaluación ciega.

## 10. Pendientes y problemas fuera de alcance

No quedan ajustes, predicciones o comprobaciones numéricas del análisis A/B
pendientes. Falta integrar los bloques en la fuente exacta del manuscrito revisado
y compilar ese proyecto completo; el suplemento independiente sí dispone de
fuente y se valida por separado. La causa autoral sigue sin poder determinarse.
No se realizaron nuevos análisis de semillas, arquitecturas ni cambios de parada.
Las inconsistencias de representación y otros placeholders del borrador histórico
no se corrigieron porque ese borrador no es la fuente revisada y exceden el alcance.
