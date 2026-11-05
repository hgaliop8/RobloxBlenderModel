"""Traces de l'incident et derniers objets (Nadir-4) : mobilier renversé, papiers au sol, carton éventré, éclats de verre,
flaques, sang séché, aquarium brisé ; écran mural, interphone, coffret électrique, banc de vestiaire, banc de musculation,
lave-linge. Convention : origine au sol ; objets muraux dos à y = 0 et façade vers +Y ; objets au sol centrés."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from kit_meshes import *
from kit_labo import M_inox, M_chrome, aquarium as _aquarium
import kit_quartiers as Q
import kit_vie as V
import kit_tech as T

# ---------------------------------------------------------------- outils : poser un objet couché au sol
def coucher(root, rot, dz=0.0):
    """fait pivoter un objet construit (racine + enfants) puis le repose sur le sol (z min = dz)"""
    root.rotation_euler = rot; bpy.context.view_layer.update()
    pts = [c.matrix_world @ Vector(b) for c in root.children if c.type == 'MESH' for b in c.bound_box]
    root.location.z -= min(p.z for p in pts) - dz
    cx = sum(p.x for p in pts)/len(pts); cy = sum(p.y for p in pts)/len(pts)
    root.location.x -= cx; root.location.y -= cy
    bpy.context.view_layer.update()
    # aplatir la hiérarchie dans une nouvelle racine sans rotation (le kit attend des enfants directs)
    r2 = empty(root.name + '_couche'); enf = list(root.children)
    parent_all(enf, r2); bpy.data.objects.remove(root); return r2

def tache_plate(name, R, loc, material, seed=0, rug=0.45, n=48, z=0.012, etire=(1, 1)):
    """forme plate irrégulière (flaque, tache) : disque au contour bruité, légèrement bombé"""
    bm = bmesh.new(); c = bm.verts.new((0, 0, z + 0.004)); ring = []
    for k in range(n):
        a = 2*math.pi*k/n
        r = R*(1 + rug*noise.noise(Vector((math.cos(a)*1.3 + seed, math.sin(a)*1.3, 0.5))) + 0.15*rug*noise.noise(Vector((math.cos(a)*4, math.sin(a)*4 + seed, 1))))
        ring.append(bm.verts.new((r*math.cos(a)*etire[0], r*math.sin(a)*etire[1], z)))
    for k in range(n): bm.faces.new((c, ring[k], ring[(k + 1) % n]))
    ob = obj_from_bm(bm, name, material); ob.location = loc; return ob

# ---------------------------------------------------------------- mobilier renversé
def chaise_renversee(seed=0):
    rnd = random.Random(seed)
    r = Q.chaise(seed=seed, col=rnd.choice([(66, 88, 120), (120, 60, 50), (70, 100, 80)]))
    return coucher(r, (rnd.choice([math.pi/2, -math.pi/2]), 0, rnd.uniform(0, 6.28)))

def chaise_bureau_renversee(seed=0):
    rnd = random.Random(seed); r = V.chaise_bureau(seed)
    return coucher(r, (0, math.pi/2 + rnd.uniform(-0.1, 0.1), rnd.uniform(0, 6.28)))

def tabouret_renverse(seed=0):
    rnd = random.Random(seed); r = __import__('kit_labo').tabouret(seed)
    return coucher(r, (math.pi/2 - 0.25, 0, rnd.uniform(0, 6.28)))

def etagere_renversee(seed=0):
    """rayonnage tombé face contre terre, cartons et bacs répandus autour"""
    rnd = random.Random(seed); r = T.etagere_stockage(6.0, 2.0, 7.0, seed=seed)
    r = coucher(r, (-math.pi/2 + 0.12, 0, 0), dz=0.0)
    o = list(r.children)
    for k in range(rnd.randint(4, 7)):
        L = rnd.uniform(0.8, 1.5); H = rnd.uniform(0.6, 1.1)
        o.append(cube('Carton', (L, rnd.uniform(0.9, 1.4), H), (rnd.uniform(-3.5, 3.5), rnd.uniform(2.2, 4.5), H/2), mat('carton', (190, 156, 110)), 0.03,
                      rot=(rnd.choice([0, 0, math.pi/2]), 0, rnd.uniform(0, 3))))
    for k in range(2): o += T.bac_plastique((rnd.uniform(-3, 3), rnd.uniform(-3.5, -2.0), 0), rnd, rnd.uniform(0, 3))
    for c in o: c.parent = None
    root = empty(f'EtagereRenversee_{seed}'); parent_all(o, root); bpy.data.objects.remove(r); return root

# ---------------------------------------------------------------- papiers, carton, verre
def feuille_courbe(name, loc, rot, material, rnd, w=0.75, h=1.05):
    bm = bmesh.new(); nu, nv = 6, 8; Vt = {}
    k1, k2 = rnd.uniform(-0.12, 0.12), rnd.uniform(0, 0.18)
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i/nu - 0.5, j/nv - 0.5
            z = k1*(u*u) + k2*max(0, v)**2*2 + 0.01*noise.noise(Vector((u*5, v*5, rnd.random()*9)))
            Vt[(i, j)] = bm.verts.new((u*w, v*h, z + 0.008))
    for i in range(nu):
        for j in range(nv): bm.faces.new((Vt[(i, j)], Vt[(i + 1, j)], Vt[(i + 1, j + 1)], Vt[(i, j + 1)]))
    ob = obj_from_bm(bm, name, material); ob.location = loc; ob.rotation_euler = (0, 0, rot); return ob

def papiers_sol(seed=0, rayon=2.5):
    rnd = random.Random(seed); root = empty(f'PapiersSol_{seed}'); o = []
    Mp = [mat('plastique', c) for c in ((236, 234, 226), (240, 236, 210), (226, 232, 236), (230, 228, 220))]
    for k in range(rnd.randint(9, 16)):
        a = rnd.uniform(0, 6.28); r = rayon*math.sqrt(rnd.random())
        o.append(feuille_courbe('Feuille', (r*math.cos(a), r*math.sin(a), k*0.003), rnd.uniform(0, 6.28), rnd.choice(Mp), rnd))
    if rnd.random() < 0.6:
        o.append(cube('Classeur', (0.35, 1.0, 1.25), (rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0.18), mat('simili_cuir', rnd.choice([(40, 60, 120), (130, 40, 40)])), 0.02,
                      rot=(math.pi/2, 0, rnd.uniform(0, 3))))
    if rnd.random() < 0.5:
        o.append(revolution('Mug', [(0.0, 0.0), (0.15, 0.0), (0.16, 0.02), (0.17, 0.34)], mat('plastique', (230, 230, 226)), 20, (0, 0, 0), ferme_haut=False))
        o[-1].rotation_euler = (math.pi/2, 0, rnd.uniform(0, 6.28)); o[-1].location = (rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), 0.17)
    parent_all(o, root); return root

def carton_renverse(seed=0):
    """carton ouvert couché sur le flanc, rabats ouverts, contenu répandu"""
    rnd = random.Random(seed); root = empty(f'CartonRenverse_{seed}'); o = []; L, W, H = 1.6, 1.2, 1.1; Mc = mat('carton', (190, 156, 110))
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*L, v.co.y*W, v.co.z*H))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.x > 0.5], context='FACES')
    c = obj_from_bm(bm, 'Carton', Mc, smooth=False); c.modifiers.new('ep', 'SOLIDIFY').thickness = 0.03; c.location = (0, 0, W/2); c.rotation_euler = (math.pi/2, 0, 0); o.append(c)
    for s in (-1, 1):
        o.append(cube('Rabat', (0.55, 0.02, H*0.95), (L/2 + 0.25, s*0.0, W/2 + s*W*0.48), Mc, 0.0, rot=(0, s*0.5, 0)))
    for k in range(rnd.randint(4, 8)):
        o.append(cube('Contenu', (rnd.uniform(0.25, 0.6), rnd.uniform(0.25, 0.5), rnd.uniform(0.1, 0.35)), (L/2 + rnd.uniform(0.3, 2.2), rnd.uniform(-1.0, 1.0), 0.1),
                      mat('carton', rnd.choice([(226, 226, 220), (200, 170, 120), (120, 150, 190)])), 0.02, rot=(0, 0, rnd.uniform(0, 3))))
    for k in range(rnd.randint(3, 6)):
        o.append(feuille_courbe('Feuille', (L/2 + rnd.uniform(0.5, 2.5), rnd.uniform(-1.4, 1.4), 0.0), rnd.uniform(0, 6.28), mat('plastique', (236, 234, 226)), rnd))
    parent_all(o, root); return root

def eclats_verre(seed=0, rayon=2.2, n=None, root_nom=None):
    rnd = random.Random(seed); root = empty(root_nom or f'EclatsVerre_{seed}'); o = []; Vg = mat_verre()
    bm = bmesh.new()
    for k in range(n or rnd.randint(25, 45)):
        a = rnd.uniform(0, 6.28); r = rayon*rnd.random()**0.7; s = rnd.uniform(0.06, 0.35)*(1.6 if rnd.random() < 0.15 else 1)
        cx, cy = r*math.cos(a), r*math.sin(a); b = rnd.uniform(0, 6.28)
        pts = [(cx + s*math.cos(b + j*2.1 + rnd.uniform(-0.5, 0.5))*rnd.uniform(0.5, 1.2), cy + s*math.sin(b + j*2.1 + rnd.uniform(-0.5, 0.5))*rnd.uniform(0.5, 1.2)) for j in range(3)]
        lo = [bm.verts.new((x, y, 0.005)) for x, y in pts]; hi = [bm.verts.new((x, y, 0.035)) for x, y in pts]
        bm.faces.new(hi); bm.faces.new(lo[::-1])
        for j in range(3): bm.faces.new((lo[j], lo[(j + 1) % 3], hi[(j + 1) % 3], hi[j]))
    o.append(obj_from_bm(bm, 'Eclats', Vg, smooth=False))
    parent_all(o, root); return root

# ---------------------------------------------------------------- liquides
def flaque_eau(seed=0, R=2.2):
    rnd = random.Random(seed); root = empty(f'FlaqueEau_{seed}')
    o = [tache_plate('Flaque', R, (0, 0, 0), mat_liquide('EauSol', (110, 140, 140), 0.3), seed=rnd.uniform(0, 50), rug=0.4, etire=(rnd.uniform(1.0, 1.6), 1))]
    for k in range(rnd.randint(2, 5)):
        a = rnd.uniform(0, 6.28); d = R*rnd.uniform(1.2, 1.9)
        o.append(tache_plate('Goutte', R*rnd.uniform(0.08, 0.25), (d*math.cos(a), d*math.sin(a), 0), mat_liquide('EauSol', (110, 140, 140), 0.3), seed=rnd.uniform(0, 50), rug=0.3))
    parent_all(o, root); return root

SANG = (78, 16, 12); SANG_SEC = (58, 20, 16)
def tache_sang(seed=0, R=1.2):
    """sang séché : tache principale sombre, éclaboussures, quelques gouttes"""
    rnd = random.Random(seed); root = empty(f'TacheSang_{seed}'); Ms = mat_plain('SangSeche', SANG_SEC, rough=0.5)
    o = [tache_plate('Tache', R, (0, 0, 0), Ms, seed=rnd.uniform(0, 50), rug=0.55)]
    for k in range(rnd.randint(5, 10)):
        a = rnd.uniform(0, 6.28); d = R*rnd.uniform(1.1, 2.4)
        o.append(tache_plate('Goutte', rnd.uniform(0.05, 0.18), (d*math.cos(a), d*math.sin(a), 0), Ms, seed=rnd.uniform(0, 50), rug=0.3, n=12, etire=(rnd.uniform(1, 2.2), 1)))
    parent_all(o, root); return root

def trainee_sang(seed=0, L=6.0):
    """traînée : bande irrégulière qui s'amincit, comme un corps tiré"""
    rnd = random.Random(seed); root = empty(f'TraineeSang_{seed}'); Ms = mat_plain('SangSeche', SANG_SEC, rough=0.5)
    bm = bmesh.new(); prev = None; n = 40
    for i in range(n + 1):
        t = i/n; x = (t - 0.5)*L; yc = 0.4*noise.noise(Vector((t*2 + seed, 0, 0)))
        w = 0.55*(1 - 0.7*t)*(1 + 0.4*noise.noise(Vector((t*9, seed, 1))))
        a, b = bm.verts.new((x, yc - w/2, 0.012)), bm.verts.new((x, yc + w/2, 0.012))
        if prev: bm.faces.new((prev[0], a, b, prev[1]))
        prev = (a, b)
    o = [obj_from_bm(bm, 'Trainee', Ms), tache_plate('Tache', 0.9, (-L/2 - 0.3, 0, 0), Ms, seed=seed, rug=0.5)]
    for k in range(rnd.randint(3, 7)): o.append(tache_plate('Empreinte', 0.13, (rnd.uniform(-L/2, L/2), rnd.uniform(-1.0, 1.0), 0), Ms, seed=rnd.uniform(0, 50), rug=0.25, n=12, etire=(1.8, 1)))
    parent_all(o, root); return root

# ---------------------------------------------------------------- aquarium brisé
def aquarium_brise(seed=0):
    """aquarium dont la vitre avant a éclaté : bris en dents de scie, eau presque vidée, flaque et éclats devant, sable répandu"""
    rnd = random.Random(seed); r = _aquarium(seed=seed)
    w, d, h, hb = 8.0, 3.0, 3.6, 2.8
    o = list(r.children)
    for c in o: c.parent = None
    bpy.data.objects.remove(r)
    for c in [c for c in o if c.name.startswith('Bac') or c.name.startswith('Eau')]: o.remove(c); bpy.data.objects.remove(c)
    Vg = mat_verre()
    # bac sans face avant + face avant cassée (contour gardé, trou déchiqueté)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*w, v.co.y*d, v.co.z*h))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5 or f.normal.y > 0.5], context='FACES')
    bac = obj_from_bm(bm, 'Bac', Vg, smooth=False); bac.location = (0, d/2, hb + h/2); bac.modifiers.new('ep', 'SOLIDIFY').thickness = 0.06; o.append(bac)
    bm = bmesh.new(); n = 56; cx, cz = rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3)
    outer, inner = [], []
    for k in range(n):
        a = 2*math.pi*k/n; ca, sa = math.cos(a), math.sin(a)
        tx = (w/2 - abs(cx)*0 - 0.05)/max(1e-6, abs(ca)) if abs(ca) > 1e-6 else 1e9; tz = (h/2 - 0.05)/max(1e-6, abs(sa)) if abs(sa) > 1e-6 else 1e9
        t = min(tx, tz); ox, oz = t*ca, t*sa
        f = rnd.uniform(0.62, 0.92) if k % 2 else rnd.uniform(0.75, 0.97)
        outer.append(bm.verts.new((ox, 0, oz))); inner.append(bm.verts.new((cx*(1 - f) + ox*f, 0, cz*(1 - f) + oz*f)))
    for k in range(n): bm.faces.new((outer[k], outer[(k + 1) % n], inner[(k + 1) % n], inner[k]))
    vit = obj_from_bm(bm, 'VitreBrisee', Vg, smooth=False); vit.location = (0, d, hb + h/2); vit.modifiers.new('ep', 'SOLIDIFY').thickness = 0.05; o.append(vit)
    o.append(cube('Eau', (w - 0.14, d - 0.14, 0.35), (0, d/2, hb + 0.03 + 0.175), mat_liquide('EauAquarium', (170, 214, 210), 0.05), 0))
    f = flaque_eau(seed, 3.0); f.location = (0, d + 2.6, 0); bpy.context.view_layer.update()
    e = eclats_verre(seed + 1, 2.6); e.location = (0, d + 2.2, 0); bpy.context.view_layer.update()
    for g in (f, e):
        for c in list(g.children): o.append(c)
    s = tache_plate('SableRepandu', 1.4, (rnd.uniform(-1, 1), d + 0.9, 0.0), mat('beton', (190, 176, 150)), seed=seed, rug=0.4, z=0.02, etire=(1.6, 0.8)); o.append(s)
    root = empty(f'AquariumBrise_{seed}'); parent_all(o, root)
    for g in (f, e): bpy.data.objects.remove(g)
    return root

# ---------------------------------------------------------------- derniers objets muraux et de salle
def ecran_mural(w=6.0, h=3.4, seed=0, allume=False):
    """grand écran mural sur support (centré sur z = 0, dos à y = 0)"""
    root = empty(f'EcranMural_{int(w)}'); o = []; Mn = mat('plastique', (28, 28, 30))
    o.append(cube('Support', (min(2.0, w*0.3), 0.15, min(1.6, h*0.5)), (0, 0.075, 0), mat('metal_peint', (40, 40, 42)), 0.02))
    o.append(cube('Cadre', (w, 0.3, h), (0, 0.3, 0), Mn, 0.05))
    o.append(cube('Dalle', (w - 0.2, 0.02, h - 0.2), (0, 0.46, 0), mat_plain('DalleOn' if allume else 'DalleOff', (60, 110, 120) if allume else (8, 9, 10), 0.08, emit=1.6 if allume else 0.0), 0))
    o.append(cube('Logo', (0.4, 0.02, 0.06), (0, 0.46, -h/2 + 0.06), mat('metal_brut', (160, 160, 160)), 0))
    parent_all(o, root); return root

def interphone(seed=0):
    rnd = random.Random(seed); root = empty('Interphone'); o = []; z = 5.0
    o.append(cube('Boitier', (0.9, 0.25, 1.4), (0, 0.125, z), mat('metal_peint', (60, 64, 68)), 0.06))
    o.append(cube('Grille', (0.6, 0.02, 0.45), (0, 0.26, z + 0.3), mat('grille_vent', (90, 90, 90)), 0.0))
    o.append(cube('Ecran', (0.5, 0.02, 0.22), (0, 0.26, z - 0.08), mat_plain('LCD', (20, 40, 30), 0.2), 0.0))
    o.append(cyl('Bouton', 0.09, 0.06, (-0.18, 0.25, z - 0.42), mat_plain('BoutonInterphone', (255, 160, 40), 0.3, emit=2.0), 16, axe='Y'))
    o.append(cyl('Bouton', 0.07, 0.05, (0.18, 0.25, z - 0.42), mat('plastique', (30, 30, 30)), 16, axe='Y'))
    o.append(tube_path('Cable', [Vector((0.3, 0.06, z + 0.7)), Vector((0.32, 0.06, z + 1.4)), Vector((0.32, 0.06, z + 3.0))], 0.035, mat('caoutchouc', (30, 30, 30))))
    parent_all(o, root); return root

def coffret_elec(seed=0):
    rnd = random.Random(seed); root = empty('CoffretElec'); o = []; z = 4.5; Mc = mat('metal_peint', (150, 156, 150))
    o.append(cube('Coffret', (1.8, 0.55, 2.4), (0, 0.3, z), Mc, 0.05))
    o.append(cube('Porte', (1.7, 0.05, 2.3), (0, 0.6, z), mat('metal_peint', (160, 166, 160)), 0.02))
    for sz in (-0.7, 0.7): o.append(cube('Charniere', (0.08, 0.08, 0.25), (-0.86, 0.62, z + sz), M_chrome(), 0.01))
    o.append(cube('Serrure', (0.1, 0.06, 0.3), (0.7, 0.64, z), mat('plastique', (30, 30, 30)), 0.02))
    o.append(cube('Danger', (0.45, 0.01, 0.4), (0, 0.63, z + 0.6), mat('plastique', (210, 170, 40)), 0.0))
    parent_all(o, root); return root

def banc_vestiaire(L=8.0, seed=0):
    rnd = random.Random(seed); root = empty('BancVestiaire'); o = []; Mb = mat('bois', (180, 140, 96))
    for k in range(3): o.append(cube('Latte', (L, 0.42, 0.12), (0, -0.5 + k*0.5, 1.45), Mb, 0.03))
    for x in (-L/2 + 0.6, 0, L/2 - 0.6):
        o.append(cube('Pied', (0.14, 1.3, 0.12), (x, 0, 1.33), mat('metal_peint', (60, 64, 70)), 0.02))
        o.append(cube('Pied', (0.14, 0.14, 1.3), (x, 0, 0.67), mat('metal_peint', (60, 64, 70)), 0.02))
        o.append(cube('Patin', (0.3, 1.2, 0.08), (x, 0, 0.04), mat('caoutchouc', (40, 40, 40)), 0.02))
    if rnd.random() < 0.7:
        o.append(cube('Serviette', (1.0, 0.8, 0.12), (rnd.uniform(-2, 2), 0, 1.57), mat('tissu', rnd.choice([(220, 220, 210), (60, 100, 160)])), 0.06, 3))
    parent_all(o, root); return root

def banc_musculation(seed=0):
    rnd = random.Random(seed); root = empty('BancMuscu'); o = []; Mn = mat('metal_peint', (40, 40, 42)); Mc = M_chrome()
    o.append(V.coussin('Assise', 1.1, 5.2, 0.35, (0, 0, 1.75), mat('simili_cuir', (30, 30, 32)), seed))
    o.append(cube('Poutre', (0.3, 5.0, 0.25), (0, 0, 1.4), Mn, 0.03))
    for y in (-2.2, 2.2):
        o.append(cube('Pied', (0.25, 0.25, 1.4), (0, y, 0.7), Mn, 0.03)); o.append(cube('Patin', (2.0, 0.3, 0.2), (0, y, 0.1), Mn, 0.03))
    for sx in (-1, 1):
        o.append(tube('Montant', (sx*1.3, 2.0, 0.1), (sx*1.3, 2.0, 4.6), 0.1, Mn)); o.append(cube('Crochet', (0.2, 0.4, 0.25), (sx*1.3, 1.8, 4.3), Mn, 0.03))
    o.append(cyl('Barre', 0.07, 6.0, (-3.0, 1.8, 4.5), Mc, 16, axe='X'))
    for x in (-2.4, 2.1): o.append(cyl('Disque', 1.0, 0.3, (x, 1.8, 4.5), mat('caoutchouc', (25, 25, 26)), 32, axe='X'))
    if rnd.random() < 0.6:
        for k in range(2): o.append(cyl('DisqueSol', 0.8, 0.25, (rnd.uniform(-2, 2), rnd.uniform(-3, -2), 0.0 + k*0.25), mat('caoutchouc', (25, 25, 26)), 28))
    parent_all(o, root); return root

def lave_linge(seed=0):
    rnd = random.Random(seed); root = empty(f'LaveLinge_{seed}'); o = []; w, d, h = 2.8, 2.8, 3.8; Mw = mat('metal_peint', (232, 234, 232))
    o.append(cube('Corps', (w, d, h), (0, d/2, h/2), Mw, 0.08))
    o.append(cube('Bandeau', (w - 0.1, 0.05, 0.6), (0, d + 0.02, h - 0.4), mat('plastique', (210, 212, 210)), 0.02))
    o.append(cyl('Programmateur', 0.18, 0.08, (w/2 - 0.5, d + 0.05, h - 0.4), mat('plastique', (180, 182, 180)), 20, axe='Y'))
    o.append(cube('Tiroir', (0.7, 0.04, 0.3), (-w/2 + 0.55, d + 0.04, h - 0.4), mat('plastique', (220, 222, 220)), 0.02))
    o.append(anneau_hublot(1.0, (0, d + 0.02, h*0.45)))
    o.append(cyl('Hublot', 0.82, 0.08, (0, d - 0.02, h*0.45), mat_verre('VitreHublot', (190, 200, 205), 0.05), 32, axe='Y'))
    o.append(cyl('Tambour', 0.8, 0.05, (0, d - 0.4, h*0.45), M_inox(), 32, axe='Y'))
    if rnd.random() < 0.5: o.append(blob('Linge', 0.5, (0, d - 0.6, h*0.36), mat('tissu', rnd.choice([(60, 90, 140), (200, 200, 190)])), seed=seed, amp=0.25, etire=(1.2, 0.8, 0.7)))
    parent_all(o, root); return root

def anneau_hublot(R, loc):
    from kit_tech import anneau
    return anneau('CadreHublot', R*0.9, R*0.12, loc, M_chrome(), 'Y', 40)
