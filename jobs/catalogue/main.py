"""Planche de contrôle du kit : chaque objet rendu seul dans un petit studio (sol, mur, éclairage doux), vue 3/4 avant.
OBJETS = liste de noms (séparés par des virgules) ; ECH, RES, EXPO."""
import bpy, sys, os, math, time, json
from mathutils import Vector
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
import kit_meshes as K
import catalogue as C
ECH = int(os.environ.get('ECH', '64')); RES = tuple(int(x) for x in os.environ.get('RES', '900x700').split('x'))
NOMS = os.environ.get('OBJETS', ','.join(C.REGISTRE)).split(',')
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = ECH; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = RES
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = float(os.environ.get('EXPO', '0'))
w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.022, 0.025, 1); sc.world = w
# studio
studio = [K.cube('StudioSol', (80, 80, 0.4), (0, 10, -0.2), K.mat('vinyle', (110, 116, 120)), 0), K.cube('StudioMur', (80, 0.4, 30), (0, -0.25, 15), K.mat('peinture_mur', (180, 186, 190)), 0)]
for o in studio: K.box_uv(o)
def area(loc, size, energy, tgt):
    ld = bpy.data.lights.new('A', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size, size; ld.energy = energy
    ob = bpy.data.objects.new('A', ld); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return ob
cd = bpy.data.cameras.new('C'); cd.lens = 50; cd.clip_start = 0.05; cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
lights = []
stats = {}
for nom in NOMS:
    t0 = time.time()
    avant = set(bpy.data.objects)
    root = C.REGISTRE[nom]()
    bpy.context.view_layer.update()
    neufs = [o for o in bpy.data.objects if o not in avant]
    mesh = [o for o in neufs if o.type == 'MESH']
    for o in mesh:
        if o.data.materials and o.data.materials[0].get('tex'): K.box_uv(o)
    pts = [o.matrix_world @ Vector(c) for o in mesh for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    dz = -lo.z if lo.z < -0.01 else (1.0 - lo.z if lo.z > 1.0 else 0.0)   # objet mural / centré : le poser pour la photo
    root.location.z += dz; lo.z += dz; hi.z += dz
    root.location.x -= (lo.x + hi.x)/2; root.location.y += 0.05 - lo.y
    bpy.context.view_layer.update()
    dim = hi - lo; ctr = Vector((0, 0.05 + dim.y/2, lo.z + dim.z/2))
    dist = max(dim.x, dim.z*1.3, dim.y)*2.3 + 2.0
    dirv = Vector((0.55, 1.0, 0.42)).normalized(); cam.location = ctr + dirv*dist
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for l in lights: bpy.data.objects.remove(l)
    s = max(dim.length, 4)
    lights = [area(ctr + Vector((s*0.8, s*1.2, s*1.1)), s*0.9, 90*s*s, ctr), area(ctr + Vector((-s*1.2, s*0.9, s*0.4)), s*0.9, 25*s*s, ctr),
              area(ctr + Vector((0, -0.1, s*1.4)), s*0.6, 20*s*s, ctr)]
    sc.render.filepath = os.path.join(out, f'cat_{nom}.png'); bpy.ops.render.render(write_still=True)
    # statistiques (triangles après modificateurs)
    dg = bpy.context.evaluated_depsgraph_get(); tri = 0; parmat = {}
    for o in mesh:
        me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); n = len(me.loop_triangles); tri += n
        k = o.data.materials[0].name if o.data.materials else '-'; parmat[k] = parmat.get(k, 0) + n; o.evaluated_get(dg).to_mesh_clear()
    stats[nom] = {'objets': len(mesh), 'triangles': tri, 'dim': [round(v, 2) for v in dim], 'par_matiere': parmat}
    log(f'{nom}: {len(mesh)} maillages, {tri} triangles, {dim.x:.1f}×{dim.y:.1f}×{dim.z:.1f} studs ({time.time() - t0:.0f}s)')
    for o in neufs: bpy.data.objects.remove(o)
json.dump(stats, open(os.path.join(out, 'stats.json'), 'w'), indent=1)
log('fin')
