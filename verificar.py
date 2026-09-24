# -*- coding: utf-8 -*-
"""Comprueba las tres piezas y saca los renders. Ejecutar despues de preparar.py."""
import os
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import wkt as _wkt
from geo import xy_material
from render import rasterize, sheet

OUT = os.path.dirname(os.path.abspath(__file__))
OBJ = (r'C:/Users/sergi/Downloads/Meshy_AI_Starlit_Stag_0923134854_generate_obj'
       r'/Meshy_AI_Starlit_Stag_0923134854_generate_obj'
       r'/Meshy_AI_Starlit_Stag_0923134854_generate.obj')
ENGINE = 'manifold'
ok = []


def chk(cond, txt):
    ok.append(bool(cond))
    print(('  OK    ' if cond else '  FALLO ') + txt, flush=True)


def log(*a):
    print(*a, flush=True)


def anillos(g):
    gs = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    return [x for x in gs if x.geom_type == 'Polygon']


def contorno(g):
    return unary_union([Polygon(x.exterior) for x in anillos(g)])


def pared_minima(g, min_hueco=3.0):
    """Pared mas fina; ignora huecos minusculos (ruido numerico)."""
    peor = None
    for x in anillos(g):
        for h in x.interiors:
            if Polygon(h).area < min_hueco:
                continue
            d = x.exterior.distance(h)
            peor = d if peor is None else min(peor, d)
    return peor


P = trimesh.load(os.path.join(OUT, '1_piedra.ply'), process=False)
L = trimesh.load(os.path.join(OUT, '2_luz.ply'), process=False)
T = trimesh.load(os.path.join(OUT, '3_tapa.ply'), process=False)
SIL_CIERVO, POZO_M, W0 = [_wkt.loads(l) for l in
                          open(os.path.join(OUT, 'contornos.wkt')).read().splitlines()[:3]]
S, Z_TRASERA, Z_SUELO, Z_BOCA, Z_FRENTE, Z_ARO, Z_CONO0, \
    OFF_LUZ, OFF_PIEDRA, OFF_ANILLO, TAPA_ESP, CIERVO_RELIEVE = np.load(
        os.path.join(OUT, 'cotas.npy'))

log('=' * 74)
log('1. PIEZAS')
for n, m in (('piedra', P), ('luz', L), ('tapa', T)):
    cs = m.split(only_watertight=False)
    log(f'  {n:7s} {len(m.faces):7d} caras  {m.volume/1000:7.1f} cm3  '
        f'{np.round(m.extents,1)} mm  trozos={len(cs)}')
    chk(m.is_watertight and m.is_winding_consistent, f'{n}: cerrada y coherente')
    chk(len(cs) == 1, f'{n}: una sola pieza, sin migas')

log('')
log('2. INTERFERENCIAS ENTRE PIEZAS')
for a, b, na, nb in ((P, L, 'piedra', 'luz'), (P, T, 'piedra', 'tapa'),
                     (L, T, 'luz', 'tapa')):
    v = trimesh.boolean.intersection([a, b], engine=ENGINE).volume
    chk(v < 30, f'{na} vs {nb}: solape {v:.2f} mm3')

log('')
log('3. POR DONDE SALE LA LUZ')
rng = np.random.default_rng(0)
poly = W0.buffer(-1.0).difference(SIL_CIERVO.buffer(1.0))
minx, miny, maxx, maxy = poly.bounds
pts = []
while len(pts) < 900:
    x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
    if poly.contains(Polygon([(x, y), (x + .01, y), (x, y + .01)])):
        pts.append((x, y, Z_SUELO - 0.8))
pts = np.array(pts)
# el fondo del nicho va montado en la tapa, asi que cuenta piedra + tapa
fr_p = (P.contains(pts) | T.contains(pts)).mean()
fr_l = L.contains(pts).mean()
log(f'  detras del fondo del nicho (fuera de la silueta del ciervo): '
    f'{fr_p*100:.1f} % opaco, {fr_l*100:.1f} % translucido')
chk(fr_p > 0.97, 'el fondo del nicho es opaco macizo: por ahi no sale luz')
chk(fr_l < 0.02, 'el translucido no llega al fondo del nicho')
log(f'  espesor de ese fondo: {Z_SUELO - Z_TRASERA:.1f} mm de piedra')
chk(Z_SUELO - Z_TRASERA > 8, 'fondo del nicho bien grueso')

n_alturas = 0
for z in np.linspace(Z_SUELO + 2, Z_ARO - 2, 24):
    if any(x.area > 300 for x in anillos(xy_material(L, z))):
        n_alturas += 1
chk(n_alturas >= 22, f'las paredes translucidas cubren toda la altura del pozo '
                     f'({n_alturas}/24 cortes)')

log('')
log('4. EL MONTAJE REPRODUCE EL MODELO ORIGINAL')
orig = trimesh.load(OBJ, process=False)
orig.apply_scale(S)
orig = trimesh.intersections.slice_mesh_plane(
    orig, plane_normal=[0, 0, 1], plane_origin=[0, 0, Z_TRASERA], cap=True)
orig = trimesh.Trimesh(orig.vertices, orig.faces)
UNION = trimesh.boolean.union([P, L, T], engine=ENGINE)
anadido = trimesh.boolean.difference([UNION, orig], engine=ENGINE)
quitado = trimesh.boolean.difference([orig, UNION], engine=ENGINE)
log(f'  anadido (el tallo, detras del ciervo): {anadido.volume/1000:.2f} cm3')
log(f'  quitado (camara + agujero + canal + tornillos): {quitado.volume/1000:.1f} cm3')

tapado = SIL_CIERVO.buffer(0.6)
peor_ext = 0.0
for z in np.linspace(Z_TRASERA + 3.6, Z_FRENTE - 0.5, 40):
    a, b = xy_material(orig, z), xy_material(UNION, z)
    if a.is_empty or b.is_empty:
        continue
    ca, cb = contorno(a), contorno(b)
    peor_ext = max(peor_ext, ca.symmetric_difference(cb).area / ca.length)
chk(peor_ext < 0.05, f'silueta exterior intacta ({peor_ext:.3f} mm)')

# toda la superficie VISTA del original tiene que seguir existiendo en el montaje
# (las cavidades interiores no se ven y no cuentan)
sup, _ = trimesh.sample.sample_surface(orig, 3000)
dd = np.abs(trimesh.proximity.signed_distance(UNION, sup))
fuera_ciervo = ~np.array([tapado.contains(Polygon([(x, y), (x+.01, y), (x, y+.01)]))
                          for x, y, z in sup])
# la zona de debajo de la tapa no se ve (canal del cable y tornillos)
vista = fuera_ciervo & (sup[:, 2] > Z_TRASERA + 3.5)
mal = (dd > 0.3) & vista
log(f'  superficie vista del original que ya no coincide: {mal.sum()} de '
    f'{vista.sum()} puntos ({mal.sum()/max(vista.sum(),1)*100:.2f} %)')
chk(mal.sum() / max(vista.sum(), 1) < 0.01,
    'el montaje reproduce la superficie vista del original')

log('')
log('5. HOLGURAS Y ENCAJES')
smp, _ = trimesh.sample.sample_surface(L, 4000)
d = trimesh.proximity.signed_distance(P, smp)
chk(d.max() < 0.05, f'el forro no invade la piedra (maximo {d.max():+.3f} mm)')
cerca = np.sort(-d[(d < 0) & (d > -1.0)])
if len(cerca):
    log(f'  holgura donde se tocan: min {cerca[0]:.2f}  mediana '
        f'{np.median(cerca):.2f}  max {cerca[-1]:.2f} mm')

# RECORRIDO de montaje completo. El forro entra POR DETRAS (el marco se mete
# hacia dentro por abajo y no cabe por delante); el aro y la tapa, cada uno por
# su lado. Se comprueba desplazando la pieza por todo el camino.
def recorrido(pieza, nombre, sentido, contra=(), pasos=(1, 2, 4, 8, 16, 30, 50)):
    peor = 0.0
    for d in pasos:
        q = pieza.copy()
        q.apply_translation([0, 0, d * sentido])
        for otra in (P,) + contra:
            peor = max(peor, trimesh.boolean.intersection(
                [q, otra], engine=ENGINE).volume)
    lado = 'por delante' if sentido > 0 else 'por detras'
    chk(peor < 30, f'{nombre} entra y sale {lado} sin chocar '
                   f'(maximo solape en el recorrido: {peor:.1f} mm3)')


recorrido(L, 'la pieza de luz', -1)
recorrido(T, 'la tapa con el fondo', -1, contra=(L,))

log('')
log('6. ESPESORES')
peor, peor_z = 99.0, None
for z in np.linspace(Z_TRASERA + 1, Z_ARO - 1.0, 20):
    w = pared_minima(xy_material(L, z))
    if w and w < peor:
        peor, peor_z = w, z
log(f'  pieza de luz: pared minima {peor:.2f} mm en Z={peor_z:+.1f}')
chk(peor > 1.2, 'pared de la pieza de luz >= 1,2 mm (3 perimetros de 0,4)')

peor_c, peor_cz = 99.0, None
for z in np.linspace(Z_SUELO + 2.0, Z_SUELO + CIERVO_RELIEVE - 2.5, 12):
    w = pared_minima(xy_material(L, z))
    if w and w < peor_c:
        peor_c, peor_cz = w, z
log(f'  ciervo en relieve: pared minima {peor_c:.2f} mm en Z={peor_cz:+.1f}')
chk(peor_c > 1.0, 'pared del ciervo >= 1,0 mm')

peor_p, peor_pz = 99.0, None
for z in np.linspace(Z_TRASERA + 4.0, Z_CONO0 - 1, 12):   # por encima del canal del cable
    for x in anillos(xy_material(P, z)):
        for h in x.interiors:
            if Polygon(h).area > 2000:
                dd = x.exterior.distance(h)
                if dd < peor_p:
                    peor_p, peor_pz = dd, z
log(f'  piedra entre la camara y el exterior: minimo {peor_p:.1f} mm en Z={peor_pz:+.1f}')
chk(peor_p > 5, 'la camara queda enterrada en piedra')

log('')
log('7. VOLADIZOS EN LA ORIENTACION DE IMPRESION (sin soportes)')


def ancho(geom, lim=12.0):
    if geom.is_empty:
        return 0.0
    lo, hi = 0.0, lim
    for _ in range(14):
        mid = (lo + hi) / 2
        if geom.buffer(-mid).is_empty:
            hi = mid
        else:
            lo = mid
    return 2 * lo


for n, m in (('piedra', P), ('luz', L), ('tapa', T)):
    z0, z1 = m.bounds[0][2], m.bounds[1][2]
    dz = 0.4
    peor_a, peor_z, peor_g, prev = 0.0, None, None, None
    for z in np.arange(z0 + 0.25, z1 - 0.25, dz):
        cur = xy_material(m, z)
        if cur.is_empty:
            continue
        if prev is not None:
            libre = cur.difference(prev.buffer(dz))
            if libre.area > peor_a:
                peor_a, peor_z, peor_g = libre.area, z, libre
        prev = cur
    w = ancho(peor_g) if peor_g is not None else 0.0
    zt = f'{peor_z:+.1f}' if peor_z is not None else '  -  '
    log(f'  {n:7s} peor capa sin apoyo: {peor_a:6.1f} mm2 en Z={zt}, '
        f'puente de {w:.1f} mm')
    # un puente apoyado en los dos lados hasta 15 mm lo hace el laminador solo;
    # lo que no vale es un voladizo en el aire
    chk(w < 15.0, f'{n}: nada que pida soporte (puente de {w:.1f} mm)')

log('')
log('8. MEDIDAS')
log(f'  estrella                   {P.extents[0]:.0f} x {P.extents[1]:.0f} mm')
log(f'  grosor piedra / con tapa   {P.extents[2]:.1f} / {P.extents[2]+TAPA_ESP:.1f} mm')
log(f'  nicho                      {Z_BOCA - Z_SUELO:.1f} mm de profundidad')
log(f'  fondo del nicho (piedra)   {Z_SUELO - Z_TRASERA:.1f} mm')
log(f'  camara anular              {OFF_ANILLO - OFF_PIEDRA:.1f} mm de ancho, recta '
    f'hasta Z={Z_CONO0:+.1f} y cerrando a 45 hasta Z={Z_ARO:+.1f}')
log(f'  forro                      {L.extents[0]:.0f} x {L.extents[1]:.0f} x '
    f'{L.extents[2]:.1f} mm   {L.volume/1000:.1f} cm3')
log(f'  tapa                       {T.extents[0]:.0f} x {T.extents[1]:.0f} x '
    f'{T.extents[2]:.1f} mm   {T.volume/1000:.1f} cm3')
log(f'  piedra                     {P.volume/1000:.0f} cm3 de solido')
log('')
log('=' * 74)
log(f'{sum(ok)}/{len(ok)} comprobaciones correctas')

log('renderizando...')
PIE = (170, 164, 152); LUZC = (255, 198, 96); TAP = (130, 126, 118)
ims, lab = [], []


def add(ms, cols, d, n, up=(0, 1, 0), size=560):
    ims.append(rasterize(ms, d, up=up, size=size, colors=cols)); lab.append(n)


add([P, L, T], [PIE, LUZC, TAP], (0, 0, -1), 'FRENTE montado')
add([P, L, T], [PIE, LUZC, TAP], (0.35, 0.18, -0.92), 'frente 3/4')
add([P, L, T], [PIE, LUZC, TAP], (-0.6, 0.25, -0.75), 'frente desde el otro lado')
add([P, T], [PIE, TAP], (0, 0, 1), 'TRASERA con tapa')
add([L], [LUZC], (0.45, 0.25, -0.85), 'pieza de LUZ')
add([L], [LUZC], (0.3, 0.2, 0.9), 'LUZ por detras')
add([P], [PIE], (0.3, 0.35, 0.9), 'PIEDRA tal como se imprime')
add([T], [TAP], (0.25, 0.2, -0.94), 'TAPA con el fondo del nicho')
sheet(ims, cols=3, labels=lab).save(os.path.join(OUT, 'verificacion.png'))

rasterize([P, L, T], (0.06, 0.05, -0.99), up=(0, 1, 0), size=950,
          colors=[(52, 48, 44), (255, 216, 145), (40, 38, 36)],
          bg=(11, 11, 13),
          light=(0.25, 0.35, 1.0)).save(os.path.join(OUT, 'encendida.png'))
log('hecho')
