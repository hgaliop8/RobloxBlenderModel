"""Ballast — essai Blender : un bras-chaîne qui sort d'une grille d'aération du plancher et tend sa main.
Rendus Cycles : plan large + gros plan de la main. Export GLB du bras pour contrôle."""
import bpy, sys, os, time, math
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
from mathutils import Vector, Matrix

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); log = open(os.path.join(out, 'etapes.txt'), 'w')
def step(msg): log.write(f'{time.time() - T0:7.1f}s  {msg}\n'); log.flush(); print('>>', msg, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# ------------------------------------------------------------------ le bras
path = B.Path([(0.05, -0.15, -0.95), (0.0, -0.02, -0.45), (0.0, 0.0, -0.02), (0.03, 0.0, 0.42), (0.14, 0.02, 0.82),
               (0.42, 0.04, 1.04), (0.72, 0.02, 0.98), (0.9, 0.0, 0.8)])
parts, NL = B.arm_chain(path, r_start=0.05, r_end=0.043, seed=1, up=(0, 0, 1), hand_scale=1.45, hand_kw=dict(curl=0.3, spread=0.65))
step(f'squelettes : {len(parts)} objets, chemin {path.L:.2f} m')
for p in parts: B.bake_mods(p)
arm = B.join(parts, 'Bras')
step(f'skin + subsurf : {len(arm.data.vertices)} sommets')
arm = B.remesh(arm, voxel=0.0026, smooth=3)
step(f'remaillage voxel : {len(arm.data.vertices)} sommets')
B.displace(arm, 'CLOUDS', 0.09, 0.006, 2, name='bosses')
B.displace(arm, 'CLOUDS', 0.018, 0.0015, 1, name='peau')
B.bake_mods(arm); B.shade_smooth(arm)
step(f'déplacements appliqués : {len(arm.data.polygons)} faces')
nails = B.nails_from(NL, 'Ongles')
chair = B.mat_chair('Chair', grime=0.75); arm.data.materials.append(chair)
nails.data.materials.append(B.mat_ongle())

# ------------------------------------------------------------------ plancher et grille
def box(name, c, h, mat):
    bpy.ops.mesh.primitive_cube_add(location=c); o = bpy.context.object; o.name = name; o.scale = h
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(mat)
    for col in o.users_collection: col.objects.unlink(o)
    B.coll().objects.link(o); return o
lino = B.mat_simple('Lino', (0.06, 0.065, 0.07), 0.55, noise_scale=6, noise_col=(0.025, 0.025, 0.025), bump=0.05)
acier = B.mat_simple('Acier', (0.45, 0.46, 0.47), 0.38, 0.9, noise_scale=30, noise_col=(0.12, 0.1, 0.08), bump=0.1)
# plancher troué autour de la grille (0.5 x 0.24)
for c, h in (((-1.6, 0, -0.05), (1.35, 1.5, 0.05)), ((1.6, 0, -0.05), (1.35, 1.5, 0.05)), ((0, 0.86, -0.05), (0.25, 0.74, 0.05)), ((0, -0.86, -0.05), (0.25, 0.74, 0.05))):
    box('Plancher', c, h, lino)
for k in range(9):
    y = -0.11 + k*0.0275
    if k in (4, 5):   # lames arrachées, tordues vers le haut
        o = box('LameTordue', (0.0, y, 0.0), (0.25, 0.006, 0.0035), acier)
        o.rotation_euler = (0, -0.9 + 0.25*(k - 4), 0.15*(k - 4.5)); o.location = (-0.33, y + 0.02*(k - 4.5), 0.17); continue
    box('Lame', (0, y, 0.002), (0.25, 0.0055, 0.004), acier)
box('Cadre', (0, 0.135, 0.004), (0.27, 0.012, 0.006), acier); box('Cadre', (0, -0.135, 0.004), (0.27, 0.012, 0.006), acier)
box('Cadre', (0.26, 0, 0.004), (0.012, 0.135, 0.006), acier); box('Cadre', (-0.26, 0, 0.004), (0.012, 0.135, 0.006), acier)
# paroi du fond et banquette sombre
mur = B.mat_simple('Mur', (0.2, 0.24, 0.22), 0.6, noise_scale=3, noise_col=(0.06, 0.07, 0.06))
box('Mur', (0, 1.6, 1.2), (3, 0.05, 1.3), mur)
siege = B.mat_simple('Moquette', (0.12, 0.05, 0.045), 0.95, noise_scale=40, noise_col=(0.05, 0.025, 0.02), bump=0.15)
box('Assise', (1.2, 1.1, 0.48), (0.5, 0.25, 0.07), siege); box('Dossier', (1.2, 1.36, 0.9), (0.5, 0.07, 0.4), siege)
step('décor')

# ------------------------------------------------------------------ lumière et caméras
sc = B.setup_render((1280, 720), samples=160, exposure=0.3)
B.world((0.002, 0.0025, 0.004))
B.light('AREA', (0.5, 0.4, 2.3), 140, (0.75, 0.9, 0.85), size=1.4, target=(0.4, 0.1, 0), name='Neon')
B.light('SPOT', (2.4, -2.6, 1.5), 260, (1.0, 0.86, 0.68), size=0.05, target=(0.5, 0, 0.75), name='Lampe', spot=0.5)
B.light('AREA', (-1.2, 1.2, 1.4), 60, (0.35, 0.45, 0.9), size=1.0, target=(0.3, 0, 0.6), name='Contre')
wide = B.camera((2.3, -2.5, 1.35), (0.38, 0.05, 0.55), 35, 'Large')
hand_tip, _ = path.at(path.L)
close = B.camera((1.35, -0.95, 1.12), (0.82, 0.0, 0.84), 70, 'Gros')
step('rendu large…')
B.render(os.path.join(out, 'large.png'), wide)
step('rendu gros plan…')
B.render(os.path.join(out, 'main.png'), close)
step('rendus faits')

# ------------------------------------------------------------------ export de contrôle
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); nails.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=os.path.join(out, 'bras.glb'), use_selection=True, export_apply=True)
step(f'fin, {len(arm.data.polygons)} faces pour le bras')
