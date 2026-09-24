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
from geo import xy_material, alturas
import ciudadela

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

TOL_POZO      = 0.9     # con que tolerancia se enderezan los contornos
TOL_CORONA    = 1.2
# borde exterior de la corona: 'dentro' = 0-2,4 mm antes del pie del escalon
# (deja una tira de piedra a la altura de la corona); 'fuera' = hasta la pared
# del escalon (la corona llega a la pared; el corte entra 0-2*TOL_FUERA en ella
# y, al cruzar en rasante la pared texturada de Meshy, deja costura en sierra)
CORONA_BORDE  = 'ciudadela'
# 'ciudadela' = trazado acordado con Sergi (ciudadela.py): pozo, pared corona->
# escalon y pared escalon->terraza simetricos y coherentes con la silueta.
# ('dentro', 'fuera' y 'canto' se conservan: son los intentos anteriores.)
TERRAZA_ANCHO = 8.0     # por fuera de la pared escalon->terraza se rellena hasta la
                        # terraza en esta franja (entierra la rampa de Meshy y lo
                        # que queda del trazado viejo)
TERRAZA_MIN   = 25.8    # lo que esta por encima de esto en el marco es terraza
TERRAZA_LIMPIA = 3.0    # la terraza de Meshy se da por buena a partir de esta distancia
                        # de la pared (mas cerca queda el labio rugoso de la rampa vieja)
TERRAZA_BAJA  = 0.4     # ... y si no queda mas de esto por debajo de su entorno
CANTO_R       = 1.0     # radio del canto redondo de la pared escalon->terraza
CAMPO_PASO    = 0.25    # lado de los triangulos de las superficies rehechas (mm)
COSTURA       = 0.03    # costura con Meshy: lo rehecho pasa de esto por encima a
RAMPA         = 2.0     # 2x esto por debajo en esta franja, y las dos superficies se
                        # cruzan en angulo (ni escalon ni roce que las pellizque)
# rombo de la punta de abajo: copia de la malla real de media punta lateral derecha,
# llevada con una afin de sus tres vertices (L = union de las ranuras de dentro,
# T y O = esquina y punta de la silueta) a los de abajo, y reflejada en X = 0
ROMBO_LAT     = ((63.7, -28.7), (73.67, -21.28), (79.03, -32.23))
ROMBO_ABAJO   = ((0.0, -73.3), (7.6, -81.18), (0.0, -85.5))
ROMBO_BORDE   = 5.5     # se coge tambien esta franja por fuera del lado L-T (su ranura
                        # entera y la costura, que queda en la terraza lisa)
# el canto de fuera de las dos caras de abajo (ondulado en Meshy): perfil medio
# barrido a lo largo de la cara, fundido con lo de Meshy en los extremos
CARA_ABAJO    = ((57.37, -98.87), (11.78, -88.89))   # la derecha; la izquierda, en espejo
BARRIDO_ANCHO = 4.5     # ancho de la franja rehecha, desde el borde (mm)
BARRIDO_Z0    = 19.5    # altura a la que se ajusta la recta de la pared
BARRIDO_FUERA = 0.05    # la pared rehecha queda esto por fuera de esa recta
BARRIDO_FUNDE = 5.0     # en los extremos se funde con Meshy a lo largo de esto (mm)
BARRIDO_MARGEN = 4.5    # y los extremos quedan esto antes de las esquinas de la cara
TOL_FUERA     = 0.6
# 'canto' = por el canto de arriba de la pared corona->escalon: el rebaje se
# lleva la rampa de Meshy entera y deja una pared vertical cuyo canto corta la
# cara plana del escalon en perpendicular (sin rasantes, sin sierra)
CANTO_NIVEL   = 0.5     # el borde se toma a esta fraccion de la pared corona->escalon
                        # (a media pared: las hondonadas de la cara del escalon no
                        # lo deforman)
RELLENO_SOBRE = 0.15    # la cara del escalon se rellena hasta su plano + esto (mm)
RELLENO_ANCHO = 8.0     # ... en esta franja por fuera del borde de la corona (mm)
CANTO_FUERA   = 0.4     # y el borde se saca esto hacia fuera, sobre la cara plana
CANTO_TOL     = 2.0     # tolerancia de enderezado de ese borde: basta con que caiga
                        # entre el pie de la rampa y la cara del escalon (lo de
                        # dentro lo quita el rebaje, lo de fuera lo entierra el relleno)
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
CAJA_MAX      = 14.0    # donde la caja del LED es mas ancha que esto (las puntas de
                        # los baluartes) su centro se deja macizo: la corona no tiene
                        # que puentear mas de esto al imprimirse

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
      altura de la aguja (< 0,1 micras);
    - si nada de eso se puede y el lado corto mide < 0,1 mm, se colapsa solo si
      el otro extremo esta en el plano de todas las caras que se mueven (zona
      plana o a lo largo de una arista), a menos de 0,02 mm: la superficie no
      cambia de forma apreciable (una capa son 0,2 mm)."""
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

        def colapsar(f, solo_plano=False):
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
            if solo_plano:
                # b solo puede deslizarse hasta a si a esta en el plano de cada
                # cara de b (zona plana o a lo largo de una arista): la
                # geometria no cambia
                cb = [c_ for c_ in caras_b if c_ not in (f, g)]
                tv = V[F[cb]]
                nv = np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0])
                nv = nv / np.maximum(np.linalg.norm(nv, axis=1)[:, None], 1e-12)
                if np.abs(((V[a] - tv[:, 0]) * nv).sum(1)).max() > 0.02:
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
            if not ok and ls[f].min() < 0.1:
                ok = colapsar(f, solo_plano=True)
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
        sitios = np.unique(np.round(dup / 2.0) * 2.0, axis=0)
        raise AssertionError(
            f'{nombre}: {len(dup)} vertices en contacto sin espesor, en '
            f'{np.round(sitios[:8], 0).astype(int).tolist()}'
            f'{" ..." if len(sitios) > 8 else ""}: hay dos solidos '
            f'que se tocan en una arista o un punto')
    M = manifold3d.Manifold(manifold3d.Mesh(
        vert_properties=np.asarray(mesh.vertices, np.float32),
        tri_verts=np.asarray(mesh.faces, np.uint32)))
    g = M.simplify(tol).to_mesh()
    m = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts, process=False)
    m = sanear(m)
    for _ in range(3):      # a veces colapsar deja otra aguja: simplify + sanear otra vez
        if not degenerados(m).any():
            break
        g = manifold3d.Manifold(manifold3d.Mesh(
            vert_properties=np.asarray(m.vertices, np.float32),
            tri_verts=np.asarray(m.faces, np.uint32))).simplify(tol).to_mesh()
        m = sanear(trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts, process=False))
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


def a_manifold(m):
    return manifold3d.Manifold(manifold3d.Mesh(
        vert_properties=np.asarray(m.vertices, np.float32),
        tri_verts=np.asarray(m.faces, np.uint32)))


def a_trimesh(M):
    g = M.to_mesh()
    return trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts, process=False)


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
POZO_MESHY = POZO          # el pozo del OBJ: sirve para aislar el ciervo
if CORONA_BORDE == 'ciudadela':
    POZO = ciudadela.POZO
log(f'  POZO: {len(POZO.exterior.coords)-1} lados rectos, desviacion max al pozo '
    f'de Meshy {_env.hausdorff_distance(POZO):.2f} mm, area {POZO.area:.0f} mm2')

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
elif CORONA_BORDE == 'ciudadela':
    Z_ESCALON = plano_dominante(malla, Z_CORONA + 5, Z_CORONA + 14)
    AEX = ciudadela.AEX
    W2 = ciudadela.W2
    log(f'  trazado de la Ciudadela: escalon en Z={Z_ESCALON:.2f}, marco '
        f'{ciudadela.MARCO:.0f} mm, escalon {ciudadela.ESCALON:.0f} mm, entrantes '
        f'{ciudadela.ENTRANTE:.0f} grados')
else:   # 'canto'
    Z_ESCALON = plano_dominante(malla, Z_CORONA + 5, Z_CORONA + 14)
    import shapely as _sh
    _ox, _oy, _sc, _n = GEO
    _jj, _ii = np.mgrid[0:_n, 0:_n]
    _cerca = _sh.contains(_ext.buffer(8.0), _sh.points(
        ((_ii - _n / 2) / _sc + _ox).ravel(), ((_n / 2 - _jj) / _sc + _oy).ravel())).reshape(D.shape)
    _nivel = Z_CORONA + CANTO_NIVEL * (Z_ESCALON - Z_CORONA)
    _can = Polygon(mascara_a_poligono((D > Z_CORONA - 3.5) & (D < _nivel) & _cerca,
                                      GEO).exterior)
    AEX = mayor(_can.buffer(CANTO_FUERA, join_style=1).simplify(CANTO_TOL))
    log(f'  escalon en Z={Z_ESCALON:.2f}; borde de la corona a media pared (Z={_nivel:.1f})')
_min = off(POZO, PARED + HOLGURA + FALDA + 0.3)   # minimo para que quepa la falda
_fuera = _min.difference(_ext)
log(f'  (la falda pide {_fuera.area:.0f} mm2 por fuera del escalon del marco, '
    f'hasta {_ext.exterior.hausdorff_distance(_min.exterior) if not _fuera.is_empty else 0:.1f} mm)')
if CORONA_BORDE == 'ciudadela':
    # el trazado ya deja sitio a la falda: se comprueba, no se retoca
    assert _min.difference(AEX.buffer(0.05)).area < 0.5, \
        f'la falda no cabe en la corona ({_min.difference(AEX).area:.1f} mm2 fuera)'
else:
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
caja = prisma(POZO_MESHY.buffer(-0.5, join_style=JS, mitre_limit=8),
              Z_SUELO + 0.4, Z_CORONA + 4.0)
tr = [c for c in bo('intersection', [malla, caja]).split(only_watertight=False)
      if c.volume > 100]
tr.sort(key=lambda c: -c.volume)
CIERVO = tr[0]
if CORONA_BORDE == 'ciudadela':
    # centrado en el pozo simetrico
    CIERVO.apply_translation([ciudadela.CIERVO_DX, 0, 0])
    log(f'  ciervo desplazado {ciudadela.CIERVO_DX:+.2f} mm en X para quedar centrado')
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
# la cara del escalon, allanada: por fuera del borde de la corona se rellena hasta
# un plano unico. Entierra las hondonadas de Meshy y lo que quede de la rampa, y
# la pared del rebaje sube vertical y limpia desde la corona hasta ese plano.
# Donde la superficie ya esta mas alta (la pared siguiente, las terrazas) no cambia.
MARCO = malla
if CORONA_BORDE == 'canto':
    Z_RELLENO = Z_ESCALON + RELLENO_SOBRE
    MARCO = bo('union', [malla, prisma_multi(
        AEX.buffer(RELLENO_ANCHO, join_style=JS, mitre_limit=8).intersection(
            ESTRELLA.buffer(-3.0, join_style=1)), Z_JUNTA, Z_RELLENO)])
    log(f'  cara del escalon allanada a Z={Z_RELLENO:.2f} en {RELLENO_ANCHO:.0f} mm por fuera '
        f'de la corona (+{(MARCO.volume - malla.volume):.0f} mm3)')
elif CORONA_BORDE == 'ciudadela':
    import shapely as _sh
    from scipy import ndimage
    Z_RELLENO = Z_ESCALON + RELLENO_SOBRE
    RELLENO_ANCHO = ciudadela.ESCALON + TERRAZA_ANCHO
    # mapa de alturas de Meshy (Z interpolada, 0,1 mm) y un muestreador bilineal
    _LIM, _RES = 101.0, 0.1
    H = alturas(malla, _RES, _LIM)
    _n = H.shape[0]
    _jj, _ii = np.mgrid[0:_n, 0:_n]
    HX = -_LIM + (_ii + 0.5) * _RES
    HY = _LIM - (_jj + 0.5) * _RES
    _, (_jv, _iv) = ndimage.distance_transform_edt(~np.isfinite(H), return_indices=True)
    HS = H[_jv, _iv]         # fuera de la pieza, el valor mas cercano (para muestrear)

    def muestrear(M, x, y):
        return ndimage.map_coordinates(M, [(_LIM - np.asarray(y)) / _RES - 0.5,
                                           (np.asarray(x) + _LIM) / _RES - 0.5],
                                       order=1, mode='nearest')

    def a_costura(z, x, y, e, guarda=True, sobre=COSTURA, bajo=2 * COSTURA):
        """Costura sin escalon con Meshy. Lo rehecho llega RAMPA mm mas alla del
        corte de Meshy (e = distancia a su borde): en el corte queda COSTURA por
        encima de Meshy (tapa su cara cortada) y en su borde, 2*COSTURA por debajo
        (queda dentro). En medio las dos superficies se cruzan en angulo, sin
        tocarse de refilon (eso deja pellizcos) y sin escalon a la vista."""
        e = np.asarray(e)
        hs = muestrear(HS, x, y)
        w = np.clip(1.0 - e / RAMPA, 0, 1)
        w = w * w * (3 - 2 * w)
        v = np.clip(1.0 - (e - RAMPA) / 1.0, 0, 1) * guarda   # junto al corte, nunca bajo Meshy
        v = v * v * (3 - 2 * v)
        arriba = z + v * (np.maximum(z, hs) - z) + sobre
        return (1 - w) * arriba + w * (np.minimum(z, hs) - bajo)

    def campo(poly, z0, fz, paso=CAMPO_PASO):
        """Solido sobre `poly` entre z0 y la superficie z = fz(x, y)."""
        z1 = z0 + 1.0      # prisma bajo: sus paredes no se subdividen de mas
        M = a_manifold(prisma_multi(poly, z0, z1)).refine_to_length(paso)

        def w(v):
            v = np.array(v, dtype=np.float64)
            v[:, 2] = z0 + (v[:, 2] - z0) / (z1 - z0) * (fz(v[:, 0], v[:, 1]) - z0)
            return v
        return M.warp_batch(w)

    # (b) el rombo de la punta de abajo: Meshy tiene ahi el rombo hundido. Se
    # copia la malla de media punta lateral (la derecha, de la trasera arriba:
    # ranuras, rombo, canto y pared), se lleva con una afin a media punta de
    # abajo y se refleja. Las alturas se ajustan en la costura con la terraza.
    _src = np.array(ROMBO_LAT)
    _dst = np.array(ROMBO_ABAJO)
    _A = np.linalg.solve(np.c_[_src, np.ones(3)], _dst).T     # dst = A @ [x, y, 1]

    def _a_abajo(xy):
        return xy @ _A[:, :2].T + _A[:, 2]

    def _normal(p, q, lejos_de):
        e = (q - p) / np.linalg.norm(q - p)
        nv = np.array([-e[1], e[0]])
        return -nv if np.dot(lejos_de - p, nv) > 0 else nv
    _L, _T, _O = _src
    _nLT, _nLO, _nTO = _normal(_L, _T, _O), _normal(_L, _O, _T), _normal(_T, _O, _L)
    _eto = (_O - _T) / np.linalg.norm(_O - _T)
    _mTO = (_T + _O) / 2
    _borde = [_L + _nLT * ROMBO_BORDE, _T + _nLT * ROMBO_BORDE]
    _zona_src = unary_union([
        Polygon(_src),
        Polygon([_L, _T, _borde[1], _borde[0]]),        # franja sobre la terraza (costura)
        Polygon([_L, _O, _O + _nLO, _L + _nLO]),         # 1 mm pasado el eje: se abre en X = 0
        Polygon([_mTO, _O + _eto * 2, _O + _eto * 2 + _nTO * 2, _mTO + _nTO * 2]),  # fuera de la punta
    ]).buffer(0)
    _lc = LineString(_borde)
    _cost = np.array([(q.x, q.y) for q in _lc.interpolate(np.linspace(0.1, 0.9, 60),
                                                           normalized=True)])
    _h_lat = muestrear(HS, _cost[:, 0], _cost[:, 1])
    _dz = float(np.median(muestrear(HS, *_a_abajo(_cost).T) - _h_lat))
    _z_terr = float(np.median(_h_lat))
    _pieza = bo('intersection', [malla, prisma(_zona_src, Z_TRASERA - 1.0, Z_FRENTE + 1.0)])
    _trozos = _pieza.split(only_watertight=False)     # (Meshy tiene granitos sueltos)
    _pieza = max(_trozos, key=lambda c: c.volume)
    log(f'  rombo: {len(_trozos) - 1} trozos sueltos de Meshy fuera de la copia')
    _pieza = a_trimesh(a_manifold(_pieza).refine_to_length(0.3))
    _v = _pieza.vertices.copy()
    _v[:, :2] = _a_abajo(_v[:, :2])
    _v[:, 2] += _dz * (_v[:, 2] - Z_TRASERA) / (_z_terr - Z_TRASERA)   # la trasera no se mueve
    # costura con la terraza: en la franja de fuera del lado L-T
    _bd = _a_abajo(np.array(_borde))
    _cost_ab = LineString(_bd)
    _lado = LineString(_a_abajo(np.array([_L, _T])))
    _e_v = np.asarray(_sh.distance(_cost_ab, _sh.points(_v[:, 0], _v[:, 1])))
    _fuera_LT = np.asarray(_sh.distance(_lado, _sh.points(_v[:, 0], _v[:, 1]))) < \
        _lado.distance(_cost_ab) + 1e-6
    _fuera_LT &= _e_v < _lado.distance(_cost_ab)
    # la terraza copiada no es la de abajo (+-0,1): de la ranura hacia la costura
    # la franja pasa a seguir la terraza de Meshy de abajo, y en la costura se
    # cruza con ella en angulo (a_costura)
    # (se aplica como desplazamiento de la cara de arriba, que baja hasta 1 mm por
    # la pared: los vertices de las paredes no se cruzan)
    _ws = _lado.distance(_cost_ab)
    _Hp = alturas(trimesh.Trimesh(_v, _pieza.faces, process=False), _RES, _LIM)
    _, (_jp, _ip) = ndimage.distance_transform_edt(~np.isfinite(_Hp), return_indices=True)
    _Hp = _Hp[_jp, _ip]
    _xs, _ys = _v[:, 0], _v[:, 1]
    _g = np.where(_fuera_LT, np.clip((_ws - 0.4 - _e_v) / 0.5, 0, 1), 0.0)
    _g = _g * _g * (3 - 2 * _g)
    _ztop = muestrear(_Hp, _xs, _ys)
    _f = np.clip((_v[:, 2] - (_ztop - 1.0)) / 1.0, 0, 1)     # 1 en la cara de arriba
    _zref = _f * _v[:, 2] + (1 - _f) * _ztop                  # (asi los granitos se van)
    _delta = COSTURA + _g * (a_costura(muestrear(HS, _xs, _ys), _xs, _ys, _e_v, guarda=False)
                             - (_zref + COSTURA))
    _v[:, 2] += _delta * _f
    # media pieza abierta por X = 0; las dos mitades se cosen por esos vertices
    # (una booleana de dos solidos que solo se tocan en un plano deja pellizcos)
    _pieza = trimesh.intersections.slice_mesh_plane(
        trimesh.Trimesh(_v, _pieza.faces), plane_normal=[1, 0, 0], plane_origin=[0, 0, 0],
        cap=False)
    _v = _pieza.vertices.copy()
    _v[np.abs(_v[:, 0]) < 1e-6, 0] = 0.0
    _f = _pieza.faces[~(_v[_pieza.faces][:, :, 0] == 0).all(axis=1)]   # ninguna en el plano
    _ve = _v * [-1.0, 1, 1]
    ROMBO = trimesh.Trimesh(np.vstack([_v, _ve]),
                            np.vstack([_f, _f[:, ::-1] + len(_v)]), process=False)
    ROMBO.merge_vertices()
    assert ROMBO.is_watertight and ROMBO.is_winding_consistent, 'el rombo cosido no cierra'
    # la trasera de la punta lateral trae ranuras de Meshy en su primer mm y medio:
    # se maciza con el contorno de mas arriba (primera capa limpia)
    _z_ok = Z_TRASERA + 1.6
    ROMBO = bo('union', [ROMBO, prisma_multi(xy_material(ROMBO, _z_ok), Z_TRASERA, _z_ok + 0.1)])

    def _espejo(p):
        return p.union(Polygon([(-x, y) for x, y in p.exterior.coords])).buffer(0)
    ROMBO_ZONA = _espejo(Polygon(_a_abajo(np.array(_zona_src.exterior.coords))))
    # Meshy se quita en la zona menos la parte de fuera de la franja (alli se cruzan)
    _franja_ab = Polygon([_bd[0], _bd[1], *_a_abajo(np.array([_T, _L]))])
    _cruce = _espejo(_franja_ab.intersection(_cost_ab.buffer(RAMPA, cap_style=2)))
    ROMBO_CORTE = ROMBO_ZONA.difference(_cruce).buffer(-COSTURA)
    assert _lado.distance(_cost_ab) > RAMPA + 1.6, \
        f'la franja del rombo ({_lado.distance(_cost_ab):.1f} mm) no da para la costura'

    # (a) la terraza junto a la pared escalon->terraza: Meshy deja ahi un labio
    # rugoso de 1-3 mm (lo que queda de su rampa) y alguna hondonada. Se rehace la
    # franja entera: a la altura de la terraza buena mas cercana (lo que esta a
    # mas de TERRAZA_LIMPIA de la pared y no se hunde respecto a su entorno) y con
    # un canto redondo de radio CANTO_R arriba de la pared.
    dW2 = np.asarray(_sh.distance(W2, _sh.points(HX.ravel(), HY.ravel()))).reshape(H.shape)
    _terr = (H >= TERRAZA_MIN) & (dW2 > 0) & (dW2 < TERRAZA_ANCHO + 6)
    _k = 4        # nivel del entorno: percentil 75 en 8 mm, en malla gruesa
    _ref = ndimage.percentile_filter(np.where(_terr, H, -1e3)[::_k, ::_k], 75, size=21)
    _ref = ndimage.zoom(_ref, _k, order=1)[:_n, :_n]
    _limpio = _terr & (dW2 >= TERRAZA_LIMPIA) & (H >= _ref - TERRAZA_BAJA)
    _dl, (_jl, _il) = ndimage.distance_transform_edt(~_limpio, return_indices=True)
    # donde se extrapola (labio, hondonadas) se suaviza mas: la terraza buena mas
    # cercana cambia de golpe de un lado a otro y dejaria muescas
    _a = np.clip(_dl * _RES / 1.0, 0, 1)
    T_TERRAZA = (1 - _a) * ndimage.gaussian_filter(H[_jl, _il], 3) + \
        _a * ndimage.gaussian_filter(H[_jl, _il], 15)
    _dentro_w2 = W2.buffer(-0.05, join_style=JS, mitre_limit=8)
    _fuera = W2.buffer(TERRAZA_ANCHO + RAMPA, join_style=JS, mitre_limit=8).intersection(
        ESTRELLA.buffer(-1.0)).difference(ROMBO_ZONA.buffer(1.0))
    BANDA = _fuera.difference(_dentro_w2)
    BANDA_CORTE = _fuera.buffer(-RAMPA, join_style=JS, mitre_limit=8).difference(_dentro_w2)

    def _z_terraza(x, y):
        d = np.clip(np.asarray(_sh.distance(W2, _sh.points(x, y))), 0, CANTO_R)
        z = muestrear(T_TERRAZA, x, y) - (
            CANTO_R - np.sqrt(np.maximum(CANTO_R ** 2 - (CANTO_R - d) ** 2, 0)))
        return a_costura(z, x, y, np.asarray(_sh.distance(_fuera.boundary, _sh.points(x, y))))
    TERRAZA = campo(BANDA, Z_JUNTA, _z_terraza)
    log(f'  terraza: {TERRAZA_ANCHO:.0f} mm junto a la pared rehechos a la altura de la '
        f'terraza buena, canto redondo R{CANTO_R:.1f}')

    # (c) el canto de fuera de las dos caras de abajo: en Meshy ondula (hasta
    # 1,4 mm). La pared de esas caras es recta (+-0,06 mm): se ajusta su recta a
    # Z=BARRIDO_Z0 y la franja se rehace entera, de la trasera arriba: pared plana
    # y el canto con su perfil medio barrido a lo largo de ella, en una rejilla
    # alineada con la cara (las curvas de nivel del canto van paralelas a los
    # triangulos: sombreado liso). En los extremos se funde con Meshy.
    _E0 = Polygon(max(secciones_xy(malla, BARRIDO_Z0, min_area=200), key=lambda p: p.area).exterior)
    _pE0 = np.array(_E0.exterior.coords)

    def _cara(a, b):
        a, b = np.array(a, float), np.array(b, float)
        t = (b - a) / np.linalg.norm(b - a)
        nn = np.array([-t[1], t[0]])
        if not ESTRELLA.contains(Point(*((a + b) / 2 + nn * 3))):
            nn = -nn                                   # nn: hacia dentro
        L = np.linalg.norm(b - a)
        s, u = (_pE0 - a) @ t, (_pE0 - a) @ nn
        k = (s > 2) & (s < L - 2) & (np.abs(u) < 3)
        c1, c0 = np.polyfit(s[k], u[k], 1)             # la pared: u = c0 + c1 s
        a2 = a + nn * c0
        t2 = (b + nn * (c0 + c1 * L)) - a2
        L2 = np.linalg.norm(t2)
        t2 /= L2
        n2 = np.array([-t2[1], t2[0]]) * np.sign(np.dot([-t2[1], t2[0]], nn))
        a2, L2 = a2 + t2 * BARRIDO_MARGEN, L2 - 2 * BARRIDO_MARGEN   # lejos de las esquinas
        corte = Polygon([a2 - n2 * 2, a2 + t2 * L2 - n2 * 2,
                         a2 + t2 * L2 + n2 * BARRIDO_ANCHO, a2 + n2 * BARRIDO_ANCHO])
        return a2, t2, n2, L2, corte.buffer(0)
    CARAS = [_cara(*CARA_ABAJO), _cara((-CARA_ABAJO[0][0], CARA_ABAJO[0][1]),
                                      (-CARA_ABAJO[1][0], CARA_ABAJO[1][1]))]
    # perfil medio: altura segun la distancia hacia dentro desde la pared
    _us, _zs = [], []
    for a2, t2, n2, L2, _ in CARAS:
        s = (HX - a2[0]) * t2[0] + (HY - a2[1]) * t2[1]
        u = (HX - a2[0]) * n2[0] + (HY - a2[1]) * n2[1]
        k = (s > 0.15 * L2) & (s < 0.85 * L2) & (u > 0) & (u < BARRIDO_ANCHO + RAMPA + 0.3)
        _us.append(u[k]); _zs.append(H[k])
    _us, _zs = np.concatenate(_us), np.concatenate(_zs)
    _bins = np.arange(0, BARRIDO_ANCHO + RAMPA + 0.3, 0.1)
    _idx = np.digitize(_us, _bins)
    _uperf = _bins[:-1] + 0.05
    PERFIL = np.array([np.median(_zs[_idx == i]) for i in range(1, len(_bins))])
    PERFIL = ndimage.uniform_filter1d(np.maximum.accumulate(PERFIL), 3, mode='nearest')

    def _barrido(a2, t2, n2, L2):
        """Losa cerrada sobre una rejilla (s a lo largo de la cara, u hacia dentro)."""
        R = RAMPA
        ss = np.linspace(-R, L2 + R, int(np.ceil((L2 + 2 * R) / 0.5)) + 1)
        vv = np.r_[np.arange(0, 3.0, 0.05), np.arange(3.0, BARRIDO_ANCHO + R + 1e-6, 0.25)]
        S_, V_ = np.meshgrid(ss, vv, indexing='ij')
        # la pared: BARRIDO_FUERA por fuera de la recta (tapa la de Meshy, que se
        # aparta +-0,06) y, pasado el corte de los extremos, se mete hasta quedar
        # dentro de la de Meshy: las dos paredes se cruzan en angulo, sin escalon
        f_ext = np.clip((np.maximum(-S_, S_ - L2) - 0.3) / 0.6, 0, 1)
        u_pared = -BARRIDO_FUERA + f_ext * (BARRIDO_FUERA + 0.5)
        W_ = BARRIDO_ANCHO + R
        U_ = u_pared + V_ * (W_ - u_pared) / W_
        X_ = a2[0] + S_ * t2[0] + U_ * n2[0]
        Y_ = a2[1] + S_ * t2[1] + U_ * n2[1]
        w = np.clip(np.minimum(S_, L2 - S_) / BARRIDO_FUNDE, 0, 1)
        w = w * w * (3 - 2 * w)
        # (Meshy se muestrea por dentro de su pared: fuera, el mapa no dice nada)
        Uc = np.maximum(U_, 0.3)
        Zm = muestrear(HS, a2[0] + S_ * t2[0] + Uc * n2[0], a2[1] + S_ * t2[1] + Uc * n2[1])
        Z_ = w * np.interp(U_, _uperf, PERFIL) + (1 - w) * Zm
        e = np.minimum(np.minimum(S_ + R, L2 + R - S_), BARRIDO_ANCHO + R - U_)
        Z_ = a_costura(Z_.ravel(), X_.ravel(), Y_.ravel(), e.ravel()).reshape(Z_.shape)
        ns, nu = S_.shape
        top = np.c_[X_.ravel(), Y_.ravel(), Z_.ravel()]
        bot = np.c_[X_.ravel(), Y_.ravel(), np.full(X_.size, Z_TRASERA)]
        idx = np.arange(ns * nu).reshape(ns, nu)
        q = np.c_[idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()]
        f_top = np.r_[q[:, [0, 1, 2]], q[:, [0, 2, 3]]]
        f_bot = f_top[:, ::-1] + ns * nu
        borde = np.r_[idx[:, 0], idx[-1, 1:], idx[::-1, -1][1:], idx[0, ::-1][1:-1]]
        b1 = np.roll(borde, -1)
        f_lado = np.r_[np.c_[borde, borde + ns * nu, b1], np.c_[b1, borde + ns * nu, b1 + ns * nu]]
        m = trimesh.Trimesh(np.r_[top, bot], np.r_[f_top, f_bot, f_lado], process=False)
        if m.volume < 0:
            m.invert()
        assert m.is_watertight and m.is_winding_consistent, 'el barrido no cierra'
        return a_manifold(m)
    BARRIDOS = [_barrido(a2, t2, n2, L2) for a2, t2, n2, L2, _ in CARAS]
    _huellas = [Polygon([a2 - t2 * RAMPA - n2 * 0.3, a2 + t2 * (L2 + RAMPA) - n2 * 0.3,
                         a2 + t2 * (L2 + RAMPA) + n2 * (BARRIDO_ANCHO + RAMPA),
                         a2 - t2 * RAMPA + n2 * (BARRIDO_ANCHO + RAMPA)])
                for a2, t2, n2, L2, _ in CARAS]
    # todo lo rehecho a proposito, para verificar.py
    REHECHO = unary_union([_fuera, ROMBO_ZONA] + _huellas).buffer(0)
    FRANJAS = [(None, c, None) for *_, c in CARAS]

    # montaje: se quita lo de Meshy en cada zona rehecha y se pone lo nuevo; el
    # escalon entre las dos paredes es un plano exacto (relleno por debajo y
    # cortado por encima) y la pared escalon->terraza queda vertical
    M = a_manifold(malla)
    M = M - a_manifold(prisma_multi(BANDA_CORTE, Z_JUNTA + 1.0, Z_FRENTE + 1.0))
    M = M - a_manifold(prisma_multi(ROMBO_CORTE, Z_TRASERA - 1.5, Z_FRENTE + 1.0))
    for _, qc, *_ in FRANJAS:
        M = M - a_manifold(prisma(qc, Z_TRASERA - 1.0, Z_FRENTE + 1.0))
    M = M + TERRAZA + a_manifold(ROMBO)
    for B in BARRIDOS:
        M = M + B
    M = M + a_manifold(prisma_multi(W2, Z_JUNTA, Z_RELLENO))
    M = M - a_manifold(prisma_multi(W2, Z_RELLENO, Z_FRENTE + 1.0))
    MARCO = a_trimesh(M)
    log(f'  marco: escalon plano a Z={Z_RELLENO:.2f}; rombo de abajo copiado de la punta '
        f'lateral (dz {_dz:+.2f}); canto de las caras de abajo con perfil medio '
        f'(de {PERFIL[0]:.2f} a {PERFIL[-1]:.2f} en {BARRIDO_ANCHO:.1f} mm)')
else:
    Z_RELLENO, RELLENO_ANCHO = Z_CORONA, 0.0
    REHECHO = AEX
PIEDRA = bo('difference', [MARCO, HUECO_PIEDRA])
PIEDRA = bo('difference', [PIEDRA, CANAL])
PIEDRA = limpiar(bo('difference', [PIEDRA] + TALADROS))
PIEDRA = pulir(PIEDRA, 'piedra', tol=0.005)   # (5 micras: junta los racimos de vertices de las costuras)


# ----------------------------------------------------------------------------
# 6. LUZ: corona + escalon interno + falda + ciervo, todo de una pieza
# ----------------------------------------------------------------------------
log('pieza de luz...')
# caja del LED: el hueco entre tubo y falda, sin zonas estrechas. Donde los dos
# quedarian casi pegados (rendija de menos de CAJA_MIN) se maciza: tubo y falda
# salen de un solo prisma sin ranuras.
CAJA = abrir(AEX.buffer(-FALDA, join_style=JS, mitre_limit=8)
             .difference(off(POZO, OFF_LUZ)), CAJA_MIN)
_nucleo = abrir(CAJA.buffer(-CAJA_MAX / 2 + 1.0, join_style=1), 2.0)
if not _nucleo.is_empty:
    CAJA = abrir(CAJA.difference(_nucleo), CAJA_MIN)
    log(f'  caja del LED: nucleo macizo de {_nucleo.area:.0f} mm2 en las puntas (puente < {CAJA_MAX:.0f} mm)')
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
            + CORONA.wkt + '\n' + REHECHO.wkt + '\n')
np.save(os.path.join(OUT, 'cotas.npy'), np.array([
    S, Z_TRASERA, Z_SUELO, Z_CORONA, Z_JUNTA, Z_FRENTE,
    OFF_LUZ, OFF_PIEDRA, TAPA_ESP, CIERVO_RELIEVE, HOLGURA, FALDA, Z_RELLENO, RELLENO_ANCHO]))
log('hecho')
