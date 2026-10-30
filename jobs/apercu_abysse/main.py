"""Aperçus des créatures de la base sous-marine abandonnée. CREA=siphon|echo|scaph (une machine par créature)."""
import bpy, sys, os, time, math
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
import abysse as A
from mathutils import Vector

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(msg): logf.write(f'{time.time() - T0:7.1f}s  {msg}\n'); logf.flush(); print('>>', msg, flush=True)
CREA = os.environ.get('CREA', 'siphon')
bpy.ops.wm.read_factory_settings(use_empty=True)
M = A.mats()
sc = B.setup_render((1600, 900), samples=128, exposure=0.0)
sc.cycles.volume_step_rate = 2.0; sc.cycles.volume_max_steps = 256; sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 10
B.world((0.0008, 0.0015, 0.002))

def lampe(eye, tgt, energy=160, spot=0.6):
    e = Vector(eye); t = Vector(tgt); l = B.light('SPOT', tuple(e + Vector((0.12, 0, 0.2)) + (t - e).normalized()*0.15), energy, (1.0, 0.9, 0.75), size=0.02, name='Lampe', spot=spot)
    l.rotation_euler = (t - l.location).to_track_quat('-Z', 'Y').to_euler(); return l

VUES = []
if CREA == 'siphon':
    A.coursive(M, alarme=8)
    B.light('AREA', (4, 0, 1.4), 40, (0.3, 0.8, 0.75), size=3, target=(4, 0, -1), name='Glauque')
    A.eau_trouble('EauCoursive', (-4, -1.6, -1.1), (12, 1.6, 1.6), (0.08, 0.42, 0.4), 0.07, 0.6)
    A.neige_marine((-3.5, -1.3, -0.85), (11.5, 1.3, 1.4), 3000)
    path = [(9.6, 0.0, 0.42), (8.2, -0.35, 0.65), (6.6, 0.3, 0.95), (5.0, 0.55, 1.05), (3.4, 0.2, 1.1), (1.8, 0.55, 1.0), (0.4, 0.75, 0.85), (-1.2, 0.5, 1.0)]
    A.siphon(M, [Vector(p) for p in path], n=70, lure_at=(10.6, 0.0, 0.35))
    # le vrai panneau de sortie : éteint, sur la paroi de gauche
    A.text_obj('SORTIE', (3.2, -1.36, 0.9), (math.pi/2, 0, 0), 0.18, A._emission('SortieEteinte', (0.1, 0.8, 0.3), 0.8))
    VUES = [('siphon_couloir', (-3.3, -0.55, 0.15), (8.0, 0.15, 0.55), 24), ('siphon_proche', (0.2, -0.75, 0.35), (2.1, 0.5, 0.98), 30)]
elif CREA == 'echo':
    zc = A.citerne(M)
    A.echo(M, c=(0.9, 0.3, 0.7), yaw=math.pi - 0.15, pitch=0.32)
    A.eau_trouble('Brume', (-4.6, -4.6, 0.01), (4.6, 4.6, 5.4), (0.5, 0.55, 0.55), 0.018, 0.3)
    A.eau_trouble('EauNoire', (-4.6, -4.6, -4.0), (4.6, 4.6, -0.01), (0.03, 0.12, 0.1), 0.6, 0.2)
    A.neige_marine((-4, -4, 0.1), (4, 4, 5), 1800)
    B.light('AREA', (0, 0, 5.3), 300, (0.6, 0.75, 0.9), size=1.0, target=(0.5, 0.2, 0), name='Trappe')
    B.light('POINT', (-2.8, 3.2, 3.0), 60, (1.0, 0.08, 0.04), size=0.1, name='Alarme')
    VUES = [('echo_citerne', (-3.9, -0.9, 3.55), (0.0, 0.2, 0.6), 26), ('echo_gueule', (-2.6, -1.2, 1.2), (-0.3, 0.35, 0.3), 30)]
elif CREA == 'scaph':
    A.coursive(M, alarme=14)
    bpy.ops.mesh.primitive_plane_add(size=1); w = bpy.context.object; w.scale = (16, 3, 1); w.location = (4, 0, -0.86); w.data.materials.append(M['eau'])
    A.eau_trouble('Brouillard', (-4, -1.6, -0.86), (12, 1.6, 1.6), (0.5, 0.55, 0.55), 0.03, 0.4)
    s = A.scaphandrier(M, base=(4.6, 0.05, -0.92), yaw=math.pi)
    h = s['head']
    VUES = [('scaph_couloir', (0.6, -0.55, 0.0), (4.6, 0.05, 0.3), 30), ('scaph_casque', tuple(h + Vector((-0.75, -0.22, -0.02))), tuple(h + Vector((-0.1, 0, 0))), 45)]
log('scène prête')
for name, eye, tgt, lens in VUES:
    cam = B.camera(eye, tgt, lens, name)
    l = lampe(eye, tgt)
    B.render(os.path.join(out, f'{name}.png'), cam)
    bpy.data.objects.remove(l)
    log(f'rendu {name}')
log('fin')
