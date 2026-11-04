"""Salle témoin : Quartiers A modélisés (vrais objets 3D + textures PBR), rendus Cycles.
COURANT = 1 (éclairage normal) | 0 (secours + lampe torche). VUES = liste de vues."""
import bpy, sys, os, math, time, random
from mathutils import Vector
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
import kit_meshes as K
import kit_quartiers as Q
COURANT = os.environ.get('COURANT', '1') == '1'
ECH = int(os.environ.get('ECH', '128')); RES = tuple(int(x) for x in os.environ.get('RES', '1600x900').split('x'))
VUES = os.environ.get('VUES', 'large,lit,casiers').split(',')
EXPOS = [float(x) for x in os.environ.get('EXPOS', os.environ.get('EXPO', '0')).split('_')]

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = ECH; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = RES
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = float(os.environ.get('EXPO', '0'))
w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.002, 0.003, 0.004, 1); sc.world = w

# ---------------------------------------------------------------- salle (taille réelle des Quartiers A : 76,8 × 52,8 studs)
X0, Y0, X1, Y1 = 0.0, 0.0, 76.8, 52.8; H = 16.0
objs = Q.piece(X0, Y0, X1, Y1, H, porte=('S', 38.4, 7.2))
log('pièce construite')
# variantes d'objets (construites une fois, puis copiées)
lits = [Q.lit_superpose(seed=s) for s in range(3)]; log('lits simulés')
cas = [Q.casiers(4, seed=s, ouvert=s % 4) for s in range(2)]; log('casiers')
tab = Q.table(); chs = [Q.chaise(seed=s, col=c) for s, c in enumerate([(66, 88, 120), (120, 60, 50), (70, 100, 80)])]
def placer(root, loc, rot=0.0):
    """copie d'un ensemble (maillages partagés) à une position et une rotation"""
    new = K.empty(root.name + '_c', loc, (0, 0, rot))
    for ch in root.children:
        c = ch.copy(); K.coll().objects.link(c); c.parent = new; c.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
    return new
for r in lits + cas + [tab] + chs: r.location = (0, 0, -100)
rnd = random.Random(3)
# lits le long des deux grands murs (tête au mur)
for i in range(8):
    x = 6.5 + i*8.0
    if abs(x - 38.4) < 6: continue
    placer(lits[(i + 1) % 3], (x, 1.0 + 3.5, 0), -math.pi/2)                # mur sud (la porte au milieu)
for i in range(9):
    x = 6.5 + i*8.0
    placer(lits[i % 3], (x, Y1 - 1.0 - 3.5, 0), math.pi/2)                 # mur nord
# casiers sur les petits murs
for j in range(3):
    placer(cas[j % 2], (X0 + 0.9, 12 + j*9.5, 0), -math.pi/2)
    placer(cas[(j + 1) % 2], (X1 - 0.9, 12 + j*9.5, 0), math.pi/2)
# îlot central : lits dos à dos + tables
for i in range(3):
    x = 22 + i*16
    placer(tab, (x, 22, 0), 0)
    placer(chs[i % 3], (x - 1.2, 22 - 2.2, 0), rnd.uniform(-0.4, 0.4)); placer(chs[(i + 1) % 3], (x + 1.4, 22 + 2.1, 0), math.pi + rnd.uniform(-0.4, 0.4))
    placer(lits[(i + 2) % 3], (x, 32.5, 0), 0)
# petits objets
for i in range(3):
    t = Q.tasse(); t.location = (22 + i*16 + rnd.uniform(-1.5, 1.5), 22 + rnd.uniform(-0.6, 0.6), 2.6)
    b = Q.livre(i); b.location = (22 + i*16 + rnd.uniform(-1.5, 1.5), 22 + rnd.uniform(-0.6, 0.6), 2.6); b.rotation_euler = (0, 0, rnd.uniform(0, 3))
p = Q.poubelle(); p.location = (31, 2.2, 0)
# UV boîte sur tout ce qui est maillé
bpy.context.view_layer.update()
for o in bpy.data.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].get('tex'):
        if o.data.users > 1 and o.data.uv_layers: continue
        K.box_uv(o)
log('scène assemblée')
for o in bpy.data.objects:
    if o.type == 'MESH' and (o.name.startswith('Couverture') or o.name.startswith('Serviette')) and o.data.users >= 1 and not o.name.endswith(('.001', '.002', '.003', '.004', '.005', '.006', '.007', '.008', '.009')):
        zs = [v.co.z for v in o.data.vertices]; log(f'  {o.name}: {len(zs)} sommets, z {min(zs):.2f}..{max(zs):.2f}')

# ---------------------------------------------------------------- éclairage
def area(loc, size, energy, col=(1, 1, 1)):
    ld = bpy.data.lights.new('A', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size; ld.energy = energy; ld.color = col
    ob = bpy.data.objects.new('A', ld); sc.collection.objects.link(ob); ob.location = loc; return ob
def point(loc, energy, col, r=0.2):
    ld = bpy.data.lights.new('P', 'POINT'); ld.energy = energy; ld.color = col; ld.shadow_soft_size = r
    ob = bpy.data.objects.new('P', ld); sc.collection.objects.link(ob); ob.location = loc; return ob
dif = bpy.data.materials.get('Diffuseur')
if COURANT:
    for o in bpy.data.objects:
        if o.name.startswith('Diffuseur'): area((o.location.x, o.location.y, o.location.z - 0.1), (4.0, 1.1), float(os.environ.get('PUIS', '600')), (1.0, 0.97, 0.92))
    dif.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 6
else:
    point((38.4, 1.6, 10.6), 1500, (1.0, 0.12, 0.06), 0.3)                   # bloc de secours au-dessus de la porte
    point((38.4, 50.0, 13.0), 300, (1.0, 0.12, 0.06), 0.3)
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0005, 0.0008, 0.001, 1)

def cam(name, eye, tgt):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(70); cd.clip_start = 0.05
    ob = bpy.data.objects.new(name, cd); sc.collection.objects.link(ob); ob.location = eye
    ob.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler(); return ob
VIEWS = {
    'large': ((38.4, 6.0, 5.2), (40, 40, 3.2)),          # depuis la porte, hauteur des yeux d'un joueur
    'lit':   ((14.5, 40.5, 5.4), (6.5, 48.0, 3.0)),       # gros plan sur un lit du mur nord
    'casiers': ((66.0, 18.0, 5.2), (76.0, 22.0, 3.6)),
    'table': ((30.0, 15.5, 5.2), (38.0, 24.0, 2.4)),
}
for v in VUES:
    eye, tgt = VIEWS[v]; c = cam(v, eye, tgt); sc.camera = c
    lamp = None
    if not COURANT:
        ld = bpy.data.lights.new('Torche', 'SPOT'); ld.energy = 1600; ld.spot_size = math.radians(38); ld.spot_blend = 0.6; ld.color = (1.0, 0.95, 0.85); ld.shadow_soft_size = 0.05
        lamp = bpy.data.objects.new('Torche', ld); sc.collection.objects.link(lamp)
        lamp.location = Vector(eye) + Vector((0.8, 0, -0.9)); lamp.rotation_euler = (Vector(tgt) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.render.render()
    img = bpy.data.images['Render Result']
    for e in EXPOS:
        sc.view_settings.exposure = e
        img.save_render(os.path.join(out, f'temoin_{v}' + (f'_e{e:+g}' if len(EXPOS) > 1 else '') + '.png'), scene=sc)
    if lamp: bpy.data.objects.remove(lamp)
    log(f'rendu {v}')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'salle_temoin.blend'))
log('fin')
