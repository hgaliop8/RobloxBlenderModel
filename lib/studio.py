"""Petit studio photo pour les planches de contrôle : sol, mur, trois sources douces, caméra 3/4 avant cadrée sur l'objet."""
import bpy, os
from mathutils import Vector
import kit_meshes as K

def preparer(ech=64, res=(900, 700), expo=0.0):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = ech; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = expo
    w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.022, 0.025, 1); sc.world = w
    studio = [K.cube('StudioSol', (80, 80, 0.4), (0, 10, -0.2), K.mat('vinyle', (110, 116, 120)), 0), K.cube('StudioMur', (80, 0.4, 30), (0, -0.25, 15), K.mat('peinture_mur', (180, 186, 190)), 0)]
    for o in studio: K.box_uv(o)
    cd = bpy.data.cameras.new('C'); cd.lens = 50; cd.clip_start = 0.05; cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
    return {'cam': cam, 'lights': [], 'studio': studio}

def _area(loc, size, energy, tgt):
    sc = bpy.context.scene
    ld = bpy.data.lights.new('A', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size, size; ld.energy = energy
    ob = bpy.data.objects.new('A', ld); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return ob

def photo(st, objets_mesh, racine, chemin):
    """pose l'objet (racine) contre le mur, cadre, éclaire et rend"""
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objets_mesh for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    dz = -lo.z if lo.z < -0.01 else (1.0 - lo.z if lo.z > 1.0 else 0.0)
    if racine is not None:
        racine.location.z += dz; racine.location.x -= (lo.x + hi.x)/2; racine.location.y += 0.05 - lo.y
    else:
        for o in objets_mesh:
            if o.parent is None: o.location += Vector((-(lo.x + hi.x)/2, 0.05 - lo.y, dz))
    lo.z += dz; hi.z += dz; bpy.context.view_layer.update()
    dim = hi - lo; ctr = Vector((0, 0.05 + dim.y/2, lo.z + dim.z/2))
    dist = max(dim.x, dim.z*1.3, dim.y)*2.3 + 2.0
    cam = st['cam']; cam.location = ctr + Vector((0.55, 1.0, 0.42)).normalized()*dist
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for l in st['lights']: bpy.data.objects.remove(l)
    s = max(dim.length, 4)
    st['lights'] = [_area(ctr + Vector((s*0.8, s*1.2, s*1.1)), s*0.9, 90*s*s, ctr), _area(ctr + Vector((-s*1.2, s*0.9, s*0.4)), s*0.9, 25*s*s, ctr),
                    _area(ctr + Vector((0, -0.1, s*1.4)), s*0.6, 20*s*s, ctr)]
    bpy.context.scene.render.filepath = chemin; bpy.ops.render.render(write_still=True)
    return dim
