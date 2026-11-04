"""VITRELLE — poulpe de verre géant (inspiré de Vitreledonella richardi), échappé de son bassin dans la base sous-marine.
Corps presque invisible : on voit les yeux tubulaires et leur reflet, les organes (glande digestive, trois cœurs, branchies,
cerveau, nerfs optiques), les ventouses laiteuses, et des photophores le long des bras.
Construit dans un repère « sol » local (Z en haut, le poulpe posé à plat) ; pose 'plafond' : enroulé sur le plafond
cylindrique d'une coursive par une simple transformation des sommets."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
import ballast_bl as B
from abysse import mesh_obj, xf_verts, tube_bm, ell_bm, box_bm, torus_bm

UP = Vector((0, 0, 1))
CROWN = Vector((0.05, 0.0, 0.13))
EYE_BASE = {s: Vector((0.06, s*0.17, 0.42)) for s in (-1, 1)}
EYE_AX = {s: Vector((0.3, s*0.9, 0.25)).normalized() for s in (-1, 1)}
EYE_R = 0.07                                    # rayon du globe oculaire
EYE_C = {s: EYE_BASE[s] + EYE_AX[s]*0.05 for s in (-1, 1)}

def eye_frame(s):
    """repère de l'œil : x = horizontal, y = haut, z = axe du regard (la fente de la pupille reste horizontale)"""
    z = EYE_AX[s]; x = UP.cross(z).normalized(); y = z.cross(x)
    return Matrix((x, y, z)).transposed()
MANTLE_C, MANTLE_AX = Vector((-0.3, 0, 0.62)), Vector((-1, 0, 0.8)).normalized()

# ================================================================ bras
def arm_curve(k, rng, raised=False, L=None):
    """bras k : tortue 3D (lacet + tangage), au sol par défaut, ou dressé et recourbé en crochet"""
    phi = k*math.pi/4 + 0.2 + rng.uniform(-0.12, 0.12)
    L = L or rng.uniform(2.4, 3.1); ds = 0.022; n = int(L/ds)
    th = phi; al = -0.55; pos = CROWN + Vector((math.cos(phi), math.sin(phi), 0))*0.15
    bend = rng.uniform(-0.35, 0.35); amp = rng.uniform(0.6, 1.4); om = rng.uniform(2.5, 4.5); ph = rng.uniform(0, 6.28)
    curl_r = rng.uniform(0.6, 1.0); tip0 = L - rng.uniform(0.45, 0.7)
    P = [pos.copy()]; R = []
    for i in range(n):
        s = i*ds; r = rad_at(s, L)
        if s < tip0: kap = bend + amp*math.sin(s*om + ph)*min(1, s/0.6)
        else: kap = (s - tip0)/(L - tip0)*14*curl_r*(1 if bend >= 0 else -1)     # bout qui s'enroule
        if raised:
            alt = 1.05*min(1, max(0, (s - 0.4)/1.1))
            al = alt if s < tip0 else alt + (s - tip0)/(L - tip0)*3.2              # crochet par-dessus
            th += kap*ds*0.5
        else:
            th += kap*ds
            target = r + 0.006*math.sin(s*7 + ph)
            al = max(-0.6, min(0.5, math.atan2(target - pos.z, 0.12)))
        pos = pos + Vector((math.cos(al)*math.cos(th), math.cos(al)*math.sin(th), math.sin(al)))*ds
        P.append(pos.copy())
    return P, L

def rad_at(s, L):
    return 0.072*(1 - min(s/L, 1))**0.85 + 0.0045 + 0.012*math.exp(-(s/0.18)**2)

def rmf(P, n0=UP):
    """repères à rotation minimale le long d'une courbe ; N = dos"""
    T = [(P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized() for i in range(len(P))]
    N = [(n0 - T[0]*n0.dot(T[0])).normalized()]
    for i in range(len(P) - 1):
        v1 = P[i + 1] - P[i]; c1 = v1.dot(v1) or 1e-9
        rL = N[i] - v1*(2/c1*v1.dot(N[i])); tL = T[i] - v1*(2/c1*v1.dot(T[i]))
        v2 = T[i + 1] - tL; c2 = v2.dot(v2) or 1e-9
        N.append((rL - v2*(2/c2*v2.dot(rL))).normalized())
    return T, N

def smooth_body(ob, iters=24, r0=0.42, r1=0.62):
    """lissage fort réservé au corps (tête, manteau, base des bras) : efface les marches du remaillage voxel sans amincir le bout des bras"""
    a = CROWN + UP*0.2; b = MANTLE_C + MANTLE_AX*0.5; ab = b - a
    vg = ob.vertex_groups.new(name='corps')
    for v in ob.data.vertices:
        t = max(0.0, min(1.0, (v.co - a).dot(ab)/ab.dot(ab))); d = (v.co - (a + ab*t)).length
        w = 1.0 if d < r0 else max(0.0, 1 - (d - r0)/(r1 - r0))
        if w > 0: vg.add([v.index], w*w*(3 - 2*w), 'REPLACE')
    m = ob.modifiers.new('lisse', 'LAPLACIANSMOOTH'); m.iterations = iters; m.lambda_factor = 0.5; m.use_volume_preserve = True; m.vertex_group = 'corps'
    B.bake_mods(ob)

def pigment(ob):
    """attribut « pigment » : masque de chromatophores sombres autour des yeux, plus dense sur l'arcade"""
    at = ob.data.attributes.new('pigment', 'FLOAT', 'POINT')
    ss = lambda e0, e1, x: (lambda t: t*t*(3 - 2*t))(max(0.0, min(1.0, (x - e0)/(e1 - e0))))
    Fi = {sg: eye_frame(sg).transposed() for sg in (-1, 1)}
    for v in ob.data.vertices:
        w = 0.0
        for sg in (-1, 1):
            q = Fi[sg] @ ((v.co - EYE_C[sg])/EYE_R); d = q.length
            if d < 2.6: w = max(w, (1 - ss(1.2, 2.4, d))*(0.5 + 0.5*ss(-0.3, 0.8, q.y)))
        at.data[v.index].value = w

def spindle_bm(bm, c, half_len, rad, R, seg=48):
    """fuseau : section (1-u²)^0.85, bouts effilés"""
    o = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg//2, radius=1.0)
    for v in o['verts']:
        x, y, z = v.co; f = (max(0.0, 1 - x*x))**0.85/max(1e-6, (max(0.0, 1 - x*x))**0.5) if abs(x) < 0.999 else 0.0
        v.co = R @ Vector((x*half_len, y*rad*f, z*rad*f)) + c

def lid_bm(bm, sg, k=0.55, cosa=0.42, seg=72, rings=18):
    """calotte sphérique autour de l'œil sg, centrée vers le haut et un peu vers l'avant ; son bord descend vers l'avant"""
    F = eye_frame(sg); n = (F @ Vector((-sg*k, 1.0, 0.45))).normalized()
    t1 = n.orthogonal().normalized(); t2 = n.cross(t1); Rr = EYE_R*1.15; al = math.acos(cosa)
    top = bm.verts.new(EYE_C[sg] + n*Rr); prev = None
    for i in range(1, rings + 1):
        th = al*i/rings; ring = []
        for j in range(seg):
            ph = j/seg*2*math.pi; d = n*math.cos(th) + (t1*math.cos(ph) + t2*math.sin(ph))*math.sin(th)
            ring.append(bm.verts.new(EYE_C[sg] + d*Rr))
        if prev is None:
            for j in range(seg): bm.faces.new((top, ring[j], ring[(j + 1) % seg]))
        else:
            for j in range(seg): bm.faces.new((prev[j], ring[j], ring[(j + 1) % seg], prev[(j + 1) % seg]))
        prev = ring

def card_obj(name, c, h, R):
    """carte plate (demi-dimensions h) avec UV : recto = image entière, verso = image en miroir, tranches sur un coin"""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    V = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1): V[sx, sy, sz] = bm.verts.new(R @ Vector((sx*h[0], sy*h[1], sz*h[2])) + c)
    def face(keys, uvs):
        f = bm.faces.new([V[k] for k in keys])
        for l, u in zip(f.loops, uvs): l[uv].uv = u
    face([(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    face([(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)], [(1, 1), (0, 1), (0, 0), (1, 0)])
    z = (0.01, 0.01)
    for keys in ([(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)],
                 [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)], [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)]):
        face(keys, [z]*4)
    return mesh_obj(name, bm)

# ================================================================ construction
def build(log=print, seed=21, raised=(1, 6)):
    rng = random.Random(seed)
    skin = []                                  # objets fusionnés en une seule peau
    arms = []
    for k in range(8):
        P, L = arm_curve(k, rng, raised=(k in raised))
        arms.append((P, L))
        sk = B.Skel(); prev = None
        for i, p in enumerate(P[::2]):
            s = i*2*0.022; ii = sk.v(p, rad_at(s, L))
            if prev is not None: sk.e(prev, ii)
            prev = ii
        skin.append(B.skin_object(f'bras{k}', sk, sub=2))
    # palmure entre les bras (bords festonnés)
    bm = bmesh.new()
    for k in range(8):
        A, Bc = arms[k][0], arms[(k + 1) % 8][0]; nu, nv = 50, 30; grid = []
        for iu in range(nu + 1):
            row = []
            for iv in range(nv + 1):
                v = iv/nv; smax = 0.55*(1 - 0.55*math.sin(math.pi*v)); s = smax*iu/nu; j = int(s/0.022); f = s/0.022 - j
                pa = A[j].lerp(A[j + 1], f); pb = Bc[j].lerp(Bc[j + 1], f)
                p = pa.lerp(pb, v) + UP*(0.025*math.sin(math.pi*v))
                row.append(bm.verts.new(p))
            grid.append(row)
        for iu in range(nu):
            for iv in range(nv): bm.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
    web = mesh_obj('palmure', bm); so = web.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.014; so.offset = 0; B.bake_mods(web); skin.append(web)
    # corps : couronne, tête, cou, manteau, yeux tubulaires, entonnoir
    bm = bmesh.new()
    HD = 192                                   # primitives très fines : sinon leurs facettes survivent au remaillage et font miroir dans le verre
    ell_bm(bm, CROWN, (0.21, 0.21, 0.1), Matrix.Identity(3), HD)
    ell_bm(bm, Vector((0.02, 0, 0.34)), (0.25, 0.3, 0.22), Matrix.Identity(3), HD)
    ell_bm(bm, Vector((-0.12, 0, 0.45)), (0.25, 0.28, 0.24), Matrix.Identity(3), HD)
    ell_bm(bm, MANTLE_C, (0.56, 0.37, 0.34), B.frame(MANTLE_AX, UP).to_3x3(), HD)
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]
        tube_bm(bm, b0 - e*0.04, b0 + e*0.075, 0.064, 128)                       # orbite : seul l'iris dépasse de la peau
        torus_bm(bm, b0 + e*0.093, e, 0.056, 0.012, 128, 32)                     # paupière serrée sur le bord de l'iris
        F = eye_frame(sg); xl, yl, zl = F.col[0], F.col[1], F.col[2]
        ell_bm(bm, EYE_C[sg] + yl*EYE_R*0.78 + zl*EYE_R*0.25, (EYE_R*1.3, EYE_R*0.4, EYE_R*0.7), F @ Matrix.Rotation(sg*0.35, 3, 'Z'), 128)   # arcade qui retombe vers l'avant
    tube_bm(bm, Vector((-0.04, -0.24, 0.24)), Vector((0.06, -0.33, 0.17)), 0.04, 96)
    skin.append(mesh_obj('corps', bm))
    for o in skin: B.bake_mods(o)
    body = B.remesh(B.join(skin, 'Vitrelle'), voxel=0.0034, smooth=6)
    smooth_body(body, iters=24)
    B.shade_smooth(body); pigment(body)
    log(f'peau : {len(body.data.polygons)} faces')
    parts = dict(peau=body)
    # ventouses : deux rangées alternées sur la face orale
    bm = bmesh.new(); bmc = bmesh.new()
    for P, L in arms:
        T, N = rmf(P); s = 0.12; side = 1
        while s < L - 0.12:
            i = int(s/0.022); r = rad_at(s, L); rs = 0.5*r
            Sd = T[i].cross(N[i]); oral = -N[i]
            c = P[i] + oral*r*0.82 + Sd*side*r*0.42
            Mx = Matrix.Translation(c) @ oral.to_track_quat('Z', 'Y').to_matrix().to_4x4()
            o = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=rs*0.85, radius2=rs, depth=rs*0.7)
            xf_verts(o['verts'], Mx @ Matrix.Translation((0, 0, rs*0.1)))
            o = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=rs, radius2=rs*0.55, depth=rs*0.25)   # rebord + cupule
            xf_verts(o['verts'], Mx @ Matrix.Translation((0, 0, rs*0.5)) @ Matrix.Rotation(math.pi, 4, 'X'))
            ell_bm(bmc, c + oral*rs*0.35, (rs*0.18, rs*0.18, rs*0.05), oral.to_track_quat('Z', 'Y').to_matrix(), 8)   # pore central
            side = -side; s += max(rs*1.25, 0.012)
    parts['ventouses'] = mesh_obj('Ventouses', bm, smooth=True); parts['pores'] = mesh_obj('Pores', bmc, smooth=True)
    log(f'ventouses : {len(parts["ventouses"].data.polygons)} faces')
    # yeux : globe saillant (sclère argentée sombre, iris doré strié, pupille en fente qui luit), cornée bombée par-dessus.
    # l'attribut « oeil » garde les coordonnées locales de chaque globe (sphère unité, z = regard, x = horizontal) pour le matériau
    bme, bmk = bmesh.new(), bmesh.new()
    for sg in (-1, 1):
        ell_bm(bme, EYE_C[sg], (EYE_R,)*3, eye_frame(sg), 96)
        ell_bm(bmk, EYE_C[sg] + EYE_AX[sg]*0.016, (EYE_R*0.9, EYE_R*0.9, EYE_R*0.86), eye_frame(sg), 64)
    eye = mesh_obj('Yeux', bme, smooth=True)
    at = eye.data.attributes.new('oeil', 'FLOAT_VECTOR', 'POINT')
    for v in eye.data.vertices:
        sg = -1 if v.co.y < 0 else 1
        at.data[v.index].vector = eye_frame(sg).transposed() @ ((v.co - EYE_C[sg])/EYE_R)
    parts['yeux'] = eye; parts['cornees'] = mesh_obj('Cornees', bmk, smooth=True)
    # organes visibles par transparence
    bm_g, bm_h, bm_br = bmesh.new(), bmesh.new(), bmesh.new()
    Rm = B.frame(MANTLE_AX, UP).to_3x3(); rg = random.Random(5)
    spindle_bm(bm_g, MANTLE_C + MANTLE_AX*0.04 - UP*0.03, 0.25, 0.07, Rm)                          # glande digestive (fuseau argenté)
    ell_bm(bm_h, Vector((-0.17, 0, 0.5)), (0.034, 0.03, 0.03))                                  # cœur systémique
    sk = B.Skel(); sv = B.Skel(); so_ = B.Skel()
    for sg in (-1, 1):
        ell_bm(bm_h, Vector((-0.22, sg*0.1, 0.47)), (0.022, 0.022, 0.022))                        # cœurs branchiaux
        # branchie bipennée : un rachis, deux rangées de lamelles fines qui raccourcissent vers la pointe
        a, b_ = Vector((-0.12, sg*0.16, 0.45)), Vector((-0.45, sg*0.21, 0.64))
        G = B.catmull([a, a.lerp(b_, 0.5) + Vector((0, sg*0.035, -0.03)), b_], 40)
        sv.chain(sv.v(G[0], 0.0035), G[1:], [0.0035 - 0.002*i/len(G) for i in range(1, len(G))])   # vaisseau branchial (rouge)
        for j in range(96):
            t = j/95; i = min(int(t*(len(G) - 1)), len(G) - 2); c = G[i]; ax = (G[i + 1] - G[i]).normalized()
            sd = ax.cross(UP).normalized(); nn = sd.cross(ax)
            ln = 0.032*(1 - 0.7*t)*(0.65 + 0.55*rg.random())*(1.0 if j % 2 else 0.78)
            for side in (-1, 1):
                ang = 0.45 + rg.uniform(-0.18, 0.18)
                d = (sd*side*math.cos(ang) - ax*math.sin(ang) + nn*rg.uniform(-0.15, 0.15)).normalized()
                ell_bm(bm_br, c + d*ln*0.55 + nn*0.002*side, (ln*0.55, 0.0009, ln*0.38), B.frame(d, nn).to_3x3() @ Matrix.Rotation(rg.uniform(-0.2, 0.2), 3, 'X'), 12)
        # nerf optique : de l'arrière de l'œil au lobe du cerveau, en courbe
        e = EYE_AX[sg]; p0 = EYE_C[sg] - e*EYE_R*0.85; p2 = Vector((0.0, sg*0.04, 0.43))
        P = B.catmull([p0, (p0 + p2)/2 + UP*0.025, p2], 8)
        sk.chain(sk.v(P[0], 0.0075), P[1:], [0.0075 - 0.0025*i/len(P) for i in range(1, len(P))])
        ell_bm(bm_br, Vector((0.0, sg*0.035, 0.43)), (0.045, 0.04, 0.036), Matrix.Rotation(sg*0.2, 3, 'Z'), 24)   # lobes du cerveau
    P = B.catmull([CROWN + Vector((0.01, 0, -0.03)), Vector((0.02, 0, 0.3)), Vector((-0.04, 0, 0.44)), Vector((-0.14, 0, 0.5)), MANTLE_C + MANTLE_AX*0.2 - UP*0.03], 10)
    so_.chain(so_.v(P[0], 0.0035), P[1:], [0.0035]*(len(P) - 1))                                  # œsophage (fin, translucide)
    nerfs = B.skin_object('Nerfs', sk, sub=1); B.bake_mods(nerfs); B.shade_smooth(nerfs)
    parts['glande'] = mesh_obj('Glande', bm_g, smooth=True); parts['coeurs'] = mesh_obj('Coeurs', bm_h, smooth=True)
    parts['branchies'] = mesh_obj('Branchies', bm_br, smooth=True); parts['nerfs'] = nerfs
    for key, sk_, nm in (('vaisseaux', sv, 'Vaisseaux'), ('oesophage', so_, 'Oesophage')):
        o = B.skin_object(nm, sk_, sub=1); B.bake_mods(o); B.shade_smooth(o); parts[key] = o
    # ce qu'il a avalé : le badge d'accès du Dr Aldane, avec son cordon, coincé contre la paroi du manteau (côté -Y)
    bx = Vector((1, 0, 0.25)).normalized(); bz = Vector((0, -1, 0)); Rb = Matrix((bx, bz.cross(bx), bz)).transposed()   # face imprimée vers -Y
    Rb = Rb @ Matrix.Rotation(-0.35, 3, 'Z') @ Matrix.Rotation(0.3, 3, 'X')
    bc = MANTLE_C + MANTLE_AX*(-0.1) + Vector((0, -0.17, -0.02))
    parts['badge'] = card_obj('Badge', bc, (0.0428, 0.027, 0.0012), Rb)
    pts = [bc + Rb @ Vector((0.0, 0.03 + 0.24*j/47, 0.0)) + Rb @ Vector((0.035*math.sin(j/47*4.0), 0, 0.02*math.sin(j/47*6.5))) for j in range(48)]
    bm = bmesh.new(); prev = None; nrm = Rb.col[2].copy()
    for j, p in enumerate(pts):
        t = (pts[min(j + 1, 47)] - pts[max(j - 1, 0)]).normalized(); w = t.cross(nrm).normalized()*0.0065
        tw = Matrix.Rotation(0.6*math.sin(j/47*5), 3, t); w = tw @ w; n2 = t.cross(w).normalized()*0.0007
        ring = [bm.verts.new(p + w + n2), bm.verts.new(p - w + n2), bm.verts.new(p - w - n2), bm.verts.new(p + w - n2)]
        if prev:
            for k in range(4): bm.faces.new((prev[k], prev[(k + 1) % 4], ring[(k + 1) % 4], ring[k]))
        prev = ring
    parts['cordon'] = mesh_obj('Cordon', bm)
    # bec
    bm = bmesh.new()
    for sg in (-1, 1):
        o = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.035, radius2=0.004, depth=0.07)
        xf_verts(o['verts'], Matrix.Translation(CROWN + Vector((0.02*sg, 0, -0.07))) @ Vector((0.3*sg, 0, -1)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    parts['bec'] = mesh_obj('Bec', bm, smooth=True)
    # photophores : rangée dorsale le long des bras, couronne autour des yeux, deux lignes sur le manteau
    bm_v, bm_r = bmesh.new(), bmesh.new()
    for ai, (P, L) in enumerate(arms):
        T, N = rmf(P); s = 0.3; j = 0
        while s < L - 0.15:
            i = int(s/0.022); r = rad_at(s, L)
            sz = (0.003 + r*0.08)*rng.uniform(0.6, 1.5)
            ell_bm(bm_r if rng.random() < 0.12 else bm_v, P[i] + N[i]*r*0.86, (sz,)*3, Matrix.Identity(3), 24)
            s += rng.uniform(0.14, 0.34); j += 1
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]; t1 = e.cross(UP).normalized(); t2 = e.cross(t1)
        for k in range(10):
            a = k/10*2*math.pi + 0.3; ell_bm(bm_v, b0 + e*0.05 + (t1*math.cos(a) + t2*math.sin(a))*0.088, (0.0055,)*3, Matrix.Identity(3), 24)
        for j in range(9):
            t = j/8; c = MANTLE_C + MANTLE_AX*(0.45 - 0.9*t) + Vector((0, sg*0.2*(1 - 0.5*abs(t - 0.5)), 0.24*(1 - (2*t - 1)**2) + 0.05))
            ell_bm(bm_v, c, (0.009,)*3, Matrix.Identity(3), 24)
    parts['photo_v'] = mesh_obj('PhotophoresV', bm_v, smooth=True); parts['photo_r'] = mesh_obj('PhotophoresR', bm_r, smooth=True)
    return parts

# ================================================================ matériaux
def mats(glow=6.0):
    M = {}
    import os
    E = os.environ.get
    M['peau'] = _verre_vivant('PeauVerre', density=float(E('ABSORB', '1.2')), milk=float(E('LAIT', '0.12')), spots=E('TACHES', '1') == '1', pig=E('TACHES', '1') == '1', ior=1.07)
    M['ventouse'] = _verre_vivant('Ventouse', density=6.0, milk=0.55, spots=False)
    m = bpy.data.materials.new('Cornee'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (1, 1, 1, 1); b.inputs['Roughness'].default_value = 0.0; b.inputs['Transmission Weight'].default_value = 1; b.inputs['IOR'].default_value = 1.376
    m.node_tree.links.new(_ombre_claire(m.node_tree, b.outputs[0]), m.node_tree.nodes['Material Output'].inputs['Surface'])
    M['cornee'] = m
    M['oeil'] = _oeil(glow)
    M['glande'] = _argent()
    M['coeur'] = _organe('Coeur', (0.35, 0.03, 0.04), 1.2, (1.0, 0.1, 0.1))
    M['branchie'] = _organe('Branchie', (0.9, 0.66, 0.62), 0.0, trans=0.6)
    M['nerf'] = _organe('Nerf', (0.85, 0.82, 0.76), 0.0, trans=0.55)
    M['pore'] = _organe('Pore', (0.1, 0.035, 0.025), 0.0)
    M['oesophage'] = _organe('Oesophage', (0.9, 0.74, 0.7), 0.0, trans=0.8)
    M['badge'] = _badge()
    M['cordon'] = B.mat_simple('Cordon', (0.04, 0.26, 0.3), 0.75, noise_scale=400, noise_col=(0.02, 0.15, 0.18), bump=0.2)
    M['bec'] = B.mat_simple('Bec', (0.015, 0.01, 0.008), 0.25)
    M['photo_v'] = _emi('PhotoV', (0.15, 1.0, 0.7), 14)
    M['photo_r'] = _emi('PhotoR', (1.0, 0.15, 0.08), 8)
    return M

def _nodes(nt):
    L = nt.links
    def math(op, a, b_=None):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b_)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    def smooth(x, e0, e1):
        n = nt.nodes.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; L.new(x, n.inputs['Value'])
        n.inputs['From Min'].default_value = e0; n.inputs['From Max'].default_value = e1; return n.outputs['Result']
    def mix(f, a, b_):
        n = nt.nodes.new('ShaderNodeMix'); n.data_type = 'RGBA'; A_, B_, R_ = B._mix_sockets(n)
        L.new(f, n.inputs[0])
        for sock, v in ((A_, a), (B_, b_)):
            if isinstance(v, tuple): sock.default_value = v
            else: L.new(v, sock)
        return R_
    return L, math, smooth, mix

def _oeil(glow):
    """globe : sclère argentée sombre ; iris doré à fibres radiaires, cryptes, collerette claire, limbe noir ;
    pupille en barre horizontale, noire, avec une lueur verte au fond (reflet du tapis)"""
    m = bpy.data.materials.new('Oeil'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    L, math, smooth, mix = _nodes(nt)
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'oeil'
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L.new(at.outputs['Vector'], sep.inputs[0])
    qx, qy, qz = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']
    rho = math('SQRT', math('ADD', math('MULTIPLY', qx, qx), math('MULTIPLY', qy, qy)))
    front = smooth(qz, 0.0, 0.08)
    iris = math('MULTIPLY', math('SUBTRACT', 1.0, smooth(rho, 0.76, 0.8)), front)
    hx = math('DIVIDE', math('ABSOLUTE', qx), 0.52)
    pv0 = math('ADD', math('POWER', hx, 4.0), math('POWER', math('DIVIDE', qy, math('ADD', 0.075, math('MULTIPLY', math('MULTIPLY', hx, hx), 0.1))), 2.0))
    cpn = nt.nodes.new('ShaderNodeCombineXYZ'); L.new(qx, cpn.inputs[0]); L.new(qy, cpn.inputs[1])
    nzp = nt.nodes.new('ShaderNodeTexNoise'); nzp.inputs['Scale'].default_value = 7.0; nzp.inputs['Detail'].default_value = 3; L.new(cpn.outputs[0], nzp.inputs['Vector'])
    pv = math('ADD', pv0, math('MULTIPLY', math('SUBTRACT', nzp.outputs['Fac'], 0.5), 0.55))      # bord irrégulier, vivant
    pup = math('MULTIPLY', math('SUBTRACT', 1.0, smooth(pv, 0.85, 1.05)), front)
    ang = math('ARCTAN2', qy, qx)
    cmb = nt.nodes.new('ShaderNodeCombineXYZ')
    L.new(math('MULTIPLY', math('SINE', ang), 14.0), cmb.inputs[0]); L.new(math('MULTIPLY', math('COSINE', ang), 14.0), cmb.inputs[1]); L.new(math('MULTIPLY', rho, 2.5), cmb.inputs[2])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 12; nz.inputs['Roughness'].default_value = 0.62
    L.new(cmb.outputs[0], nz.inputs['Vector'])
    fib = B.ramp(nt, (0, 0), [(0.3, (0.06, 0.018, 0.002, 1)), (0.46, (0.38, 0.15, 0.012, 1)), (0.6, (0.78, 0.42, 0.05, 1)), (0.74, (0.98, 0.7, 0.2, 1))])
    L.new(nz.outputs['Fac'], fib.inputs[0])
    cpos = nt.nodes.new('ShaderNodeCombineXYZ'); L.new(qx, cpos.inputs[0]); L.new(qy, cpos.inputs[1])
    vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 16; L.new(cpos.outputs[0], vo.inputs['Vector'])
    crypt = math('MULTIPLY', math('SUBTRACT', 1.0, smooth(vo.outputs['Distance'], 0.05, 0.22)), 0.55)
    col = mix(crypt, fib.outputs['Color'], (0.12, 0.04, 0.005, 1))
    coll = math('SUBTRACT', 1.0, smooth(pv, 1.3, 4.5))                                   # collerette claire autour de la fente
    col = mix(math('MULTIPLY', coll, 0.45), col, (1.0, 0.78, 0.3, 1))
    limb = smooth(rho, 0.5, 0.76)                                                      # limbe sombre
    col = mix(math('MULTIPLY', limb, 0.85), col, (0.03, 0.015, 0.004, 1))
    iris_col = col
    col = mix(iris, (0.06, 0.065, 0.065, 1), col)
    col = mix(pup, col, (0.0, 0.0, 0.0, 1))
    L.new(col, b.inputs['Base Color'])
    L.new(math('MULTIPLY', math('SUBTRACT', 1.0, iris), 0.85), b.inputs['Metallic'])
    b.inputs['Roughness'].default_value = 0.32
    if 'Thin Film Thickness' in b.inputs: b.inputs['Thin Film Thickness'].default_value = 260.0
    # émission : lueur de la pupille (plus forte au centre de la fente) + faible lueur dorée de l'iris
    core = math('MULTIPLY', pup, math('POWER', math('SUBTRACT', 1.0, smooth(pv0, 0.0, 0.55)), 3.0))
    ecol = mix(core, mix(iris, (0, 0, 0, 1), iris_col), (0.1, 1.0, 0.22, 1))
    L.new(ecol, b.inputs['Emission Color'])
    gv = nt.nodes.new('ShaderNodeValue'); gv.name = 'Lueur'; gv.outputs[0].default_value = glow
    L.new(math('ADD', math('MULTIPLY', core, gv.outputs[0]), math('MULTIPLY', iris, math('MULTIPLY', gv.outputs[0], 0.06))), b.inputs['Emission Strength'])
    return m

def _argent():
    """glande digestive : fuseau couvert de cellules réfléchissantes (camouflage du poulpe de verre), irisé"""
    m = bpy.data.materials.new('GlandeArgent'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    b.inputs['Base Color'].default_value = (0.8, 0.78, 0.74, 1); b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.14
    if 'Thin Film Thickness' in b.inputs: b.inputs['Thin Film Thickness'].default_value = 420.0; b.inputs['Thin Film IOR'].default_value = 1.5
    tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], nz.inputs['Vector']); bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08
    L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m

def _badge():
    import os
    m = bpy.data.materials.new('Badge'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(os.getcwd(), 'data', 'vitrelle', 'badge_aldane.png'))
    tx.interpolation = 'Cubic'; L.new(tx.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.45; b.inputs['Coat Weight'].default_value = 0.6; b.inputs['Coat Roughness'].default_value = 0.15
    return m

def _emi(name, col, s):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1); b.inputs['Emission Color'].default_value = (*col, 1); b.inputs['Emission Strength'].default_value = s
    b.inputs['Transmission Weight'].default_value = 0.5; b.inputs['Roughness'].default_value = 0.1
    return m

def _organe(name, col, emi, ecol=(1, 0.2, 0.2), trans=0.0):
    m = B.mat_simple(name, col, 0.45, noise_scale=60, noise_col=tuple(c*0.5 for c in col), bump=0.3); b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Subsurface Weight'].default_value = 0.4; b.inputs['Subsurface Radius'].default_value = (1, 0.3, 0.2); b.inputs['Subsurface Scale'].default_value = 0.01
    if emi: b.inputs['Emission Color'].default_value = (*ecol, 1); b.inputs['Emission Strength'].default_value = emi
    if trans: b.inputs['Transmission Weight'].default_value = trans; b.inputs['Roughness'].default_value = 0.3
    return m

def _ombre_claire(nt, surf):
    """les rayons d'ombre traversent le verre : les organes à l'intérieur reçoivent la lumière directe (pas de caustiques à calculer)"""
    lp = nt.nodes.new('ShaderNodeLightPath'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Shadow Ray'], mx.inputs[0]); nt.links.new(surf, mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    return mx.outputs[0]

def _verre_vivant(name, density=1.2, milk=0.12, spots=True, pig=False, ior=1.15):
    """chair de verre : transmission, film mince irisé, gel légèrement laiteux à l'intérieur, chromatophores épars"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; L = nt.links
    out = nt.nodes['Material Output']; g = nt.nodes['Principled BSDF']
    g.inputs['Base Color'].default_value = (0.9, 0.95, 0.97, 1); g.inputs['Roughness'].default_value = 0.07; g.inputs['IOR'].default_value = ior
    g.inputs['Transmission Weight'].default_value = 1.0; g.inputs['Coat Weight'].default_value = 0.25; g.inputs['Coat Roughness'].default_value = 0.03
    if 'Thin Film Thickness' in g.inputs: g.inputs['Thin Film Thickness'].default_value = 320.0; g.inputs['Thin Film IOR'].default_value = 1.38
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 18; nz.inputs['Detail'].default_value = 2; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.006; L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], g.inputs['Normal'])
    surf = g.outputs[0]
    if spots:
        vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 55; L.new(tc.outputs['Object'], vo.inputs['Vector'])
        rr = B.ramp(nt, (0, 0), [(0.0, (1, 1, 1, 1)), (0.12, (0, 0, 0, 1))]); L.new(vo.outputs['Distance'], rr.inputs[0])
        ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 3; L.new(tc.outputs['Object'], ns.inputs['Vector'])
        rm = B.ramp(nt, (0, -200), [(0.5, (0, 0, 0, 1)), (0.7, (0.8, 0.8, 0.8, 1))]); L.new(ns.outputs['Fac'], rm.inputs[0])
        mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(rr.outputs['Color'], mm.inputs[0]); L.new(rm.outputs['Color'], mm.inputs[1])
        d = nt.nodes.new('ShaderNodeBsdfPrincipled'); d.inputs['Base Color'].default_value = (0.25, 0.06, 0.04, 1); d.inputs['Roughness'].default_value = 0.4
        fac = mm.outputs[0]
        if pig:                                          # masque sombre autour des yeux : chromatophores serrés
            at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'pigment'
            d.inputs['Base Color'].default_value = (0.11, 0.022, 0.012, 1); d.inputs['Coat Weight'].default_value = 0.7; d.inputs['Coat Roughness'].default_value = 0.05
            pm = nt.nodes.new('ShaderNodeMath'); pm.operation = 'MULTIPLY'; L.new(at.outputs['Fac'], pm.inputs[0]); pm.inputs[1].default_value = 0.22
            sp = nt.nodes.new('ShaderNodeMath'); sp.operation = 'MULTIPLY'; L.new(rr.outputs['Color'], sp.inputs[0]); L.new(at.outputs['Fac'], sp.inputs[1])
            a1 = nt.nodes.new('ShaderNodeMath'); a1.operation = 'ADD'; a1.use_clamp = True; L.new(fac, a1.inputs[0]); L.new(pm.outputs[0], a1.inputs[1])
            a2 = nt.nodes.new('ShaderNodeMath'); a2.operation = 'ADD'; a2.use_clamp = True; L.new(a1.outputs[0], a2.inputs[0]); L.new(sp.outputs[0], a2.inputs[1])
            fac = a2.outputs[0]
        mix = nt.nodes.new('ShaderNodeMixShader'); L.new(fac, mix.inputs[0]); L.new(surf, mix.inputs[1]); L.new(d.outputs[0], mix.inputs[2]); surf = mix.outputs[0]
    L.new(_ombre_claire(nt, surf), out.inputs['Surface'])
    va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.88, 0.95, 0.97, 1); va.inputs['Density'].default_value = density
    vs = nt.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Color'].default_value = (0.9, 0.95, 1, 1); vs.inputs['Density'].default_value = milk; vs.inputs['Anisotropy'].default_value = 0.4
    av = nt.nodes.new('ShaderNodeAddShader'); L.new(va.outputs[0], av.inputs[0]); L.new(vs.outputs[0], av.inputs[1]); L.new(av.outputs[0], out.inputs['Volume'])
    return m

def assign(parts, M):
    pairs = dict(vaisseaux='coeur', oesophage='oesophage', peau='peau', ventouses='ventouse', pores='pore', yeux='oeil', cornees='cornee', glande='glande', cordon='cordon',
                 coeurs='coeur', branchies='branchie', nerfs='nerf', badge='badge', bec='bec', photo_v='photo_v', photo_r='photo_r')
    for k, o in parts.items(): o.data.materials.clear(); o.data.materials.append(M[pairs[k]])

# ================================================================ poses
def wrap_ceiling(parts, R=1.5, x0=3.5, gap=0.02, rot=0.0):
    """enroule le poulpe (repère sol) sur le plafond cylindrique d'une coursive d'axe X : le sol local devient le plafond ;
    rot = rotation préalable autour de la verticale locale (pour orienter un œil vers la caméra)"""
    c, s_ = math.cos(rot), math.sin(rot)
    for o in parts.values():
        me = o.data
        for v in me.vertices:
            x0_, y0_, h = v.co; x, y = c*x0_ - s_*y0_, s_*x0_ + c*y0_
            th = -y/R; r = R - gap - h      # rotation de 180° autour de X (pas de miroir)
            v.co = Vector((x0 + x, r*math.sin(th), r*math.cos(th)))
        me.update()
