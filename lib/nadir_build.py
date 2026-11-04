"""NADIR-4 — construction de la base pour Roblox à partir de nadir_layout.py.
Usage : python nadir_build.py SORTIE_DIR  -> nadir4.rbxlx + nadir4.json (aperçus)"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import nadir_layout as N
from nadir_kit import Scene, Frame, rot_y, I3, write_rbxlx, write_json
S = N.S
WT = 0.8            # épaisseur d'un mur (chaque espace a le sien : cloisons de 1,6 stud)
DOOR_H = 8.5
sc = Scene()
R = sc.rng

# ================================================================ espaces en coordonnées monde
def wrect(r): x0, z0, x1, z1 = r; return (x0*S, -z1*S, x1*S, -z0*S)        # (X0, Z0, X1, Z1)
class Espace:
    def __init__(s, d, est_couloir):
        s.d = d; s.id = d['id']; s.couloir = est_couloir
        s.X0, s.Z0, s.X1, s.Z1 = wrect(d['rect']); s.h = d['h']; s.elev = d['elev']
        s.esc = d.get('escalier')
        if s.esc:
            za, zb, ea, eb = s.esc; s.ymin, s.ymax = min(ea, eb), max(ea, eb) + s.h
        else: s.ymin, s.ymax = s.elev, s.elev + s.h
        s.secteur = d.get('secteur', 'couloir'); s.nom = d.get('nom', s.id)
        s.folder = f"Nadir4/{N.SECTEURS[s.secteur]['nom'] if s.secteur in N.SECTEURS else 'Couloirs'}/{s.nom if not est_couloir else s.id}"
    def floor_at(s, Z):
        if not s.esc: return s.elev
        za, zb, ea, eb = s.esc; z = -Z/S
        if z <= za: return ea
        if z >= zb: return eb
        return ea + (eb - ea)*(z - za)/(zb - za)
ESP = [Espace(c, True) for c in N.COULOIRS] + [Espace(s, False) for s in N.SALLES]
COUL = [e for e in ESP if e.couloir]
SAL = [e for e in ESP if not e.couloir]
BYID = {e.id: e for e in ESP}

def vert_overlap(a, b): return min(a.ymax, b.ymax) - max(a.ymin, b.ymin) > 1

# ================================================================ styles
def style(e):
    i = e.id
    def has(*k): return any(i.startswith(x) or x in i for x in k)
    if e.couloir:
        if e.d.get('verre'): return dict(kind='verre', wall=('Glass', (150, 190, 205)), wains=('Metal', (70, 76, 80)), floor=('DiamondPlate', (80, 84, 88)), ceil=('Glass', (150, 190, 205)), rib=('Metal', (62, 66, 70)))
        if e.elev < 0: return dict(kind='couloir_m', wall=('Metal', (104, 112, 106)), wains=('Metal', (66, 72, 68)), floor=('DiamondPlate', (78, 80, 78)), ceil=('Metal', (88, 92, 90)), rib=('Metal', (58, 62, 60)))
        return dict(kind='couloir', wall=('Metal', (132, 136, 138)), wains=('SmoothPlastic', (74, 78, 82)), floor=('DiamondPlate', (86, 90, 94)), ceil=('Metal', (108, 112, 116)), rib=('Metal', (64, 68, 72)))
    if i == 'serre': return dict(kind='serre', wall=('SmoothPlastic', (210, 214, 210)), wains=('SmoothPlastic', (90, 110, 90)), floor=('Concrete', (120, 120, 116)), ceil=('Glass', (140, 170, 190)), rib=('Metal', (80, 84, 86)))
    if has('toilettes', 'douches', 'infirmerie', 'pharmacie', 'soins', 'morgue', 'decontamination', 'quarantaine'):
        return dict(kind='sanitaire', wall=('Marble', (224, 226, 224)), wains=('Marble', (150, 186, 190)), floor=('Slate', (112, 118, 120)), ceil=('SmoothPlastic', (214, 216, 214)), rib=('SmoothPlastic', (170, 174, 174)))
    if has('labo', 'dissection', 'specimens', 'aquariums', 'stock_chimie', 'chambre_froide', 'stock_echant', 'salle_cuves', 'module_prel', 'depot_labo', 'laverie_labo', 'sonar', 'observatoire', 'cloche'):
        return dict(kind='labo', wall=('SmoothPlastic', (212, 216, 214)), wains=('SmoothPlastic', (128, 156, 162)), floor=('SmoothPlastic', (172, 184, 180)), ceil=('SmoothPlastic', (200, 204, 202)), rib=('Metal', (120, 128, 130)))
    if has('bureau', 'archives', 'reunion', 'securite', 'imprimerie', 'salle_plans', 'biblio', 'crise', 'scelles', 'salle_info', 'serveurs', 'radio', 'cabine_cdt', 'local_comms', 'attente', 'briefing', 'poste_garde'):
        return dict(kind='bureau', wall=('SmoothPlastic', (196, 192, 182)), wains=('WoodPlanks', (104, 80, 58)), floor=('Fabric', (66, 72, 84)), ceil=('SmoothPlastic', (204, 204, 198)), rib=('Metal', (110, 108, 102)))
    if has('quartiers', 'cantine', 'cuisine', 'detente', 'sport', 'jeux', 'projection', 'musique', 'recueillement', 'linge', 'buanderie', 'vestiaire'):
        fl = ('Marble', (164, 164, 158)) if has('cantine', 'cuisine') else ('Fabric', (88, 72, 64)) if has('quartiers', 'detente', 'projection', 'musique', 'recueillement') else ('SmoothPlastic', (140, 142, 138))
        return dict(kind='vie', wall=('SmoothPlastic', (188, 196, 202)), wains=('SmoothPlastic', (86, 102, 120)), floor=fl, ceil=('SmoothPlastic', (200, 204, 206)), rib=('Metal', (104, 110, 116)))
    if has('reserve', 'placard', 'consigne', 'magasin', 'stock', 'entrepot', 'pieces', 'outillage', 'huiles', 'carburant', 'local_tech'):
        return dict(kind='stock', wall=('Metal', (130, 132, 128)), wains=('Metal', (94, 96, 94)), floor=('Concrete', (118, 118, 114)), ceil=('Metal', (108, 110, 108)), rib=('Metal', (80, 82, 80)))
    if e.secteur in ('machines', 'fonds'):
        return dict(kind='machines', wall=('Metal', (102, 110, 104)), wains=('Metal', (68, 76, 70)), floor=('Concrete', (96, 96, 92)), ceil=('Metal', (88, 92, 90)), rib=('Metal', (56, 60, 58)))
    return dict(kind='hub', wall=('Metal', (140, 146, 150)), wains=('Metal', (70, 74, 78)), floor=('DiamondPlate', (90, 94, 98)), ceil=('Metal', (110, 114, 118)), rib=('Metal', (62, 66, 70)))
for e in ESP: e.st = style(e)

# ================================================================ portes en coordonnées monde
DOORS = []
for x, z, mur, w, t in N.PORTES:
    DOORS.append(dict(axis='X' if mur == 'z' else 'Z', line=(-z*S if mur == 'z' else x*S), c=(x*S if mur == 'z' else -z*S), w=w*S, t=t, X=x*S, Z=-z*S))

# ================================================================ murs
def edges(e):
    """(nom, axe le long, coordonnée fixe, u0, u1, normale vers l'intérieur)"""
    return [('N', 'X', e.Z0, e.X0, e.X1, +1), ('S', 'X', e.Z1, e.X0, e.X1, -1), ('W', 'Z', e.X0, e.Z0, e.Z1, +1), ('E', 'Z', e.X1, e.Z0, e.Z1, -1)]

def holes_for(e, side, axis, fixed, u0, u1):
    H = []
    for d in DOORS:
        if d['axis'] == axis and abs(d['line'] - fixed) < 0.05 and u0 - 0.1 <= d['c'] <= u1 + 0.1:
            fy = e.floor_at(d['Z'])
            H.append((d['c'] - d['w']/2, d['c'] + d['w']/2, fy - 1, fy + (DOOR_H + 1.5 if d['w'] >= 10 else DOOR_H), 'porte', d))
    if e.couloir:
        for o in COUL:
            if o is e or not vert_overlap(e, o): continue
            if axis == 'X' and o.Z0 - 0.05 <= fixed <= o.Z1 + 0.05:
                a, b = max(u0, o.X0), min(u1, o.X1)
            elif axis == 'Z' and o.X0 - 0.05 <= fixed <= o.X1 + 0.05:
                a, b = max(u0, o.Z0), min(u1, o.Z1)
            else: continue
            if b - a > 0.2: H.append((a, b, -1e4, 1e4, 'jonction', o))
    return H

def wall_boxes(fr, axis, fixed, nrm, u0, u1, y0, y1, holes, mat, col, th=WT, inset=0.0, name='Mur'):
    """boîtes d'un mur plein percé de trous (u0..u1 le long de l'axe, y0..y1), décalé de inset vers l'intérieur"""
    pts = sorted(set([u0, u1] + [max(u0, min(u1, h[0])) for h in holes] + [max(u0, min(u1, h[1])) for h in holes]))
    off = fixed + nrm*(inset + th/2)
    for a, b in zip(pts[:-1], pts[1:]):
        if b - a < 0.02: continue
        m = (a + b)/2; cov = sorted([(h[2], h[3]) for h in holes if h[0] <= m <= h[1]])
        ys = []; cur = y0
        for ha, hb in cov:
            if ha > cur: ys.append((cur, min(ha, y1)))
            cur = max(cur, hb)
        if cur < y1: ys.append((cur, y1))
        for ya, yb in ys:
            if yb - ya < 0.02: continue
            if axis == 'X': fr.box(((a + b)/2, (ya + yb)/2, off), (b - a, yb - ya, th), mat, col, name=name)
            else: fr.box((off, (ya + yb)/2, (a + b)/2), (th, yb - ya, b - a), mat, col, name=name)

def free_intervals(u0, u1, holes, ylo, yhi):
    """intervalles le long du mur sans trou couvrant la bande ylo..yhi"""
    cut = sorted([(h[0], h[1]) for h in holes if h[2] < yhi and h[3] > ylo])
    out = []; cur = u0
    for a, b in cut:
        if a > cur: out.append((cur, min(a, u1)))
        cur = max(cur, b)
    if cur < u1: out.append((cur, u1))
    return [(a, b) for a, b in out if b - a > 0.3]

def build_walls(e):
    fr = Frame(sc, e.folder + '/Structure', (0, 0, 0))
    st = e.st; e.wall_holes = {}
    if e.d.get('forme') == 'octo': return build_octo(e)
    for side, axis, fixed, u0, u1, nrm in edges(e):
        H = holes_for(e, side, axis, fixed, u0, u1); e.wall_holes[side] = H
        if e.couloir and e.d.get('verre'):
            build_glass_side(e, fr, axis, fixed, nrm, u0, u1, H); continue
        y0, y1 = e.ymin - 1, e.ymax + 1
        wall_boxes(fr, axis, fixed, nrm, u0, u1, y0, y1, H, *st['wall'])
        # soubassement (plinthe haute) et plinthe
        wy = 3.2 if st['kind'] not in ('sanitaire',) else 4.0
        for a, b in free_intervals(u0, u1, H, e.ymin, e.ymin + wy):
            seg = [(a, b, -1e4, 1e4)]
            if e.esc: continue
            wall_boxes(fr, axis, fixed, nrm, a, b, e.ymin, e.ymin + wy, [], *st['wains'], th=0.12, inset=WT, name='Soubassement')
            wall_boxes(fr, axis, fixed, nrm, a, b, e.ymin, e.ymin + 0.5, [], 'Metal', (40, 42, 44), th=0.2, inset=WT, name='Plinthe')
            wall_boxes(fr, axis, fixed, nrm, a, b, e.ymin + wy, e.ymin + wy + 0.18, [], *st['rib'], th=0.2, inset=WT, name='Cimaise')
        # corniche sous plafond
        if not e.esc:
            for a, b in free_intervals(u0, u1, H, e.ymax - 0.6, e.ymax):
                wall_boxes(fr, axis, fixed, nrm, a, b, e.ymax - 0.6, e.ymax, [], *st['rib'], th=0.3, inset=WT, name='Corniche')

def build_octo(e):
    fr = Frame(sc, e.folder + '/Structure', (0, 0, 0)); st = e.st
    x0, z0, x1, z1 = e.d['rect']; c = 0.29*(x1 - x0)
    P = [(x0 + c, z1), (x1 - c, z1), (x1, z1 - c), (x1, z0 + c), (x1 - c, z0), (x0 + c, z0), (x0, z0 + c), (x0, z1 - c)]
    P = [(px*S, -pz*S) for px, pz in P]
    cx, cz = (e.X0 + e.X1)/2, (e.Z0 + e.Z1)/2
    for (ax, az), (bx, bz) in zip(P, P[1:] + P[:1]):
        L = math.hypot(bx - ax, bz - az); mx, mz = (ax + bx)/2, (az + bz)/2
        nx, nz = cx - mx, cz - mz; ln = math.hypot(nx, nz); nx, nz = nx/ln, nz/ln
        yaw = math.atan2(nx, nz)                      # +Z local vers l'intérieur, +X local le long du mur
        f = Frame(sc, e.folder + '/Structure', (mx, 0, mz), rot_y(yaw))
        H = []
        for d in DOORS:
            if abs((d['X'] - mx)*nx + (d['Z'] - mz)*nz) < 0.1 and math.hypot(d['X'] - mx, d['Z'] - mz) < L/2:
                H.append((-d['w']/2, d['w']/2, e.elev - 1, e.elev + DOOR_H + 1.5, 'porte', d))
        wall_boxes(f, 'X', 0, 1, -L/2 - 0.6, L/2 + 0.6, e.ymin - 1, e.ymax + 1, H, *st['wall'])
        for a, b in free_intervals(-L/2, L/2, H, e.ymin, e.ymin + 3.2):
            wall_boxes(f, 'X', 0, 1, a, b, e.ymin, e.ymin + 3.2, [], *st['wains'], th=0.12, inset=WT, name='Soubassement')
        for k in (-1, 1):                              # piliers aux angles
            f.box((k*L/2, e.ymin + e.h/2, WT + 0.6), (1.6, e.h, 1.2), *st['rib'], name='Pilier')

# ================================================================ sols, plafonds, gaines
DUCT_W, DUCT_H, DUCT_T = 4.6, 4.6, 0.3
def duct_rects():
    """gaines en rectangles monde, à leur niveau : sol de gaine = élévation + 13"""
    out = []
    for g in N.GAINES:
        if g.get('vertical'): continue
        for (ax, az), (bx, bz) in zip(g['pts'][:-1], g['pts'][1:]):
            ax, az, bx, bz = ax*S, -az*S, bx*S, -bz*S; hw = DUCT_W/2 + DUCT_T
            r = (min(ax, bx) - hw, min(az, bz) - hw, max(ax, bx) + hw, max(az, bz) + hw)
            out.append(dict(r=r, y=g['elev'] + 13, branche=g.get('branche', False), id=g['id']))
    return out
DUCTS = duct_rects()
GRILLE_W = [(x*S, -z*S, sid, soud) for x, z, sid, soud in N.GRILLES]

def build_floor_ceiling(e):
    fr = Frame(sc, e.folder + '/Structure', (0, 0, 0)); st = e.st
    W, D = e.X1 - e.X0, e.Z1 - e.Z0; cx, cz = (e.X0 + e.X1)/2, (e.Z0 + e.Z1)/2
    if e.esc: return build_stairs(e, fr)
    fr.box((cx, e.elev - 0.5, cz), (W, 1, D), *st['floor'], name='Sol')
    # plafond, percé là où une grille de gaine débouche
    yc = e.elev + e.h
    holes = [(gx - 2.4, gz - 2.4, gx + 2.4, gz + 2.4) for gx, gz, sid, soud in GRILLE_W if sid == e.id and e.h <= 12.5]
    if e.d.get('verre') or e.id == 'serre':
        return
    slab_with_holes(fr, e.X0, e.Z0, e.X1, e.Z1, yc, 1.0, holes, *st['ceil'])
    e.ceil_holes = holes

def slab_with_holes(fr, X0, Z0, X1, Z1, y, th, holes, mat, col, name='Plafond'):
    xs = sorted(set([X0, X1] + [max(X0, min(X1, v)) for h in holes for v in (h[0], h[2])]))
    for a, b in zip(xs[:-1], xs[1:]):
        if b - a < 0.02: continue
        m = (a + b)/2; cov = sorted([(h[1], h[3]) for h in holes if h[0] <= m <= h[2]])
        cur = Z0
        for ha, hb in cov + [(Z1, Z1)]:
            if ha - cur > 0.02: fr.box(((a + b)/2, y + th/2, (cur + ha)/2), (b - a, th, ha - cur), mat, col, name=name)
            cur = max(cur, hb)

def build_stairs(e, fr):
    st = e.st; za, zb, ea, eb = e.esc
    Za, Zb = -za*S, -zb*S                       # Za > Zb (monde)
    W = e.X1 - e.X0; cx = (e.X0 + e.X1)/2
    lo, hi = (ea, eb)
    # paliers
    Zlow0, Zlow1 = Za, e.Z1                     # côté za (bas : plan z < za -> monde Z > Za)
    if Zlow1 - Zlow0 > 0.05: fr.box((cx, lo - 0.5, (Zlow0 + Zlow1)/2), (W, 1, Zlow1 - Zlow0), *st['floor'], name='Palier')
    if Zb - e.Z0 > 0.05: fr.box((cx, hi - 0.5, (e.Z0 + Zb)/2), (W, 1, Zb - e.Z0), *st['floor'], name='Palier')
    n = int(round(abs(hi - lo))); tread = (Za - Zb)/n
    for k in range(n):
        top = lo + (k + 1)*(hi - lo)/n; Zc = Za - (k + 0.5)*tread
        fr.box((cx, (lo - 1 + top)/2, Zc), (W - 2*WT, top - lo + 1, tread), 'DiamondPlate', (84, 86, 88), name='Marche')
        fr.box((cx, top - 0.05, Zc - tread/2 + 0.15), (W - 2*WT, 0.12, 0.3), 'SmoothPlastic', (196, 160, 30), name='NezDeMarche', cc=False)
    # plafonds : bas côté za, haut côté zb ; retombée au changement
    fr.box((cx, lo + e.h + 0.5, (Za + e.Z1)/2), (W, 1, e.Z1 - Za), *st['ceil'], name='Plafond')
    fr.box((cx, hi + e.h + 0.5, (e.Z0 + Za)/2), (W, 1, Za - e.Z0), *st['ceil'], name='Plafond')
    fr.box((cx, (lo + e.h + hi + e.h)/2, Za), (W, hi - lo, 1), *st['ceil'], name='Retombee')
    # mains courantes
    for k in (-1, 1):
        x = cx + k*(W/2 - WT - 0.5)
        fr.pipe((x, lo + 3.2, Za), (x, hi + 3.2, Zb), 0.25, 'Metal', (170, 172, 170), name='MainCourante')
        for t in (0.0, 0.5, 1.0):
            Z = Za + (Zb - Za)*t; y = lo + (hi - lo)*t
            fr.box((x, y + 1.6, Z), (0.2, 3.2, 0.2), 'Metal', (120, 122, 120), name='Montant')

def build_ducts():
    """gaines praticables : union de rectangles, murs supprimés là où deux gaines se rejoignent"""
    fr = Frame(sc, 'Nadir4/Gaines', (0, 0, 0)); col = (120, 124, 120)
    for i, d in enumerate(DUCTS):
        X0, Z0, X1, Z1 = d['r']; y = d['y']
        holes = [(gx - 2.3, gz - 2.3, gx + 2.3, gz + 2.3) for gx, gz, sid, soud in GRILLE_W
                 if BYID.get(sid) and BYID[sid].h <= 12.5 and X0 <= gx <= X1 and Z0 <= gz <= Z1 and abs(BYID[sid].elev + 13 - y) < 0.5]
        slab_with_holes(fr, X0, Z0, X1, Z1, y, DUCT_T, holes, 'Metal', col, name='GaineFond')
        fr.box(((X0 + X1)/2, y + DUCT_H + DUCT_T*1.5, (Z0 + Z1)/2), (X1 - X0, DUCT_T, Z1 - Z0), 'Metal', col, name='GaineDessus')
        for side, axis, fixed, u0, u1 in (('N', 'X', Z0, X0, X1), ('S', 'X', Z1, X0, X1), ('W', 'Z', X0, Z0, Z1), ('E', 'Z', X1, Z0, Z1)):
            H = []
            for j, o in enumerate(DUCTS):
                if j == i or abs(o['y'] - y) > 0.5: continue
                oX0, oZ0, oX1, oZ1 = o['r']
                if axis == 'X' and oZ0 + DUCT_T < fixed < oZ1 - DUCT_T: a, b = max(u0, oX0 + DUCT_T), min(u1, oX1 - DUCT_T)
                elif axis == 'Z' and oX0 + DUCT_T < fixed < oX1 - DUCT_T: a, b = max(u0, oZ0 + DUCT_T), min(u1, oZ1 - DUCT_T)
                else: continue
                if b - a > 0.2: H.append((a, b, -1e4, 1e4))
            nrm = 1 if side in ('N', 'W') else -1
            wall_boxes(fr, axis, fixed, nrm, u0, u1, y, y + DUCT_H + DUCT_T, H, 'Metal', col, th=DUCT_T, name='GaineParoi')
    # grilles
    for gx, gz, sid, soud in GRILLE_W:
        e = BYID.get(sid)
        if not e: continue
        f = Frame(sc, e.folder + '/Grille', (gx, e.elev + min(e.h, 12.5), gz))
        y = 0.1 if e.h <= 12.5 else 0.0
        if e.h > 12.5: y = 13 - e.h                       # gaine apparente dans les salles hautes : grille au bout de la gaine
        f.box((0, y + 0.15, 0), (4.8, 0.3, 4.8), 'Metal', (70, 72, 70), name='CadreGrille', tags=['Grille'] + (['Soudee'] if soud else []))
        for k in range(-3, 4):
            f.box((k*0.62, y - 0.05, 0), (0.18, 0.25, 4.4), 'Metal', (54, 56, 56), name='Lame', cc=False)
        if soud:
            for sx, sz in ((-2.3, -2.3), (2.3, -2.3), (-2.3, 2.3), (2.3, 2.3), (0, -2.35), (0, 2.35)):
                f.box((sx, y - 0.1, sz), (0.7, 0.2, 0.7), 'CorrodedMetal', (120, 80, 50), name='Soudure', cc=False)
    # gaines apparentes sous les plafonds hauts (habillage extérieur visible)
    for d in DUCTS:
        if not d['branche']: continue

# ================================================================ habillage des couloirs : arches, tuyaux, chemins de câbles, lumières
def build_corridor_dressing(e):
    if e.esc or e.d.get('verre'): return
    st = e.st; fr = Frame(sc, e.folder + '/Habillage', (0, 0, 0))
    W, D = e.X1 - e.X0, e.Z1 - e.Z0; along_x = W >= D
    L = W if along_x else D; wid = D if along_x else W
    u0 = e.X0 if along_x else e.Z0; y0 = e.elev; h = e.h
    def P(u, v, y):          # u le long, v en travers (0 = bord moins, wid = bord plus)
        return (u, y, e.Z0 + v) if along_x else (e.X0 + v, y, u)
    def S3(lu, lv, ly): return (lu, ly, lv) if along_x else (lv, ly, lu)
    sides = ('N', 'S') if along_x else ('W', 'E')
    H0, H1 = e.wall_holes.get(sides[0], []), e.wall_holes.get(sides[1], [])
    def in_hole(u, H): return any(h[0] - 1 <= u <= h[1] + 1 and h[4] == 'jonction' or (h[0] - 0.6 <= u <= h[1] + 0.6) for h in H)
    n = max(1, int(L/12)); step = L/n
    for k in range(n + 1):
        u = u0 + k*step
        if k in (0, n): continue
        a0, a1 = in_hole(u, H0), in_hole(u, H1)
        if not a0: fr.box(P(u, WT + 0.35, y0 + h/2), S3(1.0, 0.7, h), *st['rib'], name='Arche')
        if not a1: fr.box(P(u, wid - WT - 0.35, y0 + h/2), S3(1.0, 0.7, h), *st['rib'], name='Arche')
        if not (a0 and a1): fr.box(P(u, wid/2, y0 + h - 0.35), S3(1.0, wid - 2*WT, 0.7), *st['rib'], name='Arche')
        # goussets d'angle
        for v, sgn, bad in ((WT + 0.7, 1, a0), (wid - WT - 0.7, -1, a1)):
            if bad: continue
            fr.box(P(u, v + sgn*0.5, y0 + h - 1.2), S3(0.9, 1.4, 0.5), *st['rib'], name='Gousset', R=None)
        # lumières : bandeau normal un arc sur deux, feu de secours un arc sur trois
        if k % 2 == 1:
            it = fr.box(P(u + step/2, wid/2, y0 + h - 0.2), S3(3.2, 0.7, 0.25), 'SmoothPlastic', (230, 232, 228), name='Plafonnier',
                        tags=['LumiereNormale'], children=[dict(cls='SurfaceLight', Brightness=1.3, Color=(236, 240, 255), Range=18, Shadows=False, Enabled=False, Face=4, Angle=120)])
        if k % 3 == 0:
            v = WT + 0.25 if (k//3) % 2 == 0 else wid - WT - 0.25
            if not in_hole(u + step/2, H0 if v < wid/2 else H1):
                fr.box(P(u + step/2, v, y0 + h - 2.2), S3(0.8, 0.5, 0.5), 'Metal', (40, 40, 40), name='BoitierSecours')
                fr.box(P(u + step/2, v + (0.3 if v < wid/2 else -0.3), y0 + h - 2.2), S3(0.6, 0.15, 0.35), 'Neon', (255, 40, 25), name='FeuSecours',
                       cc=False, shadow=False, tags=['LumiereSecours'],
                       children=[dict(cls='PointLight', Brightness=1.6, Color=(255, 50, 30), Range=16, Shadows=True, Enabled=True)])
    # tuyaux le long d'un côté, chemin de câbles de l'autre (interrompus aux jonctions)
    def runs(H):
        return free_intervals(u0, u0 + L, [h for h in H if h[4] == 'jonction'], y0 + h - 2, y0 + h)
    for a, b in runs(H0):
        for dv, dy, dd, col in ((1.3, h - 1.3, 0.9, (120, 128, 132)), (2.3, h - 1.0, 0.6, (150, 70, 50)), (1.2, h - 2.3, 0.5, (70, 110, 150))):
            fr.pipe(P(a + 0.3, dv, y0 + dy), P(b - 0.3, dv, y0 + dy), dd, 'Metal', col, name='Tuyau')
        for u in [a + 0.6 + i*8 for i in range(int((b - a - 1.2)/8) + 1)]:
            fr.box(P(u, 1.6, y0 + h - 1.0), S3(0.3, 2.2, 2.2), 'Metal', (60, 62, 64), name='Collier', cc=False)
    for a, b in runs(H1):
        fr.box(P((a + b)/2, wid - 1.6, y0 + h - 0.9), S3(b - a - 0.6, 1.8, 0.12), 'Metal', (100, 104, 106), name='ChemindeCables', cc=False)
        for dv, col in ((-0.4, (30, 30, 32)), (0.0, (160, 40, 30)), (0.4, (30, 30, 32))):
            fr.pipe(P(a + 0.4, wid - 1.6 + dv, y0 + h - 0.72), P(b - 0.4, wid - 1.6 + dv, y0 + h - 0.72), 0.22, 'SmoothPlastic', col, name='Cable', cc=False, shadow=False)
    # caillebotis central et bandes de sol
    fr.box(P(u0 + L/2, wid/2, y0 + 0.03), S3(L - 0.4, 3.0, 0.06), 'Metal', (64, 68, 70), name='Caillebotis', cc=False)
    for v in (2.4, wid - 2.4):
        fr.box(P(u0 + L/2, v, y0 + 0.02), S3(L - 0.4, 0.25, 0.04), 'SmoothPlastic', (186, 150, 30), name='BandeSol', cc=False, shadow=False)

def build_glass_side(e, fr, axis, fixed, nrm, u0, u1, H):
    """tunnel de verre : arceaux tous les 6 studs, vitrage entre eux"""
    y0, h = e.elev, e.h
    wall_boxes(fr, axis, fixed, nrm, u0, u1, y0, y0 + 1.2, H, 'Metal', (60, 64, 68), name='Muret')
    wall_boxes(fr, axis, fixed, nrm, u0, u1, y0 + 1.2, y0 + h, H, 'Glass', (120, 170, 190), name='Vitrage')
    for it in sc.items[-6:]:
        if it['n'] == 'Vitrage': it['t'] = 0.75; it['r'] = 0.15

def build_tunnel_extras(e):
    if not e.d.get('verre'): return
    fr = Frame(sc, e.folder + '/Habillage', (0, 0, 0))
    W, D = e.X1 - e.X0, e.Z1 - e.Z0; along_x = W >= D; L = W if along_x else D; wid = D if along_x else W
    u0 = e.X0 if along_x else e.Z0; y0, h = e.elev, e.h
    def P(u, v, y): return (u, y, e.Z0 + v) if along_x else (e.X0 + v, y, u)
    def S3(lu, lv, ly): return (lu, ly, lv) if along_x else (lv, ly, lu)
    it = fr.box(P(u0 + L/2, wid/2, y0 + h + 0.15), S3(L, wid, 0.3), 'Glass', (120, 170, 190), name='Verriere'); it['t'] = 0.75; it['r'] = 0.15
    for k in range(int(L/6) + 1):
        u = u0 + min(L - 0.4, max(0.4, k*6))
        fr.box(P(u, 0.4, y0 + h/2), S3(0.6, 0.8, h), 'Metal', (60, 64, 68), name='Arceau')
        fr.box(P(u, wid - 0.4, y0 + h/2), S3(0.6, 0.8, h), 'Metal', (60, 64, 68), name='Arceau')
        fr.box(P(u, wid/2, y0 + h + 0.2), S3(0.6, wid, 0.8), 'Metal', (60, 64, 68), name='Arceau')
    for v in (1.0, wid - 1.0):                            # balisage lumineux au sol
        for k in range(int(L/4)):
            fr.box(P(u0 + 2 + k*4, v, y0 + 0.05), S3(0.8, 0.3, 0.1), 'Neon', (120, 200, 255), name='Balisage', cc=False, shadow=False, tags=['LumiereSecours'])
        fr.light(P(u0 + L/2, v, y0 + 0.6), 'PointLight', (110, 190, 255), 0.8, 14, tags=['LumiereSecours'])

# ================================================================ portes : cadres, panneaux de commande, battants (fermés, invisibles tant que les mécaniques ne sont pas branchées)
TYPE_COL = dict(porte=(60, 200, 90), motorisee=(160, 90, 220), badge1=(60, 200, 90), badge2=(240, 160, 30), badge3=(230, 50, 40),
                volet=(60, 130, 230), sas=(30, 190, 200), pression=(30, 190, 200), etanche=(40, 90, 170), navette=(60, 130, 230), ouvert=None)
def build_doors():
    for d in DOORS:
        if d['t'] == 'ouvert': continue
        # espaces de part et d'autre
        X, Z = d['X'], d['Z']
        fl = 0.0
        for e in ESP:
            if e.X0 - 0.1 <= X <= e.X1 + 0.1 and e.Z0 - 0.1 <= Z <= e.Z1 + 0.1: fl = e.floor_at(Z); break
        yaw = 0.0 if d['axis'] == 'X' else math.pi/2
        f = Frame(sc, f"Nadir4/Portes/{d['t']}", (X, fl, Z), rot_y(yaw))
        w = d['w']; hgt = DOOR_H + 1.5 if w >= 10 else DOOR_H; dep = 2*WT + 0.5
        heavy = d['t'] in ('sas', 'pression', 'etanche', 'navette')
        fw = 1.0 if heavy else 0.6; col = (70, 74, 78) if not heavy else (52, 56, 60)
        for k in (-1, 1):
            f.box((k*(w/2 + fw/2 - 0.3), hgt/2, 0), (fw, hgt, dep), 'Metal', col, name='Montant')
        f.box((0, hgt + fw/2 - 0.3, 0), (w + 2*fw - 0.6, fw, dep), 'Metal', col, name='Linteau')
        f.box((0, 0.04, 0), (w, 0.08, dep), 'DiamondPlate', (190, 160, 40) if heavy else (100, 102, 104), name='Seuil', cc=False)
        # battant fermé (invisible et traversable pour l'instant : les scripts de portes le feront coulisser)
        f.box((0, hgt/2, 0), (w, hgt, 0.4), 'Metal', (120, 124, 126), name='Battant', tr=1.0, cc=False, tags=['Porte', 'Porte_' + d['t']])
        if heavy:
            for k in (-1, 1):
                f.box((w/2 + fw + 0.2, hgt*0.55, k*(dep/2 + 0.05)), (0.25, 0.25, 0.3), 'Metal', (40, 40, 40), name='Axe')
                f.cyl((w/2 + fw + 0.2, hgt*0.55, k*(dep/2 + 0.25)), 0.15, 1.8, 'z', 'Metal', (170, 40, 30), name='Volant')
            for k in (-1, 1):
                for j in range(5):
                    f.box((k*(w/2 + fw/2 - 0.3), 0.5 + j*1.6, 0), (fw + 0.05, 0.8, dep + 0.04), 'SmoothPlastic', (200, 160, 20) if j % 2 == 0 else (25, 25, 25), name='Hachures', cc=False)
        if d['t'] == 'volet':
            f.box((0, hgt + 1.1, 0), (w + 1.2, 1.4, dep + 0.6), 'Metal', (56, 60, 64), name='CaissonVolet')
        # boîtiers de commande des deux côtés
        c = TYPE_COL.get(d['t'])
        if c:
            for k in (-1, 1):
                f.box((w/2 + fw + 0.9, 4.6, k*(dep/2 + 0.15)), (0.9, 1.4, 0.3), 'Metal', (46, 48, 50), name='BoitierPorte')
                f.box((w/2 + fw + 0.9, 5.0, k*(dep/2 + 0.32)), (0.5, 0.25, 0.05), 'Neon', c, name='Voyant', cc=False, shadow=False, tags=['Voyant'])
                if d['t'].startswith('badge'):
                    f.text((w/2 + fw + 0.9, 4.3, k*(dep/2 + 0.32)), (0.6, 0.4, 0.04), 'NIV. ' + d['t'][-1], txtcol=(255, 255, 255), bg=c,
                           face='Front' if k < 0 else 'Back', name='Lecteur', cc=False)

# ================================================================ lumières des salles
def build_room_lights(e):
    if e.couloir: return
    f = Frame(sc, e.folder + '/Lumieres', (0, 0, 0)); y = e.elev + e.h
    W, D = e.X1 - e.X0, e.Z1 - e.Z0
    nx, nz = max(1, round(W/16)), max(1, round(D/16))
    long_x = W >= D
    for i in range(nx):
        for j in range(nz):
            X = e.X0 + (i + 0.5)*W/nx; Z = e.Z0 + (j + 0.5)*D/nz
            if any(h[0] - 1 < X < h[2] + 1 and h[1] - 1 < Z < h[3] + 1 for h in getattr(e, 'ceil_holes', [])): X += 4
            sz = (4.2, 0.25, 1.2) if long_x else (1.2, 0.25, 4.2)
            f.box((X, y - 0.15, Z), (sz[0] + 0.3, 0.2, sz[2] + 0.3), 'Metal', (90, 92, 94), name='CadrePlafonnier', cc=False)
            f.box((X, y - 0.3, Z), sz, 'SmoothPlastic', (226, 228, 224), name='Plafonnier', cc=False, tags=['LumiereNormale'],
                  children=[dict(cls='SurfaceLight', Brightness=1.1, Color=(240, 242, 255), Range=max(14, e.h + 6), Shadows=(i + j) % 2 == 0, Enabled=False, Face=4, Angle=120)])
    # éclairage de secours : un bloc autonome au-dessus d'une porte
    door = None
    for side, H in getattr(e, 'wall_holes', {}).items():
        for h in H:
            if h[4] == 'porte': door = (side, h); break
        if door: break
    if door:
        side, h = door; u = (h[0] + h[1])/2; yy = e.elev + min(DOOR_H + 2.2, e.h - 1)
        pos = {'N': (u, yy, e.Z0 + WT + 0.35), 'S': (u, yy, e.Z1 - WT - 0.35), 'W': (e.X0 + WT + 0.35, yy, u), 'E': (e.X1 - WT - 0.35, yy, u)}[side]
        f.box(pos, (1.4, 0.6, 0.6) if side in 'NS' else (0.6, 0.6, 1.4), 'SmoothPlastic', (230, 230, 225), name='BlocSecours', cc=False)
        it = f.box((pos[0], pos[1] - 0.35, pos[2]), (1.0, 0.12, 0.4) if side in 'NS' else (0.4, 0.12, 1.0), 'Neon', (255, 70, 40), name='FeuSecours', cc=False, shadow=False,
                   tags=['LumiereSecours'], children=[dict(cls='PointLight', Brightness=1.2, Color=(255, 60, 35), Range=max(16, min(28, max(W, D)*0.7)), Shadows=True, Enabled=True)])

# ================================================================ extérieur : fond marin visible depuis les vitrages
def build_exterior():
    f = Frame(sc, 'Nadir4/Exterieur', (0, 0, 0))
    zones = [(-560, 30, -40, 420), (-40, 222, 40, 420), (40, 30, 300, 300), (380, -110, 760, 120)]       # (x0, z0, x1, z1) du, au niveau 0 seulement
    for x0, z0, x1, z1 in zones:
        X0, Z0, X1, Z1 = x0*S, -z1*S, x1*S, -z0*S
        f.box(((X0 + X1)/2, -2.2, (Z0 + Z1)/2), (X1 - X0, 2, Z1 - Z0), 'Sand', (46, 52, 54), name='FondMarin', cc=False)
    for k in range(260):
        x0, z0, x1, z1 = zones[k % len(zones)]
        X = R.uniform(x0, x1)*S; Z = -R.uniform(z0, z1)*S
        if any(e.X0 - 6 < X < e.X1 + 6 and e.Z0 - 6 < Z < e.Z1 + 6 for e in ESP): continue
        s = R.uniform(2, 11)
        f.box((X, -1.6 + s*0.25, Z), (s, s*R.uniform(0.4, 0.9), s*R.uniform(0.6, 1.2)), 'Rock', (52, 56, 58), name='Rocher', R=rot_y(R.uniform(0, 6.28)), cc=False)
    # neige marine autour des vitrages
    for e in ESP:
        if e.d.get('verre') or e.id in ('serre', 'observatoire', 'module_prel'):
            cx, cz = (e.X0 + e.X1)/2, (e.Z0 + e.Z1)/2
            f.box((cx, e.elev + 26, cz), (max(30, e.X1 - e.X0 + 40), 1, max(30, e.Z1 - e.Z0 + 40)), 'SmoothPlastic', (0, 0, 0), tr=1, cc=False, shadow=False, name='EmetteurNeige',
                  children=[dict(cls='ParticleEmitter', Rate=40, Lifetime=(12, 20), Speed=(0.3, 0.8), Size=0.12, Transp=(0.2, 0.7), Color=(200, 215, 220),
                                 Acc=(0.1, -0.4, 0), Spread=40, Dir=4)])

# ================================================================ assemblage
def build_all(meubler=None):
    for e in ESP: build_walls(e)
    for e in ESP: build_floor_ceiling(e)
    for e in COUL: build_corridor_dressing(e); build_tunnel_extras(e)
    build_ducts(); build_doors()
    for e in SAL: build_room_lights(e)
    for e in COUL:
        if e.d.get('verre'): continue
    build_exterior()
    if meubler:
        for e in SAL: meubler(sc, e)
    nav = BYID['navette']
    sc.add('Nadir4/Arrivee', 'SpawnLocation', 'Apparition', (8, 1, 8), ((nav.X0 + nav.X1)/2, nav.elev + 0.5, (nav.Z0 + nav.Z1)/2 + 10), I3, 'DiamondPlate', (60, 130, 230))

LIGHTING = dict(ambient=(14, 16, 20), brightness=0, outdoor=(4, 8, 12), diffuse=0.25, specular=0.7, exposure=0.3, fog=(4, 12, 18), fog_end=260,
                atmos=dict(density=0.38, offset=0.0, color=(14, 30, 40), decay=(4, 10, 16), haze=1.6),
                cc=dict(brightness=0.0, contrast=0.12, saturation=-0.18, tint=(232, 244, 248)), bloom=dict(intensity=0.6, size=22, threshold=1.6))

SCRIPT_COURANT = r'''-- Nadir-4 : courant de la base. Passer ReplicatedStorage.Courant à true rallume l'éclairage normal.
local CS = game:GetService("CollectionService")
local RS = game:GetService("ReplicatedStorage")
local courant = RS:WaitForChild("Courant")
local function appliquer()
	local on = courant.Value
	for _, p in ipairs(CS:GetTagged("LumiereNormale")) do
		p.Material = on and Enum.Material.Neon or Enum.Material.SmoothPlastic
		for _, l in ipairs(p:GetChildren()) do if l:IsA("Light") then l.Enabled = on end end
	end
	for _, p in ipairs(CS:GetTagged("LumiereSecours")) do
		for _, l in ipairs(p:GetChildren()) do if l:IsA("Light") then l.Brightness = on and 0.4 or 1.4 end end
	end
end
courant.Changed:Connect(appliquer)
appliquer()
-- quelques plafonniers grésillent
local normales = CS:GetTagged("LumiereNormale")
task.spawn(function()
	while true do
		task.wait(math.random(2, 6))
		if courant.Value and #normales > 0 then
			local p = normales[math.random(1, #normales)]
			local l = p:FindFirstChildWhichIsA("Light")
			if l then
				for i = 1, math.random(2, 5) do l.Enabled = false; p.Material = Enum.Material.SmoothPlastic; task.wait(0.05 + math.random() * 0.12); l.Enabled = true; p.Material = Enum.Material.Neon; task.wait(0.04 + math.random() * 0.2) end
			end
		end
	end
end)
'''

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    try:
        import nadir_props as P
        meub = P.meubler
    except ImportError:
        meub = None
    build_all(meub)
    write_rbxlx(sc, os.path.join(out, 'nadir4.rbxlx'), LIGHTING, scripts=[('Courant', SCRIPT_COURANT, 'ServerScriptService')], rs_values=[('Courant', False)])
    write_json(sc, os.path.join(out, 'nadir4.json'))
    from collections import Counter
    cnt = Counter(it['n'] for it in sc.items)
    print(len(sc.items), 'pièces ;', sum(len(it['ch']) for it in sc.items), 'enfants (lumières, textes, particules)')
    print(cnt.most_common(25))
