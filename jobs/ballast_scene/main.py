"""Ballast — scène complète sous Blender : l'amas sous le wagon, trois bras (grille, fenêtre, toilettes), décor.
Rendus Cycles des six vues de la visionneuse + gros plan de l'amas."""
import bpy, sys, os, time, math
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
import ballast_scene as S
from mathutils import Vector

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(msg): logf.write(f'{time.time() - T0:7.1f}s  {msg}\n'); logf.flush(); print('>>', msg, flush=True)
ONLY = os.environ.get('VUES', '').split(',') if os.environ.get('VUES') else None
bpy.ops.wm.read_factory_settings(use_empty=True)

M = S.materiaux()
amas, levres, fond, ongles, cailloux, tirefonds, dents = S.amas(log=log)
dents.data.materials.append(M['dents'])
for o in (amas, levres): o.data.materials.append(M['chair'])
fond.data.materials.append(M['gorge']); ongles.data.materials.append(M['ongle'])
cailloux.data.materials.append(M['caillou']); tirefonds.data.materials.append(M['rouille'])
for n, seed in (('BrasGrille', 1), ('BrasFenetre', 2), ('BrasToilettes', 3)):
    b, o = S.bras_scene(n, seed, log=log); b.data.materials.append(M['chair']); o.data.materials.append(M['ongle'])
S.wagon(M, log=log); S.voie(M, log=log)

# ------------------------------------------------------------------ lumières
sc = B.setup_render((1600, 900), samples=160, exposure=0.0)
sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8
B.world((0.0015, 0.002, 0.0035))
neon = B.light('AREA', (0.35, 0.55, 3.24), 90, (0.72, 0.92, 0.85), size=1.2, target=(0.35, 0.55, 0), name='Neon')
neon.data.shape = 'RECTANGLE'; neon.data.size = 1.2; neon.data.size_y = 0.12
sun = bpy.data.lights.new('Lune', 'SUN'); sun.energy = 0.55; sun.color = (0.55, 0.66, 1.0); sun.angle = math.radians(1.5)
so = bpy.data.objects.new('Lune', sun); B.coll().objects.link(so)
so.rotation_euler = Vector((-0.25, -0.72, -0.6)).to_track_quat('-Z', 'Y').to_euler()
B.light('AREA', (0.2, -3.2, 0.55), 18, (0.4, 0.5, 0.85), size=2.5, target=(0.0, 0, 0.6), name='Contre')
lampe = B.light('SPOT', (0, -5, 2), 120, (1.0, 0.87, 0.7), size=0.03, name='Lampe', spot=0.75)

VUES = [
    ('ensemble', (1.36, -8.05, 1.84), (-0.1, 0.0, 1.35), 28),
    ('amas', (0.55, -1.75, 0.5), (0.1, -0.3, 0.74), 30),
    ('bouche', tuple(S.MO + S.MN*0.85 + Vector((0.12, 0, -0.06))), tuple(S.MO - S.MN*0.12), 42),
    ('gorge', tuple(S.MO + S.MN*0.42 + Vector((0.03, 0, 0.02))), tuple(S.MO - S.MN*0.3), 30),
    ('grille', (2.9, -2.7, 1.95), (1.35, -0.55, 1.6), 30),
    ('fenetre', (-0.69, -1.58, 2.17), (0.75, 1.05, 2.05), 28),
    ('dehors', (1.91, 5.67, 1.96), (0.4, 1.55, 1.7), 28),
    ('toilettes', (-1.21, -1.83, 2.13), (-2.3, 0.6, 1.65), 28),
    ('dessous', (-0.97, -3.65, 0.47), (0.05, -0.1, 0.62), 28),
]
log('scène prête')
for name, eye, tgt, lens in VUES:
    if ONLY and name not in ONLY: continue
    cam = B.camera(eye, tgt, lens, name)
    e = Vector(eye); t = Vector(tgt); lampe.location = e + Vector((0.15, 0, 0.25)) + (t - e).normalized()*0.2
    lampe.rotation_euler = (t - lampe.location).to_track_quat('-Z', 'Y').to_euler()
    plafond = bpy.data.objects.get('Plafond'); vis = eye[2] < 3.3 and abs(eye[1]) < 6
    B.render(os.path.join(out, f'{name}.png'), cam)
    log(f'rendu {name}')
log('fin')
