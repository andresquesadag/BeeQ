# Registro de fuentes y verificación

Presentación: `output/beeq_conference_v2/index.html` (16 diapositivas, cinco bloques).
Última verificación: 6 de noviembre de 2026.

Este registro relaciona cada cifra y afirmación relevante de la presentación con
su fuente, y deja constancia de las discrepancias que **no** pudieron resolverse
con los archivos disponibles.

> **Cambio respecto de la versión anterior de la presentación.** Por decisión del
> autor, **toda la charla usa ahora el MLP balanceado y retuneado (variante B)**,
> de forma consistente en las diapositivas 10, 11 y 12. La versión anterior usaba
> el MLP original sin ponderación. Las consecuencias están en la sección D-1.

> **Nota sobre los pies de figura.** En esta revisión los pies en pantalla se
> abreviaron a la tabla exacta (por ejemplo «Tabla S18 del suplemento»). La
> trazabilidad completa de cada cifra sigue estando en este documento, que es el
> registro de referencia. Ninguna cifra cambió.
>
> **Versión en inglés.** `output/beeq_conference_v3/` contiene la misma
> presentación traducida. Comparte los generadores y, por tanto, exactamente los
> mismos datos verificados; sólo cambian el idioma y la coma decimal por punto.

## 1. Jerarquía de fuentes adoptada

| Prioridad | Fuente | Uso |
|---|---|---|
| 1 | Campaña congelada `BEEQ_FINAL_NESTED_STRUCT_IMPL_20260827T144143Z` y las tablas del suplemento que la leen | Métricas de LR, RF, RBF, Product QK e IQP-ZZ QK; geometría; dominio de aplicabilidad |
| 2 | `results/mlp_sensitivity/full_20261009_v2/` | **Todas** las cifras del MLP (variante balanceada B) |
| 3 | `docs/mlp_sensitivity/audit_20261105/` | Auditoría independiente que re-puntúa los modelos guardados y confirma 1 y 2 |
| 4 | CSV congelados en `data/official/` (hashes SHA-256 verificados en tabla S32) | Valores por molécula: SMILES, X10, etiquetas |
| 5 | Paper principal | Narrativa y definiciones; no se usa como fuente numérica cuando contradice a 1–3 |

Abreviaturas: `[TI]` tabla I del paper (= tabla S15 del suplemento); `[Sn]` tabla
n del suplemento; `[§]` sección del paper; `[MLP-B]`
`results/mlp_sensitivity/full_20261009_v2/`; `[AUD]` `docs/mlp_sensitivity/audit_20261105/`.

## 2. Trazabilidad por diapositiva

### D3 · Contexto
Sin cifras. El encuadre —polinizador clave, ensayo in vivo como estándar, NAM
como apoyo a la priorización— procede de `[§ I]` y de las referencias [6] y [14]
del paper. La diapositiva declara explícitamente que BeeQ es exploratorio y no un
criterio de decisión regulatoria.

### D4 · Pregunta de investigación y tubería
El titular es la pregunta del paper, traducida sin ampliar ni debilitar su
alcance (`[§ I]`, último párrafo de la introducción). La tubería refleja
`[§ II.C–II.E]`: ApisTox → curación y escalado por partición → folds disjuntos
por clúster → dos vías (modelos clásicos LR/RF/MLP, y los tres kernels con SVC de
kernel precomputado) → métricas comunes. Marcada en pantalla como esquema
conceptual. La nota «RBF igualado no implica igualar el ancho de banda» proviene
de `[§ II.D]`.

### D5 · Datos y endpoint
| Cifra | Valor | Fuente |
|---|---|---|
| BeeQ893 | 893 = 622 no tóxicas + 271 tóxicas | `[S1]`, `[§ II.A]` |
| Development | 712 = 490 / 222 · 374 clústeres | `[S1]` |
| Holdout histórico | 181 = 132 / 49 · 88 clústeres | `[S1]` |
| CR8 | 8 = 6 / 2, sin ID de clúster | `[S1]` |
| Punto de partida | 1 035 compuestos de ApisTox | `[S1 A]`, `[§ II.A]` |
| Endpoint | LD₅₀ ≤ 11 µg/abeja ⇒ clase 1; fijado antes de modelar | `[§ II.A]`, `[S1 B]` |

Límites declarados en las notas, no en pantalla: las 142 exclusiones no tienen
registro por operación reconstruible `[S1 A]`; la etiqueta agrega la vía de
exposición más severa `[§ II.A]`.

### D6 · Particiones y congelamiento
| Afirmación | Fuente |
|---|---|
| Morgan radio 2, 1 024 bits, con quiralidad; Tanimoto | `[§ II.C]`, `[S3 A]` |
| Butina con corte 0,60 sobre d = 1 − T | `[§ II.C]`, `[S3 A]` |
| 462 clústeres, 334 singletons, mayor de 40 | `[§ II.C]`, `[S3 A]` |
| Composición de los cinco folds y cero clústeres compartidos | `[S9]` |
| 4 divisiones internas StratifiedGroupKFold, selección por AUROC medio interno | `[§ II.C]`, `[S3 B]` |
| Umbral: máx. MCC, desempate por BA, luego \|t\|, luego t | `[§ II.D]`, `[S3 B]` ec. S5 |
| Refit único sobre 712; manifiesto escrito antes de abrir lo externo | `[S3 B]` |
| Holdout «histórico» por inspección exploratoria previa | `[§ II.C]`, `[S1 B]` |

### D7 · Molécula → X10 → ángulo de qubit
Valores crudos de Ethiprole tomados textualmente de
`data/official/ExternalFinal_RDKitFixed.csv`. La estandarización se calculó sobre
las 712 filas de `data/official/train_RDKitFixed.csv` con la convención de
`StandardScaler` (desviación poblacional, ec. S3). Script reproducible:
`build/encoding_values.py`.

| qb | Descriptor | Crudo | z | θ = 0,25·z |
|---|---|---|---|---|
| 1 | logP | 3,7793 | +0,44 | +0,109 |
| 2 | MW | 397,209 | +0,77 | +0,193 |
| 3 | TPSA | 90,69 | +0,37 | +0,092 |
| 4 | HBD | 1 | +0,12 | +0,031 |
| 5 | RotB | 3 | −0,52 | −0,130 |
| 6 | ArR | 2 | +0,78 | +0,195 |
| 7 | nHal | 5 | +1,94 | +0,486 |
| 8 | nOP | 0 | −0,36 | −0,090 |
| 9 | LiPHEX | −1,9154 | −1,62 | −0,406 |
| 10 | fSASA | 0,1900 | +0,27 | +0,067 |

Comprobación cruzada: las medias y desviaciones calculadas coinciden con `[S4]`
(p. ej. logP 2,9626 / 1,8734 calculada frente a 2,963 / 1,875 publicada; la
diferencia es desviación poblacional frente a muestral). Orden de descriptores y
asignación de qubits: `[S3]`. Escala s = 0,25: selección congelada en `[S14]`.

### D8–D9 · Kernels y codificación cuántica
| Afirmación | Fuente |
|---|---|
| K_RBF(z,z′) = exp(−γ‖z−z′‖²) | `[S4 A]` ec. S8 |
| SVC con kernel precomputado, pesos balanceados | `[§ II.D]`, `[S4 A]` |
| Fidelidad K_Q = \|⟨ψ(z)\|ψ(z′)⟩\|² | `[S4 B]` ec. S10 |
| Product: diez RY(s·z), sin entrelazamiento | `[S4 C]` ec. S11 |
| IQP-ZZ: H + RZ + cadena RZZ de vecinos, λ = 1, una repetición, sin Hadamard final | `[S4 D]` ecs. S15–S16 |
| Escalas seleccionadas: Product s = 0,25; IQP-ZZ s = 0,125 | `[S14]` |
| Statevector exacto en NumPy, 1 024 amplitudes, sin disparos, ruido ni hardware | `[S4 E]` |
| Qiskit presente en el entorno pero no ejecutó la campaña | `[S4 E]` |

### D10 · Desempeño en Development
AUROC por fold de `[S17]`; medias y DE de `[TI]` = `[S15]`; cruces de holdout de
`[S18]`. **La fila del MLP procede de `[MLP-B]`** (`NESTED_SUMMARY.csv`,
`EXTERNAL_METRICS.csv`), confirmada por `[AUD]`.

| Modelo | Media ± DE | Holdout |
|---|---|---|
| Random Forest | 0,7480 ± 0,0574 | 0,6926 |
| Regresión logística | 0,7328 ± 0,1039 | 0,6848 |
| Product QK | 0,7216 ± 0,1075 | 0,6974 |
| IQP-ZZ QK | 0,7130 ± 0,1056 | 0,6962 |
| RBF igualado | 0,7106 ± 0,1084 | 0,7058 |
| **MLP balanceado (B)** | **0,6792 ± 0,0997** | **0,4821** |

AUROC por fold del MLP balanceado: 0,535825 · 0,645469 · 0,780835 · 0,667547 ·
0,766513 (`[AUD]`, bloque «Figure 2 and main table»).

La barra mostrada es **desviación estándar entre folds**, rotulada en pantalla
como «no es un intervalo de confianza», conforme a `[§ III.A]` y `[S6 A]`.

### D11 · Holdout histórico
Cifras de `[S18]` para las cinco familias congeladas y de `[MLP-B]` para el MLP.

| Modelo | AUROC | Sens. | TP | FN | FP | Espec. |
|---|---|---|---|---|---|---|
| Random Forest | 0,6926 | 0,2653 | 13 | 36 | 4 | 0,9697 |
| Regresión logística | 0,6848 | 0,1633 | 8 | 41 | 7 | 0,9470 |
| Product QK | 0,6974 | 0,0816 | 4 | 45 | 2 | 0,9848 |
| IQP-ZZ QK | 0,6962 | 0,0816 | 4 | 45 | 3 | 0,9773 |
| RBF igualado | 0,7058 | 0,1020 | 5 | 44 | 2 | 0,9848 |
| **MLP balanceado (B)** | **0,4821** | **0,2653** | **13** | **36** | **22** | **0,8333** |

Rangos resultantes, mostrados en las notas: sensibilidad **0,082–0,265**,
especificidad **0,833–0,985**, entre 36 y 45 falsos negativos de 49. Con esta
alineación los tres rangos **coinciden exactamente** con los publicados en el
resumen y en `[§ III.B]` del paper.

### D12 · CR8 y dominio de aplicabilidad
| Afirmación | Fuente |
|---|---|
| Dominio dual y coordenadas de los ocho compuestos | `[S26]` |
| Cortes S = 0,223134 (P05) y d = 2,198975 (P95), derivados sólo de Development | `[S9 A]`, `[§ II.E]` |
| 7 de 8 dentro de ambos dominios; Fluoxapiprolin IN/OUT | `[S26]` |
| Decisiones de LR, RF, RBF, Product, IQP-ZZ | `[S27]` |
| **Decisiones del MLP (columna balanceada)** | **`docs/mlp_sensitivity/CR8_COMPOUND_TABLE.csv`, confirmado por `[AUD]`** |
| Spearman ρ = −0,31 entre los dos ejes | `[§ III.E]` |
| Sin solapamiento con BeeQ893/ApisTox (SMILES canónico + InChIKey) | `[§ II.E]`, `[S1 B]` |

Matriz mostrada: todos los modelos predicen clase 0 en los ocho compuestos,
**salvo** el MLP balanceado, que predice clase 1 para Isocycloseram (acierto),
Fluoxapiprolin (falso positivo) y Florylpicoxamid (falso positivo). Recuento del
MLP balanceado en CR8: TP 1, TN 4, FP 2, FN 1.

### D13 · Soporte químico local
| Afirmación | Fuente |
|---|---|
| Vecino estructural más cercano de Ethiprole: ID 387, fipronil, T = 0,7400, clase 1 | `[S29]`, `[S30]` |
| Soporte estructural máximo de Isocycloseram: 0,2326 | `[S26]`, `[S30]` |
| LD₅₀ de ambos muy por debajo de 11 µg/abeja | `[§ III.E]` y refs. [26], [27] del paper |
| Ethiprole mal clasificado por los seis modelos | `[S27]` + `[MLP-B]` (ambas variantes del MLP lo fallan) |

Las dos estructuras se dibujaron con RDKit 2026.03.5 desde los SMILES congelados
(`build/render_molecules.py`); no se copiaron de ninguna figura publicada.

### D14 · Conclusiones
Los CKA citados en las notas (0,982 y 0,985 frente al RBF; 0,9995 entre los dos
cuánticos) proceden de `[S22]`. El rango de sensibilidad 0,082–0,265, de la tabla
de D11.

### D15 · Trabajo futuro
Las tres líneas se corresponden con `[§ IV]` («extending encoding-scale
optimization, training embedding parameters through kernel-target alignment, and
evaluating projected kernels»). La tercera —reorganizar y ampliar los qubits— es
una extensión propuesta por el autor para esta charla; se apoya en un hecho
documentado, que la cadena RZZ de IQP-ZZ sólo acopla qubits vecinos `[S4 D]`, y
en que el orden de los descriptores fija la asignación de qubits `[S3]`. Se
presenta como línea de trabajo, no como resultado.

El gráfico es el AUROC univariado sin orientación de `[S5]`, rotulado en pantalla
como descriptivo y declarando que no fue criterio de selección, tal como indica
la propia tabla.

## 3. Discrepancias

### D-1 · El paper mezcla dos variantes del MLP · **resuelta; la charla adopta la variante B**

La campaña congelada registra un solo MLP, **sin ponderación de clases**. El
re-análisis `[MLP-B]` añade dos variantes balanceadas. Las cifras del paper
provienen de ambas fuentes a la vez:

| Pasaje del paper | Valor publicado | Corresponde a |
|---|---|---|
| Tabla I, fila MLP | 0,679 ± 0,100 · AUPRC 0,594 ± 0,112 · BA 0,632 · MCC 0,338 | **balanceado B** (0,6792 ± 0,0997 · 0,5942 ± 0,1119 · 0,6322 · 0,3376) |
| Resumen y § III.B: «AUROC … 0,462 (MLP)» | 0,462 | **original sin ponderar** (0,4624) |
| § III.B: «su AUPRC disminuyó a 0,329» | 0,329 | **balanceado B** (0,3290) |
| § III.B: «identificó 13 de los 49 … y produjo 22 falsos positivos» | 13 / 22 | **balanceado B** |
| § III.B: «especificidad entre 0,833 y 0,985» | 0,833 | **balanceado B** (0,8333) |

**Decisión adoptada.** La presentación usa la variante **balanceada B** en todas
las diapositivas, rotulada «MLP balanceado». Con ese criterio, cuatro de los
cinco pasajes del paper quedan reproducidos exactamente, y el único que no
—el AUROC de holdout 0,462 del resumen— corresponde al MLP original, que la
charla no muestra.

**Pendiente en el manuscrito.** El texto sigue combinando ambas variantes en un
mismo párrafo. Las correcciones ya están redactadas en
`docs/mlp_sensitivity/audit_20261105/CORRECTIONS_EN.md`, que propone exactamente
este criterio: rotular la fila del MLP de la tabla I y de la figura 2 como la
variante balanceada y retuneada, y conservar la original como línea base
separada, sustituyendo además el rango del resumen por «0,482 … a 0,706».

#### Corroboración independiente

La auditoría `[AUD]` re-puntuó los modelos guardados sin reajustar ninguno
(`model_fits_performed: 0`, error máximo de re-puntuación ~1e-16) y verificó 6
filas de métricas externas, 15 de folds externos y 32 archivos del manifiesto.
Sus valores recalculados coinciden **exactamente** con los usados aquí:

| | Auditoría | Usado en la presentación |
|---|---|---|
| MLP balanceado B · Development | 0,679238 ± 0,099729 | idéntico |
| MLP balanceado B · holdout | AUROC 0,482066 · AP 0,329039 · TP 13 · FP 22 · FN 36 | idéntico |
| MLP balanceado B · CR8 | TP 1 · TN 4 · FP 2 · FN 1 | idéntico |
| MLP original · holdout (no mostrado) | AUROC 0,462430 · TP 4 · FP 4 · FN 45 | sólo citado en este registro |

### D-2 · CR8: Isocycloseram · **resuelta**

| | Campaña congelada `[S27]`, `[S28]` | Variante balanceada B (mostrada) |
|---|---|---|
| Ethiprole | clase 0 en los seis modelos | clase 0 (falso negativo) |
| Isocycloseram | clase 0 en los seis modelos | **clase 1 (acierto)** |
| Falsos positivos del MLP | sólo Florylpicoxamid | Fluoxapiprolin **y** Florylpicoxamid |
| Recuento del MLP | TP 0, FP 1, FN 2 | TP 1, FP 2, FN 1 |

Con la variante B, la afirmación del paper —«cinco modelos clasificaron mal
Isocycloseram; el MLP lo identificó correctamente», con falsos positivos en
Fluoxapiprolin y Florylpicoxamid— queda reproducida exactamente. La diapositiva
12 muestra esa matriz y la nota al pie la rotula como «MLP balanceado».

### D-3 · Tabla II (seis representaciones alternativas) · **no verificable, excluida**

La tabla II del paper compara X10 con WL-OA (0,805 ± 0,073), ECFP (0,787 ± 0,091),
RDKit2D (0,784 ± 0,064), Mordred (0,755 ± 0,103), conteos atómicos (0,748 ± 0,068)
y MACCS (0,732 ± 0,104), afirmando recálculo sobre BeeQ893 con el mismo protocolo
anidado. No fue posible sustentarla:

1. El suplemento **no** contiene esa comparación. `[S10 A]` documenta un tamizaje
   exploratorio **distinto** (X5, X7, FREE20, X10 sin HBD, X10 frente a X9) y
   advierte que esos valores «pertenecen al pre-tamizaje exploratorio … y no
   sustituyen los resultados anidados congelados».
2. `[S11]` declara expresamente que «ablaciones predictivas de descriptores
   emparejadas … no estaban disponibles para esta evaluación».
3. Búsqueda en el repositorio: los valores 0,805 / 0,787 / 0,784 no aparecen en
   ningún archivo de `results/`, `docs/` ni `manuscript/`.
4. `manuscript/final_revision/audit/PUBLISHED_APISTOX_CONTEXT.csv` contiene las
   cifras **publicadas** del benchmark ApisTox (WL-OA SVM MaxMin 0,8395; ECFP RF
   0,7166 MaxMin / 0,7816 temporal …), que **no** coinciden con la tabla II.

**Decisión.** La tabla II no se presenta. La justificación de X10 descansa en el
argumento documentado (un descriptor, un qubit) y, en la diapositiva 15, en
asociaciones univariadas rotuladas como descriptivas.

### D-4 · Menor: columnas de la tabla S2 en la extracción de texto
Al extraer texto del PDF del suplemento, la tabla S2 desalinea la columna CAS. El
CSV congelado da Isocycloseram CAS 2061933-85-3 y Ethiprole 181587-01-9. La
presentación no muestra números CAS, así que no afecta a ninguna afirmación.

## 4. Afirmaciones deliberadamente no hechas

La presentación **no** afirma, en pantalla ni en notas: ventaja cuántica;
desempeño en hardware cuántico real o bajo ruido; utilidad clínica o regulatoria;
equivalencia matemática entre los tres kernels; generalización más allá de X10,
estos mapas fijos y este protocolo; que la pertenencia al dominio de
aplicabilidad garantice una clasificación correcta; ni que las desviaciones entre
folds sean intervalos de confianza. La diapositiva 14 dedica una columna entera a
«lo que este trabajo no muestra».

## 5. Límites que el propio suplemento declara y que la presentación respeta

- El holdout es **histórico**: fue inspeccionado en etapas exploratorias previas
  `[S1 B]`. Se declara en las notas de la D6 y de la D11.
- CR8 tiene **ocho compuestos y dos positivos**: cambiar una decisión mueve la
  sensibilidad en 0,5 `[S9 B]`. Se declara en las notas de la D12.
- La disjunción por clúster **no** es una garantía formal de fuera de distribución
  `[S3 A]`. Se declara en las notas de la D6.
- Un CKA alto **no** implica entradas, espectros ni decisiones idénticas `[S8]`.
- El procedimiento upstream de generación de fSASA no es reproducible desde los
  artefactos conservados `[S2 A]`. No se afirma lo contrario en la D7.
- La parada temprana nativa del MLP usa una reserva aleatoria **no** agrupada por
  clúster, en ambas variantes `[S4 A]`, `[MLP-B]`. No se menciona en pantalla.
- Las evaluaciones externas de las variantes balanceadas son **retrospectivas**:
  un congelamiento dentro de ese reanálisis no deshace la observación previa de
  los resultados externos originales (`[AUD]`, Methods II-D propuesto).
- El cuaderno de ejecución completa fechado 2026-08-31 difiere de la campaña
  congelada del 2026-08-27 en el cuarto decimal de algunos resultados cuánticos
  `[S1 C]`. La presentación usa exclusivamente la campaña congelada.

## 6. Comprobaciones que no pudieron realizarse

- No se verificaron visualmente las figuras 1 a 4 del paper: el texto extraído del
  PDF conserva los rótulos pero no permite comparar las posiciones graficadas.
  Todos los gráficos de la presentación se construyeron desde las **tablas**.
- No se re-ejecutó ningún modelo. Las métricas se leyeron de los artefactos
  conservados, igual que hacen el suplemento y la auditoría `[AUD]`.
- El PDF exportado se verificó estructuralmente (16 páginas, una por diapositiva,
  proporción 16:9, fondos de color presentes en las cuatro diapositivas oscuras),
  pero no se inspeccionó página por página de forma visual.
