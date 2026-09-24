# Handoff — lámpara Ciudadela / Starlit Stag

Pega esto en una sesión nueva para continuar.

---

Estoy preparando para imprimir en 3D una lámpara a partir de un OBJ de Meshy AI.
El proyecto vive en `C:\Users\sergi\Documents\claudeproject\estrella-meshy`.
Lee primero el `README.md` y `preparar.py` de esa carpeta.

**Entorno**: Python de sistema en
`C:/Users/sergi/AppData/Local/Programs/Python/Python313/python.exe`, con trimesh,
shapely, manifold3d, scipy, matplotlib, PIL, rtree. El motor de booleanas es
`manifold`. El OBJ original está en
`C:/Users/sergi/Downloads/Meshy_AI_Starlit_Stag_0923134854_generate_obj/Meshy_AI_Starlit_Stag_0923134854_generate_obj/Meshy_AI_Starlit_Stag_0923134854_generate.obj`.
No modifiques el OBJ; todo se genera desde él con `preparar.py`.

## Qué es

Estrella de 5 puntas de 200 × 198 × 58 mm con un nicho pentagonal y un ciervo
dentro. Se imprime en **tres piezas** y se monta con 5 tornillos M3:

- `1_piedra` (filamento opaco, acabado piedra): el marco de la estrella.
- `2_luz` (filamento **translúcido**): UNA sola pieza = la corona iluminada que
  rodea la boca del nicho + el escalón interno (la pared del pozo) + el ciervo en
  relieve + una **falda exterior** oculta dentro de la piedra que hace que la
  pieza se imprima sin soportes y forma la caja donde va la tira LED.
- `3_tapa` (opaco): cierra por detrás, lleva los tornillos y el canal del cable, y
  **lleva montado el fondo del nicho** (la pared de detrás del ciervo) como un
  pedestal de 13,4 mm.

## La regla de la luz (esto costó cinco rondas, no te la saltes)

Hay **tres paredes** en el nicho. Solo se encienden dos de ellas y el ciervo:

| pared | pieza | ¿emite? |
|---|---|---|
| marco exterior de la estrella | `1_piedra` | **NO** |
| **la corona iluminada** (la franja plana a Z ≈ +11 que rodea la boca, 7–9 mm de ancho vista de frente) | `2_luz` | **SÍ** |
| **el escalón interno** (las paredes del pozo, 24 mm de caída) | `2_luz` | **SÍ** |
| el fondo, detrás del ciervo | pedestal de `3_tapa` | **NO** |
| el ciervo | `2_luz` | **SÍ** |

El ciervo es un **relieve de 15 mm** pegado al fondo: se recula 10,9 mm respecto
al OBJ y se corta en el plano del fondo. No lleva tallo ni hueco por detrás; la
luz le entra por un agujero con su silueta (metida 2,5 mm, así no se ve) en el
pedestal de la tapa. Las pezuñas se hunden 4 mm en el suelo del pozo para que el
relieve quede soldado a la pieza y no salga suelto.

## Cotas y decisiones ya cerradas

- Escala: 200 mm de ancho → 105,2085 mm por unidad del OBJ.
- Planos: trasera aplanada `Z=-26,41` · fondo del nicho `Z=-12,99` · cara de la
  corona `Z=+10,90` · junta corona/tubo `Z=+7,40` · frente `Z=+28,69`.
- Pared translúcida 2,0 mm, falda 2,0 mm, holgura única 0,2 mm, corona 3,5 mm.
- Orientación de impresión = la de exportación: cara plana en la cama, cavidades
  hacia arriba, **sin soportes**.
- La pieza `2_luz` entra **por detrás** (el marco se mete hacia dentro por abajo y
  no cabe por delante). La tapa también por detrás. Verificado desplazando cada
  pieza 1/2/4/8/16/30/50 mm e intersecando, no solo en la posición final.
- La trasera de la estrella se aplana 0,5 mm para quitarle la textura de Meshy.

## Dónde estoy ahora mismo (a medias)

Sergi vio las piezas en el laminador y **rechazó las costuras**: bordes en sierra,
lengüetas finas y ondulaciones, porque yo estaba cortando todas las caras de
encaje contra la malla facetada de Meshy. Medido: la cara de la corona iba de
Z +6,25 a +20,80 en vez de ser un plano, y las piezas llevaban 4 324 y 12 563
triángulos por debajo de 0,001 mm².

Acordamos con él: **nada que encaje se corta contra la malla**. Todo sale de dos
polígonos limpios (lados rectos, esquinas vivas) y dos planos de verdad. Eligió
expresamente «contornos limpios sin tocar la forma», **no** simetrizar (medí que
simetrizar movería el pozo 6,4 mm y la estrella 7,7 mm, y se lo dije).

`preparar.py` ya está reescrito con ese criterio y **corre entero**. Última salida:

```
POZO:   1467 vertices -> 16 lados rectos, desviacion max 1.03 mm, area 7171 mm2
CORONA: 6419 vertices -> 37 lados rectos, area 3398 mm2, ancho medio 7.5 mm
(la falda pide 5822 mm2 por fuera del escalon del marco)
piedra: pulido 235042 -> 235042 caras, 484 astillas, cerrada=True   754.8 cm3
luz:    la limpieza abria la malla, se deja como estaba              80.4 cm3
tapa:   la limpieza abria la malla, se deja como estaba             137.5 cm3
```

### Lo que queda por hacer

1. **`verificar.py` está desactualizado y no arranca**: espera el `cotas.npy` y el
   `contornos.wkt` del diseño anterior. Ahora `preparar.py` escribe
   `cotas = [S, Z_TRASERA, Z_SUELO, Z_CORONA, Z_JUNTA, Z_FRENTE, OFF_LUZ,
   OFF_PIEDRA, TAPA_ESP, CIERVO_RELIEVE, HOLGURA, FALDA]` y
   `contornos.wkt = SIL_CIERVO, POZO, AEX, CORONA`. Hay que adaptarlo y volver a
   pasar las comprobaciones (la versión anterior sacaba 24/24).
2. **`pulir()` no consigue limpiar `2_luz` ni `3_tapa`**: al fusionar vértices la
   malla se abre, así que se queda como estaba. Hay que resolverlo de verdad
   (fusión por distancia con tolerancia, o rehacer esas piezas para que no salgan
   astillas de las booleanas). Es justo lo que Sergi quiere arreglado.
3. **Verificar que la falda no muerde el escalón visible del marco**: el log dice
   que pide 5 822 mm² por fuera de la corona. Hay que mirarlo en render y, si se
   come marco visible, estrechar la falda o recortarla ahí.
4. **Renderizar y enseñárselo**: no he mirado todavía la versión limpia. Usa
   `render.py` (rasterizador propio) y compara con la versión anterior.
5. Actualizar el `README.md` con las cotas nuevas cuando esté cerrado.

## Sesión del 24-09 (nube): estado

El OBJ está en el repo como `meshy.obj`; `preparar.py` y `verificar.py` lo
buscan ahí primero. Piezas regeneradas. `verificar.py`: **40/43**.

Decisiones de Sergi (24-09):
- **Falda, opción B**: se deja la franja de corona que recorta el marco (bloque
  de abajo y esquina de la roca) para verlo impreso. Si no gusta, opción A:
  sin corona donde el original no la tiene, placa escondida bajo el marco.
- **Soportes solo bajo el ciervo** en la pieza de luz (su relieve empieza en el
  aire en la orientación de impresión). Descartado el apoyo oculto en el pedestal.

Hecho:
- `pulir()`: para si la booleana deja pellizcos (fallo de diseño) y colapsa
  astillas con `Manifold.simplify` (0,001 mm; la luz 0,01 mm, que cierra los
  pliegues de vacío < 0,01 mm que deja la erosión dentro del ciervo).
- Tapa: el avellanado estaba al revés y su cono tocaba el taladro en un círculo.
- Luz: boca trasera del ciervo dentro de su base real (el prisma de la silueta
  cortaba el lomo casi horizontal y pellizcaba); pezuñas prolongadas en recto
  hasta media pared del tubo (antes: muñones fantasma y asomaban a la caja).
- POZO: la envolvente se muestrea solo hasta la junta. Antes llegaba a Z +9,4 y
  metía en el pozo un rellano de la corona (esquina de la roca, Z ≈ +9), creando
  un pocillo iluminado de 24 mm que el original no tiene. Desvío al original:
  19,4 → 1,74 mm.
- `verificar.py`: malla limpia, regla de la luz, falda, sección 4 separando lo
  aceptado, recorrido fino, e islas en el aire (la de antes no las veía).

- Malla perfecta: `sanear()` en `pulir()` quita los triángulos degenerados
  (colapsa lados < 0,01 mm con condición de enlace, voltea agujas) y exige 0.
  `verificar.py` comprueba también los .stl.
- `render.py` con z-buffer: el algoritmo del pintor sacaba esquirlas falsas.
- Anomalías que Sergi vio en el laminador (24-09), arregladas:
  - Picos en esquinas del pozo y del borde de la corona (dientes que deja
    `simplify`): `sin_dientes()` quita zigzags y rehace esquinas mordidas.
  - Rendija de 0,4 mm entre tubo y falda en toda la altura: la caja del LED es
    ahora el hueco sin zonas de menos de 1,5 mm; lo demás se maciza (caja: 17
    cm² útiles; las rendijas no servían para el LED).
  - Espigo y agujero del pedestal sin partes de menos de 1,2 mm.
  - Hueco del ciervo solo donde la silueta pasa de 8 mm: en patas y cuernas
    dejaba láminas de vacío que se verían al trasluz.
  - Pezuñas: cada una baja al suelo con su forma (envolvente convexa de su
    último mm); antes quedaba una rendija de 0,4–0,6 mm bajo las patas.
- `CORONA_BORDE`: probado 'fuera' (la corona hasta la pared del escalón) y
  descartado: el corte recto cruza en rasante la pared texturada y deja costura
  en sierra. Se queda 'dentro'.
- `verificar.py`: contornos sin dientes y barrido de lengüetas/rendijas < 0,8 mm
  en lo construido (tapa entera, luz fuera del ciervo). **49/50**.

- **Borde de la corona por el canto (`CORONA_BORDE = 'canto'`)**, a petición de
  Sergi (24-09): las paredes corona→escalón de Meshy eran rampas con nervaduras
  y cantos dentados. El borde de la corona se traza ahora por el canto de arriba
  de esa pared (Z_ESCALON − 0,5, sacado 0,4 mm sobre la cara plana): el rebaje
  se lleva la rampa entera y deja una pared vertical lisa cuyo canto corta en
  perpendicular la cara plana del escalón (Z 21,19). La corona pasa a 4 544 mm²
  (10,4 mm de ancho medio). Probado antes 'fuera' (costura en sierra) y
  'dentro' (tira de piedra); ver comparación en la conversación.
- Eje de simetría medido: X = 0 sin giro; alturas de terrazas simétricas
  (mediana 0,08 mm); las paredes difieren unos mm de un lado a otro.

- Corrección de Sergi (24-09, capturas del laminador): en los dos valles de
  arriba la cara del escalón de Meshy tiene hondonadas (Z 19–20 en vez de 21,2).
  El borde por el canto se metía en ellas (derecha: se comía el escalón;
  izquierda: dos planos). Ahora: el borde se toma a media pared (Z 16,0) y se
  endereza con 2 mm; y la cara del escalón se RELLENA hasta un plano único
  (Z_ESCALON + 0,15 = 21,34) en 8 mm por fuera del borde, antes de cortar el
  rebaje. Hondonadas y restos de rampa quedan enterrados; donde la superficie
  ya está más alta no cambia. Borde de la corona: 29 lados, valles simétricos.
- `TOL_POZO` 1,2 → 0,9: pozo de 11 lados, 99 % de las paredes a < 1,05 mm del
  original.

`verificar.py`: **50/50**.

Queda de Meshy sin tocar: la pata delantera modelada como una tabla plana.

## Rediseño Ciudadela (24-09, aprobado por Sergi: «Ahora SÍ»)

El nicho ya no sigue las paredes de Meshy: se traza según la Ciudadela de Jaca
(el logo de su web), como interpretación artística pero simétrica y con ángulos
coherentes. Todo el trazado está en `ciudadela.py`, fijado como diseño (no se
recalcula desde el OBJ); `preparar.py` lo usa con `CORONA_BORDE = 'ciudadela'`
(los modos 'dentro', 'fuera' y 'canto' siguen ahí para comparar).

- `W2` (escalón → terraza): cada cara de baluarte a **17 mm** de la silueta
  simetrizada; cortinas con orejones; entrantes a **100°**; puntas laterales con
  sus dos caras iguales (29,8 mm).
- `AEX` (borde de la corona) = W2 metido **5 mm** (escalón constante). En la
  puerta de abajo no hay escalón por arriba.
- `POZO`: pentágono simétrico dibujado por Sergi, lados de abajo verticales.
  El ciervo se aísla con el pozo de Meshy (`POZO_MESHY`) y luego se desplaza
  `CIERVO_DX = 4,9` mm a la derecha para quedar centrado.
- Piedra: el escalón es un prisma plano a `Z_RELLENO = 21,34`; la terraza de
  8 mm por fuera se alisa con un campo de alturas (nivel del píxel de terraza
  más cercano, filtro de mediana); el valle de la punta de abajo es copia del
  valle lateral derecho girada 73° (+0,22 mm), aplicada solo donde sube, para
  que su rombo quede delante como los demás.
- Luz: la caja del LED lleva un núcleo macizo en el centro (54 mm²) para que el
  puente de la corona no pase de 12,9 mm.
- `cotas.npy` tiene 14 valores (añade `Z_RELLENO` y `RELLENO_ANCHO = 13`).
- `verificar.py`: la silueta y el marco se comparan fuera de lo rehecho
  (`AEX.buffer(RELLENO_ANCHO + 0,3)` y la puerta de abajo); el pozo se informa
  pero no se exige (está rediseñado).

`verificar.py`: **49/49**. Piedra 752 cm³, luz 88 cm³, tapa 136 cm³, corona
3 885 mm², caja del LED 39 cm² × 34 mm.

Queda de Meshy sin tocar:
- la pata delantera modelada como una tabla plana;
- la textura de piedra de las paredes del marco (de la terraza a la cara de
  delante) y de los rombos de las puntas. Es la piedra original; si Sergi la
  quiere lisa, es el siguiente paso.

## Cómo trabaja Sergi (importante)

- La parte estética la lleva él y te la marca sobre fotos y renders. Tu papel es
  la ingeniería de fabricación: booleanas, espesores, voladizos, encajes y
  verificación numérica. No le propongas conceptos propios.
- **Antes de un cambio grande, confírmale lo que has entendido** y enséñale un
  esquema o un render. Te lo ha pedido explícitamente dos veces.
- Mide y da números, no impresiones. Verifica el **recorrido entero** de montaje,
  no solo la posición final.
- `limpiar()` aborta si una booleana desprende algo de más de 50 mm³: eso no es
  una miga, es una pieza que ha quedado aislada. No subas ese umbral para que
  pase; arregla el diseño.
- Hay notas de la serie de lámparas en la memoria del proyecto
  (`project-lamparas-3d`), con las lecciones de los modelos anteriores.

Empieza por leer `preparar.py` y ejecutarlo para ver el estado, y sigue por el
punto 1.
