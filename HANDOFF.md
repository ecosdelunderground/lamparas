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

## Sesión del 24-09 (nube): qué se hizo y qué queda

**Las piezas .stl/.ply de la carpeta NO están regeneradas**: el OBJ no se subió
al repo y `preparar.py` no se ha podido ejecutar aquí. Hay que subirlo como
`meshy.obj` en esta carpeta (preparar y verificar lo buscan ahí primero).

Hecho:
- `verificar.py` adaptado a las cotas y contornos nuevos, con comprobaciones
  nuevas: malla limpia (pellizcos, contactos entre láminas, triángulos
  degenerados), la regla de la luz pared a pared, la falda contra el marco y el
  recorrido de montaje con pasos de 0,1 / 0,25 / 0,5 mm además de los de antes.
  Sobre las piezas actuales: 30/38, sección 4 sin ejecutar (falta el OBJ).
- `pulir()` reescrito: primero exige que la malla de la booleana no tenga
  pellizcos (si los tiene, para y dice dónde: es diseño), luego colapsa astillas
  con `Manifold.simplify(0,001 mm)`, que no puede abrir la malla.
- Causa de que la tapa no se pudiera limpiar: el avellanado estaba AL REVÉS
  (Ø3,6 por fuera, Ø5,9 contra la piedra) y su cono tocaba el taladro en un
  círculo exacto. Ahora es un solo sólido de revolución que abre hacia fuera.
  Probado sobre la tapa: 0 pellizcos, 0 degenerados, 0 astillas tras pulir.
- Las pezuñas atravesaban el tubo y asomaban 1–3 mm² dentro de la caja del LED:
  ahora se recortan a media pared del tubo.

Pendiente (todo necesita el OBJ):
1. Luz, pellizco en Z_SUELO+0,2: la tapa del prisma `MACIZO`
   (`SIL_REL.buffer(-2)`, hasta Z_SUELO+0,2) roza la piel del relieve. Rehacer el
   vaciado prolongando hacia atrás la sección real de la base del relieve.
2. Luz, vacío de espesor cero en (0,8, −38,5, −2,4): donde la pata mide < 4,4 mm
   la erosión de 2,2 deja una lámina. Hacer apertura (erosionar 2,4 y dilatar 0,2).
3. Luz, muñones fantasma: la copia de pezuñas desplazada 4 mm en −Y se ve junto
   a las patas inclinadas. Mejor extruir la planta de las pezuñas en −Y.
4. Piedra: 9 agujas en el canto de la trasera (Z=−26,41): imantar al plano los
   vértices del OBJ a menos de 0,02 mm antes de cortar.
5. **Falda contra el marco (decisión de Sergi)**: el rebaje corta marco visible en
   88 mm de contorno, hasta 17,3 mm de alto, 1 881 mm² (abajo, bajo las pezuñas, y
   en la esquina de la roca). Ver `falda_marco.png` y `falda_zoom.png`.

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
