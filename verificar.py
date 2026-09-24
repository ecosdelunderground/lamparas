# -*- coding: utf-8 -*-
"""Comprueba las tres piezas y saca los renders. Ejecutar despues de preparar.py.

Lee lo que escribe preparar.py:
  cotas.npy     = [S, Z_TRASERA, Z_SUELO, Z_CORONA, Z_JUNTA, Z_FRENTE,
                   OFF_LUZ, OFF_PIEDRA, TAPA_ESP, CIERVO_RELIEVE, HOLGURA, FALDA]
  contornos.wkt = SIL_CIERVO, POZO, AEX, CORONA

La seccion 4 (comparar con el modelo original) necesita el OBJ de Meshy. Si no
esta, esa seccion sale como NO EJECUTADA y el total no puede ser completo.
"""
import os
import numpy as np
import trimesh
import shapely
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import wkt as _wkt
from scipy.spatial import cKDTree
from geo import xy_material, contactos, estrechos
from render import rasterize, sheet

OUT = os.path.dirname(os.path.abspath(__file__))
OBJS = [os.path.join(OUT, 'meshy.obj'),
        r'C:/Users/sergi/Downloads/Meshy_AI_Starlit_Stag_0923134854_generate_obj'
        r'/Meshy_AI_Starlit_Stag_0923134854_generate_obj'
        r'/Meshy_AI_Starlit_Stag_0923134854_generate.obj']
OBJ = next((p for p in OBJS if os.path.exists(p)), None)
ENGINE = 'manifold'
JS = 2
ok = []
no_ejecutadas = []


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
SIL_CIERVO, POZO, AEX, CORONA = [_wkt.loads(l) for l in
                                 open(os.path.join(OUT, 'contornos.wkt')).read().splitlines()[:4]]
(S, Z_TRASERA, Z_SUELO, Z_CORONA, Z_JUNTA, Z_FRENTE, OFF_LUZ, OFF_PIEDRA,
 TAPA_ESP, CIERVO_RELIEVE, HOLGURA, FALDA) = np.load(os.path.join(OUT, 'cotas.npy'))

log('=' * 74)
log('1. PIEZAS')
for n, m in (('piedra', P), ('luz', L), ('tapa', T)):
    cs = m.split(only_watertight=False)
    log(f'  {n:7s} {len(m.faces):7d} caras  {m.volume/1000:7.1f} cm3  '
        f'{np.round(m.extents,1)} mm  trozos={len(cs)}')
    chk(m.is_watertight and m.is_winding_consistent, f'{n}: cerrada y coherente')
    chk(len(cs) == 1, f'{n}: una sola pieza, sin migas')

log('')
log('1b. MALLA LIMPIA (sin pellizcos, filos de espesor cero ni triangulos nulos)')
for n, m in (('piedra', P), ('luz', L), ('tapa', T)):
    f = trimesh.Trimesh(m.vertices.copy(), m.faces.copy(), process=False)
    f.merge_vertices()
    chk(f.is_watertight, f'{n}: sigue cerrada al fusionar vertices '
                         f'({len(m.vertices) - len(f.vertices)} vertices duplicados)')
    c = contactos(m)
    zs = np.unique(np.round(m.vertices[c[:, 0], 2], 1)) if len(c) else []
    chk(len(c) == 0, f'{n}: {len(c)} contactos entre laminas a < 0,01 mm'
                     + (f' (Z {list(map(float, zs[:5]))})' if len(c) else ''))
    t = m.triangles
    ls = np.linalg.norm(t[:, [1, 2, 0]] - t, axis=2)
    deg = (ls.min(1) < 1e-6) | (2 * m.area_faces / np.maximum(ls.max(1), 1e-12) < 1e-4)
    chk(deg.sum() == 0, f'{n}: {deg.sum()} triangulos degenerados (arista nula o aguja); '
                        f'{(m.area_faces < 1e-3).sum()} por debajo de 0,001 mm2')

# lo que se abre en el laminador: el .stl (precision simple, sin conectividad)
for n in ('1_piedra', '2_luz', '3_tapa'):
    st = trimesh.load(os.path.join(OUT, n + '.stl'))      # trimesh fusiona vertices al cargar
    t = st.triangles
    ls = np.linalg.norm(t[:, [1, 2, 0]] - t, axis=2)
    deg = (ls.min(1) < 1e-6) | (2 * st.area_faces / np.maximum(ls.max(1), 1e-12) < 1e-4)
    chk(st.is_watertight and st.is_winding_consistent and deg.sum() == 0
        and len(st.split(only_watertight=False)) == 1,
        f'{n}.stl: cerrado, coherente, de una pieza y {deg.sum()} degenerados')

# contornos limpios: sin zigzags ni puntas (dientes que deja enderezar)
for n, pol in (('POZO', POZO), ('borde de la corona', AEX)):
    c = np.array(pol.exterior.coords)[:-1]
    u = np.roll(c, 1, 0) - c; w_ = np.roll(c, -1, 0) - c
    tri = 0.5 * np.abs(u[:, 0] * w_[:, 1] - u[:, 1] * w_[:, 0])
    ang = np.degrees(np.arccos(np.clip((u * w_).sum(1) / np.linalg.norm(u, axis=1)
                                       / np.linalg.norm(w_, axis=1), -1, 1)))
    chk(tri.min() >= 2.0 and ang.min() >= 45,
        f'{n}: sin dientes ({len(c)} lados; angulo min {ang.min():.0f} deg, '
        f'triangulo min {tri.min():.1f} mm2)')

# lenguetas y rendijas de menos de 0,8 mm en lo que se construye (no en la
# superficie de Meshy): toda la tapa y la pieza de luz fuera del ciervo
# (el ciervo y sus pezunas son modelado de Meshy: sus detalles no cuentan)
for n, m, zona in (('tapa', T, None),
                   ('luz fuera del ciervo', L, AEX.buffer(1).difference(POZO.buffer(-0.3))
                    .difference(SIL_CIERVO.buffer(1.5)))):
    e = estrechos(m, zona=zona)
    sitios = sorted({(round(q.centroid.x), round(q.centroid.y)) for _, _, q in e})
    chk(not e, f'{n}: {len(e)} lenguetas o rendijas de menos de 0,8 mm'
        + (f' en {sitios[:6]}' if e else ''))

log('')
log('2. INTERFERENCIAS ENTRE PIEZAS')
for a, b, na, nb in ((P, L, 'piedra', 'luz'), (P, T, 'piedra', 'tapa'),
                     (L, T, 'luz', 'tapa')):
    v = trimesh.boolean.intersection([a, b], engine=ENGINE).volume
    chk(v < 30, f'{na} vs {nb}: solape {v:.2f} mm3')

log('')
log('3. LA REGLA DE LA LUZ')
rng = np.random.default_rng(0)


def puntos_en(poly, n, z):
    minx, miny, maxx, maxy = poly.bounds
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if poly.contains(Point(x, y)):
            pts.append((x, y, z))
    return np.array(pts)


# el fondo de detras del ciervo: opaco (va montado en la tapa)
pts = puntos_en(POZO.buffer(-1.0).difference(SIL_CIERVO.buffer(1.0)), 900, Z_SUELO - 0.8)
fr_o = (P.contains(pts) | T.contains(pts)).mean()
fr_l = L.contains(pts).mean()
log(f'  detras del fondo (fuera del ciervo): {fr_o*100:.1f} % opaco, '
    f'{fr_l*100:.1f} % translucido')
chk(fr_o > 0.97, 'el fondo del nicho es opaco macizo: por ahi no sale luz')
chk(fr_l < 0.02, 'el translucido no llega al fondo del nicho')
chk(Z_SUELO - Z_TRASERA > 8, f'fondo del nicho bien grueso ({Z_SUELO - Z_TRASERA:.1f} mm)')

# el escalon interno: el tubo translucido en toda la caida del pozo
tubo = POZO.buffer(OFF_LUZ, join_style=JS, mitre_limit=8).difference(POZO)
peor_t = 0.0
for z in np.linspace(Z_SUELO + 0.2, Z_CORONA - 0.2, 24):
    falta = tubo.difference(xy_material(L, z).buffer(0.05)).area / tubo.area
    peor_t = max(peor_t, falta)
chk(peor_t < 0.01, f'el escalon interno es translucido en toda su caida '
                   f'(falta como mucho {peor_t*100:.2f} % del tubo)')

# la corona: translucida, plana en Z_CORONA y sin nada opaco delante
g = xy_material(L, Z_CORONA - 0.1)
cub = g.intersection(CORONA).area / CORONA.area
chk(cub > 0.99, f'la corona es translucida en toda su planta ({cub*100:.1f} %)')
up = (L.face_normals[:, 2] > 0.999)
en_corona = shapely.contains(CORONA.buffer(-0.3), shapely.points(L.triangles_center[:, :2]))
cara = up & en_corona & (L.triangles_center[:, 2] > Z_JUNTA)
dz = np.abs(L.triangles[cara][:, :, 2] - Z_CORONA).max() if cara.any() else 99
chk(dz < 0.005, f'la cara de la corona es un plano: Z = {Z_CORONA:+.2f} '
                f'+/- {dz:.4f} mm ({cara.sum()} triangulos)')
tapa_c = max(xy_material(P, z).intersection(CORONA.buffer(-0.3)).area
             for z in np.linspace(Z_CORONA + 0.1, Z_FRENTE - 0.1, 12))
chk(tapa_c < 0.5, f'nada opaco delante de la corona ({tapa_c:.1f} mm2)')
g_r = g.intersection(AEX.buffer(1.0).difference(POZO.buffer(1.0)))
dev = contorno(g_r).symmetric_difference(AEX).area / AEX.exterior.length
chk(dev < 0.02, f'el borde exterior de la corona es el poligono limpio '
                f'(desvio medio {dev:.4f} mm)')

# el marco exterior no emite: la luz no asoma fuera de la corona
fuera = max(xy_material(L, z).difference(AEX.buffer(0.05)).area
            for z in np.linspace(Z_TRASERA + 0.5, Z_CORONA - 0.1, 16))
alto = L.vertices[:, 2] > Z_CORONA + 0.01
asoma = (~shapely.contains(POZO, shapely.points(L.vertices[alto][:, :2]))).sum()
chk(fuera < 0.5 and asoma == 0,
    f'la luz no toca el marco: {fuera:.2f} mm2 fuera de la corona, '
    f'{asoma} vertices por encima de ella fuera del pozo')

# el ciervo, translucido
ciervo_a = xy_material(L, Z_SUELO + CIERVO_RELIEVE / 2).intersection(POZO.buffer(-0.5)).area
chk(ciervo_a > 300, f'el ciervo es translucido ({ciervo_a:.0f} mm2 a media altura)')

log('')
log('3b. LA FALDA Y EL ESCALON VISIBLE DEL MARCO')
# el rebaje de la corona es un prisma de AEX: donde el marco del original sube
# por encima de la corona dentro de AEX, el corte deja una pared vertical vista
b = AEX.buffer(HOLGURA / 2, join_style=JS, mitre_limit=8).exterior
d = shapely.distance(shapely.points(P.triangles_center[:, :2]), b)
vis = (d < 0.02) & (np.abs(P.face_normals[:, 2]) < 0.05) & \
      (P.triangles_center[:, 2] > Z_CORONA + 0.3)
s = np.linspace(0, b.length, 600, endpoint=False)
mues = np.array([b.interpolate(t).coords[0] for t in s])
hmax = np.zeros(len(s))
if vis.any():
    _, k = cKDTree(mues).query(P.triangles_center[vis][:, :2])
    np.maximum.at(hmax, k, P.triangles[vis][:, :, 2].max(1) - Z_CORONA)
paso = b.length / len(s)
ancho_c = np.array([POZO.exterior.distance(Point(p)) for p in mues])
_pared = P.submesh([np.where((d < 0.02) & (np.abs(P.face_normals[:, 2]) < 0.05))[0]], append=True)
_arriba = trimesh.intersections.slice_mesh_plane(_pared, [0, 0, 1], [0, 0, Z_CORONA + 0.3])
log(f'  marco cortado por encima de la corona: {_arriba.area:.0f} mm2 de pared nueva '
    f'a la vista, en {(hmax > 0.5).sum()*paso:.0f} mm de {b.length:.0f} mm de contorno, '
    f'hasta {hmax.max():.1f} mm de alto')
log(f'  en esos tramos la corona mide {ancho_c[hmax > 0.5].min() if (hmax > 0.5).any() else 0:.1f}'
    f'-{ancho_c[hmax > 0.5].max() if (hmax > 0.5).any() else 0:.1f} mm '
    f'(minimo que pide la falda: {OFF_LUZ + HOLGURA + FALDA + 0.3:.1f} mm)')
# Decision de Sergi (24-09, opcion B): se deja asi para verlo impreso. No cuenta
# como fallo, pero se informa siempre por si se cambia a la opcion A.
log('  ACEPTADO (opcion B): la franja de corona de la falda recorta el marco en esos tramos')

log('')
log('4. EL MONTAJE REPRODUCE EL MODELO ORIGINAL')
if OBJ is None:
    log('  NO EJECUTADA: no encuentro el OBJ de Meshy (ponlo como meshy.obj en esta carpeta)')
    no_ejecutadas.append('4')
else:
    orig = trimesh.load(OBJ, process=False)
    orig.apply_scale(S)
    orig = trimesh.intersections.slice_mesh_plane(
        orig, plane_normal=[0, 0, 1], plane_origin=[0, 0, Z_TRASERA], cap=True)
    orig = trimesh.Trimesh(orig.vertices, orig.faces)
    UNION = trimesh.boolean.union([P, L, T], engine=ENGINE)
    peor_ext = 0.0
    for z in np.linspace(Z_TRASERA + 3.6, Z_FRENTE - 0.5, 40):
        a, bb = xy_material(orig, z), xy_material(UNION, z)
        if a.is_empty or bb.is_empty:
            continue
        ca, cb = contorno(a), contorno(bb)
        dif = ca.symmetric_difference(cb).difference(AEX.buffer(0.5))
        peor_ext = max(peor_ext, dif.area / ca.length)
    chk(peor_ext < 0.05, f'silueta exterior intacta fuera de la corona ({peor_ext:.3f} mm)')

    # superficie VISTA del original: fuera de la corona tiene que seguir igual
    # (0,3 mm); dentro, el pozo y la corona se han enderezado a proposito
    # (tolerancia 1,2 mm, la de preparar.py)
    sup, _ = trimesh.sample.sample_surface(orig, 4000)
    dd = np.abs(trimesh.proximity.signed_distance(UNION, sup))
    xy = shapely.points(sup[:, :2])
    vista = (~shapely.contains(SIL_CIERVO.buffer(0.6), xy)) & (sup[:, 2] > Z_TRASERA + 3.5)
    dentro = shapely.contains(AEX.buffer(0.3), xy)
    mal_m = vista & ~dentro & (dd > 0.3)
    # dentro de AEX: por encima de la corona es el marco que quita la falda
    # (opcion B, aceptada); por debajo, las paredes del pozo enderezadas
    b_ok = vista & dentro & (sup[:, 2] > Z_CORONA + 0.5)
    pz = vista & dentro & ~b_ok
    mal_c = pz & (dd > 1.2)
    log(f'  marco: {mal_m.sum()} de {(vista & ~dentro).sum()} puntos se apartan > 0,3 mm')
    log(f'  marco quitado por la falda (opcion B, aceptado): {(b_ok & (dd > 1.2)).sum()} puntos')
    if pz.any():
        log(f'  pozo y corona: {mal_c.sum()} de {pz.sum()} puntos se apartan > 1,2 mm; '
            f'percentiles 50/90/99/max: {np.round(np.percentile(dd[pz], [50, 90, 99, 100]), 2).tolist()} mm')
    chk(mal_m.sum() / max((vista & ~dentro).sum(), 1) < 0.005, 'el marco visto queda intacto')
    chk(mal_c.sum() / max(pz.sum(), 1) < 0.01,
        'el pozo y la corona se apartan del original como mucho la tolerancia de enderezado')

log('')
log('5. HOLGURAS Y RECORRIDO DE MONTAJE')
smp, _ = trimesh.sample.sample_surface(L, 4000)
d = trimesh.proximity.signed_distance(P, smp)
chk(d.max() < 0.05, f'la pieza de luz no invade la piedra (maximo {d.max():+.3f} mm)')
cerca = np.sort(-d[(d < 0) & (d > -1.0)])
if len(cerca):
    log(f'  holgura donde se tocan: min {cerca[0]:.2f}  mediana '
        f'{np.median(cerca):.2f}  max {cerca[-1]:.2f} mm')


def recorrido(pieza, nombre, sentido, contra=(),
              pasos=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 30, 50)):
    """La pieza se desplaza por TODO el camino, no solo la posicion final."""
    peor, peor_d = 0.0, 0
    for d in pasos:
        q = pieza.copy()
        q.apply_translation([0, 0, d * sentido])
        for otra in (P,) + contra:
            v = trimesh.boolean.intersection([q, otra], engine=ENGINE).volume
            if v > peor:
                peor, peor_d = v, d
    lado = 'por delante' if sentido > 0 else 'por detras'
    chk(peor < 30, f'{nombre} entra y sale {lado} sin chocar '
                   f'(maximo solape en el recorrido: {peor:.1f} mm3'
                   + (f' a {peor_d} mm)' if peor > 0.01 else ')'))


recorrido(L, 'la pieza de luz', -1)
recorrido(T, 'la tapa con el fondo', -1, contra=(L,))

log('')
log('6. ESPESORES')
peor, peor_z = 99.0, None
for z in np.linspace(Z_TRASERA + 1, Z_CORONA - 0.5, 20):
    w = pared_minima(xy_material(L, z))
    if w and w < peor:
        peor, peor_z = w, z
log(f'  pieza de luz: pared minima {peor:.2f} mm en Z={peor_z:+.1f}')
chk(peor > 1.2, 'pared de la pieza de luz >= 1,2 mm (3 perimetros de 0,4)')

peor_c, peor_cz = 99.0, None
for z in np.linspace(Z_SUELO + 2.0, Z_SUELO + CIERVO_RELIEVE - 2.5, 12):
    w = pared_minima(xy_material(L, z).intersection(POZO.buffer(-0.5)))
    if w and w < peor_c:
        peor_c, peor_cz = w, z
log(f'  ciervo en relieve: pared minima {peor_c:.2f} mm en Z={peor_cz:+.1f}')
chk(peor_c > 1.0, 'pared del ciervo >= 1,0 mm')

peor_p, peor_pz = 99.0, None
for z in np.linspace(Z_TRASERA + 4.0, Z_JUNTA - 1, 12):   # por encima del canal del cable
    for x in anillos(xy_material(P, z)):
        for h in x.interiors:
            if Polygon(h).area > 2000:
                dd = x.exterior.distance(h)
                if dd < peor_p:
                    peor_p, peor_pz = dd, z
log(f'  piedra entre la caja del LED y el exterior: minimo {peor_p:.1f} mm en Z={peor_pz:+.1f}')
chk(peor_p > 5, 'la caja del LED queda enterrada en piedra')

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


# zona donde se ACEPTAN soportes (decision de Sergi, 24-09): solo bajo el
# ciervo de la pieza de luz, dentro del pozo. Su lomo va contra el fondo y las
# marcas no se ven.
ZONA_SOPORTE = {'luz': (POZO.buffer(-0.3), Z_SUELO - 0.5, Z_SUELO + CIERVO_RELIEVE + 0.5)}
for n, m in (('piedra', P), ('luz', L), ('tapa', T)):
    z0, z1 = m.bounds[0][2], m.bounds[1][2]
    dz = 0.4
    peor_a, peor_z, peor_g, prev = 0.0, None, None, None
    islas_ok, islas_mal = [], []
    for z in np.arange(z0 + 0.25, z1 - 0.25, dz):
        cur = xy_material(m, z)
        if cur.is_empty:
            continue
        if prev is not None:
            libre = cur.difference(prev.buffer(dz))
            # islas: trozos de la capa que no tocan NADA de la capa de debajo
            for q in anillos(cur):
                if q.area > 0.05 and not q.intersects(prev.buffer(0.05)):
                    zs = ZONA_SOPORTE.get(n)
                    dentro = zs and zs[1] <= z <= zs[2] and zs[0].contains(q)
                    (islas_ok if dentro else islas_mal).append((round(float(z), 1), q))
            libre = libre.difference(unary_union([q for _, q in islas_ok + islas_mal])) \
                if islas_ok or islas_mal else libre
            if libre.area > peor_a:
                peor_a, peor_z, peor_g = libre.area, z, libre
        prev = cur
    w = ancho(peor_g) if peor_g is not None else 0.0
    zt = f'{peor_z:+.1f}' if peor_z is not None else '  -  '
    log(f'  {n:7s} peor capa sin apoyo: {peor_a:6.1f} mm2 en Z={zt}, '
        f'puente de {w:.1f} mm')
    # un puente apoyado en los dos lados hasta 15 mm lo hace el laminador solo;
    # lo que no vale es un voladizo en el aire
    chk(w < 15.0, f'{n}: puentes que el laminador hace solo (el peor, {w:.1f} mm)')
    if islas_ok:
        log(f'  {n:7s} {len(islas_ok)} islas bajo el ciervo, entre Z={islas_ok[0][0]:+.1f} y '
            f'{islas_ok[-1][0]:+.1f}: LLEVAN SOPORTE (aceptado)')
    chk(not islas_mal, f'{n}: ninguna isla en el aire fuera de la zona con soporte'
        + (f' ({len(islas_mal)}: Z {sorted(set(z for z, _ in islas_mal))[:6]})' if islas_mal else ''))

log('')
log('8. MEDIDAS')
log(f'  estrella                   {P.extents[0]:.0f} x {P.extents[1]:.0f} mm')
log(f'  grosor piedra / con tapa   {P.extents[2]:.1f} / {P.extents[2]+TAPA_ESP:.1f} mm')
log(f'  nicho                      {Z_CORONA - Z_SUELO:.1f} mm de caida del escalon interno')
log(f'  fondo del nicho (tapa)     {Z_SUELO - Z_TRASERA:.1f} mm')
log(f'  corona                     {CORONA.area:.0f} mm2, cara en Z={Z_CORONA:+.2f}, '
    f'junta en Z={Z_JUNTA:+.2f}')
log(f'  caja del LED               {(AEX.area - POZO.area)/100:.0f} cm2 x '
    f'{Z_JUNTA - Z_TRASERA:.0f} mm')
log(f'  luz                        {L.extents[0]:.0f} x {L.extents[1]:.0f} x '
    f'{L.extents[2]:.1f} mm   {L.volume/1000:.1f} cm3')
log(f'  tapa                       {T.extents[0]:.0f} x {T.extents[1]:.0f} x '
    f'{T.extents[2]:.1f} mm   {T.volume/1000:.1f} cm3')
log(f'  piedra                     {P.volume/1000:.0f} cm3 de solido')
log('')
log('=' * 74)
log(f'{sum(ok)}/{len(ok)} comprobaciones correctas'
    + (f'   (seccion {", ".join(no_ejecutadas)} NO EJECUTADA)' if no_ejecutadas else ''))

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
add([T], [TAP], (0.2, 0.15, 0.97), 'TAPA por fuera (avellanados)')
sheet(ims, cols=3, labels=lab).save(os.path.join(OUT, 'verificacion.png'))

rasterize([P, L, T], (0.06, 0.05, -0.99), up=(0, 1, 0), size=950,
          colors=[(52, 48, 44), (255, 216, 145), (40, 38, 36)],
          bg=(11, 11, 13),
          light=(0.25, 0.35, 1.0)).save(os.path.join(OUT, 'encendida.png'))

# primeros planos de la zona de abajo, con el marco cortado en rojo
from render import _basis
Pr = P.submesh([np.where(vis)[0]], append=True) if vis.any() else None
Pg = P.submesh([np.where(~vis)[0]], append=True)
zims, zlab = [], []
for dcam, cen, span, n in (((0, 0, -1), (-15, -58, 10), 80, 'zona de abajo, de frente (rojo = marco cortado)'),
                           ((0.25, -0.35, -0.9), (-15, -58, 10), 80, 'zona de abajo, desde arriba-derecha'),
                           ((-0.45, -0.2, -0.87), (-40, -55, 10), 70, 'esquina inferior izquierda'),
                           ((0, 0, -1), (0, 0, 0), 215, 'frente completo')):
    ms = [Pg] + ([Pr] if Pr is not None else []) + [L, T]
    cs = [PIE] + ([(230, 40, 40)] if Pr is not None else []) + [LUZC, TAP]
    zims.append(rasterize(ms, dcam, size=620, colors=cs,
                          frame=(np.array(cen) @ _basis(dcam, (0, 1, 0)).T, span)))
    zlab.append(n)
sheet(zims, cols=2, labels=zlab).save(os.path.join(OUT, 'falda_zoom.png'))

# planta del contorno: donde el rebaje de la corona corta marco visible
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
EST = contorno(xy_material(P, Z_TRASERA + 0.5))
fig, ax = plt.subplots(figsize=(9, 9))
for poly, fc, ec, lw in ((EST, '#8f887c', 'k', 0.8), (AEX, '#ffc660', '#a06a00', 0.8),
                         (POZO, '#2a2a2e', 'k', 0.8)):
    for q in anillos(poly):
        ax.fill(*q.exterior.xy, fc=fc, ec=ec, lw=lw)
corte = hmax > 0.5
sc = ax.scatter(mues[corte, 0], mues[corte, 1], c=hmax[corte], cmap='Reds', s=14,
                vmin=0, vmax=max(hmax.max(), 1), zorder=5)
if corte.any():
    plt.colorbar(sc, ax=ax, shrink=0.6, label='marco cortado por encima de la corona (mm)')
ax.set_aspect('equal'); ax.set_title('Planta: corona (amarillo) y donde su rebaje corta el marco (rojo)')
ax.set_xlabel('X mm'); ax.set_ylabel('Y mm (arriba)')
fig.savefig(os.path.join(OUT, 'falda_marco.png'), dpi=110, bbox_inches='tight')
plt.close(fig)
log('hecho')
