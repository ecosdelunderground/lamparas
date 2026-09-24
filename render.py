"""Rasterizador con z-buffer (profundidad resuelta pixel a pixel).

Antes pintaba cada triangulo entero ordenado por la profundidad de su centro
(algoritmo del pintor). Con triangulos largos eso pinta caras de detras encima
de las de delante y salen manchas que no existen en el modelo. Ahora cada pixel
se queda con la cara que de verdad esta mas cerca.

Usa numba si esta instalado; si no, el mismo algoritmo en numpy (mas lento).
"""
import numpy as np
from PIL import Image, ImageDraw

try:
    from numba import njit
except ImportError:          # sin numba: mismo codigo, sin compilar
    def njit(*a, **k):
        return (lambda f: f) if not (len(a) == 1 and callable(a[0])) else a[0]
    _NUMBA = False
else:
    _NUMBA = True


def _basis(cam_dir, up):
    d = np.array(cam_dir, float); d /= np.linalg.norm(d)
    u = np.array(up, float)
    r = np.cross(d, u)
    if np.linalg.norm(r) < 1e-6:
        u = np.array([0., 0., 1.]) if abs(d[2]) < 0.9 else np.array([0., 1., 0.])
        r = np.cross(d, u)
    r /= np.linalg.norm(r)
    tu = np.cross(r, d); tu /= np.linalg.norm(tu)
    return np.stack([r, tu, -d])


@njit(cache=True)
def _zbuffer(tx, ty, tz, col, W, H, img, zb):
    for i in range(tx.shape[0]):
        x0, x1, x2 = tx[i, 0], tx[i, 1], tx[i, 2]
        y0, y1, y2 = ty[i, 0], ty[i, 1], ty[i, 2]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area == 0.0:
            continue
        xa = max(int(np.floor(min(x0, x1, x2))), 0)
        xb = min(int(np.ceil(max(x0, x1, x2))), W - 1)
        ya = max(int(np.floor(min(y0, y1, y2))), 0)
        yb = min(int(np.ceil(max(y0, y1, y2))), H - 1)
        for py in range(ya, yb + 1):
            cy = py + 0.5
            for px in range(xa, xb + 1):
                cx = px + 0.5
                w0 = ((x1 - cx) * (y2 - cy) - (x2 - cx) * (y1 - cy)) / area
                w1 = ((x2 - cx) * (y0 - cy) - (x0 - cx) * (y2 - cy)) / area
                w2 = 1.0 - w0 - w1
                if w0 < 0.0 or w1 < 0.0 or w2 < 0.0:
                    continue
                z = w0 * tz[i, 0] + w1 * tz[i, 1] + w2 * tz[i, 2]
                if z > zb[py, px]:
                    zb[py, px] = z
                    img[py, px, 0] = col[i, 0]
                    img[py, px, 1] = col[i, 1]
                    img[py, px, 2] = col[i, 2]


def rasterize(meshes, cam_dir, up=(0, 1, 0), size=700, bg=(16, 16, 18),
              colors=None, margin=1.06, light=(0.35, 0.55, 1.0), frame=None, ss=2):
    """Render con z-buffer. frame=(center,span) para compartir encuadre.
    ss = supermuestreo (antialias)."""
    R = _basis(cam_dir, up)
    if colors is None:
        colors = [(196, 190, 178)] * len(meshes)
    if frame is None:
        allv = np.vstack([np.asarray(m.vertices) for m in meshes]) @ R.T
        c = (allv.min(0) + allv.max(0)) / 2
        span = max(np.ptp(allv[:, 0]), np.ptp(allv[:, 1])) * margin
    else:
        c, span = frame
    N = size * ss
    scale = N / span
    L = np.array(light, float); L /= np.linalg.norm(L)

    TX, TY, TZ, CO = [], [], [], []
    for m, col in zip(meshes, colors):
        v = (np.asarray(m.vertices) @ R.T) - c
        n = np.asarray(m.face_normals) @ R.T
        keep = n[:, 2] > 0
        f = np.asarray(m.faces)[keep]
        sh = np.clip(n[keep] @ L, 0, 1) * 0.72 + 0.28
        px = v[:, 0] * scale + N / 2
        py = N / 2 - v[:, 1] * scale
        TX.append(px[f]); TY.append(py[f]); TZ.append(v[:, 2][f])
        CO.append(np.clip(np.array(col, float)[None, :] * sh[:, None], 0, 255))
    tx = np.ascontiguousarray(np.vstack(TX), dtype=np.float64)
    ty = np.ascontiguousarray(np.vstack(TY), dtype=np.float64)
    tz = np.ascontiguousarray(np.vstack(TZ), dtype=np.float64)
    co = np.ascontiguousarray(np.vstack(CO), dtype=np.float64)
    img = np.empty((N, N, 3), np.float64); img[:] = bg
    zb = np.full((N, N), -np.inf)
    if _NUMBA:
        _zbuffer(tx, ty, tz, co, N, N, img, zb)
    else:
        _zbuffer_np(tx, ty, tz, co, N, img, zb)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return out.resize((size, size), Image.LANCZOS) if ss > 1 else out


def _zbuffer_np(tx, ty, tz, col, N, img, zb):
    """El mismo z-buffer triangulo a triangulo, vectorizado por pixel."""
    for i in range(len(tx)):
        x, y, z = tx[i], ty[i], tz[i]
        area = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0])
        if area == 0:
            continue
        xa, xb = max(int(np.floor(x.min())), 0), min(int(np.ceil(x.max())), N - 1)
        ya, yb = max(int(np.floor(y.min())), 0), min(int(np.ceil(y.max())), N - 1)
        if xa > xb or ya > yb:
            continue
        cx, cy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
        w0 = ((x[1] - cx) * (y[2] - cy) - (x[2] - cx) * (y[1] - cy)) / area
        w1 = ((x[2] - cx) * (y[0] - cy) - (x[0] - cx) * (y[2] - cy)) / area
        w2 = 1 - w0 - w1
        dentro = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
        sub = zb[ya:yb + 1, xa:xb + 1]
        gana = dentro & (zz > sub)
        sub[gana] = zz[gana]
        img[ya:yb + 1, xa:xb + 1][gana] = col[i]


def sheet(images, cols=3, pad=4, bg=(10, 10, 12), labels=None):
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    out = Image.new('RGB', (cols * (w + pad) + pad, rows * (h + pad) + pad), bg)
    dr = ImageDraw.Draw(out)
    for i, im in enumerate(images):
        x = pad + (i % cols) * (w + pad); y = pad + (i // cols) * (h + pad)
        out.paste(im, (x, y))
        if labels:
            dr.text((x + 8, y + 6), labels[i], fill=(255, 220, 120))
    return out
