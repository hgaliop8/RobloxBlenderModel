"""Ballast — cuisson pour la visionneuse et Roblox : maillages légers + textures (couleur, normales, rugosité)
cuites depuis les modèles détaillés Blender. Sorties : <piece>.npz (maillage) et <piece>_{Couleur,Normale,Rugosite}.png"""
import bpy, sys, os, time, math
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
import ballast_scene as S

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(msg): logf.write(f'{time.time() - T0:7.1f}s  {msg}\n'); logf.flush(); print('>>', msg, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = B.setup_render((64, 64), samples=12)
sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = 0.02; sc.render.bake.max_ray_distance = 0.06; sc.render.bake.margin = 12
M = S.materiaux()

def dup(o):
    c = o.copy(); c.data = o.data.copy(); B.coll().objects.link(c); c.modifiers.clear(); return c

def low_from(objs, name, voxel, target):
    lo = B.join([dup(o) for o in objs], name)
    lo = B.remesh(lo, voxel=voxel, smooth=2)
    n = len(lo.data.polygons)
    if n > target:
        d = lo.modifiers.new('dec', 'DECIMATE'); d.ratio = target/n; d.use_collapse_triangulate = True
    lo.modifiers.new('tri', 'TRIANGULATE'); B.bake_mods(lo); B.shade_smooth(lo)
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.0025, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    log(f'{name} : {len(lo.data.polygons)} triangles')
    return lo

def low_import(name):
    """maillage léger déplié dans le pipeline maison (data/ballast/<nom>_uv.npz), normales lisses imposées"""
    d = np.load(os.path.join(os.getcwd(), 'data', 'ballast', f'{name}_uv.npz'))
    me = bpy.data.meshes.new(name + '_bas'); me.from_pydata(d['V'].tolist(), [], d['F'].tolist()); me.update()
    uv = me.uv_layers.new(name='UV'); uv.data.foreach_set('uv', d['UV'][d['F']].reshape(-1))
    for p in me.polygons: p.use_smooth = True
    me.normals_split_custom_set_from_vertices(d['N'].tolist())
    ob = bpy.data.objects.new(name + '_bas', me); B.coll().objects.link(ob)
    log(f'{name} léger importé : {len(me.polygons)} triangles'); return ob

def bake(lo, highs, name, size):
    imgs = {}
    mat = bpy.data.materials.new('cuisson_' + name); mat.use_nodes = True; nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tex
    lo.data.materials.clear(); lo.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    for h in highs: h.select_set(True)
    lo.select_set(True); bpy.context.view_layer.objects.active = lo
    for key, typ, kw, col, smp in (('Couleur', 'DIFFUSE', dict(pass_filter={'COLOR'}), 'sRGB', 12), ('Normale', 'NORMAL', dict(normal_space='TANGENT'), 'Non-Color', 1),
                                   ('Rugosite', 'ROUGHNESS', {}, 'Non-Color', 4)):
        img = bpy.data.images.new(f'{name}_{key}', size, size); img.colorspace_settings.name = col
        tex.image = img; nt.nodes.active = tex; sc.cycles.samples = smp
        bpy.ops.object.bake(type=typ, **kw)
        img.filepath_raw = os.path.join(out, f'{name}_{key}.png'); img.file_format = 'PNG'; img.save()
        log(f'  cuit {name} {key}')

def export_npz(lo, name):
    me = lo.data; uvn = me.uv_layers.active.name; me.calc_tangents(uvmap=uvn)
    nl = len(me.loops)
    vi = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', vi)
    N = np.zeros(nl*3, np.float32)
    if hasattr(me, 'corner_normals'): me.corner_normals.foreach_get('vector', N)
    else: me.loops.foreach_get('normal', N)
    T = np.zeros(nl*3, np.float32); me.loops.foreach_get('tangent', T)
    Ws = np.zeros(nl, np.float32); me.loops.foreach_get('bitangent_sign', Ws)
    UV = np.zeros(nl*2, np.float32); me.uv_layers.active.data.foreach_get('uv', UV)
    P = np.zeros(len(me.vertices)*3, np.float32); me.vertices.foreach_get('co', P)
    P = P.reshape(-1, 3); N = N.reshape(-1, 3); T = T.reshape(-1, 3); UV = UV.reshape(-1, 2)
    key = np.concatenate([vi[:, None].astype(np.float64), np.round(UV*65535), np.round(N*127)], 1)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    np.savez_compressed(os.path.join(out, f'{name}.npz'), V=P[vi[first]], N=N[first], T=T[first], W=Ws[first], UV=UV[first], F=inv.reshape(-1, 3).astype(np.int32))
    log(f'  exporté {name} : {len(first)} sommets, {nl//3} triangles')

# ------------------------------------------------------------------ l'amas
amas, levres, fond, ongles, cailloux, tirefonds = S.amas(log=log)
for o in (amas, levres): o.data.materials.append(M['chair'])
fond.data.materials.append(M['gorge']); ongles.data.materials.append(M['ongle'])
cailloux.data.materials.append(M['caillou']); tirefonds.data.materials.append(M['rouille'])
lo = low_import('Amas')
bake(lo, [amas, levres, fond, ongles, cailloux, tirefonds], 'Amas', 4096)
export_npz(lo, 'Amas')
for o in (amas, levres, fond, ongles, cailloux, tirefonds, lo): bpy.data.objects.remove(o)

# ------------------------------------------------------------------ les bras, modélisés droits
for name, seed in (('BrasGrille', 1), ('BrasFenetre', 2), ('BrasToilettes', 3)):
    hi, nails = S.bras_scene(name, seed, log=log, droit=True)
    hi.data.materials.append(M['chair']); nails.data.materials.append(M['ongle'])
    lo = low_import(name)
    bake(lo, [hi, nails], name, 2048)
    export_npz(lo, name)
    for o in (hi, nails, lo): bpy.data.objects.remove(o)
log('fin')
