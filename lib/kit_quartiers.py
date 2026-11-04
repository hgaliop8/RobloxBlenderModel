"""Objets de la salle témoin (Quartiers A) : lit superposé, casiers, table, chaise, petits objets, murs, plafond."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from kit_meshes import *

GRIS_BLEU = (92, 102, 116); GRIS_F = (64, 68, 74); BLEU_CASIER = (84, 104, 128)

def rounded_rect_slab(name, Lx, Ly, th, r, material, z=0.0, seg=6):
    bm = bmesh.new(); pts = []
    for cx, cy, a0 in ((Lx/2 - r, Ly/2 - r, 0), (-Lx/2 + r, Ly/2 - r, 90), (-Lx/2 + r, -Ly/2 + r, 180), (Lx/2 - r, -Ly/2 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90*k/seg); pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    vb = [bm.verts.new((x, y, z)) for x, y in pts]; vt = [bm.verts.new((x, y, z + th)) for x, y in pts]
    bm.faces.new(vb[::-1]); bm.faces.new(vt)
    n = len(pts)
    for i in range(n): bm.faces.new((vb[i], vb[(i + 1) % n], vt[(i + 1) % n], vt[i]))
    ob = obj_from_bm(bm, name, material); bevel(ob, 0.03, 2); return ob

# ================================================================ lit superposé
def lit_superpose(seed=0, couleurs=((70, 86, 112), (112, 72, 60), (84, 98, 80), (96, 94, 102))):
    rnd = random.Random(seed); root = empty(f'LitSuperpose_{seed}')
    L, W, Hp = 7.0, 3.2, 6.6
    M_cadre = mat('metal_peint', GRIS_BLEU); M_lame = mat('metal_brut', (150, 150, 150)); M_mat = mat('matelas', (232, 230, 222))
    objs = []
    for x in (-L/2 + 0.15, L/2 - 0.15):
        for y in (-W/2 + 0.15, W/2 - 0.15):
            objs.append(cube('Montant', (0.26, 0.26, Hp), (x, y, Hp/2), M_cadre, 0.05))
            objs.append(cube('Patin', (0.36, 0.36, 0.12), (x, y, 0.06), mat('caoutchouc', (60, 60, 60)), 0.03))
    for z in (1.15, 4.65):
        for y in (-W/2 + 0.15, W/2 - 0.15): objs.append(cube('Longeron', (L, 0.14, 0.34), (0, y, z), M_cadre, 0.04))
        for x in (-L/2 + 0.15, L/2 - 0.15): objs.append(cube('Traverse', (0.14, W, 0.34), (x, 0, z), M_cadre, 0.04))
        for i in range(9): objs.append(cube('Lame', (0.22, W - 0.3, 0.06), (-L/2 + 0.6 + i*(L - 1.2)/8, 0, z + 0.14), M_lame, 0.02))
    for x in (-L/2 + 0.15, L/2 - 0.15):                       # panneaux de tête et de pied
        for z0 in (1.6, 5.1):
            objs.append(cube('Panneau', (0.08, W - 0.3, 1.0), (x, 0, z0 + 0.3), M_cadre, 0.03))
    # garde-corps du haut et échelle
    objs.append(tube_path('GardeCorps', [Vector((-L/2 + 0.15, W/2 - 0.15, 6.4)), Vector((-L/2 + 1.2, W/2 - 0.15, 6.45)), Vector((L/2 - 2.0, W/2 - 0.15, 6.45)), Vector((L/2 - 1.6, W/2 - 0.15, 5.0))], 0.08, M_cadre))
    objs.append(tube('Echelle', (L/2 - 0.6, W/2 + 0.32, 0.1), (L/2 - 0.6, W/2 + 0.32, 6.3), 0.07, M_cadre))
    objs.append(tube('Echelle', (L/2 - 1.6, W/2 + 0.32, 0.1), (L/2 - 1.6, W/2 + 0.32, 6.3), 0.07, M_cadre))
    for z in range(7): objs.append(tube('Echelon', (L/2 - 0.6, W/2 + 0.32, 0.8 + z*0.8), (L/2 - 1.6, W/2 + 0.32, 0.8 + z*0.8), 0.05, M_lame))
    # matelas, oreillers, couvertures (tissu simulé)
    for k, z in enumerate((1.4, 4.9)):
        mt = cube('Matelas', (L - 0.4, W - 0.3, 0.55), (0, 0, z + 0.27), M_mat, 0.16, 4)
        sb = mt.modifiers.new('sub', 'SUBSURF'); sb.levels = 1
        ore = oreiller('Oreiller', 2.2, 1.35, 0.55, seed=seed*10 + k, material=mat('tissu', (238, 238, 234)))
        ore.location = (-L/2 + 1.25, rnd.uniform(-0.15, 0.15), z + 0.55 + 0.22); ore.rotation_euler = (0, rnd.uniform(-0.12, 0.05), math.pi/2 + rnd.uniform(-0.15, 0.15))
        bpy.context.view_layer.update()
        col = rnd.choice(couleurs)
        cov = tissu_simule('Couverture', rnd.uniform(4.8, 5.8), W + 2.0, z + 1.5, [mt, ore], mat('tissu', col), seed=seed*10 + k, frames=70, drop_noise=0.3, res=0.11,
                           shrink=0.06, crumple=0.5,
                           centre=(0.8 + rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.2)), rot=rnd.uniform(-0.08, 0.08))
        objs += [mt, ore, cov]
    parent_all(objs, root)
    return root

def tissu_libre(name, L, W, z0, colliders, material, seed=0):
    return tissu_simule(name, L, W, z0, colliders, material, seed=seed, frames=40, drop_noise=0.3)

# ================================================================ casiers
def casiers(n=4, seed=0, ouvert=1):
    rnd = random.Random(seed); root = empty(f'Casiers_{seed}')
    w, d, h = 1.7, 1.7, 6.6; M = mat('metal_peint', BLEU_CASIER); Mi = mat('metal_peint', (70, 74, 80)); objs = []
    objs.append(cube('Socle', (n*w, d - 0.1, 0.5), (0, d/2, 0.25), mat('metal_peint', (40, 42, 46)), 0.03))
    objs.append(cube('Corps', (n*w, d, h - 0.5), (0, d/2, 0.5 + (h - 0.5)/2), Mi, 0.05))
    for i in range(n):
        x = (i - (n - 1)/2)*w
        if i == ouvert:
            ang = math.radians(rnd.uniform(60, 100))
            door = cube('Porte', (w - 0.12, 0.06, h - 0.8), (0, 0, 0), M, 0.03)
            door.location = (x - w/2 + 0.06 + math.cos(ang)*(w - 0.12)/2, d + math.sin(ang)*(w - 0.12)/2, 0.5 + (h - 0.8)/2 + 0.15); door.rotation_euler = (0, 0, ang)
            objs.append(door)
            objs.append(cube('Interieur', (w - 0.2, 0.05, h - 0.9), (x, 0.15, 0.5 + (h - 0.9)/2 + 0.1), mat('metal_peint', (40, 44, 48)), 0.0))
            sh = cube('Etagere', (w - 0.22, d - 0.3, 0.05), (x, d/2, 5.2), Mi, 0.01); objs.append(sh)
            bpy.context.view_layer.update()
            tc = mat('tissu', rnd.choice([(200, 70, 60), (60, 100, 160), (220, 220, 210)]))
            for k in range(2):                                   # serviettes pliées empilées
                objs.append(cube('Serviette', (1.15 - k*0.06, 0.95 - k*0.04, 0.2), (x + rnd.uniform(-0.05, 0.05), d/2, 5.35 + k*0.2), tc, 0.08, 3, rot=(0, 0, rnd.uniform(-0.08, 0.08))))
            objs.append(cube('Sac', (1.1, 0.9, 1.4), (x, d/2, 1.3), mat('tissu', (60, 70, 50)), 0.25, 3))
        else:
            objs.append(cube('Porte', (w - 0.12, 0.08, h - 0.8), (x, d + 0.03, 0.5 + (h - 0.8)/2 + 0.15), M, 0.03))
            for k in range(5): objs.append(cube('Aeration', (w - 0.6, 0.06, 0.08), (x, d + 0.06, h - 0.9 - k*0.22), mat('metal_peint', (30, 32, 36)), 0.0))
            objs.append(tube('Poignee', (x + w/2 - 0.35, d + 0.16, 2.9), (x + w/2 - 0.35, d + 0.16, 3.6), 0.05, mat('metal_brut', (180, 180, 180))))
            objs.append(cube('Etiquette', (0.6, 0.02, 0.3), (x, d + 0.08, h - 2.2), mat('plastique', (230, 226, 210)), 0.0))
    objs.append(cube('Chapeau', (n*w + 0.1, d + 0.1, 0.12), (0, d/2, h + 0.06), Mi, 0.03))
    parent_all(objs, root); return root

# ================================================================ table, chaise
def table(Lx=5.0, Ly=2.6, h=2.6, seed=0):
    rnd = random.Random(seed); root = empty(f'Table_{seed}'); objs = []
    objs.append(rounded_rect_slab('Plateau', Lx, Ly, 0.14, 0.25, mat('plastique', (214, 210, 198)), z=h - 0.14))
    objs.append(rounded_rect_slab('Chant', Lx + 0.02, Ly + 0.02, 0.06, 0.26, mat('plastique', (70, 70, 72)), z=h - 0.12))
    for sx in (-1, 1):
        objs.append(tube_path('Pied', [Vector((sx*(Lx/2 - 0.5), -Ly/2 + 0.35, 0.05)), Vector((sx*(Lx/2 - 0.5), 0, h - 0.18)), Vector((sx*(Lx/2 - 0.5), Ly/2 - 0.35, 0.05))], 0.09, mat('metal_brut', (160, 162, 164))))
        objs.append(cube('Patin', (0.2, Ly - 0.6, 0.08), (sx*(Lx/2 - 0.5), 0, 0.04), mat('caoutchouc', (40, 40, 40)), 0.02))
    objs.append(tube('Entretoise', (-Lx/2 + 0.5, 0, 1.0), (Lx/2 - 0.5, 0, 1.0), 0.06, mat('metal_brut', (160, 162, 164))))
    parent_all(objs, root); return root

def chaise(seed=0, col=(66, 88, 120)):
    rnd = random.Random(seed); root = empty(f'Chaise_{seed}'); objs = []
    # coque moulée : surface paramétrique (assise qui se relève en dossier)
    bm = bmesh.new(); nu, nv = 16, 12; V = {}
    for i in range(nu + 1):
        t = i/nu
        for j in range(nv + 1):
            s = j/nv; x = (s - 0.5)*1.55*(1 - 0.08*t)
            if t < 0.55: y = -0.75 + t/0.55*1.4; z = 1.75 + 0.06*math.sin(math.pi*s)*(1 - t) - 0.05*(t/0.55)**2
            else:
                a = (t - 0.55)/0.45*math.radians(100); y = 0.65 + math.sin(a)*0.35; z = 1.70 + (1 - math.cos(a))*0.35 + max(0, a - 1.2)*1.2
                if t > 0.7: y = 0.65 + 0.35 + (t - 0.7)*0.4; z = 1.70 + 0.35 + (t - 0.7)/0.3*1.25
            z += 0.08*(2*s - 1)**2
            V[(i, j)] = bm.verts.new((x, y, z))
    for i in range(nu):
        for j in range(nv): bm.faces.new((V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]))
    sh = obj_from_bm(bm, 'Coque', mat('plastique', col))
    so = sh.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.08; sb = sh.modifiers.new('sub', 'SUBSURF'); sb.levels = 2
    objs.append(sh)
    Mt = mat('metal_brut', (170, 172, 174))
    for sx in (-1, 1):
        objs.append(tube_path('Luge', [Vector((sx*0.62, -0.7, 0.06)), Vector((sx*0.62, 0.65, 0.06)), Vector((sx*0.62, 0.75, 0.9)), Vector((sx*0.6, 0.55, 1.68))], 0.06, Mt))
        objs.append(tube('Montant', (sx*0.62, -0.62, 0.06), (sx*0.6, -0.55, 1.68), 0.06, Mt))
    parent_all(objs, root); return root

# ================================================================ petits objets
def tasse(col=(200, 200, 196)):
    root = empty('Tasse'); M = mat('plastique', col)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.17, radius2=0.2, depth=0.42)
    c = obj_from_bm(bm, 'Corps', M); c.location = (0, 0, 0.21); so = c.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.02
    an = tube_path('Anse', [Vector((0.19, 0, 0.32)), Vector((0.32, 0, 0.26)), Vector((0.19, 0, 0.12))], 0.025, M)
    parent_all([c, an], root); return root

def livre(seed=0):
    rnd = random.Random(seed); root = empty('Livre'); col = rnd.choice([(120, 40, 40), (40, 60, 100), (60, 90, 60), (150, 120, 70)])
    c = cube('Couverture', (0.75, 1.05, 0.16), (0, 0, 0.08), mat('simili_cuir', col), 0.02); p = cube('Pages', (0.7, 1.0, 0.13), (0.03, 0, 0.08), mat('plastique', (236, 230, 210)), 0.005)
    parent_all([c, p], root); return root

def poubelle():
    root = empty('Poubelle'); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.5, radius2=0.6, depth=1.8)
    o = obj_from_bm(bm, 'Corps', mat('metal_peint', (90, 96, 100))); o.location = (0, 0, 0.9); bevel(o, 0.03, 2)
    so = o.modifiers.new('ep', 'SOLIDIFY'); so.thickness = 0.03
    parent_all([o], root); return root

# ================================================================ architecture de la salle témoin
def piece(X0, Y0, X1, Y1, h=12.0, porte=None, sol=('vinyle', (96, 102, 106)), mur=('peinture_mur', (206, 212, 218)), soub=('metal_peint', (88, 102, 120))):
    """sol, murs à panneaux (soubassement, plinthe, joints, corniche), pilastres, plafond à dalles, plafonniers"""
    objs = []; Mm = mat(*mur); Ms = mat(*soub); Mp = mat('metal_peint', (52, 56, 60)); Mpl = mat('metal_peint', (120, 126, 132))
    W, D = X1 - X0, Y1 - Y0
    objs.append(cube('Sol', (W, D, 0.5), ((X0 + X1)/2, (Y0 + Y1)/2, -0.25), mat(*sol), 0))
    objs.append(cube('Plafond', (W, D, 0.4), ((X0 + X1)/2, (Y0 + Y1)/2, h + 0.2), mat('plafond', (230, 230, 226)), 0))
    walls = [('N', (X0, Y1), (X1, Y1), (0, -1)), ('S', (X1, Y0), (X0, Y0), (0, 1)), ('W', (X0, Y0), (X0, Y1), (1, 0)), ('E', (X1, Y1), (X1, Y0), (-1, 0))]
    for name, a, b, n in walls:
        a, b, n = Vector((*a, 0)), Vector((*b, 0)), Vector((*n, 0)); d = (b - a); Lw = d.length; t = d.normalized()
        holes = []
        if porte and porte[0] == name: holes.append((porte[1] - porte[2]/2, porte[1] + porte[2]/2))
        def seg_iter():
            cur = 0.0
            for h0, h1 in sorted(holes):
                if h0 > cur: yield cur, h0
                cur = h1
            if cur < Lw: yield cur, Lw
        rot = math.atan2(t.y, t.x)
        for u0, u1 in seg_iter():
            m = a + t*((u0 + u1)/2); ln = u1 - u0
            objs.append(cube('Mur', (ln, 0.6, h), (m.x - n.x*0.3, m.y - n.y*0.3, h/2), Mm, 0, rot=(0, 0, rot)))
            objs.append(cube('Soubassement', (ln, 0.14, 3.2), (m.x + n.x*0.07, m.y + n.y*0.07, 1.6), Ms, 0.04, rot=(0, 0, rot)))
            objs.append(cube('Cimaise', (ln, 0.24, 0.2), (m.x + n.x*0.12, m.y + n.y*0.12, 3.25), Mp, 0.05, rot=(0, 0, rot)))
            objs.append(cube('Plinthe', (ln, 0.2, 0.45), (m.x + n.x*0.1, m.y + n.y*0.1, 0.22), mat('caoutchouc', (40, 40, 42)), 0.03, rot=(0, 0, rot)))
            objs.append(cube('Corniche', (ln, 0.35, 0.45), (m.x + n.x*0.17, m.y + n.y*0.17, h - 0.22), Mpl, 0.06, rot=(0, 0, rot)))
            k = 4.0
            while k < ln - 0.5:          # joints de panneaux
                p = a + t*(u0 + k)
                objs.append(cube('Joint', (0.07, 0.05, h - 3.9), (p.x + n.x*0.01, p.y + n.y*0.01, 3.35 + (h - 3.9)/2), mat('metal_peint', (90, 94, 100)), 0, rot=(0, 0, rot)))
                k += 4.0
        k = 8.0
        while k < Lw - 2:                # pilastres
            if not any(h0 - 1.5 < k < h1 + 1.5 for h0, h1 in holes):
                p = a + t*k
                objs.append(cube('Pilastre', (1.1, 0.7, h), (p.x + n.x*0.35, p.y + n.y*0.35, h/2), Mpl, 0.08, rot=(0, 0, rot)))
            k += 16.0
        if holes:                        # encadrement de porte
            c = a + t*porte[1]; w = porte[2]
            for sx in (-1, 1):
                q = c + t*(sx*(w/2 + 0.3))
                objs.append(cube('Chambranle', (0.6, 1.4, 8.6), (q.x, q.y, 4.3), Mp, 0.1, rot=(0, 0, rot)))
            objs.append(cube('Linteau', (w + 1.2, 1.4, 0.6), (c.x, c.y, 8.9), Mp, 0.1, rot=(0, 0, rot)))
            objs.append(cube('Imposte', (w, 0.6, h - 9.2), (c.x - n.x*0.3, c.y - n.y*0.3, 9.2 + (h - 9.2)/2), Mm, 0, rot=(0, 0, rot)))
    # plafonniers encastrés
    nx, ny = max(1, round(W/14)), max(1, round(D/14))
    for i in range(nx):
        for j in range(ny):
            x = X0 + (i + 0.5)*W/nx; y = Y0 + (j + 0.5)*D/ny
            objs.append(cube('Plafonnier', (4.4, 1.5, 0.3), (x, y, h - 0.12), mat('metal_peint', (200, 202, 204)), 0.06))
            objs.append(cube('Diffuseur', (4.0, 1.1, 0.06), (x, y, h - 0.28), mat_plain('Diffuseur', (240, 242, 250), rough=0.3, emit=0.0), 0.02))
    return objs
