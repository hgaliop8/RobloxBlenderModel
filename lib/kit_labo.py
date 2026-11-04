"""Mobilier de laboratoire (Nadir-4) : paillasse, hotte, étagère à spécimens, aquarium, armoire vitrée, petits appareils.
Convention : origine au sol ; meubles muraux : dos à y = 0, façade vers +Y ; objets libres : centrés en x/y."""
import bpy, bmesh, math, random
from mathutils import Vector, noise
from kit_meshes import *

BLANC_LABO = (214, 218, 214); GRIS_LABO = (150, 156, 160); RESINE = (36, 38, 40)
def M_inox(): return mat('metal_brut', (200, 202, 204))
def M_chrome(): return mat_plain('Chrome', (220, 222, 226), rough=0.08, metal=1.0)
def M_laiton(): return mat_plain('Laiton', (190, 150, 70), rough=0.3, metal=1.0)

# ---------------------------------------------------------------- verrerie et flacons
FORMOL = (214, 206, 120); EAU = (170, 214, 220)
def flacon(kind, loc, rnd, liquide=None, echelle=1.0):
    """petite verrerie : 'reactif' (flacon à col étroit + bouchon), 'erlen', 'becher', 'pissette', 'brun' (flacon ambré)"""
    x, y, z = loc; e = echelle; o = []
    V = mat_verre('VerreBrun', (150, 90, 40), 0.05) if kind == 'brun' else mat_verre()
    if kind in ('reactif', 'brun'):
        p = [(0.0, 0), (0.17, 0.0), (0.2, 0.03), (0.2, 0.42), (0.17, 0.5), (0.08, 0.56), (0.07, 0.62)]
        o.append(revolution('Flacon', [(r*e, h*e) for r, h in p], V, 24, (x, y, z), ferme_haut=False))
        o.append(cyl('Bouchon', 0.085*e, 0.12*e, (x, y, z + 0.6*e), mat('plastique', rnd.choice([(30, 30, 30), (40, 70, 140), (150, 40, 30), (230, 230, 225)])), 16))
        hl = rnd.uniform(0.12, 0.4)
    elif kind == 'erlen':
        p = [(0.0, 0), (0.24, 0.0), (0.26, 0.03), (0.08, 0.42), (0.07, 0.56), (0.085, 0.58)]
        o.append(revolution('Erlen', [(r*e, h*e) for r, h in p], V, 24, (x, y, z), ferme_haut=False)); hl = rnd.uniform(0.06, 0.2)
    elif kind == 'becher':
        p = [(0.0, 0), (0.17, 0.0), (0.18, 0.02), (0.18, 0.42), (0.2, 0.44)]
        o.append(revolution('Becher', [(r*e, h*e) for r, h in p], V, 24, (x, y, z), ferme_haut=False)); hl = rnd.uniform(0.08, 0.3)
    else:                                                   # pissette en plastique
        p = [(0.0, 0), (0.15, 0.0), (0.16, 0.03), (0.16, 0.42), (0.1, 0.5), (0.05, 0.52)]
        o.append(revolution('Pissette', [(r*e, h*e) for r, h in p], mat('plastique', (230, 235, 240)), 20, (x, y, z)))
        o.append(tube_path('Bec', [Vector((x, y, z + 0.52*e)), Vector((x, y, z + 0.64*e)), Vector((x + 0.14*e, y, z + 0.6*e))], 0.015*e, mat('plastique', (230, 235, 240))))
        return o
    if liquide is not False and hl > 0.07:
        lt = liquide or rnd.choice([EAU, (220, 200, 110), (120, 170, 90), (200, 120, 70), (150, 150, 200)])
        r0 = {'reactif': 0.18, 'brun': 0.18, 'erlen': 0.22, 'becher': 0.165}[kind]*e
        rt = r0 if kind != 'erlen' else max(0.07*e, r0*(1 - hl/0.42))
        o.append(revolution('Liquide', [(0.0, 0.01*e), (r0, 0.01*e), (rt, hl*e)], mat_liquide('Liq%d%d%d' % lt, lt, 2.0), 20, (x, y, z)))
    return o

def bocal_specimen(loc, rnd, h=1.3, r=0.42):
    """grand bocal en verre : couvercle, formol, spécimen organique, étiquette"""
    x, y, z = loc; o = []
    p = [(0.0, 0), (r - 0.03, 0.0), (r, 0.04), (r, h - 0.16), (r - 0.05, h - 0.08), (r - 0.06, h - 0.02)]
    o.append(revolution('Bocal', p, mat_verre(), 32, (x, y, z), ferme_haut=False))
    o.append(cyl('Couvercle', r - 0.02, 0.1, (x, y, z + h - 0.06), mat('metal_peint', rnd.choice([(40, 40, 40), (160, 150, 120), (90, 30, 30)])), 32, bev=0.02))
    lt = rnd.choice([FORMOL, (200, 196, 140), (190, 210, 150), (220, 190, 130)])
    hl = h - rnd.uniform(0.2, 0.45)
    o.append(revolution('Formol', [(0.0, 0.03), (r - 0.025, 0.03), (r - 0.025, hl)], mat_liquide('Formol%d' % lt[0], lt, 0.5), 28, (x, y, z)))
    chair = mat_plain('Chair%d' % rnd.randint(0, 2), rnd.choice([(214, 190, 170), (200, 170, 160), (190, 196, 176)]), rough=0.55)
    kind = rnd.random()
    if kind < 0.45:                                          # masse pâle
        o.append(blob('Specimen', r*0.45, (x, y, z + hl*0.45), chair, seed=rnd.uniform(0, 50), amp=0.3, etire=(1, 0.9, 1.4)))
    elif kind < 0.8:                                         # tentacules repliés
        for k in range(rnd.randint(3, 5)):
            a = rnd.uniform(0, 6.28); pts = []
            for t in range(6):
                rr = r*0.25 + t*0.04; pts.append(Vector((x + rr*math.cos(a + t*0.5), y + rr*math.sin(a + t*0.5), z + 0.15 + t*(hl - 0.3)/6)))
            o.append(tube_path('Tentacule', pts, 0.05 - k*0.006, chair))
        o.append(blob('Specimen', r*0.3, (x, y, z + 0.3), chair, seed=rnd.uniform(0, 50), amp=0.25))
    else:                                                    # poisson des abysses
        o.append(blob('Poisson', r*0.4, (x, y, z + hl*0.5), chair, seed=rnd.uniform(0, 50), amp=0.15, etire=(1.6, 0.6, 0.8)))
    o.append(cube('Etiquette', (r*0.9, 0.01, 0.28), (x, y + r + 0.006, z + h*0.62), mat('plastique', (226, 220, 196)), 0))
    return o

# ---------------------------------------------------------------- paillasse
def paillasse(w=8.0, seed=0, evier=True, etagere=True):
    rnd = random.Random(seed); root = empty(f'Paillasse_{seed}'); o = []; d = 2.6; h = 3.05
    faces = [(1, 'tiroirs3'), (1.3, 'porte'), (1.3, 'porte'), (1, 'tiroirs3')] if w >= 7 else [(1, 'tiroirs3'), (1.3, 'porte')]
    meuble_bas(o, -w/2, w/2, d, h, mat('metal_peint', BLANC_LABO), mat('metal_peint', rnd.choice([(150, 172, 190), BLANC_LABO, (176, 190, 170)])), M_inox(), faces=faces, rnd=rnd)
    top = cube('Plan', (w + 0.1, d + 0.15, 0.14), (0, d/2 + 0.03, h + 0.07), mat('plastique', RESINE), 0)
    xs = rnd.choice([-w/4, w/4])
    if evier:                                                # découpe + cuve inox + col de cygne
        cut = cube('Decoupe', (1.6, 1.2, 1.0), (xs, d/2 + 0.2, h), M_inox(), 0)
        bo = top.modifiers.new('bool', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; apply_mods(top); bpy.data.objects.remove(cut)
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = Vector((v.co.x*1.6, v.co.y*1.2, v.co.z*0.8))
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context='FACES')
        cuve = obj_from_bm(bm, 'Cuve', M_inox()); cuve.location = (xs, d/2 + 0.2, h + 0.14 - 0.4)
        cuve.modifiers.new('ep', 'SOLIDIFY').thickness = 0.03; bevel(cuve, 0.05, 3); o.append(cuve)
        o.append(cyl('Bonde', 0.09, 0.01, (xs, d/2 + 0.2, h + 0.14 - 0.8 + 0.01), mat_plain('Bonde', (30, 30, 30), 0.5), 16))
        o.append(tube_path('Robinet', [Vector((xs, 0.3, h + 0.14)), Vector((xs, 0.3, h + 1.5)), Vector((xs, 0.75, h + 1.62)), Vector((xs, 1.05, h + 1.2))], 0.05, M_chrome()))
        for s in (-1, 1):
            o.append(cyl('Vanne', 0.06, 0.25, (xs + s*0.35, 0.3, h + 0.14), M_chrome(), 16))
            o.append(cube('Manette', (0.06, 0.32, 0.05), (xs + s*0.35, 0.42, h + 0.42), mat('plastique', (40, 90, 170) if s < 0 else (180, 40, 30)), 0.02))
    bevel(top, 0.03, 2); o.append(top)
    for k in range(int(w//2.5)):                             # robinets de gaz
        gx = -w/2 + 1.2 + k*2.5
        if evier and abs(gx - xs) < 1.4: continue
        o.append(cyl('RobinetGaz', 0.05, 0.3, (gx, 0.22, h + 0.14), M_laiton(), 12))
        o.append(cyl('BecGaz', 0.03, 0.25, (gx, 0.22, h + 0.4), M_laiton(), 10, axe='Y'))
    if etagere:                                              # étagère à réactifs sur montants
        Mm = mat('metal_peint', GRIS_LABO)
        for sx in (-1, 1): o.append(cube('Montant', (0.14, 0.14, 3.8), (sx*(w/2 - 0.3), 0.2, h + 0.14 + 1.9), Mm, 0.02))
        o.append(cube('Goulotte', (w - 0.6, 0.3, 0.45), (0, 0.25, h + 0.14 + 0.5), mat('plastique', (220, 222, 220)), 0.03))
        for k in range(int(w//1.6)):
            px = -w/2 + 0.9 + k*1.6
            o.append(cube('Prise', (0.36, 0.04, 0.24), (px, 0.41, h + 0.64), mat('plastique', (200, 200, 196)), 0.02))
        for zz in (h + 1.5, h + 2.85):
            o.append(cube('Tablette', (w - 0.4, 0.95, 0.08), (0, 0.55, zz), mat_verre('VerreEtagere', (210, 235, 230), 0.05), 0.01))
            o.append(cube('TabletteBord', (w - 0.4, 0.04, 0.18), (0, 1.02, zz + 0.05), Mm, 0.01))
            xx = -w/2 + 0.6
            while xx < w/2 - 0.5:
                kind = rnd.choice(['reactif', 'reactif', 'brun', 'brun', 'boite', 'vide'])
                if kind == 'boite':
                    bw = rnd.uniform(0.5, 0.9); o.append(cube('Boite', (bw, 0.6, rnd.uniform(0.3, 0.6)), (xx + bw/2, 0.5, zz + 0.04 + 0.2), mat('carton', rnd.choice([(230, 230, 225), (200, 180, 140)])), 0.01)); xx += bw + 0.1
                elif kind == 'vide': xx += rnd.uniform(0.3, 0.8)
                else:
                    o += flacon(kind, (xx + 0.2, 0.55 + rnd.uniform(-0.15, 0.15), zz + 0.04), rnd, echelle=rnd.uniform(0.9, 1.3)); xx += rnd.uniform(0.45, 0.6)
    # verrerie et objets sur le plan
    for k in range(rnd.randint(3, 6)):
        px = rnd.uniform(-w/2 + 0.5, w/2 - 0.5)
        if evier and abs(px - xs) < 1.2: continue
        o += flacon(rnd.choice(['erlen', 'becher', 'becher', 'pissette', 'reactif']), (px, rnd.uniform(1.0, 2.2), h + 0.14), rnd, echelle=rnd.uniform(0.9, 1.4))
    if rnd.random() < 0.7:
        mx = rnd.choice([-w/2 + 1.0, w/2 - 1.0])
        if not (evier and abs(mx - xs) < 1.6): o += microscope((mx, 1.6, h + 0.14), rnd.uniform(-0.5, 0.5))
    parent_all(o, root); return root

# ---------------------------------------------------------------- petits appareils
def microscope(loc, rot=0.0):
    x, y, z = loc; Mb = mat('plastique', (225, 225, 220)); Mn = mat('plastique', (40, 40, 42)); o = []
    c, s = math.cos(rot), math.sin(rot)
    def P(dx, dy, dz): return (x + dx*c - dy*s, y + dx*s + dy*c, z + dz)
    R = (0, 0, rot)
    o.append(cube('Socle', (0.75, 0.95, 0.16), P(0, 0, 0.08), Mb, 0.06, 3, rot=R))
    o.append(cube('Bras', (0.22, 0.25, 1.05), P(0, -0.32, 0.6), Mb, 0.08, 3, rot=R))
    o.append(cube('Platine', (0.6, 0.5, 0.05), P(0, 0.08, 0.62), Mn, 0.02, rot=R))
    o.append(cube('Tete', (0.3, 0.55, 0.22), P(0, -0.1, 1.15), Mb, 0.07, 3, rot=R))
    o.append(cyl('Revolver', 0.13, 0.08, P(0, 0.08, 0.95), M_chrome(), 20))
    for k in range(3):
        a = k*2.1; o.append(cyl('Objectif', 0.035, 0.18, P(0.06*math.cos(a), 0.08 + 0.06*math.sin(a), 0.78), M_chrome(), 12))
    for sx in (-1, 1):
        o.append(tube('Oculaire', P(sx*0.07, -0.05, 1.25), P(sx*0.09, 0.12, 1.5), 0.045, Mn, 14))
        o.append(cyl('Vis', 0.09, 0.06, P(sx*0.14 - (0.06 if sx > 0 else 0), -0.32, 0.45), Mn, 16, axe='X'))
    o.append(cyl('Lampe', 0.07, 0.04, P(0, 0.08, 0.18), mat_plain('LampeMicro', (250, 240, 210), 0.2, emit=0.0), 16))
    return o

def tabouret(seed=0):
    rnd = random.Random(seed); root = empty(f'Tabouret_{seed}'); o = []; Mn = mat('plastique', (36, 36, 38)); Mc = M_chrome()
    hs = rnd.uniform(2.35, 2.7)
    seat = revolution('Assise', [(0.0, 0.0), (0.5, 0.0), (0.56, 0.06), (0.58, 0.16), (0.55, 0.24), (0.0, 0.26)], mat('simili_cuir', rnd.choice([(40, 40, 44), (40, 60, 90), (120, 40, 36)])), 32, (0, 0, hs))
    seat.modifiers.new('sub', 'SUBSURF').levels = 1; o.append(seat)
    o.append(cyl('Verin', 0.09, hs - 0.4, (0, 0, 0.32), Mc, 16)); o.append(cyl('Fourreau', 0.13, 0.9, (0, 0, 0.45), Mn, 20))
    a0 = rnd.uniform(0, 1)
    for k in range(5):
        a = a0 + k*2*math.pi/5; ex, ey = 0.85*math.cos(a), 0.85*math.sin(a)
        o.append(tube_path('Pied', [Vector((0, 0, 0.5)), Vector((ex*0.6, ey*0.6, 0.44)), Vector((ex, ey, 0.4))], 0.06, Mn))
        o += roulette('Roulette', (ex, ey, 0.0), Mn, Mn)
    ring = [Vector((0.62*math.cos(t*2*math.pi/16), 0.62*math.sin(t*2*math.pi/16), 1.15)) for t in range(17)]
    o.append(tube_path('Repose', ring, 0.035, Mc))
    for k in range(3):
        a = k*2*math.pi/3; o.append(tube('Rayon', (0.12*math.cos(a), 0.12*math.sin(a), 1.15), (0.6*math.cos(a), 0.6*math.sin(a), 1.15), 0.03, Mc))
    parent_all(o, root); return root

def ecran_pc(loc, rot=0.0, allume=False, rnd=None):
    """moniteur sur pied + clavier + souris"""
    x, y, z = loc; c, s = math.cos(rot), math.sin(rot); R = (0, 0, rot); Mn = mat('plastique', (34, 34, 36)); o = []
    def P(dx, dy, dz): return (x + dx*c - dy*s, y + dx*s + dy*c, z + dz)
    o.append(cube('PiedEcran', (0.6, 0.45, 0.05), P(0, -0.25, 0.025), Mn, 0.02, rot=R))
    o.append(cube('Colonne', (0.12, 0.08, 0.55), P(0, -0.32, 0.3), Mn, 0.03, rot=R))
    o.append(cube('Ecran', (1.75, 0.12, 1.05), P(0, -0.28, 1.05), Mn, 0.03, rot=R))
    o.append(cube('Dalle', (1.65, 0.01, 0.95), P(0, -0.218, 1.07), mat_plain('DalleOn' if allume else 'DalleOff', (60, 110, 120) if allume else (8, 9, 10), 0.08, emit=1.6 if allume else 0.0), 0, rot=R))
    o.append(cube('Clavier', (1.35, 0.45, 0.06), P(0, 0.35, 0.03), Mn, 0.02, rot=R))
    o.append(cube('Touches', (1.25, 0.36, 0.02), P(0, 0.35, 0.065), mat('plastique', (60, 60, 64)), 0.005, rot=R))
    o.append(cube('Souris', (0.18, 0.3, 0.08), P(0.95, 0.4, 0.04), Mn, 0.05, 3, rot=R))
    return o

def centrifugeuse(loc, rot=0.0):
    x, y, z = loc; o = []
    o.append(cube('Centrifugeuse', (1.2, 1.3, 0.8), (x, y, z + 0.4), mat('plastique', (226, 228, 226)), 0.18, 4, rot=(0, 0, rot)))
    o.append(cyl('Couvercle', 0.45, 0.06, (x, y, z + 0.8), mat('plastique', (70, 110, 160)), 32))
    o.append(cube('Panneau', (0.8, 0.02, 0.22), (x, y + 0.66, z + 0.55), mat_plain('LCD', (20, 40, 30), 0.2), 0.0, rot=(0, 0, rot)))
    return o

# ---------------------------------------------------------------- hotte aspirante
def hotte(w=5.0, seed=0, hauteur_plafond=12.0):
    rnd = random.Random(seed); root = empty(f'Hotte_{seed}'); o = []; d = 2.7; hb = 2.9
    Mw = mat('metal_peint', (226, 228, 224)); Mg = mat('metal_peint', GRIS_LABO)
    meuble_bas(o, -w/2, w/2, d, hb, Mw, mat('metal_peint', (190, 196, 200)), M_inox(), faces=[(1, 'porte'), (1, 'porte')], rnd=rnd)
    o.append(cube('PlanHotte', (w, d, 0.12), (0, d/2, hb + 0.06), mat('plastique', RESINE), 0.02))
    zc0, zc1 = hb + 0.12, hb + 3.6
    o.append(cube('Fond', (w, 0.1, zc1 - zc0), (0, 0.05, (zc0 + zc1)/2), Mw, 0.01))
    for sx in (-1, 1): o.append(cube('Flanc', (0.25, d, zc1 - zc0 + 0.9), (sx*(w/2 - 0.125), d/2, (zc0 + zc1 + 0.9)/2), Mw, 0.04))
    o.append(cube('Caisson', (w, d + 0.1, 1.0), (0, d/2 + 0.05, zc1 + 0.4), Mw, 0.05))
    o.append(cube('Bandeau', (w - 0.5, 0.05, 0.5), (0, d + 0.12, zc1 + 0.45), mat('metal_peint', (60, 64, 70)), 0.01))
    o.append(cube('Afficheur', (0.6, 0.02, 0.25), (w/2 - 0.8, d + 0.15, zc1 + 0.45), mat_plain('AffHotte', (40, 200, 90), 0.2, emit=0.0), 0.0))
    o.append(cube('Rampe', (w - 0.8, 0.3, 0.06), (0, d/2, zc1 - 0.1), mat_plain('Diffuseur', (240, 242, 250), rough=0.3), 0.02))
    zs = zc0 + rnd.uniform(1.2, 2.2)                          # vitre coulissante entrouverte
    o.append(cube('Vitre', (w - 0.55, 0.04, 1.9), (0, d - 0.1, zs + 0.95), mat_verre(), 0.0))
    o.append(cube('Poignee', (w - 0.6, 0.12, 0.12), (0, d - 0.02, zs + 0.06), M_inox(), 0.03))
    for sz in (zs + 1.9,): o.append(cube('Cadre', (w - 0.55, 0.08, 0.08), (0, d - 0.1, sz), M_inox(), 0.02))
    o.append(cyl('Gaine', 0.65, hauteur_plafond - (zc1 + 0.9), (0, d/2 - 0.3, zc1 + 0.9), mat('metal_brut', (170, 172, 172)), 28))
    for k in range(int((hauteur_plafond - zc1)//1.2)): o.append(cyl('Agrafe', 0.68, 0.06, (0, d/2 - 0.3, zc1 + 1.3 + k*1.2), mat('metal_brut', (130, 130, 130)), 28))
    for k in range(rnd.randint(2, 4)):
        o += flacon(rnd.choice(['erlen', 'becher', 'reactif']), (rnd.uniform(-w/2 + 0.6, w/2 - 0.6), rnd.uniform(0.6, 1.8), zc0), rnd, echelle=1.2)
    parent_all(o, root); return root

# ---------------------------------------------------------------- étagère à spécimens
def etagere_metal(o, w, d, h, n, Mm, Mt):
    """rayonnage métallique : 4 cornières perforées, n tablettes à rebord"""
    for sx in (-1, 1):
        for y in (0.08, d - 0.08):
            o.append(cube('Corniere', (0.14, 0.14, h), (sx*(w/2 - 0.07), y, h/2), Mm, 0.01))
    zs = [0.35 + k*(h - 0.6)/(n - 1) for k in range(n)]
    for z in zs:
        o.append(cube('Tablette', (w - 0.04, d - 0.02, 0.06), (0, d/2, z), Mt, 0.01))
        for y in (0.02, d - 0.02): o.append(cube('Rebord', (w - 0.04, 0.04, 0.16), (0, y, z - 0.05), Mt, 0.005))
    return zs

def etagere_specimens(w=6.0, seed=0):
    rnd = random.Random(seed); root = empty(f'EtagereSpecimens_{seed}'); o = []; d = 1.8; h = 7.0
    zs = etagere_metal(o, w, d, h, 5, mat('metal_peint', (70, 74, 78)), mat('metal_peint', (92, 96, 100)))
    for z in zs:
        x = -w/2 + 0.5
        while x < w/2 - 0.5:
            r = rnd.uniform(0.3, 0.45); hh = rnd.uniform(0.9, min(1.3, (h - 0.6)/4 - 0.15))
            if x + r > w/2 - 0.15: break
            if rnd.random() < 0.85: o += bocal_specimen((x + r, d/2 + rnd.uniform(-0.15, 0.15), z + 0.03), rnd, hh, r)
            x += 2*r + rnd.uniform(0.08, 0.3)
    parent_all(o, root); return root

# ---------------------------------------------------------------- aquarium de recherche
def aquarium(w=8.0, d=3.0, h=3.6, seed=0):
    rnd = random.Random(seed); root = empty(f'Aquarium_{seed}'); o = []; hb = 2.8
    meuble_bas(o, -w/2, w/2, d, hb, mat('metal_peint', (50, 56, 62)), mat('metal_peint', (60, 66, 72)), M_inox(), faces=[(1, 'porte'), (1, 'porte'), (1, 'porte')], rnd=rnd)
    z0 = hb; Mf = mat('metal_brut', (60, 62, 64)); t = 0.12
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*w, v.co.y*d, v.co.z*h))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context='FACES')
    bac = obj_from_bm(bm, 'Bac', mat_verre(), smooth=False); bac.location = (0, d/2, z0 + h/2); bac.modifiers.new('ep', 'SOLIDIFY').thickness = 0.06; o.append(bac)
    for sx in (-1, 1):                                        # cornières
        for sy in (0, 1):
            o.append(cube('Arete', (t, t, h + 0.05), (sx*(w/2), sy*d, z0 + h/2), Mf, 0.01))
    for sz in (z0, z0 + h):
        for sy in (0, 1): o.append(cube('Arete', (w + t, t, t), (0, sy*d, sz), Mf, 0.01))
        for sx in (-1, 1): o.append(cube('Arete', (t, d + t, t), (sx*w/2, d/2, sz), Mf, 0.01))
    hw = h - rnd.uniform(0.25, 0.5)
    o.append(cube('Eau', (w - 0.14, d - 0.14, hw), (0, d/2, z0 + 0.03 + hw/2), mat_liquide('EauAquarium', (150, 200, 200), 0.12), 0))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=40, y_segments=16, size=0.5)
    for v in bm.verts:
        v.co = Vector((v.co.x*(w - 0.16), v.co.y*(d - 0.16), 0.25 + 0.18*noise.noise(Vector((v.co.x*6, v.co.y*6, seed))) + 0.12*(v.co.y + 0.5)))
    sable = obj_from_bm(bm, 'Sable', mat('beton', (190, 176, 150))); sable.location = (0, d/2, z0 + 0.05); o.append(sable)
    for k in range(rnd.randint(3, 6)):
        o.append(blob('Roche', rnd.uniform(0.25, 0.55), (rnd.uniform(-w/2 + 0.8, w/2 - 0.8), rnd.uniform(0.7, d - 0.7), z0 + 0.35), mat('beton', (90, 92, 90)), seed=rnd.uniform(0, 99), amp=0.3, etire=(1.2, 1, 0.7)))
    o.append(cube('Rampe', (w - 0.3, 0.6, 0.18), (0, d/2, z0 + h + 0.15), mat('plastique', (40, 40, 42)), 0.04))
    o.append(cube('Filtre', (0.6, 0.4, 1.4), (w/2 - 0.5, 0.35, z0 + h - 0.5), mat('plastique', (40, 40, 42)), 0.05))
    o.append(tube('Tuyau', (w/2 - 0.5, 0.35, z0 + h + 0.2), (w/2 - 0.5, 0.35, z0 + h + 0.8), 0.06, mat('caoutchouc', (40, 40, 40))))
    o.append(cube('Etiquette', (1.2, 0.01, 0.5), (-w/2 + 1.2, d + 0.07, z0 + 0.4), mat('plastique', (230, 226, 210)), 0))
    parent_all(o, root); return root

# ---------------------------------------------------------------- armoire vitrée
def armoire_vitree(w=3.2, d=1.6, h=7.0, seed=0):
    rnd = random.Random(seed); root = empty(f'ArmoireVitree_{seed}'); o = []
    Mw = mat('metal_peint', BLANC_LABO); hb = 2.2
    meuble_bas(o, -w/2, w/2, d, hb, Mw, mat('metal_peint', (200, 204, 200)), M_inox(), faces=[(1, 'tiroirs3'), (1, 'tiroirs3')], rnd=rnd)
    z0 = hb; hh = h - hb
    o.append(cube('Dos', (w, 0.06, hh), (0, 0.03, z0 + hh/2), Mw, 0.0))
    for sx in (-1, 1): o.append(cube('Cote', (0.06, d, hh), (sx*(w/2 - 0.03), d/2, z0 + hh/2), Mw, 0.01))
    o.append(cube('Toit', (w + 0.06, d + 0.06, 0.1), (0, d/2, h), Mw, 0.02))
    for k in range(3):
        z = z0 + 0.15 + k*(hh - 0.4)/3
        o.append(cube('Rayon', (w - 0.14, d - 0.2, 0.04), (0, d/2 - 0.05, z), mat_verre('VerreEtagere', (210, 235, 230), 0.05), 0))
        x = -w/2 + 0.35
        while x < w/2 - 0.35:
            o += flacon(rnd.choice(['reactif', 'brun', 'brun', 'reactif', 'erlen']), (x, d/2 + rnd.uniform(-0.2, 0.2), z + 0.02), rnd, echelle=rnd.uniform(0.9, 1.4)); x += rnd.uniform(0.42, 0.6)
    for sx in (-1, 1):                                        # portes vitrées (une entrouverte)
        ang = 0.0 if sx < 0 or rnd.random() < 0.6 else math.radians(rnd.uniform(15, 40))
        pw = w/2 - 0.04; hx = sx*(w/2 - 0.02)
        door = empty('Porte', (hx, d, z0 + hh/2), (0, 0, -sx*ang)); door.parent = None
        parts = [cube('Vitre', (pw - 0.2, 0.03, hh - 0.25), (-sx*pw/2, 0, 0), mat_verre(), 0),
                 cube('Montant', (0.1, 0.06, hh - 0.05), (-sx*0.05, 0, 0), Mw, 0.01), cube('Montant', (0.1, 0.06, hh - 0.05), (-sx*(pw - 0.05), 0, 0), Mw, 0.01),
                 cube('Traverse', (pw, 0.06, 0.1), (-sx*pw/2, 0, hh/2 - 0.08), Mw, 0.01), cube('Traverse', (pw, 0.06, 0.1), (-sx*pw/2, 0, -hh/2 + 0.08), Mw, 0.01),
                 cube('Serrure', (0.08, 0.04, 0.2), (-sx*(pw - 0.12), 0.05, -0.3), M_chrome(), 0.01)]
        for p in parts: p.parent = door
        bpy.context.view_layer.update(); o += parts; o.append(door)
    o.append(cube('Pictogramme', (0.5, 0.01, 0.5), (0, d + 0.04, h - 0.45), mat('plastique', (230, 190, 30)), 0.0, rot=(0, math.pi/4, 0)))
    parent_all(o, root); return root

# ---------------------------------------------------------------- tableau blanc, chariot
def tableau_blanc(w=7.0, h=3.6, seed=0):
    rnd = random.Random(seed); root = empty(f'TableauBlanc_{seed}'); o = []; Ma = mat('metal_brut', (190, 192, 194))
    o.append(cube('Panneau', (w, 0.08, h), (0, 0.04, 0), mat_plain('Emaille', (236, 238, 236), rough=0.18), 0.0))
    for sz in (-1, 1): o.append(cube('Cadre', (w + 0.16, 0.14, 0.12), (0, 0.07, sz*h/2), Ma, 0.03))
    for sx in (-1, 1): o.append(cube('Cadre', (0.12, 0.14, h + 0.16), (sx*w/2, 0.07, 0), Ma, 0.03))
    o.append(cube('Auget', (w*0.8, 0.35, 0.08), (0, 0.22, -h/2 - 0.1), Ma, 0.02))
    for k in range(3):
        o.append(cyl('Feutre', 0.04, 0.5, (-w*0.3 + k*0.6, 0.25, -h/2 - 0.02), mat('plastique', [(30, 30, 30), (180, 30, 30), (30, 60, 160)][k]), 12, axe='X'))
    o.append(cube('Brosse', (0.7, 0.25, 0.2), (w*0.25, 0.22, -h/2 + 0.02), mat('plastique', (40, 40, 44)), 0.04))
    Mk = mat_plain('Encre', (20, 20, 20))
    for k in range(rnd.randint(5, 9)):                         # traits de feutre (schémas à demi effacés)
        x0, z0 = rnd.uniform(-w/2 + 0.6, w/2 - 1.5), rnd.uniform(-h/2 + 0.5, h/2 - 0.5)
        pts = [Vector((x0, 0.085, z0))]
        for t in range(rnd.randint(2, 4)): pts.append(pts[-1] + Vector((rnd.uniform(0.2, 1.1), 0, rnd.uniform(-0.4, 0.4))))
        o.append(tube_path('Trait', pts, 0.012, mat_plain(rnd.choice(['Encre', 'EncreBleue', 'EncreRouge']), rnd.choice([(20, 20, 20), (20, 40, 140), (150, 20, 20)]))))
    parent_all(o, root); return root

def chariot(seed=0):
    rnd = random.Random(seed); root = empty(f'Chariot_{seed}'); o = []; w, d = 3.0, 1.8; Mi = M_inox()
    for z in (0.9, 2.9):
        o.append(cube('Plateau', (w, d, 0.06), (0, 0, z), Mi, 0.01))
        for sy in (-1, 1): o.append(cube('Rebord', (w, 0.04, 0.18), (0, sy*d/2, z + 0.09), Mi, 0.005))
        for sx in (-1, 1): o.append(cube('Rebord', (0.04, d, 0.18), (sx*w/2, 0, z + 0.09), Mi, 0.005))
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(cyl('Pied', 0.06, 2.8, (sx*(w/2 - 0.08), sy*(d/2 - 0.08), 0.35), Mi, 12))
            o += roulette('Roulette', (sx*(w/2 - 0.08), sy*(d/2 - 0.08), 0), mat('caoutchouc', (40, 40, 40)), mat('metal_peint', (60, 60, 60)))
    o.append(tube_path('Poignee', [Vector((-w/2 - 0.0, -d/2 + 0.2, 2.95)), Vector((-w/2 - 0.35, -d/2 + 0.2, 3.3)), Vector((-w/2 - 0.35, d/2 - 0.2, 3.3)), Vector((-w/2, d/2 - 0.2, 2.95))], 0.04, Mi))
    for k in range(rnd.randint(2, 5)):
        o += flacon(rnd.choice(['erlen', 'becher', 'reactif', 'brun']), (rnd.uniform(-w/2 + 0.4, w/2 - 0.4), rnd.uniform(-d/2 + 0.4, d/2 - 0.4), 2.93), rnd, echelle=1.2)
    o.append(cube('Bac', (1.2, 0.9, 0.35), (0.6, 0, 1.1), mat('plastique', (60, 90, 150)), 0.05))
    parent_all(o, root); return root
