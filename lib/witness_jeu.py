"""THE WITNESS — version jeu (Roblox) : maillage allégé, squelette, poids de peau.
Pose de repos : posée à plat au sol, bras droits en étoile (le script Roblox anime tout à partir de cette pose).
Unités de sortie : studs (envergure ≈ 12 studs ≈ 3,4 m, comme dans le lore). Devant = +X (côté yeux/bec).
Os : Racine, Tete, Manteau1, Manteau2, Bec, OeilG, OeilD, Bras{k}_{1..8} (k = 0..7)."""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix
import ballast_bl as B
from abysse import mesh_obj, xf_verts, tube_bm, ell_bm
from vitrelle import CROWN, EYE_BASE, EYE_AX, EYE_R, EYE_C, MANTLE_C, MANTLE_AX, UP, rad_at, eye_frame

L_BRAS = 2.75; N_OS = 8; ENVERGURE_STUDS = 12.1
def angle_bras(k): return k*math.pi/4 + math.pi/8          # aucun bras droit devant : les yeux restent dégagés

def chemin_bras(k, n=120):
    """bras au repos : droit, couché au sol (hauteur = son rayon), base sous la couronne"""
    a = angle_bras(k); d = Vector((math.cos(a), math.sin(a), 0)); P = []
    for i in range(n + 1):
        s = L_BRAS*i/n; r = rad_at(s, L_BRAS)
        P.append(CROWN*(1 - min(1, s/0.25)) + Vector((0, 0, 0)) + d*(0.15 + s) + Vector((0, 0, r*min(1, s/0.25) + (1 - min(1, s/0.25))*CROWN.z)))
    return P

def construire(log=print, cible_tri=11000, seed=21):
    rng = random.Random(seed); parts = {}
    # ---------------------------------------------------------------- peau : bras + palmure + corps, remaillée puis allégée
    skin = []
    for k in range(8):
        P = chemin_bras(k); sk = B.Skel(); prev = None
        for i, p in enumerate(P[::3]):
            s = i*3*L_BRAS/120; ii = sk.v(p, max(rad_at(s, L_BRAS), 0.012))
            if prev is not None: sk.e(prev, ii)
            prev = ii
        skin.append(B.skin_object(f'bras{k}', sk, sub=1))
    bm = bmesh.new()
    for k in range(8):                                       # palmure : nappe entre deux bras voisins, jusqu'à 0,5 m
        A, C = chemin_bras(k), chemin_bras((k + 1) % 8); nu, nv = 14, 8; grid = []
        for iu in range(nu + 1):
            row = []
            for iv in range(nv + 1):
                v = iv/nv; smax = 0.5*(1 - 0.5*math.sin(math.pi*v)); s = smax*iu/nu; j = int(s/L_BRAS*120)
                p = A[j].lerp(C[j], v) + UP*(0.02*math.sin(math.pi*v)); row.append(bm.verts.new(p))
            grid.append(row)
        for iu in range(nu):
            for iv in range(nv): bm.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
    web = mesh_obj('palmure', bm); so = web.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.03; so.offset = 0; B.bake_mods(web); skin.append(web)
    bm = bmesh.new()
    ell_bm(bm, CROWN, (0.21, 0.21, 0.1), Matrix.Identity(3), 32)
    ell_bm(bm, Vector((0.02, 0, 0.34)), (0.25, 0.3, 0.22), Matrix.Identity(3), 32)
    ell_bm(bm, Vector((-0.12, 0, 0.45)), (0.25, 0.28, 0.24), Matrix.Identity(3), 32)
    ell_bm(bm, MANTLE_C, (0.56, 0.37, 0.34), B.frame(MANTLE_AX, UP).to_3x3(), 40)
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]; tube_bm(bm, b0 - e*0.04, b0 + e*0.06, 0.07, 24)
    tube_bm(bm, Vector((-0.04, -0.24, 0.24)), Vector((0.06, -0.33, 0.17)), 0.045, 16)      # entonnoir
    skin.append(mesh_obj('corps', bm))
    for o in skin: B.bake_mods(o)
    corps = B.remesh(B.join(skin, 'Corps'), voxel=0.009, smooth=5)
    n0 = len(corps.data.polygons)
    d = corps.modifiers.new('dec', 'DECIMATE'); d.ratio = min(1.0, cible_tri/max(1, n0*2)); d.use_collapse_triangulate = True; B.bake_mods(corps)
    B.shade_smooth(corps); parts['corps'] = corps
    log(f'peau : {n0} faces remaillées -> {len(corps.data.polygons)} triangles')
    # ---------------------------------------------------------------- ventouses : une rangée alternée, cupules basses
    bm = bmesh.new()
    for k in range(8):
        a = angle_bras(k); dd = Vector((math.cos(a), math.sin(a), 0)); sd = Vector((-dd.y, dd.x, 0)); s = 0.18; side = 1
        while s < L_BRAS - 0.15:
            r = rad_at(s, L_BRAS); rs = 0.55*r; c = CROWN*0 + dd*(0.15 + s) + sd*side*r*0.45 + Vector((0, 0, 0.0015))
            o = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=5, radius1=rs, radius2=rs*0.7, depth=rs*0.35)
            zmax = max(v.co.z for v in o['verts'])                # disque du haut : noyé dans le bras, jamais visible, on le retire
            fond = {fc for v in o['verts'] if v.co.z >= zmax - 1e-7 for fc in v.link_faces if all(w.co.z >= zmax - 1e-7 for w in fc.verts)}
            bmesh.ops.delete(bm, geom=list(fond), context='FACES_ONLY')
            xf_verts(o['verts'], Matrix.Translation(c + Vector((0, 0, rs*0.17))))
            side = -side; s += max(rs*3.5, 0.04)
    parts['ventouses'] = mesh_obj('Ventouses', bm, smooth=True)
    # ---------------------------------------------------------------- yeux : globe doré + fente lumineuse verte
    bmo, bmp = bmesh.new(), bmesh.new()
    for sg in (-1, 1):
        F = eye_frame(sg)
        ell_bm(bmo, EYE_C[sg], (EYE_R,)*3, F, 20)
        ell_bm(bmp, EYE_C[sg] + EYE_AX[sg]*EYE_R*0.93, (EYE_R*0.62, EYE_R*0.13, EYE_R*0.1), F, 12)     # fente horizontale
    parts['oeil'] = mesh_obj('Yeux', bmo, smooth=True); parts['pupille'] = mesh_obj('Pupilles', bmp, smooth=True)
    # ---------------------------------------------------------------- organes visibles et badge
    bm_r, bm_a, bm_b = bmesh.new(), bmesh.new(), bmesh.new()
    ell_bm(bm_r, Vector((-0.17, 0, 0.5)), (0.034, 0.03, 0.03), Matrix.Identity(3), 10)
    for sg in (-1, 1): ell_bm(bm_r, Vector((-0.22, sg*0.1, 0.47)), (0.022,)*3, Matrix.Identity(3), 8)
    ell_bm(bm_a, MANTLE_C + MANTLE_AX*0.04 - UP*0.03, (0.25, 0.07, 0.07), B.frame(MANTLE_AX, UP).to_3x3(), 14)
    bc = MANTLE_C - MANTLE_AX*0.1 + Vector((0, -0.17, -0.02)); bx = Vector((1, 0, 0.25)).normalized()
    from abysse import box_bm
    box_bm(bm_b, bc, (0.0428, 0.027, 0.002), B.frame(bx, Vector((0, -1, 0))).to_3x3())
    parts['coeurs'] = mesh_obj('Coeurs', bm_r, smooth=True); parts['glande'] = mesh_obj('Glande', bm_a, smooth=True); parts['badge'] = mesh_obj('Badge', bm_b)
    # ---------------------------------------------------------------- photophores : dos des bras, autour des yeux, manteau
    bm_v, bm_rr = bmesh.new(), bmesh.new()
    for k in range(8):
        a = angle_bras(k); dd = Vector((math.cos(a), math.sin(a), 0)); s = 0.3
        while s < L_BRAS - 0.2:
            r = rad_at(s, L_BRAS); sz = (0.004 + r*0.1)*rng.uniform(0.7, 1.4)
            ell_bm(bm_rr if rng.random() < 0.12 else bm_v, dd*(0.15 + s) + Vector((0, 0, r*1.85)), (sz,)*3, Matrix.Identity(3), 6)
            s += rng.uniform(0.2, 0.36)
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]; t1 = e.cross(UP).normalized(); t2 = e.cross(t1)
        for k in range(8):
            a = k/8*2*math.pi + 0.3; ell_bm(bm_v, b0 + e*0.05 + (t1*math.cos(a) + t2*math.sin(a))*0.09, (0.006,)*3, Matrix.Identity(3), 6)
        for j in range(7):
            t = j/6; c = MANTLE_C + MANTLE_AX*(0.45 - 0.9*t) + Vector((0, sg*0.2*(1 - 0.5*abs(t - 0.5)), 0.24*(1 - (2*t - 1)**2) + 0.06))
            ell_bm(bm_v, c, (0.01,)*3, Matrix.Identity(3), 6)
    parts['photo_v'] = mesh_obj('PhotophoresV', bm_v, smooth=True); parts['photo_r'] = mesh_obj('PhotophoresR', bm_rr, smooth=True)
    # ---------------------------------------------------------------- échelle : studs
    pts = np.array([v.co[:] for v in corps.data.vertices]); env = max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1]))
    f = ENVERGURE_STUDS/env
    for o in parts.values(): o.data.transform(Matrix.Scale(f, 4))
    log(f'échelle ×{f:.3f} (envergure {env:.2f} m -> {ENVERGURE_STUDS} studs)')
    return parts, f

# ================================================================ squelette
def os_bras(f):
    """segments des os d'un bras : (nom, tête, queue, rayon)"""
    out = []
    for k in range(8):
        a = angle_bras(k); dd = Vector((math.cos(a), math.sin(a), 0)); s0 = 0.05
        for j in range(N_OS):
            sa = s0 + (L_BRAS - s0)*(j/N_OS)**1.15; sb = s0 + (L_BRAS - s0)*((j + 1)/N_OS)**1.15
            pa = dd*(0.15 + sa) + Vector((0, 0, rad_at(sa, L_BRAS))); pb = dd*(0.15 + sb) + Vector((0, 0, rad_at(sb, L_BRAS)))
            out.append((f'Bras{k}_{j + 1}', pa*f, pb*f, rad_at((sa + sb)/2, L_BRAS)*f, f'Bras{k}_{j}' if j else 'Racine'))
    return out

def squelette(f):
    """armature : renvoie l'objet et la liste (nom, tête, queue, rayon d'influence, parent)"""
    tete0 = CROWN*f; tete1 = Vector((0.02, 0, 0.42))*f
    m0 = Vector((-0.12, 0, 0.47))*f; m1 = MANTLE_C*f; m2 = (MANTLE_C + MANTLE_AX*0.5)*f      # le manteau part vers l'arrière et le haut
    defs = [('Racine', Vector((0, 0, 0)), tete0, 0.25*f, None),
            ('Tete', tete0, tete1, 0.26*f, 'Racine'),
            ('Manteau1', m0, m1, 0.3*f, 'Tete'),
            ('Manteau2', m1, m2, 0.33*f, 'Manteau1'),
            ('Bec', tete0, tete0 - Vector((0, 0, 0.08))*f, 0.05*f, 'Racine')]
    for sg, nm in ((1, 'OeilG'), (-1, 'OeilD')):
        defs.append((nm, EYE_C[sg]*f, (EYE_C[sg] + EYE_AX[sg]*0.1)*f, EYE_R*1.4*f, 'Tete'))
    defs += os_bras(f)
    arm = bpy.data.armatures.new('SqueletteWitness'); ob = bpy.data.objects.new('Witness', arm); B.coll().objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for nm, h, t, r, par in defs:
        b = arm.edit_bones.new(nm); b.head = h; b.tail = t if (t - h).length > 1e-4 else h + Vector((0, 0, 0.05)); b.roll = 0.0
        if par: b.parent = eb[par]; b.use_connect = False
        eb[nm] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob, defs

def _dist_segments(P, A, Bq):
    """distance de chaque point P (n,3) à chaque segment [A_j, B_j] (m,3) -> (n, m)"""
    AB = Bq - A; L2 = np.maximum((AB*AB).sum(1), 1e-12)
    t = np.clip(((P[:, None, :] - A[None])*AB[None]).sum(2)/L2[None], 0, 1)
    Q = A[None] + t[..., None]*AB[None]
    return np.linalg.norm(P[:, None, :] - Q, axis=2)

def lier(ob_mesh, arm_ob, defs, rigide=None, kmax=4):
    """poids par enveloppes : chaque os influence selon la distance à son segment, normalisée sur ses 4 plus proches.
    rigide = nom d'os : tout le maillage suit cet os (yeux, organes)"""
    names = [d[0] for d in defs]
    for nm in names: ob_mesh.vertex_groups.new(name=nm)
    P = np.array([v.co[:] for v in ob_mesh.data.vertices])
    if rigide:
        ob_mesh.vertex_groups[rigide].add(list(range(len(P))), 1.0, 'REPLACE')
    else:
        A = np.array([d[1][:] for d in defs]); Bq = np.array([d[2][:] for d in defs]); R = np.array([d[3] for d in defs])
        sig = R*2.2 + 0.25
        Dm = _dist_segments(P, A, Bq)
        W = np.exp(-(Dm/sig[None])**2)
        # le corps central ne doit pas tirer sur les bras lointains et inversement
        idx = np.argsort(-W, axis=1)[:, :kmax]
        for i in range(len(P)):
            ws = W[i, idx[i]]; s = ws.sum()
            if s < 1e-9: ws = np.array([1.0] + [0.0]*(kmax - 1)); s = 1.0
            for j, w in zip(idx[i], ws/s):
                if w > 0.01: ob_mesh.vertex_groups[names[j]].add([i], float(w), 'REPLACE')
    mod = ob_mesh.modifiers.new('squelette', 'ARMATURE'); mod.object = arm_ob
    ob_mesh.parent = arm_ob
