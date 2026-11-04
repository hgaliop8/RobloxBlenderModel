"""Aperçus de la base Nadir-4 (même géométrie que le fichier Roblox) rendus dans Cycles.
VUES = liste séparée par des virgules (ids de salles ou de couloirs, 'dessus0', 'dessus16', 'dessus28') ; COURANT = 0|1 ; ECH = échantillons."""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)

import nadir_build as NB
try:
    import nadir_props as NP; meub = NP.meubler
except ImportError: meub = None
NB.build_all(meub); items = NB.sc.items
log(f'{len(items)} pièces construites')
COURANT = os.environ.get('COURANT', '0') == '1'
VUES = [v for v in os.environ.get('VUES', 'rotonde').split(',') if v]
ECH = int(os.environ.get('ECH', '64')); RES = tuple(int(x) for x in os.environ.get('RES', '1280x720').split('x'))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = ECH; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 12; sc.cycles.use_adaptive_sampling = True
sc.render.resolution_x, sc.render.resolution_y = RES
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = float(os.environ.get('EXPO', '0.6'))
w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.012, 0.018, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0; sc.world = w
coll = bpy.data.collections.new('Nadir'); sc.collection.children.link(coll)

def mixrgb(nt, fac, a, b, blend='MIX'):
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = blend; mx.inputs[0].default_value = fac
    A = [i for i in mx.inputs if i.name == 'A' and i.type == 'RGBA'][0]; B = [i for i in mx.inputs if i.name == 'B' and i.type == 'RGBA'][0]
    Rr = [o for o in mx.outputs if o.name == 'Result' and o.type == 'RGBA'][0]
    nt.links.new(a, A); nt.links.new(b, B); return Rr
def rbx2bl(v): return Vector((v[0], -v[2], v[1]))
def srgb(c): return tuple(((x/255 + 0.055)/1.055)**2.4 if x/255 > 0.04045 else x/255/12.92 for x in c)

# ---------------------------------------------------------------- matériaux (couleur par sommet)
def mat_for(kind, tr):
    name = f'{kind}_{tr:.2f}'
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; L = nt.links; b = nt.nodes['Principled BSDF']; out_ = nt.nodes['Material Output']
    at = nt.nodes.new('ShaderNodeVertexColor'); at.layer_name = 'col'
    tc = nt.nodes.new('ShaderNodeTexCoord')
    def noise(scale, detail=4):
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; L.new(tc.outputs['Object'], n.inputs['Vector']); return n
    def bump(h, s):
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = s; L.new(h, bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    colin = at.outputs['Color']
    P = dict(SmoothPlastic=(0, 0.42), Plastic=(0, 0.6), Metal=(0.85, 0.38), DiamondPlate=(0.9, 0.32), CorrodedMetal=(0.5, 0.75), Concrete=(0, 0.88),
             Marble=(0, 0.16), Slate=(0, 0.6), Fabric=(0, 0.95), Wood=(0, 0.6), WoodPlanks=(0, 0.55), Granite=(0, 0.5), Brick=(0, 0.9), Sand=(0, 1), Rock=(0, 0.95),
             Foil=(1, 0.2), Ice=(0, 0.05), Glass=(0, 0.02), Neon=(0, 0.5), Pebble=(0, 0.9), Cobblestone=(0, 0.9))
    met, rough = P.get(kind, (0, 0.5)); b.inputs['Metallic'].default_value = met; b.inputs['Roughness'].default_value = rough
    if kind == 'Metal':
        n = noise(14, 6); colin = mixrgb(nt, 0.12, colin, n.outputs['Color']); bump(n.outputs['Fac'], 0.04)
    if kind == 'DiamondPlate':
        wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 3.2; L.new(tc.outputs['Object'], wv.inputs['Vector']); bump(wv.outputs['Fac'], 0.25)
    if kind in ('Concrete', 'Sand', 'Rock', 'CorrodedMetal', 'Slate'):
        n = noise(6 if kind != 'Sand' else 30, 8); bump(n.outputs['Fac'], 0.3)
        colin = mixrgb(nt, 0.25 if kind != 'CorrodedMetal' else 0.6, colin, n.outputs['Color'])
    if kind == 'Marble':
        br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 0.6; br.offset = 0.0; L.new(tc.outputs['Object'], br.inputs['Vector'])
        br.inputs['Mortar Size'].default_value = 0.01; br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (1, 1, 1, 1); br.inputs['Mortar'].default_value = (0.5, 0.5, 0.5, 1)
        colin = mixrgb(nt, 1.0, colin, br.outputs['Color'], 'MULTIPLY')
    if kind in ('Wood', 'WoodPlanks'):
        wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.5; wv.inputs['Distortion'].default_value = 6; L.new(tc.outputs['Object'], wv.inputs['Vector'])
        colin = mixrgb(nt, 0.35, colin, wv.outputs['Color'], 'MULTIPLY')
    if kind == 'Fabric':
        n = noise(80, 2); bump(n.outputs['Fac'], 0.15)
    L.new(colin, b.inputs['Base Color'])
    if kind == 'Neon':
        L.new(at.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 8
    if kind == 'Glass':
        b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.45
    if tr > 0.01:
        tp = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = tr
        L.new(b.outputs[0], mx.inputs[1]); L.new(tp.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out_.inputs['Surface'])
    return m

# ---------------------------------------------------------------- géométrie
CYL = [(math.cos(a*2*math.pi/16), math.sin(a*2*math.pi/16)) for a in range(16)]
def geom(it):
    sx, sy, sz = it['s']; k = it['cls']; sh = it.get('shape')
    if sh == 'Cylinder':
        d = min(sy, sz)/2; V = []
        for x in (-sx/2, sx/2):
            for c, s in CYL: V.append((x, c*d, s*d))
        F = [tuple(range(16))[::-1], tuple(range(16, 32))] + [(i, (i + 1) % 16, 16 + (i + 1) % 16, 16 + i) for i in range(16)]
        return V, F
    if sh == 'Ball':
        V = []; F = []; nu, nv = 12, 8; r = sx/2
        for j in range(nv + 1):
            t = math.pi*j/nv
            for i in range(nu): a = 2*math.pi*i/nu; V.append((r*math.sin(t)*math.cos(a), r*math.cos(t), r*math.sin(t)*math.sin(a)))
        for j in range(nv):
            for i in range(nu): F.append((j*nu + i, j*nu + (i + 1) % nu, (j + 1)*nu + (i + 1) % nu, (j + 1)*nu + i))
        return V, F
    if k == 'WedgePart':
        V = [(-sx/2, -sy/2, -sz/2), (sx/2, -sy/2, -sz/2), (sx/2, -sy/2, sz/2), (-sx/2, -sy/2, sz/2), (-sx/2, sy/2, sz/2), (sx/2, sy/2, sz/2)]
        F = [(0, 1, 2, 3), (3, 2, 5, 4), (0, 4, 5, 1), (0, 3, 4), (1, 5, 2)]
        return V, F
    V = [(x*sx/2, y*sy/2, z*sz/2) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return V, F

HIDE_TOP = ('Plafond', 'GaineDessus', 'GaineFond', 'GaineParoi', 'Verriere', 'Retombee', 'CadreGrille', 'Lame', 'Soudure', 'Plafonnier', 'CadrePlafonnier',
            'Arche', 'Gousset', 'Tuyau', 'Collier', 'ChemindeCables', 'Cable', 'EmetteurNeige', 'Corniche')
def build(filter_fn):
    for o in list(coll.objects): bpy.data.objects.remove(o)
    groups = {}
    for it in items:
        if it['t'] >= 0.99 or not filter_fn(it): continue
        groups.setdefault((it['m'], round(it['t'], 2)), []).append(it)
    for (m, tr), lst in groups.items():
        bm = bmesh.new(); colL = bm.loops.layers.color.new('col')
        for it in lst:
            V, F = geom(it); R = it['R']; p = it['p']
            vs = [bm.verts.new(rbx2bl((p[0] + R[0][0]*x + R[0][1]*y + R[0][2]*z, p[1] + R[1][0]*x + R[1][1]*y + R[1][2]*z, p[2] + R[2][0]*x + R[2][1]*y + R[2][2]*z))) for x, y, z in V]
            c = (*srgb(it['c']), 1.0)
            for f in F:
                try: fa = bm.faces.new([vs[i] for i in f])
                except ValueError: continue
                for l in fa.loops: l[colL] = c
        me = bpy.data.meshes.new(f'{m}_{tr}'); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob); me.materials.append(mat_for(m, tr))
    # lumières
    for it in items:
        if not filter_fn(it): continue
        for L in [c for c in it['ch'] if c['cls'] in ('PointLight', 'SurfaceLight', 'SpotLight')]:
            if not L['Enabled'] and not (COURANT and 'LumiereNormale' in it['tags']): continue
            col = srgb(L['Color']); b = L['Brightness']; rg = L['Range']
            if COURANT and 'LumiereSecours' in it['tags']: b *= 0.3
            pos = rbx2bl(it['p'])
            if L['cls'] == 'PointLight':
                ld = bpy.data.lights.new('P', 'POINT'); ld.energy = b*55*(rg/16)**2; ld.shadow_soft_size = 0.2
            else:
                ld = bpy.data.lights.new('A', 'AREA'); ld.energy = b*75*(rg/16)**2; ld.size = max(it['s'][0], it['s'][2]); ld.size_y = min(it['s'][0], it['s'][2]); ld.shape = 'RECTANGLE'
                if abs(it['s'][0]) < abs(it['s'][2]): ld.size, ld.size_y = ld.size_y, ld.size
            ld.color = col; ob = bpy.data.objects.new('L', ld); coll.objects.link(ob); ob.location = pos - Vector((0, 0, 0.2)) if L['cls'] != 'PointLight' else pos
    log('scène Blender prête')

def cam(name, eye, tgt, lens=20, ortho=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.1; cd.clip_end = 3000
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd); sc.collection.objects.link(ob); ob.location = eye
    ob.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler(); return ob

def vue_espace(eid):
    e = NB.BYID[eid]; W, D = e.X1 - e.X0, e.Z1 - e.Z0
    y = e.elev + min(5.5, e.h*0.45)
    if e.couloir and not e.d.get('forme'):
        if W >= D: eye = (e.X0 + 6, y, (e.Z0 + e.Z1)/2 + 0.8); tgt = (e.X1, y - 0.6, (e.Z0 + e.Z1)/2)
        else: eye = ((e.X0 + e.X1)/2 + 0.8, y, e.Z1 - 6); tgt = ((e.X0 + e.X1)/2, y - 0.6, e.Z0)
        if e.esc: eye = ((e.X0 + e.X1)/2 + 0.6, e.ymax - 3, e.Z0 + 4); tgt = ((e.X0 + e.X1)/2, e.ymin + 2, e.Z1)
    else:
        eye = (e.X0 + 2.2, y, e.Z1 - 2.2); tgt = (e.X1 - 3, e.elev + 2.2, e.Z0 + 3)
    return rbx2bl(eye), rbx2bl(tgt)

for v in VUES:
    if v.startswith('dessus'):
        lvl = -int(v[6:]) if v[6:] else 0
        lo, hi = lvl - 2, lvl + 14
        build(lambda it, lo=lo, hi=hi: lo - 1 <= it['p'][1] <= hi and not any(it['n'].startswith(h) for h in HIDE_TOP) and it['f'] != 'Nadir4/Gaines')
        xs = [p for e in NB.ESP if lo - 1 <= e.elev <= hi for p in (e.X0, e.X1)]; zs = [p for e in NB.ESP if lo - 1 <= e.elev <= hi for p in (e.Z0, e.Z1)]
        cx, cz = (min(xs) + max(xs))/2, (min(zs) + max(zs))/2; span = max(max(xs) - min(xs), (max(zs) - min(zs))*16/9)*1.03
        sun = bpy.data.lights.new('S', 'SUN'); sun.energy = 3.5; so = bpy.data.objects.new('S', sun); coll.objects.link(so); so.rotation_euler = (0.5, 0.2, 0.3)
        c = cam('dessus', rbx2bl((cx, hi + 300, cz)), rbx2bl((cx, lo, cz + 0.001)), ortho=span)
        c.rotation_euler = (0, 0, 0)
    else:
        e = NB.BYID[v]
        build(lambda it, e=e: (e.X0 - 70 <= it['p'][0] <= e.X1 + 70 and e.Z0 - 70 <= it['p'][2] <= e.Z1 + 70 and e.ymin - 30 <= it['p'][1] <= e.ymax + 30))
        eye, tgt = vue_espace(v); c = cam(v, eye, tgt, lens=16 if not e.couloir else 18)
    sc.camera = c; sc.render.filepath = os.path.join(out, f'{v}.png'); bpy.ops.render.render(write_still=True)
    log(f'rendu {v}')
log('fin')
