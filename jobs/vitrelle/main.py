"""VITRELLE — rendus Cycles. VUE=studio|profil|oeil|plafond|test (test : petites images rapides des deux poses)."""
import bpy, sys, os, time, math
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
import abysse as A
import vitrelle as V
from mathutils import Vector

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(msg): logf.write(f'{time.time() - T0:7.1f}s  {msg}\n'); logf.flush(); print('>>', msg, flush=True)
VUE = os.environ.get('VUE', 'test'); TEST = VUE == 'test'
bpy.ops.wm.read_factory_settings(use_empty=True)

sc = B.setup_render((480, 270) if TEST else (1600, 900), samples=24 if TEST else 320, exposure=0.0)
c = sc.cycles; c.max_bounces = 24; c.transmission_bounces = 24; c.transparent_max_bounces = 16; c.glossy_bounces = 8; c.volume_bounces = 2
c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 0.6; c.adaptive_threshold = 0.012
c.volume_step_rate = 1.0

def studio():
    """cyclorama sombre, lumières qui dessinent les bords du verre"""
    bm = A.bmesh.new(); Rb = 2.0; verts = []
    prof = [(-6 + k*0.25, 0.0) for k in range(28)] + [(1.0 + Rb*math.sin(a), Rb - Rb*math.cos(a)) for a in [i/12*math.pi/2 for i in range(1, 13)]] + [(1.0 + Rb, 2.0 + k*0.4) for k in range(1, 12)]
    rows = []
    for (u, z) in prof:
        rows.append([bm.verts.new((u, y, z)) for y in [-6 + j*0.5 for j in range(25)]])
    for a, b in zip(rows[:-1], rows[1:]):
        for j in range(24): bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    cyc = A.mesh_obj('Cyclo', bm, smooth=True); cyc.rotation_euler = (0, 0, math.pi*0.85)
    m = B.mat_simple('Fond', (0.03, 0.033, 0.036), 0.35, noise_scale=1.5, noise_col=(0.012, 0.014, 0.016), bump=0.02); cyc.data.materials.append(m)
    B.world((0.002, 0.0025, 0.003))
    B.light('AREA', (2.2, -1.6, 2.8), 520, (0.95, 0.97, 1.0), size=2.2, target=(0, 0, 0.4), name='Cle')
    B.light('AREA', (-2.4, 1.6, 1.6), 380, (0.35, 0.85, 1.0), size=1.4, target=(0, 0, 0.5), name='ContreCyan')
    B.light('AREA', (-1.0, -2.8, 0.6), 160, (1.0, 0.75, 0.55), size=1.0, target=(0, 0, 0.4), name='ContreChaud')
    B.light('AREA', (0, 0, 4), 90, (0.8, 0.9, 1.0), size=3, target=(0, 0, 0), name='Haut')

parts = V.build(log=log); M = V.mats(); V.assign(parts, M)
log('créature construite')
vues = []
eyeR = V.EYE_BASE[-1] + V.EYE_AX[-1]*0.16
if VUE in ('studio', 'profil', 'oeil', 'test'):
    studio()
    if VUE in ('studio', 'test'): vues.append(('vitrelle_studio', (2.9, -2.5, 1.25), (-0.15, 0.05, 0.45), 40))
    if VUE == 'profil': vues.append(('vitrelle_profil', (-0.6, -3.8, 0.9), (-0.25, 0.0, 0.45), 45))
    if VUE == 'oeil': vues.append(('vitrelle_oeil', tuple(eyeR + Vector((0.42, -0.3, 0.12))), tuple(eyeR - Vector((0.02, 0, 0.02))), 85))
if VUE in ('plafond', 'test'):
    if VUE == 'test':
        for o in list(bpy.data.objects):
            if o.type != 'MESH' or not o.name.startswith(('Cyclo',)): continue
            bpy.data.objects.remove(o)
        for o in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
    MA = A.mats(); A.coursive(MA, alarme=10)
    A.eau_trouble('Brouillard', (-4, -1.6, -0.9), (12, 1.6, 1.6), (0.5, 0.6, 0.6), 0.02, 0.4)
    V.wrap_ceiling(parts, x0=3.6)
    B.world((0.0008, 0.0012, 0.0016))
    vues.append(('vitrelle_plafond', (-1.2, -0.35, -0.3), (3.3, 0.05, 0.9), 26))
log('scène prête')
for name, eye, tgt, lens in vues:
    cam = B.camera(eye, tgt, lens, name)
    e = Vector(eye); t = Vector(tgt)
    lp = B.light('SPOT', tuple(e + Vector((0.1, 0, 0.15))), 60 if 'plafond' in name else 25, (1.0, 0.92, 0.8), size=0.02, name='Lampe', spot=0.55)
    lp.rotation_euler = (t - lp.location).to_track_quat('-Z', 'Y').to_euler()
    B.render(os.path.join(out, f'{name}.png'), cam); bpy.data.objects.remove(lp)
    log(f'rendu {name}')
log('fin')
