import numpy as np
from PIL import Image, ImageDraw

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

def rasterize(meshes, cam_dir, up=(0, 1, 0), size=700, bg=(16, 16, 18),
              colors=None, margin=1.06, light=(0.35, 0.55, 1.0), frame=None):
    """Painter's-algorithm render with PIL polygons. frame=(center,span) to share framing."""
    R = _basis(cam_dir, up)
    if colors is None:
        colors = [(196, 190, 178)] * len(meshes)
    if frame is None:
        allv = np.vstack([np.asarray(m.vertices) for m in meshes]) @ R.T
        c = (allv.min(0) + allv.max(0)) / 2
        span = max(np.ptp(allv[:, 0]), np.ptp(allv[:, 1])) * margin
    else:
        c, span = frame
    scale = size / span
    L = np.array(light, float); L /= np.linalg.norm(L)

    tris, cols, depth = [], [], []
    for m, col in zip(meshes, colors):
        v = (np.asarray(m.vertices) @ R.T) - c
        n = np.asarray(m.face_normals) @ R.T
        keep = n[:, 2] > 0
        f = np.asarray(m.faces)[keep]
        sh = np.clip(n[keep] @ L, 0, 1) * 0.72 + 0.28
        px = v[:, 0] * scale + size / 2
        py = size / 2 - v[:, 1] * scale
        pz = v[:, 2]
        t = np.stack([px[f], py[f]], -1)              # (F,3,2)
        tris.append(t)
        cols.append(np.clip(np.array(col, float)[None, :] * sh[:, None], 0, 255).astype(np.uint8))
        depth.append(pz[f].mean(1))
    tris = np.vstack(tris); cols = np.vstack(cols); depth = np.concatenate(depth)
    order = np.argsort(depth)
    img = Image.new('RGB', (size, size), bg)
    dr = ImageDraw.Draw(img)
    for i in order:
        t = tris[i]
        dr.polygon([(t[0, 0], t[0, 1]), (t[1, 0], t[1, 1]), (t[2, 0], t[2, 1])],
                   fill=tuple(int(x) for x in cols[i]))
    return img

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
