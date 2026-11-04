"""NADIR-4 — mobilier et équipements, posés automatiquement dans chaque salle selon sa fonction.
Chaque objet est construit dans un repère local : origine au pied du mur (ou au centre de l'objet au sol),
+Z vers l'intérieur de la salle, +X le long du mur, Y vers le haut."""
import math, random, zlib
from nadir_kit import Frame, rot_y, rot_x, rot_z, mm, I3

WT_IN = 0.95          # épaisseur mur + habillage
# ---------------------------------------------------------------- palette
BLANC = (222, 224, 220); GRIS_C = (176, 180, 182); GRIS = (128, 132, 134); GRIS_F = (70, 74, 78); NOIR = (28, 29, 31)
ACIER = (150, 154, 156); BLEU_LAB = (96, 132, 160); VERT_M = (88, 110, 92); JAUNE = (210, 168, 36); ROUGE = (168, 40, 34)
BOIS = (122, 92, 64); BOIS_C = (164, 128, 88); CARTON = (156, 120, 78); TISSU_B = (62, 74, 98); TISSU_G = (90, 94, 92)
ECRAN_OFF = (14, 18, 22); ECRAN_ON = (60, 140, 190)

# ================================================================ objets
def armoire(f, w=1.8, d=1.6, h=6.2, col=GRIS, n_tiroirs=4):
    f.box((0, h/2, d/2), (w, h, d), 'Metal', col, name='Armoire')
    for i in range(n_tiroirs):
        y = h*(i + 0.5)/n_tiroirs
        f.box((0, y, d + 0.03), (w - 0.25, h/n_tiroirs - 0.18, 0.06), 'Metal', tuple(min(255, c + 12) for c in col), name='Tiroir', cc=False)
        f.box((0, y + h/n_tiroirs*0.25, d + 0.1), (0.6, 0.12, 0.1), 'Metal', ACIER, name='Poignee', cc=False)

def casiers(f, n=4, col=(84, 104, 126), rng=None):
    w = 1.7; h = 6.6; d = 1.7
    for i in range(n):
        x = (i - (n - 1)/2)*w
        f.box((x, h/2, d/2), (w - 0.06, h, d), 'Metal', col, name='Casier')
        open_ = rng and rng.random() < 0.25
        if open_:
            f.box((x + w/2 - 0.05, h/2 + 0.2, d + w/2 - 0.1), (0.06, h - 0.6, w - 0.2), 'Metal', col, name='PorteCasier', R=rot_y(0.0))
            f.box((x, h*0.7, d*0.5), (w - 0.4, 0.08, d - 0.3), 'Metal', GRIS, name='Tablette', cc=False)
            f.box((x, h*0.35, d*0.6), (w - 0.6, 2.4, 0.5), 'Fabric', TISSU_G, name='Vetement', cc=False)
        else:
            f.box((x, h/2 + 0.2, d + 0.03), (w - 0.3, h - 0.6, 0.06), 'Metal', tuple(min(255, c + 14) for c in col), name='PorteCasier', cc=False)
            for k in range(4): f.box((x, h - 0.9 - k*0.3, d + 0.07), (w - 0.8, 0.08, 0.04), 'Metal', NOIR, name='Aeration', cc=False)
            f.box((x + w/2 - 0.45, h*0.5, d + 0.1), (0.12, 0.6, 0.12), 'Metal', ACIER, name='Poignee', cc=False)
    f.box((0, 0.3, d/2), (n*w, 0.6, d - 0.1), 'Metal', NOIR, name='Socle')

def etagere(f, w=6.0, d=2.0, h=7.0, n=4, rng=None, contenu='mixte'):
    rng = rng or random.Random(0)
    for x in (-w/2 + 0.12, w/2 - 0.12):
        for z in (0.12, d - 0.12): f.box((x, h/2, z), (0.2, h, 0.2), 'Metal', (60, 92, 140), name='Montant')
    for i in range(n):
        y = 0.4 + i*(h - 0.6)/(n - 1) if n > 1 else 0.5
        f.box((0, y, d/2), (w, 0.12, d), 'Metal', ACIER, name='Rayon')
        if i == n - 1 and n > 1: continue
        x = -w/2 + 0.35
        while x < w/2 - 0.6:
            k = rng.random()
            if contenu in ('mixte', 'cartons') and k < 0.45:
                bw = rng.uniform(0.9, 1.8); bh = rng.uniform(0.7, 1.3)
                if x + bw > w/2 - 0.3: break
                f.box((x + bw/2, y + 0.06 + bh/2, d/2 + rng.uniform(-0.15, 0.15)), (bw, bh, d - 0.3), 'Plastic', CARTON, name='Carton', R=rot_y(rng.uniform(-0.08, 0.08)))
                x += bw + 0.12
            elif contenu in ('mixte', 'bacs') and k < 0.7:
                bw = 1.4; f.box((x + bw/2, y + 0.06 + 0.45, d/2), (bw, 0.9, d - 0.25), 'Plastic', rng.choice([(40, 90, 160), (190, 60, 40), (70, 70, 74), (200, 170, 40)]), name='Bac'); x += bw + 0.1
            elif contenu in ('mixte', 'flacons', 'labo'):
                for j in range(rng.randint(2, 5)):
                    hh = rng.uniform(0.4, 0.9)
                    f.cyl((x + 0.2 + j*0.32, y + 0.06 + hh/2, d/2 + rng.uniform(-0.4, 0.4)), hh, 0.26, 'y', 'Glass' if rng.random() < 0.5 else 'Plastic',
                          rng.choice([(200, 210, 220), (150, 90, 40), (60, 120, 70), (220, 220, 210)]), name='Flacon', cc=False, tr=0.3 if rng.random() < 0.5 else 0)
                x += 2.0
            else:
                x += 0.8

def bureau(f, w=5.0, d=2.6, rng=None, ecran=True, papiers=True):
    rng = rng or random.Random(0); h = 2.6
    f.box((0, h - 0.08, d/2), (w, 0.16, d), 'WoodPlanks', BOIS_C, name='Plateau')
    f.box((w/2 - 0.9, (h - 0.16)/2, d/2), (1.6, h - 0.16, d - 0.2), 'Metal', GRIS, name='Caisson')
    for i in range(3): f.box((w/2 - 0.9, 0.4 + i*0.75, d - 0.08), (1.4, 0.6, 0.06), 'Metal', GRIS_C, name='Tiroir', cc=False)
    f.box((-w/2 + 0.12, (h - 0.16)/2, d/2), (0.16, h - 0.16, d - 0.2), 'Metal', GRIS, name='Pied')
    f.box((0, 1.5, 0.3), (w - 0.4, 1.6, 0.08), 'Metal', GRIS, name='Voile')
    if ecran:
        ff = f.sub((-0.4 + rng.uniform(-0.3, 0.3), h, 0.7), rng.uniform(-0.2, 0.2))
        ff.box((0, 0.05, 0), (0.9, 0.1, 0.6), 'Plastic', NOIR, name='PiedEcran'); ff.box((0, 0.5, 0), (0.15, 0.9, 0.15), 'Plastic', NOIR, name='PiedEcran')
        ff.box((0, 1.25, 0.05), (2.4, 1.45, 0.14), 'Plastic', NOIR, name='Ecran')
        ff.box((0, 1.25, 0.13), (2.2, 1.25, 0.02), 'SmoothPlastic', ECRAN_OFF, name='Dalle', cc=False, tags=['Ecran'])
        f.box((-0.4, h + 0.04, 1.6), (1.9, 0.08, 0.6), 'Plastic', (40, 40, 42), name='Clavier', cc=False)
        f.box((1.0, h + 0.05, 1.6), (0.3, 0.1, 0.45), 'Plastic', (40, 40, 42), name='Souris', cc=False)
    if papiers:
        for i in range(rng.randint(1, 4)):
            f.box((rng.uniform(-w/2 + 0.7, w/2 - 0.7), h + 0.01 + i*0.01, rng.uniform(0.8, d - 0.4)), (0.85, 0.02, 1.1), 'SmoothPlastic', (236, 234, 226),
                  name='Feuille', R=rot_y(rng.uniform(-0.6, 0.6)), cc=False, shadow=False)
    if rng.random() < 0.6: f.cyl((w/2 - 0.6, h + 0.25, d - 0.6), 0.5, 0.36, 'y', 'SmoothPlastic', rng.choice([(200, 200, 196), (150, 40, 40), (40, 70, 120)]), name='Tasse', cc=False)
    chaise(f.sub((rng.uniform(-0.5, 0.5), 0, d + 1.0), math.pi + rng.uniform(-0.5, 0.5)), renversee=rng.random() < 0.15, rng=rng)

def chaise(f, renversee=False, rng=None, col=TISSU_B):
    if renversee: f = f.sub((0, 0.75, 0), R=rot_z(math.pi/2*0.98))
    f.box((0, 1.75, 0), (1.6, 0.3, 1.6), 'Fabric', col, name='Assise')
    f.box((0, 3.0, -0.75), (1.5, 2.1, 0.25), 'Fabric', col, name='Dossier')
    f.cyl((0, 1.0, 0), 1.3, 0.22, 'y', 'Metal', ACIER, name='Verin', cc=False)
    for a in range(5):
        t = a*2*math.pi/5; f.box((math.sin(t)*0.55, 0.3, math.cos(t)*0.55), (0.18, 0.15, 1.1), 'Plastic', NOIR, name='Pietement', R=rot_y(t), cc=False)

def chaise_simple(f, col=(70, 90, 120)):
    f.box((0, 1.75, 0), (1.5, 0.15, 1.5), 'Plastic', col, name='Assise')
    f.box((0, 2.8, -0.68), (1.5, 1.4, 0.12), 'Plastic', col, name='Dossier')
    for x in (-0.65, 0.65):
        for z in (-0.65, 0.65): f.box((x, 0.85, z), (0.12, 1.7, 0.12), 'Metal', ACIER, name='Pied', cc=False)

def table(f, w=6.0, d=3.0, h=2.6, col=(196, 196, 190), mat='SmoothPlastic', chaises=0, rng=None, objets=True):
    rng = rng or random.Random(0)
    f.box((0, h - 0.08, 0), (w, 0.16, d), mat, col, name='Plateau')
    for x in (-w/2 + 0.3, w/2 - 0.3):
        for z in (-d/2 + 0.3, d/2 - 0.3): f.box((x, (h - 0.16)/2, z), (0.2, h - 0.16, 0.2), 'Metal', GRIS, name='Pied')
    n = chaises
    for i in range(n):
        side = 1 if i % 2 == 0 else -1; k = i//2; m = (n + 1)//2
        x = (k - (m - 1)/2)*(w/max(m, 1))
        if rng.random() < 0.12: chaise_simple(f.sub((x + 0.8, 0, side*(d/2 + 1.8)), R=rot_z(math.pi/2*0.97)))
        else: chaise_simple(f.sub((x + rng.uniform(-0.3, 0.3), 0, side*(d/2 + 0.9 + rng.uniform(0, 0.6))), (0 if side < 0 else math.pi) + rng.uniform(-0.3, 0.3)))
    if objets:
        for i in range(rng.randint(0, 3)):
            f.box((rng.uniform(-w/2 + 0.6, w/2 - 0.6), h + 0.01, rng.uniform(-d/2 + 0.5, d/2 - 0.5)), (0.85, 0.02, 1.1), 'SmoothPlastic', (236, 234, 226), name='Feuille', R=rot_y(rng.uniform(0, 3)), cc=False, shadow=False)
        if rng.random() < 0.5: f.cyl((rng.uniform(-w/3, w/3), h + 0.25, rng.uniform(-d/3, d/3)), 0.5, 0.36, 'y', 'SmoothPlastic', (210, 210, 205), name='Tasse', cc=False)

def paillasse(f, w=8.0, d=2.8, rng=None, evier=True):
    rng = rng or random.Random(0); h = 3.0
    f.box((0, (h - 0.2)/2, d/2), (w, h - 0.2, d - 0.1), 'SmoothPlastic', (218, 220, 216), name='Meuble')
    for i in range(int(w/2)):
        x = -w/2 + 1 + i*2
        f.box((x, (h - 0.2)/2, d - 0.03), (1.85, h - 0.6, 0.06), 'SmoothPlastic', (206, 210, 208), name='PorteMeuble', cc=False)
        f.box((x + 0.6, h - 0.8, d + 0.02), (0.5, 0.1, 0.1), 'Metal', ACIER, name='Poignee', cc=False)
    f.box((0, h - 0.1, d/2), (w + 0.1, 0.2, d + 0.1), 'SmoothPlastic', (34, 36, 38), name='PlanDeTravail')
    # étagère à réactifs et prises
    f.box((0, h + 2.6, 0.45), (w - 0.4, 0.12, 0.8), 'Metal', ACIER, name='EtagereReactifs')
    for x in (-w/2 + 0.4, w/2 - 0.4): f.box((x, h + 1.4, 0.2), (0.12, 2.6, 0.12), 'Metal', ACIER, name='Montant')
    f.box((0, h + 0.6, 0.08), (w - 0.6, 0.6, 0.16), 'Metal', GRIS_C, name='Goulotte')
    for j in range(int(w/1.6)):
        f.box((-w/2 + 0.9 + j*1.6, h + 0.6, 0.18), (0.5, 0.4, 0.05), 'Plastic', (230, 230, 226), name='Prise', cc=False)
    for j in range(rng.randint(3, 8)):
        hh = rng.uniform(0.5, 1.0)
        f.cyl((-w/2 + 0.7 + j*(w - 1.4)/8, h + 2.66 + hh/2, 0.45), hh, 0.34, 'y', rng.choice(['Glass', 'Plastic']), rng.choice([(200, 120, 40), (210, 214, 218), (90, 140, 80), (120, 40, 40)]), name='Flacon', cc=False, tr=0.35)
    if evier:
        x = w/2 - 1.6
        f.box((x, h - 0.18, d/2 + 0.1), (1.8, 0.1, 1.5), 'Metal', (40, 42, 44), name='Evier', cc=False)
        f.pipe((x, h, 0.4), (x, h + 1.3, 0.4), 0.16, 'Metal', ACIER, name='Robinet', cc=False); f.pipe((x, h + 1.3, 0.4), (x, h + 1.2, 1.1), 0.14, 'Metal', ACIER, name='Robinet', cc=False)
    # verrerie, microscope, carnets
    for j in range(rng.randint(2, 6)):
        x = rng.uniform(-w/2 + 0.6, w/2 - 2.8); z = rng.uniform(0.8, d - 0.6); hh = rng.uniform(0.5, 1.1)
        if rng.random() < 0.2:
            f.cyl((x, h + 0.1, z), 0.24 + 0 * hh, 0.36, 'y', 'Glass', (200, 220, 220), name='BecherCouche', cc=False, tr=0.4)
            f.cyl((x, h + 0.13, z + 0.5), 0.6, 0.36, 'x', 'Glass', (200, 220, 220), name='BecherRenverse', cc=False, tr=0.45)
        else:
            f.cyl((x, h + hh/2, z), hh, rng.uniform(0.35, 0.6), 'y', 'Glass', rng.choice([(190, 220, 220), (170, 220, 150), (230, 200, 130)]), name='Becher', cc=False, tr=0.45)
    if rng.random() < 0.6:
        m = f.sub((rng.uniform(-w/2 + 1, 0), h, 1.3), rng.uniform(-0.4, 0.4))
        m.box((0, 0.12, 0), (1.0, 0.24, 1.2), 'Plastic', (230, 230, 226), name='Microscope'); m.box((0, 0.9, -0.35), (0.3, 1.4, 0.3), 'Plastic', (230, 230, 226), name='Microscope')
        m.cyl((0, 1.5, 0.05), 0.9, 0.28, (0, 0.6, 0.8), 'Plastic', NOIR, name='Oculaire', cc=False); m.box((0, 0.55, 0.1), (0.8, 0.08, 0.7), 'Plastic', NOIR, name='Platine', cc=False)
    if rng.random() < 0.5:
        f.box((rng.uniform(-w/2 + 1, w/2 - 3), h + 0.04, d - 0.7), (1.0, 0.08, 1.3), 'SmoothPlastic', (40, 60, 110), name='Carnet', R=rot_y(rng.uniform(-0.5, 0.5)), cc=False)

def hotte(f, w=5.0, d=3.0):
    h = 3.0
    f.box((0, (h - 0.2)/2, d/2), (w, h - 0.2, d - 0.1), 'SmoothPlastic', (218, 220, 216), name='Meuble')
    f.box((0, h - 0.1, d/2), (w, 0.2, d), 'SmoothPlastic', (34, 36, 38), name='PlanDeTravail')
    for x in (-w/2 + 0.2, w/2 - 0.2): f.box((x, h + 2.4, d/2), (0.4, 4.8, d), 'SmoothPlastic', (226, 228, 224), name='Joue')
    f.box((0, h + 2.4, 0.15), (w, 4.8, 0.3), 'SmoothPlastic', (226, 228, 224), name='Fond')
    f.box((0, h + 5.4, d/2), (w, 1.2, d), 'SmoothPlastic', (226, 228, 224), name='Chapeau')
    it = f.box((0, h + 3.3, d - 0.15), (w - 0.4, 2.8, 0.08), 'Glass', (200, 225, 230), name='Vitre'); it['t'] = 0.6
    f.box((0, h + 4.75, d - 0.05), (w - 0.4, 0.3, 0.2), 'Metal', ACIER, name='Traverse')
    f.cyl((0, h + 7.5, 1.0), 3.4, 1.4, 'y', 'Metal', ACIER, name='Extraction')
    f.box((0, h + 4.7, d*0.6), (w - 0.8, 0.12, 0.4), 'Neon', (230, 236, 255), name='LampeHotte', cc=False, shadow=False, tags=['LumiereNormale'])

def bocaux(f, w=6.0, d=1.8, h=7.0, rng=None):
    rng = rng or random.Random(0)
    f.box((0, h/2, 0.1), (w, h, 0.2), 'Metal', GRIS_F, name='Fond')
    for i in range(4):
        y = 0.3 + i*1.7
        f.box((0, y, d/2), (w, 0.12, d), 'Metal', ACIER, name='Rayon')
        if i == 3: continue
        for j in range(int(w/1.1)):
            if rng.random() < 0.15: continue
            hh = rng.uniform(0.8, 1.35); x = -w/2 + 0.6 + j*1.1
            jar = f.cyl((x, y + 0.06 + hh/2, d/2), hh, 0.85, 'y', 'Glass', (190, 210, 180), name='Bocal', cc=False); jar['t'] = 0.55
            f.cyl((x, y + 0.06 + hh*0.42, d/2), hh*0.8, 0.78, 'y', 'SmoothPlastic', rng.choice([(170, 190, 120), (200, 190, 130), (150, 180, 160)]), name='Formol', cc=False, tr=0.55)
            sp = rng.random()
            if sp < 0.5: f.ball((x, y + 0.06 + hh*0.4, d/2), hh*0.45, 'SmoothPlastic', rng.choice([(220, 200, 190), (200, 170, 150), (230, 220, 210)]), name='Specimen', cc=False)
            else:
                for t in range(3): f.cyl((x + (t - 1)*0.12, y + 0.06 + hh*0.4, d/2), hh*0.6, 0.1, (math.sin(t), 1, 0.3), 'SmoothPlastic', (220, 190, 180), name='Tentacule', cc=False)
            f.cyl((x, y + 0.08 + hh, d/2), 0.12, 0.9, 'y', 'Metal', (60, 60, 60), name='Couvercle', cc=False)

def aquarium(f, w=8.0, d=3.0, h=6.5, rng=None, brise=False):
    rng = rng or random.Random(0)
    f.box((0, 1.4, d/2), (w, 2.8, d), 'Metal', GRIS_F, name='Support')
    gl = f.box((0, 2.8 + (h - 2.8)/2, d/2), (w, h - 2.8, d), 'Glass', (170, 210, 220), name='Bac'); gl['t'] = 0.65
    if not brise:
        it = f.box((0, 2.8 + (h - 3.4)/2, d/2), (w - 0.3, h - 3.4, d - 0.3), 'Glass', (60, 140, 150), name='Eau', cc=False); it['t'] = 0.45
    for i in range(4): f.box((rng.uniform(-w/2 + 0.8, w/2 - 0.8), 3.1, d/2 + rng.uniform(-0.6, 0.6)), (rng.uniform(0.6, 1.4), rng.uniform(0.4, 0.9), rng.uniform(0.6, 1.2)), 'Rock', (80, 84, 80), name='Pierre', cc=False)
    f.box((0, h + 0.15, d/2), (w + 0.1, 0.3, d + 0.1), 'Metal', GRIS_F, name='Couvercle')
    f.box((0, h - 0.05, d/2), (w - 0.6, 0.1, 0.5), 'Neon', (90, 220, 210), name='Rampe', cc=False, shadow=False)
    f.light((0, h - 0.8, d/2), 'PointLight', (90, 220, 210), 0.7, 10, tags=['LumiereSecours'])

def lit_superpose(f, rng=None):
    rng = rng or random.Random(0); L, d = 7.0, 3.2
    for x in (-L/2 + 0.15, L/2 - 0.15):
        for z in (0.15, d - 0.15): f.box((x, 3.3, z), (0.25, 6.6, 0.25), 'Metal', GRIS, name='Montant')
    for y in (1.3, 4.8):
        f.box((0, y, d/2), (L, 0.25, d), 'Metal', GRIS, name='Sommier')
        f.box((0, y + 0.45, d/2), (L - 0.3, 0.6, d - 0.2), 'Fabric', (196, 196, 190), name='Matelas')
        f.box((-L/2 + 1.0, y + 0.95, d/2), (1.3, 0.4, d - 0.6), 'Fabric', (220, 220, 214), name='Oreiller')
        col = rng.choice([(70, 86, 110), (110, 70, 60), (80, 96, 80), (90, 90, 96)])
        f.box((0.9 + rng.uniform(-0.3, 0.3), y + 0.82, d/2 + rng.uniform(-0.1, 0.3)), (L*0.62, 0.22, d - 0.1), 'Fabric', col, name='Couverture', R=rot_y(rng.uniform(-0.12, 0.12)), cc=False)
    f.box((0, 6.0, d - 0.1), (L, 0.15, 0.15), 'Metal', GRIS, name='Garde')
    for i in range(5): f.box((L/2 - 0.5, 1.6 + i*0.8, d + 0.05), (0.7, 0.12, 0.12), 'Metal', ACIER, name='Echelle')

def lit_hopital(f, rng=None):
    L, w = 7.0, 3.4
    f.box((0, 2.2, L/2), (w, 0.3, L), 'Metal', (210, 212, 210), name='Sommier')
    f.box((0, 2.65, L/2), (w - 0.2, 0.6, L - 0.3), 'Fabric', (232, 234, 232), name='Matelas')
    f.box((0, 3.2, 1.0), (w - 0.8, 0.4, 1.2), 'Fabric', (240, 240, 238), name='Oreiller')
    f.box((0, 3.3, 0.1), (w, 2.2, 0.2), 'Metal', (180, 186, 190), name='TeteDeLit')
    for x in (-w/2 + 0.2, w/2 - 0.2):
        for z in (0.4, L - 0.4): f.cyl((x, 1.0, z), 2.0, 0.2, 'y', 'Metal', ACIER, name='Pied', cc=False)
    f.box((w/2 + 1.6, 0.05, 1.2), (1.4, 0.1, 1.4), 'Metal', ACIER, name='PiedPerfusion', cc=False)
    f.cyl((w/2 + 1.6, 3.5, 1.2), 7.0, 0.12, 'y', 'Metal', ACIER, name='PiedPerfusion', cc=False)
    f.box((w/2 + 1.6, 6.3, 1.2), (0.6, 1.0, 0.3), 'Glass', (230, 236, 236), name='Poche', cc=False, tr=0.4)
    f.box((-w/2 - 1.5, 3.6, 0.8), (1.6, 1.4, 0.3), 'Plastic', NOIR, name='Moniteur')
    f.box((-w/2 - 1.5, 3.6, 0.97), (1.4, 1.1, 0.03), 'SmoothPlastic', ECRAN_OFF, name='Dalle', cc=False, tags=['Ecran'])
    f.cyl((-w/2 - 1.5, 1.4, 0.8), 2.8, 0.2, 'y', 'Metal', ACIER, name='Pied', cc=False)

def rack_serveur(f, rng=None):
    rng = rng or random.Random(0); w, d, h = 2.4, 3.6, 7.6
    f.box((0, h/2, d/2), (w, h, d), 'Metal', (30, 32, 34), name='Baie')
    f.box((0, h/2, d + 0.03), (w - 0.2, h - 0.4, 0.06), 'Metal', (44, 46, 48), name='PorteGrillagee', cc=False)
    for i in range(14):
        y = 0.7 + i*0.48
        f.box((0, y, d + 0.07), (w - 0.5, 0.32, 0.03), 'Metal', (60, 62, 64), name='Serveur', cc=False)
        for j in range(3):
            if rng.random() < 0.55:
                f.box((-0.8 + j*0.18, y, d + 0.1), (0.07, 0.07, 0.02), 'Neon', rng.choice([(60, 255, 120), (255, 170, 40), (60, 160, 255)]), name='Diode', cc=False, shadow=False)

def console(f, w=6.0, d=3.0, rng=None, ecrans=2):
    rng = rng or random.Random(0)
    f.box((0, 1.4, d/2 + 0.2), (w, 2.8, d - 0.4), 'Metal', (64, 68, 72), name='Pupitre')
    f.box((0, 3.0, d - 0.65), (w, 0.3, 1.4), 'Metal', (54, 58, 62), name='Tablette', R=rot_x(-0.35))
    for i in range(int(w*2)):
        if rng.random() < 0.6:
            f.box((-w/2 + 0.4 + i*0.5, 3.17, d - 0.7 + rng.uniform(-0.3, 0.3)), (0.16, 0.06, 0.16), 'Neon' if rng.random() < 0.2 else 'Plastic',
                  rng.choice([(220, 50, 40), (60, 200, 90), (230, 180, 40), (200, 200, 200)]), name='Bouton', cc=False, shadow=False)
    for i in range(ecrans):
        x = (i - (ecrans - 1)/2)*(w/ecrans)
        f.box((x, 4.4, 0.5), (w/ecrans - 0.3, 2.0, 0.3), 'Plastic', NOIR, name='Ecran')
        f.box((x, 4.4, 0.67), (w/ecrans - 0.5, 1.8, 0.03), 'SmoothPlastic', ECRAN_OFF, name='Dalle', cc=False, tags=['Ecran'])
    chaise(f.sub((rng.uniform(-1, 1), 0, d + 1.4), math.pi + rng.uniform(-0.6, 0.6)), rng=rng, col=(40, 44, 50))

def armoire_elec(f, w=3.0, d=1.6, h=7.0, rng=None, ouverte=False):
    f.box((0, h/2, d/2), (w, h, d), 'Metal', (150, 156, 150), name='ArmoireElec')
    if ouverte:
        f.box((w/2 + w/2 - 0.1, h/2, d + w/2 - 0.2), (0.08, h - 0.4, w - 0.2), 'Metal', (150, 156, 150), name='Porte', R=rot_y(0))
        for i in range(6):
            for j in range(5): f.box((-w/2 + 0.5 + j*0.5, 1.4 + i*0.9, d - 0.1), (0.3, 0.6, 0.15), 'Plastic', (30, 30, 30), name='Disjoncteur', cc=False)
    else:
        f.box((0, h/2, d + 0.03), (w - 0.2, h - 0.3, 0.06), 'Metal', (160, 166, 160), name='Porte', cc=False)
        f.box((w/2 - 0.4, h/2, d + 0.12), (0.12, 0.8, 0.12), 'Metal', NOIR, name='Poignee', cc=False)
    f.text((0, h - 1.4, d + 0.08), (1.2, 1.0, 0.04), '⚡', txtcol=(20, 20, 20), bg=(230, 190, 30), name='Danger', cc=False)

def etabli(f, w=7.0, d=3.0, rng=None):
    rng = rng or random.Random(0); h = 3.0
    f.box((0, h - 0.15, d/2), (w, 0.3, d), 'WoodPlanks', BOIS, name='Plateau')
    for x in (-w/2 + 0.2, w/2 - 0.2):
        for z in (0.2, d - 0.2): f.box((x, (h - 0.3)/2, z), (0.25, h - 0.3, 0.25), 'Metal', (60, 90, 130), name='Pied')
    f.box((0, 0.6, d/2), (w - 0.4, 0.15, d - 0.4), 'Metal', (60, 90, 130), name='Tablette')
    f.box((0, h + 3.0, 0.1), (w, 4.0, 0.2), 'WoodPlanks', (150, 120, 84), name='PanneauOutils')
    for i in range(int(w*1.3)):
        x = -w/2 + 0.5 + i*0.75
        if rng.random() < 0.7: f.box((x, h + rng.uniform(1.8, 4.2), 0.3), (0.15, rng.uniform(0.8, 1.5), 0.1), 'Metal', rng.choice([ACIER, ROUGE, (40, 40, 40), JAUNE]), name='Outil', cc=False, R=rot_z(rng.uniform(-0.3, 0.3)))
    f.box((w/2 - 1.0, h + 0.4, d - 0.5), (0.8, 0.8, 1.0), 'Metal', (60, 90, 130), name='Etau')
    for i in range(rng.randint(1, 4)): f.box((rng.uniform(-w/2 + 0.6, w/2 - 1.8), h + 0.12, rng.uniform(0.6, d - 0.6)), (rng.uniform(0.4, 1.2), 0.2, 0.25), 'Metal', ACIER, name='Piece', R=rot_y(rng.uniform(0, 3)), cc=False)

def cuve(f, diam=6.0, h=10.0, col=(150, 156, 150)):
    f.cyl((0, h/2, 0), h, diam, 'y', 'Metal', col, name='Cuve')
    for y in (1.0, h/2, h - 1.0): f.cyl((0, y, 0), 0.4, diam + 0.25, 'y', 'Metal', GRIS_F, name='Cerclage')
    f.cyl((0, h + 0.3, 0), 0.6, diam*0.6, 'y', 'Metal', GRIS_F, name='Trappe')
    f.pipe((diam/2, 2.0, 0), (diam/2 + 2.0, 2.0, 0), 0.8, 'Metal', (120, 70, 50), name='Tuyau')
    f.cyl((diam/2 + 1.0, 2.0, 0.7), 0.15, 1.2, 'z', 'Metal', ROUGE, name='Vanne')
    f.box((diam/2 + 0.2, h*0.6, 0), (0.1, h*0.5, 0.3), 'Glass', (180, 200, 200), name='Niveau', cc=False, tr=0.3)

def pompe(f, rng=None):
    f.box((0, 0.5, 0), (5.0, 1.0, 2.6), 'Metal', (60, 64, 60), name='Socle')
    f.cyl((-0.8, 2.0, 0), 2.8, 2.0, 'x', 'Metal', (40, 90, 140), name='Moteur')
    f.cyl((1.4, 2.0, 0), 1.6, 2.6, 'x', 'Metal', (40, 90, 140), name='Volute')
    f.pipe((1.4, 3.2, 0), (1.4, 7.5, 0), 0.9, 'Metal', ACIER, name='Refoulement')
    f.pipe((2.4, 2.0, 0), (4.0, 2.0, 0), 0.9, 'Metal', ACIER, name='Aspiration')
    f.cyl((1.4, 5.4, 0.7), 0.2, 1.4, 'z', 'Metal', ROUGE, name='Volant')
    f.box((-1.0, 3.3, 1.05), (0.7, 0.7, 0.2), 'Metal', NOIR, name='Manometre'); f.cyl((-1.0, 3.3, 1.2), 0.1, 0.55, 'z', 'SmoothPlastic', (230, 230, 226), name='Cadran', cc=False)

def turbine(f, L=16, diam=7):
    f.box((0, 0.6, 0), (L + 2, 1.2, diam + 1), 'Metal', (60, 64, 60), name='Socle')
    f.cyl((0, diam/2 + 1.2, 0), L, diam, 'x', 'Metal', (150, 110, 40), name='Carter')
    for x in (-L/2 + 1, 0, L/2 - 1): f.cyl((x, diam/2 + 1.2, 0), 0.6, diam + 0.5, 'x', 'Metal', GRIS_F, name='Bride')
    f.cyl((L/2 + 1.5, diam/2 + 1.2, 0), 3.0, diam*0.7, 'x', 'Metal', (60, 90, 130), name='Alternateur')
    f.pipe((-L/2 + 2, diam + 1.2, 0), (-L/2 + 2, diam + 7, 0), 1.6, 'Metal', ACIER, name='Vapeur')

def transformateur(f, rng=None):
    f.box((0, 0.3, 0), (6.4, 0.6, 4.4), 'Concrete', (110, 110, 106), name='Dalle')
    f.box((0, 3.4, 0), (4.6, 5.6, 2.8), 'Metal', (96, 110, 96), name='Transformateur')
    for i in range(9): f.box((-2.0 + i*0.5, 3.0, 1.6), (0.12, 4.4, 0.5), 'Metal', (86, 100, 86), name='Ailette', cc=False)
    for i in range(3): f.cyl((-1.4 + i*1.4, 6.9, 0), 1.6, 0.6, 'y', 'Plastic', (150, 90, 60), name='Isolateur')
    f.text((0, 4.0, -1.45), (1.6, 1.2, 0.05), 'DANGER\n11 kV', txtcol=(20, 20, 20), bg=(230, 190, 30), face='Back', name='Danger', cc=False)
    for x in (-3.4, 3.4): f.box((x, 2.2, 0), (0.15, 4.4, 4.6), 'Metal', JAUNE, name='Garde', cc=False, tr=0.0)

def armoire_vitree(f, w=3.0, d=1.6, h=7.0, rng=None):
    rng = rng or random.Random(0)
    f.box((0, h/2, d/2), (w, h, d), 'Metal', (226, 228, 226), name='ArmoireVitree')
    v = f.box((0, h*0.62, d + 0.03), (w - 0.3, h*0.6, 0.05), 'Glass', (210, 225, 230), name='Vitre', cc=False); v['t'] = 0.6
    for i in range(3):
        y = h*0.4 + i*1.4; f.box((0, y, d/2), (w - 0.3, 0.08, d - 0.2), 'Glass', (220, 230, 230), name='Rayon', cc=False, tr=0.4)
        for j in range(rng.randint(2, 6)):
            f.box((-w/2 + 0.4 + j*0.45, y + 0.35, d/2), (0.3, 0.6, 0.4), 'Plastic', rng.choice([(230, 230, 226), (200, 60, 50), (60, 100, 170)]), name='Boite', cc=False)

def rideau_lit(f, L=7.0):
    f.box((0, 8.0, L/2), (0.1, 0.1, L), 'Metal', ACIER, name='Rail', cc=False)
    f.box((0, 5.0, L*0.35), (0.08, 5.8, L*0.7), 'Fabric', (150, 186, 190), name='Rideau', cc=False, tr=0.1)

def chariot(f, rng=None):
    f.box((0, 2.8, 0), (2.4, 0.1, 1.6), 'Metal', ACIER, name='Chariot'); f.box((0, 1.4, 0), (2.4, 0.1, 1.6), 'Metal', ACIER, name='Chariot')
    for x in (-1.1, 1.1):
        for z in (-0.7, 0.7): f.box((x, 1.5, z), (0.1, 2.9, 0.1), 'Metal', ACIER, name='Pied', cc=False)
    f.box((0.4, 3.0, 0.1), (0.8, 0.3, 0.6), 'Plastic', (220, 220, 214), name='Boite', cc=False)

def tuyauterie_plafond(s, n=3, couleurs=((120, 128, 132), (150, 70, 50), (70, 110, 150), (60, 120, 70))):
    """faisceau de tuyaux au plafond le long de la grande dimension, avec colliers"""
    e = s.e; y = e.elev + e.h - 1.6; f = Frame(s.sc, s.folder, (0, 0, 0))
    lx = s.W >= s.D
    for i in range(n):
        o = 2.0 + i*1.3; d = [0.9, 0.6, 1.2, 0.5][i % 4]; col = couleurs[i % len(couleurs)]
        if lx: f.pipe((e.X0 + 1, y - i*0.2, e.Z0 + 1 + o), (e.X1 - 1, y - i*0.2, e.Z0 + 1 + o), d, 'Metal', col, name='TuyauPlafond')
        else: f.pipe((e.X0 + 1 + o, y - i*0.2, e.Z0 + 1), (e.X0 + 1 + o, y - i*0.2, e.Z1 - 1), d, 'Metal', col, name='TuyauPlafond')
    L = s.W if lx else s.D
    for k in range(int(L/8)):
        t = 4 + k*8
        if lx: f.box((e.X0 + t, y - 0.2, e.Z0 + 1 + n*0.65 + 1.4), (0.3, 1.0, n*1.3 + 1.0), 'Metal', (60, 62, 64), name='Collier', cc=False)
        else: f.box((e.X0 + 1 + n*0.65 + 1.4, y - 0.2, e.Z0 + t), (n*1.3 + 1.0, 1.0, 0.3), 'Metal', (60, 62, 64), name='Collier', cc=False)

def chemin_cables(s):
    e = s.e; y = e.elev + e.h - 1.0; f = Frame(s.sc, s.folder, (0, 0, 0)); lx = s.W >= s.D
    if lx: c = ((e.X0 + e.X1)/2, y, e.Z1 - 2.4); sz = (s.W - 2, 0.12, 1.8)
    else: c = (e.X1 - 2.4, y, (e.Z0 + e.Z1)/2); sz = (1.8, 0.12, s.D - 2)
    f.box(c, sz, 'Metal', (100, 104, 106), name='ChemindeCables', cc=False)

def marquage_sol(s, X, Z, w, d):
    f = Frame(s.sc, s.folder, (X, s.y, Z))
    for sx, sz, px, pz in ((w + 2, 0.3, 0, -d/2 - 1), (w + 2, 0.3, 0, d/2 + 1), (0.3, d + 2, -w/2 - 1, 0), (0.3, d + 2, w/2 + 1, 0)):
        f.box((px, 0.02, pz), (sx, 0.04, sz), 'SmoothPlastic', JAUNE, name='Marquage', cc=False, shadow=False)

def bassin_brise(f, rng=None, L=22.0, H=9.0):
    """bassin C : muret de béton, parois vitrées, une paroi éclatée, eau presque vidée qui a débordé"""
    rng = rng or random.Random(0); h0 = 3.2
    for sgn in (-1, 1):
        f.box((0, h0/2, sgn*(L/2 - 0.6)), (L, h0, 1.2), 'Concrete', (150, 156, 152), name='Muret')
        f.box((sgn*(L/2 - 0.6), h0/2, 0), (1.2, h0, L - 2.4), 'Concrete', (150, 156, 152), name='Muret')
    f.box((0, 0.2, 0), (L - 2.4, 0.4, L - 2.4), 'Marble', (70, 120, 130), name='FondBassin')
    for x in (-L/2 + 0.6, L/2 - 0.6):
        for z in (-L/2 + 0.6, L/2 - 0.6): f.box((x, h0 + (H - h0)/2, z), (0.8, H - h0, 0.8), 'Metal', (70, 74, 78), name='Poteau')
    for sgn in (-1, 1):
        f.box((0, H, sgn*(L/2 - 0.6)), (L, 0.5, 0.8), 'Metal', (70, 74, 78), name='Lisse')
        f.box((sgn*(L/2 - 0.6), H, 0), (0.8, 0.5, L), 'Metal', (70, 74, 78), name='Lisse')
    for side in range(4):
        if side == 0:      # paroi éclatée : quelques éclats restés dans le cadre
            for i in range(9):
                x = rng.uniform(-L/2 + 1.5, L/2 - 1.5); y = rng.choice([h0 + rng.uniform(0.2, 1.2), H - rng.uniform(0.3, 1.4)])
                g = f.wedge((x, y, L/2 - 0.6), (rng.uniform(0.6, 2.2), rng.uniform(0.6, 1.8), 0.12), 'Glass', (170, 210, 220), name='Eclat', R=rot_z(rng.uniform(0, 6.3)) if False else None, cc=False); g['t'] = 0.5
            continue
        it = None
        if side == 1: it = f.box((0, h0 + (H - h0)/2, -L/2 + 0.6), (L - 1.6, H - h0, 0.15), 'Glass', (170, 210, 220), name='Vitre', cc=True)
        if side == 2: it = f.box((-L/2 + 0.6, h0 + (H - h0)/2, 0), (0.15, H - h0, L - 1.6), 'Glass', (170, 210, 220), name='Vitre', cc=True)
        if side == 3: it = f.box((L/2 - 0.6, h0 + (H - h0)/2, 0), (0.15, H - h0, L - 1.6), 'Glass', (170, 210, 220), name='Vitre', cc=True)
        it['t'] = 0.7; it['r'] = 0.2
    w = f.box((0, 0.9, 0), (L - 2.6, 1.0, L - 2.6), 'Glass', (40, 90, 100), name='EauBassin', cc=False); w['t'] = 0.4; w['r'] = 0.3
    for i in range(40):          # éclats de verre au sol, devant la paroi brisée
        x = rng.uniform(-L/2, L/2); z = L/2 + rng.uniform(0.3, 7); s_ = rng.uniform(0.3, 1.2)
        g = f.wedge((x, 0.05, z), (s_, 0.08, s_*rng.uniform(0.6, 1.4)), 'Glass', (180, 215, 225), name='EclatSol', R=rot_y(rng.uniform(0, 6.3)), cc=False); g['t'] = 0.4
    fl = f.cyl((0, 0.03, L/2 + 5), 0.04, 14, 'y', 'Glass', (40, 70, 76), name='Debordement', cc=False, shadow=False); fl['t'] = 0.3; fl['r'] = 0.5
    for i in range(6): f.box((rng.uniform(-L/2 + 2, L/2 - 2), 0.75, rng.uniform(-L/2 + 2, L/2 - 2)), (rng.uniform(0.5, 1.4), 0.3, rng.uniform(0.5, 1.4)), 'Rock', (80, 84, 80), name='Pierre', cc=False)
    f.text((0, h0 - 1.2, -L/2 - 0.02), (5, 1.0, 0.05), 'SPÉCIMEN C-17 — CONFINEMENT', txtcol=(255, 255, 255), bg=(160, 30, 30), face='Front', name='PlaqueBassin', cc=False)
    f.pipe((L/2 - 2, H + 0.25, 0), (L/2 - 2, H + 6, 0), 1.0, 'Metal', ACIER, name='Alimentation')

def bouteilles(f, n=5, col=(40, 120, 60)):
    for i in range(n):
        x = (i - (n - 1)/2)*1.0
        f.cyl((x, 2.4, 0.6), 4.8, 0.9, 'y', 'Metal', col, name='Bouteille')
        f.ball((x, 4.85, 0.6), 0.9, 'Metal', col, name='Ogive', cc=False)
        f.cyl((x, 5.4, 0.6), 0.5, 0.3, 'y', 'Metal', ACIER, name='Robinet', cc=False)
    f.box((0, 3.5, 1.15), (n*1.0 + 0.4, 0.15, 0.1), 'Metal', JAUNE, name='Chaine')

def caisse(f, s=None, rng=None, col=None, mat='WoodPlanks'):
    rng = rng or random.Random(0); s = s or rng.uniform(2.2, 3.6)
    f.box((0, s/2, 0), (s, s*rng.uniform(0.7, 1.0), s*rng.uniform(0.8, 1.0)), mat, col or (rng.choice([BOIS_C, (110, 120, 90), (80, 100, 120)]) if mat != 'WoodPlanks' else BOIS_C), name='Caisse')

def futs(f, n=3, rng=None):
    rng = rng or random.Random(0)
    for i in range(n):
        x = (i - (n - 1)/2)*2.2
        if rng.random() < 0.2: f.cyl((x, 1.0, 1.4), 3.2, 2.0, 'z', 'Metal', rng.choice([(40, 80, 140), (170, 60, 30), (60, 90, 60)]), name='FutCouche')
        else:
            f.cyl((x, 1.6, 1.2), 3.2, 2.0, 'y', 'Metal', rng.choice([(40, 80, 140), (170, 60, 30), (60, 90, 60)]), name='Fut')
            for y in (0.9, 2.3): f.cyl((x, y, 1.2), 0.15, 2.08, 'y', 'Metal', GRIS_F, name='Cercle', cc=False)

def comptoir_cuisine(f, w=10.0, d=2.6, rng=None):
    rng = rng or random.Random(0); h = 3.0
    f.box((0, (h - 0.2)/2, d/2), (w, h - 0.2, d), 'Metal', (176, 180, 182), name='Meuble')
    f.box((0, h - 0.1, d/2), (w, 0.2, d), 'Metal', (196, 200, 202), name='PlanInox')
    f.box((-w/2 + 1.5, h - 0.25, d/2), (2.0, 0.1, 1.6), 'Metal', (60, 62, 64), name='Evier', cc=False)
    f.pipe((-w/2 + 1.5, h, 0.3), (-w/2 + 1.5, h + 1.2, 0.3), 0.15, 'Metal', ACIER, name='Robinet', cc=False)
    for i in range(4): f.cyl((w/2 - 1.0 - (i % 2)*1.3, h + 0.05, 0.8 + (i//2)*1.0), 0.1, 0.9, 'y', 'Metal', NOIR, name='Feu', cc=False)
    f.box((0, h + 3.4, 0.6), (w, 2.4, 1.2), 'Metal', (176, 180, 182), name='Placard')
    f.box((w/2 - 1.6, h + 1.8, 0.8), (2.8, 0.9, 1.6), 'Metal', (150, 154, 156), name='Hotte')
    for i in range(rng.randint(2, 6)):
        f.cyl((rng.uniform(-w/2 + 3, w/2 - 3), h + 0.35, rng.uniform(0.5, d - 0.5)), 0.7, rng.uniform(0.6, 1.4), 'y', 'Metal', ACIER, name='Casserole', cc=False)

def frigo(f, w=3.0, d=2.6, h=7.2):
    f.box((0, h/2, d/2), (w, h, d), 'Metal', (200, 204, 206), name='Refrigerateur')
    f.box((0, h*0.62, d + 0.03), (w - 0.1, h*0.7, 0.06), 'Metal', (210, 214, 216), name='Porte', cc=False)
    f.box((w/2 - 0.3, h*0.62, d + 0.12), (0.12, 1.6, 0.12), 'Metal', ACIER, name='Poignee', cc=False)

def wc(f):
    f.box((0, 0.7, 1.0), (1.4, 1.4, 1.6), 'SmoothPlastic', (236, 238, 236), name='Cuvette')
    f.box((0, 2.0, 0.35), (1.5, 1.4, 0.6), 'SmoothPlastic', (236, 238, 236), name='Reservoir')
    for x in (-1.6, 1.6): f.box((x, 3.4, 1.6), (0.1, 6.0, 3.2), 'SmoothPlastic', (120, 140, 150), name='Cloison')
    f.box((0, 3.6, 3.2), (3.1, 5.6, 0.1), 'SmoothPlastic', (120, 140, 150), name='PorteCabine', R=rot_y(-0.7))

def lavabo(f):
    f.box((0, 2.8, 0.8), (2.0, 0.4, 1.4), 'SmoothPlastic', (236, 238, 236), name='Vasque')
    f.cyl((0, 1.3, 0.5), 2.6, 0.5, 'y', 'SmoothPlastic', (236, 238, 236), name='Colonne', cc=False)
    f.pipe((0, 3.0, 0.2), (0, 3.6, 0.2), 0.12, 'Metal', ACIER, name='Robinet', cc=False)
    m = f.box((0, 5.0, 0.06), (1.9, 2.4, 0.08), 'Glass', (200, 210, 212), name='Miroir', cc=False); m['r'] = 0.6
    f.box((0.4, 5.0, 0.11), (1.0, 1.8, 0.02), 'Glass', (160, 170, 172), name='Fissure', cc=False, R=rot_z(0.7), tr=0.5)

def douche(f):
    f.box((0, 0.15, 1.6), (3.2, 0.3, 3.2), 'Marble', (220, 222, 220), name='Receveur')
    for x in (-1.65, 1.65): f.box((x, 3.6, 1.6), (0.1, 7.2, 3.2), 'Marble', (200, 210, 214), name='Cloison')
    f.pipe((0, 1.0, 0.15), (0, 7.0, 0.15), 0.15, 'Metal', ACIER, name='Colonne', cc=False)
    f.cyl((0, 6.9, 0.6), 0.15, 0.9, 'y', 'Metal', ACIER, name='Pommeau', cc=False)
    f.box((0, 4.0, 3.15), (3.2, 6.0, 0.05), 'Fabric', (200, 210, 220), name='Rideau', cc=False, tr=0.2)

def canape(f, w=6.0, col=(84, 70, 64)):
    f.box((0, 0.9, 1.4), (w, 1.4, 2.6), 'Fabric', col, name='Assise')
    f.box((0, 2.2, 0.3), (w, 2.4, 0.6), 'Fabric', col, name='Dossier')
    for x in (-w/2 + 0.3, w/2 - 0.3): f.box((x, 1.6, 1.4), (0.6, 2.0, 2.6), 'Fabric', col, name='Accoudoir')
    f.box((-w/4, 1.75, 1.3), (w/2 - 0.6, 0.3, 2.0), 'Fabric', tuple(c + 10 for c in col), name='Coussin', cc=False)

def bibliotheque(f, w=5.0, d=1.4, h=7.5, rng=None):
    rng = rng or random.Random(0)
    f.box((0, h/2, 0.1), (w, h, 0.2), 'WoodPlanks', BOIS, name='Fond')
    for x in (-w/2 + 0.1, w/2 - 0.1): f.box((x, h/2, d/2), (0.2, h, d), 'WoodPlanks', BOIS, name='Joue')
    for i in range(6):
        y = 0.2 + i*1.4
        f.box((0, y, d/2), (w, 0.15, d), 'WoodPlanks', BOIS, name='Rayon')
        if i == 5: continue
        x = -w/2 + 0.3
        while x < w/2 - 0.4:
            bw = rng.uniform(0.18, 0.35); bh = rng.uniform(0.8, 1.15)
            if rng.random() < 0.08: x += 0.6; continue
            tilt = rot_z(0.35) if rng.random() < 0.06 else None
            f.box((x + bw/2, y + 0.08 + bh/2, d/2 + 0.1), (bw, bh, d - 0.4), 'SmoothPlastic', rng.choice([(120, 40, 40), (40, 60, 100), (60, 90, 60), (160, 140, 100), (40, 40, 44), (140, 110, 60)]),
                  name='Livre', cc=False, R=tilt, shadow=False)
            x += bw + 0.02

def tableau_blanc(f, w=7.0, rng=None):
    rng = rng or random.Random(0)
    f.box((0, 5.0, 0.08), (w, 3.6, 0.12), 'SmoothPlastic', (240, 240, 238), name='TableauBlanc')
    f.box((0, 5.0, 0.04), (w + 0.3, 3.9, 0.08), 'Metal', ACIER, name='Cadre')
    for i in range(rng.randint(5, 12)):
        f.box((rng.uniform(-w/2 + 0.8, w/2 - 0.8), rng.uniform(3.6, 6.4), 0.16), (rng.uniform(0.6, 2.4), 0.06, 0.02), 'SmoothPlastic', rng.choice([(30, 30, 30), (30, 60, 150), (170, 30, 30)]),
              name='Ecriture', cc=False, shadow=False, R=rot_z(rng.uniform(-0.2, 0.2)))

def ecran_mural(f, w=6.0, h=3.4, y=6.0):
    f.box((0, y, 0.15), (w, h, 0.3), 'Plastic', NOIR, name='EcranMural')
    f.box((0, y, 0.31), (w - 0.3, h - 0.3, 0.02), 'SmoothPlastic', ECRAN_OFF, name='Dalle', cc=False, tags=['Ecran'])

def extincteur(f):
    f.cyl((0, 2.0, 0.45), 1.8, 0.7, 'y', 'SmoothPlastic', (190, 20, 20), name='Extincteur')
    f.box((0, 3.05, 0.45), (0.3, 0.3, 0.3), 'Metal', NOIR, name='Tete', cc=False)
    f.box((0, 2.0, 0.06), (0.9, 2.6, 0.12), 'Metal', (170, 20, 20), name='Support')

def poubelle(f):
    f.cyl((0, 1.0, 0.7), 2.0, 1.2, 'y', 'Metal', GRIS, name='Poubelle')

def plantes(f, L=10.0, rng=None):
    rng = rng or random.Random(0)
    f.box((0, 1.2, 0), (L, 2.4, 2.6), 'Metal', (200, 204, 200), name='Bac')
    f.box((0, 2.35, 0), (L - 0.3, 0.1, 2.3), 'Concrete', (60, 50, 40), name='Substrat')
    for i in range(int(L/0.9)):
        x = -L/2 + 0.6 + i*0.9
        if rng.random() < 0.2:
            f.box((x, 2.5, rng.uniform(-0.6, 0.6)), (0.6, 0.2, 0.8), 'SmoothPlastic', (100, 80, 50), name='PlanteMorte', cc=False); continue
        s = rng.uniform(0.6, 1.3); f.ball((x, 2.5 + s*0.4, rng.uniform(-0.5, 0.5)), s, 'Grass', rng.choice([(70, 130, 60), (90, 140, 50), (60, 110, 70)]), name='Plante', cc=False)
    f.box((0, 8.0, 0), (L, 0.3, 0.8), 'Metal', GRIS_F, name='RampeCulture')
    f.box((0, 7.8, 0), (L - 0.4, 0.1, 0.6), 'Neon', (200, 80, 255), name='LampeCulture', cc=False, shadow=False, tags=['LumiereNormale'])
    f.light((0, 7.4, 0), 'SurfaceLight', (200, 90, 255), 1.2, 12, 'Bottom', 120, shadows=False, enabled=False, tags=['LumiereNormale'], part_size=(L - 0.4, 0.1, 0.6))

def tiroirs_morgue(f, w=6.0, d=2.8):
    f.box((0, 3.6, d/2), (w, 7.2, d), 'Metal', (176, 182, 184), name='Casiers')
    for i in range(3):
        for j in range(3):
            x = -w/2 + 1 + j*2; y = 1.2 + i*2.3
            f.box((x, y, d + 0.04), (1.8, 2.0, 0.08), 'Metal', (196, 200, 202), name='Trappe', cc=False)
            f.box((x, y + 0.4, d + 0.12), (0.8, 0.12, 0.1), 'Metal', ACIER, name='Poignee', cc=False)
    f.box((w/2 - 1, 1.2, d + 2.4), (1.8, 0.2, 4.6), 'Metal', (196, 200, 202), name='TiroirOuvert')
    f.box((w/2 - 1, 1.5, d + 2.6), (1.4, 0.5, 4.0), 'Fabric', (220, 222, 220), name='Drap', cc=False)

def table_autopsie(f):
    f.box((0, 2.9, 0), (3.2, 0.2, 7.0), 'Metal', (190, 196, 198), name='TableAutopsie')
    f.cyl((0, 1.4, 0), 2.8, 0.9, 'y', 'Metal', ACIER, name='Pied')
    for x in (-1.55, 1.55): f.box((x, 3.1, 0), (0.12, 0.3, 7.0), 'Metal', (190, 196, 198), name='Rebord')
    f.cyl((0, 9.0, 0), 0.4, 3.0, 'y', 'Metal', GRIS, name='Scialytique')
    f.box((2.6, 2.4, -1.5), (1.6, 0.1, 2.4), 'Metal', ACIER, name='Desserte')
    for i in range(4): f.box((2.6 + (i - 1.5)*0.3, 2.47, -1.5), (0.06, 0.04, 1.0), 'Metal', (210, 210, 210), name='Instrument', cc=False)

def drone(f):
    f.box((0, 2.4, 0), (4.0, 1.4, 2.4), 'Metal', (210, 180, 40), name='CorpsDrone')
    f.box((2.2, 2.4, 0), (0.6, 1.0, 1.6), 'Glass', (40, 40, 50), name='Camera', tr=0.2)
    for x in (-1.6, 1.6):
        for z in (-1.6, 1.6):
            f.cyl((x, 3.2, z), 0.6, 1.4, 'y', 'Metal', GRIS_F, name='Propulseur')
            f.box((x, 2.8, z*0.6), (0.2, 0.2, 1.2), 'Metal', GRIS_F, name='Bras', cc=False)
    f.box((0, 0.8, 0), (4.6, 1.6, 3.0), 'Metal', (60, 64, 60), name='Berceau')
    f.pipe((-2.0, 2.4, 1.2), (-6.0, 0.3, 3.0), 0.25, 'Plastic', (200, 150, 30), name='Ombilical', cc=False)

def capsule_survie(f):
    f.cyl((0, 4.0, 0), 8.0, 6.0, 'y', 'Metal', (200, 120, 40), name='Capsule')
    f.ball((0, 8.0, 0), 6.0, 'Metal', (200, 120, 40), name='Dome')
    f.box((0, 3.4, 3.0), (2.6, 5.0, 0.3), 'Metal', (60, 64, 68), name='Ecoutille')
    f.cyl((0, 6.6, 3.05), 0.1, 1.2, 'z', 'Glass', (120, 160, 180), name='Hublot', tr=0.3)
    f.text((0, 1.6, 3.12), (2.6, 0.8, 0.05), 'CAPSULE DE SURVIE — 3 PL.', txtcol=(20, 20, 20), bg=(220, 220, 210), name='Plaque', cc=False)

def hublot(f, y=5.0, d=2.6):
    """hublot rond posé sur un mur : cadre, vitre, et l'eau noire derrière"""
    f.cyl((0, y, 0.15), 0.3, d + 0.8, 'z', 'Metal', (70, 74, 78), name='CadreHublot')
    for k in range(10):
        a = k*2*math.pi/10; f.cyl((math.cos(a)*(d/2 + 0.2), y + math.sin(a)*(d/2 + 0.2), 0.32), 0.12, 0.18, 'z', 'Metal', ACIER, name='Boulon', cc=False)
    f.cyl((0, y, 0.05), 0.12, d, 'z', 'Neon', (6, 22, 32), name='Abysse', cc=False, shadow=False)
    v = f.cyl((0, y, 0.2), 0.08, d, 'z', 'Glass', (120, 170, 190), name='VitreHublot', cc=False); v['t'] = 0.6; v['r'] = 0.25

def affiche(f, txt, w=3.0, h=2.0, y=5.5, bg=(230, 220, 190), col=(40, 40, 40)):
    f.text((0, y, 0.04), (w, h, 0.05), txt, txtcol=col, bg=bg, name='Affiche', cc=False)

def flaque(f, rng=None, s=None):
    rng = rng or random.Random(0); s = s or rng.uniform(2, 5)
    p = f.cyl((0, 0.03, 0), 0.04, s, 'y', 'Glass', (40, 60, 64), name='Flaque', cc=False, shadow=False); p['t'] = 0.35; p['r'] = 0.4

def debris_papiers(f, n=6, rng=None, r=4):
    rng = rng or random.Random(0)
    for i in range(n):
        f.box((rng.uniform(-r, r), 0.03, rng.uniform(-r, r)), (0.85, 0.02, 1.1), 'SmoothPlastic', (230, 228, 220), name='Feuille', R=rot_y(rng.uniform(0, 6.3)), cc=False, shadow=False)

def tache(f, rng=None, s=None, col=(40, 30, 26)):
    rng = rng or random.Random(0); s = s or rng.uniform(1.5, 4)
    f.cyl((0, 0.025, 0), 0.03, s, 'y', 'SmoothPlastic', col, name='Tache', cc=False, shadow=False, tr=0.35)

# ================================================================ placement dans une salle
class Salle:
    def __init__(s, sc, e):
        s.sc, s.e = sc, e; s.rng = random.Random(zlib.crc32(e.id.encode()))
        s.y = e.elev; s.folder = e.folder + '/Mobilier'
        X0, Z0, X1, Z1 = e.X0, e.Z0, e.X1, e.Z1
        s.sides = {
            'N': dict(o=(X0, s.y, Z0 + WT_IN), yaw=0.0, L=X1 - X0, conv=lambda X, Z: X - X0),
            'S': dict(o=(X1, s.y, Z1 - WT_IN), yaw=math.pi, L=X1 - X0, conv=lambda X, Z: X1 - X),
            'W': dict(o=(X0 + WT_IN, s.y, Z1), yaw=math.pi/2, L=Z1 - Z0, conv=lambda X, Z: Z1 - Z),
            'E': dict(o=(X1 - WT_IN, s.y, Z0), yaw=-math.pi/2, L=Z1 - Z0, conv=lambda X, Z: Z - Z0)}
        for k, sd in s.sides.items():
            sd['used'] = []
            for h in getattr(e, 'wall_holes', {}).get(k, []):
                a, b = sorted((sd['conv'](h[0], h[0]) if k in 'NS' else sd['conv'](0, h[0]), sd['conv'](h[1], h[1]) if k in 'NS' else sd['conv'](0, h[1])))
                sd['used'].append((a - 2.6, b + 2.6))
            for gx, gz, sid, soud in []: pass
        s.corner = 4.4; s.pris = []
        s.W, s.D = X1 - X0, Z1 - Z0
    def frame_mur(s, side, u):
        sd = s.sides[side]; f = Frame(s.sc, s.folder, sd['o'], rot_y(sd['yaw'])); return f.sub((u, 0, 0))
    def place(s, side, w, fn, *a, pref='debut', **kw):
        sd = s.sides[side]; L = sd['L']; lo, hi = s.corner, L - s.corner
        cands = []
        u = lo
        while u + w <= hi + 0.01:
            if not any(not (u + w <= a_ or u >= b_) for a_, b_ in sd['used']): cands.append(u)
            u += 0.5
        if not cands: return False
        u = cands[0] if pref == 'debut' else cands[-1] if pref == 'fin' else min(cands, key=lambda c: abs(c + w/2 - L/2))
        sd['used'].append((u, u + w)); fn(s.frame_mur(side, u + w/2), *a, **kw); return True
    def remplir(s, side, w, fn, *a, gap=0.4, maxn=99, **kw):
        n = 0
        while n < maxn and s.place(side, w, fn, *a, **kw): n += 1
        return n
    def centre(s, marge=7.5):
        X0, Z0, X1, Z1 = s.e.X0 + marge, s.e.Z0 + marge, s.e.X1 - marge, s.e.Z1 - marge
        return (X0, Z0, X1, Z1) if X1 > X0 + 1 and Z1 > Z0 + 1 else None
    def fc(s, X, Z, yaw=0.0): return Frame(s.sc, s.folder, (X, s.y, Z), rot_y(yaw))
    def grille_centre(s, iw, id_, gx=3.0, gz=4.0, marge=7.5, maxn=99):
        c = s.centre(marge)
        if not c: return []
        X0, Z0, X1, Z1 = c; out = []
        nx = max(0, int((X1 - X0 + gx)/(iw + gx))); nz = max(0, int((Z1 - Z0 + gz)/(id_ + gz)))
        if nx == 0 or nz == 0: return []
        ox = X0 + (X1 - X0 - (nx*iw + (nx - 1)*gx))/2 + iw/2; oz = Z0 + (Z1 - Z0 - (nz*id_ + (nz - 1)*gz))/2 + id_/2
        for i in range(nx):
            for j in range(nz):
                X, Z = ox + i*(iw + gx), oz + j*(id_ + gz)
                r = (X - iw/2 - gx/2, Z - id_/2 - gz/2, X + iw/2 + gx/2, Z + id_/2 + gz/2)
                if any(r[0] < q[2] and r[2] > q[0] and r[1] < q[3] and r[3] > q[1] for q in s.pris): continue
                if len(out) < maxn: out.append((X, Z)); s.pris.append(r)
        return out
    def sides_by_len(s): return sorted(s.sides, key=lambda k: -s.sides[k]['L'])
    def libres(s): return [k for k in s.sides_by_len()]

# ================================================================ recettes par type de salle
def kind_of(e):
    i = e.id
    for k in ('depot_labo', 'laverie', 'salle_cuves', 'chambre_froide', 'atelier_drone', 'reserve_m2', 'salle_info', 'salle_plans', 'cabine_cdt', 'local_elec', 'local_tech', 'local_comms',
              'placard', 'toilettes', 'douches', 'quartiers', 'vestiaire', 'serveurs', 'archives', 'bureau', 'reserve', 'stock', 'labo', 'aquariums', 'specimens',
              'cantine', 'cuisine', 'infirmerie', 'pharmacie', 'morgue', 'dissection', 'centrale', 'turbines', 'pompes', 'compresseurs', 'chaufferie', 'ateliers', 'soudure',
              'entrepot', 'pieces', 'outillage', 'local_elec', 'sous_station', 'batteries', 'controle', 'oxygene', 'traitement_air', 'filtration', 'reservoirs', 'eaux_usees',
              'groupe_froid', 'vannes', 'carburant', 'huiles', 'magasin', 'consigne', 'local_tech', 'local_comms', 'radio', 'securite', 'reunion', 'crise', 'briefing',
              'attente', 'poste_garde', 'decontamination', 'sas', 'navette', 'amarrage', 'rotonde', 'hangar', 'atelier_drone', 'biblio', 'detente', 'sport', 'jeux',
              'projection', 'musique', 'recueillement', 'linge', 'buanderie', 'serre', 'observatoire', 'module_prel', 'cloche', 'quarantaine', 'chambre_froide',
              'salle_cuves', 'depot_labo', 'laverie', 'sonar', 'imprimerie', 'salle_plans', 'scelles', 'salle_info', 'cabine_cdt', 'cellule', 'soins', 'inondes',
              'puisard', 'ballasts', 'reserve_m2'):
        if i.startswith(k) or k in i: return k
    return 'divers'

def meubler(sc, e):
    s = Salle(sc, e); r = s.rng; k = kind_of(e); L = s.sides_by_len()
    def murs(w, fn, *a, n=99, cotes=None, **kw):
        t = 0
        for c in (cotes or L):
            t += s.remplir(c, w, fn, *a, maxn=n - t, **kw)
            if t >= n: break
        return t
    def deco_porte():
        for c in L:
            if s.place(c, 1.2, extincteur, pref='fin'): break
    # ---------------------------------------------------------- pièces uniques
    if e.id == 'labo_c':
        X, Z = (e.X0 + e.X1)/2, (e.Z0 + e.Z1)/2 + 4
        bassin_brise(s.fc(X, Z), rng=r); s.pris.append((X - 18, Z - 15, X + 18, Z + 20))
    # ---------------------------------------------------------- par type
    if k == 'placard':
        murs(2.6, etagere, 2.4, 1.6, 6.5, 4, rng=r, n=2); s.place(L[-1], 1.4, poubelle)
        s.fc(e.X0 + s.W/2, e.Z0 + s.D/2).cyl((0, 1.0, 0), 2.0, 1.0, 'y', 'Plastic', (200, 170, 40), name='Seau')
    elif k in ('toilettes',):
        murs(3.2, wc, n=4, cotes=L[:1]); murs(2.4, lavabo, n=3, cotes=L[1:2])
    elif k == 'douches':
        murs(3.4, douche, n=6, cotes=L[:2]); murs(2.4, lavabo, n=3, cotes=L[2:3]); murs(1.8, casiers, 1, rng=r, n=4, cotes=L[3:])
    elif k in ('quartiers',):
        murs(7.4, lit_superpose, rng=r, cotes=L[:2]); murs(3.6, casiers, 2, rng=r, cotes=L[2:])
        for X, Z in s.grille_centre(7.4, 6.8, 5, 6, marge=8.5):
            f0 = s.fc(X, Z, 0); lit_superpose(f0.sub((0, 0, 0.05)), rng=r); lit_superpose(f0.sub((0, 0, -0.05), math.pi), rng=r)
    elif k == 'vestiaire':
        murs(7.0, casiers, 4, rng=r, cotes=L[:2])
        for X, Z in s.grille_centre(8, 1.4, 3, 6, marge=7, maxn=3): s.fc(X, Z).box((0, 1.4, 0), (8, 0.3, 1.4), 'WoodPlanks', BOIS_C, name='Banc')
    elif k in ('serveurs', 'salle_info'):
        if k == 'serveurs':
            for X, Z in s.grille_centre(2.4*5, 3.6, 0, 6, marge=6):
                for i in range(5): rack_serveur(s.fc(X + (i - 2)*2.4, Z), rng=r)
        murs(6.2, console, rng=r, n=2, cotes=L[:1]); murs(5.2, bureau, rng=r, n=4, cotes=L[1:])
    elif k in ('archives', 'imprimerie', 'scelles', 'salle_plans'):
        murs(2.0, armoire, cotes=L[:2]); murs(6.2, etagere, 6, 1.8, 7, 5, rng=r, contenu='cartons', cotes=L[2:])
        for X, Z in s.grille_centre(10, 3.6, 5, 6, marge=8, maxn=6):
            for i in range(5): armoire(s.fc(X - 4 + i*2, Z - 0.05, 0)); armoire(s.fc(X - 4 + i*2, Z + 0.05, math.pi))
        for X, Z in s.grille_centre(6, 3, 4, 5, marge=8, maxn=1): table(s.fc(X, Z), 6, 3, chaises=2, rng=r)
        if k == 'archives': s.fc(e.X0 + s.W*0.7, e.Z0 + s.D*0.6).box((0, 2.5, 0), (3.0, 5.0, 2.6), 'Metal', (60, 64, 70), name='Coffre', tags=['Coffre'])
    elif k in ('bureau', 'cabine_cdt', 'poste_garde', 'attente', 'local_comms'):
        murs(5.2, bureau, rng=r, n=99 if k != 'cabine_cdt' else 1, cotes=L[:2]); murs(2.0, armoire, n=6, cotes=L[2:3]); murs(5.2, bibliotheque, rng=r, n=3, cotes=L[3:])
        if k in ('bureau', 'local_comms', 'poste_garde'):
            for X, Z in s.grille_centre(10.4, 5.4, 5, 8, marge=8.5):
                for dx in (-2.6, 2.6):
                    bureau(s.fc(X + dx, Z - 0.1, 0), 5.0, 2.6, rng=r); bureau(s.fc(X + dx, Z + 0.1, math.pi), 5.0, 2.6, rng=r)
        if k == 'attente':
            for X, Z in s.grille_centre(6, 2.6, 3, 4, marge=7): canape(s.fc(X, Z), 6, (70, 80, 96))
        if k == 'cabine_cdt': s.place(L[2], 7.4, lit_superpose, rng=r)
    elif k in ('reserve', 'stock', 'magasin', 'consigne', 'linge', 'depot_labo', 'pieces', 'outillage', 'reserve_m2'):
        murs(6.2, etagere, 6, 2.0, 7, 4, rng=r, contenu='flacons' if k == 'stock' else 'mixte')
        for X, Z in s.grille_centre(12.4, 4.2, 5, 6, marge=8):
            for dx in (-3.1, 3.1):
                etagere(s.fc(X + dx, Z - 0.1, 0), 6, 2.0, 7, 4, rng=r); etagere(s.fc(X + dx, Z + 0.1, math.pi), 6, 2.0, 7, 4, rng=r)
        for X, Z in s.grille_centre(3.4, 3.4, 3, 3, marge=6, maxn=4): caisse(s.fc(X, Z, r.uniform(-0.3, 0.3)), rng=r)
    elif k in ('labo', 'dissection', 'quarantaine', 'laverie', 'chambre_froide'):
        murs(8.4, paillasse, rng=r, cotes=L[:2]); murs(5.4, hotte, n=2, cotes=L[2:3]); murs(6.2, etagere, 6, 2, 7, 4, rng=r, contenu='labo', cotes=L[2:])
        for X, Z in s.grille_centre(8.4, 5.8, 5, 7, marge=8.5):
            paillasse(s.fc(X, Z - 0.1, 0), 8, 2.8, rng=r, evier=r.random() < 0.3); paillasse(s.fc(X, Z + 0.1, math.pi), 8, 2.8, rng=r, evier=False)
        if k == 'dissection': table_autopsie(s.fc(e.X0 + s.W/2, e.Z0 + s.D/2, 0.2))
        if k == 'chambre_froide':
            for X, Z in s.grille_centre(2, 2, 1, 1, marge=6, maxn=4): s.fc(X, Z).box((0, 0.05, 0), (2, 0.1, 2), 'Ice', (220, 230, 240), name='Givre', cc=False)
    elif k in ('aquariums',):
        murs(8.4, aquarium, rng=r, cotes=L[:2], brise=False); murs(8.4, aquarium, rng=r, cotes=L[2:], brise=True)
        flaque(s.fc(e.X0 + s.W/2, e.Z0 + s.D/2), rng=r, s=7)
    elif k in ('specimens', 'stock_echant', 'salle_cuves'):
        murs(6.2, bocaux, rng=r)
        for X, Z in s.grille_centre(3, 3, 6, 6, marge=8): cuve(s.fc(X, Z), 3.0, 6.0, (180, 200, 200))
    elif k == 'cantine':
        for X, Z in s.grille_centre(10, 3, 4, 5, marge=6): table(s.fc(X, Z), 10, 3, chaises=8, rng=r)
        murs(10.4, comptoir_cuisine, rng=r, n=1, cotes=L[:1]); murs(1.4, poubelle, n=2, cotes=L[1:])
    elif k == 'cuisine':
        murs(10.4, comptoir_cuisine, rng=r, cotes=L[:2]); murs(3.4, frigo, n=3, cotes=L[2:])
        for X, Z in s.grille_centre(6, 3, 4, 4, marge=7, maxn=1): table(s.fc(X, Z), 6, 3, h=3.2, mat='Metal', col=(196, 200, 202), rng=r)
    elif k in ('infirmerie', 'soins'):
        def lit_rideau(f, rng=None): lit_hopital(f, rng=rng); rideau_lit(f.sub((2.6, 0, 0)))
        murs(5.6, lit_rideau, rng=r, cotes=L[:2]); murs(3.2, armoire_vitree, rng=r, n=4, cotes=L[2:3]); murs(5.2, bureau, rng=r, n=1, cotes=L[3:])
        for X, Z in s.grille_centre(2.4, 1.6, 6, 6, marge=9, maxn=3): chariot(s.fc(X, Z, r.uniform(0, 3)), rng=r)
    elif k == 'pharmacie':
        murs(6.2, etagere, 6, 1.6, 7, 6, rng=r, contenu='flacons')
    elif k == 'morgue':
        murs(6.4, tiroirs_morgue, cotes=L[:1], n=2); table_autopsie(s.fc(e.X0 + s.W/2, e.Z0 + s.D/2))
    elif k in ('centrale',):
        for X, Z in s.grille_centre(18, 8, 6, 10, marge=10, maxn=2): turbine(s.fc(X, Z), 16, 7); marquage_sol(s, X, Z, 18, 8)
        for X, Z in s.grille_centre(6.4, 4.4, 5, 5, marge=8): transformateur(s.fc(X, Z), rng=r); marquage_sol(s, X, Z, 6.4, 4.4)
        murs(3.4, armoire_elec, rng=r, ouverte=True, n=6, cotes=L[:1]); murs(6.2, console, rng=r, n=2, cotes=L[1:2])
    elif k in ('turbines',):
        for X, Z in s.grille_centre(16, 7, 6, 8, marge=8, maxn=2): turbine(s.fc(X, Z), 14, 6); marquage_sol(s, X, Z, 16, 7)
        for X, Z in s.grille_centre(6.4, 4.4, 5, 5, marge=8): transformateur(s.fc(X, Z), rng=r)
    elif k in ('pompes', 'vannes', 'eaux_usees', 'filtration', 'reservoirs', 'oxygene', 'traitement_air', 'groupe_froid', 'compresseurs', 'chaufferie'):
        if k in ('reservoirs', 'oxygene', 'eaux_usees', 'chaufferie', 'traitement_air'):
            for X, Z in s.grille_centre(7, 7, 4, 4, marge=8): cuve(s.fc(X, Z), 7, min(e.h - 2, 12))
        else:
            for X, Z in s.grille_centre(6, 3, 6, 6, marge=7): pompe(s.fc(X, Z, r.choice([0, math.pi/2])), rng=r); marquage_sol(s, X, Z, 5, 2.6)
        murs(3.4, armoire_elec, rng=r, n=2, cotes=L[:1]); murs(5.4, bouteilles, 5, (40, 120, 60) if k == 'oxygene' else (120, 120, 120), n=2, cotes=L[1:2])
    elif k in ('ateliers', 'soudure', 'atelier_drone'):
        murs(7.4, etabli, rng=r, cotes=L[:2]); murs(6.2, etagere, 6, 2, 7, 4, rng=r, cotes=L[2:3])
        if k == 'soudure': murs(4.4, bouteilles, 4, (60, 60, 140), n=1, cotes=L[3:])
        for X, Z in s.grille_centre(3, 3, 4, 4, marge=8, maxn=3): futs(s.fc(X, Z), 1, rng=r)
    elif k in ('entrepot',):
        for X, Z in s.grille_centre(6, 2, 4, 4, marge=5): etagere(s.fc(X, Z - 1), 6, 2, 9, 5, rng=r, contenu='cartons')
        murs(7, futs, 3, rng=r, n=4)
    elif k in ('local_elec', 'sous_station', 'batteries', 'local_tech'):
        murs(3.4, armoire_elec, rng=r, ouverte=r.random() < 0.4)
    elif k in ('carburant', 'huiles'):
        murs(7, futs, 3, rng=r)
    elif k in ('controle', 'radio', 'securite', 'crise', 'sonar'):
        murs(6.2, console, rng=r, ecrans=2 if k != 'securite' else 3, cotes=L[:2]); murs(2.0, armoire, n=8, cotes=L[2:])
        for X, Z in s.grille_centre(12.4, 3.2, 6, 8, marge=9): console(s.fc(X, Z - 1.5, 0), 12, 3, rng=r, ecrans=3)
        if k in ('securite', 'crise'):
            for c in L[:1]: ecran_mural(s.frame_mur(c, s.sides[c]['L']/2), min(10, s.sides[c]['L'] - 10), 4, 7.2)
        if k == 'radio': s.fc(e.X0 + s.W/2, e.Z0 + s.D/2).box((0, 3.0, 0), (1.6, 0.8, 1.2), 'Plastic', (60, 50, 40), name='Magnetophone', tags=['Enregistrement'])
    elif k in ('reunion', 'briefing', 'projection'):
        c = s.grille_centre(12, 4, 0, 0, marge=7, maxn=1)
        if c and k != 'projection': table(s.fc(*c[0]), 12, 4, mat='WoodPlanks', col=BOIS, chaises=10, rng=r)
        if k == 'projection':
            for X, Z in s.grille_centre(1.6, 1.6, 1.0, 2.6, marge=6): chaise_simple(s.fc(X, Z, math.pi), (120, 40, 40))
        s.place(L[0], 7.4, tableau_blanc, rng=r, pref='centre')
        ecran_mural(s.frame_mur(L[1], s.sides[L[1]]['L']/2), min(12, s.sides[L[1]]['L'] - 10), 5, 6.5)
    elif k in ('detente', 'jeux', 'musique', 'recueillement', 'biblio'):
        murs(5.2, bibliotheque, rng=r, cotes=L[:1] if k != 'biblio' else L)
        for X, Z in s.grille_centre(6, 2.6, 4, 5, marge=7, maxn=3): canape(s.fc(X, Z, r.choice([0, math.pi])), 6, r.choice([(84, 70, 64), (60, 76, 90), (90, 80, 60)]))
        if k == 'jeux':
            for X, Z in s.grille_centre(4, 4, 4, 4, marge=8, maxn=2): table(s.fc(X, Z), 4, 4, chaises=4, rng=r, col=(30, 90, 50), mat='Fabric')
    elif k == 'sport':
        for X, Z in s.grille_centre(3, 6, 4, 3, marge=7):
            f = s.fc(X, Z); f.box((0, 1.6, 0), (2.4, 0.4, 6), 'Fabric', NOIR, name='Banc'); f.box((0, 0.8, 0), (0.4, 1.6, 4), 'Metal', GRIS, name='Pied')
            f.cyl((0, 4.0, 1.8), 6.0, 0.25, 'x', 'Metal', ACIER, name='Barre'); [f.cyl((x, 4.0, 1.8), 0.4, 2.2, 'x', 'Metal', NOIR, name='Disque') for x in (-2.2, 2.2)]
        murs(3.0, armoire, col=(80, 80, 84), n=2)
    elif k in ('buanderie',):
        for c in L[:2]:
            s.remplir(c, 3.0, lambda f: (f.box((0, 1.9, 1.4), (2.8, 3.8, 2.8), 'SmoothPlastic', (230, 232, 230), name='LaveLinge'),
                                          f.cyl((0, 2.2, 2.85), 0.1, 1.8, 'z', 'Glass', (60, 70, 80), name='Hublot', cc=False)))
    elif k == 'serre':
        for X, Z in s.grille_centre(12, 2.6, 4, 4, marge=6): plantes(s.fc(X, Z), 12, rng=r)
    elif k in ('hangar',):
        drone(s.fc(e.X0 + s.W/2, e.Z0 + s.D/2, 0.4)); murs(6.2, console, rng=r, n=1, cotes=L[:1]); murs(7.4, etabli, rng=r, n=2, cotes=L[1:2]); murs(7, futs, 3, rng=r, n=2, cotes=L[2:])
    elif k in ('ballasts',):
        for X, Z in s.grille_centre(7, 7, 10, 4, marge=10, maxn=2): capsule_survie(s.fc(X, Z, math.pi))
        murs(6.2, console, rng=r, n=1, cotes=L[:1]); murs(5.4, pompe, n=3, cotes=L[1:2])
    elif k in ('inondes', 'puisard'):
        murs(7, futs, 3, rng=r, n=3); murs(6.2, etagere, 6, 2, 7, 3, rng=r, n=2)
    elif k in ('rotonde',):
        f = s.fc((e.X0 + e.X1)/2, (e.Z0 + e.Z1)/2)
        for a in range(8):
            ff = f.sub((math.sin(a*math.pi/4)*7.5, 0, math.cos(a*math.pi/4)*7.5), a*math.pi/4 + math.pi)
            ff.box((0, 1.6, 0), (5.6, 3.2, 2.4), 'Metal', (60, 64, 68), name='ConsoleRonde')
            ff.box((0, 3.5, 0.6), (5.2, 0.25, 1.4), 'Metal', (50, 54, 58), name='Tablette', R=rot_x(-0.3))
            ff.box((0, 5.0, -0.7), (4.8, 2.4, 0.25), 'Plastic', NOIR, name='Ecran'); ff.box((0, 5.0, -0.55), (4.5, 2.1, 0.03), 'SmoothPlastic', ECRAN_OFF, name='Dalle', cc=False, tags=['Ecran'])
        f.cyl((0, 1.6, 0), 3.2, 8.0, 'y', 'Metal', (54, 58, 62), name='TablePlan')
        for a, txt, col in ((0, 'ARRIVÉE ↑', (170, 170, 176)), (math.pi/2, 'VIE →', (60, 120, 200)), (math.pi, 'MACHINES ↓', (220, 130, 30)), (-math.pi/2, '← RECHERCHE', (70, 160, 90))):
            ff = f.sub((math.sin(a)*22, 0, -math.cos(a)*22), -a)
            ff.cyl((0, 4.5, 0), 9, 0.5, 'y', 'Metal', (70, 74, 78), name='Mat')
            ff.text((0, 8.0, 0.3), (5.0, 1.4, 0.2), txt, txtcol=(255, 255, 255), bg=col, face='Back', name='Direction', cc=False)
        for a in range(4):
            ff = f.sub((math.sin(a*math.pi/2 + math.pi/4)*20, 0, math.cos(a*math.pi/2 + math.pi/4)*20), a*math.pi/2 + math.pi/4)
            ff.box((0, 1.2, 0), (7, 0.4, 2), 'Metal', (80, 84, 88), name='Banc'); ff.box((0, 0.5, 0), (6, 1.0, 0.4), 'Metal', (60, 64, 68), name='PiedBanc')
        f.cyl((0, 3.25, 0), 0.1, 7.6, 'y', 'Neon', (20, 60, 80), name='PlanHolo', cc=False, tags=['Ecran'])
        f.cyl((0, e.h - 1.5, 0), 3.0, 14, 'y', 'Metal', (70, 74, 78), name='CouronnePlafond')
        f.light((0, e.h - 3.2, 0), 'PointLight', (255, 70, 40), 1.4, 30, tags=['LumiereSecours'])
    elif k in ('navette',):
        for c in L[:2]: s.remplir(c, 2.2, lambda f: (f.box((0, 1.6, 1.0), (2.0, 0.3, 2.0), 'Fabric', (50, 56, 70), name='Siege'), f.box((0, 3.6, 0.2), (2.0, 4.0, 0.4), 'Fabric', (50, 56, 70), name='Dossier'),
                                                      f.box((0, 4.6, 0.6), (1.8, 0.2, 0.2), 'Metal', JAUNE, name='Harnais', cc=False)), maxn=8)
        f = s.fc((e.X0 + e.X1)/2, e.Z0 + 10); f.box((0, 4.0, 0), (10, 8, 6), 'Glass', (120, 200, 220), name='ReservoirConfinement', tr=0.6)
        f.box((0, 0.5, 0), (11, 1, 7), 'Metal', (60, 64, 68), name='SocleReservoir'); f.box((0, 8.3, 0), (11, 0.6, 7), 'Metal', (60, 64, 68), name='ToitReservoir')
        f2 = s.fc((e.X0 + e.X1)/2, e.Z1 - 8); f2.box((0, 2.0, 0), (6, 4, 4), 'Metal', (70, 74, 80), name='CoffrePreuves', tags=['CoffrePreuves'])
        f2.text((0, 3.0, -2.05), (4, 1, 0.05), 'PREUVES', txtcol=(255, 255, 255), bg=(40, 90, 170), face='Back', name='Plaque', cc=False)
    elif k in ('decontamination', 'sas', 'amarrage', 'cloche'):
        murs(1.2, lambda f: f.pipe((0, 9.0, 0.6), (0, 9.0, 1.6), 0.4, 'Metal', ACIER, name='Buse'), n=6)
        murs(1.8, casiers, 1, rng=r, n=2)
    elif k in ('observatoire', 'module_prel', 'sonar'):
        murs(6.2, console, rng=r, n=2, cotes=L[1:2]); murs(8.4, paillasse, rng=r, n=2, cotes=L[2:3])
    elif k == 'cellule':
        s.place(L[0], 7.4, lit_superpose, rng=r); s.place(L[1], 3.2, wc)
    else:
        murs(6.2, etagere, 6, 2, 7, 4, rng=r, n=2); murs(2.0, armoire, n=2)
    if k == 'rotonde': return
    if e.secteur in ('machines', 'fonds') or k in ('hangar', 'entrepot', 'reserve_m2', 'pieces'):
        tuyauterie_plafond(s, 4 if s.W*s.D > 1500 else 2)
    if k in ('serveurs', 'salle_info', 'securite', 'controle', 'radio', 'local_elec', 'sous_station', 'batteries'):
        chemin_cables(s)
    # ---------------------------------------------------------- détails communs : hublots, extincteur, poubelle, traces de l'incident
    if e.secteur in ('recherche', 'vie', 'arrivee') and e.elev == 0 and k not in ('placard', 'toilettes', 'serveurs', 'archives', 'navette', 'sas', 'amarrage', 'chambre_froide'):
        for c in L[:2]:
            sd = s.sides[c]
            if sd['L'] > 14 and s.place(c, 4.2, hublot, pref='centre'): break
    deco_porte()
    if k not in ('placard', 'toilettes', 'douches', 'cellule') and r.random() < 0.7: s.place(L[-1], 1.4, poubelle, pref='fin')
    c = s.centre(4)
    if c:
        X0, Z0, X1, Z1 = c
        for i in range(r.randint(0, 2)): debris_papiers(s.fc(r.uniform(X0, X1), r.uniform(Z0, Z1)), r.randint(2, 7), rng=r, r=2.5)
        if r.random() < 0.35: tache(s.fc(r.uniform(X0, X1), r.uniform(Z0, Z1)), rng=r)
        if e.elev < 0 and r.random() < 0.6: flaque(s.fc(r.uniform(X0, X1), r.uniform(Z0, Z1)), rng=r)
    # plaque nominative à côté de la porte (côté salle)
    for side, H in getattr(e, 'wall_holes', {}).items():
        for h in H:
            if h[4] != 'porte': continue
            sd = s.sides[side]; a = sorted((sd['conv'](h[0], h[0]) if side in 'NS' else sd['conv'](0, h[0]), sd['conv'](h[1], h[1]) if side in 'NS' else sd['conv'](0, h[1])))
            u = a[1] + 2.0
            if u + 1.6 < sd['L']:
                s.frame_mur(side, u + 0.8).text((0, 6.2, 0.05), (2.6, 0.9, 0.06), e.nom.upper(), txtcol=(250, 250, 250), bg=(40, 70, 110), name='PlaqueSalle', cc=False)
            break
        else: continue
        break
    # eau dans les salles inondées
    if e.d.get('eau'):
        it = Frame(sc, e.folder + '/Eau', (0, 0, 0)).box(((e.X0 + e.X1)/2, e.elev + e.d['eau']/2, (e.Z0 + e.Z1)/2), (s.W - 1.6, e.d['eau'], s.D - 1.6), 'Glass', (30, 70, 70),
                                                         name='Eau', cc=False, tags=['Eau'])
        it['t'] = 0.35; it['r'] = 0.2
