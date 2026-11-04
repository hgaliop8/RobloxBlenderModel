"""Stockage et technique (Nadir-4) : rayonnages, caisses, fûts, bouteilles de gaz, établi, armoires électriques, baie serveur,
pupitre, pompe, cuve, groupe électrogène, transformateur, vannes, extincteur.
Convention : origine au sol ; meubles muraux : dos à y = 0, façade vers +Y ; objets libres : centrés."""
import bpy, bmesh, math, random
from mathutils import Vector, noise
from kit_meshes import *
from kit_labo import etagere_metal, M_inox, M_chrome, M_laiton

JAUNE = (210, 170, 40); ROUGE = (170, 34, 28); VERT_MACH = (70, 96, 84); GRIS_MACH = (110, 118, 124); BLEU_MACH = (52, 84, 120)

def anneau(name, r, rt, loc, material, axe='Z', seg=32):
    """tore (volant de vanne, cerclage)"""
    bm = bmesh.new(); n2 = 10
    V = [[bm.verts.new(((r + rt*math.cos(b))*math.cos(a), (r + rt*math.cos(b))*math.sin(a), rt*math.sin(b)))
          for b in [2*math.pi*j/n2 for j in range(n2)]] for a in [2*math.pi*i/seg for i in range(seg)]]
    for i in range(seg):
        for j in range(n2): bm.faces.new((V[i][j], V[(i + 1) % seg][j], V[(i + 1) % seg][(j + 1) % n2], V[i][(j + 1) % n2]))
    ob = obj_from_bm(bm, name, material); ob.location = loc
    if axe == 'X': ob.rotation_euler = (0, math.pi/2, 0)
    elif axe == 'Y': ob.rotation_euler = (math.pi/2, 0, 0)
    return ob

def volant(loc, r, material, axe='Y'):
    """volant de vanne : jante + 3 rayons + moyeu"""
    x, y, z = loc; o = [anneau('Volant', r, r*0.12, loc, material, axe)]
    for k in range(3):
        a = k*2*math.pi/3; ca, sa = math.cos(a)*r, math.sin(a)*r
        d = (ca, 0, sa) if axe == 'Y' else ((0, ca, sa) if axe == 'X' else (ca, sa, 0))
        o.append(tube('Rayon', loc, (x + d[0], y + d[1], z + d[2]), r*0.07, material, 8))
    return o

def bride(loc, r, axe, material):
    return cyl('Bride', r*1.6, 0.12, loc, material, 24, axe=axe)

# ---------------------------------------------------------------- caisses, bacs, fûts, bouteilles
def caisse_bois(s=(2.4, 2.0, 2.0), seed=0, loc=(0, 0, 0), rot=0.0):
    """caisse en planches : faces en lattes, chants renforcés, coins métalliques"""
    rnd = random.Random(seed); o = []; L, W, H = s; x0, y0, z0 = loc; c, sn = math.cos(rot), math.sin(rot)
    def P(dx, dy, dz): return (x0 + dx*c - dy*sn, y0 + dx*sn + dy*c, z0 + dz)
    tint = rnd.choice([(196, 160, 112), (176, 140, 96), (150, 120, 84)]); Mb = mat('bois', tint); Mr = mat('bois', tuple(int(v*0.82) for v in tint))
    o.append(cube('Caisse', (L - 0.1, W - 0.1, H - 0.1), P(0, 0, H/2), Mb, 0.02, rot=(0, 0, rot)))
    t = 0.07
    for sy in (-1, 1):                               # renforts en cadre sur les grandes faces
        for zz in (0.12, H - 0.12): o.append(cube('Latte', (L, 0.06, 0.24), P(0, sy*(W/2 - 0.0), zz), Mr, 0.02, rot=(0, 0, rot)))
        for sx in (-1, 1): o.append(cube('Latte', (0.24, 0.06, H - 0.48), P(sx*(L/2 - 0.12), sy*W/2, H/2), Mr, 0.02, rot=(0, 0, rot)))
        o.append(cube('Diagonale', (math.hypot(L - 0.48, H - 0.48), 0.05, 0.2), P(0, sy*(W/2 + 0.01), H/2), Mr, 0.02, rot=(0, -math.atan2(H - 0.48, L - 0.48)*sy, rot)))
    for zz in (0.12, H - 0.12):
        for sx in (-1, 1): o.append(cube('Latte', (0.06, W, 0.24), P(sx*L/2, 0, zz), Mr, 0.02, rot=(0, 0, rot)))
    return o

def bac_plastique(loc, rnd, rot=0.0, s=(1.6, 1.1, 0.8), col=None):
    x, y, z = loc; L, W, H = s; o = []
    col = col or rnd.choice([(60, 90, 150), (200, 160, 40), (60, 120, 70), (150, 40, 40), (90, 90, 96)])
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*L*(1 if v.co.z > 0 else 0.9), v.co.y*W*(1 if v.co.z > 0 else 0.9), v.co.z*H))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context='FACES')
    b = obj_from_bm(bm, 'Bac', mat('plastique', col), smooth=False); b.location = (x, y, z + H/2); b.rotation_euler = (0, 0, rot)
    b.modifiers.new('ep', 'SOLIDIFY').thickness = 0.04; bevel(b, 0.04, 2); o.append(b)
    o.append(cube('Levre', (L + 0.06, W + 0.06, 0.06), (x, y, z + H - 0.03), mat('plastique', col), 0.02, rot=(0, 0, rot)))
    if rnd.random() < 0.6:                            # contenu
        for k in range(rnd.randint(1, 3)):
            o.append(cube('Contenu', (rnd.uniform(0.3, L*0.7), rnd.uniform(0.3, W*0.7), rnd.uniform(0.2, H*0.9)), (x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.2, 0.2), z + 0.15 + rnd.uniform(0.0, H*0.3)),
                          mat('carton', rnd.choice([(200, 170, 120), (226, 226, 220)])), 0.02, rot=(0, 0, rot + rnd.uniform(-0.3, 0.3))))
    return o

def fut(loc, rnd, col=None, couche=False, cabosse=True):
    """fût métallique de 200 L : deux cerclages roulés, bondes, peinture écaillée (texture), bosses"""
    x, y, z = loc; R = 1.0; H = 3.1; o = []
    col = col or rnd.choice([(40, 70, 130), (150, 40, 30), (60, 90, 60), (200, 170, 40), (90, 94, 100)])
    prof = [(0.0, 0.0), (R - 0.06, 0.0), (R, 0.06), (R, 0.95), (R + 0.04, 1.0), (R, 1.05), (R, 2.05), (R + 0.04, 2.1), (R, 2.15), (R, H - 0.06), (R - 0.06, H), (R - 0.12, H - 0.04), (0.0, H - 0.04)]
    b = revolution('Fut', prof, mat('metal_peint', col), 40)
    if cabosse:
        for v in b.data.vertices:
            n = noise.noise(Vector((v.co.x*1.4 + loc[0], v.co.y*1.4, v.co.z*0.8 + loc[1])))
            if abs(v.co.z - 0.98) > 0.15 and abs(v.co.z - 2.12) > 0.15: v.co.x *= 1 + 0.025*n; v.co.y *= 1 + 0.025*n
    o.append(b)
    for (dx, dy, r) in ((0.55, 0.0, 0.14), (-0.55, 0.1, 0.09)): o.append(cyl('Bonde', r, 0.05, (dx, dy, H - 0.04), mat('metal_brut', (120, 120, 116)), 16))
    root = empty('FutR', (x, y, z + (R if couche else 0)), (math.pi/2 if couche else 0, 0, rnd.uniform(0, 6.28)))
    for p in o: p.parent = root
    bpy.context.view_layer.update(); return o + [root]

def bouteille_gaz(loc, rnd, col=None, chapeau=True):
    x, y, z = loc; R = 0.42; H = 5.0; o = []
    col = col or rnd.choice([(40, 110, 60), (40, 40, 42), (60, 90, 150), (200, 200, 196), (150, 40, 30)])
    prof = [(0.0, 0.0), (R - 0.08, 0.0), (R, 0.1), (R, H - 0.55), (R - 0.08, H - 0.3), (0.2, H - 0.14), (0.12, H - 0.06), (0.11, H)]
    o.append(revolution('Bouteille', prof, mat('metal_peint', col), 32, (x, y, z)))
    o.append(revolution('Ogive', [(R + 0.002, H - 0.95), (R + 0.002, H - 0.55), (R - 0.078, H - 0.3), (0.202, H - 0.14), (0.0, H - 0.14)], mat('metal_peint', rnd.choice([(220, 220, 210), (200, 170, 40), (60, 110, 60)])), 32, (x, y, z), ferme_bas=False))
    o.append(cyl('Robinet', 0.06, 0.3, (x, y, z + H), M_laiton(), 12)); o.append(cyl('Sortie', 0.04, 0.2, (x, y, z + H + 0.18), M_laiton(), 10, axe='X'))
    o += volant((x, y, z + H + 0.36), 0.13, mat('metal_peint', (40, 40, 40)), axe='Z')
    return o

def extincteur(loc=(0, 0, 0), rot=0.0, mural=True):
    """extincteur sur support mural (dos à y=0)"""
    x, y, z = loc; o = []; R = 0.3; H = 2.0; c, s = math.cos(rot), math.sin(rot)
    def P(dx, dy, dz): return (x + dx*c - dy*s, y + dx*s + dy*c, z + dz)
    zb = 2.2 if mural else 0.0
    cx, cy, cz = P(0, 0.45, zb)
    o.append(revolution('Corps', [(0.0, 0.0), (R - 0.04, 0.0), (R, 0.06), (R, H - 0.35), (R - 0.1, H - 0.12), (0.1, H - 0.04), (0.08, H)], mat('metal_peint', (190, 30, 24)), 32, (cx, cy, cz)))
    o.append(cube('Tete', (0.2, 0.2, 0.25), (cx, cy, cz + H + 0.1), mat('metal_peint', (40, 40, 42)), 0.03, rot=(0, 0, rot)))
    o.append(cube('Levier', (0.5, 0.08, 0.05), P(0.15, 0.45, zb + H + 0.27), mat('metal_peint', (30, 30, 30)), 0.02, rot=(0, -0.2, rot)))
    o.append(cyl('Manometre', 0.07, 0.04, P(0, 0.56, zb + H + 0.1), mat('plastique', (230, 230, 226)), 16, axe='Y'))
    o.append(tube_path('Flexible', [Vector(P(0.1, 0.45, zb + H + 0.08)), Vector(P(0.38, 0.5, zb + H - 0.2)), Vector(P(0.36, 0.55, zb + 0.6)), Vector(P(0.3, 0.6, zb + 0.35))], 0.04, mat('caoutchouc', (30, 30, 30))))
    o.append(cube('Etiquette', (0.38, 0.01, 0.6), P(0, 0.45 + R + 0.004, zb + 1.0), mat('plastique', (226, 220, 200)), 0, rot=(0, 0, rot)))
    if mural:
        o.append(cube('Support', (0.35, 0.12, 0.6), P(0, 0.06, zb + 1.5), mat('metal_peint', (40, 40, 40)), 0.02, rot=(0, 0, rot)))
        o.append(cube('Panneau', (0.9, 0.03, 0.9), P(0, 0.015, zb + H + 1.0), mat('plastique', (200, 30, 24)), 0.01, rot=(0, 0, rot)))
    return o

# ---------------------------------------------------------------- rayonnage de stockage
def etagere_stockage(w=6.0, d=2.0, h=7.0, seed=0, contenu='mixte'):
    rnd = random.Random(seed); root = empty(f'EtagereStockage_{seed}'); o = []
    zs = etagere_metal(o, w, d, h, 4, mat('metal_peint', rnd.choice([(52, 84, 120), (180, 130, 40), (70, 74, 78)])), mat('metal_peint', (120, 124, 128)))
    for z in zs:
        x = -w/2 + 0.2
        while x < w/2 - 0.6:
            k = rnd.random()
            if k < 0.35:
                L = rnd.uniform(1.0, 1.8); o += bac_plastique((x + L/2, d/2, z + 0.03), rnd, rnd.uniform(-0.05, 0.05), (L, min(1.5, d - 0.2), rnd.uniform(0.6, 1.0))); x += L + 0.1
            elif k < 0.7:
                L = rnd.uniform(0.8, 1.6); H = rnd.uniform(0.6, 1.2)
                c = cube('Carton', (L, rnd.uniform(1.0, d - 0.2), H), (x + L/2, d/2 + rnd.uniform(-0.1, 0.1), z + 0.03 + H/2), mat('carton', (190, 156, 110)), 0.03, rot=(0, 0, rnd.uniform(-0.08, 0.08)))
                o.append(c)
                if rnd.random() < 0.5: o.append(cube('Scotch', (L + 0.01, 0.25, 0.01), (x + L/2, d/2, z + 0.03 + H + 0.005), mat('plastique', (190, 170, 120)), 0, rot=(0, 0, c.rotation_euler.z)))
                if rnd.random() < 0.4 and H < 0.9:
                    o.append(cube('Carton', (L*0.8, 0.9, H*0.7), (x + L/2, d/2, z + 0.03 + H + H*0.35), mat('carton', (176, 140, 100)), 0.03, rot=(0, 0, rnd.uniform(-0.2, 0.2))))
                x += L + 0.08
            elif k < 0.82:
                o.append(anneau('Cable', 0.45, 0.12, (x + 0.6, d/2, z + 0.15), mat('caoutchouc', rnd.choice([(30, 30, 30), (200, 120, 30), (40, 60, 140)])))); x += 1.3
            else: x += rnd.uniform(0.4, 1.0)
    parent_all(o, root); return root

def palette_caisses(seed=0):
    rnd = random.Random(seed); root = empty(f'PaletteCaisses_{seed}'); o = []
    Mp = mat('bois', (170, 140, 100))
    for sx in (-1, 0, 1): o.append(cube('Semelle', (0.4, 4.0, 0.35), (sx*1.7, 0, 0.175), Mp, 0.02))
    for k in range(7): o.append(cube('Planche', (4.0, 0.42, 0.08), (0, -1.8 + k*0.6, 0.39), Mp, 0.01))
    z = 0.43
    o += caisse_bois((2.0, 1.9, 1.7), seed, (-0.95, -0.95, z), rnd.uniform(-0.05, 0.05)); o += caisse_bois((2.0, 1.9, 1.7), seed + 1, (0.95, -0.95, z), rnd.uniform(-0.05, 0.05))
    o += caisse_bois((2.0, 1.9, 1.7), seed + 2, (-0.95, 0.95, z), rnd.uniform(-0.05, 0.05))
    if rnd.random() < 0.7: o += caisse_bois((2.0, 1.9, 1.7), seed + 3, (-0.6, -0.4, z + 1.72), rnd.uniform(-0.2, 0.2))
    o.append(cube('Film', (4.02, 4.02, 1.2), (0, 0, z + 0.6), mat_verre('Film', (230, 236, 240), 0.35), 0.05)) if rnd.random() < 0.3 else None
    parent_all([p for p in o if p], root); return root

def groupe_futs(n=3, seed=0):
    rnd = random.Random(seed); root = empty(f'Futs_{seed}'); o = []
    pos = [(0, 0), (2.1, 0.2), (1.0, 1.9), (-1.3, 1.6)]
    for k in range(n):
        x, y = pos[k % len(pos)]
        o += fut((x + rnd.uniform(-0.1, 0.1), y + rnd.uniform(-0.1, 0.1), 0), rnd)
    if rnd.random() < 0.5: o += fut((0.5, -2.3, 0), rnd, couche=True)
    o.append(cube('Bac', (5.2, 4.8, 0.3), (0.5, 0.8, 0.15), mat('metal_peint', JAUNE), 0.04)) if rnd.random() < 0.5 else None
    parent_all([p for p in o if p], root); return root

def rack_bouteilles(n=4, seed=0):
    rnd = random.Random(seed); root = empty(f'RackBouteilles_{seed}'); o = []; w = n*1.0 + 0.4; Mr = mat('metal_peint', (60, 64, 70))
    o.append(cube('Socle', (w, 1.2, 0.12), (0, 0.6, 0.06), Mr, 0.02))
    for zz in (2.2, 4.0):
        o.append(cube('Barre', (w, 0.08, 0.12), (0, 1.15, zz), Mr, 0.02))
        o.append(tube_path('Chaine', [Vector((-w/2 + 0.1, 1.2, zz)), Vector((0, 1.34, zz - 0.05)), Vector((w/2 - 0.1, 1.2, zz))], 0.025, mat('metal_brut', (150, 150, 150))))
    for sx in (-1, 1): o.append(cube('Montant', (0.1, 0.1, 4.4), (sx*w/2, 1.15, 2.2), Mr, 0.02))
    col = rnd.choice([(40, 110, 60), (40, 40, 42), (60, 90, 150), (200, 200, 196)])
    for k in range(n): o += bouteille_gaz((-w/2 + 0.7 + k*1.0, 0.6, 0.12), rnd, col if rnd.random() < 0.7 else None)
    parent_all(o, root); return root

# ---------------------------------------------------------------- établi
def etabli(w=7.0, seed=0):
    rnd = random.Random(seed); root = empty(f'Etabli_{seed}'); o = []; d = 2.6; h = 3.2; Mc = mat('metal_peint', (60, 86, 120)); Mb = mat('bois', (190, 150, 100))
    for sx in (-1, 1):
        for y in (0.15, d - 0.15): o.append(cube('Pied', (0.2, 0.2, h - 0.25), (sx*(w/2 - 0.2), y, (h - 0.25)/2), Mc, 0.02))
        o.append(cube('Traverse', (0.14, d - 0.3, 0.14), (sx*(w/2 - 0.2), d/2, 0.5), Mc, 0.02))
    o.append(cube('Tablette', (w - 0.4, d - 0.3, 0.06), (0, d/2, 0.6), mat('metal_peint', (110, 114, 118)), 0.01))
    o.append(cube('Plateau', (w, d, 0.25), (0, d/2, h - 0.125), Mb, 0.03))
    meuble_bas(o, w/2 - 2.4, w/2 - 0.4, d - 0.25, h - 0.3, Mc, mat('metal_peint', (70, 96, 130)), M_inox(), faces=[(1, 'tiroirs3')], plinthe=0.6, rnd=rnd)
    # étau
    ex = -w/2 + 1.0; Mv = mat('metal_peint', (40, 70, 60))
    o.append(cube('EtauBase', (0.6, 0.7, 0.3), (ex, d - 0.3, h + 0.15), Mv, 0.04)); o.append(cube('EtauMors', (0.7, 0.25, 0.45), (ex, d - 0.05, h + 0.45), Mv, 0.03))
    o.append(cube('EtauMors', (0.7, 0.25, 0.45), (ex, d - 0.55, h + 0.45), Mv, 0.03)); o.append(tube('EtauVis', (ex, d + 0.1, h + 0.35), (ex, d + 0.7, h + 0.35), 0.05, M_chrome()))
    o.append(tube('EtauLevier', (ex - 0.4, d + 0.6, h + 0.35), (ex + 0.4, d + 0.6, h + 0.35), 0.03, M_chrome()))
    # panneau perforé + outils
    o.append(cube('PanneauPerfore', (w - 0.6, 0.06, 3.0), (0, 0.04, h + 2.0), mat('grille_vent', (200, 200, 196)), 0.0))
    for sx in (-1, 1): o.append(cube('MontantPanneau', (0.12, 0.12, 3.4), (sx*(w/2 - 0.3), 0.06, h + 1.7), Mc, 0.02))
    Mo = mat('metal_brut', (170, 170, 168)); Mm = mat('plastique', (180, 40, 30))
    x = -w/2 + 0.8
    while x < w/2 - 0.8:
        k = rnd.random(); zt = h + rnd.uniform(1.4, 2.8)
        if k < 0.3:                                             # clé plate
            o.append(cube('Cle', (0.08, 0.04, 0.9), (x, 0.12, zt), Mo, 0.02, rot=(0, rnd.uniform(-0.1, 0.1), 0)))
            o.append(cyl('CleTete', 0.1, 0.04, (x, 0.1, zt + 0.45), Mo, 12, axe='Y'))
        elif k < 0.55:                                          # tournevis
            o.append(cyl('Manche', 0.07, 0.4, (x, 0.12, zt), mat('plastique', rnd.choice([(200, 160, 40), (180, 40, 30), (40, 80, 160)])), 12))
            o.append(cyl('Tige', 0.02, 0.5, (x, 0.12, zt - 0.5), Mo, 8))
        elif k < 0.75:                                          # marteau
            o.append(cube('MancheMarteau', (0.07, 0.07, 1.0), (x, 0.12, zt - 0.2), mat('bois', (170, 130, 80)), 0.02))
            o.append(cube('TeteMarteau', (0.45, 0.12, 0.14), (x, 0.13, zt + 0.32), Mo, 0.02))
        else:                                                   # pince
            for s in (-1, 1): o.append(cube('Pince', (0.06, 0.04, 0.8), (x + s*0.06, 0.12, zt), Mm if s > 0 else Mo, 0.02, rot=(0, s*0.12, 0)))
        x += rnd.uniform(0.35, 0.6)
    for k in range(rnd.randint(2, 4)):                         # objets sur le plan
        o.append(cube('Piece', (rnd.uniform(0.3, 0.8), rnd.uniform(0.3, 0.6), rnd.uniform(0.15, 0.4)), (rnd.uniform(-w/2 + 2, w/2 - 1), rnd.uniform(0.8, 2.0), h + 0.15), mat('metal_brut', (130, 130, 128)), 0.04, rot=(0, 0, rnd.uniform(0, 3))))
    o.append(cube('CaisseOutils', (1.4, 0.6, 0.6), (w/2 - 1.2, 1.4, h + 0.3), mat('metal_peint', ROUGE), 0.05))
    o.append(tube_path('AnseCaisse', [Vector((w/2 - 1.7, 1.4, h + 0.6)), Vector((w/2 - 1.7, 1.4, h + 0.85)), Vector((w/2 - 0.7, 1.4, h + 0.85)), Vector((w/2 - 0.7, 1.4, h + 0.6))], 0.035, M_chrome()))
    o.append(cube('Lampe', (w - 1.0, 0.4, 0.12), (0, 0.5, h + 3.55), mat('metal_peint', (200, 200, 196)), 0.03))
    parent_all(o, root); return root

# ---------------------------------------------------------------- électricité, serveurs, pupitre
def armoire_elec(w=3.0, d=1.6, h=7.0, seed=0, ouverte=None, plafond=12.0):
    rnd = random.Random(seed); root = empty(f'ArmoireElec_{seed}'); o = []; ouverte = rnd.random() < 0.35 if ouverte is None else ouverte
    Mc = mat('metal_peint', (190, 192, 186)); Mi = mat('metal_peint', (160, 164, 160))
    o.append(cube('Socle', (w, d - 0.1, 0.4), (0, d/2, 0.2), mat('metal_peint', (40, 40, 42)), 0.02))
    if ouverte:
        o.append(cube('Fond', (w, 0.05, h - 0.4), (0, 0.025, 0.2 + h/2), Mc, 0.0))
        for sx in (-1, 1): o.append(cube('Flanc', (0.05, d, h - 0.4), (sx*(w/2 - 0.025), d/2, 0.2 + h/2), Mc, 0.01))
        o.append(cube('Toit', (w, d, 0.05), (0, d/2, h - 0.02), Mc, 0.0))
        for k in range(5):                                          # rangées de disjoncteurs sur rail
            zz = 1.2 + k*1.1
            o.append(cube('Rail', (w - 0.4, 0.1, 0.12), (0, 0.4, zz), M_inox(), 0.0))
            for j in range(int((w - 0.6)//0.24)):
                o.append(cube('Disjoncteur', (0.2, 0.5, 0.65), (-w/2 + 0.42 + j*0.24, 0.6, zz), mat('plastique', (226, 226, 220)), 0.02))
                o.append(cube('Manette', (0.08, 0.08, 0.14), (-w/2 + 0.42 + j*0.24, 0.88, zz + (0.06 if rnd.random() < 0.85 else -0.06)), mat('plastique', (40, 40, 40) if rnd.random() < 0.8 else ROUGE), 0.01))
            o.append(cube('Goulotte', (w - 0.4, 0.35, 0.3), (0, 0.3, zz + 0.55), mat('plastique', (110, 114, 118)), 0.01))
        ang = math.radians(rnd.uniform(70, 110))
        door = cube('Porte', (w - 0.05, 0.06, h - 0.5), (0, 0, 0), Mc, 0.02)
        door.location = (-w/2 + math.cos(ang)*w/2, d + math.sin(ang)*w/2, 0.2 + h/2); door.rotation_euler = (0, 0, ang); o.append(door)
        for k in range(3):
            o.append(tube_path('CableSortant', [Vector((rnd.uniform(-1, 1), 0.6, h - 0.05)), Vector((rnd.uniform(-1, 1), 0.7, h + 0.4)), Vector((rnd.uniform(-1, 1), 0.4, h + 1.6))], 0.06, mat('caoutchouc', (30, 30, 30))))
    else:
        o.append(cube('Corps', (w, d, h - 0.4), (0, d/2, 0.2 + h/2), Mc, 0.03))
        o.append(cube('Porte', (w - 0.1, 0.05, h - 0.6), (0, d + 0.02, 0.2 + h/2), Mi, 0.02))
        o.append(cube('Serrure', (0.12, 0.08, 0.5), (w/2 - 0.3, d + 0.07, 0.2 + h/2), mat('plastique', (30, 30, 30)), 0.02))
        o.append(cube('Danger', (0.7, 0.01, 0.6), (0, d + 0.05, h - 1.2), mat('plastique', JAUNE), 0.0, rot=(0, 0, 0)))
        o.append(cube('Aeration', (w - 0.8, 0.02, 0.6), (0, d + 0.05, 1.0), mat('grille_vent', (150, 150, 150)), 0.0))
    o.append(cube('Gaine', (w*0.6, 0.6, plafond - h), (0, 0.35, h + (plafond - h)/2), mat('metal_peint', (130, 134, 136)), 0.02))
    parent_all(o, root); return root

def rack_serveur(seed=0):
    rnd = random.Random(seed); root = empty(f'RackServeur_{seed}'); o = []; w, d, h = 2.2, 3.6, 7.2; Mn = mat('metal_peint', (30, 31, 34))
    for sx in (-1, 1):
        o.append(cube('Flanc', (0.06, d, h), (sx*(w/2 - 0.03), d/2, h/2), Mn, 0.02))
    o.append(cube('Toit', (w, d, 0.1), (0, d/2, h - 0.05), Mn, 0.02)); o.append(cube('Socle', (w, d, 0.3), (0, d/2, 0.15), Mn, 0.02))
    z = 0.5; Leds = [mat_plain('LedVerte', (40, 255, 90), 0.3, emit=6.0), mat_plain('LedAmbre', (255, 170, 30), 0.3, emit=6.0), mat_plain('LedBleue', (60, 140, 255), 0.3, emit=6.0)]
    while z < h - 0.6:
        u = rnd.choice([1, 1, 2, 2, 4]); hu = u*0.155
        if rnd.random() < 0.12: z += hu; continue
        o.append(cube('Serveur', (w - 0.16, d - 0.4, hu - 0.02), (0, d/2 - 0.1, z + hu/2), mat('metal_peint', rnd.choice([(70, 72, 76), (180, 184, 186), (110, 112, 116)])), 0.01))
        o.append(cube('Facade', (w - 0.3, 0.02, hu - 0.05), (0, d - 0.3, z + hu/2), mat('grille_vent', (170, 170, 174)), 0.0))
        for k in range(rnd.randint(1, 4)): o.append(cube('Led', (0.04, 0.02, 0.04), (w/2 - 0.3 - k*0.08, d - 0.28, z + hu - 0.07), rnd.choice(Leds), 0.0))
        z += hu
    o.append(cube('PorteVitree', (w - 0.1, 0.05, h - 0.5), (0, d + 0.02, h/2), mat_verre('VerreFume', (190, 200, 204), 0.08), 0.0))
    for sx in (-1, 1): o.append(cube('CadrePorte', (0.1, 0.07, h - 0.45), (sx*(w/2 - 0.08), d + 0.03, h/2), Mn, 0.01))
    for k in range(4): o.append(tube_path('Cable', [Vector((rnd.uniform(-0.6, 0.6), 0.3, h - 0.3)), Vector((rnd.uniform(-0.6, 0.6), 0.25, h + 0.5)), Vector((rnd.uniform(-0.6, 0.6), 0.6, h + 0.9))], 0.04, mat('caoutchouc', rnd.choice([(30, 30, 30), (40, 70, 160), (200, 160, 40)]))))
    parent_all(o, root); return root

def pupitre(w=6.0, seed=0, ecrans=2, allume=False):
    """pupitre de contrôle : caisson incliné, écrans, boutons, voyants, interrupteurs, chaise"""
    rnd = random.Random(seed); root = empty(f'Pupitre_{seed}'); o = []; d = 3.0; h = 2.7; Mc = mat('metal_peint', (96, 104, 110)); Mn = mat('plastique', (34, 34, 36))
    o.append(cube('Caisson', (w, d - 0.6, h), (0, (d - 0.6)/2, h/2), Mc, 0.04))
    o.append(cube('Socle', (w - 0.2, d - 0.9, 0.3), (0, (d - 0.6)/2 - 0.1, 0.15), mat('metal_peint', (40, 40, 42)), 0.02))
    pent = cube('Pente', (w, 1.6, 0.14), (0, d - 0.85, h + 0.3), Mc, 0.04, rot=(-0.35, 0, 0)); o.append(pent)
    o.append(cube('Rebord', (w, 0.5, 0.12), (0, d - 0.02, h + 0.04), mat('caoutchouc', (40, 40, 40)), 0.05))
    o.append(cube('Rehausse', (w, 0.8, 1.4), (0, 0.4, h + 0.7), Mc, 0.04))
    for k in range(ecrans):
        ex = -w/2 + w*(k + 0.5)/ecrans
        o.append(cube('Ecran', (min(2.2, w/ecrans - 0.3), 0.18, 1.3), (ex, 0.95, h + 1.35), Mn, 0.04, rot=(0.12, 0, 0)))
        o.append(cube('Dalle', (min(2.2, w/ecrans - 0.3) - 0.14, 0.01, 1.14), (ex, 1.05, h + 1.36), mat_plain('DalleOn' if allume else 'DalleOff', (60, 110, 120) if allume else (8, 9, 10), 0.08, emit=1.6 if allume else 0.0), 0, rot=(0.12, 0, 0)))
    Vy = [mat_plain('VoyantRouge', (200, 30, 20), 0.3, emit=3.0 if allume else 0.0), mat_plain('VoyantVert', (40, 200, 60), 0.3, emit=3.0 if allume else 0.0), mat_plain('VoyantJaune', (220, 180, 30), 0.3, emit=3.0 if allume else 0.0)]
    import math as _m
    for i in range(int(w//0.5) - 1):                             # boutons et voyants sur la pente
        for j in range(3):
            bx = -w/2 + 0.5 + i*0.5; by = d - 1.35 + j*0.42; bz = h + 0.3 + (by - (d - 0.85))*_m.tan(0.35)*(-1) + 0.09
            k = rnd.random()
            if k < 0.4: o.append(cyl('Bouton', 0.07, 0.06, (bx, by, bz), mat('plastique', rnd.choice([(30, 30, 30), (170, 30, 24), (40, 90, 160), (200, 200, 196)])), 12))
            elif k < 0.6: o.append(cyl('Voyant', 0.05, 0.05, (bx, by, bz), rnd.choice(Vy), 12))
            elif k < 0.75: o.append(cube('Interrupteur', (0.05, 0.05, 0.18), (bx, by, bz + 0.05), M_chrome(), 0.01, rot=(rnd.choice([-0.4, 0.4]), 0, 0)))
    o.append(cube('Clavier', (1.4, 0.5, 0.06), (rnd.uniform(-w/4, w/4), d - 0.6, h + 0.12), Mn, 0.02))
    parent_all(o, root); return root

# ---------------------------------------------------------------- machines
def pompe(seed=0):
    """pompe centrifuge : moteur à ailettes, accouplement, volute, brides, socle"""
    rnd = random.Random(seed); root = empty(f'Pompe_{seed}'); o = []; col = rnd.choice([BLEU_MACH, VERT_MACH, GRIS_MACH, (150, 50, 40)]); Mc = mat('metal_peint', col)
    o.append(cube('Socle', (6.2, 2.4, 0.4), (0, 0, 0.2), mat('metal_peint', (60, 62, 64)), 0.04))
    for k in range(4): o.append(cyl('Boulon', 0.08, 0.12, (-2.8 + k*1.85, 1.0, 0.4), M_chrome(), 8))
    zc = 1.6
    mot = revolution('Moteur', [(0.0, 0.0), (0.9, 0.0), (1.0, 0.1), (1.0, 2.6), (0.9, 2.7), (0.0, 2.7)], Mc, 36); mot.rotation_euler = (0, math.pi/2, 0); mot.location = (-3.0, 0, zc); o.append(mot)
    for k in range(14):
        a = k*2*math.pi/14
        o.append(cube('Ailette', (2.4, 0.06, 0.18), (-1.65, 1.08*math.cos(a), zc + 1.08*math.sin(a)), Mc, 0.0, rot=(a, 0, 0)))
    o.append(cube('Bornier', (0.8, 0.7, 0.5), (-1.7, 0, zc + 1.2), Mc, 0.05))
    for sy in (-1, 1): o.append(cube('Patte', (0.5, 0.3, 0.9), (-2.7 + 1.8*(sy > 0), sy*0.7, 0.85), Mc, 0.03))
    o.append(cyl('Accouplement', 0.45, 0.8, (-0.3, 0, zc), mat('metal_peint', JAUNE), 24, axe='X'))
    vol = revolution('Volute', [(0.0, 0.0), (1.2, 0.0), (1.35, 0.15), (1.35, 0.85), (1.2, 1.0), (0.0, 1.0)], Mc, 36); vol.rotation_euler = (0, math.pi/2, 0); vol.location = (0.6, 0, zc); o.append(vol)
    o.append(cyl('Aspiration', 0.5, 1.2, (1.6, 0, zc), Mc, 24, axe='X')); o.append(bride((2.8, 0, zc), 0.5, 'X', Mc))
    o.append(cyl('Refoulement', 0.42, 1.4, (1.1, 0, zc + 0.9), Mc, 24)); o.append(bride((1.1, 0, zc + 2.3), 0.42, 'Z', Mc))
    o.append(cube('Pied', (1.2, 1.6, zc - 0.6), (1.1, 0, 0.4 + (zc - 0.6)/2 - 0.2), Mc, 0.04))
    o.append(cyl('Manometre', 0.22, 0.1, (1.5, 0.45, zc + 1.6), mat('plastique', (230, 230, 226)), 24, axe='Y'))
    parent_all(o, root); return root

def cuve(diam=6.0, h=10.0, seed=0):
    """cuve verticale : fond bombé, pieds, trou d'homme, échelle, jauge, tuyaux"""
    rnd = random.Random(seed); root = empty(f'Cuve_{seed}'); o = []; R = diam/2; col = rnd.choice([(150, 156, 150), (180, 180, 176), (120, 140, 150)]); Mc = mat('metal_peint', col)
    z0 = 1.6; prof = [(0.0, z0 - 0.5), (R*0.6, z0 - 0.42), (R*0.92, z0 - 0.2), (R, z0)]
    prof += [(R, z0 + h*k/6) for k in range(1, 7)] + [(R*0.92, z0 + h + 0.2), (R*0.6, z0 + h + 0.45), (0.0, z0 + h + 0.55)]
    o.append(revolution('Cuve', prof, Mc, 48))
    for k in range(4):
        a = k*math.pi/2 + math.pi/4; o.append(cube('Pied', (0.35, 0.35, z0 + 0.2), (R*0.75*math.cos(a), R*0.75*math.sin(a), (z0 + 0.2)/2), mat('metal_peint', (60, 62, 64)), 0.03))
    for zz in (z0 + h*0.33, z0 + h*0.66): o.append(revolution('Cerclage', [(R + 0.01, zz), (R + 0.08, zz + 0.04), (R + 0.08, zz + 0.2), (R + 0.01, zz + 0.24)], mat('metal_brut', (130, 130, 128)), 48, ferme_haut=False, ferme_bas=False))
    o.append(cyl('TrouHomme', 0.8, 0.3, (0, R - 0.05, z0 + 1.6), Mc, 32, axe='Y'))
    for k in range(12):
        a = k*2*math.pi/12; o.append(cyl('Boulon', 0.05, 0.1, (0.68*math.cos(a), R + 0.25, z0 + 1.6 + 0.68*math.sin(a)), M_chrome(), 8, axe='Y'))
    ax = 0.8                                                  # échelle à crinoline
    for sx in (-1, 1): o.append(tube('Echelle', (ax + sx*0.35 + R*0.0, -(R + 0.4), 0.2), (ax + sx*0.35, -(R + 0.4), z0 + h + 1.0), 0.05, mat('metal_peint', JAUNE)))
    for k in range(int((z0 + h)//0.8)): o.append(tube('Barreau', (ax - 0.35, -(R + 0.4), 0.6 + k*0.8), (ax + 0.35, -(R + 0.4), 0.6 + k*0.8), 0.035, mat('metal_peint', JAUNE)))
    o.append(tube('Niveau', (R + 0.3, 0, z0 + 0.6), (R + 0.3, 0, z0 + h - 0.6), 0.07, mat_verre('VerreNiveau', (200, 220, 210), 0.05)))
    for zz in (z0 + 0.6, z0 + h - 0.6): o.append(tube('Piquage', (R - 0.1, 0, zz), (R + 0.3, 0, zz), 0.07, M_inox()))
    o.append(cyl('Tuyau', 0.35, 0.8, (-(R - 0.1), 0, z0 + 0.6), Mc, 20, axe='X')); o.append(tube_path('TuyauSortie', [Vector((-(R + 0.6), 0, z0 + 0.6)), Vector((-(R + 1.4), 0, z0 + 0.6)), Vector((-(R + 1.5), 0, 0.4))], 0.35, Mc))
    o.append(cyl('Event', 0.25, 0.8, (0, 0, z0 + h + 0.5), Mc, 16))
    parent_all(o, root); return root

def groupe_electrogene(L=14.0, seed=0):
    rnd = random.Random(seed); root = empty(f'Groupe_{seed}'); o = []; Mc = mat('metal_peint', rnd.choice([VERT_MACH, (200, 170, 40), GRIS_MACH])); Mn = mat('metal_peint', (50, 52, 54))
    o.append(cube('Chassis', (L, 4.6, 0.6), (0, 0, 0.3), Mn, 0.04))
    for k in range(6): o.append(cube('Silentbloc', (0.5, 0.5, 0.3), (-L/2 + 1 + k*(L - 2)/5, 1.8*(1 if k % 2 else -1), 0.75), mat('caoutchouc', (30, 30, 30)), 0.05))
    o.append(cube('Moteur', (L*0.5, 3.6, 3.6), (-L*0.18, 0, 2.7), Mc, 0.15))
    for k in range(6): o.append(cube('Culasse', (0.9, 1.2, 0.5), (-L*0.4 + k*1.1, 0, 4.7), Mc, 0.1))
    alt = revolution('Alternateur', [(0.0, 0.0), (1.9, 0.0), (2.0, 0.15), (2.0, L*0.32), (1.9, L*0.32 + 0.15), (0.0, L*0.32 + 0.15)], Mc, 40)
    alt.rotation_euler = (0, math.pi/2, 0); alt.location = (L*0.1, 0, 2.6); o.append(alt)
    o.append(cube('Radiateur', (0.8, 4.0, 4.2), (-L/2 + 0.4, 0, 2.7), Mn, 0.05))
    o.append(cube('Grille', (0.05, 3.6, 3.8), (-L/2 - 0.02, 0, 2.7), mat('grille_vent', (110, 110, 110)), 0.0))
    o.append(cube('Coffret', (1.6, 1.0, 2.6), (L/2 - 1.2, -2.0, 4.3), mat('metal_peint', (190, 190, 186)), 0.05))
    o.append(tube_path('Echappement', [Vector((-L*0.2, 1.5, 4.8)), Vector((-L*0.2, 1.5, 6.5)), Vector((-L*0.2, 0.0, 7.5)), Vector((-L*0.2, 0.0, 11.5))], 0.45, mat('metal_rouille', (150, 110, 80))))
    parent_all([p for p in o if p], root); return root

def transformateur(seed=0):
    rnd = random.Random(seed); root = empty(f'Transfo_{seed}'); o = []; Mc = mat('metal_peint', (120, 128, 120))
    o.append(cube('Cuve', (4.0, 2.6, 4.2), (0, 0, 2.4), Mc, 0.08)); o.append(cube('Socle', (4.4, 3.0, 0.3), (0, 0, 0.15), mat('metal_peint', (50, 52, 54)), 0.03))
    for sy in (-1, 1):
        for k in range(9): o.append(cube('Ailette', (0.06, 0.9, 3.4), (-1.8 + k*0.45, sy*1.75, 2.4), Mc, 0.0))
    for k in range(3):
        x = -1.2 + k*1.2
        o.append(revolution('Isolateur', [(0.18, 0), (0.18, 0.1)] + [(0.18 + (0.14 if j % 2 else 0.0), 0.1 + j*0.12) for j in range(1, 9)] + [(0.1, 1.2), (0.0, 1.25)], mat_plain('Porcelaine', (130, 80, 50), 0.25), 24, (x, 0, 4.5)))
    o.append(cube('Plaque', (0.9, 0.02, 0.6), (0, -1.31, 3.6), mat('metal_brut', (180, 180, 176)), 0.0))
    o.append(cube('Danger', (0.8, 0.02, 0.7), (1.2, -1.31, 3.6), mat('plastique', JAUNE), 0.0))
    parent_all(o, root); return root

def nourrice_vannes(w=8.0, seed=0):
    """collecteur mural : tuyaux horizontaux, vannes à volant, manomètres, étiquettes"""
    rnd = random.Random(seed); root = empty(f'Vannes_{seed}'); o = []; cols = [(150, 60, 40), (60, 100, 70), (70, 90, 120), (190, 170, 60)]
    for k, zz in enumerate((3.0, 5.0)):
        Mc = mat('metal_peint', cols[(k + seed) % 4]); r = 0.3
        o.append(tube('Collecteur', (-w/2, 0.7, zz), (w/2, 0.7, zz), r, Mc, 20))
        for j in range(int(w//2)):
            x = -w/2 + 1.0 + j*2.0
            o.append(tube('Depart', (x, 0.7, zz), (x, 0.7, zz + 0.8 if k == 1 else zz - 0.9), 0.18, Mc, 16))
            o.append(cube('CorpsVanne', (0.45, 0.45, 0.5), (x, 0.7, zz + (0.55 if k == 1 else -0.6)), mat('metal_peint', (60, 62, 64)), 0.08))
            o.append(tube('Tige', (x, 0.7, zz + (0.8 if k == 1 else -0.35)), (x, 1.4, zz + (0.8 if k == 1 else -0.35)), 0.04, M_chrome()))
            o += volant((x, 1.45, zz + (0.8 if k == 1 else -0.35)), 0.32, mat('metal_peint', ROUGE if rnd.random() < 0.6 else (40, 90, 160)), axe='Y')
            if rnd.random() < 0.5: o.append(cyl('Manometre', 0.2, 0.1, (x + 0.7, 1.0, zz), mat('plastique', (230, 230, 226)), 24, axe='Y'))
            o.append(cube('Etiquette', (0.4, 0.02, 0.2), (x, 1.02, zz + (0.25 if k == 1 else -0.25)), mat('plastique', (226, 220, 196)), 0.0))
        for x in (-w/2 + 0.4, w/2 - 0.4): o.append(cube('Collier', (0.12, 0.8, 0.8), (x, 0.35, zz), mat('metal_brut', (130, 130, 130)), 0.02))
    parent_all(o, root); return root
