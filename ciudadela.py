# -*- coding: utf-8 -*-
"""Trazado del nicho segun la Ciudadela de Jaca (acordado con Sergi el 24-09).

El modelo es una interpretacion artistica de la Ciudadela: estrella de cinco
baluartes con un patio pentagonal. Las lineas del nicho se trazan de fuera
hacia dentro para que todo sea coherente con la silueta:

  W2    pared escalon -> terraza: cada cara de baluarte paralela a la silueta
        (simetrizada) a MARCO mm, asi el marco exterior de piedra tiene el mismo
        ancho en todas las caras. Entre baluartes, una cortina con un orejon a
        cada lado; los entrantes a ENTRANTE grados (algo abiertos: mas artistico
        que 90). Las puntas laterales, con sus dos caras iguales.
  AEX   pared corona -> escalon: W2 desplazada ESCALON mm hacia dentro (escalon
        de ancho constante). En la puerta de abajo no hay escalon por arriba.
  POZO  el patio: pentagono simetrico con los lados de abajo verticales, para
        enmarcar al ciervo (dibujo de Sergi).

Todo es simetrico respecto a X=0. Las coordenadas son el resultado de la
construccion (ver la conversacion del 24-09): se fijan aqui como diseno y no se
recalculan desde el OBJ.
"""
import numpy as np
from shapely.geometry import Polygon, box

MARCO = 17.0            # ancho del marco exterior (silueta -> W2), en las caras
ESCALON = 5.0           # ancho del escalon (W2 -> AEX)
ENTRANTE = 100.0        # angulo de los entrantes de los orejones
X_PUERTA, Y_PUERTA = 19.5, -60.65
CIERVO_DX = 4.90        # el ciervo se desplaza a la derecha para quedar centrado

# W2, lado derecho, de la punta de arriba a la puerta
W2_DER = [(0.0, 77.98), (29.05, 47.19), (24.95, 41.05), (41.5, 25.22), (50.0, 31.46),
          (76.59, 17.94), (61.75, -7.94), (53.65, -7.18), (44.77, -39.57),
          (53.61, -43.76), (54.24, -80.78), (19.5, -73.23), (19.5, -60.65)]
# POZO, lado derecho
POZO_DER = [(0.0, 50.5), (46.5, 7.33), (34.0, -41.0), (34.0, -56.1)]


def espejo(der):
    """Poligono simetrico respecto a X=0 a partir de su lado derecho (de arriba
    abajo, empezando y acabando en el eje o en la puerta)."""
    izq = [(-x, y) for x, y in reversed(der) if x > 1e-6]
    return Polygon(list(der) + izq)


W2 = espejo(W2_DER)
AEX = W2.buffer(-ESCALON, join_style=2, mitre_limit=8).union(
    box(-X_PUERTA - ESCALON, Y_PUERTA, X_PUERTA + ESCALON, Y_PUERTA + ESCALON + 0.5))
POZO = espejo(POZO_DER)


def angulos(p):
    c = np.array(p.exterior.coords)[:-1]
    u = np.roll(c, 1, 0) - c
    w = np.roll(c, -1, 0) - c
    return np.degrees(np.arccos(np.clip((u * w).sum(1) / np.linalg.norm(u, axis=1)
                                        / np.linalg.norm(w, axis=1), -1, 1)))
