"""THE WITNESS (ex-Vitrelle) — rendus Cycles.
VUE = studio | profil | oeil | tete | nuit | plafond | apercu (petites images rapides de oeil, tete, nuit)
TUILE = i-n : ne rend que la bande horizontale i sur n (avec recouvrement), pour répartir une vue sur plusieurs machines.
ECH = nombre d'échantillons (défaut 1024 en final, 48 en aperçu) ; RES = LxH."""
import bpy, sys, os, time, math, json
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
import abysse as A
import vitrelle as V
from mathutils import Vector

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(msg): logf.write(f'{time.time() - T0:7.1f}s  {msg}\n'); logf.flush(); print('>>', msg, flush=True)
VUE = os.environ.get('VUE', 'apercu'); TEST = VUE == 'apercu'
res = tuple(int(x) for x in os.environ.get('RES', '640x360' if TEST else '1920x1080').split('x'))
ech = int(os.environ.get('ECH', '48' if TEST else '1024'))
bpy.ops.wm.read_factory_settings(use_empty=True)

sc = B.setup_render(res, samples=ech, exposure=0.0)
c = sc.cycles; c.max_bounces = 32; c.transmission_bounces = 32; c.transparent_max_bounces = 16; c.glossy_bounces = 8; c.volume_bounces = 2
c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 0.3; c.adaptive_threshold = 0.006 if not TEST else 0.03
c.volume_step_rate = 1.0
for k, v in (('use_guiding', True), ('use_surface_guiding', True), ('use_volume_guiding', True)):
    if hasattr(c, k): setattr(c, k, v)
if hasattr(c, 'denoiser'): c.denoiser = 'OPENIMAGEDENOISE'
if hasattr(c, 'denoising_prefilter'): c.denoising_prefilter = 'ACCURATE'
if hasattr(c, 'denoising_quality'): c.denoising_quality = 'HIGH'

def studio(intensite=1.0, lampes=True):
    """cyclorama sombre, lumières qui dessinent les bords du verre"""
    bm = A.bmesh.new(); Rb = 2.0
    prof = [(-6 + k*0.25, 0.0) for k in range(28)] + [(1.0 + Rb*math.sin(a), Rb - Rb*math.cos(a)) for a in [i/12*math.pi/2 for i in range(1, 13)]] + [(1.0 + Rb, 2.0 + k*0.4) for k in range(1, 12)]
    rows = []
    for (u, z) in prof:
        rows.append([bm.verts.new((u, y, z)) for y in [-6 + j*0.5 for j in range(25)]])
    for a, b in zip(rows[:-1], rows[1:]):
        for j in range(24): bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    cyc = A.mesh_obj('Cyclo', bm, smooth=True); cyc.rotation_euler = (0, 0, math.pi*0.85)
    m = B.mat_simple('Fond', (0.03, 0.033, 0.036), 0.35, noise_scale=1.5, noise_col=(0.012, 0.014, 0.016), bump=0.02); cyc.data.materials.append(m)
    B.world((0.002, 0.0025, 0.003))
    if not lampes: return
    k = intensite
    B.light('AREA', (2.2, -1.6, 2.8), 520*k, (0.95, 0.97, 1.0), size=2.2, target=(0, 0, 0.4), name='Cle')
    B.light('AREA', (-2.4, 1.6, 1.6), 380*k, (0.35, 0.85, 1.0), size=1.4, target=(0, 0, 0.5), name='ContreCyan')
    B.light('AREA', (-1.0, -2.8, 0.6), 160*k, (1.0, 0.75, 0.55), size=1.0, target=(0, 0, 0.4), name='ContreChaud')
    B.light('AREA', (0, 0, 4), 90*k, (0.8, 0.9, 1.0), size=3, target=(0, 0, 0), name='Haut')

parts = V.build(log=log)
M = V.mats(); V.assign(parts, M)
log('créature construite')

eC = V.EYE_C[-1]; eA = V.EYE_AX[-1]
CAMS = {
    'studio': ((3.3, -2.9, 1.45), (-0.2, 0.05, 0.55), 38, True),
    'profil': ((-0.7, -4.2, 1.0), (-0.25, 0.0, 0.55), 42, True),
    'oeil':   (tuple(eC + eA*0.7 + Vector((0.22, 0.0, -0.12))), tuple(eC - eA*0.03 + Vector((0, 0, 0.01))), 55, True),
    'tete':   (tuple(eC + eA*1.55 + Vector((0.35, 0.0, 0.06))), tuple(eC + Vector((-0.22, 0.0, 0.06))), 50, True),
    'nuit':   (tuple(eC + eA*1.2 + Vector((0.35, 0.0, -0.32))), tuple(eC + Vector((-0.12, 0.0, 0.04))), 35, False),
}
vues = []
if VUE in ('studio', 'profil', 'oeil', 'tete', 'apercu'):
    studio()
    vues = ['oeil', 'tete', 'nuit'] if TEST else [VUE]
elif VUE == 'nuit':
    studio(lampes=False); vues = ['nuit']
if VUE == 'plafond':
    MA = A.mats(); A.coursive(MA, alarme=10)
    A.eau_trouble('Brouillard', (-4, -1.6, -0.9), (12, 1.6, 1.6), (0.5, 0.6, 0.6), 0.02, 0.4)
    V.wrap_ceiling(parts, x0=3.6)
    B.world((0.0008, 0.0012, 0.0016))
    CAMS['plafond'] = ((-1.2, -0.35, -0.3), (3.3, 0.05, 0.9), 26, True); vues = ['plafond']
for o in bpy.data.objects:
    if o.type == 'LIGHT' and o.data.type == 'AREA': o.data.shape = 'DISK'
log('scène prête')

tuile = os.environ.get('TUILE')
for name in vues:
    eye, tgt, lens, lampe = CAMS[name]
    cam = B.camera(eye, tgt, lens, name)
    studio_l = [o for o in bpy.data.objects if o.type == 'LIGHT']
    if name == 'nuit':                                           # tout éteint sauf un liseré froid très faible
        for o in studio_l: o.hide_render = True
        rim = B.light('AREA', (-2.0, 1.2, 1.4), 35, (0.3, 0.7, 1.0), size=1.5, target=(0, 0, 0.5), name='Liseré')
    lp = None
    if lampe:
        e = Vector(eye); t = Vector(tgt)
        lp = B.light('SPOT', tuple(e + Vector((0.1, 0, 0.15))), 60 if name == 'plafond' else 25, (1.0, 0.92, 0.8), size=0.02, name='Lampe', spot=0.55)
        lp.rotation_euler = (t - lp.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.data.materials['Oeil'].node_tree.nodes['Lueur'].outputs[0].default_value = float(os.environ.get('LUEUR', '8' if name in ('nuit', 'plafond') else '0.12'))
    fn = f'witness_{name}'
    r = sc.render
    if tuile:
        i, n = (int(x) for x in tuile.split('-')); ov = 24/res[1]
        r.use_border = True; r.use_crop_to_border = True; r.border_min_x, r.border_max_x = 0.0, 1.0
        r.border_min_y = max(0.0, 1 - (i + 1)/n - ov); r.border_max_y = min(1.0, 1 - i/n + ov)
        json.dump(dict(i=i, n=n, y0=r.border_min_y, y1=r.border_max_y, W=res[0], H=res[1]), open(os.path.join(out, f'{fn}_t{i}.json'), 'w'))
        fn += f'_t{i}'
    B.render(os.path.join(out, f'{fn}.png'), cam)
    if lp: bpy.data.objects.remove(lp)
    if name == 'nuit':
        for o in studio_l: o.hide_render = False
        bpy.data.objects.remove(rim)
    log(f'rendu {fn}')
log('fin')
