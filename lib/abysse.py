"""Base sous-marine abandonnée — décors et trois créatures (aperçus) : le Siphon, l'Écho, le Scaphandrier.
Repère Blender : Z en haut, mètres."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
import ballast_bl as B

# ================================================================ outils
def mesh_obj(name, bm, mat=None, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); B.coll().objects.link(ob)
    if mat: ob.data.materials.append(mat)
    if smooth: B.shade_smooth(ob)
    return ob

def xf_verts(verts, M):
    for v in verts: v.co = M @ v.co

def tube_bm(bm, a, b, r, seg=24, cap=True):
    a = Vector(a); b = Vector(b); d = b - a
    o = bmesh.ops.create_cone(bm, cap_ends=cap, segments=seg, radius1=r, radius2=r, depth=d.length)
    M = Matrix.Translation((a + b)/2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    xf_verts(o['verts'], M)

def torus_bm(bm, c, axis, R, r, seg=48, rseg=12):
    c = Vector(c); q = Vector(axis).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    verts = []
    rings = []
    for i in range(seg):
        a = i/seg*2*math.pi; ring = []
        for j in range(rseg):
            b = j/rseg*2*math.pi
            p = Vector(((R + r*math.cos(b))*math.cos(a), (R + r*math.cos(b))*math.sin(a), r*math.sin(b)))
            ring.append(bm.verts.new(Matrix.Translation(c) @ q @ p))
        rings.append(ring)
    for i in range(seg):
        r0, r1 = rings[i], rings[(i + 1) % seg]
        for j in range(rseg): bm.faces.new((r0[j], r1[j], r1[(j + 1) % rseg], r0[(j + 1) % rseg]))

def ell_bm(bm, c, r, R=Matrix.Identity(3), seg=32):
    o = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg//2, radius=1.0)
    xf_verts(o['verts'], Matrix.Translation(Vector(c)) @ R.to_4x4() @ Matrix.Diagonal((*r, 1)))

def box_bm(bm, c, h, R=Matrix.Identity(3)):
    o = bmesh.ops.create_cube(bm, size=2.0)
    xf_verts(o['verts'], Matrix.Translation(Vector(c)) @ R.to_4x4() @ Matrix.Diagonal((*h, 1)))

def text_obj(txt, loc, rot, size, mat):
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = txt; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.004
    ob = bpy.data.objects.new('Texte', cu); B.coll().objects.link(ob); ob.location = loc; ob.rotation_euler = rot
    ob.data.materials.append(mat); return ob

# ================================================================ matériaux
def mats():
    S = B.mat_simple; M = {}
    M['coque'] = _rouille_peinte('Coque', (0.12, 0.15, 0.14), (0.16, 0.07, 0.03))
    M['acier'] = S('AcierAb', (0.3, 0.31, 0.32), 0.4, 0.85, noise_scale=20, noise_col=(0.09, 0.06, 0.04), bump=0.15)
    M['tuyau'] = _rouille_peinte('Tuyau', (0.22, 0.2, 0.12), (0.13, 0.05, 0.02))
    M['caillebotis'] = S('Caillebotis', (0.18, 0.18, 0.18), 0.5, 0.9, noise_scale=30, noise_col=(0.08, 0.04, 0.02), bump=0.2)
    M['verre'] = _verre('Hublot', 0.05)
    M['verre_buee'] = _verre('Buee', 0.22, (0.7, 0.85, 0.8))
    M['rouge'] = _emission('Alarme', (1.0, 0.06, 0.03), 18)
    M['vert'] = _emission('Sortie', (0.15, 1.0, 0.35), 9)
    M['noir'] = S('Noir', (0.01, 0.012, 0.015), 0.6)
    M['eau'] = _eau()
    M['laiton'] = _laiton()
    M['gelee'] = _gelee('Gelee', (0.62, 0.82, 0.86), 0.06)
    M['filament'] = _gelee('Filament', (0.95, 0.55, 0.65), 0.35)
    M['tige'] = _gelee('Tige', (0.9, 0.6, 0.7), 0.15)
    M['peau_echo'] = _peau_baleine()
    M['oeil'] = _verre('OeilLaiteux', 0.35, (0.85, 0.9, 0.92))
    M['langue'] = _peau('Langue', (0.28, 0.12, 0.13), (0.12, 0.04, 0.05), sss=0.3)
    M['fanon'] = S('Fanon', (0.07, 0.06, 0.05), 0.45, noise_scale=60, noise_col=(0.02, 0.018, 0.015), bump=0.4)
    M['anguille'] = _peau('Anguille', (0.25, 0.27, 0.22), (0.08, 0.09, 0.07), sss=0.3)
    M['bernacle'] = S('Bernacle', (0.45, 0.43, 0.38), 0.85, noise_scale=80, noise_col=(0.15, 0.14, 0.12), bump=0.6)
    return M

def _rouille_peinte(name, col, rust):
    m = B.mat_simple(name, col, 0.55, 0.3); nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 1, 0.15)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 5; n.inputs['Detail'].default_value = 10; nt.links.new(mp.outputs[0], n.inputs['Vector'])
    r = B.ramp(nt, (0, 0), [(0.5, (*col, 1)), (0.66, (*rust, 1)), (0.8, (rust[0]*0.4, rust[1]*0.4, rust[2]*0.4, 1))])
    nt.links.new(n.outputs['Fac'], r.inputs[0]); nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.2; nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def _verre(name, rough, col=(0.8, 0.9, 0.95)):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.5
    return m

def _emission(name, col, s):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.02, 0.02, 0.02, 1); b.inputs['Emission Color'].default_value = (*col, 1); b.inputs['Emission Strength'].default_value = s
    return m

def _eau():
    m = bpy.data.materials.new('Eau'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.01, 0.02, 0.02, 1); b.inputs['Roughness'].default_value = 0.03; b.inputs['Specular IOR Level'].default_value = 0.8
    tc = nt.nodes.new('ShaderNodeTexCoord'); n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 6; n.inputs['Detail'].default_value = 6
    nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.12; nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def _laiton():
    m = bpy.data.materials.new('Laiton'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Metallic'].default_value = 1.0
    tc = nt.nodes.new('ShaderNodeTexCoord'); n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 4; n.inputs['Detail'].default_value = 6
    nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    r = B.ramp(nt, (0, 0), [(0.45, (0.55, 0.37, 0.15, 1)), (0.6, (0.32, 0.2, 0.08, 1)), (0.7, (0.12, 0.3, 0.24, 1))])   # laiton, terni, vert-de-gris
    nt.links.new(n.outputs['Fac'], r.inputs[0]); nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
    rr = B.ramp(nt, (0, -200), [(0.45, (0.3, 0.3, 0.3, 1)), (0.7, (0.75, 0.75, 0.75, 1))]); nt.links.new(n.outputs['Fac'], rr.inputs[0]); nt.links.new(rr.outputs['Color'], b.inputs['Roughness'])
    mt = B.ramp(nt, (0, -400), [(0.6, (1, 1, 1, 1)), (0.7, (0.1, 0.1, 0.1, 1))]); nt.links.new(n.outputs['Fac'], mt.inputs[0]); nt.links.new(mt.outputs['Color'], b.inputs['Metallic'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.06; nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def _gelee(name='Gelee', col=(0.6, 0.8, 0.85), emi=0.25):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = 0.12; b.inputs['Transmission Weight'].default_value = 0.92; b.inputs['IOR'].default_value = 1.34
    b.inputs['Emission Color'].default_value = (col[0]*0.4, col[1]*0.7, col[2], 1); b.inputs['Emission Strength'].default_value = emi
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    nt.links.new(lw.outputs['Facing'], b.inputs['Coat Weight'])
    return m

def _peau_baleine():
    m = bpy.data.materials.new('PeauEcho'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 1.6; n.inputs['Detail'].default_value = 8; nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    r = B.ramp(nt, (0, 0), [(0.35, (0.05, 0.06, 0.075, 1)), (0.6, (0.13, 0.14, 0.16, 1)), (0.75, (0.24, 0.22, 0.22, 1))]); nt.links.new(n.outputs['Fac'], r.inputs[0])
    # cicatrices : longues griffures pâles (bandes étirées)
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6, 0.6, 0.6); mp.inputs['Rotation'].default_value = (0.3, 0.5, 0.2)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = 3; w.inputs['Distortion'].default_value = 4; nt.links.new(mp.outputs[0], w.inputs['Vector'])
    rs = B.ramp(nt, (0, -200), [(0.0, (1, 1, 1, 1)), (0.06, (0, 0, 0, 1))]); nt.links.new(w.outputs['Fac'], rs.inputs[0])
    n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 2.5; nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    rm = B.ramp(nt, (0, -400), [(0.55, (0, 0, 0, 1)), (0.65, (1, 1, 1, 1))]); nt.links.new(n2.outputs['Fac'], rm.inputs[0])
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; nt.links.new(rs.outputs['Color'], mm.inputs[0]); nt.links.new(rm.outputs['Color'], mm.inputs[1])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; A_, B_, R_ = B._mix_sockets(mx)
    nt.links.new(mm.outputs[0], mx.inputs[0]); nt.links.new(r.outputs['Color'], A_); B_.default_value = (0.42, 0.4, 0.38, 1); nt.links.new(R_, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.28; b.inputs['Coat Weight'].default_value = 0.5; b.inputs['Coat Roughness'].default_value = 0.1
    b.inputs['Subsurface Weight'].default_value = 0.08; b.inputs['Subsurface Radius'].default_value = (1.0, 0.4, 0.3); b.inputs['Subsurface Scale'].default_value = 0.05
    n3 = nt.nodes.new('ShaderNodeTexNoise'); n3.inputs['Scale'].default_value = 40; nt.links.new(tc.outputs['Object'], n3.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.15; nt.links.new(n3.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def _peau(name, col, col2, sss=0.15):
    m = B.mat_simple(name, col, 0.5, noise_scale=3, noise_col=col2, bump=0.35); b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (1.0, 0.4, 0.3); b.inputs['Subsurface Scale'].default_value = 0.05
    return m

def eau_trouble(name, lo, hi, col=(0.1, 0.45, 0.42), dens=0.06, aniso=0.5):
    bm = bmesh.new(); box_bm(bm, (Vector(lo) + Vector(hi))/2, (Vector(hi) - Vector(lo))/2); ob = mesh_obj(name, bm)
    m = bpy.data.materials.new(name + 'Vol'); m.use_nodes = True; nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    v = nt.nodes.new('ShaderNodeVolumePrincipled'); v.inputs['Color'].default_value = (*col, 1); v.inputs['Density'].default_value = dens; v.inputs['Anisotropy'].default_value = aniso
    v.inputs['Absorption Color'].default_value = (col[0]*0.6, col[1]*0.9, col[2], 1)
    nt.links.new(v.outputs[0], nt.nodes['Material Output'].inputs['Volume']); ob.data.materials.append(m)
    return ob

def neige_marine(lo, hi, n=2500, seed=3, avoid=(), avoid_r=1.2):
    """particules en suspension (neige marine)"""
    rng = random.Random(seed); bm = bmesh.new()
    for k in range(n):
        p = Vector([rng.uniform(lo[i], hi[i]) for i in range(3)]); s = rng.uniform(0.002, 0.006)
        if any((p - Vector(a)).length < avoid_r for a in avoid): continue
        o = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s); xf_verts(o['verts'], Matrix.Translation(p))
    m = B.mat_simple('Neige', (0.7, 0.75, 0.72), 0.8); b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (0.5, 0.7, 0.65, 1); b.inputs['Emission Strength'].default_value = 0.15
    return mesh_obj('NeigeMarine', bm, m)

# ================================================================ décor : coursive cylindrique
def coursive(M, L=16.0, R=1.5, x0=-4.0, porte=True, rng_seed=1, alarme=25):
    rng = random.Random(rng_seed)
    bm = bmesh.new(); o = bmesh.ops.create_cone(bm, cap_ends=False, segments=64, radius1=R, radius2=R, depth=L)
    xf_verts(o['verts'], Matrix.Translation((x0 + L/2, 0, 0)) @ Matrix.Rotation(math.pi/2, 4, 'Y'))
    coque = mesh_obj('Coque', bm, M['coque'], smooth=True)
    bm = bmesh.new()
    for x in [x0 + 0.6 + 1.6*k for k in range(int(L/1.6))]: torus_bm(bm, (x, 0, 0), (1, 0, 0), R - 0.05, 0.07)
    mesh_obj('Couples', bm, M['acier'], smooth=True)
    # plancher en caillebotis
    bm = bmesh.new()
    for k in range(48):
        y = -1.1 + k*2.2/47; box_bm(bm, (x0 + L/2, y, -0.92), (L/2, 0.012, 0.025))
    for x in [x0 + 0.6 + 1.6*k for k in range(int(L/1.6))]: box_bm(bm, (x, 0, -0.97), (0.03, 1.12, 0.04))
    mesh_obj('Caillebotis', bm, M['caillebotis'])
    # tuyauteries le long des parois, avec brides
    bm = bmesh.new()
    for (y, z, r) in ((1.22, 0.55, 0.09), (1.05, 0.95, 0.06), (-1.25, 0.45, 0.07), (-1.33, 0.05, 0.05), (0.4, 1.38, 0.05), (-0.45, 1.36, 0.04)):
        tube_bm(bm, (x0, y, z), (x0 + L, y, z), r, 20)
        for x in [x0 + 1 + 2.2*k for k in range(int(L/2.2))]: torus_bm(bm, (x + rng.uniform(-0.2, 0.2), y, z), (1, 0, 0), r + 0.012, 0.018, 24, 8)
    mesh_obj('Tuyaux', bm, M['tuyau'], smooth=True)
    # hublots sur la paroi droite (+Y)
    bm = bmesh.new(); bg = bmesh.new()
    for x in (x0 + 2.2, x0 + 7.0, x0 + 11.8):
        torus_bm(bm, (x, 1.42, 0.25), (0, 1, 0), 0.24, 0.04)
        ell_bm(bg, (x, 1.44, 0.25), (0.22, 0.01, 0.22))
    mesh_obj('CadresHublots', bm, M['acier'], smooth=True); mesh_obj('VitresHublots', bg, M['verre'])
    # lampes d'alarme rouges au plafond
    lamps = []; bm = bmesh.new()
    for x in (x0 + 1.4, x0 + 6.2, x0 + 11.0):
        box_bm(bm, (x, 0, 1.43), (0.12, 0.05, 0.03)); lamps.append(Vector((x, 0, 1.3)))
    mesh_obj('Alarmes', bm, M['rouge'])
    for p in lamps: B.light('POINT', tuple(p), alarme, (1.0, 0.08, 0.04), size=0.08, name='LumAlarme')
    # sas au fond
    if porte:
        bm = bmesh.new(); torus_bm(bm, (x0 + L - 0.3, 0, 0), (1, 0, 0), 0.75, 0.08); ell_bm(bm, (x0 + L - 0.25, 0, 0), (0.03, 0.72, 0.72))
        torus_bm(bm, (x0 + L - 0.36, 0, 0), (1, 0, 0), 0.22, 0.025, 32, 8)
        for k in range(4):
            a = k*math.pi/2; tube_bm(bm, (x0 + L - 0.36, 0, 0), (x0 + L - 0.36, math.cos(a)*0.22, math.sin(a)*0.22), 0.015, 8)
        mesh_obj('Sas', bm, M['acier'], smooth=True)
    return coque

# ================================================================ 1. LE SIPHON
def siphon(M, path_pts, n=64, seed=7, lure_at=None):
    """colonie : chaîne de cloches translucides (nectophores), organes lumineux, filaments urticants qui pendent"""
    rng = random.Random(seed); path = B.Path(path_pts)
    bm_b = bmesh.new(); bm_o_r = bmesh.new(); bm_o_v = bmesh.new(); bm_f = bmesh.new(); bm_t = bmesh.new()
    stem = [path.at(path.L*k/120)[0] for k in range(121)]
    for a, b in zip(stem[:-1], stem[1:]): tube_bm(bm_f, a, b, 0.011, 10, cap=False)
    i = 0; x = 0.0
    while x < path.L:
        f = x/path.L; p, d = path.at(x)
        s = (1.0 - 0.6*f)*(1.35 if i < 3 else 1.0)*rng.uniform(0.7, 1.3)
        up = Vector((0, 0, 1)); Fm = B.frame(d, up).to_3x3()
        wob = Matrix.Rotation(rng.uniform(-1.2, 1.2), 3, d) @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 3, Fm.col[1])
        off = (Fm.col[1]*rng.uniform(-1, 1) + Fm.col[2]*rng.uniform(-1, 1))*0.03*s
        # cloche : forme irrégulière, ouverture vers l'arrière, paroi double
        ell_bm(bm_b, p + off, (0.12*s*rng.uniform(0.8, 1.25), 0.085*s, 0.075*s*rng.uniform(0.8, 1.2)), wob @ Fm, 24)
        ell_bm(bm_b, p + off + d*0.04*s, (0.055*s, 0.05*s, 0.045*s), wob @ Fm, 16)
        green = (i % 6 == 0) or (i < 6)
        if rng.random() < 0.8:
            ell_bm(bm_o_v if green else bm_o_r, p + off - Fm.col[2]*0.02*s, (0.02*s, 0.016*s, 0.016*s), Fm, 10)
        for k in range(rng.choice([1, 2, 2, 3, 4])):
            q = p + off - Fm.col[2]*0.06*s
            ln = rng.uniform(0.6, 1.7)*(1.25 - 0.5*f); drift = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0)); ph = rng.uniform(0, 6.28)
            pts = [q + (Vector((0, 0, -1)) + drift*t)*ln*t + Vector((math.sin(t*11 + ph), math.cos(t*8 + ph*1.3), 0))*0.05*t for t in [j/20 for j in range(21)]]
            for a, b in zip(pts[:-1], pts[1:]): tube_bm(bm_f, a, b, 0.0014*(1.2 - 0.5*(pts.index(a)/20)), 6, cap=False)
            for t in (0.4, 0.7, 1.0):
                ell_bm(bm_t, pts[int(t*20)], (0.006, 0.006, 0.009), Matrix.Identity(3), 8)
        x += rng.uniform(0.07, 0.22)*(1.0 - 0.4*f); i += 1
    obs = [mesh_obj('SiphonCloches', bm_b, M['gelee'], True), mesh_obj('SiphonFilaments', bm_f, M['filament'], True),
           mesh_obj('SiphonPerles', bm_t, _emission('Perle', (0.9, 0.3, 0.5), 1.5), True),
           mesh_obj('SiphonOrganesR', bm_o_r, _emission('OrganeR', (1.0, 0.08, 0.04), 9), True),
           mesh_obj('SiphonOrganesV', bm_o_v, _emission('OrganeV', (0.2, 1.0, 0.35), 16), True)]
    # flotteur de tête : grosse cloche nacrée
    p, d = path.at(0.0); bm = bmesh.new(); ell_bm(bm, p - d*0.2, (0.26, 0.2, 0.2), B.frame(d, (0, 0, 1)).to_3x3(), 32)
    obs.append(mesh_obj('SiphonFlotteur', bm, _gelee('Nacre', (0.85, 0.6, 0.7), 0.6), True))
    # leurre : la tête s'enroule en rectangle de lumières vertes, comme un panneau « SORTIE »
    if lure_at is not None:
        c = Vector(lure_at); bm = bmesh.new(); bmc = bmesh.new()
        for k in range(26):
            u = k/26; per = 2*(0.5 + 0.22); s_ = u*per
            if s_ < 0.5: q = Vector((0, -0.25 + s_, 0.11))
            elif s_ < 0.72: q = Vector((0, 0.25, 0.11 - (s_ - 0.5)))
            elif s_ < 1.22: q = Vector((0, 0.25 - (s_ - 0.72), -0.11))
            else: q = Vector((0, -0.25, -0.11 + (s_ - 1.22)))
            ell_bm(bm, c + q, (0.03, 0.03, 0.03), Matrix.Identity(3), 12); ell_bm(bmc, c + q + Vector((0.02, 0, 0)), (0.045, 0.05, 0.045), Matrix.Identity(3), 16)
        obs.append(mesh_obj('Leurre', bm, _emission('LeurreV', (0.2, 1.0, 0.38), 22), True)); obs.append(mesh_obj('LeurreGelee', bmc, M['gelee'], True))
    return obs

# ================================================================ 2. L'ÉCHO
def echo(M, c=(0, 0, 0.0), yaw=0.0, pitch=0.0, seed=11):
    """tête aveugle énorme : front de graisse plissé, gueule béante à fanons en lambeaux, langue, yeux laiteux enfoncés,
    rangées de pores sur le melon (ses « oreilles »), bernacles ; un dos énorme qui plonge sous l'eau"""
    rng = random.Random(seed); c = Vector(c); R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-pitch, 3, 'Y')
    def P(x, y, z): return c + R @ Vector((x, y, z))
    sk = B.Skel(); prev = None
    for (x, y, z, r) in [(-0.4, 0, -0.3, 1.0), (-1.8, 0.2, -1.1, 1.15), (-3.2, 0.9, -2.0, 1.05), (-3.8, 2.5, -2.8, 0.9), (-2.8, 3.7, -3.4, 0.75), (-1.0, 3.6, -3.8, 0.6)]:
        i_ = sk.v(P(x, y, z), r)
        if prev is not None: sk.e(prev, i_)
        prev = i_
    objs = [B.skin_object('EchoCorps', sk, sub=2)]
    bm = bmesh.new()
    ell_bm(bm, P(0.75, 0, 0.45), (1.15, 1.0, 1.05), R, 48)            # melon bombé
    ell_bm(bm, P(1.3, 0, 0.2), (0.75, 0.85, 0.75), R, 40)             # front qui avance
    ell_bm(bm, P(0.3, 0, -0.15), (1.1, 1.05, 0.85), R, 48)            # crâne
    Rj = R @ Matrix.Rotation(0.38, 3, 'Y')                            # mâchoire basse, grande ouverte
    ell_bm(bm, P(1.1, 0, -0.95), (1.25, 0.8, 0.24), Rj, 40)
    for sg in (-1, 1):                                                # joues tombantes
        ell_bm(bm, P(1.0, sg*0.78, -0.45), (0.7, 0.25, 0.45), R, 24)
    objs.append(mesh_obj('EchoTete', bm))
    for o in objs: B.bake_mods(o)
    head = B.remesh(B.join(objs, 'Echo'), voxel=0.016, smooth=3)
    # gueule : creusée entre le front et la mâchoire
    bm = bmesh.new(); ell_bm(bm, P(1.55, 0, -0.55), (1.05, 0.66, 0.33), R @ Matrix.Rotation(0.18, 3, 'Y'), 32); cut = mesh_obj('cut', bm)
    m = head.modifiers.new('bouche', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cut; m.solver = 'FAST'
    t = bpy.data.textures.new('plis_echo', 'WOOD'); t.wood_type = 'BANDNOISE'; t.noise_scale = 0.35; t.turbulence = 9
    d1 = head.modifiers.new('plis', 'DISPLACE'); d1.texture = t; d1.strength = 0.03; d1.texture_coords = 'LOCAL'
    B.displace(head, 'CLOUDS', 0.7, 0.025, 2, name='echo_bosses'); B.displace(head, 'VORONOI', 0.06, 0.004, name='echo_rides')
    B.bake_mods(head); bpy.data.objects.remove(cut); B.shade_smooth(head); head.data.materials.append(M['peau_echo'])
    # langue grasse au fond de la gueule
    bm = bmesh.new(); ell_bm(bm, P(1.15, 0, -0.68), (0.75, 0.42, 0.14), Rj, 32); lg = mesh_obj('Langue', bm, M['langue'], True)
    # fanons : lames noires en lambeaux qui pendent du palais, longues et irrégulières
    bm = bmesh.new()
    for k in range(110):
        u = k/109; a = (u - 0.5)*2.5; side = 1 if a > 0 else -1
        base = P(1.0 + 0.95*math.cos(a), 0.64*math.sin(a), -0.28)
        hh = rng.uniform(0.25, 0.6)*(1.0 - 0.35*abs(a)/1.25)
        Rb = R @ Matrix.Rotation(a, 3, 'Z') @ Matrix.Rotation(rng.uniform(-0.15, 0.15), 3, 'X')
        box_bm(bm, base - R @ Vector((0, 0, hh/2)), (0.028, 0.004, hh/2), Rb)
        if rng.random() < 0.5: box_bm(bm, base - R @ Vector((0.02, 0, hh*0.9)), (0.012, 0.003, hh*0.25), Rb)   # franges
    mesh_obj('Fanons', bm, M['fanon'], True)
    # barbillons pâles qui pendent de la mâchoire dans l'eau
    bm = bmesh.new()
    for k in range(36):
        a = (k/35 - 0.5)*2.6; base = P(1.0 + 1.15*math.cos(a), 0.78*math.sin(a), -1.0)
        ln = rng.uniform(0.6, 1.4); ph = rng.uniform(0, 6.28)
        pts = [base + Vector((math.sin(t*5 + ph)*0.06, math.cos(t*4 + ph)*0.06, -ln*t)) for t in [j/12 for j in range(13)]]
        for j, (a_, b_) in enumerate(zip(pts[:-1], pts[1:])): tube_bm(bm, a_, b_, 0.018*(1 - j/13) + 0.003, 8)
    mesh_obj('Barbillons', bm, M['anguille'], True)
    # yeux laiteux enfoncés, et rangées de pores sur le melon
    bm = bmesh.new(); bmp = bmesh.new()
    for sg in (-1, 1):
        ell_bm(bm, P(1.15, sg*0.86, 0.08), (0.09, 0.05, 0.08), R, 20)
        for row in range(3):
            for k in range(7):
                a_ = 0.25 + k*0.16; z_ = 0.35 + row*0.22
                n = Vector((math.cos(a_)*0.8, sg*math.sin(a_), (z_ - 0.45)/1.05)).normalized()
                pp = P(0.75 + n.x*1.12, n.y*0.98, 0.45 + n.z*1.02); ell_bm(bmp, pp, (0.03, 0.03, 0.03), R, 10)
    mesh_obj('Yeux', bm, M['oeil'], True); mesh_obj('Pores', bmp, M['noir'], True)
    # bernacles en grappes sur le dessus
    bm = bmesh.new()
    for k in range(160):
        th = rng.uniform(-2.4, 2.4); ph = rng.uniform(0.3, 1.3)
        n = Vector((math.cos(ph)*math.cos(th), math.cos(ph)*math.sin(th), math.sin(ph)))
        p = P(0.5 + n.x*1.12, n.y*0.98, 0.45 + n.z*1.02); r = rng.uniform(0.02, 0.06)
        o = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=r*0.45, depth=r*1.2)
        xf_verts(o['verts'], Matrix.Translation(p) @ (R @ n).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    mesh_obj('Bernacles', bm, M['bernacle'], True)
    return head

def citerne(M, R=4.6, H=9.0, water=0.0):
    """ballast : grande citerne cylindrique, passerelle circulaire, tuyaux qui plongent, échelle"""
    bm = bmesh.new(); o = bmesh.ops.create_cone(bm, cap_ends=True, segments=96, radius1=R, radius2=R, depth=H)
    xf_verts(o['verts'], Matrix.Translation((0, 0, water + 1.0)))
    mesh_obj('Citerne', bm, M['coque'], True)
    bm = bmesh.new()
    for z in (water - 2.5, water - 0.5, water + 1.5, water + 3.5): torus_bm(bm, (0, 0, z), (0, 0, 1), R - 0.06, 0.08, 96, 10)
    mesh_obj('Cerclages', bm, M['acier'], True)
    # passerelle (demi-anneau) à 2 m au-dessus de l'eau
    bm = bmesh.new(); zc = water + 2.0
    for k in range(60):
        a = math.pi*0.55 + k/59*math.pi*0.9
        p = Vector((math.cos(a), math.sin(a), 0))*(R - 0.6)
        box_bm(bm, p + Vector((0, 0, zc)), (0.08, 0.55, 0.02), Matrix.Rotation(a, 3, 'Z'))
    for k in range(24):
        a = math.pi*0.55 + k/23*math.pi*0.9; p = Vector((math.cos(a), math.sin(a), 0))*(R - 1.12)
        tube_bm(bm, p + Vector((0, 0, zc)), p + Vector((0, 0, zc + 1.0)), 0.02, 8)
    pts = [Vector((math.cos(math.pi*0.55 + k/40*math.pi*0.9), math.sin(math.pi*0.55 + k/40*math.pi*0.9), 0))*(R - 1.12) + Vector((0, 0, zc + 1.0)) for k in range(41)]
    for a, b in zip(pts[:-1], pts[1:]): tube_bm(bm, a, b, 0.025, 8)
    mesh_obj('Passerelle', bm, M['caillebotis'], True)
    # tuyaux qui descendent dans l'eau
    bm = bmesh.new()
    for a, r in ((0.2, 0.25), (0.45, 0.15), (-0.35, 0.18), (2.0, 0.22), (-1.2, 0.3)):
        p = Vector((math.cos(a), math.sin(a), 0))*(R - 0.45)
        tube_bm(bm, p + Vector((0, 0, water - 3)), p + Vector((0, 0, water + 5)), r, 24)
        for z in (water + 0.6, water + 2.6, water + 4.2): torus_bm(bm, p + Vector((0, 0, z)), (0, 0, 1), r + 0.03, 0.03, 32, 8)
    mesh_obj('TuyauxCiterne', bm, M['tuyau'], True)
    bm = bmesh.new(); box_bm(bm, (0, 0, water), (R, R, 0.002)); mesh_obj('SurfaceEau', bm, M['eau'])
    return zc

# ================================================================ 3. LE SCAPHANDRIER
def scaphandrier(M, base=(0, 0, -0.9), yaw=math.pi, seed=5):
    """scaphandre rigide de grande profondeur en laiton : articulations à anneaux, pinces, bottes de plomb ;
    casque à hublots couvert de buée, et derrière, des anguilles pâles qui se pressent contre la vitre"""
    rng = random.Random(seed); o0 = Vector(base); R = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z): return o0 + R @ Vector((x, y, z))
    bm = bmesh.new()
    ell_bm(bm, P(0, 0, 1.45), (0.36, 0.42, 0.42), R, 40)              # torse
    ell_bm(bm, P(0, 0, 1.05), (0.3, 0.36, 0.2), R, 32)                # bassin
    torus_bm(bm, P(0, 0, 1.78), (0, 0, 1), 0.24, 0.05)                # collerette
    for z in (1.2, 1.3): torus_bm(bm, P(0, 0, z), (0, 0, 1), 0.33, 0.03)
    for k in range(16):                                                # boulons de la collerette
        a = k/16*2*math.pi; ell_bm(bm, P(math.cos(a)*0.24, math.sin(a)*0.24, 1.84), (0.018, 0.018, 0.018), R, 8)
    # bras : épaule à anneaux, segments, coude, pince ; bras droit levé vers la caméra
    for sg, lift in ((-1, 0.0), (1, 1.0)):
        sh = P(0.0, sg*0.47, 1.58)
        el = P(0.12 + 0.25*lift, sg*0.6, 1.18 + 0.22*lift); wr = P(0.32 + 0.35*lift, sg*0.55, 0.9 + 0.48*lift)
        torus_bm(bm, sh, (sh - P(0, 0, 1.58)), 0.14, 0.05)
        for a_, b_, r in ((sh, el, 0.11), (el, wr, 0.095)):
            d = (b_ - a_); n_ = 5
            for k in range(n_):
                q0 = a_ + d*(k/n_); q1 = a_ + d*((k + 1)/n_); tube_bm(bm, q0, q1, r*(1 - 0.03*k), 24)
                torus_bm(bm, q1, d, r + 0.012, 0.018, 32, 8)
        ell_bm(bm, el, (0.13, 0.13, 0.13), R, 20)
        dd = (wr - el).normalized(); side = dd.cross(Vector((0, 0, 1))).normalized()
        for s2 in (-1, 1):                                             # pince à deux mâchoires
            tip = wr + dd*0.24 + side*s2*0.07
            tube_bm(bm, wr + side*s2*0.03, wr + dd*0.12 + side*s2*0.08, 0.025, 12); tube_bm(bm, wr + dd*0.12 + side*s2*0.08, tip, 0.02, 12)
    # jambes et bottes de plomb
    for sg in (-1, 1):
        hip = P(0, sg*0.2, 0.95); kn = P(0.06, sg*0.23, 0.5); an = P(0.0, sg*0.24, 0.13)
        for a_, b_, r in ((hip, kn, 0.13), (kn, an, 0.115)):
            d = b_ - a_
            for k in range(4):
                q0 = a_ + d*(k/4); q1 = a_ + d*((k + 1)/4); tube_bm(bm, q0, q1, r, 24); torus_bm(bm, q1, d, r + 0.012, 0.02, 32, 8)
        ell_bm(bm, kn, (0.15, 0.15, 0.15), R, 20)
        box_bm(bm, P(0.08, sg*0.24, 0.07), (0.2, 0.12, 0.07), R)
    body = mesh_obj('Scaphandre', bm, M['laiton'], True)
    bev = body.modifiers.new('sub', 'SUBSURF'); bev.levels = 1; B.bake_mods(body)
    # casque : sphère de laiton, hublot frontal + deux latéraux + un supérieur
    hc = P(0, 0, 2.06); bm = bmesh.new(); ell_bm(bm, hc, (0.29, 0.29, 0.29), R, 48)
    ports = [(Vector((1, 0, 0.05)), 0.13), (Vector((0, 1, 0)), 0.08), (Vector((0, -1, 0)), 0.08), (Vector((0.35, 0, 1)), 0.07)]
    cutters = []
    for dv, r in ports:
        dw = (R @ dv).normalized(); torus_bm(bm, hc + dw*0.285, dw, r + 0.025, 0.028, 48, 10)
        for k in range(8):
            a = k/8*2*math.pi; t1 = dw.cross(Vector((0, 0, 1))).normalized() if abs(dw.z) < 0.9 else Vector((1, 0, 0)); t2 = dw.cross(t1)
            ell_bm(bm, hc + dw*0.3 + (t1*math.cos(a) + t2*math.sin(a))*(r + 0.04), (0.012, 0.012, 0.012), R, 8)
        cb = bmesh.new(); ell_bm(cb, hc + dw*0.29, (r, r, r), Matrix.Identity(3), 24); cutters.append(mesh_obj('c', cb))
    helmet = mesh_obj('Casque', bm, M['laiton'], True)
    for c_ in cutters:
        m = helmet.modifiers.new('h', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c_; m.solver = 'FAST'
    B.bake_mods(helmet)
    for c_ in cutters: bpy.data.objects.remove(c_)
    bm = bmesh.new()
    for dv, r in ports:
        dw = (R @ dv).normalized(); ell_bm(bm, hc + dw*0.262, (r*1.02, r*1.02, r*1.02), Matrix.Identity(3), 24)
    glass = mesh_obj('Vitres', bm, M['verre_buee'], True)
    # à l'intérieur : des anguilles pâles qui se pressent contre la vitre
    sk = B.Skel()
    for k in range(9):
        pts = []
        for j in range(9):
            t = j/8; a = k*0.7 + t*5.5
            q = hc + R @ Vector((0.1 + 0.12*abs(math.cos(a*0.9 + k)), 0.16*math.sin(a + k*0.3), 0.16*math.cos(a*0.6 + k*1.1)))
            pts.append(q)
        i0 = sk.v(pts[0], 0.022); sk.chain(i0, pts[1:], [0.022*(1 - 0.08*j) for j in range(1, 9)])
    eels = B.skin_object('Anguilles', sk, sub=2); B.bake_mods(eels); B.shade_smooth(eels); eels.data.materials.append(M['anguille'])
    B.light('POINT', tuple(hc), 3, (0.4, 0.9, 0.7), size=0.05, name='LueurCasque')
    return dict(body=body, helmet=helmet, glass=glass, eels=eels, head=hc)
