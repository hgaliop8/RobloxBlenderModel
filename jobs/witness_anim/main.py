"""THE WITNESS — aperçu animé du mouvement. Mêmes formules que les scripts Roblox WitnessCorps et WitnessGestes, portées en Python.
PLAN = couloir (vu par un joueur : plafond, chute, course, bras levés), chute (de côté, chute du plafond),
etrangle (gros plan : saisie et étranglement d'un mannequin de joueur).
IMAGES = a-b, FPS (images par seconde du plan), ECH, RES, EXPO."""
import bpy, sys, os, time, math
sys.path.insert(0, os.path.join(os.getcwd(), 'lib'))
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
T0 = time.time(); logf = open(os.path.join(out, 'etapes.txt'), 'w')
def log(m): logf.write(f'{time.time() - T0:7.1f}s  {m}\n'); logf.flush(); print('>>', m, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
from mathutils import Vector, Matrix, Euler, Quaternion
import witness_jeu as W
import kit_meshes as K

PLAN = os.environ.get('PLAN', 'couloir')
parts, f = W.construire(log)
arm, defs = W.squelette(f)
for key in ('corps', 'ventouses', 'photo_v', 'photo_r'): W.lier(parts[key], arm, defs)
for key in ('coeurs', 'glande', 'badge'): W.lier(parts[key], arm, defs, rigide='Manteau1')
for key in ('oeil', 'pupille'):
    o = parts[key]
    for nm in [d[0] for d in defs]: o.vertex_groups.new(name=nm)
    for v in o.data.vertices: o.vertex_groups['OeilG' if v.co.y > 0 else 'OeilD'].add([v.index], 1.0, 'REPLACE')
    m = o.modifiers.new('squelette', 'ARMATURE'); m.object = arm; o.parent = arm
M = {'corps': K.mat_verre('VerreWitness', (215, 236, 240), 0.04), 'ventouses': K.mat_plain('Ventouse', (232, 228, 218), 0.6),
     'oeil': K.mat_plain('Iris', (212, 162, 60), 0.3, 0.6), 'pupille': K.mat_plain('Pupille', (108, 255, 140), 0.3, emit=6.0),
     'photo_v': K.mat_plain('PhotoV', (86, 224, 208), 0.3, emit=5.0), 'photo_r': K.mat_plain('PhotoR', (255, 80, 64), 0.3, emit=5.0),
     'coeurs': K.mat_plain('Coeur', (184, 48, 48), 0.4), 'glande': K.mat_plain('Glande', (200, 204, 212), 0.3, 0.8), 'badge': K.mat_plain('Badge', (232, 232, 224), 0.5)}
for k, m in M.items(): parts[k].data.materials.clear(); parts[k].data.materials.append(m)
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
log('modèle prêt')

# ================================================================ formules partagées avec Roblox (WitnessConfig / WitnessGestes)
G_JEU = 196.2; DECROCHAGE = 0.3; ATTERR = 0.45
SIGNE = {'encre': 0.5, 'plaquage': 0.5, 'fouet': 0.5, 'balayage': 0.6, 'morsure': 0.35, 'saisie': 0.7, 'enlevement': 1.0, 'chute': 1.5, 'encre': 0.5}
P_ARR = Vector((-2.2, 0, 0)); P_CAB = Vector((-1.8, 0, 0)); UPV = Vector((0, 0, 1))
def lisse(a): a = max(0.0, min(1.0, a)); return a*a*(3 - 2*a)
# repère du modèle : Roblox (avant X, haut Y, côté Z) = Blender (avant X, haut Z, côté -Y) ; Roblox Rz(+a) = Blender Ry(-a)
def autour(p, a): return Matrix.Translation(p) @ Matrix.Rotation(-a, 4, 'Y') @ Matrix.Translation(-p)
def interp(M0, M1, s):
    l0, q0, _ = M0.decompose(); l1, q1, _ = M1.decompose()
    return Matrix.Translation(l0.lerp(l1, s)) @ q0.slerp(q1, s).to_matrix().to_4x4()
RETOURNE = Matrix.Rotation(math.pi, 4, 'X')
def chute(e, d, tf):
    aMax = 1.2*min(1, d/0.3)
    if e < d:
        h = lisse(e/max(d, 1e-3)); return RETOURNE @ autour(P_ARR, aMax*h), 0.0, 'decroche', h, 0.0
    if e < d + tf:
        a = e - d; u = a/tf; s = lisse(min(1, u*1.15))
        return interp(RETOURNE @ autour(P_ARR, aMax), Matrix.Identity(4), s), 0.5*G_JEU*a*a, 'chute', u, 0.0
    tau = e - d - tf
    y = -0.45*math.sin(math.pi*min(tau/0.2, 1))*math.exp(-4*tau); b = -0.12*math.sin(math.pi*min(tau/0.25, 1))
    return Matrix.Translation((0, 0, y)) @ Matrix.Rotation(-b, 4, 'Y'), None, 'atterrit', min(1, tau/ATTERR), tau
def cabrer(tt):
    a = lisse(tt/0.5); return Matrix.Translation((0, 0, 1.0*a)) @ autour(P_CAB, 0.55*a)
def bezier(a, b, c, d, n, pts):
    for i in range(1, n + 1):
        u = i/n; v = 1 - u; pts.append(a*(v*v*v) + b*(3*v*v*u) + c*(3*v*u*u) + d*(u*u*u))
def chemin_enroule(B, N, U, fv, r, h0, sens, tours):
    l = U.cross(fv).normalized(); pas = 0.3
    def P(th): return N + U*(h0 + pas*abs(th)/(2*math.pi)) + (fv*math.cos(th) + l*math.sin(th))*r
    th0 = sens*0.75; E = P(th0); tg = (P(th0 + sens*0.05) - E).normalized()
    dehors = Vector((B.x - N.x, B.y - N.y, 0)); dehors = dehors.normalized() if dehors.length > 1e-3 else fv
    pts = [B.copy()]; bezier(B, B + (E - B)*0.3 + dehors*0.5 + U*0.4, E - tg*1.1, E, 10, pts)
    n = math.ceil(tours*24)
    for i in range(1, n + 1): pts.append(P(th0 + sens*(i/24)*2*math.pi))
    return pts
def chemin_sol(B, dirv, F, haut):
    pts = [B.copy()]; bezier(B, B + dirv*1.4 + haut*0.6, F + haut*1.4, F, 10, pts); pts += [F + dirv*2, F + dirv*5]; return pts
def articulations(base, pts, L):
    J = []; cur = base; i = 0
    for Lj in L:
        tr = None
        while i < len(pts) - 1:
            a, b = pts[i], pts[i + 1]; d = b - a; m = a - cur
            A = d.dot(d); Bq = 2*m.dot(d); Cq = m.dot(m) - Lj*Lj; disc = Bq*Bq - 4*A*Cq
            if A > 1e-9 and disc >= 0:
                u = (-Bq + math.sqrt(disc))/(2*A)
                if 0 <= u <= 1: tr = a + d*u; break
            i += 1
        if tr is None:
            dv = pts[-1] - pts[-2]; tr = cur + (dv.normalized() if dv.length > 1e-6 else Vector((1, 0, 0)))*Lj
        J.append(tr); cur = tr
    return J
CHAINES = {k: [arm.pose.bones[f'Bras{k}_{j}'] for j in range(1, 9)] for k in range(8)}
LONG = {k: [pb.bone.length for pb in CHAINES[k]] for k in range(8)}
REST_REL = {pb.name: pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local for pb in arm.pose.bones if pb.parent}
NPROX = 5                                                    # seuls les 5 premiers os s'étirent (la pointe s'enroule serré)
ETIRE = {}                                                   # bras qui s'allongent : k -> facteur (os 2 à 8 écartés de leur parent)
def etire_os(nm):
    if not nm.startswith('Bras') or int(nm.split('_')[1]) > NPROX + 1 or nm.endswith('_1'): return 1.0
    return ETIRE.get(int(nm[4]), 1.0)
ECRASE = {'serre': 0.0, 'etire': 0.0}                     # passage d'une grille : bases des bras ramenées, manteau allongé
def facteur_os(nm):
    """multiplicateurs (x, y, z) de la position de la tête de l'os dans le repère de son parent"""
    s_ = etire_os(nm)
    if nm.startswith('Bras') and nm.endswith('_1') and ECRASE['serre'] > 0:
        f = 1 - 0.45*ECRASE['serre']; return (f, 1.0, f)                    # repère de la Racine : Y = haut du modèle
    if nm in ('Manteau1', 'Manteau2') and ECRASE['etire'] > 0:
        f = 1 + 0.4*ECRASE['etire']; return (f, f, f)
    return (s_, s_, s_)
def rest_rel(pb):
    M = REST_REL[pb.name]; f = facteur_os(pb.name)
    if f == (1.0, 1.0, 1.0): return M
    M = M.copy(); tr = M.translation; M.translation = Vector((tr.x*f[0], tr.y*f[1], tr.z*f[2])); return M
def longueurs(k):
    s_ = ETIRE.get(k, 1.0); return [L*s_ for L in LONG[k][:NPROX]] + LONG[k][NPROX:]
def orienter(chaine, Mparent, J, poids, Q):
    Mc = Mparent
    for j, pb in enumerate(chaine):
        repos = Mc @ rest_rel(pb); v = J[j] - repos.translation; q = Q[pb.name]
        if v.length > 1e-4:
            dl = (repos.to_3x3().inverted() @ v).normalized(); ax = Vector((0, 1, 0)); c = ax.cross(dl)
            ang = math.acos(max(-1.0, min(1.0, ax.dot(dl))))
            q = q.slerp(Quaternion(c.normalized(), ang) if c.length > 1e-6 else Quaternion(), poids[j])
        Q[pb.name] = q; Mc = repos @ q.to_matrix().to_4x4()

phases = {k: k*0.79 + (k % 3)*0.4 for k in range(8)}
PLAQUE_ACTIF = [False]
def animer(t, vit, coup, e, saisie, ch):
    """port de WitnessCorps.animer : quaternion de chaque os"""
    signe = SIGNE.get(coup, 0.5); Q = {}
    bec_m, ecart_m = 0.0, 0.0
    for k in range(8):
        ph = phases[k]; avant = k in (0, 7, 1, 6)
        for j in range(1, 9):
            yaw = 0.05*math.sin(t*1.1 - j*0.5 + ph); pitch = 0.025*math.sin(t*0.8 + j*0.6 + ph)
            if j >= 7: pitch += 0.22 + 0.05*math.sin(t*1.4 + ph)
            if coup in ('saisie', 'enlevement') or saisie:
                if avant:
                    a = lisse(e/signe); pitch += a*(0.5 if j == 1 else (0.06 if j <= 4 else 0.12)); yaw += a*(0.2 if k <= 1 else -0.2)
            elif coup == 'fouet':
                pitch -= 0.05*lisse(e/signe)
            elif coup == 'encre' and j <= 3:
                pitch -= 0.15*math.sin(max(0.0, min(1.0, e/0.8))*math.pi)
            elif coup == 'chute':
                pitch += 0.12 + 0.03*math.sin(t*22 + k)
            elif PLAQUE_ACTIF[0] and k in (0, 7):
                pitch += 0.35 if j == 1 else 0.08
            elif coup == 'balayage' or (coup == 'plaquage' and e < signe):
                a = lisse(e/signe) if e < signe else 1.0
                pitch += (-0.1 if j <= 2 else (0.3 if j >= 6 else 0.0))*a
            elif coup == 'descente' and ch:
                prog, tau = ch['prog'], ch['tau']
                if ch['phase'] == 'decroche':
                    if avant: pitch += prog*(0.55 if j == 1 else 0.16) + prog*0.08*math.sin(t*9 + j + k)
                    elif j <= 2: pitch -= 0.3*prog
                elif ch['phase'] == 'chute':
                    tr = ch['hautY']*min(1, prog*1.6); pose = lisse((prog - 0.6)/0.4)
                    pitch = pitch*0.3 + (1 - pose)*(0.28 if j >= 2 else 0.1)*tr + pose*(-0.22 if j <= 2 else 0.04) + 0.07*math.sin(t*24 + j*0.8 + k)
                else:
                    am = math.exp(-7*tau)
                    if j <= 2: pitch += -0.32*am*math.cos(15*tau)
                    elif j >= 6: pitch += 0.45*math.exp(-5*tau)
                    yaw *= (1 - 0.6*am)
            Q[f'Bras{k}_{j}'] = Euler((pitch, 0, yaw), 'XYZ').to_quaternion()
    respi = math.sin(t*1.25); contraction = 0.0
    if coup == 'encre': contraction += math.sin(max(0.0, min(1.0, e/0.6))*math.pi)*0.25
    if coup == 'descente' and ch and ch['phase'] == 'atterrit': contraction += 0.35*math.exp(-7*ch['tau'])*math.cos(12*ch['tau'])
    Q['Manteau1'] = Euler((0.05*respi + contraction, 0, 0.02*math.sin(t*0.7)), 'XYZ').to_quaternion()
    Q['Manteau2'] = Euler((0.08*math.sin(t*1.25 + 0.5) + contraction, 0, 0.04*math.sin(t*0.6)), 'XYZ').to_quaternion()
    Q['Tete'] = Euler((-0.3*ecart_m + 0.03*math.sin(t*0.8), 0, 0), 'XYZ').to_quaternion()
    for nm in ('Racine', 'OeilG', 'OeilD'): Q[nm] = Quaternion()
    Q['Bec'] = Euler((0.6*bec_m, 0, 0), 'XYZ').to_quaternion()
    return Q

# ---------------------------------------------------------------- attaques au contact (port de WitnessGestes)
FOUET = dict(frappe=0.18, retard=0.018, suite=0.55, arme=2.0, courbure=0.24, depasse=0.3, portee_bras=5.5, contact=0.28)
TOUR_B, ENF_B = 0.35, 0.3
MORS = dict(bond=1.8, tenue=0.1, retour=0.35)
def angle_fouet(x, signe, a_repos, a_cible):
    F = FOUET
    if x <= 0: return a_repos
    if x < signe: return a_repos + (F['arme'] - a_repos)*lisse(x/signe)
    fin = a_cible - F['depasse']; u = (x - signe)/F['frappe']
    if u < 1: return F['arme'] + (fin - F['arme'])*u**2.2
    tau = x - signe - F['frappe']
    return fin - 0.25*lisse(tau/0.35) - 0.2*math.sin(tau*10)*math.exp(-tau*7)
def fouet_bras(e, signe, B, T, centre, haut, L):
    F = FOUET
    vers = T - B; vers = vers - haut*vers.dot(haut); avant = vers.normalized() if vers.length > 1e-3 else Vector((1, 0, 0))
    lat = B - centre; lat = lat - haut*lat.dot(haut) - avant*lat.dot(avant)
    cote = lat.normalized() if lat.length > 1e-3 else haut.cross(avant).normalized()
    plan = (haut*0.9 + cote*0.45).normalized(); v = T - B; a_c = math.atan2(v.dot(plan), v.dot(avant))
    frappe = lisse((e - signe)/F['frappe'])
    courbe = F['courbure']*lisse(e/signe)*(1 - frappe) - 0.05*frappe*(1 - lisse((e - signe - F['frappe'])/0.3)) + 0.04*lisse((e - signe - F['frappe'])/0.3)
    J = []; cur = B.copy()
    for j in range(1, len(L) + 1):
        a = angle_fouet(e - F['retard']*(j - 1), signe, 0.15, a_c) + courbe*(j - 1) + 0.06*math.sin(9*e - 0.9*j)*(1 - frappe)
        cur = cur + (avant*math.cos(a) + plan*math.sin(a))*L[j - 1]; J.append(cur)
    return J, lisse(e/0.15)*(1 - lisse((e - signe - F['frappe'] - 0.25)/0.3))
def fouet_corps(e, signe, distance, cote):
    F = FOUET; arme = lisse(e/signe)
    coup = lisse((e - signe + 0.04)/F['frappe'])*(1 - lisse((e - signe - F['frappe'] - 0.1)/0.4))
    fin = 1 - lisse((e - signe - F['frappe'] - 0.1)/0.4)
    bond = max(0.0, min(3.5, distance - F['portee_bras'])); pivot = cote*(0.16*arme*(1 - coup) - 0.2*coup)*fin
    return Matrix.Translation((bond*coup, 0, 0.9*arme*fin)) @ Matrix.Rotation(pivot, 4, 'Z') @ autour(P_CAB, (0.22*arme*(1 - coup) - 0.08*coup)*fin)
def balayage_g(e, signe):
    if e < signe: return Matrix.Translation((0, 0, -ENF_B*lisse(e/signe))), 0.0, 0.0
    u = max(0.0, min(1.0, (e - signe)/TOUR_B)); ang = 2*math.pi*(1 - (1 - u)**3)
    om = 2*math.pi*3*(1 - u)**2/TOUR_B if u < 1 else 0.0
    w = lisse((e - signe + 0.08)/0.08)*(1 - lisse((e - signe - TOUR_B)/0.4))
    return Matrix.Translation((0, 0, -ENF_B*(1 - u))) @ Matrix.Rotation(ang, 4, 'Z'), om, w
def chemin_balayage(B, centre, haut, om):
    rel = B - centre; rel = rel - haut*rel.dot(haut); r0 = rel.length; d = rel.normalized() if r0 > 1e-3 else Vector((1, 0, 0))
    cote = haut.cross(d); kap = 0.004*om; pts = [B.copy()]
    for i in range(1, 21):
        s_ = i*0.35; a = -kap*s_
        pts.append(centre + (d*math.cos(a) + cote*math.sin(a))*(r0 + s_) + haut*(0.6*min(1, s_/1.5)))
    return pts
def decalage_geste(coup, e, signe, T):
    if coup == 'fouet' and e < signe + FOUET['frappe'] + FOUET['suite']:
        dist = (Vector((T.x, T.y, 0))).length if T is not None else 0
        return fouet_corps(e, signe, dist, 1 if FOUET_K.get('k', 0) == 0 else -1)
    if coup == 'balayage' and e < signe + TOUR_B + 0.4: return balayage_g(e, signe)[0]
    return Matrix.Identity(4)
FOUET_K = {}
def gestes_attaque(Q, coup, e, signe, Mw, T):
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local; centre = Mrac.translation; haut = haut_de(Mw)
    if coup == 'fouet' and e < signe + FOUET['frappe'] + FOUET['suite']:
        k = FOUET_K['k']; ch = CHAINES[k]; B = (Mrac @ rest_rel(ch[0])).translation
        J, glob = fouet_bras(e, signe, B, T, centre, haut, LONG[k])
        orienter(ch, Mrac, J, [glob]*8, Q)
    elif coup == 'balayage':
        _, om, w = balayage_g(e, signe)
        if w < 0.001: return
        for k in range(8):
            ch = CHAINES[k]; B = (Mrac @ rest_rel(ch[0])).translation
            orienter(ch, Mrac, articulations(B, chemin_balayage(B, centre, haut, om), LONG[k]), [x*w for x in P_COURSE], Q)

def enrouler(Q, tt, tete_bas, U, sol_z, Mw):
    """port de WitnessCorps.enrouler (étranglement) ; Mw = matrice monde de l'armature"""
    r = 0.68 + 0.5*math.exp(-tt*0.9) - 0.04*max(0, math.sin(tt*7))
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local @ Q['Racine'].to_matrix().to_4x4()
    centre = Mrac.translation; N = tete_bas
    fv = Vector((centre.x - N.x, centre.y - N.y, 0)); fv = fv.normalized() if fv.length > 1e-3 else Vector((1, 0, 0))
    l = U.cross(fv).normalized()
    for k in (0, 7):
        ch = CHAINES[k]; B = (Mrac @ rest_rel(ch[0])).translation
        sens = 1 if (B - N).dot(l) >= 0 else -1
        pts = chemin_enroule(B, N, U, fv, r, 0.1 if k == 0 else 0.3, sens, 1.75)
        orienter(ch, Mrac, articulations(B, pts, LONG[k]), [lisse((tt - 0.05*j)/0.4) for j in range(8)], Q)
    w = 0.9*lisse(tt/0.5)
    for k in range(1, 7):
        ch = CHAINES[k]; B = (Mrac @ rest_rel(ch[0])).translation
        dv = Vector((B.x - centre.x, B.y - centre.y, 0)); dv = dv.normalized() if dv.length > 1e-3 else fv
        F = Vector((centre.x, centre.y, sol_z)) + dv*4.2
        orienter(ch, Mrac, articulations(B, chemin_sol(B, dv, F, UPV), LONG[k]), [w]*8, Q)

# ---------------------------------------------------------------- marche à pieds posés (port de WitnessGestes)
MR = dict(rayon=4.1, seuil=1.5, seuil_repos=0.6, avance=1.5, anticipation=0.15, course_debut=16, course_plein=22)
DIRS = {}
for k in range(8):
    d = arm.data.bones[f'Bras{k}_8'].head_local - arm.data.bones[f'Bras{k}_1'].head_local; d.z = 0; DIRS[k] = d.normalized()
POSES_PIEDS = []                     # (instant, position) de chaque pied qui se repose : petits ronds dans l'eau
class Marche:
    def __init__(self): self.pieds = {}; self.air = {}; self.dernier = 0
def haut_de(Mw): return (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
SURFACE = [None]                     # escalade : fonction qui ramène un point sur le coin sol/mur/plafond
def maj_marche(m, t, Mw, vel):
    surf = SURFACE[0]
    haut = haut_de(Mw); orig = Mw.translation; vel = vel - haut*vel.dot(haut); v = vel.length; ideal = {}
    for k, d in DIRS.items():
        p = Mw @ (d*MR['rayon']); p = p - haut*(p - orig).dot(haut); ideal[k] = p + vel*MR['anticipation']
        if surf: ideal[k] = surf(ideal[k])
        f0 = m.pieds.get(k)
        if f0 is None or (f0 - ideal[k]).length > 13 or (not surf and abs((f0 - orig).dot(haut)) > 1.5): m.pieds[k] = ideal[k].copy(); m.air.pop(k, None)
    for k, a in list(m.air.items()):
        if t - a['t0'] >= a['duree']: m.pieds[k] = a['fin']; del m.air[k]; POSES_PIEDS.append((a['t0'] + a['duree'], a['fin'].copy()))
    if m.air: return
    seuil = MR['seuil'] if v > 1 else MR['seuil_repos']; ec = [0.0, 0.0]
    for k in DIRS: ec[k % 2] = max(ec[k % 2], (m.pieds[k] - ideal[k]).length)
    if ec[0] > seuil and ec[1] > seuil: g = 1 if m.dernier == 0 else 0
    elif ec[0] > seuil: g = 0
    elif ec[1] > seuil: g = 1
    else: return
    m.dernier = g; duree = max(0.18, min(0.3, 0.3 - v*0.005))
    for k in DIRS:
        if k % 2 == g:
            fin = ideal[k] + vel*duree*MR['avance']
            if surf: fin = surf(fin)
            if (m.pieds[k] - fin).length > 0.3: m.air[k] = dict(t0=t, duree=duree, debut=m.pieds[k].copy(), fin=fin, hauteur=0.8 + v*0.025)
def pied(m, k, t, haut):
    a = m.air.get(k)
    if a: u = lisse((t - a['t0'])/a['duree']); return a['debut'].lerp(a['fin'], u) + haut*(a['hauteur']*math.sin(math.pi*u))
    return m.pieds.get(k)
NORMALE = [None]                     # escalade : normale de la surface sous un pied
def chemin_pied(B, F, centre, haut):
    nS = NORMALE[0](F) if NORMALE[0] else haut
    dh = F - centre; dh = dh - nS*dh.dot(nS); dh = dh.normalized() if dh.length > 1e-3 else Vector((1, 0, 0))
    Fp = F + nS*0.2; pts = [B.copy()]
    bezier(B, B + (Fp - B)*0.35 + haut*0.5, Fp - dh*1.0 + nS*0.25, Fp, 10, pts); pts += [Fp + dh*1.5, Fp + dh*4]; return pts
def chemin_trainee(B, centre, avant, haut, t):
    cote = haut.cross(avant).normalized(); rel = B - centre; lat = rel.dot(cote)
    E = centre - avant*5.6 + cote*lat*2.0 + haut*0.25
    dh = rel - haut*rel.dot(haut); dh = dh.normalized() if dh.length > 1e-3 else -avant
    brut = []; bezier(B, B + dh*1.0 + haut*0.3, E + avant*3.0, E, 14, brut)
    pts = [B.copy()] + [p + cote*(0.35*(i/len(brut))*math.sin(t*9 - (i/len(brut))*5)) for i, p in enumerate(brut, 1)]
    pts.append(E - avant*3); return pts
P_POSE = [1, 1, 1, 1, 1, 1, 0.75, 0.5]; P_COURSE = [1, 1, 1, 1, 1, 1, 0.85, 0.7]
def locomotion(Q, t, Mw, vel, m, poids):
    haut = haut_de(Mw); vel = vel - haut*vel.dot(haut)
    course = lisse((vel.length - MR['course_debut'])/(MR['course_plein'] - MR['course_debut']))
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local; centre = Mrac.translation
    avant = vel.normalized() if vel.length > 0.5 else (Mw.to_3x3() @ Vector((1, 0, 0))).normalized()
    wp = [x*poids*(1 - course) for x in P_POSE]; wc = [x*poids*course for x in P_COURSE]
    for k in range(8):
        ch = CHAINES[k]; B = (Mrac @ rest_rel(ch[0])).translation
        if course < 0.999:
            F = pied(m, k, t, haut)
            if F is not None: orienter(ch, Mrac, articulations(B, chemin_pied(B, F, centre, haut), LONG[k]), wp, Q)
        if course > 0.001: orienter(ch, Mrac, articulations(B, chemin_trainee(B, centre, avant, haut, t), LONG[k]), wc, Q)

def poser(Mw, Q, cam_pos):
    arm.matrix_world = Mw
    for nm, q in Q.items(): arm.pose.bones[nm].rotation_quaternion = q
    for pb in arm.pose.bones:                                 # os écartés (Bone.Position dans Roblox) : déplacement de la tête de l'os
        if not pb.parent: continue
        M0 = REST_REL[pb.name]; f = facteur_os(pb.name); tr = M0.translation
        pb.location = M0.to_3x3().inverted() @ (Vector((tr.x*f[0], tr.y*f[1], tr.z*f[2])) - tr) if f != (1.0, 1.0, 1.0) else Vector((0, 0, 0))
    bpy.context.view_layer.update()
    for nm in ('OeilG', 'OeilD'):                     # les yeux suivent la caméra (angle max 0,7 rad)
        pb = arm.pose.bones[nm]; Mb = arm.matrix_world @ pb.bone.matrix_local
        d = (Mb.inverted().to_3x3() @ (cam_pos - Mb.translation)).normalized()
        q = Vector((0, 1, 0)).rotation_difference(d); pb.rotation_quaternion = Quaternion(q.axis, min(q.angle, 0.7))

# ================================================================ scène
FPS = int(os.environ.get('FPS', '24'))
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('ECH', '32')); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 12; sc.cycles.transmission_bounces = 12; sc.cycles.transparent_max_bounces = 12
sc.render.resolution_x, sc.render.resolution_y = (int(x) for x in os.environ.get('RES', '1280x720').split('x'))
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
EXPO = {'couloir': 0.0, 'chute': 0.0, 'etrangle': 0.0, 'plafond': 0.0, 'sol': 0.0, 'fouet': 0.0, 'balayage': 0.0, 'morsure': 0.0, 'devore': 0.0, 'plaquage': 0.0, 'enlevement': 0.0, 'encre': 0.0, 'escalade': 0.0, 'traversee': 0.0}[PLAN]
sc.view_settings.exposure = float(os.environ.get('EXPO', EXPO))
w = bpy.data.worlds.new('W'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.01, 0.012, 0.016, 1); sc.world = w
H = 12.0; LARG = 12.0
L0, L1 = (-80.0, 110.0) if PLAN == 'couloir' else (-40.0, 40.0)
LX = L1 - L0; CX = (L0 + L1)/2
for nom, size, loc, mt in (('Sol', (LX, LARG, 0.4), (CX, 0, -0.2), K.mat('tole_striee', (120, 124, 126))),
                           ('Plafond', (LX, LARG, 0.4), (CX, 0, H + 0.2), K.mat('plafond', (190, 192, 188))),
                           ('MurN', (LX, 0.4, H), (CX, LARG/2 + 0.2, H/2), K.mat('metal_peint', (150, 156, 160))),
                           ('MurS', (LX, 0.4, H), (CX, -LARG/2 - 0.2, H/2), K.mat('metal_peint', (150, 156, 160))),
                           ('Fond', (0.4, LARG, H), (L0 + 0.2, 0, H/2), K.mat('metal_peint', (120, 126, 130)))):
    if PLAN != 'couloir' and nom == 'MurS': continue        # vue de côté : mur retiré côté caméra
    if PLAN == 'traversee' and nom == 'Plafond':             # plafond percé d'une vraie trouée sous la grille, gaine au-dessus (en coupe)
        pl = K.mat('plafond', (190, 192, 188)); mg = K.mat('metal_peint', (120, 126, 128))
        for sz_, lc_ in (((LX, 6 - 2.2, 0.5), (CX, -(6 + 2.2)/2, H + 0.25)), ((LX, 6 - 2.2, 0.5), (CX, (6 + 2.2)/2, H + 0.25)),
                         ((L1 - 2.2, 4.4, 0.5), ((L1 + 2.2)/2, 0, H + 0.25)), ((2.2 - L0, 4.4, 0.5), ((L0 - 2.2)/2, 0, H + 0.25))):
            K.box_uv(K.cube('Plafond', sz_, lc_, pl, 0))
        K.box_uv(K.cube('GaineFond', (30, 0.3, 4.6), (0, 2.45, H + 0.5 + 2.3), mg, 0))
        K.box_uv(K.cube('GaineHaut', (30, 4.9, 0.3), (0, 0, H + 0.5 + 4.6 + 0.15), mg, 0))
        for (sx, sy_, x_, y_) in ((4.8, 0.2, 0, 2.3), (4.8, 0.2, 0, -2.3), (0.2, 4.8, 2.3, 0), (0.2, 4.8, -2.3, 0)):
            K.cube('Cadre', (sx, sy_, 0.3), (x_, y_, H + 0.25), K.mat('metal_peint', (70, 72, 70)), 0.03)
        for i in range(7): K.cube('Barreau', (0.18, 4.4, 0.25), (-1.86 + i*0.62, 0, H + 0.05), K.mat('metal_peint', (54, 56, 56)), 0.02)
        continue
    o = K.cube(nom, size, loc, mt, 0); K.box_uv(o)
for x in range(int(L0) + 6, int(L1), 8):
    for sy in (-1, 1):
        if sy == -1 and PLAN != 'couloir': continue
        if PLAN == 'escalade' and x in (-2, 6): continue
        o = K.cube('Arche', (0.8, 0.6, H), (x, sy*(LARG/2 - 0.3), H/2), K.mat('metal_peint', (90, 96, 104)), 0.05); K.box_uv(o)
    if PLAN in ('chute', 'etrangle'): o = K.cube('ArcheHaut', (0.8, LARG, 0.6), (x, 0, H - 0.3), K.mat('metal_peint', (90, 96, 104)), 0.05); K.box_uv(o)
def lampe(loc, e, col=(1.0, 0.95, 0.88), size=2.0, cible=None, forme='SQUARE', size_y=None):
    ld = bpy.data.lights.new('A', 'AREA'); ld.size = size; ld.energy = e; ld.color = col; ld.shape = forme
    if size_y: ld.size_y = size_y
    ob = bpy.data.objects.new('A', ld); sc.collection.objects.link(ob); ob.location = loc
    if cible is not None: ob.rotation_euler = (Vector(cible) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob
cd = bpy.data.cameras.new('C'); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(60); cam = bpy.data.objects.new('C', cd)
sc.collection.objects.link(cam); sc.camera = cam
def viser(pos, cible): cam.location = pos; cam.rotation_euler = (Vector(cible) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- mannequin de joueur (proportions R15 : 5,3 studs)
class Mannequin:
    def __init__(self):
        bleu = K.mat_plain('Combinaison', (46, 58, 78), 0.7); peau = K.mat_plain('Peau', (196, 152, 118), 0.6)
        bande = K.mat_plain('Bande', (210, 170, 40), 0.5)
        self.racine = bpy.data.objects.new('Mannequin', None); sc.collection.objects.link(self.racine)
        def piv(nom, loc):
            e = bpy.data.objects.new(nom, None); sc.collection.objects.link(e); e.parent = self.racine; e.location = loc; return e
        def boite(nom, size, loc, mat, parent):
            o = K.cube(nom, size, (0, 0, 0), mat, 0.08); o.parent = parent; o.location = loc; return o
        boite('Torse', (1.0, 2.0, 2.0), (0, 0, 0), bleu, self.racine)
        boite('Bande', (1.04, 2.04, 0.18), (0, 0, 0.35), bande, self.racine)
        self.tete = boite('Tete', (1.2, 1.2, 1.2), (0, 0, 1.65), peau, self.racine)
        self.epaule = {s: piv(f'Epaule{s}', (0, s*1.5, 0.8)) for s in (-1, 1)}
        for s in (-1, 1): boite(f'Bras{s}', (0.95, 0.95, 2.0), (0, 0, -0.8), bleu, self.epaule[s]); boite(f'Main{s}', (0.9, 0.9, 0.4), (0, 0, -1.85), peau, self.epaule[s])
        self.hanche = {s: piv(f'Hanche{s}', (0, s*0.5, -1.0)) for s in (-1, 1)}
        for s in (-1, 1): boite(f'Jambe{s}', (0.95, 0.95, 2.0), (0, 0, -1.0), bleu, self.hanche[s])
    def points_membres(self):
        """poignet, coude, cheville, genou de chaque côté : (position, axe du membre)"""
        out = []
        for s_ in (1, -1):
            e_ = self.epaule[s_].matrix_world; o = e_.translation; m = e_ @ Vector((0, 0, -1.85)); ax = (m - o).normalized()
            out += [(m, ax), (o + (m - o)*0.5, ax)]
        for s_ in (1, -1):
            h_ = self.hanche[s_].matrix_world; o = h_.translation; f_ = h_ @ Vector((0, 0, -1.9)); ax = (f_ - o).normalized()
            out += [(f_, ax), (o + (f_ - o)*0.5, ax)]
        return out
    def extremites(self):
        """mains et pieds (position, axe du membre vers l'extrémité)"""
        out = {}
        for s_, nom in ((1, 'G'), (-1, 'D')):
            e_ = self.epaule[s_].matrix_world; m = e_ @ Vector((0, 0, -1.85)); out['main' + nom] = (m, (m - e_.translation).normalized())
            h_ = self.hanche[s_].matrix_world; f_ = h_ @ Vector((0, 0, -1.9)); out['pied' + nom] = (f_, (f_ - h_.translation).normalized())
        return out
    def libre(self, M, epaules=(0.0, 0.0), ecart=0.0, hanches=(0.0, 0.0), jambes=0.0):
        """pose quelconque : M = repère du centre du torse ; épaules : bras levés vers l'avant (rad) ; ecart : bras ouverts sur le côté"""
        self.racine.matrix_world = M
        for i, s_ in enumerate((-1, 1)):
            self.epaule[s_].rotation_mode = 'XYZ'; self.epaule[s_].rotation_euler = (s_*ecart, -epaules[i], 0)
            self.hanche[s_].rotation_mode = 'XYZ'; self.hanche[s_].rotation_euler = (s_*jambes, hanches[i], 0)
        bpy.context.view_layer.update()
    def poser(self, hrp, face, tt, saisi):
        """hrp = centre du torse ; face = direction regardée ; tt = temps depuis la saisie"""
        yaw = math.atan2(face.y, face.x)
        self.racine.matrix_world = Matrix.Translation(hrp) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(-0.1*lisse(tt/0.6) if saisi else 0, 4, 'Y')
        a = lisse((tt - 0.15)/0.45) if saisi else 0.0
        for s in (-1, 1):
            # les mains montent vers le cou et tirent sur les bras qui l'étranglent
            vis = Vector((0.75, -s*0.6, -1.0)).normalized()
            q = Vector((0, 0, -1)).rotation_difference(vis)
            tir = 0.12*math.sin(tt*11 + s) if saisi else 0
            self.epaule[s].rotation_mode = 'QUATERNION'; self.epaule[s].rotation_quaternion = Quaternion().slerp(q, a) @ Quaternion((1, 0, 0), tir)
            k = lisse(tt/0.6)*0.55*math.sin(tt*9 + (0 if s > 0 else math.pi)) if saisi else 0
            self.hanche[s].rotation_mode = 'XYZ'; self.hanche[s].rotation_euler = (0.08*s*lisse(tt/0.6) if saisi else 0, k, 0)
        bpy.context.view_layer.update()
        U = (self.tete.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        return self.tete.matrix_world.translation - U*0.6, U

# ---------------------------------------------------------------- plans
def profil(cles, x0):
    """position le long de X pour une vitesse définie par des points (temps, vitesse) reliés en ligne droite"""
    def pos(t):
        x = x0
        for (ta, va), (tb, vb) in zip(cles, cles[1:]):
            if t <= ta: break
            u = min(t, tb) - ta; x += va*u + 0.5*(vb - va)/(tb - ta)*u*u
        if t > cles[-1][0]: x += cles[-1][1]*(t - cles[-1][0])
        return x
    return pos
X_PLAF = profil([(0, 0), (0.6, 0), (1.0, 14), (3.6, 14), (4.2, 0), (4.8, 0)], -24)
X_SOL = profil([(0, 0), (0.5, 0), (1.0, 8), (2.2, 8), (2.8, 26), (4.0, 26), (4.6, 0), (5.2, 0)], -30)
def racine_plafond(t): return Matrix.Translation((X_PLAF(t), 0, H)) @ RETOURNE, None, 0.0, None
def racine_sol(t): return Matrix.Translation((X_SOL(t), 0, 0)), None, 0.0, None
def racine_couloir(t):
    tf = math.sqrt(2*H/G_JEU); t_ch = 3.0; fin_ch = t_ch + DECROCHAGE + tf + ATTERR; t_run = 0.65
    if t < t_ch: return Matrix.Translation((26 + 14*t, 0.4*math.sin(t*0.8), H)) @ RETOURNE, None, 0.0, None
    if t < fin_ch:
        Mm, tombe, phase, prog, tau = chute(t - t_ch, DECROCHAGE, tf)
        ch = {'phase': phase, 'prog': prog, 'tau': tau, 'hautY': (Mm.to_3x3().inverted() @ UPV).z}
        return Matrix.Translation((68, 0.4*math.sin(2.4), H - tombe if tombe is not None else 0)) @ Mm, 'descente', t - t_ch, ch
    if t < fin_ch + t_run:
        a = (t - fin_ch)/t_run; return Matrix.Translation((68 + 17*a, 0.3*math.sin(t*3), 0)), 'descente', t - t_ch, None
    return Matrix.Translation((85, 0, 0)), 'saisie', t - fin_ch - t_run, None
SIM = {'t': -1.0, 'm': Marche(), 'poids': 0.0}
def avancer(racine_fn, t_fin):
    """simule la marche pas à pas (1/96 s) jusqu'à t_fin, comme le ferait chaque image du jeu"""
    h = 1/96
    def vitesse(t):
        t0 = max(0.0, t - h); return (racine_fn(t + h)[0].translation - racine_fn(t0)[0].translation)/(t + h - t0)
    def etape(t, dt):
        Mw, coup, e, ch = racine_fn(t); vel = vitesse(t)
        geste = ch is not None or (coup is not None and e < SIGNE.get(coup, 0.5) + 0.8)
        cible = 0.0 if geste else 1.0
        SIM['poids'] = cible if dt is None else SIM['poids'] + (cible - SIM['poids'])*min(1.0, dt*6)
        if SIM['poids'] < 0.01: SIM['m'] = Marche()
        if SIM.get('preset'): SIM['preset'](t, SIM['m'])
        if SIM['poids'] >= 0.01: maj_marche(SIM['m'], t, Mw, vel)
        SIM['t'] = t; SIM['vel'] = vel
    if SIM['t'] < 0: etape(0.0, None)
    while SIM['t'] < t_fin - 1e-9:
        t = min(SIM['t'] + h, t_fin); etape(t, t - SIM['t'])
    return racine_fn(t_fin)
def plan_marche(t, racine_fn, camera_fn):
    Mw, coup, e, ch = avancer(racine_fn, t)
    Q = animer(t, 0, coup, e, False, ch)
    if SIM['poids'] >= 0.01: locomotion(Q, t, Mw, SIM['vel'], SIM['m'], SIM['poids'])
    CAM = camera_fn(t, Mw)
    poser(Mw, Q, CAM)
def cam_plafond(t, Mw):
    x = Mw.translation.x; xc = X_PLAF(max(0, t - 0.3)) - 1.5
    CAM = Vector((xc, -10.5, 2.6)); viser(CAM, (x + 0.5, 0, 10.0)); cd.angle_y = math.radians(56); return CAM
def cam_sol(t, Mw):
    x = Mw.translation.x; xc = X_SOL(max(0, t - 0.25)) + 1.0
    CAM = Vector((xc, -13.5, 5.2)); viser(CAM, (x + 0.8, 0, 1.0)); cd.angle_y = math.radians(48); return CAM
def cam_couloir(t, Mw):
    pos = Mw.translation; CAM = Vector((96, -1.5, 5.0)); cible = pos + Vector((0, 0, -1.2 if pos.z > H - 1 else 1.4))
    dist = (cible - CAM).length; cd.angle_y = max(math.radians(24), min(math.radians(70), 2*math.atan(6.5/dist)))
    viser(CAM, cible); return CAM
def plan_couloir_ancien(t):
    """vu par un joueur au bout du couloir : plafond 14 studs/s, chute, course 26 studs/s, bras qui se lèvent"""
    tf = math.sqrt(2*H/G_JEU); t_ch = 3.0; fin_ch = t_ch + DECROCHAGE + tf + ATTERR; t_run = 0.65
    ch = None; coup = None; e = 0.0
    if t < t_ch:
        pos = Vector((26 + 14*t, 0.4*math.sin(t*0.8), H)); Mm = RETOURNE; vit = 14
    elif t < fin_ch:
        Mm, tombe, phase, prog, tau = chute(t - t_ch, DECROCHAGE, tf); coup = 'descente'; e = t - t_ch; vit = 0
        pos = Vector((68, 0.4*math.sin(2.4), H - tombe if tombe is not None else 0))
        ch = {'phase': phase, 'prog': prog, 'tau': tau, 'hautY': (Mm.to_3x3().inverted() @ UPV).z}
    elif t < fin_ch + t_run:
        a = (t - fin_ch)/t_run; pos = Vector((68 + 17*a, 0.3*math.sin(t*3), 0)); Mm = Matrix.Identity(4); vit = 26
    else:
        pos = Vector((85, 0, 0)); Mm = Matrix.Identity(4); vit = 0; coup = 'saisie'; e = t - fin_ch - t_run
    Q = animer(t, vit, coup, e, False, ch)
    CAM = Vector((96, -1.5, 5.0)); cible = pos + Vector((0, 0, -1.2 if pos.z > H - 1 else 1.4))
    dist = (cible - CAM).length; cd.angle_y = max(math.radians(24), min(math.radians(70), 2*math.atan(6.5/dist)))
    viser(CAM, cible)
    poser(Matrix.Translation(pos) @ Mm, Q, CAM)
def plan_chute(t):
    """de côté : accrochée au plafond, elle se décroche, tombe et se reçoit"""
    tf = math.sqrt(2*H/G_JEU); t_ch = 0.4; fin_ch = t_ch + DECROCHAGE + tf + ATTERR; ch = None; coup = None; e = 0.0
    if t < t_ch: pos = Vector((0, 0, H)); Mm = RETOURNE; vit = 0
    elif t < fin_ch:
        Mm, tombe, phase, prog, tau = chute(t - t_ch, DECROCHAGE, tf); coup = 'descente'; e = t - t_ch; vit = 0
        pos = Vector((0, 0, H - tombe if tombe is not None else 0))
        ch = {'phase': phase, 'prog': prog, 'tau': tau, 'hautY': (Mm.to_3x3().inverted() @ UPV).z}
    else:
        a = t - fin_ch; pos = Vector((3*lisse(a/0.6)*a, 0, 0)); Mm = Matrix.Identity(4); vit = 10*lisse(a/0.4)
    Q = animer(t, vit, coup, e, False, ch)
    CAM = Vector((3.5, -19.0, 6.2)); viser(CAM, (0.8, 0, 5.6)); cd.angle_y = math.radians(46)
    poser(Matrix.Translation(pos) @ Mm, Q, CAM)
MANN = Mannequin() if PLAN in ('etrangle', 'fouet', 'morsure', 'devore', 'plaquage', 'enlevement') else None
MANNS = [Mannequin() for _ in range(3)] if PLAN == 'balayage' else []
T0_ATT = {'fouet': 0.4, 'balayage': 0.3, 'morsure': 0.4}
def bascule(pieds, yaw, angle, lever=0.0):
    """repère du torse d'un mannequin qui pivote autour de ses pieds : angle > 0 = tombe en arrière"""
    return (Matrix.Translation(pieds + Vector((0, 0, lever))) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(-angle, 4, 'Y') @ Matrix.Translation((0, 0, 3)))
def mannequins(t):
    """pose des mannequins ; renvoie le centre du torse visé (fouet, morsure) et les éclaboussures (x, y, instant, force)"""
    eclab = []
    if PLAN == 'fouet':
        th = T0_ATT['fouet'] + 0.5 + FOUET['contact']; a = max(0.0, t - th)
        recul = 4*(1 - math.exp(-a/0.12)) if t > th else 0.0
        tilt = (0.6*math.sin(math.pi*min(1, a/1.2))) if t > th else 0.0
        pieds = Vector((8 + recul, -1.2, 0))
        MANN.libre(bascule(pieds, math.pi, tilt), epaules=(1.2*lisse(a/0.2)*(1 - lisse((a - 0.8)/0.6)),)*2, ecart=0.5*lisse(a/0.2)*(1 - lisse((a - 0.8)/0.6)))
        eclab += [(8, -1.2, th, 0.14), (8 + 2, -1.2, th + 0.12, 0.08)]
        return MANN.racine.matrix_world.translation, eclab
    if PLAN == 'morsure':
        tb = T0_ATT['morsure'] + 0.35; a = max(0.0, t - tb)
        sursaut = 0.25*math.exp(-a/0.15)*math.sin(a*40) if t > tb else 0.0
        M = Matrix.Translation((4.2, 0, 0.85 + sursaut)) @ Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))
        MANN.libre(M, epaules=(0.6 + 0.8*lisse(a/0.15)*(1 - lisse((a - 0.4)/0.5)), 0.6 + 0.6*lisse(a/0.15)*(1 - lisse((a - 0.4)/0.5))), hanches=(0.3, -0.2))
        eclab += [(3.2, 0, tb, 0.16)]
        return MANN.racine.matrix_world.translation + Vector((-0.6, 0, 0.2)), eclab
    if PLAN == 'balayage':
        for i, (mn, ang) in enumerate(zip(MANNS, (0.4, 2.2, 3.5))):
            th = T0_ATT['balayage'] + 0.6 + 0.05 + 0.04*i; a = max(0.0, t - th)
            chute_ = (math.pi/2)*lisse(a/0.4)**1.6 if t > th else 0.0
            releve = lisse((t - 2.6 - 0.1*i)/0.6)
            chute_ *= (1 - releve)
            pieds = Vector((math.cos(ang)*7.5, math.sin(ang)*7.5, 0)); yaw = math.atan2(-pieds.y, -pieds.x)
            mn.libre(bascule(pieds, yaw, chute_, 0.8*math.sin(chute_)), epaules=(0.9*min(1, chute_), 0.9*min(1, chute_)), ecart=0.4*min(1, chute_))
            impact = pieds + Vector((math.cos(ang), math.sin(ang), 0))*2.5
            eclab += [(impact.x, impact.y, th + 0.4, 0.2)]
        eclab += [(0, 0, T0_ATT['balayage'] + 0.6, 0.3), (0, 0, T0_ATT['balayage'] + 0.75, 0.18)]
        return None, eclab
    return None, eclab
# ---------------------------------------------------------------- chute dévorante et plaquage (port de WitnessGestes / WitnessCerveau)
def chemin_cage(B, N, U, sens):
    rel = B - N; rel = rel - U*rel.dot(U); d = rel.normalized() if rel.length > 1e-3 else U.cross(Vector((1, 0, 0))).normalized()
    l = U.cross(d).normalized(); pts = [B.copy()]
    for i in range(1, 25):
        s_ = i*0.25; a = sens*0.35*s_; r = 1.05 + 0.25*min(1, s_)
        pts.append(N + (d*math.cos(a) + l*math.sin(a))*r - U*(0.15 + s_*0.75))
    return pts
def repere(pos, avant, haut):
    """matrice monde : avant du modèle = X, haut = Z"""
    av = avant - haut*avant.dot(haut); av = av.normalized(); y = haut.cross(av)
    M = Matrix((av, y, haut)).transposed().to_4x4(); M.translation = pos; return M
PLAQ = dict(signe=0.5, vol=0.45, hauteur=4)
def chemin_coupe(B, centre, axe, ouverture, t, k):
    rel = B - centre; rel = rel - axe*rel.dot(axe); r0 = rel.length; d = rel.normalized() if r0 > 1e-3 else axe.cross(Vector((1, 0, 0))).normalized()
    l = axe.cross(d); pts = [B.copy()]
    for i in range(1, 25):
        s_ = i*0.3
        r = r0 + (ouverture - r0)*math.sin(min(1, s_/3.5)*math.pi/2) - 0.9*max(0, (s_ - 4.5)/2.7)**1.5 + 0.04*math.sin(t*22 + k*1.7 + s_)
        a = 0.1*math.sin(t*3 + k); pts.append(centre + (d*math.cos(a) + l*math.sin(a))*r + axe*(s_*0.85))
    return pts
def coupe(Q, Mw, t, w, ouverture, tete):
    if w < 0.001: return
    arm.matrix_world = Mw; bpy.context.view_layer.update()
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local; centre = Mrac.translation
    axe = (tete - centre).normalized()
    for k in range(8):
        chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
        orienter(chn, Mrac, articulations(B, chemin_coupe(B, centre, axe, ouverture, t, k), LONG[k]), [w]*8, Q)
def chemin_plante(B, P, axe, centre, haut, sens):
    f_ = centre - P; f_ = f_ - axe*f_.dot(axe); f_ = f_.normalized() if f_.length > 1e-3 else haut
    pts = chemin_enroule(B, P, axe, f_, 0.42, 0, sens, 1.1); fin = pts[-1]
    return pts + [fin - haut*1.2, fin - haut*2.5]
def attribuer(bases, points, centre, haut, avant):
    cote = haut.cross(avant)
    ang = lambda v: math.atan2((v - centre).dot(cote), (v - centre).dot(avant))
    bras = sorted(bases.keys(), key=lambda k: ang(bases[k])); pts = sorted(range(len(points)), key=lambda i: ang(points[i]))
    n = min(len(bras), len(pts)); best = min(range(n), key=lambda dec: sum((bases[bras[i]] - points[pts[(i + dec) % n]]).length for i in range(n)))
    return {bras[i]: pts[(i + best) % n] for i in range(n)}
def passage_grille(O, dirv): return O + dirv*0.9 - Vector((0, 0, 0.3))
def par_la_grille(B, passage, suite):
    pts = [B.copy()]; bezier(B, B + Vector((0, 0, -0.6)), passage + Vector((0, 0, 0.8)), passage, 6, pts); return pts + suite[1:]
def chemin_pendant(passage, vers, t, k):
    h = Vector((vers.x - passage.x, vers.y - passage.y, 0)); h = h.normalized() if h.length > 1e-3 else Vector((1, 0, 0))
    lat = Vector((-h.y, h.x, 0)); pts = [passage.copy()]
    for i in range(1, 21):
        s_ = i*0.35; pts.append(passage + h*(0.35*s_) - Vector((0, 0, s_)) + lat*(0.25*math.sin(2.5*t - 0.8*s_ + k)))
    return pts
def a_coups(u, n=3):
    u = max(0.0, min(1.0, u)); i = min(n - 1, int(u*n)); f = u*n - i; return (i + lisse(min(1, f/0.45)))/n
def chemin_ramasse(B, centre, haut, serre, t, k):
    rel = B - centre; rel = rel - haut*rel.dot(haut); d = rel.normalized() if rel.length > 1e-3 else haut.cross(Vector((1, 0, 0))).normalized()
    l = haut.cross(d).normalized()*(1 if k % 2 == 0 else -1)
    plan = centre - haut*(centre - B).dot(haut) - haut*0.12
    R = (2.3 - 0.35*serre)*(1 + 0.025*math.sin(t*7 + k)); r0 = rel.length
    pts = [B.copy()] + [plan + d*(r0 + (R - r0)*(i/6)) for i in range(1, 7)]
    fin = plan + d*R; rho0 = 0.75 - 0.15*serre; C = fin + l*rho0
    for i in range(1, 25):
        phi = i/24*1.7*math.pi; rho = rho0*(1 - 0.55*i/24); pts.append(C + (-l*math.cos(phi) + d*math.sin(phi))*rho)
    return pts
def ramasser(Q, Mw, t, w, serre):
    if w < 0.001: return
    arm.matrix_world = Mw; bpy.context.view_layer.update()
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local; centre = Mrac.translation; haut = (Mw.to_3x3() @ UPV).normalized()
    for k in range(8):
        chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
        orienter(chn, Mrac, articulations(B, chemin_ramasse(B, centre, haut, serre, t, k), LONG[k]), [w]*8, Q)
def poids_chaine(p, j):
    p = max(0.0, min(1.0, p)); return 1.0 if p >= 1 else 1 - (1 - p)**(1/j)
def longueur(pts): return sum((b - a).length for a, b in zip(pts, pts[1:]))
def tronquer(pts, l):
    out = [pts[0]]; s_ = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        if s_ + seg >= l: out.append(a.lerp(b, (l - s_)/max(seg, 1e-6))); return out
        s_ += seg; out.append(b)
    return out
ETIRE_MAX = 4.5
PLAQUE_OFF = Vector((0.6, 0, 0.2))                               # Roblox (0, 0,2, -0,6) dans le repère du joueur
def plaque_repere(Mv):
    R = Mv.to_3x3(); return repere(Mv @ PLAQUE_OFF, R @ Vector((0, 0, 1)), R @ Vector((1, 0, 0)))
def bond_repere(dep, arr, hauteur, u):
    u = max(0.0, min(1.0, u)); pos = dep.lerp(arr, u) + Vector((0, 0, 4*hauteur*u*(1 - u))); b = 0.4*(1 - 2*u)
    dv = Vector((arr.x - dep.x, arr.y - dep.y, 0)).normalized()
    vol = repere(pos, dv, UPV) @ Matrix.Rotation(-b, 4, 'Y'); colle = repere(pos, UPV, -dv)
    return interp(vol, colle, lisse((u - 0.35)/0.65))
def plan_devore(t):
    """au plafond au-dessus d'un joueur ; tension (fin du signe), décrochage bref, chute sur la tête, cage de bras, effondrement"""
    t_f = 1.2; tete_haut = 3 + 1.65 + 0.6; tf = math.sqrt(2*(H - tete_haut)/G_JEU); ti = t_f + 0.12 + tf; D = 2.0
    pieds = Vector((0.3, 0, 0)); avant = Vector((1, 0, 0)); axe = Vector((0, 0, 1)).cross(avant)
    tt = t - ti
    bas = 1.45*lisse((tt - 0.9)/1.0) if tt > 0 else 0.0
    sec = 0.06*math.sin(tt*38) if 0.3 < tt < 1.1 else 0.0
    rot = Matrix.Rotation(-bas, 4, axe)
    M = Matrix.Translation(pieds) @ rot @ Matrix.Translation((sec, 0, 3)) ; M = Matrix.Translation((0, 0, 0.6*math.sin(bas))) @ M
    M = M @ Matrix.Rotation(math.pi, 4, 'Z')                    # le joueur fait face à la créature
    bras = lisse((tt - 0.25)/0.3)*(1 - lisse((tt - 1.0)/0.5)) if tt > 0 else 0.0
    MANN.libre(M, epaules=(2.4*bras + 0.15*math.sin(tt*21)*bras, 2.2*bras + 0.15*math.sin(tt*17 + 1)*bras), ecart=0.3*bras)
    ECLAB[:] = [(1.8, 0, ti + D - 0.15, 0.28), (1.8, 0, ti + D, 0.14)]
    hautC = (rot.to_3x3() @ Vector((0, 0, 1))).normalized()
    tete_c = MANN.tete.matrix_world.translation
    if t < t_f:
        Mw = Matrix.Translation((0, 0, H)) @ RETOURNE; coup, e, ch = 'chute', t + 0.3, None
    elif t < ti:
        Mm, tombe, phase, prog, tau = chute(t - t_f, 0.12, tf)
        Mw = Matrix.Translation((0, 0, H - tombe)) @ Mm; coup, e = 'descente', t - t_f
        ch = {'phase': phase, 'prog': prog, 'tau': tau, 'hautY': (Mm.to_3x3().inverted() @ UPV).z}
    elif tt < D:
        g = min(1, tt/0.3); pos = (tete_c + hautC*0.6).lerp(tete_c - hautC*0.6, g)
        Mw = repere(pos, avant, hautC); coup, e, ch = 'descente', 99.0, None
    else:
        a = lisse((tt - D)/0.6); fin = Vector((3.2, 0, 0))
        pos = (tete_c - hautC*0.6).lerp(fin, a); Mw = repere(pos, avant, hautC.lerp(Vector((0, 0, 1)), a).normalized()); coup, e, ch = None, 0.0, None
    Q = animer(t, 0, coup, e, False, ch)
    if t < t_f: ramasser(Q, Mw, t, lisse(e/0.5), lisse((e - 1.5 + 0.4)/0.4))     # attente : bras enroulés à plat contre le plafond
    elif t < ti:                                                                  # chute : les bras s'ouvrent en ombrelle vers sa tête
        wO = lisse((t - t_f - 0.06)/0.12); ramasser(Q, Mw, t, 1 - wO, 1.0); coupe(Q, Mw, t, wO, 2.6, tete_c)
    if 0 <= tt < 0.3: coupe(Q, Mw, t, 1.0, 2.6 - 1.25*lisse(tt/0.25), tete_c)   # l'ombrelle se referme en cage
    if 0 <= tt < D + 0.4:
        w = 1 - lisse((tt - D)/0.4); arm.matrix_world = Mw; bpy.context.view_layer.update()
        Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local
        U = (MANN.tete.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized(); N = tete_c - U*0.6
        for k in range(8):
            chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
            orienter(chn, Mrac, articulations(B, chemin_cage(B, N, U, 1 if k % 2 == 0 else -1), LONG[k]), [w*lisse((tt - 0.03*j)/0.25) for j in range(8)], Q)
    CAM = Vector((2.2, -11.5, 6.0)); viser(CAM, (0.8, 0, 5.8)); cd.angle_y = math.radians(60)
    poser(Mw, Q, CAM)
def plan_plaquage(t):
    """ramassé, bond en arc qui finit collé contre sa poitrine, bras lancés chacun vers son membre ; ils se referment dès le contact
    et il tombe à la renverse avec elle dessus (port de coupPlaquage et de WitnessCorps)"""
    t0 = 0.3; tb = t0 + PLAQ['signe']; ta = tb + PLAQ['vol']; RENV = 0.35
    dep = Vector((0, 0, 0)); dirv = Vector((1, 0, 0)); pieds = Vector((10, 0, 0))
    Mdeb = Matrix.Translation(pieds + Vector((0, 0, 3))) @ Matrix.Rotation(math.pi, 4, 'Z')     # debout, il lui fait face
    arr = Mdeb @ PLAQUE_OFF
    couche = Vector((10 + 1.0, 0, 0.75))
    Mall = Matrix.Translation(couche) @ Matrix(((0, 0, 1, 0), (0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1)))
    if 'assign' not in PLAQ:                                     # bras -> membres, dans la pose collée contre lui debout (une fois par bond)
        MANN.libre(Mdeb); Mb = bond_repere(dep, arr, PLAQ['hauteur'], 1); Mc = Mb @ arm.pose.bones['Racine'].bone.matrix_local
        PLAQ['assign'] = attribuer({k: (Mc @ rest_rel(CHAINES[k][0])).translation for k in range(8)}, [p_ for p_, _ in MANN.points_membres()],
                                   Mc.translation, (Mb.to_3x3() @ UPV).normalized(), (Mb.to_3x3() @ Vector((1, 0, 0))).normalized())
    if t < ta: MANN.libre(Mdeb); Mv = Mdeb
    else:
        a = min(1, (t - ta)/RENV); a = a*a; Mv = interp(Mdeb, Mall, a)
        tt = max(0.0, t - ta - RENV); lutte = 0.12*math.sin(tt*9)*math.exp(-tt*0.3)
        MANN.libre(Mv, epaules=(0.0, 0.0), ecart=1.25*a + lutte, jambes=0.35*a - lutte*0.5)
    ECLAB[:] = [(10.8, 0, ta + RENV, 0.3), (11.5, 0, ta + RENV + 0.1, 0.2), (0, 0, tb, 0.12)]
    if t < tb:
        coup, e = ('plaquage', t - t0) if t >= t0 else (None, 0.0)
        Mw = decalage_ramasse(e) if coup else Matrix.Identity(4)
    elif t < ta:
        coup, e = 'plaquage', t - t0; Mw = bond_repere(dep, arr, PLAQ['hauteur'], (t - tb)/PLAQ['vol'])
    else:
        coup, e = 'plaquage', t - t0; Mw = plaque_repere(Mv)
    PLAQUE_ACTIF[0] = False
    racine_fn = lambda tt_: (Matrix.Identity(4) if tt_ < tb else Matrix.Translation(arr), 'plaquage' if tt_ >= t0 else None, tt_ - t0, None)
    avancer(racine_fn, t)
    Q = animer(t, 0, coup, e, False, None)
    if SIM['poids'] >= 0.01 and t < t0 + 0.3: locomotion(Q, t, Mw, SIM['vel'], SIM['m'], SIM['poids'])
    arm.matrix_world = Mw; bpy.context.view_layer.update()
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local; centre = Mrac.translation
    pts = MANN.points_membres()
    if tb <= t < ta + 0.5:                                       # en vol : faisceau, puis chaque bras lancé vers son membre
        u = (t - tb)/PLAQ['vol']; fin = lisse((t - ta)/0.2)
        wT = 1 - lisse((u - 0.2)/0.3); wA = lisse((u - 0.3)/0.35)*(1 - fin)
        for k in range(8):
            chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
            if wT > 0.001: orienter(chn, Mrac, articulations(B, chemin_trainee(B, centre, dirv, UPV, t), LONG[k]), [wT]*8, Q)
            if wA > 0.001:
                P = pts[PLAQ['assign'][k]][0]
                orienter(chn, Mrac, articulations(B, [B.copy(), P, P + (P - B).normalized()*0.8], LONG[k]), [wA]*8, Q)
    if t >= ta:                                                  # huit bras plantés, deux par membre, dès le contact
        tt = t - ta; haut = (Mw.to_3x3() @ UPV).normalized()
        for k, i in PLAQ['assign'].items():
            P, axe = pts[i]; chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
            c_ = centre - P; l_ = axe.cross(c_.normalized() if c_.length > 1e-3 else haut); sens = 1 if (B - P).dot(l_) >= 0 else -1
            orienter(chn, Mrac, articulations(B, chemin_plante(B, P, axe, centre, haut, sens), LONG[k]), [lisse((tt - 0.01*k - 0.015*j)/0.15) for j in range(8)], Q)
    CAM = Vector((7.5, -10.5, 7.0)); viser(CAM, (8.0, 0, 1.6)); cd.angle_y = math.radians(56)
    poser(Mw, Q, CAM)
# ---------------------------------------------------------------- enlèvement par une grille du plafond, nuage d'encre
ENL = dict(signe=1.0, trainee=1.2, levee=1.8, avalee=0.4)
def suspendre(prog, tt):
    h, rentre = lisse(prog), 0.0
    if tt is not None:
        h = 1 - 0.7*lisse((tt - ENL['trainee'])/ENL['levee']); rentre = lisse((tt - ENL['trainee'] - ENL['levee'])/ENL['avalee']); h *= (1 - rentre)
    return Matrix.Translation((0, 0, 2.5*h - 2.5*rentre)) @ autour(P_ARR, 0.9*h)
GRILLE = Vector((0, 0, H))
if PLAN == 'enlevement':                                         # grille : cadre, trou noir, barreaux
    noir_ = K.mat_plain('Trou', (3, 3, 4), 0.9)
    K.cube('Trou', (4.4, 4.4, 0.06), (0, 0, H - 0.03), noir_, 0)
    for (sx, sy, x_, y_) in ((4.8, 0.3, 0, 2.25), (4.8, 0.3, 0, -2.25), (0.3, 4.8, 2.25, 0), (0.3, 4.8, -2.25, 0)):
        o = K.cube('Cadre', (sx, sy, 0.3), (x_, y_, H - 0.15), K.mat('metal_peint', (70, 72, 70)), 0.03); K.box_uv(o)
    for i in range(7):
        K.cube('Barreau', (0.1, 4.3, 0.1), (-1.8 + i*0.6, 0, H - 0.2), K.mat('metal_peint', (70, 72, 70)), 0.02)
def plan_enlevement(t):
    t0 = 0.3; ts = t0 + ENL['signe']; tt = t - ts; e = t - t0
    O = GRILLE - Vector((0, 0, 0.2))
    depart = Vector((5, 0, 3)); dessous = Vector((0, 0, 4)); haut = Vector((0, 0, H - 1.5)); dedans = Vector((0, 0, H + 3))
    T1, T2 = ENL['trainee'], ENL['trainee'] + ENL['levee']
    if tt < 0: pos, prog = depart, 0.0
    elif tt < T1: pos, prog = depart.lerp(dessous, lisse(tt/T1)), 0.0
    elif tt < T2: prog = a_coups((tt - T1)/ENL['levee']); pos = dessous.lerp(haut, prog)
    else: pos, prog = haut.lerp(dedans, lisse((tt - T2)/ENL['avalee'])), 1.0
    if tt > 0: pos = pos + Vector((0.35*math.sin(tt*4)*math.exp(-tt*0.4), 0, 0))
    lutte = lisse(tt/0.3) if tt > 0 else 0.0
    face = Vector((GRILLE.x - pos.x, GRILLE.y - pos.y, 0))
    yaw = math.atan2(face.y, face.x) if face.length > 0.3 else math.pi
    MANN.libre(Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z'), epaules=(1.6*lutte + 0.3*math.sin(tt*13)*lutte, 1.4*lutte + 0.3*math.sin(tt*11 + 1)*lutte),
               ecart=0.5*lutte, hanches=(0.5*math.sin(tt*9)*lutte, -0.5*math.sin(tt*9)*lutte))
    em = []
    for i in range(int(max(0.0, min(tt, T1))*24)):
        te = ts + i/24; pp = depart.lerp(dessous, lisse((i/24)/T1))
        if pp.z < 4.2: em.append((pp.x, pp.y, te, 0.06))
    ECLAB[:] = em + [(dessous.x, 0, ts + T1*0.8, 0.2)]
    coup = 'enlevement' if t >= t0 else None
    if coup is None: zc = 4.0
    elif tt < 0: zc = 4 - 2.8*lisse(e/ENL['signe'])
    else: zc = 1.2 + 0.5*prog + 2.5*lisse((tt - T2)/ENL['avalee'])
    Mw = Matrix.Translation(GRILLE + Vector((0, 0, zc)))
    Q = animer(t, 0, coup, e, False, None)
    if coup:
        arm.matrix_world = Mw; bpy.context.view_layer.update()
        Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local; centre = Mrac.translation
        tient = tt >= 0
        p0 = lisse(e/0.7)
        N = MANN.racine.matrix_world.translation.copy(); N.z = min(N.z, O.z - 1.3); U = (MANN.racine.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        ETIRE.clear()
        for k in range(8):
            chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
            dv = Vector((B.x - centre.x, B.y - centre.y, 0)); dv = dv.normalized() if dv.length > 1e-3 else Vector((1, 0, 0))
            pas_ = passage_grille(O, dv)
            if k not in (0, 1, 6, 7):
                chemin = par_la_grille(B, pas_, chemin_sol(pas_, dv, Vector((GRILLE.x, GRILLE.y, H - 0.25)) + dv*2.8, Vector((0, 0, -1))))
            else:                                                # s'allonge jusqu'au torse, l'enroule, puis raccourcit en le hissant
                Nf = depart if tient else N                          # direction et sens figés à la saisie (sous la grille ils ne sont plus définis)
                fv = Vector((O.x - Nf.x, O.y - Nf.y, 0)); fv = fv.normalized() if fv.length > 1e-3 else Vector((1, 0, 0))
                l_ = U.cross(fv).normalized(); sens = 1 if (pas_ - Nf).dot(l_) >= 0 else -1
                ttp = max(tt, 0.0)
                r = 1.1 + 0.4*math.exp(-ttp*0.9) - 0.04*max(0, math.sin(ttp*7))
                complet = par_la_grille(B, pas_, chemin_enroule(pas_, N, U, fv, r, {0: 0.3, 7: 0.5, 1: -0.5, 6: -0.3}[k], sens, 0.9))
                contact = longueur(complet[:17]); BL = sum(LONG[k][:NPROX]); DL = sum(LONG[k][NPROX:])
                if tient: lp = max(0.0, contact - DL) + min(contact, DL)*lisse(tt/0.4)
                else: lp = BL + max(0.0, contact - DL - BL)*lisse((e - 0.15 - 0.04*(k % 4))/(ENL['signe'] - 0.35))
                ETIRE[k] = max(1.0, min(ETIRE_MAX, lp/BL))
                chemin = complet
            poids = [poids_chaine(p0, j + 1) for j in range(8)]
            orienter(chn, Mrac, articulations(B, chemin, longueurs(k)), poids, Q)
    CAM = Vector((2.5, -9.0, 4.0)); viser(CAM, (1.2, 0, 7.4)); cd.angle_y = math.radians(62)
    poser(Mw, Q, CAM)
NUAGE = None
if PLAN == 'encre':
    import random as _r
    rg_ = _r.Random(11)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0); NUAGE = bpy.context.object; NUAGE.name = 'Nuage'
    mn = bpy.data.materials.new('Encre'); mn.use_nodes = True; nt = mn.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    pv = nt.nodes.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (0.02, 0.07, 0.065, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.5; nz.inputs['Detail'].default_value = 6.0
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.42; mr.inputs['From Max'].default_value = 0.75
    mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 1.0
    gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'                  # bord du nuage adouci
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
    mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 0.9; mu.name = 'Densite'
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(tc.outputs['Object'], gr.inputs['Vector'])
    nt.links.new(mr.outputs['Result'], m2.inputs[0]); nt.links.new(gr.outputs['Fac'], m2.inputs[1])
    nt.links.new(m2.outputs[0], mu.inputs[0]); nt.links.new(mu.outputs[0], pv.inputs['Density'])
    nt.links.new(pv.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    NUAGE.data.materials.append(mn)
    PAILLETTES = []
    mp = K.mat_plain('Paillette', (100, 255, 160), 0.4, emit=10.0)
    for i in range(150):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rg_.uniform(0.03, 0.07)); g = bpy.context.object; g.data.materials.append(mp)
        d = Vector((rg_.gauss(0, 1), rg_.gauss(0, 1), rg_.gauss(0, 0.45))).normalized()
        PAILLETTES.append((g, d, rg_.uniform(1.0, 11.0), rg_.uniform(0.3, 0.6)))
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=1.0, fill_type='NGON'); NAPPE = bpy.context.object
    mnap = bpy.data.materials.new('Nappe'); mnap.use_nodes = True; bn = mnap.node_tree.nodes['Principled BSDF']
    bn.inputs['Base Color'].default_value = (0.004, 0.012, 0.012, 1); bn.inputs['Roughness'].default_value = 0.15; bn.inputs['Alpha'].default_value = 0.85
    NAPPE.data.materials.append(mnap)
TE_ENCRE = 0.9; CENTRE_ENCRE = Vector((0.5, 0, 1.6))
def maj_encre(t):
    a = t - TE_ENCRE
    if a < 0:
        NUAGE.scale = (0.01, 0.01, 0.01); NAPPE.scale = (0.01, 0.01, 1)
        for g, d, D, dl in PAILLETTES: g.location = (0, 0, -50)
        return
    R_ = 12*(1 - math.exp(-a/0.5)); NUAGE.location = CENTRE_ENCRE + Vector((0, 0, 0.6*a)); NUAGE.scale = (R_, R_*0.85, R_*0.42)
    NUAGE.active_material.node_tree.nodes['Densite'].inputs[1].default_value = 3.0*min(1, a/0.15)
    rn = 2 + 10*(1 - math.exp(-a/0.45)); NAPPE.location = (CENTRE_ENCRE.x, 0, EAU_Z + 0.03); NAPPE.scale = (rn, rn, 1)
    for g, d, D, dl in PAILLETTES:
        dist = D*(1 - math.exp(-a/dl)); g.location = CENTRE_ENCRE + d*dist + Vector((0, 0, 0.3*a))
X_ENCRE = profil([(0, 0), (1.1, 0), (1.3, -26), (4.0, -26)], 0)
def racine_encre(t): return Matrix.Translation((X_ENCRE(t), 0, 0)), ('encre' if t >= 0.4 else None), t - 0.4, None
def plan_encre(t):
    Mw, coup, e, ch = avancer(racine_encre, t)
    Q = animer(t, 0, coup, e, False, None)
    if SIM['poids'] >= 0.01: locomotion(Q, t, Mw, SIM['vel'], SIM['m'], SIM['poids'])
    maj_encre(t)
    ECLAB[:] = [(0.5, 0, TE_ENCRE, 0.2)]
    CAM = Vector((22, -3.0, 6.0)); viser(CAM, (-1, 0, 2.5)); cd.angle_y = math.radians(50)
    poser(Mw, Q, CAM)

# ---------------------------------------------------------------- passage d'une grille, escalade (port de WitnessGestes)
TRAV = dict(a1=0.28, a2=0.72, duree=1.8)
FENTES = [-1.55, -0.93, -0.31, 0.31, 0.93, 1.55]
def dir_h(v, defaut):
    h = Vector((v.x, v.y, 0)); return h.normalized() if h.length > 0.3 else defaut
def angle_h(v): return math.atan2(v.y, v.x)
def vers_h(a): return Vector((math.cos(a), math.sin(a), 0))
def ecart_angle(a, b): return (b - a + math.pi) % (2*math.pi) - math.pi
def traversee(u, de, vers, passage, avant0, montee):
    a1, a2 = TRAV['a1'], TRAV['a2']; u = max(0.0, min(1.0, u)); a0 = dir_h(avant0, Vector((1, 0, 0)))
    serre = math.sin(math.pi*max(0.0, min(1.0, (u - a1)/(0.9 - a1)))); etire = math.sin(math.pi*max(0.0, min(1.0, (u - 0.5)/0.45)))
    if montee:
        axe = dir_h(vers - passage, a0); d = axe if axe.dot(a0) <= 0 else -axe; Q1 = Vector((passage.x, passage.y, de.z)); Q2 = Vector((passage.x, passage.y, vers.z))
        if u < a1:
            s_ = lisse(u/a1); psi = angle_h(a0) + ecart_angle(angle_h(a0), angle_h(-d))*s_
            return repere(de.lerp(Q1, s_), vers_h(psi), -UPV), 0.0, 0.0
        if u < a2: v = a_coups((u - a1)/(a2 - a1)); pos = Q1.lerp(Q2, v); th = math.pi/2*v
        else: w = lisse((u - a2)/(1 - a2)); pos = Q2.lerp(Q2 + d*1.2, w) + UPV*(0.3*math.sin(math.pi*w)); th = math.pi/2*(1 + w)
        return repere(pos, -d*math.cos(th) + UPV*math.sin(th), -d*math.sin(th) - UPV*math.cos(th)), serre, etire
    axe = dir_h(passage - de, a0); d = axe if axe.dot(a0) >= 0 else -axe; Q2 = Vector((passage.x, passage.y, de.z)); Q1 = Vector((passage.x, passage.y, vers.z))
    if u < a1:
        s_ = lisse(u/a1); psi = angle_h(a0) + ecart_angle(angle_h(a0), angle_h(d))*s_
        return repere(de.lerp(Q2, s_), vers_h(psi), UPV), 0.0, 0.0
    if u < a2: v = a_coups((u - a1)/(a2 - a1)); pos = Q2.lerp(Q1, v); th = math.pi/2*v
    else: w = lisse((u - a2)/(1 - a2)); pos = Q1.lerp(Q1 - d*1.2, w) - UPV*(0.3*math.sin(math.pi*w)); th = math.pi/2*(1 + w)
    return repere(pos, d*math.cos(th) - UPV*math.sin(th), d*math.sin(th) + UPV*math.cos(th)), serre, etire
def chemin_traversee(B, Gk, A, n, passage, dehors):
    h = (B - passage).dot(n); V = Gk.lerp(B, lisse(h/0.8)); pts = [B.copy()]
    if (V - B).length > 0.05: bezier(B, B + (V - B)*0.4, V - n*0.7, V, 6, pts)
    bezier(V, V + n*0.7, A + n*0.8, A, 8, pts); return pts + [A + dehors*2, A + dehors*4.5]
def ancres_traversee(de, vers, passage, avant0, montee):
    n = UPV if montee else -UPV
    fin, _, _ = traversee(1, de, vers, passage, avant0, montee)
    base = Vector((passage.x, passage.y, vers.z)) + n*0.05
    f_ = fin.to_3x3() @ Vector((1, 0, 0)); d = dir_h((vers - passage) if montee else (de - passage), Vector((f_.x, f_.y, 0)).normalized()); lat = Vector((-d.y, d.x, 0))
    barre, fente = Vector((0, 1, 0)), Vector((1, 0, 0)); A, R, Gs = {}, {}, {}
    for k in range(8):
        a = k*math.pi/4 + math.pi/8
        r = fin.to_3x3() @ Vector((math.cos(a), math.sin(a), 0)); r = Vector((r.x, r.y, 0)); r = r.normalized() if r.length > 1e-3 else d
        A[k] = base + d*(r.dot(d)*2.6) + lat*(r.dot(lat)*1.8); R[k] = r
        fx = r.dot(fente)*1.7; best = min(FENTES, key=lambda f: abs(f - fx))
        Gs[k] = passage + fente*best + barre*max(-1.8, min(1.8, r.dot(barre)*1.7))
    return A, R, Gs, n
def traversee_bras(Q, Mw, u, de, vers, passage, avant0, montee):
    A, R, Gs, n = ancres_traversee(de, vers, passage, avant0, montee)
    arm.matrix_world = Mw; bpy.context.view_layer.update()
    Mrac = Mw @ arm.pose.bones['Racine'].bone.matrix_local
    for k in range(8):
        chn = CHAINES[k]; B = (Mrac @ rest_rel(chn[0])).translation
        ordre = {0: 0, 7: 0, 1: 1, 6: 1, 2: 2, 5: 2, 3: 3, 4: 3}[k]
        p_ = lisse((u - 0.1 - 0.05*ordre)/0.3)*(1 - lisse((u - 0.86)/0.14))
        orienter(chn, Mrac, articulations(B, chemin_traversee(B, Gs[k], A[k], n, passage, R[k]), LONG[k]), [poids_chaine(p_, j + 1) for j in range(8)], Q)
ESC = dict(rayon=1.3, arete=0.45, V=12.0)
def escalade_duree(h): return 2*ESC['arete'] + max(0.0, h - 2*ESC['rayon'])/ESC['V']
def escalade(x, E0, n, yH):
    R, Da, V = ESC['rayon'], ESC['arete'], ESC['V']; h = yH - E0.z; Lm = max(0.0, h - 2*R); A1 = R*math.pi/2; Dm = Lm/V
    x = max(0.0, min(2*Da + Dm, x))
    if x < Da: u = x/Da; s_ = (3*u*u - 2*u**3)*A1 + (u**3 - u*u)*V*Da
    elif x < Da + Dm: s_ = A1 + V*(x - Da)
    else: u = (x - Da - Dm)/Da; s_ = A1 + Lm + (3*u*u - 2*u**3)*A1 + (u - 2*u*u + u**3)*V*Da
    if s_ < A1:
        ph = s_/R; return repere(E0 + (n*math.cos(ph) + UPV*math.sin(ph))*R, -n*math.cos(ph) + UPV*math.sin(ph), UPV*math.cos(ph) + n*math.sin(ph))
    if s_ < A1 + Lm: return repere(E0 + UPV*(R + s_ - A1), UPV, n)
    ph = min(math.pi/2, (s_ - A1 - Lm)/R); E1 = Vector((E0.x, E0.y, yH))
    return repere(E1 + (-UPV*math.cos(ph) + n*math.sin(ph))*R, UPV*math.cos(ph) + n*math.sin(ph), n*math.cos(ph) - UPV*math.sin(ph))
def coin(p, E, L, dA, dB):
    r = p - E; x, y, l = r.dot(dA), r.dot(dB), r.dot(L)
    return E + L*l + dA*max(x, 0.0) if y <= x else E + L*l + dB*max(y, 0.0)
def surface_escalade(p, E0, n, yH):
    L = n.cross(UPV)
    if p.z < (E0.z + yH)/2: return coin(p, E0, L, n, UPV)
    return coin(p, Vector((E0.x, E0.y, yH)), L, -UPV, n)
# plan « escalade » : elle traverse la salle vers le mur, roule autour de l'arête, monte le mur, roule sur le plafond
ESC_E0 = Vector((2, 6.0, 0)); ESC_N = Vector((0, -1, 0)); ESC_T0 = 1.0
ESC_D = escalade_duree(H)
def racine_escalade(t):
    pied = ESC_E0 + ESC_N*ESC['rayon']; dep = Vector((2, -1.5, 0))
    if t < ESC_T0:
        a = lisse((t - 0.25)/(ESC_T0 - 0.25)); return repere(dep.lerp(pied, a), -ESC_N, UPV), None, 0.0, None
    if t < ESC_T0 + ESC_D: return escalade(t - ESC_T0, ESC_E0, ESC_N, H), None, 0.0, None
    a = lisse((t - ESC_T0 - ESC_D)/1.0); fin = Vector((ESC_E0.x, ESC_E0.y, H)) + ESC_N*ESC['rayon']
    return repere(fin + ESC_N*(2.0*a), ESC_N, -UPV), None, 0.0, None
def plan_escalade(t):
    SURFACE[0] = lambda p_: surface_escalade(p_, ESC_E0, ESC_N, H)
    NORMALE[0] = lambda p_: UPV if p_.z < 0.05 else (-UPV if p_.z > H - 0.05 else ESC_N)
    Mw, coup, e, ch = avancer(racine_escalade, t)
    Q = animer(t, 0, None, 0.0, False, None)
    if SIM['poids'] >= 0.01: locomotion(Q, t, Mw, SIM['vel'], SIM['m'], SIM['poids'])
    CAM = Vector((-4.0, -6.5, 4.5)); viser(CAM, (2.0, 4.0, 5.4)); cd.angle_y = math.radians(74)
    poser(Mw, Q, CAM)
# plan « traversee » : montée par la grille dans la gaine, pause, redescente
TR_PAS = Vector((0, 0, H)); TR_BAS = Vector((-3.5, 0, H)); TR_HAUT = Vector((3.2, 0, H + 0.5)); TR_T1 = 0.5; TR_T2 = 3.1
TR_DE2 = traversee(1, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)[0].translation.copy()     # où la montée l'a laissée
def racine_traversee(t):
    """marche au plafond seulement (dans la gaine, bras au repos) : 'trav' coupe la marche"""
    D = TRAV['duree']
    if t < TR_T1: return repere(TR_BAS, Vector((1, 0, 0)), -UPV), None, 0.0, None
    if t < TR_T1 + D:
        u = (t - TR_T1)/D; return traversee(u, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)[0], None, 0.0, (None if u < 0.5 else 'trav')
    fin_m = traversee(1, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)[0]
    if t < TR_T2: return fin_m, None, 0.0, 'trav'
    av = fin_m.to_3x3() @ Vector((1, 0, 0))
    if t < TR_T2 + D:
        u = (t - TR_T2)/D; return traversee(u, TR_DE2, TR_BAS, TR_PAS, av, False)[0], None, 0.0, (None if u >= 0.75 else 'trav')
    return traversee(1, TR_DE2, TR_BAS, TR_PAS, av, False)[0], None, 0.0, None
def preset_traversee(t, m):
    """relais vers la marche (descente, u = 0,75) : les pieds sont là où les bras se sont agrippés"""
    D = TRAV['duree']; u = (t - TR_T2)/D
    if u >= 0.75 and not SIM.get('relais'):
        SIM['relais'] = True
        av = traversee(1, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)[0].to_3x3() @ Vector((1, 0, 0))
        A = ancres_traversee(TR_DE2, TR_BAS, TR_PAS, av, False)[0]
        m.pieds = {k: A[k].copy() for k in range(8)}; m.air = {}
def plan_traversee(t):
    SIM['preset'] = preset_traversee
    Mw, coup, e, ch = avancer(racine_traversee, t)
    D = TRAV['duree']; ECRASE['serre'] = ECRASE['etire'] = 0.0
    if TR_T1 <= t < TR_T1 + D:
        _, ECRASE['serre'], ECRASE['etire'] = traversee((t - TR_T1)/D, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)
    elif TR_T2 <= t < TR_T2 + D:
        av = traversee(1, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)[0].to_3x3() @ Vector((1, 0, 0))
        _, ECRASE['serre'], ECRASE['etire'] = traversee((t - TR_T2)/D, TR_DE2, TR_BAS, TR_PAS, av, False)
    Q = animer(t, 0, None, 0.0, False, None)
    if SIM['poids'] >= 0.01: locomotion(Q, t, Mw, SIM['vel'], SIM['m'], SIM['poids'])
    if TR_T1 <= t < TR_T1 + D: traversee_bras(Q, Mw, (t - TR_T1)/D, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)
    elif TR_T2 <= t < TR_T2 + D:
        av = traversee(1, TR_BAS, TR_HAUT, TR_PAS, Vector((1, 0, 0)), True)[0].to_3x3() @ Vector((1, 0, 0))
        traversee_bras(Q, Mw, (t - TR_T2)/D, TR_DE2, TR_BAS, TR_PAS, av, False)
    CAM = Vector((1.0, -12.0, 12.25)); viser(CAM, (0.2, 0, 12.4)); cd.angle_y = math.radians(52)
    poser(Mw, Q, CAM)

def decalage_ramasse(e):
    a = lisse(e/PLAQ['signe']); return Matrix.Translation((-0.4*a, 0, -0.3*a)) @ autour(P_CAB, 0.1*a)

ECLAB = []
def plan_attaque(t):
    nom = PLAN; t0 = T0_ATT[nom]; signe = SIGNE[nom]
    coup = nom if t >= t0 else None; e = t - t0
    T, ec = mannequins(t); ECLAB[:] = ec
    if nom == 'fouet' and 'k' not in FOUET_K:               # le bras avant le plus proche de la cible
        Mr0 = arm.pose.bones['Racine'].bone.matrix_local
        FOUET_K['k'] = min((0, 7), key=lambda k: ((Mr0 @ rest_rel(CHAINES[k][0])).translation - T).length)
    racine_fn = lambda tt: (Matrix.Identity(4), nom if tt >= t0 else None, tt - t0, None)
    avancer(racine_fn, t)
    Q = animer(t, 0, coup, e, False, None)
    Mw = decalage_geste(coup, e, signe, T)
    if SIM['poids'] >= 0.01: locomotion(Q, t, Mw, SIM['vel'], SIM['m'], SIM['poids'])
    if coup: gestes_attaque(Q, coup, e, signe, Mw, T if T is not None else Vector((9, 0, 2)))
    CAMS = {'fouet': ((4, -13.5, 5.2), (4.2, -0.5, 2.6), 50), 'balayage': ((7, -11.5, 7.5), (0, 0, 1.0), 52), 'morsure': ((2.6, -9.5, 3.8), (2.6, 0, 1.2), 46)}
    c, cib, ang = CAMS[nom]; CAM = Vector(c); viser(CAM, cib); cd.angle_y = math.radians(ang)
    poser(Mw, Q, CAM)
def plan_etrangle(t):
    """gros plan : bras levés (0,7 s), puis saisie : elle se dresse, enroule ses deux bras avant autour du cou et serre"""
    t_signe = 0.5; t_sais = t_signe + 0.7; avant = Vector((1, 0, 0))
    saisi = t >= t_sais; tt = max(0.0, t - t_sais)
    coup = 'saisie' if t >= t_signe else None; e = t - t_signe
    Mm = cabrer(tt) if saisi else Matrix.Identity(4)
    lev = lisse(tt/0.8) if saisi else 0.0
    hrp = avant*2.1 + Vector((0, 0, 3 + 0.6*lev + (0.08*math.sin(tt*7) if saisi else 0)))
    tete_bas, U = MANN.poser(hrp, -avant, tt, saisi)
    Q = animer(t, 0, coup, e, saisi, None)
    Mw = Matrix.Identity(4) @ Mm
    if saisi:
        arm.matrix_world = Mw; bpy.context.view_layer.update(); enrouler(Q, tt, tete_bas, U, 0.0, Mw)
    a = t/6.0; z = lisse((t - 1.0)/1.6)                  # plan large, puis on se rapproche de la gorge
    CAM = Vector((1.4 - 1.8*a, -10.5 + 2.5*z, 4.0 + 0.6*z)); viser(CAM, Vector((0.9, 0, 2.4)).lerp(Vector((1.4, 0, 3.9)), z))
    cd.angle_y = math.radians(56 - 14*z)
    poser(Mw, Q, CAM)
    if saisi and os.environ.get('DEBUG'):
        for k in (0, 7):
            pts = [arm.matrix_world @ pb.tail for pb in CHAINES[k]]
            log(f't={t:.2f} bras {k} : ' + ' '.join(f'({(p - tete_bas).x:+.2f},{(p - tete_bas).y:+.2f},{(p - tete_bas).z:+.2f})' for p in pts))

if PLAN == 'couloir':
    for x in range(-36, 108, 16):
        lampe((x + 4, 0, H - 0.5), 900, (0.82, 0.92, 1.0), 3.0, forme='RECTANGLE', size_y=0.5)   # néons de service
        lampe((x + 12, 0, H - 0.8), 250, (1.0, 0.2, 0.12), 1.0)                                  # voyants de secours
    torche = bpy.data.lights.new('Torche', 'SPOT'); torche.energy = 4000; torche.spot_size = math.radians(36); torche.spot_blend = 0.5; torche.color = (1.0, 0.95, 0.85)
    tob = bpy.data.objects.new('Torche', torche); sc.collection.objects.link(tob); tob.location = (96.6, -2.0, 4.2)
elif PLAN in ('plafond', 'sol') + ('fouet', 'balayage', 'devore', 'plaquage', 'enlevement', 'encre', 'escalade', 'traversee'):
    for x in range(-36, 40, 10):
        lampe((x, 4.2, H - 0.4), 700, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.5)
        lampe((x + 5, -4.2, H - 0.4), 500, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.5)
    CLE = lampe((0, -12, 8), 1600, (1.0, 0.95, 0.9), 6.0)
    CONTRE = lampe((0, 5, 6), 1100, (0.6, 0.85, 1.0), 4.0)
    for L_ in (CLE, CONTRE): L_.visible_glossy = False; L_.visible_transmission = False     # pas de grande tache blanche reflétée dans l'eau
    if PLAN == 'traversee':                             # néons de la gaine
        lampe((-4, 1.2, H + 4.8), 700, (0.85, 0.93, 1.0), 2.0, forme='RECTANGLE', size_y=0.4)
        lampe((5, 1.2, H + 4.8), 600, (0.85, 0.93, 1.0), 2.0, forme='RECTANGLE', size_y=0.4)
        lampe((1, -8, 14.5), 900, (1.0, 0.95, 0.9), 4.0, cible=(0, 0, 13.2))                  # appoint côté caméra dans la gaine
    if PLAN in ('balayage', 'encre', 'plaquage', 'escalade'):       # vue plongeante : les néons se reflètent en taches ; reflet doux d'un grand plafonnier à la place
        for o in list(sc.objects):
            if o.type == 'LIGHT' and o.data.type == 'AREA' and o.data.shape == 'RECTANGLE': o.visible_glossy = False
        lampe((0, 0, H - 0.3), 260, (0.8, 0.9, 1.0), 26.0)
    if PLAN in ('sol',) + ('fouet', 'balayage', 'devore', 'plaquage', 'enlevement', 'encre', 'escalade', 'traversee'):                                   # sol et eau prolongés côté caméra : pas de bord coupé dans le champ
        K.box_uv(K.cube('SolAvant', (LX, 16, 0.4), (CX, -14, -0.2), K.mat('tole_striee', (120, 124, 126)), 0))
elif PLAN == 'chute':
    lampe((-6, -2, H - 0.5), 1400, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.6)
    lampe((6, -2, H - 0.5), 1400, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.6)
    lampe((4, -14, 8), 1800, (1.0, 0.95, 0.9), 6.0, cible=(0, 0, 5))
    lampe((-3, 5, 6), 1500, (0.6, 0.85, 1.0), 4.0, cible=(0, 0, 5))
else:
    lampe((7, -7, 10), 2600, (1.0, 0.95, 0.9), 5.0, cible=(1, 0, 3))
    lampe((-4, 5, 8), 2200, (0.6, 0.85, 1.0), 4.0, cible=(1, 0, 3.5))
    lampe((1, 0, H - 0.5), 800, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.6)

# ---------------------------------------------------------------- eau : 30 cm (1,1 stud) dans toute la base
import numpy as np
EAU_Z = 1.1
EAU = None
if PLAN in ('sol', 'couloir') + ('fouet', 'balayage', 'devore', 'plaquage', 'enlevement', 'encre', 'escalade'):
    me_ = bpy.data.materials.new('Eau'); me_.use_nodes = True; nt = me_.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.03, 0.07, 0.075, 1); b.inputs['Roughness'].default_value = 0.03
    b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.33
    va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.32, 0.58, 0.56, 1); va.inputs['Density'].default_value = 0.15 if PLAN == 'plaquage' else 0.45
    nt.links.new(va.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 3.0
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.06
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    def nappe(nom, x0, x1, y0, y1, pas):
        nx, ny = int((x1 - x0)/pas) + 1, int((y1 - y0)/pas) + 1
        X, Y = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny))
        co = np.stack([X.ravel(), Y.ravel(), np.full(X.size, EAU_Z)], 1)
        idx = np.arange(nx*ny).reshape(ny, nx)
        faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
        me = bpy.data.meshes.new(nom); me.from_pydata(co.tolist(), [], faces.tolist()); me.materials.append(me_)
        for pl in me.polygons: pl.use_smooth = True
        ob = bpy.data.objects.new(nom, me); sc.collection.objects.link(ob)
        so = ob.modifiers.new('volume', 'SOLIDIFY'); so.thickness = EAU_Z + 0.05; so.offset = -1; so.use_even_offset = False
        return ob, X.ravel(), Y.ravel()
    if PLAN == 'sol': EAU = nappe('Eau', -40, 40, -21, 6, 0.24)
    elif PLAN in ('fouet', 'balayage', 'devore', 'plaquage', 'enlevement', 'encre', 'escalade'): EAU = nappe('Eau', -14, 20, -20, 6, 0.2)
    else:
        EAU = nappe('Eau', 40, 100, -6, 6, 0.25)
        o = K.cube('EauLoin', (120, 12, EAU_Z + 0.05), (-20, 0, (EAU_Z - 0.05)/2), me_, 0)
    # gouttes de la gerbe (trajectoires calculées, pesanteur réelle pour qu'on les voie voler)
    GOUTTES = []
    if PLAN == 'couloir':
        mg = K.mat_plain('Goutte', (205, 228, 232), 0.05, transmission=1.0)
        rg = __import__('random').Random(7)
        for i in range(70):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rg.uniform(0.05, 0.13)); g = bpy.context.object; g.data.materials.append(mg)
            a = rg.uniform(0, 2*math.pi); rad = rg.uniform(0.6, 2.2)
            GOUTTES.append((g, Vector((math.cos(a)*rad, math.sin(a)*rad, 0)), Vector((math.cos(a)*rg.uniform(2, 7), math.sin(a)*rg.uniform(2, 7), rg.uniform(6, 13))), rg.uniform(0, 0.06)))
def emetteurs(t):
    """sources d'ondes : le corps qui avance dans l'eau, les pieds qui se reposent, l'impact de la chute"""
    if PLAN in ('fouet', 'balayage', 'devore', 'plaquage', 'enlevement', 'encre', 'escalade', 'traversee'):
        return [x for x in ECLAB if x[2] <= t] + [(pp.x, pp.y, te, 0.05) for te, pp in POSES_PIEDS if t - 2.4 < te <= t and pp.z < 0.6]
    out = []; fn = racine_sol if PLAN == 'sol' else racine_couloir
    for i in range(max(0, int((t - 2.4)*24)), int(t*24) + 1):
        te = i/24
        if te > t: break
        p0 = fn(te)[0].translation; p1 = fn(te + 1/48)[0].translation
        if p0.z > 0.5: continue                            # au plafond ou en l'air : pas d'eau
        v = (p1 - p0).length*48
        if v > 2: out.append((p0.x, p0.y, te, 0.11*(v/24) + 0.012))     # amplitude proportionnelle au chemin parcouru : pas de crête qui s'accumule
    for te, pp in POSES_PIEDS:
        if t - 2.4 < te <= t and pp.z < 0.5: out.append((pp.x, pp.y, te, 0.05))
    if PLAN == 'couloir':
        tf = math.sqrt(2*H/G_JEU); ti = 3.0 + DECROCHAGE + tf
        out += [(68, 0.27, ti, 0.32), (68, 0.27, ti + 0.18, 0.16)]
    return out
def maj_eau(t):
    if EAU is None: return
    ob, X, Y = EAU; h = np.zeros_like(X)
    for ex, ey, te, amp in emetteurs(t):
        a = t - te
        if a <= 0 or a > 2.4: continue
        r = np.hypot(X - ex, Y - ey); u = r - 5.5*a; sig = 0.3 + 0.25*a
        m = np.abs(u) < 4*sig + 0.5
        if not m.any(): continue
        h[m] += amp*math.exp(-a/0.9)/(1 + 1.4*a)*np.exp(-u[m]*u[m]/(2*sig*sig))*np.cos(2*math.pi*u[m]/1.0 + (te*37.0 % 6.283)*0.35)
    co = np.stack([X, Y, EAU_Z + h], 1).ravel()
    ob.data.vertices.foreach_set('co', co); ob.data.update()
    if PLAN == 'couloir':
        tf = math.sqrt(2*H/G_JEU); ti = 3.0 + DECROCHAGE + tf
        for g, p0, v0, dl in GOUTTES:
            a = t - ti - dl
            if a < 0: g.location = (0, 0, -50); continue
            p = Vector((68, 0.27, EAU_Z)) + p0 + v0*a + Vector((0, 0, -0.5*35*a*a))
            g.location = p if p.z > EAU_Z - 0.2 else (0, 0, -50)

PLANS = {'couloir': lambda t: plan_marche(t, racine_couloir, cam_couloir), 'chute': plan_chute, 'etrangle': plan_etrangle,
         'plafond': lambda t: plan_marche(t, racine_plafond, cam_plafond), 'sol': lambda t: plan_marche(t, racine_sol, cam_sol),
         'fouet': plan_attaque, 'balayage': plan_attaque, 'devore': plan_devore, 'plaquage': plan_plaquage,
         'enlevement': plan_enlevement, 'encre': plan_encre, 'escalade': plan_escalade, 'traversee': plan_traversee}
IM = os.environ.get('IMAGES', '1-24')
if '-' in IM: i0, i1 = (int(x) for x in IM.split('-')); LISTE = range(i0, i1 + 1)
else: LISTE = [int(x) for x in IM.split('_')]
DIAG = os.environ.get('DIAG') == '1'
prec = {}
for fr in LISTE:
    t = (fr - 1)/FPS
    PLANS[PLAN](t)
    if DIAG:                                                      # pas de rendu : sauts d'une image à l'autre des articulations des bras
        bpy.context.view_layer.update()
        pires = []
        for k in range(8):
            for j in range(1, 9):
                pb = arm.pose.bones[f'Bras{k}_{j}']; q = arm.matrix_world @ pb.tail
                if (k, j) in prec: pires.append(((q - prec[(k, j)]).length, k, j))
                prec[(k, j)] = q
        if os.environ.get('DIAGK') and int(os.environ['DIAGK']) in range(8):
            kk = int(os.environ['DIAGK'])
            log(f'joints {fr} ' + ' '.join(f'({v.x:.1f},{v.y:.1f},{v.z:.1f})' for v in (arm.matrix_world @ arm.pose.bones[f'Bras{kk}_{j}'].tail for j in range(1, 9))))
        if pires:
            m = max(pires); log(f'diag {fr} t={t:.3f} saut max {m[0]:.2f} (bras {m[1]} os {m[2]}) etire {dict((k, round(v, 2)) for k, v in ETIRE.items())}')
        continue
    maj_eau(t)
    if PLAN in ('plafond', 'sol') + ('fouet', 'balayage', 'devore', 'plaquage', 'enlevement', 'encre', 'escalade', 'traversee'):                     # lumière principale et contre-jour qui suivent la créature
        c = arm.matrix_world.translation.copy(); cz = 9.0 if PLAN == 'plafond' else 2.0
        if PLAN == 'devore': c.z = 2.0; cz = 4.5
        if PLAN == 'enlevement': c = Vector((1.5, 0, 3.0)); cz = 6.5
        if PLAN == 'encre': c = Vector((2.0, 0, 1.0))
        if PLAN == 'traversee': c = Vector((0, 0, 12.0)); cz = 12.5
        if PLAN == 'escalade': c = Vector((2, 3, 6.0)); cz = 6.0
        CLE.location = c + Vector((2, -11, 6 if PLAN == 'sol' else -6)); CLE.rotation_euler = (Vector((c.x, 0, cz)) - CLE.location).to_track_quat('-Z', 'Y').to_euler()
        CONTRE.location = c + Vector((-3, 5, 4 if PLAN == 'sol' else -3)); CONTRE.rotation_euler = (Vector((c.x, 0, cz)) - CONTRE.location).to_track_quat('-Z', 'Y').to_euler()
    if PLAN == 'couloir':
        tob.rotation_euler = (arm.matrix_world.translation + Vector((0, 0.2*math.sin(t*1.5), 0.6)) - tob.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(out, f'img_{fr:04d}.png'); bpy.ops.render.render(write_still=True)
    if fr % 12 == 0: log(f'image {fr}')
log('fin')
