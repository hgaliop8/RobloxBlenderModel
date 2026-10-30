"""Ballast — l'amas complet, les trois bras posés le long de leurs chemins, et le décor (coupe de wagon + voie).
Repère Blender : X = longueur du train, Y = largeur (le spectateur est côté -Y), Z = haut ; mètres."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
import ballast_bl as B

def W(x, y, z):
    """repère de l'ancien modèle (y en haut, z vers le spectateur) -> Blender"""
    return Vector((x, -z, y))

FLOOR_LO, FLOOR_HI = 1.05, 1.15
RAIL_Y, RAIL_TOP = 0.7175, 0.32
WALL_Y = 1.45
VENT = (0.9, -0.45, 0.25, 0.12)          # centre x, centre y, demi x, demi y
WIN = (0.5, 1.95, 2.75, 0.75)            # centre x, bas, haut, demi-largeur
WIN_GLASS_TOP = 2.42
WC = Vector((-2.45, 0.85, FLOOR_HI))
WC_WALL_X = -1.55
MASS_C = Vector((0, 0, 0.73)); MASS_R = Vector((1.2, 0.56, 0.3))
MO = W(0.15, 0.7, 0.56); MN = Vector((0.05, -1.0, -0.15)).normalized()

# ================================================================ maillages simples
def mesh_obj(name, bm, mat=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); B.coll().objects.link(ob)
    if mat: ob.data.materials.append(mat)
    return ob

def ell_bm(bm, c, r, R=Matrix.Identity(3), seg=24):
    o = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg//2, radius=1.0)
    M = Matrix.Translation(c) @ R.to_4x4() @ Matrix.Diagonal((*r, 1))
    for v in o['verts']: v.co = M @ v.co

def box_bm(bm, c, h, R=Matrix.Identity(3)):
    o = bmesh.ops.create_cube(bm, size=2.0)
    M = Matrix.Translation(c) @ R.to_4x4() @ Matrix.Diagonal((*h, 1))
    for v in o['verts']: v.co = M @ v.co

def box(name, c, h, mat, bevel=0.0, seg=2):
    bm = bmesh.new(); box_bm(bm, Vector(c), h); ob = mesh_obj(name, bm, mat)
    if bevel:
        m = ob.modifiers.new('bev', 'BEVEL'); m.width = bevel; m.segments = seg; m.limit_method = 'ANGLE'
        for p in ob.data.polygons: p.use_smooth = True
        ob.data.set_sharp_from_angle(angle=math.radians(40)) if hasattr(ob.data, 'set_sharp_from_angle') else None
    return ob

def cut(ob, cutters, solver='EXACT'):
    for c in cutters:
        m = ob.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; m.solver = solver
    B.bake_mods(ob)
    for c in cutters: bpy.data.objects.remove(c)
    return ob

# ================================================================ l'amas
def surf_point(th, ph, R=(1.25, 0.6, 0.32)):
    dv = Vector((math.cos(ph)*math.cos(th), math.cos(ph)*math.sin(th), math.sin(ph)))
    p = MASS_C + Vector((dv.x*R[0], dv.y*R[1], dv.z*R[2])); n = Vector((dv.x/R[0], dv.y/R[1], dv.z/R[2])).normalized()
    return p, n

def proj(p, k):
    q = Vector(((p - MASS_C).x/MASS_R.x, (p - MASS_C).y/MASS_R.y, (p - MASS_C).z/MASS_R.z))
    q = q.normalized()*k; return MASS_C + Vector((q.x*MASS_R.x, q.y*MASS_R.y, q.z*MASS_R.z))

def nrm_at(p):
    q = p - MASS_C; return Vector((q.x/MASS_R.x**2, q.y/MASS_R.y**2, q.z/MASS_R.z**2)).normalized()

def forearm_skel(sk, a, b, r0, r1, start=None):
    """avant-bras simple (ventre musculaire, poignet fin) ; renvoie l'indice du poignet"""
    a = Vector(a); b = Vector(b); prev = start
    for t, f in ((0.0, 0.85), (0.25, 1.15), (0.55, 0.92), (0.8, 0.72), (1.0, None)):
        r = r1 if f is None else r0*f
        i = sk.v(a.lerp(b, t), r)
        if prev is not None: sk.e(prev, i)
        prev = i
    return prev

def amas(seed=42, n_arms=195, log=print):
    rng = random.Random(seed); obs = []; NL_all = []
    bm = bmesh.new()
    for c, r in ((W(0.0, 0.76, 0.0), (0.82, 0.36, 0.18)), (W(-0.6, 0.78, 0.08), (0.42, 0.28, 0.17)), (W(0.65, 0.75, -0.08), (0.38, 0.29, 0.17))):
        ell_bm(bm, c, r, seg=32)
    obs.append(mesh_obj('noyau', bm))
    # le nid : des bras emmêlés qui s'enroulent autour de l'amas
    for i in range(n_arms):
        th = rng.uniform(0, 2*math.pi) if i < 150 else -math.pi/2 + rng.gauss(0, 0.55)
        ph = rng.uniform(-1.4, 1.25); k0 = rng.uniform(0.8, 1.02)
        p, n = surf_point(th, ph); p = proj(p, k0)
        t = n.cross(Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))).normalized(); pts = [p]
        L = rng.uniform(0.45, 1.05); nstep = int(L/0.07); lift = rng.random() < 0.22
        for st in range(nstep):
            n = nrm_at(pts[-1])
            t = (t - n*t.dot(n) + n.cross(t)*rng.gauss(0, 1)*0.35).normalized()
            kk = k0 + (0.02 + 0.025*st if lift else 0.012*math.sin(st*0.9 + i))
            pts.append(proj(pts[-1] + t*0.07, kk))
        if min((q - MO).length for q in pts) < 0.3: continue
        r0 = rng.uniform(0.034, 0.058); nr = len(pts); el = rng.uniform(0.3, 0.6)
        sk = B.Skel(); prev = None
        for j, q in enumerate(pts):
            f = j/max(nr - 1, 1); r = r0*(1 - 0.32*f)*(1 + 0.2*math.exp(-((f - el)/0.08)**2))
            ii = sk.v(q, r)
            if prev is not None: sk.e(prev, ii)
            prev = ii
        if rng.random() < 0.62 and nr > 2:
            d = (pts[-1] - pts[-2]).normalized(); n = nrm_at(pts[-1])
            if lift: d = (d + n*0.8).normalized()
            curl = rng.choice([0.05, 0.4, 0.9, 1.2])
            hsk, hnl = B.hand(curl=curl, spread=rng.uniform(0, 0.7), long=rng.uniform(1.2, 1.5), seed=300 + i, flat=curl < 0.1)
            sc = r0*0.68/0.027*1.05
            M = Matrix.Translation(pts[-1]) @ B.frame(d, n).to_4x4()
            sk.merge(hsk, M, sc, at=prev); NL_all.append((hnl, M, sc))
        obs.append(B.skin_object(f'nid{i}', sk, sub=1))
    log(f'nid : {len(obs)} objets')
    # mains qui sortent de partout
    for i in range(16):
        th = rng.uniform(0, 2*math.pi); ph = rng.uniform(-1.2, 0.35); p, n = surf_point(th, ph)
        if (p - MO).length < 0.42: continue
        t = n.cross(Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))).normalized(); d = (n*rng.uniform(0.2, 0.8) + t).normalized()
        sc = rng.choice([0.45, 0.55, 0.65, 0.8])*1.25; curl = rng.choice([0.05, 0.3, 0.6, 1.0]); em = rng.uniform(-0.02, 0.12)
        sk = B.Skel(); O = p + n*em - d*0.06*sc
        wi = forearm_skel(sk, p - n*0.08, O, 0.032*sc*1.2, 0.026*sc)
        hsk, hnl = B.hand(curl=curl, spread=rng.uniform(0, 0.5), long=rng.uniform(1.15, 1.5), seed=i, flat=curl < 0.1)
        M = Matrix.Translation(O) @ B.frame(d, n if abs(n.dot(d)) < 0.95 else Vector((0, 0, 1))).to_4x4()
        sk.merge(hsk, M, sc, at=wi); NL_all.append((hnl, M, sc)); obs.append(B.skin_object(f'main{i}', sk))
    # mains plaquées sous le plancher, doigts écartés
    for k in range(10):
        a = k/10*2*math.pi + 0.2; O = MASS_C + Vector((math.cos(a)*1.35, math.sin(a)*0.66, 0)); O.z = FLOOR_LO - 0.02
        d = Vector((math.cos(a), math.sin(a)*1.2, 0)).normalized()
        sk = B.Skel(); wi = forearm_skel(sk, MASS_C + Vector((math.cos(a)*0.95, math.sin(a)*0.42, 0.12)), O - d*0.03 - Vector((0, 0, 0.01)), 0.035, 0.03)
        hsk, hnl = B.hand(curl=0.02, spread=0.9, long=1.45, seed=60 + k, flat=True, thumb_curl=0.1)
        M = Matrix.Translation(O) @ B.frame(d, Vector((0, 0, -1))).to_4x4(); sk.merge(hsk, M, 1.25, at=wi); NL_all.append((hnl, M, 1.25))
        obs.append(B.skin_object(f'plaque{k}', sk))
    # mains qui pendent et agrippent les rails
    for k, (x, sg) in enumerate(((-0.75, 1), (0.55, 1), (-0.3, -1), (0.95, -1))):
        top = MASS_C + Vector((x, -sg*0.38, -0.22)); grip = Vector((x + 0.05, -sg*(RAIL_Y - 0.03), RAIL_TOP + 0.03))
        sk = B.Skel(); wi = forearm_skel(sk, top, grip + Vector((0, sg*0.05, 0.09)), 0.038, 0.03)
        hsk, hnl = B.hand(curl=1.15, spread=0.1, long=1.3, seed=90 + k, thumb_curl=1.0)
        M = Matrix.Translation(grip + Vector((0, sg*0.06, 0.07))) @ B.frame(Vector((0, -sg*0.35, -1)), Vector((0, sg, 0))).to_4x4()
        sk.merge(hsk, M, 1.2, at=wi); NL_all.append((hnl, M, 1.2)); obs.append(B.skin_object(f'rail{k}', sk))
    log(f'mains : {len(obs)} objets au total')
    for o in obs: B.bake_mods(o)
    ob = B.join(obs, 'Amas')
    log(f'joint : {len(ob.data.vertices)} sommets')
    ob = B.remesh(ob, voxel=VOX_AMAS, smooth=3)
    log(f'remaillé : {len(ob.data.vertices)} sommets')
    # bouche : un entonnoir de gencives, rangées de dents crochues tournées vers la gorge
    cutter = mouth_solid('bouche_cut', margin=0.012, front=0.2)
    m = ob.modifiers.new('bouche', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'FAST'
    B.displace(ob, 'CLOUDS', 0.2, 0.014, 2, name='plis_amas'); B.displace(ob, 'CLOUDS', 0.045, 0.004, 2, name='bourrelets_amas')
    B.displace(ob, 'VORONOI', 0.007, 0.0009, name='peau_amas')
    B.bake_mods(ob); bpy.data.objects.remove(cutter); B.shade_smooth(ob)
    log(f'amas final : {len(ob.data.polygons)} faces')
    fond = mouth_gums('Gencives')
    dents = mouth_teeth('Dents')
    log(f'bouche : {len(fond.data.polygons)} faces de gencives, {len(dents.data.polygons)} faces de dents')
    # mains qui bordent la bouche, doigts recourbés par-dessus la lèvre
    rim = []
    t1, t2 = mouth_axes()
    for k in range(12):
        a = k/12*2*math.pi + 0.13; rp = MO + (t1*math.cos(a)*MOUTH_A*1.2 + t2*math.sin(a)*MOUTH_B*1.2); inward = (MO - MN*0.05 - rp).normalized()
        hsk, hnl = B.hand(curl=0.95, spread=0.25, long=1.15, seed=200 + k)
        M = Matrix.Translation(rp - inward*0.12 + MN*0.02) @ B.frame(inward, MN).to_4x4()
        rim.append(B.skin_object(f'levre{k}', B._xf(hsk, M, 0.95))); NL_all.append((hnl, M, 0.95))
    # lèvres : bourrelet de chair roulé tout autour de l'ouverture
    lsk = B.Skel(); prev = first = None; nl = 72
    for k in range(nl):
        a = k/nl*2*math.pi; wob = 1 + 0.05*math.sin(a*7 + 1.3) + 0.03*math.sin(a*13)
        p = MO + MN*0.004 + (t1*math.cos(a)*MOUTH_A + t2*math.sin(a)*MOUTH_B)*1.1*wob
        i = lsk.v(p, 0.03*(1 + 0.25*math.sin(a*5 + 0.7)))
        if prev is not None: lsk.e(prev, i)
        else: first = i
        prev = i
    lsk.e(prev, first); rim.append(B.skin_object('levre_bourrelet', lsk, sub=2))
    for o in rim: B.bake_mods(o)
    rimo = B.remesh(B.join(rim, 'Levres'), voxel=0.0018, smooth=2); B.shade_smooth(rimo)
    nails = B.nails_from(NL_all, 'OnglesAmas')
    # cailloux de ballast incrustés, tire-fonds rouillés
    bm = bmesh.new()
    for k in range(80):
        th = rng.uniform(0, 2*math.pi); ph = rng.uniform(-1.3, -0.25); p, n = surf_point(th, ph); r = rng.uniform(0.018, 0.042)
        if (p - MO).length < 0.4: continue
        o = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        R = Matrix.Rotation(rng.uniform(0, 3), 3, Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized())
        sc = Vector((r, r*rng.uniform(0.6, 0.9), r*rng.uniform(0.7, 1.0)))
        for v in o['verts']:
            q = v.co; q = Vector((q.x*sc.x, q.y*sc.y, q.z*sc.z))*(1 + 0.18*(rng.random() - 0.5)); v.co = p - n*r*0.25 + R @ q
    stones = mesh_obj('CaillouxAmas', bm)
    bm = bmesh.new()
    for k, (th, ph) in enumerate(((0.7, -0.4), (2.6, -0.6), (4.1, -0.2), (5.4, -0.7))):
        p, n = surf_point(th, ph); d = (-n + Vector((rng.gauss(0, 0.3), rng.gauss(0, 0.3), rng.gauss(0, 0.3)))).normalized()
        o = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.011, radius2=0.009, depth=0.2)
        Mx = Matrix.Translation(p + d*0.04) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        for v in o['verts']: v.co = Mx @ v.co
        o = bmesh.ops.create_cylinder(bm, cap_ends=True, segments=12, radius=0.022, depth=0.016) if hasattr(bmesh.ops, 'create_cylinder') else bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.022, radius2=0.022, depth=0.016)
        Mh = Matrix.Translation(p - d*0.062) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        for v in o['verts']: v.co = Mh @ v.co
    spikes = mesh_obj('TireFonds', bm)
    return ob, rimo, fond, nails, stones, spikes, dents

# ================================================================ la bouche
VOX_AMAS = 0.0028
MOUTH_A, MOUTH_B = 0.21, 0.145           # demi-axes de l'ouverture (horizontal, vertical)
# profil de l'entonnoir : (échelle de l'ellipse, profondeur sous l'ouverture)
MOUTH_PROF = [(1.14, -0.02), (1.08, 0.0), (1.0, 0.012), (0.9, 0.04), (0.8, 0.075), (0.69, 0.11), (0.58, 0.145), (0.47, 0.18),
              (0.37, 0.215), (0.28, 0.25), (0.2, 0.29), (0.14, 0.33), (0.09, 0.37), (0.05, 0.4), (0.0, 0.41)]
TEETH_RINGS = [(0.03, 26, 0.062, 0.0115), (0.075, 24, 0.054, 0.0102), (0.12, 21, 0.046, 0.009), (0.165, 18, 0.038, 0.008),
               (0.21, 15, 0.031, 0.007), (0.255, 12, 0.025, 0.006), (0.3, 9, 0.019, 0.005)]

def mouth_axes():
    t1 = MN.cross(Vector((0, 0, 1))).normalized(); t2 = MN.cross(t1).normalized()
    if t2.z < 0: t2 = -t2
    return t1, t2

def prof_at(depth):
    for (s0, d0), (s1, d1) in zip(MOUTH_PROF[:-1], MOUTH_PROF[1:]):
        if d0 <= depth <= d1: return s0 + (s1 - s0)*(depth - d0)/max(d1 - d0, 1e-9)
    return MOUTH_PROF[-1][0]

def ridge(depth):
    """bourrelet de gencive à chaque rangée de dents"""
    return sum(math.exp(-((depth - d)/0.012)**2) for d, *_ in TEETH_RINGS)

def mouth_solid(name, margin=0.0, front=0.0):
    t1, t2 = mouth_axes(); bm = bmesh.new(); seg = 64
    prof = ([(1.6, -front)] if front else []) + MOUTH_PROF
    rings = []
    for sc, d in prof:
        ring = []
        for j in range(seg):
            a = j/seg*2*math.pi; k = sc + margin/MOUTH_B
            ring.append(bm.verts.new(MO - MN*d + t1*math.cos(a)*MOUTH_A*k + t2*math.sin(a)*MOUTH_B*k))
        rings.append(ring)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for j in range(seg): bm.faces.new((r0[j], r0[(j + 1) % seg], r1[(j + 1) % seg], r1[j]))
    bm.faces.new(rings[0]); bm.faces.new(rings[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm)

def mouth_gums(name):
    """paroi interne de la bouche (gencives), avec épaisseur, bourrelets à chaque rangée de dents, plis vers la gorge"""
    t1, t2 = mouth_axes(); bm = bmesh.new(); seg = 96; nd = 120
    rings = []
    d0, d1 = MOUTH_PROF[0][1], MOUTH_PROF[-2][1]
    for i in range(nd + 1):
        d = d0 + (d1 - d0)*i/nd; sc = prof_at(d)*(1 - 0.06*ridge(d)); ring = []
        for j in range(seg):
            a = j/seg*2*math.pi; fold = 1 + 0.035*math.sin(a*14 + d*40)*min(1, d/0.15)    # plis longitudinaux
            ring.append(bm.verts.new(MO - MN*d + (t1*math.cos(a)*MOUTH_A + t2*math.sin(a)*MOUTH_B)*sc*fold))
        rings.append(ring)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for j in range(seg): bm.faces.new((r0[j], r1[j], r1[(j + 1) % seg], r0[(j + 1) % seg]))
    bm.faces.new(rings[-1])
    ob = mesh_obj(name, bm)
    so = ob.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.016; so.offset = 0.0
    ss = ob.modifiers.new('sub', 'SUBSURF'); ss.levels = 1
    B.bake_mods(ob); B.shade_smooth(ob)
    return ob

def mouth_teeth(name, sub=2):
    rng = random.Random(77); t1, t2 = mouth_axes(); sk = B.Skel()
    for ri, (d, n, L, rb) in enumerate(TEETH_RINGS):
        sc = prof_at(d)*(1 - 0.06*ridge(d))
        for k in range(n):
            a = (k + 0.5*(ri % 2) + rng.uniform(-0.15, 0.15))/n*2*math.pi
            P = MO - MN*d + (t1*math.cos(a)*MOUTH_A + t2*math.sin(a)*MOUTH_B)*sc
            rad = -(t1*math.cos(a)*MOUTH_A + t2*math.sin(a)*MOUTH_B).normalized()
            ln = L*rng.uniform(0.75, 1.2); broken = rng.random() < 0.08
            if broken: ln *= 0.45
            dv = (rad*0.8 - MN*0.55 + Vector((rng.gauss(0, 0.08), rng.gauss(0, 0.08), rng.gauss(0, 0.08)))).normalized()
            pts = []; p = P - rad*0.006; rads = []
            for j, (f, rr) in enumerate(((0.0, 1.0), (0.22, 0.85), (0.48, 0.6), (0.72, 0.36), (0.9, 0.16), (1.0, 0.05))):
                if broken and f > 0.72: break
                ang = 0.55*f*f                                   # crochet : la pointe se recourbe vers la gorge
                dd = (dv*math.cos(ang) - MN*math.sin(ang)).normalized()
                pts.append(P - rad*0.006 + dd*ln*f if j else P - rad*0.006); rads.append(max(rb*rr, 0.0007))
            i0 = sk.v(pts[0], rads[0]); sk.chain(i0, pts[1:], rads[1:])
    ob = B.skin_object(name, sk, sub=sub); B.bake_mods(ob); B.shade_smooth(ob)
    return ob

def mat_dents():
    m = B.mat_simple('Dent', (0.34, 0.29, 0.19), 0.32, noise_scale=90, noise_col=(0.13, 0.085, 0.04), bump=0.15)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Subsurface Weight'].default_value = 0.15; b.inputs['Subsurface Radius'].default_value = (0.8, 0.6, 0.3); b.inputs['Subsurface Scale'].default_value = 0.004
    # base des dents plus sombre (dans la gencive), pointes plus claires
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.02
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; A, Bs, R = B._mix_sockets(mx)
    src = b.inputs['Base Color'].links[0].from_socket
    nt.links.new(src, A); nt.links.new(ao.outputs['Color'], Bs); mx.inputs[0].default_value = 0.8; nt.links.new(R, b.inputs['Base Color'])
    return m

def mat_gencive():
    m = B.mat_simple('Gencive', (0.05, 0.011, 0.015), 0.42, noise_scale=18, noise_col=(0.016, 0.004, 0.008), bump=0.3)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Subsurface Weight'].default_value = 0.2; b.inputs['Subsurface Radius'].default_value = (1.0, 0.2, 0.1); b.inputs['Subsurface Scale'].default_value = 0.006
    b.inputs['Coat Weight'].default_value = 0.12; b.inputs['Coat Roughness'].default_value = 0.08     # salive
    return m

# ================================================================ bras posés dans la scène
PATHS = {
    'BrasGrille': [(0.45, 0.78, 0.22), (0.82, 0.92, 0.42), (0.9, 1.06, 0.45), (0.9, 1.3, 0.45), (1.0, 1.75, 0.47), (1.35, 2.05, 0.55), (1.85, 2.08, 0.72), (2.25, 1.9, 0.8)],
    'BrasFenetre': [(-0.1, 0.78, -0.4), (0.15, 0.86, -1.1), (0.3, 0.95, -1.6), (0.38, 1.4, -1.63), (0.45, 2.1, -1.62), (0.5, 2.55, -1.58), (0.55, 2.62, -1.44),
                    (0.65, 2.55, -1.2), (0.85, 2.2, -1.0), (1.0, 1.85, -0.85)],
    'BrasToilettes': [(-0.85, 0.76, -0.2), (-1.6, 0.8, -0.55), (-2.3, 0.78, -0.82), (-2.45, 0.9, -0.85), (-2.45, 1.25, -0.85), (-2.45, 1.55, -0.85),
                      (-2.42, 1.85, -0.78), (-2.3, 1.95, -0.6), (-2.15, 1.72, -0.5)],
}
HAND_KW = {'BrasGrille': dict(curl=0.3, spread=0.65), 'BrasFenetre': dict(curl=0.45, spread=0.5), 'BrasToilettes': dict(curl=0.85, spread=0.3)}

ARM_LEN = {'BrasGrille': 3.2, 'BrasFenetre': 6.3, 'BrasToilettes': 4.3}

def bras_scene(name, seed, log=print, droit=False):
    """droit=True : bras modélisé droit le long de +X (racine en x = -0.2, bout des doigts vers x = longueur), dos vers +Z,
    pour la visionneuse qui le plie le long de son chemin"""
    path = B.Path([(-0.2, 0, 0), (ARM_LEN[name] - 0.1, 0, 0)]) if droit else B.Path([W(*p) for p in PATHS[name]])
    parts, NL = B.arm_chain(path, r_start=0.05, r_end=0.043, seed=seed, up=(0, 0, 1), hand_scale=1.45, hand_kw=HAND_KW[name])
    for p in parts: B.bake_mods(p)
    ob = B.remesh(B.join(parts, name), voxel=0.0018, smooth=4)
    B.displace(ob, 'CLOUDS', 0.09, 0.006, 2, name=f'bosses_{name}'); B.displace(ob, 'CLOUDS', 0.018, 0.0015, 1, name=f'peau_{name}')
    B.displace(ob, 'VORONOI', 0.0055, 0.0007, name=f'rides_{name}')
    B.bake_mods(ob); B.shade_smooth(ob)
    nails = B.nails_from(NL, f'Ongles{name}')
    log(f'{name} : {len(ob.data.polygons)} faces, chemin {path.L:.2f} m')
    return ob, nails

# ================================================================ décor
def wagon(M, log=print):
    X0, X1 = -3.2, 3.2; obs = {}
    # plancher troué : grille d'aération et passage du tuyau des toilettes
    fl = box('Plancher', (0, 0, (FLOOR_LO + FLOOR_HI)/2), (X1, WALL_Y, (FLOOR_HI - FLOOR_LO)/2), M['lino'])
    c1 = box('c1', (VENT[0], VENT[1], 1.1), (VENT[2], VENT[3], 0.2), None)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.075, radius2=0.075, depth=0.4)
    c2 = mesh_obj('c2', bm); c2.location = (WC.x, WC.y, 1.1)
    cut(fl, [c1, c2])
    # longeron arrière
    box('Longeron', (0, 1.32, 0.97), (X1, 0.05, 0.08), M['rouille'], bevel=0.008)
    # grille : lames, deux arrachées et tordues vers le haut
    for k in range(9):
        y = VENT[1] - VENT[3] + 0.012 + k*(2*VENT[3] - 0.024)/8
        if k in (4, 5):
            sk = B.Skel(); a = sk.v((VENT[0] - VENT[2], y, FLOOR_HI + 0.004), 0.0055)
            sk.chain(a, [(VENT[0] - 0.16, y + 0.012*(k - 4.5), FLOOR_HI + 0.03), (VENT[0] - 0.09, y + 0.03*(k - 4.5), FLOOR_HI + 0.1), (VENT[0] - 0.06, y + 0.05*(k - 4.5), FLOOR_HI + 0.17)], [0.0055]*3)
            o = B.skin_object(f'barre{k}', sk, sub=2); o.data.materials.append(M['acier']); continue
        box('Lame', (VENT[0], y, FLOOR_HI + 0.004), (VENT[2], 0.0075, 0.004), M['acier'])
    for (c, h) in (((VENT[0], VENT[1] - VENT[3] - 0.012, FLOOR_HI + 0.005), (VENT[2] + 0.024, 0.012, 0.006)), ((VENT[0], VENT[1] + VENT[3] + 0.012, FLOOR_HI + 0.005), (VENT[2] + 0.024, 0.012, 0.006)),
                   ((VENT[0] - VENT[2] - 0.012, VENT[1], FLOOR_HI + 0.005), (0.012, VENT[3], 0.006)), ((VENT[0] + VENT[2] + 0.012, VENT[1], FLOOR_HI + 0.005), (0.012, VENT[3], 0.006))):
        box('Cadre', c, h, M['acier'], bevel=0.002)
    # paroi intérieure (soubassement vert, haut crème) avec la fenêtre ; caisse extérieure verte
    def holed(name, y, t, zc, zh, mat):
        o = box(name, (0, y, zc), (X1, t, zh), mat)
        h = box('h', (WIN[0], y, (WIN[1] + WIN[2])/2), (WIN[3], t + 0.05, (WIN[2] - WIN[1])/2), None); cut(o, [h]); return o
    holed('Paroi', WALL_Y + 0.03, 0.03, 2.25, 1.1, M['paroi'])
    holed('Caisse', WALL_Y + 0.075, 0.015, 2.15, 1.2, M['caisse'])
    # cadre alu de la fenêtre, vitre baissée, traverse
    for (c, h) in (((WIN[0], WALL_Y + 0.04, WIN[1] - 0.02), (WIN[3] + 0.04, 0.06, 0.02)), ((WIN[0], WALL_Y + 0.04, WIN[2] + 0.02), (WIN[3] + 0.04, 0.06, 0.02)),
                   ((WIN[0] - WIN[3] - 0.02, WALL_Y + 0.04, (WIN[1] + WIN[2])/2), (0.02, 0.06, (WIN[2] - WIN[1])/2 + 0.04)), ((WIN[0] + WIN[3] + 0.02, WALL_Y + 0.04, (WIN[1] + WIN[2])/2), (0.02, 0.06, (WIN[2] - WIN[1])/2 + 0.04)),
                   ((WIN[0], WALL_Y + 0.035, WIN_GLASS_TOP), (WIN[3], 0.014, 0.018))):
        box('Alu', c, h, M['alu'], bevel=0.004)
    box('Vitre', (WIN[0], WALL_Y + 0.035, (WIN[1] + WIN_GLASS_TOP)/2), (WIN[3], 0.004, (WIN_GLASS_TOP - WIN[1])/2), M['verre'])
    # banquettes face à face
    for xc, sg in ((-0.25, 1), (1.25, -1)):
        for zq in (-0.24, 0.24):
            box('Coussin', (xc, 0.95 + zq, 1.6), (0.24, 0.22, 0.06), M['moquette'], bevel=0.035, seg=4)
            box('Dossier', (xc - sg*0.27, 0.95 + zq, 2.0), (0.06, 0.22, 0.36), M['moquette'], bevel=0.035, seg=4)
        box('Appuitete', (xc - sg*0.26, 0.95, 2.4), (0.075, 0.47, 0.06), M['moquette'], bevel=0.05, seg=4)
        box('Assise', (xc, 0.95, 1.52), (0.26, 0.48, 0.02), M['acier'], bevel=0.005)
        for yq in (0.6, 1.3):
            box('Pied', (xc + 0.12, yq, 1.33), (0.018, 0.018, 0.19), M['acier'], bevel=0.006)
        box('Poignee', (xc - sg*0.27, 0.95, 2.47), (0.014, 0.36, 0.014), M['acier'], bevel=0.007, seg=3)
    # toilettes : cloison avec porte, cuvette inox, tuyau
    cl = box('Cloison', (WC_WALL_X, 0.5, 2.25), (0.03, 0.95, 1.1), M['paroi'])
    door = box('d', (WC_WALL_X, -0.05, 2.15), (0.1, 0.38, 1.0), None); cut(cl, [door])
    bm = bmesh.new()
    prof = [(0.0, 0.06), (0.11, 0.06), (0.15, 0.2), (0.2, 0.36), (0.215, 0.43), (0.2, 0.445), (0.13, 0.42), (0.06, 0.12), (0.0, 0.1)]
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    for a, b in zip(vs[:-1], vs[1:]): bm.edges.new((a, b))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], angle=2*math.pi, steps=40, axis=(0, 0, 1), cent=(0, 0, 0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bowl = mesh_obj('Cuvette', bm, M['inox']); bowl.location = WC; bowl.scale = (1.0, 1.22, 1.0)
    for p in bowl.data.polygons: p.use_smooth = True
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.07, radius2=0.07, depth=0.5)
    pipe = mesh_obj('Tuyau', bm, M['rouille']); pipe.location = (WC.x, WC.y, 0.95)
    # plafond, néon, parois d'extrémité
    box('Plafond', (0, 0, 3.37), (X1, WALL_Y + 0.05, 0.03), M['plafond'])
    box('NeonBoitier', (0.35, 0.55, 3.31), (0.65, 0.05, 0.025), M['alu'], bevel=0.008)
    box('NeonTube', (0.35, 0.55, 3.28), (0.6, 0.016, 0.012), M['neon'])
    for x in (X0 - 0.035, X1 + 0.035):
        box('Bout', (x, 0, 2.25), (0.035, WALL_Y + 0.05, 1.12), M['paroi'])
    log('wagon')

def voie(M, log=print):
    rng = random.Random(5)
    # traverses en bois
    for x in [-3.3 + 0.6*k for k in range(12)]:
        box('Traverse', (x + rng.uniform(-0.03, 0.03), 0, 0.07), (0.13, 1.3, 0.08), M['bois'], bevel=0.012)
    # rails (profil en I)
    for sg in (-1, 1):
        y = sg*RAIL_Y
        box('RailTete', (0, y, RAIL_TOP - 0.025), (3.6, 0.036, 0.025), M['rail'], bevel=0.006)
        box('RailAme', (0, y, 0.22), (3.6, 0.009, 0.07), M['rouille'])
        box('RailPatin', (0, y, 0.158), (3.6, 0.075, 0.008), M['rouille'], bevel=0.003)
    # lit de ballast : sol + des milliers de cailloux instanciés
    bpy.ops.mesh.primitive_plane_add(size=1); g = bpy.context.object; g.name = 'Ballast'; g.scale = (7.4, 4.0, 1); g.location = (0, 0, 0.0)
    bpy.ops.object.transform_apply(scale=True)
    for c in g.users_collection: c.objects.unlink(g)
    B.coll().objects.link(g); g.data.materials.append(M['gravier'])
    rc = bpy.data.collections.new('Cailloux'); bpy.context.scene.collection.children.link(rc)
    for k in range(6):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x*rng.uniform(0.8, 1.2), v.co.y*rng.uniform(0.7, 1.0), v.co.z*rng.uniform(0.5, 0.8)))*(1 + 0.25*(rng.random() - 0.5))
        o = mesh_obj(f'caillou{k}', bm, M['caillou'])
        for c in o.users_collection: c.objects.unlink(o)
        rc.objects.link(o)
        for p in o.data.polygons: p.use_smooth = False
    rc.hide_render = False
    lc = bpy.context.view_layer.layer_collection.children.get('Cailloux')
    if lc: lc.exclude = True
    ps = g.modifiers.new('cailloux', 'PARTICLE_SYSTEM'); st = ps.particle_system.settings
    st.type = 'EMITTER'; st.count = 26000; st.frame_start = 1; st.frame_end = 1; st.lifetime = 100000; st.physics_type = 'NO'
    st.render_type = 'COLLECTION'; st.instance_collection = rc; st.use_collection_pick_random = True
    st.particle_size = 0.028; st.size_random = 0.65; st.emit_from = 'FACE'; st.distribution = 'RAND'; st.use_emit_random = True
    st.use_rotations = True; st.rotation_mode = 'NOR'; st.phase_factor_random = 2.0; st.rotation_factor_random = 0.35
    st.normal_factor = 0.0; st.show_unborn = True; st.use_dead = True
    log('voie')

def materiaux():
    S = B.mat_simple; M = {}
    M['lino'] = S('Lino', (0.045, 0.05, 0.052), 0.5, noise_scale=5, noise_col=(0.015, 0.015, 0.014), bump=0.04)
    M['acier'] = S('Acier', (0.42, 0.43, 0.44), 0.35, 0.9, noise_scale=25, noise_col=(0.1, 0.08, 0.06), bump=0.1)
    M['alu'] = S('Alu', (0.6, 0.61, 0.62), 0.3, 1.0, noise_scale=20, noise_col=(0.3, 0.3, 0.3))
    M['inox'] = S('Inox', (0.7, 0.7, 0.7), 0.22, 1.0, noise_scale=12, noise_col=(0.25, 0.22, 0.2), bump=0.03)
    M['rouille'] = S('Rouille', (0.16, 0.06, 0.025), 0.8, 0.2, noise_scale=14, noise_col=(0.04, 0.025, 0.018), bump=0.3)
    M['rail'] = S('Rail', (0.5, 0.5, 0.52), 0.28, 1.0, noise_scale=30, noise_col=(0.15, 0.08, 0.04), bump=0.05)
    M['bois'] = S('Bois', (0.06, 0.042, 0.03), 0.85, noise_scale=8, noise_col=(0.02, 0.015, 0.01), bump=0.4)
    M['caillou'] = S('Caillou', (0.075, 0.072, 0.068), 0.8, noise_scale=40, noise_col=(0.07, 0.068, 0.065), bump=0.5)
    M['gravier'] = S('Gravier', (0.05, 0.045, 0.04), 0.9, noise_scale=12, noise_col=(0.015, 0.013, 0.012))
    M['moquette'] = S('Moquette', (0.11, 0.045, 0.04), 0.95, noise_scale=60, noise_col=(0.04, 0.02, 0.018), bump=0.08)
    M['plafond'] = S('Plafond', (0.35, 0.36, 0.34), 0.7, noise_scale=4, noise_col=(0.15, 0.15, 0.13))
    M['caisse'] = _peinture('Caisse', (0.06, 0.12, 0.1), (0.12, 0.05, 0.02))
    M['paroi'] = _paroi()
    v = bpy.data.materials.new('Verre'); v.use_nodes = True; b = v.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.6, 0.65, 0.65, 1); b.inputs['Roughness'].default_value = 0.08; b.inputs['Transmission Weight'].default_value = 1.0
    M['verre'] = v
    n = bpy.data.materials.new('Neon'); n.use_nodes = True; b = n.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (0.75, 0.95, 0.88, 1); b.inputs['Emission Strength'].default_value = 25.0
    M['neon'] = n
    M['chair'] = B.mat_chair('Chair', grime=0.8); M['ongle'] = B.mat_ongle()
    g = bpy.data.materials.new('Gorge'); g.use_nodes = True; b = g.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.022, 0.003, 0.003, 1); b.inputs['Roughness'].default_value = 0.4; b.inputs['Subsurface Weight'].default_value = 0.2
    M['gorge'] = mat_gencive(); M['dents'] = mat_dents()
    return M

def _peinture(name, col, rust):
    m = B.mat_simple(name, col, 0.45); nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 1, 0.12)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 6; n.inputs['Detail'].default_value = 8; nt.links.new(mp.outputs[0], n.inputs['Vector'])
    r = B.ramp(nt, (0, 0), [(0.55, (*col, 1)), (0.72, (*rust, 1))]); nt.links.new(n.outputs['Fac'], r.inputs[0]); nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
    return m

def _paroi():
    m = bpy.data.materials.new('Paroi'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
    # objet centré à z = 2.25 : le soubassement s'arrête à z monde ~1.9
    r = B.ramp(nt, (0, 0), [(0.0, (0.035, 0.055, 0.045, 1)), (0.338, (0.035, 0.055, 0.045, 1)), (0.34, (0.45, 0.44, 0.38, 1)), (0.355, (0.45, 0.44, 0.38, 1)), (0.357, (0.3, 0.31, 0.27, 1))])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 1.15; mr.inputs['From Max'].default_value = 3.35
    nt.links.new(sep.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs[0], r.inputs[0])
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 1, 0.2); nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 5; n.inputs['Detail'].default_value = 8; nt.links.new(mp.outputs[0], n.inputs['Vector'])
    rr = B.ramp(nt, (0, -200), [(0.5, (1, 1, 1, 1)), (0.75, (0.35, 0.32, 0.25, 1))]); nt.links.new(n.outputs['Fac'], rr.inputs[0])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    A, Bs, R = B._mix_sockets(mx); nt.links.new(r.outputs['Color'], A); nt.links.new(rr.outputs['Color'], Bs); nt.links.new(R, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55
    return m
