"""THE WITNESS — aperçu animé du mouvement (mêmes formules que le script Roblox WitnessCorps, portées en Python).
Scénario dans un couloir, vu depuis la hauteur des yeux d'un joueur : elle avance au plafond, se laisse tomber, court au sol
vers le joueur et dresse ses bras pour le saisir. IMAGES = a-b (plage d'images à rendre), FPS = 24, ECH, RES."""
import bpy, sys, os, time, math
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
for key in ('corps', 'ventouses', 'photo_v', 'photo_r'): W.lier(parts[key], arm, defs)
for key in ('coeurs', 'glande', 'badge'): W.lier(parts[key], arm, defs, rigide='Manteau1')
for key in ('oeil', 'pupille'):
    o = parts[key]
    for nm in [d[0] for d in defs]: o.vertex_groups.new(name=nm)
    for v in o.data.vertices: o.vertex_groups['OeilG' if v.co.y > 0 else 'OeilD'].add([v.index], 1.0, 'REPLACE')
    m = o.modifiers.new('squelette', 'ARMATURE'); m.object = arm; o.parent = arm
M = {'corps': K.mat_verre('VerreWitness', (215, 236, 240), 0.04), 'ventouses': K.mat_plain('Ventouse', (232, 228, 218), 0.6),
     'oeil': K.mat_plain('Iris', (212, 162, 60), 0.3, 0.6), 'pupille': K.mat_plain('Pupille', (108, 255, 140), 0.3, emit=6.0),
     'photo_v': K.mat_plain('PhotoV', (86, 224, 208), 0.3, emit=5.0), 'photo_r': K.mat_plain('PhotoR', (255, 80, 64), 0.3, emit=5.0),
     'coeurs': K.mat_plain('Coeur', (184, 48, 48), 0.4), 'glande': K.mat_plain('Glande', (200, 204, 212), 0.3, 0.8), 'badge': K.mat_plain('Badge', (232, 232, 224), 0.5)}
for k, m in M.items(): parts[k].data.materials.clear(); parts[k].data.materials.append(m)
log('modèle prêt')

# ---------------------------------------------------------------- couloir
FPS = int(os.environ.get('FPS', '24')); H = 12.0
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('ECH', '32')); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 12; sc.cycles.transmission_bounces = 12; sc.cycles.transparent_max_bounces = 12
sc.render.resolution_x, sc.render.resolution_y = (int(x) for x in os.environ.get('RES', '1280x720').split('x'))
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = float(os.environ.get('EXPO', '1.6'))
w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.006, 0.008, 0.011, 1); sc.world = w
LARG = 12.0; L0, L1 = -80.0, 110.0; LX = L1 - L0; CX = (L0 + L1)/2
for nom, size, loc, mt in (('Sol', (LX, LARG, 0.4), (CX, 0, -0.2), K.mat('tole_striee', (120, 124, 126))),
                           ('Plafond', (LX, LARG, 0.4), (CX, 0, H + 0.2), K.mat('plafond', (190, 192, 188))),
                           ('MurN', (LX, 0.4, H), (CX, LARG/2 + 0.2, H/2), K.mat('metal_peint', (150, 156, 160))),
                           ('MurS', (LX, 0.4, H), (CX, -LARG/2 - 0.2, H/2), K.mat('metal_peint', (150, 156, 160))),
                           ('Fond', (0.4, LARG, H), (L0 + 0.2, 0, H/2), K.mat('metal_peint', (120, 126, 130)))):
    o = K.cube(nom, size, loc, mt, 0); K.box_uv(o)
for x in range(int(L0) + 6, int(L1), 8):                                 # arches et soubassement
    for sy in (-1, 1): o = K.cube('Arche', (0.8, 0.6, H), (x, sy*(LARG/2 - 0.3), H/2), K.mat('metal_peint', (90, 96, 104)), 0.05); K.box_uv(o)
    o = K.cube('ArcheHaut', (0.8, LARG, 0.6), (x, 0, H - 0.3), K.mat('metal_peint', (90, 96, 104)), 0.05); K.box_uv(o)
def lampe(loc, e, col=(1.0, 0.95, 0.88), size=2.0):
    ld = bpy.data.lights.new('A', 'AREA'); ld.size = size; ld.energy = e; ld.color = col
    ob = bpy.data.objects.new('A', ld); sc.collection.objects.link(ob); ob.location = loc; return ob
for x in range(-36, 108, 16):
    lampe((x + 4, 0, H - 0.8), 1400, (1.0, 0.2, 0.12), 1.0)  # éclairage de secours rouge, un tous les 16 studs
torche = bpy.data.lights.new('Torche', 'SPOT'); torche.energy = 7000; torche.spot_size = math.radians(40); torche.spot_blend = 0.5; torche.color = (1.0, 0.95, 0.85); torche.shadow_soft_size = 0.05
tob = bpy.data.objects.new('Torche', torche); sc.collection.objects.link(tob)
cd = bpy.data.cameras.new('C'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(70); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
CAM = Vector((96, -1.5, 5.0)); cam.location = CAM

# ---------------------------------------------------------------- scénario (racine) : temps -> (position, plafond?, coup, temps du coup)
def racine(t):
    if t < 3.0:   return Vector((26 + 14*t, 0.4*math.sin(t*0.8), H)), 1.0, None, 0, 14.0           # plafond, 14 studs/s
    if t < 3.6:                                                                                   # chute au sol, 0,6 s
        a = (t - 3.0)/0.6; e = a*a*(3 - 2*a)
        return Vector((68 + 4*a, 0.4*math.sin(2.4), H*(1 - e))), 1.0 - e, 'descente', 3.0, 8.0
    if t < 4.22:                                                                                  # course au sol, 26 studs/s
        a = (t - 3.6)/0.62; return Vector((72 + 16.0*a, 0.3*math.sin(t*3), 0)), 0.0, None, 0, 26.0
    return Vector((88, 0, 0)), 0.0, 'saisie', 4.22, 0.0
SIGNE = {'fouet': 0.5, 'balayage': 0.6, 'morsure': 0.35, 'saisie': 0.7, 'enlevement': 1.0, 'chute': 1.5, 'encre': 0.5, 'descente': 0.6}
def lisse(a): a = max(0.0, min(1.0, a)); return a*a*(3 - 2*a)
phases = {k: k*0.79 + (k % 3)*0.4 for k in range(8)}

def animer(t, vit, coup, coupT, mode):
    """port exact de WitnessCorps.animer (Luau) : angles (x = tangage, z = lacet) de chaque os"""
    e = t - coupT; signe = SIGNE.get(coup, 0.5); saisie = coup in ('saisie', 'enlevement')
    marche = max(0.0, min(1.0, vit/10)); wg = 2 + vit*0.8; R = {}
    for k in range(8):
        ph = phases[k]
        for j in range(1, 9):
            yaw = 0.13*math.sin(t*1.3 - j*0.55 + ph); pitch = 0.04*math.sin(t*0.9 + j*0.6 + ph)
            if j >= 7: pitch += 0.22 + 0.08*math.sin(t*1.7 + ph)
            if marche > 0.05 and j <= 4:
                g = math.sin(t*wg + (k % 2)*math.pi)
                yaw += marche*0.28*g*(1 - (j - 1)/4); pitch += marche*0.22*max(0, g)*(1 if j >= 2 else 0)
            if coup == 'fouet' and k in (0, 7):
                if e < signe: pitch += lisse(e/signe)*0.4*(j/8)*2
                elif e < signe + 0.3: pitch -= 0.35; yaw += (0.4 if k == 0 else -0.4)*(1 if j <= 3 else 0.4)
            elif saisie and k in (0, 7, 1, 6):
                a = lisse(e/signe); pitch += a*(0.6 if j == 1 else (0.25 if j <= 4 else 0.45)); yaw += a*(0.2 if k <= 1 else -0.2)
            elif coup == 'descente':
                pitch += lisse(e/0.6)*(0.35 if j >= 4 else 0.1)
            R[f'Bras{k}_{j}'] = (pitch, yaw)
    respi = math.sin(t*1.25)
    R['Manteau1'] = (0.05*respi, 0.02*math.sin(t*0.7)); R['Manteau2'] = (0.08*math.sin(t*1.25 + 0.5), 0.04*math.sin(t*0.6))
    R['Tete'] = (0.03*math.sin(t*0.8), 0)
    return R

IM = os.environ.get('IMAGES', '1-156'); i0, i1 = (int(x) for x in IM.split('-'))
prec = None
for fr in range(i0, i1 + 1):
    t = (fr - 1)/FPS
    pos, plaf, coup, coupT, vit = racine(t)
    # orientation : devant = +X du modèle vers +X du couloir ; au plafond, retournée (rotation de pi autour de l'axe avant)
    arm.rotation_euler = Euler((math.pi*plaf, 0, 0)); arm.location = pos
    R = animer(t, vit, coup, coupT, 'plafond' if plaf > 0.5 else 'sol')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'; x, z = R.get(pb.name, (0, 0)); pb.rotation_euler = Euler((x, 0, z))
    # yeux vers la caméra
    for nm in ('OeilG', 'OeilD'):
        pb = arm.pose.bones[nm]; bpy.context.view_layer.update()
        Mw = arm.matrix_world @ pb.bone.matrix_local; d = (Mw.inverted().to_3x3() @ (CAM - Mw.translation)).normalized()
        q = Vector((0, 1, 0)).rotation_difference(d); ang = min(q.angle, 0.7); pb.rotation_mode = 'QUATERNION'
        from mathutils import Quaternion
        pb.rotation_quaternion = Quaternion(q.axis, ang)
    # lampe torche du joueur : légère respiration de la main
    tob.location = CAM + Vector((0.6, -0.5, -0.8)); cible = pos + Vector((0, 0, -1.0 if plaf > 0.5 else 1.0))
    tob.rotation_euler = (cible - tob.location + Vector((0, 0.2*math.sin(t*1.5), 0.15*math.sin(t*2.1)))).to_track_quat('-Z', 'Y').to_euler()
    cam.rotation_euler = (cible.lerp(Vector((0, 0, 5)), 0.35) - CAM).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(out, f'img_{fr:04d}.png'); bpy.ops.render.render(write_still=True)
    if fr % 12 == 0: log(f'image {fr}')
log('fin')
