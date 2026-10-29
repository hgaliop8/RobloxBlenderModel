"""Bibliothèque Blender du Ballast : mains et bras-chaînes construits par squelettes + modificateur Skin,
fusionnés par remaillage voxel, détaillés par déplacement ; matériaux Cycles (chair sale translucide, ongles).
Repère Blender : Z en haut, unité = mètre."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

# ------------------------------------------------------------------ outils
def coll(name='Ballast'):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c

def nrm(v): v = Vector(v); return v.normalized() if v.length > 1e-9 else Vector((1, 0, 0))

def frame(d, up):
    """repère (x = d, z = dos) orthonormé"""
    d = nrm(d); up = Vector(up); up = (up - d*up.dot(d)); up = up.normalized() if up.length > 1e-6 else nrm(d.orthogonal())
    s = up.cross(d)   # y = côté pouce
    return Matrix((d, s, up)).transposed()

class Skel:
    """squelette pour le modificateur Skin : sommets, arêtes, rayons"""
    def __init__(s): s.V, s.E, s.R = [], [], []
    def v(s, p, r):
        s.V.append(Vector(p)); s.R.append(r if isinstance(r, (tuple, list)) else (r, r)); return len(s.V) - 1
    def e(s, a, b): s.E.append((a, b))
    def chain(s, start, pts, radii):
        prev = start
        for p, r in zip(pts, radii):
            i = s.v(p, r); s.e(prev, i); prev = i
        return prev
    def merge(s, o, M=Matrix.Identity(4), sc=1.0, at=None):
        """ajoute un autre squelette transformé ; at = indice du sommet de ce squelette qui remplace le sommet 0 de o"""
        base = len(s.V); remap = {}
        for i, (p, r) in enumerate(zip(o.V, o.R)):
            if i == 0 and at is not None: remap[i] = at; continue
            remap[i] = s.v(M @ (p*sc), (r[0]*sc, r[1]*sc))
        for a, b in o.E: s.e(remap[a], remap[b])
        return remap

def skin_object(name, sk, sub=2, root=0):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(p) for p in sk.V], sk.E, []); me.update()
    ob = bpy.data.objects.new(name, me); coll().objects.link(ob)
    m = ob.modifiers.new('skin', 'SKIN'); m.use_smooth_shade = True; m.branch_smoothing = 0.6
    if not me.skin_vertices: me.skin_vertices.new()
    for i, r in enumerate(sk.R):
        sv = me.skin_vertices[0].data[i]; sv.radius = r; sv.use_root = (i == root)
    if sub:
        ss = ob.modifiers.new('sub', 'SUBSURF'); ss.levels = sub; ss.render_levels = sub
    return ob

def bake_mods(ob):
    """applique les modificateurs (maillage évalué)"""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); old = ob.data; ob.data = me; bpy.data.meshes.remove(old)
    return ob

def join(objs, name):
    objs = [o for o in objs if o]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join(); ob = bpy.context.object; ob.name = name; return ob

def remesh(ob, voxel=0.0025, smooth=4, adapt=0.0):
    m = ob.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = voxel; m.adaptivity = adapt; m.use_smooth_shade = True
    if smooth:
        s = ob.modifiers.new('sm', 'LAPLACIANSMOOTH'); s.iterations = smooth; s.lambda_factor = 0.35; s.use_volume_preserve = True
    return bake_mods(ob)

def displace(ob, kind='CLOUDS', size=0.05, strength=0.004, depth=2, mid=0.5, coords='OBJECT', basis='BLENDER_ORIGINAL', name=None):
    t = bpy.data.textures.new(name or f'tx_{kind}_{size}', kind)
    if kind in ('CLOUDS', 'VORONOI', 'MUSGRAVE'): t.noise_scale = size
    if kind == 'CLOUDS': t.noise_depth = depth; t.noise_basis = basis
    m = ob.modifiers.new('disp', 'DISPLACE'); m.texture = t; m.strength = strength; m.mid_level = mid; m.texture_coords = 'GLOBAL' if coords == 'GLOBAL' else 'LOCAL'
    return m

def shade_smooth(ob):
    for p in ob.data.polygons: p.use_smooth = True

# ------------------------------------------------------------------ la main (repère local : poignet à l'origine, doigts +X, dos +Z, pouce +Y)
FING_Y = (0.029, 0.0095, -0.0095, -0.028)
FING_L = (0.076, 0.087, 0.080, 0.063)
FING_R = (0.0082, 0.0086, 0.0081, 0.0071)

def hand(curl=0.35, spread=0.2, long=1.35, seed=0, thumb_curl=None, flat=False, gaunt=1.0, nails=True):
    """renvoie (squelette, ongles) ; ongles = liste de (position, direction, dos, longueur, largeur)"""
    rng = random.Random(seed); sk = Skel(); NL = []
    w = sk.v((0, 0, 0), 0.027)
    up = Vector((0, 0, 1))
    for k in range(4):
        y = FING_Y[k]; r = FING_R[k]
        m = sk.v((0.045, y*0.85, 0.003), 0.0148*gaunt); sk.e(w, m)
        K = sk.v((0.092, y, 0.005), r*1.38); sk.e(m, K)
        d = nrm((1.0, spread*y/0.026*0.32 + rng.uniform(-0.04, 0.04), -0.06 if flat else 0.0))
        L = FING_L[k]*long*rng.uniform(0.94, 1.07); p = Vector((0.092, y, 0.004)); prev = K
        c = curl*rng.uniform(0.7, 1.3); u = up.copy()
        for j, fr in enumerate((0.46, 0.3, 0.24)):
            if j > 0 or not flat:
                ang = c*(0.55 if j == 0 else 1.0)*(1.25 if j == 2 else 1.0)
                ax = u.cross(d); R = Matrix.Rotation(ang, 3, ax); d = (R @ d).normalized(); u = (R @ u).normalized()
            q = p + d*L*fr
            rr = r*(0.98, 0.9, 0.82)[j]
            if j < 2:   # articulation légèrement noueuse
                i = sk.v(q, rr*1.14)
            else:
                i = sk.v(q - d*rr*0.4, rr*0.92)
            sk.e(prev, i); prev = i
            if j == 2 and nails:
                NL.append((q - d*L*fr*0.38 + u*rr*0.55, d.copy(), u.copy(), L*fr*0.95*rng.uniform(0.9, 1.25), rr*1.65))
            p = q
    # pouce
    tc = curl if thumb_curl is None else thumb_curl
    T0 = sk.v((0.028, 0.026, -0.008), 0.018*gaunt); sk.e(w, T0)
    d = nrm((0.6, 0.62, -0.12)); u = nrm((0.1, -0.35, 0.93)); p = Vector((0.028, 0.026, -0.008)); prev = T0; r = 0.0125
    for j, ln in enumerate((0.036, 0.034, 0.028)):
        if j > 0:
            ax = u.cross(d); R = Matrix.Rotation(tc*0.9, 3, ax); d = (R @ d).normalized(); u = (R @ u).normalized()
        q = p + d*ln*long*0.95
        i = sk.v(q if j < 2 else q - d*r*0.4, r*(1.05 if j < 2 else 0.85)); sk.e(prev, i); prev = i
        if j == 2 and nails:
            NL.append((q - d*ln*0.35 + u*r*0.55, d.copy(), u.copy(), ln*0.9*rng.uniform(0.9, 1.2), r*1.6))
        p = q; r *= 0.9
    return sk, NL

def nail_objects(NL, M=Matrix.Identity(4), sc=1.0, name='Ongles'):
    bm = bmesh.new()
    for (p, d, u, ln, wd) in NL:
        F = frame(d, u); o = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=1.0)
        S = Matrix.Diagonal((ln*0.55, wd*0.5, 0.0016)).to_4x4()
        T = M @ Matrix.Translation(p*sc) @ F.to_4x4() @ Matrix.Diagonal((sc, sc, sc, 1)) @ Matrix.Translation((ln*0.12, 0, 0)) @ S
        for v in o['verts']:
            v.co = T @ v.co
            # ongle bombé, bout recourbé vers le bas
            pass
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll().objects.link(ob); shade_smooth(ob); return ob

# ------------------------------------------------------------------ bras-chaîne le long d'un chemin
def catmull(P, n_per=24):
    P = [Vector(p) for p in P]; out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(len(P) - 1, i + 2)]
        for s in range(n_per):
            t = s/n_per
            out.append(0.5*((2*p1) + (-p0 + p2)*t + (2*p0 - 5*p1 + 4*p2 - p3)*t*t + (-p0 + 3*p1 - 3*p2 + p3)*t*t*t))
    out.append(P[-1]); return out

class Path:
    def __init__(s, P):
        s.P = catmull(P); s.cum = [0.0]
        for i in range(1, len(s.P)): s.cum.append(s.cum[-1] + (s.P[i] - s.P[i - 1]).length)
        s.L = s.cum[-1]
    def at(s, x):
        x = min(max(x, 0.0), s.L); i = 0
        lo, hi = 0, len(s.cum) - 1
        while hi - lo > 1:
            mid = (lo + hi)//2
            if s.cum[mid] <= x: lo = mid
            else: hi = mid
        i = lo; f = (x - s.cum[i])/max(s.cum[i + 1] - s.cum[i], 1e-9)
        return s.P[i].lerp(s.P[i + 1], f), nrm(s.P[i + 1] - s.P[i])

def arm_chain(path, r_start=0.05, r_end=0.042, seed=1, up=(0, 0, 1), hand_scale=1.45, hand_kw=None, extra_hands=True, start=0.0):
    """bras fait d'avant-bras soudés coude à poignet le long du chemin ; renvoie (objets chair, ongles)"""
    rng = random.Random(seed); sk = Skel(); L = path.L; hand_len = 0.105*hand_scale
    x = start; prev = None; parts = []; NL_all = []; seg = 0
    upv = Vector(up)
    while x < L - hand_len - 0.06:
        ln = min(rng.uniform(0.33, 0.42), L - hand_len - x)
        if ln < 0.12: break
        r0 = r_start + (r_end - r_start)*(x/L); r1 = r0*0.56
        ts = (0.0, 0.1, 0.28, 0.5, 0.75, 1.0)
        rad = [r0*0.82, r0*1.0, r0*1.18, r0*0.95, r0*0.72, r1]
        for k, (t, rr) in enumerate(zip(ts, rad)):
            p, d = path.at(x + ln*t)
            if k == 0 and prev is not None:
                i = sk.v(p, rr); sk.e(prev, i)
            elif k == 0:
                i = sk.v(p, rr)
            else:
                i = sk.v(p, rr); sk.e(prev, i)
            prev = i
        # cubitus saillant et veines : chaînes fines à fleur de peau, fusionnées au remaillage
        ex = Skel(); ph = rng.uniform(0, 6.28)
        def off(t, ang, f):
            p, d = path.at(x + ln*t); sd = nrm(d.cross(upv)); nn = sd.cross(d)
            rr = r0*(1.0 + 0.18*math.exp(-((t - 0.28)/0.15)**2))*(1 - 0.44*t**1.25)
            return p + (sd*math.cos(ang) + nn*math.sin(ang))*rr*f, rr
        pts = [off(t, ph, 0.5) for t in (0.04, 0.3, 0.6, 0.92)]
        ex.chain(ex.v(*[pts[0][0], pts[0][1]*0.55]), [q for q, _ in pts[1:]], [rr*0.52 for _, rr in pts[1:]])
        for vk in range(2):
            a0 = ph + 2.2 + vk*1.9 + rng.uniform(-0.3, 0.3); tt = [0.1 + 0.8*j/7 for j in range(8)]
            vp = [off(t, a0 + 0.35*math.sin(t*9 + vk*2), 0.93)[0] for t in tt]
            ex.chain(ex.v(vp[0], 0.0032), vp[1:], [0.0036]*(len(vp) - 1))
        parts.append(skin_object(f'os{seed}_{seg}', ex, sub=1))
        # petite main atrophiée ou doigts qui pointent à certains raccords
        if extra_hands and seg % 3 == 2:
            p, d = path.at(x + ln*0.95); side = nrm(d.cross(upv))*(1 if seg % 2 else -1)
            hsk, hnl = hand(curl=0.9, spread=0.3, long=1.15, seed=seed*10 + seg, gaunt=0.9)
            F = frame(nrm(d*0.35 + side + upv*0.3), upv).to_4x4(); M = Matrix.Translation(p + side*(r1 + 0.03)) @ F
            parts.append(skin_object(f'atro{seed}_{seg}', _xf(hsk, M, 0.75)))
            NL_all.append((hnl, M, 0.75))
        x += ln + 0.03; seg += 1
    # la grande main au bout
    p, d = path.at(L - hand_len); i = sk.v(p, (r_end*0.56)); sk.e(prev, i)
    hk = dict(curl=0.25, spread=0.6, long=1.5, seed=seed*7); hk.update(hand_kw or {})
    hsk, hnl = hand(**hk)
    M = Matrix.Translation(p) @ frame(d, upv).to_4x4()
    sk.merge(hsk, M, hand_scale, at=i)
    NL_all.append((hnl, M, hand_scale))
    parts.insert(0, skin_object(f'bras{seed}', sk))
    return parts, NL_all

def _xf(sk, M, sc):
    o = Skel(); o.V = [M @ (p*sc) for p in sk.V]; o.R = [(r[0]*sc, r[1]*sc) for r in sk.R]; o.E = list(sk.E); return o

def nails_from(NL_all, name):
    obs = [nail_objects(nl, M, sc, f'{name}_{k}') for k, (nl, M, sc) in enumerate(NL_all)]
    return join(obs, name) if len(obs) > 1 else obs[0]

# ------------------------------------------------------------------ matériaux
def _n(nt, kind, loc, **kw):
    n = nt.nodes.new(kind); n.location = loc
    for k, v in kw.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n

def _mix_sockets(x):
    A = [i for i in x.inputs if i.name == 'A' and i.type == 'RGBA'][0]; B = [i for i in x.inputs if i.name == 'B' and i.type == 'RGBA'][0]
    R = [o for o in x.outputs if o.name == 'Result' and o.type == 'RGBA'][0]; return A, B, R

def ramp(nt, loc, stops):
    r = _n(nt, 'ShaderNodeValToRGB', loc); cr = r.color_ramp
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = stops[0][0]; cr.elements[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def mat_chair(name='Chair', grime=0.8, scale=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; L = nt.links
    nt.nodes.clear()
    out = _n(nt, 'ShaderNodeOutputMaterial', (1400, 0))
    b = _n(nt, 'ShaderNodeBsdfPrincipled', (1100, 0))
    b.inputs['Subsurface Weight'].default_value = 0.22
    b.inputs['Subsurface Radius'].default_value = (0.9, 0.35, 0.18)
    b.inputs['Subsurface Scale'].default_value = 0.012
    b.inputs['Specular IOR Level'].default_value = 0.45
    L.new(b.outputs[0], out.inputs['Surface'])
    tc = _n(nt, 'ShaderNodeTexCoord', (-1200, 0))
    co = tc.outputs['Object']
    def noise(loc, sc, det=4, rough=0.55, dist=0.0):
        n = _n(nt, 'ShaderNodeTexNoise', loc); n.inputs['Scale'].default_value = sc*scale; n.inputs['Detail'].default_value = det
        n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = dist; L.new(co, n.inputs['Vector']); return n
    def mix(loc, a, bb, fac, blend='MIX'):
        x = _n(nt, 'ShaderNodeMix', loc); x.data_type = 'RGBA'; x.blend_type = blend
        A, B, R = _mix_sockets(x)
        L.new(fac, x.inputs[0])
        if isinstance(a, tuple): A.default_value = a
        else: L.new(a, A)
        if isinstance(bb, tuple): B.default_value = bb
        else: L.new(bb, B)
        return R
    # base : gris cadavre, marbrures violacées, jaunissements
    n1 = noise((-900, 400), 4.0, 5, 0.6, 0.4)
    r1 = ramp(nt, (-650, 400), [(0.35, (0.150, 0.135, 0.118, 1)), (0.65, (0.118, 0.092, 0.095, 1))])
    L.new(n1.outputs['Fac'], r1.inputs[0])
    n2 = noise((-900, 150), 9.0, 3, 0.5)
    r2 = ramp(nt, (-650, 150), [(0.55, (0, 0, 0, 1)), (0.75, (1, 1, 1, 1))])
    L.new(n2.outputs['Fac'], r2.inputs[0])
    c = mix((-350, 300), r1.outputs['Color'], (0.17, 0.14, 0.08, 1), r2.outputs['Color'])
    # veines bleuâtres (bords de cellules)
    vo = _n(nt, 'ShaderNodeTexVoronoi', (-900, -100)); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 14*scale
    L.new(co, vo.inputs['Vector'])
    rv = ramp(nt, (-650, -100), [(0.0, (1, 1, 1, 1)), (0.035, (0, 0, 0, 1))])
    L.new(vo.outputs['Distance'], rv.inputs[0])
    nm = noise((-900, -330), 2.5, 2)
    rm = ramp(nt, (-650, -330), [(0.45, (0, 0, 0, 1)), (0.62, (0.55, 0.55, 0.55, 1))])
    L.new(nm.outputs['Fac'], rm.inputs[0])
    vm = _n(nt, 'ShaderNodeMath', (-400, -200), operation='MULTIPLY'); L.new(rv.outputs['Color'], vm.inputs[0]); L.new(rm.outputs['Color'], vm.inputs[1])
    c = mix((-150, 200), c, (0.06, 0.06, 0.09, 1), vm.outputs[0])
    # crasse : creux (occlusion), coulures, dessous
    ao = _n(nt, 'ShaderNodeAmbientOcclusion', (-900, -600)); ao.inputs['Distance'].default_value = 0.035; ao.samples = 8
    ra = ramp(nt, (-650, -600), [(0.35, (1, 1, 1, 1)), (0.9, (0, 0, 0, 1))])
    L.new(ao.outputs['AO'], ra.inputs[0])
    sm = _n(nt, 'ShaderNodeMapping', (-1000, -850)); sm.inputs['Scale'].default_value = (1, 1, 0.25); L.new(co, sm.inputs['Vector'])
    ns = _n(nt, 'ShaderNodeTexNoise', (-800, -850)); ns.inputs['Scale'].default_value = 7*scale; ns.inputs['Detail'].default_value = 4; L.new(sm.outputs[0], ns.inputs['Vector'])
    rs = ramp(nt, (-560, -850), [(0.42, (0, 0, 0, 1)), (0.68, (1, 1, 1, 1))])
    L.new(ns.outputs['Fac'], rs.inputs[0])
    gm0 = _n(nt, 'ShaderNodeMath', (-400, -700), operation='ADD', use_clamp=True); L.new(ra.outputs['Color'], gm0.inputs[0]); L.new(rs.outputs['Color'], gm0.inputs[1])
    nb = noise((-800, -1050), 3.2, 4, 0.6, 0.6); rb = ramp(nt, (-560, -1050), [(0.45, (0, 0, 0, 1)), (0.65, (0.7, 0.7, 0.7, 1))]); L.new(nb.outputs['Fac'], rb.inputs[0])
    gm = _n(nt, 'ShaderNodeMath', (-300, -700), operation='ADD', use_clamp=True); L.new(gm0.outputs[0], gm.inputs[0]); L.new(rb.outputs['Color'], gm.inputs[1])
    gk = _n(nt, 'ShaderNodeMath', (-150, -700), operation='MULTIPLY', use_clamp=True); L.new(gm.outputs[0], gk.inputs[0]); gk.inputs[1].default_value = grime
    c = mix((100, 100), c, (0.010, 0.008, 0.006, 1), gk.outputs[0])
    L.new(c, b.inputs['Base Color'])
    # rugosité : gras luisant dans la crasse
    rr = _n(nt, 'ShaderNodeMapRange', (300, -400)); rr.inputs['To Min'].default_value = 0.62; rr.inputs['To Max'].default_value = 0.3
    L.new(gk.outputs[0], rr.inputs['Value']); L.new(rr.outputs[0], b.inputs['Roughness'])
    # relief : pores + rides
    np_ = noise((-500, -1100), 380.0, 2, 0.5)
    wv = _n(nt, 'ShaderNodeTexVoronoi', (-500, -1300)); wv.feature = 'DISTANCE_TO_EDGE'; wv.inputs['Scale'].default_value = 70*scale
    L.new(co, wv.inputs['Vector'])
    wr = ramp(nt, (-350, -1300), [(0.0, (0, 0, 0, 1)), (0.06, (1, 1, 1, 1))]); L.new(wv.outputs['Distance'], wr.inputs[0])
    wm = _n(nt, 'ShaderNodeMath', (-200, -1300), operation='MULTIPLY'); L.new(wr.outputs['Color'], wm.inputs[0]); wm.inputs[1].default_value = 0.6
    hb = _n(nt, 'ShaderNodeMath', (-50, -1200), operation='ADD'); L.new(np_.outputs['Fac'], hb.inputs[0]); L.new(wm.outputs[0], hb.inputs[1])
    bp = _n(nt, 'ShaderNodeBump', (700, -600)); bp.inputs['Strength'].default_value = 0.16; bp.inputs['Distance'].default_value = 0.0006
    L.new(hb.outputs[0], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m

def mat_simple(name, col, rough=0.5, metal=0.0, noise_scale=0, noise_col=None, bump=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if noise_scale:
        tc = nt.nodes.new('ShaderNodeTexCoord'); n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = noise_scale; n.inputs['Detail'].default_value = 6
        nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
        x = nt.nodes.new('ShaderNodeMix'); x.data_type = 'RGBA'; nt.links.new(n.outputs['Fac'], x.inputs[0]); A, B, R = _mix_sockets(x)
        A.default_value = (*col, 1); B.default_value = (*(noise_col or [c*0.4 for c in col]), 1)
        nt.links.new(R, b.inputs['Base Color'])
        if bump:
            bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def mat_ongle():
    return mat_simple('Ongle', (0.2, 0.15, 0.07), 0.3, noise_scale=120, noise_col=(0.12, 0.08, 0.04), bump=0.3)

# ------------------------------------------------------------------ rendu
def setup_render(res=(1280, 720), samples=128, exposure=0.0):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = exposure
    return sc

def world(col=(0.003, 0.004, 0.006), strength=1.0):
    w = bpy.data.worlds.new('Nuit'); w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*col, 1); bg.inputs['Strength'].default_value = strength
    bpy.context.scene.world = w

def camera(loc, target, lens=50, name='Cam'):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.01
    ob = bpy.data.objects.new(name, cd); coll().objects.link(ob); ob.location = loc
    d = Vector(target) - Vector(loc); ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob

def light(kind, loc, energy, col=(1, 1, 1), size=0.5, target=None, name='L', spot=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = col
    if kind == 'AREA': ld.size = size
    if kind in ('POINT', 'SPOT'): ld.shadow_soft_size = size
    if spot: ld.spot_size = spot; ld.spot_blend = 0.4
    ob = bpy.data.objects.new(name, ld); coll().objects.link(ob); ob.location = loc
    if target: ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob

def render(path, cam):
    sc = bpy.context.scene; sc.camera = cam; sc.render.filepath = path; bpy.ops.render.render(write_still=True)
