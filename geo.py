# -*- coding: utf-8 -*-
"""Secciones horizontales en coordenadas mundo."""
import numpy as np
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union, polygonize
from shapely.affinity import affine_transform


def xy_polys(mesh, z, min_area=1.0):
    """Caras del corte Z=z (cada anillo cerrado por separado, coords mundo)."""
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return []
    lines = [LineString(s.vertices[e.points][:, :2]) for e in s.entities
             if len(e.points) > 2]
    if not lines:
        return []
    return [p for p in polygonize(unary_union(lines)) if p.area > min_area]


def xy_material(mesh, z, min_area=0.02):
    """Material del corte Z=z, con los huecos bien restados (coords mundo)."""
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return Polygon()
    p2, T = s.to_2D()
    polys = [q for q in p2.polygons_full if q.area > min_area]
    if not polys:
        return Polygon()
    m = [T[0, 0], T[0, 1], T[1, 0], T[1, 1], T[0, 3], T[1, 3]]
    return unary_union([affine_transform(q, m) for q in polys])
