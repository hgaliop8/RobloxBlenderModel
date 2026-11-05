"""Architecture de Nadir-4 en maillages texturés (mode kit).
Reprend exactement la géométrie du générateur (murs, sols, plafonds, habillages, gaines, tuyaux…) pour les pièces « maillables »,
les regroupe par tronçon (salle ou couloir) et par matière teintée, applique la projection boîte (textures raccordées entre pièces
voisines) et exporte un .glb par secteur, en coordonnées réelles de la map (repère « Origine » au point 0,0,0).
VUES = liste de vues de contrôle à rendre (noms de tronçons) ; SECTEURS = secteurs à exporter."""
import bpy, bmesh, sys, os, math, time, json
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sys.argv_sauve = sys.argv; sys.argv = ['nadir_build']
import kit_meshes as K
import nadir_build as B, nadir_props as P
P.KIT = True; B.KIT = True
B.build_all(P.meubler)
items = [it for it in B.sc.items if B.est_maillable(it)]
log(f'{len(items)} pièces maillables sur {len(B.sc.items)}')
SECTEURS = [x for x in os.environ.get('SECTEURS', '').split(',') if x]

C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))          # Roblox (X, Y, Z) -> Blender (x, y, z) = (X, -Z, Y)
def vers_blender(p): return Vector((p[0], -p[2], p[1]))

def cle(it):
    m = it['m']; c = it['c']
    if m == 'Neon': return f"P_{'%02X%02X%02X' % tuple(c)}_30_0_4"
    if m == 'Glass': return f"V_{'%02X%02X%02X' % tuple(c)}"
    return f"T_{B.MAT_ARCHI[m]}_{'%02X%02X%02X' % tuple(c)}"

def ajouter(bm, it):
    """ajoute la pièce au bmesh, en coordonnées monde Blender"""
    R = Matrix(it['R']); p = Vector(it['p']); s = it['s']
    def W(v): return vers_blender(p + R @ Vector(v))
    if it['shape'] == 'Cylinder':
        L, d = s[0], min(s[1], s[2]); r = d/2; n = 10 if d < 0.5 else (16 if d < 2 else 28)
        ring = [[bm.verts.new(W((x, r*math.cos(2*math.pi*k/n), r*math.sin(2*math.pi*k/n)))) for k in range(n)] for x in (-L/2, L/2)]
        for k in range(n): bm.faces.new((ring[0][k], ring[0][(k + 1) % n], ring[1][(k + 1) % n], ring[1][k]))
        bm.faces.new(ring[0][::-1]); bm.faces.new(ring[1])
    else:
        hx, hy, hz = s[0]/2, s[1]/2, s[2]/2
        V = [bm.verts.new(W((x, y, z))) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            try: bm.faces.new([V[i] for i in f])
            except ValueError: pass

groupes = {}
for it in items:
    groupes.setdefault((B.troncon(it), cle(it)), []).append(it)
log(f'{len(groupes)} maillages (tronçon × matière)')

def materiau(k):
    import re
    m = re.match(r'^T_(.+)_([0-9A-F]{6})$', k)
    if m: return K.mat(m.group(1), tuple(int(m.group(2)[i:i + 2], 16) for i in (0, 2, 4)))
    m = re.match(r'^V_([0-9A-F]{6})$', k)
    if m: return K.mat_verre('V' + m.group(1), tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)))
    m = re.match(r'^P_([0-9A-F]{6})_(\d+)_(\d+)_(\d+)$', k)
    return K.mat_plain('P' + k, tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)), int(m.group(2))/100, int(m.group(3))/100, emit=float(m.group(4)))

par_secteur = {}; stats = {}
for (tr, k), its in sorted(groupes.items()):
    sect = tr.split('/')[1]
    if SECTEURS and sect not in SECTEURS: continue
    bm = bmesh.new()
    for it in its: ajouter(bm, it)
    me = bpy.data.meshes.new(k); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(k, me); K.coll().objects.link(ob); me.materials.append(materiau(k))
    for pl in me.polygons: pl.use_smooth = False
    if k.startswith('T_'): K.box_uv(ob)
    tri = sum(len(pl.vertices) - 2 for pl in me.polygons)
    if tri > 19000: log(f'  ATTENTION {tr} {k} : {tri} triangles')
    par_secteur.setdefault(sect, {}).setdefault(tr, []).append(ob); stats[tr] = stats.get(tr, 0) + tri
log('maillages construits')

for sect, trs in par_secteur.items():
    for o in bpy.context.selected_objects: o.select_set(False)
    bmo = bmesh.new(); bmesh.ops.create_cube(bmo, size=0.05); me = bpy.data.meshes.new('Origine'); bmo.to_mesh(me); bmo.free()
    orig = bpy.data.objects.new('Origine', me); K.coll().objects.link(orig); orig.select_set(True)
    for tr, obs in trs.items():
        g = K.empty(tr.split('/')[-1]); g.select_set(True)
        for o in obs: o.parent = g; o.select_set(True)
    nom = 'archi_' + sect.lower().replace('é', 'e')
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, nom + '.glb'), export_format='GLB', use_selection=True, export_materials='NONE', export_texcoords=True,
                              export_normals=True, export_yup=True, export_apply=True, export_animations=False)
    nm = sum(len(v) for v in trs.values()); nt = sum(stats[t] for t in trs)
    log(f'{nom}.glb : {len(trs)} tronçons, {nm} maillages, {nt} triangles, {os.path.getsize(os.path.join(out, nom + ".glb"))//1024} Ko')
    bpy.data.objects.remove(orig)

# ---------------------------------------------------------------- vues de contrôle : architecture maillée + kit 3D posé sur les emplacements
VUES = [v for v in os.environ.get('VUES', '').split(',') if v]
if VUES:
    import catalogue as CAT
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('ECH', '48')); sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1200, 675
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = float(os.environ.get('EXPO', '0'))
    w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.005, 0.006, 1); sc.world = w
    def M_blender(it):
        R = Matrix(it['R']); Mb = (C @ R @ C.transposed()).to_4x4(); Mb.translation = vers_blender(it['p']); return Mb
    dossiers = [B.BYID[v].folder for v in VUES if v in B.BYID]
    dans = lambda it: any(it['f'].startswith(d) for d in dossiers)
    cache = {}
    def modele(nom):
        if nom not in cache:
            r = CAT.REGISTRE[nom](); bpy.context.view_layer.update()
            enfants = [c for c in r.children if c.type == 'MESH']
            for c in enfants:
                if c.data.materials and c.data.materials[0].get('tex') and c.data.users == 1: K.box_uv(c)
            r.location = (0, 0, -5000); bpy.context.view_layer.update(); cache[nom] = (r, enfants)
        return cache[nom]
    n_pl = 0
    for it in B.sc.items:
        if not dans(it): continue
        if it['n'].startswith('Kit:'):
            nom = it['n'][4:]
            if nom not in CAT.REGISTRE: log(f'  kit manquant : {nom}'); continue
            r, enfants = modele(nom); Mp = M_blender(it); inv = r.matrix_world.inverted()
            for c in enfants:
                d = c.copy(); K.coll().objects.link(d); d.parent = None; d.matrix_world = Mp @ inv @ c.matrix_world
            n_pl += 1
        elif not B.est_maillable(it) and '/Objet_' not in it['f'] and it['t'] < 0.99 and it['cls'] in ('Part', 'SpawnLocation'):
            bm = bmesh.new(); ajouter(bm, it); me = bpy.data.meshes.new(it['n']); bm.to_mesh(me); bm.free()
            col = tuple(it['c']); emis = 3.0 if it['m'] == 'Neon' else 0.0
            if it['m'] == 'Glass' or it['t'] > 0.2: m = K.mat_verre('VP%02X%02X%02X' % col, col)
            else: m = K.mat_plain('BP%02X%02X%02X_%d' % (*col, emis), col, 0.4, 0.5 if it['m'] in ('Metal', 'DiamondPlate') else 0.0, emit=emis)
            me.materials.append(m); ob = bpy.data.objects.new(it['n'], me); K.coll().objects.link(ob)
        if it['ch'] and it['tags'] and 'LumiereNormale' in it['tags']:
            ld = bpy.data.lights.new('L', 'AREA'); ld.size = 3.0; ld.energy = float(os.environ.get('PUIS', '500')); ld.color = (1.0, 0.96, 0.9)
            ob = bpy.data.objects.new('L', ld); sc.collection.objects.link(ob); ob.location = vers_blender(it['p']) + Vector((0, 0, -0.5))
    for r, enf in cache.values():
        for c in enf: c.hide_render = True
    log(f'{n_pl} objets du kit posés pour les vues')
    for v in VUES:
        e = B.BYID.get(v)
        if e is None: log(f'vue {v} : tronçon introuvable'); continue
        cd = bpy.data.cameras.new(v); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(70); cam = bpy.data.objects.new(v, cd); sc.collection.objects.link(cam); sc.camera = cam
        X0, Z0, X1, Z1, y = e.X0, e.Z0, e.X1, e.Z1, e.elev
        eye = vers_blender((X0 + 2.5, y + 5.2, Z0 + 2.5)); tgt = vers_blender(((X0 + X1)/2 + (X1 - X0)*0.15, y + 3.4, (Z0 + Z1)/2 + (Z1 - Z0)*0.15))
        cam.location = eye; cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, f'vue_{v}.png'); bpy.ops.render.render(write_still=True); log(f'vue {v}')
json.dump(stats, open(os.path.join(out, 'triangles_par_troncon.json'), 'w'), indent=1)
log('fin')
