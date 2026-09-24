# -*- coding: utf-8 -*-
"""
Ciudadela / Starlit Stag  ->  lampara imprimible en TRES piezas.

  1_piedra  (opaco)       el marco de la estrella.
  2_luz     (translucido) UNA sola pieza: la corona iluminada que rodea la boca
                          + el escalon interno (la pared del pozo) + el ciervo en
                          relieve + una falda exterior oculta que la hace
                          imprimible y aloja el LED.
  3_tapa    (opaco)       cierra por detras y lleva montado el FONDO del nicho,
                          la pared de detras del ciervo, que no emite luz.

Criterio de construccion: **nada que encaje se corta contra la malla de Meshy**.
El pozo, la corona, la falda, el rebaje y el pedestal salen de dos poligonos
limpios (lados rectos, esquinas vivas) y de dos planos de verdad. Asi las juntas
son planas, la holgura es una sola y no quedan astillas ni costuras.

Lo unico que conserva la superficie original de Meshy es lo que se ve por fuera:
el marco de la estrella con su textura, y el ciervo.

Orientacion de impresion: tal cual se exporta, cara plana en la cama y todas las
cavidades abriendo hacia arriba -> sin soportes.
"""
import os
import numpy as np
import trimesh
import manifold3d
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.ops import unary_union, polygonize
from geo import xy_material

# ----------------------------------------------------------------------------
# PARAMETROS
# ----------------------------------------------------------------------------
OUT = os.path.dirname(os.path.abspath(__file__))
# el OBJ de Meshy: una copia en esta carpeta como meshy.obj, o donde se descargo
OBJ = next((p for p in (
    os.path.join(OUT, 'meshy.obj'),
    r'C:/Users/sergi/Downloads/Meshy_AI_Starlit_Stag_0923134854_generate_obj'
    r'/Meshy_AI_Starlit_Stag_0923134854_generate_obj'
    r'/Meshy_AI_Starlit_Stag_0923134854_generate.obj') if os.path.exists(p)),
    os.path.join(OUT, 'meshy.obj'))

ANCHO_MM      = 200.0   # ancho final de la estrella (manda la escala)
APLANAR       = 0.5     # mm de textura que se quitan a la trasera para dejarla plana

TOL_POZO      = 1.2     # con que tolerancia se enderezan los contornos
TOL_CORONA    = 1.2
# borde exterior de la corona: 'dentro' = 0-2,4 mm antes del pie del escalon
# (deja una tira de piedra a la altura de la corona); 'fuera' = hasta la pared
# del escalon (la corona llega a la pared; el corte entra 0-2*TOL_FUERA en ella
# y, al cruzar en rasante la pared texturada de Meshy, deja costura en sierra)
CORONA_BORDE  = 'canto'
TOL_FUERA     = 0.6
# 'canto' = por el canto de arriba de la pared corona->escalon: el rebaje se
# lleva la rampa de Meshy entera y deja una pared vertical cuyo canto corta la
# cara plana del escalon en perpendicular (sin rasantes, sin sierra)
CANTO_BAJO    = 0.5     # el canto se toma esto por debajo del plano del escalon
CANTO_FUERA   = 0.4     # y el borde se saca esto hacia fuera, sobre la cara plana
CANTO_TOL     = 0.5     # tolerancia de enderezado de ese borde
DIENTE_AREA   = 2.0     # vertices de los contornos que se quitan: triangulo < esto (mm2)
ESQUINA_MAX   = 3.0     # lados cortos: se rehace la esquina si el cruce esta a < esto (mm)
ESQUINA_AREA  = 5.0     # ... y el triangulo que cambia es < esto (mm2)
ESQUINA_LADO  = 4.0     # ... y el lado corto mide < esto (mm)

PARED         = 2.0     # pared translucida (tubo del pozo)
FALDA         = 2.0     # pared de la falda exterior, oculta en la piedra
HOLGURA       = 0.2     # holgura unica de todos los encajes
ESP_CORONA    = 3.5     # espesor de la placa de la corona

CIERVO_RELIEVE = 15.0   # cuanto sobresale el ciervo de la pared del fondo
CIERVO_PARED   = 2.2    # pared del ciervo (erosion 3D real)
CIERVO_BOCA    = 1.2    # pared que queda alrededor de la boca trasera del ciervo
CIERVO_HUECO_MIN = 8.0  # solo se vacia donde la silueta es mas ancha que esto
                        # (cuerpo, cuello, cabeza): en patas y cuernas el hueco
                        # acabaria en laminas de vacio que se ven al trasluz
CIERVO_CLAVO   = 4.0    # cuanto se prolongan las pezunas hacia el suelo del pozo
CIERVO_SUELA   = 1.0    # ultimo tramo de cada pata que se prolonga (mm)
                        # (se recortan a media pared del tubo: no asoman a la caja)

TAPA_ESP      = 3.0     # espesor de la tapa (superpuesta a la trasera)
TAPA_VUELO    = 5.0     # cuanto sobresale la tapa del hueco
TAPA_ENCASTRE = 2.0     # espigo de la tapa que centra la pieza de luz
TAPA_ESPIGO_W = 2.0
CAJA_MIN      = 1.5     # la caja del LED no tiene zonas mas estrechas que esto (mm):
                        # donde tubo y falda quedarian casi pegados, se macizan
ANCHO_MIN     = 1.2     # espigo y agujero del pedestal: nada mas estrecho que esto

TORNILLO_D    = 2.7     # taladro para M3 autorroscante
TORNILLO_H    = 8.0
TORNILLO_R    = 4.5     # distancia del borde del hueco
TORNILLO_CAB  = 6.2     # avellanado de 90 grados, abierto hacia la cara de fuera
N_TORNILLOS   = 5

CABLE_ANCHO   = 6.0     # canal del cable en la trasera
CABLE_ANCHO_T = 3.5     # anchura arriba -> se imprime sin soporte
CABLE_PROF    = 3.0

ENGINE = 'manifold'
JS = 2  # mitre
TOL_PULIDO = 1e-3       # cuanto puede moverse una superficie al pulir (mm)


# ----------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------
def log(*a):
    print(*a, flush=True)


def sin_dientes(poly, nombre=''):
    """Quita los dientes que deja enderezar un contorno, sin perder esquinas:
    1. zigzags: vertices cuyo triangulo con sus vecinos mide < DIENTE_AREA;
    2. lados cortos (< ESQUINA_LADO) entre dos largos (puntas, esquinas mordidas): sus dos
       extremos se cambian por el cruce de los lados vecinos, si ese cruce esta
       cerca (< ESQUINA_MAX) y el triangulo que se gana o pierde es < ESQUINA_AREA.
       Los escalones de verdad no cambian: sus lados vecinos se cruzan lejos."""
    c = [np.array(x) for x in np.array(poly.exterior.coords)[:-1]]
    hechos = []

    def tri(a, b, d):
        return 0.5 * abs((b[0] - a[0]) * (d[1] - a[1]) - (d[0] - a[0]) * (b[1] - a[1]))

    cambio = True
    while cambio and len(c) > 4:
        cambio = False
        n = len(c)
        areas = [tri(c[i - 1], c[i], c[(i + 1) % n]) for i in range(n)]
        i = int(np.argmin(areas))
        if areas[i] < DIENTE_AREA:
            hechos.append(('zigzag', np.round(c[i], 1).tolist(), round(areas[i], 2)))
            c.pop(i)
            cambio = True
            continue
        # lados cortos, del mas corto al mas largo
        lados = sorted(range(n), key=lambda k: np.linalg.norm(c[(k + 1) % n] - c[k]))
        for k in lados:
            if np.linalg.norm(c[(k + 1) % n] - c[k]) >= ESQUINA_LADO:
                break
            a0, a1 = c[k - 1], c[k]                 # lado anterior
            b0, b1 = c[(k + 1) % n], c[(k + 2) % n]  # lado siguiente
            d1, d2 = a1 - a0, b1 - b0
            den = d1[0] * d2[1] - d1[1] * d2[0]
            if abs(den) < 1e-9:
                continue
            t = ((b0[0] - a0[0]) * d2[1] - (b0[1] - a0[1]) * d2[0]) / den
            x = a0 + t * d1
            medio = (a1 + b0) / 2
            if np.linalg.norm(x - medio) > ESQUINA_MAX or tri(a1, b0, x) > ESQUINA_AREA:
                continue
            hechos.append(('esquina', np.round(a1, 1).tolist(), np.round(b0, 1).tolist(),
                           '->', np.round(x, 1).tolist()))
            c[k] = x
            c.pop((k + 1) % n)
            cambio = True
            break
    out = Polygon(c)
    assert out.is_valid, f'{nombre}: el contorno sin dientes no es valido'
    for h in hechos:
        log(f'  {nombre}: {h}')
    return out


def secciones_xy(mesh, z, min_area=1.0):
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return []
    lines = [LineString(s.vertices[e.points][:, :2]) for e in s.entities
             if len(e.points) > 2]
    if not lines:
        return []
    return [p for p in polygonize(unary_union(lines)) if p.area > min_area]


def mayor(poly):
    if poly.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return max([g for g in poly.geoms if g.geom_type == 'Polygon'],
                   key=lambda g: g.area)
    return poly


def off(poly, d):
    return mayor(poly.buffer(d, join_style=JS, mitre_limit=8))


def abrir(poly, ancho):
    """Quita las partes de un poligono mas estrechas que `ancho` (apertura). Los
    extremos que quedan son redondos: sin puntas finas."""
    return poly.buffer(-ancho / 2, join_style=JS, mitre_limit=8).buffer(
        ancho / 2, join_style=1).intersection(poly)


def prisma(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, height=z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def prisma_multi(poly, z0, z1, min_area=0.5):
    poly = poly.buffer(0)
    gs = list(poly.geoms) if poly.geom_type != 'Polygon' else [poly]
    ms = [prisma(g, z0, z1) for g in gs
          if g.geom_type == 'Polygon' and g.area > min_area and g.is_valid]
    assert ms, 'poligono vacio al extruir'
    return ms[0] if len(ms) == 1 else trimesh.boolean.union(ms, engine=ENGINE)


def _direcciones():
    dirs = [np.array(v, float) for v in
            ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    dirs += [np.array(v, float) / np.sqrt(3) for v in
             ((1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
              (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1))]
    return dirs


def erosionar(mesh, r):
    """Erosion 3D: interseccion de copias trasladadas (6 ejes + 8 diagonales).
    Calibrado sobre una esfera: con r=2,2 deja entre 1,87 y 2,20 mm."""
    out = mesh
    for d in _direcciones():
        c = mesh.copy()
        c.apply_translation(d * r)
        out = trimesh.boolean.intersection([out, c], engine=ENGINE)
    return out


def limpiar(mesh, aviso=50.0):
    """Tira las migas de las booleanas. Si se desprende algo grande es un fallo
    de diseno, no una miga: para el script."""
    cs = mesh.split(only_watertight=False)
    if len(cs) <= 1:
        return mesh
    cs = sorted(cs, key=lambda c: -c.volume)
    if cs[1].volume > aviso:
        raise AssertionError(
            f'se ha desprendido un trozo de {cs[1].volume:.0f} mm3 en '
            f'{np.round(cs[1].bounds, 1).tolist()}: hay algo aislado')
    log(f'    (descartadas {len(cs)-1} migas, la mayor de {cs[1].volume:.2f} mm3)')
    return cs[0]


def degenerados(mesh):
    """Triangulos sin forma: con una arista nula o tan aplastados (aguja) que su
    altura no llega a 0,1 micras. Los triangulos pequenos pero bien formados no
    cuentan: no son un defecto."""
    t = mesh.triangles
    ls = np.linalg.norm(t[:, [1, 2, 0]] - t, axis=2)
    h = 2 * mesh.area_faces / np.maximum(ls.max(1), 1e-12)
    return (ls.min(1) < 1e-6) | (h < 1e-4)


def sanear(mesh, corta=0.01, max_iter=40):
    """Elimina los triangulos degenerados que deja simplify sin mover la superficie:
    - con un lado de menos de `corta`: se colapsa ese lado, solo si no pellizca
      la malla (los dos extremos solo comparten los 2 vecinos opuestos:
      condicion de enlace). La superficie se mueve menos de `corta`;
    - aguja (el tercer vertice cae sobre el lado largo), o si el colapso no se
      puede: se voltea el lado largo. La superficie se mueve menos que la
      altura de la aguja (< 0,1 micras)."""
    V = np.asarray(mesh.vertices, float).copy()
    F = np.asarray(mesh.faces).copy()
    for _ in range(max_iter):
        t = V[F]
        ls = np.linalg.norm(t[:, [1, 2, 0]] - t, axis=2)      # lado k: F[k] -> F[k+1]
        area = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
        h = 2 * area / np.maximum(ls.max(1), 1e-12)
        malas = np.where((h < 1e-4) | (ls.min(1) < 1e-6))[0]
        if not len(malas):
            break
        e = np.stack([F, np.roll(F, -1, axis=1)], axis=2).reshape(-1, 2)
        mapa = dict(zip(map(tuple, e), np.repeat(np.arange(len(F)), 3)))
        vecinos = {}
        for a, b in e:
            vecinos.setdefault(a, set()).add(b)
            vecinos.setdefault(b, set()).add(a)
        tocadas, borrar, hechos = set(), set(), 0

        def colapsar(f):
            k = int(np.argmin(ls[f]))
            a, b = F[f][k], F[f][(k + 1) % 3]
            g = mapa.get((b, a))
            if g is None or g in tocadas:
                return False
            opuestos = {F[f][(k + 2) % 3]} | {v for v in F[g] if v != a and v != b}
            if (vecinos[a] & vecinos[b]) != opuestos:
                return False
            caras_b = set(np.where((F == b).any(1))[0].tolist())
            if tocadas & caras_b:
                return False
            F[F == b] = a
            borrar.update((f, g))
            tocadas.update(caras_b | {f, g})
            return True

        def voltear(f):
            k = int(np.argmax(ls[f]))
            a, b, c = F[f][k], F[f][(k + 1) % 3], F[f][(k + 2) % 3]
            g = mapa.get((b, a))
            if g is None or g in tocadas:
                return False
            d = [v for v in F[g] if v != a and v != b][0]
            if c == d or d in vecinos[c]:
                return False
            F[f] = (a, d, c)
            F[g] = (d, b, c)
            tocadas.update((f, g))
            return True

        for f in malas:
            if f in tocadas:
                continue
            if ls[f].min() < corta:
                ok = colapsar(f) or voltear(f)
            else:
                ok = voltear(f) or colapsar(f)
            hechos += ok
        if borrar:
            F = np.delete(F, sorted(borrar), axis=0)
        if not hechos:
            break
    m = trimesh.Trimesh(V, F, process=False)
    m.remove_unreferenced_vertices()
    return m


def pulir(mesh, nombre='', tol=TOL_PULIDO):
    """Quita las astillas de las booleanas sin abrir la malla.

    1. Antes de tocar nada exige que la malla que sale de la booleana siga
       cerrada al fusionar los vertices que coinciden. Si no, dos solidos se
       tocan en una arista o un punto (un pellizco, un filo de espesor cero).
       Eso no es suciedad de la malla sino un fallo de diseno, y como en
       limpiar() se para el script en vez de disimularlo.
    2. Colapsa aristas cortas y triangulos astilla DENTRO de manifold, que por
       construccion no puede dejar la malla abierta, sin mover ninguna
       superficie mas de `tol`.
    3. Quita los triangulos degenerados que queden (sanear) y exige que no
       quede ninguno."""
    f = trimesh.Trimesh(mesh.vertices.copy(), mesh.faces.copy(), process=False)
    f.merge_vertices()
    if not f.is_watertight:
        _, inv, cnt = np.unique(mesh.vertices, axis=0, return_inverse=True,
                                return_counts=True)
        dup = mesh.vertices[cnt[inv] > 1]
        raise AssertionError(
            f'{nombre}: {len(dup)} vertices en contacto sin espesor en '
            f'Z {np.unique(np.round(dup[:, 2], 2))[:6].tolist()}, '
            f'XY ~{np.round(dup[:, :2].mean(0), 1).tolist()}: hay dos solidos '
            f'que se tocan en una arista o un punto')
    M = manifold3d.Manifold(manifold3d.Mesh(
        vert_properties=np.asarray(mesh.vertices, np.float32),
        tri_verts=np.asarray(mesh.faces, np.uint32)))
    g = M.simplify(tol).to_mesh()
    m = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts, process=False)
    m = sanear(m)
    f = trimesh.Trimesh(m.vertices.copy(), m.faces.copy(), process=False)
    f.merge_vertices()
    assert m.is_watertight and m.is_winding_consistent and f.is_watertight, \
        f'{nombre}: el pulido abrio la malla'
    assert not degenerados(m).any(), f'{nombre}: quedan {degenerados(m).sum()} triangulos degenerados'
    log(f'    pulido {nombre}: {len(mesh.faces)} -> {len(m.faces)} caras, '
        f'astillas <0,001 mm2 {(mesh.area_faces < 1e-3).sum()} -> '
        f'{(m.area_faces < 1e-3).sum()}, degenerados {degenerados(mesh).sum()} -> '
        f'{degenerados(m).sum()}, volumen {abs(m.volume - mesh.volume):.2f} mm3 '
        f'de diferencia')
    return m


def bo(op, partes):
    return getattr(trimesh.boolean, op)(partes, engine=ENGINE)


# ----------------------------------------------------------------------------
# 1. cargar, escalar y aplanar la trasera
# ----------------------------------------------------------------------------
log('cargando', os.path.basename(OBJ))
malla = trimesh.load(OBJ, process=False)
S = ANCHO_MM / malla.extents[0]
malla.apply_scale(S)
log(f'  escala {S:.4f} mm/u  ->  {np.round(malla.extents, 2)} mm   '
    f'cerrada={malla.is_watertight}')

Z_TRASERA = round(malla.bounds[0][2] + APLANAR, 2)
malla = trimesh.intersections.slice_mesh_plane(
    malla, plane_normal=[0, 0, 1], plane_origin=[0, 0, Z_TRASERA], cap=True)
malla = trimesh.Trimesh(malla.vertices, malla.faces)
Z_FRENTE = malla.bounds[1][2]
log(f'  trasera aplanada en Z={Z_TRASERA}   frente Z={Z_FRENTE:.2f}')


# ----------------------------------------------------------------------------
# 2. los dos planos y los dos contornos limpios
# ----------------------------------------------------------------------------
def plano_dominante(mesh, zmin, zmax):
    n = mesh.face_normals
    zc = mesh.vertices[mesh.faces][:, :, 2].mean(1)
    sel = (n[:, 2] > 0.99) & (zc > zmin) & (zc < zmax)
    h, e = np.histogram(zc[sel], bins=600, weights=mesh.area_faces[sel])
    i = int(np.argmax(h))
    return (e[i] + e[i + 1]) / 2.0


Z_SUELO = plano_dominante(malla, Z_TRASERA + 2, 0)            # fondo del nicho
Z_CORONA = plano_dominante(malla, Z_SUELO + 5, Z_SUELO + 40)  # cara de la corona
Z_JUNTA = Z_CORONA - ESP_CORONA
log(f'  plano del fondo    Z={Z_SUELO:.2f}')
log(f'  plano de la corona Z={Z_CORONA:.2f}   junta en Z={Z_JUNTA:.2f}')


def anillo_pozo(z):
    ps = secciones_xy(malla, z, min_area=200)
    ps.sort(key=lambda p: -p.area)
    return max((Polygon(r) for r in ps[0].interiors), key=lambda g: g.area)


# POZO: envolvente del pozo en toda su altura, enderezada. Es la cara VISTA de
# la pared del pozo, y de ella salen tubo, ranura y pedestal. Se muestrea solo
# por debajo de la junta: mas arriba, los rellanos de la corona (en la esquina
# de la roca hay uno a Z~+9) salen como hueco y la envolvente los convertia en
# un pocillo hasta el fondo que el original no tiene.
_env = mayor(unary_union([anillo_pozo(z) for z in
                          np.linspace(Z_SUELO + 0.3, Z_JUNTA - 0.5, 22)])).buffer(0)
POZO = sin_dientes(mayor(_env.simplify(TOL_POZO)), 'POZO')
log(f'  POZO: {len(_env.exterior.coords)} vertices -> {len(POZO.exterior.coords)-1} '
    f'lados rectos, desviacion max {_env.hausdorff_distance(POZO):.2f} mm, '
    f'area {POZO.area:.0f} mm2')

qs = secciones_xy(malla, Z_TRASERA + 0.5, min_area=200)
qs.sort(key=lambda p: -p.area)
ESTRELLA = Polygon(qs[0].exterior)


def mapa_frontal(size=900):
    """Z de la cara frontal del modelo, rasterizado."""
    from PIL import Image, ImageDraw
    b = malla.bounds
    ox, oy = (b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2
    span = max(b[1][0] - b[0][0], b[1][1] - b[0][1]) * 1.02
    sc = size / span
    V, F, N = malla.vertices, malla.faces, malla.face_normals
    X = (V[:, 0] - ox) * sc + size / 2
    Y = size / 2 - (V[:, 1] - oy) * sc
    f = F[N[:, 2] > 0]
    zc = V[f][:, :, 2].mean(1)
    img = Image.new('F', (size, size), -1e4)
    dr = ImageDraw.Draw(img)
    for i in np.argsort(zc):
        t = f[i]
        dr.polygon([(X[t[0]], Y[t[0]]), (X[t[1]], Y[t[1]]), (X[t[2]], Y[t[2]])],
                   fill=float(zc[i]))
    return np.array(img), (ox, oy, sc, size)


def mascara_a_poligono(mask, geo, cierre=3):
    from scipy import ndimage
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ox, oy, sc, size = geo
    m = ndimage.binary_fill_holes(
        ndimage.binary_closing(mask, np.ones((cierre, cierre))))
    fig = plt.figure()
    cs = plt.contour(m.astype(float), levels=[0.5])
    segs = [sg for coll in cs.allsegs for sg in coll if len(sg) > 8]
    plt.close(fig)
    polis = []
    for sg in segs:
        x = (sg[:, 0] - size / 2) / sc + ox
        y = (size / 2 - sg[:, 1]) / sc + oy
        q = Polygon(np.c_[x, y]).buffer(0)
        if q.area > 50:
            polis.append(q)
    polis.sort(key=lambda q: -q.area)
    out = polis[0]
    for q in polis[1:]:
        out = out.symmetric_difference(q) if out.contains(q) else out.union(q)
    return mayor(out)


# CORONA: la pared iluminada. Se reconoce por su altura y se endereza.
D, GEO = mapa_frontal()
_reg = mascara_a_poligono((D > Z_CORONA - 3.5) & (D < Z_CORONA + 1.2), GEO)
_ext = Polygon(_reg.exterior)
if CORONA_BORDE == 'dentro':
    # se mete TOL hacia dentro antes de enderezar: el contorno recto nunca se
    # sale del escalon original, pero deja una tira de piedra antes de el
    AEX = mayor(_ext.buffer(-TOL_CORONA, join_style=1).simplify(TOL_CORONA))
elif CORONA_BORDE == 'fuera':
    # se saca TOL_FUERA hacia fuera antes de enderezar: el contorno recto cubre
    # toda la zona plana y llega a la pared del escalon (entra 0-2*TOL_FUERA)
    AEX = mayor(_ext.buffer(TOL_FUERA, join_style=1).simplify(TOL_FUERA))
else:   # 'canto'
    Z_ESCALON = plano_dominante(malla, Z_CORONA + 5, Z_CORONA + 14)
    import shapely as _sh
    _ox, _oy, _sc, _n = GEO
    _jj, _ii = np.mgrid[0:_n, 0:_n]
    _cerca = _sh.contains(_ext.buffer(8.0), _sh.points(
        ((_ii - _n / 2) / _sc + _ox).ravel(), ((_n / 2 - _jj) / _sc + _oy).ravel())).reshape(D.shape)
    _can = Polygon(mascara_a_poligono((D > Z_CORONA - 3.5) & (D < Z_ESCALON - CANTO_BAJO) & _cerca,
                                      GEO).exterior)
    AEX = mayor(_can.buffer(CANTO_FUERA, join_style=1).simplify(CANTO_TOL))
    log(f'  escalon en Z={Z_ESCALON:.2f}; borde de la corona por su canto '
        f'({_can.area - _ext.area:.0f} mm2 mas que la zona plana)')
_min = off(POZO, PARED + HOLGURA + FALDA + 0.3)   # minimo para que quepa la falda
_fuera = _min.difference(_ext)
log(f'  (la falda pide {_fuera.area:.0f} mm2 por fuera del escalon del marco, '
    f'hasta {_ext.exterior.hausdorff_distance(_min.exterior) if not _fuera.is_empty else 0:.1f} mm)')
AEX = sin_dientes(mayor(mayor(AEX.union(_min)).simplify(0.3)), 'AEX')
CORONA = mayor(AEX.difference(POZO))
log(f'  CORONA: {len(_ext.exterior.coords)} vertices -> '
    f'{len(AEX.exterior.coords)-1} lados rectos, area {CORONA.area:.0f} mm2, '
    f'ancho medio {CORONA.area/((AEX.exterior.length + POZO.exterior.length)/2):.1f} mm')

OFF_LUZ = PARED
OFF_PIEDRA = PARED + HOLGURA
P_TAPA = mayor(AEX.buffer(TORNILLO_R + TAPA_VUELO, join_style=JS, mitre_limit=8)
               .intersection(ESTRELLA.buffer(-4.0, join_style=1)))
log(f'  tapa: bbox {np.round(P_TAPA.bounds, 1)}  margen al borde '
    f'{ESTRELLA.exterior.distance(P_TAPA):.1f} mm')
assert ESTRELLA.contains(P_TAPA), 'la tapa se sale de la estrella'


# ----------------------------------------------------------------------------
# 3. el ciervo, en relieve sobre la pared del fondo
# ----------------------------------------------------------------------------
log('aislando el ciervo...')
caja = prisma(POZO.buffer(-0.5, join_style=JS, mitre_limit=8),
              Z_SUELO + 0.4, Z_CORONA + 4.0)
tr = [c for c in bo('intersection', [malla, caja]).split(only_watertight=False)
      if c.volume > 100]
tr.sort(key=lambda c: -c.volume)
CIERVO = tr[0]
SIL_CIERVO = trimesh.path.polygons.projected(
    CIERVO, normal=[0, 0, 1], precise=True).buffer(0).simplify(0.05)
log(f'  ciervo original: vol {CIERVO.volume:.0f} mm3   Z {CIERVO.bounds[0][2]:.2f}..'
    f'{CIERVO.bounds[1][2]:.2f}   silueta {SIL_CIERVO.area:.0f} mm2')

_atras = CIERVO.bounds[1][2] - (Z_SUELO + CIERVO_RELIEVE)
CIERVO_REL = CIERVO.copy()
CIERVO_REL.apply_translation([0, 0, -_atras])
CIERVO_REL = trimesh.intersections.slice_mesh_plane(
    CIERVO_REL, plane_normal=[0, 0, 1], plane_origin=[0, 0, Z_SUELO], cap=True)
CIERVO_REL = trimesh.Trimesh(CIERVO_REL.vertices, CIERVO_REL.faces)
# boca trasera del relieve: solo dentro de su base real (el lomo es redondeado y
# la base en el plano del fondo es pequena). Si se abriese con la silueta, un
# plano cortaria el lomo donde es casi horizontal y la malla se pellizcaria.
_base = xy_material(CIERVO_REL, Z_SUELO + 0.01).intersection(
    xy_material(CIERVO_REL, Z_SUELO + 0.3))
BOCA_CIERVO = _base.buffer(-CIERVO_BOCA, join_style=1)
# las pezunas quedan a 0,5-1 mm del suelo del pozo. Cada pata se prolonga
# hasta el suelo con su propia forma: envolvente convexa de su ultimo milimetro
# y de ese mismo trozo bajado hasta media pared del tubo. Asi no queda rendija
# bajo las patas ni munones (antes: copia del pie desplazada 4 mm). Se recorta
# a media pared del tubo para no asomar a la caja del LED.
_ym = CIERVO_REL.bounds[0][1]
_suela = bo('intersection', [CIERVO_REL, prisma(sbox(-500, _ym - 1, 500, _ym + CIERVO_SUELA),
                                                 Z_SUELO - 1, Z_SUELO + CIERVO_RELIEVE + 1)])
_pies = []
for _p in _suela.split(only_watertight=False):
    if _p.volume < 0.05:
        continue
    _pies.append(trimesh.convex.convex_hull(np.vstack([_p.vertices,
                                                       _p.vertices - [0, CIERVO_CLAVO, 0]])))
_pies = bo('intersection', [bo('union', _pies) if len(_pies) > 1 else _pies[0],
                            prisma(off(POZO, PARED / 2), Z_SUELO - 1, Z_SUELO + CIERVO_RELIEVE + 1)])
log(f'  {len(_pies.split(only_watertight=False))} pies prolongados hasta el suelo')
CIERVO_REL = bo('union', [CIERVO_REL, _pies])
SIL_REL = trimesh.path.polygons.projected(
    CIERVO_REL, normal=[0, 0, 1], precise=True).buffer(0).simplify(0.05)
log(f'  relieve: reculado {_atras:.1f} mm, Z {Z_SUELO:.2f}..'
    f'{Z_SUELO + CIERVO_RELIEVE:.2f}, vol {CIERVO_REL.volume:.0f} mm3')


# ----------------------------------------------------------------------------
# 4. solidos de corte: todos prismas rectos y planos
# ----------------------------------------------------------------------------
log('construyendo los cortes...')
HUECO_PIEDRA = bo('union', [
    prisma_multi(AEX.buffer(HOLGURA / 2, join_style=JS, mitre_limit=8),
                 Z_TRASERA - 1, Z_JUNTA),                     # caja de la luz
    prisma_multi(CORONA.buffer(HOLGURA / 2, join_style=JS, mitre_limit=8),
                 Z_JUNTA - HOLGURA, Z_FRENTE + 1),            # rebaje de la corona
    prisma_multi(POZO, Z_JUNTA - HOLGURA, Z_FRENTE + 1),      # boca del pozo
])

y_alto = AEX.bounds[1] + 4.0
y_bajo = malla.bounds[0][1] - 1
CANAL = bo('union', [
    prisma(sbox(-CABLE_ANCHO / 2, y_bajo, CABLE_ANCHO / 2, y_alto),
           Z_TRASERA - 1, Z_TRASERA + 0.8),
    prisma(sbox(-CABLE_ANCHO_T / 2, y_bajo, CABLE_ANCHO_T / 2, y_alto),
           Z_TRASERA + 0.8, Z_TRASERA + CABLE_PROF),
])

cx, cy = POZO.centroid.x, POZO.centroid.y
anillo_t = off(AEX, TORNILLO_R)
TORNILLOS = []
for k in range(N_TORNILLOS):
    a = np.radians(90 + 360.0 / N_TORNILLOS * k)
    ray = LineString([(cx, cy), (cx + 400 * np.cos(a), cy + 400 * np.sin(a))])
    it = ray.intersection(anillo_t.exterior)
    pt = list(it.geoms)[-1] if it.geom_type != 'Point' else it
    TORNILLOS.append((pt.x, pt.y))
for x, y in TORNILLOS:
    assert P_TAPA.contains(Point(x, y).buffer(TORNILLO_CAB / 2 + 0.8)), 'tornillo fuera'
    assert not AEX.intersects(Point(x, y).buffer(TORNILLO_D / 2 + 1.0)), 'tornillo en el hueco'
    assert Point(x, y).distance(sbox(-CABLE_ANCHO, -1e4, CABLE_ANCHO, y_alto)) > 3
log('  tornillos en ' + ', '.join(f'({x:.0f},{y:.0f})' for x, y in TORNILLOS))
TALADROS = []
for x, y in TORNILLOS:
    c = trimesh.creation.cylinder(radius=TORNILLO_D / 2, height=TORNILLO_H + 2)
    c.apply_translation([x, y, Z_TRASERA + (TORNILLO_H + 2) / 2 - 1])
    TALADROS.append(c)


# ----------------------------------------------------------------------------
# 5. PIEDRA
# ----------------------------------------------------------------------------
log('piedra...')
PIEDRA = bo('difference', [malla, HUECO_PIEDRA])
PIEDRA = bo('difference', [PIEDRA, CANAL])
PIEDRA = limpiar(bo('difference', [PIEDRA] + TALADROS))
PIEDRA = pulir(PIEDRA, 'piedra')


# ----------------------------------------------------------------------------
# 6. LUZ: corona + escalon interno + falda + ciervo, todo de una pieza
# ----------------------------------------------------------------------------
log('pieza de luz...')
# caja del LED: el hueco entre tubo y falda, sin zonas estrechas. Donde los dos
# quedarian casi pegados (rendija de menos de CAJA_MIN) se maciza: tubo y falda
# salen de un solo prisma sin ranuras.
CAJA = abrir(AEX.buffer(-FALDA, join_style=JS, mitre_limit=8)
             .difference(off(POZO, OFF_LUZ)), CAJA_MIN)
LUZ = bo('union', [
    prisma_multi(CORONA, Z_JUNTA, Z_CORONA),                                # corona
    bo('difference', [prisma_multi(AEX.difference(POZO), Z_TRASERA, Z_JUNTA),  # tubo + falda
                      prisma_multi(CAJA, Z_TRASERA - 1, Z_JUNTA)]),
    CIERVO_REL,
])
# hueco del ciervo: erosion 3D; la boca trasera lo une con el agujero del pedestal
HUECO_CIERVO = bo('intersection', [
    erosionar(CIERVO_REL, CIERVO_PARED),
    prisma_multi(abrir(SIL_REL, CIERVO_HUECO_MIN), Z_SUELO - 2, Z_SUELO + CIERVO_RELIEVE + 2)])
LUZ = limpiar(bo('difference', [LUZ, HUECO_CIERVO,
                                prisma_multi(BOCA_CIERVO, Z_SUELO - 1, Z_SUELO + 3.0)]))
log(f'  hueco del ciervo {HUECO_CIERVO.volume:.0f} mm3, boca trasera {BOCA_CIERVO.area:.0f} mm2')
# 0,01 mm: la erosion deja dentro del ciervo pliegues de vacio de menos de
# 0,01 mm que no existen en una impresion; pulir a esa tolerancia los cierra
LUZ = pulir(LUZ, 'luz', tol=0.01)


# ----------------------------------------------------------------------------
# 7. TAPA: placa + el fondo del nicho
# ----------------------------------------------------------------------------
log('tapa...')
_e0 = AEX.buffer(-FALDA - HOLGURA, join_style=JS, mitre_limit=8)
espigo = _e0.difference(_e0.buffer(-TAPA_ESPIGO_W, join_style=JS, mitre_limit=8))
espigo = abrir(espigo.intersection(CAJA.buffer(-HOLGURA, join_style=JS, mitre_limit=8)),
               ANCHO_MIN)
TAPA = bo('union', [
    prisma_multi(P_TAPA, Z_TRASERA - TAPA_ESP, Z_TRASERA),
    prisma_multi(espigo, Z_TRASERA - 0.01, Z_TRASERA + TAPA_ENCASTRE),
])
PEDESTAL = bo('difference', [
    prisma_multi(POZO.buffer(-HOLGURA, join_style=JS, mitre_limit=8),
                 Z_TRASERA, Z_SUELO),
    prisma_multi(abrir(mayor(SIL_REL.buffer(-2.5, join_style=1)), ANCHO_MIN),
                 Z_TRASERA - 1, Z_SUELO + 1)])
TAPA = bo('union', [TAPA, PEDESTAL])
log(f'  + fondo del nicho: {PEDESTAL.volume/1000:.1f} cm3, '
    f'{Z_SUELO - Z_TRASERA:.1f} mm de grueso')

muesca = prisma(sbox(-CABLE_ANCHO / 2 - HOLGURA, P_TAPA.bounds[1] - 5,
                     CABLE_ANCHO / 2 + HOLGURA, y_alto + 2),
                Z_TRASERA - 0.01, Z_TRASERA + TAPA_ENCASTRE + 0.01)
TAPA = bo('difference', [TAPA, muesca])
# paso del tornillo + avellanado de 90 grados que abre hacia la cara de FUERA
# (la cabeza queda enrasada), en un solo solido de revolucion: sin booleana
# entre cono y cilindro, que se tocaban en un circulo y pellizcaban la malla
_zb = Z_TRASERA - TAPA_ESP
_rp, _rc = TORNILLO_D / 2 + 0.45, TORNILLO_CAB / 2
PERFIL_PASO = [(0, _zb - 1), (_rc + 1, _zb - 1), (_rc, _zb), (_rp, _zb + _rc - _rp),
               (_rp, Z_TRASERA + 1), (0, Z_TRASERA + 1)]
PASOS = []
for x, y in TORNILLOS:
    c = trimesh.creation.revolve(PERFIL_PASO, sections=48)
    c.apply_translation([x, y, 0])
    PASOS.append(c)
TAPA = limpiar(bo('difference', [TAPA] + PASOS))
TAPA = pulir(TAPA, 'tapa')
log(f'  hueco para el LED dentro de la pieza translucida: '
    f'{CAJA.area / 100:.0f} cm2 de planta, '
    f'{Z_JUNTA - Z_TRASERA:.0f} mm de fondo')


# ----------------------------------------------------------------------------
# 8. exportar
# ----------------------------------------------------------------------------
log('exportando...')
for nombre, m in (('1_piedra', PIEDRA), ('2_luz', LUZ), ('3_tapa', TAPA)):
    m.export(os.path.join(OUT, nombre + '.stl'))
    m.export(os.path.join(OUT, nombre + '.ply'))
    log(f'  {nombre}   {len(m.faces):7d} caras   {m.volume/1000:6.1f} cm3   '
        f'{np.round(m.extents,1)} mm')

esc = trimesh.Scene()
for n, m in (('piedra', PIEDRA), ('luz', LUZ), ('tapa', TAPA)):
    esc.add_geometry(m, node_name=n)
esc.export(os.path.join(OUT, 'montada.3mf'))

with open(os.path.join(OUT, 'contornos.wkt'), 'w') as f:
    f.write(SIL_CIERVO.wkt + '\n' + POZO.wkt + '\n' + AEX.wkt + '\n'
            + CORONA.wkt + '\n')
np.save(os.path.join(OUT, 'cotas.npy'), np.array([
    S, Z_TRASERA, Z_SUELO, Z_CORONA, Z_JUNTA, Z_FRENTE,
    OFF_LUZ, OFF_PIEDRA, TAPA_ESP, CIERVO_RELIEVE, HOLGURA, FALDA]))
log('hecho')
