import numpy as np
import gamemesh as G

FORCED2 = {}
def unwrap_split(V, F, cone_deg=60.0, min_area=0.004, seg=0.62, blade=False, ring=False):
    FORCED2.clear()
    chart, fn, fa = G.make_charts(V, F, cone_deg)
    adj = G.face_adjacency(F)
    chart = G.merge_small(chart, F, fn, fa, adj, min_area, 0.18)
    cen = V[F].mean(1)
    forced = {}
    if blade:
        # flat sides: planar XY projection cut into equal x-bricks; everything else keeps its cone charts
        x0, x1 = V[:, 0].min(), V[:, 0].max(); nb = 6; segx = (x1 - x0)/nb
        side = np.where(fn[:, 2] > 0.35, 1, np.where(fn[:, 2] < -0.35, -1, 0))
        xb = np.minimum(((cen[:, 0] - x0)/segx).astype(int), nb - 1)
        base = chart.max() + 1
        for sgn in (1, -1):
            for k in range(nb):
                m = (side == sgn) & (xb == k)
                if m.any():
                    cid = base + (0 if sgn > 0 else nb) + k; chart[m] = cid; forced[cid] = sgn
    ids = np.unique(chart); new = np.zeros_like(chart); nid = 0
    for c in ids:
        fs = np.where(chart == c)[0]
        if c in forced:
            new[fs] = nid; forced_new = forced[c]; FORCED2[nid] = forced[c]; nid += 1; continue
        P = cen[fs]; m = P.mean(0)
        if len(fs) > 3:
            w, ev = np.linalg.eigh((P - m).T @ (P - m)); ax = ev[:, -1]
        else: ax = np.array([1.0, 0, 0])
        s = (P - m) @ ax; ext = s.max() - s.min()
        nb = max(1, int(np.ceil(ext/seg)))
        b = np.minimum(((s - s.min())/max(ext, 1e-9)*nb).astype(int), nb - 1)
        for k in range(nb):
            sel = fs[b == k]
            if len(sel): new[sel] = nid; nid += 1
    chart = new
    if ring:
        th = np.arctan2(cen[:, 2], cen[:, 1]); sec = np.floor((th + np.pi)/(2*np.pi)*12).astype(int) % 12
        chart = chart*12 + sec
    ids, inv = np.unique(chart, return_inverse=True)
    idmap = {c: i for i, c in enumerate(ids)}
    newV, newUV, newF, src, charts = [], [], np.zeros_like(F), [], []
    base = 0
    for ci in range(len(ids)):
        fs = np.where(inv == ci)[0]
        acc = (fn[fs]*fa[fs, None]).sum(0); cn = acc/max(np.linalg.norm(acc), 1e-12)
        t1 = np.cross(cn, [0, 1, 0])
        if np.linalg.norm(t1) < 0.3: t1 = np.cross(cn, [1, 0, 0])
        t1 /= np.linalg.norm(t1); t2 = np.cross(cn, t1)
        fz = FORCED2.get(ids[ci])
        if fz is not None: t1 = np.array([float(fz), 0, 0]); t2 = np.array([0, 1.0, 0])
        vs, loc = np.unique(F[fs], return_inverse=True)
        P = V[vs]; uv = np.stack([P @ t1, P @ t2], 1)
        c = uv - uv.mean(0)
        if len(c) > 2 and fz is None:
            w, ev = np.linalg.eigh(c.T @ c); R = ev[:, ::-1]
            if np.linalg.det(R) < 0: R[:, 1] *= -1
            uv = c @ R
        uv = np.nan_to_num(uv - uv.min(0))
        if uv[:, 1].max() > uv[:, 0].max():
            uv = np.stack([uv[:, 1], -uv[:, 0]], 1); uv = uv - uv.min(0)
        newV.append(P); newUV.append(uv); src.append(vs)
        newF[fs] = loc.reshape(-1, 3) + base
        charts.append(dict(start=base, n=len(vs), size=uv.max(0)))
        base += len(vs)
    return np.vstack(newV), np.vstack(newUV), newF, np.concatenate(src), charts

def fix_normals(g):
    N = g['N']; bad = np.linalg.norm(N, axis=1) < 0.5
    if bad.any():
        fn = np.cross(g['V'][g['F'][:, 1]] - g['V'][g['F'][:, 0]], g['V'][g['F'][:, 2]] - g['V'][g['F'][:, 0]])
        area = np.linalg.norm(fn, axis=1)
        for fi in np.argsort(area):
            for v in g['F'][fi]:
                if bad[v]: N[v] = fn[fi]/max(area[fi], 1e-12)
        g['N'] = N/np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def _skyline(sizes, s, pad):
    """bottom-left skyline packing into [0,1]^2; returns positions, rotation flags or None"""
    order = np.argsort(-np.maximum(sizes[:, 0], sizes[:, 1]))
    sky = [(0.0, 1.0, 0.0)]          # segments (x0, x1, y)
    pos = np.zeros((len(sizes), 2)); rot = np.zeros(len(sizes), bool)
    for i in order:
        best = None
        for r in (False, True):
            w, h = (sizes[i][::-1] if r else sizes[i])*s + 2*pad
            if w > 1: continue
            for k in range(len(sky)):
                x0 = sky[k][0]
                if x0 + w > 1 + 1e-9: break
                # height needed over [x0, x0+w]
                y = 0.0; j = k
                while j < len(sky) and sky[j][0] < x0 + w - 1e-12:
                    y = max(y, sky[j][2]); j += 1
                if y + h > 1 + 1e-9: continue
                score = (y + h, x0)
                if best is None or score < best[0]: best = (score, x0, y, w, h, r)
        if best is None: return None
        _, x0, y, w, h, r = best
        pos[i] = (x0 + pad, y + pad); rot[i] = r
        new = []
        for (a, b, yy) in sky:
            if b <= x0 or a >= x0 + w: new.append((a, b, yy)); continue
            if a < x0: new.append((a, x0, yy))
            if b > x0 + w: new.append((x0 + w, b, yy))
        new.append((x0, x0 + w, y + h)); new.sort()
        merged = []
        for seg in new:
            if merged and abs(merged[-1][2] - seg[2]) < 1e-12 and abs(merged[-1][1] - seg[0]) < 1e-12: merged[-1] = (merged[-1][0], seg[1], seg[2])
            else: merged.append(seg)
        sky = merged
    return pos, rot

def pack_skyline(charts, pad_px=4, res=1024):
    sizes = np.array([np.maximum(c['size'], 1e-6) for c in charts]); pad = pad_px/res
    tot = (sizes[:, 0]*sizes[:, 1]).sum()
    lo, hi = 0.0, 1.2/np.sqrt(tot); best = None
    for _ in range(26):
        mid = (lo + hi)/2; r = _skyline(sizes, mid, pad)
        if r is not None: lo = mid; best = (mid, r[0], r[1])
        else: hi = mid
    return best

def apply_pack(geo, charts, s, pos, rot):
    for c, p, r in zip(charts, pos, rot):
        g = geo[c['piece']]; sl = slice(c['start'], c['start'] + c['n'])
        uv = g['UV'][sl]
        if r: uv = np.stack([uv[:, 1], c['size'][0] - uv[:, 0]], 1)
        g['UV'][sl] = uv*s + p
