"""Kit de modèles 3D pour Nadir-4 (Blender). Unités : 1 unité Blender = 1 stud Roblox. Z en haut.
Chaque objet du kit est un ensemble de maillages, un par matière (Roblox : un SurfaceAppearance par MeshPart).
UV : projection « boîte » à l'échelle du monde, une répétition de texture tous les TILE studs (textures raccordables)."""
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, noise

TEX = os.path.join(os.getcwd(), 'data', 'textures')
TILE = {'metal_peint': 6, 'metal_brut': 6, 'metal_rouille': 6, 'tole_striee': 6, 'beton': 10, 'vinyle': 8, 'carrelage': 6, 'moquette': 8, 'tissu': 3,
        'matelas': 4, 'bois': 6, 'plastique': 5, 'peinture_mur': 10, 'plafond': 8, 'caoutchouc': 4, 'simili_cuir': 3, 'carton': 4, 'grille_vent': 3}

def coll():
    c = bpy.data.collections.get('Kit')
    if not c: c = bpy.data.collections.new('Kit'); bpy.context.scene.collection.children.link(c)
    return c

# ---------------------------------------------------------------- matériaux PBR
def srgb2lin(c): return tuple(((x + 0.055)/1.055)**2.4 if x > 0.04045 else x/12.92 for x in c)
_MATS = {}
def mat(tex, tint=(1, 1, 1), emit=None, name=None):
    key = name or f'{tex}_{tint}_{emit}'
    if key in _MATS: return _MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree; L = nt.links; b = nt.nodes['Principled BSDF']
    def img(suffix, noncolor):
        n = nt.nodes.new('ShaderNodeTexImage'); p = os.path.join(TEX, f'{tex}_{suffix}.png')
        n.image = bpy.data.images.load(p, check_existing=True)
        if noncolor: n.image.colorspace_settings.name = 'Non-Color'
        return n
    c = img('Couleur', False); r = img('Rugosite', True); mt = img('Metal', True); nm = img('Normale', True)
    tn = nt.nodes.new('ShaderNodeMix'); tn.data_type = 'RGBA'; tn.blend_type = 'MULTIPLY'; tn.inputs[0].default_value = 1.0
    A = [i for i in tn.inputs if i.name == 'A' and i.type == 'RGBA'][0]; Bk = [i for i in tn.inputs if i.name == 'B' and i.type == 'RGBA'][0]
    R = [o for o in tn.outputs if o.name == 'Result' and o.type == 'RGBA'][0]
    L.new(c.outputs['Color'], A); Bk.default_value = (*srgb2lin(tint), 1); L.new(R, b.inputs['Base Color'])
    L.new(r.outputs['Color'], b.inputs['Roughness']); L.new(mt.outputs['Color'], b.inputs['Metallic'])
    nmap = nt.nodes.new('ShaderNodeNormalMap'); L.new(nm.outputs['Color'], nmap.inputs['Color']); L.new(nmap.outputs['Normal'], b.inputs['Normal'])
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb2lin(emit[0]), 1); b.inputs['Emission Strength'].default_value = emit[1]
    m['tex'] = tex; m['tint'] = list(tint)
    _MATS[key] = m; return m

def mat_plain(name, col, rough=0.5, metal=0.0, emit=0.0, alpha=1.0, transmission=0.0):
    if name in _MATS: return _MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb2lin(col), 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*srgb2lin(col), 1); b.inputs['Emission Strength'].default_value = emit
    if transmission: b.inputs['Transmission Weight'].default_value = transmission
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    _MATS[name] = m; return m

# ---------------------------------------------------------------- utilitaires maillage
def obj_from_bm(bm, name, material, smooth=True, uv=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll().objects.link(ob); me.materials.append(material)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return ob

def box_uv(ob, tile=None):
    """projection boîte en coordonnées monde (raccord parfait entre objets voisins)"""
    me = ob.data; t = tile or TILE.get(me.materials[0].get('tex', ''), 6)
    if not me.uv_layers: me.uv_layers.new(name='UV')
    uvl = me.uv_layers.active.data; M = ob.matrix_world; R = M.to_3x3()
    for p in me.polygons:
        n = (R @ p.normal); ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            v = M @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0: u, w = v.y, v.z
            elif ax == 1: u, w = v.x, v.z
            else: u, w = v.x, v.y
            uvl[li].uv = (u/t, w/t)

def bevel(ob, w=0.05, seg=2, limit='ANGLE'):
    m = ob.modifiers.new('bv', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = limit; m.angle_limit = math.radians(40); m.harden_normals = False
    return m

def apply_mods(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True)
    for m in list(ob.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as ex: print('modif', m.name, ex)

def cube(name, size, loc, material, bev=0.04, seg=2, rot=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*size[0], v.co.y*size[1], v.co.z*size[2]))
    ob = obj_from_bm(bm, name, material); ob.location = loc
    if rot: ob.rotation_euler = rot
    if bev: bevel(ob, bev, seg)
    return ob

def tube(name, a, b, r, material, seg=12):
    a, b = Vector(a), Vector(b); d = b - a
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    ob = obj_from_bm(bm, name, material); ob.location = (a + b)/2; ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return ob

def tube_path(name, pts, r, material, seg=10):
    """tube le long d'une polyligne (coudes arrondis par la courbe)"""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, q in zip(sp.bezier_points, pts):
        p.co = q; p.handle_left_type = p.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu); coll().objects.link(ob); cu.materials.append(material)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True); bpy.ops.object.convert(target='MESH')
    return bpy.context.view_layer.objects.active

def join(objs, name):
    objs = [o for o in objs if o]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in objs: apply_mods(o)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); ob = bpy.context.view_layer.objects.active; ob.name = name
    return ob

def parent_all(objs, root):
    for o in objs:
        if o and o is not root:
            mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw

def empty(name, loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); coll().objects.link(e); e.location = loc; e.rotation_euler = rot; return e

# ---------------------------------------------------------------- formes organiques
def oreiller(name, L=2.0, W=1.25, H=0.55, seed=0, material=None):
    """oreiller : boîte subdivisée gonflée au centre, coins pincés, creux de tête, plis"""
    # construction directe : surface paramétrique fermée
    bm = bmesh.new(); nu, nv = 28, 18; rnd = random.Random(seed)
    verts = {}
    def P(u, v, side):
        x = (u - 0.5)*L; y = (v - 0.5)*W
        e = (1 - (2*u - 1)**2)**0.6*(1 - (2*v - 1)**2)**0.6           # gonflement
        corner = (abs(2*u - 1)**6 + abs(2*v - 1)**6)                  # coins pincés
        z = side*H/2*(e - 0.15*corner)
        if side > 0:
            z -= 0.12*H*math.exp(-((x/(L*0.28))**2 + (y/(W*0.3))**2))           # creux de tête
        n = noise.noise(Vector((x*2.2 + seed, y*2.2, side*0.5)))*0.04*e + noise.noise(Vector((x*7, y*7 + seed, side)))*0.012*e
        return Vector((x*(1 - 0.06*e*abs(2*v - 1)), y*(1 - 0.04*e), z + n))
    for side in (1, -1):
        for i in range(nu + 1):
            for j in range(nv + 1):
                if side < 0 and (i in (0, nu) or j in (0, nv)): verts[(side, i, j)] = verts[(1, i, j)]; continue
                verts[(side, i, j)] = bm.verts.new(P(i/nu, j/nv, side))
    for side in (1, -1):
        for i in range(nu):
            for j in range(nv):
                q = [verts[(side, i, j)], verts[(side, i + 1, j)], verts[(side, i + 1, j + 1)], verts[(side, i, j + 1)]]
                bm.faces.new(q if side > 0 else q[::-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    ob = obj_from_bm(bm, name, material); return ob

def tissu_simule(name, L, W, z0, colliders, material, seed=0, frames=34, thick=0.06, res=0.16, drop_noise=0.12, pin_head=False, centre=(0, 0), rot=0.0):
    """couverture : plan subdivisé lâché sur les objets « colliders », simulation de tissu, puis figé"""
    nu, nv = max(4, int(L/res)), max(4, int(W/res))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=nu, y_segments=nv, size=0.5)
    rnd = random.Random(seed)
    for v in bm.verts:
        x, y = v.co.x*L, v.co.y*W
        c, s_ = math.cos(rot), math.sin(rot)
        v.co = Vector((centre[0] + x*c - y*s_, centre[1] + x*s_ + y*c, z0 + noise.noise(Vector((x*0.7 + seed, y*0.7, 0)))*drop_noise + noise.noise(Vector((x*2.1, y*2.1 + seed, 1)))*drop_noise*0.4))
    ob = obj_from_bm(bm, name, material)
    for c in colliders:
        m = c.modifiers.new('col', 'COLLISION'); c.collision.thickness_outer = 0.02; c.collision.cloth_friction = 8
    cl = ob.modifiers.new('tissu', 'CLOTH'); s = cl.settings
    s.quality = 6; s.mass = 0.4; s.tension_stiffness = 12; s.compression_stiffness = 12; s.shear_stiffness = 6; s.bending_stiffness = 0.6
    s.air_damping = 2.0; cl.collision_settings.use_self_collision = True; cl.collision_settings.distance_min = 0.012; cl.collision_settings.self_distance_min = 0.01
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames
    sc = bpy.context.scene
    for f in range(1, frames + 1): sc.frame_set(f)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=cl.name)
    sc.frame_set(1)
    for c in colliders:
        for m in [m for m in c.modifiers if m.type == 'COLLISION']: c.modifiers.remove(m)
    so = ob.modifiers.new('ep', 'SOLIDIFY'); so.thickness = thick; so.offset = 1.0
    sb = ob.modifiers.new('sub', 'SUBSURF'); sb.levels = 1; sb.render_levels = 1
    for p in ob.data.polygons: p.use_smooth = True
    return ob
