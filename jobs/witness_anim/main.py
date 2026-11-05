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
SIGNE = {'fouet': 0.5, 'balayage': 0.6, 'morsure': 0.35, 'saisie': 0.7, 'enlevement': 1.0, 'chute': 1.5, 'encre': 0.5}
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
def rest_rel(pb): return pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
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
def animer(t, vit, coup, e, saisie, ch):
    """port de WitnessCorps.animer : quaternion de chaque os"""
    signe = SIGNE.get(coup, 0.5); Q = {}
    for k in range(8):
        ph = phases[k]; avant = k in (0, 7, 1, 6)
        for j in range(1, 9):
            yaw = 0.05*math.sin(t*1.1 - j*0.5 + ph); pitch = 0.025*math.sin(t*0.8 + j*0.6 + ph)
            if j >= 7: pitch += 0.22 + 0.05*math.sin(t*1.4 + ph)
            if coup in ('saisie', 'enlevement') or saisie:
                if avant:
                    a = lisse(e/signe); pitch += a*(0.5 if j == 1 else (0.06 if j <= 4 else 0.12)); yaw += a*(0.2 if k <= 1 else -0.2)
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
    if coup == 'descente' and ch and ch['phase'] == 'atterrit': contraction += 0.35*math.exp(-7*ch['tau'])*math.cos(12*ch['tau'])
    Q['Manteau1'] = Euler((0.05*respi + contraction, 0, 0.02*math.sin(t*0.7)), 'XYZ').to_quaternion()
    Q['Manteau2'] = Euler((0.08*math.sin(t*1.25 + 0.5) + contraction, 0, 0.04*math.sin(t*0.6)), 'XYZ').to_quaternion()
    Q['Tete'] = Euler((0.03*math.sin(t*0.8), 0, 0), 'XYZ').to_quaternion()
    for nm in ('Racine', 'Bec', 'OeilG', 'OeilD'): Q[nm] = Quaternion()
    return Q

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
def maj_marche(m, t, Mw, vel):
    haut = haut_de(Mw); orig = Mw.translation; vel = vel - haut*vel.dot(haut); v = vel.length; ideal = {}
    for k, d in DIRS.items():
        p = Mw @ (d*MR['rayon']); p = p - haut*(p - orig).dot(haut); ideal[k] = p + vel*MR['anticipation']
        f0 = m.pieds.get(k)
        if f0 is None or (f0 - ideal[k]).length > 9 or abs((f0 - orig).dot(haut)) > 1.5: m.pieds[k] = ideal[k].copy(); m.air.pop(k, None)
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
            if (m.pieds[k] - fin).length > 0.3: m.air[k] = dict(t0=t, duree=duree, debut=m.pieds[k].copy(), fin=fin, hauteur=0.8 + v*0.025)
def pied(m, k, t, haut):
    a = m.air.get(k)
    if a: u = lisse((t - a['t0'])/a['duree']); return a['debut'].lerp(a['fin'], u) + haut*(a['hauteur']*math.sin(math.pi*u))
    return m.pieds.get(k)
def chemin_pied(B, F, centre, haut):
    dh = F - centre; dh = dh - haut*dh.dot(haut); dh = dh.normalized() if dh.length > 1e-3 else Vector((1, 0, 0))
    Fp = F + haut*0.2; pts = [B.copy()]
    bezier(B, B + (Fp - B)*0.35 + haut*0.5, Fp - dh*1.0 + haut*0.25, Fp, 10, pts); pts += [Fp + dh*1.5, Fp + dh*4]; return pts
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
EXPO = {'couloir': 0.0, 'chute': 0.0, 'etrangle': 0.0, 'plafond': 0.0, 'sol': 0.0}[PLAN]
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
    o = K.cube(nom, size, loc, mt, 0); K.box_uv(o)
for x in range(int(L0) + 6, int(L1), 8):
    for sy in (-1, 1):
        if sy == -1 and PLAN != 'couloir': continue
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
        else: maj_marche(SIM['m'], t, Mw, vel)
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
MANN = Mannequin() if PLAN == 'etrangle' else None
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
elif PLAN in ('plafond', 'sol'):
    for x in range(-36, 40, 10):
        lampe((x, 4.2, H - 0.4), 700, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.5)
        lampe((x + 5, -4.2, H - 0.4), 500, (0.85, 0.93, 1.0), 3.0, forme='RECTANGLE', size_y=0.5)
    CLE = lampe((0, -12, 8), 1600, (1.0, 0.95, 0.9), 6.0)
    CONTRE = lampe((0, 5, 6), 1100, (0.6, 0.85, 1.0), 4.0)
    for L_ in (CLE, CONTRE): L_.visible_glossy = False; L_.visible_transmission = False     # pas de grande tache blanche reflétée dans l'eau
    if PLAN == 'sol':                                   # sol et eau prolongés côté caméra : pas de bord coupé dans le champ
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
if PLAN in ('sol', 'couloir'):
    me_ = bpy.data.materials.new('Eau'); me_.use_nodes = True; nt = me_.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.03, 0.07, 0.075, 1); b.inputs['Roughness'].default_value = 0.03
    b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.33
    va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.32, 0.58, 0.56, 1); va.inputs['Density'].default_value = 0.45
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
         'plafond': lambda t: plan_marche(t, racine_plafond, cam_plafond), 'sol': lambda t: plan_marche(t, racine_sol, cam_sol)}
IM = os.environ.get('IMAGES', '1-24')
if '-' in IM: i0, i1 = (int(x) for x in IM.split('-')); LISTE = range(i0, i1 + 1)
else: LISTE = [int(x) for x in IM.split('_')]
for fr in LISTE:
    t = (fr - 1)/FPS
    PLANS[PLAN](t)
    maj_eau(t)
    if PLAN in ('plafond', 'sol'):                     # lumière principale et contre-jour qui suivent la créature
        c = arm.matrix_world.translation; cz = 9.0 if PLAN == 'plafond' else 2.0
        CLE.location = c + Vector((2, -11, 6 if PLAN == 'sol' else -6)); CLE.rotation_euler = (Vector((c.x, 0, cz)) - CLE.location).to_track_quat('-Z', 'Y').to_euler()
        CONTRE.location = c + Vector((-3, 5, 4 if PLAN == 'sol' else -3)); CONTRE.rotation_euler = (Vector((c.x, 0, cz)) - CONTRE.location).to_track_quat('-Z', 'Y').to_euler()
    if PLAN == 'couloir':
        tob.rotation_euler = (arm.matrix_world.translation + Vector((0, 0.2*math.sin(t*1.5), 0.6)) - tob.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(out, f'img_{fr:04d}.png'); bpy.ops.render.render(write_still=True)
    if fr % 12 == 0: log(f'image {fr}')
log('fin')
