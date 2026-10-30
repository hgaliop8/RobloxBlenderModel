"""VITRELLE — poulpe de verre géant (inspiré de Vitreledonella richardi), échappé de son bassin dans la base sous-marine.
Corps presque invisible : on voit les yeux tubulaires et leur reflet, les organes (glande digestive, trois cœurs, branchies,
cerveau, nerfs optiques), les ventouses laiteuses, et des photophores le long des bras.
Construit dans un repère « sol » local (Z en haut, le poulpe posé à plat) ; pose 'plafond' : enroulé sur le plafond
cylindrique d'une coursive par une simple transformation des sommets."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
import ballast_bl as B
from abysse import mesh_obj, xf_verts, tube_bm, ell_bm, box_bm

UP = Vector((0, 0, 1))
CROWN = Vector((0.05, 0.0, 0.13))
EYE_BASE = {s: Vector((0.06, s*0.17, 0.42)) for s in (-1, 1)}
EYE_AX = {s: Vector((0.25, s*0.8, 0.55)).normalized() for s in (-1, 1)}
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
            alt = 1.45*min(1, max(0, (s - 0.35)/1.0))
            al = alt if s < tip0 else alt + (s - tip0)/(L - tip0)*2.8              # crochet par-dessus
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
        A, Bc = arms[k][0], arms[(k + 1) % 8][0]; nu, nv = 16, 10; grid = []
        for iu in range(nu + 1):
            row = []
            for iv in range(nv + 1):
                v = iv/nv; smax = 0.55*(1 - 0.55*math.sin(math.pi*v)); s = smax*iu/nu; j = int(s/0.022)
                p = A[min(j, len(A) - 1)].lerp(Bc[min(j, len(Bc) - 1)], v) + UP*(0.025*math.sin(math.pi*v))
                row.append(bm.verts.new(p))
            grid.append(row)
        for iu in range(nu):
            for iv in range(nv): bm.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
    web = mesh_obj('palmure', bm); so = web.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.014; so.offset = 0; B.bake_mods(web); skin.append(web)
    # corps : couronne, tête, cou, manteau, yeux tubulaires, entonnoir
    bm = bmesh.new()
    ell_bm(bm, CROWN, (0.21, 0.21, 0.1))
    ell_bm(bm, Vector((0.02, 0, 0.34)), (0.25, 0.3, 0.22))
    ell_bm(bm, Vector((-0.12, 0, 0.45)), (0.25, 0.28, 0.24))
    ell_bm(bm, MANTLE_C, (0.56, 0.37, 0.34), B.frame(MANTLE_AX, UP).to_3x3(), 48)
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]
        tube_bm(bm, b0, b0 + e*0.12, 0.068, 32)
        ell_bm(bm, b0 + e*0.12, (0.07, 0.07, 0.07))
    tube_bm(bm, Vector((-0.04, -0.24, 0.24)), Vector((0.06, -0.33, 0.17)), 0.04, 20)
    skin.append(mesh_obj('corps', bm))
    for o in skin: B.bake_mods(o)
    body = B.remesh(B.join(skin, 'Vitrelle'), voxel=0.0042, smooth=3)
    B.displace(body, 'CLOUDS', 0.12, 0.004, 2, name='vit_plis'); B.displace(body, 'VORONOI', 0.012, 0.0007, name='vit_grain')
    B.bake_mods(body); B.shade_smooth(body)
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
    # yeux : cristallin, pupille en fente horizontale, tapis réfléchissant (reflet dans la lampe)
    bml, bmp, bmt = bmesh.new(), bmesh.new(), bmesh.new()
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]; Re = B.frame(e, UP).to_3x3()
        ell_bm(bml, b0 + e*0.118, (0.042, 0.042, 0.042), Re)
        box_bm(bmp, b0 + e*0.158, (0.003, 0.034, 0.0055), Re)
        ell_bm(bmt, b0 + e*0.05, (0.045, 0.058, 0.058), Re)
    parts['cristallins'] = mesh_obj('Cristallins', bml, smooth=True); parts['pupilles'] = mesh_obj('Pupilles', bmp)
    parts['tapis'] = mesh_obj('TapisOeil', bmt, smooth=True)
    # organes visibles par transparence
    bm_g, bm_h, bm_b, bm_n, bm_br = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    Rm = B.frame(MANTLE_AX, UP).to_3x3()
    ell_bm(bm_g, MANTLE_C + MANTLE_AX*0.06 - UP*0.02, (0.21, 0.075, 0.07), Rm)                 # glande digestive
    ell_bm(bm_h, Vector((-0.17, 0, 0.5)), (0.038, 0.034, 0.034))                                # cœur systémique
    for sg in (-1, 1):
        ell_bm(bm_h, Vector((-0.22, sg*0.1, 0.47)), (0.026, 0.026, 0.026))                        # cœurs branchiaux
        a, b_ = Vector((-0.12, sg*0.16, 0.45)), Vector((-0.45, sg*0.21, 0.64))
        for j in range(20):                                                                        # branchies plumeuses
            t = j/19; c = a.lerp(b_, t); ell_bm(bm_br, c, (0.004, 0.032*(1 - 0.5*abs(t - 0.4)), 0.022), B.frame((b_ - a).normalized(), UP).to_3x3(), 10)
        tube_bm(bm_n, EYE_BASE[sg], Vector((0.0, sg*0.05, 0.42)), 0.012, 10)                       # nerfs optiques
    ell_bm(bm_n, Vector((0.0, 0, 0.42)), (0.07, 0.1, 0.055))                                       # cerveau
    pts = [CROWN + Vector((0, 0, -0.04)), Vector((0.02, 0, 0.3)), Vector((-0.05, 0, 0.44)), MANTLE_C + MANTLE_AX*0.15]
    for a, b_ in zip(pts[:-1], pts[1:]): tube_bm(bm_n, a, b_, 0.011, 10)                           # œsophage
    parts['glande'] = mesh_obj('Glande', bm_g, smooth=True); parts['coeurs'] = mesh_obj('Coeurs', bm_h, smooth=True)
    parts['branchies'] = mesh_obj('Branchies', bm_br, smooth=True); parts['nerfs'] = mesh_obj('Nerfs', bm_n, smooth=True)
    # ce qu'il a avalé : un badge d'accès du personnel, pris dans la glande
    bm = bmesh.new(); box_bm(bm, MANTLE_C + MANTLE_AX*0.0 + Vector((0, 0.02, -0.01)), (0.042, 0.027, 0.0018), Rm @ Matrix.Rotation(0.5, 3, 'X'))
    parts['badge'] = mesh_obj('Badge', bm)
    # bec
    bm = bmesh.new()
    for sg in (-1, 1):
        o = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.035, radius2=0.004, depth=0.07)
        xf_verts(o['verts'], Matrix.Translation(CROWN + Vector((0.02*sg, 0, -0.07))) @ Vector((0.3*sg, 0, -1)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    parts['bec'] = mesh_obj('Bec', bm, smooth=True)
    # photophores : rangée dorsale le long des bras, couronne autour des yeux, deux lignes sur le manteau
    bm_v, bm_r = bmesh.new(), bmesh.new()
    for ai, (P, L) in enumerate(arms):
        T, N = rmf(P); s = 0.25; j = 0
        while s < L - 0.15:
            i = int(s/0.022); r = rad_at(s, L)
            ell_bm(bm_r if (j % 5 == 4) else bm_v, P[i] + N[i]*r*0.9, (0.005 + r*0.12,)*3, Matrix.Identity(3), 8)
            s += 0.11; j += 1
    for sg in (-1, 1):
        b0 = EYE_BASE[sg]; e = EYE_AX[sg]; t1 = e.cross(UP).normalized(); t2 = e.cross(t1)
        for k in range(10):
            a = k/10*2*math.pi; ell_bm(bm_v, b0 + e*0.06 + (t1*math.cos(a) + t2*math.sin(a))*0.078, (0.007,)*3, Matrix.Identity(3), 8)
        for j in range(9):
            t = j/8; c = MANTLE_C + MANTLE_AX*(0.45 - 0.9*t) + Vector((0, sg*0.2*(1 - 0.5*abs(t - 0.5)), 0.24*(1 - (2*t - 1)**2) + 0.05))
            ell_bm(bm_v, c, (0.009,)*3, Matrix.Identity(3), 8)
    parts['photo_v'] = mesh_obj('PhotophoresV', bm_v, smooth=True); parts['photo_r'] = mesh_obj('PhotophoresR', bm_r, smooth=True)
    return parts

# ================================================================ matériaux
def mats():
    M = {}
    M['peau'] = _verre_vivant('PeauVerre', density=1.2, spots=True)
    M['ventouse'] = _verre_vivant('Ventouse', density=6.0, milk=0.55, spots=False)
    m = bpy.data.materials.new('Cristallin'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.95, 0.97, 1, 1); b.inputs['Roughness'].default_value = 0.0; b.inputs['Transmission Weight'].default_value = 1; b.inputs['IOR'].default_value = 1.6
    M['cristallin'] = m
    M['pupille'] = B.mat_simple('Pupille', (0.002, 0.002, 0.003), 0.2)
    m = bpy.data.materials.new('Tapis'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.55, 0.75, 0.35, 1); b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.18
    b.inputs['Emission Color'].default_value = (0.5, 0.95, 0.45, 1); b.inputs['Emission Strength'].default_value = 0.6
    M['tapis'] = m
    M['glande'] = _organe('Glande', (0.1, 0.035, 0.025), 0.0)
    M['coeur'] = _organe('Coeur', (0.35, 0.03, 0.04), 1.2, (1.0, 0.1, 0.1))
    M['branchie'] = _organe('Branchie', (0.5, 0.25, 0.28), 0.0)
    M['nerf'] = _organe('Nerf', (0.6, 0.55, 0.5), 0.0)
    M['badge'] = B.mat_simple('Badge', (0.7, 0.68, 0.62), 0.4)
    M['bec'] = B.mat_simple('Bec', (0.015, 0.01, 0.008), 0.25)
    M['photo_v'] = _emi('PhotoV', (0.3, 1.0, 0.75), 10)
    M['photo_r'] = _emi('PhotoR', (1.0, 0.15, 0.08), 8)
    return M

def _emi(name, col, s):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1); b.inputs['Emission Color'].default_value = (*col, 1); b.inputs['Emission Strength'].default_value = s
    b.inputs['Transmission Weight'].default_value = 0.5; b.inputs['Roughness'].default_value = 0.1
    return m

def _organe(name, col, emi, ecol=(1, 0.2, 0.2)):
    m = B.mat_simple(name, col, 0.45, noise_scale=60, noise_col=tuple(c*0.5 for c in col), bump=0.3); b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Subsurface Weight'].default_value = 0.4; b.inputs['Subsurface Radius'].default_value = (1, 0.3, 0.2); b.inputs['Subsurface Scale'].default_value = 0.01
    if emi: b.inputs['Emission Color'].default_value = (*ecol, 1); b.inputs['Emission Strength'].default_value = emi
    return m

def _verre_vivant(name, density=1.2, milk=0.12, spots=True):
    """chair de verre : transmission, film mince irisé, gel légèrement laiteux à l'intérieur, chromatophores épars"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; L = nt.links
    out = nt.nodes['Material Output']; g = nt.nodes['Principled BSDF']
    g.inputs['Base Color'].default_value = (0.9, 0.95, 0.97, 1); g.inputs['Roughness'].default_value = 0.07; g.inputs['IOR'].default_value = 1.35
    g.inputs['Transmission Weight'].default_value = 1.0; g.inputs['Coat Weight'].default_value = 0.25; g.inputs['Coat Roughness'].default_value = 0.03
    if 'Thin Film Thickness' in g.inputs: g.inputs['Thin Film Thickness'].default_value = 320.0; g.inputs['Thin Film IOR'].default_value = 1.38
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 90; nz.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.05; L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], g.inputs['Normal'])
    surf = g.outputs[0]
    if spots:
        vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 55; L.new(tc.outputs['Object'], vo.inputs['Vector'])
        rr = B.ramp(nt, (0, 0), [(0.0, (1, 1, 1, 1)), (0.12, (0, 0, 0, 1))]); L.new(vo.outputs['Distance'], rr.inputs[0])
        ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 3; L.new(tc.outputs['Object'], ns.inputs['Vector'])
        rm = B.ramp(nt, (0, -200), [(0.5, (0, 0, 0, 1)), (0.7, (0.8, 0.8, 0.8, 1))]); L.new(ns.outputs['Fac'], rm.inputs[0])
        mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(rr.outputs['Color'], mm.inputs[0]); L.new(rm.outputs['Color'], mm.inputs[1])
        d = nt.nodes.new('ShaderNodeBsdfPrincipled'); d.inputs['Base Color'].default_value = (0.25, 0.06, 0.04, 1); d.inputs['Roughness'].default_value = 0.4
        mix = nt.nodes.new('ShaderNodeMixShader'); L.new(mm.outputs[0], mix.inputs[0]); L.new(surf, mix.inputs[1]); L.new(d.outputs[0], mix.inputs[2]); surf = mix.outputs[0]
    L.new(surf, out.inputs['Surface'])
    va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.88, 0.95, 0.97, 1); va.inputs['Density'].default_value = density
    vs = nt.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Color'].default_value = (0.9, 0.95, 1, 1); vs.inputs['Density'].default_value = milk; vs.inputs['Anisotropy'].default_value = 0.4
    av = nt.nodes.new('ShaderNodeAddShader'); L.new(va.outputs[0], av.inputs[0]); L.new(vs.outputs[0], av.inputs[1]); L.new(av.outputs[0], out.inputs['Volume'])
    return m

def assign(parts, M):
    pairs = dict(peau='peau', ventouses='ventouse', pores='glande', cristallins='cristallin', pupilles='pupille', tapis='tapis', glande='glande',
                 coeurs='coeur', branchies='branchie', nerfs='nerf', badge='badge', bec='bec', photo_v='photo_v', photo_r='photo_r')
    for k, o in parts.items(): o.data.materials.clear(); o.data.materials.append(M[pairs[k]])

# ================================================================ poses
def wrap_ceiling(parts, R=1.5, x0=3.5, gap=0.02):
    """enroule le poulpe (repère sol) sur le plafond cylindrique d'une coursive d'axe X : le sol local devient le plafond"""
    for o in parts.values():
        me = o.data
        for v in me.vertices:
            x, y, h = v.co
            th = -y/R; r = R - gap - h      # rotation de 180° autour de X (pas de miroir)
            v.co = Vector((x0 + x, r*math.sin(th), r*math.cos(th)))
        me.update()
