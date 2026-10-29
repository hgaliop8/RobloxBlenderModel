"""Ballast — étape 1 de la cuisson : construit les modèles détaillés et en tire des maillages légers (sans UV),
exportés en npz (V, F) pour être dépliés dans le pipeline maison, puis cuits par jobs/ballast_bake."""
import bpy, sys, os, time
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
import ballast_bl as B
import ballast_scene as S

out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(msg): logf.write(f'{time.time() - T0:7.1f}s  {msg}\n'); logf.flush(); print('>>', msg, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

def dup(o):
    c = o.copy(); c.data = o.data.copy(); B.coll().objects.link(c); c.modifiers.clear(); return c

def low_from(objs, name, voxel, target, remesh=True):
    lo = B.join([dup(o) for o in objs], name)
    if remesh: lo = B.remesh(lo, voxel=voxel, smooth=2)
    n = len(lo.data.polygons)
    if n > target:
        d = lo.modifiers.new('dec', 'DECIMATE'); d.ratio = target/n; d.use_collapse_triangulate = True
    lo.modifiers.new('tri', 'TRIANGULATE'); B.bake_mods(lo)
    me = lo.data; P = np.zeros(len(me.vertices)*3, np.float32); me.vertices.foreach_get('co', P)
    F = np.zeros(len(me.polygons)*3, np.int32); me.polygons.foreach_get('vertices', F)
    np.savez_compressed(os.path.join(out, f'{name}.npz'), V=P.reshape(-1, 3), F=F.reshape(-1, 3))
    log(f'{name} : {len(me.polygons)} triangles exportés')

amas, levres, fond, ongles, cailloux, tirefonds, dents = S.amas(log=log)
low_from([amas, levres, fond, cailloux, tirefonds], 'Amas', 0.0036, 130000)
low_from([dents], 'Dents', 0, 24000, remesh=False)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
for name, seed in (('BrasGrille', 1), ('BrasFenetre', 2), ('BrasToilettes', 3)):
    hi, nails = S.bras_scene(name, seed, log=log, droit=True)
    low_from([hi], name, 0.0035, 36000)
    bpy.data.objects.remove(hi); bpy.data.objects.remove(nails)
log('fin')
