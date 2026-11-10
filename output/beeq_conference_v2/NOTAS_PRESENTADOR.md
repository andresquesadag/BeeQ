# Notas del presentador · BeeQ · IEEE BIP 2026

Duración prevista del contenido: **13:10**, sobre una ranura de 15 minutos.
Quedan ~1:50 de margen. Las mismas notas están dentro de la presentación: se
abren con **N** y muestran el tiempo objetivo y el acumulado de cada diapositiva.

## Presupuesto por bloque

| Bloque | Diapositivas | Tiempo | Acumulado |
|---|---|---|---|
| Portada y agenda | 1–2 | 0:45 | 0:45 |
| **A · Contexto** | 3–4 | 1:40 | 2:25 |
| **B · Metodología** | 5–7 | 2:50 | 5:15 |
| **C · Implementación** | 8–9 | 1:55 | 7:10 |
| **D · Resultados** | 10–13 | 3:50 | 11:00 |
| **E · Conclusiones** | 14–16 | 2:10 | 13:10 |

**Si va retrasado**, comprima en este orden: la 8 (si el público ya conoce
kernels), la 13 (el caso Ethiprole se puede contar en dos frases) y la 2 (lea la
agenda de corrido). **No** comprima la 11 ni la 14: son el resultado práctico y
los límites.

---

## 1 · Portada — 0:20 · acum. 0:20
Buenos días. Voy a contarles un experimento de control: tomamos un problema real
de toxicología computacional y preguntamos si un kernel cuántico compara moléculas
de forma distinta a un kernel clásico, cuando todo lo demás se mantiene fijo.

> **Transición:** «Este es el recorrido.»

## 2 · Agenda — 0:25 · acum. 0:45
Cinco bloques. Contexto y pregunta; metodología, que es el dato y cómo lo
preparamos; implementación, que es el kernel y la codificación cuántica;
resultados; y conclusiones con el trabajo futuro. La barra de arriba indica en
todo momento en qué bloque estamos.

> **Transición:** «Empecemos por el porqué.»

## 3 · Contexto — 0:40 · acum. 1:25
Las abejas son polinizadores importantes y están expuestas a ingredientes activos
agrícolas. El estándar para medir toxicidad aguda es un ensayo in vivo que da la
LD₅₀ por abeja: confiable, pero lento, caro y con uso de animales.

La idea del tercer paso es la que da sentido al proyecto: no se trata de llevar
todas las moléculas al laboratorio, sino de tener una comparativa previa que diga
cuáles tienen más probabilidad de ser tóxicas y merecen el ensayo. Priorizar, no
reemplazar.

> **Transición:** «Dentro de ese marco, nuestra pregunta es metodológica.»

## 4 · Pregunta de investigación — 1:00 · acum. 2:25
La pregunta es literalmente la del paper, en pantalla. Un kernel cuántico
codifica descriptores en estados cuánticos y usa la fidelidad entre esos estados
como medida de semejanza. Eso cambia qué tan parecidas se consideran dos
moléculas, pero el clasificador puede seguir siendo clásico.

Huang y colaboradores mostraron que la diferencia geométrica entre kernels
clásicos y cuánticos es el factor clave para que su comportamiento predictivo
pueda diferir. Además, los kernels de fidelidad pueden concentrarse
exponencialmente. Así que la pregunta es empírica.

**La tubería.** Partimos de ApisTox, pasamos por curación y preprocesamiento,
separamos por clústeres moleculares, y ahí se abren dos vías: los modelos
clásicos de referencia —regresión logística, Random Forest y MLP— y los tres
kernels con un mismo SVC. Todo converge a las mismas métricas.

Lo importante es que todo está fijo salvo la caja ámbar. Por eso podemos atribuir
cualquier diferencia al kernel. Un matiz: «RBF igualado» no significa igualar el
ancho de banda.

> **Transición:** «Veamos el dato de partida.»

## 5 · BeeQ893 y el endpoint — 0:50 · acum. 3:15
Partimos de ApisTox, que integra datos curados de ECOTOX, PPDB y BPDB, con 1 035
compuestos. Tras una etapa adicional de curación y estandarización estructural
—exclusión de estructuras metálicas, tratamiento de sales y estados de carga con
RDKit— quedan 893 moléculas orgánicas: 622 no tóxicas y 271 tóxicas.

Esas 893 se reparten en Development, 712 moléculas, y un holdout histórico de
181. Aparte está CR8, un panel externo de ocho ingredientes activos aprobados en
Costa Rica.

El endpoint es binario: tóxica si la LD₅₀ es igual o menor que 11 microgramos por
abeja. Ese umbral viene de ApisTox y de la guía de la EPA, se fijó antes de
modelar y no se optimizó.

*Si preguntan:* de las 142 moléculas excluidas no se puede reconstruir el
registro operación por operación; y la etiqueta agrega la vía de exposición más
severa disponible, así que no es un protocolo homogéneo.

> **Transición:** «Ahora, cómo se separan para evaluar de forma justa.»

## 6 · Particiones y congelamiento — 0:55 · acum. 4:10
El riesgo central en evaluación molecular es la fuga por semejanza: si una
molécula de evaluación tiene un pariente casi idéntico en entrenamiento, el
modelo parece mejor de lo que es.

Por eso agrupamos primero. Huella Morgan de radio 2 y 1 024 bits con quiralidad,
similitud Tanimoto, y agrupamiento Butina con corte 0,60. Resultan 462 clústeres,
334 de un solo compuesto y el mayor de 40. Los clústeres completos se asignan de
forma disjunta.

Arriba ven la composición de los cinco folds externos congelados y la auditoría:
cero clústeres compartidos a ambos lados de cada fold. Fíjense en la
heterogeneidad —el fold 4 valida 181 moléculas con 59 tóxicas; el fold 2 sólo 105
con 37—: eso explicará buena parte de la dispersión que veremos después.

Abajo, el flujo de selección y congelamiento. Dentro del entrenamiento de cada
fold externo, cuatro divisiones internas agrupadas por clúster eligen
hiperparámetros por AUROC medio interno y el umbral por máximo MCC. Después, un
refit único sobre las 712 y se congela todo. El manifiesto se escribe antes de
abrir el holdout y CR8, que se evalúan una sola vez.

*Matiz:* el holdout es «histórico», fue inspeccionado en etapas exploratorias
previas. Y la disjunción por clúster no es una garantía formal de fuera de
distribución.

> **Transición:** «¿Y cómo describimos cada molécula?»

## 7 · De la molécula a X10 — 1:05 · acum. 5:15
Todos los modelos reciben el mismo vector ordenado de diez dimensiones, X10. Aquí
lo construimos con una molécula concreta, Ethiprole, del panel externo.

Tres pasos. Primero se calculan los diez descriptores fisicoquímicos y
estructurales sobre la estructura: ese es el valor grande en cada ficha. Segundo,
se estandariza: se le resta la media y se divide por la desviación del conjunto
de entrenamiento correspondiente, nunca con datos de evaluación; eso es la z.
Tercero, y esto es lo que conecta con la parte cuántica: ese valor estandarizado
se multiplica por la escala s, que vale 0,25, y da el ángulo theta con el que se
rota un qubit.

Un descriptor, un qubit. El orden de los descriptores fija qué qubit recibe cuál;
por eso cada ficha lleva su número arriba a la derecha. Esa decisión vuelve a
aparecer en el trabajo futuro.

Vean que nHal da el ángulo más grande: Ethiprole tiene cinco halógenos frente a
una media de 1,25. LiPHEX da el más negativo.

La analogía útil es la ficha técnica de una casa: metros cuadrados, cuartos, año.
Permite comparar casas, pero nadie diría que reconstruye la casa.

> **Transición:** «Con la molécula ya en números, pasemos a los modelos.»

## 8 · Qué es un kernel — 0:40 · acum. 5:55
Para quienes no trabajan con esto: un kernel es una función que, dadas dos
moléculas, devuelve un número que dice qué tan parecidas son. Si lo hacemos para
todos los pares, obtenemos una tabla cuadrada, la matriz de Gram.

La referencia clásica es el RBF, que decae exponencialmente con la distancia al
cuadrado entre los descriptores estandarizados. El parámetro gamma dice qué tan
rápido decae, es decir, qué tan exigente es el concepto de «parecido».

Lo clave: el clasificador no cambia. Un SVC recibe la tabla ya calculada y
aprende la frontera. Cambiar de kernel cambia la geometría de semejanza, no la
máquina que decide. Por eso podemos aislar el efecto del kernel.

> **Transición:** «Y aquí entra la parte cuántica.»

## 9 · Codificación cuántica y fidelidad — 1:15 · acum. 7:10
Tomamos el descriptor estandarizado y lo convertimos en un ángulo. En la esfera
de Bloch, un qubit que empieza en el polo |0⟩ se inclina un ángulo theta igual a
s por z. Con diez descriptores, diez qubits.

El mapa Product hace exactamente eso: diez rotaciones RY independientes, sin
ninguna operación de entrelazamiento. El mapa IQP-ZZ parte de una superposición
uniforme con Hadamards, aplica una capa de fases RZ y luego fases RZZ entre
qubits vecinos en cadena, con fuerza de interacción fija en uno y una sola
repetición. No hay capa final de Hadamard.

Fíjense en ese detalle de la cadena: sólo se acoplan qubits vecinos. Volveremos a
él al final.

La semejanza entre dos moléculas es la fidelidad entre sus estados: el módulo
cuadrado del producto interno. Está entre cero y uno, y vale uno cuando los
estados coinciden.

**El alcance, que conviene decir antes de cualquier resultado:** todo se simuló
con estados vectoriales exactos en NumPy, 1 024 amplitudes por molécula, sin
muestreo de disparos, sin modelo de ruido y sin ejecución en hardware. Qiskit
aparece en el entorno pero no ejecutó la campaña reportada. Esto no es un
benchmark de hardware.

> **Transición:** «Veamos qué pasó al medir.»

## 10 · Desempeño — 1:10 · acum. 8:20
Primero, qué es AUROC, porque todo lo demás depende de entenderlo: la
probabilidad de que una molécula tóxica elegida al azar reciba una puntuación
mayor que una no tóxica elegida al azar. Mide **capacidad de ordenar**, no
porcentaje de aciertos.

Random Forest obtuvo la media más alta, 0,748 ± 0,057. Luego regresión logística
con 0,733. Los tres kernels quedaron muy juntos: Product 0,722, IQP-ZZ 0,713 y
RBF igualado 0,711. El MLP balanceado, 0,679.

**Lo que quiero que vean es la dispersión, no el orden.** Cada círculo abierto es
un fold. Las desviaciones de los kernels rondan 0,106 a 0,108, mientras que las
diferencias entre sus medias son de una o dos milésimas. El fold 1 hunde a todos
los kernels por debajo de 0,57; el fold 5 los sube por encima de 0,79. Recuerden
la composición de los folds: no son intercambiables.

Las cruces son el holdout histórico, como referencia.

Que Random Forest vaya bien es compatible con relaciones no lineales en X10; que
la logística sea competitiva sugiere que buena parte de la señal la captura un
modelo lineal simple.

*Si preguntan por la comparación emparejada:* las diferencias por fold entre
Product y RBF, y entre IQP-ZZ y RBF, son de +0,011 y +0,002 de media, no
mantienen dirección entre folds, y en el holdout cambian de signo. El bootstrap
emparejado por clúster incluye el cero en los tres contrastes.

> **Transición:** «Pero todo esto es capacidad de ordenar. ¿Y detectar?»

## 11 · Ordenar frente a detectar — 1:00 · acum. 9:20
**La distinción que más importa para un toxicólogo.** Una decisión regulatoria
necesita un umbral y una respuesta binaria. Y ahí el panorama cambia.

En el holdout de 181 moléculas —49 tóxicas y 132 no tóxicas— cinco de los seis
modelos mantienen AUROC entre 0,68 y 0,71, parecido a Development. El RBF
igualado incluso sube a 0,706.

**Pero con los umbrales congelados la sensibilidad se desploma:** entre 0,082 y
0,265. El mejor caso es Random Forest: detecta 13 de 49 y deja pasar 36. Product
e IQP-ZZ detectan cuatro cada uno. La especificidad es alta, entre 0,833 y 0,985.

Dicho de otra forma: ordenan razonablemente, pero en el punto de operación
elegido funcionan como filtros muy conservadores que casi no levantan alarmas.
Para priorización eso es un problema serio, porque el falso negativo es el error
costoso.

*Sobre el MLP:* el que muestro es la variante balanceada y retuneada. Detecta 13
de 49 como Random Forest, pero a costa de 22 falsos positivos y de una AUROC de
0,482, por debajo del azar.

> **Transición:** «¿Y si la molécula se parece a lo que el modelo ya vio?»

## 12 · CR8 y dominio de aplicabilidad — 0:55 · acum. 10:15
CR8 son ocho ingredientes activos aprobados en Costa Rica bajo el decreto 43838,
sin solapamiento con BeeQ893 ni con ApisTox, verificado por SMILES canónico e
InChIKey completo.

El dominio se define con dos criterios derivados sólo de Development. Eje
horizontal: soporte estructural, máxima similitud Morgan/Tanimoto, corte en el
percentil 5, que es 0,223. Eje vertical: soporte en descriptores, distancia media
a los cinco vecinos en X10 estandarizado, corte en el percentil 95, que es 2,199.
Ninguno se optimizó según desempeño.

Siete de los ocho caen dentro de ambos dominios; el único fuera es
Fluoxapiprolin, por distancia en descriptores.

**Y aquí está el punto:** los dos compuestos tóxicos, Ethiprole e Isocycloseram,
están dentro de ambos dominios. Ethiprole fue clasificado como no tóxico por los
seis modelos, e Isocycloseram por cinco: el MLP balanceado sí lo detectó, pero a
cambio produjo dos falsos positivos, Fluoxapiprolin y Florylpicoxamid. La
pertenencia formal al dominio mide proximidad a Development; no garantiza una
clasificación correcta.

*Con ocho compuestos y dos positivos, cambiar una decisión mueve la sensibilidad
medio punto. Son observaciones por molécula, no conclusiones poblacionales. Los
dos ejes se asocian débilmente, Spearman −0,31.*

> **Transición:** «Miremos de cerca el caso de Ethiprole.»

## 13 · Ethiprole y su vecino — 0:45 · acum. 11:00
Para mí es el resultado más instructivo. El vecino más cercano de Ethiprole en
Development es fipronil, con similitud Tanimoto 0,740. Son estructuras claramente
emparentadas: el mismo núcleo de pirazol con el fenilo diclorado y
trifluorometilado; cambia el sustituyente del azufre.

Y fipronil está etiquetado como **tóxico** y estaba en entrenamiento. El modelo
tenía un ejemplo tóxico muy parecido y aun así clasificó Ethiprole como no
tóxico. Los seis modelos fallaron.

Tampoco es un caso de frontera: su LD₅₀ experimental está bien por debajo de los
11 µg por abeja.

Isocycloseram es el caso complementario: su soporte estructural máximo es 0,233,
apenas por encima del corte. Ahí el problema sí parece ser extrapolación de
quimiotipo.

La lectura honesta es que X10 podría no capturar algunas relaciones
estructura-actividad relevantes. Es una hipótesis para estudios toxicodinámicos y
biofísicos, no una conclusión demostrada aquí.

> **Transición:** «Cerremos con lo que esto sí y no muestra.»

## 14 · Conclusiones — 0:55 · acum. 11:55
Dos hallazgos bajo evaluación disjunta por clúster molecular.

Primero: los kernels cuánticos evaluados no aportaron una mejora predictiva
consistente frente al RBF igualado. Estuvieron muy cerca, sin ventaja que
persistiera en los cinco folds, y en el holdout los contrastes cambiaron de signo.

Segundo: tampoco indujeron una geometría de semejanza claramente distinta. Las
matrices de Gram de los tres kernels están muy alineadas: CKA de 0,982 y 0,985
frente al RBF, y 0,9995 entre los dos cuánticos.

Y un hallazgo práctico que trasciende la pregunta cuántica: la detección de
compuestos tóxicos fuera de Development es débil.

**La columna de la derecha es igual de importante.** Esto no demuestra ventaja
cuántica: muestra que estos dos mapas fijos, con esta representación y este
protocolo, no se separan del RBF. No evaluamos ruido ni hardware. No establece
utilidad clínica ni regulatoria. Y no generaliza más allá de X10 y estos mapas.

> **Transición:** «¿Hacia dónde seguimos?»

## 15 · Trabajo futuro — 0:50 · acum. 12:45
Tres líneas concretas.

Primera: extender la optimización de la escala de codificación. El ancho de banda
resultó ser el factor determinante, así que merece tratarse como objeto de
estudio y no como un subproducto de la búsqueda de hiperparámetros.

Segunda: en vez de mapas fijos, entrenar los parámetros del embedding por
alineación kernel-objetivo.

Tercera, y aquí entra la figura: reorganizar y ampliar los qubits. Recuerden que
en el mapa IQP-ZZ las interacciones RZZ sólo acoplan qubits vecinos en cadena.
Eso significa que **qué descriptor va junto a cuál** determina qué pares de
características pueden interactuar. Hoy el orden es simplemente el heredado de la
tabla.

La figura muestra cuánta señal tiene cada descriptor por separado en Development.
nOP es el más informativo con 0,675; LiPHEX, por sí solo, queda casi en el azar.
Una línea de trabajo es usar esa estructura para decidir el orden de los qubits,
duplicar qubits por descriptor para conservar más contexto, o añadir
descriptores. Insisto en que esta figura es descriptiva: ningún descriptor se
eligió ni se eliminó a partir de ella.

> **Transición:** «Y con eso cierro.»

## 16 · Cierre — 0:25 · acum. 13:10
El suplemento está archivado en Zenodo y el dataset curado, los descriptores y el
flujo de entrenamiento están en el repositorio de GitHub. Muchas gracias.

---

## Preguntas probables y respuestas breves

**¿Por qué no ejecutaron en hardware cuántico?**
El objetivo era aislar el efecto de la geometría del kernel. Introducir ruido y
error de muestreo habría confundido ese efecto con el del dispositivo. Diez
qubits mantienen el circuito pequeño para hacerlo después; está en trabajo futuro.

**¿Por qué sólo diez descriptores? Parece poco.**
Porque cada descriptor ocupa un qubit y el número de descriptores fija el tamaño
del circuito. Es una decisión de diseño declarada, no una afirmación de que diez
basten. De hecho el caso Ethiprole sugiere que X10 puede no capturar todo.

**¿No es un resultado negativo?**
Es un resultado acotado y, creemos, informativo. En particular, al controlar el
ancho de banda —comparando Product contra un RBF clásico con el mismo gamma
efectivo de 0,015625— el rango efectivo pasa de 3,086 a 3,078: la diferencia
aparente era de bandwidth, no de naturaleza cuántica. Eso orienta el trabajo
futuro hacia la escala de codificación y los kernels entrenables.

**¿Qué pasa con el MLP?**
Hay dos variantes: la original sin ponderación de clases y la balanceada y
retuneada. Presento la balanceada de forma consistente en toda la charla. La
procedencia está documentada en el registro de verificación.

**¿La comparación con otras representaciones?**
El paper reporta una tabla con seis representaciones alternativas, pero no pude
sustentar su procedencia con los artefactos conservados, así que no la presento.
Está anotado como pendiente.

**¿Sirve esto para regulación?**
No. La sensibilidad fuera de Development está entre 0,082 y 0,265. Como apoyo a
priorización exploratoria tiene interés; como criterio de decisión, no.
