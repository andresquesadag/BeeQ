# Guía de la presentación BeeQ (español)

Tercera revisión, en cinco bloques. La misma presentación en inglés está en `output/beeq_conference_v3/`. Es una propuesta para revisión
del autor: no está publicada ni enviada a terceros.

## Cómo abrirla

Abra `index.html` con doble clic en cualquier navegador moderno. El archivo es
autocontenido: no carga fuentes, scripts ni imágenes externas, así que funciona
sin conexión y desde una memoria USB.

| Tecla | Acción |
|---|---|
| `→` `espacio` `AvPág` | Siguiente |
| `←` `RePág` | Anterior |
| `Inicio` / `Fin` | Primera / última |
| `N` | Notas del presentador (con tiempo objetivo y acumulado) |
| `F` | Pantalla completa |
| `P` | Imprimir o guardar como PDF |
| `T` | Cronómetro de ensayo (compara con los 13:10 previstos) |

La barra inferior tiene los mismos controles. La dirección lleva el número de
diapositiva (`index.html#10`), así que puede enlazar una concreta o recargar sin
perder el sitio.

**Para proyectar:** pulse `F`. La diapositiva se escala sola manteniendo 16:9;
está diseñada a 1600 × 900 y se adapta a cualquier resolución.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | La presentación. Autocontenida, ~178 KB, 16 diapositivas |
| `BeeQ_presentacion.pdf` | Exportación a PDF, 16 páginas en 16:9 |
| `NOTAS_PRESENTADOR.md` | Guion con tiempos, transiciones y preguntas probables |
| `VERIFICACION.md` | Registro de fuentes, trazabilidad y discrepancias |
| `GUIA.md` | Este documento |
| `build/` | Generadores: si cambia un dato, se regenera desde aquí |

La presentación inicial en `output/beeq_conference/` no se modificó.

## Estructura: cinco bloques

Dieciséis diapositivas. La barra superior muestra en qué bloque está, con el
ancho de cada segmento proporcional a su número de diapositivas. La diapositiva 2
es una agenda que anuncia los cinco bloques. El pie lleva siempre
«BeeQ · IEEE BIP 2026» y el número de diapositiva.

| # | Diapositiva | Bloque |
|---|---|---|
| 1 | Portada · título original del paper | — |
| 2 | Agenda · los cinco bloques | — |
| 3 | El problema: exposición, medición, priorización | **A · Contexto** |
| 4 | Pregunta de investigación y tubería igualada | **A · Contexto** |
| 5 | BeeQ893 y el endpoint | **B · Metodología** |
| 6 | Particiones por clúster y congelamiento | **B · Metodología** |
| 7 | De la molécula a X10 y al ángulo del qubit | **B · Metodología** |
| 8 | Qué es un kernel | **C · Implementación** |
| 9 | Codificación cuántica, fidelidad y alcance | **C · Implementación** |
| 10 | Desempeño entre familias de modelos | **D · Resultados** |
| 11 | Ordenar frente a detectar: el holdout | **D · Resultados** |
| 12 | CR8 y dominio de aplicabilidad | **D · Resultados** |
| 13 | Ethiprole y su vecino tóxico | **D · Resultados** |
| 14 | Conclusiones y límites, a dos columnas | **E · Conclusiones** |
| 15 | Trabajo futuro | **E · Conclusiones** |
| 16 | Datos, código y cierre | **E · Conclusiones** |

### Por qué el corte de bloques quedó así

«Metodología» agrupa el dato y cómo lo preparamos: el conjunto, las particiones y
la representación. «Implementación» agrupa lo que efectivamente se construyó y
corrió: el kernel y la codificación cuántica con su alcance de simulación. Si
prefiere que la codificación cuántica cuente como metodología, basta cambiar
`data-block="C"` por `"B"` en la diapositiva 9 de `build/template.html`.

### Cambios de esta revisión

- **Portada**: el titular es ahora el título original del paper, en inglés, por ser el título
  registrado de la publicación. Se eliminó el texto descriptivo y los autores pasaron al pie en
  tres columnas.
- **Agenda**: encabezado «Agenda», sin el titular «Cinco bloques», con los cinco bloques listados.
- **Contexto**: ilustración de abeja en SVG al pie, con el texto subido.
- **Pregunta**: cada familia de modelos lleva su color en el diagrama; el pie se redujo a
  «Esquema conceptual».
- **Datos**: se corrigió el recorte del gráfico, que ahora va al ras del margen izquierdo.
- **Particiones**: se quitaron las dos líneas de nota y el diagrama inferior bajó.
- **X10**: fichas en cuatro columnas, con la leyenda de valor / z / θ ocupando las dos celdas
  libres de la última fila; la columna izquierda queda sólo para la molécula.
- **Kernel y cuántico**: se corrigió el pie cortado de la matriz, se quitaron las marcas
  «Esquema conceptual» de cada figura y se dejó una sola etiqueta.
- **Pies de fuente** reducidos a la tabla exacta en todas las diapositivas.
- **Viñetas** con más separación en conclusiones y trabajo futuro.

### Cambios respecto de la primera versión

- De 18 a 16 diapositivas, reorganizadas en cinco bloques con agenda y pie fijo.
- **El MLP es ahora la variante balanceada y retuneada (B) en toda la charla**,
  de forma consistente. Afecta a las diapositivas 10, 11 y 12.
- La pregunta de investigación es ahora el titular de la diapositiva 4, con el
  texto exacto del paper, y se eliminó el texto accesorio.
- La tubería de la 4 arranca en ApisTox y añade la vía de los modelos clásicos
  junto a la de los kernels. El escalado se absorbió dentro de «preprocesamiento»
  para no multiplicar cajas.
- Las antiguas 7 y 8 se fusionaron en una sola diapositiva (la 6), que ahora va
  justo después del dato: arriba la composición de los folds, abajo el flujo de
  selección y congelamiento.
- La representación X10 se movió después de las particiones y ahora explica
  explícitamente qué son la z y el ángulo θ, con una leyenda junto a la molécula.
- Se eliminaron las diapositivas de comparación emparejada y de geometría de
  kernels. Sus cifras siguen disponibles en las notas y en el registro de
  verificación por si surgen en preguntas.
- La diapositiva de descriptores dejó de ser una justificación de X10 y pasó al
  trabajo futuro, donde sostiene el argumento del orden de los qubits.
- Conclusiones a dos columnas: hallazgos a la izquierda, «lo que este trabajo no
  muestra» a la derecha.
- El cierre se separó en dos: trabajo futuro (tres líneas) y una última
  diapositiva con datos, código y agradecimiento.
- Se eliminó el texto sobrante de las diapositivas 8, 9, 10, 11, 12 y 13, y se
  dio más tamaño a los gráficos y a las estructuras químicas.

## Decisiones visuales

**Una diapositiva, una idea.** Cada titular es una afirmación, no una etiqueta.
Si el público lee sólo los titulares, sigue la tesis.

**Composiciones variadas.** Agenda tipográfica (2), rejilla de tres columnas (3),
diagrama a ancho completo (4), gráfico dominante con comentario lateral
(5, 10, 11), dos gráficos apilados (6), fichas de datos (7), dos columnas
equilibradas (8, 12, 14, 15) y composición simétrica centrada (13).

**Color con significado, constante en toda la charla.** Verde azulado para lo
clásico (RBF), índigo para Product QK, violeta para IQP-ZZ, pizarra para los
modelos no kernel, rojo para tóxico/error/límite y ámbar para lo que se destaca.
Los mismos colores identifican a los mismos modelos en todos los gráficos.

**Tipografía.** Serif para los titulares —da el registro académico y los separa
del dato— y sans con cifras tabulares para todo lo numérico. Sólo fuentes del
sistema: nada que descargar, nada que falle en el portátil de la sala.

**Tamaños pensados para proyección.** Los titulares están entre 42 y 78 px sobre
un lienzo de 1600 × 900; el texto que el público debe leer no baja de ~25 px, y
las etiquetas de los gráficos se dimensionaron contando el factor de escala con
que cada gráfico se inserta en su columna.

**Honestidad gráfica.** Tres reglas aplicadas sin excepción:
1. Todo gráfico de datos lleva al pie la tabla exacta de la que sale.
2. Todo esquema conceptual lleva la marca «esquema conceptual» con línea
   discontinua, para que nunca se confunda con una medición.
3. Donde se muestran medias se muestran también los folds individuales y la
   dispersión, y se declara en pantalla que la barra es desviación estándar y no
   un intervalo de confianza.

**Los gráficos salen de los datos, no de las figuras del paper.** Cada uno se
genera desde las tablas del suplemento con un script. Las dos estructuras
químicas se dibujaron con RDKit desde los SMILES congelados.

**Qué se dejó fuera a propósito.** No hay animaciones ni transiciones: en una
charla de 15 minutos restan tiempo y se rompen al proyectar. No hay iconos
decorativos ni fotografías de abejas.

## Exportar a PDF

Ya hay un PDF generado: `BeeQ_presentacion.pdf`, 16 páginas, una por diapositiva,
en 16:9 y con los fondos de color.

Para regenerarlo desde el navegador: pulse `P`, elija «Guardar como PDF», sin
márgenes y **con** la opción de gráficos de fondo activada (si no, las cuatro
diapositivas oscuras salen en blanco). El PDF incluye las diapositivas, no las
notas: el guion está en `NOTAS_PRESENTADOR.md`.

## Regenerar la presentación

Los datos verificados viven en los scripts, no en el HTML a mano, para que
cualquier corrección se propague a los gráficos de forma reproducible.

```bash
python output/beeq_conference_v2/build/render_molecules.py
```

```bash
python output/beeq_conference_v2/build/make_charts.py
```

```bash
python output/beeq_conference_v2/build/assemble.py
```

Para la versión en inglés (`output/beeq_conference_v3/`):

```bash
python output/beeq_conference_v2/build/make_charts.py --lang=en
```

```bash
python output/beeq_conference_v2/build/assemble.py --lang=en
```

- `render_molecules.py` dibuja Ethiprole y fipronil con RDKit desde los SMILES de
  `data/official/`. Necesita el intérprete del proyecto (`.venv/Scripts/python.exe`).
- `make_charts.py` contiene las tablas verificadas, cada una con su fuente
  anotada, y produce los once gráficos SVG. Con `--lang=en` los escribe traducidos en
  `generated_en/`; la tabla de traducción `TR` está al inicio del archivo y también cambia la
  coma decimal por punto.
- `encoding_values.py` recalcula los valores estandarizados y los ángulos de la
  diapositiva 7 y los contrasta con la tabla S4.
- `assemble.py` incrusta todo en `index.html`.

Para cambiar texto o disposición edite `build/template.html` (español) o
`build/template_en.html` (inglés) y vuelva a ejecutar `assemble.py` con o sin `--lang=en`.
Los dos templates se editan por separado: comparten CSS y JavaScript, pero su prosa es
independiente. Para cambiar una cifra, edítela en `make_charts.py` junto a su
fuente y regenere: así el registro de verificación sigue siendo cierto.

## Pendientes para el autor

1. **Tabla II.** No se pudo sustentar con los artefactos conservados y por eso no
   aparece. Si localiza la campaña que la produjo, puede añadirse una diapositiva
   al bloque B. Detalle en `VERIFICACION.md`, discrepancia D-3.
2. **Coherencia del manuscrito con la charla.** La presentación usa el MLP
   balanceado B de forma consistente; el manuscrito todavía mezcla las dos
   variantes en un mismo párrafo. Las correcciones propuestas ya están redactadas
   en `docs/mlp_sensitivity/audit_20261105/CORRECTIONS_EN.md`.
3. **Idioma.** Está en español. Si la sesión es en inglés hay que traducir
   titulares, gráficos y notas; los textos de los gráficos están en
   `make_charts.py` y se regeneran.
4. **Autores y afiliaciones** de la portada: conviene confirmarlos y fijar el
   orden definitivo.
5. **Corte de bloques** entre Metodología e Implementación: ver la nota más
   arriba si prefiere mover la codificación cuántica al bloque B.
