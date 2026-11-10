# BeeQ: presentación de conferencia

Abra `index.html` en un navegador moderno. Use las flechas del teclado o los botones para avanzar y retroceder, N para mostrar las notas del presentador y F para pantalla completa. La impresión del navegador incluye todas las diapositivas y permite guardar un PDF.

## Evidencia y límites

- El paper facilitado, páginas 1–7, contiene los datos, la validación, la tabla I y los análisis de kernels y CR8. La gráfica de la diapositiva 6 reproduce las medias y desviaciones estándar de su tabla I. Las barras representan desviación estándar entre cinco folds, no intervalos de confianza.
- `results/campaigns/BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z/BEEQ_FINAL_CAMPAIGN_SUMMARY.md` registra 712 moléculas de desarrollo, 181 de holdout y ocho de CR8. En el holdout, Random Forest presenta 13 verdaderos positivos, 36 falsos negativos y cuatro falsos positivos.
- `results/mlp_sensitivity/full_20261009_v2/EXTERNAL_METRICS.csv` registra para el MLP original AUROC 0,4624 y para el MLP balanceado con búsqueda AUROC 0,4821 en el holdout. El paper combina en el texto AUROC 0,462 con AUPRC 0,329 y 13 detecciones y 22 falsas alarmas, valores estos últimos de la variante balanceada. La diapositiva evita reportar ese AUROC externo dudoso.
- El paper indica para CR8 que el MLP balanceado detectó Isocycloseram, mientras que la campaña original registra que ningún modelo detectó ninguno de los dos positivos. Se identifican las versiones en las notas.
- El paper describe seis representaciones adicionales en la tabla II; el suplemento adjunto parece reflejar una etapa distinta. No se incluye esa comparación como resultado principal hasta confirmar sus archivos y procedencia.
- Las matrices de la diapositiva 7 son esquemas conceptuales expresamente etiquetados, no visualizaciones de matrices medidas.
- Las propuestas futuras son hipótesis de trabajo, no experimentos presentados como ya completados.
