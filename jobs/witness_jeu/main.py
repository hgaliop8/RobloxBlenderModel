"""THE WITNESS — modèle de jeu : construction, squelette, poids, export .glb pour Roblox, et rendus de contrôle de la peau
dans plusieurs poses (repos au sol, accrochée au plafond, attaque). POSES = liste ; ECH, RES."""
import bpy, sys, os, time, math, json
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
from mathutils import Vector, Matrix, Euler
import witness_jeu as W
import kit_meshes as K

parts, f = W.construire(log)
arm, defs = W.squelette(f)
log(f'squelette : {len(defs)} os')
# poids
for key in ('corps', 'ventouses', 'photo_v', 'photo_r'): W.lier(parts[key], arm, defs)
for key in ('coeurs', 'glande', 'badge'): W.lier(parts[key], arm, defs, rigide='Manteau1')
for key in ('oeil', 'pupille'):
    o = parts[key]
    for nm in [d[0] for d in defs]: o.vertex_groups.new(name=nm)
    for v in o.data.vertices: o.vertex_groups['OeilG' if v.co.y > 0 else 'OeilD'].add([v.index], 1.0, 'REPLACE')
    m = o.modifiers.new('squelette', 'ARMATURE'); m.object = arm; o.parent = arm
log('poids calculés')

# noms Roblox (habillage par le script KitNadir) + matériaux d'aperçu
NOMS = {'corps': ('V_D8ECF0', K.mat_verre('VerreWitness', (215, 236, 240), 0.04)),
        'ventouses': ('P_E8E4DA_60_0_0', K.mat_plain('Ventouse', (232, 228, 218), 0.6)),
        'oeil': ('P_D4A23C_30_60_0', K.mat_plain('Iris', (212, 162, 60), 0.3, 0.6)),
        'pupille': ('P_6CFF8C_30_0_6', K.mat_plain('Pupille', (108, 255, 140), 0.3, emit=6.0)),
        'photo_v': ('P_56E0D0_30_0_5', K.mat_plain('PhotoV', (86, 224, 208), 0.3, emit=5.0)),
        'photo_r': ('P_FF5040_30_0_5', K.mat_plain('PhotoR', (255, 80, 64), 0.3, emit=5.0)),
        'coeurs': ('P_B83030_40_0_0', K.mat_plain('Coeur', (184, 48, 48), 0.4)),
        'glande': ('P_C8CCD4_30_80_0', K.mat_plain('Glande', (200, 204, 212), 0.3, 0.8)),
        'badge': ('P_E8E8E0_50_0_0', K.mat_plain('Badge', (232, 232, 224), 0.5))}
stats = {}
for key, (nom, m) in NOMS.items():
    o = parts[key]; o.name = nom; o.data.name = nom; o.data.materials.clear(); o.data.materials.append(m)
    o.data.calc_loop_triangles(); stats[nom] = len(o.data.loop_triangles)
log('triangles : ' + ', '.join(f'{k} {v}' for k, v in stats.items()) + f' ; total {sum(stats.values())}')

# ---------------------------------------------------------------- export (pose de repos)
for o in bpy.context.selected_objects: o.select_set(False)
arm.select_set(True)
for o in parts.values(): o.select_set(True)
bpy.context.view_layer.objects.active = arm
chemin = os.path.join(out, 'witness.glb')
bpy.ops.export_scene.gltf(filepath=chemin, export_format='GLB', use_selection=True, export_materials='NONE', export_skins=True, export_yup=True,
                          export_apply=False, export_animations=False, export_texcoords=True, export_normals=True)
log(f'witness.glb : {os.path.getsize(chemin)//1024} Ko')
json.dump({'triangles': stats, 'os': [d[0] for d in defs], 'echelle': f}, open(os.path.join(out, 'witness.json'), 'w'), indent=1)

# ---------------------------------------------------------------- poses de contrôle
POSES = [p for p in os.environ.get('POSES', 'repos,plafond,attaque').split(',') if p]
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('ECH', '64')); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 16; sc.cycles.transmission_bounces = 16; sc.cycles.transparent_max_bounces = 16
sc.render.resolution_x, sc.render.resolution_y = (int(x) for x in os.environ.get('RES', '1200x675').split('x'))
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.025, 0.03, 1); sc.world = w
H = 14.0
sol = K.cube('Sol', (80, 80, 0.4), (0, 0, -0.2), K.mat('vinyle', (110, 116, 120)), 0); K.box_uv(sol)
plaf = K.cube('Plafond', (80, 80, 0.4), (0, 0, H + 0.2), K.mat('plafond', (200, 200, 196)), 0); K.box_uv(plaf)
mur = K.cube('Mur', (80, 0.4, H), (0, -14, H/2), K.mat('peinture_mur', (180, 186, 190)), 0); K.box_uv(mur)
def lampe(loc, e, size=6):
    ld = bpy.data.lights.new('A', 'AREA'); ld.size = size; ld.energy = e; ob = bpy.data.objects.new('A', ld); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 3)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return ob
lampe((10, 12, 12), 9000); lampe((-12, 6, 6), 3000); lampe((0, -10, 13), 2500)
cd = bpy.data.cameras.new('C'); cd.lens = 32; cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam

def rot(pb, x=0.0, z=0.0):
    pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((x, 0, z))
def poser(mode):
    for pb in arm.pose.bones: pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((0, 0, 0))
    arm.location = (0, 0, 0); arm.rotation_euler = (0, 0, 0)
    for k in range(8):
        for j in range(1, W.N_OS + 1):
            pb = arm.pose.bones[f'Bras{k}_{j}']; ph = k*1.3 + j*0.55
            if mode == 'repos':                   # bras qui ondulent au sol, pointes relevées
                rot(pb, x=0.08*math.sin(ph)*(j > 2) + (0.25 if j >= 6 else 0.0), z=0.22*math.sin(ph + 0.7))
            elif mode == 'plafond':               # ventouses collées, bras écartés en vagues, pointes qui pendent
                rot(pb, x=(0.35 if j >= 7 else 0.03*math.sin(ph)), z=0.18*math.sin(ph))
            elif mode == 'attaque':
                if k in (0, 7):                    # deux bras avant dressés vers la proie, enroulés au bout
                    rot(pb, x=(0.55 if j == 1 else 0.28 if j < 5 else 0.6), z=(0.15 if k == 0 else -0.15))
                else: rot(pb, x=0.06*math.sin(ph) + (0.15 if j == 1 else 0.0), z=0.25*math.sin(ph))
    if mode == 'plafond':
        arm.rotation_euler = (math.pi, 0, 0.4); arm.location = (0, 0, H)
        cam.location = (9, 13, 2.2); tgt = Vector((0, 0, H - 1.5))
    elif mode == 'attaque':
        rot(arm.pose.bones['Tete'], x=-0.25); rot(arm.pose.bones['Manteau1'], x=0.3)
        arm.rotation_euler = (0, 0, -0.5); cam.location = (11, 7, 3.0); tgt = Vector((0, 0, 1.8))
    else:
        arm.rotation_euler = (0, 0, -0.6); cam.location = (10, 10, 7); tgt = Vector((0, 0, 0.5))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
for p in POSES:
    poser(p); sc.render.filepath = os.path.join(out, f'witness_{p}.png'); bpy.ops.render.render(write_still=True); log(f'pose {p}')
log('fin')
