"""Mobilier de vie (Nadir-4) : cuisine, réfrigérateur, sanitaires, douche, bureau, chaise de bureau, bibliothèque, canapé, table basse,
lit d'hôpital, potence, paravent, tiroirs de morgue, table d'autopsie, bac à plantes, distributeur.
Convention : origine au sol ; meubles muraux : dos à y = 0, façade vers +Y ; objets libres : centrés."""
import bpy, bmesh, math, random
from mathutils import Vector, noise
from kit_meshes import *
from kit_labo import M_inox, M_chrome, flacon, ecran_pc
from kit_tech import volant

CARRELAGE_BLANC = (232, 234, 230)

def coussin(name, L, W, H, loc, material, seed=0, rot=0.0, gonfle=0.25):
    """coussin rembourré : pavé subdivisé, faces bombées, bords pincés"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    for v in bm.verts:
        x, y, z = v.co
        b = (1 - (2*x)**4)*(1 - (2*y)**4)
        v.co = Vector((x*L, y*W, z*H*(1 + gonfle*b) + noise.noise(Vector((x*3 + seed, y*3, z)))*0.03))
    ob = obj_from_bm(bm, name, material); ob.location = loc; ob.rotation_euler = (0, 0, rot)
    ob.modifiers.new('sub', 'SUBSURF').levels = 2; return ob

# ---------------------------------------------------------------- cuisine
def plaque_cuisson(o, x, y, z):
    o.append(cube('Plaque', (1.9, 1.7, 0.06), (x, y, z + 0.03), mat_plain('Vitroceram', (14, 14, 16), 0.12), 0.02))
    for dx, dy, r in ((-0.45, -0.4, 0.32), (0.45, -0.4, 0.25), (-0.45, 0.4, 0.25), (0.45, 0.4, 0.32)):
        o.append(anneau_plat('Foyer', r, (x + dx, y + dy, z + 0.062)))

def anneau_plat(name, r, loc):
    bm = bmesh.new(); n = 32
    vi = [bm.verts.new((r*0.92*math.cos(2*math.pi*k/n), r*0.92*math.sin(2*math.pi*k/n), 0)) for k in range(n)]
    vo = [bm.verts.new((r*math.cos(2*math.pi*k/n), r*math.sin(2*math.pi*k/n), 0)) for k in range(n)]
    for k in range(n): bm.faces.new((vi[k], vo[k], vo[(k + 1) % n], vi[(k + 1) % n]))
    ob = obj_from_bm(bm, name, mat_plain('Serigraphie', (120, 120, 120), 0.3)); ob.location = loc; return ob

def evier(o, x, y, z, w=2.0, d=1.4, prof=0.7):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*w, v.co.y*d, v.co.z*prof))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context='FACES')
    c = obj_from_bm(bm, 'Bac', M_inox()); c.location = (x, y, z - prof/2 + 0.02); c.modifiers.new('ep', 'SOLIDIFY').thickness = 0.03; bevel(c, 0.08, 3); o.append(c)
    o.append(cyl('Bonde', 0.1, 0.01, (x, y, z - prof + 0.04), mat_plain('Bonde', (30, 30, 30), 0.5), 16))
    o.append(tube_path('Robinet', [Vector((x, y - d/2 - 0.25, z)), Vector((x, y - d/2 - 0.25, z + 1.1)), Vector((x, y - d/2 + 0.2, z + 1.2)), Vector((x, y - d/2 + 0.45, z + 0.9))], 0.05, M_chrome()))
    o.append(cube('Mitigeur', (0.08, 0.4, 0.06), (x + 0.15, y - d/2 - 0.1, z + 0.3), M_chrome(), 0.02, rot=(0.3, 0, 0)))

def cuisine(w=10.0, seed=0, hotte=True):
    """plan de travail continu : caissons bas, évier, plaques, crédence carrelée, éléments hauts, hotte, électroménager, vaisselle"""
    rnd = random.Random(seed); root = empty(f'Cuisine_{seed}'); o = []; d = 2.4; h = 3.1
    Mc = mat('metal_peint', (200, 202, 198)); Mf = mat('metal_peint', rnd.choice([(160, 170, 176), (196, 190, 176), (120, 140, 150)]))
    n = max(2, int(w//2.0)); faces = [(1, 'tiroirs3') if k % 3 == 0 else (1, 'porte') for k in range(n)]
    meuble_bas(o, -w/2, w/2, d, h - 0.12, Mc, Mf, M_inox(), faces=faces, rnd=rnd)
    plan = cube('PlanTravail', (w + 0.1, d + 0.1, 0.14), (0, d/2 + 0.03, h - 0.05), M_inox(), 0)
    xe = -w/2 + 2.0; xp = w/2 - 2.0
    cut = cube('Decoupe', (2.0, 1.4, 1.0), (xe, d/2 + 0.15, h), M_inox(), 0)
    bo = plan.modifiers.new('bool', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; apply_mods(plan); bpy.data.objects.remove(cut); bevel(plan, 0.02, 2); o.append(plan)
    evier(o, xe, d/2 + 0.15, h + 0.02)
    plaque_cuisson(o, xp, d/2 + 0.1, h + 0.02)
    o.append(cube('Credence', (w, 0.06, 2.4), (0, 0.03, h + 1.2), mat('carrelage', CARRELAGE_BLANC), 0.0))
    for k in range(max(2, int(w//2.4))):                       # éléments hauts
        ew = w/max(2, int(w//2.4)); ex = -w/2 + ew*(k + 0.5)
        if hotte and abs(ex - xp) < ew/2 + 0.1: continue
        o.append(cube('Haut', (ew - 0.04, 1.3, 2.3), (ex, 0.65, h + 2.4 + 1.15), Mc, 0.02))
        o.append(cube('PorteHaute', (ew - 0.1, 0.05, 2.2), (ex, 1.32, h + 2.4 + 1.15), Mf, 0.015))
        o += poignee_barre('Poignee', (ex, 1.35, h + 2.4 + 0.3), 0.6, M_inox(), 'X')
    if hotte:
        o.append(cube('Hotte', (2.4, 1.6, 0.5), (xp, 0.8, h + 2.6), M_inox(), 0.05))
        o.append(cube('Cheminee', (1.0, 0.8, 2.0), (xp, 0.4, h + 3.85), M_inox(), 0.03))
    # objets : bouilloire, casseroles, vaisselle, rouleau
    o.append(revolution('Casserole', [(0.0, 0.0), (0.42, 0.0), (0.45, 0.04), (0.45, 0.45), (0.47, 0.47)], M_inox(), 28, (xp - 0.45, d/2 - 0.3, h + 0.08), ferme_haut=False))
    o.append(tube('Manche', (xp - 0.45, d/2 - 0.75, h + 0.45), (xp - 0.45, d/2 - 1.5, h + 0.5), 0.04, mat('plastique', (30, 30, 30))))
    xm = rnd.uniform(-w/2 + 3.5, w/2 - 3.5)
    o.append(cube('CafetiereSocle', (0.8, 0.8, 0.12), (xm, 0.7, h + 0.08), mat('plastique', (30, 30, 30)), 0.04))
    o.append(cube('Cafetiere', (0.8, 0.5, 1.4), (xm, 0.45, h + 0.75), mat('plastique', (30, 30, 30)), 0.08))
    o.append(revolution('Verseuse', [(0.0, 0.0), (0.25, 0.0), (0.3, 0.2), (0.28, 0.5), (0.2, 0.6)], mat_verre(), 24, (xm, 0.75, h + 0.15), ferme_haut=False))
    o.append(revolution('Cafe', [(0.0, 0.01), (0.24, 0.01), (0.28, 0.18)], mat_liquide('Cafe', (40, 22, 10), 4.0), 20, (xm, 0.75, h + 0.15)))
    for k in range(rnd.randint(2, 5)):
        o.append(revolution('Assiette', [(0.0, 0.0), (0.3, 0.0), (0.42, 0.06), (0.44, 0.07)], mat('plastique', (236, 236, 232)), 28, (rnd.uniform(-w/2 + 3.5, w/2 - 3.5), rnd.uniform(1.0, 1.8), h + 0.08 + k*0.07), ferme_haut=False))
    for k in range(rnd.randint(2, 4)):
        o.append(revolution('Mug', [(0.0, 0.0), (0.15, 0.0), (0.16, 0.02), (0.17, 0.34)], mat('plastique', rnd.choice([(230, 230, 226), (60, 90, 140), (170, 50, 40)])), 20, (rnd.uniform(-w/2 + 3.5, w/2 - 3.5), rnd.uniform(0.6, 1.9), h + 0.08), ferme_haut=False))
    parent_all(o, root); return root

def frigo(w=3.0, d=2.6, h=7.2, seed=0):
    rnd = random.Random(seed); root = empty(f'Frigo_{seed}'); o = []; Mc = M_inox()
    o.append(cube('Corps', (w, d - 0.1, h - 0.3), (0, (d - 0.1)/2, 0.3 + (h - 0.3)/2), Mc, 0.06))
    o.append(cube('Socle', (w - 0.2, d - 0.4, 0.3), (0, d/2 - 0.2, 0.15), mat('metal_peint', (40, 40, 42)), 0.02))
    hz = h*0.68
    o.append(cube('PorteFrigo', (w - 0.06, 0.1, hz - 0.4), (0, d - 0.05, 0.35 + (hz - 0.4)/2 + 0.05 + (h - hz)), Mc, 0.04))
    o.append(cube('PorteCongel', (w - 0.06, 0.1, h - hz - 0.45), (0, d - 0.05, 0.35 + (h - hz - 0.45)/2), Mc, 0.04))
    o += poignee_barre('Poignee', (-w/2 + 0.3, d + 0.02, h - hz + 1.6), 2.0, M_chrome(), 'Z', 0.18, 0.05)
    o += poignee_barre('Poignee', (-w/2 + 0.3, d + 0.02, (h - hz)/2 + 0.6), 0.9, M_chrome(), 'Z', 0.18, 0.05)
    o.append(cube('Afficheur', (0.6, 0.02, 0.3), (w/2 - 0.7, d + 0.01, h - 1.0), mat_plain('LCD', (20, 40, 30), 0.2), 0.0))
    for k in range(rnd.randint(2, 5)):                         # aimants / papiers
        o.append(cube('Papier', (rnd.uniform(0.4, 0.7), 0.01, rnd.uniform(0.5, 0.8)), (rnd.uniform(-w/2 + 0.8, w/2 - 0.5), d + 0.012, rnd.uniform(h - hz + 0.5, h - 0.8)), mat('plastique', rnd.choice([(236, 234, 226), (240, 230, 160)])), 0.0, rot=(0, rnd.uniform(-0.15, 0.15), 0)))
    parent_all(o, root); return root

def distributeur(seed=0):
    """distributeur de boissons : vitrine éclairée, rangées de canettes, monnayeur"""
    rnd = random.Random(seed); root = empty(f'Distributeur_{seed}'); o = []; w, d, h = 3.4, 2.8, 6.6
    Mc = mat('metal_peint', rnd.choice([(150, 30, 30), (40, 70, 130), (40, 44, 48)]))
    o.append(cube('Corps', (w, d, h), (0, d/2, h/2), Mc, 0.06))
    o.append(cube('Vitrine', (w*0.66, 0.05, h - 2.2), (-w*0.15, d + 0.02, h/2 + 0.6), mat_verre('VitreDistrib', (220, 230, 235), 0.08), 0.0))
    o.append(cube('FondVitrine', (w*0.62, 0.05, h - 2.4), (-w*0.15, d - 0.6, h/2 + 0.6), mat_plain('FondDistrib', (220, 226, 230), 0.4, emit=0.6), 0.0))
    for r in range(6):
        zz = 1.6 + r*0.75
        o.append(cube('Spirale', (w*0.62, 0.5, 0.04), (-w*0.15, d - 0.3, zz), M_chrome(), 0.0))
        col = rnd.choice([(200, 30, 30), (30, 90, 180), (230, 180, 30), (40, 150, 70), (220, 220, 220)])
        for k in range(5): o.append(cyl('Canette', 0.14, 0.5, (-w*0.15 - w*0.25 + k*0.36, d - 0.35, zz + 0.03), mat('metal_peint', col), 16))
    o.append(cube('Panneau', (w*0.25, 0.04, 2.2), (w*0.36, d + 0.02, h/2 + 0.8), mat('metal_peint', (40, 40, 44)), 0.02))
    for k in range(9): o.append(cube('Touche', (0.16, 0.04, 0.16), (w*0.31 + (k % 3)*0.22, d + 0.05, h/2 + 0.6 + (k//3)*0.24), mat('plastique', (200, 200, 196)), 0.02))
    o.append(cube('Trappe', (w*0.55, 0.1, 0.6), (-w*0.15, d + 0.03, 0.8), mat('plastique', (20, 20, 22)), 0.04))
    parent_all(o, root); return root

# ---------------------------------------------------------------- sanitaires
def wc_cabine(seed=0, porte_ouverte=None):
    """cabine WC : cloisons, porte, cuvette en porcelaine, réservoir, dérouleur"""
    rnd = random.Random(seed); root = empty(f'CabineWC_{seed}'); o = []; w, d, h = 3.6, 5.2, 7.0
    Mp = mat('plastique', rnd.choice([(170, 186, 196), (196, 200, 190), (120, 140, 150)])); Mpo = mat_plain('Porcelaine', (238, 238, 234), 0.12)
    for sx in (-1, 1):
        o.append(cube('Cloison', (0.12, d, h - 0.5), (sx*w/2, d/2, 0.5 + (h - 0.5)/2), Mp, 0.03))
        o.append(cyl('Pied', 0.06, 0.5, (sx*w/2, d - 0.3, 0), M_inox(), 12))
    ouverte = rnd.random() < 0.5 if porte_ouverte is None else porte_ouverte
    ang = math.radians(rnd.uniform(40, 90)) if ouverte else 0.0; pw = w - 0.2
    door = cube('Porte', (pw, 0.1, h - 0.9), (0, 0, 0), Mp, 0.03)
    door.location = (-w/2 + 0.1 + math.cos(ang)*pw/2, d + math.sin(ang)*pw/2, 0.5 + (h - 0.9)/2); door.rotation_euler = (0, 0, ang); o.append(door)
    # cuvette : bol de révolution aplati + abattant
    bol = revolution('Cuvette', [(0.0, 0.0), (0.45, 0.0), (0.55, 0.3), (0.62, 0.9), (0.7, 1.35), (0.66, 1.45), (0.5, 1.4), (0.38, 0.9), (0.0, 0.85)], Mpo, 32)
    bol.scale = (1.0, 1.25, 1.0); bol.location = (0, 1.9, 0); o.append(bol)
    o.append(cube('Abattant', (1.45, 1.8, 0.08), (0, 1.95, 1.5), mat('plastique', (236, 236, 232)), 0.3, 4))
    o.append(cube('Reservoir', (1.5, 0.6, 1.4), (0, 0.4, 2.1), Mpo, 0.12, 3))
    o.append(cyl('Chasse', 0.1, 0.05, (0, 0.4, 2.8), M_chrome(), 16))
    o.append(cyl('Rouleau', 0.22, 0.4, (w/2 - 0.35, 1.8, 2.6), mat('tissu', (240, 240, 236)), 20, axe='X'))
    o.append(cube('Derouleur', (0.1, 0.5, 0.1), (w/2 - 0.08, 1.8, 2.85), M_chrome(), 0.02))
    parent_all(o, root); return root

def lavabo(seed=0, miroir=True):
    rnd = random.Random(seed); root = empty(f'Lavabo_{seed}'); o = []; Mpo = mat_plain('Porcelaine', (238, 238, 234), 0.12)
    vasque = revolution('Vasque', [(0.0, 0.0), (0.3, 0.0), (0.55, 0.15), (0.75, 0.45), (0.82, 0.52), (0.78, 0.55), (0.0, 0.5)], Mpo, 32)
    vasque.scale = (1.25, 0.95, 1.0); vasque.location = (0, 1.0, 2.6); o.append(vasque)
    o.append(revolution('Colonne', [(0.25, 0.0), (0.3, 0.0), (0.22, 1.2), (0.3, 2.6), (0.0, 2.6)], Mpo, 24, (0, 0.9, 0)))
    o.append(tube_path('Robinet', [Vector((0, 0.25, 3.15)), Vector((0, 0.25, 3.5)), Vector((0, 0.6, 3.55)), Vector((0, 0.75, 3.4))], 0.045, M_chrome()))
    o.append(cube('Mitigeur', (0.06, 0.3, 0.05), (0.16, 0.25, 3.45), M_chrome(), 0.02))
    if miroir:
        o.append(cube('Miroir', (1.9, 0.04, 2.4), (0, 0.04, 5.2), mat_plain('Miroir', (230, 232, 234), 0.02, metal=1.0), 0.01))
        o.append(cube('Tablette', (1.8, 0.45, 0.06), (0, 0.25, 3.85), mat_verre(), 0.01))
        o.append(revolution('Gobelet', [(0.0, 0.0), (0.1, 0.0), (0.12, 0.3)], mat('plastique', (60, 120, 170)), 16, (0.5, 0.25, 3.88), ferme_haut=False))
        o.append(cube('Savon', (0.3, 0.2, 0.1), (-0.5, 0.25, 3.93), mat('plastique', (230, 220, 180)), 0.04))
    parent_all(o, root); return root

def douche(seed=0):
    """cabine de douche : bac, parois carrelées, rideau (tissu simulé épinglé), pomme et barre"""
    rnd = random.Random(seed); root = empty(f'Douche_{seed}'); o = []; w, d, h = 3.6, 3.6, 7.6; Mt = mat('carrelage', (214, 222, 226))
    o.append(cube('Receveur', (w, d, 0.3), (0, d/2, 0.15), mat_plain('Porcelaine', (238, 238, 234), 0.12), 0.06))
    o.append(cyl('Siphon', 0.15, 0.01, (0, d/2, 0.3), M_inox(), 16))
    for sx in (-1, 1): o.append(cube('Paroi', (0.12, d, h), (sx*w/2, d/2, h/2), Mt, 0.0))
    o.append(cube('Fond', (w, 0.12, h), (0, 0.0, h/2), Mt, 0.0))
    o.append(tube('Barre', (-w/2, d - 0.15, h - 0.4), (w/2, d - 0.15, h - 0.4), 0.04, M_chrome()))
    o.append(tube('Colonne', (0.6, 0.12, 3.0), (0.6, 0.12, 6.4), 0.05, M_chrome()))
    o.append(revolution('Pomme', [(0.0, 0.0), (0.25, 0.0), (0.27, 0.06), (0.05, 0.2)], M_chrome(), 24, (0.6, 0.45, 6.3)))
    o.append(tube_path('Bras', [Vector((0.6, 0.12, 6.4)), Vector((0.6, 0.3, 6.6)), Vector((0.6, 0.45, 6.5))], 0.04, M_chrome()))
    o.append(cube('Mitigeur', (0.5, 0.15, 0.3), (0.6, 0.15, 3.6), M_chrome(), 0.05))
    bm = bmesh.new(); nu, nv = 40, 30; V = {}
    off = rnd.uniform(-0.5, 0.3)
    for i in range(nu + 1):
        for j in range(nv + 1):
            u = i/nu; t = j/nv; x = -w/2 + 0.1 + u*(w*0.62) + off; z = h - 0.45 - t*5.6
            yy = d - 0.15 + 0.18*math.sin(u*math.pi*11) * (1 - 0.3*t) + 0.06*noise.noise(Vector((u*6, t*4, seed)))*t
            V[(i, j)] = bm.verts.new((x, yy, z))
    for i in range(nu):
        for j in range(nv): bm.faces.new((V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]))
    r = obj_from_bm(bm, 'Rideau', mat('tissu', rnd.choice([(200, 210, 220), (150, 170, 140), (230, 230, 220)]))); r.modifiers.new('ep', 'SOLIDIFY').thickness = 0.02; o.append(r)
    for k in range(10): o.append(anneau('Anneau', 0.08, 0.015, (-w/2 + 0.15 + k*w*0.065 + off, d - 0.15, h - 0.4), M_chrome(), 'Y', 12))
    o.append(revolution('Flacon', [(0.0, 0.0), (0.12, 0.0), (0.13, 0.5), (0.05, 0.6)], mat('plastique', rnd.choice([(40, 110, 160), (200, 90, 40)])), 16, (-w/2 + 0.4, 0.4, 0.3)))
    parent_all(o, root); return root

def anneau(name, r, rt, loc, material, axe='Z', seg=24):
    from kit_tech import anneau as A
    return A(name, r, rt, loc, material, axe, seg)

# ---------------------------------------------------------------- bureau, chaise de bureau, bibliothèque
def chaise_bureau(seed=0):
    rnd = random.Random(seed); root = empty(f'ChaiseBureau_{seed}'); o = []; Mn = mat('plastique', (34, 34, 36)); Mt = mat('tissu', rnd.choice([(50, 54, 60), (40, 50, 80), (70, 40, 40)]))
    hs = 1.75
    o.append(coussin('Assise', 1.6, 1.6, 0.3, (0, 0, hs), Mt, seed))
    o.append(coussin('Dossier', 1.5, 0.3, 2.0, (0, -0.85, hs + 1.35), Mt, seed + 1, gonfle=0.15)); o[-1].rotation_euler = (-0.12, 0, 0)
    o.append(cube('Support', (0.25, 0.2, 1.2), (0, -0.8, hs + 0.3), Mn, 0.05, rot=(-0.3, 0, 0)))
    for sx in (-1, 1):
        o.append(tube_path('Accoudoir', [Vector((sx*0.75, -0.4, hs + 0.05)), Vector((sx*0.8, -0.3, hs + 0.75)), Vector((sx*0.8, 0.4, hs + 0.8))], 0.05, Mn))
        o.append(cube('Manchette', (0.22, 0.9, 0.08), (sx*0.8, 0.0, hs + 0.82), Mn, 0.03))
    o.append(cyl('Verin', 0.09, hs - 0.5, (0, 0, 0.4), M_chrome(), 16)); o.append(cyl('Fourreau', 0.14, 0.6, (0, 0, 0.45), Mn, 20))
    a0 = rnd.uniform(0, 1)
    for k in range(5):
        a = a0 + k*2*math.pi/5; ex, ey = 0.95*math.cos(a), 0.95*math.sin(a)
        o.append(tube_path('Branche', [Vector((0, 0, 0.5)), Vector((ex*0.7, ey*0.7, 0.42)), Vector((ex, ey, 0.38))], 0.07, Mn))
        o += roulette('Roulette', (ex, ey, 0.0), Mn, Mn)
    root.rotation_euler = (0, 0, rnd.uniform(-0.6, 0.6))
    parent_all(o, root); return root

def bureau(w=5.0, seed=0, ecran=True, desordre=0.5):
    """bureau métallique : caisson à tiroirs, voile de fond, écran, lampe, papiers, classeurs"""
    rnd = random.Random(seed); root = empty(f'Bureau_{seed}'); o = []; d = 2.6; h = 2.6
    Mc = mat('metal_peint', rnd.choice([(150, 156, 150), (110, 120, 130), (170, 166, 150)])); Mp = mat('plastique', rnd.choice([(196, 186, 160), (170, 170, 166), (120, 100, 80)]))
    o.append(cube('Plateau', (w, d, 0.12), (0, d/2, h - 0.06), Mp, 0.03))
    o.append(cube('Chant', (w + 0.02, d + 0.02, 0.05), (0, d/2, h - 0.1), mat('plastique', (50, 50, 52)), 0.02))
    meuble_bas(o, w/2 - 1.7, w/2 - 0.05, d - 0.1, h - 0.14, Mc, Mc, M_inox(), faces=[(1, 'tiroirs3')], plinthe=0.15, rnd=rnd)
    o.append(cube('Pied', (0.12, d - 0.2, h - 0.14), (-w/2 + 0.1, d/2, (h - 0.14)/2), Mc, 0.02))
    o.append(cube('Voile', (w - 1.9, 0.06, 1.2), (-0.85, 0.2, h - 0.8), Mc, 0.01))
    if ecran: o += ecran_pc((rnd.uniform(-0.6, 0.2), 0.9, h), rnd.uniform(-0.2, 0.2), allume=rnd.random() < 0.3)
    lx = -w/2 + 0.5                                           # lampe articulée
    o.append(cyl('LampePied', 0.28, 0.08, (lx, 0.5, h), mat('metal_peint', (40, 40, 42)), 20))
    o.append(tube_path('LampeBras', [Vector((lx, 0.5, h + 0.08)), Vector((lx + 0.1, 0.4, h + 1.2)), Vector((lx + 0.6, 0.9, h + 1.5))], 0.035, mat('metal_peint', (40, 40, 42))))
    o.append(revolution('Abat', [(0.05, 0.0), (0.12, 0.0), (0.32, -0.38), (0.3, -0.4)], mat('metal_peint', (40, 40, 42)), 20, (lx + 0.6, 0.9, h + 1.62), ferme_haut=False, ferme_bas=False))
    for k in range(int(3 + desordre*8)):                       # papiers épars
        o.append(cube('Feuille', (0.75, 1.05, 0.006), (rnd.uniform(-w/2 + 0.6, w/2 - 0.6), rnd.uniform(1.2, d - 0.4), h + 0.005 + k*0.004), mat('plastique', rnd.choice([(236, 234, 226), (240, 236, 210), (226, 232, 236)])), 0.0, rot=(0, 0, rnd.uniform(-0.6, 0.6))))
    for k in range(rnd.randint(1, 3)):
        o.append(cube('Classeur', (0.35, 1.0, 1.25), (w/2 - 0.4 - k*0.38, 0.6, h + 0.62), mat('simili_cuir', rnd.choice([(40, 60, 120), (130, 40, 40), (40, 90, 60), (40, 40, 40)])), 0.02, rot=(0, rnd.uniform(-0.15, 0) if k == 0 else 0, 0)))
    o.append(revolution('Mug', [(0.0, 0.0), (0.15, 0.0), (0.16, 0.02), (0.17, 0.34)], mat('plastique', rnd.choice([(230, 230, 226), (60, 90, 140)])), 20, (rnd.uniform(0.5, 1.5), 1.8, h), ferme_haut=False))
    parent_all(o, root); return root

def livres_rangee(o, x0, x1, y, z, hmax, rnd, d=1.0):
    x = x0
    while x < x1 - 0.2:
        if rnd.random() < 0.08: x += rnd.uniform(0.3, 0.8); continue
        t = rnd.uniform(0.12, 0.3); hh = rnd.uniform(0.75, min(hmax, 1.25)); dd = rnd.uniform(0.75, d)
        col = rnd.choice([(120, 30, 30), (30, 50, 100), (40, 80, 50), (150, 120, 70), (40, 40, 40), (200, 190, 160), (90, 60, 40)])
        tilt = 0.0
        if rnd.random() < 0.06 and x > x0 + 0.5: tilt = rnd.uniform(0.15, 0.35)
        o.append(cube('Livre', (t, dd, hh), (x + t/2 + hh*math.sin(tilt)*0.5, y + dd/2, z + hh/2*math.cos(tilt)), mat('simili_cuir', col), 0.015, rot=(0, tilt, 0)))
        x += t + (hh*math.sin(tilt) if tilt else 0.005)

def bibliotheque(w=5.0, d=1.4, h=7.5, seed=0):
    rnd = random.Random(seed); root = empty(f'Bibliotheque_{seed}'); o = []; Mb = mat('bois', rnd.choice([(150, 110, 70), (120, 86, 56), (190, 160, 120)]))
    t = 0.1
    for sx in (-1, 1): o.append(cube('Montant', (t, d, h), (sx*(w/2 - t/2), d/2, h/2), Mb, 0.01))
    o.append(cube('Dos', (w, 0.05, h), (0, 0.025, h/2), Mb, 0.0)); o.append(cube('Socle', (w, d, 0.35), (0, d/2, 0.175), Mb, 0.01))
    n = 5
    for k in range(n + 1):
        z = 0.35 + k*(h - 0.45)/n
        o.append(cube('Tablette', (w - 2*t, d - 0.05, t), (0, d/2, z), Mb, 0.01))
        if k < n: livres_rangee(o, -w/2 + t, w/2 - t, 0.1, z + t/2, (h - 0.45)/n - 0.15, rnd, d - 0.2)
    parent_all(o, root); return root

# ---------------------------------------------------------------- détente
def canape(w=6.0, seed=0):
    rnd = random.Random(seed); root = empty(f'Canape_{seed}'); o = []; d = 2.8
    Mt = mat('tissu', rnd.choice([(84, 70, 64), (60, 70, 84), (90, 90, 80), (110, 60, 50)]))
    o.append(cube('Base', (w, d, 1.0), (0, d/2, 0.75), Mt, 0.15, 3))
    for k in range(int(w//2.0)):
        n = int(w//2.0); cw = (w - 1.0)/n
        o.append(coussin('Assise', cw - 0.05, d - 0.9, 0.5, (-w/2 + 0.5 + cw*(k + 0.5), d/2 + 0.35, 1.5), Mt, seed + k, rot=rnd.uniform(-0.03, 0.03)))
        o.append(coussin('Dossier', cw - 0.05, 0.6, 1.6, (-w/2 + 0.5 + cw*(k + 0.5), 0.6, 2.3), Mt, seed + 10 + k, gonfle=0.3)); o[-1].rotation_euler = (-0.2, 0, rnd.uniform(-0.03, 0.03))
    for sx in (-1, 1): o.append(coussin('Accoudoir', 0.55, d, 1.3, (sx*(w/2 - 0.27), d/2, 1.6), Mt, seed + 20 + sx, gonfle=0.2))
    for sx in (-1, 1):
        for sy in (0.3, d - 0.3): o.append(cyl('Pied', 0.08, 0.25, (sx*(w/2 - 0.35), sy, 0), mat('bois', (70, 50, 30)), 10))
    if rnd.random() < 0.6:
        o.append(tissu_simule('Plaid', 2.4, 1.8, 3.4, [o[1], o[2], o[0]], mat('tissu', rnd.choice([(150, 40, 40), (200, 180, 140), (60, 90, 70)])), seed=seed, frames=45, drop_noise=0.2, res=0.1, centre=(w/2 - 1.4, d/2), shrink=0.04, crumple=0.3))
    parent_all(o, root); return root

def table_basse(seed=0):
    rnd = random.Random(seed); root = empty(f'TableBasse_{seed}'); o = []
    o.append(cube('Plateau', (3.6, 2.0, 0.12), (0, 0, 1.45), mat('bois', (140, 100, 64)), 0.03))
    for sx in (-1, 1):
        for sy in (-1, 1): o.append(cube('Pied', (0.14, 0.14, 1.4), (sx*1.6, sy*0.85, 0.7), mat('metal_peint', (40, 40, 42)), 0.02))
    for k in range(rnd.randint(1, 3)):
        o.append(cube('Magazine', (0.8, 1.1, 0.03), (rnd.uniform(-1, 1), rnd.uniform(-0.4, 0.4), 1.53 + k*0.03), mat('plastique', rnd.choice([(200, 60, 50), (40, 90, 160), (230, 220, 200)])), 0.0, rot=(0, 0, rnd.uniform(-0.5, 0.5))))
    parent_all(o, root); return root

def bac_plantes(L=6.0, seed=0, mortes=True, plafond=12.0):
    """bac de culture : caisson, terreau, plantes (feuilles en lanières), tuteurs, rampe lumineuse"""
    rnd = random.Random(seed); root = empty(f'BacPlantes_{seed}'); o = []; W = 2.2; H = 2.2
    o.append(cube('Bac', (L, W, H), (0, 0, H/2), mat('metal_peint', (60, 80, 70)), 0.05))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=24, y_segments=8, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x*(L - 0.2), v.co.y*(W - 0.2), 0.08*noise.noise(Vector((v.co.x*8, v.co.y*8, seed)))))
    t = obj_from_bm(bm, 'Terreau', mat('moquette', (70, 52, 36))); t.location = (0, 0, H - 0.15); o.append(t)
    Mv = mat_plain('Feuille' + ('Morte' if mortes else ''), (120, 110, 60) if mortes else (60, 110, 50), 0.6)
    for k in range(int(L//0.9)):
        px, py = -L/2 + 0.5 + k*0.9 + rnd.uniform(-0.15, 0.15), rnd.uniform(-0.5, 0.5)
        for j in range(rnd.randint(5, 9)):
            a = rnd.uniform(0, 6.28); ln = rnd.uniform(0.6, 1.4); droop = rnd.uniform(0.4, 1.2) if mortes else rnd.uniform(0.1, 0.4)
            pts = [Vector((px, py, H - 0.12))]
            for s in range(1, 5):
                f = s/4; pts.append(Vector((px + math.cos(a)*ln*f, py + math.sin(a)*ln*f, H - 0.1 + ln*0.8*f - droop*f*f)))
            bmL = bmesh.new(); prev = None
            for s, p in enumerate(pts):
                wv = 0.09*(1 - s/5); side = Vector((-math.sin(a), math.cos(a), 0))*wv
                a1, a2 = bmL.verts.new(p - side), bmL.verts.new(p + side)
                if prev: bmL.faces.new((prev[0], prev[1], a2, a1))
                prev = (a1, a2)
            f = obj_from_bm(bmL, 'Feuille', Mv); f.modifiers.new('ep', 'SOLIDIFY').thickness = 0.01; o.append(f)
        o.append(cyl('Tuteur', 0.025, 1.6, (px + 0.1, py + 0.1, H - 0.2), mat('bois', (150, 120, 80)), 6))
    o.append(cube('Rampe', (L, 0.5, 0.15), (0, 0, H + 3.0), mat('metal_peint', (200, 200, 196)), 0.03))
    o.append(cube('Led', (L - 0.3, 0.3, 0.02), (0, 0, H + 2.92), mat_plain('LedHorticole', (220, 80, 255), 0.3, emit=0.0), 0.0))
    for sx in (-1, 1): o.append(tube('Suspente', (sx*(L/2 - 0.3), 0, H + 3.07), (sx*(L/2 - 0.3), 0, plafond), 0.015, mat('metal_brut', (150, 150, 150))))
    parent_all(o, root); return root

# ---------------------------------------------------------------- infirmerie, morgue
def lit_hopital(seed=0):
    rnd = random.Random(seed); root = empty(f'LitHopital_{seed}'); o = []; L, W = 7.2, 3.2; Mc = mat('metal_peint', (214, 216, 212)); Mi = M_inox()
    zm = 2.3
    o.append(cube('Chassis', (L - 0.6, W - 0.4, 0.3), (0, 0, zm - 0.35), Mc, 0.05))
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(cube('Pied', (0.22, 0.22, zm - 0.6), (sx*(L/2 - 0.6), sy*(W/2 - 0.4), (zm - 0.6)/2 + 0.3), Mc, 0.03))
            o += roulette('Roulette', (sx*(L/2 - 0.6), sy*(W/2 - 0.4), 0.0), mat('caoutchouc', (40, 40, 40)), Mc)
    for sx, hh in ((-1, 2.4), (1, 1.6)):                        # têtière et pied de lit
        o.append(cube('Panneau', (0.2, W, hh), (sx*(L/2 - 0.1), 0, zm + hh/2 - 0.4), mat('plastique', (180, 200, 210)), 0.1, 3))
    mt = cube('Matelas', (L - 0.5, W - 0.5, 0.55), (0, 0, zm + 0.27), mat('simili_cuir', (110, 150, 170)), 0.16, 4); mt.modifiers.new('sub', 'SUBSURF').levels = 1; o.append(mt)
    ore = oreiller('Oreiller', 2.4, 1.5, 0.6, seed=seed, material=mat('tissu', (236, 236, 232))); ore.location = (-L/2 + 1.3, 0, zm + 0.85); ore.rotation_euler = (0, -0.2, math.pi/2 + rnd.uniform(-0.1, 0.1)); o.append(ore)
    for sy in (-1, 1):                                          # barrières latérales
        if rnd.random() < 0.7:
            o.append(tube_path('Barriere', [Vector((-L/2 + 1.0, sy*(W/2 - 0.1), zm + 0.2)), Vector((-L/2 + 1.1, sy*(W/2 - 0.1), zm + 1.1)), Vector((0.5, sy*(W/2 - 0.1), zm + 1.1)), Vector((0.6, sy*(W/2 - 0.1), zm + 0.2))], 0.05, Mi))
            for k in range(3): o.append(tube('Barreau', (-L/2 + 1.6 + k*0.9, sy*(W/2 - 0.1), zm + 0.3), (-L/2 + 1.6 + k*0.9, sy*(W/2 - 0.1), zm + 1.1), 0.03, Mi))
    bpy.context.view_layer.update()
    o.append(tissu_simule('Drap', rnd.uniform(4.6, 5.6), W + 1.8, zm + 1.4, [mt, ore], mat('tissu', (226, 230, 232)), seed=seed, frames=70, drop_noise=0.3, res=0.11, centre=(0.8, 0), shrink=0.05, crumple=0.5))
    parent_all(o, root); return root

def potence(seed=0):
    rnd = random.Random(seed); root = empty(f'Potence_{seed}'); o = []; Mi = M_inox()
    o.append(cyl('Mat', 0.05, 6.4, (0, 0, 0.35), Mi, 12))
    for k in range(5):
        a = k*2*math.pi/5; o.append(tube('Branche', (0, 0, 0.4), (0.9*math.cos(a), 0.9*math.sin(a), 0.25), 0.05, Mi)); o += roulette('Roulette', (0.9*math.cos(a), 0.9*math.sin(a), 0.0), mat('caoutchouc', (40, 40, 40)), Mi)
    o.append(tube_path('Crochets', [Vector((-0.5, 0, 6.5)), Vector((0, 0, 6.75)), Vector((0.5, 0, 6.5))], 0.03, Mi))
    poche = blob('Poche', 0.35, (0.5, 0, 5.8), mat_verre('Poche', (240, 236, 220), 0.25), seed=seed, amp=0.08, etire=(0.9, 0.35, 1.5)); o.append(poche)
    o.append(tube_path('Tubulure', [Vector((0.5, 0, 5.3)), Vector((0.6, 0.1, 4.0)), Vector((0.3, 0.4, 2.8)), Vector((0.9, 0.9, 2.4))], 0.015, mat_verre('Tubulure', (230, 236, 236), 0.2)))
    parent_all(o, root); return root

def paravent(seed=0):
    rnd = random.Random(seed); root = empty(f'Paravent_{seed}'); o = []; Mi = M_inox()
    for k in range(3):
        a = (k - 1)*0.5; cx = (k - 1)*2.1
        for sx in (-1, 1): o.append(cyl('Tube', 0.04, 5.6, (cx + sx*1.0, (k % 2)*0.6, 0.3), Mi, 10))
        o.append(cube('Toile', (1.9, 0.02, 4.4), (cx, (k % 2)*0.6, 3.2), mat('tissu', (190, 214, 220)), 0.0))
        for sx in (-1, 1): o += roulette('Roulette', (cx + sx*1.0, (k % 2)*0.6, 0.0), mat('caoutchouc', (40, 40, 40)), Mi)
    parent_all(o, root); return root

def tiroirs_morgue(w=6.0, seed=0):
    """paroi frigorifique : 3×2 portes inox à poignée de chambre froide, une porte ouverte avec plateau sorti et housse"""
    rnd = random.Random(seed); root = empty(f'Morgue_{seed}'); o = []; d = 2.8; h = 7.0; Mi = M_inox(); n = int(w//2.9)
    o.append(cube('Paroi', (w, d, h), (0, d/2, h/2), mat('metal_brut', (180, 182, 184)), 0.03))
    ouv = (rnd.randrange(n), rnd.randrange(3))
    for i in range(n):
        for j in range(3):
            x = -w/2 + w*(i + 0.5)/n; z = 0.9 + j*2.1 + 0.9
            if (i, j) == ouv:
                o.append(cube('Niche', (w/n - 0.6, 0.05, 1.6), (x, d - 0.02, z), mat_plain('Noir', (6, 6, 7), 0.9), 0.0))
                ang = math.radians(rnd.uniform(80, 100)); door = cube('Porte', (w/n - 0.4, 0.15, 1.8), (0, 0, 0), Mi, 0.04)
                door.location = (x - (w/n - 0.4)/2 + math.cos(ang)*(w/n - 0.4)/2, d + 0.1 + math.sin(ang)*(w/n - 0.4)/2, z); door.rotation_euler = (0, 0, ang); o.append(door)
                o.append(cube('Plateau', (w/n - 0.8, 3.0, 0.08), (x, d + 1.4, z - 0.6), Mi, 0.02))
                for sx in (-1, 1): o.append(cube('Glissiere', (0.06, 3.2, 0.12), (x + sx*(w/n - 0.8)/2, d + 1.3, z - 0.66), Mi, 0.01))
                h_ = blob('Housse', 0.5, (x, d + 1.5, z - 0.35), mat('simili_cuir', (30, 32, 36)), seed=seed, amp=0.12, etire=(0.9, 2.6, 0.45)); o.append(h_)
            else:
                o.append(cube('Porte', (w/n - 0.4, 0.15, 1.8), (x, d + 0.07, z), Mi, 0.04))
                o.append(cube('Poignee', (0.7, 0.18, 0.18), (x + (w/n)/2 - 0.7, d + 0.2, z + 0.4), M_chrome(), 0.04))
                o.append(cube('Charniere', (0.12, 0.12, 0.35), (x - (w/n)/2 + 0.3, d + 0.18, z + 0.5), M_chrome(), 0.02))
                o.append(cube('Charniere', (0.12, 0.12, 0.35), (x - (w/n)/2 + 0.3, d + 0.18, z - 0.5), M_chrome(), 0.02))
                o.append(cube('Etiquette', (0.6, 0.02, 0.35), (x, d + 0.16, z + 0.45), mat('plastique', (230, 226, 210)), 0.0))
    parent_all(o, root); return root

def table_autopsie(seed=0, plafond=12.0):
    rnd = random.Random(seed); root = empty(f'TableAutopsie_{seed}'); o = []; Mi = M_inox(); L, W = 7.6, 2.8; h = 3.2
    bm = bmesh.new(); nu, nv = 30, 10; V = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            u = i/nu; v = j/nv; x = (u - 0.5)*L; y = (v - 0.5)*W
            edge = max(abs(2*u - 1), abs(2*v - 1)); z = 0.25*(edge > 0.92) - 0.05*(1 - abs(2*v - 1)) + 0.04*(u - 0.5)
            V[(i, j)] = bm.verts.new((x, y, z))
    for i in range(nu):
        for j in range(nv): bm.faces.new((V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]))
    plateau = obj_from_bm(bm, 'Plateau', Mi); plateau.location = (0, 0, h); plateau.modifiers.new('ep', 'SOLIDIFY').thickness = 0.06; o.append(plateau)
    o.append(cyl('Bonde', 0.12, 0.02, (-L/2 + 0.6, 0, h - 0.02), mat_plain('Noir', (6, 6, 7), 0.9), 16))
    o.append(revolution('Colonne', [(0.6, 0.0), (0.6, 0.15), (0.35, 0.3), (0.3, h - 0.5), (0.5, h - 0.15), (0.0, h - 0.1)], Mi, 32, (0.6, 0, 0)))
    o.append(cube('Socle', (2.0, 1.6, 0.15), (0.6, 0, 0.075), Mi, 0.04))
    o.append(tube_path('Douchette', [Vector((L/2 - 0.3, -W/2 + 0.2, h + 0.1)), Vector((L/2 - 0.3, -W/2 + 0.2, h + 1.6)), Vector((L/2 - 1.0, -W/2 + 0.2, h + 1.9))], 0.04, M_chrome()))
    o.append(cube('Bloc', (0.25, 0.8, 0.12), (-L/2 + 1.2, 0, h + 0.08), mat('caoutchouc', (40, 40, 40)), 0.03))
    # scialytique (lampe opératoire)
    o.append(revolution('Scialytique', [(0.0, 0.0), (0.9, 0.0), (1.0, 0.15), (0.6, 0.45), (0.15, 0.5)], mat('metal_peint', (220, 222, 220)), 36, (0, 0, h + 5.6)))
    o.append(cyl('Lentille', 0.85, 0.02, (0, 0, h + 5.58), mat_plain('LentilleScialytique', (240, 244, 250), 0.1), 36))
    o.append(tube_path('BrasLampe', [Vector((0, 0, h + 6.1)), Vector((0.4, 0, h + 6.9)), Vector((1.4, 0, h + 7.4)), Vector((1.4, 0, plafond))], 0.07, mat('metal_peint', (220, 222, 220))))
    for k in range(rnd.randint(2, 4)):                          # instruments sur desserte
        o.append(cube('Instrument', (0.04, 0.5, 0.02), (L/2 - 1.2 + k*0.15, W/2 - 0.5, h + 0.06), M_chrome(), 0.005, rot=(0, 0, rnd.uniform(-0.2, 0.2))))
    parent_all(o, root); return root
