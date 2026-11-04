"""Export du kit vers Roblox.
Pour chaque objet : maillages regroupés par matière (une MeshPart par matière), transformations appliquées, réduction du nombre de
triangles au budget, export .glb (1 unité = 1 stud, devant de l'objet vers -Z Roblox), plus un manifeste JSON.
Les MeshParts sont nommées d'après leur matière, le script Studio leur applique ensuite l'apparence :
  T_<texture>_<RRGGBB>   texture PBR du kit teintée (SurfaceAppearance clonée depuis la bibliothèque « Matieres »)
  V_<RRGGBB>             verre (Material Glass, transparence)
  L_<RRGGBB>             liquide (Glass, transparence plus faible)
  P_<RRGGBB>_<r>_<m>_<e> matière unie (rugosité, métal, émission -> Neon)
MATIERES=1 exporte aussi matieres.glb : un carré par texture PBR, textures intégrées, à importer une seule fois."""
import bpy, bmesh, sys, os, math, time, json
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
import kit_meshes as K
import catalogue as C
NOMS = [n for n in os.environ.get('OBJETS', ','.join(C.REGISTRE)).split(',') if n]
BUDGET = {'lit_superpose': 9000, 'casiers': 6000, 'chaise': 3000, 'tabouret': 3000, 'chaise_bureau': 4000, 'etagere_specimens': 14000,
          'paillasse': 12000, 'paillasse_courte': 9000}
BUDGET_DEFAUT = int(os.environ.get('BUDGET', '12000')); MAX_MESH = 19000

def hexc(c): return '%02X%02X%02X' % tuple(int(round(v)) for v in c[:3])
def cle(m):
    if m is None: return 'P_C8C8C8_50_0_0'
    if m.get('tex'): return f"T_{m['tex']}_{hexc(m['tint'])}"
    if m.get('liquide'): return f"L_{hexc(m['liquide'])}"
    if m.get('verre'): return f"V_{hexc(m['col'])}"
    if m.get('plain'): return f"P_{hexc(m['col'])}_{int(m['rough']*100)}_{int(m['metal']*100)}_{int(m['emit'])}"
    return 'P_C8C8C8_50_0_0'

def triangles(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)

def reduire(ob, ratio):
    if ratio >= 0.999: return
    d = ob.modifiers.new('dec', 'DECIMATE'); d.decimate_type = 'COLLAPSE'; d.ratio = max(0.05, ratio); d.use_collapse_triangulate = True
    K.finir(ob, 35.0)

def exporter(nom):
    avant = set(bpy.data.objects)
    root = C.REGISTRE[nom](); bpy.context.view_layer.update()
    neufs = [o for o in bpy.data.objects if o not in avant]
    meshes = [o for o in neufs if o.type == 'MESH']
    for o in meshes:                                      # modificateurs appliqués, transformations figées dans le maillage
        if o.data.users > 1: o.data = o.data.copy()
        K.finir(o)
        o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix.Identity(4)
        if o.data.materials and o.data.materials[0] and o.data.materials[0].get('tex'): K.box_uv(o)
    groupes = {}
    for o in meshes:
        m = o.data.materials[0] if o.data.materials else None
        groupes.setdefault(cle(m), []).append(o)
    parts = []
    for k, objs in groupes.items():
        for o in bpy.context.selected_objects: o.select_set(False)
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active; ob.name = k; ob.data.name = k; parts.append(ob)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=0.05); me = bpy.data.meshes.new('Origine'); bm.to_mesh(me); bm.free()
    orig = bpy.data.objects.new('Origine', me); K.coll().objects.link(orig)       # repère d'origine (pied de l'objet) pour le script de placement
    tot = sum(triangles(p) for p in parts); budget = BUDGET.get(nom, BUDGET_DEFAUT)
    if tot > budget:                                       # réduction proportionnelle des gros maillages
        gros = [p for p in parts if triangles(p) > 400]; tg = sum(triangles(p) for p in gros); petit = tot - tg
        r = max(0.08, (budget - petit)/max(1, tg))
        for p in gros: reduire(p, r)
    for p in parts:
        n = triangles(p)
        if n > MAX_MESH: reduire(p, (MAX_MESH - 500)/n)
    tot2 = sum(triangles(p) for p in parts)
    # boîte englobante en coordonnées Roblox (X, Y, Z) = (x, z, -y)
    pts = [Vector(v.co) for p in parts for v in p.data.vertices]
    lo = Vector((min(v.x for v in pts), min(v.z for v in pts), min(-v.y for v in pts))); hi = Vector((max(v.x for v in pts), max(v.z for v in pts), max(-v.y for v in pts)))
    for o in bpy.context.selected_objects: o.select_set(False)
    for p in parts: p.select_set(True)
    orig.select_set(True)
    chemin = os.path.join(out, f'{nom}.glb')
    bpy.ops.export_scene.gltf(filepath=chemin, export_format='GLB', use_selection=True, export_materials='NONE', export_texcoords=True, export_normals=True,
                              export_yup=True, export_apply=True, export_animations=False)
    info = {'triangles_bruts': tot, 'triangles': tot2, 'parties': {p.name: triangles(p) for p in parts},
            'boite_min': [round(v, 3) for v in lo], 'boite_max': [round(v, 3) for v in hi], 'octets': os.path.getsize(chemin)}
    for o in [o for o in bpy.data.objects if o not in avant]: bpy.data.objects.remove(o)
    return info

def bibliotheque_matieres():
    """matieres.glb : un carré de 4×4 studs par texture, matériau glTF standard (couleur, métal-rugosité, normale) avec images intégrées"""
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    noms = sorted({f[:-len('_Couleur.png')] for f in os.listdir(K.TEX) if f.endswith('_Couleur.png')})
    for i, t in enumerate(noms):
        m = bpy.data.materials.new(t); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
        def img(sfx, nc):
            n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(K.TEX, f'{t}_{sfx}.png'), check_existing=True)
            if nc: n.image.colorspace_settings.name = 'Non-Color'
            return n
        L.new(img('Couleur', False).outputs['Color'], b.inputs['Base Color'])
        L.new(img('Rugosite', True).outputs['Color'], b.inputs['Roughness']); L.new(img('Metal', True).outputs['Color'], b.inputs['Metallic'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(img('Normale', True).outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
        bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
        uv = bm.loops.layers.uv.new('UV')
        for f in bm.faces:
            for l in f.loops: l[uv].uv = ((l.vert.co.x + 2)/4, (l.vert.co.y + 2)/4)
        me = bpy.data.meshes.new(t); bm.to_mesh(me); bm.free(); me.materials.append(m)
        ob = bpy.data.objects.new(t, me); bpy.context.scene.collection.objects.link(ob); ob.location = ((i % 5)*5, -(i//5)*5, 0)
    for o in bpy.data.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, 'matieres.glb'), export_format='GLB', use_selection=True, export_materials='EXPORT', export_image_format='AUTO')
    log(f'matieres.glb : {len(noms)} matières, {os.path.getsize(os.path.join(out, "matieres.glb"))//1024} Ko')

def materiau_depuis_nom(n):
    """reconstitue le matériau d'après le nom de la MeshPart (comme le fera le script Studio)"""
    import re
    m = re.match(r'^T_(.+)_([0-9A-F]{6})$', n)
    if m: return K.mat(m.group(1), tuple(int(m.group(2)[i:i + 2], 16) for i in (0, 2, 4)))
    m = re.match(r'^[VL]_([0-9A-F]{6})$', n)
    if m: return K.mat_verre('V' + m.group(1), tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)))
    m = re.match(r'^P_([0-9A-F]{6})_(\d+)_(\d+)_(\d+)$', n)
    if m: return K.mat_plain('P' + n, tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)), int(m.group(2))/100, int(m.group(3))/100, emit=float(m.group(4)))
    return None

def apercus(noms):
    """réimporte chaque .glb exporté, rhabille les pièces d'après leur nom et rend une vignette (contrôle de ce que reçoit Roblox)"""
    import studio
    st = studio.preparer(int(os.environ.get('ECH', '48')), (720, 560))
    for nom in noms:
        f = os.path.join(out, f'{nom}.glb')
        if not os.path.exists(f): continue
        avant = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=f)
        neufs = [o for o in bpy.data.objects if o not in avant]; mesh = [o for o in neufs if o.type == 'MESH']
        for o in mesh:
            base = o.name.split('.')[0]
            if base == 'Origine': o.hide_render = True; continue
            m = materiau_depuis_nom(base)
            if m: o.data.materials.clear(); o.data.materials.append(m)
        studio.photo(st, [o for o in mesh if not o.hide_render], None, os.path.join(out, f'apercu_{nom}.png'))
        for o in neufs: bpy.data.objects.remove(o)
        log(f'aperçu {nom}')

manifeste = {}
for nom in NOMS:
    t0 = time.time()
    try:
        manifeste[nom] = exporter(nom)
        i = manifeste[nom]; log(f"{nom}: {i['triangles_bruts']} -> {i['triangles']} triangles, {len(i['parties'])} parties, {i['octets']//1024} Ko ({time.time() - t0:.0f}s)")
    except Exception as ex:
        import traceback; traceback.print_exc(); log(f'{nom}: ERREUR {ex}')
json.dump(manifeste, open(os.path.join(out, 'manifeste.json'), 'w'), indent=1)
if os.environ.get('APERCU') == '1': apercus(NOMS)
if os.environ.get('MATIERES') == '1': bibliotheque_matieres()
log('fin')
