"""Game-asset pipeline: QEM decimation, UV charting/packing, tangent frames, texture baking helpers."""
import numpy as np, heapq
from collections import defaultdict

# ======================================================================  QEM decimation
def _face_planes(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    area = np.linalg.norm(n, axis=1)
    n = n/np.maximum(area, 1e-12)[:, None]
    d = -(n*V[F[:, 0]]).sum(1)
    return np.concatenate([n, d[:, None]], 1), area*0.5

REJ = defaultdict(int)
def decimate(V, F, target, feature_w=1.0, log=None):
    V = np.asarray(V, float).copy(); F = np.asarray(F, np.int64).copy()
    nV = len(V)
    pl, ar = _face_planes(V, F)
    Q = np.zeros((nV, 4, 4))
    K = np.einsum('fi,fj->fij', pl, pl)*ar[:, None, None]
    for k in range(3): np.add.at(Q, F[:, k], K)
    vf = [set() for _ in range(nV)]
    for fi, (a, b, c) in enumerate(F): vf[a].add(fi); vf[b].add(fi); vf[c].add(fi)
    alive_f = np.ones(len(F), bool); alive_v = np.ones(nV, bool); ver = np.zeros(nV, np.int64)
    # boundary edges get a penalty quadric (meshes here are closed, but be safe)
    def cost(a, b):
        q = Q[a] + Q[b]
        A = q[:3, :3]; bb = -q[:3, 3]
        cand = [V[a], V[b], (V[a] + V[b])*0.5]
        try:
            if abs(np.linalg.det(A)) > 1e-12:
                p = np.linalg.solve(A, bb)
                if np.linalg.norm(p - (V[a] + V[b])*0.5) < 2.0*np.linalg.norm(V[a] - V[b]) + 1e-9: cand.append(p)
        except np.linalg.LinAlgError: pass
        best = None
        for p in cand:
            h = np.r_[p, 1.0]; e = h @ q @ h
            if best is None or e < best[0]: best = (e, p)
        return best
    heap = []
    edges = set()
    for a, b, c in F:
        for u, v in ((a, b), (b, c), (c, a)):
            edges.add((min(u, v), max(u, v)))
    for a, b in edges:
        e, p = cost(a, b); heap.append((e, a, b, ver[a], ver[b]))
    heapq.heapify(heap)
    nF = len(F); it = 0
    def nbrs(v):
        s = set()
        for f in vf[v]: s.update(F[f])
        s.discard(v); return s
    passes = 0
    while nF > target:
        if not heap:
            passes += 1
            if passes > 4: break
            es = set()
            for f in np.where(alive_f)[0]:
                x, y, z = F[f]
                for u, v in ((x, y), (y, z), (z, x)): es.add((min(u, v), max(u, v)))
            for u, v in es:
                e2, _ = cost(u, v); heap.append((e2, u, v, ver[u], ver[v]))
            heapq.heapify(heap)
            continue
        e, a, b, va, vb = heapq.heappop(heap)
        if not (alive_v[a] and alive_v[b]) or ver[a] != va or ver[b] != vb: continue
        shared = vf[a] & vf[b]
        if len(shared) != 2: REJ['shared'] += 1; continue
        na, nb = nbrs(a), nbrs(b)
        if len(na & nb) != 2: REJ['link'] += 1; continue                                         # link condition
        ec, p = cost(a, b)
        # flip test
        ok = True
        for f in (vf[a] | vf[b]) - shared:
            tri = F[f].copy(); old = V[tri]
            n0 = np.cross(old[1]-old[0], old[2]-old[0])
            tri = np.where((tri == a) | (tri == b), -1, tri)
            new = old.copy(); new[tri == -1] = p
            n1 = np.cross(new[1]-new[0], new[2]-new[0])
            l0, l1 = np.linalg.norm(n0), np.linalg.norm(n1)
            if l1 < 1e-14 or (n0 @ n1) < 0.2*l0*l1: ok = False; REJ['flip'] += 1; break
            # avoid needle triangles
            ed = np.linalg.norm(new - np.roll(new, 1, axis=0), axis=1); ed0 = np.linalg.norm(old - np.roll(old, 1, axis=0), axis=1)
            q1 = l1/(max(ed.max(), 1e-12)**2); q0 = l0/(max(ed0.max(), 1e-12)**2)
            if q1 < 0.012 and q1 < q0: ok = False; REJ['needle'] += 1; break
        if not ok:
            continue
        for f in shared: alive_f[f] = False; nF -= 1
        for f in shared:
            for v in F[f]: vf[v].discard(f)
        for f in vf[b]:
            F[f][F[f] == b] = a; vf[a].add(f)
        vf[b] = set(); alive_v[b] = False
        V[a] = p; Q[a] = Q[a] + Q[b]; ver[a] += 1
        for n in nbrs(a):
            ver[n] += 0
            e2, _ = cost(min(a, n), max(a, n))
            heapq.heappush(heap, (e2, min(a, n), max(a, n), ver[min(a, n)], ver[max(a, n)]))
        it += 1
        if log and it % 20000 == 0: log(f'    decimate {nF} tris')
    F = F[alive_f]
    used = np.unique(F); remap = -np.ones(nV, np.int64); remap[used] = np.arange(len(used))
    return V[used], remap[F]

def vertex_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3): np.add.at(N, F[:, k], n)
    return N/np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)

# ======================================================================  UV charting
def face_adjacency(F):
    em = defaultdict(list)
    for fi, (a, b, c) in enumerate(F):
        for u, v in ((a, b), (b, c), (c, a)): em[(min(u, v), max(u, v))].append(fi)
    adj = [[] for _ in range(len(F))]
    for fs in em.values():
        if len(fs) == 2: adj[fs[0]].append(fs[1]); adj[fs[1]].append(fs[0])
    return adj

def make_charts(V, F, cone_deg=58.0, max_area=None):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    fa = np.linalg.norm(fn, axis=1)*0.5
    fn = fn/np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    adj = face_adjacency(F)
    chart = -np.ones(len(F), np.int64); cos_c = np.cos(np.radians(cone_deg))
    order = list(np.argsort(-fa)); cid = 0; oi = 0
    while True:
        while oi < len(order) and chart[order[oi]] >= 0: oi += 1
        if oi >= len(order): break
        seed = order[oi]
        chart[seed] = cid; acc = fn[seed]*fa[seed]; cn = fn[seed].copy()
        front = [seed]
        while front:
            nxt = []
            for f in front:
                for g in adj[f]:
                    if chart[g] >= 0 or fn[g] @ cn < cos_c: continue
                    chart[g] = cid; nxt.append(g); acc = acc + fn[g]*fa[g]
            if nxt:
                cn2 = acc/np.maximum(np.linalg.norm(acc), 1e-12)
                # keep the cone valid for all members: only accept the drifted normal if every member still fits
                mem = np.where(chart == cid)[0]
                if np.all(fn[mem] @ cn2 > cos_c*0.97): cn = cn2
            front = nxt
        cid += 1
    return chart, fn, fa

def merge_small(chart, F, fn, fa, adj, min_area, cos_c):
    """Absorb small charts into the neighbouring chart they fit best (all faces must stay front-facing)."""
    for _ in range(6):
        ids, inv = np.unique(chart, return_inverse=True)
        area = np.bincount(inv, weights=fa)
        acc = np.zeros((len(ids), 3)); np.add.at(acc, inv, fn*fa[:, None])
        order = np.argsort(area); changed = False
        members = [[] for _ in ids]
        for f, c in enumerate(inv): members[c].append(f)
        members = [np.array(m) for m in members]
        dead = np.zeros(len(ids), bool)
        for s in order:
            if dead[s] or area[s] >= min_area or len(members[s]) == 0: continue
            cand = set()
            for f in members[s]:
                for g in adj[f]:
                    if inv[g] != s and not dead[inv[g]]: cand.add(inv[g])
            best = None; bestv = -1
            for t in cand:
                a2 = acc[s] + acc[t]; n2 = a2/max(np.linalg.norm(a2), 1e-12)
                allf = np.concatenate([members[s], members[t]])
                mn = (fn[allf] @ n2).min()
                if mn > cos_c and mn > bestv: best, bestv = t, mn
            if best is not None:
                inv[members[s]] = best; members[best] = np.concatenate([members[best], members[s]]); members[s] = np.array([], int)
                acc[best] += acc[s]; area[best] += area[s]; area[s] = 0; dead[s] = True; changed = True
        chart = ids[inv]
        if not changed: break
    return chart

def unwrap(V, F, cone_deg=58.0, min_chart_area=None):
    chart, fn, fa = make_charts(V, F, cone_deg)
    adj = face_adjacency(F)
    if min_chart_area:
        chart = merge_small(chart, F, fn, fa, adj, min_chart_area, 0.18)
    ids, inv = np.unique(chart, return_inverse=True)
    newV, newUV, newF, src = [], [], np.zeros_like(F), []
    charts = []
    base = 0
    for ci in range(len(ids)):
        fs = np.where(inv == ci)[0]
        acc = (fn[fs]*fa[fs, None]).sum(0); cn = acc/max(np.linalg.norm(acc), 1e-12)
        t1 = np.cross(cn, [0, 1, 0])
        if np.linalg.norm(t1) < 0.3: t1 = np.cross(cn, [1, 0, 0])
        t1 /= np.linalg.norm(t1); t2 = np.cross(cn, t1)
        vs, loc = np.unique(F[fs], return_inverse=True)
        P = V[vs]; uv = np.stack([P @ t1, P @ t2], 1)
        # rotate to min-area bbox (PCA)
        c = uv - uv.mean(0)
        if len(c) > 2:
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

def pack(charts_list, pad_px=4, res=1024, log=None):
    """charts_list: list of (uv array (modified in place via return), size). Uniform scale shelf packing into [0,1]^2."""
    sizes = np.array([c['size'] for c in charts_list])
    tot = (np.maximum(sizes[:, 0], 1e-6)*np.maximum(sizes[:, 1], 1e-6)).sum()
    def try_pack(s):
        pad = pad_px/res
        order = np.argsort(-(sizes[:, 1]))
        x = y = shelf_h = 0.0; pos = np.zeros((len(sizes), 2)); rot = np.zeros(len(sizes), bool)
        for i in order:
            w, h = sizes[i]*s
            if w > h*1.2 and w + 2*pad <= 1: pass
            if x + w + 2*pad > 1:
                x = 0; y += shelf_h; shelf_h = 0
            if w + 2*pad > 1: return None
            pos[i] = (x + pad, y + pad); x += w + 2*pad; shelf_h = max(shelf_h, h + 2*pad)
            if y + shelf_h > 1: return None
        return pos
    s = 0.9/np.sqrt(tot)
    lo, hi = 0.0, s*2
    best = None
    for _ in range(30):
        mid = (lo + hi)/2; p = try_pack(mid)
        if p is not None: lo = mid; best = (mid, p)
        else: hi = mid
    return best

def tangents(V, N, UV, F):
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    w0, w1, w2 = UV[F[:, 0]], UV[F[:, 1]], UV[F[:, 2]]
    e1, e2 = p1 - p0, p2 - p0; d1, d2 = w1 - w0, w2 - w0
    r = d1[:, 0]*d2[:, 1] - d2[:, 0]*d1[:, 1]
    r = np.where(np.abs(r) < 1e-14, 1e-14, r)
    sdir = (e1*d2[:, 1, None] - e2*d1[:, 1, None])/r[:, None]
    tdir = (e2*d1[:, 0, None] - e1*d2[:, 0, None])/r[:, None]
    T = np.zeros_like(V); B = np.zeros_like(V)
    for k in range(3): np.add.at(T, F[:, k], sdir); np.add.at(B, F[:, k], tdir)
    T = T - N*(T*N).sum(1, keepdims=True)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    w = np.where((np.cross(N, T)*B).sum(1) < 0, -1.0, 1.0)
    return T, w

# ======================================================================  rasterisation in UV space
def raster_uv(UVpx, F, res):
    """Return for each covered texel: (texel index, face index, barycentrics). UV in pixel units, v up."""
    out_t, out_f, out_b = [], [], []
    a, b, c = UVpx[F[:, 0]], UVpx[F[:, 1]], UVpx[F[:, 2]]
    xmin = np.floor(np.minimum(np.minimum(a[:, 0], b[:, 0]), c[:, 0]) - 0.5).astype(int)
    xmax = np.ceil(np.maximum(np.maximum(a[:, 0], b[:, 0]), c[:, 0]) + 0.5).astype(int)
    ymin = np.floor(np.minimum(np.minimum(a[:, 1], b[:, 1]), c[:, 1]) - 0.5).astype(int)
    ymax = np.ceil(np.maximum(np.maximum(a[:, 1], b[:, 1]), c[:, 1]) + 0.5).astype(int)
    for fi in range(len(F)):
        xs = np.arange(max(xmin[fi], 0), min(xmax[fi], res-1)+1); ys = np.arange(max(ymin[fi], 0), min(ymax[fi], res-1)+1)
        if len(xs) == 0 or len(ys) == 0: continue
        X, Y = np.meshgrid(xs + 0.5, ys + 0.5)
        P = np.stack([X.ravel(), Y.ravel()], 1)
        v0 = b[fi] - a[fi]; v1 = c[fi] - a[fi]; v2 = P - a[fi]
        den = v0[0]*v1[1] - v1[0]*v0[1]
        if abs(den) < 1e-12: continue
        l1 = (v2[:, 0]*v1[1] - v1[0]*v2[:, 1])/den
        l2 = (v0[0]*v2[:, 1] - v2[:, 0]*v0[1])/den
        l0 = 1 - l1 - l2
        eps = -0.02
        m = (l0 >= eps) & (l1 >= eps) & (l2 >= eps)
        if not m.any(): continue
        px = (P[m, 0] - 0.5).astype(int); py = (P[m, 1] - 0.5).astype(int)
        out_t.append(py*res + px); out_f.append(np.full(m.sum(), fi)); out_b.append(np.stack([l0[m], l1[m], l2[m]], 1))
    return np.concatenate(out_t), np.concatenate(out_f), np.concatenate(out_b)

def dilate(img, mask, iters=8):
    img = img.copy(); mask = mask.copy()
    H, W = mask.shape
    for _ in range(iters):
        acc = np.zeros_like(img, dtype=float); cnt = np.zeros((H, W))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                sm = np.roll(np.roll(mask, dy, 0), dx, 1); si = np.roll(np.roll(img, dy, 0), dx, 1)
                acc += si*sm[..., None] if img.ndim == 3 else si*sm; cnt += sm
        fill = (~mask) & (cnt > 0)
        if img.ndim == 3: img[fill] = acc[fill]/cnt[fill][:, None]
        else: img[fill] = acc[fill]/cnt[fill]
        mask = mask | fill
    return img, mask

# ======================================================================  fast native decimation
import os as _os, subprocess as _sp, tempfile as _tf
_QEM = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'qem')
def decimate_fast(V, F, target, lmax=1e9):
    V = np.ascontiguousarray(V, np.float64); F = np.ascontiguousarray(F, np.int32)
    with _tf.TemporaryDirectory() as d:
        a = _os.path.join(d, 'a.bin'); b = _os.path.join(d, 'b.bin')
        with open(a, 'wb') as fh:
            fh.write(np.array([len(V), len(F)], np.int32).tobytes()); fh.write(V.tobytes()); fh.write(F.tobytes())
        _sp.run([_QEM, a, b, str(int(target)), str(float(lmax))], check=True)
        raw = open(b, 'rb').read()
    nv, nf = np.frombuffer(raw[:8], np.int32)
    V2 = np.frombuffer(raw[8:8+nv*24], np.float64).reshape(-1, 3).copy()
    F2 = np.frombuffer(raw[8+nv*24:8+nv*24+nf*12], np.int32).reshape(-1, 3).astype(np.int64)
    return V2, F2
